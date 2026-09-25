---
name: CTO_Flow_Omni1.1_Continuity
description: >-
  Continuity sheet + pre-shoot gate for an AI film shot in Google Flow (Omni 1.1
  Flash, องค์ประกอบ mode): one table of time, place, who, wardrobe and props per
  shot, and flags for what cost re-shoots on «จุดจบของเจ้าหนี้นอกระบบ» (night on a
  day plate, a healthy character on a sickbed, what Flow silently deletes, fast
  lines, REF_1 close-ups). Trigger on /CTO_Flow_Omni1.1_Continuity and proactively
  before any paid Flow shoot of a multi-scene film — 'check continuity',
  'เช็คความต่อเนื่อง', 'ก่อนยิงเช็คอะไร', 'ฉากกลางคืนออกมาเป็นกลางวัน', 'ชุดเปลี่ยน',
  'ตัวละครนอนบนเตียง', or when a shot sheet (docs/scripts/*.data.py) is written or
  changed. Do NOT fire for Higgsfield/Seedance, Kling, Grok or fal.ai work — its
  Flow flags are untested there (higgsfield-unlimited-gen owns Seedance).
created_by: agent
author: {role: cto, date: "2026-09-23"}
audience: [cto, script_writer, browser_operator]
---

# Continuity — Google Flow · Omni 1.1 Flash

## Model scope — read this first (CEO 2026-09-23)

> "ต้อง Scope ให้ดีเพราะ ที่เราทำคือ Model อะไร … Seedance 2.5 อาจไม่ต้องใช้ Skill
> เหล่านี้เลย เพราะมันคนละส่วนกัน"

**Proven on:** Google Flow (`flow.google.com`) · model **Omni 1.1 Flash** (Veo 3.1
family) · mode **องค์ประกอบ** (Ingredients — up to 10 image references, each named in
the prompt as `<IMAGE_REF_n>` in attach order) · 720p · 9:16 · stills for plates by
**Nano Banana 2** (free in Flow). One film: «จุดจบของเจ้าหนี้นอกระบบ», 186 shots,
2026-09-18..23, shot by `tools/flow_shoot.py` from sheets built by
`tools/build_shotsheet.py`.

Every rule below is tagged:

| tag | meaning | on another model |
|---|---|---|
| **[ANY]** | about the story or the table, not the generator | applies as written |
| **[FLOW]** | measured on Omni 1.1 Flash in องค์ประกอบ mode | a hypothesis — test it (one 360p/4 s arm) before relying on it |

**Not this skill:** Higgsfield Seedance 2.5 / 2.0 (`higgsfield-unlimited-gen`) binds
references differently (`@Element` plates, no per-chip `<IMAGE_REF_n>` order), has
its own content filter and its own night behaviour; Kling, Grok, fal.ai likewise. On
those, keep the [ANY] parts — the table itself — and drop the [FLOW] flags until
measured there.

## What it does

`tools/continuity_sheet.py` reads the film's `docs/scripts/*.data.py` (the same files
the shot-sheet builder renders), prints one row per shot — act · shot · seconds ·
time of day · location plate · who (+ wardrobe plate) · NOT keys · action — with a
**TRANSITION** line wherever place or time changes, and flags risks. It never edits
anything and never spends anything. A flag is a question for the person writing the
sheet, not a verdict.

## When to invoke

- A new film's shot sheet is written, or any `*.data.py` changes before a paid shoot.
- A scene comes back with the wrong time of day, wrong clothes, a person where they
  should not be, or a clip that vanished.
- Before inserting new scenes into a finished film (the police line, the arrest, the
  happy ending were all inserts on this one).

## When NOT to invoke

- Reviewing clips already shot — that is `CTO_Flow_Omni1.1_FilmQC`.
- Writing the story itself — `thai-moral-drama` (its Structure gate) and
  `tig-scene-engine` own that; run this after they are done.
- Any non-Flow generator (see scope).

## Workflow

1. Run it over every act, in order:
   `python3 tools/continuity_sheet.py docs/scripts/<film>-ACT*.data.py --out <Work>/tmp/continuity.md`
   If a data file will not load, stop and fix the file — do not hand-read around it.
2. Read the **TRANSITION** lines first. Each is a place or time change; the first shot
   after one should establish where and when (a wide shot, or a time card for a jump
   such as "หนึ่งปีต่อมา"). [ANY]
3. Read the flags, strongest first (calibration below), and change the sheet — not the
   prompt by hand — then rebuild with `build_shotsheet.py`.
4. Re-run until the only flags left are ones you are knowingly accepting; say which and
   why in the shoot report.
5. Paid shooting starts only after this. **If a FLOW-DELETES flag is still open, do not
   fire that shot** — see Rules.

## The flags, and how much to trust each (calibrated on the banchi film)

| flag | what it catches | measured on banchi | trust |
|---|---|---|---|
| **FLOW-DELETES** [FLOW] | handcuffs; uniform + police lights; the word "police" with a uniform | 6 flags = 183-186, and Flow deleted every take of those four; 0 false | high |
| **NIGHT-ON-DAY-PLATE** [FLOW] | night/dusk/dawn/evening over a location whose plate is a daylight plate | 75 flags; every shop-at-night shot came back as daylight | high |
| **REF1-CLOSEUP** [FLOW] | a close-up two-shot — the second-listed character is REF_1 | 3 flags incl. 106, whose REF_1 lost his hair twice | medium |
| **SICKBED** [ANY staging, FLOW effect] | a healthy character staged on the patient's bed | 5 flags, 1 real (169); missed 65 and 171 (their text never said "on the bed") | low — read the room scenes yourself too |
| **FAST-LINE** [FLOW] | > 10 Thai characters/second | 43 at 10.5/s captioned 3×, clean at 8 s; 16 and 24 flagged and were clean | low — a nudge, not a stop |
| **INAUDIBLE-SPEECH** [FLOW] | "to himself", "under his breath", "whispered" | 17 flags; 2 of the 3 captioned shots had this wording | low |

## Rules

1. **HARD — Do not pay for a shot the sheet already shows Flow deletes.** Rewrite it
   first: describe clothes, not the institution ("an everyday khaki duty uniform, a
   metal badge", never "police uniform"); no handcuffs on anyone; police lights only
   in a shot with no uniformed character in it (a bystander watching the car leave).

   **Why hard:** money — Flow generated and then silently deleted 184, 185, 186 and
   eight test arms; each submit is spent or at best a wasted slot, and the runner
   cannot tell a deleted clip from a slow one for minutes.

2. Night needs a night plate. [FLOW] The word "night" did not beat a daylight
   location plate in 71 shots; the alley shots, whose plate is itself a night image,
   came out genuinely dark. Make every location in a DAY and a NIGHT version (free
   stills), and describe night by its light — bulbs on, the street black beyond the
   shutter — not by one word. A/B the first night scene at 360p/4 s (≈8 credits).

3. The character a shot is about goes first. [FLOW] In a close-up, the REF_1 face seen
   in profile drifted (hair in 106 twice; the father's shirt in 149/150/188/189); with
   the same framing and the subject as REF_0 facing 3/4 to camera, it held (107, 106
   take 3).

4. Faces and clothes come from separate plates. [FLOW] One full-body "him in the
   uniform" still gave วิทย์ the father's older face next to the father's close-up plate
   (149, 151); his face plate + a wardrobe plate with no person in it held (A/B arm B).
   Use `WARDROBE` in the data files. Ordinary clothes by words alone worked (ต้น's
   office shirt, 188-190).

5. Nobody healthy on a sickbed. [ANY] A patient's props (the nasal cannula) move to
   whoever is on her bed — ต้น wore it three times. Stage a chair beside the bed. A
   "no cannula" negative lost to the staging every time.

6. A continuity rule is not an exclusion. [ANY] `NOT["ya"]` (how she looks) used to
   mean "keep her out" put her in frame; exclusion is its own key (`noya`).

7. Say where a prop IS, not what it is not. [FLOW] "No banknote with a portrait" lost
   to the Thai-shop context six times; binding a plain envelope prop plate fixed it.

8. Every character, prop and location carries named STATES. [ANY] (CEO ruling 2026-09-25)
   *"หนึ่ง Charactor อาจจะมี 1 หรือหลาย State … ถ้าเรามีครบ เราจะ Keep Charactor ได้ดีมากๆ → ใช้กับ Prop
   และ Location ด้วย เพื่อ Continue Scene ให้ไปข้างหน้าแบบควบคุมได้ ตั้งแต่ต้นน้ำจนปลายน้ำ"*

   **What a state is.** One look at one point in the story: face, hair, beard, clothes, physical condition,
   age. Examples:
   - a role change: the vendor before arrest → after arrest, stressed, different clothes
   - an injury ladder: bruise 1 → 2 → 3 → bandaged → bandage off with a faint mark → healed (back to base)
   - hair: short / medium / long
   - beard: short / long
   - age: child / early 20s / working age. A new age needs a new FACE plate.

   **How it is used.**
   - Each state gets its own plate, `<who>__<state>`, next to one identity plate, `<who>__face`.
   - Every shot names its state.
   - The data file maps shot → state, so no prompt ever leaves the model to guess a look.
   - Facial emotion is NOT a state. It changes every shot, and a plate would freeze it. Physical conditions
     that last across shots ARE states: red swollen eyes after a night of crying, a soaked crumpled shirt.

   **How to make one.**
   - Generate in ChatGPT Plus through `tools/chatgpt_images.py`, face first. Make every state as a
     same-chat `--continue` edit of that face (a new chat makes a new person).
   - Upload to Flow as an Element. The upload route is being probed (task-c2723478).
   - Rule 4 still applies: if a full-body state plate loses the face in a two-shot, fall back to face +
     wardrobe plate.
   - First registry: `docs/scripts/taachang-CAST-STATES.md`.

## Output format

```
231 rows, 111 flags: {'NIGHT-ON-DAY-PLATE': 75, 'FLOW-DELETES': 6, 'SICKBED': 5, ...}
| 6 | 184 · 10s · night · @back_alley | wit_uniform(@cop_wit +@police_uniform), cherd(@lender_cherd) | cuffed,noledger,nosubs | walk side by side ... |
| | **TRANSITION** @back_alley · night → @noodle_shop_thriving · midday | | | |
- shot 184 · **FLOW-DELETES** — handcuffs — Flow deleted every take with them
```

## Reference

- Tool: `tools/continuity_sheet.py` · builder: `tools/build_shotsheet.py` (`WARDROBE`, `PROPS_BY_SHOT`)
- Evidence: `docs/scripts/banchi-RETRO.md`; google-flow-ops sections "A clip that vanishes after
  Submit" and "What Flow silently deletes in an arrest scene"
- Story side: `thai-moral-drama` (Structure gate) · clip review: `CTO_Flow_Omni1.1_FilmQC`

## Field notes
- 2026-09-25 [MISSING] rule 1 (what Flow deletes) — **a young child + banknotes in frame vanishes.** On taachang ACT1, S7 and S19 (grandmother + the 11-year-old + pastel prop notes) both came back with no card after a 9-min timeout, and 12 credits each were spent. S6 (the same two, a pebble jar, no money) rendered. Banknotes with the 16-year-old (S2, S14, S23) rendered. The probe S20 (same pair, money kept inside a closed cloth pouch, `nomoney` block, no touching) rendered first time. Rewrite: the child and the money are never in one frame, and money talk is fine in the dialogue. n=2 vanished + 1 probe held; S5 (father + 16-year-old, no notes shown) also vanished once and is unexplained · evidence: state/taachang/ACT1.tsv, docs/scripts/taachang-ACT1.data.py · status: pending
- 2026-09-25 [MISSING] rule 1, follow-up to the child + banknotes note — **the WORDS count, not only the pixels.** S7 and S19 vanished a second time after the notes were moved into a closed pouch, because their framing line still said "over the notes" / "notes in her hands". S20 rendered with the same pair and the same `nomoney` negation ("No banknotes, coins or money…"). So a negation passes; a positive money phrase anywhere in a prompt with the child vanishes. S19 finally rendered as the grandmother alone, with the boy off screen and his 3-word reply cut. Check: grep every prompt containing the child for notes/money/cash/baht/coins outside the negation block before firing · evidence: taachang ACT1 ledger, commits 'S7 framing', 'S19 solo' · status: pending
