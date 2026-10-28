# REPORT task-18f51218

Implemented the Contabo Flow spend card route. Owner: CTO Main (cto-fresh).

CTO iteration 1: restored the reviewed implementation from local commit f88e932c because the assigned worktree started without it, then applied all six requested fixes within the same seven files. The patched attach enforces the platform and brings the selected project tab forward. Pullback lists file names, sizes and SHA256 digests, then fetches and verifies one file per RPC while retaining exclusive clip creation, existing-file comparison and shot-ledger compare-and-swap behavior. Balance reads retry up to three times, five seconds apart. A rising balance uses the charges.tsv estimate sum with an explicit note. Failed taskkill commands report their return code without interrupting pullback or accounting.

## Files changed
- tools/flow_shoot_card.py — strict CLI, live-ledger preflight, balance gates, pinned bundle transfer and remote hash comparison, output streaming, signal termination, pullback, accounting and summary.
- tools/flow_shoot_card_remote.py — stdlib SSH bootstrap, Windows exclusive OS lock, exact-project balance selection, PID-gated child start, project-restricted browser attachment, transfer and charge-estimate journal.
- tools/credit_ledger.py — optional include_balances preserves an explicit null when a balance is unknown; existing callers retain their behavior.
- config/spend-tools.txt — Flow entry and cap/SIGKILL comment; existing lines unchanged.
- tests/test_flow_shoot_card.py — offline fake transport coverage.
- docs/reports/flow-card/REPORT.md and docs/reports/task-18f51218/REPORT.md — this report.

flow_shoot.py is unchanged. The remote launcher supplies its parsed run argv and restricts its browser attachment to the sheet's exact project URL. All code/config bytes come from the card's own checkout. Code lives under C:\mooniex\flowcard\<bundle-sha12>\<unique-run-id> and each transferred file is hashed on Windows before execution. Transfers use base64 JSON over SSH rather than scp.

The balance reader's pinned source is sent over stdin and executed without writing a file before the balance gate. The remote lock is acquired before that gate so competing cards cannot both pass it. Only lock-file infrastructure is created before balance validation.

## Validation performed
- Exact required command:
  /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_flow_shoot_card.py tests/test_flow_shoot.py
- Final result: **163 passed** (51 card tests, 112 existing flow_shoot tests; 148 at iteration 1, +15 in the CTO fixes), 15.01 seconds.
- New offline regression coverage checks foreground attachment (including a foreground exception), three separate clip fetches with incremental writes, remote list/get metadata, clip and ledger hash mismatches returning exit 2, balance retry success/exhaustion, a rising balance, and failed taskkill followed by ledger accounting and exit 143.
- The offline filtered-tree test copies only repository .py/.yaml/.toml files and successfully runs:
  /usr/bin/python3 tools/flow_shoot_card.py --help
- A second system-Python import check confirms requests, playwright and tools.flow_shoot are not imported by the card.
- git diff --check passed.
- No SSH connection, live API call, browser access or spend occurred.

## CTO review fixes (28 Oct, after iteration 1)
- Tabs are matched by project id (`own_tab`): `/project/<id>`, its `/edit/` routes, a query string, a `/u/N/` prefix. The bare project tab is preferred. The exact-string match with "exactly one tab" failed whenever an `/edit/` tab was open next to the project tab, and the runner works in an `/edit/` tab (flow_balance_ws.py docstring).
- When no project tab is open, the card opens one through CDP `PUT /json/new`. This is navigation only and spends no credits. The card never closes a tab. At 23:50 TH on 28 Oct, 9226 had only the Flow home page open, so every card would have exited 4.
- The lock refuses (exit 5, "busy") while an old-way `flow_shoot` run is alive on winbox. Those runs hold no card lock, and the card brings its tab to the front. CMO, 28 Oct: no tab to the front on 9226 during another lane's shoot.
- 163 passed: 51 card tests, 112 flow_shoot tests.

## Fake cards
- First line of each card: "ปลอม (ทดสอบ ไม่ใช้เครดิต)".
- They are raised only after the merge, and only after the CMO relays "ILAG shoot done".

Test copies (untracked, under `state/flowcard-test/`):
- `banchi-ACT2-test.md` = `docs/scripts/banchi-ACT2.md` plus one line naming the banchi project URL.
- `ACT2-test.tsv` = `state/banchi/ACT2.tsv` with shot 37 set to `todo`.
- ACT2 itself is 24/24 verified. A dry run on it prints "nothing to do" and never opens the browser, so the argv this worker first proposed would have tested nothing.

| Card | Own flags | Pass when |
|---|---|---|
| F1 | `--max-credits 20 --dry-run` | a `DRY-RUN shot 37` line, exit 0, one ledger row with amount 0 and kind test |
| F2 | `--max-credits 100000 --dry-run` | "over balance", exit 3, nothing pushed |
| F3 | `--max-credits 1` | flow_shoot's spend-cap stop before Submit, exit 3, balance unchanged |

Shot estimates in the banchi logs run 4 to 15 credits. A cap of 20 therefore lets F1 reach its dry-run line, and a cap of 1 stops F3. If the estimate cannot be read, `EstimateUnreadable` stops F3 before Submit.

Flags shared by all three cards:
`--sheet /opt/MoonieXHQ/Agents/Core/state/flowcard-test/banchi-ACT2-test.md --ledger /opt/MoonieXHQ/Agents/Core/state/flowcard-test/ACT2-test.tsv --dest /opt/MoonieXHQ/Agents/Core/state/flowcard-test/out --only 37 --resolution 360p --channel ILAG --purpose "Flow card fake test" --kind test --task task-18f51218 --who cto-fresh`

## Not checked / risk
- A real card must cover at most 10 shots via --only until a live 40-shot pull is measured.
- Run one Flow job at a time on 9226. The card refuses while an old-way flow_shoot run is alive, but it only sees `python.exe` command lines. A run under another interpreter name, or a person working in the Flow UI, is not detected and can change the balance delta.
- A tab the card opens comes to the front at once (`/json/new` opens a foreground tab).
- Windows SSH, msvcrt locking, the installed interpreter/dependencies, ffmpeg/ffprobe, the real Flow DOM and live end-to-end execution are tested by the fake cards above, not by this suite.
- The existing shot TSV has no credit-estimate column. The remote worker therefore keeps a separate per-run charges.tsv from the runner's submitted-shot estimate messages. If the after balance fails, accounting sums that journal and labels the amount an estimate. A kill between Submit and its log line can leave an estimate out.
- Shared-account activity outside this card lock can affect the balance delta. The row records both balances; a delta over the card cap exits 6.
- A SIGKILL cannot trigger local pullback or accounting. The remote run may continue up to its own cap, and its private files are kept for recovery. Losing SSH or the host can likewise require recovery from the kept run folder.
- Existing clips are compared by sha256 and never replaced with different content. The shot ledger is updated only if its original digest still matches. A conflict keeps the remote artifacts and returns exit 2 after accounting.
- Clip transfer buffers one file's RPC response in memory. A live 40-shot pull and its peak memory use have not been measured.
- When the balance rises, the row records the charges.tsv estimate sum with the note "balance rose by X; amount = estimate sum". Both observed balances stay in the row.

## Blockers
- None for offline implementation and validation. Live acceptance is intentionally deferred to CTO.

## Skill learning
- (none)
