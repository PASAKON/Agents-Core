# Facebook Thai AI Short-Drama Pages — Monetization Gate Measurement

Measured 2026-09-17, read-only, logged-in Chrome session (CEO's account, no
interactions taken — no likes/follows/comments/shares). Goal: settle whether
the Facebook Content Monetization gate (10,000 followers + 600,000
watch-minutes in a rolling 60 days) looks reachable for ILAG-style Thai AI
short drama, and whose eyeballs are actually watching.

**Everything under "estimated watch-minutes" is a CEILING, not a real
figure.** It assumes every viewer watched every second of a video, which
never happens. The real number is lower — probably much lower. Treat it as
an upper bound used to test whether the gate is even in reach, never as a
measurement of actual watch-minutes.

**No number below was guessed.** Where Facebook didn't show a value in the
rendered page, it is recorded as "not visible," per standing rule (ห้ามเดา).

---

## Pages measured

7 Thai pages actually posting AI-generated short drama, plus 1 foreign
contrast page. All found via Facebook's own page search (no Google fallback
needed — FB search worked directly while logged in).

| # | Page | URL | Followers | Category / Location signal | AI disclosed? | Last-2-wk active? |
|---|------|-----|-----------|------------------------------|----------------|---------------------|
| 1 | ละครสั้น AI. | facebook.com/profile.php?id=61591418074970 | 33K | Art · Ratchaburi, Thailand | No Meta "AI content" tag seen; only implied by name/hashtags | Borderline — most recent dated post found was 19 days old (29 Aug) |
| 2 | ละครสั้น Ai . | facebook.com/profile.php?id=61573202124955 | 5.6K | Performance art · ghost-story niche | **Yes** — "AI content" label | Yes — posted 1h before capture |
| 3 | ละครสั้น AI | facebook.com/profile.php?id=100076382971169 | 12K | Personal blog · Bangkok | No tag seen | Yes — posted 47m before capture |
| 4 | Natthika story - ละครสั้น AI | facebook.com/profile.php?id=61590287301190 | 15K | Video creator · Thailand | **Yes** — "AI content" label | Yes — posted 3h before capture |
| 5 | ละครสั้น AI | facebook.com/profile.php?id=61591373571715 | **44K** | Reel creator · Nonthaburi, Thailand | No tag seen (only #AI hashtag) | Bio claims "ตอนใหม่ทุกวัน" (new ep daily); exact last-post age not visible |
| 6 | ละครสั้น Ai (shortdramammaris) | facebook.com/shortdramammaris | 55K | Digital creator | No | **Excluded as peer — see below** |
| 7 | ละครสั้นai | facebook.com/profile.php?id=61592739899243 | 11K | Musician/band (category mismatch) · Bang Lamung, Thailand | No | Shows "Active" status; last sampled post low-engagement |
| 8 (contrast) | AI Short Drama (Myanmar) | facebook.com/profile.php?id=100083682112292 | 25K | Digital creator · Burmese-language | **Yes** — "AI content" label | Not checked |

**Page #6 is excluded from the peer set.** Its bio sells access to a paid VIP
Google-Drive membership (฿299 lifetime) carrying NC-20+ (adult) content, with
an explicit legal threat against redistribution and "updates 3-5 เรื่อง/วัน."
That is a paywalled/likely-reposted content-membership business, not an
ad-revenue Reels operation, and not something the CEO should model the FB
Content Monetization gate on. Its numbers are recorded for completeness but
not used in the arithmetic below.

A genuinely large **English-language** AI-drama page was not found inside
budget — search surfaced only a 32-follower Philippines-run reposting page
("theluciferisback": bio literally says "Uploading full video clips of AI and
short dramas," a repost/aggregator, not a creator). The best contrast
available was a **Burmese-language** AI-drama page (#8), used instead — see
"Whose eyeballs" below for what it does and doesn't tell us.

### Page Transparency — could not be measured for ANY page

The task asked for page-creation date and admin-location country from
"ความโปร่งใสของเพจ" (Page Transparency). **This was not reachable for any of
the 8 pages**, despite five different attempts:
`&sk=about_profile_transparency`, `&sk=about`, the numeric-ID path variant
(`/<id>/about_profile_transparency`), the legacy `page_transparency/?page_id=`
endpoint, and the profile's "•••" options menu (which only offered Sharing /
Invite friends / Safety / Report Page / Block — no transparency link). The
"Highlighted details" popover surfaced only a bio-style address (e.g.
"Ratchaburi, Thailand, 70150"), not a formal admin-country breakdown.

Best guess at the cause (not confirmed): all 8 pages carry informal categories
— Art, Personal blog, Digital creator, Musician/band, Reel creator — that
render more like personal profiles than classic Facebook Business Pages, and
the classic Transparency module may not attach to that hybrid type, or the
feature has moved somewhere this session didn't find in the time budget.

**Consequence: "months from page creation to today" and "followers/month"
cannot be computed for any page.** Guessing a creation date from the page ID
or follower count was considered and rejected — that would be exactly the kind
of estimate the CEO's standing rule forbids presenting as data.

---

## The numbers — last 10 Reels view counts per page (real, measured)

Facebook's Reels tab (`?sk=reels_tab`) renders 10 view-count numbers directly
as text with no scrolling needed — the one cheap, reliable, structured number
this UI exposes. It does **not** show per-reel dates, so these are the 10
**most recent** reels by tab order, of unconfirmed individual age.

| Page | Last-10-reels views (as shown, newest→oldest by tab order) | Sum |
|---|---|---|
| #1 ละครสั้น AI. (33K) | 334K, 304K, 210K, 10K, 22K, 15K, 57K, 67K, 81K, 392K | 1,492,000 |
| #2 ละครสั้น Ai . (5.6K) | 363, 308, 5.8K, 1.3K, 6K, 2K, 1K, 1.6K, 5K, 2.7K | ~26,071 |
| #3 ละครสั้น AI (12K) | 125, 464, 1K, 2.6K, 3.3K, 3.1K, 974, 2.7K, 1.5K, 2.4K | ~18,163 |
| #4 Natthika story (15K) | 153K, 196K, 202K, 1.3K, 7.8K, 3.3K, 7.7K, 6K, 6.2K, 61K | 644,300 |
| #5 ละครสั้น AI (44K) | **1.9M, 2.5M**, 167K, 3K, 13K, 168K, 7.6K, 8.5K, 118K, 7.8K | 4,892,900 |
| #6 shortdramammaris (55K, excluded) | 338, 16K, 208K, 259K, 84K, 35K, 34K, 39K, 34K, 9K | ~718,338 |
| #7 ละครสั้นai (11K) | 127K, 153K, 135K, 244, 256, 1.4K, 1.2K, 2.1K, 3K, 2.8K | ~426,000 |
| #8 AI Short Drama, Myanmar (25K) | 219, 174, 405, 201, 571, 466, 1.4K, 2K, 4.4K, 7.1K | ~16,936 |

Page #7's pattern is worth flagging on its own: three old reels at 127K–153K
views sitting next to seven recent ones in the low hundreds/thousands — reach
that spiked once and then collapsed, not a sustained pattern.

---

## Arithmetic for the 3 strongest pages

"Strongest" = highest sustained reach among the legitimate (non-excluded)
peer set: **#5 (44K)**, **#1 (33K)**, **#4 Natthika (15K)**.

For each, one representative reel's video length was measured directly from
the `<video>` element's real `duration` property after the browser loaded it
(not guessed, not read off a UI label — Facebook doesn't show duration as
text anywhere in this viewer). Only one reel per page was sampled this way;
video length is **assumed uniform across that page's other 9 reels**, which
is the biggest source of error in this section — flagged per page below.

### #5 — ละครสั้น AI (44K followers)
- Sampled reel: 24.07s, 77.5K reactions, 356 comments, 3.2K shares.
- Ceiling = Σ views × 24.07s = 4,892,900 views × 0.401 min ≈ **1,962,600
  minutes**, using only the 10 most-recent reels.
- **That ceiling alone is ~3.3× the 600,000-minute line — using ONLY 10
  clips.** Bio claims daily posting ("ตอนใหม่ทุกวัน"); if true, this page
  likely publishes far more than 10 reels inside any 60-day window, so the
  real 60-day post count — and therefore the real ceiling — is probably
  considerably higher than what's computed here. This computation is a
  **measured floor, not the full 60-day figure**, because only 10 reels'
  view data was collected.
- Follower gate (10,000): already cleared, 4.4× over.

### #1 — ละครสั้น AI. (33K followers)
- Sampled reel: 9.5s, 334K views, 10.6K reactions, 85 comments, 62 shares —
  dated 29 Aug 2026 (confirmed by matching caption against the one dated post
  visible on the main timeline).
- **This sampled reel is explicitly a trailer**, not a full episode — its own
  caption says "ตัวอย่าง ep14 ลง พรุ่งนี้" (episode 14 preview drops
  tomorrow) and "ดูน้ำจิ้มๆไปก่อน" (just a teaser). 9.5s is very likely
  shorter than this page's real average episode length.
- Ceiling using the trailer length literally: 1,492,000 views × 0.158 min ≈
  **236,200 minutes — only 39% of the 600k line.**
- Because the sampled length is almost certainly non-representative (a
  teaser, not a typical post), this specific number should not be trusted as
  this page's real ceiling — it's a likely understatement. Sampling a
  full-episode duration for this page was not affordable within the step
  budget; flagged as an explicit gap rather than corrected with a guess.
- Follower gate: cleared, 3.3× over. Also worth noting: the most recent
  dated post found was 19 days old — this page may not be posting weekly at
  present, despite its large past reach.

### #4 — Natthika story - ละครสั้น AI (15K followers)
- Sampled reel: 40.03s, 153K views (page's top reel), 3.4K reactions, 49
  comments, 15 shares.
- Ceiling = 644,300 views × 0.667 min ≈ **429,970 minutes — 72% of the 600k
  line**, using only the 10 most-recent reels.
- Follower gate: cleared, 1.5× over.
- Same caveat as #5: if this page posts frequently, the true 60-day reel
  count is probably above 10, so 72% is a floor, not the ceiling.

---

## Does the 600k gate look reachable, and in how long?

**Most important finding first: for the biggest page found (44K followers),
even the generous, full-watch-through CEILING from just its 10 most recent
clips already clears the 600,000-minute line by more than 3×.** That is
strong evidence the gate is reachable for a page performing at that level —
*if* real watch-through behaves anything like even a modest fraction of the
ceiling. The real (partial-watch) number is certainly much lower than the
ceiling; there is no way to measure actual average watch-percentage from a
public page view, so we cannot say by how much.

For the next two pages down (33K and 15K followers), the 10-clip ceiling
falls short of the line (39% and 72% respectively) — but both numbers are
understated for reasons explained above (a trailer-length sample; possibly
fewer than a full 60 days' worth of posts captured). A page performing at
Natthika's level, sustained over an actual 60-day window with its true post
count (likely more than 10), plausibly clears the line; the 33K page's
result is too distorted by the trailer-length sample to conclude either way.

**The follower gate (10,000) is the easy one.** 4 of the 6 legitimate peer
pages already exceed it (44K, 33K, 15K, 12K); only two small/niche pages
(11K borderline, 5.6K short) sit near or below it. The 600,000-minute watch
gate is the real constraint, not follower count.

**Timeline to clear both gates cannot be stated in months**, because Page
Transparency (creation date) was not reachable for any page measured — see
above. What can be said: several of these pages are demonstrably young
(numeric IDs in Meta's newer 2025-era ID range, several with very recent
first-post activity) and at least one (#5, 44K followers, viral reels in the
millions) is already producing individual clips whose ceiling alone would
clear the line — meaning for a page hitting that tier of hook/production
quality, the constraint is likely months, not years, but this is a
qualitative read, not a measured figure.

---

## Whose eyeballs?

**Evidence is thin — this is the single biggest shortfall against what the
task asked for.** The plan was to read the top ~10 comments on 2-3 of each
page's biggest posts and judge language mix. In practice, Facebook's Reels
comment panel would not open via automated click in this session (the click
either did nothing or advanced to the next reel in the feed) — three
different click strategies were tried and none reliably opened a comment
list. Given the step budget, this was not chased further, per the task's own
"do NOT burn steps fighting it" instruction.

What was captured, incidentally, from ordinary (non-Reels) timeline views:
- Natthika story page: one real audience comment, in **Thai**: "สมควร
  แก้วสุข · ต่อเลยค่ะ" ("please continue") — posted under a post that was 3
  hours old at capture time.
- No English or other-language comments were observed anywhere in this
  session's captures.

**With only one real comment sampled, this cannot support a Thai-vs-foreign
conclusion either way.** It is one data point, not a pattern. A follow-up
pass specifically built around opening comment lists (possibly needing a
human click rather than automation, or more step budget to find the right
selector) is needed before this question can be answered with any
confidence.

The Myanmar contrast page (#8, 25K followers, Burmese-language, "AI content"
labeled) is informative on a different axis: despite a follower count in the
same range as several Thai pages here, its Reels view counts topped out at
7.1K — far below the Thai pages' top performers. That doesn't prove where
Thai pages' viewers are, but it does show that follower count alone predicts
almost nothing about reach; a 25K-follower page can under-perform an
11K-follower Thai page (#7's early viral reels hit 127-153K) by more than
20×.

---

## What the good ones do that the bad ones don't

- **The strongest page (#5, 44K) pairs a provocative romantic/social-drama
  hook with an explicit "reflects real life, reflects society" framing**
  (สะท้อนชีวิต สะท้อนสังคม) and claims daily posting. High hook density +
  high claimed cadence is the one pattern shared by every big number in this
  dataset.
- **Natthika (#4) is the only page that explicitly asserts creative
  ownership** ("ทุกเรื่องราวเกิดจากความคิดของหนูเองค่ะ หนูใช้ AI เป็นแค่พู่กัน" —
  "every story is my own idea, I only use AI as a brush") and numbers its
  episodes (EP.3 รักร้าย) as a signal of an ongoing series arc, not one-off
  clips. This is the closest any page here comes to a defensible
  "quality, not slop" public position.
- **Page #1 runs a hybrid model**, using Reels/teasers ("ตัวอย่าง ep14")
  to funnel toward an external paid-subscription tier ("สมัครสมาชิก ได้ดูก่อนใคร")
  rather than relying on FB ad-share revenue alone.
- **Bad example (#7, 11K):** three old reels sit at 127-153K views, but the
  seven most recent sit in the low hundreds — reach that spiked once,
  algorithmically, and then collapsed. Its bio gives no differentiation
  signal (category is mis-set to "Musician/band"), consistent with a page
  that got lucky once rather than built a repeatable hook.
- **Worst example (#6, excluded, 55K):** abandons the FB ad-monetization
  path entirely in favor of external paywalled membership access to
  adult-rated content sold via Google Drive links, with an explicit legal
  threat against redistribution. This is a red flag pattern to avoid
  modeling — high follower/view numbers built on a business model
  fundamentally different from (and riskier than) the Content Monetization
  gate this task is measuring against.
- Common thread across every "small reach" page (#2, #3, #8): generic
  hashtag spam (#reelsviralシ, #shortdrama, #love) with no story-ownership
  claim, no episode numbering, no stated cadence commitment.

---

## What could not be measured, and why

- **Page Transparency (creation date, admin-location country) — 0 of 8
  pages.** Five different URL/menu paths tried; none surfaced the module.
  See dedicated section above.
- **Full 10-post table (date + length + views + reactions + comments +
  shares) for every page.** Only view-counts were captured at scale for all
  8 pages (cheap: one Reels-tab text read per page). Reactions/comments/
  shares/date/length were sampled for exactly 1 representative post on the
  3 strongest pages (plus partial data on 2 more), not the full 80 data
  points a complete 10×8 grid would need — each additional sample requires
  opening one individual reel (a real navigation, non-batchable, with a
  multi-second wait for `<video>` metadata to populate), and 80 of those
  would have blown the 60-step budget by a wide margin.
- **Individual reel dates.** The Reels tab grid shows view counts only, no
  dates. The only date recovered came from cross-matching one reel's caption
  against a dated post on the ordinary timeline (page #1, 29 Aug).
  Posting-cadence numbers ("posts per week") could not be computed with
  confidence for any page beyond a single "last active X ago" data point
  per page.
- **Comment-language sample (top ~10 comments × 2-3 posts per page).** See
  "Whose eyeballs" — the comment panel did not open reliably via automation;
  only 1 real comment was captured across the whole session.
- **Video length beyond one sample per strongest page.** `<video>.duration`
  only populates after the browser attempts to load/play the clip; each
  measurement is a real multi-second wait, not scriptable in bulk here.

### Is this scriptable for next time?

**Partially, and only the cheap part.** No public JSON/XHR endpoint was
found — Facebook's GraphQL calls for this surface are signed/obfuscated and
reverse-engineering them was correctly out of scope for a read-only research
task. What *is* stable and worth reusing is the Reels-tab view-count scrape,
which needs an authenticated `claude-in-chrome` browser session (not
headless curl) but costs one `get_page_text` call per page:

```
1. Navigate to  https://www.facebook.com/<page-url-or-profile.php?id=X>&sk=reels_tab
2. get_page_text  →  the trailing list of K/M numbers after "<Page name>'s reels"
   is the last 10 reels' view counts, newest-first.
```

That's the only piece worth calling "repeatable" from this session. Per-post
date/length/reactions/comments/shares and Page Transparency all required
manual per-post navigation and did not reduce to a stable recipe — a future
pass should expect the same cost each time, not zero.

No separate replay script file was written (task's TOUCHES restricted this
session to this one markdown file); the recipe above is everything a future
operator needs to repeat the cheap part.
