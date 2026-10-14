# Round 6 review — Console #33 / Agents-Core #307

Reviewed Console `d9e0c46068738340dbe311f5d975f3588a264731` (cached `origin/feat/run-spend-label-r6`) and Agents-Core `8effad557e8a8f72180cc7809a930d97aaf4ef45`. File references below are relative to the named repository at those commits. No application code was changed.

## BLOCKING — The current allowlist blesses historical, uncapped implementations

**Console `src/run/script.js:173`**, `src/run/script.js:175`, `src/run/routes.js:79`; related Core `config/spend-tools.txt:4`.

Inputs → wrong result: commit A contains `tools/pay.py` that ignores argv and spends without a cap. Commit B on main fixes that tool to enforce `--max-usd` and adds `tools/pay.py --max-usd` to the allowlist. A worker submits a script card pinned to A with args `["--max-usd", "1"]` and a matching spend label under enforce. A is an ancestor of B, and the path is listed at B, so the old uncapped implementation is accepted with `cap_checked: true`.

Reproduced with a local bare origin, two commits, and the actual creation route handler, using an in-memory database instead of an HTTP socket: response **201**, persisted spend JSON **`cap_checked: true`**. Running A with the accepted args printed `SIMULATED_SPEND=100; cap ignored`. The fixed B implementation was never selected. No real spend occurred. Core's initially empty list prevents this today, but the first reviewed entry enables the bypass for that path's old history.

**Smallest fix:** conservatively require the requested full commit to equal the main tip whose allowlist is read. To support historical versions, make entries authorize explicit reviewed commit/tree identities, including dependencies; ancestry and a pathname alone are insufficient.

**Missing test:** old uncapped A → reviewed capped B plus allowlist → request A must be refused. The existing positive fixture uses a script that only prints its argv, and never distinguishes old and reviewed implementations.

## BLOCKING — Archived Python dependencies can execute mutable files outside the pinned tree

**Console `src/run/script.js:201`**, `src/run/script.js:203`, `src/run/executor.js:134`, `src/run/executor.js:170`.

Inputs → wrong result: a pushed commit contains regular `tools/entry.py` importing `tools.helper`, plus `tools/helper.py` as an absolute symlink to a writable Python file outside the repository. The regular-file check validates only the entry script. `git archive` preserves the helper symlink, extraction succeeds, and the executor adds that tree to `PYTHONPATH`. Changing the external file after pinning changes the code executed without changing the commit or entry-script hash. This also creates a check/use race: external module bytes remain mutable until Python opens them.

Reproduced with the actual `fetchScriptBytes` and `unpackCodeTree`: both returned success. Changed the external helper from `NAME="UNPINNED_V1"` to `NAME="UNPINNED_V2"`, then invoked Python with the executor's tree/PYTHONPATH arrangement. Output was **`UNPINNED_V2`**. Directly requesting the same symlink as the entry script correctly returned `E_SCRIPT_NOT_A_FILE`; dependency extraction bypasses that protection. Execution is as the service user, and the checked-in unit specifies `User=root` (`deploy/mooniex-console.service:38`). Operator approval is still required; the failure is approval no longer binding the executed code to the selected commit.

**Smallest fix:** reject symlink entries in the exported code tree before extraction and fail the run closed. If symlinks must be supported, resolve them strictly within the selected Git tree and materialize verified regular blobs. Also fail closed when tree preparation fails instead of falling back to a different import environment (`executor.js:134`).

**Missing tests:** absolute and escaping relative helper symlinks, external target changes between creation and execution, and tree-extraction failure. Also cover archive attributes: a separate probe showed `tools/helper.py export-ignore` produces a successful extraction without that dependency.

## LOW — Shell quoting bypasses the new no_spend/cap-flag refusal

**Console `src/run/spend.js:232`** (raw-text matching at `src/run/spend.js:223`).

Inputs → wrong result: under enforce, submit a command card as an authorized command requester with `command='python3 tools/pay.py --max-""usd 1'` and `no_spend='read only'`. Bash passes `--max-usd` to Python, but the raw command does not contain the regex's literal spelling. The new refusal is skipped and the card is classified as no-spend instead of requiring a spend label. This needs command-card authority; it is not a worker privilege escalation.

Reproduced: the application's `simpleWords` returned `["python3","tools/pay.py","--max-usd","1"]`, while `checkSpend` returned `{spend:{kind:"no_spend",reason:"read only",matched:[]}}` with no error.

**Smallest fix:** check normalized argument tokens for simple commands, and actual argv for script cards, before accepting `no_spend`; under enforce, refuse an unparseable command if this guarantee must hold. Do not rely solely on a substring regex.

**Missing tests:** adjacent quoted fragments such as `--max-""usd` and `--max-'credits'`, including forms with `=value`.

## Remaining claims and validation

- **L1:** a disposable remote branch was deleted while a forged local tracking ref still contained its commit. `fetchScriptBytes` refused it with `E_SCRIPT_NOT_PUSHED`.
- **L2:** the direct symlink request was refused with `E_SCRIPT_NOT_A_FILE`; the dependency exception is the blocking finding above.
- **L3:** `cloneFor` returned null for inherited `constructor`, `toString`, `hasOwnProperty`, `valueOf`, and `__proto__`. No own-key bypass found.
- **L4:** interpreter selection maps js/mjs/cjs to Node. Python's import-tree guarantee fails as reproduced above. The existing real-process integration test could not complete in this sandbox.
- **L5/L7:** explicit-zone and `not_simple`/`not_bound` pure tests passed. No additional defect established.
- **Console tests:** ran `npm test -- --maxWorkers=2 --minWorkers=1 test/run-spend-tools.test.js test/run-spend.test.js test/run-spend-capflag.test.js test/run-spend-page.test.js`: **153 passed, 5 failed, 8 skipped**. Five API tests failed because listening returned `EPERM`; the spend-tools suite failed setup at `spawnSync git EPERM`, skipping its eight cases. These are environment limitations, not asserted product regressions. Direct async Git and route-handler probes above succeeded without listening sockets.
- **Core tests:** attempted the PR's `tests/test_ask_run_spend.py tests/test_ask_run.py` using the existing Core virtualenv. The combined run stalled at `test_org_spend_body_equals_the_cli_body`; a diagnostic rerun showed the wait in `asyncio.run(srv.mcp.call_tool(...))` at `tests/test_ask_run_spend.py:177` and hit a 120-second timeout. Rerunning with `-k 'not org'` yielded **198 passed, 54 setup errors** from denied fake-hub socket creation. Full claimed 265-pass validation was not reproduced.
- Tests and probes ran against extracted commit snapshots in the assigned worktree. No paid APIs, live services, production tmux panes, or external pushes were used. Entry arguments remain positional parameters in the executor; no new shell interpolation or log-secret leak was established in the changed lines. Additional missing race coverage: allowlist removal between creation and approval, and main changing between fetch and policy lookup.
- **Source limitation:** GitHub metadata confirmed the Core head above. Shell GitHub access failed and the connector returned 404 for Console #33, so its live head could not be verified; Console findings apply to the named cached Round 6 commit.

BLOCKING: yes
