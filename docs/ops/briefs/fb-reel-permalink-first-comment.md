# Brief — fb_reel_post.py: the public link, then the page's first comment

**Role:** developer · **Repo:** Agents-Core · **Owner:** CTO cto-83a61127 · 2026-09-26

## Why (CEO, 2026-09-26)

1. Film 2 «ตาชั่งของเสี่ย» was posted as a Reel, but the posting report never gave the
   CEO a link. The CEO: after posting, the report must carry the real link to the post
   "เพื่อยืนยันว่าลงแล้วจริงๆ".
2. After every post, the Page must leave one comment that invites people to follow:
   "หลังจากที่ worker โพสคลิปเสร็จแล้ว ให้ comment ชวนเพื่อนติดตาม". Automatic if possible.

## What is true today (do not rediscover)

- Tool: `tools/fb_reel_post.py` — zero-model Playwright over CDP, Business Suite Reels
  composer. Tests: `tests/test_fb_reel_post.py` (10 tests).
- Page «ละครสั้นคุณธรรม by ILAG Studio»: Business Suite `asset_id=1319535331240503`,
  public page id `61594116376333`.
- Film 2 is live: `https://www.facebook.com/61594116376333/videos/1729583468302869/`
  (the CEO's share link `https://www.facebook.com/share/v/1Lv4x2SGQK/` resolves there).
  Business Suite gave `content_id 122117103027470545`, which is an **insights id, not the
  public video id**. Never report it as the link.
- Why no link came back: after the click on "แชร์" the tab stays on
  `business.facebook.com/latest/reels_composer/...`. `capture_post_publish_link()`
  found no `/reel/` anchor, printed `reel_id (best-effort): None`, and the run still
  **exited 0**. See `/Users/gob/MoonieXHQ/Work/task-c2723478/out/fb-publish.log`.
- Business Suite list with the new row (caption text + date):
  `https://business.facebook.com/latest/content_management/reels?asset_id=1319535331240503`.
  Its hrefs are `.../insights/object_insights/?content_id=...`.
- Chrome on `:9230` is running (profile `~/.fb-automation/chrome-profile`). It is signed in
  as a **personal** profile that admins the Page. Do not quit it, because you did not start it.
  If it has 0 tabs, run `curl -X PUT 'http://127.0.0.1:9230/json/new?about:blank'` first.
- **Never edit a published post.** On film 1, an edit broke the post (see the tool docstring).
  A comment is not a post edit.
- Python: `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python` (a sparse worktree has no .venv).

## Build

**A. Permalink, or not done.** After publishing, resolve the post's **public** URL. That is
a `www.facebook.com` link that someone who is not logged in could open. One way: take the
newest row from the Business Suite list, or from the page's public videos/reels tab. Match
it on the caption's first line. Open the candidate, and confirm the caption on the public
page. Print `PERMALINK <url>`. If there is no link within ~5 min, print `PUBLISHED-NO-LINK`
and **exit 6**. A publish run must never exit 0 without a link.
Expose the resolver on its own as `--resolve-permalink --caption-file X`, so it can be
proven on film 2 without re-posting.

**B. `--first-comment-file PATH`: comment as the Page, then pin.** Run it after A, on the
permalink.
- HARD gate, before submitting: the commenting identity shown in the composer must be the
  Page name. If you cannot switch to the Page or cannot verify it, do not submit, and
  **exit 7**.
- After submitting, read the comment back. Its author must be the Page, and its text must
  equal the file (normalize the way `captions_match` does). If the author is a person,
  delete that comment immediately and exit 7.
- Pin it ("ปักหมุดความคิดเห็น" / Pin comment). Print `COMMENT <permalink or id> pinned=<true|false>`.
- Idempotent: if an identical comment by the Page is already on the post, skip it
  (and pin it if it is not pinned). Never post twice.

**C. `--comment-only --permalink URL --first-comment-file PATH`.** Runs B alone on a post
that is already up.

**D. Tests.** Add pure-logic tests to `tests/test_fb_reel_post.py`: text normalization, the
duplicate-comment check, and the mapping from outcome to exit code. The existing 10 tests
stay green.

## Live acceptance (real, public; the CEO approved the text)

1. `--resolve-permalink --caption-file docs/scripts/taachang-reels-caption.txt` returns
   the `1729583468302869` URL.
2. `--comment-only --permalink <that URL> --first-comment-file docs/scripts/taachang-first-comment.txt`
   posts that comment **as the Page**, once, and pins it. Do not post anything else, and
   do not publish or re-publish any video.

## Report

- `docs/reports/<task-id>/WORKLOG.md`: append a line as you go.
- `docs/reports/<task-id>/REPORT.md`: files changed, test output, the film 2 permalink
  from step 1, the comment's link and its pinned state, the exact replay commands, and
  the Skill learning section.
- Budgets: ≤10 screenshots. Answer in text.
