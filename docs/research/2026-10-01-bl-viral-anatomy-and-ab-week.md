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
