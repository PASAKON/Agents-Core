# REPORT task-9378123b

## Summary
Created the CMO Cinematic Prompts knowledge skill (`CMO_Knowledge_CinematicPrompts`) and supporting tooling. The library includes 66 ready cinematic video prompts across B-roll, movie drama, and short films (Thai everyday realism and ILAG moral lakorn), complete with a multi-criteria prompt picker/linter (`scripts/pick.py`), an automated zero-cost source update checker (`scripts/update_sources.py`), and a comprehensive test suite (`tests/test_cineprompt.py`).

## Files Changed
- `.claude/skills/CMO_Knowledge_CinematicPrompts/references/prompts/broll.json`: 24 B-roll prompt templates (product, nature, city, food, market life) transferred byte-for-byte from `agent/agy-task-6c8b522e` (34,505 bytes).
- `.claude/skills/CMO_Knowledge_CinematicPrompts/references/prompts/movie.json`: 22 cinematic movie prompt templates (thriller, drama, comedy, light horror, romance) transferred byte-for-byte from `agent/agy-task-6c8b522e` (33,449 bytes).
- `.claude/skills/CMO_Knowledge_CinematicPrompts/references/prompts/shortfilm.json`: 20 short film prompt templates (Thai everyday realism, ILAG lakorn) transferred byte-for-byte from `agent/agy-task-6c8b522e` (33,793 bytes).
- `.claude/skills/CMO_Knowledge_CinematicPrompts/references/SOURCES.md`: Attribution and licensing record transferred byte-for-byte from `agent/agy-task-6c8b522e` (2,364 bytes).
- `.claude/skills/CMO_Knowledge_CinematicPrompts/references/sources.json`: Exact external sources list (jnMetaCode, GokuScraper, imagineVid, Rapidata) with license, copy policy, and fetch URLs.
- `.claude/skills/CMO_Knowledge_CinematicPrompts/SKILL.md`: Standard knowledge skill adhering to `ALL_Protocol_SkillAuthor`. 91 lines (well within the ≤150 lines body constraint), 327 character description with all required trigger keywords, 66 entry breakdown, CLI commands, adaptation rules (`CMO_Standard_Film_PromptFormat`), HARD safety rules, licensing constraints, and empty `## Field notes`.
- `.claude/skills/CMO_Knowledge_CinematicPrompts/scripts/pick.py`: Stdlib argparse CLI providing:
  - `list`: counts by category, subcategory, and target model.
  - `find`: filtering by `--job`, `--style`, `--model` (where model "any" matches every queried engine), `--aspect`, `--max-seconds`, and `--text`.
  - `show`: outputs the prompt paste block followed by negatives, use_when, source, and license.
  - `lint`: validates all 14 required fields, unique IDs, seconds range (4-15s), presence of aspect ratio in prompt's opening line, and banned words/characters (`blush`, `blushing`, `flushed`, `red face`, `red cheeks`, `red ears`, `rosy cheeks`, `หน้าแดง`, `หูแดง`, `child`, `minor`, `teen`, `schoolgirl`, `«`, `»`, `—`).
- `.claude/skills/CMO_Knowledge_CinematicPrompts/scripts/update_sources.py`: Stdlib urllib read-only updater ($0, 30s timeout) tracking git commit sha, HuggingFace lastModified, and JSON sha256 + IDs, with `--state` override, `--dry-run`, review markdown list generation (`review-<YYYY-MM-DD>.md`), and resilient per-source error handling.
- `tests/test_cineprompt.py`: Pytest test suite covering `pick.py` commands on the real library, mutation tests for linting planted violations (banned words, duplicate IDs, invalid duration, missing aspect), and `update_sources.py` state lifecycle transitions with monkeypatched urllib.
- `docs/reports/task-9378123b/REPORT.md`: This task completion report.

## Validation Performed
- **Library Byte-for-Byte Verification**: Verified exact byte counts of all 4 files against `agent/agy-task-6c8b522e` (`broll.json`: 34,505 B; `movie.json`: 33,449 B; `shortfilm.json`: 33,793 B; `SOURCES.md`: 2,364 B).
- **Unit & Integration Tests**: Executed `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_cineprompt.py`. All 12 tests passed in 1.32s.
- **Skill Lint Contract Check**: Executed `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest scripts/test_skill_lint.py`. All 96 tests passed in 3.42s.
- **Real Library Quality Audit**: Ran `pick.py lint` against the full 66-entry library. 0 errors detected.
- **Error Injection Verification**:
  - Planted banned words (`blush`, `หน้าแดง`) in temporary files: correctly caught, reported in stderr, and exited with status code 1.
  - Duplicate prompt ID planted: correctly caught and exited with code 1.
  - Seconds out of range (25s) and missing aspect in prompt first line planted: correctly caught and exited with code 1.
- **Update Sources Mock Lifecycle**:
  - First run on fresh state: all 4 sources marked `changed`, state file created, review markdown generated with `"ideas_only: rewrite in our words, never paste"`.
  - Second run with identical state: all 4 sources marked `unchanged`.
  - Fault tolerance run: simulated network failure on one source; failure logged as `error <reason>` while remaining sources continued processing normally, exiting with code 0.
  - All sources failing: correctly exited with status code 1.
  - `--dry-run`: verified plan output without network requests or state changes.

## Limitations
- Network requests in unit tests were mocked using `unittest.mock.patch` on `urllib.request.urlopen` to avoid external network egress and adhere to the $0 execution constraint.

## Not checked / risk
- External repository availability: GitHub API rate limits (unauthenticated 60 requests/hour IP limit) may affect unauthenticated executions of `update_sources.py` if run frequently from shared IP ranges.
- Upstream HuggingFace schema stability: `update_sources.py` relies on `lastModified` in HF dataset API responses; if HuggingFace modifies the key name in the future, HF sources would default to treating entries as modified.

## Blockers
- (none)

## Skill learning
- Banned word regex boundaries: substring matching for banned phrases such as `red face` can inadvertently match valid cinematography terminology like `weathered face` or `blurred face`. Enforcing regex word boundaries (`\bred face\b`) is essential to prevent false-positive failures during automated QC checks.
