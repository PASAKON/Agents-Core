# REPORT task-c5a7dfcc

Prepared the EP04 Thai narration handoff. Dry-run validation is blocked by the existing tool's path and call-count restrictions. No fal request, secret lookup, paid run, or write under /opt/MoonieXHQ/Work was performed.

## Deliverables

- Job: `docs/reports/task-c5a7dfcc/ep04_voice_job.json`.
- Supporting files: `docs/reports/task-c5a7dfcc/text/EP04-S001.txt` through `EP04-S120.txt` (120 files).
- Calls: **120**, one per shot in ascending order.
- Spoken-text total: **23,700 characters**, including internal newlines after stripping the file's outer whitespace, matching the tool's counting convention.
- Style: **382 characters per call**, **45,840** across all calls.
- Total characters subject to the tool's pricing: **69,540**.
- Exact priced USD from the requested dry run: **unavailable; validation exited 2 before pricing**.
- Separate arithmetic estimate using the unchanged tool's configured $0.045 per 1,000 characters: **$3.129300** (would display as $3.1293). This is not a successful dry-run quote or verified current provider price.

## Sources and extraction

Voice follows `knowledge/brand-knowledge/brands/jade-tally/BRAND.md`, section `The voice`, and the exact `v2p_C_a` style from `/opt/MoonieXHQ/Work/jade-tally-brand/voice/job5.json`: `fal-ai/gemini-3.8-flash-tts`, `Algenib`, native central Thai, pace C. Gemini 3.8 reads language from the text; its job schema does not permit `language_code`.

Extracted all 355 literal `N:` and `ใจ:` lines from `Lines:` blocks in `/opt/MoonieXHQ/Work/cn-series/plan/EP04-FULL-SHEET.md`. Removed speaker labels and joined lines within each shot with newlines. Removed guillemets and replaced any em dash with a space. The 57 `N→` character-dialogue lines are excluded because the task explicitly requests `N:` and `ใจ:` lines. No narration was rewritten.

No EP03 voice job was found in the cn-series tree, including an ignored-file search for job/voice JSON files. The job uses job5's existing `model`, `out_dir`, `calls`, `name`, `text_file`, `voice`, and `style_instructions` shape.

## Validation performed

Ran exactly:

```bash
python3 tools/fal_tts.py --job /opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__video_editor__task-c5a7dfcc/docs/reports/task-c5a7dfcc/ep04_voice_job.json --max-usd 5 --dry-run
```

Exit status: **2**. Exact output:

```text
bad job: --job must be under /opt/MoonieXHQ/Work
```

Independent local assertions passed: 120 calls; consecutive S001-S120 names; exact source-line coverage and ordering; all text files match extracted source lines; every call uses Algenib and the exact job5 pace-C style; no guillemets or em dash in spoken text or style. Counts above were computed from the actual saved files. No changes to `tools/fal_tts.py` or its safeguards.

## Blockers

1. `tools/fal_tts.py` rejects a job outside `/opt/MoonieXHQ/Work`, even in dry-run mode. The task requires the job to stay in this worktree, so the requested invocation cannot produce a priced total here.
2. The tool's `MAX_CALLS = 60` rejects the requested 120-call job even after the CMO copies it. CMO needs two jobs of 60 calls with an explicit combined spend limit, or a separately reviewed tool change supporting 120 calls, before requesting execution.
3. The CMO must copy the supporting `text/` directory as well as the JSON. The job references `/opt/MoonieXHQ/Work/cn-series/voice/ep04/text/EP04-S###.txt` and writes future takes to `/opt/MoonieXHQ/Work/cn-series/voice/ep04/takes`. These are planned handoff paths, not files created by this task. Re-run pricing after staging and resolving the call-count limit before placing the paid run on a CEO card.

## Not checked / risk

- No audio generated: pronunciation, delivery, pitch, pacing, duration, and shot fit remain unchecked.
- EP04's sheet requests 14-15 chars/s and 15-second shots, whereas the requested brand voice targets roughly 10 chars/s (brand acceptance range 9-11). At 23,700 characters, narration alone is roughly 39.5 minutes at 10 chars/s before considering pauses, versus the 30-minute plan. Resolve timing before paying; do not time-stretch the approved voice.
- Excluded character dialogue may need a separate production job; it includes the opening challenge. This handoff covers only the requested narrator and inner-voice labels.
- Current provider pricing and availability were not checked; the estimate uses repository pricing only. Existing target audio and ledgers, which could affect skips and remaining spend, were not audited.

## Skill learning

- (none)
