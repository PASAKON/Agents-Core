# REPORT task-d9603926

## Summary
`tools/colab_batch.py` now runs a file-based Openjutsu take (`openjutsu_object`, `openjutsu_people`) so it can go on a labelled SCRIPT card: re-pinned to ComfyRunpod `c0eb0d9`, an explicit workflow-to-graph map, a snapshotted `source`, and a private 0700 temp dir under the take's parent (never `/tmp`). PR: https://github.com/PASAKON/Agents-Core/pull/596 (branch `kit/winbox/d9603926-colab-batch-openjutsu`; the host moved to winbox per the CTO feedback, and `<sid8>` is the task id).

## Files Changed
- tools/colab_batch.py — `PINNED_FROM` c0eb0d94756fa2952114efcf4da127b85870e349; all `PINNED` hashes regenerated from the git objects there; adds `third_party/openjutsu/object.api.json` and `simple.api.json`; `OPENJUTSU` map (workflow to graph) used by the workflow check; Openjutsu takes must be gpu G4 + `fallback_gpus: []`; `source` (top level and per scene) read at load, hashed, snapshotted like `refs`, files named `ref_N` / `src_N`; `snapshot_ready` re-hashes every snapshot file right before each attempt (exit 6, take not started); a take's snapshot is deleted when the take is done; `pinned_tree(source, parent)` puts tree and data in a 0700 `.colab-batch-*` dir under the first take's parent, data beside the tree (run_take refuses a people file or `--out` inside its ROOT); docstring (exit 6, snapshots, Audit scope).
- tests/test_colab_batch.py — `invoke` also checks the temp dir is gone and takes `on_spec`; 55 new test cases (181 now, 126 before; see Tests); imports `ast`, `os`, `re`.
- REPORT.md — this file (last commit, for the hub poller; drop it on merge).

## Commits
- 820f2cc2 — colab_batch: run Openjutsu file takes (re-pin ComfyRunpod c0eb0d9, pinned graphs, source snapshot, private temp dir)
- ad9987b3 — colab_batch: Openjutsu takes G4-only, snapshot hashed at load and re-hashed per attempt, neutral names, per-take cleanup
- (REPORT.md commit follows these on the branch)

## Tests
- ran (winbox, Windows, Python 3.11 in a scratch venv with pytest + a local-only POSIX shim for dir mode / O_NOFOLLOW / killpg and a stub `fcntl`; not committed): `python -m pytest tests/test_colab_batch.py -p winposix --tb=no` with `COMFYRUNPOD_CLONE` pointing at a read-only clone
- passed: 175
- failed: 6 (all `symlink_to` tests: Windows has no symlink privilege here; the same 6 fail on unchanged `main` with the same shim, 120 passed there)
- skipped: 0 with the clone; the 2 pin-vs-git tests skip without one (CI has none)
- unmodified `main` without the shim: 30 of 126 fail on Windows (mode 0700, `O_NOFOLLOW`, symlinks, `killpg`), so the Linux CI run on the PR is the real gate.
- The new tests against the old tool code (base): 57 of 181 fail, 124 pass (the new `invoke` assertion that the temp dir is gone fails every test on base; the rest are the behaviours above). The tests that pass on base are refusals that base also makes (an unpinned workflow is refused there too), kept as regression guards.

## Issues / Blockers
- The auto-mode classifier refused me executing the cloned ComfyRunpod `run_take.py` (`--dry-run` of the new layout). I did not retry. Pin completeness was checked statically instead (AST import scan of every pinned file at c0eb0d9: no unpinned local module; only third-party `huggingface_hub`, `websocket`, `nudenet`, unchanged from the old pin).
- `config/spend-tools.txt` is untouched: the task text says not to touch it, and the later "now allowed" came only from a peer message, not the hub mailbox. Proposed comment for the colab_batch entry, to apply on a CTO Main go: "the cap is the rate table x time (G4 8.9 CU/h); worst case, a card kill during `colab new` can leave an orphan VM that no guard stops; Studio and Openjutsu takes run on G4 only."
- No gitleaks on winbox; I ran a regex scan of the diff for key, token, private-key, email and user-path patterns: no hits.

