# FB groups share — จุดจบของเจ้าหนี้นอกระบบ (task-708dd145)

CEO authorized 25 Sep 2026: "แชร์ลงกลุ่มให้เลย 10 กลุ่ม" — share the Page's live
Reel (https://www.facebook.com/reel/4560927164226012) into 10 already-joined
FB groups, one post per group. **HOLD issued by CTO 2026-09-25T01:23:06Z**
after the group4 post below: new research says 2-3 groups/day, not 10 in 3h;
CEO decides whether to continue today. All further posting stopped per that
instruction. This report is the per-group ground-truth table + the anomaly
found while verifying.

## Per-group table

| # | Group | URL | Identity | Status | Evidence | Post URL |
|---|-------|-----|----------|--------|----------|----------|
| 1 | ละคร AI ไทย \| ละครสั้น AI... | groups/1128465650898382 | Dorsine Gobb | **posted (real), content now unreachable** | Activity Log: "Dorsine Gobb ได้โพสต์ใน [this group]" at 07:45 — a genuine logged action. But since ~08:00 the group URL, the permalink, and a name search all return "เนื้อหานี้ไม่พร้อมใช้งานในขณะนี้" / no results, under both Dorsine Gobb and Page identity. Group appears gone/inaccessible. | facebook.com/groups/1128465650898382/posts/2542835299461403/ (unreachable) |
| 2 | ละครสั้น AI | groups/2241521005964979 | Dorsine Gobb | **NOT posted — failed silently** | Composer readback matched, publish click fired with no visible error, but: no pending-approval badge, no post in feed sorted newest, **no entry at all in Activity Log** for this group today. Ground truth (Activity Log) says the attempt never actually landed. | none |
| 3 | ละครสั้น | groups/720458009234748 | — | not attempted (real member, confirmed) | membership re-checked live: "เข้าร่วมแล้ว" | — |
| 4 | รวมละครซีรีย์ AI ฝีมือคนไทย | groups/1341293771473179 | Dorsine Gobb | **posted, pending admin approval** | Group shows "รออนุมัติจากผู้ดูแล / 1 โพสต์" badge; Activity Log has the full caption text logged at 08:21. Counts as done per task's pending-approval rule. | none (pending, not yet linkable) |
| 5 | AI Filmmakers Hub - Gumvue Studio | groups/533068934883217 | — | not attempted (real member, confirmed) | membership re-checked live: "เข้าร่วมแล้ว" | — |
| 6 | แชร์เทคนิค Ai ChatGPT... | groups/801149272689355 | — | **not a member — join reverted** | groups.json's 24-Sep "Joined instantly" was the known false-join bug. Rejoined live per CTO instruction with a coordinate click (ref-click no-op'd first, as expected) — flipped to "เข้าร่วมแล้ว" immediately, no approval/questions modal. Re-checked ~40 min later, before posting: back to "เข้าร่วมกลุ่ม" (Join). The join itself silently reverted. Not posted, not retried. | — |
| 7 | Google Flow Thailand Community | groups/1186370691006379 | — | not attempted (real member, confirmed) | membership re-checked live: "เข้าร่วมแล้ว" | — |
| 8 | Seedance 2.0 & 2.5 Community | groups/1405079694162137 | — | not attempted (real member, confirmed) | membership re-checked live: "เข้าร่วมแล้ว" | — |
| 9 | seedance 2.0 Ai Thailand | groups/1481374853552014 | — | not attempted (real member, confirmed) | membership re-checked live: "เข้าร่วมแล้ว" | — |
| 10 | Seedance 2.0 Community Thailand | groups/739851845673593 | — | not attempted (real member, confirmed) | membership re-checked live: "เข้าร่วมแล้ว" | — |
| sub | แจก Prompt Google Flow Thailand | groups/681574071631926 | — | not a member currently | live check: "เข้าร่วมกลุ่ม" (Join button), not used | — |

**Counts: 1 posted (unreachable) · 1 pending · 1 failed silently · 6 real-member groups not yet attempted · 2 not currently members (group6, substitute).**

## The anomaly (why this needed a HOLD)

Two separate, serious findings surfaced while verifying, beyond the CTO's
original ask about my `confirm_result()` check being wrong (it was — see
below):

1. **The whole browser session's active FB identity silently flipped from
   Dorsine Gobb to the Page** ("ละครสั้นคุณธรรม by ILAG Studio") at some point
   between the group1/group2 post attempts and my later checks — visible in
   the top-left hamburger menu switching from Dorsine's personal shortcuts to
   "แดชบอร์ดมืออาชีพ" / "ตัวจัดการโฆษณา" (Page professional-mode sidebar). I
   never asked for this switch. It explains why group1's and group2's pages
   started reading as "you're not a member" / "content unavailable" right
   after posting — the *Page* identity isn't a member of groups Dorsine
   personally joined. I switched back to Dorsine Gobb via the account
   switcher (confirmed: menu now shows "Dorsine Gobb" and her personal group
   shortcuts) and re-verified from there.
2. **Group 6's rejoin (done live, coordinate-click, confirmed "เข้าร่วมแล้ว"
   immediately) reverted on its own within roughly 40 minutes**, back to
   showing a Join button — before any post was attempted there. This is not
   explained by the identity flip (checked as Dorsine Gobb both times). I
   have no explanation for this and did not attempt to force it through a
   second time.

