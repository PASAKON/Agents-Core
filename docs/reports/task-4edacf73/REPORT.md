# task-4edacf73 — ilag_cut.py, fixes for the Codex review of PR #468 (task-762348af)

Project IlagLakorn (PH #d5e4d1fd). Branch `agent/developer-task-4edacf73`, cut from origin/main `30227a80`. Not merged.
Line numbers in the brief were from `bf06bcf4`; `tools/ilag_cut.py` on main had not changed since (1035 lines), so
they still pointed at the right code.

Method: the 43 new tests were written first and committed red (`4f9f128d`). Against the unfixed tool, 39 of the 43 fail,
each for the stated reason (plan exits 0 instead of refusing, `ValueError: relative path can't be expressed as a file URI`,
the trap `render_kit.py` writes its marker, `OverflowError: cannot convert float infinity to integer`, stale NG frames
reused ...). The other 4 are guards that must pass before and after (they prove the fix does not over-block). Then one
commit per item.

## Items

| # | Sev | Fix (tools/ilag_cut.py) | Tests (tests/test_ilag_cut.py) | Commit |
|---|---|---|---|---|
| 1 | HIGH | `resolve()` now refuses any EDL path (every src incl. ng take/take2, `sfx`, `kit`) that, with symlinks followed, is outside `--root`; `check(edl, root)` lists every such path at `plan`/`cards`/`encode`; `build_cmd` and `preflight` re-check at use and open the resolved path. The kit's Python is always `REPO_KIT` (`knowledge/brand-knowledge/brands/ilag/templates`): `stage_kit`, `logo_source`, `kit_fingerprint` read template, fonts and logo from the chosen kit folder, but `render_kit.py` (run in-process) and `cut_logo.py` (child) only from the repo. `output` no longer takes `:` (`C:x.mp4` is drive-relative on Windows). | `test_plan_refuses_an_edl_path_that_leaves_root` (8 cases: dot-dot, absolute, symlinked src, end card, ng take, ng take2, sfx folder, kit folder), `test_encode_never_reaches_ffmpeg_for_an_escaping_source`, `test_encode_refuses_an_sfx_file_that_is_a_link_out_of_root`, `test_output_name_cannot_carry_a_windows_drive`, `test_the_kit_python_always_comes_from_the_repo_kit[png,jpg]` (a kit copy whose two .py files write a marker: marker must not exist, staged `render_kit.py` must equal the repo's). Guard: `test_plan_still_takes_paths_that_stay_inside_root`. | `1a0377cf` |
| 2 | HIGH | `refuse_escaping_links(work)`: walks WORK (no link followed) and refuses, before anything is written or deleted, any symlink whose target is outside WORK. Called first in `render_card_set` and in `cmd_encode`. Covers cards/, seg/, out/, kit/ and single linked files. | `test_refuse_escaping_links_unit` (inside link ok, escaping link refused and named), `test_encode_refuses_a_symlinked_work_folder[seg,out]`, `test_cards_refuses_a_symlinked_cards_folder`, `test_cards_refuses_a_symlinked_kit_stage` (each also asserts the outside folder is still empty). | `1331d77b` |
| 3 | MED | `edl_root(a)` and `Path(a.out).resolve()` in `cmd_plan/cards/encode`; `render_card_set` resolves its own `work` too, so a direct caller is safe. | `test_cards_hands_an_absolute_work_folder_to_the_renderer` (no browser needed), `test_cards_with_a_relative_out_draws_instead_of_crashing_on_as_uri` (real Chromium). Guard: `test_encode_with_a_relative_out_and_root`. | `9c9675a6` |
| 4 | MED | `draw_ng_frames` writes `ng-<key>/.src` = path + size + mtime_ns of the source (after the last frame, so a half-drawn set has none) and reuses the set only when it matches. `preflight` makes `encode` refuse a set whose stamp no longer matches ("NG slam frames are stale ... run `cards` again"). | `test_ng_frames_are_redrawn_when_the_source_is_replaced_at_the_same_path` (red video replaced by blue at the same path: redrawn, frame luma drops; an unchanged source still hits the cache), `test_encode_refuses_ng_frames_drawn_from_a_replaced_source`. | `82ba8dcb` |
| 5 | MED | `expand_ng` applies the clip rule to the rewind: source span read (`rdur * REWIND_SPEED`) over `REVERSE_MAX` (8 s, now one constant shared with the reversed clip) is an error that says to set `rewind_in` later in the take. | `test_ng_rewind_span_over_8_s_is_refused` (default `rewind_in`, 9 s take), `test_ng_rewind_span_over_8_s_by_explicit_times_is_refused`. Guard: `test_a_long_take_is_fine_when_rewind_in_keeps_the_span_short`. | `e158a466` |
| 6 | LOW | The take-2 sticker is `min(TAKE2_STICKER, dur2)`. `V.num` refuses a non-finite float ("'dur' must be a finite number, got inf") and anything over `NUM_MAX = 1e6` ("must be at most 1e+06 in size"), for every numeric EDL field, so no `q()`/`int()` OverflowError is reachable from an EDL. | `test_take2_sticker_is_clamped_to_its_part` (and a 3 s take 2 keeps the full 1.5 s), `test_a_non_finite_or_absurd_number_is_a_clear_error_not_a_traceback[Infinity,-Infinity,NaN,1e999,a 401-digit int]`, `test_every_number_field_refuses_infinity[at,in,gain,blur,freeze_last]` (`speed` was already bounded; kept as a guard). | `e158a466` |
| 7 | CMO | `pick_lock()`: `--lock` as given; on Linux without it, one WARN and `DEFAULT_LOCK = /opt/MoonieXHQ/Work/.bl-render.lock`; if that folder is missing, one WARN and no lock; macOS/Windows unchanged (no default, no warning). `--help` and the docstring say so. | `test_pick_lock_rules`, `test_pick_lock_without_the_lock_folder_warns_and_goes_on`, `test_the_default_lock_is_the_black_liquidity_render_lock`, `test_encode_without_lock_holds_the_default_lock_and_warns_once` (spy proves every ffmpeg call runs while the lock is held; 6 segments, 1 warning). An autouse fixture points `DEFAULT_LOCK` at tmp, so no test ever waits on or holds the real Contabo lock. | `f858d620` |

