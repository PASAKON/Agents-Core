# `state/` — legacy runtime location

Databases, queues, logs, locks, reports, and live session metadata have historically
been written here. Most contents are already ignored.

- Do not add durable source or project knowledge here.
- The target is a configurable runtime root outside the Git checkout.
- Existing tracked fixtures must be reviewed before migration; do not move them blindly.
