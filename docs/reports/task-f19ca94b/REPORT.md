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
| `7710695534243187974` | 2026-11-21T18:36:55Z | 30d | 417 | n/a | n/a | n/a | n/a | n/a | หุ้นพังทั้งโลก แต่ทำไมทองคำถึงดิ่งเหว -43,500 จุด ($4,157 ลงมาแตะ $3,722) ลงมาพร |
| `7710652893585509652` | 2026-11-21T15:51:20Z | 30d | 343 | n/a | n/a | n/a | n/a | n/a | เดือนที่ทองคำดิ่งหนักสุดในรอบปี 2026 ร่วงลงมา -43,500 จุด ($4,157 ลงมาแตะ $3,722 |
| `7710212271481310516` | 2026-11-20T11:21:30Z | 30d | 0 | n/a | n/a | n/a | n/a | n/a | #MoonieXPoster |
| `7709956153014275349` | 2026-11-19T18:47:39Z | 30d | 0 | n/a | n/a | n/a | n/a | n/a | #MoonieXPoster |
| `7709739918775373108` | 2026-11-19T04:48:32Z | 30d | 339 | n/a | n/a | n/a | n/a | n/a | ทองดิ่ง -43,500 จุดใน 10 วัน ($4,157 ➔ $3,722) ใครเทรดกราฟเปล่าไม่เช็กข่าวเศรษฐก |
| `7709445921142082837` | 2026-11-18T09:47:46Z | 30d | 360 | n/a | n/a | n/a | n/a | n/a | เคยสงสัยไหม ทำไมตั้ง Stop Loss ไว้ที่แนวรับทีไร กราฟชอบทิ้งไส้ลงมาแตะจุดคัดลอสเป |
| `7709071237460348180` | 2026-11-17T09:33:46Z | 30d | 370 | n/a | n/a | n/a | n/a | n/a | ถ้าปล่อยให้พอร์ตติดลบ -50% คุณไม่ได้ต้องทำกำไรคืนแค่ 50% แต่ต้องทำกำไรถึง +100% |
| `7708759223013870868` | 2026-11-16T13:22:55Z | 30d | 413 | n/a | n/a | n/a | n/a | n/a | คนเทรดทองที่ถือออเดอร์ติดลบค้างคืน ไม่ได้เสียแค่ค่าธรรมเนียม Swap ตอนตีสี่ (และโ |
| `7707145234324737300` | 2026-11-12T04:59:54Z | 30d | 145 | n/a | n/a | n/a | n/a | n/a | เห็นแท่งเทียนสีเขียวพุ่งแรงแล้วรีบกด Buy ตามเพราะกลัวตกรถ แต่พอกดปุ๊บกราฟทุบกลับ |
| `7706942633687698708` | 2026-11-11T15:53:39Z | 30d | 53 | n/a | n/a | n/a | n/a | n/a | เห็นแท่งเทียนสีเขียวพุ่งแรงแล้วรีบกด Buy ตามเพราะกลัวตกรถ แต่พอกดปุ๊บกราฟทุบกลับ |
| `7706836748445175060` | 2026-11-11T09:02:45Z | 30d | 158 | n/a | n/a | n/a | n/a | n/a | คนที่พอร์ตพังยับหลังโดน Stop Loss ไม่ใช่เพราะกราฟแกล้ง แต่พอกราฟตัดขาดทุนปุ๊บ สม |
| `7706518231984409876` | 2026-11-10T12:26:48Z | 30d | 184 | n/a | n/a | n/a | n/a | n/a | ทำไมกดเข้าออเดอร์ทีไรได้ราคาแย่กว่าคนอื่นตลอด ปัญหาไม่ได้อยู่ที่มองกราฟผิดทาง แต |
| `7706378629835459861` | 2026-11-10T03:25:05Z | 30d | 165 | n/a | n/a | n/a | n/a | n/a | ปั้นพอร์ตมาทั้งเดือนแต่คืนตลาดในคืนเดียว เพราะเวลากำไรนิดเดียวรีบกดปิด แต่พอติดล |
| `7705923649861061909` | 2026-11-08T21:59:34Z | 30d | 85 | n/a | n/a | n/a | n/a | n/a | กำไรนิดเดียวรีบปิด แต่พอติดลบปล่อยลากจนล้างพอร์ต อาการนี้ไม่ได้แปลว่าเข้าออเดอร์ |
| `7696270171547110664` | 2026-10-13T21:39:06Z | older (>30d) | 26 | n/a | n/a | n/a | n/a | n/a | จีบียังมีใบอนุญาตไหม กูไปดูสิ่งที่วิกิเอฟเอ็กซ์ระบุไว้ ณ วันที่ 1 ต.ค. 2569 มาให |
| `7696267883713760520` | 2026-10-13T21:30:16Z | older (>30d) | 19 | n/a | n/a | n/a | n/a | n/a | ผมไปเจอโพสต์หนึ่งในเฟซบุ๊กที่ตั้งคำถามกับวิกิเอฟเอ็กซ์ ในโพสต์ติดป้ายว่าเนื้อหาส |
| `7696265373473197320` | 2026-10-13T21:20:30Z | older (>30d) | 14 | n/a | n/a | n/a | n/a | n/a | หนึ่งออเดอร์จ่ายจริงเท่าไหร่ กูเอาตัวเลขจากหน้าบัญชีของติ๊กมิลล์เองมาคิดให้ดู ณ |
| `7696497006512000263` | 2026-10-14T12:19:17Z | older (>30d) | 8 | n/a | n/a | n/a | n/a | n/a | เทรดเดอร์หญิงคนหนึ่งเล่าในโพสต์ว่า CXM Direct ไม่จ่ายกำไรบัญชี Cent เกือบ 6 ล้าน |
| `7693208243417402645` | 2026-10-05T15:37:13Z | older (>30d) | 398 | n/a | n/a | n/a | n/a | n/a | Weltrade ถูกร้องเรียนถอดเงินไม่ออก ?! #blackliquidity #wikifx #weltrade |
| `7688706319301250305` | 2026-09-23T12:27:25Z | older (>30d) | 503 | n/a | n/a | n/a | n/a | n/a | โบรคดังบิดเงินลูกค้า #blackliquidity #wikifx #โบรคเกอร์forex |
| `7687750111182605588` | 2026-09-20T22:36:56Z | older (>30d) | 395 | n/a | n/a | n/a | n/a | n/a | Rebate คืออะไร?! ไขข้อสงใสที่ทุกคนถามถึง #blackliquidity |
| `7687521664116018452` | 2026-09-20T07:50:29Z | older (>30d) | 344 | n/a | n/a | n/a | n/a | n/a | ออเดอร์ที่กดไม่เคยถึงจริง ?! #blackliquidity |
| `7687113817964301588` | 2026-09-19T05:27:46Z | older (>30d) | 465 | n/a | n/a | n/a | n/a | n/a | ชวนเพื่อนเทรด ผิดกฏหมายไหม?! #blackliquidity |
| `7686895495733660948` | 2026-09-18T15:20:30Z | older (>30d) | 382 | n/a | n/a | n/a | n/a | n/a | Forex 3d ตายไปแล้ว แต่ทำไมตัวอื่นยังอยู่ #blackliquidity #forex3d |
| `7667143014506073365` | 2026-07-27T09:50:53Z | older (>30d) | 429 | n/a | n/a | n/a | n/a | n/a | โค้ชจริง หรือ โค้ชปลอม #blackliquidity #forex3d #โค้ชสอนเทรด |
| `7652951329719061780` | 2026-06-19T03:59:52Z | older (>30d) | 978 | n/a | n/a | n/a | n/a | n/a | #blackliquidity #forex3d #dsi เตือน |
| `7652876945092349205` | 2026-06-18T23:11:13Z | older (>30d) | 24,954 | n/a | n/a | n/a | n/a | n/a | ยังจำได้ไหม #blackliquidity #forex3d #dsi |
| `7634089534006840597` | 2026-04-29T08:06:26Z | older (>30d) | 549 | n/a | n/a | n/a | n/a | n/a | #blackliquidity |
| `7633206505902214421` | 2026-04-26T22:59:59Z | older (>30d) | 941 | n/a | n/a | n/a | n/a | n/a | โค้ชบางคนไม่ได้ทำเงินจริงในตลาด #Forex #blackliquidity #โค้ชเถื่อน |
| `7632447064848239892` | 2026-04-24T21:52:57Z | older (>30d) | 3,671 | n/a | n/a | n/a | n/a | n/a | XM vs EXNESS #blackliquidity #brokers #xm #exness |
| `7624115562821602580` | 2026-04-02T11:02:22Z | older (>30d) | 472 | n/a | n/a | n/a | n/a | n/a | Demo หรือ Reals ?! วิธีเชค #blackliquidity #scam |
| `7622955246095961365` | 2026-03-30T07:59:49Z | older (>30d) | 988 | n/a | n/a | n/a | n/a | n/a | แร่ที่ทั้งโลกขาดมันไม่ได้ #blackliquidity |
| `7622178918690344212` | 2026-03-28T05:47:12Z | older (>30d) | 3,456 | n/a | n/a | n/a | n/a | n/a | ACT เหรียญจริงหรือแค่มาหยอก ?! #blackliquidity #scam #act |
| `7621361756446690581` | 2026-03-26T00:56:15Z | older (>30d) | 3,599 | n/a | n/a | n/a | n/a | n/a | ทรัพย์สินหน้าเก็บในปี 2026 #blackliquidity #gold #silver |
| `7616191798012153108` | 2026-03-12T02:34:06Z | older (>30d) | 1,082 | n/a | n/a | n/a | n/a | n/a | จบแล้วพ่อใหญ่ทรัมป์ #blackliquidity #สงคราม #ทรัมป์ |
| `7604803528766360852` | 2026-02-09T10:01:54Z | older (>30d) | 151,681 | n/a | n/a | n/a | n/a | n/a | รู้ไหม ?!! #blackliquidity #rebate |
| `7604500158365306133` | 2026-02-08T14:24:33Z | older (>30d) | 153,046 | n/a | n/a | n/a | n/a | n/a | ทรัมป์ประกาศบรรลุข้อตกลงกรีนแลนด์ #blackliquidity #ทรัมป์ #กรีนแลนด์ #นาโต้ #สงค |
| `7598276866448952584` | 2026-01-22T19:55:04Z | older (>30d) | 50,691 | n/a | n/a | n/a | n/a | n/a | เกิดอะไรขึ้น ?! #blackliquidity #exness #copytrade #ปิดบริการ |
| `7597953437430517010` | 2026-01-21T23:00:02Z | older (>30d) | 1,806 | n/a | n/a | n/a | n/a | n/a | ทรัมป์กำลังจะยึด GreenLand จริงหรือ ?! #blackliquidity #donaldtrump #greenland # |
| `7597915470162873608` | 2026-01-21T20:32:36Z | older (>30d) | 619 | n/a | n/a | n/a | n/a | n/a | เทรดบ่อย = แพ้ #blackliquidity |

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
