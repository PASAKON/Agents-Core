# REPORT task-81d39324

## Summary

`spawn_c_level` in the secretary relay now starts a C-level on any host in `config/hosts.yaml` (mac, contabo, winbox) through `mesh.dispatch(host, "start_clevel", role[, "--resume", sid])` when `ORG_MESH_DISPATCH` is on. With the flag off the relay behaves as it did (pinned by tests that compare the exact JSON and audit lines). A second env, `ORG_MESH_PARALLEL_MAC_AGENT=1`, keeps the mac_agent queue leg alive beside the mesh call for the parallel run. `runners/mac_agent.py` got its retirement note and nothing else. Nothing was installed, no real host was dialled, no unit was restarted.

One environment finding cost me a first, tainted full run: `/dev/null` on this Contabo box had become a regular file. The CTO repaired it; the numbers below are from a clean pass after that. See Issues / Blockers.

## Files Changed

- `runners/relay_mcp_server.py` — `spawn_c_level` gains the mesh path behind `mesh.enabled()`; new helpers `_spawn_c_level_mesh`, `_spawn_via_mesh`, `_queue_mac_spawn` (the old inline Mac enqueue, moved unchanged), `_mesh_parallel_mac_agent`; constants `MESH_PARALLEL_ENV`, `RESUME_SESSION_ID_RE`; optional tool argument `resume_session_id`; imports `config`, `mesh`.
- `runners/mac_agent.py` — retirement note at the top of the module docstring. No code change.
- `tests/test_w25_spawn_c_level_mesh.py` — NEW, 58 tests, fakes only.
- `docs/reports/task-81d39324/REPORT.md` — this file.

## Commits

- 49fd77f1 — relay: spawn_c_level starts a C-level on any host via mesh start_clevel behind ORG_MESH_DISPATCH; mac_agent retirement note
- f0814b1c — tests: W2.5 spawn_c_level over the mesh, parallel mac_agent leg, flag-off pins
- the commit after f0814b1c adds this report (docs only)

## What was done

**Flag off (default).** `spawn_c_level` runs the old body. The only edits inside it: the Mac branch calls `_queue_mac_spawn(role)`, which is the same eight lines moved into a function (same `_queue_enqueue`, same `queued` audit line, same JSON keys in the same order), and a new `resume_session_id` argument is rejected with a clear message instead of being silently ignored. I recorded the old code's output for `(cfo, mac)`, `(cfo, winbox)` and `(ceo, mac)` before editing, and the tests assert the same bytes.

**Flag on.**
1. Role is checked with `_reject_unknown_role` (unchanged). Host must be a key of `config.hosts()`; an unknown one is rejected with `Known: mac, winbox, contabo`. `resume_session_id`, when given, must match `[0-9a-f]{8}` (the pattern `node_dispatch` enforces; a test pins the two together). All three refusals happen before `mesh.dispatch` is called.
2. `mesh.dispatch(host, "start_clevel", role)` or `(..., role, "--resume", sid)`. `lib/mesh.dispatch` already runs in-process when `host == self_host()` and over `ssh -i ~/.ssh/org_dispatch` otherwise, so the relay does not duplicate that switch.
3. Answers, all JSON, no queue row on any of them:
   - `spawned`: `role`, `host`, `transport: "mesh"`, `session_id`, `tmux_session` (when present) and the verb's `result`.
   - `refused`: the host was reached and said no (`detail` carries its error).
   - `unreachable`: `reason: "host <h> unreachable"` plus `detail`. Says nothing about whether the verb ran.
   - `error`: this relay could not resolve `self_host()`, or the host config is bad.
4. Audit lines (existing logger, `state/logs/relay.log` or `$ORG_LOG_DIR/relay.log`): `spawned`, `refused`, `unreachable`, `spawn_failed`, `rejected`, each with `host=<h> transport=mesh`.

