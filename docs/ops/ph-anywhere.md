# A Project Head on any host (org restructure M13)

CEO 2026-10-14 13:00 TH, via the COO: "ทำให้ CXO spawn PH บน Mac และ Windows ได้เลย".
Every C-level must be able to start a Project Head on the Mac and on winbox, not only
on Contabo. This pulls plan Phase 4 forward. M13a (the Mac, local) is here; the
cross-host card (M13b) and winbox (M13c) follow in their own PRs.

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
