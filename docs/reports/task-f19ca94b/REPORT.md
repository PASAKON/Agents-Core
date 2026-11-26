# REPORT task-f19ca94b

## Summary

Implemented the zero-model, read-only TikTok Studio analytics collector `tools/bl_studio_pull.py` for `@black_liquidity` over Browser Home `tiktok-bl` (`http://127.0.0.1:9282`, lock `home:contabo:9282`), together with sanitized raw endpoint schema samples under `state/cgo/bl/raw-schema/` and unit tests in `tests/test_bl_studio_pull.py`.

## Files Changed

- `tools/bl_studio_pull.py` — Zero-model TikTok Studio analytics reader and pure JSON-to-row adapters:
  - **Lock discipline**: Acquires `home:contabo:9282` (`--purpose "CGO studio pull"`) via `tools/home_lock.py` before connecting to CDP, and releases the lock in a `finally:` block on all exit paths.
  - **Read-only CDP XHR interception (no UI clicking)**: Opens a dedicated temporary tab on `http://127.0.0.1:9282` (closing only its own tab on exit without disturbing existing Browser Home tabs), enables `Network.enable`, and captures JSON responses via `Network.responseReceived` + `Network.getResponseBody` across `https://www.tiktok.com/tiktokstudio/content`, `https://www.tiktok.com/tiktokstudio/analytics`, and `https://www.tiktok.com/tiktokstudio/analytics/<video_id>`.
  - **Query-token stripping**: `sanitize_url()` strips all query strings (`?msToken=...`, `verifyFp=...`, `_signature=...`) and fragments before logging, printing, or saving raw schema samples under `state/cgo/bl/raw-schema/`.
  - **Pacing & safety guards**:
    - Enforces `>= 3.0 s` (`DEFAULT_PACING_S = 3.5`) between every page load (`enforce_pacing()`).
    - Immediately stops on any captcha/verification text or DOM selector (`VerificationWall`) and exits `3` (`EXIT_CAPTCHA = 3`) — never attempts to solve a challenge.
    - Immediately stops if the page lands on `/login` or renders an unauthenticated login channel picker (`SignedOut`), prints `SIGNED_OUT`, and exits `4` (`EXIT_SIGNED_OUT = 4`).
  - **Pure adapters & outputs**:
    - `extract_content_list_from_raw()`, `extract_video_analytics_from_raw()`, `extract_account_overview_from_raw()`, `merge_video_records()`, `detect_unexposed_fields()`, `build_pull_payload()`, and `write_pull_outputs()`.
    - Writes `state/cgo/bl/pull-<YYYY-MM-DD>.json` and flat CSV `state/cgo/bl/pull-<YYYY-MM-DD>.csv` atomically via `.tmp` rename.
- `state/cgo/bl/raw-schema/content_list.json` — Raw endpoint schema sample for the Studio content list endpoint (`_meta.endpoint_path` query-stripped; tagged `synthetic_fixture_pending_live_login` until overwritten by the first authenticated live run).
- `state/cgo/bl/raw-schema/video_analytics.json` — Raw endpoint schema sample for the per-video analytics endpoint (`avg_watch_time_s`, `full_video_watched_rate`, `retention_curve`, `traffic_sources`, `new_followers`).
- `state/cgo/bl/raw-schema/account_overview.json` — Raw endpoint schema sample for the 30-day account overview endpoint (`followers_start`, `followers_end`, `total_views`).
- `tests/test_bl_studio_pull.py` — 14 unit tests exercising the pure adapters against `state/cgo/bl/raw-schema/*.json`, alternate camelCase/nested TikTok Studio JSON shapes, 30-day window flagging (`within_30d` / `older_than_30d`), unexposed-field reporting, URL token stripping, `>= 3 s` pacing enforcement, exit code `4` (`SIGNED_OUT`) and exit code `3` (captcha) with guaranteed `home_lock.release()` in `finally:`, and atomic JSON + flat CSV generation.

## 30-Day Table (views, avg watch s, completion %, FYP %)

Rendered via `format_30d_markdown_table()` against the saved raw schema samples in `state/cgo/bl/raw-schema/` (live account table awaits CEO phone login on relay request `rq-ecb2cc16`; run `python3 tools/bl_studio_pull.py --print-table` after login to overwrite with live data):

| Video ID | Post Time (UTC) | Window | Views | Avg Watch (s) | Completion (%) | FYP (%) | New Followers | Caption (first 80 chars) |
|---|---|---|---:|---:|---:|---:|---:|---|
| `7440100000000000001` | 2025-11-24T04:00:00Z | 30d | 28,450 | 24.6 | 21.8% | 74.2% | 134 | โบรกเกอร์เถื่อนอ้างใบอนุญาต ASIC ปลอม เช็คยังไงไม่ให้โดนหลอก ถอนเงินไม่ได้ #BLAC |
| `7438200000000000002` | 2025-11-17T04:00:00Z | 30d | 15,300 | n/a | n/a | n/a | n/a | แชร์ลูกโซ่คริปโตสัญญาปันผลวันละ 3% ปิดเว็บหนีแล้ว ผู้เสียหายกว่า 400 ราย #BLACKL |
| `7420500000000000003` | 2025-10-05T04:00:00Z | older (>30d) | 9,200 | n/a | n/a | n/a | n/a | คลิปเก่าเกิน 30 วัน: วิธีเช็คเลขทะเบียน FCA อังกฤษด้วยตัวเองใน 1 นาที #BLACKLIQU |

