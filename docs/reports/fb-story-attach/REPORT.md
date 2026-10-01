# fb-story-attach — task-01700f3e

Goal: `FBPageBrowser.upload_story_video` must prove the Story video is attached
using a positive marker read off the live page (Chrome CDP :9230, Page
«ละครสั้นคุณธรรม by ILAG Studio»). Read-only probes plus `set_input_files`
only. Nothing published.

Video: `/Users/gob/MoonieXHQ/Work/task-16d79c84/story-ep4-1.mp4` (22,357,478 bytes;
identical-size copy at `$WORK_DIR/story-ep4-1.mp4`).

## Probe log

- P0 prep: `/json/list` on :9230 shows one story_composer tab (`8AEE7460`, url
  `.../latest/story_composer/?asset_id=1319535331240503&business_id=3502876973213389&ir_qe_exposed=1`)
  plus one about:blank tab. `tools/fb_page_post.py` has NO story_composer URL
  constant (only `STORY_HOME_URL_TMPL` = Business Suite Home, then clicks
  "สร้างสตอรี่"). Module docstring L88-97 documents the real route as
  `https://business.facebook.com/latest/story_composer/?asset_id={asset_id}&ref=biz_web_home_stories&context_ref=HOME`
  (confirmed live by an earlier task). Probe opens that URL in ONE new tab.
- P1 (read-only) open ONE new tab on the story_composer URL above, wait 7 s, snapshot.
  Result: composer empty. `video` 0, `img` 4, `canvas` 1, `progress` 1, `input[type=file]` **0**.
