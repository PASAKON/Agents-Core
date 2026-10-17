# MimiPage — STATUS (Project Head #36c49776, reports to cmo-ef04792e)

Page «บ้านนี้มีมีมี่» (FB id 61594776486312). Brief: `state/ph-briefs/project_head-36c49776.md`.
Per-slot detail lives in `mimi-weekly-calendar.md`; this file holds milestones, blocker and decisions only.

## Ready gate (opened 2026-10-14 09:22 Thai)
| Item | State |
|---|---|
| Goal | in brief: run the page, Fri–Sun video, Mon–Thu poster, 19:30 Thai |
| Done-criteria | **CONFIRMED by cmo-ef04792e 14 Oct 09:24 Thai**: the 5 slots Wed 14 → Sun 18 Oct each published on the Page timeline (post URL as evidence) or cancelled by the CEO |
| Owner | project_head-36c49776 · C-level cmo-ef04792e |
| Host | Contabo (repo) + winbox (Flow, Chrome :9281 fb-dorsine, poster renderer) |
| Budget | ≤330 cr/episode, reshoot ≤3 shots/≤48 cr, 2nd test round needs new OK, reserve ≥250 (EP7 bend needs CEO «go ยิง») |
| Milestones | **CONFIRMED by cmo-ef04792e**, below |
| CEO GO | ongoing project; spends only after his per-item go (EP7 shoot) |

