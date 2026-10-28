# task-d79aa2c7 — HQSecurity M3: leak guards (order O-20261027-1347-4e62)

Branch `agent/developer-task-d79aa2c7` (not `hqsec/m3-leak-guards`: the worktree's branch is the one
the CTO assigned). Nothing was pushed and no PR was opened from here (worker rule 2).

## What was built

| File | What |
|---|---|
| `scripts/security/leak-guards.sh` | `--check <root>...` (read-only, one line per repo, exit 1 if any repo lacks a guard) and `--install <root>...` (idempotent, chains, respects `core.hooksPath`). Extras: `--install --dry-run`, `--skip NAME`; skips repos another account can write (`skipped-not-owned`). |
| `scripts/security/github-scan-report.sh` | Read-only. Visibility + secret scanning + push protection for every repo of an owner; prints (never runs) the `gh api -X PATCH` line for each PUBLIC, non-archived repo where either is off. |
| `scripts/install-git-hooks.sh` | 4 lines: if `pre-commit` is a leak-guards wrapper, write its stanzas to `pre-commit.local` (otherwise they land after the wrapper's `exit`: dead code). |
| `tests/test_leak_guards.py`, `tests/test_github_scan_report.py` | 26 tests. |

Codex's branch `agent/codex-task-8710a1c5` was identical to `main` (tip `94aa1271`): there was no partial work to keep.
`tests/test_install_git_hooks_gitleaks.py` named in the brief does not exist; the real file is
`scripts/test_install_git_hooks_gitleaks.py` (untouched, still passes).

### How the hooks behave
- **pre-commit**: `gitleaks git --staged --redact --no-banner` (8.19+) or `gitleaks protect --staged ...` (older), picked at run time from `gitleaks version`.
- **pre-push**: per pushed ref, `gitleaks git --log-opts "<remote_sha>..<local_sha>"`. New branch, or a remote sha this clone does not have: `<local_sha> --not --remotes=<remote>` (commits not on the remote being pushed to; every remote when `$1` is a URL). Deleting a ref scans nothing.
- **Chain**: an existing hook is renamed `<hook>.local`; the new hook runs it first with the same arguments and the same stdin (buffered in a temp file) and stops on its non-zero exit. If `<hook>.local` already exists the installer refuses and touches neither file.
- **Already guarded**: a pre-commit that already runs gitleaks (`install-git-hooks.sh`'s) is kept as is, reported `kept-already-guarded`.
- **Missing gitleaks**: the hook warns on every commit/push and lets it through (same as `install-git-hooks.sh`); `--check`/`--install` then exit 2 (`ALLOW_NO_GITLEAKS=1` accepts it). A guard that skips silently is the bug that bit Contabo on 2026-10-12.
- **Repo discovery**: `.git` dirs under the roots; `node_modules`, `.venv`, `worktrees` never entered; a linked worktree is not a repo of its own; a symlink is followed one step only (see Skill learning: `find -L` walked `wineprefix/.../z: -> /`).

## Contabo: exact commands (run as root; hooks dirs are root's)
After this branch is merged, from the Agents-Core main checkout:

```
# 1. preview, writes nothing
bash /opt/MoonieXHQ/Agents/Core/scripts/security/leak-guards.sh --install --dry-run --skip Archive /opt/MoonieXHQ
# 2. install
bash /opt/MoonieXHQ/Agents/Core/scripts/security/leak-guards.sh --install --skip Archive /opt/MoonieXHQ
# 3. prove
bash /opt/MoonieXHQ/Agents/Core/scripts/security/leak-guards.sh --check --skip Archive /opt/MoonieXHQ
```
**Expect exit 1 from steps 2 and 3, on purpose:** `Projects/MoonieX/SomPong/.git` is owned by `sompong` (uid 994), so as root the installer skips it (`skipped-not-owned`, nothing written or read-run there) and an install that skipped a repo is not a clean exit. Expected: 14 repos installed or kept, `skipped-not-owned=1`. After step 2, step 3 should read `repos=15 without-guard=1 skipped-not-owned=1`. SomPong needs its own install **run as that user** (COO lane), e.g. `sudo -u sompong bash /opt/MoonieXHQ/Agents/Core/scripts/security/leak-guards.sh --install /opt/MoonieXHQ/Projects/MoonieX/SomPong` (not run by me; needs that account to be able to read the script). `--skip SomPong` makes the root run exit clean but hides the gap from `--check` too.
`/root/projects` needs no run of its own: its 5 entries are symlinks into `/opt/MoonieXHQ/Projects/MoonieX/`, and the 2 that are repos (ClaudeFlow, Option) are already covered. Dropping `--skip Archive` adds the 2 archived repos (`Archive/LLMs.stale-20260803`, `Archive/mooniex-vps/.../option`).

## Read-only `--check` on the real machine (no hook was installed anywhere)
- `/opt/MoonieXHQ`: **17 repos, 0 errors, 0 with `core.hooksPath`, gitleaks found.** pre-commit guard: 1 of 17 (`Agents/Core`). pre-push guard: 0 of 17. 17 of 17 lack a full guard. (15 repos with `--skip Archive`.) Took 4.5 s.
- `/root/projects`: 2 repos (both also under `/opt/MoonieXHQ`), neither guarded.
- `--install --dry-run` over both roots: `Agents/Core` pre-commit `kept-already-guarded`, pre-push `would-be-chained` (its a60f1744 hook is plain sh, reads stdin, exit 0: runs fine as `pre-push.local`); the other 16 `would-be-installed`. Hooks dirs verified unchanged afterwards.
- Not git repos on Contabo (plain directories, no `.git`): `Projects/MoonieX/AlphaTrader`, `LineAutomation`, `LinePoster`. Nothing to guard there; they are also not covered by any push protection. `ComfyRunpod-wt-foreignsafe` is a linked worktree (shares ComfyRunpod's hooks).

## `github-scan-report.sh` output (live, GET only)
50 repos under PASAKON: **15 PUBLIC, all `secret_scanning=enabled` and `push_protection=enabled`; 35 PRIVATE, both columns `unknown`** (the API returns no `security_and_analysis` for them). 0 PATCH lines printed, as the PH already enabled Agents-Core and Agents-Rules.

## Winbox / Mac
No PowerShell twin. Winbox docs show Git Bash in use there; Git for Windows ships `bash.exe` and its own `sh`, so `leak-guards.sh` should run unchanged under Git Bash (command in the script header) and the hooks run under Git's sh. **Not run on winbox or on a Mac.**

## Tests
`pytest tests/test_leak_guards.py tests/test_github_scan_report.py scripts/test_install_git_hooks_gitleaks.py scripts/test_install_git_hooks_media.py` → **43 passed, 0 failed, 0 skipped** (26 new, 17 existing installer tests). Added for the ownership rule: a 0777 hooks dir and a 0777 `.git` are skipped and left untouched (with a planted symlink beside them), an owner that is another existing account is skipped, an owner uid with no account is not. Mutation (`unsafe_path` always "safe") fails 3 of them.
Each of the five asked-for cases has a test (a planted key refused, clean allowed, existing pre-push still runs and still blocks, install twice changes nothing including mtimes, a range holding the key makes the hook exit non-zero), plus a real `git push` to a local bare remote, the Contabo held-commit hook chained, hooksPath, symlink hub/loop, linked worktree, hostile names (`my repo (ไทย) #1`), dry-run, usage errors, missing gitleaks.
Mutation checks (logic removed, tests must fail): chain call removed → 2 fail; pre-push result ignored → 2 fail; pre-commit result ignored → 1 fails; scan-report PATCH condition removed → 1 fails. All restored.
The planted key is `"ghp_" + two string parts`, assembled at runtime; the test sources scan clean.

## Not checked / risk
- **gitleaks version**: only 8.30.1 was run. The pre-8.19 branch (`protect`, `detect --log-opts=...`) is selected by a version `case` but never executed.
- **Real-gitleaks tests skip where gitleaks is absent** (the CI pytest job installs none): 4 of 26 tests skip there (plus 2 more that need root and a `nobody` account), so CI green does not re-prove the key-refusal cases or the foreign-owner cases; they were run here (root, gitleaks 8.30.1, 0 skipped).
- **SomPong is skipped and needs its own install as its owner** (COO lane), see the commands section. Reported by `--check` as `skipped-not-owned`.
- **Ownership rule (PH review, §2b).** A repo is skipped, before git reads its config, when `.git`, the git dir or the hooks dir is owned by a real account that is neither root nor the user running the script, or is group/other-writable (`mode & 022`); an owner uid with no account (the Mac's 501 on ClaudeFlow, Console, Option, LungNote/Mcp) counts as safe. **Deviation from the PH's wording:** "an existing account that is not root" would also skip every repo when a non-root user runs the script (CI, Mac, winbox), so "the user running it" is exempt too. Group-writable repos (`core.sharedRepository=group`, 2775) are skipped for everyone. On Windows (Git Bash) the stat owner and mode are NTFS pseudo-values: untested there. `put_file` also writes through `mktemp` (random exclusive name, `mv -f` replaces the hook itself), which closes the planted-symlink write on its own; that part is covered only through the skip tests, not by a direct test.
- **Working-tree root not checked**: the skip judges `.git`, the git dir and the hooks dir, not the repo root. A repo whose root another account owns while `.git` is root's could have `.git` swapped between the check and the write. None on Contabo today (every repo root and its `.git` share an owner, checked 27 Oct 16:08 TH).
- **Hooks fail open when gitleaks is missing** (loud warning, commit/push goes through); `--check` and `--install` exit 2 so it shows, but nothing stops it at commit time.
- **`--no-verify` bypasses both hooks.** The only server-side guard is GitHub push protection: on for all 15 public repos, but the 35 private repos read `unknown`, and the 3 non-repo dirs above have no remote at all.
- **`--check` is textual**: a hook counts as a guard if it is executable and has the marker or a non-comment `gitleaks (protect|git|detect)` line. A hook that runs gitleaks and ignores the result (`|| true`) counts as guarded.
- **`core.hooksPath`**: 0 repos on Contabo set one, so that path ran only in temp repos. A hooksPath inside the work tree (e.g. a tracked `.githooks/`) would make `--install` modify tracked files; a hooksPath shared by many repos gets one wrapper for all. Winbox and Mac were not checked.
- **First push after install can block on old history**: a new-branch push scans every unpushed commit, so a repo whose history holds a finding gets blocked until its fingerprint is in `.gitleaksignore`. A read-only `gitleaks git --redact` history count over the 15 real repos (`--skip Archive`): **11 clean, 3 with findings, 1 not counted.** 0 findings: `/opt/MoonieXHQ`, `Agents/Memory`, `Agents/Rules`, `Agents/Wikis`, `Chatudo/Webapp`, `LungNote/Mcp`, `ClaudeFlow`, `ComfyRunpod`, `ExpertAdvisor`, `Option`, `SomPong`. Findings: `Agents/Core` 2, `MoonieX/Console` 7, `MoonieX/Scriptable` 1 (file:line kept off-repo, contabo:/root/hqsecurity). **`MoonieX/Bedrock` timed out at 150 s: no count.** A push of commits already on the remote is not rescanned (`--not --remotes=<remote>`), so these only bite a first push of a never-pushed clone. I did not check whether the Console and Scriptable findings are real secrets or fixtures, or whether those commits are on origin.
- **Pre-existing, not mine**: `gitleaks dir .` on this worktree also flags 2 lines in 2 tracked test files on main (generic-api-key, outside this diff; file:line kept off-repo). If main's CI gitleaks job is red, that is why.
- macOS bash 3.2 / BSD `find` / `mktemp` were not run; the script avoids arrays under `set -u`, `sed -i`, `readlink -f`, `date -d`, `timeout`, but that is reading, not running.
- Paths containing a newline are unsupported (the repo list is line-based after the NUL-separated `find`).
