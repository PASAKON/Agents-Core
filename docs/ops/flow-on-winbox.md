# Flow on winbox — CEO ruling 2026-09-26

> "Generate คลิป Google Flow ทำบน Window ... ฉันจะใช้ MAC ตัดต่อ Video"

Flow generation runs on **winbox's Chrome**, never the Mac. The Mac is for
editing. `tools/flow_cdp.py` enforces this in code: every Flow tool refuses
to run on `darwin` (exit 2) unless `FLOW_ALLOW_MAC=1` is set.

All four Flow tools (`flow_shoot.py`, `flow_upload_element.py`,
`flow_music.py`, `flow_reupscale.py`) now share one CDP endpoint,
resolved by `tools/flow_cdp.py` in this order: `--cdp-url` flag →
`$FLOW_CDP` env → default `http://127.0.0.1:9226`.

## 1. Start Chrome on winbox (once per boot / crash)

SSH lands in Windows session 0, which has no desktop — a headed Chrome can
only be started via an **interactive scheduled task**, run as the logged-in
user (`gob\passg`). This is already registered as `MooniexFlowChrome9226`.

```
ssh winbox "powershell -NoProfile -Command \"Start-ScheduledTask -TaskName MooniexFlowChrome9226\""
```

That runs `C:\mooniex\flow-chrome\flow-chrome-debug.cmd`, which launches:

```
chrome.exe --user-data-dir=C:\Users\passg\.flow-automation\chrome-profile
           --remote-debugging-port=9226
           --no-first-run --no-default-browser-check --disable-notifications
           https://labs.google/fx/th/tools/flow
```

**Never `taskkill` Chrome by name on winbox** — the CEO's own Chrome runs on
that machine too, under a different profile. If 9226 needs a fresh Chrome,
close only the Flow window by hand (or `Get-Process | Where CommandLine
-match '9226'` to target that PID specifically), then re-run the task above.

Re-registering the task from scratch (if it's ever missing):

```
scp windows/flow-chrome-debug.cmd winbox:C:/mooniex/flow-chrome/flow-chrome-debug.cmd
scp windows/flow-chrome-task-register.ps1 winbox:C:/mooniex/flow-chrome/flow-chrome-task-register.ps1
ssh winbox "powershell -NoProfile -ExecutionPolicy Bypass -File C:\mooniex\flow-chrome\flow-chrome-task-register.ps1"
```

**Any of this counts as an app launch on winbox's desktop — take a
`winbox-pc-lease` first** (`./scripts/pc-lease.sh take --who "..."`, then
`give-back` right after the task starts; you don't need to hold the lease
while Chrome keeps running).

Verify the port is up (read-only, no lease needed — this is just an HTTP GET):

```
ssh winbox "powershell -NoProfile -Command \"(Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:9226/json/version').Content\""
```

## 2. Log in once

Google AI Ultra account, this Chrome profile only, never typed by an agent —
follow the `relay-login` skill. Once logged in, the session persists in
`C:\Users\passg\.flow-automation\chrome-profile` across restarts of the task.

## 3. Run a shoot

The orchestrator (`flow_shoot.py`) itself must also run on a non-Mac box —
winbox directly, or any machine that can reach `winbox:9226` (e.g. Contabo
over the tailnet). `--cdp-url` only needs to be passed explicitly from a
machine other than winbox itself; on winbox the default already points at
`127.0.0.1:9226`.

```
python tools/flow_shoot.py status --ledger <ledger.tsv>

python tools/flow_shoot.py run --sheet <sheet.md> --ledger <ledger.tsv> \
    --dest <download-folder> --credit-cap <N> --cdp-url http://<winbox-host>:9226 \
    [--only 37-46] [--dry-run]

python tools/flow_shoot.py pull --sheet <sheet.md> --ledger <ledger.tsv> \
    --dest <download-folder> --cdp-url http://<winbox-host>:9226 [--only 53-58]
```

Clips land in whatever `--dest` was given, on the machine that ran the
command — i.e. if `flow_shoot.py run` runs ON winbox, clips land on
winbox's disk at that `--dest` path.

The run log defaults to `<ledger dir>/flow_shoot.log` now (was hardcoded to
`state/banchi/flow_shoot.log`); `--log` still overrides it.

## 4. Pull finished clips to the Mac

```
bash scripts/flow/winbox_pull.sh 'C:\path\on\winbox\to\dest' ~/Desktop/wherever-on-mac
```

Lists every file under the winbox dir (size + sha256, via
`scripts/flow/winbox_pull_helper.py`, scp'd over and run with whatever
`python` winbox has), skips anything already identical locally, pulls the
rest over `scp`, and re-verifies size + sha256 after each transfer. Prints
`total/pulled/skipped(identical)/failed` and exits non-zero on any failure.

## Notes

- `FLOW_ALLOW_MAC=1` exists only for genuine one-off debugging on the Mac —
  it prints a loud warning and is not for production shoots.
- The old Mac-era ports (9223 shoot/upload, 9224 music) are gone; everything
  is 9226 now, one Chrome, one profile, on winbox.
