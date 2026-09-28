# docs/ops/mesh-probe/

Landing zone for Org Mesh L3 acceptance-test probes
(`tools/mesh_check.py --live`, `docs/ops/mesh-check.md`, `roles/probe.md`).

- **Written by**: the `probe` worker role only, one file per delegate
  direction: `<from>-<to>.md` (e.g. `mac-contabo.md`).
- **Overwritten every run** — a probe file holds the result of the most
  recent `<from>-><to>` delegate cycle, not a history. Diffing this folder
  across commits is how you see whether a route was ever exercised, not how
  you see every time it was.
- **Nothing else lives here.** No other role, script, or manual edit should
  add or modify a file in this folder — it exists solely as the probe's
  one allowed write target (CEO decision 2026-09-28).

Format of each file: exactly one line —
`<ISO-8601 UTC> task=<task_id> ran_on=<self host key> from=<from> to=<to>`
