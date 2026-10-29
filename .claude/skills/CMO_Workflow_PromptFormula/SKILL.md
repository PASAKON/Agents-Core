---
name: CMO_Workflow_PromptFormula
kind: workflow
owner: CMO
description: >-
  WORKFLOW — How every CMO-lane prompt is born and how a hit becomes a formula: look up the channel's
  formula index first; with no formula, search MeiGen for similar work and REWRITE it under our rules
  (never paste); make, post, measure for 7 days against the channel's own average; a hit is written up as
  one formula file that the next EP repeats, and that other channels may adopt. Trigger on
  /CMO_Workflow_PromptFormula and before ANY prompt for a film, B-roll, cover, reel or still in the CMO
  lane: "เขียน prompt", "หา prompt", "MeiGen", "สูตรสำเร็จ", "formula", "ทำตามสูตร", "EP ต่อไปทำแบบเดิม",
  "ใช้สูตรนี้กับช่องอื่น". Do NOT use it for engine rules (the engine's Knowledge skill) or the house
  prompt layout (CMO_Standard_Film_PromptFormat).
created_by: agent
author: {role: cmo, date: "2026-10-30"}
audience: [cmo, project_head, script_writer, prompt_engineer, browser_operator, video_editor, web_designer]
---

# Prompt formula loop: MeiGen thinks, a hit becomes our formula

CEO 30 Oct 2026 (CMO chat), his words: *"อยากให้ใช้ MeiGen แทนการคิดเอง และ ส่วนของเราเอาไว้ใช้เป็น Skill สำหรับ
Workflow ซ้ำๆ … เราได้สูตรสำเร็จมาแล้วใน EP ใด EP นึง เราก็ทำตามสูตรนั้นรัวๆ … ใช้ MeiGen เป็นคลังความรู้ ดึงเอาสิ่งที่คล้าย
มาปรับใช้ ไม่ใช้ตรงๆ ตามกฎรวมๆ ที่เราใช้กัน … เมื่อมัน Success เราก็เอามาเขียนเป็นสูตรสำเร็จ ไว้ใช้กับช่องนั้น หรือช่องอื่นๆ"*.

## Hard rules

1. **HARD — The formula index is read before anything else.** `knowledge/brand-knowledge/brands/<channel>/formulas/INDEX.md`.
   A formula that fits the job is followed as written; MeiGen is searched only when none fits.
   **Why hard:** the CEO's order is "ทำตามสูตรนั้นรัวๆ"; a worker that re-invents a proven EP throws the proof away.
2. **HARD — Nothing from MeiGen is pasted.** A MeiGen prompt is someone else's work: ideas only (CEO 11 Oct). Take the
   mechanism (light, lens, framing, beat order), write our own words in `CMO_Standard_Film_PromptFormat`, then the
   target engine's rules. **Why hard:** others' work never becomes our base; a pasted prompt is not ours to own.
3. **HARD — Only MeiGen's free tools.** `search_gallery`, `get_inspiration`, `enhance_prompt`, `list_models`.
   Never `generate_image` / `generate_video` (paid, and not our engines). **Why hard:** money (ALL_Rules_Approvals).
4. **HARD — Every prompt report carries the source line** (§Step 3). No line, the CMO sends it back unread.
   **Why hard:** without it nobody can tell a formula run from a guess, and a formula's proof is lost.
5. The org's prompt bans still bind: no blush / หน้าแดง / หูแดง, every person 18+, no « » or em dash in Thai.

## What MeiGen is good for (measured 30 Oct 2026, 6 searches)

- Mostly **still-image** prompts (gptimage, nanobanana): strong on light, lens, grade, framing, product and food looks.
- **Few video prompts**: some timed storyboards (`0-3s …`), mostly ads. Weak on motion, beats and acting.
- So: MeiGen gives the **look** (first frame, Element plates, covers, thumbnails, the light of a shot); the **motion and
  beats** come from the engine skill (`CMO_Knowledge_Flow_Omni1.1`, `_Seedance2.5_Higgsfield`, `_Wan3.0_TopView`)
  and our own library `CMO_Knowledge_CinematicPrompts` (66 entries, the fallback when MeiGen has nothing close).
- Its text is in many languages (Russian, Japanese, Korean). Read the idea, never translate-and-paste.

## The steps

### Step 1 · Formula lookup [node: lookup]

Open the channel's `formulas/INDEX.md`. A row whose "use for" matches the job → open that formula and follow it;
skip to Step 4. A row from another channel marked "adopt to: <this channel>" counts too. No match → Step 2.
A channel with no `formulas/` folder yet: create it with an empty `INDEX.md` (template in §Formula file).

### Step 2 · MeiGen search [node: meigen]

2-4 searches in plain English describing the shot (subject, place, light, mood, camera), `limit` 5-10. Open the
1-3 closest with `get_inspiration`. Note their ids. Pick per shot what to borrow: light direction, lens, grade,
composition, a beat order. Nothing else.

### Step 3 · Write our prompt [node: write]

Write it fresh in `CMO_Standard_Film_PromptFormat`, then apply the engine skill. 1-2 person story shots may use a
`CMO_Knowledge_CinematicPrompts` entry as the skeleton (CMO ruling 29 Oct); crowds and physics gags stay plain.
Every prompt report (sheet, PLAN.md, letter to the CMO) carries one source line per shot or per batch:

```
source: formula ilag/F2-true-disaster v1      # a formula run
source: meigen 2110375165523800074, community_db6aa5b0… · borrowed: haze + low key light · rewritten    # no formula
source: library shortfilm-ilag-03 · rewritten
```

### Step 4 · Make and post [node: make]

The engine's own workflow (`CMO_Workflow_ShortFilm`, `CMO_Workflow_LakornSerial`, `CMO_Workflow_BlackLiquidity`)
and its spend cards. Record in the EP's STATUS or logs.txt which formula or source each shot used.

### Step 5 · Measure [node: measure]

7 days after the post, against **the same channel's own average** of its last 5 posts (or all, if fewer):

| Platform | Hit = both of |
|---|---|
| YouTube long | views ≥ 1.5× channel average · average view duration ≥ channel average |
| Shorts / Reels / TikTok | views ≥ 1.5× channel average · 3-s hold or watch-through ≥ channel average |
| Basket / shop clip | basket CTR ≥ 0.5% (the BL rethink line) |

Under 5 prior posts, the bar is a hint, not proof: a formula born there is `v0 (unproven)` until a second EP repeats it.
A CEO judgment ("ตัวนี้ปัง") also counts as a hit; write his words as the evidence.

### Step 6 · Write the formula [node: formula]

A hit becomes one file `formulas/<id>.md` plus one row in `INDEX.md`, the same day the numbers land. The PH writes
it; the CMO approves it (the bank is the CMO's). What made it work goes in, as rules a worker can follow without
guessing: structure, timing, shot types, prompt skeleton with the slots marked, voice, length, cover, caption.

### Step 7 · Repeat and adopt [node: repeat]

The next EP follows the formula from Step 1. Each repeat appends one evidence row (EP, numbers). Two misses in a row
→ the formula is marked `paused` in INDEX.md and the CMO decides: fix, or retire. To use it on another channel, the
CMO adds an "adopt to" row naming what must change (language, length, platform, brand).

## Formula file

`knowledge/brand-knowledge/brands/<channel>/formulas/INDEX.md`:

```
# <channel> formulas
| id | use for | status | proven by | adopt to |
|---|---|---|---|---|
| F2-true-disaster | YouTube long, real disaster, narrated | v0 (unproven) | Lituya EP (pending) | — |
```

`formulas/<id>.md`: title, status (`v0 unproven` · `v1 proven` · `paused` · `retired`), use for, the rules, the prompt
skeleton with `{slots}`, what must never change, evidence rows (EP · link · date · numbers vs average), adopt notes.

## For a PH briefing a worker

Runners outside Claude (AGY, Codex) do not load skills. Paste rules 1-5 above and the channel's formula (or the
MeiGen ids you chose) into the brief itself. A brief that says only "use the skill" is a guess waiting to happen.
