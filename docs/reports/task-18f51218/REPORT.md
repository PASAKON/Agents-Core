# REPORT task-18f51218

Implemented the Contabo Flow spend card route. Owner: CTO Main (cto-fresh).

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
- Final result: **138 passed** (26 card tests, 112 existing flow_shoot tests), 10.57 seconds.
- The offline filtered-tree test copies only repository .py/.yaml/.toml files and successfully runs:
  /usr/bin/python3 tools/flow_shoot_card.py --help
- A second system-Python import check confirms requests, playwright and tools.flow_shoot are not imported by the card.
- git diff --check passed.
- No SSH connection, live API call, browser access or spend occurred.

## Exact proposed dry-run card argv
```text
python3 tools/flow_shoot_card.py --max-credits 20 --sheet /opt/MoonieXHQ/Agents/Core/docs/scripts/banchi-ACT2.md --ledger /opt/MoonieXHQ/Agents/Core/state/banchi/ACT2.tsv --dest /opt/MoonieXHQ/Agents/Core/state/banchi/flow-card-dry-run --only 37 --resolution 360p --dry-run --channel ILAG --purpose "Flow card dry run" --kind test --task task-18f51218 --who cto-fresh
```

The Run label must also declare a 20-credit cap. Before issuing this example, CTO must use the intended existing sheet/shot ledger and ensure that sheet contains exactly one full https://flow.google.com/.../project/<id> URL identifying its own lane. Missing or ambiguous project identity fails closed with exit 4. These live paths and shot selection were not validated by this worker.

## Not checked / risk
- Windows SSH, msvcrt locking, the installed interpreter/dependencies, ffmpeg/ffprobe, real Flow DOM and live end-to-end execution remain for the CTO's dry-run card. Browser access was expressly prohibited.
- The existing balance reader's DOM behavior is retained; tab selection is tightened to the exact project (or its edit route), requires exactly one match, and reloads on every read.
- The existing shot TSV has no credit-estimate column. The remote worker therefore persists a separate per-run charges.tsv from the runner's submitted-shot estimate messages. If the after balance fails, accounting sums that journal and explicitly labels the amount an estimate. A kill between Submit and its log line can omit an estimate.
- Shared-account activity outside this card lock can affect the balance delta. The row records both balances; a delta over the card cap exits 6.
- A SIGKILL cannot trigger local pullback/accounting. The remote run may continue up to its own cap; its private files are retained for recovery. SSH/host loss can likewise require recovery from the retained run folder.
- Existing clips are compared by sha256 and never replaced with different content. The shot ledger is updated only if its original digest still matches; conflicts retain remote artifacts and return exit 2 after accounting.
- Clip transfer currently buffers each RPC response in memory; very large runs should be split into smaller cards.
- A balance increase is rejected by the existing credit-ledger helper's negative-amount rule and requires manual reconciliation.

## Blockers
- None for offline implementation and validation. Live acceptance is intentionally deferred to CTO.

## Skill learning
- (none)

