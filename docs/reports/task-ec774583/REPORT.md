# REPORT task-ec774583

FIX

1. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md` (H4 — Check 1: Thai typo `กล่ำ` and non-homophone pun)
   - **Why:** Cabbage in Thai is `กะหล่ำ` / `กะหล่ำปลี` (`kà-làm`), not `กล่ำ` (`klàm`, which means dark red as in แดงกล่ำ), and neither is a homophone (`คำพ้องเสียง`) of `กรรม` (`kam`). Also `"กล่ำสดๆ ใครทำไว้ได้คืนทุกคน!"` is unnatural for selling vegetables. In a Thai market, `กำ` (a bunch/bundle of greens) is an exact homophone of `กรรม` (`kam`), and `"กำใครกำมัน"` works in both senses.
   - **Current text:**
     ```markdown
     **H4. กล่ำ or กรรม** (#5 sound play + karma theme)
     - Frame 1: แม่ค้า holds up a cabbage, already mid-shout; the bully of the episode walks past behind her.
     - Line: แม่ค้า: "กล่ำมาแล้วจ้า! กล่ำสดๆ ใครทำไว้ได้คืนทุกคน!" | bully stops, uneasy: "ป้า... หมายถึงผักใช่ไหม"
     - Timing: 0.0-2.4 shout | 2.5 bully freezes (0.7 s hold) | 3.2-4.4 his line | 4.5 ป้า just smiles and holds the cabbage higher.
     - Voice: ป้า loud, cheerful, market sing-song; bully quiet, a little scared.
     - Muted: subtitle shows กล่ำ, then a small second line "(กรรม?)" on the bully's face.
     ```
   - **Exact replacement:**
     ```markdown
     **H4. กำ or กรรม** (#5 sound play + karma theme)
     - Frame 1: แม่ค้า holds up bunches of greens, already mid-shout; the bully of the episode walks past behind her.
     - Line: แม่ค้า: "ผักเป็นกำจ้า! กำใครกำมัน รับไปเลยคนละกำ!" | bully stops, uneasy: "ป้า... หมายถึงผักใช่ไหม"
     - Timing: 0.0-2.4 shout | 2.5 bully freezes (0.7 s hold) | 3.2-4.4 his line | 4.5 ป้า just smiles and holds the bunch higher.
     - Voice: ป้า loud, cheerful, market sing-song; bully quiet, a little scared.
     - Muted: subtitle shows กำ, then a small second line "(กรรม?)" on the bully's face.
     ```

2. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md` (H6 & H9 — Check 1: unnatural Thai classifier and verb choice)
   - **Why:** In H6, `"ข้าวหอมมีทุกอย่างที่ต้องใช้" ... "...หนึ่งลูก"` uses the classifier `ลูก` without naming `มะพร้าว`, which does not agree grammatically with `ทุกอย่าง`. In H9, `"ทำไมต้องพาเบ็ดตกปลามาทะเลทราย"` uses `พา` with an inanimate object (`เบ็ดตกปลา`); in natural Thai, `พา` is for people/animals while objects take `พก` or `เอา`.
   - **Current text (H6):**
     ```markdown
     - Line: narrator (newsreader calm): "วันที่หนึ่งบนเกาะร้าง ข้าวหอมมีทุกอย่างที่ต้องใช้" | camera pans: one coconut | "...หนึ่งลูก"
     - Timing: 0.0-2.4 line | 2.4-3.2 pan | 3.3-3.9 "หนึ่งลูก" | 4.0 the coconut rolls into the sea.
     ```
   - **Exact replacement (H6):**
     ```markdown
     - Line: narrator (newsreader calm): "วันที่หนึ่งบนเกาะร้าง ข้าวหอมมีทุกอย่างที่ต้องใช้" | camera pans: one coconut | "...มะพร้าวหนึ่งลูก"
     - Timing: 0.0-2.4 line | 2.4-3.2 pan | 3.3-3.9 "มะพร้าวหนึ่งลูก" | 4.0 the coconut rolls into the sea.
     ```
   - **Current text (H9):**
     ```markdown
     - Line: big text on frame 1: "ทำไมต้องพาเบ็ดตกปลามาทะเลทราย" | ข้าวหอม, to camera, confident: "เดี๋ยวก็รู้"
     ```
   - **Exact replacement (H9):**
     ```markdown
     - Line: big text on frame 1: "ทำไมต้องพกเบ็ดตกปลามาทะเลทราย" | ข้าวหอม, to camera, confident: "เดี๋ยวก็รู้"
     ```

3. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md` and `.claude/skills/CMO_Knowledge_ThaiHumor/references/thumbstop.md` (Check 1: Thai spelling typo `มุขแป้ก`)
   - **Why:** Standard Thai spelling (used throughout `SKILL.md` and `humour-map.md`) is `มุกแป้ก` (with `ก`), whereas `hooks-20.md` (H17) and `thumbstop.md` spell it `มุขแป้ก` (with `ข`).
   - **Current text in `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md`:**
     ```markdown
     **H17. Three seconds that change your life** (#3 มุขแป้ก on purpose + #1 cue)
     ```
   - **Exact replacement in `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md`:**
     ```markdown
     **H17. Three seconds that change your life** (#3 มุกแป้ก on purpose + #1 cue)
     ```
   - **Current text in `.claude/skills/CMO_Knowledge_ThaiHumor/references/thumbstop.md`:**
     ```markdown
     พากย์นรก with burned subtitles, slapstick and the lakorn zoom pass both; มุขแป้ก silence and คำผวน need the subtitle.
     ```
   - **Exact replacement in `.claude/skills/CMO_Knowledge_ThaiHumor/references/thumbstop.md`:**
     ```markdown
     พากย์นรก with burned subtitles, slapstick and the lakorn zoom pass both; มุกแป้ก silence and คำผวน need the subtitle.
     ```

4. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/SKILL.md` (Check 3: banned blush / red-face / red-ear tokens appear in `SKILL.md`)
   - **Why:** Check 3 prohibits those three tokens anywhere in the skill (note how `humour-map.md` line 57 avoided them with `เขิน without the colour words`), but `SKILL.md` line 86 includes the literal banned words.
   - **Current text:**
     ```markdown
     - No crude words (no มึง/กู, no swearing), even though many popular clips use them. Never write blush/หน้าแดง/หูแดง.
     ```
   - **Exact replacement:**
     ```markdown
     - No crude words (no swearing or crude pronouns), even though many popular clips use them. Never write face-colour or ear-colour embarrassment cues (see `CMO_Standard_HumanVoice_TH`).
     ```

5. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md` (H20 — Check 4 & Check 6: arrow `->` in public Thai subtitle text)
   - **Why:** `SKILL.md` line 90 states `No guillemets, em dashes, middle dots or arrows in Thai public text (scripts/check-post-text.sh)`, and H20 places an arrow `->` inside the on-screen Thai subtitle (`subtitle: นอนหลับ -> นับหลอน`).
   - **Current text:**
     ```markdown
     - Line: "นอนไม่หลับ ทำยังไงดี" | friend (deadpan, off-screen): "ลองผวนดูสิ" | subtitle: นอนหลับ -> นับหลอน | they slowly look at the dark corner.
     ```
   - **Exact replacement:**
     ```markdown
     - Line: "นอนไม่หลับ ทำยังไงดี" | friend (deadpan, off-screen): "ลองผวนดูสิ" | subtitle (two lines): "นอนหลับ / นับหลอน" | they slowly look at the dark corner.
     ```

6. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/references/jokes-round2.md` (J4 & J5 — Check 5: J4 reuses the source bit's line; J5 does not name a specific source bit/URL)
   - **Why:** In `real-jokes.md` row 4, the source clip (น้าค่อม "อบรมผี" `youtu.be/yDq_-Zsxrfk`) has the line `"ใครชวนมา เพื่อนชวนเหรอ"`. J4 in `jokes-round2.md` reuses that line (`ป้า: "ใครชวนมา เพื่อนชวนมาใช่ไหม ทีหลังอย่าตามเพื่อน"`), violating Check 5 and `SKILL.md` Writing rule 6 (`Keep the frame of the real bit, never its lines`). J4 also lacks a spoken `ตบ` line (`SKILL.md` Writing rule 4). In J5, the header says `โครงจาก: observational แบบ เดี่ยว โน้ส อุดม` without naming the specific decoded bit and URL from `real-jokes.md`.
   - **Current text (J4):**
     ```markdown
     ป้า: "ใครชวนมา เพื่อนชวนมาใช่ไหม ทีหลังอย่าตามเพื่อน"
     [ภาพ ปิด] ผีก้มหน้า แล้วช่วยป้ายกลังผักขึ้นแผง
     ```
   - **Exact replacement (J4):**
     ```markdown
     ป้า: "ผมเผ้าก็ไม่หวี มายืนเกะกะหน้าร้าน มาช่วยป้าเด็ดพริกเลย"
     ผี (ตบ เสียงอ่อย): "ป้า... หนูมาหลอก ไม่ได้มาสมัครงาน"
     [ภาพ ปิด] ผีก้มหน้า นั่งเด็ดพริกข้างแผง
     ```
   - **Current text (J5):**
     ```markdown
     ## J5 ความจริงที่ทุกคนรู้ (B-roll opener) โครงจาก: observational แบบ เดี่ยว โน้ส อุดม
     ```
   - **Exact replacement (J5):**
     ```markdown
     ## J5 ความจริงที่ทุกคนรู้ (B-roll opener) โครงจาก: เดี่ยว 12 โน้ส อุดม "ผู้หญิงไม่มีอะไรจะใส่" youtu.be/U2d2tneIVgU (observational เรื่องจริงในชีวิตประจำวัน)
     ```

7. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md` (H2 — Check 6: internal contradiction with `SKILL.md` and `real-jokes.md`)
   - **Why:** `SKILL.md` (lines 55, 65) and `real-jokes.md` (line 21) explicitly cite `"the vegetable phoned"` (`ผักโทรมา`) as the failed round-1 concept gag rejected by the CEO (`"ไม่ขำเลยแม้แต่น้อย"`, `"never a surreal idea"`), yet `hooks-20.md` retains **H2. The vegetable that phoned** as a hook to reuse (`SKILL.md` line 77: `Those 20 are ours to reuse`).
   - **Current text:**
     ```markdown
     **H2. The vegetable that phoned** (#7 deadpan + #6 literal answer)
     - Frame 1: close-up, a customer squeezes a bunch of greens, doubtful.
     - Line: ลูกค้า: "ป้า ผักนี่สดไหมครับ" | ป้า (not looking up, counting change): "สดค่ะ เมื่อเช้ามันยังโทรหาป้าอยู่เลย"
     - Timing: 0.0-1.2 question | answer starts at 1.4 with no pause | 3.0 the customer slowly puts the greens down.
     - Voice: ป้า calm, low, polite ค่ะ; no smile. The customer's silence is the laugh.
     - Muted: works on the customer's face.
     ```
   - **Exact replacement:**
     ```markdown
     **H2. Reverse haggling** (#6 literal answer + #7 deadpan, frame from น้าค่อม "ขายไม้จิ้มฟัน" youtu.be/HpJsjUKeeZU)
     - Frame 1: close-up on ป้า's sympathetic face holding two lemons, subtitle on screen: "เมื่อขอแม่ค้าลดราคามะนาวสามลูกสิบสอง"
     - Line: ลูกค้า: "มะนาวสามลูกสิบสองได้ไหมป้า" | ป้า (sympathetic, deadpan): "อย่าต่อเลยลูก เอาไปสองลูกสิบสองพอ" | ลูกค้า (ตบ): "ป้า! นั่นป้าขึ้นราคา!"
     - Timing: 0.0-1.2 question + cash-register ding | 1.3-2.8 ป้า's answer | 2.9-4.2 cut to customer's reaction + ตบ line.
     - Voice: ป้า warm and motherly as if doing a favour; customer stunned.
     - Muted: Frame 1 face + subtitle, then cut to customer counting on fingers at 2.9 s.
     ```

8. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/SKILL.md` (Check 6: step ordering in `## How to write a hook with this skill`)
   - **Why:** Step 5 starts with `"5. Before writing, open knowledge/brand-knowledge/brands/<channel>/formulas/INDEX.md..."`, placing a prerequisite `"Before writing"` step after Steps 1-4 have already written and checked the hook.
   - **Current text:**
     ```markdown
     ## How to write a hook with this skill
     1. Pick the channel's job (ILAG moral drama, KhaoHom survival, Jade Tally drama dub, B-roll opener) and 1-2 mechanisms
        from the table that fit a hook.
     2. Write frame 1 first (checklist 1-4), then the line, then the timing in seconds, then the voice direction.
     3. Run the benign check (below), then `scripts/check-post-text.sh` on anything public.
     4. Copy the format of `references/hooks-20.md`. Those 20 are ours to reuse; test 2-3 per channel before scaling.
     5. Before writing, open `knowledge/brand-knowledge/brands/<channel>/formulas/INDEX.md`: a proven hook formula that
        fits is followed as written (`CMO_Workflow_PromptFormula`).
     ```
   - **Exact replacement:**
     ```markdown
     ## How to write a hook with this skill
     1. Before writing, open `knowledge/brand-knowledge/brands/<channel>/formulas/INDEX.md`: a proven hook formula that
        fits is followed as written (`CMO_Workflow_PromptFormula`).
     2. Pick the channel's job (ILAG moral drama, KhaoHom survival, Jade Tally drama dub, B-roll opener) and 1-2 mechanisms
        from the table that fit a hook.
     3. Write frame 1 first (checklist 1-4), then the line, then the timing in seconds, then the voice direction.
     4. Copy the format of `references/hooks-20.md`. Those 20 are ours to reuse; test 2-3 per channel before scaling.
     5. Run the benign check (below), then `scripts/check-post-text.sh` on anything public.
     ```

9. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/references/thumbstop.md` and `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md` (Check 6: 10-point checklist item #10 mismatch between `SKILL.md` and `thumbstop.md`, and hooks violating Frame 1 face/motion/cut rules)
   - **Why:** Item 10 in `SKILL.md` is `"Write it to work twice: with sound (voice + cue) and muted (face + subtitle)"`, while Item 10 in `thumbstop.md` is `"Benign check..."`. In `hooks-20.md`, H3 opens on a still freeze frame of a hand and a back with no cut until `4.8 s` (violating Checklist #1, #3, #8), and H10, H12, H14, H16 do not open on a close face on Frame 1 (H16 opens on landscape B-roll `sea, rice field`, which `thumbstop.md` Claim 3 explicitly forbids).
   - **Current text in `.claude/skills/CMO_Knowledge_ThaiHumor/references/thumbstop.md`:**
     ```markdown
     10. **Benign check:** the broken rule is harmless and nobody is mocked for who they are. If it would hurt someone in
         real life, cut it. (11 + brief rules)
     ```
   - **Exact replacement in `.claude/skills/CMO_Knowledge_ThaiHumor/references/thumbstop.md`:**
     ```markdown
     10. **Write it to work twice (sound-on + muted) and pass the benign check:** voice + cue carry it with sound, face + subtitle carry it muted, and nobody is mocked for who they are. (8, 10, 11)
     ```
   - **Current text in `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md` (H3, H10, H12, H14, H16):**
     ```markdown
     **H3. Freeze before the slap** (#8 reversal + #7 deadpan narrator)
     - Frame 1: freeze frame, a hand mid-air, the other person's back to camera. No contact is ever shown.
     - Line: narrator (low, even): "ฝ่ามือนี้ จะเป็นฝ่ามือที่แพงที่สุดในตลาด" | 0.6 s pause | "เพราะคนที่กำลังจะโดน... คือเจ้าของตลาด"
     - Timing: 0.0-2.2 line 1 | 2.2-2.8 pause | 2.8-4.6 line 2 | 4.8 the back turns: the market owner.
     ```
     ```markdown
     **H10. Water count** (#1 sound cue + #7 deadpan)
     - Frame 1: three water bottles in a row, ข้าวหอม's hand already reaching.
     ```
     ```markdown
     **H12. Priceless or worthless** (#5 double meaning, ties to EP02 ไข่ที่ไม่มีราคา)
     - Frame 1: a plain egg in the merchant's palm, close.
     ```
     ```markdown
     **H14. Everything has a price** (#8 reversal + hierarchy play)
     - Frame 1: abacus beads snapping in slow motion, sting.
     ```
     ```markdown
     **H16. Calm before the news** (#7 deadpan + #10 subtitle)
     - Frame 1: beautiful slow B-roll (sea, rice field), a big subtitle already on.
     ```
   - **Exact replacement in `.claude/skills/CMO_Knowledge_ThaiHumor/references/hooks-20.md` (H3, H10, H12, H14, H16):**
     ```markdown
     **H3. Freeze before the slap** (#8 reversal + #7 deadpan narrator)
     - Frame 1: close-up of the villain's angry face raising a hand mid-swing (slow-motion movement + whoosh sting at 0.2 s), subtitle: "ฝ่ามือที่แพงที่สุดในตลาดนัดแห่งนี้". No contact is ever shown.
     - Line: narrator (low, even): "ฝ่ามือนี้ จะเป็นฝ่ามือที่แพงที่สุดในตลาด" | cut at 2.2 s to the calm face of the target turning around | "เพราะคนที่กำลังจะโดน... คือเจ้าของตลาด"
     - Timing: 0.0-2.1 line 1 (slow-mo swing) | 2.2 cut to the market owner's face | 2.4-4.2 line 2 + villain freezes.
     ```
     ```markdown
     **H10. Water count** (#1 sound cue + #7 deadpan)
     - Frame 1: close-up on ข้าวหอม's parched face already gulping from bottle #1, two more bottles beside him, subtitle: "น้ำสามขวดสุดท้ายบนเกาะร้าง".
     ```
     ```markdown
     **H12. Priceless or worthless** (#5 double meaning, ties to EP02 ไข่ที่ไม่มีราคา)
     - Frame 1: close-up on the greedy merchant's face holding a plain egg up to the hero, subtitle: "ไข่ธรรมดาฟองนี้ราคาเท่าไหร่กันแน่".
     ```
     ```markdown
     **H14. Everything has a price** (#8 reversal + hierarchy play)
     - Frame 1: close-up on the hero's solemn face flicking abacus beads in slow motion (sting at 0.2 s), subtitle: "ในแผ่นดินนี้ทุกสิ่งล้วนมีราคา".
     ```
     ```markdown
     **H16. Calm before the news** (#7 deadpan + #10 subtitle)
     - Frame 1: close-up on the presenter's overly serene face holding a cup of tea in front of a sea/rice-field backdrop (gentle chime at 0.2 s), big subtitle: "ภาพสวยๆ นี้มีไว้ให้คุณใจเย็นลง".
     ```

10. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/references/humour-map.md`, `.claude/skills/CMO_Knowledge_ThaiHumor/references/thumbstop.md`, and `.claude/skills/CMO_Knowledge_ThaiHumor/references/real-jokes.md` (Check 6: unreferenced clip IDs `I8IJWWdmLaA` and `3qIbuTdCS5U`, and `real-jokes.md` straight-man example mismatch)
    - **Why:** `thumbstop.md` Claim 15 and `humour-map.md` line 162 cite `I8IJWWdmLaA (6.88M, 0 s)` and `3qIbuTdCS5U (107k, 4 s)` as measured in `humour-map.md`, but neither clip appears in the 12 mechanisms of `humour-map.md` (whereas `O0jnKIMJwDo` 6.06M peak 0 s and `clt8XWuR2FI` 6.69M peak 0 s are in Mechanism #7). Also, `real-jokes.md` line 22 uses `("คุณโง่หรือคุณบ้า")` as the `คนตบ` example while `SKILL.md` line 68 uses `("ป้า! ตกลงป้าลดหรือป้าขึ้นเนี่ย")`.
    - **Current text in `.claude/skills/CMO_Knowledge_ThaiHumor/references/humour-map.md`:**
      ```markdown
      Measured pattern: five short clips with a heatmap peak at second 0-4: two Shorts (HrCrSwBWY_Y 16 s, Dp6iiZhEATE 39 s) and three 3-5 min clips (GOuiAD2dw48, I8IJWWdmLaA, 3qIbuTdCS5U).
      ```
    - **Exact replacement in `.claude/skills/CMO_Knowledge_ThaiHumor/references/humour-map.md`:**
      ```markdown
      Measured pattern: five clips in the map with a heatmap peak at second 0: two Shorts (HrCrSwBWY_Y 16 s, Dp6iiZhEATE 39 s) and three comedy clips (GOuiAD2dw48 584k, O0jnKIMJwDo 6.06M, clt8XWuR2FI 6.69M).
      ```
    - **Current text in `.claude/skills/CMO_Knowledge_ThaiHumor/references/thumbstop.md`:**
      ```markdown
      | 15 | In our Thai sample, viewers rewind second 0-4 of short clips: HrCrSwBWY_Y (8.68M, peak 0 s), Dp6iiZhEATE (602k, peak 0 s), GOuiAD2dw48 (584k, 0 s), I8IJWWdmLaA (6.88M, 0 s), 3qIbuTdCS5U (107k, 4 s). | YouTube "most replayed" heatmap, read 29 Oct 2026 (humour-map.md) | MEASURED (n=5, YouTube only) | The first line is the most-watched moment. Put the joke there, not a greeting. |
      ```
    - **Exact replacement in `.claude/skills/CMO_Knowledge_ThaiHumor/references/thumbstop.md`:**
      ```markdown
      | 15 | In our Thai sample, viewers rewind second 0 of comedy clips: HrCrSwBWY_Y (8.68M, peak 0 s), Dp6iiZhEATE (602k, peak 0 s), GOuiAD2dw48 (584k, peak 0 s), O0jnKIMJwDo (6.06M, peak 0 s), clt8XWuR2FI (6.69M, peak 0 s). | YouTube "most replayed" heatmap, read 29 Oct 2026 (humour-map.md) | MEASURED (n=5, YouTube only) | The first line is the most-watched moment. Put the joke there, not a greeting. |
      ```
    - **Current text in `.claude/skills/CMO_Knowledge_ThaiHumor/references/real-jokes.md`:**
      ```markdown
      - ไม่มีคนตบ: มุกไทยเกือบทุกมุกมีคนที่สองพูดสิ่งที่คนดูคิด ("คุณโง่หรือคุณบ้า") เสียงหัวเราะรอบสองมาจากตรงนั้น
      ```
    - **Exact replacement in `.claude/skills/CMO_Knowledge_ThaiHumor/references/real-jokes.md`:**
      ```markdown
      - ไม่มีคนตบ: มุกไทยเกือบทุกมุกมีคนที่สองพูดสิ่งที่คนดูคิด ("ป้า! ตกลงป้าลดหรือป้าขึ้นเนี่ย") เสียงหัวเราะรอบสองมาจากตรงนั้น
      ```

11. **File:** `.claude/skills/CMO_Knowledge_ThaiHumor/SKILL.md` (Check 4 & Check 7: frontmatter `description` em dash, US-spelling trigger `"Thai humor"`, and `verified`/`refresh_after` dates)
    - **Why:** `description` contains an em dash (`KNOWLEDGE — What`) and only triggers on UK spelling `"Thai humour"` (while the skill name is `CMO_Knowledge_ThaiHumor`), and `verified` is `"2026-10-29"` although `SKILL.md` incorporates 2026-10-30 additions (`references/jokes-round2.md`, `CEO 2026-10-30`).
    - **Current text:**
      ```yaml
      description: "KNOWLEDGE — What Thai viewers find funny and why (12 measured comedy mechanisms with clip evidence, timing, voice, sound cues), what stops the thumb in the first 3 seconds, and 20 worked hook examples for our channels. Trigger on /CMO_Knowledge_ThaiHumor and on \"มุกตลก\", \"ตลกแบบไทย\", \"เขียนมุก\", \"hook ตลก\", \"เปิดคลิปให้หยุดนิ้ว\", \"thumb-stop\", \"Thai humour\", \"comedy hook\", \"ทำให้คนดูขำ\". Do NOT use for drama story structure (CMO_Standard_Story_ThaiMoralDrama) or narrator voice rules (CMO_Standard_HumanVoice_TH)."
      owner: CMO
      created_by: agent
      author: {role: project_head, date: "2026-10-29"}
      audience: [cmo, script_writer, content_strategist, video_editor, project_head]
      improved_by: []
      aka: []
      verified: "2026-10-29"
      refresh_after: "2027-01-29"
      ```
    - **Exact replacement:**
      ```yaml
      description: "KNOWLEDGE: What Thai viewers find funny and why (12 measured comedy mechanisms with clip evidence, timing, voice, sound cues), the decode-a-real-bit formula, what stops the thumb in the first 3 seconds, and 20 worked hook examples for our channels. Trigger on /CMO_Knowledge_ThaiHumor and on \"มุกตลก\", \"ตลกแบบไทย\", \"เขียนมุก\", \"hook ตลก\", \"เปิดคลิปให้หยุดนิ้ว\", \"thumb-stop\", \"Thai humour\", \"Thai humor\", \"comedy hook\", \"ทำให้คนดูขำ\". Do NOT use for drama story structure (CMO_Standard_Story_ThaiMoralDrama) or narrator voice rules (CMO_Standard_HumanVoice_TH)."
      owner: CMO
      created_by: agent
      author: {role: project_head, date: "2026-10-30"}
      audience: [cmo, script_writer, content_strategist, video_editor, project_head]
      improved_by: []
      aka: []
      verified: "2026-10-30"
      refresh_after: "2027-01-30"
      ```

## Not checked / risk
- Live YouTube URLs, view counts, and heatmap peaks were checked for internal consistency across the 5 inlined files only (no network or shell commands run per brief).
- Cross-references to external repo files (`CMO_Workflow_LakornSerial`, `CMO_Workflow_PromptFormula`, `CMO_Standard_Story_ThaiMoralDrama`, `CMO_Standard_HumanVoice_TH`, `scripts/check-post-text.sh`, and channel `STATUS`/`formulas/INDEX.md` files) were not opened per the read-only inlined review constraint.
- In `hooks-20.md`, H17 uses mechanism #3 (`มุกแป้ก`) and H20 uses mechanism #4 (`คำผวน`) as hooks, whereas the mechanism tables in `SKILL.md` and `humour-map.md` classify #3 as weak for hooks and #4 as mid/ending only.
