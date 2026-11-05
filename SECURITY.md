# Security and privacy

Report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/vitofico/dynamic-dns-updater/security/advisories/new). If that channel is temporarily unavailable, open a minimal issue requesting a private contact channel without technical disclosure. Never post credentials, update URLs, raw provider responses, real domains, or production logs in public issues.

Provider tokens authorize DNS changes. Grant only the permissions needed for the intended zone, store credentials in a protected environment file or your platform's private secret store, and rotate exposed credentials. `.env`, local settings, and production diagnostics must remain outside Git. Do not mount unrelated credentials or the Docker socket into the updater.

Before releases, inspect every eligible file, scan the snapshot and all Git refs with an offline secret scanner, and independently review personal identifiers and release metadata. Also inspect PR discussions, release assets, Actions logs, build artifacts, and container metadata for accidental disclosure. Keep audit evidence and private identifier lists outside this repository.
