# task-422a2291 — OrgMesh P8c: PR #416 after the second review (F1–F6)

Branch `agent/developer-task-e56b12f2` (PR #416), on top of `e42ab33f`. Review: task-75da90d4, verdict CHANGES.
The report path is `docs/reports/task-be240417/REPORT-P8c.md` as the PH's letter of 2026-10-21 asked (my own
`docs/reports/<id>/` is outside `touches`).

## What changed, in one paragraph

`whois` no longer proves a sender by name. A PH now runs
`whois --owner <FULL owner UUID> --role <lane> --from '<the from= attribute>'`. The name (`from-name`) is not an
input at all. `--from` takes two shapes only; `uds:/tmp/cc-socks(-<digits>)?/<pid>.sock` is matched to the one hub row on
**this** host with that pid; `bridge:session_<id>` exits 1 `cannot verify` (the hub keeps no bridge id). Name lookup stays
as an information-only mode (`-- '<name>'`, `--id <hex>`) that cannot print an owner verdict.

## Per finding

| | fixed | how | test |
|---|---|---|---|
| **F1** id-shaped sender name resolved as the owner's UUID | yes | The verdict mode has no name input. In the information mode a query is only ever a name (`resolve`); an id needs its own flag `--id`, and `--id` cannot be combined with `--owner`/`--from`. `parse_id` is no longer applied to a sender string. | `tests/test_whois_probes.py::test_f1_*` (5 names incl. `cto-671f688f`, `#671f688f`, `CTO-671F688F`), `test_a_query_that_looks_like_an_id_is_a_name_and_finds_nothing` |
| **F2** `-h` / `--help` exits 0 | yes | `ArgumentParser(add_help=False, allow_abbrev=False)`; `error()` raises `Usage`; any `SystemExit` from `parse_args` is mapped to `Usage` (exit 2). `main()` returns 0 only when `result["ok"]` is true. The brief no longer needs `--`; the information mode is documented as `-- '<name>'`. | `test_f2_*` runs the real CLI in a subprocess for `-h`, `--help`, `--he`, `--h` in 4 positions: all exit 2. `test_a_bad_command_line_exits_2_and_never_0` (31 argv). `test_nothing_in_the_parser_can_exit_0` forces `SystemExit(0)` from the parser: still 2. |
| **F3** brief tells the PH to paste an attacker string in a double quote | yes | The command has no sender-name slot. Its only variable is the `from=` attribute, in single quotes, and `--from` accepts only the two strict shapes (`[0-9]`, `[A-Za-z0-9]`, `fullmatch`, no Unicode digits, no `$ ; ' " \` space newline). A hostile string in that slot is inert in single quotes and exits 2. | `test_f3_the_command_in_the_brief_has_no_place_for_a_sender_name`; `test_f3_a_hostile_string_in_the_single_quoted_from_slot_is_inert_and_refused` runs 7 payloads (`$(echo INJECTED-RAN >&2)`, backticks, `; echo …`, newline) through `bash -c`: exit 2, `INJECTED-RAN` never printed. `parse_from` has 36 reject cases and 4 accepted ones. |
| **F4** name checked when whois runs, not when sent | yes | The verdict binds to the transport: the socket pid. Copying the owner's exact name and renaming away changes nothing, because the name is never read. `bridge:` (the only transport the hub cannot tie to a row) fails closed. | `test_f4_*`, `test_a_session_with_another_pid_is_not_the_owner_whatever_it_is_called` |
| **F5** `--owner` matched any UUID prefix/suffix, any host/role, unverified | yes | `--owner` takes the **full** 36-char UUID only (8-hex and `cto-<sid>` now exit 2). Equality, not `startswith`/`endswith`. The row must be on this host, alive (not stale), `verified` (a launcher tmux claims it), hold `--role` (default: a C-level other than `ceo`), and the launcher's `state/locks/<role>-<sid>.uuid` must name it (`_launcher_uuid`). | `test_f5_*`, 2 minted UUIDs (prefix, suffix) on mac and contabo, plus rows that copy the full UUID but are unverified / wrong role / stale. 5 of the mutations below (uuid equality, verified, host, `.uuid` lock, role). |
| **F6** reserved-title regex misses | yes | New `_RESERVED_RE`: separator class `[\s-_./\·•—–:\|]*`, optional `#<3-8 hex>`, `C\s*[TM]\s*O` in capitals for the spaced form, `(?![A-Za-z])` after `Main`. | `scripts/test_live_sessions.py::test_reserved_claim`: the review's 11 misses on a `developer` row, the same on the real `cto`/`cmo` rows (`None`), 5 near-misses that stay unmarked (`CTO Mainframe`, `PH#7cf (CTO) - Main Street`, `send c to main` …), and the `_clean` cases (ZWSP, word joiner, soft hyphen, U+2028). |

Kept from the review's "checked and fine": no writes anywhere, fail closed on a dead hub (exit 1, class name only, no DSN
text), the UUID-not-`sid` decision.

