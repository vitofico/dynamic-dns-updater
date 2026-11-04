# Dynamic DNS Updater

A small, one-shot container for updating DuckDNS, FreeDNS, Dynu, or deSEC/dedyn DNS records. It performs one update and exits: `0` means every requested update was accepted; nonzero means configuration, transport, HTTP, or provider failure.

Source: [vitofico/dynamic-dns-updater](https://github.com/vitofico/dynamic-dns-updater).
Container: `ghcr.io/vitofico/dynamic-dns-updater/updater`.
An optional [Kubernetes Homelab Kit integration](https://github.com/vitofico/kubernetes-homelab-kit/blob/feat/companion-tool-images-20261104/docs/dynamic-dns.md) is prepared on the companion-image branch and is pending merge.

## Build and check without provider traffic

Docker is required. Build locally and run the isolated smoke check; these commands need no provider credentials and send no DNS updates:

```sh
git clone https://github.com/vitofico/dynamic-dns-updater.git
cd dynamic-dns-updater
make build
make smoke
```

The smoke check disables networking and verifies the image runs as a non-root user and rejects missing credentials with the expected error. `make build` downloads container dependencies. During private preparation, cloning requires repository access; published image pulls also require registry access until the packages are made public.

## Configure and run one real update

Choose the example for your provider, copy it to the ignored `.env`, and replace every synthetic value with your own settings using a local editor:

```sh
cp examples/desec.env.example .env  # or duckdns, freedns, dynu
chmod 600 .env
```

After reviewing those settings, this command **contacts the selected provider and updates DNS**:

```sh
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --env-file .env ghcr.io/vitofico/dynamic-dns-updater/updater:dev
```

A successful run prints `DNS update accepted` and exits with status zero. The root `.env.example` remains a DuckDNS starter for existing workflows. Use separate invocations/environment files to update different providers.

For released images, select a published version and pin its **registry digest** rather than `latest`. Release metadata includes source revision, SBOM, and build provenance. The image runs as UID/GID `65532` and writes no local state. It requires outbound HTTPS and DNS resolution, and no inbound ports or Kubernetes API access.

The script can also run directly with POSIX `sh` and curl. It uses fixed HTTPS endpoints with certificate verification, a 10-second connection timeout, a 30-second request timeout, and a 64 KiB response limit. It does not follow redirects or retry automatically. Logs omit hostnames, tokens, raw provider responses, and curl diagnostics. Credentials remain visible to privileged processes through their environment/arguments; use a dedicated runtime and never enable shell tracing.

## Provider configuration

Set `DNS_PROVIDER` to one of the following; it defaults to `duckdns`. Only the selected provider's variables are required. Comma-separated lists must not contain spaces or empty entries.

| Provider | Required variables | Behavior |
| --- | --- | --- |
| `duckdns` | `DUCKDNS_TOKEN`, `DUCKDNS_DOMAINS` | Domains are comma-separated DuckDNS subnames; discovers the outbound IPv4 address. |
| `freedns` | `FREEDNS_TOKEN` | One or more comma-separated [FreeDNS v2 update tokens](https://freedns.afraid.org/dynamic/v2/). Requests run sequentially; the first failure stops the run. Earlier updates are not rolled back. |
| `dynu` | `DYNU_PASSWORD` and exactly one of `DYNU_HOSTNAME` / `DYNU_GROUP` | Uses the provider's update password/hash and discovers the outbound IPv4 address. |
| `desec` | `DESEC_TOKEN`, `DESEC_DOMAINS` | Domains are full hostnames, comma-separated within one deSEC zone. Authenticates with a token header. |

Example deSEC `.env` with synthetic settings (replace values before running):

```dotenv
DNS_PROVIDER=desec
DESEC_TOKEN=replace-with-your-token
DESEC_DOMAINS=home.example.invalid,service.example.invalid
DESEC_IPV4=auto
DESEC_IPV6=preserve
```

### deSEC address families

The default is `DESEC_IPV4=auto`, `DESEC_IPV6=preserve`: connect over IPv4, discover that address, and retain existing AAAA records. To discover IPv6 instead, use `DESEC_IPV4=preserve`, `DESEC_IPV6=auto`. Either variable also accepts an explicit address. At most one family may be `auto`; explicit empty values are rejected to prevent accidental record deletion. Automatic discovery records the provider-visible outbound address, which may belong to a proxy or NAT gateway.

The [official deSEC API contract](https://desec.readthedocs.io/en/latest/dyndns/update-api.html) describes token permissions, same-zone hostname lists, rate limits, and address-family semantics. This client intentionally provides no record-deletion mode.

## Schedule updates

Use an external scheduler, such as cron, a Kubernetes CronJob, or Argo Workflows. Choose an interval compatible with your provider's rate limits, prevent overlapping runs, and alert on nonzero exits. The process exits after one update; it does not run an internal update loop. No real provider request runs as part of default tests.

For a Linux host with Docker and `flock`, [examples/cron.example](examples/cron.example) shows a 15-minute user-crontab entry. After verifying one real update:

1. Create `local/` in the checkout for the lock and log: `mkdir -p local`.
2. Replace the checkout and executable paths in the example, and select your reviewed image digest.
3. Install the reviewed entry with `crontab -e`, removing its leading `#` to enable it.
4. Verify the next run and arrange log rotation and failure monitoring. The lock prevents overlapping invocations; providers can still impose stricter intervals.

For Kubernetes, review the proposed [Homelab Kit dynamic DNS module](https://github.com/vitofico/kubernetes-homelab-kit/blob/feat/companion-tool-images-20261104/docs/dynamic-dns.md), which is pending merge on the companion-image branch. The proposed module starts suspended and stores credentials separately from image configuration.

## Migration

The executable is `/usr/local/bin/update_dns.sh`; replace any override calling the former `/usr/local/bin/update_duckdns.sh`. Removing the override also uses the new image's default command. The source repository is now `vitofico/dynamic-dns-updater`; new images use the clean package path `ghcr.io/vitofico/dynamic-dns-updater/updater`.

The existing `DNS_PROVIDER` and provider variables are retained. deSEC preserves IPv6 records by default; review the address-family settings before migration. Move scheduling, domains, credentials, and deployment-specific configuration into your own deployment repository. Existing private repositories and images can remain available until their consumers have verified cutover. Registry packages and repository visibility are managed independently.

## Development and releases

```sh
make lint test  # shellcheck, POSIX syntax, offline subprocess tests
make build smoke  # local build plus isolated runtime check
```

Python 3 and ShellCheck are development dependencies. Tests replace curl and send no DNS updates. CI also builds the image and checks non-root, read-only startup with missing credentials and networking disabled. Successful `main` pushes and manual workflow dispatches publish source-SHA images at `ghcr.io/<repository>/updater`; `vX.Y.Z` tags publish versioned images and `latest`. Forks inherit their own repository image namespace. This fresh source repository intentionally begins with a reviewed release baseline.

Before public release, review the final source, commit identity, Actions logs/artifacts, releases, image contents, and build metadata. After the companion kit branch is merged, switch its documentation links above to `main`; retain the pending-merge label until then. Verify an authenticated pull while private. After repository and intended package visibility change, separately verify an anonymous clone and image pull, then exercise the documented setup from a clean directory. Keep private audit evidence and real deployment data outside this repository.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [Changelog.md](Changelog.md). Original source is MIT licensed; Alpine, curl, and bundled dependencies retain their upstream licenses.