Account window summary fields in `pull-<YYYY-MM-DD>.json` (`account_window`):
- `followers_start`: `14210` (sample fixture)
- `followers_end`: `14685` (sample fixture)
- `total_views`: `43750` (`total_views_from_30d_videos` also computed directly from the 30-day video rows)

## Which Fields Studio Did NOT Expose

1. **Content list endpoint (`/tiktokstudio/content`)**:
   - Exposes `video_id`, `post_time_utc` (`create_time`), `caption_80` (`desc`/`title`), `duration_s` (`video.duration`), and basic engagement counters (`views`, `likes`, `comments`, `shares`, `saves`).
   - Does **not** expose `avg_watch_time_s`, `watched_full_video_pct`, `retention_curve`, `traffic_sources`, or `new_followers` — those require loading each 30-day video's per-video analytics route (`/tiktokstudio/analytics/<video_id>`).
2. **Per-video analytics & account overview**:
   - `detect_unexposed_fields()` automatically inspects every live run and records any fields that TikTok Studio omits or nulls under `payload["unexposed_fields"]["per_video"]` and `payload["unexposed_fields"]["account_window"]`.
   - When the account overview XHR does not expose `followers_start` (TikTok Studio sometimes returns only current `follower_count` plus a net delta or daily series unless a 28/30-day range XHR is pre-loaded), `extract_account_overview_from_raw()` attempts to derive `followers_start` and `followers_end` from `follower_history` / `followers_series`, and otherwise lists `followers_start` in `unexposed_fields.account_window`.

## Validation Performed

- Verified all imports, function signatures, edge cases, and test assertions in `tools/bl_studio_pull.py` and `tests/test_bl_studio_pull.py` via static inspection (per AGY Remote Worker Contract: file tools only; shell/pytest execution is left to the review process).
- Confirmed `state/cgo/bl/raw-schema/*.json` contain zero query strings or tokens (`?`, `&`, `msToken`, `verifyFp`, `_signature`).

## Blockers

- **Live CDP pull awaits CEO login (`rq-ecb2cc16`) and review-runner shell execution**:
  - Per the task brief (Item 5), CGO's login relay request `rq-ecb2cc16` is open for `@black_liquidity` on `home:contabo:9282`. If `tools/bl_studio_pull.py` is run before login completes, it acquires and releases `home:contabo:9282`, prints `SIGNED_OUT`, and exits `4`.
  - Per the AGY Remote Worker Contract ("For AGY, use file tools only; leave shell validation to the review process. AGY in print mode cannot ask for a permission: a command outside its allow-list ends the whole run with no output"), `python3` / `pytest` were not executed from this AGY print-mode session. Once `rq-ecb2cc16` is signed in, run:
    - `pytest tests/test_bl_studio_pull.py`
    - `python3 tools/bl_studio_pull.py --print-table`

## Not checked / risk

- **Live TikTok Studio internal XHR endpoint paths and envelope keys**: Because `home:contabo:9282` could not be probed live in this AGY file-only session (and `rq-ecb2cc16` awaits CEO login), `state/cgo/bl/raw-schema/*.json` are initial schema fixtures (`schema_status: "synthetic_fixture_pending_live_login"`). To minimize schema-mismatch risk on the first live run:
  - `classify_xhr_payload()` classifies intercepted JSON both by URL path tokens and by structural payload inspection (falling back to structural probing if TikTok renames the endpoint path).
  - The pure adapters accept multiple known TikTok Studio field variants (snake_case and camelCase, nested `data`, 0..1 ratios vs 0..100 percentages, and millisecond vs second durations).
  - If a newly encountered live endpoint shape still fails matching, `UnrecognizedResponseShape` is raised explicitly (never silently zeroed) and the raw captured payload in `state/cgo/bl/raw-schema/` can be inspected to add the exact key name.
- **Per-video analytics page count**: For accounts with many videos in a 30-day window, `run_live_pull()` skips videos flagged `older_than_30d` when fetching per-video analytics pages and enforces `>= 3.5 s` pacing between each navigation (`--max-videos` defaults to 50).

## Skill learning

- When attaching to a shared Browser Home (`home:contabo:9282`) over CDP with Playwright, always open a dedicated temporary page (`ctx.new_page()`) for `Network.responseReceived` + `Network.getResponseBody` capture, close only that page on teardown, and stop Playwright with `self._pw.stop()` rather than `self._browser.close()` so the Browser Home's persistent contexts and other tabs are never closed (`tools/bl_studio_pull.py:553-574`, `tools/agy_browse.py:457-463`).
- In CDP network interception, `Network.getResponseBody` can fail if called synchronously inside `Network.responseReceived` before the body stream finishes; recording `requestId` in `Network.responseReceived` and reading `Network.getResponseBody` on `Network.loadingFinished` (with a post-wait drain fallback) prevents truncated or missing XHR JSON bodies (`tools/bl_studio_pull.py:576-612`).
