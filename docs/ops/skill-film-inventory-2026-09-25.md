# Film-skill inventory, 2026-09-25 (evidence only, no design)

Read-only audit for the CEO's reorganisation order (film skills named by ENGINE, engine-agnostic material in ONE
shared skill, no skill repeating another). Nothing was edited except this file. Working tree state: `ai-film-production/SKILL.md`
carries an uncommitted Field note (2026-09-25); `docs/promo/TOPVIEW-WAN3-REFERENCES.md` is untracked.

## Source codes

| Code | File | Lines | Headings |
|---|---|---|---|
| AFP | `.claude/skills/ai-film-production/SKILL.md` | 618 | 21 |
| ABL | `.claude/skills/ai-film-production/AB-LEDGER.md` | 955 | 65 |
| HF | `.claude/skills/higgsfield-unlimited-gen/SKILL.md` | 1791 | 57 |
| TMD | `.claude/skills/thai-moral-drama/SKILL.md` | 531 | 30 |
| CONT | `.claude/skills/CTO_Flow_Omni1.1_Continuity/SKILL.md` | 150 | 11 |
| QC | `.claude/skills/CTO_Flow_Omni1.1_FilmQC/SKILL.md` | 125 | 10 |
| GFO | `.claude/skills/google-flow-ops/SKILL.md` | 1941 | 88 |
| SB | `.claude/skills/ai-video-storyboard/SKILL.md` (a symlink to `external/ai-video-storyboard-skill`, third-party, MIT) | 166 | 14 |
| LC | `.claude/skills/CTO_ChatGPT-Image_LakornCover/SKILL.md` | 165 | 13 |
| PS | `docs/prompts/absence/PROMPT-STYLE.md` | 91 | 5 |
| AR | `docs/prompts/absence/AUTHORING-RULES.md` | 314 | 28 |
| IR | `docs/prompts/ilag-topview/README.md` | 48 | 2 |
| IC | `docs/prompts/ilag-topview/CAST.md` | 26 | 1 |
| IB | `docs/prompts/ilag-topview/build.py` (header + helper blocks; no headings, one row per block) | 745 | 13 blocks |
| MA | memory `reference_h3_studio_api_tailnet.md` (no headings, one row per bold block) | 34 | 7 blocks |
| MG | memory `reference_h3_grid_ref_fails.md` | 58 | 3 |
| MS | memory `reference_h3_studio_architecture.md` (no headings, one row per bold block) | 31 | 6 blocks |
| WR | `docs/promo/TOPVIEW-WAN3-RULES.md` | 130 | 13 |
| WF | `docs/promo/TOPVIEW-WAN3-REFERENCES.md` | 218 | 7 |

Engine codes: **SH** = Seedance on Higgsfield · **FL** = Google Flow (Omni 1.1 Flash unless the row says Veo 3.1 Fast) ·
**H3** = MiniMax H3 on our RunPod studio · **W3** = Wan 3.0 on TopView · **AG** = engine-agnostic · **UN** = unclear / none of the four.

**Sections inventoried: 394 rows** (one per heading; one per code block for build.py and per bold block for the two
heading-less memory files): AFP 21, ABL 65, HF 57, TMD 30, CONT 11, QC 10, GFO 88, SB 14, LC 13, PS 5, AR 28, IR 2, IC 1,
IB 13, MA 7, MG 3, MS 6, WR 13, WF 7. By the first engine tag in each row: SH 162 · FL 102 · AG 68 · H3 32 · W3 20 · UN 7 ·
empty field-note sections 3. The 32 H3 rows include the IR/IC/IB pipeline rows, whose rules were measured on Seedance, not H3.

---

## 1. Section table

### AFP (ai-film-production/SKILL.md)

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| AFP1 | Running a multi-scene AI film (intro) | Layer above the tool; tool rules live in HF | SH: "paid for on «Sorry, Sir», seventeen scenes" | HF intro (both "every rule from a real incident") |
| AFP2 | 1 ONE FACE PER PLATE | Face scanner kills multi-face plates; location plates with no people; scan is retroactive; fire a plate's scenes in one loop | SH: "Three plates died permanently in one day" | HF hard rule 3 (scanner "terminally killed three healthy plates in one day", rescans retroactively); HF "one reference per person" |
| AFP3 | 2 NEVER LET THE GENERATION SLOT SIT IDLE | Unlimited = idle slot is the cost; keep a no-dependency list; paid image lane runs in parallel; pre-stage next prompt | SH: "Where video generation is unlimited" | HF Operating pattern bullet 1; HF Pre-stage; HF Never make a worker sit; HF grant expiring; HF hard rule 4 (paid image does not contend) |
| AFP4 | 3 BRIEF WORKERS THROUGH A FILE | Long pane text fragments; write QUEUE.md; mailbox empty bodies; pane messages kill background waits | AG: "reconstruct scattered CEO relays" (org worker ops) | HF "worker mailbox delivers notifications with no body"; HF render-wait (long sleep makes operator unreachable) |
| AFP5 | 4 A WORKTREE FREEZES WHEN THE TASK IS CREATED | Copy changed files into live worktrees, md5-verify | AG: "A worker's checkout is cut at task creation" | none in the audited sources |
| AFP6 | 5 CHANGE AN ELEMENT, RE-SHOOT EVERYTHING BOUND TO IT | Dependency map from grep; never re-point an Element, new name | SH: "one location Element fed twelve of seventeen scenes" | HF "A bound reference keeps the OLD asset"; IC header (row changes first, sheets rebuilt) |
| AFP7 | 6 SET A TOLERANCE OUT LOUD | 10-20% drift OK; name what it does not cover (people in plates, duration, resolution, price) | SH: "480p insert in a 720p film", "the price on the generate button" | HF "composer silently resets" (480p); HF hard rule 2 |
| AFP8 | 7 THE MODEL FOLLOWS YOUR PROSE OVER YOUR REFERENCE | Unbound ref = prose wins; count chips; keep prose and plate in agreement | SH: "reference chips", "Element naming is not uniform" | GFO "THE PROMPT OVERRIDES THE REFERENCE IMAGE" (same principle, FL); TMD Production constraints item 2; HF RED tag; ABL S2E; GFO "Anything that must look a specific way needs an Element" |
| AFP9 | 7a AN ELEMENT'S NAME IS NOT ITS CONTENT | Read what the plate depicts before binding; a name from the director is a pointer | SH: "S2AC v2 ... project_absence_loc_hall_big_d" | TMD "Look at every plate" (FL); GFO "Verify a chip by its THUMBNAIL" (FL); AFP 11b proven paragraph |
| AFP10 | 7b Depth words are a size instruction | Size relative to something in frame; no depth words; gaze in camera terms | SH: "S2M 3b ... NO WIDER THAN THE RED DOOR" | ABL S2M size, S2M orientation, S2N gaze, S2M-B; memory `feedback_depth_words_are_a_size_instruction.md`; tension with ABL prop_van (metres + ratio worked) |
| AFP11 | 8 WHAT THE DIRECTOR DECIDES | Story is the director's; do not stall; record his words verbatim | AG | ABL 01:45 S2AC (cites §8); HF Operating pattern "Scope discoveries are a C-level decision" |
| AFP12 | 9 YOUR OPERATORS ARE THE ONLY EYES | Require shot-by-shot operator descriptions; check delivery; commit asset id first | AG, SH evidence: "a clip at 480p inside a 720p film" | HF "THE REVIEW LOOP" (tension: operator never self-certifies, CTO opens frames); GFO "Capture each clip's id at SUBMIT"; ABL S2S retracted; QC workflow |
| AFP13 | 10 A CHARACTER'S NAME CAN BLOCK THE CLIP | Copyright filter collides on names; diagnose from files; change one variable | SH: "Measured 2026-09-05 on «Sorry, Sir»" | ABL S2Q, S2R ("§10 amended": image, not name), SC2, 13:20/13:40 Madame; GFO "A policy refusal comes from the DIALOGUE" (FL, same bisect method, different trigger) |
| AFP14 | 11 A PROHIBITION WITH NOTHING PUT IN ITS PLACE DOES NOT HOLD | Replace, ban the relationship, name the exact wrong thing, fill vague descriptions; check the reference first | SH: "Four measured instances in one night on «Sorry, Sir»" | ABL S2C, IV2c, S2PT 1-3 to 4; AR rules 5-6 (CONFLICT with item 3); GFO Omni grammar rule 4 + Sound ("describe what you want"); PS rule 8; CONT rule 7 |
| AFP15 | 11b An adjective is not a direction: make motion COUNTABLE | Count position changes with deadlines; falsifiable review test; look first, number is a footnote; `shot-motion.sh` trend | SH: "S2AC ... v3 changed the plate" | ABL 2026-09-11 01:45 (near-verbatim lesson); QC rule 3 + GFO audit heading (tension: mechanical first vs look first) |
| AFP16 | 12 WHEN A RE-FIRE PASSES, WRITE THE A/B ENTRY | Ledger entry shape, written by the reviewer, quoted from git | AG (process) | ABL header; GFO "How this file changes" (SKILL-CONTRADICTION shape, sibling process) |
| AFP17 | 13 EVERY PROJECT HAS A CAST.md FROM DAY ONE | One row per character; sheets must match; lint on colours | AG rule, SH evidence: "On «Sorry, Sir» the late-film cast" | IC (implements it); IB CAST_KEYS; ABL grandmother; GFO ASSET SHEET, APPEARANCE LOCK, Wardrobe, set-drift blocks (FL equivalent); TMD "Look at every plate" + constraint 2; CONT WARDROBE |
| AFP18 | 14b PLATFORM COST, NORMALISED TO BAHT PER SECOND | Dreamina vs Higgsfield ฿/s; free tier cannot make a clip; Omni reference unproven | SH (Seedance 2.0 Mini on Dreamina and Higgsfield) | HF "2026-09-13 plan page" (CONFLICT: HF lists "Dreamina 225 free credits/day"; AFP says that figure did not match; AFP says Higgsfield "16" refs, HF says 50); GFO "Price, for the same model" (FL ฿/s); WF §4 |
| AFP19 | 14 CHOOSE THE MODEL BY WHAT THE SHOT HAS TO CARRY | 2.5 vs 2.0 Fast vs Mini table; Fast for inserts; never mix models in a scene; background claim withdrawn | SH: "Measured on Higgsfield ... s2rq15-lab" | ABL 16:10, 16:35, 16:50, 17:10, 00:15 (same numbers); GFO "Which model for a drama" (FL analogue); memory `reference_seedance_model_tiers_higgsfield.md` (title) |
| AFP20 | Scene structure comes first (IRON §51) | Scene must pass tig-scene-engine before generation | AG: "tig-scene-engine" | TMD order of work step 9 + Structure gate; CONT When NOT to invoke |
| AFP21 | Field notes | 09-25: skill never points to PS/AR; ilag build.py pattern | SH format applied to H3 | IR; IB docstring; memory `feedback_new_film_prompts_use_house_format.md` (near-verbatim) |