## pytest tail

Interpreter: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` (system `python3` has no pytest, PIL or Playwright).

```
before the fixes (tests only added, tool unchanged):   39 failed, 4 guards passed of the 43 new tests, 54 old tests passed
after all seven:   pytest tests/test_ilag_cut.py tests/test_ilag_theme.py -p no:cacheprovider -rs -o addopts="" -q
........................................................................ [ 60%]
...............................................                          [100%]
119 passed in 193.10s (0:03:13)
```
97 in `test_ilag_cut.py` (54 existing + 43 new) and 22 in `test_ilag_theme.py`; 0 failed, 0 skipped (Playwright, Chromium,
PIL, numpy and ffmpeg are all present in this venv, so the browser tests ran). Chromium was used only for the tiny
card renders in the tests; no EP render was run.

## Behaviour changes the reviewer should know

- A symlink inside `--root` that points outside is refused, including a `footage/` that is a link to a Drive mount. That is
  the brief's rule ("resolve every EDL path and refuse anything outside"); the way out is a `--root` that is the common
  ancestor. An absolute `src` is fine if it lands inside `--root`.
- The EDL's `kit` string is checked even when `--kit` overrides it (strict reading of "every EDL path"). An EDL with
  `"kit": "../../knowledge/.../templates"` now fails `plan` with a clear line; drop the key or point it inside root.
- A kit folder's own `render_kit.py` / `cut_logo.py` are ignored, even an edited one. To change what the kit's Python does,
  change the repo kit. `--kit` folders no longer need those two files at all.
- `cards` now needs the NG source to exist even when frames are cached, and a frame set drawn by #468 (no `.src`) is redrawn
  once. `encode` tolerates a missing stamp (an old set) and refuses a mismatching one.
- `NUM_MAX = 1e6` and the `:` ban in `output` go slightly past the brief, same bug class (an EDL value reaching an
  OverflowError or an escaping path).

## Reach (what the change touches)

Only `tools/ilag_cut.py` and `tests/test_ilag_cut.py` changed. Nothing else in the repo imports `ilag_cut` (grep: the
tool, its test, and `REBUILD.md`). `check()` keeps `root=None` as default, so every existing `check(edl)` call in the tests
behaves as before; `resolve`'s callers are `cmd_cards`, `draw_ng_frames`, `build_cmd`, `preflight`.

## For the CMO (bank is theirs, not edited here)

`knowledge/brand-knowledge/brands/ilag/templates/REBUILD.md` §"Cut a full EP" is now stale in three places:
1. table row for `encode` (line 58): add that on Linux it holds `/opt/MoonieXHQ/Work/.bl-render.lock` by default.
2. code block (lines 65-67): `--lock ...` is no longer needed on Contabo; the winbox line should say there is no lock off Linux.
3. lines 70-72: swapping an `ng` source is now caught by the tool (`cards` redraws, `encode` refuses stale frames).
Also worth one sentence: EDL paths must stay inside `--root`.

## Skill learning
- MISSING [CXO_Protocol_DevSpawn §3d] : the brief for this task carried neither the interpreter line nor the pytest line the skill already lists (`.venv/bin/python` by absolute path, plain `pytest` with no extra `-q`); I hit both (system python3 has no pytest; my first `-q` runs printed no totals line) · evidence: task-4edacf73 (scratchpad runs full1.txt vs full2.txt)
- MISSING [no owner] : `git diff origin/main` in a worker worktree turns other sessions' later merges into phantom reverse changes once main moves during the task (it listed an unrelated SKILL.md); use `git merge-base HEAD origin/main` and `git diff <base> HEAD`, and `git merge-tree --write-tree HEAD origin/main` to prove a clean merge · evidence: task-4edacf73 (base 30227a80, origin/main 90fa1d47)
- MISSING [no owner] : in a worker session `wiki_read("org:IRON-RULES.md")` answers "wiki 'org' not available"; the same files read fine from `/opt/MoonieXHQ/Agents/Rules/` on Contabo · evidence: task-4edacf73
- COSTLY [no owner] : a `cd "$VAR"` in a Bash call is blocked by `scripts/hook-cwd-guard.py`; scratch scripts in the scratchpad run with absolute paths instead · evidence: task-4edacf73 (one blocked hostile-path check, rerun via a script file)
