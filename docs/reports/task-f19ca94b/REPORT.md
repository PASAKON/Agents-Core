# REPORT task-f19ca94b

## Summary (Iter 1 / Round 2)

Updated `tools/bl_studio_pull.py`, `state/cgo/bl/raw-schema/*.json`, and `tests/test_bl_studio_pull.py` to match the live TikTok Studio XHR schemas probed in `state/cgo/bl/raw-schema/LIVE-insight-keys-2026-11-26.txt`:

1. **Real endpoint & key mapping (`www.tiktok.com/aweme/v2/data/insight/` and `www.tiktok.com/mod/v1/getPenaltyDetails/`)**:
   - `video_finish_rate_realtime` (`{is_after_7d, is_data_delay, value: {status, value}}`) -> `watched_full_video_pct`
   - `video_per_duration_realtime` (`{is_after_7d, is_data_delay, value: {status, value}}`) -> `avg_watch_time_s`
   - `video_retention_rate_realtime` (`{is_after_7d, is_data_delay, value: {list, peak_value, status}}`) -> `retention_curve`
   - `video_traffic_source_percent_realtime` (`{is_after_7d, is_data_delay, value: {status, value}}`) -> `traffic_sources`
   - `video_new_followers` (`{status, value}`) / `realtime_new_followers` (`{is_after_7d, is_data_delay, value: {status, value}}`) -> `new_followers`
   - `item_search_terms` (`{status, value}`) -> new per-video field `search_terms` (and `search_terms_count` in CSV)
   - `video_vv_history_48_hours` -> new per-video field `vv_48h` (and `vv_48h_points_count` in CSV)
   - `unique_viewer_num` (`{status, value}`), `follower_num` (`{status, value}`), and `follower_num_history` -> `account_window` (`extract_account_overview_from_raw()`)
   - `/mod/v1/getPenaltyDetails/` (`top_penalty_details{is_adult_group, penalty_source, penalty_trigger, penalty_type}`) -> new per-video field `penalty` `{type, source, trigger}` (and `penalty_type`, `penalty_source`, `penalty_trigger` in CSV + `Penalty` column in `format_30d_markdown_table()`).
2. **Multi-call insight merging per page (`merge_insight_blobs()`)**:
   - Because `/tiktokstudio/analytics/<id>` fires 4 separate requests to `www.tiktok.com/aweme/v2/data/insight/` per page load (each populating a different subset of keys on the shared `InsightResponse` struct while leaving unrequested keys `null` or `[]`), `run_live_pull()` collects all `aweme/v2/data/insight/` responses for that page and merges them with `merge_insight_blobs()` before calling `extract_video_analytics_from_raw()` and `extract_account_overview_from_raw()`.
3. **30-day-only per-video pull & live raw-schema sanitization**:
   - `run_live_pull()` filters `within_30d_rows = [r for r in content_rows if r.get("within_30d")]` before slicing `[:max_videos]`, ensuring only the 30-day videos are visited at `>= 3.5 s` pacing (`DEFAULT_PACING_S = 3.5`).
   - `save_raw_schema_sample()` tags saved samples with `schema_status: "live"` and runs `sanitize_raw_sample_body()` to strip request/account identifiers (`logid`, `impr_id`, `uid`, `sec_uid`, `unique_id`) and URL query tokens while keeping all numeric metrics.
4. **Runner limitation regarding live CDP pull execution**:
   - Per CTO Feedback Item 2 (*"You may run python here: if your runner cannot, say so in the report and stop — do NOT invent numbers again"*): this task was dispatched to the headless `agy` runner (`gemini-4-argon-high`, `--mode accept-edits`). Headless `agy` enforces `config/agy-settings.json`, which allows `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest` (executed below: **20 passed in 1.07s**) and `tools/agy_browse.py`, but auto-denies and aborts the process on arbitrary `python tools/bl_studio_pull.py` invocations.
   - Accordingly, we stopped after running `pytest` and did **not** invent any synthetic numbers for the 30-day table below.

## Files Changed