### ABL (ai-film-production/AB-LEDGER.md), all Seedance on Higgsfield unless marked

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| ABL1 | Title / intro | Kept per §12, quotes from git | SH | AFP §12 |
| ABL2 | S2C Dupe's pacing | Negatives cannot slow a character; previz m/s set the speed | SH: "previz proxy was re-cut" | AFP §11 table row 2; ABL63 |
| ABL3 | S2E to S2Eb fake cleaning | Object with no reference is invented (insect mark) | SH: "@project_absence_loc_hall_big_d ... four-panel sheet" | AFP §7 bullet 4; ABL S15a-2 vs S2G |
| ABL4 | S2Q Madame's entrance | Name stripped, passed the gate | SH: "protected-content gate" | AFP §10 (its main example); ABL S2R (confound note) |
| ABL5 | S2M crack SIZE | Depth words make objects big; anchor to the red door | SH | AFP §7b (rule restated) |
| ABL6 | S2M ORIENTATION | Gaze in camera terms; size variance 1x-3x | SH | AFP §7b bullet 3 |
| ABL7 | S2N gaze | "backs to the room" read as backs to us | SH | AFP §7b |
| ABL8 | S2N cast count | Every character gets a beat line naming them | SH | HF IRON rule; ABL13 |
| ABL9 | S2R copyright gate | A prop IMAGE (croc bag) triggered; prose kept the prop | SH: "Rejected due to copyright restrictions" | AFP §10; ABL SC2; GFO policy refusal (FL: "chips were never the trigger", opposite) |
| ABL10 | S2M-B reverse angle | Size anchored to the plaque in the same frame | SH | AFP §7b |
| ABL11 | prop_van image plate | Class first, metres + ratio, banned silhouettes by name | SH (Higgsfield image plate) | AFP §7b (tension: "never a world measurement" vs metres worked here) |
| ABL12 | SC2 flagged prop Element vs prose | Warning triangle: move object to prose | SH: "credits 461 to 409" | ABL S2R; AFP §10 |
| ABL13 | S15a-1 unnamed side mirrored | A count is not a placement; empty side filled by copying nearest chip | SH | HF IRON rule (CONFLICT on sufficiency of stating counts); ABL15, ABL20, ABL23, ABL24 |
| ABL14 | S15a-2 vs S2G insect mark | The canon travels with the mark | SH | AFP §7 bullet 4; ABL3 |
| ABL15 | S15a-1 t1 to t2 anchoring both sides | Name the side of frame each group holds | SH: "free lane" | ABL13 (same finding twice); AR rule 5 example |
| ABL16 | S15a-2 weight before size + correction | Weight before size; later: not deterministic, use as acceptance test | SH | ABL19 |
| ABL17 | SC5 wide copying plate sky | Plate wins over light words; reframe; give a figure a JOB; camera must see background | SH | AFP §11 closing; GFO night / set drift (FL, same mechanism); CONT rule 2 |
| ABL18 | S2R-JC no cut | Seedance has no concept of a cut; move change inside a shot | SH: "Seedance generates twenty CONTINUOUS seconds" | ABL24 (same lesson again); PS rule 4 (tension: "Seedance invents cuts"); WF §3 (W3 multi-shot) |
| ABL19 | Mark darkness is size-dependent | Below ~1% width the mark cannot read black | SH | ABL16 |
| ABL20 | S15b bound character with no position | Takes the most salient slot; every person-chip gets a WHERE | SH | ABL22, ABL23, ABL24 |
| ABL21 | S2S RETRACTED | Identify a card by Created time = fire time | SH: "Higgsfield's Created time is the FIRE time" | AFP §9; GFO capture id at SUBMIT (FL); QC workflow step 3 (same class) |
| ABL22 | The grandmother's clothes | No wardrobe sentence = dressed from the rest of the prompt | SH | AFP §13; GFO Wardrobe + set drift (FL); CONT rule 4 |
| ABL23 | S16 saw to grinder | Generic word resolves to its common picture; two chars on one ref need two positions | SH: "FREE lane" | ABL20, ABL13 |
| ABL24 | S2R-JC take 3 to 4 | A cut needs a visible change; separation by distance and ownership | SH | ABL18 (dup) |
| ABL25 | PENDING header | Holding area for unfired entries (many PASSED entries sit below it) | AG | structure defect: orphan paragraph at l.544-548 |
| ABL26 | S2R-F faces rejected | Violence-adjacent prose hypothesis | SH | GFO policy refusal (FL prose trigger); ABL ladder entries |
| ABL27 | S2P tour | Awaiting t3 | SH | ABL S2PT entries |
| ABL28 | Projector plate | Prose-only and image ref both rejected; CEO supplies plate | SH | none |
| ABL29 | IV2c crew reveal | Stillness as bans replaced by an action | SH | AFP §11 item 1 |
| ABL30 | 09-09 21:15 S2AJ pass / S2R-F rejected | Close-up framing hypothesis | SH: "Unlimited Seedance 2.5 Refunded" | ABL45-49 (withdrawn later) |
| ABL31 | 09-09 22:45 S2PT t1 fail | Review headcounts at full resolution | SH | HF REVIEW LOOP; ABL50, ABL64 |
| ABL32 | 09-10 00:10 S2PU pass | Log; corner-diff lock check | SH | none |
| ABL33 | 01:35 S2PT t2 pass | Count cast by clothes, "ONE man in black" three ways | SH | HF IRON rule |
| ABL34 | 02:20 S15e-AB + overnight plan | Keep the free lane busy with add-ons | SH | AFP §2 |
| ABL35 | 03:10 S18 + plaque plan | PIL-composed plaque plan | SH | ABL38 |
| ABL36 | 03:45 chain 1 closed | Log | SH | none |
| ABL37 | 04:05 S3a t2 | Two-camera previz as Video 1 fixes locked camera | SH | HF "Attaching a VIDEO reference" |
| ABL38 | 04:50 PLAQUE PLAN WITHDRAWN | Rule 00 breach + flagged Element | SH: "Rule 00 (festival...)" | HF Rule 00 (same incident); memory `feedback_festival_rule00_no_edited_uploads.md` |
| ABL39 | 05:20 S2AW pass | Log | SH | none |
| ABL40 | 05:45 S2AP pass | Framing hypothesis | SH | superseded by ABL45/49 |
| ABL41 | 06:50 S2R-F V1 rejected | Third rejection | SH | ABL48-49 |
| ABL42 | 10:05 S19 pass | 1080p settings drift caught; European daytime jam | SH | HF composer resets; HF render time schedule |
| ABL43 | 11:45 paid A/B ladder | One variable per fire, stop at first rejection | SH: "credit lane (140 per passing fire)" | AFP §10 step 3; GFO policy refusal "Bisect, one variable" (FL) |
| ABL44 | 12:25 editor instructions collected | Edit rows | AG ops | none |
| ABL45 | 12:45 ladder L0/L1 | Bidder Elements, not framing | SH | ABL48-49 |
| ABL46 | 13:10 L2 passed | Carrington's Element cleared | SH | ABL49 |
| ABL47 | 13:15 CEO stops credit lane | Free lane only | SH | HF grant expiring ("do not fall back to the credit lane") |
| ABL48 | 13:20 cause found (Madame) | Later overstated | SH | ABL49; memory `reference_higgsfield_madame_element_trigger.md` (title) |
| ABL49 | 13:40 correction | Framing and chip count ruled out; Element a risk factor | SH | AFP §10 (not reflected there) |
| ABL50 | 14:05 S2PT second cart | Count props like cast, full res, two frames | SH | ABL64; QC stage 2 (FL) |
| ABL51 | 14:30 S2PT take 3 | ONE CART stated three ways | SH | HF IRON rule |
| ABL52 | 16:10 MODEL LAB setup | Prices 2.5/2.0; Unlimited does not cover 2.0 | SH | AFP §14; HF "UNLIMITED COVERS SEEDANCE 2.5 VIDEO ONLY" |
| ABL53 | 16:35 lab fire 1 (2.0 Fast) | Binds Elements; 53 credits; 4.5 min | SH | AFP §14 (same numbers) |
| ABL54 | 16:50 lab fire 2 (2.0 Mini) | Draft tier; bitrate/saturation numbers | SH | AFP §14 (same numbers) |
| ABL55 | 17:10 lab closed / viewport lock-up | "MOBILE ACCESS COMING SOON" collapse twice | SH | HF MAXIMISE THE WINDOW; HF window can shrink |
| ABL56 | 17:20 S20 pass | Prop count applied; locked-camera numbers | SH | ABL50 |
| ABL57 | 18:41 editor instructions sent (LINE) | Line-by-line typing | AG | memory `reference_line_desktop_computer_use_typing.md`; skill winbox-desktop-gui |
| ABL58 | 19:35 S21 pass | Sheet negatives encode predictions; deviations can be improvements | SH (2.0 Fast) | AFP §11b ("S21 broke two written rules"); ABL61 |
| ABL59 | 21:45 S0b pass / S2PT t3 fail | First-vs-last lock test; previz proxy occluded | SH | ABL63 (same previz story); skill blender-previz |
| ABL60 | 22:00 session parked | Session save | AG | none |
| ABL61 | 23:20 S22 pass | Geometry encodes predictions; grade miss accepted | SH | ABL58 (same lesson) |
| ABL62 | 09-11 00:15 S2R-Q pass, corrects rule 14 | Scene detector blind to identical-framing cuts; background not a tier tell | SH | AFP §14 (withdrawal restated) |
| ABL63 | S2PT takes 1-3 to 4: fix not in the prose | One previz coordinate; blocking beats prose | SH | AFP §11 closing, AFP §7; ABL59; memory `prose-cannot-beat-a-video-ref.md` |
| ABL64 | 01:05 S2PT t4 pass | Count props at full res or not at all | SH | ABL50 |
| ABL65 | 01:45 S2AC | Vague motion order gives a posed group | SH | AFP §11b (near dup) |