**Parallel run.** Flag on, `host == "mac"`, `ORG_MESH_PARALLEL_MAC_AGENT` in `1/true/on`: after the mesh leg (whatever it said) the relay also enqueues the `spawn` row and answers with today's `queued` JSON plus a `mesh` key holding the mesh leg's outcome. One audit line ties them together:

    outcome=parallel_mac_agent detail=queue_id=<n> mesh_status=<spawned|unreachable|refused|error> mesh_session_id=<sid|None>

A resume request gets no queue leg (mac_agent's `spawn` cannot resume; a fresh session would answer a different question); the answer says `queue_leg: skipped` and the audit line says `queue_id=none`. The switch does nothing for winbox/contabo, and nothing with the mesh flag off.

**Comparison query** (checked end to end on a scratch log and scratch queue, real audit lines):

    # 1. the mesh leg and the queue id, per call (on the box that runs the relay)
    grep -h 'outcome=parallel_mac_agent' state/logs/relay.log* \
      | sed -E 's/.*target=([a-z]+) outcome=parallel_mac_agent detail=queue_id=([0-9]+) mesh_status=([a-z]+).*/\2 \1 \3/' \
      | while read id role ms; do
          sqlite3 -separator ' | ' "$SECRETARY_RELAY_QUEUE_DB" \
            "SELECT id, target_role, status, result, '$ms' AS mesh FROM relay_queue WHERE id=$id"
        done

Output, one line per call: `queue_id | role | mac_agent status | mac_agent result | mesh status`. A match is `done | spawned <role> on mac | spawned` (or both failing). `done ... | unreachable` and `failed ... | spawned` are the mismatches the 24 h window exists to surface. The queue file is `/home/secretary/runtime/relay_queue.db` by default on Contabo (`mac_agent.REMOTE_DB`); the audit lines are where the relay's logger writes. Sample run on a scratch log:

    1 | cfo | done   | spawned cfo on mac | spawned
    2 | cto | failed | spawn exit 1: x    | unreachable

**Which process loads this file.** `runners/relay_mcp_server.py` is not a service of its own. `mooniex-secretary.service` (User=secretary, `runners/secretary_server.py`) writes `config/secretary.mcp.json` at startup (`ensure_mcp_config()`), and every `claude -p` turn the secretary runs starts a fresh stdio child `…/.venv/bin/python …/runners/relay_mcp_server.py` from it. So a new turn loads new code without a unit restart, but the secretary's owner (SomPong lane) should still be told before the flag goes live. That MCP `env` block carries only `PYTHONUNBUFFERED=1`. Whether Claude Code hands its parent environment on to a stdio MCP child is not something I measured here, so **`ORG_MESH_DISPATCH` and `ORG_MESH_PARALLEL_MAC_AGENT` may need to be added to the `env` written by `ensure_mcp_config()`** when the flag goes live; the first audit line after go-live (`transport=mesh`) proves it arrived. I changed neither file, so the flag stays off everywhere.

## Tests

- New file alone: `.venv/bin/python -m pytest -p no:warnings tests/test_w25_spawn_c_level_mesh.py` → **58 passed** in 3.96 s. (The worktree has no `.venv`; I used the main checkout's interpreter, `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`, from the worktree directory.)
- Mutation check that the file has teeth (each applied to the relay, run, reverted): unreachable also enqueues → 4 failed; parallel switch always on → 8 failed; sid check removed → 10 failed; flag ignored → 10 failed.
- Existing pins (`scripts/test_relay_mcp_server.py`, `scripts/test_secretary_server.py`, `lib/test_config_roles.py`) stay green in the full runs below.
All three runs below are `.venv/bin/python -m pytest -p no:warnings` from the worktree, after the CTO restored `/dev/null` (verified `character special file 666`, 1:3, before and after the runs). One clean pass, both hosts, run back to back:

- Full suite, this box's default `ORG_HOST` (`contabo`): **2 failed, 3902 passed, 41 skipped in 607.83s.** Both reds are environment, see Issues 2.
- Full suite, `ORG_HOST=mac`: **3 failed, 3901 passed, 41 skipped in 537.93s.** The same two environment reds, plus `tests/test_storage_reclaim.py::test_delegate_skips_reclaim_when_green`: `RuntimeError: tmux session 'wd-65d220a0' was not alive after new-session` at `tools/tmux_session.py:142`, raised from `tools/delegate.py::_spawn_local` (files this task did not touch; that test starts a real tmux session). It passes alone: `tests/test_storage_reclaim.py` 19 passed, three times (twice with `ORG_HOST=mac`, once at the default host), and it passed in the clean default-host pass above. I did not chase the race.
- Earlier, tainted runs, kept for the record: first default-host run (`/dev/null` missing part-way) `8 failed, 3886 passed, 41 skipped, 10 errors`; first `ORG_HOST=mac` run `2 failed, 3902 passed, 41 skipped`; a run interrupted by the repair was stopped and discarded.
- New file inside those totals: 58 tests, all passed in both hosts. `scripts/test_relay_mcp_server.py`, `scripts/test_secretary_server.py`, `lib/test_config_roles.py` and the rest of the existing pins on `spawn_c_level` / `HOSTS` are not among the reds.
- `scripts/test_org_tools_registry.py`: `1 FAILURE(S)` with the environment as I found it (`[FAIL] wiki_list matches (toon)`); `ALL PASS` with `WIKI_ROOT_ORG=/opt/MoonieXHQ/Agents/Rules WIKI_ROOT_MOONIEX=/opt/MoonieXHQ/Agents/Wikis` exported, which is what `cto-claude.sh` does. The same single failure reproduces on an untouched export of base commit 4c839e72, so it is not this change.
- `scripts/test_mcp_role_config.py`: `OK — 0 failure(s)`.

## Issues / Blockers

1. **`/dev/null` on this box became a regular file; the CTO repaired it, the cause is still unknown.** Found at about 14:04 UTC: `regular file`, mode 644, born 2026-09-30 15:29:11 CEST (13:29 UTC), where it should be `character special file 1:3`, mode 666. While it was missing, `git init` died with `fatal: could not open '/dev/null' for reading and writing: No such file or directory`, which turned my first default-host run into `8 failed, 3886 passed, 41 skipped, 10 errors` (git-based fixtures in `scripts/test_install_git_hooks_media.py`, `scripts/test_skill_lint.py`, `tests/test_delegate_*`, `tests/test_storage_reclaim.py`). Who removed the device is not established. My default-host suite started at about 15:27 CEST, so my run cannot be ruled out; my new test file does not touch it, and I found no test in `tests/` or `scripts/` that unlinks it (grep for unlink/remove/rename next to `devnull`). The box is shared with other worktrees, so a peer session is equally possible. A stray file `/dev/null^M` (0 bytes, 16 Sep) is also in `/dev`, from an earlier CRLF script. I changed nothing in `/dev` myself: my `mv` + `mknod` repair was refused by the classifier both times and I did not route around it. After the CTO's repair `stat` says `character special file 666` and stayed that way through the clean pass. If it recurs, the first suspect to rule out is a full run of this suite on a shared box as root.
2. **Two environment reds unrelated to this change**, present in both host runs: `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins` (this box's `installed_plugins.json` has only `topview-browser@topview`), and `tests/test_h3_runner_model_launch.py::test_script_org_tools_registry_verdict` (runs the registry script without `WIKI_ROOT_ORG`, see above).
3. **Turning the flag on without the parallel switch breaks Mac spawns from Contabo.** `hosts.yaml` has `ssh: null` for the Mac, so `mesh.dispatch("mac", ...)` from the secretary can only answer `unreachable`, and the spec says an unreachable answer writes no queue row. Until the Mac has a dialable alias, go live with `ORG_MESH_DISPATCH=1` **and** `ORG_MESH_PARALLEL_MAC_AGENT=1`; then Mac spawns keep working through mac_agent and the audit shows `mesh_status=unreachable` for each.
4. **winbox is accepted by the relay but the verb refuses it today.** `tools/node_dispatch.verb_start_clevel` raises `start_clevel is not supported on windows until W3`, so `spawn_c_level(role, "winbox")` returns `refused` with that text once the flag is on. The relay-side acceptance (and the ssh command it builds) is tested; the far side arrives with W3.
5. **Double spawn is possible during the parallel run.** If the mesh leg ever does reach the Mac while `ORG_MESH_PARALLEL_MAC_AGENT=1`, the mesh call starts a session and mac_agent starts another. That is inherent in "run both and compare", and it only happens once the Mac is dialable; today the mesh leg is `unreachable`.
6. Several of my attempts to run extra checks (a base-commit rerun of the two environment reds, a read-only watcher on `/dev/null`, a file monitor) were refused by the auto-mode classifier as "Modify Shared Resources". I did not retry them. The evidence for the two environment reds is in the runs above and the earlier base-export run of the registry script.

## Notes for Reviewer

- The diff for the flag-off path is small on purpose: `git diff 4c839e72 HEAD -- runners/relay_mcp_server.py` shows the old Mac branch replaced by a call to `_queue_mac_spawn`, plus one `if resume_session_id is not None` reject. Everything else is additive.
- The tool's docstring (what the secretary's model reads) now mentions the mesh and `resume_session_id`, including with the flag off, because the schema is static. With the flag off both are rejected with a clear reason.
- `resume_session_id` is a new argument on a Telegram-reachable tool. It is 8 lowercase hex characters, checked in the relay and again by `node_dispatch`, and the verb itself resolves it to a UUID from the session's own record or refuses (`no resumable UUID`). `test_no_tool_accepts_a_free_form_command_argument` still passes.
- The secretary's system prompt (`runners/secretary_server.py`) was not touched; it does not name the new argument. Say if the secretary should be taught `resume_session_id` before go-live.
- mac_agent retirement is the CTO's call after 24 h of matching output counted from go-live; this task adds only the note.

## Skill learning

- MISSING [no owner] : `tests/test_storage_reclaim.py::test_delegate_skips_reclaim_when_green` (and, once, `tests/test_delegate_workdir.py`) start a real tmux session and can fail with `tmux session ... was not alive after new-session` inside a full run while passing alone; a worker reading a red full run has no way to tell that flake from a regression short of rerunning the file · evidence: task-81d39324, `ORG_HOST=mac` clean pass, 3 failed vs 19 passed alone ×3 · one sighting, a note not a rule.
- MISSING [CTO_Gate_MergeChecklist | no owner] : a full pytest run on this shared Contabo box can be poisoned by a broken `/dev/null` (git fixtures die with exit 128, `could not open '/dev/null'`), and nothing tells a worker to `stat /dev/null` before trusting red results · evidence: task-81d39324, default-host run `8 failed, 10 errors` vs 3 real environment reds in isolation · prevented by: one line "if `git init` fails with exit 128 in fixtures, run `stat -c %F /dev/null`; it must be a character special file".
- MISSING [no owner] : the hook `scripts/hook-self-repo-guard.py` blocked a Bash command whose scratch probe ran `git init` under `/tmp`, naming the worktree's declared touches as the reason; a probe under the scratchpad with no `.git` in the path is what it wants · evidence: task-81d39324, first `/dev/null` repair attempt · prevented by: note in the worker brief that any command text containing `.git` paths is checked, even outside the repo.
- COSTLY [no owner] : the auto-mode classifier refused every later background/test command after a `/dev/null` repair attempt, including read-only file monitors; the worker could not tell which part was flagged · evidence: task-81d39324, four consecutive "Modify Shared Resources" denials · prevented by: ask the C-level for the repair first and keep verification commands to the exact form that was already accepted.
