# WORKLOG — task-cfdc75a8 (fb_reel_post.py: permalink + first-comment + test-post-and-delete)

Chronological. See REPORT.md for the final summary and leak-audit table.

## Build (prior session portion, before this file existed)
- Rewrote `tools/fb_reel_post.py` per `docs/ops/briefs/fb-reel-permalink-first-comment.md`:
  three-state `resolve_permalink` (VERIFIED/PUBLISHED-UNVERIFIED/FAILED per CTO-FEEDBACK.md),
  `do_first_comment` (identity-gated comment + pin), `--delete-test-post` marker guard.
- Rewrote `tests/test_fb_reel_post.py`: 54 tests (10 original + 44 new), all pure-logic,
  no live browser. Green at time of writing.
- Live acceptance, Part A: `--resolve-permalink --caption-file docs/scripts/taachang-reels-caption.txt`
  → `VERIFIED https://www.facebook.com/61594116376333/videos/1729583468302869/` (exit 0). Measured.
- Negative check (CTO-FEEDBACK.md requirement): film 1's dead reel
  (`https://www.facebook.com/reel/1104791208680559`) has no `og:description`/`name="description"`
  meta and a bare `<title>Facebook</title>`; `verify_permalink_content()` returns `False`. Measured.

## Test-post cycle, run 1 — refused before publishing
- Composer identity gate refused: `confirm_page_name()` returned the literal string `'​'`
  (zero-width space) instead of the Page name, so the hard gate correctly refused a good composer.
  Exit 10. Log: `scratchpad/test-post-run.log`.
  ```
  REFUSED: composer identity gate — expected Page 'ละครสั้นคุณธรรม by ILAG Studio', saw '​'
  composer opened; Page name shown: '​'
  EXIT=10
  ```
- Root cause (via `explore9_pagename.py`): the composer renders the "โพสต์ไปยัง" label twice
  (outer heading + inner label), each followed by U+200B before the real name. The original JS
  filtered only the exact heading string and picked up the zero-width-space line first.
- Fixed `confirm_page_name`: strip U+200B from every line before the emptiness/heading check.
  Verified fix with a standalone script before patching the real method: returned
  `'ละครสั้นคุณธรรม by ILAG Studio'`. No post existed yet at this point — nothing to clean up.

## Test-post cycle, run 2 — published, comment posted, verification raced
- Full publish pipeline ran clean: upload → caption → cover → advance-to-final-step →
  AI-label search (none found, expected) → set-public-audience → publish → resolve_permalink.
  Log: `scratchpad/test-post-run2.log`:
  ```
  composer opened; Page name shown: 'ละครสั้นคุณธรรม by ILAG Studio'
  upload_video: 100% confirmed, snippet='test-clip-5s.mp4\n1080 x 1920\n100%\nลบ\n​\nเพิ่มวิดีโอ\nเพิ่มรูปภาพ\nรายละเอียดคลิป Re'
  caption readback matches: True
  cover set: True
  AI label: no AI-content-disclosure control found in this composer
  audience set to Public: True
  screenshot saved: .../test-post-final-step-2.png
  PUBLISHED — clicked the real 'แชร์' button exactly once.
  VERIFIED https://www.facebook.com/61594116376333/videos/4116998775270501/
  REFUSED: posted, but could not locate the comment DOM node to verify author — needs manual check
  EXIT=7
  ```
- Live post: `https://www.facebook.com/61594116376333/videos/4116998775270501/`, caption
  `ทดสอบระบบ [TEST-a151e260]`. CTO independently confirmed this is public 18:5x via a logged-out
  `facebookexternalhit` fetch: `og:title` = `ทดสอบระบบ [TEST-a151e260]`.
- The comment text `ทดสอบคอมเมนต์ระบบ [TEST-a151e260]` WAS present in the page body right after
  submit (`body_contains_text` passed), but the post-submit `find_comment_block` lookup (used to
  verify the author and to pin) came up empty at ~2.5s — a timing race, not a wrong-identity event.
  My own later recon (`explore10_comment.py`, ~1 minute after submit) found the same comment's DOM
  node fine and its container text carried the Page name — but **this was a manual recon, not the
  same code path the tool itself runs**, and the CTO's own independent read of the live page still
  flags the comment's true author as unconfirmed ("it may be the CEO's personal profile"). Treat
  the comment's authorship as **not conclusively confirmed by the shipped code** — see REPORT.md.
- Fixed `do_first_comment`: retry the post-submit container lookup up to 4x/1.5s instead of once.
  Committed in `e472e6d3`. **Not re-verified live** — CTO-FEEDBACK-4 stopped all further browser
  work before a fresh publish+comment run could re-exercise this path.

## Pin-comment investigation
- `find_more_options_in` originally matched only `/เพิ่มเติม/`; a Page-authored comment's own menu
  button is labelled `"แก้ไข หรือ ลบนี้"` (Edit or delete this). Fixed to match either pattern and
  to search from `closest('[role="article"]')`. Confirmed live: locates exactly 1 button.
