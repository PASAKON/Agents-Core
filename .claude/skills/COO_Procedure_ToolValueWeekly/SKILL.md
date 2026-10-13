---
name: COO_Procedure_ToolValueWeekly
kind: procedure
description: PROCEDURE — Relay the Monday "are our tools worth it" report (tools/tool_value.py) to the CEO unchanged, have a doubted number checked, and turn each tool under its floor into one dated LungNote to-do. Trigger on /COO_Procedure_ToolValueWeekly, on the Monday letter from "CTO tool-value", "รายงานความคุ้มค่าเครื่องมือ", "เครื่องมือคุ้มไหม", "tool value report". Do NOT use it to build or repair the script (the CTO's job, plan §6) or to route one task (CXO_Gate_RouteFirst).
owner: COO
audience: [coo, cto]
created_by: agent
author: {role: cto, date: "2026-10-14"}
improved_by: []
aka: []
---

# The Monday tool-value report: relay it, check it, act on its flags

Input: one hub letter from `CTO tool-value`, Monday about 08:00 BKK · Output: the CEO's copy, ≤5 LungNote to-dos,
one line to the CTO on duty · Tool: `tools/tool_value.py`. It is run by the Contabo timers (collect 07:30, report
08:00, Asia/Bangkok). You never run it. Plan: `docs/plans/tool-value-weekly-and-enforcement-2026-10-13.md`.
CEO order 13 Oct 2026; subscription target 14 Oct ($320 → $140 a month).

## What arrives

- **One letter.** The sender is `CTO tool-value`: the timer itself, not a session and not the CEO. The same text
  is in `state/reports/tool-value/<week>.md`, next to `.json` and a `.sent` marker. These files are gitignored,
  because Agents-Core is public.
- **Shape:**
  - header lines 1–5, from a fixed Thai template (0 model tokens);
  - the table: the previous window vs the current one, the delta, and a per-day rate;
  - the subscriptions against the CEO's target;
  - the bucket state at each Claude reset;
  - the runner-fit table;
  - context sizes;
  - `ต่ำกว่าเกณฑ์`, the idle list;
  - `คำถามถึง CEO`, on 19 Oct only.
- **Every number carries a label:**
  - `วัดจริง` = measured;
  - `ประมาณการ` = estimated;
  - `ไม่มีข้อมูล` = no source, never a zero;
  - `ไม่มีข้อมูล (Mac)` = the Mac collector is not installed yet. winbox data starts 26 Oct at the earliest.
- **The windows:**
  - Every week: Mon 00:00 to Sun 24:00 BKK.
  - The first report, Mon 19 Oct, compares 6–12 Oct with 13 Oct → 19 Oct 07:00.

## Steps

1. **Did it arrive?** Check by 08:30 BKK. The Contabo clock prints CEST until 25 Oct, so 08:30 BKK is 03:30 CEST.
   - No letter → send the CTO on duty one line, `tool-value letter missing <date>`, and stop.
   - Never run the script, start a unit or write a report yourself.
   - *Stop:* the letter is in.
2. **Relay it to the CEO as it is.** Send header lines 1–5 and the table through your channel to him.
   - Do not reword a number, drop a label or add a figure of your own. A label stays next to its number (CEO: "อย่าหลงข้อมูล").
   - If the table is long, put the 5 lines inline and send the rest as the file.
   - *Stop:* sent, in one turn.
3. **Questions** (19 Oct, and any week that carries them).
   - Ask each one once: on a question card (`ask_ceo`) if your org MCP works, otherwise in the same message. Never repeat a pending question.
   - Send each answer word for word to the CTO on duty:
     - floors → `FLOORS` in `tools/tool_value.py`;
     - the Rules line and the Agent-hook block mode → plan §5 and §4.3 M2.
   - *Stop:* every question is answered, or carried to next Monday.
4. **Flags → to-dos** (plan §4.3 M3). For each line under `ต่ำกว่าเกณฑ์`, first search the open LungNote to-dos for `tool-value · <tool>`.
   - **None open** → `add_todo` with the text `[SomPong · tool-value · <tool>] ต่ำกว่าเกณฑ์ <week>: <value> (เกณฑ์ <floor>) → <owner>: <job>`. The deadline is the line's due date, next Monday.
   - **One open from an earlier week** → don't add another. Append this week's value to it. If the number has not moved for two weeks running, tell the CEO so in the next relay.
   - **A tool back above its floor** → complete its to-do with this week's number.
   - The idle list never has more than 5 lines, so there are never more than 5 to-dos a week.
   - *Stop:* every idle line has exactly one open to-do.
5. **Close the loop.** Send the CTO on duty one line: `relayed <week> · questions <asked>/<answered> · to-dos +<added> ~<updated> ✓<completed>`.

## The floors (proposed until the CEO rules, plan §7 Q1)

| Tool | Floor | Where the number comes from |
|---|---|---|
| AGY (Gemini, Claude bucket), Codex | ≥50% of the weekly quota, at a full-week pace | quota-history drops, measured |
| Jules | ≥10 sessions a week (PRs count as a lower bound when sessions are `ไม่มีข้อมูล`) | the Jules session list, GitHub branches |
| JEV | ≥1 call per wired site a week | jev_lab balance |

They print as `เกณฑ์ที่เสนอ` until the CEO rules. A missing source never trips a floor.

## Verify a number the CEO doubts

- **Your side:** read the `.md` and the `.json`. The `.json` lists each source and whether it was read (`missing:`).
- **The CTO on duty** re-runs it read-only and compares the cell with its source (plan §2: quota-history, the hub
  task table, the transcripts, the credit ledger). It prints only, and writes and sends nothing:
  `bash scripts/hub/org-python.sh tools/tool_value.py report --dry-run --week <start-date>`
- **Answer him with the label.** An estimate (`ประมาณการ`) is never passed off as a measurement.

## Repair (CTO)

- **The units:** `tool-value-collect` and `tool-value-report`, systemd timers on Contabo, installed by Run card
  RUN-20261013-2000-8e8f. They run from the deploy worktree `worktrees/tool-value-deploy`, which is pinned to one
  sha. New code reaches a Monday run only after that worktree moves to the new sha.
- **Send again after a fix:** `report --force-send`. Without it, the `.sent` marker refuses a second send.
- **Hub down:** `collect` and `report` exit 3 when the hub does not answer, and nothing is sent.

## Failure modes seen

- **2026-10-14:** a mid-week dry run read "Claude now $20". It clamps the window to the current time, which fell
  before the 14 Oct $200 entry in `config/plans.yaml`. A Monday run ends its window on Monday and reads correctly.
- **2026-10-13:** agy_browse calls made by workers were lost with their worktrees. Fixed in 1116f7c8: the main log
  plus a hub event.
- **2026-10-14:** the Agent-tool hook cannot reach the hub from a C-level session (no ORG_DB_URL, and no psycopg in
  the system python). It spools to `state/reports/agent-calls.jsonl` instead.

## Field notes
