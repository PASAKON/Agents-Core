# REPORT — task-cfdc75a8: fb_reel_post.py permalink + first-comment + test-post-and-delete

Status: **stopped on CTO-FEEDBACK-4.md order.** All browser/Chrome work halted 2026-09-26.
Full chronology in `WORKLOG.md`. This file is the summary CTO-FEEDBACK-2.md and -4.md require.

## What shipped (committed, `e472e6d3` and earlier this task)
- `tools/fb_reel_post.py`: three-state permalink resolver (VERIFIED/PUBLISHED-UNVERIFIED/FAILED),
  identity-gated first-comment + pin, marker-gated `--delete-test-post`.
- `tests/test_fb_reel_post.py`: 54 pure-logic tests, no browser. **Green: 54 passed, 1 warning,
  0.20s** (re-ran this session via `.venv/bin/python3 -m pytest tests/test_fb_reel_post.py -q`).
- 3 live-bug fixes in `e472e6d3`:
  1. `confirm_page_name()` — strip U+200B before the empty/heading check (was refusing a correct
     composer because the label line was zero-width-space, not the real Page name).
  2. `do_first_comment()` — retry the post-submit comment-lookup 4x/1.5s instead of once (timing
     race between comment submit and DOM settle).
  3. `find_more_options_in()`/`pin_comment()` — also match a Page-authored comment's own menu label
     (`"แก้ไข หรือ ลบนี้"`), and press Escape after a failed pin so no menu is left open.

## Leak-audit table (per CTO-FEEDBACK-2.md)

| Risk | Guard in code | Status |
|---|---|---|
| Double-publish (click แชร์ twice) | `run_publish` clicks the real share button exactly once, no retry-on-ambiguity | Measured — run 2 published exactly once |
| Wrong-Page composer (posting as wrong identity) | `confirm_page_name()` hard gate, refuses before upload if name mismatches `--page-name` | Measured — run 1 correctly refused on a real defect (U+200B), fixed, run 2 passed |
| Comment posted as wrong identity | `do_first_comment()` posts from the same authenticated composer session as the publish; no separate identity switch | Not independently re-verified live after the retry fix — CTO's own read flags authorship as unconfirmed (see below) |
| Duplicate first comment | Tool posts once per invocation; no dedupe check against existing comments | Not tested |
| Pin-comment missing capability | `pin_comment()` degrades to `pinned=False` without crashing, closes any opened menu | Measured — confirmed no pin control exists in current FB Reels comment UI (exhaustive check, see WORKLOG) |
| Permalink falsely reported VERIFIED | `verify_permalink_content()` requires actual `og:description`/`description` meta content from a logged-out fetch, not just HTTP 200 | Measured positive (film 2) and negative (film 1 dead reel, no meta → correctly not VERIFIED) |
| Permalink state mislabeled FAILED when merely unverified | Three-state model: PUBLISHED-UNVERIFIED (exit 6) is distinct from FAILED (exit 8, requires positive evidence of failure) | Measured via code path design + tests; not forced live (would need simulating a network partition) |
| Deleting the wrong post | `--delete-test-post` refuses without a `[TEST-xxxxxxxx]` marker in the LIVE caption (re-fetched, not cached) | Measured — refused correctly against film 2 (no marker), exit 9; confirmed marker match against the real test post before attempting delete |
| Chrome not running / 0 tabs | `FBReelBrowser.connect()` raises a clear error on CDP connect failure | Not tested this session (Chrome was up throughout) |
| Logged-out session mid-run | Composer identity gate would refuse (no Page name shown) | Not tested |
| Upload stuck / never reaches 100% | `upload_video()` polls for the 100% marker with a timeout, does not proceed on timeout | Not tested this session (upload completed cleanly both runs) |
| Caption mismatch after paste | Explicit post-paste readback compare in the composer | Measured — `caption readback matches: True` both runs |
| Cover frame not set | Explicit post-set readback | Measured — `cover set: True` run 2 |
| UI in English instead of Thai (selector break) | All selectors are Thai-text/aria-label based; no English fallback | Not tested — UI was Thai throughout; an English UI would break every selector silently |
| Scratch-script Chrome tab leaks | **No guard exists.** Disposable diagnostic scripts (not part of the shipped tool) lacked `try`/`finally` around their Playwright page lifecycle | Measured as a real defect — see below. Shipped tool's own `run_*` entry points ARE correctly wrapped in `try`/`finally` and were not the source of the leak |

