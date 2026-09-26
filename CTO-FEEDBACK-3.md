# CTO-FEEDBACK-3 — the test post is public right now: delete it first, time-boxed

What the CTO measured (18:5x):
- Your run 2 published exactly one test post, and it is PUBLIC:
  `https://www.facebook.com/61594116376333/videos/4116998775270501/`. A logged-out
  facebookexternalhit fetch returns og:title "ทดสอบระบบ [TEST-a151e260]". Run 1 refused
  before publishing (identity gate), which is good.
- Run 2 ended `REFUSED: posted, but could not locate the comment DOM node to verify author`,
  exit 7. So a comment exists and **its author is unknown**. It may be the CEO's personal profile.
- You have 12 screenshots against a budget of 10, and 30 exploration scripts looking for Delete.

Order of work, now:
1. **Stop screenshot exploration.** Find controls by dumping text and aria-labels
   (`page.locator('[aria-label]')` / `inner_text`), not by images.
2. **Delete path to try first (NOT verified by the CTO, it is a hint):** on www.facebook.com the
   personal profile sees only a few menu items on a Page's post. Switch into the Page first
   (profile switcher, "สลับไปใช้ … / Switch to Page"), open the video URL above, then use the
   post's "…" menu and look for "ลบวิดีโอ" / "ลบ" / "Delete video". Switch back to the profile
   afterwards if you changed it.
   Second choice: the Page's own "จัดการโพสต์ / Manage posts" view while acting as the Page.
3. Before deleting, re-read the caption and require `[TEST-a151e260]` (your exit-9 guard). Never
   touch film 2 (`1729583468302869`).
4. The test comment on that post goes with the post when the post is deleted. If for any reason
   the post cannot be deleted, find that comment's author, and delete the comment if the author
   is a person and not the Page.
5. **Time box: 20 minutes from reading this.** If the post is still up by then, stop and write
   in REPORT.md exactly what you tried and what you saw. The CTO will ask the CEO to delete it by
   hand. Do not leave it without saying so.
6. After deleting, confirm it the two ways from CTO-FEEDBACK-2: the logged-out URL no longer
   returns that og:title, and the Business Suite row is gone.

Then finish the report. The comment-author check failed on the real page, so it is a bug to
fix (exit 7 was correct: it refused rather than guessing). Label it measured.