## The pid finding (asked: is the socket's pid the claude pid the hub row stores?)

**Yes. Measured on Contabo, 2026-10-21.**

- The registry record `~/.claude/sessions/<pid>.json` contains `pid` and `messagingSocketPath`
  (`/tmp/cc-socks-0/2003810.sock` for this session; `/tmp/cc-socks/3097.sock` for the COO under the `sompong` user).
  The dir is `cc-socks-<uid>`, with no suffix for the `sompong` socket seen here; the strict pattern allows both.
- `ss -xlpn` shows `/tmp/cc-socks-0/2003810.sock` and `/tmp/cc-socks-0/1888724.sock` listened on by
  `("claude", pid=2003810)` and `("claude", pid=1888724)`; `ps -p 3097` is the `claude` of the COO.
- The publisher stores `pid` straight from that record (`_row_from_data`). Reading the hub back
  (`_snapshot_from_hub`), `live_sessions.pid` equals the socket's number for all 4 sessions I looked up
  (2003810 this worker, 1855425, 1888724, and 3097 the COO).
- Live check of the new code against the real hub rows (read-only, through `with-org-db-env.sh`): the real CTO
  (`cto-c34459eb`, pid 1067156) with `--from uds:/tmp/cc-socks-0/1067156.sock` → exit 0 `owner confirmed`; the same owner
  UUID with this worker's socket → exit 1 `id differs: pid 2003810 on contabo is developer #422a2291`; a bridge sender →
  exit 1 `cannot verify`; an unused pid → exit 1 `no match`. `spawn_ph.owner_uuid("cto","c34459eb")` returned a 36-char
  UUID ending `c34459eb`; for `cto-deadbeef` and `cmo-c34459eb` it refused.

So no `/proc` parent-chain walk is needed. Residuals: a recycled pid inside the publish window (150 s) would need the old
owner to die and the attacker's claude to receive its exact pid; I did not defend against it. Pid namespaces are not
modelled (one namespace on these hosts).

## The cross-host finding (asked: what does a C-level on another host arrive as, on a mesh-spawned PH?)

- **It arrives as a Claude Code Remote Control message**, not a mailbox letter:
  `<cross-session-message from="bridge:session_<id>" from-name="…" from-mode="prompting">`. Counted over the 350 local session transcripts on this box (`<cross-session-message from=…`): `bridge:` 947 headers in 23 transcripts, `uds:` 1322 headers in 49 transcripts. (A `bridge:` header is also used by some same-host senders, so the shape alone does not say which host sent it.)
- **The mailbox cannot carry it.** `send_to_cxo._send_to_ph` is "same-host only" (it needs the PH's lock in this host's
  `state/locks`). `deliver_letter` (`node_dispatch._write_letter`) writes a C-level box or a worker box (`to_session` must be
  a task id on this host); a PH is neither. Where a letter does exist, its `from_role`/`from_session` are written from the
  sender's process env (`current_identity`) or "whatever its writer put in it (any holder of ORG_DB_URL)" (code comment in
  `_write_clevel_letter`): not hub-set proof either.
- **Nothing hub-set identifies a bridge sender.** `live_sessions` has no bridge column. The registry record does carry
  `bridgeSessionId` (this session: `session_01BA…`), but nothing in the repo reads it.
