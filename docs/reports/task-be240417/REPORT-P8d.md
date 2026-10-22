# task-4098b698 — OrgMesh P8d: verify a `bridge:` sender by the hub row

Branch `agent/developer-task-e56b12f2` (PR #416), on top of `72816999` (P8c). Report path as the CTO's brief gave it
(`docs/reports/task-be240417/`; my own `docs/reports/<id>/` is outside `touches`).

## What changed, in one paragraph

A mesh-spawned PH's owner is on another host, so its messages arrive as `from=bridge:session_<id>` (Remote Control).
P8c failed those closed (`cannot verify`). Now `live_sessions` has a `bridge_id TEXT` column fed from the registry's
`bridgeSessionId`, and `whois --owner <FULL UUID> --role <lane> --from 'bridge:session_<id>'` finds the one row on **any
host** with that bridge id and applies the uds-style owner checks. The brief a PH gets names the `whois` command for its
own OS, because winbox has no bash. The winbox pull script (`PS_PULL_SCRIPT`) did not forward `bridgeSessionId`; it does now.

## Per item of the brief

| # | item | done | where |
|---|---|---|---|
| 1 | `bridge_id TEXT` migration | yes | `lib/db.py` `_LIVE_SESSIONS_MIGRATION` (additive, nullable; the existing ALTER loop adds it; `_pg_schema_current` already covers migration columns). `db_pg.py` `PG_SCHEMA` untouched |
| 2 | registry → row → hub → reader, Windows path too | yes | `tools/live_sessions.py`: `_bridge_id()` keeps only `session_` + 1-100 `[A-Za-z0-9]` (a `str`, `fullmatch`), else `None`; `_row_from_data` sets `bridge_id`; `publish_rows` and `_snapshot_from_hub` carry it; **`PS_PULL_SCRIPT` now emits `bridgeSessionId=[string]$j.bridgeSessionId`** |
| 3 | `whois --from bridge:` | yes | `tools/whois.py` `_verify_bridge`, below |
| 4 | `MESH_BRIEF` per OS | yes | `tools/spawn_ph.py` `whois_command`, `mesh_brief`, `_windows_hub_prefix` |
| 5 | docs | yes | `docs/ops/node-dispatch.md:20`, `docs/ops/ph-anywhere.md:163`, `docs/ops/live-sessions.md`, `docs/plans/p8-role-text.md` |
| 6 | tests | yes | below |

### The bridge verdict (`_verify_bridge`)

1. rows with that `bridge_id` on any host (stale ones included): **0 → exit 1 `no match`, 2+ → exit 1 `ambiguous`**;
2. the row's full UUID must equal `--owner` (else `id differs`), the row must not be stale (`not alive`);
3. **extra over the brief:** the owner's UUID must be on exactly one live row (a forged twin next to the real owner → `ambiguous`);
4. a launcher tmux must claim the role (`not verified`), the role must be `--role` (`role differs`);
5. the launcher's `.uuid` lock is read **only when the row is on this host** (the lock is a file on the row's host).

Exit 0 is reachable only through that path. `bridge_id` is never printed: not in `describe`, `format_text`, `--json`, or
`live-sessions.sh`.

### The brief, per OS (`spawn_ph.whois_command`)

- **POSIX (Contabo, Mac):** `bash scripts/hub/org-python.sh -m tools.whois --owner <UUID> --role <lane> --from '<the from= attribute>'`, unchanged.
- **Windows (winbox):** no bash. The line is `scripts/lib/cxo_mcp_config.windows_hub_prefix(root)`
  (`<venv python> -E -s tools/infisical_setup.py run Agents-Core prod --as winbox --`) + `<venv python> -m tools.whois …`,
  written with forward slashes (PowerShell and Git Bash read both). The PH's own environment has **no `ORG_DB_URL`**
  (`windows/cxo-claude.ps1`: it lives only in a process started under `infisical_setup.py run … --as winbox`), so the hub
  prefix is what gives whois its route; the PH runs it with cwd = the repo root (`Set-Location $root`), the same assumption
  the POSIX form makes.
- **A Windows host that cannot reach the hub gets no PH.** `windows_hub_prefix` returns `None` (not Windows, no `org_db: hub`
  node file, no venv, no credential file) → `spawn_from_mesh` raises `Refused` **before** the claim lock, nothing written,
  nothing launched. So a winbox PH that could not run `whois` (and so could take no order by message) is never started. Paths
  with whitespace or shell characters are refused too, not half-quoted.

