# `runners/`

Long-lived agent processes and executable orchestration entrypoints.

- A runner assembles capabilities and lifecycle behavior; reusable logic belongs in `lib/`.
- Permission checks must not be bypassed in runner-specific code.
- Session logs, PIDs and process state belong in the external runtime root, not here.
