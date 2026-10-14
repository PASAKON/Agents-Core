# A Project Head on any host (org restructure M13)

CEO 2026-10-14 13:00 TH, via the COO: "ทำให้ CXO spawn PH บน Mac และ Windows ได้เลย".
Every C-level must be able to start a Project Head on the Mac and on winbox, not only
on Contabo. This pulls plan Phase 4 forward.

| part | what | state |
|---|---|---|
| M13a | `spawn-ph.sh` on the Mac, by a C-level on the Mac | code + tests in this PR; install below |
| M13b | Contabo C-level → Mac, one Run Inbox card per spawn | code + tests in this PR; needs Run Inbox P2 (task-5eb22787) |
| M13c | winbox: org_dispatch key (#238), Windows PH launcher | key: blocked on the CEO; launcher next |

## M13a: on the Mac

What was Linux-only and what changed:

- **Launcher liveness** (`tools/clevel_gate._pid_is_launcher`): with no `/proc` it
  used to count any alive pid as the launcher, so a pid the OS reused after a
  Project Head ended kept its project held. It now reads argv from
  `ps -ww -o command= -p <pid>`; with no ps either (Windows) an alive pid counts.
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

**Live test** (Mac PH LuminaSkies #f39cb080, on its own host, read-only):

```
cd /Users/gob/MoonieXHQ/Agents/Core && git pull --ff-only && .venv/bin/python -m pytest -q -p no:warnings tests/test_ph_on_mac.py tests/test_org_p2_launchers.py
ORG_PH_ROLES=1 CXO_ROLE=cto CTO_SESSION_ID=c0ffee01 bash scripts/spawn-ph.sh --project MacProbe --brief x --dry-run
```

Expected: the tests pass; the dry run prints one JSON line with
`"owner": "cto-c0ffee01"` and writes nothing. A real spawn needs a real Mac C-level.

## M13b: from Contabo to the Mac

There is no ssh to the Mac by design (sshd off). A C-level on Contabo raises one Run
Inbox card for host `mac`; the CEO's tap is the authority, one tap per spawn.

```
bash scripts/hub/org-python.sh -m tools.spawn_ph card --host mac --project <Name> --brief-file <path>          # prints the card
bash scripts/hub/org-python.sh -m tools.spawn_ph card --host mac --project <Name> --brief-file <path> --send   # raises it
```

The card it raises (`tools/ask_run.py create`, kind `script`, pinned):

```
host     mac
script   Agents-Core@<origin/main sha>:scripts/spawn-ph.sh
args     --project <Name> --from-card <16-hex nonce> --brief <text>
risk     amber · timeout 120 s
```

On the Mac the executor runs `spawn-ph.sh --from-card <nonce>`. That process has no
C-level identity, so `tools/spawn_ph.card_owner` reads the hub: exactly one card that
is `running`, on this host (`lib.config.self_host`), kind `script`, repo
`Agents-Core`, path `scripts/spawn-ph.sh`, whose args carry that nonce and that
project. Its requester must be a C-level (`<role>-<sid>`, role matching); that
session becomes the owner. Anything else is refused, and so is a host with no Run
Inbox token. No flag ever names the owner.

Needs from Run Inbox P2 (task-5eb22787): the Mac executor, a hub token readable by
the user it runs as (`~/.config/mooniex/run-inbox.token`), a card listed as
`running` while its script runs, and `script.args` in `GET /api/run/asks`. The Mac
host flag from M13a must be on.

## M13c: winbox

### (2) org_dispatch key (#238): blocked, the CEO's call

Read-only facts (2026-10-14): passg is in winbox's Administrators group, so sshd reads
`C:\ProgramData\ssh\administrators_authorized_keys` (`Match Group administrators`);
the venv python, `tools\node_dispatch.py` and `tools\infisical_setup.py` exist under
`C:\Users\passg\mooniex\repo\MoonieX-Agents`; no org_dispatch line is there yet; the
file's ACL is SYSTEM + Administrators only; DefaultShell is unset (cmd), which the W3.4
line in `docs/ops/node-dispatch.md` is written for. Contabo's tailnet IPv4 is
100.118.171.23.

Writing an installer for that line into this repo was refused by the auto-mode
classifier ([Unauthorized Persistence], PH #7cf528f0, 2026-10-14), as an earlier
append was (2026-10-10). Granting Contabo standing access to winbox is the CEO's
decision; nothing here works around it.
