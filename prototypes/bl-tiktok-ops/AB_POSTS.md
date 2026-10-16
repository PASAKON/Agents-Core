# BL A/B post ledger (CMO)

One row per episode, in posting order. Arm A = headline plate over the first beats, arm B = today's look.
The CEO posts from the Drive `Finals` folders; the arm of a post is read back from Studio, never assumed.
Baseline before the test: the 5 posts of 19 Sep to 5 Oct sit at 337 to 481 views (Studio, read 14 Oct).

| # | EP | arm | posted (Thai) | TikTok id | length | 48 h views | note |
|---|---|---|---|---|---|---|---|
| 1 | EP58 | A | 5 Oct 22:37 | 7693208243417402645 | 01:35 | not read; 365 at 9 days (9 likes, 0 comments); 368 at 11 days (public, 16 Oct) | n=1. Arm settled 14 Oct from the Studio thumbnail: match to arm A at 46.5 s is 0.78, arm B is 0.42, every other final and an unrelated post stay at 0.26 to 0.49; a side-by-side sheet shows the headline plate in the thumbnail and not in B. |
| 2 | EP61 | B | 14 Oct 22:00 (17:00 CEST), live | 7696265373473197320 | 01:08 | 8 (public playCount, 16 Oct 22:13 Thai) | opposite arm to EP58 so the pairs alternate. Scheduled in Studio 14 Oct 04:20 Thai; the content list shows it at Oct 14, 5:00 PM, Everyone. Stamp 13 Oct 2569: must go out 14 Oct. Live confirmed 22:10 Thai: Studio row 2 views, profile grid shows it with no schedule-date label (EP59/EP60 still carry theirs); EP62 had 1 view at the same read |
| 3 | EP59 | A | 15 Oct 22:00 (17:00 CEST), live | 7696267883713760520 | 01:34 | read 17 Oct 22:00 Thai | caption data stamped 1 Oct 2569 (risk accepted by the CEO, Q-20261013-2044-865f). Scheduled 14 Oct 04:30 Thai; list shows Oct 15, 5:00 PM |
| 4 | EP60 | B | 16 Oct 22:00 (17:00 CEST), live | 7696270171547110664 | 01:30 | read 18 Oct 22:00 Thai | caption data stamped 1 Oct 2569 (risk accepted, Q-20261013-2044-865f). Scheduled 14 Oct 04:39 Thai by the CEO's tap on RUN-20261013-2136-69c9 (the classifier refused my own click); list shows Oct 16, 5:00 PM. Live confirmed 22:12 Thai 16 Oct: public /video/7696270171547110664 page loads, "12m ago", playCount 1 (BL browser :9282 down, read in a fresh headless browser, not Studio) |
| 5 | EP62 | B look (one arm, not in the A/B) | 14 Oct 20:00 (15:00 CEST), live | 7696497006512000263 | 01:07 | | CXM cent-account case, posted inside EP61's 48 h window (confound for pair 1). Scheduled 14 Oct 19:19 Thai; list shows Oct 14, 3:00 PM, Everyone, AI label ON. Live confirmed 20:1x Thai: the owner's profile grid shows it with no schedule-date label, while EP61/59/60 still carry theirs. 48 h read 16 Oct 20:00 Thai |

Reads: first pair (EP58 vs EP61) after 16 Oct 22:00 Thai; the real read on 18 Oct 22:00 Thai (2 posts per arm).
A gap of 2x or more between the arm averages counts. A difference inside the 337 to 481 band does not.
Fill the id, posted time and 48 h views from Studio after each post. Do not read the arm from a TikTok cover alone
unless the cover frame differs between the arms (EP58's does; check first).

Settings the three scheduled posts carry (set in Studio 14 Oct): privacy Everyone, no link, caption exactly as each CAPTION.md,
"AI-generated content" label ON for all three (CEO, Q-20261013-2114-267a, "Label ON for all three"), Disclose post content off,
Audience control off, High-quality uploads on. EP58's label was never read, so pair 1 (EP58 vs EP61) may differ by that label as well as by arm;
the 18 Oct read (2 posts per arm, all three with the label) is the clean one.
Tools: prototypes/bl-tiktok-ops/studio_post_flow.py fills a post, studio_post_confirm.py re-checks and clicks Schedule once.

After each slot (22:10 Thai on 14, 15 and 16 Oct) read the Studio content list in a NEW tab: confirm the post went live (a scheduled post can fail to publish), then fill its id and posted time above and set the 48 h read date.

## Pair-1 read (EP58 A vs EP61 B), 16 Oct 22:13 Thai
- EP61 (B) at ~48 h: **8 views**. EP58 (A): 48 h never read; 365 at 9 days, 368 at 11 days. Gap ~45x in A's favour, but this
  pair cannot be read as an arm effect:
  - **Label confound:** EP61 carries the "AI-generated content" label ON; EP58's label was never read.
  - EP62 went out inside EP61's 48 h window (14 Oct 20:00).
  - EP58's number is a 9-11 day count, not 48 h.
- **Every post since 14 Oct is near zero, in both arms:** EP62 (B look) 3 at ~50 h, EP59 (A) 11 at ~24 h, EP61 (B) 8 at ~48 h,
  against the 337-481 baseline. The common factor is not the arm: all four carry the AI label ON (and EP59/60 carry stale
  caption dates). Reading: an account- or label-level drop, not an A/B result. The 18 Oct read will likely sit at this floor too;
  if it does, the A/B needs the label variable split out before any arm verdict.
- Source: public video pages read headless (`playCount` in the page JSON), not Studio (BL browser :9282 down).
