# Changelog

## Unreleased

- Establish the fresh Dynamic DNS Updater repository and isolated `updater` image package.
- Fix provider validation that could report success without sending an update.
- Bound HTTPS requests, reject HTTP/provider failures, and omit sensitive diagnostics.
- Preserve deSEC IPv6 records by default and support explicit address-family configuration.
- Add offline provider regression tests, a non-root image, pinned base, and reproducible source references.
- Document local offline smoke checks, provider environment examples, external scheduling, migration, contribution, and security contracts.

Earlier private development history is intentionally excluded from the public release baseline.
