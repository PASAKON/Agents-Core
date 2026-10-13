# BL A/B post ledger (CMO)

One row per episode, in posting order. Arm A = headline plate over the first beats, arm B = today's look.
The CEO posts from the Drive `Finals` folders; the arm of a post is read back from Studio, never assumed.
Baseline before the test: the 5 posts of 19 Sep to 5 Oct sit at 337 to 481 views (Studio, read 14 Oct).

| # | EP | arm | posted (Thai) | TikTok id | length | 48 h views | note |
|---|---|---|---|---|---|---|---|
| 1 | EP58 | A | 5 Oct 22:37 | 7693208243417402645 | 01:35 | not read; 365 at 9 days (9 likes, 0 comments) | n=1. Arm settled 14 Oct from the Studio thumbnail: match to arm A at 46.5 s is 0.78, arm B is 0.42, every other final and an unrelated post stay at 0.26 to 0.49; a side-by-side sheet shows the headline plate in the thumbnail and not in B. |
| 2 | EP61 | B | scheduled 14 Oct 22:00 (17:00 CEST) | id given at publish | 01:08 | | opposite arm to EP58 so the pairs alternate. Scheduled in Studio 14 Oct 04:20 Thai; the content list shows it at Oct 14, 5:00 PM, Everyone. Stamp 13 Oct 2569: must go out 14 Oct |
| 3 | EP59 | A | scheduled 15 Oct 22:00 (17:00 CEST) | id given at publish | 01:34 | | caption data stamped 1 Oct 2569 (risk accepted by the CEO, Q-20261013-2044-865f). Scheduled 14 Oct 04:30 Thai; list shows Oct 15, 5:00 PM |
| 4 | EP60 | B | form filled, NOT yet scheduled (16 Oct 22:00 planned) | | 01:30 | | caption data stamped 1 Oct 2569 (risk accepted, Q-20261013-2044-865f). Studio form filled and checked; the classifier refused the final click, so the CEO is asked on RUN-20261013-2136-69c9. If it lapses, re-raise and keep the form tab open |

Reads: first pair (EP58 vs EP61) after 16 Oct 22:00 Thai; the real read on 18 Oct 22:00 Thai (2 posts per arm).
A gap of 2x or more between the arm averages counts. A difference inside the 337 to 481 band does not.
Fill the id, posted time and 48 h views from Studio after each post. Do not read the arm from a TikTok cover alone
unless the cover frame differs between the arms (EP58's does; check first).

Settings the three scheduled posts carry (set in Studio 14 Oct): privacy Everyone, no link, caption exactly as each CAPTION.md,
"AI-generated content" label ON for all three (CEO, Q-20261013-2114-267a, "Label ON for all three"), Disclose post content off,
Audience control off, High-quality uploads on. EP58's label was never read, so pair 1 (EP58 vs EP61) may differ by that label as well as by arm;
the 18 Oct read (2 posts per arm, all three with the label) is the clean one.
Tools: prototypes/bl-tiktok-ops/studio_post_flow.py fills a post, studio_post_confirm.py re-checks and clicks Schedule once.