## The forger analysis (asked)

**Where the id comes from.** The `from=bridge:<id>` in a header is the sender's own claude.ai Remote Control session id. The
sender cannot choose it: the service issues it. It is equal to the `bridgeSessionId` in the sender's own registry record
(measured, read-only, 2026-10-21: this session's registry record = its `Claude-Session` link, `session_016Lt…`; the CTO's
transcript shows its headers `from="bridge:session_018PXX…"` and later `session_01NJab…`, the two ids its registry held in
turn; the CTO's registry today says `01NJ…`). No same-host sender/receiver pair was available (same-host senders arrive as
`uds:`), so I could not diff a header against a registry on the same box directly; none of the 7 local registry ids appears as
a `from=` in the local transcripts.

**It changes.** A reconnect, restart or resume of Remote Control gives a session a new id; the hub row follows within one
publish cycle. A message sent just after a reconnect can answer `no match`: that is a fail-closed refusal. Retry it a minute
later, or ask by Run card.

**What a forger needs, and how that compares with `uds:`.** `uds:` needs a hub row *on this host* whose pid owns the socket
(the sender cannot pick its pid), plus the launcher's `.uuid` lock file on this host. A bridge row can be on another host, so
the lock cannot be read: that check is **weaker**, and I say so rather than hide it. To pass as the owner over a bridge a
forger needs a row with (a) the owner's full UUID, (b) `verified` (a launcher tmux claims the role) and (c) the forger's *own*
real bridge id (so the header matches). That row is made by a record in another host's `~/.claude/sessions` (or the winbox
registry that the Contabo publisher pulls over ssh), or by a write to the hub's `live_sessions` (publisher or DB credentials).
Whoever can do that already runs as the owner's account on that host or holds the hub. The one thing I added beyond the brief:
the owner's UUID must be on exactly one live row, so a forged twin **beside the real owner** makes whois answer `ambiguous`.
**Residual risk:** a forged row passes when the real owner's row is gone (stopped, stale). I did not close that, and I do not
think it can be closed from the hub's data alone.

`bridge_id` is also not granted to `org_coo` (`deploy/coo-gate/org_coo_role.sql`, not touched: outside `touches`, and no need):
the reader probes `information_schema.columns`, a role without the grant reads `NULL AS bridge_id`, and that reader can never
confirm a bridge, which is the safe side.

## Tests (all with `WORKER_*` unset)

- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_whois.py tests/test_whois_probes.py scripts/test_live_sessions.py tests/test_node_dispatch_spawn_ph.py tests/test_spawn_ph_resume.py tests/test_db_init_pg_lock.py`
- **passed: 571 · failed: 0 · skipped: 0.** By file: whois 121 (was 102), probes 23 (was 22), `scripts/test_live_sessions.py` 295 (was 269),
  node_dispatch_spawn_ph 95 (was 89), spawn_ph_resume 22, `test_db_init_pg_lock` 15 (was 13).
- New tests: bridge verdict **ok** (cross-host) / **no row** / **two rows** / **wrong uuid** / **stale** / **unverified** / role differs /
  forged twin ambiguous / forged twin after the owner is stale (the residual, asserted) / lock read on the same host and skipped on
  another; the CLI exits 0 for the owner over a bridge; **9 hostile bridge strings → exit 2**; registry **without**
  `bridgeSessionId` → `None`; 20 malformed ids → `None`; publish carries / omits `bridge_id` by column presence; reader
  returns `bridge_id` or `NULL AS bridge_id`; `PS_PULL_SCRIPT` carries the key; migration adds the column to a table that lacks it
  and only then; `_pg_schema_current` false when it is missing; brief per OS (Windows command exact, no `bash`, no hub route →
  `Refused` and nothing written, 4 paths that need quoting refused; POSIX unchanged).
- **Fails without the fix** (each guard removed in turn with the test file(s) for it, restored with `git checkout`, tree clean after):
  14 mutations, **all red**. whois: twin check off; two rows not ambiguous; lock skipped on this host; lock demanded for every host;
  `verified` ignored; stale ignored; uuid ignored; role ignored. live_sessions: any string accepted as a bridge id; `bridge_id` not
  published; `bridgeSessionId` dropped from `PS_PULL_SCRIPT`. db: column removed from the migration. spawn_ph: Windows with no hub
  prefix still starts; Windows command uses bash.
- Wider sweep, every test file that mentions `live_sessions`, `spawn_ph`, `whois`, `MESH_BRIEF`, `escalation_watch`, `windows_hub_prefix` or
  `cxo_mcp_config` (37 files): **2448 passed, 193 skipped, 1 xfailed, 0 failed, 14 errors**; the 14 errors are all `scripts/test_maintab.py`
  (script-style file, fixture `tmp` not found; untouched, same as P8c). Plus the 16 files that touch `lib/db.py` migrations / `init_schema`
  (`tests/test_db_*`, `test_hub_cutover_scripts`, `test_migrate_tasks_db`, …): 0 failed.
- Known unrelated reds on this branch's base, unchanged: `scripts/test_depends_on_enforcement.py` (12, `ArchivedDB`: this
  process predates the hub cutover; it fails identically on `72816999`, checked in a scratch worktree) and, from P8c,
  `scripts/test_maintab.py` (fixture errors), `tests/test_ph_on_mac.py::test_card_command_passes_ask_run_checks` (only with `WORKER_*` set).
- **gitleaks** `v8.30.1`: `gitleaks git --log-opts=72816999..HEAD` (2 commits) and `gitleaks stdin` on `git diff 72816999..HEAD`: no leaks found.

## Run for real (read-only)

- **winbox registry + pull, over ssh `winbox`:** the 3 registry files each have `bridgeSessionId`, all `session_[A-Za-z0-9]+`.
  The publisher's own `pull_remote("winbox")` with the new script returned 3 rows, each with a `bridge_id` of that shape
  (before P8d every winbox row had none). `windows_hub_prefix` on winbox returns the expected 9 words (venv python `-E -s`
  `tools\infisical_setup.py run Agents-Core prod --as winbox --`).
- **winbox `whois` itself: NOT run.** The checkout on winbox is at an older commit (`tools\whois.py` is not there, and
  `tools\live_sessions.py` has no `bridge_id`), so there is nothing to run until this branch is deployed there. Whether the
  Windows line works end to end (hub prefix → whois → hub) is **not measured**.
- **Contabo, live hub, this branch's code:** `owner_uuid("cto","c34459eb")` returned a 36-char UUID; `whois --owner <it> --role cto
  --from 'bridge:session_016Lt…'` → `owner: NO — no match: no live session on any host has that bridge session id`, exit 1. That
  is the **pre-migration** state (the prod hub has no `bridge_id` column yet, so the reader selects `NULL AS bridge_id`): fail closed.
  I did **not** run `init()` on the prod hub; the migration runs when the CTO deploys.

## What reaches further than the brief expected (the pre-work list)

- `_has_verified`, `_UPSERT_SESSION`, `_UPSERT_SESSION_V` had no caller outside `tools/live_sessions.py` (replaced by `_live_columns`,
  `_upsert_session(extra)`); `scripts/test_live_sessions.py` `FakeHub` answered the column probe with `[(1,)]`, so it now
  returns column names.
- `_snapshot_from_hub` callers: `tools/escalation_watch.py:436`, `tools/whois.py`, `render`, the publisher loop. All read rows as dicts, so a new
  `bridge_id` key changes none of them. `bridge_id` is in `_row_from_data` rows, not in `_snapshot_local` (local read has no hub).
- `MESH_BRIEF.format(...)` callers were tests only; `spawn_from_mesh` now calls `mesh_brief(...)`. `MESH_BRIEF` has a new `{command}` slot.
- `tests/test_db_init_pg_lock.py` `_complete_catalog` derives from `_LIVE_SESSIONS_MIGRATION`, so it tracks the new column by itself.
- **Every host's publisher must run P8d code.** A row published by older code has no bridge id, so a bridge sender whose host runs older
  code is `no match` (fail closed, but a mesh PH would take no order from it). Contabo's publisher, the Mac's and the winbox pull
  (done from Contabo) all need the deploy.

## Not done / for the CTO

- **Push**: fast-forward of HEAD to `agent/developer-task-e56b12f2` only (no force, no new PR, no merge), as the brief says.
- Deploy order: land this on Contabo first (the migration runs at `init()`), then restart the live-sessions publisher; then winbox
  (checkout + the same PS script is sent from Contabo, so winbox needs the branch only for the `whois` it will run) and the Mac.
- `roles/project_head.md` is still not edited (workers may not); `docs/plans/p8-role-text.md` carries the lines.
- The `org_coo` grant, `docs/ops/node-dispatch.md` beyond line 20 and the role text in Agents-Rules are not touched.
