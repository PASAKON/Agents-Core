# Brief — Machine Contract, phase 1 code (capture verbs, doctor, ledger field)

Context: `docs/ops/machine-contract-plan-2026-09-24.md` (approved plan), ADR 0031 (Agents-Rules
`decisions/0031-machine-contract-every-machine-rebuildable.md`), IRON §58, registry
`config/machine-contract.yaml`. You build the code; you do NOT touch Drive, secrets, or other
machines. Everything you write is English (IRON §56). Run on Contabo (this box); the Mac script is
written here and run later by the Mac CTO.

## Deliverables (all in this repo)

1. `scripts/contabo_blueprint.sh` — capture verb for this VPS. Text only, NO secrets (never read
   `.env*`, `.credentials.json`, `~/.ssh/id_*` private keys, `rclone.conf`, `/home/secretary/.secretary.env`).
   Output dir `state/contabo-blueprint-<YYYYMMDD>/` with: `apt-packages.txt` (`apt-mark showmanual`),
   `pip-freeze-<venv>.txt` for `Agents/Core/.venv` and `/root/idm-venv`, `npm-global.txt`,
   `node-version.txt`, `docker-images.txt`, `docker-volumes.txt` (names + sizes only), `docker-compose-files.txt`
   (paths of every compose file under /opt and /docker), `systemd-mooniex-units/` (copies of
   `/etc/systemd/system/mooniex-*.service`), `crontab-root.txt`, `claude-tree.txt`
   (`find $CLAUDE_CONFIG_DIR -maxdepth 2 -printf '%y %s %p\n'` — no file contents), `claude-json-keys.txt`
   (top-level keys of `~/.claude.json` + the `projects{}` map with only `allowedTools` and
   `hasTrustDialogAccepted` per project), `ssh-public-keys/` (`*.pub` + `~/.ssh/config` with
   IdentityFile lines kept), `machine.json` (hostname, OS, kernel, python/node/docker versions, tailscale
   IP, disk free, users). Idempotent; exit 0; prints the output dir. Model it 1:1 on
   `windows/winbox-reinstall/rebuild/blueprint.ps1` (numbered steps, secrets excluded by design).
2. `scripts/mac_blueprint.sh` — same for macOS: `brew bundle dump --file=Brewfile`, `launchctl list |
   grep -v com.apple`, copies of `~/Library/LaunchAgents/com.gob.*.plist` (with any secret-looking
   values replaced by `<redacted>`), `defaults read` of com.apple.dock/finder autohide + screen
   settings only, the same claude-tree / claude-json-keys / ssh-public-keys / machine.json. Must not be
   run here (no macOS); include a `--dry-run` that prints the commands so the Mac CTO can review.
3. `tools/machine_doctor.py` — registry vs disk. Verbs: `snapshot` (writes
   `state/machine-snapshot-<machine>.json`: every path in the registry for this machine expanded
   from placeholders, exists?, size), `check` (exit 1 when: an IRREPLACEABLE path exists but has no
   `restore` line; any directory over `unknown_growth.min_mb` under `$HOME`, `$CLAUDE_CONFIG_DIR`,
   `/opt`, `/var/lib/docker/volumes` matches no registry row → print it as `DISCOVERED` and append a
   `discovered: true, class: UNCLASSIFIED` row proposal to `state/machine-discovered-<machine>.yaml`
   (never edit the registry itself); a `discovered` row older than `classify_within_days` → print
   `CANDIDATE`), `report` (one line per class with GB). Machine detection: `--machine` flag or
   hostname map in the registry `machines:` block. Placeholders: `$CLAUDE_CONFIG_DIR` (env, default
   `~/.claude`), `$HOME`, `<hq>` (from `machines.<m>.hq`), Windows `%VAR%` ignored on non-Windows.
   Reuse the walk-and-fail idiom of `/opt/MoonieXHQ/scripts/hq.py` `doctor`. Tests in
   `tests/test_machine_doctor.py` with a temp registry + temp dirs (a 600 MB sparse file counts as
   discovered; a listed path does not). Also a `--on-version-change` mode: read
   `$CLAUDE_CONFIG_DIR/.last-update-result.json`, and if the version differs from
   `state/machine-snapshot-<machine>.json`'s recorded one, run `check` and print `CLAUDE_VERSION_CHANGED`.
4. `tools/workdir.py`: at `create`, record the folder's byte size as `added_bytes_start`; at `close`,
   write `added_bytes` (bytes the task added since create) next to the existing `bytes` field in the
   `Work/_ledger.jsonl` line, so "+X added, −X archived" is one row. Keep every existing test green;
   add one test for the new field.
5. `docs/ops/machine-contract-schedules.md` — the schedule table (what runs where, how often):
   Contabo cron line for `machine_doctor.py check` weekly (Mon 04:00 UTC) — write the line, do not
   install it (the CTO installs crontab); winbox `MachineContractDoctor` task XML in
   `windows/winbox-reinstall/rebuild/` modeled on `state/winbox-blueprint-20260924/tasks/CookieRun-DiskSense.xml`
   with paths for account `passg`; Mac launchd plist `com.gob.machine-doctor.plist` next to the Mac script.

## Verification you must run and paste into REPORT.md
- `bash scripts/contabo_blueprint.sh` → dir listing + `grep -riE 'token|secret|password|BEGIN .*PRIVATE' state/contabo-blueprint-*/` returns nothing.
- `python3 tools/machine_doctor.py --machine contabo snapshot && python3 tools/machine_doctor.py --machine contabo check; echo exit=$?` — expect exit 1 today with `/root/restore` and any other discovered paths listed.
- `python3 -m pytest tests/test_machine_doctor.py tests/test_workdir*.py -q` all green.
- `bash scripts/mac_blueprint.sh --dry-run` prints without error.

## Not in scope
Drive uploads, rclone, secrets, other machines, editing `config/machine-contract.yaml` (propose rows
in REPORT.md instead), IRON/ADR text. Keep the worktree small (no data files > 1 MiB; media guard).
