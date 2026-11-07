supersedes #673

PH telemetry must not abort a brain turn when the hub is missing or a write fails. Skip unavailable telemetry, refuse local SQLite recording, and emit exactly one warning per turn across model fallback attempts. Preserve start/end recording when the hub is available and retain #674's fallback metadata and shell rule 6.

Validation: 154 focused tests passed, including the real-CLI fallback regression. Rebased onto cached main 341d0dd4. Full-suite acceptance remains blocked: socket operations are denied in the worker sandbox, and the run stalled at 15% before interruption. See REPORT.md and diagnostic logs; an unrestricted full-suite rerun is required before merge.