## Test-post runs

| Run | Outcome | Exit | Root cause / fix |
|---|---|---|---|
| 1 | Refused before publish | 10 | `confirm_page_name()` returned U+200B, not the Page name. Fixed (strip U+200B). Nothing published — no cleanup needed. |
| 2 | Published, comment posted, comment-author verification failed | 7 | Publish pipeline fully clean (upload/caption/cover/audience/publish/permalink all measured true). Comment-lookup race after submit; fixed with 4x/1.5s retry in `e472e6d3`, **not re-verified live** — stop order landed first. |

Live post from run 2: `https://www.facebook.com/61594116376333/videos/4116998775270501/`,
caption `ทดสอบระบบ [TEST-a151e260]`. Confirmed public by the CTO's own independent logged-out
fetch. **This post is still live — the CEO will delete it by hand per CTO-FEEDBACK-4.md. I did
not delete it and was ordered not to attempt further.**

### Comment-author bug (exit 7) — still open
The comment text was present in the page immediately after submit, but the shipped code's own
`find_comment_block` lookup (used to confirm authorship before reporting success) came up empty at
the first check (~2.5s). My own separate manual recon script, run about a minute later, found the
same comment and its container text carried the Page's name — but that was a hand-run check, not
the same verification the tool itself performs, and it happened well outside the tool's own timing
window. The CTO's own independent measurement of the live page still lists the comment's true
author as unconfirmed, raising the possibility it posted under the CEO's personal profile rather
than the Page. **I am reporting this as unresolved, not fixed-and-confirmed** — the retry fix in
`e472e6d3` addresses the timing race in the lookup, but was never exercised against a fresh live
publish before browser work was stopped.

## Why Delete was never found (5 UI surfaces checked, all before the stop order)

1. **Public permalink's "more options for video" menu** (`[aria-label="ตัวเลือกเพิ่มเติมสำหรับวิดีโอ"]`)
   — the method `delete_video_post()` targets this. Its actual menu contains only
   `"บันทึกวิดีโอ"` (Save video) and `"คัดลอกลิงก์"` (Copy link) — a viewer-level menu, not an
   admin delete. Confirmed twice (before and after an identity-switch attempt).
2. **Business Suite Content → "โพสต์และคลิป Reels" table row dropdown**
   (`business.facebook.com/latest/posts/published_posts/?asset_id=1319535331240503`) — found the
   correct row (distinct content id, confirming the table lists posts correctly), but its "…"
   dropdown has only `"รีแชร์ไปยังสตอรี่"` (Re-share to Story) and `"คัดลอก ID คลิป Reels"` (Copy
   Reels clip ID). No delete.
3. **That row's title-cell click** — no navigation, no delete-related control appeared.
4. **The Page's own classic timeline** (`facebook.com/61594116376333`) — the test post was not
   found there even after scrolling; likely needs a Reels-specific tab on that surface, which was
   not reached before the time box in CTO-FEEDBACK-3.md ran out.
5. **Identity-switch retry** — attempted switching active identity to the Page via the
   account-settings menu per CTO-FEEDBACK-3.md's hint; the switcher menu did not open readably, and
   evidence suggested the active identity was already the Page. Re-checking surface 1 under this
   identity gave the same Save/Copy-link-only menu.

No working delete path was found within the time available. `delete_video_post()` is committed
as-is (unchanged from before this task; never worked) — **not fixed.** This should be the next
task's starting point, once someone can confirm from the live UI which control actually deletes a
Reels video post (it may require the Business Suite mobile app, a different asset-level permission,
or a "Manage" sub-page not yet located).

## Tab leak (CTO-FEEDBACK-4.md)

The CTO closed 10 extra Chrome tabs and reported the CEO observed the browser "looping, opening
tabs without stopping." Root cause: every disposable diagnostic script this session
(`scratchpad/*.py`, ~35 scripts total, none committed) opened its own tab via `ctx.new_page()` and
only closed it (`page.close()`) at the very end of a linear script — with no `try`/`finally`.

