# CTO-FEEDBACK-2 — live end-to-end test APPROVED, plus a leak audit (CEO 2026-09-26)

CEO, verbatim: "อนุมัติทดสอบ โพสโดยใช้สคริปใหม่ โพสเสร็จแล้วรายงานผล หาลิ้ง และลบออกให้ด้วย
เชคว่า Script ทำงานถูกต้อง ไม่มีข้อผิดพลาด อุดทุกรอยรั่ว ที่มีความเสี่ยงว่าจะเกิดขึ้น"

This adds to the brief and CTO-FEEDBACK.md. It replaces nothing in them.

## 1. One real test post, then delete it

- Test clip: 5 s cut from the start of `/Users/gob/MoonieXHQ/Work/task-c2723478/out/taachang-FINAL-1080.mp4`
  (`ffmpeg -t 5 -c copy`, into your worktree's scratch area, not committed). Cover:
  `/Users/gob/MoonieXHQ/Work/task-c2723478/out/cover/poster-BIG-feedsafe.png`.
- Caption: `ทดสอบระบบ [TEST-<random 8 hex>]`. Put the same marker in the test comment.
- Run the full publish path: publish, then link, then the three-state check, then the
  first comment and the pin. Then delete the post.
- **New `--delete-test-post <permalink>`.** It deletes ONLY a post whose public caption
  contains a `[TEST-xxxxxxxx]` marker, and it re-reads the caption right before the click.
  Without the marker it refuses (exit 9). This is the guard that stops a real film being
  deleted. After deleting, confirm it is gone. Check the logged-out URL and the Business
  Suite row, and report both.
- Exactly one test post. If the first attempt ends `PUBLISHED-UNVERIFIED`, do not post a
  second one. Find the first one and delete it.

## 2. Leak audit: each risk gets a guard AND a test, or a line saying why not

List these in REPORT.md as a table: risk | guard in code | how it was tested (measured / not tested).
- publish clicked twice, or a rerun publishing the same video again. Guard: before publishing,
  refuse if Business Suite already shows a post whose caption's first line is identical,
  published in the last 24 h (`--allow-repost` overrides).
- wrong Page selected in the composer. The existing `confirm_page_name` is best-effort;
  make it a gate.
- comment posted as the personal profile instead of the Page; duplicate comment; pin missing.
- the 3 states from CTO-FEEDBACK.md. Show that the logged-out check fails on film 1's dead reel.
- deleting the wrong post. The marker guard, tested on film 2: it must refuse. Refuse only,
  never click delete on film 2.
- Chrome :9230 not running, 0 tabs, or logged out (login wall). Clear message and exit
  code, never a traceback.
- upload stuck under 100 %, caption read-back mismatch, cover not set. `set_cover` returns a
  bool today, but the run does not stop on False.
- the UI in English instead of Thai. List every Thai text selector you depend on in REPORT.md.
- anything else you find. Say it; don't hide it.

## 3. Report

The last lines of REPORT.md give the test post's permalink, the three-state result, the
comment link and its pinned state, and delete=confirmed plus how. Film 2's permalink and
its comment come after that. Every claim is marked measured or not tested.