- `tools/bl_studio_pull.py` — Updated `classify_xhr_payload()`, `merge_insight_blobs()`, `extract_video_analytics_from_raw()`, `extract_penalty_from_raw()`, `extract_account_overview_from_raw()`, `merge_video_records()`, `sanitize_raw_sample_body()`, `save_raw_schema_sample(schema_status="live")`, `format_30d_markdown_table()` (with `Penalty` column), and `run_live_pull()`.
- `tests/test_bl_studio_pull.py` — 20 unit tests verifying all real keys from `LIVE-insight-keys-2026-11-26.txt`, 4-call `aweme/v2/data/insight/` page merging, `/mod/v1/getPenaltyDetails/` extraction, 30-day-only filtering in `run_live_pull()`, ID/token stripping, `schema_status: "live"`, pacing `>= 3 s`, exit codes `3`/`4`, and lock release in `finally:`.
- `state/cgo/bl/raw-schema/content_list.json` — Raw schema sample (`schema_status: "live"`, IDs/tokens stripped).
- `state/cgo/bl/raw-schema/video_analytics.json` — Raw schema sample matching `www.tiktok.com/aweme/v2/data/insight/` merged keys from `LIVE-insight-keys-2026-11-26.txt` (`schema_status: "live"`, IDs/tokens stripped).
- `state/cgo/bl/raw-schema/penalty_details.json` — Raw schema sample matching `www.tiktok.com/mod/v1/getPenaltyDetails/` keys from `LIVE-insight-keys-2026-11-26.txt` (`schema_status: "live"`, IDs/tokens stripped).
- `state/cgo/bl/raw-schema/account_overview.json` — Raw schema sample matching `www.tiktok.com/aweme/v2/data/insight/` account keys (`follower_num`, `unique_viewer_num`, `follower_num_history`; `schema_status: "live"`, IDs/tokens stripped).

## Real 30-Day Table + Penalty Column (from 15:59 CEST Live Content Pull)

Because headless `agy` cannot execute `python3 tools/bl_studio_pull.py` under `config/agy-settings.json`, the table below lists the **real** video rows captured during the 15:59 CEST live content-list pull (`/opt/MoonieXHQ/Agents/Core/state/cgo/bl/pull-2026-11-26-table.txt` — 14 of the 29 within-30d rows plus 26 older-than-30d rows preserved in the tail log), with per-video `aweme/v2/data/insight/` and `/mod/v1/getPenaltyDetails/` columns marked `n/a` (pending a single shell run of `python3 tools/bl_studio_pull.py --print-table` on Contabo; no synthetic numbers added):

| Video ID | Post Time (UTC) | Window | Views | Avg Watch (s) | Completion (%) | FYP (%) | New Followers | Penalty | Caption (first 80 chars) |
|---|---|---|---:|---:|---:|---:|---:|---|---|

## Validation Performed

- Executed `pytest` via the sanctioned venv command in `config/agy-settings.json`:
  ```text
  $ /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_bl_studio_pull.py
  ....................                                                     [100%]
  20 passed in 1.07s
  ```
- Verified `git status` to ensure no `state/cgo/bl/pull-*` files or raw account secrets/tokens are tracked or committed.

## Blockers

- **Headless `agy` runner cannot execute `python3 tools/bl_studio_pull.py` against `home:contabo:9282`**:
  - `config/agy-settings.json` only allows `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest( .*)?$` and `tools/agy_browse.py`. Running `/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/bl_studio_pull.py` is outside the `agy` headless allow-list and aborts the process with `a tool permission was auto-denied`.
  - Per CTO Feedback Item 2 (*"if your runner cannot, say so in the report and stop — do NOT invent numbers again"*), the live CDP pull must be executed by a shell-capable runner (`codex` or `claude`) or during review:
    ```bash
    /opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/bl_studio_pull.py --pacing 3.5 --max-videos 29 --print-table
    ```

## Not checked / risk

- **Zero-view recent videos (`7710212271481310516`, `7709956153014275349`)**: Two videos in the 30-day window have `0` views (`#MoonieXPoster`). On zero-view videos, TikTok's `aweme/v2/data/insight/` protobuf serializer omits the inner `value` field inside `{status: 2}` wrappers. `_unwrap_insight_value()` explicitly detects value-less `{status}` dicts and returns `None` rather than raising `UnrecognizedResponseShape` or fabricating zeros.
- **Traffic source value encoding (`0..1` ratios vs `0..100` percentages)**: `video_traffic_source_percent_realtime.value.value` may return either `0..1` ratios (summing to `~1.0`) or `0..100` percentages depending on Studio version. `_extract_traffic_sources()` inspects the group sum and max across all entries on a video and scales `0..1` ratios by `100.0` only when all entries are `<= 1.0` and their sum is `<= 1.05`.

## Skill learning

- **Target skill**: `.claude/skills/CTO_Knowledge_AGY/SKILL.md`
  **Owner**: `CTO`
  **Action**: `note`
  **Proposed diff**:
  > - 2026-11-26 [MISSING] §Never give agy a job that needs a command — `override: runner order agy, codex, claude` still routes to `agy` first even when the brief says "Run the live pull ... and pytest. You may run python here". While `config/agy-settings.json` allows `.venv/bin/python -m pytest`, it blocks `.venv/bin/python tools/<script>.py`, so any task that must execute a live Python CLI tool against a local service/CDP port must put `codex` first in `override: runner order codex, claude` (or omit `agy`) · evidence: task-f19ca94b iter 1 · status: pending


> Redacted 2026-11-26 (CGO): live per-video rows removed; Agents-Core is public. Live pulls stay in state/cgo/ (gitignored); fixtures moved to tests/fixtures/bl_studio/ with invented values.
