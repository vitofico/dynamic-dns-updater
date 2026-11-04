# Security and privacy

During private preparation, contact the repository owner through the existing private collaboration channel. After publication, use [GitHub private vulnerability reporting](https://github.com/vitofico/dynamic-dns-updater/security/advisories/new) when available. If it is unavailable, open a minimal issue requesting a private contact channel without technical disclosure. Never post credentials, update URLs, raw provider responses, real domains, or production logs in public issues.

Provider tokens authorize DNS changes. Grant only the permissions needed for the intended zone, store credentials in a protected environment file or your platform's private secret store, and rotate exposed credentials. `.env`, local settings, and production diagnostics must remain outside Git. Do not mount unrelated credentials or the Docker socket into the updater.

Before publication, inspect every eligible file, scan the exported snapshot and all candidate Git refs with an offline secret scanner, and independently review personal identifiers and publication metadata. This fresh repository and its new image package are reviewed independently of any private legacy history. Also inspect PR discussions, release assets, Actions logs, build artifacts, and container metadata before changing visibility. Keep audit evidence and private identifier lists outside this repository.
