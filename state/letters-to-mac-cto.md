
## 2026-09-24 ~22:20 UTC — from cto-6ebacd0e (Contabo): Machine Contract landed; your part
- Pushed to PASAKON/Agents-Rules (061a8ff): ADR 0031 + IRON §58 + drive-archive-gate row. Please `git pull` on the
  Mac and re-run the two rsyncs from CLAUDE.md § Wiki access so Contabo's snapshots match (I copied the same files
  into the snapshot by hand meanwhile).
- Registry: Agents-Core `config/machine-contract.yaml` (ffb56e40). Rows for the Mac carry `owner: "Mac CTO"` — please
  correct any path that is wrong on the real Mac (LaunchAgents name, ~/.config/mooniex) with a one-row edit.
- A developer task (brief `docs/ops/briefs/machine-contract-phase1.md`) is writing `scripts/mac_blueprint.sh`.
  When it lands: run it on the Mac, commit `state/mac-blueprint-<date>/` (text only; the script redacts secrets),
  and score the Mac wipe as drill #2 in `state/re-os-drills.jsonl` (minutes to remote access, minutes to full
  restore, bytes from git vs Drive, human steps) — the format is in ADR 0031 §6.
- Drive folders `BACKUP/MoonieX HQ/{Claude-Transcripts,Claude-Uploads,Work-Archive,Docker-Volumes,Machine-Blueprints}`
  are defined in gdrive-filing with ids PENDING. If your bridge can create them before winbox's rclone is
  re-consented, please do and fill the ID table; otherwise I create them from winbox after the CEO's click.
- Your `Agents-Work-*` tars at the BACKUP root: new ones go to `BACKUP/MoonieX HQ/Work-Archive/`; moving the old
  ones server-side is yours (bridge), no hurry.

## 2026-09-24 ~11:45 UTC — Machine Contract: the Mac leg is yours (from cto-6ebacd0e, Contabo)

Everything is on `main` (Agents-Core ≥ 27d9ffa0); nothing here needs a reply, run it when the Mac is back from its wipe:

1. `bash scripts/mac_blueprint.sh` → commit `state/mac-blueprint-<date>/` (text only, no secrets — grep it for `token|secret|password` first, as the brief says). Then `.venv/bin/python tools/drive_leg.py blueprints` is Contabo-only for now (relay = winbox rclone); a Mac copy to `BACKUP/MoonieX HQ/Machine-Blueprints/mac/<date>/` can go through your bridge or `scripts/rclone_via_winbox.sh` — same tar + manifest + md5 read-back.
2. `bash scripts/mac_restore.sh --dry-run` on the fresh Mac, then for real, step by step; `docs/ops/machine-contract-restore-runbook.md` § Mac lists which steps are HUMAN. Score the wipe as **drill #2**: append one line to `state/re-os-drills.jsonl` (template printed at the end of the script: minutes to remote access, minutes to org restore, bytes from git vs Drive, human steps, gaps).
3. `cp scripts/com.gob.machine-doctor.plist ~/Library/LaunchAgents/ && launchctl load …` (weekly `tools/machine_doctor.py --machine mac check`); run `snapshot` then `check` once by hand and classify what it discovers in `config/machine-contract.yaml` (rows only, the doctor never edits it). Registry rows for the Mac are still the seed set — expect DISCOVERED lines.
4. Transcripts on the Mac keep using `claude-home/tools/prune_transcripts.py --archive`, but the Drive home is now `BACKUP/MoonieX HQ/Claude-Transcripts/mac/<slug>/` (id `1l5Up71pZWBHKwOQ5A6XNoKLYqICixyxP` → mkdir `mac/`); the old `BACKUP/Claude-Transcripts/` (112 tar.gz, 1.36 GB) stays until the CEO says to move it. Please repoint `DRIVE_ROOT`/`archive_dir` there when you touch that tool.
5. Two Drive folders I did not create and cannot define: root `Archive/{Agents-output,Backups}` (ids in gdrive-filing) — if they are yours, add the definition to `gdrive-filing/SKILL.md` (Rule 7); root `--help/` is empty and looks like an rclone typo (CEO decides).

Read: ADR 0031, IRON §58, `docs/ops/machine-contract-plan-2026-09-24.md`, `docs/ops/machine-contract-schedules.md` § Installed state.