- That button's menu contains exactly 2 items: `"แก้ไข..."`, `"ลบ"` — no pin option.
- Exhaustively enumerated all 5 clickable controls in the comment's `[role="article"]` (identity
  badge, this menu button, like, react, reply) — no 6th hidden pin control.
- Site-wide `aria-label` scan for `/ปักหมุด/` on (a) the test post's permalink, (b) film 2's
  permalink (0 comments there), (c) Business Suite's home surface: zero matches anywhere.
- Conclusion: Facebook's Reels comment UI does not expose a pin control for the Page's own comment,
  as of 2026-09-26, on any surface checked. `pin_comment()` already degraded to `pinned=False`
  without crashing (matches the `pinned=<true|false>` contract); added an `Escape` press so a failed
  pin attempt doesn't leave the menu open. Committed in `e472e6d3`.

## Delete-test-post
- Negative guard test (film 2, no `[TEST-...]` marker in its real caption):
  ```
  $ python3 tools/fb_reel_post.py --delete-test-post "https://www.facebook.com/61594116376333/videos/1729583468302869/" --page-name "ละครสั้นคุณธรรม by ILAG Studio"
  REFUSED: no [TEST-xxxxxxxx] marker found in this post's LIVE caption — refusing to delete.
  EXIT=9
  ```
  Correctly refused. Film 2 untouched. Measured.
- Positive attempt (the test post, marker present):
  ```
  $ python3 tools/fb_reel_post.py --delete-test-post "https://www.facebook.com/61594116376333/videos/4116998775270501/" --page-name "ละครสั้นคุณธรรม by ILAG Studio"
  delete-test-post: marker confirmed [TEST-a151e260] on https://www.facebook.com/61594116376333/videos/4116998775270501/
  delete clicked: False
  EXIT=1
  ```
  Marker guard worked correctly. `delete_video_post()`'s click target
  (`[aria-label="ตัวเลือกเพิ่มเติมสำหรับวิดีโอ"]` → `"ลบวิดีโอ"`/`"ลบ"`) was wrong: that menu only
  has `"บันทึกวิดีโอ"` (Save video) and `"คัดลอกลิงก์"` (Copy link) — a viewer menu, not an admin
  delete. See REPORT.md for every surface checked afterward and why none worked within budget.

## CTO-FEEDBACK-3.md (time-boxed, 20 min)
- Tried the hinted path: switch active identity to the Page via the account-settings menu, then
  re-check the post's "…" menu. The account-menu click did not open a readable `[role="menu"]`
  (empty text, `switch item count: 0`), but the subsequent page load showed the Page's own feed
  composer placeholder ("คุณคิดอะไรอยู่ ละครสั้นคุณธรรม by ILAG Studio"), suggesting the active
  identity was already the Page. Re-checked the video-options menu under that identity: still only
  Save/Copy-link.
- Checked the Page's own timeline (`facebook.com/61594116376333`) for the test post — not found
  even after scrolling. (Likely needs the Reels-specific tab, not the main timeline; not checked —
  time-boxed.)
- Checked Business Suite's Content → "Posts and Reels" table
  (`business.facebook.com/latest/posts/published_posts/?asset_id=1319535331240503`): found the
  test post's row (id `122117274477470545`, distinct from film 2's `122117103027470545` in the
  same table — confirms the table lists all posts correctly). Its row-level "…" dropdown
  (`"เปิดดรอปดาวน์"`) opens a menu with exactly 2 items: `"รีแชร์ไปยังสตอรี่"` (Re-share to Story),
  `"คัดลอก ID คลิป Reels"` (Copy Reels clip ID) — no delete.
- Checked the row's title-cell click (possible detail panel) — no navigation, no delete-like
  aria-label appeared.
- Checked a "คลิป" (Clips) left-nav sub-item distinct from "โพสต์และคลิป Reels" — link not found by
  exact-text match; not investigated further (time-boxed).

## CTO-FEEDBACK-4.md — stop order
- CEO observed the worker looping and opening tabs without stopping. CTO closed 10 extra tabs,
  left one Business Suite tab open (not touched). All further Chrome :9230 work stopped immediately
  on this instruction. The test post will be deleted by hand by the CEO.
- Root cause of the tab leak: every throwaway diagnostic script in this session opened its own tab
  (`ctx.new_page()`) and only closed it (`page.close()`) at the very end of a linear script with no
  `try`/`finally`. At least 3 scripts this session raised an unhandled `TimeoutError` mid-script
  (an `element.hover()` blocked by a sticky table header, and two `element.click()` calls blocked
  the same way before a working `scroll_into_view_if_needed()` + click sequence was found) and
  never reached their closing `page.close()` — those 3 tabs leaked for certain; the CTO's count of
  10 suggests more leaked than I tracked, since I never checked tab count between runs. The shipped
  tool's own `FBReelBrowser` lifecycle (`fb.connect()`/`fb.new_tab()` wrapped in `try`/`finally`
  calling `fb.close()` in `run_publish`, `run_comment_only`, `run_resolve_permalink_cli`,
  `run_delete_test_post`) is correct and unaffected — this was a defect in my own disposable
  scratch scripts only, none of which are checked into the repo.
