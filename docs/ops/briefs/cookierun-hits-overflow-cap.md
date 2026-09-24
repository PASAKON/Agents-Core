# Brief — Cookie Run hit frames: 500 MB/day stays on the box, the overflow goes to Drive

Repo: `PASAKON/MoonieX-CookierunBot` (the bot; runs on winbox at `C:\Users\passg\cookierun-bot`, a git
clone since the 2026-09-24 reinstall). Work in the read-write clone the CTO made for you:
`/tmp/claude-0/-opt-mooniex-agents/e819fde6-36f8-4308-8818-aa716ebacd0e/scratchpad/cookierun-bot` — branch
`feature/hits-overflow-cap` cut from `origin/main` (9620c7a). Use `git -C <that path>` for every git
command; never `cd` inside a compound command (a hook blocks it). English only (IRON §56).

## The ruling (CEO 2026-09-24, Machine Contract plan `Agents-Core docs/ops/machine-contract-plan-2026-09-24.md`)
Hit frames (`modelplay/session-*/run-*/hit_NN/`, full-size JPEGs written by `play_model.py` lines ~939/990,
2–4 GB/day on a farm day, tier A in `docs/DATA-STEWARD.md`) were the bulk of the 84 GB lost in the winbox reset.
New rule: **per calendar day at most 500 MB of hit frames stays on the box; the rest goes to Drive as one
tar per day + manifest, md5-verified, and only then is deleted locally.** `rounds.jsonl`, meta and everything
not listed in an ok manifest stay, exactly as today.

## Read first
`tools/archive_runner.py` (queue items 1–4, `stream_dirs(name, kind, dest, root, members, manifest)`,
`manifest_ok`, `refresh_plan`), `tools/archive_reclaim.py` (the dir-archive rule at `candidates()`: members of
an ok manifest of kind bot_session/jumpsweep may go), `tools/rank_bot_sessions.py` (the plan-writer pattern:
decides, deletes nothing), `tools/archive_tick.bat`, `docs/DATA-STEWARD.md` (tiers; the paragraph "The ceiling
this does not touch"), `tests/` (existing tests must stay green on Linux where they can run).

## Deliverables (all on the branch)
1. `tools/hits_plan.py` — decides, deletes nothing. Walks `modelplay/session-*/run-*/hit_*/` dirs, groups them by
   calendar day (local time of the newest file inside the hit dir), skips TODAY (a day still being written is
   never planned), and per past day with total > `CAP_BYTES` (500 MB, module constant, env `HITS_CAP_MB`
   override) chooses the KEPT subset deterministically: sort by (run dir name, hit dir name), take an evenly
   spaced subset (every k-th dir, k = ceil(total/cap)) until the cap is reached — so what stays is spread across
   the day, not just its first hour. Everything else for that day is OVERFLOW. Writes `archive/hits_plan.json`:
   `{"cap_bytes":…, "generated":…, "days": {"<YYYY-MM-DD>": {"keep": [rel paths], "overflow": [rel paths],
   "bytes_keep":…, "bytes_overflow":…}}}` (paths relative to `modelplay/`). `--plan` writes, no flag = report only.
2. `tools/archive_runner.py` — queue item 5 after jumpsweeps: for each day in the plan with overflow and no ok
   `archive/hits-<day>.manifest.json`, `stream_dirs(f"hits-{day}", "hits", f"{BASE}/hits/hits-{day}.tar",
   MODELPLAY_ROOT, members, manifest)`; `refresh_plan` also re-runs `hits_plan.py --plan` when any
   `modelplay/session-*/run-*/hit_*` is newer than the plan file. **Gate:** item 5 yields nothing unless
   `archive/hits_archive_enabled` exists (its content = the CEO's approval date) — the Drive sub-folder
   `BACKUP/CookieRun Backup/hits/` is proposed, not yet approved (gdrive-filing rule 3), and rcat would create
   it. The CTO creates that file after the approval; until then the runner logs one line "hits: gated".
3. `tools/archive_reclaim.py` — the dir-archive rule accepts kind `"hits"` too (members of an ok manifest may go,
   same md5-verified manifest as the others); nothing else changes. `rounds.jsonl` stays untouched.
4. `docs/DATA-STEWARD.md` — the hits tier line becomes: tier A, on the box up to 500 MB per day (CEO 2026-09-24),
   overflow's master copy = Drive `BACKUP/CookieRun Backup/hits/hits-<day>.tar` (+ manifest), deleted locally
   only after md5 verify; rewrite "The ceiling this does not touch" accordingly; fix the deploy line (winbox is a
   git clone now: push to GitHub, `git pull` on the box; the old "scp into a synced copy" is gone).
5. `tests/test_hits_plan.py` — temp modelplay tree with 3 past days + today: one day under the cap (no overflow),
   one over the cap (kept subset ≤ cap, evenly spaced, deterministic across two runs), today excluded; runner
   queue yields no hits item without the gate file and one per overflow day with it (monkeypatch `stream_dirs`);
   reclaim with a fake ok manifest of kind hits lists exactly its members and nothing else. Also run the existing
   suite: `python3 -m pytest tests -q` (some tests are Windows-only — say which were skipped/failed and why).

## Constraints
Python 3.11 stdlib only (the box runs `.venv` 3.11, no new deps). Keep the hardcoded `C:\Users\UsEr\…` paths as
they are (a junction `UsEr → passg` keeps them valid) but note them in the report. No Drive/rclone/ssh/winbox
access from this box; no changes to `play_model.py`/`engine.py`. No file over 1 MiB.

## Finish
Commit on the branch (message starts `hits: 500 MB/day local cap, overflow to Drive per day (CEO 2026-09-24)`,
ending with the two attribution lines the CTO gave you), `git -C … push -u origin feature/hits-overflow-cap`, and
report: files changed, verification output verbatim (pytest of your tests + the suite, `python3 tools/hits_plan.py`
on a temp tree), the pushed sha, the Windows-only caveats, and a `## Skill learning` section (WRONG/MISSING/COSTLY
naming skill §section, or `- (none)`). Do NOT merge to main and do NOT deploy.
