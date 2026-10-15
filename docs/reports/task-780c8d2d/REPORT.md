# task-780c8d2d — path owners (iteration 1)

Map of which Project Head owns which paths in Agents-Core, a CLI that checks a PR against it, and the
Project Head branch of `check_collisions`. Iteration 1 moved the org-wide launchers and the watchdog to `shared`.

## Files
- `config/path-owners.yaml` — globs per project (OrgRestructure, SpendGuard, CookieRun, BlackLiquidity, MimiPage) and `shared`.
- `lib/path_owners.py` — `owners_for`, `foreign_paths`, `load_table`, `projects`. fnmatch, longest glob wins.
- `tools/pr_owner_check.py` — `<PR#> | --files f1,f2` with `--project`. Exit 0 clean, 1 foreign path, 2 could not check.
- `lib/org_tools_registry.py` — `check_collisions`: a Project Head (`ORG_PH_PROJECT` set) gets `{conflicts, path_owner}`; everyone else the bare list.
- `roles/project_head.md` — one line: run `tools/pr_owner_check.py` before merging.
- `tests/test_path_owners.py` — 63 tests.

## Tests (after merging origin/main 2df03000)
- `pytest -q -o addopts='' -p no:warnings tests/test_path_owners.py` — 63 passed.
- `pytest -q -o addopts='' -p no:warnings tests/ -k "path_owner or collision or org_tools"` — 74 passed, 1 failed, 8436 deselected.
  The 1 failure, `tests/test_h3_runner_model_launch.py::test_script_org_tools_registry_verdict`, is not from this change: it fails the same way
  with `lib/org_tools_registry.py` at HEAD ("tests must not touch a real checkout's tasks.db", ADR 0021), and
  `python scripts/test_org_tools_registry.py` run directly exits 0.
- The 4 tests changed for the ownership move fail against the previous `config/path-owners.yaml` and pass against this one.

## PR 327, `--project OrgRestructure`
```
$ python tools/pr_owner_check.py 327 --project OrgRestructure
SHARED   config/hosts.yaml  shared, tell CTO Main
SHARED   lib/config.py  shared, tell CTO Main
SHARED   scripts/cto-claude.sh  shared, tell CTO Main
SHARED   scripts/cxo-claude.sh  shared, tell CTO Main
SHARED   scripts/spawn-cto.sh  shared, tell CTO Main
SHARED   scripts/spawn-cxo.sh  shared, tell CTO Main
SHARED   scripts/tab-title.sh  shared, tell CTO Main
SHARED   tools/delegate.py  shared, tell CTO Main
pr_owner_check: OrgRestructure: 15 path(s), 0 foreign, 8 shared      <- stderr
exit 0
```
Another project (`--project SpendGuard`) gets one `FOREIGN` line, `tests/test_terminal_window.py` owned by OrgRestructure, and the same 8 `SHARED` lines; exit 1.

## Decisions that stand
PH-only shape of `check_collisions`; a shared path prints but exits 0; `gh pr view` capped at 100 files is re-read through
the paginated API (checked live on PR 286: 172 files); no entry for CooGate.
