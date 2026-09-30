---
name: CMO_Standard_Film_PromptFormat
kind: standard
owner: CMO
aka: [CTO_Film_PromptFormat]
description: >-
  STANDARD — How a shot prompt file is written, for every video engine: two zones (notes / paste block), the order of
  the paste block, one name per character, each reference declared once with a job, timed beats, the
  dialogue manner tag, negatives, the pre-fire check, and the generator (build.py + CAST lint) that makes
  the files. Trigger on /CMO_Standard_Film_PromptFormat and whenever a shot prompt, a prompt sheet or a paste block
  is written, reviewed or rebuilt: "เขียน prompt ฉาก", "prompt ตามโครงสร้าง Sorry Sir", "ตรวจ prompt ก่อนยิง",
  "prompt file", "paste block", "house format". Engine-specific syntax (how a reference is typed, audio
  markers, music words, duration limits) is NOT here: read the engine skill (CMO_Knowledge_Seedance2.5_Higgsfield,
  CMO_Knowledge_Flow_Omni1.1, CMO_Knowledge_MiniMax_H3, CMO_Knowledge_Wan3.0_TopView). Running the film is CMO_Knowledge_Film_Production.
created_by: agent
author: {role: cto, date: "2026-09-25"}
audience: [cmo, cto, script_writer, prompt_engineer, browser_operator]
---

# The shot prompt file

Built on «Sorry, Sir» (Seedance 2.5) and reused on the ILAG trailer (MiniMax H3). Each rule carries the
engine it was **measured** on: `[SD]` Seedance 2.5, `[H3]` MiniMax H3, `[ANY]` engine-independent by its
nature. On an engine where a rule was never measured, treat it as the default and record the first test in
that engine's skill. The original evidence stays in `docs/prompts/absence/PROMPT-STYLE.md` and
`AUTHORING-RULES.md` (history; this skill is the working copy).

## 1 · The file has exactly two zones [ANY]

```
=== NOTES · DO NOT PASTE ANY OF THIS ===
(everything for people: the director's words verbatim, spec, references → files, review order,
end positions, filing, take log)
=== END NOTES ===

=== ↓↓↓ PASTE FROM HERE ↓↓↓ · everything above is notes, never paste it ===
...the prompt...
=== ↑↑↑ PASTE STOPS HERE ↑↑↑ · everything below is notes, never paste it ===
```

No sentence anywhere may cancel the markers ("paste this entire text"). A warning glyph is not a marker.
One file = one shot that can actually be fired; never two timelines in one block.

## 2 · The paste block, in this order

