# REPORT task-ec82f9ea

Job: make the GitHub Actions `pytest` job pass on origin/main (run 36954979364 on 67443d49: 20 failed, 6820 passed, 40 skipped).
Branch `agent/developer-task-ec82f9ea`, 8 commits on top of 0547d1b7. Nothing pushed.

Two causes in the brief were not what the log says: B is not a production bug, and C is not two code paths that
disagree. Group A is 13 tests in that log, not 11 (13 + 1 + 1 + 1 + 2 + 2 = 20). Groups B and C were reproduced on the
Mac before any fix. Group G is not in that run: it comes from run 36952132198 on e0177fc6, quoted in the brief.

## Per group

| Group | Confirmed cause and evidence | Fix | Test that proves it |
|---|---|---|---|
| **A** `test_spawn_coo.py`, 13 tests | Confirmed. `scripts/cxo-claude.sh:106` runs `source .venv/bin/activate`. The `lroot` fixture linked `.venv` to `sys.prefix`; on CI that is the setup-python toolcache interpreter, which has no `bin/activate`. All 13 CI failures carry `cxo-claude.sh: line 106: .venv/bin/activate: No such file or directory` and exit code 2 (`assert 2 == 0` / `assert 2 == 1`). All 13 use the `lroot` fixture. The file was added 2026-10-01 (63bcb362). | `_hermetic_venv()` in the test: link `sys.prefix` when it has `bin/activate`, otherwise `venv.create(system_site_packages=True, symlinks=True, with_pip=False)`. `cxo-claude.sh` untouched. | `test_hermetic_venv_links_a_prefix_that_has_activate` and `test_hermetic_venv_builds_activate_over_a_prefix_that_has_none`. On the Mac, 11 of the 13 skip (no `flock`, `getent`/`nobody` or `/proc`); `test_launcher_still_starts_the_other_roles_off_contabo` runs and passes; `test_launcher_moves_an_unread_letter_to_the_new_box` fails here for a Mac-only reason (see Blockers). So the first run of the launcher tests through a venv built over a bare prefix is CI's. |
| **B** `test_media_gate_unstages_mp4_and_large_binary_and_keeps_large_text` | **Not a production bug.** `spawn-worker-remote.sh:349-364` refuses the codex runner with `SPAWN_REFUSED=codex-not-found` on **stdout** and exits 1. CI has no `codex` binary; the Mac has one on PATH. The test printed only `r.stderr`, which held git's `Cloning into ...` text, so the failure read as an unexplained exit. The refusal is the script's documented behaviour, so the script is unchanged. | `media_gate_env` fixture puts a fake `codex` on its private PATH; the assertion message now carries stderr and stdout; the spawn argv moved into `_media_spawn()`, shared by both tests. | The media-gate test passes. New `test_spawn_refuses_the_codex_runner_on_stdout_when_no_codex_is_installed` removes the fake codex and pins rc 1, `SPAWN_REFUSED=codex-not-found` on stdout and not on stderr (it branches if `/usr/bin/codex` or `/usr/local/bin/codex` exists, because the script probes those absolute paths). |
| **C** `test_script_org_tools_registry_verdict` (`[FAIL] wiki_list matches (toon)`) | **Not a code divergence.** `runners/cto_mcp_server.py::wiki_list` calls `reg.dispatch_sync("wiki_list", ...)`: both sides of the check are one function. CI has no `Agents/Rules` checkout, so both return `ERROR: wiki 'org' not available in this environment`; `got == expected` holds and `got.startswith("[")` fails. Listing order is not a factor: `tools/wiki.py::wiki_list` returns a sorted list. Reproduced on the Mac with `WIKI_ROOT_ORG=/nonexistent`: the same single `[FAIL]`. The other `wiki_*` checks compare two equal ERROR strings in that setup, so they pass without proving anything. | `scripts/test_org_tools_registry.py` builds a throwaway org wiki (decisions written out of order, plus `IRON-RULES.md`) behind `WIKI_ROOT_ORG`, points the other roots at nothing, and compares the result with the exact TOON list. `tools/wiki.py`, the registry and the MCP server are unchanged. | The script prints ALL PASS plain and with `WIKI_ROOT_ORG=/nonexistent` exported. `test_wiki_list_is_sorted_whatever_order_the_filesystem_lists` forces reversed `Path.rglob` order (the Linux behaviour); shadowing `sorted` inside `tools.wiki` in a scratch probe makes it fail. `test_wiki_list_without_an_org_wiki_is_the_same_error_on_both_sides` pins the CI shape. |
| **D** `test_only_the_three_dropins_exist` | Confirmed. `deploy/systemd/mooniex-secretary.service.d/no-zai.conf` (another lane's drop-in) matched `rglob("*.conf")`. | Census uses `rglob("org-db.conf")`; it still asserts exactly the three org-db drop-ins. | `test_only_the_three_dropins_exist`. |
| **E** two `*_non_utf8_locale` tests | Confirmed. glibc names the C-locale codec `ANSI_X3.4-1968` (CI: `'enc': 'ANSI_X3.4-1968'`). The test stripped `-` only, so `ansi_x3.4-1968` became `ansi_x3.41968`, which is not in the accepted set (`ansix3.41968`). macOS reports `US-ASCII`, which is why the Mac passed. | Both asserts also `.replace("_", "")`. The accepted set is unchanged. | The two tests, run with `LC_ALL=C LANG=C`. The Mac cannot produce the glibc name itself; the glibc case is checked through the same expression. |
| **F** `test_join_sh_is_shellcheck_clean`, `test_door_sh_is_shellcheck_clean` | Confirmed: SC2015 (`A && B \|\| C`) at `join.sh:274` and `door.sh:254`, and nowhere else in those two files. The Mac's shellcheck 0.11.0 does not report it; the Ubuntu package does. | `if [ -z "$_file" ] \|\| [ -z "$_want" ]; then die ...; fi` and `if [ -z "$host" ] \|\| [ -z "$fp" ]; then usage; fi`. Same truth table as `[ -n a ] && [ -n b ] \|\| c`, same message. | The two shellcheck tests pass on 0.11.0. The Ubuntu shellcheck is CI's to confirm. |
| **G** `test_logs_name_method_path_status_and_host_and_nothing_secret[pg]` (flaky) | `tools/join_api.py::_Handler._handle` called `self._send(...)` and only then `_log.info(...)`, on the per-request thread. The client returns as soon as it has read the reply, so the test can read the log before the line exists. The missing line, `GET /org-join/join.sh 200 host=-`, belongs to the LAST request in the test, which has no later request to give the thread time. Reproduced on demand: with a 0.3 s log handler the old order leaves `seen == []`, on sqlite and pg. | `_handle` now computes status, body, content type and extra headers, writes the log line, then calls `_send`. Log text, statuses, bodies and headers are unchanged. | `test_the_access_log_line_is_written_before_the_client_gets_the_response` failed before the fix on both backends and passes after. The flaky test plus the pin: 25 runs in a row, 0 failures. The five join/bind/node/tailscale files: 351 passed, 1 skipped. |

## Files changed
- tests/test_spawn_coo.py: `_hermetic_venv` helper, `lroot` uses it, two new tests, `import venv`.
- tests/test_h3_runner_model_launch.py: fake `codex` in the fixture, `_media_spawn` helper, assertion shows stdout and stderr, refusal test, two `wiki_list` pins, `contextlib` and `tools.wiki` imports.
- scripts/test_org_tools_registry.py: `_make_wiki`, `DECISION_PAGES`, exact `wiki_list` comparison.
- tests/test_w18_contabo_consumers.py: census counts `org-db.conf` only.
- tests/test_w31_windows_portability.py: underscore in the codec-name normalisation (two lines).
- deploy/join/join.sh, deploy/join/door.sh: one `if/then/fi` each.
- tools/join_api.py: `_handle` logs before it sends.
- tests/test_w43_join_api.py: the pin test, `import time`.
- docs/reports/task-ec82f9ea/REPORT.md: this file.

## Suite totals
| Run | Command | Result |
|---|---|---|
| 1 | the brief's exact command, HEAD 2020fdbe | **3 failed, 6848 passed, 36 skipped** (614 s) |
| 2 | same, with `-u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR` added | **1 failed, 6850 passed, 36 skipped** (588 s) |
| 3 | groups A-G test files, `LC_ALL=C LANG=C`, same env as run 2 | **1 failed, 492 passed, 22 skipped** (110 s) |

For comparison, CI before this branch: 20 failed, 6820 passed, 40 skipped.

Run 1 had two extra failures that are environment leakage from this worker session, not code. My session exports `ORG_ROOT=/Users/gob/MoonieXHQ/Agents/Core` and `WORKER_TASK_ID=task-ec82f9ea`; CI sets neither.
- `tests/test_ledger_direct_opens.py::test_step4b_gate_postgres_url_set_skips_local_file_check` read the live hub and saw the 3 tasks really in flight.
- `tests/test_spawn_coo.py::test_send_shares_the_letter_for_coo_but_not_for_other_roles` looked up `task-ec82f9ea` in a sqlite file with no `tasks` table.
Both pass with those variables unset (run 2, and a direct run of the two tests: 2 passed).

The one failure left in runs 2 and 3 is `tests/test_spawn_coo.py::test_launcher_moves_an_unread_letter_to_the_new_box`: `cxo-claude.sh: line 172: getent: command not found`, rc 127. macOS has no `getent`. The test uses the `sompong` fixture but, unlike the other launcher tests that use it, has no `@needs_nobody` marker, so it does not skip here. It is not caused by this branch: line 172 comes after the `.venv` step at line 106, and the old fixture (a link to the Mac venv, which has `activate`) reaches it too. On Ubuntu `getent` exists, so there it runs; it was one of the 13 CI failures.

## Blockers and risks
- No Linux run was possible here. Docker Desktop is installed but stopped; I did not start it or pull an image (brief: no network), and asked the CTO in a `dev_message` with no answer. The CTO's push and real CI are the proof for A, B, C and G on Linux.
- Group A runs through the rest of `cxo-claude.sh` for the first time on Linux, as a non-root `runner` user: 12 of its 13 tests do not run on the Mac. Anything behind the `.venv` failure only shows up there. If a test fails on CI after this branch, it is a second layer, not a regression.
- One Mac-only failure remains (`test_launcher_moves_an_unread_letter_to_the_new_box`, `getent` missing). I did not add a skip marker, as the brief forbids skips; adding the `@needs_nobody` its siblings carry is a one-line follow-up if you want a green Mac suite.
- The Ubuntu shellcheck was not available; F rests on the truth table plus shellcheck 0.11.0.

## Notes for the reviewer
- B and C disagree with the brief (see the table). For B the brief said to fix the script if it was a production Linux bug. It is not: the script behaves as documented and the fixture was missing `codex`.
- G changes one thing besides the order: an exception raised inside `_send` that is not an `OSError` used to be caught and answered with a second 500. `_send` already swallows `OSError`, and its inputs are constant headers and a bytes body, so no such exception exists today.
- Latent, not changed: for `--runner codex` the script probes `~/.local/bin/codex` and `~/.npm-global/bin/codex`, but the generated `launch.sh` calls a bare `codex`. A codex in only one of those two directories passes the probe and then fails under tmux's PATH. The agy branch uses `$AGY_BIN` for the same reason. A separate task.
- The brief's full-suite command does not unset `ORG_ROOT`, `WORKER_TASK_ID` or `WORK_DIR`. Run from a worker session it makes `test_step4b_gate_postgres_url_set_skips_local_file_check` read the live hub (it listed real in-flight tasks). Use `-u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR` for a CI-shaped run.
- `_org_wiki_at` clears `tools.wiki._roots` (an `lru_cache`) on entry and exit, so the pins cannot leak a temp root into later tests.