## Notes for Reviewer
- Reach (listed before editing): `pinned_tree` is called by `execute` and 2 tests (the new `parent` argument is optional, `None` keeps the old /tmp behaviour for them); `snapshot_spec` / `snapshot_studio_spec` are called only by `execute` (first argument is now the data dir; both now return `(path, [(path, sha256)])`); `load_job`'s `assets` values are now `(suffix, bytes, sha256)` and are read only by `snapshot_spec`; exit 6 gained one more cause. Outside the tool: `config/spend-tools.txt` (unchanged) and the skill `CMO_Procedure_Colab_DirectRender` mention colab_batch. No caller of `child_env()` changed.
- The snapshot cannot live inside the pinned tree: run_take's ROOT is the pinned dir, and for `openjutsu_people` it refuses the photo or clip inside ROOT and `--out` inside ROOT. Layout is `<take parent>/.colab-batch-XXXX/{tree,data}`; `--out` stays `directory.parent`, an ancestor of the tree. `test_people_layout_meets_run_takes_private_file_rules` runs the real `run_take()` against a fake Popen and applies run_take's own `_inside()` rule to the argv and cwd it gets.
- With several takes in one job the temp dir sits under the FIRST take's parent (one pinned tree serves the job). Snapshot data of takes 2+ therefore may sit in a different folder than their originals, still under WORK.
- Hashes: 7 of the 22 entries changed or are new vs the old pin (run_take, remote_take, colabctl, guard, scan_frames, and the two graphs); the other 15 are unchanged. `OPENJUTSU_GRAPH_SHA256` / `OPENJUTSU_PEOPLE_GRAPH_SHA256` inside run_take equal the pinned graph hashes (a test checks it when a clone is present).
- Suggested check on Contabo, 0 CU: with a ComfyRunpod checkout at c0eb0d9, `COMFYRUNPOD_CLONE=<path> pytest tests/test_colab_batch.py` (runs the two pin tests), and a `run_take.py <spec> --dry-run` of a people spec built from the batch layout.

## Not checked / risk
- The real `run_take.py` at c0eb0d9 was never executed here (refused). The layout rule is tested against a copy of its `_inside()` check and by reading its code; a wrong guess there fails at 0 CU (spec error exit 2 from the child, before any VM), after the batch has admitted the take.
- Linux CI / Python 3.14 has not run on this branch yet when this was written; locally 6 symlink tests fail on Windows only. 
- A batch that is SIGKILLed or SIGTERMed (no `finally`) leaves the `.colab-batch-*` dir with the snapshot in WORK, mode 0700, same place as the originals. Not handled; the existing code has no signal handler either.
- A source is read fully into memory at load (no size cap); a multi-GB file would exhaust RAM. Not added: the brief did not ask and run_take expects a short part.
- The child's own temp use: for file-based takes run_take/remote_take create no temp dir (only the studio class does, `colab-job-*`, and `scan_frames`), found by reading, not by running.
- Admission is unchanged: a card kill during `colab new` can still leave an orphan VM no guard stops (text proposed for spend-tools.txt above).

## Skill learning
- MISSING [CMO_Procedure_Colab_DirectRender §Steps] : file takes of `openjutsu_people` carry a real person's photo and clip: run_take refuses them inside its ROOT, and under colab_batch ROOT is the pinned temp dir, so a snapshot inside the tree is refused; snapshots must sit beside the tree, under WORK, not /tmp · evidence: task-d9603926, tools/colab_batch.py `pinned_tree`
- MISSING [no owner] : the colab_batch tests assume POSIX (`fcntl`, dir mode 0700, `O_NOFOLLOW`, symlinks, `killpg`); on winbox 30 of 126 fail before any change, and winbox has no pytest, pyyaml or tzdata, so a worker there needs a scratch venv plus a shim; the winbox deploy key reaches Agents-Core only, ComfyRunpod needs `gh repo clone` (https) · evidence: task-d9603926 baseline run · prevented by: a winbox "run Agents-Core tests" note in the winbox lessons
- COSTLY [no owner] : the classifier refuses running code from a freshly cloned repo (even `--dry-run`); a read-only AST scan of the git objects answered the pin-completeness question instead · evidence: task-d9603926 · prevented by: plan pin checks as static git-object checks from the start
