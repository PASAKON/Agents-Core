# Mimi page: asking Facebook communities for view-growth advice (CEO 14 Oct 2026)

**CEO rules (14 Oct, his words in Thai):** ask 1-2 groups a day, a different group each time, never the same group twice.
While our work is not good yet (it is not), we ASK how to get more views and whether there is a formula, let the group
critique, collect the data and use it for A/B tests ("you get better, we get better, win-win"). "Good" = a clip that goes
viral and starts to earn; only then do we TEACH instead of ask (share what we did).

**UPDATE 14 Oct 09:1x (CEO, read the draft): speak as a PERSON, not the Page.** Pronoun «หนู» (or «ผม») with ค่ะ, never «แอดมิน»; post from his own FB «แบบไม่ระบุตัวตน» (true anonymity only where a group's admins enable it); attach a real, CROPPED screenshot of our dashboard insights with the page name visible; no link unless asked. He wants to see the wording before it posts. Group 1 was posted as the Page before this rule.
**Finding 14 Oct:** Page quality shows Recommendations suspended (Settings → Page quality), 239 views in 28 days: probably why views are low; see `state/handoff/2026-10-14/cmo-c7879552.md`.

**How:** the Page «บ้านนี้มีมีมี่» (superseded by the update above) joins and posts, in the page's admin voice (ค่ะ), via
`tools/fb_cdp_do.py` on winbox :9281. Public groups let the Page in at once. No link in the post (offer it when asked).
Text passes `scripts/check-post-text.sh` + `CMO_Standard_HumanVoice_TH`; one ask per post; AI use stated; no numbers we cannot show.
Cadence: at least 2 h between two posts (Meta groups plan: at most 1 post per 1-2 h). Replies to people are quick and warm.

## Queue (search 14 Oct 08:2x Thai: Facebook group search, 5 queries; counts are what the search card showed)

| # | Group (id) | Members | When | Status |
|---|---|---|---|---|
| 1 | สร้างละครสั้นด้วย Ai หรือมือถือ แบ่งปันเทคนิค (2214946398974915) | 57k, 583 posts/day | 14 Oct 08:5x | **ASKED** https://www.facebook.com/groups/2214946398974915/posts/2539368299866055/ text `docs/scripts/community-asks/ask-1-ai-drama-techniques.txt` |
| 2 | ละครสั้นสะท้อนชีวิต (1539019761132557) | 6.2k, 253/day | HOLD 14 Oct | auto-post cron cancelled 09:05 Thai: the CEO asked to SEE the wording first (ค่ะ stays) and said to post from HIS FB anonymously. Texts: `ask-2-life-drama.txt` (as the Page, admin voice) and `ask-2-life-drama-anon.txt` (anonymous member voice, no link offer). Group 1's composer showed no anonymous option; check this group's composer read-only before any post |
| 3 | ละครAI หนังสั้น reel โปรโมทไม่อั้น (2462042090983645) | 6.1k | next | promo allowed: link in post is fine |
| 4 | คลิปสั้น คลิปReels สร้างรายได้Facebook (1654570511663221) | 4.7k | next | monetisation Q&A |
| 5 | ละคร หนังสั้น (741484657714148) | 62k | later | |
| 6 | มินิซีรี่ย์ละครสั้น (707391665395586) | 30k | later | |
| 7 | คลิป AI ละครสั้น AI หนังสั้น AI (358463722198695) | 280k | later | |
| 8 | คลิป AI ไทย (197865948739851) | 300k | later | |
| 9 | หนังสั้น AI (1220568428324578) | ? | later | |
| 10 | ละครสะท้อนสังคม ละครสั้น หนังสั้น (1208797609955012) | ? | later | |

Skip: groups for pushing each other's clips («ช่วยกันดันคลิป»), hiring/editing services, TV-drama fan groups.
Before each new group: read its About and rules, change the wording to fit it (never paste the same text twice).

## What the groups told us (fill in as replies arrive; every row feeds an A/B idea)

| Date | Group | Who (role) | Advice | A/B idea or action | Tried? |
|---|---|---|---|---|---|

## Switch to teaching when

A clip of ours goes viral AND monetisation starts (CEO's definition). Until then: ask only.
