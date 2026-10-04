# BL viral anatomy + 1-week A/B plan (CMO, 2026-10-01)

Labels: [M] measured in TikTok Studio · [S] seen in a contact-sheet frame (state/bl-tt-sheets/<id>.jpg) · [R] read from the
Whisper-small transcript (rough Thai, state/bl-tt-transcripts-2026-10-01.tsv) · [O] our estimate · [U] unverified.
Sheets were read by a subagent (all 13), first 3 s of each; the numbers below were copied from its report and the CSV, not re-measured by me.

## 1. Did we transcribe the viral clips?
Yes, 14 of 14 (Mac CTO, faster-whisper SMALL; medium thrashed the Mac's 8 GB). Quality: rough. Unusable: 9 Feb rebate 152K (4 garbage
segments), 20 Feb BTC 8.3K (mixed-script junk), 26 Mar slideshow is audio only. Medium re-run on the top 4 is in flight
(state/bl-tt-transcripts-top4-medium-2026-10-01.tsv). The two low pair partners (Greenland 22 Jan 1.8K, 10 Feb 1.7K) were not among
the 14 ids; asked the Mac CTO to add them (7597953437430517010, 7605244317824847125).

## 2. What the first 3 seconds look like [S]
| group | posts | lifetime views [M] | text on screen at frame 0 | frame 0 backdrop | avatar | length |
|---|---|---|---|---|---|---|
| Feb–Mar "headline template" | Greenland 8 Feb, rebate 9 Feb, Exness 23 Jan, XM 1 Mar, BTC 20 Feb, ACT 28 Mar | 153K · 152K · 50K · 44K · 8.3K · 3.2K (median ~47K) | yes: 2 lines, top third, one word red, stays all clip | a topical real image (Trump news photo, Exness logo, red chart, AI art) | yes | 59–85 s |
| later, no frame-0 text | Forex 3D 19 Jun, XM vs EXNESS 25 Apr | 23K (96% search) · 3.5K | no: text from 1 s | plain studio / logo wall | yes | 81–167 s |
| September | 18, 19, 20, 21, 23 Sep | 372 · 390 · 327 · 359 · 438 | no: caption from 1 s, chest height | plain red studio, or stock monitor clip with no avatar for 5 s | absent in 2 of 5 (20, 21 Sep), gone by 2–3 s in 2 more | 128–160 s |

Same claim, two outcomes: 9 Feb "ทุกออเดอร์ที่กด มีบางอย่างที่โบรกไม่อยากบอก" 152K vs 20 Sep "ออเดอร์ที่มึงกด ไม่เคยถึงตลาดสักครั้ง" 327.
The hooks' wording is not weaker in September [R]; the picture is different [S].

