# Duplicate characters in AI video — every recorded lesson and the fix that worked

Research 2026-10-04 (read-only). Searched: auto-memory, `.claude/skills/**`, `docs/**`, `Agents/Wikis`, `Agents/Rules`
(Rules has nothing on this). Paths are relative to `/Users/gob/MoonieXHQ/Agents/Core/` unless absolute.
`MEM/` = `/Users/gob/.claude/projects/-Users-gob-MoonieXHQ-Agents-Core/memory/`.
`WORK/` = `/Users/gob/MoonieXHQ/Assets/Agents/Core/last-bell/work-a0a0aeec/`.

**The short version.** The org has fought this mostly on «Sorry, Sir» (Seedance 2.5 on Higgsfield, Aug–Sep 2026). The
CEO made it an IRON RULE on 2026-08-30. What fixed it, measured take by take, was not the count by itself. The
count and the verbatim negatives were needed but not enough. What held was: (1) **every person gets a WHERE**, and
no region of the frame is left empty for the model to fill with a copy; (2) **every person gets a WHAT-HE-WEARS**,
so extras are not dressed in the only costume the prompt describes; (3) **the signature item gets one owner,
stated three ways** (a count, an ownership rule, a placement ban). THE LAST BELL's Governor prompts break all three,
and the re-shoot round (rs1) fixes only part of it.

---

## Part 1 — The lessons, in date order

### L1 · 2026-08-21 · Seedance 2.5 (Higgsfield) · CEO rule: write the "no repeated face" ban in two places
- **Rule:** the no-repeated-face ban (and the audio-endpoint ban) must sit **both in the SOUND block and in the
  negatives line**, because a ban written in only one place got dropped.
- **Proven?** No A/B recorded. It is a CEO rule, written up in research.
- Evidence: `/Users/gob/MoonieXHQ/Agents/Wikis/research/2026-09-03-seedance-prompt-structure.md:193`, `:99`.
  The same page notes that Seedance **2.0's** official guide carries anti-duplicate boilerplate (`:120`, `:226`).

### L2 · 2026-08-29/30 · Seedance 2.5 · S1D: two Dupes (over-the-shoulder man plus a second cleaner)
- **Symptom:** take 1 `be929c0a` showed the over-the-shoulder man AND a second, identical cleaner wiping the wall.
- **Cause found:** the model read "over his shoulder" and "he wipes" as two separate men.
- **Fix:** "ONE PERSON ONLY … the shoulder in the foreground and the hand that does the wiping BELONG TO THE SAME
  MAN. There is no second cleaner, no second cap, no one else in the room."
- **Proven: YES.** S1D take 2 `ab366138` is a keeper.
- Evidence: `docs/prompts/absence/QUEUE.md:538-544`, `docs/prompts/absence/s1-angles.txt:103-106`, keeper at
  `QUEUE.md:36`, `:466`. Later hygiene ruling: delete the two sentences that describe the TWO Dupes and keep only
  the positive ones (`docs/prompts/absence/AUTHORING-RULES.md:42`).

### L3 · 2026-08-30 · Seedance 2.5 · S8c: two Valders side by side
- **Cause found:** the prompt asked for SYMMETRICAL rows of guests around a man dead centre. The model mirrored the
  centre figure to complete the symmetry.
- **Fix:** "THE SYMMETRY BELONGS TO THE GUESTS ONLY. Valder is the single ASYMMETRIC thing in the frame — one man,
  dead centre, unmirrored. There is EXACTLY ONE VALDER … the ONLY person wearing a panelled multi-colour [jacket]".
- **Proven: PARTLY.** S8c take 2 went into Drafts 3 and 4, and no duplicate was recorded against it. No explicit
  PASS line was found.
- Evidence: `MEM/feedback_cto_reviews_every_clip.md:12-14`, `docs/prompts/absence/s7-s9.txt:384-393`,
  `docs/reports/absence-draft4-fixlist-20260908.md:17`, `.claude/skills/CMO_Knowledge_Seedance2.5_Higgsfield/SKILL.md:1591-1593`.

