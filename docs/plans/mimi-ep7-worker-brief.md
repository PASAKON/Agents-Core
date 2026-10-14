# Worker brief: EP7 shoot + QC + cut (MimiPage, PH #36c49776)

**Status: APPROVED by cmo-ef04792e 14 Oct (with 4 fixes, applied). Delegated only once BOTH the CEO's «go ยิง» AND his engine answer (Flow, or the Higgsfield Seedance 2.0 free lane) have reached the PH through the C-level. If the engine is Higgsfield, this brief is rewritten first (`CMO_Knowledge_Seedance2.5_Higgsfield`).**

## Job (one line)
SHOOT EP7 «ทำไมมีมี่ไม่ยอมนอนกับแม่ ต้องรอพี่ชายกลับดึก?» in Google Flow (12 shots, 720p, 10 s), QC it, CUT it to `EP7-cut-v1.mp4`, and hand the PH a 540p file **by Sat 17 Oct 15:00 Thai** (the PH reviews it, and the CEO gets it by 18:00).

## Authority + money
- CEO «go ยิง» quoted by the PH at delegation, budget per brief: ≤330 cr/episode. This episode: **test 14 cr (2 × 7, 360p 10 s) + production 180 cr (12 × 15) + reshoot ≤3 shots/≤45 cr = `--credit-cap` 239 total.**
- Plan on a balance of 298 (the live read was 348 on 14 Oct; the +50 is unexplained). Read the balance live (`tools/flow_balance_ws.py --reload` on winbox) **before the test, after the test, and after production**, and write a ledger row in `docs/ops/credit-ledger.jsonl` for each spend (`who: <worker id> for project_head-36c49776`). **Write the rows on your own branch from origin/main (a worktree) and open a PR. Never commit to Contabo's local main, never push to main** (local main has uncommitted ledger edits and a held commit).
- A second test round, or a 4th reshoot, needs a new OK from the PH. Stop at any dialog that shows a credit cost you did not expect.

## Inputs (all ready, checked 14 Oct)
- Sheet: `docs/scripts/khaoniao-ep7-ACT1.md` (copy on winbox: `C:\mooniex\khaoniao\ep7\sheets\EP7.md`). Script: `khaoniao-ep7-SCRIPT-v1.md`.
- Flow project: Mimi `29b3326b`, Chrome **:9226**. All 8 handles are attached; dry run 12/12 OK (`ep7\ledger_dry3\flow_shoot.log`).
- Runner: `C:\mooniex\Agents\Core\tools\flow_shoot.py run --sheet … --ledger C:\mooniex\khaoniao\ep7\ledger\ACT1.tsv --dest C:\mooniex\khaoniao\ep7\clips --cdp-url http://127.0.0.1:9226 --expect-gb 1` (+ `--download-resolution 720p`). Launch through a `.cmd` file with `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`.
- Prep and cut plan: `docs/plans/mimi-ep7-prep.md`. Cut pattern: `docs/scripts/mimi-ep6-cut-manifest.json`.

## Steps
1. Balance read. Then a **360p test, shots 2 + 4** (`--resolution 360p --only 2,4`, separate ledger `ledger_test`). Pass = night reads as night, the right mouth speaks, the mother's and Riao's voices fit the line, no text, no extra people or animals. Send the PH both clips. **Wait for the PH's OK** (the CEO ear-checks the voices).
2. Production: shots 1–12 at 720p, `--credit-cap` = what is left of 239.
3. QC per `CMO_Gate_Flow_Omni1.1_FilmQC`: transcript per shot (≥0.82 like EP6), and a contact sheet. Read the untested plates first: landing_night (shot 9), broroom_night (10, 11). Fail list → the PH, who decides the reshoots (≤3).
4. Cut per the plan: 120 s plus a ~2.5 s title card after shot 6, M1 piano, **NO watermark or logo burned in**: the CEO answered «ขอดูก่อน» on Q-20261014-0225-c960, so deliver a clean cut and say so in the hand-off. Output 720×1280 24 fps, plus a 540p file.
5. Hand-off: the note «clean cut, no watermark (waits CEO pick c960)», the paths of `EP7-cut-v1.mp4` and the 540p, the QC sheet, the ledger rows, and the balance reads.

## Never
- Schedule or post anything on Facebook: the PH does that after the CEO says go.
- Use winbox's screen, or any Browser Home other than :9226.
- Delete any clip.
- Message the CEO.

## Skills
`CMO_Knowledge_Flow_Omni1.1`, `CMO_Gate_Flow_Omni1.1_Continuity`, `CMO_Gate_Flow_Omni1.1_FilmQC`, `CMO_Workflow_MimiPage_Weekly` (house format), `CMO_Standard_Story_FamilyDogSeries`.