## 3. What this cannot tell us (three things moved together)
1. Calendar: all 6 headline-template posts are Jan–Mar (80% of the year's views); September is the only month with the new look.
2. Length: 59–85 s vs 128–160 s (length vs views: ≤70 s median 1,805, >120 s median 381 [M, older note §2d]).
3. Topic/news cycle: Greenland was a live news story. News posts without a hook picture did 0.7–3.6K.
So "the template made the hits" is a hypothesis, not a finding. The A/B below is built to split it.

## 4. Viral types worth repeating (from the evidence)
| type | evidence | repeat? |
|---|---|---|
| Live news about an entity (Trump, Exness) with the entity's picture at frame 0 | 153K, 50K | only when a real story exists; needs WikiFX-attributed wording |
| "Hidden cost you pay on every order" (rebate/spread) | 152K, 44K | yes, fits the channel; keep to attributed claims |
| Evergreen broker question (XM, Forex 3D) | 44K and 23K, 96% search; XM still 2.7K in the last 28 days | yes, long tail; the only thing earning views now |
| scam/crypto story with no broker | 8.3K, 3.2K | no |

## 5. The 1-week A/B
Variable: only the look of the first 3 s + the persistent headline. Same script, same voice, same lipsync, same length; two cuts.
- **A (viral spec, from the Feb sheets [S])**: 2-line headline in the top third at frame 0 (≤30 characters, one red word, includes a
  name), stays all clip; a topical real image behind the avatar at frame 0 (news photo, broker logo, chart); a new backdrop at 1 s and
  2 s; BL logo + date stamp as in the Feb posts.
- **B (control = today's look)**: plain studio close-up, no text at frame 0, caption from 1 s at chest height.
- 3 topics × 2 cuts = 6 posts: topic 1 = EP58 Weltrade (voice already paid, 95.7 s), topics 2–3 = two new WikiFX.th news items from the
  last 7 days (CMO picks; script_writer on the Max plan, ≤85 s).
- Schedule: one post a day, same hour; the first-posted arm alternates (T1 A first, T2 B first, T3 A first); at least 2 days between
  the two cuts of one topic. EP58 waits for the CEO's Weltrade IB answer; if it is "yes, we earn from Weltrade" EP58 is replaced by a
  third new topic (~$0.8 more).
- Read at 48 h from the Studio post detail page: avg watch (s), full-watch %, views, For You share. Pair verdict = A beats B on avg
  watch by ≥5 s and views ≥2×. Three pairs prove nothing statistically (3 of 3 by luck = 1 in 8); 3 of 3 means "run week 2 on a
  second sample", 2 of 3 = lean, ≤1 = the look is not the lever.
- **The scary result**: both arms stay ~300–500 views. Then the first 3 s is not what is holding the channel back (account reach is
  down 76% vs the prior 28 days [M]) and we stop polishing hooks.

## 6. Money [O, from EP58's real bill]
EP58 stage 2: fal $0.656 + OpenRouter $0.123 = $0.779 for 95.7 s with 47.6 s of lipsync. Two new topics at ≤85 s: ≈ $0.55–0.75 each.
Ask: ceiling $2.00 total for the two new topics' stage 2. Balances now: fal $6.83, OpenRouter $5.47. Cuts: Max plan, $0 cash.
Six cuts × the Arm-1 editor (about 1 h each at 80–95 s [O]), renders serialized on Contabo.

## 7. Needs a ruling
- Arm A needs a headline plate that the 25 Sep template (one caption band, no per-mode chip) does not have. Template change = Mac CTO's
  lane, with the CEO's OK.
- Hooks like "โบรกไม่อยากบอก" are a generalisation about brokers: the script standard's attributed-claim rule still applies to arm A.

## 8. Update: the spoken hooks (medium transcripts of the top 4, [R], state/bl-tt-transcripts-top4-medium-2026-10-01.tsv)
| post | first 3 s, spoken |
|---|---|
| 9 Feb rebate 152K | "มึงรู้ไหม ทุกออเดอร์ที่กดมีบางอย่างที่โบรกไม่อยากบอก" then "กูจะพูดตรงๆ…" |
| 8 Feb Greenland 153K | "ละครสั้นจบแล้ว ล่าสุดทรัมป์ออกมาประกาศเองว่า…" |
| 23 Jan Exness 50K | "พวกมึงได้ข่าว Exness กำลังจะปิดบริการ Copy Trade หรือเปล่า?" |
| 1 Mar XM 44K | "มึงเคยใช้ XM ไหม แล้วมึงรู้ไหมว่าบัญชี Standard ของ XM สเปรดสูง" |
All four open with a question or a "nobody tells you" line, name the subject inside 3 s, and run at 2 short lines per 3 s. September openings
("Order ที่มึงกด ไม่เคยออกไปถึงตลาดเลยสักครั้ง…" [R, small model]) have the same shape. So the spoken hook does not separate hits from
September; the on-screen picture does [S]. This supports building the A/B on the look and holding the script constant.

## 9. Decisions log
- 2026-10-01 CEO: approved $2.00 for stage 2 of two new topics (EP59, EP60). Weltrade: the channel never earned from it (EP58 gate cleared).
- 2026-10-01 CMO ruling for arm A layout: brand bug top-left with the date stamp, headline below it at ~12–26% of height, avatar lower
  (COMP/EVID, no FF with the plate on screen), as in the Feb sheets. Mac CTO builds it as {"headline": {...}, "beats": [...]} (a bare
  list = arm B).
- 2026-10-01 CEO: GB (Goldenburg / GB Finance, EP60): the channel never earned from it, IB gate cleared. EP59: the Facebook page is the source with no document attached, so PATTERN-3 reads "ในโพสต์ไม่เห็นหลักฐานแนบ ยืนยันไม่ได้" (eacdfce6).
- 2026-10-01 CEO "อนุมัติสำรอง": back up `Work/bl-ep58` to Drive `BACKUP/MoonieX HQ/Work-Archive` (the unique files only: cut finals and sheets, mattes, real stills, logs, briefs), verify every file by md5 read back by id, and only then delete the local working copies (drive/, media/, generator/). Not before BOTH EP58 cuts (arm A task-4305b93b, arm B v2 task-cc55e620) are accepted, because both still render from generator/ and media/. `drive/` is a plain copy of Drive folder 1usilCA-lYRs_XinTh11yjvwxSCjK0fp8 (md5-compare against its listing, no archive needed).
- 2026-10-01 stage 2 done (task-47ab0231): EP59 $0.9789 (94.08 s, Drive 1gkEN_ot34e1Gfto8y-3thB4rX8qzM29O), EP60 $0.7689 (90.23 s, Drive 1NI696i5XzNPgLLV2AMYiptjzglV7onIN); $1.7479 of the $2.00 cap.
- Headline picks (CMO, top option of each HEADLINE.md): EP58 "Weltrade ถูกร้องเรียน / ถอนไม่ออก?", EP59 "ใครตรวจ WikiFX / เว็บให้คะแนนโบรก?", EP60 "WikiFX: GB เคยมีใบ / ถูกเพิกถอนแล้ว" (swap to "GB ยังมีใบอนุญาต / อยู่ไหม?" if the CEO objects: the licence status was not checked at a regulator).

## 10. Resume list (for a session restarted by the G1 hub cutover)
1. Hold new workers until Mac CTO #e6754203 says the G1 window is over. Then say "G1 ready" only when task-4305b93b (EP58 arm A) is in review/merged.
2. EP58: review arm B v2 (cut/v2/frames, the 8 frames 0.0, 9.1, 9.3, 16.7, 59.9, 71.6, 74.4, 86.7 s; note 71.567 s is CURIOSITY-5, SUMMARY-1 starts at 74.42) and arm A (brand-mark opacity >= 95% every frame); then the archive-then-delete above.
3. EP59, EP60: create video_editor cut tasks (arm A + arm B each, one episode at a time while disk is tight; brief pattern = task-4305b93b), inputs = the two Drive folders above plus each episode's real/ folder (EP59 1F0i5tWOr_vdC4UKEpPNWOK9WzhErjNo1, EP60 1J1c6z00rgsD_YP-mnG6CkKsqRi3sI5TS).
4. Post schedule (one post a day, same hour, alternate arm order, 2+ days between the two cuts of a topic), read at 48 h from Studio post detail pages.

## 11. After the 2 Oct OOM (CMO c4432bad, 09:50 ICT) — state and rules
- The Contabo box has 7.8 GB RAM. 5 parallel HyperFrames renders (3 from task-cc55e620 + 2 from task-4305b93b) killed every tmux session at 19:53 CEST on 1 Oct. CEO rule from then on: at most ONE render or browser-heavy job at a time. Every `bl_compose` call is wrapped in `flock -w 7200 /opt/MoonieXHQ/Work/.bl-render.lock`; one driver per episode; never 3-4 drivers (this supersedes the "3-4 at once" line in the Cut skill note §9).
- EP58 arm B v2 (task-cc55e620, reopened and delegated 04:33 CEST): parts seg01-05, 11, 12 done and ffprobe-checked; windows 06-10 left.
- EP58 arm A (task-4305b93b, failed by OOM): beats.json + decisions committed, parts seg01 + seg12 done, windows 02-11 left. It is chained behind cc55e620 by a session-only poll (cron 99e823bf); if the session restarted, reopen_task + delegate_task it by hand once cc55e620 is in review, with the same one-render-at-a-time rule.
- Disk 6.6 GB free (the spawn floor is 5.0 GB). Reclaimed 832 MB by removing `Work/bl-ep58/media` (byte-identical to `generator/media`, nothing referenced it). The archive-then-delete of the rest of Work/bl-ep58 (CEO "อนุมัติสำรอง") still waits for both EP58 cuts to be accepted. EP59/EP60 staging (about 2.5 GB each) waits for that too; start with the cut whose post comes first in the schedule.

## 12. CEO orders 2026-10-04 (CMO, Contabo)
- "OK ทำต่อได้เลย": carry on with the EP58/EP59/EP60 cuts. The caption-over-mouth defect (text_over_face fails on every COMP beat; chin y ~1416-1461 vs legal pill 1430, so "under the chin" does not fit; raising the avatar 68%+166 px crushes evidence to ~220 px) is handled by moving the COMP caption ABOVE the avatar's head, avatar geometry unchanged (task-f35f2935, Claude-pinned; the first try, task-d4c1f234, was auto-routed to codex and stopped at its sandbox).
- "ทำเสร็จแล้วสำรองไว้บน Drive แล้วเคลียร์ข้อมูลงานของคุณในเครื่อง ประหยัด Disk เสร็จแล้วรายงานกลับไปที่ COO": when ALL of it is done, back up this session's work data (Work/bl-ep58, the bl59/bl60 work dirs, drive/ copies) to Drive `BACKUP/MoonieX HQ/Work-Archive`, verify every file by md5 read back by id, only then delete the local copies, then report to the COO (SomPong). Supersedes the "after both EP58 cuts accepted" wait in §9 only in timing: it runs after the whole job, not earlier, because the cuts still render from generator/ and media/.
