# A Project Head on any host (org restructure M13)

CEO 2026-10-14 13:00 TH, via the COO: "ทำให้ CXO spawn PH บน Mac และ Windows ได้เลย".
Every C-level must be able to start a Project Head on the Mac and on winbox, not only
on Contabo. This pulls plan Phase 4 forward.

| part | what | PR |
|---|---|---|
| M13a | `spawn-ph.sh` on the Mac, by a C-level on the Mac | #287 |
| M13b | Contabo C-level → Mac, one Run Inbox card per spawn; needs Run Inbox P2 (task-5eb22787) | #290 |
| M13c | winbox: org_dispatch key (#238, the CEO's call), Windows PH launcher | key blocked; launcher in the M13c PR |

## M13a: on the Mac

What was Linux-only and what changed:

- **Launcher liveness** (`tools/clevel_gate._pid_is_launcher`): with no `/proc` it
  counted any alive pid as the launcher, so a pid the OS reused after a Project Head
  ended kept its project held. It now reads argv from `ps -ww -o command= -p <pid>`.
  When ps cannot say (no ps, a non-zero exit, no output, or the `(name)` a non-root
  macOS ps prints for another user's process) an alive pid still counts: fail closed.
- Everything else already ran on Darwin and is now pinned by `tests/test_ph_on_mac.py`:
  the host flag file, `resource_gate` with no `/proc/meminfo` (RAM unknown → passes),
  `tmux_bin()` (finds `/opt/homebrew/bin/tmux`), the systemd scope (root +
  `systemd-run` only, so skipped), `flock` (skipped when missing), bash 3.2 syntax.
- `cxo-claude.sh --role project_head --dry-run` was run under real bash 3.2.57 with
  `uname -s` = Darwin: exit 0, `display=Project Head (CTO)`, `--chrome`.

**Install on the Mac** (the CEO, at the Mac; the Mac has no Run Inbox executor yet):

```
cd /Users/gob/MoonieXHQ/Agents/Core && git pull --ff-only && sudo mkdir -p /etc/org-flags && sudo touch /etc/org-flags/ORG_PH_ROLES
```

Then any Mac C-level session (started by `cto-claude.sh` / `cxo-claude.sh`) runs
`bash scripts/spawn-ph.sh --project <Name> --brief-file <path>`. Roll back:
`sudo rm -f /etc/org-flags/ORG_PH_ROLES`.

The marker `state/locks/project_head-<sid>.project` is what makes a session a PH to the name rules
(`tools/rename_service.py`) and to `live-sessions` (a C-level box with a marker is published as
`project_head`, so other hosts judge it by the PH name). Its value must match `[A-Za-z0-9_]{1,40}`:
`LastBell + Scriptable` made `build_name` return None and was not read as a PH; use `LastBell_Scriptable`.

**Live test** (a Mac session, on its own host, read-only):

```
cd /Users/gob/MoonieXHQ/Agents/Core && git pull --ff-only && .venv/bin/python -m pytest -q -p no:warnings tests/test_ph_on_mac.py tests/test_org_p2_launchers.py
ORG_PH_ROLES=1 CXO_ROLE=cto CTO_SESSION_ID=c0ffee01 bash scripts/spawn-ph.sh --project MacProbe --brief x --dry-run
```

Expected: the tests pass; the dry run prints one JSON line with
`"owner": "cto-c0ffee01"` and writes nothing. A real spawn needs a real Mac C-level.

## M13b: a Contabo C-level starts a PH on the Mac (one Run card)

There is no ssh to the Mac by design, so the C-level raises a Run Inbox card for host `mac` and the
CEO taps it. One tap per spawn.

```
bash scripts/hub/org-python.sh -m tools.spawn_ph card --host mac --project <Name> --brief "<one line>" [--sha <40-hex>] [--send]
```

Without `--send` it prints the `tools/ask_run.py create` it would run. The card runs the pinned
`Agents-Core@<sha>:scripts/spawn-ph.sh -- --project <Name> --from-card <nonce> --sha <sha> [--brief <one line>]`.

What makes the tap the only authority (§2b review of #280):

- **Pinned code only.** The executor runs a copy of the pinned script from a temp dir. The script
  ignores its own location and uses the host's fixed clone (`/Users/gob/MoonieXHQ/Agents/Core`). It
  refuses unless that clone's HEAD is the card's sha, no tracked file is changed, and no untracked
  `.py` sits where Python would import it (top level, `lib/`, `tools/`). Python then runs with `-I`
  and an empty `pycache_prefix`. Left in trust: the clone's `.venv`, the same trust as every launcher
  on that host. **Pull the Mac to the card's sha first**; the default sha is `origin/main`.
- **The owner is the card's requester.** It is taken from the ONE running card for this host whose
  script is that sha and path, whose args equal this run's argv exactly, and which a C-level raised:
  `created_via` is `clevel` and the requester's role is the lane. No flag names the owner.
  Raising the card runs the same C-level check as a local spawn (`_caller`).
- **Single use.** The nonce gets an O_EXCL marker under the claim lock, so a second run of the same
  card is refused.
- **Brief.** One line of at most 300 characters, because the hub caps script args at 500. The owner
  sends the full brief once the PH is up.

**Needs first:** task-5eb22787 (Run Inbox P2). That means a Mac executor, a hub token the executor's
user can read, the card shown as `running` while it runs, and `script.args`, `script.sha` and
`created_via` in `GET /api/run/asks`. Until then every card run is refused, so it fails closed.

Not done here: an argv that only looks like a launcher (`exec -a`) can still make the gate count a
project as held. That is denial only and mostly pre-existing (review finding 5); a follow-up checks
the script's realpath and the lock owner's uid.

## M13c: winbox

### (2) org_dispatch key (#238): blocked, the CEO's call

Read-only facts (2026-10-14): the winbox venv python, `tools\node_dispatch.py` and
`tools\infisical_setup.py` exist in the winbox checkout, and no org_dispatch key line is
installed yet; the W3.4 line in `docs/ops/node-dispatch.md` is written for winbox's
default ssh shell.

Writing an installer for that line into this repo was refused by the auto-mode
classifier ([Unauthorized Persistence], PH #7cf528f0, 2026-10-14), as an earlier
append was (2026-10-10). Granting Contabo standing access to winbox is the CEO's
decision; nothing here works around it.

### (3) The Windows Project Head launcher

- `tools/spawn_ph.py` on Windows opens a Windows Terminal tab:
  `wt.exe -w 0|new nt --title "Project Head (<LANE>) #<id> <Project>" -d <repo> powershell -NoProfile -ExecutionPolicy Bypass -File <repo>\windows\cxo-claude.ps1 -Role project_head -Lane <lane> -Project <Name> -Session <id>`.
  A wt tab takes the Terminal's environment, so nothing rides in it: the launcher reads
  the owner record spawn_ph wrote and rebuilds the first prompt (`spawn_ph.first_prompt`).
- Refused from Windows session 0 (an ssh shell or a service: its windows never reach the
  desktop) and while the CEO's PC hold is on (`windows/pc_lease.py ceo-on`). No scheduled
  task, no standing persistence: the spawner must already be in the CEO's logon session,
  either a winbox C-level he started, or the relay-mode Console that runs a winbox Run card
  (Run Inbox P2). PCLease: opening the tab is not driving the screen; a Project Head that
  needs the screen takes the lease first (`pc_lease.py take`), like any other agent.
- `windows/cxo-claude.ps1 -Role project_head`: same checks as `scripts/cxo-claude.sh`
  (host flag `%ProgramData%\org-flags\ORG_PH_ROLES`, lane, project, owner record, role doc,
  refuse from inside a PH). It now starts claude through `windows\native-args.ps1`
  `Invoke-NativeExe` (M12) for every role: `& claude @args` split the role prompt.
- `windows/spawn-ph.ps1` is the PowerShell twin of `spawn-ph.sh`; a winbox card runs
  `Agents-Core@<sha>:windows/spawn-ph.ps1` (`python -m tools.spawn_ph card --host winbox …`).
- Live on winbox (PS 5.1.26100, 2026-10-14, temp copy with the real venv): flag off → exit 2
  "off on this host"; no or wrong owner record → exit 2; record OK → passes the checks and
  `first_prompt` import, stops at the missing role doc in the copy (exit 2); launched from
  inside a PH → exit 2.

**Install on winbox** (Contabo Run card, host contabo; creates one empty file):

```
ssh -o BatchMode=yes winbox "powershell -NoProfile -Command \$null = New-Item -ItemType Directory -Force -Path C:\ProgramData\org-flags; \$null = New-Item -ItemType File -Force -Path C:\ProgramData\org-flags\ORG_PH_ROLES; Test-Path -Path C:\ProgramData\org-flags\ORG_PH_ROLES"
```

Expected output `True`. No `|` or `>`: the remote shell is cmd, which would split on them.
Read-only twin run 2026-10-14 (same quoting, `Test-Path` only): `False` `False` (neither exists yet). Roll back: delete that file. The winbox checkout must be on a
commit with M12 + M13c (`git -C C:\Users\passg\mooniex\repo\MoonieX-Agents pull --ff-only`).

**First live spawn** (CTO, read-only brief): from a winbox C-level, or a winbox Run card
once P2 lands, `windows\spawn-ph.ps1 --project WinboxProbe --brief "Read README.md and write a 3-line summary to your reply. Change no file."`.
Check: a new Windows Terminal tab titled `Project Head (CTO) #<id> WinboxProbe` shows the
claude TUI; the PH reports to its owner; `state\locks\project_head-<id>.*` is gone after it exits.
