# REPORT task-686a0caa

Completed the text-only EP04 production handoff for Jade Tally. Spending: $0. No network research, paid API, image generation, TTS, video generation, rendering or publishing was performed.

## Files changed
All files are staged inside the assigned worktree, under `docs/reports/task-686a0caa/`:
- [script/EP04-full-script.md](script/EP04-full-script.md): original Thai narration, ten three-minute beats, 120 individually timed shots using EP03 narrator/character line labels.
- [plan/EP04-FULL-SHEET.md](plan/EP04-FULL-SHEET.md): exact matching lines, type, time, retention cue, references and a Google Flow prompt or still compositing instruction for every shot.
- [plan/EP04-stills.md](plan/EP04-stills.md): 120 shot image prompts, comprising 102 first frames and 18 still plates, plus 19 new reference-plate prompts.
- [plan/validate_ep04.py](plan/validate_ep04.py): read-only structural validation.
- [REPORT.md](REPORT.md): this handoff, counts, continuity decisions, validation and limitations.

## Counts and rhythm
| Item | Result |
| --- | --- |
| Planned duration | 1,800 seconds, 30:00 |
| Beats | 10, each 12 shots / 3 minutes |
| Total shots | 120 × 15 seconds |
| flow | 102 |
| still+fx | 18 |
| still+fx share | 15% |
| Consecutive still pairs | 0 |
| Same effect on successive still shots | 0 |
| Initial hook | S001, first spoken challenge finishes by 00:05 |
| Planned retention turn | +12 seconds in every shot, maximum gap 15 seconds |
| Spoken characters | 17,497 including spaces and quotation marks, excluding speaker labels |
| Per-shot spoken characters | 120 to 161 |

Still shots: S005, S010, S015, S022, S027, S034, S041, S046, S053, S058, S065, S070, S078, S082, S089, S094, S101, S113.
Effects rotate in this order: mist, rain, falling ash, glow motes, jade dust, embers. Each has a slow camera instruction. All hooks, peaks, comic followers, active transactions, physical confrontations and the ending use flow.

| Ten-minute block | Peaks | Immediate comic followers |
| --- | --- | --- |
| 00:00-10:00 | S020 at 04:45; S032 at 07:45 | S021; S033 |
| 10:00-20:00 | S056 at 13:45; S076 at 18:45 | S057; S077 |
| 20:00-30:00 | S092 at 22:45; S108 at 26:45 | S093; S109 |

Times above mark shot starts; each payoff is planned at +12 seconds. Actual voiced timing remains unmeasured.

## Story and continuity decisions
- Opens at the pawnshop immediately after EP03. The envoy stalls Luo Yi while accomplices steal the egg, giving the confrontation a causal purpose.
- All ten EP04 outline beats retain their order and three-minute allocations. Ends on the Lin-sealed withdrawal-of-engagement letter and blood at its corner.
- EP04 does not retrieve or hatch the egg, explain Qingyan's motive, disclose the envoy's later identity, or resolve the Zhao family. These remain in the season outline's later episodes.
- Two powered abacus uses only: S028 initiates the failed appraisal, S029-S032 continue that single event and confirm one month lost; S075 costs one additional day. Warnings and Xuan's voice do not provide free appraisals. No profit restores lifespan in EP04.
- EP03 explicitly restores lifespan through profit, conflicting with the new rule. Its ending is the starting continuity, but EP04 does not repeat the restoration mechanism or claim an exact remaining-life total.
- EP03's calendar jumps to the seventh night without a complete daily ledger. EP04 avoids a numerical remaining-life balance and references the auction as a prior day, not definitively yesterday.
- The 10,000 target is new shop collateral/profit needed within three days, separate from the personal debt already paid in EP03. The shutdown is described verbally; there is no readable notice.
- Fang provides a separate 200-stone shop reserve. Entry cost was already covered separately. Bowl purchase 20, sale proceeds 200, profit 180, cash remaining 380, profit still needed 9,820. Abao loses his own funds; medicine money is not spent.
- Luo Mei is visible only in family-bedroom shots S039, S040 and S042. Her established age is left unspecified; every other person and all background extras are 18+.
- Xuan is voice-only. Prices and the letter's message are spoken, with no readable numbers, writing or hanzi in the imagery. Each prompt forbids duplicated named people and reflections that duplicate faces.

## New plates needed
All targets below belong in `/opt/MoonieXHQ/Work/cn-series/chars/states/` during later authorized media production. They are marked NEW in the shot pack and do not exist as deliverables from this task. Each creation prompt cites an existing reference path and distinguishes style/environment guidance from identity guidance.

