# Machine Contract — restore runbook

One page per machine for rebuilding it from git + Drive (ADR 0031, IRON §58). Inputs: the
registry `config/machine-contract.yaml`, the HQ map `hq.yaml`, and each machine's latest
committed capture (`state/<machine>-blueprint-<date>/`, written by `scripts/contabo_blueprint.sh`
/ `scripts/mac_blueprint.sh`). `HUMAN` marks a step that needs a person at the keyboard (a
login, an external fetch a script must never automate) — the same wording the restore
scripts print. Nothing here fetches secrets, Drive objects, or touches another machine
automatically; every such step is printed, never executed, by design.

Drill numbers (minutes to remote access, minutes to org restore, bytes from git vs Drive,
human-step count) go in `state/re-os-drills.jsonl` — one JSON line per drill, see "Drill
scoring" below. Where a number below is not yet measured on a real drill, it is labeled
**estimate** — do not read an estimate as a measured fact (feedback:
`dont_launder_estimates_as_data`).

## Contabo

Script: `scripts/contabo_restore.sh` (`bash scripts/contabo_restore.sh --dry-run` to preview
anywhere; a real run needs root on a fresh Debian/Ubuntu VPS). Run by: Contabo CTO.

| # | Step | HUMAN | Estimate |
|---|---|---|---|
| 1 | preflight: root, disk, packages (git/python3/docker), Tailscale install + `tailscale up` | **yes** — open the printed login URL, approve the machine | 5–10 min (incl. the click) |
| 2 | clone `PASAKON/MoonieX-HQ` + `Agents-{Core,Memory}`; print the two rsync commands for `Agents/Rules`/`Agents/Wikis` | **yes** — those two rsync commands run FROM THE MAC, not here | 2–5 min (+ whenever the Mac CTO runs the rsync) |
| 3 | Python venv (`Agents/Core/.venv`, + `/root/idm-venv` if its freeze file was captured), Node 22 tarball → `/opt/node-v22`, npm globals | no | 5–10 min |
| 4 | systemd: copy `mooniex-*.service`/`.timer`, `daemon-reload`, `enable` (never `start`) | **yes** — each unit needing an `EnvironmentFile` is named; restore that file from the secrets bundle (step 8) before starting it | 2–3 min |
| 5 | crontab: print the captured `crontab-root.txt`, install only after a yes | **yes** — review the printed crontab before answering the prompt | 1–2 min |
| 6 | Docker: `compose pull`/`build` for every file in `docker-compose-files.txt` (never `up`); print the `docker volume create` + `tar xf`/`psql` lines for `n8n_data` and `org-pgdata` | **yes** — those volume tars/dumps come from Drive via winbox's rclone or the Mac bridge; this script never fetches them | 5–20 min (image pulls) + however long the Drive pull of the two volumes takes |
| 7 | Claude Code: native install, claude-home symlinks (`claude_home_migrate.py` pattern) | **yes** — `claude` login, and re-trusting `Agents/Core` in Claude Code, are both interactive | 5 min install + login time |
| 8 | secrets: print the paths that need the secrets bundle (`/root/.ssh`, `/root/.acme.sh`, `/home/secretary/.secretary.env`, each unit's `EnvironmentFile`) and where the bundle lives | **yes** — fetched by hand from another machine's `Archive/` at 0600; never Drive, never automatic | however long the bundle transfer takes |
| 9 | verify: `machine_doctor.py --machine contabo check`, `hq.py doctor`, `systemctl list-unit-files 'mooniex-*'`; print PASS/FAIL + the drill-line template | no | 1–2 min |

**Total estimate ≈ 30–60 min of script/script-adjacent time, plus however long the human
steps and the two Docker-volume Drive pulls take** (not yet measured on a real drill — see
"Drill scoring").

## Mac

Script: `scripts/mac_restore.sh` (`bash scripts/mac_restore.sh --dry-run` — the only mode
this repo can verify, since there is no macOS on Contabo; refuses a real run when `uname -s`
is not `Darwin`). Run by: Mac CTO — hand-off is a file in the repo + a mailbox letter, not
chat (CEO 2026-09-24 decision, `docs/ops/machine-contract-plan-2026-09-24.md`).

| # | Step | HUMAN | Estimate |
|---|---|---|---|
| 1 | preflight: confirm Darwin, disk free, Homebrew, git | no | 2 min |
| 2 | clone `~/MoonieXHQ` + `Agents-{Core,Rules,Wikis,Memory}` — the Mac IS the source of truth for Rules/Wikis (unlike Contabo), so all four are cloned, not rsync'd | no | 3–5 min |
| 3 | `brew bundle --file` the captured `Brewfile` | no | 10–30 min (cask downloads vary) |
| 4 | LaunchAgents: copy captured `com.gob.*.plist`, `launchctl load` | **yes** — any plist with a `<redacted>` value must be hand-filled with the real secret before it is loaded | 5–10 min |
| 5 | Tailscale install + `tailscale up` | **yes** — open the login prompt, sign in, approve the machine | 3–5 min |
| 6 | Claude Code: native install, claude-home symlinks | **yes** — `claude` login and re-trusting `Agents/Core` are both interactive | 5 min + login time |
| 7 | secrets: print the paths needing the mac-secrets bundle (`~/.config/mooniex/**`, redacted LaunchAgent values) | **yes** — fetched by hand from Contabo's `Archive/` at 0600; never Drive, never automatic | however long the bundle transfer takes |
| 8 | verify: `machine_doctor.py --machine mac check`, `hq.py doctor`; print PASS/FAIL + the drill-line template | no | 1–2 min |

**Total estimate (not yet drilled for real) ≈ 30–60 min plus cask downloads and human-step
time.** The Mac's own upcoming wipe is drill #2 (ADR 0031) — the Mac CTO runs this script for
real and reports the four numbers back.

## winbox

No new script — winbox already has a working, measured bootstrap + rebuild pipeline; this
runbook only orders and times it:

1. **`windows/winbox-reinstall/README-th.md`** — the CEO-facing one-pager (Thai): Reset this
   PC → Cloud download → OOBE → create the local account (fell back to a Microsoft account,
   `passg`, on 2026-09-24 — the planned local `UsEr` account did not stick) → download
   `winbox-bootstrap.ps1` from Drive `BACKUP/Winbox Reinstall 2026-09-24/` and run it in an
   **elevated** Terminal. **HUMAN, entirely** — every step up to here is done by hand at the
   keyboard. Measured 2026-09-24: **~10 minutes** to remote access (Reset-this-PC time not
   counted — the machine reboots itself).
2. **`windows/winbox-reinstall/winbox-bootstrap.ps1`** (`-Check` to preview) — installs OpenSSH
   + the org's two public keys, opens the firewall, installs Tailscale, disables sleep, sets
   Bangkok time, sets auto-logon (asks the Windows password once — **HUMAN**), then runs
   `tailscale up` and waits for the CEO to approve the tailnet login in a browser — **HUMAN**.
   Prints `READY` + the tailscale IP when done; the CEO relays that to the CTO.
3. **`windows/winbox-reinstall/rebuild/rebuild_r1.ps1`** (run remotely over SSH by the Contabo
   CTO) — winget-installs the base tool list (git, Python 3.11, rclone, Node LTS, gh, ffmpeg,
   yt-dlp, Chrome, VS Code, BlueStacks, ...) + the Claude Code CLI. No HUMAN step.
4. **`windows/winbox-reinstall/rebuild/rebuild_r2.ps1`** — clones `MoonieX-CookierunBot`,
   restores its 77 templates from the pre-staged tar, rebuilds its `.venv` from the captured
   pip freeze (best-effort, one pin at a time), copies `pclease` tooling, and re-creates the
   core scheduled tasks (including `MachineContractDoctor`) from the captured XMLs with the
   account rewritten to `passg`. No HUMAN step in the script itself, but its inputs
   (`bot-templates.tgz`, `venv-freeze.txt`, task XMLs) must already be staged in
   `C:\mooniex\rebuild\` — CTO prep, not on the box.
5. **Cookie Run + BlueStacks + logins — all HUMAN, no deadline** (CEO 2026-09-24 decision):
   BlueStacks instance + Google login + Cookie Run install/login, LINE (Store) install, Chrome
   login, rclone re-consent (`rclone config reconnect gdrive:`). These are pending items on the
   real 2026-09-24 box, not yet cleared — see `state/re-os-drills.jsonl`.

Measured 2026-09-24 (real, unplanned reset — `state/re-os-drills.jsonl`, drill #1): **~10 min
to remote access, ~150 min (~2.5 h) to the org leg restored** (code, rules, skills, memory,
48 scheduled tasks, winget list, SSH keys, BlueStacks settings — all from git); **84 GB of
Cookie Run data was a known, logged loss** (no Drive copy existed at reset time) —
PASS-with-known-loss. Gaps found and still open: the native Claude CLI installer hangs on
`claude --version` in some shells; BlueStacks' default instance is the wrong Android version
(Nougat32 vs the bot's expected Tiramisu64); the Microsoft Store LINE install failed once
(`0x8A150014`); the account-name change (`UsEr` → `passg`) needed a compatibility junction;
the rclone token was not in the key backup; the Mac CTO's own `C:\mooniex\{agents,line,...}`
tools were not restored (tracked as an `UNCLASSIFIED` registry row pending the Mac CTO).

## Drill scoring

Append one JSON line per drill to `state/re-os-drills.jsonl` (already has the winbox
2026-09-24 entry as a worked example). Fields: `date`, `machine`, `kind` (`real` — an actual
wipe/new box — or `rehearsed` — a dry run / scratch VM), `scope` (what was covered — e.g. "org
leg only" if personal/game state is out of scope), `result` (`PASS` / `FAIL` /
`PASS-with-known-loss`), `minutes_to_remote_access`, `minutes_to_org_restore`,
`bytes_from_git_mb`, `bytes_from_drive_mb`, `irreplaceable_lost_gb`, `human_steps` (ordered
list of what a person did by hand), `gaps_found` (anything the drill exposed that the
registry/scripts did not account for), `by` (session id), `ref` (this runbook or the
machine's own report). Both restore scripts print this template, pre-filled with their own
`machine` value, at the end of their `verify` step.

**PASS** = every `IRREPLACEABLE` row for that machine is present or logged as a known loss
(never a silent gap), every `CONFIG`/`REBUILD` restore line worked as written, and
`machine_doctor.py check` exits 0. Cadence: one real drill per quarter, rotating
Mac → winbox → Contabo; Contabo's drill always uses a disposable VPS/VM, never the live box
(ADR 0031).
