# `lib/`

Shared infrastructure used by more than one runner or tool: persistence,
configuration loading, logging, messaging, and common domain primitives.

- Keep provider-specific integration code in `tools/` or the future adapters package.
- Do not store runtime databases, credentials, project content, or generated files here.
- New modules should have tests and avoid machine-specific absolute paths.
