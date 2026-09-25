You are working inside a checkout of the `mooniex-agents` repo (a Python orchestration
meta-repo). This is a **read-only reconnaissance job**: answer the 10 questions below using
the shell. Do not edit, create, or delete any file. Do not use git to change branches or
state; only read commands (`git log`, `git show`) are needed.

Answer each question, showing your work, then finish your final message with **exactly one
line** containing a single JSON object with these keys and nothing else on that line:

```
{"q1_pytest_passed": <int>, "q1_pytest_failed": <int>, "q1_pytest_skipped": <int>, "q2_skill_commits": <int>, "q3_largest_tools_files": [["<path>", <bytes>], ...5 pairs largest first...], "q4_scripts_py_count": <int>, "q5_lib_py_count": <int>, "q6_tools_def_main_count": <int>, "q7_scripts_lsR_dir_count": <int>, "q8_head_stat": {"files_changed": <int>, "insertions": <int>, "deletions": <int>}, "q9_token_profile_lines": <int>, "q10_tools_import_argparse_count": <int>}
```

## Questions

1. **Tests.** Run `.venv/bin/python -m pytest tests/test_restore_scripts.py -q` (use the repo
   root's `.venv`; if that path doesn't exist in this checkout, use whatever `python3` with
   `pytest` installed is on PATH). Report how many tests passed, failed, and were skipped.

2. **Commit style.** Run `git log --oneline -30`. Of those 30 subject lines, how many start
   with `skill(` (immediately after the short hash + space, e.g. `skill(gdrive-filing): ...`)?

3. **Biggest tool scripts.** Under `tools/` (not recursing into any `__pycache__` directory),
   find the 5 largest files by byte size. Report each as `[path, bytes]`, largest first, path
   relative to the repo root (e.g. `tools/delegate.py`).

4. **Scripts inventory.** How many `.py` files exist under `scripts/`, counting recursively
   into every subdirectory?

5. **Lib inventory.** How many `.py` files exist under `lib/`, counting recursively?

6. **Entry points.** How many `.py` files directly under `tools/` (not subdirectories) contain
   a line that starts with `def main(`?

7. **Directory shape.** Run `ls -R scripts` and count how many lines end in `:` (each such line
   is a directory header — the root `scripts` listing itself does not print its own header).
   How many directory headers are printed in total (including nested ones)?

8. **Latest commit.** Run `git show --stat HEAD` (this checkout's HEAD, i.e. the fixture
   commit). Report the file-changed/insertions/deletions summary line as three integers
   (a stat with no deletions means deletions = 0).

9. **File size.** Run `wc -l tools/token_profile.py`. How many lines does it report?

10. **Import style.** How many `.py` files directly under `tools/` (not subdirectories, not
    `__pycache__`) contain a line that starts with `import argparse`?

Work through the questions in order, run the actual commands (don't guess), then print the
final JSON object as the very last line of your response.