## Milestones (week 2, % = done ÷ 5)
| # | Milestone | State | Evidence |
|---|---|---|---|
| 1 | Wed 14 poster «เบื้องหลัง EP5» published 19:30 | **DONE** published 14 Oct 19:30 TH with the NEW logo (swapped on CEO's typed go); seen on the Page timeline at 19:41 («12 นาทีที่แล้ว», AI label) and in Content library «เผยแพร่แล้ว» | https://www.facebook.com/61594776486312/posts/122110710759492549 |
| 2 | Thu 15 EP6-teaser poster published 19:30 | **DONE** published 15 Oct 19:30 TH, checked 19:4x TH (post page shows the text; Fri + Sat still «กำหนดเวลาแล้ว») | https://www.facebook.com/61594776486312/posts/122111569269492549 |
| 3 | Fri 16 «ข่าวด่วนในบ้าน» clip published 19:30 | **DONE** published 16 Oct 19:30 TH as Reel, label «เนื้อหาที่สร้างโดย AI» shows; checked 19:4x TH (Sat EP6 still «กำหนดเวลาแล้ว» พรุ่งนี้ 19:30) | https://www.facebook.com/reel/1427604912167276 (post 122112019809492549) |
| 4 | Sat 17 EP6 Reel + first comment 19:33 | **DONE** published 17 Oct 19:30 TH as Reel, label «เนื้อหาที่สร้างโดย AI» shows; first comment (docs/scripts/mimi-ep6-first-comment.txt) posted as the Page 19:3x TH, 1 copy. **Not pinned**: the comment's menu offers only แก้ไข/ลบ on this Reel (fb_reel_post --comment-only pinned=false, menu re-read by hand) | https://www.facebook.com/reel/879429691858374 (post 122112021279492549) |
| 5 | Sun 18 slot: EP7 → 0-credit poster «เบื้องหลัง EP6» 19:30 | EP7 dropped by CMO 17 Oct per CEO-approved month plan Q-20261017-1011-3d5f (no new Mimi credits 18–24 Oct until Recommendations return). Poster rendered 17 Oct (winbox poster\out\poster-w2sun.png, EP6 still @144 s, facts from EP6 first comment); caption passes check-post-text. Scheduling waits the CEO's typed word in the PH chat | docs/scripts/mimi-post-w2sun-caption.txt |

Progress: 4/5.

EP7 $0 prep: `mimi-ep7-prep.md` (live balance 348 on 14 Oct 09:4x Thai; test shots 2+4; cut plan).

## Blocker
- CEO answers owed (asked by cmo-c7879552 in chat, 14 Oct morning): Page Recommendations suspended (review request?), group-2 wording + identity, Thu poster image swap, Fri clip go, EP6 go, EP7 go ยิง, video watermark pick. Waiting on CEO via cmo-ef04792e since 2026-10-14 09:2x Thai. Question cards: Q-20261014-0221-988c (group-2 wording + profile), Q-20261014-0221-5f44 (Thu/Wed poster swap), Q-20261014-0221-8d1b (Recommendations review); Group 2 QG-20261014-0225-db74: Q-20261014-0225-41ed (Fri clip go), Q-20261014-0225-3e78 (EP6 go, Hook B + cover 1), Q-20261014-0225-c960 (watermark v3). EP7 «go ยิง» = spend → needs his typed word in chat, carried by cmo-ef04792e, needed by Thu 15 evening TH; PH preps $0 only. Until answers: read-only, $0, no group post, no swap, no review request, no Flow spend, no relay (no account allowed yet).

## Working mode (CEO rulings 14 Oct, roles/project_head.md @2bd6e650)
PH leads: hands-on only for short browser jobs (≤10 min: read-backs, the FB writes that need the CEO's typed word in THIS chat). Long jobs (EP7 shoot + QC + cut, group-reply logging, watermark burn-in) → worker briefs (≤2). Messages to C-level only for blocked / shared resource / done. Commits go on branch ph-36c49776/mimi-2026-10-14 (PR #256), never local main.

## Shared resources in use
- winbox Chrome :9281 Browser Home fb-dorsine: 15:05–15:20 TH (group-1 replies read), 19:41–19:50 TH (Wed publish check), plus FB writes once the CEO's word lands
- winbox Flow Chrome :9226 (Mimi project 29b3326b): used 09:29–09:52 TH for upload + dry run, released

## CEO answers (via cmo-ef04792e)
- Recommendations restriction (Q-20261014-0221-8d1b): «ไม่น่าเกี่ยวกับเพจนี่นะ เพราะ dorsine green ไม่โดนอะไร» → no review request, no digging.
- Group 2 (Q-20261014-0221-988c): option 1, his personal profile, profile name not given yet → no post until named.
- Watermark (Q-20261014-0225-c960): «ขอดูก่อน» → no burn-in.
- +50 credits (298 → 348) source unknown; plan with 298.

## Decided for CEO
- 14 Oct: EP7 voices = prompt-line voices as in EP1–6 (no Flow character generator); Riao = warm slow sleepy mid-low male. Because: same method as the 6 aired episodes, $0, no face re-render. CEO ear-checks on the 360p test.
- 14 Oct: EP7 360p test = shots 2 + 4, not 1 + 4. Because: it covers mother__night (in 5 of 12 shots) as well as cat__riao, at the same 12 cr.

## 14 Oct 15:1x TH — group-1 replies + Page restriction
- Group-1 post (6 h old): **0 comments**. Nothing to log, no reply drafts. Group asks paused (decided for CEO: the Professional Dashboard says the Page is limited «เพื่อเป็นมาตรการความปลอดภัย เนื่องจากกิจกรรมของคุณอาจไม่เป็นไปตามกฎของเรา» — activity-based, and group joins/asks as the Page are the likeliest trigger).
- Restriction read (all read-only): violations none · account status none · Recommendations ถูกระงับ, no review button («ดูรายละเอียด» loops back) · 28 d: 460 views, 23 engagements, 3 follows. Options put to the CEO in chat 14 Oct: Meta Business Support ticket (needs his typed «go ยื่น Meta») or wait.
- 14 Oct 16:xx TH, CEO typed «go ยื่น Meta» + «go ยอมรับ Meta AI» in chat: switched fb-dorsine to Dorsine Gobb → business-support-home (ads-only; no Page issue, no cases; 3 portfolios clean) → Meta AI business assistant (terms accepted) → asked for review. Answer: no appeal button = automatic re-evaluation over time; Recommendation guidelines «มีนโยบายที่ส่งผลกระทบ», listed only generic categories; **human agent could not be connected** («ข้อขัดข้องในการยืนยันสิทธิ์»). Advice: original content, remove clickbait/reposts. Switched back to the Page (left nav «จัดการเพจ»). Page has 2 followers.
- 14 Oct 16:3x TH, CEO typed «go สลับโปสเตอร์ พุธ+พฤหัส» in chat: Wed (row nth 1, guard «เบื้องหลัง EP5») and Thu (nth 0, guard «ตอนใหม่ ทำไมมีมี่วิ่งไล่รถขายผัก») images swapped to poster-w2wed.png / poster-w2thu.png (new logo, top-right plate). One image each, AI label on, no interstitial. Re-read in a later call: Wed «วันนี้ เวลา 19:30», Thu «พรุ่งนี้ เวลา 19:30»; edit dialogs viewed by eye. Script generator: scratchpad mkswap.py (nth, guard, file).


## Week-1 asks from CMO (17 Oct)
- Recommendations review: **no review/appeal control exists** (17 Oct 19:5x TH re-read): settings?tab=profile_recommendations lists reasons only; settings?tab=profile_quality says «ไม่มีการละเมิดให้แสดง», account «ไม่มีข้อจำกัด», แนะนำ «ถูกระงับ»; dashboard banner «ดูรายละเอียด» leads to the same page. Same as 14 Oct.
- Insights EP1–EP6 (read 17 Oct ~20:0x TH; views / viewers / 3-s views / 1-min views): EP1 2 Oct 71/20/24/7 · EP2 3 Oct 40/7/9/3 · EP3 4 Oct 30/6/9/3 · EP4 9 Oct 50/13/16/5 · EP5 10 Oct 33/6/11/2 · EP6 17 Oct 6/0/0/0 (≈30 min old) · recap 11 Oct 36/6/11/4 · Fri news 16 Oct 10/3/4/0.