### HF (higgsfield-unlimited-gen/SKILL.md), all Seedance/Higgsfield

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| HF1 | Higgsfield Unlimited-Mode Generation (intro) | Adds Higgsfield layer on browser-operator + dev-spawn | SH | AFP intro |
| HF2 | What it does | Button-level rules, wait pattern | SH | none |
| HF3 | When to invoke | Any higgsfield.ai browser task | SH | none |
| HF4 | When NOT to invoke | fal.ai, Kling, Veo excluded | SH | GFO scope line (mirror) |
| HF5 | The incidents this is built from | Rerun 130 credits; type() truncation | SH: "130 credits · Seedance 2.5 · Spent" | HF14 rules 1 and 6 (retold) |
| HF6 | Reading the credit ledger | Only an intro paragraph; the rule body is missing | SH | none (truncated section) |
| HF7 | SEEDANCE VIDEO EDIT grammar | Lead with edit verb, name @Video1, @Image1 refs, move = remove + add | SH: "Seedance 2.5 can edit an already-rendered clip" | GFO "Which model" table (Omni "video-to-video editing: yes", no grammar); HF32 (@Image1) |
| HF8 | WHEN THE GRANT IS EXPIRING | Charge decided at click; price on button, not clock | SH | AFP §2; HF24; ABL47 |
| HF9 | 2026-09-13 plan page | Seedance not in any plan's unlimited list; GPT Image unlimited on Ultra; other providers | SH: "higgsfield.ai/pricing" | HF10 (inverts it); AFP §14b (Dreamina CONFLICT); WF §4 ("TopView ~$50/mo annual, 60-day window, 720p cap" vs WF's Wan3 365-day line) |
| HF10 | UNLIMITED COVERS SEEDANCE 2.5 VIDEO ONLY | Images always cost credits; table | SH: "CEO, 2026-08-27" | HF14 rule 2 table (dup); HF29 table (dup); HF9 and HF56 (contradict it) |
| HF11 | HARD: MAXIMISE THE WINDOW | Mobile layout below 1280 = disabled Generate | SH | HF20 (728x420 note), HF54; ABL55; GFO Traps "viewport reverts" (FL analogue) |
| HF12 | Rule 00: festival platform-only generation | External generation banned; post-production allowed; Resolve free | SH (festival on Higgsfield) | ABL38; memory `feedback_festival_rule00_no_edited_uploads.md`; WR entry + ChatGPT section (W3 contest: external images allowed) |
| HF13 | Rule 0: generate only in the named project | Project URL in every brief | SH | WR Entry ("Every Wan3 shot must live in our TopView project", analogue) |
| HF14 | Hard rules, tiered (rules 1-7) | Never Rerun; price table; Confirm Rights; one unlimited at a time; toggle one attempt; paste-only, decoy editor, duration slider, three reads; Usage after any error | SH | HF5; HF10 + HF29 (price table x3); AFP §1 (scanner); AFP §2 (image lane); HF20 (stale toast); HF22 (editor); GFO settings panel + Traps (FL analogues) |
| HF15 | THE REVIEW LOOP | Operator never self-certifies; every clip saved, FLAGGED suffix | SH | AFP §9 (tension); AFP §12; QC loop (FL); IB notes_bottom ("File the take whatever the verdict") |
| HF16 | IRON RULE: every character EXACTLY ONCE | Count in words + verbatim duplicate negatives | SH: "Seedance duplicates a character" | ABL13/15 (a count is not a placement); AR rule 9; PS rule 10; IB main() assert |
| HF17 | PRE-FIRE lint | `scripts/prompt-lint.py`; points to AR two-zone rule | SH | AR pre-fire checks + grep; IR grep line |
| HF18 | Attaching a VIDEO reference, @Video 1 | Upload path, decoy twins, chip once; prompt authoring for a video ref | SH | HF50, HF51 (upload path x3, CONFLICT: input "by accept" vs "by panel context"); AR rule 4; skill blender-previz |
| HF19 | Render time and Europe's night | 01:00-07:00 UTC window | SH | ABL42; AFP §14 last paragraph; memory `reference_higgsfield_free_queue_jam.md` (title) |
| HF20 | A long-lived tab lies about the slot | Fresh tab every 3-4 gens; 728x420 lockup | SH | HF11, HF54 |
| HF21 | Composer silently resets its settings | Re-verify 20s/720p/2.5/High/Sound | SH | AFP §6, §9; ABL42; GFO Traps (FL: model/aspect/quantity not sticky) |
| HF22 | Editor gotchas (Lexical) | Clear, paste, End-space-Backspace, Recreate, source bytes, clear video ref | SH | HF14 rule 6; GFO Traps (first keystroke dropped) + winbox `@` eats text (FL) |
| HF23 | The render-wait pattern | DEV cannot sleep; poll loop is the wait; 20 then 5 min cadence | SH/AG | HF46 (CONFLICT: worker's job ends at fire); HF26 (10 to 5 to 3 cadence, CONFLICT); HF48 (90 s sleep); AFP §3 |
| HF24 | Pre-stage the next prompt during the wait | Stage B while A renders; re-verify at click | SH | AFP §2; HF46; HF8 |
| HF25 | Operating pattern for multi-generation jobs | Never idle; shoot the whole wave; wave cap ~5; replay script; scope is C-level | SH | AFP §2, §8; HF48 (wave cap text repeated) |
| HF26 | Task-brief checklist | Hard rules, gotchas, poll schedule, scope, stop conditions | SH | HF23 (cadence conflict) |
| HF27 | Reference | Task ids, GH issues | SH | none |
| HF28 | Findings from the Valder wave (intro) | Five stalls, fixes | SH | none |
| HF29 | The video Generate button shows a struck-through price | Table again | SH | HF10, HF14 (dup table) |
| HF30 | SEEDANCE 2.5 TAKES UP TO 50 REFERENCES | Not 9; design scenes accordingly | SH: "Higgsfield ได้มากสุด 50 REF" | AFP §14b ("16", CONFLICT); HF48 ("Seedance 2.0 is 9"); HF18 ("video chip + 10 = 11 accepted"); WF §1 ("Seedance 2.0 on Topview 9/3/3/15") |
| HF31 | One reference per person | 1 REF / 1 คน / 1 ภาพ, even extras | SH | AFP §1 |
| HF32 | THE EASY WAY: drag in, @Image1 | Positional refs without Elements | SH | HF7 (@Image1 in edit mode); WF §2 (W3 "@Image 1", same mechanic); GFO IMAGE_REF add order (FL); MG slot order (H3) |
| HF33 | Why this matters more than it sounds | Named path solves problems drag-drop does not have | SH | none |
| HF34 | When you still want a named Element | Recurring cast/locations/props | SH | none |
| HF35 | HIGGSFIELD SOUL DOES NOT ACCEPT REFERENCES | Soul Cinema: red tags, no dropdown | SH (Higgsfield Soul, image) | HF56 (Soul free counter) |
| HF36 | What this costs you, and the rule | Referenced plates on GPT Image; whole set from one model | SH | AFP §14 "never mix models" (same principle for video); GFO "Verify grade" (FL) |
| HF37 | RED tag text = Element does not exist | Look at the colour | SH | AFP §7; GFO step 9 + thumbnail rule (FL) |
| HF38 | Generating an image is NOT creating an Element | Two steps | SH | GFO field note 09-23 assets (FL analogue) |
| HF39 | @ dropdown folder-scoped, paste is not | Paste the whole prompt, count thumbnails | SH | HF22 |
| HF40 | Creating an Element: detail-modal path | Native value setter for Name/ID | SH | none |
| HF41 | Element IDs are GLOBAL | project_slug naming; replace suffixed tags first | SH | AFP §7 bullet 2; GFO field note 09-23 substring match (FL analogue) |
| HF42 | The worker mailbox delivers no body | Append to TASK.md | AG | AFP §3 |
| HF43 | Do not let a non-generating task hold the queue | Registration during a render | SH | AFP §2 |
| HF44 | Treat "Unlimited is broken" as unconfirmed | Human confirms on the real screen | SH | HF14 rule 5; HF11; memory `feedback_untested_blocker_cost_six_hours.md` (title) |
| HF45 | Two brief-writing rules (intro) | | SH | none |
| HF46 | Never make a worker sit and watch a render | Worker ends at confirmed fire; warm up next job | SH | HF23 (CONFLICT), HF24, AFP §2 |
| HF47 | Prune the safety gates | Money gates always, diagnostic gates on symptom | SH/AG | none |
| HF48 | Hard caps | Seedance 2.0 cap 9; wave cap ~5; sleep 90 s | SH | HF25 (wave cap repeated, same "Missed 2026-08-14" story); HF23; HF30 |
| HF49 | A bound reference keeps the OLD asset | Remove and re-add, never refresh | SH | AFP §5 |
| HF50 | Video-ref attach on the PROJECT composer | Two-click eligibility; broken chip; focus check; settings row order | SH | HF18, HF51; HF14 rule 6 (slider repeated); HF21 |
| HF51 | Video-ref upload: "+" then Uploads then Videos | Byte-match content-length | SH | HF18 step 3 (CONFLICT); HF53; ABL 00:10 |
| HF52 | Tab hygiene | Pointer to browser-operator | AG | browser-operator |
| HF53 | HARD: paid controls, one click | Never a retry above struck zero | SH | HF14 rule 5; HF51 (content-length repeated) |
| HF54 | HARD: window can shrink; resize_window can lie | Read innerWidth back | SH | HF11, HF20; GFO winbox + Traps (FL analogue) |
| HF55 | HARD: the Unlimited toggle can be COVERED | "Credits are running low" banner | SH | HF14 rule 5; HF44 |
| HF56 | Free IMAGE plates (Kling O1) | Unlimited toggle on Kling O1 image; plate recipe | SH | HF10 (CONTRADICTS "images always cost"); HF9; GFO free stills (FL analogue) |
| HF57 | Uploading project assets (audio) | Folder upload path, 10 MB cap | SH | none |

### TMD (thai-moral-drama/SKILL.md)

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| TMD1 | ละครสั้นคุณธรรม: the format (intro) | ฟ้ามีตา model; narrator is the brand | AG: "four real ฟ้ามีตา episodes" | none |
| TMD2 | The nine rules (header) | | AG | none |
| TMD3 | 1 One episode is one complete story | No arcs | AG | TMD29 item 2 |
| TMD4 | 2 The wrongdoer has a reason | | AG | none |
| TMD5 | 3 The wrong needs a power gap | | AG | none |
| TMD6 | 4 The turning point is an ACT | | AG | none |
| TMD7 | 5 Reversal from a witness | Plant the witness in 2 minutes | AG | TMD29 items 4-5 |
| TMD8 | 6 Karma earned, not administered | | AG | TMD29 item 4 |
| TMD9 | 7 Every named character gets a conclusion | Conclusion table | AG | TMD29 item 3 (extends it) |
| TMD10 | 8 The family must come through it | | AG | none |
| TMD11 | 9 Show it, never claim it | | AG | TMD16 |
| TMD12 | Money on screen is invented prop money | Model draws real Thai notes; paste the prop-money block | FL: "Four of four money shots in the first Act 1 shoot" | GFO "Anything that must look a specific way needs an Element" (same prop-money block; CONFLICT: GFO says the words failed 6 clips, fix is an Element); CONT rule 7; LC rule 3; GFO set-drift NOT-LIST ("no notebook, no pen, no paper" same string); GFO field note 09-22 |
| TMD13 | Look at every plate before writing a shot sheet | Appearance blocks from what you see | AG rule, FL evidence: "bedroom-drift" | AFP §7a; GFO ASSET SHEET ("Look at each asset once") |
| TMD14 | How to look, without burning the context | `tools/plate_montage.py` one sheet | AG | QC stage 2 contact sheet (same economy) |
| TMD15 | Where the plates live | Download once; replace on regenerate | AG | GFO "Clips do not live in git" (sibling); gdrive-filing |
| TMD16 | The spoken lines carry everything | 80-90% of shots speak; no two silent shots | AG + FL | GFO Thai text rule 5 ("see thai-moral-drama") |
| TMD17 | DENSITY, not presence | 20-34 syllables per 8 s shot; shotsheet_lint | FL: "8-second shot", "84% verbatim by speech-to-text" | CONT FAST-LINE flag (>10 Thai chars/s, opposite pressure); GFO field note 09-23 shot 43 |
| TMD18 | Two more: say it plainly, earshot | | AG | none |
| TMD19 | The rule and the test are not the same thing | A transcript cannot show a gap | AG | QC rule 1 / GFO audit (a check that cannot fail); memory `feedback_check_against_an_artefact_that_can_show_the_failure.md` |
| TMD20 | The rule makes the script better | | AG | none |
| TMD21 | Plausibility is part of the dialogue | | AG | none |
| TMD22 | Straight line, one flashback | | AG | none |
| TMD23 | The character acts WHILE speaking | Never "then"; no silent actions | FL: "Twelve Act 1 shots were rendered and measured" | GFO "A speaker whose face is not in frame" (FL); PS rule 5 (SH dialogue inline) |
| TMD24 | Thai TTS stutters (numeral + classifier + vocative) | Particle between count and vocative | FL (in-clip Omni voice) | GFO "Never diagnose audio" (208 งวด); QC stage 1 |
| TMD25 | Length, and where the money is | 18-24 min; mid-roll map; 12 credits/shot | FL: "Flow credits @12/shot" | GFO Google AI Ultra (12 credits, keep-rate estimate); GFO Measured costs |
| TMD26 | The recurring assets | Narrator, one neighbourhood | AG | none |
| TMD27 | Production constraints (Google Flow) | Text is garbage; prompt overrides reference; voice binds to character | FL | GFO Thai text (CONFLICT: GFO says image model writes Thai and quoted Thai renders in video); GFO PROMPT OVERRIDES + ASSET SHEET; GFO "A voice belongs to the CHARACTER" |
| TMD28 | Writing a new episode: order of work | 12 steps; tig then Continuity | AG | AFP Scene structure §51; CONT When NOT |
| TMD29 | Structure gate | 8 items, 7 and 8 Flow-specific | AG + FL (item 7 "On Flow: no handcuffs...", item 8 "Flow's image model costs 0") | CONT flags + rules 1, 2, 5; GFO vanish + arrest sections; GFO free stills; CONT TRANSITION (item 6) |
| TMD30 | Field notes | Structure gate promoted; cover notes (09-24) | AG / UN (cover) | LC layout (cover note ~10 lines dup), LC worked example |

### CONT (CTO_Flow_Omni1.1_Continuity/SKILL.md), all Flow

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| CONT1 | Continuity (title) | | FL | none |
| CONT2 | Model scope | Omni 1.1 Flash, องค์ประกอบ, up to 10 refs, [ANY]/[FLOW] tags | FL: "Proven on ... Omni 1.1 Flash" | QC2 (same block shape); GFO chip-cap statements (CONFLICT: "up to 10" vs GFO "plan for three") |
| CONT3 | What it does | continuity_sheet.py rows + TRANSITION + flags | FL/AG tool | none |
| CONT4 | When to invoke | | FL | none |
| CONT5 | When NOT to invoke | QC, TMD, tig own the rest | AG | TMD28; AFP §51 |
| CONT6 | Workflow | TRANSITION first; fix the sheet not the prompt | FL/AG | TMD29 item 6 |
| CONT7 | The flags, and how much to trust each | FLOW-DELETES, NIGHT-ON-DAY-PLATE, REF1-CLOSEUP, SICKBED, FAST-LINE, INAUDIBLE-SPEECH | FL: "calibrated on the banchi film" | GFO vanish + arrest; GFO night paragraphs + field note 09-22; GFO field notes shot 106 and shot 43; TMD29 item 7 |
| CONT8 | Rules 1-7 | No paid deleted shots; night plate; subject first; face + wardrobe plates; sickbed; NOT key is not exclusion; say where a prop is | FL (rules 5-6 [ANY]) | rule 1 = GFO vanish (verbatim "an everyday khaki duty uniform, a metal badge"); rule 2 = GFO night; rule 3 = GFO field note 106; rule 4 = GFO Wardrobe + field note 09-23; rule 6 = GFO "A prohibition is not an inventory"; rule 7 = GFO money Element + TMD12 |
| CONT9 | Output format | | FL | none |
| CONT10 | Reference | Pointers | AG | none |
| CONT11 | Field notes | empty | none | none |

### QC (CTO_Flow_Omni1.1_FilmQC/SKILL.md), all Flow

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| QC1 | Film QC (title) | | FL | none |
| QC2 | Model scope | Tools [ANY], defects [FLOW] | FL: "Omni 1.1 Flash ... Thai dialogue generated in-clip" | CONT2 |
| QC3 | What it does | 4-stage loop, cheapest first | AG tools / FL defects | GFO mechanical audit (same tools table); TMD14 |
| QC4 | When to invoke | | FL | none |
| QC5 | When NOT to invoke | | FL | none |
| QC6 | Workflow 1-6 | Transcript + caption scan; contact sheet; pull --search; 540p per act; lock; assemble once | FL | GFO audit + "Never diagnose audio" (step 1); GFO field note 09-23 pull (step 3, verbatim "OLD take of 149 and 151") |
| QC7 | Rules 1-4 | Calibrate detectors; vanished = Flow deleted; look to confirm; state what the loop misses | FL/AG | rule 1 = GFO "OCR is not a caption detector" + 2 field notes; rule 2 = GFO vanish + field note; rule 3 = GFO audit heading; rule 4 = GFO "What none of these can see"; AFP §11b (tension) |
| QC8 | Output format | | FL | none |
| QC9 | Reference | | AG | none |
| QC10 | Field notes | empty | none | none |

### GFO (google-flow-ops/SKILL.md), all Flow unless marked

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| GFO1 | Google Flow operating rules (intro) | Flow equivalent of HF | FL (seeded on Veo 3.1 recon) | HF1 |
| GFO2 | Mute the page first | | AG (browser-operator rule) | GFO34; browser-operator |
| GFO3 | A policy refusal comes from the DIALOGUE | Refunded refusals; dialogue was the trigger | FL: "measured 2026-09-19" | AFP §10 + ABL S2R (SH: names/images, opposite trigger) |
| GFO4 | What was measured | Bisection table | FL | ABL43 (SH ladder) |
| GFO5 | The two phrasings that tripped it | Dependent + demand; absolute money ban | FL | ABL26 (SH prose hypothesis) |
| GFO6 | The fix: same beat, positive surface | Say it forward | FL | AFP §11 item 1 (replace, don't forbid) |
| GFO7 | How to work when a shot is refused | Re-fire once, bisect one variable at 360p, confirm by revert | FL | AFP §10 step 3; ABL43 |
| GFO8 | Money | Credit pool; never upgrade; read balance + estimate | FL | HF14 rule 2 (analogue) |
| GFO9 | Google AI Ultra | ฿3,500, 10,000 credits, pace, keep rate | FL | GFO38 (account tier dup); TMD25; memory `reference_google_ai_plans_thailand.md` |
| GFO10 | Measured costs | Stills 0; Veo Fast 10 (was 20); Omni 360p/4s = 4 | FL (Veo 3.1 Fast and Omni) | GFO16 (tension: 4 s for plumbing tests vs "never 4 s" for behaviour tests); GFO54 (Veo Fast 20) |
| GFO11 | Anything that must look a specific way needs an Element | Prop money failed as words; night word loses to paragraph | FL: "«จุดจบของเจ้าหนี้นอกระบบ», 6 clips lost" | TMD12 (same money block, CONFLICT); CONT rules 2, 7; GFO field notes 09-22 x2; AFP §7 last bullet (SH) |
| GFO12 | Every shoot ends with a mechanical audit | transcript, burned_text_scan, crop fix, OCR not a detector | FL: "3 of 173 shots" | QC3, QC6, QC7; memory `reference_cheap_film_audit.md`; GFO field notes 09-23 x4 |
| GFO13 | Never diagnose audio you have not read back | film_transcript.py; three defect classes | FL | QC6 step 1; PS RULE 5 CORRECTED ("Always transcribe", SH); TMD24 |
| GFO14 | Which things get a chip when slots are scarce | Four chips bind; cap 10; biggest and most reused get chips | FL | GFO20 step 8b; GFO39; GFO65 (CONFLICT: 3 vs 4 vs 10); field note 09-22 |
| GFO15 | A prohibition is not an inventory | NOT["money"] is a ban, not a marker | FL | CONT rule 6; memory `feedback_a_flag_is_not_an_inventory.md` |
| GFO16 | Test fires run at 360p / 8 seconds | Never a 4 s test | FL (Omni) | GFO10, GFO59, CONT2 + rule 2 (CONFLICT: behaviour A/Bs run as 360p/4 s arms) |
| GFO17 | Concurrency: ~3 at once | x4 fails | FL | none |
| GFO18 | A failed generation is not charged | | FL | GFO3 (refunded refusals) |
| GFO19 | What this does and does not license | x1 default, 2 machines one tab each | FL | HF14 rule 4 (SH one-at-a-time, analogue) |
| GFO20 | The shortest path, 12 steps | Veo 3.1 Fast; chip attach via ⋮ menu; cap 10; count chips | FL (Veo 3.1 Fast) | GFO55, GFO63, GFO73 (chip attach path x4, ⋮ path retired); GFO54 (model choice CONFLICT: Omni) |
| GFO21 | Measured timings | Veo 3.1 Fast renders, still times | FL (Veo 3.1 Fast) | none |
| GFO22 | The settings panel (live DOM) | Labels always in DOM; estimate only when open; เริ่มสร้าง | FL | GFO23 |
| GFO23 | Traps | Chips drop; model resets to Omni (re-select Veo); not sticky; export hangs; viewport; first keystroke | FL | HF21, HF22 (SH analogues); GFO54 (CONFLICT on which model to keep) |
| GFO24 | Google Flow Music | Separate product, flowmusic.app | FL (product) | memory `feedback_new_google_product_urls_from_google_domains_only.md` |
| GFO25 | What Flow does NOT have | No 1080p, no storyboard, no episode export, no audio upload | FL | GFO26 (retraction inside) |
| GFO26 | Start and end frames exist | | FL (Veo 3.1 Fast) | GFO25 |
| GFO27 | The exact path | เฟรม / องค์ประกอบ toggle | FL | none |
| GFO28 | เฟรม and องค์ประกอบ are mutually exclusive | Faces OR set, never both in the UI | FL | MS "@refs ... mutually exclusive with i2v" (H3, same structural constraint); GFO77 |
| GFO29 | What the frame picker will show | Tagged images excluded | FL | GFO31 |
| GFO30 | Cost in เฟรม mode | 20 credits (Veo Fast) | FL (Veo 3.1 Fast) | GFO10 |
| GFO31 | Two assets per location | Ingredient + plain image | FL | GFO29 |
| GFO32 | Capture each clip's id at SUBMIT | Cache trap; CDN URL at first play | FL | AFP §9; ABL21; QC6 step 3; GFO35, GFO62 |
| GFO33 | Clips do not live in git | Video to Drive | AG | TMD15; ABL45 repo note |
| GFO34 | Never press play | Mute, no playback | AG/FL | GFO2 |
| GFO35 | In-page player can fail: pull from CDN | read_network_requests, curl, ffprobe | FL | GFO62 (download dead, same recipe) |
| GFO36 | Left sidebar | | FL | none |
| GFO37 | Composer settings row | 720p ceiling on PLUS | FL | GFO38 |
| GFO38 | Account tier | ULTRA since 09-18 | FL | GFO9 |
| GFO39 | Two ceilings that were never real | "still 3 in the Flow UI"; every character can speak | FL | GFO14, GFO20, GFO65, CONT2 (chip cap CONFLICT) |
| GFO40 | THE PROMPT OVERRIDES THE REFERENCE IMAGE | Omitted detail is surrendered | FL: "Measured on the CEO's own characters" | AFP §7 (SH); TMD27 item 2 |
| GFO41 | The ASSET SHEET | Look once, every prompt quotes it | FL | AFP §13 (SH); TMD13; IC |
| GFO42 | Wardrobe | Outfits as separate assets | FL | CONT rule 4; ABL22 (SH); GFO field note 09-23 wardrobe |
| GFO43 | Why this is the difference from AI slop | Bookkeeping | FL | none |
| GFO44 | Mid-session Google sign-out | One-second test; do not sign in | FL | skill relay-login |
| GFO45 | The MCP tab group can be destroyed | Re-verify composer | AG | GFO64 (dup) |
| GFO46 | How this file changes | SKILL-CONTRADICTION report | AG | AFP §12; AR owner section |
| GFO47 | Voices: lock one per character first | Documented Google flow | FL (Omni) | GFO48, GFO66, GFO68 (voice x6) |
| GFO48 | Casting a voice (header) | | FL | GFO47 |
| GFO49 | Rules | One voice per character; C-level casts; ledger score | FL | GFO47 |
| GFO50 | Casting criteria | Sex, pitch as age proxy | FL | none |
| GFO51 | All 30 presets | Label table | FL | none |
| GFO52 | Cast ledger | Two ledgers; grid negative is not evidence | FL | memory `reference_flow_voice_lock.md` (title) |
| GFO53 | Sound: what can be steered | No off switch; delete "No music." | FL (Omni) | GFO65 rule 4 (dup); PS "no music every scene" (SH, CONFLICT by engine); IB HOUSE_NEG + non_diegetic_music (H3) |
| GFO54 | Which model: Omni Flash, not Veo 3.1 Fast | Table | FL | GFO20, GFO23 (still tell operators to pick Veo Fast) |
| GFO55 | Chip attach: the ⋮ menu is gone | Row then preview pane | FL | GFO20, GFO63, GFO73 |
| GFO56 | Measured on the account 09-08 | Voices live on PLUS; customise bullet RETRACTED | FL | GFO66 (retraction) |
| GFO57 | winbox findings | resize never works; trusted click; `@` eats text; plates 9:16 | FL (winbox) | HF22, HF54 (SH analogues) |
| GFO58 | winbox run 2 additions | Pixel clicks; download walks; verify grade | FL | HF36 (grade) |
| GFO59 | A clip that vanishes after Submit (police) | Describe the clothes, never name the institution | FL: "A/B, 360p/4s, 3 arms" | CONT rule 1 + FLOW-DELETES; QC rule 2; field notes 09-23 x2 |
| GFO60 | What Flow silently deletes in an arrest scene | Handcuffs; uniform + police lights | FL: "11 arms" | CONT rule 1; TMD29 item 7; LC rule 2; field note 09-23 |
| GFO61 | Chrome blocks downloads | One human click | AG (browser) | field note 09-23 (pending workaround) |
| GFO62 | Download button is dead: go to the CDN | | FL | GFO35 |
| GFO63 | Chip attach is inconsistent | Both behaviours occur | FL | GFO20, GFO55, GFO73 |
| GFO64 | Tab-group destruction is routine | | AG | GFO45 |
| GFO65 | Prompt syntax: Omni is not Seedance | IMAGE_REF inline, attach order, say each ref's job, describe anyway, drop "No music"; 4th chip disabled | FL: "Google's own Omni guide" | PS rule 7 (SH jobbed refs); WF §5 (W3 same advice); GFO72; GFO53; GFO14/39 (cap CONFLICT) |
| GFO66 | Custom voices | Three fields; 18-20 s; save then bind | FL | GFO56 (retracted opposite claim) |
| GFO67 | A speaker whose face is not in frame gets a random voice | Face in frame while speaking | FL | TMD23 |
| GFO68 | A voice belongs to the CHARACTER | Bind at character creation | FL | TMD27 item 3; GFO47 (per-shot chip habit invalidated) |
| GFO69 | Binding a voice does not make the character talk | | FL | none |
| GFO70 | Why this matters more than it looks | Multi-speaker needs character-bound voices | FL | none |
| GFO71 | The rules that follow | Bind at creation; verify in picker; ข้อมูลตัวละคร | FL | none |
| GFO72 | IMAGE_REF_N numbered by ADD ORDER | | FL | GFO65; MG ("@handle first-appearance order", H3); HF32 (@Image1 drop order, SH); WF §2 (upload order, W3) |
| GFO73 | How a chip is added | + then row then เพิ่มไปยังพรอมต์ | FL | GFO55, GFO63 |
| GFO74 | The trap demonstrated | Inverted refs pass every check | FL | GFO85 |
| GFO75 | The rule | Decide order, add, re-read row | FL | none |
| GFO76 | APPEARANCE LOCK is the ground truth | Check shots against text | FL | AFP §13; IC |
| GFO77 | Voice: the API cannot do it | Flow UI vs Gemini API trade | FL | GFO28 |
| GFO78 | Price per second | Ultra ฿0.53/s vs API ฿3.50 | FL | AFP §14b (SH ฿/s) |
| GFO79 | Thai text (intro) | Image model can write | FL | TMD27 item 1 (CONFLICT) |
| GFO80 | What Nano Banana Pro does with Thai | One prominent phrase legible | FL (Nano Banana Pro) | none |
| GFO81 | So the rule is now | Quote the words and you get them | FL | TMD16, TMD27 |
| GFO82 | Settled, and what it cost | 12 credits | FL | none |
| GFO83 | The set drifts as much as the face | What the prompt does not say, the model decides | FL | ABL22 (SH); AFP §13 |
| GFO84 | Three fixed blocks (SET, POSTURE, NOT-LIST) | Paste verbatim | FL | IB STATE/GLOW/HOUSE_NEG (H3 pipeline, same idea); TMD12 ("no notebook, no pen, no paper") |
| GFO85 | Verify a chip by its THUMBNAIL | Flow tags locations as ตัวละคร | FL | AFP §7a; HF37 |
| GFO86 | The rule | Search box, preview, exclusion, order | FL | GFO85 |
| GFO87 | Both, every time | Grammar + thumbnail | FL | none |
| GFO88 | Field notes (21 entries) | Chip cap, NOT inventory, money Element, night, audio, captions x4, runner traps, vanish, wardrobe, arrest, RETRO pointer | FL | GFO11, GFO12, GFO14, GFO15, GFO59, GFO60; CONT7, CONT8; QC6, QC7 |

### SB (ai-video-storyboard/SKILL.md, external), all engine-agnostic by design

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| SB1 | AI Video Storyboard Generator (title) | | AG | none |
| SB2 | Overview | 5-15 s clips; consistency over single-shot quality | AG: "AI video generators produce 5-15 second clips" | none |
| SB3 | When to Use | >15 s videos | AG | AFP description (says storyboard with no generation is SB) |
| SB4 | Workflow (header) | | AG | none |
| SB5 | Step 1 Brief Intake | 5 questions | AG | none |
| SB6 | Step 2 Infer Structure | ~5 s shots, cadence table | AG | conflicts with measured lengths: PS 20 s, GFO 8 s, H3 5-12 s, W3 up to 30 s |
| SB7 | Step 3 Visual Consistency Layer | Palette, light, lens, film look, motion block | AG | IB GRADE block; PS grade block; GFO SET BLOCK |
| SB8 | Step 4 Write Each Shot | Per-shot template; end every prompt with "cinematic 1080p, synchronized audio"; "No model-specific hacks" | AG | PS THE TEMPLATE (CONFLICT: tech header FIRST, engine-specific rules) |
| SB9 | Step 5 Narrative Structure | Hook/Build/Payoff patterns | AG | TMD29; tig-scene-engine |
| SB10 | Step 6 Post-Production Checklist | | AG | none |
| SB11 | Step 7 Explain Why It Works | | AG | none |
| SB12 | Output Format | | AG | none |
| SB13 | References | Points to `references/*.md` which do NOT exist in `external/ai-video-storyboard-skill/` | AG | none |
| SB14 | License | MIT | AG | none |

### LC (CTO_ChatGPT-Image_LakornCover/SKILL.md)

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| LC1 | Lakorn cover (title) | | UN (ChatGPT gpt-image, none of the four) | none |
| LC2 | Model scope | ChatGPT Plus web UI + local lettering | UN: "Proven on: ChatGPT Plus web UI (gpt-image)" | none |
| LC3 | What it does | People, 3 logos, local lettering | UN/AG | none |
| LC4 | The layout | Ch3 poster slots; title is the identity | AG | TMD30 cover field note (~10 lines dup); memory `feedback_study_genre_references_for_identity.md` |
| LC5 | When to invoke | | AG | none |
| LC6 | When NOT to invoke | Festival films excluded | AG | none |
| LC7 | Workflow | Inputs, people, logos, spell-check, compose, send | UN | none |
| LC8 | Logo prompt template | | UN | none |
| LC9 | Rules 1-8 | No API; nothing from the ending; no royal banknotes; logo not font | UN/AG | rule 3 = TMD12 + GFO11 (royal-portrait banknotes, FL evidence); rule 2 = GFO60 (uniform spoils ending) |
| LC10 | Output format | | AG | none |
| LC11 | Worked example (banchi) | | UN | TMD30 |
| LC12 | Reference | | AG | none |
| LC13 | Field notes | empty | none | none |

### PS (docs/prompts/absence/PROMPT-STYLE.md), Seedance

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| PS1 | HOUSE PROMPT TEMPLATE (title + sources) | "applies to every video prompt" | SH: "Higgsfield's own Seedance guide ... cross-checked against what our own fires proved" | IR, IB docstring (restate it for H3) |
| PS2 | THE TEMPLATE | Tech header, refs with jobs, [Ns] beats, audio, negatives | SH | IB paste_block (implements it); SB8 (CONFLICT); WF §3 (W3 bracket timelines); GFO65 ("[0-3s]" Google example) |
| PS3 | THE TEN RULES | Tech first; timestamps; operator terms; no cuts; tone before line; physical verbs; jobbed refs; aimed negatives; front-load; identical nouns | SH: "Without 'no cuts, no zoom' Seedance invents cuts" | rule 4 vs ABL18 (tension); rule 7 = GFO65 + WF §5 + IR; rule 8 = AFP §11; rule 10 = IR fixed names + IC |
| PS4 | WHAT WE ALREADY DO RIGHT | "no music" every scene, one-colour casting, count thumbnails | SH | GFO53 + GFO65 ("drop No music", FL, CONFLICT by engine); IB HOUSE_NEG |
| PS5 | RULE 5 CORRECTED: manner tag only | Model spoke a stage direction; ≤5-word manner tag; transcribe | SH: "S15a take 1 (35b4edd4) transcribed with whisper" | AR rule 10 + A4; IB DIALOGUE_NEG (near-verbatim negative); GFO13; QC6 |

### AR (docs/prompts/absence/AUTHORING-RULES.md), Seedance

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| AR1 | Title / intro | What must not be inside a prompt | SH: "หลัง S1C fail 3 ครั้งติด" | PS1 |
| AR2 | Corpus sweep summary (16 files) | Real failures: notes in paste, stale text, bans that describe | SH | none |
| AR3 | PART 1 (header) | File-specific fix list | SH | none |
| AR4 | ก. urgent (header) | | SH | none |
| AR5 | A1 accident + blocker (s1-angles) | Historical per-line fixes | SH | none |
| AR6 | A2 stale text contradicts shot | | SH | AR19, AR20 (the general rules) |
| AR7 | A3 bans that describe the banned | | SH | AR17 (examples re-cited) |
| AR8 | A4 text leaks into quotes | | SH | PS5; AR22 |
| AR9 | A5 blocks that paste badly | | SH | AR21, AR23 |
| AR10 | A6 marker cancelled by its own sentence | | SH | AR15 |
| AR11 | ข. Hygiene | Token waste classes | SH | AR26 grep |
| AR12 | PART 2 (header) | Rules | SH | none |
| AR13 | 1 Two zones only | NOTES vs PASTE | SH/AG | HF17; IR; IB main() |
| AR14 | 2 Marker format with head and tail | | SH/AG | IB main() (verbatim marker strings) |
| AR15 | 3 No sentence cancels the marker | | SH/AG | AR10 |
| AR16 | 4 @Video 1 mentioned once | Warnings count as mentions | SH | HF18 ("video is a CHIP exactly ONCE") |
| AR17 | 5 Never quote the wrong example | Write the positive; short negative without description | SH | AFP §11 item 3 (CONFLICT: "name the exact wrong thing you actually got"); GFO65 rule 4 |
| AR18 | 6 Never type the banned word; split shared blocks | | SH | none |
| AR19 | 7 Announcement is not a fix | | SH | AR6 |
| AR20 | 8 Stop add-only sweeps | Read CRITICAL NEGATIVES on every edit | SH | AR6 |
| AR21 | 9 Every reference declared once, no pointers | | SH | HF16; IB assert (@ once); PS rule 7 |
| AR22 | 10 Dialogue manner tag ≤5 words | Pointer to PS | SH | PS5 (dup summary); IB DIALOGUE_NEG |
| AR23 | 11 One block = one shot | | SH/AG | none |
| AR24 | 12 ⚠️ is not a marker | | SH/AG | none |
| AR25 | 13 Numbers must count | | SH/AG | HF16; ABL13 |
| AR26 | Before Generate: 3 checks + grep | Pre-fire grep regex | SH | HF17 (prompt-lint.py); IR (same grep, adds `\.png`) |
| AR27 | File owner | CTO edits prompts; operator STOP AND REPORT | AG | GFO46 (workers do not edit skills) |
| AR28 | Added rule: previz ≥1280x720 | 640x360 previz killed S1C | SH: "Higgsfield ไม่เคยประกาศกฎนี้" | HF51 ("keep previz small ≤1.5 MB"); ABL59/63; skill blender-previz |

### IR, IC, IB (docs/prompts/ilag-topview/), the current MiniMax H3 pipeline

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| IR1 | README: shot prompts in the «Sorry, Sir» house format | Two zones, refs once, fixed names, beats, manner tags, grade, negatives; generated files; pre-fire grep | H3: "for our MiniMax H3 studio at 360p"; rules are the SH ones ("not new ones") | PS, AR (restated summary ~5 lines); AR26 grep (verbatim + `\.png`); IB docstring; AFP21; memory `feedback_new_film_prompts_use_house_format.md` |
| IR2 | The Elements table | 24 @handles, kinds, Drive files | H3: "create each once in the studio's Entities page" | IB REF (same Drive filenames); IC; MS Entities / @ID |
| IC1 | CAST.md for the TopView trailer | Canon rows, fixed names, locked lines, seat order, pole owner | H3 pipeline (AFP §13 applied) | AFP §13; IB CAST_KEYS + SEAT_ORDER (colour strings duplicated by design, asserted); GFO41 (FL analogue) |
| IB1 | Docstring header | Format from PS + AR; engine P1 = MiniMax H3 studio | H3: "Engine for P1: our MiniMax H3 studio (the @handle attaches the picture)" | IR1 (same summary); AFP21 |
| IB2 | REF dict | Per-handle reference text with a job; "take nothing of the white background" | H3 | IC (colours); ABL3 ("take NOTHING of its arrangement", SH); WF §2 design-sheet negative (W3) |
| IB3 | GRADE | DAY / TURNING / DARK_GLOW / DARK blocks | H3 pipeline | SB7; PS grade block |
| IB4 | HOUSE_NEG + DIALOGUE_NEG | No humans/land/text/grid/split/music; dialogue negatives | H3 | PS5 (DIALOGUE_NEG near-verbatim); MG (no grid); PS4 vs GFO53 (music) |
| IB5 | SCENES (data) | Per-scene spec, refs, beats, review | H3 | not audited line by line (scene data) |
| IB6 | CAST_KEYS | Each REF text must carry CAST colours | H3 pipeline | AFP §13 lint |
| IB7 | SEAT_ORDER | Fixed seat order asserted against CAST | H3 pipeline | IC |
| IB8 | SOUND + Studio marker | Only character sounds; `non_diegetic_music: none` stops the Studio's "wind and room tone" block | H3: "the Studio does not append its standing 'wind and room tone' block (MAC CTO letter)" | PS4; GFO53 (FL "no off switch") |
| IB9 | DEAD_LAMPS / WET / STATE / HOUSE_NEG_MOUNTAIN | Per-scene state lines pasted verbatim | H3 pipeline | GFO84 POSTURE BLOCK (FL, same idea) |
| IB10 | GLOW | One fixed light description reused | H3 pipeline | GFO84 SET BLOCK idea |
| IB11 | tag / paste_block | Builds the paste block: header, refs, frame, state, beats, soundscape, grade, negatives | H3 | PS2 (template) |
| IB12 | notes_top / notes_bottom | Engine note: single-panel pictures only; review order; file every take | H3: "a multi-panel sheet renders as a grid video on H3" | MG; HF15 ("Every clip is saved to Drive whether it passes or fails") |
| IB13 | main() | Asserts seat order, CAST keys, each @ exactly once, no em dash; writes marker zones | H3 pipeline | HF16; AR13-14, AR21; AFP §13 |

### MA, MG, MS (memory, MiniMax H3)

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| MA1 | Reachability | Mac-only studio, tailnet 100.64.2.37:4100, no ssh | H3 | letters in `docs/ops/letters/` |
| MA2 | API (per MAC CTO) | upload (415 on MIME), entities (returns whole list), shots/render (409 no pod), never /api/pod or /api/queue | H3 | MS (Render surface uses `/api/render`, a different route) |
| MA3 | DEADLOCK 2026-09-25 | Render refuses with pod off; empty queue auto-stops pod; offline enqueue requested | H3 | letter `...-offline-queue.md` |
| MA4 | Queue control + CEO queue rule | GET/DELETE /api/queue; delete only own items | H3 | memory `feedback_film_skills_engine_scoped_no_overlap.md` (same rule) |
| MA5 | Queue runner stops the pod when empty | Enqueue back to back | H3 | none |
| MA6 | Measured costs | H100 $3.29/h, H200 $4.59/h, boot ~7 min, 12 s 360p ~51 s warm / ~155 s cold | H3 | memory `reference_h3_pod_boot.md` (H100 $2.69/h, older) and `reference_h3_max_config.md` (~$0.30 per 15 s clip): different price points |
| MA7 | CEO 360p rule + tooling | 360p only for trailer previz; h3_add_entities.py, h3_fire.py | H3 | IR1, IB11 (360p in header) |
| MG1 | Grid reference fails (intro) | Grid in, grid out; <Picture N> defines the frame; Seedream differs | H3: "Tested 2026-09-03 on a live H100" | IB4, IB12; ABL3/ABL17 (SH uses four-panel plates); WF §2 (W3 sheet-layout negative) |
| MG2 | The real fix: nine slots | 9 image refs (12 files); slot order by @handle first appearance; 5-slot bug fixed | H3 | MS3 (still says 5 slots: stale); WF §1 (H3 "9/3/3/15"); GFO72, HF32 (positional order on other engines) |
| MG3 | Reference resolution | ref_image_size max = 2048 short edge; more refs slower | H3 | none |
| MS1 | Studio surfaces | Entities (= @Element), Shots (<Picture N>), Render, JSON store, rules.ts caps 9/3/3 | H3 | brief `docs/ops/briefs/h3-studio-add-ilag-entities.md` (restates store/atId); IR2 |
| MS2 | @ID character system | @Handle expands to refs + tags | H3 | IR2; IB1 |
| MS3 | Cap gotcha | r2v_max wires 5 slots | H3 | MG2 (CONFLICT: widened to 9 on 09-03) |
| MS4 | Render poll / timeout + orphan recovery | Queue-wait vs render time; outputs under "images" | H3 | none |
| MS5 | Speed + drift + LoRA plumbing | H200 preference; i2v continuation drift; LoRA for identity; @refs exclusive with i2v; Turbo LoRA always on; ethics | H3 | GFO28 (FL: frames vs refs exclusive in UI); memory `reference_h3_max_config.md` |
| MS6 | NSFW seam + seed | Own pod only; fixed noise_seed 42 | H3 | none |

### WR, WF (docs/promo/, Wan 3.0 on TopView)

| # | Section | Gist | Engine (evidence) | Overlaps with |
|---|---|---|---|---|
| WR1 | Title / sources | Page API + Terms + FAQ | W3 | WF1 |
| WR2 | Dates | Submission 28 Sep 06:59 Thai; Terms says 22 Sep | W3 | none |
| WR3 | Prizes | $15,000, 16 prizes | W3 | none |
| WR4 | Entry | Primary generation Wan3 on TopView; ≥30 s, ≥720p; after 4 Sep; watermark; hashtags | W3 | HF12, HF13 (SH contest rules, analogue) |
| WR5 | Judging | Weights 30/25/20/15/10 | W3 | none |
| WR6 | Judging weights are the design brief (CEO) | Every draft answers five questions | W3 | TMD29 (AG structure gate, different product) |
| WR7 | Rights | Non-exclusive licence | W3 | none |
| WR8 | Free Wan3 generations | 2 + 5, expire 7 days | W3 | WR12 |
| WR9 | Competition | 155 entries | W3 | WR11 |
| WR10 | Wan3 as TopView advertises it | 30 s, 1080/720p, modes, reference consistency, shot-level direction, audio unconfirmed | W3: "read 2026-09-23 from topview.ai/wan-3" | WF1 + WF3 (same claims and same Alibaba caveat, ~8 lines dup) |
| WR11 | Gallery | Genre counts | W3 | WR9 |
| WR12 | Extra credit routes | | W3 | WR8 |
| WR13 | ChatGPT images as Wan3 references: yes | Keep chat link as licence record | W3 | LC (ChatGPT images); HF12 (SH contest: external images banned) |
| WF1 | Title / caveat | Closed beta; not an Alibaba spec | W3 | WR10 |
| WF2 | 1 Modes and inputs | 480/720/1080p; up to 30 s; refs 10 img / 5 vid / 5 audio; audio unconfirmed | W3 | WR10; MG2 (H3 "9/3/3/15" per TopView vs memory "12 files total"); HF48 (Seedance 2.0 cap 9) |
| WF3 | 2 How a reference is tied to the prompt | Positional `@Image 1` or `<<<Image1>>>`; no Element library | W3 | HF32 (SH @Image1 drop order); GFO72 (FL add order); MG2 (H3 first-appearance order) |
| WF4 | 3 Shot-level direction | Multi-shot brief in one generation; bracket or Timeline forms | W3 | PS2 rule 2 (SH timestamps); ABL18 (SH: cuts carry no change) |
| WF5 | 4 Credit costs and plans | 1 / 0.5 / 0.3 credit/s; plans; Ultra has Wan3 720p 365-day unlimited | W3 | HF9 (TopView line; "60-day window, 720p cap" differs); AFP §14b |
| WF6 | 5 Prompt guidance | Name each reference and its job; consistency list; "Avoid" tail | W3 | PS3 rule 7; GFO65 rules 2-3 |
| WF7 | Could not confirm | Live limits, 480p, token style, native audio, avatars | W3 | none |

---

## 2. Overlaps and duplications (both locations, rough size)

Sizes are line counts of the duplicated passage on the smaller side unless stated. "Conflict" means the two copies disagree.

**Cross-skill, same engine**

1. **Mechanical audit, Flow.** QC What it does + Workflow + Rules (l.36-107) vs GFO "Every shoot ends with a mechanical audit" + "Never diagnose audio" (l.221-316) + 4 field notes (l.1926-1927, 1933-1934). Same tools table, same "OCR said 14, it was 3" story (told 4 times: QC rule 1, GFO body, two GFO field notes), same "look to confirm", same "what none of these can see", same pull --search story. About 35-45 lines duplicated. Also memory `reference_cheap_film_audit.md`.
2. **Flow deletions, night, wardrobe, REF_1.** CONT flags table + rules 1-4 (l.85-122) vs GFO "A clip that vanishes after Submit" (l.1332-1365), "What Flow silently deletes in an arrest scene" (l.1367-1392), the night paragraph (l.216-219) + field note 09-22 night, field notes 09-23 wardrobe and shot 106. The wording "an everyday khaki duty uniform, a metal badge" appears in both. About 40 lines. TMD Structure gate item 7 repeats the list a third time (5 lines); LC rule 2 a fourth (uniform on cover).
3. **Model tiers, Seedance.** AFP §14 (l.544-602, 58 lines) vs ABL 16:10, 16:35, 16:50, 17:10 (l.843-867) and 00:15 S2R-Q (l.912-921): same credits (98/53/38), bitrates (17.0 vs 4.3 Mbps), saturation (16-18%), cut timings, and the withdrawn background claim. About 25 lines of the same numbers and conclusions.
4. **Slot-never-idle, Seedance.** AFP §2 (l.55-69) vs HF Operating pattern bullet 1 (l.1150-1170), HF Pre-stage (l.1082-1101), HF "Never make a worker sit" (l.1513-1535), HF grant expiring (l.146-171), HF hard rule 4 (paid image lane, l.504-512). One idea written five times; about 15 lines on the AFP side, 80+ across HF.
5. **CAST / asset sheet / wardrobe, two engines.** AFP §13 (l.480-505) vs GFO ASSET SHEET + Wardrobe + APPEARANCE LOCK + set-drift blocks (l.887-937, 1737-1745, 1850-1879) vs TMD "Look at every plate" + Production constraint 2 vs ABL grandmother (l.569-591) vs CONT rule 4 vs IC. Same principle (one written source of every character's look, quoted into every prompt; an unnamed outfit is invented). About 15 lines AFP, 70 lines GFO.
6. **Prose vs reference, two engines.** AFP §7 (l.164-179) vs GFO "THE PROMPT OVERRIDES THE REFERENCE IMAGE" (l.871-885) vs TMD Production constraint 2 (4 lines). Same rule. Nuance: ABL S2PT fix (l.922-938) and memory `prose-cannot-beat-a-video-ref.md` say a Seedance VIDEO reference beats prose.
7. **Prop money, Flow.** TMD "Money on screen is invented prop money" (l.113-151) vs GFO "Anything that must look a specific way needs an Element" (l.181-219): the same prop-money paragraph (~6 lines, near verbatim). **Conflict:** TMD presents the words as the fix; GFO measured them failing on 6 clips and makes an Element the fix. Also CONT rule 7, LC rule 3, GFO set-drift NOT-LIST ("no notebook, no pen, no paper" in both).
8. **TMD Production constraints vs GFO.** TMD l.450-467 (18 lines) restate three GFO rules: text renders as garbage (**conflict**: GFO Thai text section l.1776-1848 says the image model writes one phrase legibly and quoted Thai renders in video), prompt overrides reference (GFO l.871), voice binds to character (GFO l.1639).
9. **Depth words / size, Seedance.** AFP §7b (l.217-237, 20 lines) vs ABL S2M size, S2M orientation, S2N gaze, S2M-B (l.77-209): lessons repeated, about 15 lines. Also memory `feedback_depth_words_are_a_size_instruction.md`.
10. **Names and copyright gate, Seedance.** AFP §10 (l.280-336) vs ABL S2Q, S2R, SC2, 13:20, 13:40 (l.60-75, 176-193, 246-264, 793-832). About 20 lines of lesson text; AFP still leads with "it was the name" while ABL S2R says the name story is confounded and the image was the trigger.
11. **Countable motion, Seedance.** AFP §11b (l.375-455) vs ABL 01:45 S2AC (l.948-955): about 8 lines near verbatim ("Motion the reviewer cannot COUNT is motion the model will not render").
12. **Continuity and QC scope blocks.** CONT l.21-44 vs QC l.20-34: same "Model scope, read this first" block, same "Proven on" line, same [ANY]/[FLOW] tag table. About 8 shared lines.
13. **Cover layout.** TMD Field notes 09-24 (l.530) vs LC "The layout" (l.37-54): the same Ch3 layout described twice, about 10 lines.
14. **Scene structure gate.** AFP "Scene structure comes first (IRON §51)" (8 lines) vs TMD order of work step 9 + Structure gate (both point at tig-scene-engine). About 5 lines.
15. **Commit the id before downloading.** AFP §9 (3 lines) vs GFO "Capture each clip's id at SUBMIT" (l.726-793) vs ABL S2S retracted (card by Created time) vs QC step 3. Same principle on two engines.

**Cross-skill, same rule restated on different engines**

16. **Every reference gets a stated job.** PS rule 7 (SH) vs GFO "Prompt syntax: Omni is not Seedance" rules 2-3 (FL) vs WF §5 (W3, TopView FAQ) vs IR1/IB2 (H3 pipeline). 3-5 lines each, four places.
17. **Positional reference numbering.** HF "THE EASY WAY" @Image1 (SH) vs GFO "IMAGE_REF_N numbered by ADD ORDER" (FL) vs MG "@handle first-appearance order" (H3) vs WF §2 upload-order `<<<Image1>>>` (W3). Same mechanism, four engines, four write-ups.
18. **Transcribe before judging dialogue.** PS RULE 5 CORRECTED "Always transcribe" (SH) vs GFO "Never diagnose audio you have not read back" (FL, 38 lines) vs QC stage 1 vs AR rule 10.
19. **Bisect one variable.** AFP §10 step 3 (SH) vs ABL 11:45 ladder (SH) vs GFO "How to work when a shot is refused" (FL). Same method; the measured TRIGGER differs by engine (SH: images and names; FL: dialogue, "the chips were never the trigger").
20. **Frames and references cannot be combined.** GFO "เฟรม and องค์ประกอบ are mutually exclusive" (FL UI) vs MS "@refs are conditioning and mutually exclusive with i2v" (H3).
21. **Multi-panel reference sheets.** MG + IB notes_top/HOUSE_NEG (H3: grid in, grid out) vs ABL S2E/SC5 (SH: four-panel location plates used, arrangement ignored, sky copied) vs WF §2 example ("do NOT render the sheet layout", W3). Engine-divergent facts on the same question.
22. **"No music".** PS template + "WHAT WE ALREADY DO RIGHT" (SH, "no music every scene") vs GFO Sound + Omni grammar rule 4 (FL, "Delete 'No music.'", twice) vs IB HOUSE_NEG "no music, no score" + `non_diegetic_music: none` (H3). **Conflict by engine.**
23. **Prohibitions.** AFP §11 item 3 "name the exact wrong thing you actually got" vs AR rule 5 "never quote the wrong example ... a ban that describes the image orders it" (**conflict**, both SH) vs GFO Omni rule 4 "describe what you want rather than negatives" (FL) vs PS rule 8 vs CONT rule 7.
24. **Look first vs mechanical first.** AFP §11b "LOOK AT IT FIRST, the number is a footnote" (CEO 09-11) vs QC rule 3 + GFO audit heading "Look at frames to CONFIRM, never to FIND" (CEO 09-23). Opposite emphasis, both CEO rulings.
25. **Who reviews.** AFP §9 "require a shot-by-shot description from the operator" vs HF "THE REVIEW LOOP: the operator never self-certifies, the CTO opens frames". **Tension.**
26. **Reference caps (numbers disagree everywhere).** HF "UP TO 50 REFERENCES" (2.5) vs HF Hard caps "Seedance 2.0 is 9" vs HF video-ref "11 chips accepted" vs AFP §14b "Higgsfield's 16" vs GFO (step 8b "cap 10", "Two ceilings" "still 3", Omni grammar "plan for three", "Which things get a chip" "four bind, cap 10", field note 09-22 "cap raised to 10") vs CONT "up to 10" vs MG "9 (12 files)" vs MS "5 slots" (stale) vs WF (Wan3 10/5/5; H3 and Seedance 2.0 "9/3/3/15").
27. **Free stills.** GFO measured costs + "Elements are free" + "most valuable fact" + "Every still is free" (four times in GFO) vs TMD Structure gate 8 vs CONT scope ("Nano Banana 2, free in Flow"). HF "Free IMAGE plates" is the SH analogue.
28. **Test-fire resolution/length, Flow.** GFO "Test fires run at 360p / 8 seconds, never 4 s" (behaviour tests) vs GFO Measured costs ("4 s 360p ... use this for every selector and plumbing test") vs GFO vanish and arrest A/Bs (behaviour, run at "360p/4s") vs CONT scope ("one 360p/4 s arm") and rule 2 ("A/B at 360p/4 s"). **Conflict** for behaviour tests; the plumbing exception is compatible.
29. **Previz.** AR "previz ≥1280x720" vs HF video-ref upload "keep previz ≤ ~1.5 MB" vs ABL 21:45 + S2PT fix (previz proxy occluded, told twice) vs skill blender-previz (outside this audit).
30. **Pre-fire lint.** HF PRE-FIRE (l.732-756) vs AR "Before Generate: 3 checks + grep" (l.273-287) vs IR (grep regex copied verbatim, plus `\.png`).
31. **@Video 1 once.** HF "PROMPT AUTHORING FOR A VIDEO REF" (l.812-816) vs AR rule 4 (l.171-184). About 8 lines.
32. **Character exactly once / count.** HF IRON RULE (l.707-730) vs AR rule 9 vs PS rule 10 vs IB main() assert vs ABL S15a-1 x2. **Tension:** HF says state the count in words; ABL S15a-1 measured that a count does not hold without placement.
33. **Storyboard vs house template.** SB Step 4 (per-shot prompt, "always end with 'cinematic 1080p, synchronized audio'", "no model-specific hacks", ~5 s shots) vs PS template (tech header FIRST, engine-measured rules, 20 s takes). **Conflict.**
34. **Pricing sources.** AFP §14b (Dreamina "free tier cannot produce one clip") vs HF 2026-09-13 ("Dreamina ... 225 free credits/day ≈ 2-3 Seedance 2.0 clips"): **conflict**. HF 09-13 "TopView ~$50/mo annual, 60-day window, 720p cap" vs WF §4 (Ultra $50/mo annual; 60-day is Seedance; Wan3 720p is 365-day unlimited).
35. **Wan3 spec written twice.** WR "Wan3 as TopView advertises it" vs WF §1 and §3: same claims and the same Alibaba caveat, about 8 lines.
36. **House-format summary written four times.** IR1 vs IB docstring vs AFP Field note 09-25 vs memory `feedback_new_film_prompts_use_house_format.md` (5-8 lines each).
37. **Grade / visual theme block.** SB Step 3 vs PS grade block vs IB GRADE vs GFO SET BLOCK: same "fixed look block pasted into every shot" idea.

**Inside one file**

38. **HF:** price-reading table x3 (UNLIMITED COVERS l.234-246, hard rule 2 l.415-421, Valder findings l.1243-1247; the file itself says it fixed one copy); wave cap ~5 x2 with the same "Missed 2026-08-14" story (l.1178-1187, 1567-1578); 90 s sleep cap x3 (render-wait, Hard caps, Task-brief checklist); mobile viewport lockup x3 (l.248-287, 920-926, 1723-1730); video-ref upload/attach x3 (l.758-824, 1611-1668, 1670-1694; the third contradicts the first on how to pick the file input); poll cadence x2 (**conflict**: 20-then-5 min vs 10-5-3 min); render wait vs "worker's job ends at the fire" (**conflict**); "Images always cost credits" vs Free IMAGE plates on Kling O1 vs 09-13 "GPT Image unlimited on Ultra" (**conflict**). "Reading the credit ledger" has a heading and no rule body.
39. **GFO:** chip cap stated five ways (**conflict**, see 26); chip attach mechanics x4 (step 8 ⋮ path, "⋮ menu is gone", "inconsistent", "How a chip is added"); voice material across 9 headings, including a bullet retracted in place; download failure x4 (dead button, in-page player, Chrome block, capture id/cache); which model to select (**conflict**: 12-step path and Traps say re-select Veo 3.1 Fast; "Which model for a drama" says Omni); account tier vs Ultra section; mute vs never press play; tab-group destruction x2; "No music" x2; free stills x4.
40. **ABL:** "a cut cannot carry a change" x2 (S2R-JC l.452-485 and l.633-666); "anchor both sides" x2 (S15a-1 l.266-293 and l.317-356); previz occlusion story x2 (21:45 and S2PT fix); "sheet negatives encode predictions" x2 (S21, S22); Madame cause stated then corrected (13:20 vs 13:40); mark darkness story x3 (S15a-2 correction, darkness entry, S2X). Structure defect: an orphan paragraph about the PENDING header sits under S15b (l.544-548) and most PASSED log entries sit below "## PENDING".
41. **AR:** Part 1 tables (A1-A6, file-specific, historical) re-cite the same examples as Part 2 rules 3, 5, 9, 10, 11 (about 25 lines duplicated inside the file).
42. **CONT/QC vs their own references:** both point at `docs/scripts/banchi-RETRO.md` and GFO sections they partly restate.

**Memory files that restate skill sections (by title, not read in this audit):** `feedback_depth_words_are_a_size_instruction.md` (AFP §7b), `prose-cannot-beat-a-video-ref.md` (ABL S2PT), `reference_cheap_film_audit.md` (QC / GFO audit), `reference_seedance_model_tiers_higgsfield.md` (AFP §14), `reference_higgsfield_madame_element_trigger.md`, `reference_higgsfield_copyright_reject_element.md`, `reference_higgsfield_closeup_moderation.md` (ABL ladder entries), `reference_higgsfield_unlimited_concurrency.md`, `reference_higgsfield_free_queue_jam.md` (HF), `reference_flow_voice_lock.md` (GFO voices), `feedback_new_film_prompts_use_house_format.md` (AFP field note).

---

## 3. Inbound references per skill name

Method: `rg -F` over the repo excluding `worktrees/`, `.git/`, `.venv/`, and excluding the skill's own directory. One file is noise and is excluded from the "real" count: `docs/ops/jev-lab-2026-09-23/options.json` holds every skill name as a score key, 59-73 times each. Under `~/.claude`, session transcripts (`*.jsonl`) and `file-history/` carry every name because the skill list is in every system prompt; only memory files are counted as real. The two project memory dirs (`-opt-mooniex-agents`, `-opt-MoonieXHQ-Agents-Core`) hold the same files, so memory counts are de-duplicated.

| Skill name | Repo files (real) | Occurrences (raw, incl. options.json) | Main referencing files | Memory files (unique) | Symlinked into ~/.claude/skills |
|---|---|---|---|---|---|
| `higgsfield-unlimited-gen` | **102** | 248 | 67 `docs/reports/absence-*` and `valder-*`; 15 `scripts/` (`scripts/browser/higgsfield-*.js` x10, `scripts/higgsfield/gen_loop.py`, `scripts/prompt-lint.py`, `scripts/skill-lint.py` + 2 lint tests); 6 `docs/prompts/absence/*` (incl. `CHECKLIST.md`); `config/decisions/browser.page_state.yaml`, `browser.moderation_action.yaml`; `tools/jev_lab.py`; `tests/test_decide_browser_sites.py`; skills browser-operator, blender-previz, winbox-desktop-gui, google-flow-ops, ai-film-production, CTO_Flow_Omni1.1_Continuity | 8 (`reference_higgsfield_model_routing`, `_protected_content_gate`, `reference_seedance_textonly_5s_cap`, `feedback_festival_rule00_no_edited_uploads`, `feedback_check_measures_wrong_thing`, `feedback_parallel_operators_share_chrome`, `feedback_untested_blocker_cost_six_hours`, `reference_flow_film_skills`) | No (Contabo: none; Mac map: no row) |
| `google-flow-ops` | **70** | 230 | 44 `docs/reports/banchi-*`, `teaser-shoot-*`, `flow-runner-build/*`; 5 `docs/briefs`; 4 `docs/scripts`; `docs/ops/google-flow-ultra-audit.md`, `flow-runner-USAGE.md`; `tools/flow_shoot.py` (5 citations), `tools/continuity_sheet.py`; `tests/test_decide.py` (**asserts `"google-flow-ops" in ids` for skill.route: a rename breaks this test**), `tests/test_decide_browser_sites.py`; `config/decisions/*.yaml`; `scripts/browser/banchi-plates-download.js`; skills browser-operator, winbox-desktop-gui, thai-moral-drama, CTO_Flow_Omni1.1_Continuity, CTO_Flow_Omni1.1_FilmQC | 4 (`reference_cheap_film_audit`, `reference_google_ai_plans_thailand`, `project_ai_thai_drama`, `feedback_new_google_product_urls_from_google_domains_only`) | No |
| `ai-film-production` | **14** | 77 | `docs/prompts/ilag-topview/build.py`, `CAST.md`, `CONTINUITY-AUDIT-cut3.md`; `docs/prompts/absence/s2s-*.txt`, `s2q-*.txt`, `COVER-YT-lineup-16x9.txt`; `docs/promo/topview-trailer/BIBLE.md`, `STORY-OPTIONS.md`, `SCRIPT.md`; 3 `docs/reports/absence-*`; `scripts/shot-motion.sh`; `docs/WAVE1-SKILL-PROVENANCE.md`. **No other skill references it.** | 4 (`feedback_new_film_prompts_use_house_format`, `feedback_my_own_cap_from_a_bad_diagnosis`, `feedback_depth_words_are_a_size_instruction`, `prose-cannot-beat-a-video-ref`) | No |
| `thai-moral-drama` | **6** | 71 | `tools/shotsheet_lint.py`; `claude-home/skills.txt`; skills google-flow-ops, CTO_Flow_Omni1.1_Continuity, CTO_Flow_Omni1.1_FilmQC, CTO_ChatGPT-Image_LakornCover | 3 (`MEMORY.md`, `project_ai_thai_drama`, `reference_flow_film_skills`) | **Yes on the Mac** (`claude-home/skills.txt` row, target `.../Agents/Core/.claude/skills/thai-moral-drama`); not on Contabo |
| `CTO_Flow_Omni1.1_Continuity` | 3 | 7 | `tools/continuity_sheet.py`; skills thai-moral-drama, CTO_Flow_Omni1.1_FilmQC | 3 (`MEMORY.md`, `reference_flow_film_skills`, `feedback_film_skills_engine_scoped_no_overlap`) | No |
| `ai-video-storyboard` | 2 | 67 | `docs/WAVE1-SKILL-PROVENANCE.md`; skill ai-film-production (description only) | 0 | No (but the repo entry `.claude/skills/ai-video-storyboard` is itself a symlink to `external/ai-video-storyboard-skill`) |
| `CTO_Flow_Omni1.1_FilmQC` | 1 | 4 | skill CTO_Flow_Omni1.1_Continuity | 1 (`reference_flow_film_skills`) | No |
| `CTO_ChatGPT-Image_LakornCover` | 1 | 3 | skill thai-moral-drama (field note) | 0 | No |

Related docs: `PROMPT-STYLE` is referenced from 6 files (AR, IR, IB, CONTINUITY-AUDIT-cut3, `scripts/prompt-lint.py`, and AFP only through its uncommitted field note); `AUTHORING-RULES` from 11 (HF is the only skill that points to it in committed text); `AB-LEDGER` from 19 (AFP + 17 `docs/reports/absence-*` + one prompt file); `TOPVIEW-WAN3-RULES` from 4 and `TOPVIEW-WAN3-REFERENCES` from 2 (`docs/promo/topview-trailer/SCRIPT.md`, `PROMPTS-H3-P1.md`); no skill references either Wan3 doc.

Symlinks: on Contabo `~/.claude/skills/` (= `/root/.claude/skills/`) holds only hyperframes*, media-use, relay-login and `synced/`; none of the eight film names. On the Mac, the map `claude-home/skills.txt` links only `thai-moral-drama` of the eight; it also links film-adjacent skills outside this audit: `seedance-scene-prompt` (target `/Users/gob/MoonieXHQ/Agents/Skills/seedance-scene-prompt`, not on Contabo, referenced by `roles/browser_operator.md`, `prompt_engineer.md`, `script_writer.md`, `video_editor.md` and skill character-reference-sheet), `tig-scene-engine`, `character-reference-sheet`.

---

## 4. Facts that live only in memory or docs, in no skill

### MiniMax H3 (sources: MA, MG, MS, IR, IB, letters in `docs/ops/letters/`, linked memories `reference_h3_max_config.md`, `reference_h3_pod_boot.md`)

- **Where it runs and how to reach it:** Mac-only studio (`comfy-runpod-worker/studio`, Next app), tailnet `http://100.64.2.37:4100` from Contabo, CEO calls it "localhost:4000", no ssh route. (MA)
- **API:** `POST /api/upload` (415 on wrong MIME); `POST /api/entities` `{kind,name,atId,notes,refs}` returns the WHOLE list including other people's; `POST/GET /api/shots/render` (409 when no pod); `GET/DELETE /api/queue`; never touch `/api/pod/*`; the CEO opens the pod (real money). (MA, letters)
- **Queue behaviour:** render refused while the pod is off and an empty queue auto-stops the pod (deadlock; offline enqueue requested from the Mac CTO); the queue runner stops the pod the moment the queue is empty, so enqueue every shot back to back; delete only your own pending items, one id at a time, checking the count (`h3_fire.py --cancel`). (MA, `feedback_film_skills_engine_scoped_no_overlap.md`)
- **Costs and timings (disagree across memories):** H100 $3.29/h, H200 $4.59/h, boot ~7 min, 12 s at 360p ~51 s warm / ~155 s first clip (MA, 2026-09-25); H100 $2.69/h (pod_boot, 2026-08-22); ~$0.30 per 15 s clip, r2v 278 s for 15 s (max_config).
- **CEO rules:** ILAG trailer previz at 360p only (MA); no background audio (IB SOUND comment, 2026-09-25); queue items are the CTO's to manage, pod runs need the CEO (scope memory).
- **Reference mechanics:** a multi-panel/grid reference renders as a grid video, and prompt prohibitions cannot fix it (`<Picture N>` defines the frame); single-panel pictures only. H3 takes 9 image refs (12 files total per MG; TopView says 9/3/3/15); refs are assigned in @handle first-appearance order, so the first handle mentioned claims slots; the old 5-slot wiring bug was fixed to 9 on 2026-09-03 (MS still says 5). `ref_image_size = max` = 2048 px short edge; more refs is slower. (MG, MS)
- **Studio model:** Entities (kind, refs with purpose label, atId) are the @Element equivalent; Shots auto-build the `<Picture N>` block; Render is the only pod-hitting surface; JSON store; caps 9 img / 3 vid / 3 aud per shot. (MS)
- **Prompt-side facts:** the Studio appends a standing "wind and room tone" block unless the prompt carries `non_diegetic_music: none` (IB comment citing a MAC CTO letter). No H3-measured prompt rule exists in any doc: IR states the P1 rules are the Seedance ones ("not new ones").
- **Render pipeline:** approved config BF16 2-pass r2v_max, 4-step Turbo LoRA always loaded, do not tick realism/motion LoRA on r2v, FaceRefine built but not default, fixed `noise_seed 42` (same composition unless the prompt changes), poll/timeout fix, orphan recovery from ComfyUI history (`outputs[node]["images"]`, subfolder `max`/`i2v`). (MS, max_config)
- **Identity drift:** chaining i2v last frame to next start drifts the face by clip 4-5; @refs are conditioning and cannot combine with i2v; a character LoRA is the identity fix; never use real-actress LoRAs. (MS)
- **Pod boot:** official template, no entrypoint override, `runtime: null` is not a failure, verify via `/system_stats`, Jupyter exec channel, installs persist on the network volume. (pod_boot)
- **ILAG specifics:** 24 entities created (`h3-entities*.json`), take naming `<tag>-H3-take<N>.mp4` in Previz/ (IB notes_bottom).

### Wan 3.0 on TopView (sources: WR, WF; one line in HF 2026-09-13)

- **Contest rules:** submission closes 28 Sep 06:59 Thai (Terms 6.1.2 says 22 Sep; two sources to one), $15,000 / 16 prizes, primary generation must be Wan3 on TopView, ≥30 s and ≥720p, made after 4 Sep (Sorry Sir and DND not eligible), challenge watermark, project link, public post with hashtags, judging 30/25/20/15/10 (CEO: the weights are the design brief), non-exclusive licence to TopView, free generations 2 + 5 plugin (expire 7 days), extra credit routes, 155 gallery entries with 2 thriller and 1 trailer. (WR)
- **Third-party images allowed:** ChatGPT images may be Wan3 inputs if rights are held; keep each chat link as the licence record; a ChatGPT still shown as a shot does not count as Wan3 footage. (WR) Contrast HF Rule 00 for the Higgsfield festival.
- **Model (advertised, unverified):** up to 30 s single continuous shot, 2-30 s; 480p/720p/1080p; 16:9, 9:16, 1:1, 4:3, 3:4; modes Omni Reference, Image to Video, Text to Video; inputs text/image/video/audio (+ documents/webpages); refs up to 10 images, 5 videos, 5 audio (20); native audio unconfirmed; closed beta since 2026-08-06; not confirmed by Alibaba. (WR, WF)
- **Reference syntax:** positional, by upload order: `@Image 1` (UI demo) or `<<<Image1>>>` / `<<<Audio1>>>` (TopView's own examples); no saved Element library; the character name is written in prose after the tag; Direction box cap 3500 characters. (WF)
- **Shot-level direction:** several shots in one generation, written as prose, as `[0-4s] ...` brackets, or as `Timeline: 0.0-3.0s | ...`. (WF)
- **Prompt guidance (TopView FAQ):** describe subject, beats, action, camera, light, performance, sound, pacing, final composition; name each reference and explain its job; list what must stay consistent; close with an "Avoid ..." tail (incl. "rendering the reference sheet layout"). (WF)
- **Pricing:** 1080p 1 credit/s, 720p 0.5 (0.4 with 20% off), 480p 0.3; Pro $29 ($16 annual, 960 credits/yr), Business $75/$44, Ultra $150/$50 (500/month, plus "Wan 3.0 720P 365 Days Unlimited" and 60-day unlimited Seedance), Team; top-ups valid 24 months. HF's one TopView line ("~$50/mo annual, 60-day window, 720p cap") does not match this breakdown. (WF, HF)
- **Open questions (need a logged-in look):** real upload limits, whether 480p is selectable, which token style the live box accepts, native audio, whether avatar/asset libraries plug into Omni Reference, file limits, live per-second cost. (WF)
- **No Wan3 generation has been measured by the org yet;** every Wan3 fact above is TopView's marketing or contest text.
