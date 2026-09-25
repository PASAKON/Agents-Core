---
name: CTO_Flow_Omni1.1_Continuity
description: >-
  Continuity sheet + pre-shoot gate for an AI film shot in Google Flow (Omni 1.1
  Flash, องค์ประกอบ mode): one table of time, place, who, wardrobe and props per
  shot, and flags for what cost re-shoots on «จุดจบของเจ้าหนี้นอกระบบ» (night on a
  day plate, a healthy character on a sickbed, what Flow silently deletes, fast
  lines, REF_1 close-ups); the asset sheet every prompt quotes, and which props
  need an Element. Trigger on /CTO_Flow_Omni1.1_Continuity and proactively
  before any paid Flow shoot of a multi-scene film — 'check continuity',
  'เช็คความต่อเนื่อง', 'ก่อนยิงเช็คอะไร', 'ฉากกลางคืนออกมาเป็นกลางวัน', 'ชุดเปลี่ยน',
  'ตัวละครนอนบนเตียง', or when a shot sheet (docs/scripts/*.data.py) is written or
  changed. Do NOT fire for Higgsfield/Seedance, Kling, Grok or fal.ai work — its
  Flow flags are untested there (CTO_Seedance2.5_Higgsfield owns Seedance).
created_by: agent
author: {role: cto, date: "2026-09-23"}
audience: [cto, script_writer, browser_operator]
---

# Continuity — Google Flow · Omni 1.1 Flash

## Model scope

Read `CTO_Flow_Omni1.1_Ops` §Model scope first: what "proven on" means, the [ANY] / [FLOW] tags every
rule below carries, and what to keep on another generator.

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
- Writing the story itself — `CTO_Story_ThaiMoralDrama` (its Structure gate) and
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
   The evidence is §What Flow silently deletes, below.

   **Why hard:** money — Flow generated and then silently deleted 184, 185, 186 and
   eight test arms; each submit is spent or at best a wasted slot, and the runner
   cannot tell a deleted clip from a slow one for minutes.

2. Night needs a night plate. [FLOW] The word "night", appended to a 60-word description
   of a lit, open, busy shop, did not beat a daylight location plate in 71 shots: a cue
   that contradicts the paragraph around it loses to the paragraph. The alley shots,
   whose plate is itself a night image, came out genuinely dark. Make every location in
   a DAY and a NIGHT version (free stills), and describe night by its light — bulbs on,
   the street black beyond the shutter — not by one word. A/B the first night scene at
   360p at the production length (`CTO_Flow_Omni1.1_Ops` §Test fires: 6 credits an arm at
   8 s). [SUPERSEDED 2026-09-25, inventory item 28: "A/B the first night scene at
   360p/4 s (≈8 credits)" — whether a plate or a word holds is a behaviour test, and
   behaviour tests run at the production length (CEO 2026-09-18).]

3. The character a shot is about goes first. [FLOW] In a close-up, the REF_1 face seen
   in profile drifted (hair in 106 twice; the father's shirt in 149/150/188/189); with
   the same framing and the subject as REF_0 facing 3/4 to camera, it held (107, 106
   take 3).

4. Faces and clothes come from separate plates. [FLOW] One character appears in different
   places, at different times, in different roles; clothing changes with all three, and an
   unspecified outfit is an invented outfit. A regenerated character wearing the other
   clothes comes back with a different face, and one full-body "him in the uniform" still
   gave วิทย์ the father's older face next to the father's close-up plate (149, 151); his
   face plate + a wardrobe plate with no person in it held (A/B arm B). So each outfit is
   its own prop / image asset in Flow, generated once; the character asset stays untouched
   so the face stays fixed; the prompt names the character AND describes the outfit from
   the asset sheet, and where the outfit matters the wardrobe plate is attached as a
   reference. Use `WARDROBE` in the data files. Every shot carries an explicit costume:
   "he is wearing the same as before" is not a costume; the model has no "before".
   Ordinary clothes by words alone worked (ต้น's office shirt, 188-190).

5. Nobody healthy on a sickbed. [ANY] A patient's props (the nasal cannula) move to
   whoever is on her bed — ต้น wore it three times. Stage a chair beside the bed. A
   "no cannula" negative lost to the staging every time.

6. A continuity rule is not an exclusion, and a prohibition is not an inventory. [ANY]
   `NOT["ya"]` (how she looks) used to mean "keep her out" put her in frame; exclusion is
   its own key (`noya`). The reverse fails too: do not automate "this shot declares X,
   therefore attach X's Element". Tried and reverted the same day: `NOT["money"]` looks
   like a marker for shots containing banknotes and is carried by 22 of them, but it is a
   **prohibition** — its text ends *"also no notebook, no pen, no paper, no ledger of any
   kind"* — and most of those 22 have no money in frame at all. Shot 133 is two people
   looking at empty tables. Attaching the money Element to all 22 would have put banknotes
   into scenes written to be empty of them: worse than the bug it was meant to fix.
   **Which shots actually hold a prop is a reading of the action line, and belongs to a
   human.**

7. Say where a prop IS, not what it is not. [FLOW] "No banknote with a portrait" lost
   to the Thai-shop context six times; binding a plain envelope prop plate fixed it. The
   general rule is §Anything that must look a specific way needs an Element, below.

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
   - Upload to Flow as an Element: `CTO_Flow_Omni1.1_Ops` §Uploading an image from disk
     (`tools/flow_upload_element.py`, task-c2723478; this line said "being probed" until that landed).
   - Rule 4 still applies: if a full-body state plate loses the face in a two-shot, fall back to face +
     wardrobe plate.
   - First registry: `docs/scripts/taachang-CAST-STATES.md`.

## What Flow silently deletes [FLOW]

The evidence behind rule 1 and the FLOW-DELETES flag. The symptom is the same in every case: Submit is
accepted, a new batch appears at the top of the feed with the prompt on it, and then it is gone — no clip,
no error tile, no toast; a deleted arm is simply absent from the feed. How the runner misreads that, and
how to read the feed instead, is `CTO_Flow_Omni1.1_FilmQC` rule 2.

### A uniform plate + the word "police" (2026-09-23)

Measured on «บัญชี»: shot 179 twice, 149 and 151 once each.

**The A/B that found it** (CEO-ordered, 360p/4s, 3 arms, one variable each):

| arm | reference plate | the word "police" in the text | result |
|---|---|---|---|
| A — 179 as written | `@cop_wit_uniform_A` (uniform) | yes (character block, action, label) | **card vanished** |
| B | `@cop_wit` (plainclothes) | yes | clip made |
| C | `@cop_wit_uniform_A` (uniform) | **none** | clip made — Flow's own auto-title still read "Police officer enters noodle shop" |

The plate carries the look; the word is what trips the filter. The fix is rule 1.

**Honest scope.** One A/B, n=1 per arm, plus four field failures. It is not
deterministic: 150, 181 and 182 carried the same plate AND the word and came
back. Treat the rule as the cheap default, not a proven law; if a clip still
vanishes without the word, A/B the next variable (framing, the plate alone in
frame) before paying for 720p again.

**Test it cheap.** `flow_shoot.py run --resolution 360p --force-duration 4` on a
scratch sheet with one variable per shot number (4 credits an arm). The feed
listing, not the runner's exit code, is the verdict: read the newest batches
and count which arms left a card. Known gap: a 360p clip has no 1080p upscale
menu, so the runner's download step fails on it with "1080p submenu did not
appear" — that is the test harness, not the arm failing.

### In an arrest scene: handcuffs, and a uniform next to police lights (2026-09-23)

Measured on «บัญชี»'s arrest, 3 shots at 720p plus 8 arms at 360p/4s (4 credits each), one variable per
arm:

| arm | uniform (face plate + wardrobe plate) | handcuffs | police lights | result |
|---|---|---|---|---|
| 156 | yes | – | – | **kept** |
| 187 | – (father alone) | – | pickup + red-blue bar, in frame | **kept** |
| 9207 V1 | yes, walking him out, charges spoken | – | – | **kept** (real night, 40 s) |
| 184/185/186 | yes | yes | pickup in frame | deleted |
| 9202 | yes | – | pickup + light bar in frame | deleted |
| 9203, 9205, 9206 | yes | yes | – | deleted (dialogue varied: irrelevant) |
| 9204 | yes | yes | red-blue from off frame | deleted |
| 9209 V3 | yes | – | red-blue from off frame | deleted |
| 9208 V2 | – (plainclothes) | yes | – | deleted |

**The rule that fits every arm:** handcuffs are deleted on anyone; a uniformed
officer is deleted when police lights are in or thrown into the frame. Dialogue
(charges, prison, threats) changed nothing. So an arrest in Flow is: the uniform,
the charges in words, him walked out with hands free — and the patrol lights only
in a shot without the officer (a bystander watching the car leave).

## Anything that must look a specific way needs an Element, not a sentence [FLOW]

**Measured 2026-09-22, «จุดจบของเจ้าหนี้นอกระบบ», 6 clips lost.** Every money
shot in Act 3 rendered a **recognisable Thai 500-baht note carrying the royal
portrait** — in a drama about illegal moneylending. The prompt had asked for the
opposite, positively *and* negatively, in 40 careful words:

> The banknotes are obvious theatrical prop money of an invented place: soft
> pastel paper in even tones, one plain printed numeral in a corner, a simple
> abstract line pattern at the edges, and nothing else on them. No portrait or
> face of any kind, and no national emblem, crest, flag or country name — this is
> not the currency of any real country.

That wording is not the problem. What it was up against is: a Bangkok shophouse,
Thai dialogue, a Thai cast, Thai signage. The model's prior for "banknotes in a
Thai noodle shop" is Thai banknotes, and no amount of description outweighs it.

**The same film proves the fix.** Its three characters and six locations render
correctly across all 74 clips, because each is bound to an `@chip` and attached
as `<IMAGE_REF_N>`. The money was words only — shot 75 attached exactly two
chips, both of them people and places. Cast and sets got references; the prop got
a paragraph; only the prop went wrong.

**So, before any shoot:** list everything the prompt merely *describes*, and ask
which of those the scene's own context would pull toward a default — currency,
signage, uniforms, food, vehicles, documents, anything with a strong local prior.
Each one needs an Element.

**And the Elements are free** (a still costs nothing: `CTO_Flow_Omni1.1_Ops` §Money), so there is no
budget argument for describing a prop instead of binding it. Generate the plate,
make it an Element, attach it. The CEO's rule, 2026-09-22: *"ต้องแก้ตั้งแต่ Prop
Element เลย — ถ้าแก้ที่ต้นตอ ต่อให้ Generate Video ยังไง ก็จะได้ตาม Prop ใหม่"*
— fix the source and every later generation inherits it; fix the prompt and you
are re-arguing with the model's prior on every single shot.

A time of day behaves the same way: rule 2.

### Money on screen is invented prop money (CEO 2026-09-18; moved from the story skill)

A prop plate asked for "worn folded Thai banknotes, no readable text" came back
as a fully legible 20-baht note — `รัฐบาลไทย` readable, the denomination
readable, serial numbers readable, and a recognisable portrait of King Rama IX.
Four of four money shots in the first Act 1 shoot did the same thing: the model
draws a real Thai note whenever a prompt says "banknotes", whether or not a money
chip is attached.

My first fix was to hide the money — closed hands, sealed envelopes, the edge of
a fold. The CEO replaced it with a better one:

> "เราไม่ต้องทำเหมือนของจริงก็ได้ มันเหมือนเกินไป ... ให้เป็นเงินกาโม้แทนได้เลย"

**Change what the notes ARE, and the scene can be shot openly.** A father
counting money at his counter is good drama; hiding it in every shot was solving
a legal problem by amputating a storytelling one.

**Foreign currency is not the safer option.** Dollars, euro, yen and yuan all
carry portraits, landmarks and protected security designs; swapping one country's
note for another's trades a Thai problem for someone else's. Invented money
belongs to nobody.

The invented money the CEO ruled for:

```
The banknotes are plain fictional prop money, not the currency of any real
country: soft pastel paper in even tones, a simple printed numeral in one corner,
a plain abstract line pattern at the edges, and nothing else. No portrait or face
of any kind on the notes. No national emblem, crest, seal, flag or country name.
No real-world currency symbol, no serial numbers, no signatures, no microtext, no
watermark. Worn and soft with handling.
```

**What carries it into the shot is an Element, not these words** (decision 2026-09-25, inventory item 7:
the 2026-09-22 measurement above is later and contradicts the words-only fix). Make the invented money
the prop, bind the prop in every money shot, and check the plate itself before binding it; on banchi the
plate that held was a plain envelope (rule 7). [SUPERSEDED 2026-09-22 by §Anything that must look a
specific way needs an Element, 6 clips lost with the words alone (task-e960f3ca): the story skill's
2026-09-18 fix, "The block, pasted into every shot where money appears".]

Two things this does not change: the amount is still spoken, never read off a note
(`CTO_Story_ThaiMoralDrama`, "Every number is spoken"); and a man whose whole story is that he never
writes anything down still gets `no notebook, no pen, no paper` wherever money is counted, because the
model reaches for a ledger whenever someone counts (the NOT-LIST, below).

## The look of every character, set and prop — one sheet, quoted in every shot

The principle (one written look per character, quoted into every shot) is `CTO_Film_Production` §2. On
Flow it carries more weight than anywhere, because the prompt wins over the chip
(`CTO_Flow_Omni1.1_Ops` §Prompt grammar): a detail you do not mention is not "left as the image" — it is
left to the model, and the model will change it. The sheet must therefore be complete enough that a
prompt built from it has nothing to invent.

### Write it from the plates, never from memory (CEO 2026-09-18; moved from the story skill) [ANY]

> "คุณเขียนบทหนัง แต่คุณไม่เคยดูภาพจริงของตัวละครและสถานที่นั้นๆ เลย"

Act 1 was written twice — 48 shots, then 34 — from appearance blocks I had typed
myself. Those blocks were my memory of the plates, not the plates. Opening one
montage afterwards found three errors in ninety seconds:

- the grandmother's hair was written "cropped very short and thinning"; the plate
  has a thick short white bob
- the lender was written "going soft at the waist" with "slicked-back" hair; the
  plate is a lean man with ordinary short hair
- **the shop's staircase was written "at the back"; in the plate it is in the
  middle of the room** — and the plate's loudest features, a central pillar and
  bright red, blue and green plastic stools, appear nowhere in any prompt

The last one is the dangerous kind: every prompt was describing a room that does
not exist, and the model was filling the gap by inventing one. That is exactly
the bedroom-drift we spent the day chasing.

**The rule: before writing or revising any shot sheet, look at every plate the
episode uses — characters, locations, props — at least once.** (Binding a plate is the same rule at the
other end: `CTO_Film_Production` §3.)

#### How to look, without burning the context

Do NOT open plates one at a time. An image costs context whether or not it
earned it, and fifteen separate looks cost fifteen times one look.

```bash
python3 tools/plate_montage.py <out.jpg> docs/reports/<plate-dir>/ [more dirs...]
```

It tiles everything into one labelled sheet, sized so faces stay readable — it
picks the column count from the plate count and targets ~1600px wide. Look at
that single image, write the appearance blocks **from what you see**, then write
the sheet.

If the montage has fallen out of context by the time you are revising, build it
and look again. Once per writing session is the cost, and it is cheap.

#### Where the plates live

Plates are downloaded **once** and kept — the repo for now, Drive under the ILAG
rules once the folder is approved. Do not send an operator to re-download them
for every script; that is a paid browser run to fetch files we already have.

**When a character or location plate is regenerated, the stored copy must be
replaced in the same turn.** A stale plate is worse than none: it will be
believed, and every later script inherits the error.

### The ASSET SHEET (Flow format)

One sheet per production, holding, for every character, location and prop:

```
@lung_somchai
  face / build   : <exactly what the reference image shows>
  hair           : <length, colour, how it sits>
  carried items  : <glasses on head? watch? apron ties?>
  default outfit : <the wardrobe item, by name>
```

A prompt for that character is assembled from the sheet, not written fresh. The script's
`APPEARANCE LOCK` line is the same sheet in the script, and the ground truth a review checks each shot
against (`CTO_Flow_Omni1.1_FilmQC` Workflow 2).

### The set drifts exactly as much as the face does, and for the same reason (2026-09-18, Act 1 shoot)

First 15 shots of «บัญชี» Act 1, checked frame by frame:

| what drifted | count | why |
|---|---|---|
| a character's face | **0** | every prompt carried the full appearance block |
| the **set**, same location chip, adjacent shots | 1 (bedroom: plaster+lamp+grey blanket → concrete+beams+bulb+red plaid) | the location got 5–6 words, different ones each shot |
| a character's **posture** | 1 (bedridden grandmother sat up on the bed edge) | the shot never restated "lying propped on pillows" |
| an accessory the plate does not have | 1 (glasses) | nothing said "no glasses" |
| a prop the story forbids | 1 (a ledger and pen under the hands of a man who never writes anything down) | "counting money" let the model add what counting usually needs |

Same rule every time — **what the prompt does not say, the model decides** — but
the shoot proved it applies with equal force to the set, the posture and the
props, not only to the face. Writing the face out in full every shot worked
perfectly. Writing the location out in six words did not.

So: three fixed blocks, pasted verbatim into every shot that uses them:

- **SET BLOCK** per location — walls, light source, bedding, furniture, window.
  Identical text in every shot in that room. Not paraphrased, not shortened.
- **POSTURE BLOCK** per character whose body state is part of the story —
  "lying propped on two pillows, nasal cannula over her ears" in every
  grandmother shot until the episode's epilogue changes it.
- **NOT-LIST** per scene — the things the model reaches for and must not:
  `no glasses` on the grandmother, `no notebook, no pen, no paper` wherever
  money is counted, `no readable text` on anything the audience must not read.

A shot sheet whose location line is shorter than its character line is a shot
sheet that will drift.

### Why this is the difference between AI slop and a real short film

Everything above is bookkeeping, and bookkeeping is the entire gap. A drama
where the father's hair length changes between two shots of the same
conversation reads as AI slop no matter how good any single frame is. A drama
where it never changes reads as a film. The sheet is what makes the second one
possible, and it is cheap — it is written once and read forever.

## Output format

```
231 rows, 111 flags: {'NIGHT-ON-DAY-PLATE': 75, 'FLOW-DELETES': 6, 'SICKBED': 5, ...}
| 6 | 184 · 10s · night · @back_alley | wit_uniform(@cop_wit +@police_uniform), cherd(@lender_cherd) | cuffed,noledger,nosubs | walk side by side ... |
| | **TRANSITION** @back_alley · night → @noodle_shop_thriving · midday | | | |
- shot 184 · **FLOW-DELETES** — handcuffs — Flow deleted every take with them
```

## Reference

- Tool: `tools/continuity_sheet.py` · builder: `tools/build_shotsheet.py` (`WARDROBE`, `PROPS_BY_SHOT`) ·
  plates: `tools/plate_montage.py`
- Evidence: `docs/scripts/banchi-RETRO.md`
- Platform: `CTO_Flow_Omni1.1_Ops` · clip review: `CTO_Flow_Omni1.1_FilmQC` · story side:
  `CTO_Story_ThaiMoralDrama` (Structure gate)

## Field notes

- 2026-09-22 [COSTLY] §Rules 6 (was google-flow-ops §A prohibition is not an inventory) — automated "shot declares X therefore attach X's Element", keyed off `NOT["money"]`. That key is a prohibition ("…also no notebook, no pen, no paper, no ledger of any kind") carried by 22 shots, most with no money in frame. Caught by shooting shot 133 at 360p (4 credits): two people looking at empty tables. Reverted the same day. Cost would have been banknotes inserted into 22 scenes written to be empty of them. · evidence: f563c707 / tools/build_shotsheet.py · status: rejected
- 2026-09-22 [MISSING] §Anything that must look a specific way needs an Element — six Act 3 clips rendered a real Thai 500-baht note with the royal portrait, in a drama about illegal moneylending, against 40 words of prompt forbidding exactly that. The project's 3 characters and 6 locations were correct across 148 clips because each is chip-bound; the money was the one thing described rather than referenced. Five of the six prop Elements in the project had never been attached to any shot. · evidence: task-e960f3ca / 3f57cd1e / docs/scripts/banchi-ACT1.data.py · status: promoted
- 2026-09-22 [MISSING] §Rules 2 (was google-flow-ops §time of day) — the word `night` appended to a 60-word description of a lit, open, busy shop produced daylight in all 71 clips shot to that point. Every automated check passed; a frame-0 look found it in seconds. CEO ruled the film stays daylight rather than re-shoot. · evidence: LungNote 87c9507d / docs/scripts/banchi-ACT5.md · status: pending
- 2026-09-23 [MISSING] §Rules 3 (was google-flow-ops §references) — shot 106 drifted ต้น's hair (longer, fringe forward) in BOTH takes, on two different runners, with prompt text identical to 105 except framing. Pattern: close-up + ต้น as REF_1 + his face in profile. 107 (same close-up framing, same room, same two men) held the plate with ต้น as REF_0 facing camera; shot 22 (the only other close-up with him as REF_1) pushed him to the frame edge. Hypothesis n=3: in a close-up the second reference holds weaker, and a face seen only in profile has its hair invented from a frontal plate. Test: 106 take 3 with ต้น REF_0 facing camera. · evidence: session cto-8c06958c, ACT4 106 · status: pending
- 2026-09-23 [MISSING] §What Flow silently deletes (was google-flow-ops §A clip that vanishes after Submit) — uniform plate + the word "police" made Flow drop the clip silently (179 x2, 149, 151, A/B arm A); without the word (arm C) or with the plainclothes plate (arm B) it came back. Section added; n=1 per arm, so the rule is a default, not a law. · evidence: session cto-8c06958c, scratchpad/ab179, runner 2df21691 · status: pending
- 2026-09-23 [MISSING] §Rules 4 (was google-flow-ops §Wardrobe) — measured, not just argued: the uniformed วิทย์ as ONE full-body still (@cop_wit_uniform_A) came back older and greying in a two-shot with the father (149, 151, and A/B arm A) — the stronger close-up face in the frame leaked in. His FACE plate (@cop_wit) + a wardrobe plate with no person in it (@police_uniform), labelled "wardrobe reference: <who> wears exactly this outfit", held his face and the uniform (arm B). build_shotsheet now has WARDROBE per character. n=1 per arm, 360p. · evidence: session cto-8c06958c, scratchpad/abface, 51a3c4e1 · status: pending
- 2026-09-23 [MISSING] §What Flow silently deletes (was google-flow-ops §What Flow silently deletes in an arrest scene) — handcuffs deleted on anyone (incl. plainclothes); uniform + police lights (even thrown in from off frame) deleted; uniform + walked out + spoken charges kept. 11 arms, one variable each. Section added. · evidence: session cto-8c06958c, scratchpad/abarrest (9202-9209), ACT6 184-186 · status: pending
- 2026-09-25 [MISSING] rule 1 (what Flow deletes) — **a young child + banknotes in frame vanishes.** On taachang ACT1, S7 and S19 (grandmother + the 11-year-old + pastel prop notes) both came back with no card after a 9-min timeout, and 12 credits each were spent. S6 (the same two, a pebble jar, no money) rendered. Banknotes with the 16-year-old (S2, S14, S23) rendered. The probe S20 (same pair, money kept inside a closed cloth pouch, `nomoney` block, no touching) rendered first time. Rewrite: the child and the money are never in one frame, and money talk is fine in the dialogue. n=2 vanished + 1 probe held; S5 (father + 16-year-old, no notes shown) also vanished once and is unexplained · evidence: state/taachang/ACT1.tsv, docs/scripts/taachang-ACT1.data.py · status: pending
- 2026-09-25 [MISSING] rule 1, follow-up to the child + banknotes note — **the WORDS count, not only the pixels.** S7 and S19 vanished a second time after the notes were moved into a closed pouch, because their framing line still said "over the notes" / "notes in her hands". S20 rendered with the same pair and the same `nomoney` negation ("No banknotes, coins or money…"). So a negation passes; a positive money phrase anywhere in a prompt with the child vanishes. S19 finally rendered as the grandmother alone, with the boy off screen and his 3-word reply cut. Check: grep every prompt containing the child for notes/money/cash/baht/coins outside the negation block before firing · evidence: taachang ACT1 ledger, commits 'S7 framing', 'S19 solo' · status: pending
- 2026-09-26 [MISSING] rule 1 (what Flow deletes) — **the delete is not only child + money.** taachang ACT2, all "failed — timeout" after 15 min and then `pull` → "card not found" (deleted, not slow), 12 credits each: S25 (three adults, the villain points at the grandmother's face and screams "คนแก่ขี้โกง … เอาเงินมาให้", no child, no money in frame) ×1; S50 (two adult men, "a small stack of pastel prop notes" handed over, @money-style NOT block, no child) ×1; S30 (grandmother + the 11-year-old at home, day's money in a closed pouch + the nomoney block) ×3, even after the school uniform was swapped for home clothes. Meanwhile S24 (schoolboy saying "ไม่ใช่เงินพ่อสักบาท") and S26 (grandmother "คืนครบทุกบาท") rendered — money WORDS in dialogue alone did not delete. Rewrites fired 2026-09-26: S30 grandmother alone with no pouch, S50 sealed envelope, S25 pointing from a step away — outcome in the next note · evidence: state/taachang/ACT2.tsv, Work/task-c2723478/out/pull-{25,30,50}.log, commit 558ed6fa · status: pending