1. **Tech header, first line** [SD]: seconds · resolution · aspect · the camera lock ("ONE CONTINUOUS
   TAKE, NO CUTS" or the framings joined by hard cuts) and what the camera is NOT doing (no cut, no zoom).
   Without the lock, Seedance invents cuts.
2. **A heading paragraph**: where we are and who matters, two sentences.
3. **REFERENCES, each with a job** [SD][H3]: every reference declared once, with what it controls
   ("face, body and colours only; take nothing of the white background"). An unjobbed reference is a coin
   flip about what the model borrows.
4. **THE FRAME**: the composition and where everyone is; optional **STATE** (what is true this shot: dead
   lamps, wet skin) and **PARTICLES** lines.
5. **WHAT HAPPENS**: `[0s] [3s] [6s]` beats, **3-4 at most** [SD]; each beat is shot type → subject and
   physical action → camera → atmosphere, 2-3 sentences.
6. **Sound**, always stated (wording is engine-specific: see the engine skill).
7. **The colour grade block** of the film (one per look, pasted verbatim).
8. **CRITICAL NEGATIVES** (the 5-12 that matter for this shot), then the film's house negatives.

## 3 · Rules

1. **One name per character, every time** [ANY]: THE ELDER is never "he", "the old man" or "him". The same
   for places and props. Name drift is a documented failure; check with a pronoun grep.
2. **Each `@reference` appears once, in the REFERENCES block** [SD][H3]; after that, the plain name. Never
   a pointer ("references as S12a"): a pasted block that points elsewhere has no references.
3. **Dialogue: a manner tag of five words or fewer right before `: "`** [SD, held on H3]. No subject and
   verb, no note, no parenthesis: `Quietly: "..."`, `THE ELDER, low: "..."`. Anything longer goes in its own
   sentence first. Measured on Seedance: a long lead-in was spoken aloud (S15a). Add to every dialogue
   shot's negatives: *no stage directions spoken aloud, no speaking anything outside the quotation marks*.
   **Transcribe every dialogue clip before calling it a keeper**; frames cannot show this failure.
4. **Physical verbs** [SD]: snap, slide, pour, burst; never "becomes", "begins to", "seems to".
5. **State size in the frame, not in depth words** [SD]: "no wider than the red door" works; "the nearest
   thing to the lens" makes it big. Say where faces point in camera terms ("facing the camera", "their backs
   to us").
6. **Negatives are few, aimed and short** [SD]. Ban a short specific ("no black suit with a white shirt")
   rather than a category; **never write a sentence that describes the unwanted image** ("take 1 showed two
   identical men side by side"): a model reads description, not intent. Better still, give the model the
   thing to do instead (`CMO_Knowledge_Film_Production` §prohibitions).
7. **Front-load** [SD]: the first 50-100 words carry the shot; keep notes, dates, stamps, file names and
   tool words (chip, plate, upload, operator) out of the paste block entirely.
8. **Change the body and the negatives together** [ANY]. After any edit, reread the whole CRITICAL
   NEGATIVES: a negative left from the old version forbids what the new one asks for. Never "add-only".
9. **A declaration is not a fix** [ANY]: a note saying "camera changed" does not change the beat that
   still describes the old camera. When a shared block is wrong for one shot, **split the shared block**;
   never write an override on top of it (an override is proof the source text is still wrong, and on
   «Sorry, Sir» the override itself was the only place the banned words appeared).
10. **Numbers must count** [ANY]: "the three riders" names three; after any edit, recount.
11. **Only the CTO edits prompt files** [ANY]. An operator who hits a problem while firing stops and
    reports; it never writes a warning into the prompt file (that is how the S1C override accident
    happened).

12. **Every shot says who faces where, who the speaker talks to, and which way things move** [ANY] (CEO ruling
    2026-10-01, after the flood-jump shot: the dog turned to the camera, spoke to the audience and jumped *backwards*
    into the water; his words: *"ตัวละคร พูดกับใคร … ภาพต้องบอกได้ว่าตัวละคร หันเข้า หรือ หันออก หันซ้าย หรือ หันขวา
    เพื่อให้มีความสมจริงกับตัวภาพด้วย"*). Write, in the shot's framing sentence and in camera terms:
    (a) **facing** of every visible character: toward the camera, away from it (back to us), three-quarter or profile,
    and screen-left or screen-right; (b) **the addressee and the eyeline**: who the speaker talks to, where that person is
    (off-screen ahead, at screen-left…) and that the eyes go there, never "to the camera" unless the camera IS the
    addressee; (c) **direction of movement**: toward or away from the lens, screen-left or screen-right (a leap
    forward is "away from the camera"; "into the water" alone let the model jump backwards); (d) **the mouth must
    stay visible**: a speaker with her back to us is written as a three-quarter rear view with the head turned to one
    side, so the side of the muzzle/mouth shows. Keep one **screen-direction plan per set** (which side the door, the
    truck, the desk are on) and repeat it in every shot of that set; an exit to the right is an entry from the left.
    Measured on Flow Omni 1.1 (EP1 shot 1): with the dog "three-quarters to camera" it addressed the viewer and
    jumped back; rewritten as "back and left flank to the camera, head turned toward screen-right, she never looks
    at the camera, speaks to someone off-screen ahead, leaps FORWARD away from the camera" she faced out, spoke
    over her shoulder and leapt forward (one frame still glanced at the camera).

## 4 · Before handing a block over: 60 seconds

Read the block top to bottom once and ask: does any line describe what this block forbids? Is every
reference declared once, with its own job? Do the negatives contradict the body? Then:

```bash
grep -nE '⚠️|✅|\(CE[OT]|\(CTO|20[0-9]{2}-[0-9]{2}|take [0-9]|GH #|\.md|\.txt|\.MP4|\.png|chip|plate|Elements panel|UUID|paste|operator|spoken words|Fire |Cuts against|as S[0-9]' <paste.txt>
```
Any hit other than the two marker lines: move it to the notes before firing.

## 5 · Generate the files, never hand-edit them [ANY]

`docs/prompts/ilag-topview/build.py` is the pattern: the shots are data (refs, heading, frame, beats,
sound, grade, negatives, review, end state), the template writes every file, and the build **refuses** when
an `@reference` appears twice or a character's text lacks the key colours of its `CAST.md` row. Shared
passages (a glow, a lamp state, a grade) are defined once and inserted, so they cannot drift between shots.
A new film copies build.py and CAST.md first (`CMO_Knowledge_Film_Production` §CAST).

## Field notes
- 2026-09-27 [WRONG] §3 rule 2 (as applied in MASTER-PROMPT-cinematic v1) — v1 told the writer to cite references by upload order on positional engines (`@Image 1 — ANA: ...`). CEO ruling, verbatim: "อันนี้ผิดนะ ต้องใช้ @ANA @MEN ... ต้องเป็นแบบนี้ `@ANA — ANA: face, build and pajamas only; ignore the background.`" The reference line is always `@<the registry TAG> — <NAME>: <what to take>; <what to ignore>.` on every engine; never `@Image N`. Master prompt v1.1 fixed (E8 + self-check) (a CEO ruling, so promoted at once) · evidence: docs/prompts/MASTER-PROMPT-cinematic.md v1.1, fc82e003 · status: promoted
- 2026-10-01 [MISSING] §3 - name a prop's colour in EVERY shot that shows it, not only in the first: EP1 S14 and S16 said 'pink towel' and came out pink, S17 said 'the towel' and came out beige; the re-fire with 'the same pink towel' came out pink (15 credits at 720p). n=1 · evidence: EP1 sheet S17 before/after 9dfceacb, rs1.tsv · status: pending
