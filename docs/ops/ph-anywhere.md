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
