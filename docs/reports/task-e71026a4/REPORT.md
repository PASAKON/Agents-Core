# task-e71026a4 — Drive SHARE broker on Contabo with the credential in Infisical, no `.env`

Brief: description of task-3851f0fe (CEO order 27 Oct 08:35 "ใช้งาน Claude โควต้าได้เต็มที่ ทำ Parreale ได้").
Branch `agent/developer-task-e71026a4` on top of `origin/main` a1c304df. Nothing was installed, started or
restarted; no `.env`, `/etc/infisical`, `/home/*` or `/proc/*/environ` was read. The PH installs on a CEO card.

## Summary

`runners/drive_share_broker.py` now takes the Drive OAuth triple from its process environment (no file), the
new unit `deploy/share-broker/mooniex-share-broker.service` gets it from `infisical_setup.py run MoonieX-SomPong
prod --as contabo --path /drive-share` and drops to `shareup` with `setpriv`, and
`scripts/install-share-broker.sh install` takes no credential file and writes none. Touched tests: 92 passed,
1 skipped (the non-root guard, because the session is root), 0 failed.

## Files Changed

- `runners/drive_share_broker.py` — `DRIVE_SHARE_BROKER_ENV` optional. Unset + all three `GOOGLE_OAUTH_*` in the
  environment → `apply_oauth_from_environ()` snapshots them, removes them from `os.environ` and swaps
  `ilag_sync._load_oauth` for a loader returning the snapshot (no file read); `load_secret_values()` still
  feeds redaction. Neither source complete → `ConfigError` naming the missing KEYS (absent or blank), never
  values. File path kept and wins when set. `main()` calls `apply_oauth_source(cfg)`.
- `deploy/share-broker/mooniex-share-broker.service` (new) — unit template (checkout path filled by the
  installer, like deploy/coo-gate); gmail-broker hardening; `+` `ExecStartPre install -d` for the socket dir
  (shareup 0750), no `User=`, no `RuntimeDirectory=`; `ALLOWED_UIDS=0`, staging root, socket path, `ORG_LOG_DIR`;
  `RestartPreventExitStatus=2` (empty `/drive-share` folder = exit 2 = not retried).
- `scripts/install-share-broker.sh` — rewritten. `install [--dry-run]` | `uninstall [--dry-run]` | `status`.
  Creates `shareup` (no home/shell), staging `/var/lib/sompong-share/staging` root:shareup 2770, log dir
  `/var/log/mooniex-share-broker`; renders + installs the unit; daemon-reload, enable, reset-failed, restart;
  prints status. Env-copy path, `sompong`→`shareup` group add and credential argument removed. Refuses an
  untrusted checkout (ancestors + `tools runners lib scripts/gdrive-bridge deploy/share-broker` root-owned, not
  group/world-writable) and names the first offender. Header carries the one-time secret step.
- `scripts/test_drive_share_broker.py` — +13 tests (env-only config, legacy file path, both sources, missing
  keys named / values never, blank = missing, loader reads no file, env secrets feed redaction, `main()` exit 1
  and a full `main(["--once"])` run). `test_load_config_requires_env_var` became `…requires_a_credential_source`.
- `tests/test_install_share_broker.py` (new, 17 tests) — `bash -n`; grep-style "no `.env`/credential code path"
  over script and unit; redirection-target allowlist; old `install <file>` call refused; dry-run render; unit
  pattern; relocated + hostile checkout paths (`a&b`, `a|b`, space, parens, `#`, Thai); uninstall touches only
  the unit; status; root guard; trust-check fixtures (root only).
- `tests/test_compat_repoint_scripts.py` — `test_share_broker_example_target` pinned the retired
  `…/ClaudeFlow/.env` example in the script header; now `test_share_broker_names_no_env_file_example`.
- `docs/design/sompong-share.md` — §2/§4/§5/§7 and status line follow the new model (it told people to run
  `install <env-file>`).
- `docs/reports/task-e71026a4/REPORT.md` — this file.

## Commits

- f7fdacda — share-broker: run on Contabo with the Drive credential from Infisical, no .env
- 127df44a — share-broker: trust check names the offender; design doc + compat test follow the new model
- (third commit: this report)

## Tests

- ran: `.venv/bin/python -m pytest tests/test_install_share_broker.py tests/test_compat_repoint_scripts.py scripts/test_drive_share_broker.py`
- passed: 92
- failed: 0
- skipped: 1 (`test_install_without_root_and_without_dry_run_is_refused` — root session; checked by hand as `nobody`: exit 1 "needs root", `--dry-run` exit 0)

Also run: `bash -n scripts/install-share-broker.sh` (ok); `systemd-analyze verify` on the rendered unit (exit 0,
no output); real entry point `python3 -m runners.drive_share_broker --once` in env-only mode with FAKE
placeholder values, uid 0 allowed, short socket: starts, serves, refuses a missing staged file, exit 0, no
placeholder value in output or log; same with only one key set: `config error: … lacks:
GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN`, exit 1.

Fail-without-the-change proof (old files from a1c304df, new tests): old broker → 13 new/changed tests fail;
old installer → 8 fail; trust check with the writable check removed → 2 fail, with the ownership check
removed → 2 fail. Files restored after each.

## Issues / Blockers

- None blocking. Four things the PH must know are under Notes.

## Notes for Reviewer

