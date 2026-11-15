# REPORT task-81e26a3c

## Summary
Read the live Flow balance (6,930 credits) and the per-clip price of every available model in เฟรม / 16:9 / x1 on winbox Chrome :9226, computed 102-clip totals and wrote /opt/MoonieXHQ/Work/cn-series/plan/EP04-flow-estimate.md (copy in docs/reports/ep04-flow-estimate-20261115/). Nothing was generated; balance read 6,930 before and after.

## What I Observed
- Balance 6,930 credits (ULTRA plan), read 2026-11-15 ~10:05 and ~10:12 TH.
- EP04-FULL-SHEET.md: 120 shots, all 15 s; 102 Type: flow, 18 still+fx. EP04-S029.png (a flow shot) is missing from stills/ep04.
- Only Omni 1.2 Flash offers 15 s (slider 3-15 s). Omni 1.1 max 10 s; Veo 3.1 max 8 s.

| Model | Quality | cr/clip | sec/clip | Total 102 | Balance after | Clips covered |
|---|---|---|---|---|---|---|
| Omni 1.2 Flash | 720p | 60 | 15 | 6,120 | 810 | 115 |
| Omni 1.2 Flash | 360p | 20 | 15 | 2,040 | 4,890 | 346 |
| Omni 1.1 Flash (retires 5 Dec) | 720p | 15 | 10 | 1,530 | 5,400 | 462 |
| Omni 1.1 Flash | 360p | 7 | 10 | 714 | 6,216 | 990 |
| Veo 3.1 Lite | n/a | 5 | 8 | 510 | 6,420 | 1,386 |
| Veo 3.1 Fast (retires 5 Dec) | n/a | 10 | 8 | 1,020 | 5,910 | 693 |
| Veo 3.1 Quality (retires 5 Dec) | n/a | 100 | 8 | 10,200 | -3,270 | 69 |

Omni 1.2 Flash curve: 360p 3s=3 ... 10s=10, 11s=12, 12s=14, 13s=16, 14s=18, 15s=20; 720p 3s=9 ... 10s=30, 11s=36, 12s=42, 13s=48, 14s=54, 15s=60.

## Browser Actions
- route: step 5 via raw CDP (tab websocket, javascript_tool-equivalent reads). The claude-in-chrome extension only exposed a macOS browser, not winbox :9226; I used the repo's own stdlib CDP pattern (tools/flow_balance_ws.py). No API for Flow credit prices.
- steps_used: ~25 CDP script runs (no extension browser actions) / no budget stated
- screenshots_taken: 0
- pages_visited: Flow home, one new empty Flow project (ids not recorded here)

## Replay Script
- path: scripts/browser/flow_price_probe/ (cdp.py, helpers.py, bal.py, models2.py, sweep.py, sweep12.py, README.md)
- covers: balance read, model list/price, duration/resolution sweep, Omni 1.2 slider sweep
- brittle: flow-prompt-box-settings, mat-button-toggle, flow-duration-slider input (range 0-12 = 3-15 s), button[role=menuitem] (model menu), [aria-label="รายละเอียดบัญชี"]

## Files Changed
- scripts/browser/flow_price_probe/* — probe scripts + README
- docs/reports/ep04-flow-estimate-20261115/EP04-flow-estimate.md — copy of the estimate
- REPORT.md
- (outside repo) /opt/MoonieXHQ/Work/cn-series/plan/EP04-flow-estimate.md on Contabo, written by scp, md5 25dad057...

## Commits
- see git log on this branch

## Tests
- ran: python -m py_compile on the 6 probe scripts
- passed: 6
- failed: 0
- skipped: 0

## Issues / Blockers
- Chrome :9226 was not running on winbox; I started it via scheduled task MooniexFlowChrome9226 (no other tabs existed, nothing lost; it was already signed in, no login typed).
- I created one empty Flow project (default name) to get a composer; left in place, CEO may delete it. No tab was closed; the Flow tab stays open on that project.
- Shot sheet is on Contabo; read and wrote it over ssh from winbox.
- S029 first frame is missing (see above).

## Notes for Reviewer
- Prices were read with the first-frame slot empty (skill says image-attached delta unmeasured).
- 360p-then-720p costs 80/shot, more than straight 720p at 60/shot, unless many shots are rejected at proof.
- 720p all-in leaves only 810 credits (~13 re-shoots). Shared pool: re-read the balance before the paid run.

## Not checked / risk
- First-frame-attached price for Omni 1.2 not measured; charges, refunds and retries not modelled; Veo output resolution unmeasured; ledger approval state of the 101 other first frames not checked; no clip quality or 15 s beat adherence verified.

## Skill learning
- MISSING [CMO_Knowledge_Flow_Omni1.1 §Money] : model list now Omni 1.2 Flash (15 s slider, 360p 20 / 720p 60 cr at 15 s), Omni 1.1 / Veo Fast / Veo Quality retiring 5 Dec, Veo Lite 5 cr; the skill still says 20 cr Veo Fast 9:16 and Omni 1.1 15 cr/10 s · evidence: task-81e26a3c, docs/reports/ep04-flow-estimate-20261115
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Step order 2] : the claude-in-chrome extension on a winbox session may list only the macOS browser; use CDP on :9226 directly (tab websocket, stdlib) and start the task MooniexFlowChrome9226 if :9226 is down · evidence: task-81e26a3c
- COSTLY [no owner] : Flow model menu items are button[role=menuitem], not [role=option]; I lost ~4 calls on the wrong selector, and a JS string with a literal newline from a Python heredoc raised SyntaxError silently as None · prevented by: run JS from a .js file and print exception details
