# `tests/`

Automated checks for the shared MoonieX control plane.

- Tests must use temporary state and must never connect to production by accident.
- Provider integrations should be faked unless a test is explicitly marked as external.
- Personal knowledge and project checkouts cannot be prerequisites for the core suite.
