# REPORT task-f3f80ab6

## Files Changed

- `config/projects.yaml`: Added `jules_repo: PASAKON/Agents-Core` to the `mooniex-agents` project entry with explanatory comment regarding the GitHub repo rename. No other projects touched.
- `config/plans.yaml`: Added top-level `pressure_rule: true` with comment citing IRON §59 rule 7 / Q-20261013-1745-f56c.
- `tools/forecast.py`:
  - Added new shell patterns to `SHELL_PATTERNS`: `"infisical run"`, `"org-python.sh"`, `"with-org-db-env.sh"`, `"git fetch"`, `"git pull"`, `"git merge"`, `"git rebase"`, `"git cherry-pick"`, `"git archive"`, `"git checkout -b"`, `"git worktree"`.
  - Added `PYTHON_COMMAND` regex matching Python script executions, `-c`, and `-m` with non-pytest modules.
  - Updated `needs_shell()` docstring documenting pytest and read-only git exemption, and integrated `PYTHON_COMMAND` check.
- `tools/route.py`:
  - Defined closed `REASON_CODES = ("review", "security", "silent-wrong", "claude-tool", "ceo-order", "ab-test", "box-bound", "quota-handoff")`.
  - Added `load_jules_config()` for safely loading `config/jules.yaml`.
  - Added `reason_code(description)` reading description header (up to 5 lines before blank line), extracting first token with delimiters `[\s:;,.()—–]+` (preserving hyphens), and checking against `REASON_CODES`.
  - Updated `_IRON_59_MSG` and `check_override()` with closed reason codes, invalid token notice (`"<token>" is not a reason code.`), codex hand pin detection (runner "codex" with empty model and no `"router:"` in `delegate_log`), and the Jules dispatch hint line for size S/M non-sensitive tasks on allowlisted repos.
  - Implemented the router pressure rule inside `plan()`: scales outside candidate reserve percentages by Claude weekly remaining (`cw`), appends `pressure: claude <cw*100:.0f>% left, reserve <orig>%→<eff>%` to `why`, and orders ok outside plans before ok Claude plans when `pressure_rule` is active (enabled by default or when absent, bypassed when `false`).
- `tests/test_route_override.py`:
  - Updated v1 tests affected by closed reason codes and codex hand pin detection.
  - Added test cases covering all 8 reason codes, refusal formatting, line 6 / post-blank-line override invalidation, codex hand pin handling, Jules hint presence/absence, and `reason_code()` unit tests.
- `tests/test_forecast.py`:
  - Added `test_needs_shell_markers_v2` testing the new shell commands, python invocations, and non-shell commands.
- `tests/test_route_plan.py`:
  - Updated v1 assertions affected by pressure reserve scaling.
  - Added 4 new tests: Pressure case 1, Pressure case 2, `pressure_rule: false` fallback to old order, and Claude quota unknown behavior.

## Tests Added or Changed

### `tests/test_route_override.py`
- **Updated v1 tests**:
  - `test_runner_set_with_override_line_returns_none`: v1 had `"override: CEO order"`; in v2 `"CEO"` is not a valid reason code, updated to `"override: ceo-order — CEO order"`.
  - `test_override_line_case_and_space_insensitive`: v1 had `"Override:   A/B test"`; in v2 `"A/B"` is not a valid reason code, updated to `"Override:   ab-test"`.
  - `test_router_written_codex_row_with_empty_model_returns_none`: in v2, a codex row with empty `runner_model` is treated as a hand pin unless `delegate_log` contains `"router:"`; added `delegate_log="router: codex"`.
- **Added tests**:
  - `test_all_8_codes_pass`: verifies each of the 8 codes in `REASON_CODES` passes, including punctuation (`override: ceo-order — CEO said X`) and uppercase (`override: Review`).
  - `test_refused_override_cases`: verifies refusal for `override: in-session Agent`, `override: runner=claude` (including `"<token>" is not a reason code.`), and verifies override directives on line 6 or after the first blank line are ignored.
  - `test_codex_hand_pin`: verifies codex rows with empty model and no `"router:"` in `delegate_log` are refused, while rows with `"router: codex"` are permitted.
  - `test_jules_hint`: verifies the Jules hint line is appended for size S tasks on `mooniex-agents` with allowlisted repos, and omitted when description mentions `"deploy"` or size is L.
  - `test_reason_code_unit`: unit test suite for `reason_code()`.

### `tests/test_forecast.py`
- **Added test**:
  - `test_needs_shell_markers_v2`: verifies True for `"bash scripts/hub/org-python.sh tools/x.py"`, `"infisical run -- python tools/a.py"`, `"python tools/tool_value.py report"`, `".venv/bin/python -c 'print(1)'"`, `"git fetch origin x && git merge origin/x"`; and False for `"python -m pytest tests/test_x.py"`, `"run pytest"`, `"git log -1"`, `"git diff main"`, `"make sure it works"`.

### `tests/test_route_plan.py`
- **Updated v1 tests**:
  - `test_plan_claude_will_hit_5h_and_agy_ok`: updated `p_agy.why` and `agy_line` assertions to expect pressure scaling (`reserve 6.7% ok, pressure: claude 67% left, reserve 10%→6.7%`) because claude quota (67% remaining) scales outside reserve from 10% to 6.7%.
  - `test_pick_runner_fallback_when_all_will_hit`: adjusted agy-gemini weekly_remaining from 0.06 to 0.05 so after (0.04) remains below scaled reserve (5.0%), preserving the test's intent to test fallback when all candidates will hit.
  - `test_cli_plan`: updated expected output substring for agy from `"reserve 10% ok"` to `"reserve 6.7% ok"`.
- **Added tests**:
  - `test_pressure_case_1_codex_picked_on_dev_shell`: verifies task-88e23258 scenario (claude 0.86, codex 0.69, size L shell job) picks codex over claude.
  - `test_pressure_case_2_codex_will_hit_vs_ok_based_on_claude`: verifies codex 0.25 left with cost 8% results in `will_hit` when claude is 1.0 (claude picked) and `ok` when claude is 0.5 (codex picked).
  - `test_pressure_rule_false_gives_old_order`: verifies `pressure_rule: false` preserves prior ranking where claude is picked ahead of codex purely on headroom.
  - `test_pressure_rule_claude_quota_unknown_no_scaling`: verifies outside reserves are not scaled when Claude quota is unreadable or unknown.

## Validation Performed

In accordance with the AGY remote worker contract ("File-only job: edit files and run nothing. The reviewer (CTO dd03bac1) runs every test."), file-only edits were made and all regexes, parsing rules, and router logic were verified against the specifications and test suites by static analysis.

## Limitations

None. All requirements in the brief were implemented as written.

## Blockers

None.

## Skill learning

- (none)