Both are new information, not just "your script's check was wrong" — they
suggest Facebook may be silently undoing some of this account's automated
actions (joins, and possibly the group2 post) rather than showing an
explicit warning/checkpoint the task told me to watch for. Flagging this
explicitly since it changes the risk picture for continuing tomorrow.

## Root cause of the original false "PUBLISHED"/"live" claims

`FBGroupBrowser.confirm_result()` in `tools/fb_group_share.py` matched
`document.querySelectorAll('a[href*="/posts/"], a[href*="/permalink/"]')` —
**any** such link already on the page, not one tied to the post just
submitted. It always found *something* (other people's posts already in the
feed) and reported "live" with a permalink that was never really ours. This
is documented below, not yet fixed (see Issues).

Its `PENDING_MARKERS` also didn't match Facebook's real wording. The actual
in-page pending indicator is a group-header badge — **"รออนุมัติจากผู้ดูแล /
N โพสต์"** — not the phrase `รอการอนุมัติจากผู้ดูแลกลุ่ม` the script searched
the post body for.

**Ground truth that actually works, used throughout this report:** Dorsine
Gobb's own Activity Log (`facebook.com/me/allactivity`) — it logs a genuine
"[name] ได้โพสต์ใน [group]" entry for a real post the moment it lands, and
shows the pending post's full text for one still awaiting approval. Nothing
else checked (feed scroll, sort-by-newest, permalink nav, group's own pending
badge) was as reliable on its own.

## Fix needed in the tool (not yet applied)

`tools/fb_group_share.py`'s `confirm_result()` and `PENDING_MARKERS` need a
rework before this script is trusted again — not done yet, since the CTO's
HOLD stops further posting anyway. Left as-is; flagging for whoever resumes
this task rather than half-fixing it blind. Concretely: (a) match the pending
badge text `รออนุมัติจากผู้ดูแล`, not `รอการอนุมัติจากผู้ดูแลกลุ่ม`; (b) for
"live", check `facebook.com/me/allactivity` for the caption's own text rather
than any `/posts/` anchor on the group page.

## Replay Script

- path: `tools/fb_group_share.py` (composer flow) — works for opening the
  composer, typing, and clicking publish; its *result-confirmation* logic is
  unreliable (see above) and needs the fix before the next run trusts its
  stdout.
- `check_replay_script.py tools/fb_group_share.py` → `ok`.
- brittle: `confirm_result()`'s anchor search (false positive, documented
  above); `COMPOSER_OPENER_TEXTS` needed a real-world addition
  (`เขียนอะไรสักหน่อย`, not the guessed `เขียนโพสต์อะไรสักอย่าง`) — fixed in
  this run.
- covers: opening a group, filling + verifying the caption text via
  paragraph-diff, waiting for the link-preview card, and firing the publish
  click. Does not cover: reading the actual outcome (see fix note above) or
  admin-approval-question dialogs (never encountered live).

## Files Changed
- `tools/fb_group_share.py` — new group-feed poster tool (composer flow
  works; result-confirmation logic flagged broken, not yet fixed)
- `tests/test_fb_group_share.py` — unit tests for the pure functions (7
  pass)
- `docs/scripts/fb-groups-ilag-captions/*.txt` — 10 per-group captions + 1
  substitute, each passing `scripts/check-post-text.sh`, built from the
  CTO's binding intro override (letter 95cbbb28)
- `docs/reports/fb-groups-ilag/groups.json` — added a `shared` field per
  touched group (1, 2, 4, 6) recording the verified outcome
- `docs/reports/fb-groups-share-banchi/REPORT.md` — this file
- `docs/reports/fb-groups-share-banchi/screenshots/*.png` — composer and
  verification screenshots

## Issues / Blockers
- **HOLD in effect** (CTO, 2026-09-25T01:23:06Z) — no further posting until
  the CEO decides whether to continue today at a slower pace (2-3
  groups/day per new research, not 10 in 3h).
- Group 1's group appears to have become fully inaccessible (to both
  identities) shortly after our post; cannot confirm the post is currently
  visible to anyone, despite the Activity Log proving the action was real.
- Group 2's post attempt failed silently — no user-visible error, but no
  server-side effect either. Not retried.
- Group 6's rejoin reverted on its own within ~40 minutes, unexplained.
- `tools/fb_group_share.py`'s live/pending detection is confirmed broken
  (see Root Cause above) and needs a fix before its stdout is trusted again.
- Never triggered a CAPTCHA, checkpoint, or explicit spam warning banner —
  the anomalies above are all silent (no UI told me anything was wrong),
  which is itself the concerning part.

## Notes for Reviewer
- The account (Dorsine Gobb, the clean/ad-capable profile) still looks
  healthy overall: home feed, notifications, and the 6 real-member groups
  (3, 5, 7, 8, 9, 10) all load and behave normally as of this report.
- Recommend fixing `confirm_result()`/`PENDING_MARKERS` in
  `tools/fb_group_share.py` (see Root Cause section) before the next episode
  resumes posting, and treating `facebook.com/me/allactivity` as the primary
  verification source, not the group page's own UI.
- Recommend re-checking group1's status and group6's membership again before
  ever posting there — do not assume either is safe/stable based on this
  session's transient reads.
