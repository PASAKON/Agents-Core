# REPORT task-762348af

Second-session, read-only review. No code fixes, approvals, merges, branch switches, or default-branch changes were made. The only deliverable changed is this report. Line references below refer to the reviewed PR heads, not the task branch.

## PR #468: changes needed

Reviewed local head `bf06bcf489671e96a1f650366278b87793630714`, matching the requested head, including `tools/ilag_cut.py`, its tests and EDL fixture, and the ILAG kit v2 diff. GitHub could not confirm the current remote head.

### Findings

1. **High: EDL paths escape `--root`; the EDL can select executable kit code.** `tools/ilag_cut.py:758` (`resolve`), `:748`, `:615`, `:623`. Validation accepts `src: ../outside.mp4`, `kit: ../outside-kit`, and `sfx: ../outside-sfx` with no errors. Resolving the source against `/safe/root` produces `/safe/outside.mp4`; absolute paths also pass. `cards` then runs the selected `cut_logo.py` and imports its `render_kit.py`. An EDL pointing to an existing untrusted kit can execute Python with the caller's permissions, including network or deletion operations. Fix: enforce canonical containment for EDL-controlled input paths, including symlinks, and use trusted renderer code rather than executing code selected by an EDL. An explicitly chosen CLI kit needs a clearly separate trust contract.

2. **High: output symlinks defeat the work-folder deletion/write boundary.** `tools/ilag_cut.py:699`, `:704`, `:705`, `:963`, `:976`, `:987`. A pre-existing `WORK/cards/ng-<key>` symlink to another directory makes a forced/stale frame rebuild unlink that directory's JPG files. A symlinked `WORK/seg` likewise redirects stamp deletion and writes; `WORK/out` or an existing final-file symlink redirects ffmpeg's `-y` overwrite. Generated names and the output-basename regex stop ordinary slash traversal but do not stop these escapes. Fix: reject symlinked output components/files and enforce containment before mutations; use no-follow, directory-relative operations where concurrent replacement is possible. No destructive reproduction was performed.

3. **Medium: the documented relative `--out` breaks card rendering.** `tools/ilag_cut.py:663`, `:683`; `knowledge/brand-knowledge/brands/ilag/templates/REBUILD.md:66`. `stage_kit` preserves a relative work path, and `as_uri()` requires an absolute path. The documented `--out Work/ep1/build` therefore raises uncaught `ValueError: relative path can't be expressed as a file URI` on a fresh render. Directly reproduced that expression. Fix: canonicalize the work directory before staging/rendering and test the CLI with a relative output path.

4. **Medium: replacing NG footage in place leaves stale freeze frames.** `tools/ilag_cut.py:190`, `:701`. The NG key contains the source path, freeze time, text, and fps, but no source identity/content metadata. When a source file is replaced at the same path, `cards` returns early if the old frame count matches, and `encode` can reuse the unchanged freeze JPGs while re-encoding the surrounding takes from new footage. This contradicts the rebuild instructions to rerun cards after swapping a source. Fix: include source content identity (and resolved root) in frame-cache invalidation; test replacement at the same path.

5. **Medium: NG rewind bypasses the reverse-buffer limit.** `tools/ilag_cut.py:378`, `:391` versus `:326`. A valid NG with `freeze_at: 600`, `rewind_in: 0` expands to a reverse source span of about 600.017 seconds without validation errors. Given sufficiently long media, preflight accepts it and ffmpeg buffers hundreds of seconds of 1080x1920 frames, potentially exhausting the render host's memory. Fix: apply the same maximum source-span guard to every generated reverse part before rendering.

### Correctness and safety checks

- All three verbs call EDL validation before their main work. Story watermark refusal is present; NG freeze frames bake the watermark in. More than two NG segments, em/en dashes and guillemets in traversed text, ordinary card/subtitle overruns, and overlapping subtitles are rejected. Path fields are intentionally excluded from punctuation checks.
- Hook length outside 12-15 seconds is a **warning**, not a refusal, matching REBUILD.md and the existing test. Missing fact/lesson/title/end also only warn. These are not hard enforcement gates.
- Additional validation edge cases: generated take-2 stickers can exceed their part (`:396`: a 0.125-second part gets a 1.5-second card); `dur: Infinity` raises `OverflowError` instead of returning validation errors (`:127`, `:311`). Reject nonfinite numbers, and clamp or validate generated cards as well as user cards.
- EDL text is passed as Playwright evaluation data and inserted as text nodes, not HTML or shell code. ffmpeg uses argv arrays without a shell; IDs and SFX names are restricted. No shell-injection path from ordinary subtitle/card text was found. This does not mitigate EDL-selected Python kit code above.
- Every `build_cmd` part ends its video graph in `setsar=1,format=yuv420p` (`:863`), and uses common encoding parameters. Concat uses stream copy (`:984`); final audio uses `loudnorm=I=<validated target>:TP=-1.5:LRA=11`, AAC, 48 kHz stereo (`:989`). This is single-pass normalization, not measured two-pass loudness verification.
- Linux lock acquisition surrounds segment encodes, concat, and loudnorm and closes in `finally` (`:959`, `:992`). Preflight and final probing sit outside the lock; `cards` has no lock. It does not serialize concurrent cards/encode operations on one output folder. Without fcntl it warns and proceeds, as documented. Lock opening follows symlinks and is not hardened for an untrusted shared lock directory.
- The checked-in renderer/template use local files, fonts and logo; no direct HTTP client/fetch was found in that execution path. REBUILD.md contains an explicit existing yt-dlp download recipe, which was not run. The tool does not enforce offline execution for arbitrary kits/media: it imports kit Python and does not block browser network requests or restrict ffmpeg demuxer protocols.
- Gitleaks: `gitleaks git --log-opts='main..bf06bcf4' --redact --no-banner` exited 0: 9 commits, about 129 KB scanned, **no leaks found**. This does not establish the provenance of the logo against a live Page; no network asset lookup was performed.

