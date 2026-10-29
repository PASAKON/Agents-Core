# REPORT task-34f846d0

Implemented the M2 installer, single P2 card and weekly LinePoster backup on feature branch `agent/codex-task-34f846d0`. WRITE ONLY: no live installation, service start, sparse deployment change, upload or production deletion was performed. The card was executed only with `--dry-run`.

## Iteration 2 review fixes

Started at `origin/main` / HEAD `41ff5cd8` (#544). The first command attempted `git rebase origin/main`; Git reported an unwritable REBASE_HEAD lock and that the branch was already up to date. Ancestry verification confirms #544 is in HEAD. Restored prior task implementation from `ba03fe90` onto this base, preserving #544's host routing and authenticated hub POST changes. No default-branch changes.

Corrected MAC to `/opt/MoonieXHQ/Archive/mac-delta-20260924`. Step-c tests capture the actual backup calls and exclude mac-secrets, winbox-keys and agents-core-presync sources. Narrowed only the guard's whole-tree mooniex-vps rule: generic secret checks remain; .env* / id_* / traefik_data / acme.json are refused there, and Archive mac-secrets*, winbox-keys* and agents-core-presync* remain fully protected. Updated docstrings and e/f text. The former whole-tree test now checks a protected secret path; all other existing guard cases remain.

## Nine secret filenames

PH-supplied name-only inventory, relative to `Archive/mooniex-vps/20260613T193125Z`:

- `alphatrader/.env`
- `option/.env`
- `option/.env.example`
- `option/.env.enc`
- `option/.env.bak.1781211822`
- `docker-n8n/.env`
- `claudeflow/.env`
- `line-automation/.env`
- `line-automation/.env.example`

Each is refused in Unix and Windows-path tests. Ordinary line-poster/file and volumes/file are allowed. The two windows.security.credentials.*.dll files stay excluded by the generic credential rule. PH reports no traefik_data in this snapshot; its exclusion remains.

## Files changed

- `deploy/systemd/org-disk-steward.{service,timer}`: Contabo oneshot, DB environment wrapper, idle I/O, 45-minute timeout, 10-minute boot delay and 30-minute interval.
- `scripts/install-disk-steward.sh`: reap-installer safety pattern, fake-systemctl/unit-directory overrides, template trust checks, timer takeover and uninstall rollback to reap; leaves reap unit files intact.
- `scripts/disksteward-p2-card.sh` and `tools/disksteward_p2.py`: ordered a–h steps, headers, before/after df, root/main-checkout live gate, mutation-free dry-run, `--only a` through `--only h` (also accepts descriptive step names). Persistent upload receipts support independent reruns. Service failure disables sparse checkout and stops the card.
- `tools/drive_leg.py`: upload-only `lineposter` verb using the shared P2 snapshot helper, existing `build_manifest`/`put` and winbox relay.
- `tools/disk_steward.py`: Contabo-only weekly success stamp inside the daily action block; failed backups remain eligible for retry.
- `tests/test_install_disk_steward.py`, `tests/test_disksteward_p2.py`, `tests/test_drive_leg.py`: isolated installer and safety tests, fake-relay LinePoster round trip.
- `.claude/skills/CXO_Knowledge_GDrive_FolderMap/SKILL.md`: matching tree/table definitions for the two approved destinations. Child folder IDs remain explicitly pending the real P2 upload; parent family ID is reused.

## Implementation evidence

Read the Thai plan and the PH brief. The brief is absent in this sparse checkout; its read-only source was `/opt/MoonieXHQ/Agents/Core/state/ph-briefs/project_head-9a54fd4d.md`. Read the requested Drive filing rules and folder map.

`git worktree list` and repository unit ExecStart lines identify:

| Deploy checkout | Services |
| --- | --- |
| `/opt/MoonieXHQ/Agents/Core/worktrees/spend-guard-deploy` | `spend-guard.service` |
| `/opt/MoonieXHQ/Agents/Core/worktrees/tool-value-deploy` | `tool-value-collect.service`, `tool-value-report.service` |

`tools/worktree.py apply-sparse` targets role-based `--no-checkout` launcher worktrees. For these existing service checkouts, the card instead applies an explicit cone keeping `tools lib config scripts runners policies`, discovers services from ExecStart, refuses dirty/missing checkouts, and rolls back sparse on failure.

Snapshots contain only regular, non-secret files. Symlinks, login-state names, secret patterns and `traefik_data` are excluded. Per-member md5 is computed from the actual bytes added to the tar. Dated UUID-suffixed names avoid replacing previous backups. Both tar and manifest are verified through `put`, then metadata is read again and matched by immutable Drive ID, size and md5. Receipts are reverified before removal; deletion checks the local member's md5 and inode/time metadata and calls `guard_path` immediately before unlink. No recursive removal is used in e/f; empty directories remain. Step f never removes `line-poster`, so it cannot bypass step e.

Child command diagnostics are suppressed to avoid leaking credentials. The journal tail retains up to 30 timestamps/unit labels but redacts MESSAGE completely. The card prints command exit status and service Result/ExecMainStatus.

## Validation performed

All tests ran in the assigned worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -o addopts='' -q -p no:cacheprovider tests/test_install_disk_steward.py tests/test_disksteward_p2.py tests/test_disk_steward.py tests/test_disk_steward_hosts.py tests/test_drive_leg.py
```

**145 passed, 1 skipped in 21.53s**. Skip requires native Windows handles. Includes #544 host routing/hub POST tests, installer safety, backup/deletion proofs, all nine secret names, allowed ordinary archive paths, protected bundles, step-c source selection and weekly retries.

`bash -n scripts/disksteward-p2-card.sh scripts/install-disk-steward.sh` and `git diff --check` passed.

## Exact CEO Run card command

After merge/live-sync, from the canonical checkout, run as root:

```sh
cd /opt/MoonieXHQ/Agents/Core && bash scripts/hub/with-org-db-env.sh bash scripts/disksteward-p2-card.sh
```

The wrapper supplies the DB environment needed by Work close. For a rerun, append e.g. `--only d`. Steps e/f need receipts from successful d/c respectively. Rollback:

```sh
bash /opt/MoonieXHQ/Agents/Core/scripts/install-disk-steward.sh uninstall
```

## Dry-run output

Command actually run in this worktree:

```sh
DRIVE_LEG_RCLONE=/bin/false PYTHONDONTWRITEBYTECODE=1 bash scripts/disksteward-p2-card.sh --dry-run
```

```text
=== before ===
would run: df -h /
=== a. install ===
would: bash scripts/install-disk-steward.sh install; systemctl start --wait org-disk-steward.service; journalctl -u org-disk-steward.service -n 30 --no-pager (redacted)
=== b. sparse ===
would: discover registered spend-guard-deploy + tool-value-deploy; git sparse-checkout set --cone tools lib config scripts runners policies; start --wait spend-guard, tool-value-collect, tool-value-report; disable sparse and stop on failure
=== c. archive ===
would: upload /opt/MoonieXHQ/Archive/mooniex-vps/20260613T193125Z and /opt/MoonieXHQ/Archive/mac-delta-20260924 to BACKUP/MoonieX HQ/Archive/contabo/; exclude traefik_data, secret names, login state and symlinks; verify dated tar + manifest by ID; save receipts; no deletion
=== d. lineposter ===
would: upload /opt/MoonieXHQ/Projects/MoonieX/LinePoster to BACKUP/MoonieX HQ/Projects/contabo/LinePoster/ as dated tar + manifest; exclude secrets; verify by ID; save receipt
=== e. duplicate ===
would: reverify d receipt on Drive; compare every duplicate/live file by md5; remove only backed-up matching files after guard_path; secret-named files and other NEVER-protected paths stay
=== f. prune ===
would: reverify c receipts on Drive; guard_path + md5 check each uploaded local file before unlink; preserve secret-named files, traefik_data and unmatched files; line-poster reserved for e
=== g. work ===
would: guard both Work trees; tools/workdir.py close task-67579503 --archive; tools/workdir.py close task-18e3ab26 --archive; no task-row edits
=== h. final ===
would: tools/disk_steward.py report; df -h /
=== after ===
would run: df -h /
```

## Blockers

- No implementation blocker. Commit/push and PR handoff belong to the launcher under the worker contract. No PR was created by this worker.
- Git metadata is read-only in this sandbox; no rebase metadata could be written. HEAD already equals the supplied origin/main ref at #544, so no replay was necessary. No remote fetch was performed.

## Not checked / risk

- No live systemd validation, sparse service execution, Drive upload, quota/free-space check, local pruning, or Work close. No task rows changed. No 48-hour disk/hub evidence exists from this write-only task.
- Installed unit overrides and service dependencies may differ from repository templates; actual start results remain a card-time check. Dirty deploy trees stop before sparse mutation.
- The backup snapshot uses a disk-backed temporary tar, roughly the selected source size plus tar overhead. Insufficient temporary space stops before verified receipts/deletion; available space and winbox availability remain operational checks.
- File-name/login-state exclusions are conservative; this is not a content-based secret scanner. Excluded files and symlinks remain local. A changing LinePoster tree can cause a snapshot or duplicate comparison to fail safely.
- Drive verification uses a fresh listing under the mapped parent ID and selects the exact recorded object IDs, with size/md5 checks for both objects. Live Drive behavior remains untested; fake relay round trip passed.
- Existing `workdir.py close --archive` semantics are reused, including its normal tmp/sourced-input cleanup. P2 first guards the entire Work tree and adds no task-row mutations.
- The journal MESSAGE redaction intentionally limits diagnostic detail; inspect protected host logs during card review if a service fails. New Drive child folder IDs need recording after the first authorized upload.

## Skill learning

- (none)