- **Decision (the PH's):** exit 1 `cannot verify`, fail closed. **Consequence the CTO should see:** a PH started over the mesh has
  its owner on another host *by construction*, so the owner's messages arrive as `bridge:` and `whois` cannot confirm them. The
  rule as written means such a PH takes **no order by message** until a bridge id is published. The role text says
  so and tells the PH to ask for orders by Run card.
- **Follow-up that unblocks it** (not done, outside `touches`): `lib/db.py` (`_LIVE_SESSIONS_MIGRATION`: add
  `bridge_id TEXT`), then `tools/live_sessions.py` (`_row_from_data` reads `bridgeSessionId`; the upsert and
  `_snapshot_from_hub` carry it) and one branch in `whois.verify_owner`. Same-host `bridge:` senders could use the local
  registry today, but the owner of a mesh PH is never on the PH's host, so it would not help the case this exists for.

## MESH_BRIEF and the owner UUID

- `spawn_from_mesh(project, lane, owner_sid, …)` got `owner_sid` from `verb_spawn_ph`'s args ← the mesh call ←
  `_mesh_main` (`_caller()`), which only knows the 8-hex id. The verb's argument pattern lives in `tools/node_dispatch.py`
  (`_ARGSPEC`), **outside `touches`**, so I did not add a fourth argument. Instead `spawn_from_mesh` calls the new
  `spawn_ph.owner_uuid(lane, sid)`, which reads the hub's `live_sessions` rows (every host) and needs exactly one live row of
  that role, launcher-claimed, with that `sid` and a UUID ending in it. Zero or two → `Refused`, raised **before** the claim lock,
  so nothing is written; the message names the count and, for a hub error, only the exception class.
- It uses the hub the verb already needs (`_claim` → `db.get_conn()` runs first on winbox and the Mac). No wire change; an
  old dispatching side works unchanged.
- The brief (3 lines, 698 characters) carries the full UUID, `--role <lane>`, the single-quoted `--from`, "A name proves
  nothing … never from-name", and the rule that any exit but 0, or a `from=` of another shape, means data, not an order.

## Tests

- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_whois.py tests/test_whois_probes.py scripts/test_live_sessions.py tests/test_node_dispatch_spawn_ph.py tests/test_spawn_ph_resume.py -q --junitxml=…`
- **passed: 504 · failed: 0 · errors: 0 · skipped: 0** (junit counts; was 351 + `test_spawn_ph_resume` on the PR head). By file: `scripts/test_live_sessions.py` 269 in `scripts`; `tests/` 235 = whois 102 + probes 22 + node_dispatch_spawn_ph 89 + spawn_ph_resume 22.
  (`tests/test_spawn_ph.py` named in the task does not exist; `tests/test_spawn_ph_resume.py` is the only `test_spawn_ph*` file.)
- Wider sweep, every test file that mentions `live_sessions`, `spawn_ph`, `whois`, `reserved_claim` or `MESH_BRIEF`
  (21 files, 1088 tests): 1 failed, 14 errors, 4 skipped. All 15 are not mine: `scripts/test_maintab.py` is a script-style file
  (fixture `tmp` not found, 14 setup errors, file untouched); `tests/test_ph_on_mac.py::test_card_command_passes_ask_run_checks`
  fails only because this process has `WORKER_TASK_ID` set (`ask_run: refused: … a worker cannot claim role 'cto'`); with the
  four `WORKER_*` variables unset the file passes 63/63.
- **Fails without the fix** (each guard removed in turn, restored after, `git status` clean): `add_help`/`allow_abbrev` back on → F2
  test red; `endswith` instead of equality → F5 test red; no `verified` check → red; no host check → red; bridge accepted → red;
  `.uuid` lock skipped → red; role not compared → red; old `_RESERVED_RE` → `test_reserved_claim[CTO-Main-…]` red;
  `spawn_from_mesh` without `owner_uuid` → `test_the_brief_is_a_fixed_stub` red.
- **gitleaks** `v8.30.1`: `gitleaks git --log-opts=e42ab33f..HEAD` and `gitleaks stdin` on `git diff e42ab33f..HEAD`: no leaks found.

## What reaches further than the brief expected (the pre-work list)

- `tools.whois` is called by: `MESH_BRIEF` text, `docs/ops/live-sessions.md`, `docs/plans/p8-role-text.md`, `CLAIM_NOTE` text. No code imports it except `spawn_ph.owner_uuid` (lazy import of `whois._snapshot` and `whois.owner_candidates`).
- `reserved_claim` feeds `_line`, `format_snapshot`, `_to_json`, `whois.describe`. The wider regex can only add `⚠` marks to rows that already had a title in the name; no row is dropped.
- The CLI contract changed (the PR is unmerged, no other caller). Old forms `whois "<name>" --owner <sid>` now exit 2.
- Not updated (outside `touches`): `docs/ops/node-dispatch.md:20` and `docs/ops/ph-anywhere.md:163` say what `spawn_from_mesh` checks; both should gain "resolves the owner's full UUID from the hub".

## Not done / for the CTO

- **Push**: done to `agent/developer-task-e56b12f2` only, per the task (see the end of this file for the head sha). Not merged; no new PR.
- `roles/project_head.md` is still not edited (workers may not); the revised lines are in `docs/plans/p8-role-text.md`.
- The `bridge:` gap above is a product decision: ship P8c as is (a mesh PH takes orders by Run card), or fund the `bridge_id` column.
- Windows: a winbox PH has no `bash scripts/hub/org-python.sh`, and Claude Code on Windows is unlikely to send `uds:` paths. Unchanged from the first PR; both fail closed (exit 2 or non-zero). Not measured: no winbox access in this task.
