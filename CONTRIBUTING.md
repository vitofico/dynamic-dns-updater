# Contributing

Keep changes focused on the one-shot updater. Preserve the POSIX shell implementation and provider configuration contracts. Deployment-specific schedules, domains, credentials, and infrastructure belong in consuming repositories.

Run `make lint test` before proposing a change. Provider-specific synthetic environment files live in `examples/`; copy them to ignored `.env` files rather than adding real settings to fixtures. Add offline tests for changed provider behavior; never make live DNS requests from CI. Review provider changes against their official API documentation. Run `make build smoke` where Docker is available and disclose any checks you could not run.

Use synthetic hostnames under `example.invalid`, documentation IP ranges, and clearly synthetic credentials. Review the final diff for private data. Report vulnerabilities as described in [SECURITY.md](SECURITY.md).
