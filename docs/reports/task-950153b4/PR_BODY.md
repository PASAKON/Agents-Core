PH brain CLI formatting could raise `KeyError('fallback_triggered')` when a result omitted fallback metadata. Read that optional field defensively and include it in every returned turn result, including timeouts. Make the Haiku shell's outage escalation duties explicit: it must send its owner a blocker letter and may open a GitHub issue without a brain reply.

Validation: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_ph_brain.py` — 11 passed; the new cases failed before the fix (3 failed, 8 passed). All AGY calls were mocked. `git diff --check` passed.

The CLI regression simulates missing metadata at the result boundary; this checkout's success producer already includes it and its timeout branch bypasses that reader. The live producer behind the incident and model oscillation remain unconfirmed. Details: `docs/reports/ph-brain-fallback-keyerror/REPORT.md`.
