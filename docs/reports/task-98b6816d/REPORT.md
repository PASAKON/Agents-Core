# REPORT task-98b6816d

Implemented `tools/film_breakdown.py` and `tests/test_film_breakdown.py`. The offline CLI prefers PySceneDetect ContentDetector, falls back to ffmpeg scene score > 0.3, and writes shots.csv, summary.json, and 320 px midpoint thumbnails. Storyboard mode compares naturally sorted local frames and labels its statistics as coarse estimates.

## Files changed

- `tools/film_breakdown.py`
- `tests/test_film_breakdown.py`
- `docs/reports/task-98b6816d/REPORT.md` (required worker-contract exception to the two-code-path scope)
- WORK_DIR `/root/MoonieXHQ/Work/task-98b6816d/in/SOURCES.txt`
- WORK_DIR `/root/MoonieXHQ/Work/task-98b6816d/out/REPORT.md` (full deliverable report)

## Validation performed

```text
env -u ORG_DB_URL -u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR PYTHONDONTWRITEBYTECODE=1 nice -n 10 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:cacheprovider tests/test_film_breakdown.py --basetemp=/root/MoonieXHQ/Work/task-98b6816d/tmp/pytest
.........                                                                [100%]
9 passed in 4.93s
```

Synthetic ffmpeg video: four two-second color shots; fallback found exactly three cuts (2, 4, 6 seconds). Tests check CLI tables, summary arithmetic, thumbnail count and width, storyboard output, fallback selection, and input errors. `git diff --check` passed. Sequential analysis ran at nice 10. Initial `free -m` reported 2859 MB available; WORK_DIR is 16 MB and disk usage is 85%, within the requested bounds.

Branch: `agent/codex-task-98b6816d`. Current pre-change HEAD: `8091ec62468bb328a4f4fc0ab99faf2f462d97d8`. Implementation commit and push are owned by the launcher. PR number: unavailable.

Tears of Steel n_shots, average/median shot length, and analysis runtime: not measured because download was blocked. No real-film CSV or sample thumbnails are claimed. Full details are in WORK_DIR/out/REPORT.md.

## Blockers

- Blender download directory request failed: `curl: (6) Could not resolve host: download.blender.org`. Need access to the permitted Blender source or a supplied file with provenance before producing real-film outputs and its SHA256 ledger entry. No downloads succeeded.
- PySceneDetect installation in WORK_DIR/tmp/venv failed: `No matching distribution found for scenedetect[opencv]`. Used the authorized ffmpeg fallback. Pytest was available in the existing repository venv.
- GitHub request failed: `error connecting to api.github.com`. PR creation is pending launcher commit/push and working GitHub access. Final implementation SHA and PR number remain outstanding.

## Not checked / risk

- Real-film processing, performance, cut accuracy, and source licensing verification remain untested.
- PySceneDetect execution remains untested; fallback and storyboard execution passed.
- Fallback scene score is fixed at 0.3, distinct from ContentDetector threshold 27; summary records that --threshold does not apply to fallback.
- Storyboards need individual uniformly spaced images; estimates can miss cuts or confuse motion with cuts. Runtime and thumbnails are approximate.
- Minute buckets count shot starts; the final partial minute is not normalized. Use fresh output directories to avoid stale thumbnails from earlier runs.

## Skill learning

- (none)