### Test result

Ran `pytest -q tests/test_ilag_cut.py` on the byte-for-byte PR snapshot inside the assigned worktree, using the existing Core venv on PATH, `PYTHONPATH=.`, and `PYTEST_ADDOPTS='--confcutdir=. --basetemp=../pytest-temp -rA'`. Original PR pytest.ini and root conftest.py were retained. Result: **40 passed, 14 skipped, exit 0** (counts from the per-test summary; the repository's additional `-q` suppresses the totals line). All ffmpeg encode/concat/cache/lock tests passed. The 14 browser/card-render tests skipped under their dependency/browser-availability guard; real card rendering and pixel comparisons therefore remain unverified.

### CI comparison

**Unknown; cannot establish that every PR failure is also on main.** `gh pr checks 468` and `gh run list --branch main -L 3` both failed with `error connecting to api.github.com`, including a retry. No fail-set or failure-log equivalence was inferred from local tests.

## PR #462: changes needed

Reviewed local branch `ph/ilaglakorn-drive-map`, head `39234e0ebcf35fa300e3b3a1e9dfbff8425222c4`. Its diff adds nine lines to `.claude/skills/CXO_Knowledge_GDrive_FolderMap/SKILL.md`. Remote freshness is unverified.

### Findings

1. **Medium: tree and ID table assign different parents.** `.claude/skills/CXO_Knowledge_GDrive_FolderMap/SKILL.md:323` and `:328`. The inserted story and graphics folders are beneath the latest same-level channel heading, `FB: บ้านนี้มีมีมี่` at line 301. The ID table at lines 547-548 puts both under `FB: ละครสั้นคุณธรรม`. An operator following the tree can file assets under the wrong channel. Move the new entries into the drama channel's subtree and repair continuation/end connectors. The preceding misplaced story entry is inherited, but extending that malformed location introduces the same error for these two new folders.

2. **Medium: forbidden guillemets remain, including in the new row.** `.claude/skills/CXO_Knowledge_GDrive_FolderMap/SKILL.md:547`. The new season title uses U+00AB/U+00BB, failing the explicit acceptance rule. Replace them with straight quotes or remove them. A whole-file scan also finds inherited occurrences at lines 235, 242, 243, 301, 502, 536, 537 and 562; those must also be addressed to satisfy "No guillemets anywhere" in this file.

### Validation and test result

- Programmatically extracted the two new table rows' IDs: **12 actual, 12 expected, zero missing, zero unexpected**. Each ID is attached to the corresponding name supplied in the brief, including both distinct logs.txt IDs.
- EP1 contains the requested All Scene, Element/Character/Location/Prop, Soundtrack, Final Draft and logs.txt descriptions. The graphics table row is flat and includes its own logs.txt. The defect is the tree's channel parent, not these IDs or inner EP contents.
- Whole-file forbidden-character check: **failed**, nine lines contain guillemets, one newly added.
- Gitleaks branch-commit scan exited 0: **1 commit, no leaks found**.
- Documentation-only PR: no executable test suite applies; checks above are the validation result.

### CI comparison

**Unknown.** `gh pr checks 462` and the main run listing were unreachable. The specific requested #468/main comparison is likewise unverified; no claim of inherited CI failures is made for either PR.

## Files changed

- `docs/reports/task-762348af/REPORT.md` only. No source, test, fixture, skill, or brand file edited.
- Temporary byte-for-byte PR files were extracted with `git archive` into a scratch subdirectory of the assigned worktree to run the requested tests without changing the task checkout or branch. Test temporary data was also confined to that scratch directory.

## Blockers

- GitHub API connectivity prevents remote-head verification and CI fail-set comparison. An authorized environment with GitHub access must run the checks and inspect failed-job details before claiming that failures match main.
- Both required posting attempts failed: `gh pr comment 468 --body-file .review-task-762348af/comment-468.md` and `gh pr comment 462 --body-file .review-task-762348af/comment-462.md` each returned exit 1, `error connecting to api.github.com`. **Neither verdict was posted.** The PR-specific sections above contain the prepared comment content for posting from a connected environment. No approval or merge was performed.
- Browser validation is limited: Playwright, PIL and numpy are installed, but a direct Chromium launch fails with `BrowserType.launch: Target page, context or browser has been closed`. This explains the 14 skips; no browser sandbox bypass or dependency installation was attempted.
- No MAILBOX.md was present at the checkpoints performed during review.
- Scratch snapshot, comment bodies and test outputs were removed after validation; only this report remains as a worktree change.

## Skill learning

- Existing absolute-path fixtures miss a documented relative-path CLI failure: `render_card_set` calls `as_uri()` without resolving `--out` first. Include a relative-path CLI case in future renderer reviews.
- Validate generated parts as well as input fields: NG expansion bypasses the reverse-memory guard and inserts a sticker longer than a short take-2 part.
- Compare a folder tree's nearest parent heading with table paths, not just names and IDs: all 12 new Drive IDs match while the tree still places the folders under the wrong channel.