**Reach list (before the first edit).** `load_config` / `BrokerConfig.env_path` (now `Path | None`): only
`main()` and the tests use them. `apply_oauth_env_override` kept as is. `ilag_sync` untouched (shared with
`drive_upload_broker`, `drive_photo_broker`, `sompong_archive_filer`, which do not use the new loader). The
retired installer's callers: `tests/test_compat_repoint_scripts.py` (updated); docs `sompong-share.md`
(updated), `sompong-archive.md` and `scripts/install-archive-uploader.sh` mention it only in comments about
a sibling (left). Socket path, staging path, folder id and service name are unchanged, so
`install-archive-uploader.sh`'s collision checks still hold.

**PH card steps, in order** (I ran none of them):
1. The Contabo main checkout (`/opt/MoonieXHQ/Agents/Core`, read-only `find`) fails the installer's trust
   check: `scripts/gdrive-bridge`, `Code.gs` and `gdrive_move.py` are owned by uid 501 (the Mac sync, same
   cause as docs/design/gmail-broker.md). `chown root:root` those three first; the installer names the first
   offender if anything else shows up. `deploy/share-broker/` does not exist there until this branch merges.
2. Secret step (header of the script has the exact commands): `infisical_setup.py mkdir MoonieX-SomPong prod
   drive-share --as <writer>`, then `import-env … --path /drive-share --only GOOGLE_OAUTH_CLIENT_ID,…_CLIENT_SECRET,…_REFRESH_TOKEN
   --comment … --meta provider_name= console_url= scope= expires= owner=` (new secrets need the five meta keys),
   then `last4`. `<writer>` must be an identity with write on MoonieX-SomPong: `contabo` is Viewer on every
   project (docs/design/gmail-broker.md, measured 23 Oct; I did not re-measure), `keyfetch-writer`'s manifest lists only Agents-Core, MoonieX-Bedrock, MoonieX-ClaudeFlow. All three
   names pass the §4b naming lint, so no `--legacy`. The source env file for `import-env` is the existing one
   (e.g. ClaudeFlow's); `--only` keeps every other line out.
3. `install --dry-run` to review, then `install`, then `status`. Before step 2 the unit exits 2 and stays down
   by design; `systemctl restart mooniex-share-broker` after the import.

**Caller uid differs from the wiki.** Brief: the inbox calls as root → `ALLOWED_UIDS=0`, staged files must be
owned by root (the broker checks owner == connecting uid), mode 0640 in a setgid root:shareup dir. Wiki
`projects/sompong-ea.md` §D (contract of record, I cannot write it) says uid `sompong`. If the staging process
is really `sompong` (uid 994 on Contabo): change the one `Environment=DRIVE_SHARE_BROKER_ALLOWED_UIDS=` line,
add `sompong` to `shareup`, stage files owned by `sompong`. The C-level should reconcile the wiki line.

**Same `.env` pattern elsewhere.** `scripts/install-drive-broker.sh`, `install-photo-broker.sh` and
`install-archive-uploader.sh` still show the credential env-file pattern (14 lines match `EnvironmentFile=`/`ENV_FILE=`/`.env"`;
I read headers and greps, not the whole scripts). Out of scope; the CEO rule covers them too.

**Judgement calls.** `enable` + `restart` instead of `enable --now` so a second install re-reads a changed unit
(coo-gate does the same). `--dry-run` added (gmail installer has it) so the installer is testable and the
rendered unit reviewable without root. `/usr/bin/python3` for the broker, not the venv (stdlib only). Folder
id, size cap and timeouts are not set in the unit; the code defaults are the CEO-approved values. If an older
install had left `/home/shareup/.drive-share.env`, it would still be there: `shareup` does not exist on this
box, so none was created. Hook note: the Drive-skill gate blocked my first read of `scripts/gdrive-bridge/…`.

**Rule conflict (conventions vs task).** Hard rule 2 says never `git push`; the task says "commit on your
branch and push it". I followed the task text for this one branch only (origin/main == my base, two commits
ahead, a60f1744 not an ancestor, gitleaks clean), no force, no main.

## Not checked / risk

- The unit has never been started: only `systemd-analyze verify` and a plain-python run of the entry point.
  Untested on Contabo: `setpriv --bounding-set=-all … --no-new-privs` inside this unit (copied from the Gmail
  unit that was measured), the `contabo` identity reading `/drive-share` (folder does not exist yet), the
  `ReadWritePaths` `-` prefix and the `shareup` read of the checkout. A start failure shows in
  `journalctl -u mooniex-share-broker` and does not touch any other unit.
- No real Google call: refresh, upload, permission and re-read are unchanged code, but the new loader is only
  exercised through fakes, so a bad value in Infisical would show up as the first share failing.
- Lint: pyflakes is not installed; `py_compile` and the test imports are the only static check.

## Skill learning

- COSTLY [no owner] : `hook-gdrive-skill-gate.py` blocks a Bash call whose text contains `gdrive-bridge` even when it only reads or `wc -l`s `scripts/gdrive-bridge/ilag_sync.py` for a code task; cost one blocked call plus a full read of the ~400-line Drive filing skill · evidence: task-e71026a4, first Bash call of the session · prevented by: matching rclone / bridge scripts / Drive MCP, not any path with that substring.
- MISSING [no owner] : Contabo checkout owned by uid 501 makes every root-run installer with a trust check refuse; only docs/design/gmail-broker.md mentions the chown, and the share broker hit the same wall (n=2 with task-c0d756ff) · evidence: `find` on /opt/MoonieXHQ/Agents/Core/scripts/gdrive-bridge, 3 items uid 501.
- MISSING [DEV conventions §Hard Rules 2] : no wording for a task that explicitly orders a branch push; I followed the task text and said so · evidence: task-e71026a4 description vs rule 2.