### L4 · 2026-08-30 · Seedance 2.5 · CEO IRON RULE: every character appears exactly once (after S4 drew two Dupes with two carts)
- **Mechanism (the skill's diagnosis):** "Seedance duplicates a character whenever the prompt gives it two
  independent reasons to draw the same person (a binding + an unbound description, **a group noun + a named
  member**, or — the worst case — a video-ref proxy + its mapped character)."
- **Fix, both halves required:** (1) in the beats, the count in words ("his TWO guards and no others", "there is
  exactly ONE Dupe in this shot"); (2) in the negatives, verbatim: `no duplicate characters, no twins, no character
  appearing twice`.
- **Review rule:** a duplicate is fixed on sight, with no question to the CEO. Label the take
  `-FLAGGED-duplicate-<who>`.
- **Proven?** The count is "necessary, not sufficient" (measured 2026-09-08/09, see L7–L10).
- Evidence: `.claude/skills/CMO_Knowledge_Seedance2.5_Higgsfield/SKILL.md:1467-1494`, `:1586-1589`;
  `MEM/feedback_cto_reviews_every_clip.md:32-38`; `docs/prompts/absence/QUEUE.md:81-88`.

### L5 · 2026-08-30 · Seedance 2.5 · a multi-person plate carries its head count
- **Symptom/cause:** the Valder guard plate shows six men. The scene needs two.
- **Fix wording:** "UNIFORM AND FACES ONLY — its plate shows six; take the look, never the count." General
  principle: "a plate always carries count, framing, background and light that we did not ask for, and text alone
  cannot remove it; the removal has to be stated per reference."
- **Proven?** No A/B. And S2S-B t2 (L7) bound a TWO-guard plate with the count stated, and it still rendered four.
  So this wording is not enough alone.
- Evidence: `docs/prompts/absence/QUEUE.md:160-167`, `docs/prompts/absence/s7-s9.txt:35`,
  `/Users/gob/MoonieXHQ/Agents/Wikis/research/2026-09-03-seedance-prompt-structure.md:191`.

### L6 · 2026-09-03 · any engine · never quote the bad example inside the prompt
- **Cause found:** the lines meant to ban duplicates described them: "two identical men in panelled jackets standing
  side by side" (s7-s9 ×4), "two cleaners, two carts", "came back with TWO Dupes". A model reads the description,
  not the intent.
- **Fix:** write the positive sentence plus a short negative with no description: "EXACTLY ONE VALDER, dead centre,
  unmirrored." Not "take 1 rendered him twice — two identical men…".
- **Proven?** A writing rule. Its evidence is the S1C failure (`Seedance SKILL.md:1498-1501`). No A/B on duplicates.
- Evidence: `docs/prompts/absence/AUTHORING-RULES.md:190-204`, `.claude/skills/CMO_Standard_Film_PromptFormat/SKILL.md:76-79`.

### L7 · 2026-09-07/08 · Seedance 2.5 · an empty side of the frame gets filled by copying the nearest costume
- **Symptoms:** S15a-1 t1 put the Registrar (one man, one chip) at BOTH frame edges. S2S-B t2 rendered a two-guard
  plate as FOUR guards, mirrored across the group. S15a-2 t1 drew a fourth guard.
- **What the sheets already said:** the count, in capitals. S2S-B even had "This one picture is both of them" plus
  "no face is repeated anywhere". **Stating the number did not stop the duplication.**
- **Cause found:** "one side of the frame had nothing named standing in it. The model filled the empty side by
  copying the closest chip it had … an unoccupied region is an instruction to invent an occupant, and the cheapest
  occupant is the one already on screen." The ledger calls it a composition failure, not a counting failure.
- **Fix:** name the side of frame for each group and **name who holds the opposite side**. For the distinctive
  character: "THERE IS EXACTLY ONE REGISTRAR — one man, standing on the RIGHT side … He is the only person in the
  entire frame wearing a black suit with white gloves and a gold V; every other guest wears something different."
- **Proven: YES.** S15a-1 t2 PASSED 2026-09-08 02:10: one registrar on the right, no copy on the left, exactly two
  navy uniforms. S15a-2 t2: the mirrored fourth guard was gone.
- Evidence: `.claude/skills/CMO_Knowledge_Seedance2.5_Higgsfield/AB-LEDGER.md:288-342`, `:391-392`.

### L8 · 2026-09-08 · Seedance 2.5 · a person with no position takes the most visible slot
- **Symptom:** S15b t2. The workman (bound, described, never placed) stood in Dupe's place for all 20 s. Dupe never
  appeared.
- **Fix:** "HE IS NOT THE MAN AT THE WALL. He stands FAR LEFT beside the two navy guards." Dupe's chip gains "HE IS
  THE MAN AT THE WALL — dead centre".
- **Proven: YES.** Take 3 PASS. "Every chip that is a person gets a WHERE, not only a WHAT."
- Evidence: `AB-LEDGER.md:481-509`.

### L9 · 2026-09-08 · Seedance 2.5 · a person with no wardrobe sentence is dressed from the rest of the prompt
- **Symptom:** the grandmother wore the Madame's sunglasses and a purple scarf, so the climax had two grandmothers.
- **Cause found:** her chip described her wheelchair for eight lines and her clothes for none. The model borrowed
  the nearest striking attribute in the prompt.
- **Fix:** "SHE WEARS EXACTLY WHAT HER PICTURE SHOWS AND NOTHING ELSE: a GREY knitted headscarf … NO sunglasses on
  her — the sunglasses in this room belong to other people."
- **Proven: YES.** S2S-B t3 PASS, and S15b t2 and t3 both came back right. CAST.md now gives every character a
  WHERE and a WHAT-SHE-WEARS. A related rule: two references for one character is a CAST defect
  (`.claude/skills/CMO_Knowledge_Film_Production/SKILL.md:44-45`).
- Evidence: `AB-LEDGER.md:530-552`. Same family: "an attribute or a place with no named owner goes to whoever is
  nearest" (`AB-LEDGER.md:497-501`).

### L10 · 2026-09-08/09 · Seedance 2.5 · two people from one reference merge, or two people fuse
- **Symptom:** S16 t1. Two navy guards who share one reference merged into ONE body.
- **Fix:** give each man a position: "half a step IN FRONT of the tall one so that BOTH navy tunics and BOTH gold
  V's are seen whole". "Shoulder against the first" had invited the merge.
- **Proven: YES.** S16 t2 rendered three distinct bodies. The opposite failure also happened: in S2R-JC t3 the
  registrar merged into Carrington (`AB-LEDGER.md:597-600`).
- Evidence: `AB-LEDGER.md:556-592`.

### L11 · 2026-09-09/10 · Seedance 2.5 · S2PT: a duplicate bodyguard, missed on small tiles
- **Symptom:** take 1 had two bodyguards in black. The CTO passed it on 426-px tiles; the worker caught it at full
  resolution.
- **Fix (sheet v2):** a countable cast by clothes, with "ONE man in black" stated three ways, and Carrington placed
  behind the shoulder.
- **Proven: YES.** Take 2 PASS: "counting the cast by clothes + 'ONE man in black' stated three ways removed the
  duplicate on the first retry."
- **Review rules from it:** count heads at FULL resolution. Count named props the same way, in two frames, and crop
  the frame edges. The prop version of the fix states the number three ways: a count ("Count the carts: ONE"), an
  ownership rule ("if Dupe is not pushing it, it is not there"), and a placement ban.
- Evidence: `AB-LEDGER.md:667-676`, `:785-789`; `MEM/feedback_count_props_like_you_count_cast.md:18-21`.

### L12 · 2026-09-11 · Seedance 2.5 · S2AC v4: two identical women in cobalt coats; the guard missing from 68 of 104 sheets
- **Cause found:** v4 said only "the complete cast is seven and not one more". It gave a group count and no count
  per character, and "a group noun invites a duplicate". The IRON RULE guard had been absent from all five versions
  of the sheet and six takes. A project sweep found 68 of 104 sheets without it.
- **Fix (v5):** a per-character list ("exactly ONE cleaner, exactly ONE woman in magenta … SIX DIFFERENT FACES, SIX
  DIFFERENT OUTFITS"); a lookalike ban ("THERE IS ONLY ONE WOMAN IN A BLUE COAT … Nobody stands beside her who
  resembles her"); "If a figure is not named below it must not exist"; the verbatim negatives plus "NO TWO WOMEN IN
  BLUE COATS, no lookalike standing next to anybody". The check also went into `scripts/prompt-lint.py`
  (IRON_RULE_DUPLICATE).
- **Proven: YES, with a caveat.** v5 had "คนซ้ำหายแล้ว", one blue woman in every frame. But v4 t2, from the
  UNCHANGED sheet, also had no duplicate, so the report itself concludes duplicates are **per-take variance, not a
  fixed outcome of a sheet**. The guard lowers the odds.
- Evidence: `docs/prompts/absence/s2ac-fix2-the-interpretations-chaos.txt:23-28`, `:170-183`, `:285-290`;
  `docs/reports/absence-overnight-20260911.md:20-21`, `:48-49`, `:69-78`; `MEM/move-remembered-rules-into-the-linter.md:11-19`;
  `scripts/prompt-lint.py:417-442`.

### L13 · 2026-09-22/23 · Google Flow (Veo 3.1 / Omni) · banchi: "the father's face on the officer" and REF_1 face drift
- **Symptom A:** the officer วิทย์ in shots 149 and 151 got the FATHER's older face.
- **Cause found A:** one full-body still of him in uniform. A character regenerated in other clothes comes back with
  a different face, and here it sat next to the father's close-up plate.
- **Fix A:** his face plate plus a separate wardrobe plate with no person in it (`WARDROBE`). The character asset
  stays untouched.
- **Proven A: YES.** A/B arm B held (arm A, the plate only, gave "a different man"). 151 was re-shot and filed.
  The CEO approved all 7 acts.
- **Symptom/fix B:** a face seen in profile as the second reference (REF_1) in a close-up drifted: the son's hair in
  106 (twice), the father's shirt in 149/150/188/189. The fix was to put the shot's subject first (REF_0), facing
  3/4 to camera. **Proven:** 106 take 3 and 107 held.
- **Related (attribute migration):** a patient's nasal cannula moved to whoever sat on her bed. A negative lost to
  the staging; restaging fixed it (169 re-shot clean).
- **Caveat:** this is Flow, and a lakorn. The CEO said on 2026-10-03 not to bring lakorn rules into THE LAST BELL
  (`MEM/project_film_last_bell.md:51`). These are engine/reference findings and are untested on Seedance 2.0.
- Evidence: `.claude/skills/CMO_Gate_Flow_Omni1.1_Continuity/SKILL.md:103-119`, `:121-123`;
  `docs/scripts/banchi-RETRO.md:11-13`, `:53`; `.claude/skills/CMO_Gate_Flow_Omni1.1_FilmQC/SKILL.md:209-216`;
  `MEM/project_banchi_film_status.md:67-72`, `:90-101`, `:136`; `MEM/feedback_a_continuity_rule_is_not_an_exclusion.md:8-15`.

### L14 · 2026-09-03 · MiniMax H3 · a multi-panel sheet in gives a grid video out
- **Rule:** "Every reference picture is ONE photograph. A multi-panel sheet in = a grid video out, for the whole
  clip; no prompt wording prevents it." Crop single panels and remove labels and numbers. The ShortFilm workflow and
  the Wan 3.0 skill repeat it for their engines.
- **Proven:** on H3 (live H100). It is about grids, not duplicates, and was **never measured on Seedance**.
- Evidence: `.claude/skills/CMO_Knowledge_MiniMax_H3/SKILL.md:50-52`; `.claude/skills/CMO_Workflow_ShortFilm/SKILL.md:129`;
  `.claude/skills/CMO_Knowledge_Wan3.0_TopView/SKILL.md:125-126`.

### L15 · 2026-10-04 · champa Seedance 2.0 · THE LAST BELL: the Governor doubled (the new case)
- **Symptom:** a second man in the Governor's white jacket and gold chain appeared in **3 of the 5 takes that bind
  the Governor sheet**:
  - B01 t2 NOTE: "right servant wears similar white jacket with gold chain";
  - B04 t2 FAIL: "a second Governor double (white jacket, gold chain, **moustache**) stands beside him from ~7 s";
  - D03 t1 FAIL: "second white-jacket gold-chain man doubles the Governor".
  B01 t1 and B04 t1, from the same prompts and the same sheet, had no double. That fits the per-take variance in L12.
- **Fix drafted (rs1):** "only one man in a white jacket" in the negatives (B04, D03), and "his men in plain brown"
  (D03 only).
- **Proven: NO.** rs1 is queued and has not been re-QC'd.
- **Support from the same film:** B03 t1 PASSED. Its extra was named (OLD BOATMAN), dressed ("white beard,
  bare-chested, faded loincloth"), placed ("sits at screen-left in profile"), and banned from the lead's look ("the
  OLD BOATMAN is not THE GOVERNOR and wears no gold"). That is n=1, and B03 does not bind the Governor sheet.
- Evidence: `.claude/skills/CMO_Gate_Champa_Seedance2.0_ShortMovieQC/SKILL.md:79`, `:102-112`; `WORK/lb_out/qc/eye-B.tsv`
  (B01 t1/t2, B03 t1, B04 t1/t2); `WORK/lb_out/qc/eye-DE.tsv` (D03 t1); `WORK/lb_build_rs1.py:21-25`, `:45-47`;
  `WORK/jobs-wave1.json` (lb-B01, lb-B03, lb-B04, lb-D03); `WORK/lb_jobs_rs1.json` (lb-B04-rs1, lb-D03-rs1).

---

## Part 2 — Why the Governor doubled: the wave-1 prompts checked against the lessons

| Lesson | B01 / B04 / D03 wave 1 | rs1 (B04, D03) |
|---|---|---|
| L4 count in words ("exactly ONE GOVERNOR") | absent in all three | still absent (B04 says "stands alone", which is closer) |
| L4 verbatim negatives `no duplicate characters, no twins, no character appearing twice` | absent | still absent |
| L4 "group noun + named member" | "servants" (B01), "his men" (B04, D03), "a crowd" | "his men" remains; D03 dresses them |
| L9 extras get a wardrobe sentence | none. The only costume in each prompt is the Governor's, so the extras borrow it | D03 "plain brown"; B04 rope-cutters still undressed |
| L7/L8 every person gets a WHERE; no empty region | B01 servants unplaced; D03 "crowded with his men"; B04 "golden barges slide away" (other barges have no named occupant) | B04 cutters "on the solid bank end"; D03 men still unplaced |
| L11 the signature item stated three ways | none | one way only ("only one man in a white jacket") |
| L5 reference job: "take the look, never the count" | "face, body, clothes, gold; ignore the sheet layout and background" | unchanged |
| L14 single-panel reference | `ch_governor_a` is a sheet: 4 numbered emotion panels + 1 full-body panel, the same man five times (`docs/prompts/last-bell/build_refs.py:22-30`, `docs/reports/last-bell-refs-r1/REPORT.md:27`) | unchanged |
| Lint (L12) | `scripts/prompt-lint.py:424-425` checks only when **≥2 `@…char_…` chips** are bound. champa prompts use `@ภาพN` and bind one character, so the check never runs on these shots | same |

The skill's own diagnosis (L4) describes this case exactly: the Governor reference plus "THE GOVERNOR's men" or
"servants" (a group noun beside a named member), with no clothes given to the group. The only costume in the text
is white silk and gold, so that is what the extras wear. In B04 t2 the double also had his moustache, so the face
was copied as well as the costume.

---

## Part 3 — Apply to THE LAST BELL (Seedance 2.0, 16:9, 15 s, ≤9 refs, ≤2,000 chars)

Each recommendation is marked PROVEN (with the take that proved it) or UNPROVEN. "Proven" means proven on
Seedance 2.5 / Higgsfield unless stated; **none of these is yet proven on champa Seedance 2.0.**

### Prompt wording

1. **Give every extra a costume with no white and no gold, and make the Governor the only owner of white and
   gold.** In WHO: "THE GOVERNOR … the only person in the frame wearing white or gold." For the extras: "TWO
   ROPE-CUTTERS: lean boatmen in plain brown cotton and dark loincloths, bare heads, no jewellery."
   **PROVEN:** grandmother, S2S-B t3 / S15b t2–t3 (AB-LEDGER:530-552); registrar "only person in the entire frame
   wearing…", S15a-1 t2 (AB-LEDGER:322-329). In-film: B03 t1 (n=1).
2. **Name the group once, with its look, and drop the bare group noun.** Write "TWO ROPE-CUTTERS" or "HIS
   OARSMEN", never just "his men" or "servants". Use one name per character every time (PromptFormat:63-64).
   **PROVEN** as part of S2AC v5, where a per-character list replaced "the complete cast is seven" (L12). The
   mechanism is Seedance SKILL.md:1471-1473.
3. **Place every person, and fill both sides of the frame.** B04: cutters on the bank at screen-left; the Governor
   alone at the rail of the last barge at screen-right; the other barges "rowed by small brown-clad oarsmen", so no
   barge is left empty. D03: the Governor alone at the stern rail, screen-right edge; the oarsmen at the bow,
   nearest the tail. If B01 is ever re-shot: "two SERVANTS in plain brown stand behind him at screen-right holding
   the parasol pole".
   **PROVEN:** S15a-1 t2 (AB-LEDGER:288-342), S15b t3 (:481-509), S16 t2 (:556-592).
4. **Count in the body:** "There is exactly ONE GOVERNOR." "Necessary, not sufficient."
   **PROVEN** only together with 1–3 (S2AC v5, S1D t2). Count alone failed on S15a-1 t1 and S2S-B t2 (AB-LEDGER:301-303).
5. **Verbatim negatives, at the head of CRITICAL NEGATIVES:** `no duplicate characters, no twins, no character
   appearing twice; nobody beside THE GOVERNOR`.
   **PROVEN** only as part of S2AC v5. Alone, S2S-B carried "no face is repeated anywhere" and still duplicated.
   The CEO's 2026-08-21 rule says to repeat the ban in the SOUND line too (L1): **UNPROVEN**, and it costs about 60
   characters.
6. **State the signature item three ways:** a count ("one white silk jacket in this shot"), an ownership rule ("THE
   GOVERNOR is the only person in white or gold"), and a placement ban ("nobody beside him at the rail").
   **PROVEN:** S2PT t2, "ONE man in black" stated three ways (AB-LEDGER:667-676). Use the frame-wide ownership
   sentence rather than "only one man in a white jacket" alone. That rs1 wording is one of the three ways, and
   **UNPROVEN** by itself.
7. **Never describe the double in the paste block** (no "a second man in a white jacket stands beside him").
   Positive count and short bans only. **Rule** (AUTHORING-RULES:190-204); not A/B'd for duplicates.
8. **No symmetric composition around the Governor.** If symmetry is wanted, it belongs to the extras, and he is the
   one asymmetric figure. **PARTLY PROVEN:** S8c t2 (L3).

### Reference images

9. **Change the Governor reference's job:** "@ภาพN — THE GOVERNOR, one man: face, body, clothes, gold; the sheet
   shows him several times, take the look, never the count; ignore the sheet layout and background."
   **UNPROVEN.** The wording comes from the Valder guard plate (QUEUE.md:164-167); S2S-B shows that wording alone
   does not stop a mirror.
10. **Single-panel plate:** crop the full-body panel of `ch_governor_a` (one figure, no numbers or labels, nothing
    else in it) and bind that instead of the 5-panel sheet.
    **UNPROVEN on Seedance.** The single-photo rule is measured on H3 only, where it is about grids (L14).
    "One character per plate" (Film_Production §3:51) means one character, not one picture of him. B01 t1 and B04
    t1 used the same sheet and did not double, so the sheet alone does not cause it. Cheap test on the free lane:
    take the B04 text with fixes 1–6 and fire 2 takes with the sheet and 2 with the full-body crop.
11. **A face plate plus a person-free wardrobe plate** (the banchi fix) is **PROVEN on Flow only** (L13). It costs
    one more slot (9 available; B04/D03 use 2–3). It also clashes with "two references for one character is a CAST
    defect" (Film_Production:44-45) unless the second reference is a garment with no person. Treat it as UNPROVEN
    here; try it only if 9–10 fail.

### Firing and review

12. **Fire 2 takes of each re-shot Governor shot.** Duplicates vary from take to take (L12; here B01 and B04 t1 were
    clean and t2 doubled). The free lane makes this cheap. **PROVEN** that the variance exists (S2AC v4 t1 vs t2).
    The ShortMovieQC gate (stage 5) still files "a costume doubled" as systematic, so fix the prompt AND take two.
13. **Review:** count heads at full resolution in ≥2 frames, crop the edges, and count the signature items (white
    jacket, gold chain, gold buttons) the way props are counted. **PROVEN** as a method: S2PT t1 was caught at full
    resolution after tiles passed it (AB-LEDGER:669; `MEM/feedback_count_props_like_you_count_cast.md:18-21`). Per
    the CEO's loop, a duplicate is fixed on sight without asking (Seedance SKILL.md:1588).
14. **Put the check in the builder, not in memory.** `prompt-lint`'s IRON_RULE check never runs on champa prompts
    (it needs ≥2 `@…char_…` chips). A check in the LAST BELL builder could flag any prompt that binds a lead and
    contains a group noun (men, servants, crowd, guards, oarsmen) but lacks "exactly ONE" and the verbatim
    negatives. **UNPROVEN** (tooling); the reason is `MEM/move-remembered-rules-into-the-linter.md:49-53`.

### Drafts that fit the 2,000-character cap (measured: B04 1,972 chars, D03 1,833 chars)

These apply fixes 1–6 and 9 to the rs1 text. Not fired, so **UNPROVEN**.

**B04 (rs2 draft)**
```
15 seconds · 720p · 16:9 · ONE CONTINUOUS TAKE, NO CUTS, no zoom, a slow pan following the barges screen-left to screen-right.
Under a black-green sky, two ROPE-CUTTERS cut the bridge as THE GOVERNOR's barges leave.
REFERENCES: @ภาพ1 — THE CANAL and its long wooden footbridge. @ภาพ2 — THE GOVERNOR, one man: face, body, clothes, gold; the sheet shows him several times, take the look, never the count; ignore the sheet layout and background.
WHO: THE GOVERNOR, heavyset Thai man in his fifties, white silk jacket, gold buttons, gold chain, gold fan; the only person in the frame wearing white or gold. TWO ROPE-CUTTERS: lean boatmen in plain brown cotton and dark loincloths, bare heads, no jewellery.
THE FRAME: Wide over THE CANAL: the long footbridge to the chedi island crosses the frame; the TWO ROPE-CUTTERS stand on the solid bank end at screen-left; golden barges slide away screen-right, rowed by small brown-clad oarsmen; THE GOVERNOR stands alone at the rail of the last barge, his back to the camera the whole time. There is exactly ONE GOVERNOR.
WHAT HAPPENS: [0s] Black-green clouds roll in; the first yellow lightning. [4s] The TWO ROPE-CUTTERS slash the ropes of the long footbridge with long knives. [8s] The middle of the bridge sags and drops into the water; THE GOVERNOR looks back over his shoulder once and turns away.
SOUND: Thunder, ropes snapping, timber splashing, a crowd crying out off-screen.
Grade: (unchanged storm grade)
CRITICAL NEGATIVES: no duplicate characters, no twins, no character appearing twice; nobody beside THE GOVERNOR; no sun, no sunset, no golden hour, no clear sky; THE GOVERNOR never looks at the camera; no people on the falling section of the bridge; no text, no subtitles, no watermark; no sheet panels, no white backdrop, no split screen; nothing modern.
```

**D03 (rs2 draft)**: the changed lines only; the rest is as in rs1.
```
REFERENCES: … @ภาพ3 — THE GOVERNOR, one man: face, body, clothes, gold; take the look, never the count; ignore the sheet layout and background.
WHO: THE GOVERNOR, heavyset Thai man in his fifties, white silk jacket, gold buttons, gold chain; the only person in white or gold. HIS OARSMEN: plain brown cotton, bare heads, no jewellery. PHAYA NAK, …
THE FRAME: Wide over open water: THE GOVERNOR's golden barge at screen-right; THE GOVERNOR alone at the stern rail, screen-right edge; his brown-clad OARSMEN at the bow, nearest the tail, with chests of gold; the huge jade tail of PHAYA NAK rising from the water at screen-left. There is exactly ONE GOVERNOR.
… [8s] The barge rolls over; THE GOVERNOR clings to the stern rail, gold chests sliding into the sea.
CRITICAL NEGATIVES: no duplicate characters, no twins, no character appearing twice; the Naga's head never in frame; no text, no subtitles, no watermark; no sheet panels, no white backdrop, no split screen; nothing modern.
```
Change line 2 of each prompt (the heading) if it is re-fired again, so the harvester keys a new card
(ShortMovieQC SKILL.md:113).

---

## What this research did not find
- No Seedance A/B of a single-panel crop against a multi-panel character sheet, for duplicates or anything else.
- No outcome recorded for S4's re-take (two Dupes with two carts). Only the rule it triggered is recorded.
- Nothing in `Agents/Rules` (IRON-RULES, ADRs) on duplicates; the rule lives in the Seedance skill and in prompt-lint.
