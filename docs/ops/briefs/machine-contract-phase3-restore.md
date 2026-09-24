# Brief — Machine Contract, phase 3: restore verbs for Contabo and the Mac

Context: `docs/ops/machine-contract-plan-2026-09-24.md` (approved plan, phase 3), ADR 0031 and
IRON §58 (copies under /opt/MoonieXHQ/Agents/Rules/), registry `config/machine-contract.yaml`,
capture verbs `scripts/contabo_blueprint.sh` / `scripts/mac_blueprint.sh` (their output layout is
the input of restore), precedents `scripts/vps-backup/README.md` § "Restore cheatsheet",
`windows/winbox-reinstall/winbox-bootstrap.ps1` + `rebuild/rebuild_r1.ps1` + `rebuild_r2.ps1`
(the winbox restore that actually ran on 2026-09-24), `scripts/claude_home_migrate.py`
(claude-home symlink pattern). Everything you write is English (IRON §56). You may run
read-only checks on this Contabo box; you must NOT run a restore here, touch Drive, secrets,
systemd, docker, crontab, or other machines.

## Deliverables

1. `scripts/contabo_restore.sh` — idempotent, ordered, registry-driven restore for a FRESH Debian/
   Ubuntu VPS. Steps, each printed as `[n/N] <name>` with `--dry-run` printing the commands only:
   (1) preflight: root, disk free, `git`/`python3`/`docker` present or apt-install them, Tailscale
   installed + `tailscale up` (prints the login URL — HUMAN step, wait for it); (2) clone
   `PASAKON/MoonieX-HQ` to `/opt/MoonieXHQ` and the Agents-* sub-repos per `hq.yaml` rows
   (`Agents/Core`, `Agents/Memory`; Rules/Wikis are rsync snapshots from the Mac — print the two
   rsync commands from CLAUDE.md § Wiki access instead of cloning); (3) Python venv for Agents/Core
   from `requirements.txt` (+ `/root/idm-venv` only if `state/contabo-blueprint-<date>/pip-freeze-idm-venv.txt`
   exists), Node 22 tarball to `/opt/node-v22`, npm globals from `npm-global.txt`; (4) systemd units
   from `state/contabo-blueprint-<date>/systemd-mooniex-units/` → `/etc/systemd/system/`, daemon-reload,
   enable (do NOT start; print which need their EnvironmentFile restored from the secrets bundle
   first); (5) crontab from `crontab-root.txt` (print, ask before installing); (6) Docker: compose
   files listed in `docker-compose-files.txt` → `docker compose pull/build` (no `up`), volumes:
   print the `docker volume create` + `tar xf` / `psql` restore lines for `n8n_data` and
   `org-pgdata` from Drive `BACKUP/MoonieX HQ/Docker-Volumes/contabo/...` (HUMAN step: the tars come
   from Drive via winbox's rclone or the Mac bridge); (7) Claude Code: `curl -fsSL https://claude.ai/install.sh | bash`
   (native), `claude` login = HUMAN step, then `scripts/claude_home_migrate.py`-style symlinks for
   claude-home + Agents/Memory, and re-trust of `/opt/MoonieXHQ/Agents/Core` = HUMAN step; (8)
   secrets: print the list of paths from the registry rows marked "secrets bundle" (`/root/.ssh`,
   `/root/.acme.sh`, `/home/secretary/.secretary.env`, unit EnvironmentFiles) and where the bundle
   lives (`<other machine>/opt/MoonieXHQ/Archive/contabo-secrets-<date>/`, 0600) — never fetch them
   automatically; (9) verify: `python3 tools/machine_doctor.py --machine contabo check`, `hq.py doctor`,
   `systemctl list-unit-files 'mooniex-*'`; print a PASS/FAIL summary line and the four drill numbers
   template for `state/re-os-drills.jsonl` (minutes to remote access, minutes to restore, bytes from
   git vs Drive, human steps) for the operator to fill.
2. `scripts/mac_restore.sh` — the same shape for macOS (Homebrew from `state/mac-blueprint-<date>/Brewfile`,
   LaunchAgents plists from the capture with `<redacted>` values flagged as HUMAN steps, `~/MoonieXHQ`
   clone per `hq.yaml`, claude-home symlinks, Tailscale, `claude` login). `--dry-run` only here
   (no macOS on this box); refuse a real run on non-Darwin.
3. `docs/ops/machine-contract-restore-runbook.md` — one page per machine (Contabo, Mac, winbox —
   winbox points at `windows/winbox-reinstall/README-th.md` and the rebuild scripts): the ordered
   steps, which are HUMAN, expected minutes (winbox measured 2026-09-24: ~10 min to remote access,
   ~150 min org restore), and the drill scoring line format.
4. `tests/test_restore_scripts.py` — `bash -n` both scripts, `--dry-run` runs exit 0 and print every
   step header in order, no step is missing its HUMAN marker where the brief says HUMAN.

## Verification to paste into your report
- `bash -n scripts/contabo_restore.sh && bash -n scripts/mac_restore.sh`
- `bash scripts/contabo_restore.sh --dry-run` (full output) and `bash scripts/mac_restore.sh --dry-run`
- `.venv/bin/python -m pytest tests/test_restore_scripts.py -q`
- `grep -nE 'HUMAN' scripts/contabo_restore.sh | wc -l` (must be ≥ 5)

## Not in scope
Running any restore; Drive/rclone; secrets; winbox changes; editing the registry (propose rows in
the report). No file over 1 MiB.