- P1b (read-only) look for a file input in every frame and open shadow root.
  Result: still **0**. The `input[type=file]` does not exist until the composer's own
  attach button is clicked. So step 3 as written ("`upload` on the composer's
  `input[type=file]`") has no input to target.
  **Deviation:** I clicked exactly one button, `เพิ่มรูปภาพ/วิดีโอ` (exact-text count 1), with
  Playwright `expect_file_chooser` armed. This is the same click `upload_story_video`
  makes in production, the label is not on the forbidden list, and it cannot publish.
  Nothing else was clicked, nothing typed. `chooser.set_files(story-ep4-1.mp4)` then ran.
- P2 attach + poll (2.5 s, 5 s, then every 10 s, stopped at t=75.9 s after 4 identical ticks).
  Full tick data: `$WORK_DIR/probe2_log.json` (not committed). Timeline below.
- P3 local ffprobe of the video: h264 1080x1920, duration 24.000 s. Matches the page's
  "0:24 วินาที" / "1080 × 1920" lines, so the marker belongs to OUR file.
- P4 leave: `goto about:blank` ok (a `dialog` handler accepting beforeunload was armed;
  whether it fired was not logged; the goto completed), then probe tab closed. `/json/list` afterwards: the original
  story_composer tab `8AEE7460` untouched + one about:blank. Nothing published.

## Timeline of one attach (seconds after `set_files`)

| t (s) | placeholder text | status line | `video` els | `img` | `progress` | remove control `ลบออก` | duration text |
|---|---|---|---|---|---|---|---|
| before | present | none | 0 | 4 | 1 | absent | none |
| 2.5 | **gone** | `กำลังอัพโหลดสื่อ` | 0 | 6 | 6 | present | none |
| 5.3 – 25.5 | gone | `กำลังประมวลผลสื่อ` | 0 | 6 | 6 | present | none |
| 35.5 | gone | none | **2** | 8 | 1 | present | `0:24 วินาที`, `1080 × 1920` |
| 45.6 – 75.9 | gone | none | 2 | 8 | 1 | present | same |

Reading: the placeholder disappears at ~2.5 s, while the file is still uploading. The
old check (placeholder gone on 2 reads 2 s apart) therefore "confirmed" at ~4 s, long
before the video was processed, and would equally confirm a failed upload. The remove
control `ลบออก` also appears at 2.5 s, so it is NOT an end-state marker either.

Before-attach text excerpt (empty composer, 7 of ~20 lines):
```
สื่อ
คุณสามารถอัพโหลดรูปภาพและวิดีโอได้สูงสุด 10 รายการ
ลากแล้วปล่อยรูปภาพหรือวิดีโอที่นี่
เพิ่มรูปภาพ/วิดีโอ
กำหนดเวลา / แชร์เลย / กำหนดเวลา
อัพโหลดสื่อเพื่อดูตัวอย่างสตอรี่ของคุณ
ยกเลิก / แชร์
```
After-attach text, diff vs before at t=35.5 s (lines added; the two lines above that
mention "ลากแล้วปล่อย…" and "อัพโหลดสื่อเพื่อดูตัวอย่าง…" are removed):
```
0:24 วินาที
1080 × 1920
ตัวเลือกการแชร์
ปิด
ลบออก
(ขณะนี้ใช้ได้เฉพาะ Facebook เท่านั้น)
```
Mid-upload diff at t=5.3 s (lines added): `กำลังประมวลผลสื่อ`, `ตัวเลือกการแชร์`, `ปิด`, `ลบออก`.
`<video>` details at t=35.5: 2 elements, `readyState` 4, `duration` 24.105 s, 720x1280,
`src` an https://scontent.* URL. New buttons at 35.5: `เพิ่มลิงก์`. New aria-label: `Video player`.

Screenshots (3, `$WORK_DIR`, not committed): `shot1_t2s.png`, `shot2_t45s.png`,
`shot3_final.png`. The Chrome viewport is only ~1000x508 and they show the
`ตัวเลือกการแชร์` panel, not the preview, and look the same before and after. They prove
nothing here; the DOM probes above are the evidence.

## Marker chosen and why

**A `<video>` element with `readyState >= 1` and finite `duration > 0`** (`story_attach_marker`
in `tools/fb_page_post.py`).

- Absent before attach (0), absent for the whole upload + processing window (t=2.5 to ~25.5 s),
  present from the first read after processing ended (t=35.5 s) and stable to t=75.9 s.
  It is the first signal that flips only when the video is processed, not merely picked.
- It is a real DOM property (decoded metadata), not Thai UI copy, so it needs no string match.
- It matches our file: page duration 24.105 s vs ffprobe 24.000 s, and the page text shows
  `0:24 วินาที` / `1080 × 1920`, which equals the file's 1080x1920.
- Rejected, with the reason measured:
  - placeholder text gone: flips at 2.5 s, mid-upload (this was the bug).
  - remove control `ลบออก`: present from 2.5 s, mid-upload.
  - `progress` count back to baseline: also flips at the end, but baseline is 1 and a
    plain page can show it with nothing attached, so it is weaker than the video.
  - file name / "100%": never appears in the page text (`filename_in_text` False on every tick).
- Vetoes (can only say "no", never "yes"): placeholder still shown, or either busy line
  `กำลังอัพโหลดสื่อ` / `กำลังประมวลผลสื่อ` still shown. The marker must also hold on 2
  consecutive reads 2 s apart (existing rule, kept; a flicker resets the count).

## Code change

- `tools/fb_page_post.py`: constants `STORY_PLACEHOLDER_TEXT`, `STORY_ATTACH_BUSY_TEXTS`,
  `STORY_ATTACH_STATE_JS`; pure `story_attach_marker(body, videos)`; `upload_story_video`
  polls it. Log line kept: `upload_story_video: attach confirmed, marker=<marker>`
  (the old `snippet=` was always `''` live, so it is replaced by the marker). Timeout line now
  says what was missing and prints `placeholder_gone`. Module docstring bullet and the
  `run_story` refusal text updated (they said UNVERIFIED LIVE / filename+100%).
- No new publish/submit call site: the only `click` in `upload_story_video` is the existing
  attach-button click. `publish_story` and `_find_publish_button_by_text` untouched.
- `tests/test_fb_page_post.py`: appended `_FakeStoryPage` and 11 new test cases (existing
  tests untouched): 7 parametrized no-marker cases return False after a 0.05 s timeout
  (placeholder-gone with nothing else, mid-upload, mid-processing, video still processing,
  video metadata not loaded, zero duration, placeholder still shown); marker present returns
  True and logs the marker; waits through upload+processing (5 reads); flicker resets the
  stable count (4 reads); pure `story_attach_marker` check.

## Verification

- `pytest tests/test_fb_page_post.py tests/test_fb_reel_post.py -q -o addopts=""`: 111 passed.
- Guard probe (not a unit test): re-imposing the OLD rule (placeholder absent == confirmed) makes
  the mid-upload, mid-processing and empty states all return True; the new rule returns False
  for the same three. So the new tests do discriminate the bug.
- P5 live run of the FIXED method (`FBPageBrowser.upload_story_video`, scratch script, new tab,
  same single attach click, `timeout_s=120`): log `upload_story_video: attach confirmed,
  marker=video element (readyState=4, duration=24.1s)`, returned True at **33.8 s** after
  set_files (the old code confirmed at ~4 s). Left via `about:blank`, tab closed; `/json/list`
  after: original composer tab `8AEE7460` + one about:blank. Nothing published.

## For the CTO before 19:00

- The real flow `run_story` now waits ~30 s (22 MB / 24 s file) for processing before the
  screenshot and publish; default `timeout_s` is 30 min (`frp.UPLOAD_TIMEOUT_S`), so no change needed.
- A different file size/length changes the wait, not the marker.
- Gate note: `git diff main...HEAD --name-only` lists 3 `.claude/skills/*/SKILL.md` files that
  are NOT from this task. They come from 3 skill-note commits already on the branch base
  (`b3d04732`, `ee3dd285`, `afe78370`) which `main` does not have. This task's own commits touch only the
  three allowed paths; check with `git diff afe78370..HEAD --name-only`.