| Planned plate | Purpose |
| --- | --- |
| luoyi__ep04_before_cost.png | EP03-ending hair and costume state |
| luoyi__ep04_after_cost.png | New right-temple white strand after month loss |
| envoy__ep04.png | Hooded envoy, cloud tiers, wrist scar |
| fang__ep04.png | Consistent Old Fang identity, subject to prior-face match |
| luomei__ep04_family.png | Family-only sister plate; prior approved face required |
| rival__ep04.png | Adult Zhao-employed appraiser |
| courier__ep04.png | Adult Lin courier |
| buyer__ep04.png | Adult medicine buyer |
| vendor__ep04.png | Adult junk vendor |
| broker__ep04.png | Adult gate-fee broker, distinct from EP03 lender |
| receiver__ep04.png | Adult auction receiver |
| porter__ep04.png | Adult auction porter |
| officer__ep04.png | Adult warehouse officer |
| token__ep04_blackcloud.png | Abstract three-cloud iron token |
| bowl__ep04_closed.png | Cracked bowl before opening |
| bowl__ep04_open.png | Matching fragments and exposed beast bone |
| letter__ep04.png | Abstract Lin seal, blank reverse, blood-marked corner |
| pawn__ep04_ransacked.png | Ransacked pawnshop main room |
| auctiongate__ep04.png | Closed underground auction stair and gate |

No egg plate is required for EP04: the egg remains offscreen after the theft, identified through witness descriptions and an empty transport box. No new Qingyan appearance is required; her letter drives the ending.

## Validation performed
- Read the season outline, EP04 outline, EP03 full script, EP03 builder and Jade Tally BRAND production rules. Followed the latest 30-minute instruction over the older ten-minute EP04 outline header.
- Ran `python3 docs/reports/task-686a0caa/plan/validate_ep04.py`: PASS. Checks 120 ordered unique shot IDs in all three documents; continuous 15-second timing; matching Thai lines; allowed shot types; percentage; still adjacency; effect alternation; slow cameras; hook/end type; six peak/comic pairs; two peaks per ten minutes; planned retention spacing; forbidden wording/punctuation; and reference-path existence with explicit NEW exceptions.
- Reference audit: 17 distinct existing reference filenames resolve; 19 explicitly planned new filenames. File existence does not establish visual suitability.
- Reviewed the original Thai narrative against all ten beats, the two-use lifespan ledger, the profit ledger, and EP05 spoiler boundaries.
- `git diff --check` passed. New files were additionally checked by the validator; they remain untracked for the launcher to commit.
- MAILBOX.md was absent on checks during the task. No STOP message was received.
- No brief-specific test suite was named. No unrelated repository tests were run for this text-only change.

## Not checked / risk
- This is a 30-minute timed script and prompt plan, not a voiced or rendered episode. A real read-through is required to fit individual lines and breathing at 9 to 11 characters per second. At 10 characters per second the text is about 29:10 before pauses; longer shots need the upper end of the approved pace. Do not time-stretch audio.
- Retention spacing and the first five-second hook are editorial targets, not verified playback measurements. Land the listed turn at +12 seconds and finish each line by +15. If a performance cannot fit, shorten the line while retaining its turn and mirror the edit in the sheet.
- Existing PNG references were not visually inspected. Before generation compare Luo Yi's wardrobe, Fang's face and all recurring identities to approved EP03 assets. References used solely for environment/palette cannot establish a new character's identity.
- Luo Mei's approved prior face plate was not present in the supplied states directory listing. Her proposed plate must wait for that identity reference; do not invent a replacement face.
- The proposed Lin floral emblem is a visual continuity assumption. Match the approved existing clan emblem if it differs. The screenplay does not authenticate the letter's author or identify whose blood it is.
- EP03's lifespan-restoration rule and unspecified intervening calendar days remain upstream continuity issues; this task does not rewrite EP03.
- Rain/ash/embers/dust in still shots are sparse atmospheric composite layers, not new physical fires or abacus activations. Keep evidence legible and adapt layer placement to the indoor/outdoor setting.
- Actual frames must still be checked for character duplication, readable marks, age consistency, particle quality and adherence to the static-shot plan. Text checks cannot guarantee generated pixels.
- Narration voice, pitch, loudness and Google Flow clip capabilities were not tested. No service sign-in or availability claim was made.
- Plot and lines were newly authored from the supplied original outline. No external drama was used or copied; no exhaustive external similarity search was performed.

## Blockers
- Delivery-path restriction: the requested live destinations `/opt/MoonieXHQ/Work/cn-series/script/` and `/opt/MoonieXHQ/Work/cn-series/plan/` are outside this worker's writable roots and the contract says to work only in the assigned worktree. The complete handoff is therefore staged in this report directory's `script/` and `plan/` subdirectories. A downstream authorized owner must promote those files to the requested live locations. No outside-worktree writes were attempted.
- Missing approved Luo Mei face reference blocks later image generation for her scenes, not completion of this text handoff. No CEO decision or paid action is requested here.

## Skill learning
- (none)