At least 3 scripts crashed mid-run on an unhandled Playwright `TimeoutError` (a sticky `<thead>`
intercepting `.hover()`/`.click()` on the Business Suite data-grid before a `scroll_into_view_if_needed()`
workaround was found) and never reached their closing `page.close()` — those 3 tabs are confirmed
leaked. I did not track live tab count between runs, so I cannot account for the CTO's full count
of 10 from documented crashes alone; more likely leaked than I have direct evidence for.

**Fix status:** per CTO-FEEDBACK-4.md's instruction ("add the fix if small; otherwise list it here
as open") — I did not go back and patch the ~35 scratch scripts, because (a) none are committed to
the repo (they live only in the session scratchpad and have no lasting effect on the codebase), and
(b) doing so would require exactly the further browser/Chrome work this task is now stopped from
doing to verify. **Listed here as an open gap, not fixed.**

**Important distinction:** the shipped, committed tool (`tools/fb_reel_post.py`) is NOT affected.
Its `FBReelBrowser` class and all four `run_*` CLI entry points (`run_publish`,
`run_comment_only`, `run_resolve_permalink_cli`, `run_delete_test_post`) already wrap
`fb.connect()` / `fb.new_tab()` / `fb.close()` in `try`/`finally`. The leak was confined entirely to
my own throwaway investigation scripts, never to the production code path.

## Replay commands (everything measured above)

```bash
# tests
.venv/bin/python3 -m pytest tests/test_fb_reel_post.py -q

# permalink resolve (positive, film 2)
python3 tools/fb_reel_post.py --resolve-permalink "https://www.facebook.com/61594116376333/videos/1729583468302869/"

# permalink resolve (negative, film 1 dead reel)
curl -sL -A "facebookexternalhit/1.1" "https://www.facebook.com/reel/1104791208680559" | grep -i description

# delete guard, negative (film 2, no marker — must refuse, exit 9)
python3 tools/fb_reel_post.py --delete-test-post "https://www.facebook.com/61594116376333/videos/1729583468302869/" --page-name "ละครสั้นคุณธรรม by ILAG Studio"
```

## Outstanding work for the next session
1. Re-run the full publish→comment cycle once (or wait until the CEO deletes the current live test
   post, then use a fresh one) to confirm the `do_first_comment` retry fix actually resolves the
   exit-7 authorship-check race, with a fresh CTO-independent read of the resulting comment.
2. Find the real delete control for a Reels video post — none of the 5 surfaces checked exposed
   one; needs either a different UI surface or a permission/role check.
3. Patch the disposable scratch scripts' Playwright lifecycle to use `try`/`finally` — or, better,
   promote the useful ones (identity confirm, comment-menu enumeration) into a single reusable
   diagnostic script under `scripts/browser/` with proper cleanup, per the browser-operator skill's
   "leave a replay script behind" rule, which I did not follow this session because the target UI
   kept moving under active investigation.

## Skill learning
- WRONG [none — see MISSING below] : (none)
- MISSING [browser-operator §Leaving a replay script behind] : the skill says "if the flow could
  ever run again, the run is not finished until a script exists," but has no explicit rule that
  every throwaway diagnostic script MUST wrap its Playwright page/browser lifecycle in
  `try`/`finally` before it is ever run against a real CDP session — I treated disposable
  exploration scripts as exempt from cleanup discipline, which directly caused the tab-leak
  incident this task was stopped for · evidence: CTO-FEEDBACK-4.md ("Worker วนลูป เปิด tab ไม่หยุด"),
  ~35 uncommitted scratch scripts in this session's scratchpad, at least 3 confirmed leaked on
  unhandled `TimeoutError` · fix: add a hard rule — "every Playwright scratch script, however
  disposable, opens its page/context inside a `try` and closes it in a `finally`, no exceptions —
  a script that skips this is not allowed to run against a live CDP session."
- COSTLY [browser-operator §Select the browser before anything else / general exploration budget]
  : most of this session's browser-time cost was open-ended DOM exploration (looking for a delete
  control across 5 different FB/Business-Suite surfaces) with no step budget or exploration cap
  enforced, which is exactly the "expect to see runaway tab/script growth" failure mode the skill's
  cost-discipline sections warn about for screenshots but do not explicitly extend to raw tab count
  · evidence: CTO closed 10 extra tabs; ~35 scratch scripts written this session · prevented by: a
  hard cap (e.g. "no more than N live scratch-script tabs open at once; count with
  `tabs_context_mcp` before opening a new one") would have surfaced the pileup long before the CEO
  had to flag it by eye.
