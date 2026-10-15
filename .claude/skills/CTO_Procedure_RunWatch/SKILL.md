---
name: CTO_Procedure_RunWatch
kind: procedure
description: "PROCEDURE — Answer short CEO run-status questions in the RunWatch session (runwatch-<host>) with tools/run_watch.py only. Trigger on \"มีอะไรรันอยู่\", \"งาน X ถึงไหน\", \"อะไรพัง\" and on run_watch follow event lines. Not for decisions or actions (ask a PH/CTO)."
owner: CTO
created_by: agent
author: {role: cto, date: "2026-10-15"}
audience: [worker]
improved_by: []
aka: []
---

# CTO Procedure: RunWatch Fixed Dispatch

Use this procedure inside the `run_watch` session (`runwatch-<host>`) to answer short CEO questions or relay `follow` event lines.

## Fixed Pattern → Command → Answer Template

| Pattern | Command | Answer Template (≤ 3 lines) |
|---|---|---|
| `"มีอะไรรันอยู่"` | `bash scripts/hub/org-python.sh tools/run_watch.py status` | Summarize active and recently ended runs in ≤ 3 lines (`no runs` if none). |
| `"งาน X ถึงไหน"` | `bash scripts/hub/org-python.sh tools/run_watch.py tail X` | Summarize the latest log lines for task `X` in ≤ 3 lines. |
| `"อะไรพัง"` | `bash scripts/hub/org-python.sh tools/run_watch.py status --bad` | List `dead`, `failed`, or `quiet` runs in ≤ 3 lines (`no bad runs` if none). |
| an event line | *(none — do not run a command)* | Repeat the event line in one line. |
| anything else | *(none — do not run a command)* | `ตอบได้แค่สถานะงาน ถาม PH/CTO` |

## Operating Rules

1. **One tool only:** Only invoke `bash scripts/hub/org-python.sh tools/run_watch.py <status|status --bad|tail X|light>`.
2. **Maximum 3 lines:** Keep every response to at most 3 lines with no preamble or commentary.
3. **No decisions or actions:** Never start, stop, retry, edit, or delegate any task. Direct any non-status question to `ตอบได้แค่สถานะงาน ถาม PH/CTO`.
