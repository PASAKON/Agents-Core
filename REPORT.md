# REPORT task-944f4c3e

## Summary
Read-only pass over the 7 YouTube channels of pass.gob1@gmail.com in Studio (winbox Chrome, CDP 9226, own tab). All 7 channels read. Window: 13 Oct - 9 Nov 2026 (Studio "last 28 days"). Nothing posted, edited or typed.

## Channel table (Studio Analytics, last 28 days)

| channel | subs | views 28d | watch h 28d | impressions 28d | CTR | monetization |
|---|---|---|---|---|---|---|
| Jade Tally (@JadeTally) | 28 | 6,040 | 313.0 | 68.4K | 3.2% | not eligible (subs 28/500; uploads 3/3 in 90d; qualified watch 148/3,000 h; Shorts views 0/3M) |
| Ghost Rules (@ghostrulestv) | 0 | 0 | 0.0 | no data (0 views) | no data | not eligible (subs 0/1,000; watch 0/4,000 h; Shorts 0/10M) |
| RED SEAL ARCHIVE (@redsealarchive) | 19 | 5,175 | 40.3 | 511 | 6.5% | not eligible (subs 19/500; uploads 0/3 in 90d; qualified watch 0/3,000 h; Shorts 0/3M) |
| ILAG Studio (@ILAGStudio) | 272 | 770 | 28.8 | 5.1K | 5.4% | not eligible (subs 272/500; uploads 3/3 in 90d; qualified watch 1,188/3,000 h; Shorts 0/3M) |
| TRADER UNCUT (@TRADERUNCUT) | 0 | 0 | 0.0 | no data (0 views) | no data | not determinable: Earn page shows "country of residence not set" and no eligibility card; subs 0 so not eligible by any tier |
| myPasakon (@myPasakon) | 1,605 | 796 | 9.7 | 6,240 | 5.9% | not eligible (subs 1,605/500 met; uploads 0/3 in 90d; qualified watch 83/3,000 h; Shorts 1.4K/3M) |
| Mine-TH (@mine-thminecraftserverthai3469) | 140 | 1 | 0.0 | 15 | 6.7% | not eligible (subs 140/1,000; watch 0/4,000 h; Shorts 0/10M) |

No channel showed "in YPP". Earn-page eligibility data is "as of 5 Nov 2026" (Studio's own date).

Other channel on the same account, not in the task list: personal channel @oopsminecraft646 (19 subs, 6 views / 0.0 h in 28 d).

## Files Changed
- REPORT.md - this report (no code changed)

## Commits
- see git log (one commit with REPORT.md)

## Tests
- ran: none (read-only browsing task)
- passed: 0
- failed: 0
- skipped: 0

## Issues / Blockers
- A Studio deep link `/channel/<UC>/...` for a brand channel returned "no permission" for ILAG and Mine-TH until the active channel was switched through the avatar menu > Switch account; the same link worked for the others. Switching is the only change made, see below.
- Analytics URLs of the form `/analytics/tab/overview/...` render "something went wrong"; `/analytics/tab-overview/...` and `/analytics/tab-content/...` work (impressions + CTR are on tab-content).

## Notes for Reviewer
- Route: no API path for Studio analytics; text reads over CDP (Playwright `connect_over_cdp`, own tab opened and closed in try/finally), no screenshots (0).
- Sources per field: subs = dashboard "current subscribers"; views and watch hours = tab-overview; impressions and CTR = tab-content ("การแสดงผลภาพปก", "อัตราการคลิกผ่านของภาพปก"); monetization = /monetization/overview eligibility card.
- myPasakon uses Studio's newer layout with no impressions card, so impressions and CTR (6,240, 5.9%) come from Advanced mode's table "total" row.
- RED SEAL views (5,175) are 99.8% Shorts.
- Active channel switching: the session's active channel was changed through Studio's switcher (and put back to the personal channel at the end, see below). No other state touched.
- PC lease: taken on winbox via the box's pc_lease.py (screen was FREE, Cookie Run not running), given back at the end. Work was headless CDP.
- Never touched MT5/terminal64, no reboot, no login typed.

## Not checked / risk
- Active Studio channel: switched back to the personal channel @oopsminecraft646 (UC3jHBRYkQ-21L-8ThCYOrPQ), verified by the landing URL. The first switch-back attempt timed out on navigation and a second one clicked the wrong item before the third succeeded; I did not verify the channel in other open tabs (Flow, a Studio video-edit tab held by another job), which may still show the identity they had.
- Numbers are as Studio showed at read time (Studio data can lag ~1-2 days and the dashboard rounds to K); Jade Tally's 68.4K and ILAG's 5.1K impressions are Studio-rounded. Mine-TH, Ghost Rules and TRADER UNCUT figures are tiny or zero and could be sampling noise. TRADER UNCUT monetization was not readable because the channel has no country of residence set.
- The "not eligible" labels are my reading of the thresholds Studio displayed; Studio did not print the words "not eligible" itself.

## Skill learning
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Step order 5 (YouTube Studio)] : Studio analytics URLs use a hyphen, `/analytics/tab-overview/period-default` and `/analytics/tab-content/period-default` (impressions + CTR are on tab-content); the `tab/overview` form in the 2026-10-09 field note renders "something went wrong" · evidence: task-944f4c3e, 4 channels read via tab-overview/tab-content
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Step order 5 (YouTube Studio)] : a brand channel deep link answers "no permission" until the active channel is switched with avatar > Switch account (worked for ILAG and Mine-TH after the click); `#avatar-btn` then text "สลับบัญชี" then the channel name · evidence: task-944f4c3e
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Step order 5 (YouTube Studio)] : a channel on Studio's newer "Channel insights" layout (myPasakon) has no impressions card; click "โหมดขั้นสูง" and read the table's total row (views, watch h, subs, impressions, CTR) · evidence: task-944f4c3e
- COSTLY [BROWSER_OPERATOR_Protocol_Playbook | no owner] : Python on winbox raises cp1252 UnicodeEncodeError printing Thai; set `PYTHONIOENCODING=utf-8` first · evidence: task-944f4c3e probe1
