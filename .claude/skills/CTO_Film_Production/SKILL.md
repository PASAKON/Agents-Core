---
name: CTO_Film_Production
description: >-
  How to run a multi-shot AI film on any engine so it stays one film: the story gate, CAST.md from day one,
  reference plates, what to re-shoot when something changes, tolerance, prose against reference, why a
  prohibition fails, countable motion, reviewing by eye, the continuity check before firing, and what the
  director decides. Trigger on /CTO_Film_Production and whenever a C-level directs a short film, trailer
  or ad made of many generated shots: "ทำหนัง", "หนังสั้น", "trailer", "ตรวจความต่อเนื่อง", "ต้องยิงใหม่ฉากไหน",
  "เปลี่ยน Element", "CAST". Engine facts (buttons, money, reference caps, what a scanner blocks) live in the
  engine skills: CTO_Seedance2.5_Higgsfield, CTO_Flow_Omni1.1_Ops (+ _Continuity, _FilmQC), CTO_MiniMax_H3,
  CTO_Wan3.0_TopView. How a prompt file is written is CTO_Film_PromptFormat. Do NOT fire for a single
  standalone clip or still-image work.
created_by: agent
author: {role: cto, date: "2026-09-25"}
audience: [cto, cxo, script_writer]
---

# Running a multi-shot AI film

Paid for on «Sorry, Sir» (Seedance 2.5, Higgsfield), «จุดจบของเจ้าหนี้นอกระบบ» (Google Flow) and the ILAG
trailer (MiniMax H3). These are the rules that did not depend on the engine. Engine facts are in the
engine skills; this file never repeats them.

## 1 · Story before shots

A scene is prompted only after it passes the structure gate (IRON-RULES §51, `tig-scene-engine`: goal,
obstacle, tactic, reversal, value shift, and the removal test). For the Thai moral short dramas the story
rules are `CTO_Story_ThaiMoralDrama`.

## 2 · CAST.md from day one (CEO 2026-09-08)

Before the first shot prompt, one `CAST.md` beside the prompts: one row per character, with the canonical
reference name, the look with colours named, what they carry and never carry, the acting register in five
words, and their locked lines. A prompt may not describe a character in words that disagree with its row;
when the director changes a character, the row changes first and every shot bound to it is rebuilt. One
saturated colour per person, so two characters never read alike.

- The first commit of a new film's prompt directory is CAST.md. A prompt that binds a reference absent
  from CAST.md fails lint.
- Two references for one character is a defect in CAST.md, not a style choice («Sorry, Sir» shipped two
  registrars and two grandmother wardrobes into Draft 3 because no single page showed the split).
- The check is "does every character line in this paste block match its row?": grep the FLATTENED paste
  block (phrases wrap across lines) for each character's colour and carried object.

## 3 · Plates

- One character per plate; a location plate holds no people (people in it freeze stale wardrobe into every
  shot that uses it). Engine scanners add their own reasons (see the engine skill).
- **Read what a plate depicts before binding it.** A name, even one the director gave you, is a pointer,
  not a verification (a "wall" plate that was a corridor cost a take on Sorry Sir). Read one line of prose
  that describes it (a prompt that already used it, CAST.md, or the image itself), never the id alone.
- **A prose sentence that contradicts the plate's own geometry is the tell.** If you find yourself writing
  "the camera faces X" over a reference that does not face X, you have the wrong plate, and no wording
  will fix it.
- **Never re-point an existing reference to a new image**: shots that bound it keep the old one silently.
  A new name, then sweep the prompts.

## 4 · Change a reference or a prompt → re-shoot everything bound to it

The director's rule: no "close enough". Keep the dependency map generated from the prompt files, never
remembered (`grep -o '@[A-Za-z_]*' <prompts> | sort | uniq -c`), and tell the director the re-shoot count
before a plate is ordered.

## 5 · Say the tolerance out loud, early

Without one, an operator chases an exactness nobody asked for. Put it in the brief ("10-20 % drift is
fine") and name what it does not cover: people in a location plate, the length of a dialogue shot, the
resolution, the money check.

## 6 · Prose against reference

- The model follows your words over a reference that failed to attach, and a wrong reference over your
  words. Count bound references against mentions before every fire; keep prose and reference agreeing.
- Anything that must look identical across shots comes from a reference, described in matching words as
  the fallback.
- Some engines let a video reference beat the prose (measured on Seedance): see the engine skill.

## 7 · Why a prohibition fails, and what holds

A ban says what not to render, never what to render instead, and the gap fills itself. In order:
1. **Replace, don't forbid**: something specific to look at, a named body angle, an object in hand.
2. **Ban the relationship**, not the absence ("the cart is with him and only with him").
3. **A vague description is a blank the model fills**: paste the plate's full description.
4. **Check the reference before rewriting the words**: twice the words were right and the reference won.
How to word a ban is `CTO_Film_PromptFormat` rule 6.

## 8 · Motion you can count; judge by eye

- An adjective is not a direction. Say how many position changes, who swaps with whom, and by when; give
  the review a test that can fail ("if 15 s looks like 1 s, it failed").
- Staging is a location problem first: a narrow set clumps any crowd, whatever the words say.
- **Look at it first; a number only confirms (CEO 2026-09-11: "อย่าวัดจากตัวเลข วัดจากสายตา").** Review every
  round from one numbered contact sheet (start / middle / end frame per clip), then give the director a
  per-number table of what failed against the brief. Mechanical checks (transcripts, burned text) are
  there to FIND audio and text defects that frames cannot show; frames CONFIRM.
- Transcribe every dialogue clip before calling it a keeper.

## 9 · The continuity check before any paid round

One table, shot by shot, in cut order: where it starts, where it ends, and what breaks against the next
shot. Check: time of day and grade, place, who is present and where they sit, wardrobe and props, every
light source, weather, above or below water, screen direction (one direction for travel, never toward the
camera unless meant), and whether each shot's end is the next shot's start. Then ask the director every
open question at once, with a recommended answer each, and record his answers in the film's folder before
changing any prompt. Engine-specific flags (what Flow deletes, night on a day plate) are in the engine's
continuity skill.

## 10 · What the director decides

Story, who a character is, every line, the ending, the order. Do not override it, even while he sleeps;
but do not stall either: do everything that does not depend on the open question and flag assumptions in
writing. Write his words down verbatim, in his language, the moment he says them; after any renumbering,
re-attach his messages to the new numbers before calling anything missing. When two sessions relay notes
on one film, the direct answers win and the relays are listed as superseded.

## 11 · When a re-fire passes, write the A/B entry

Prompt A (produced the defect) against Prompt B (fixed it), quoted from git, the defect as seen in the
frames, and why B held; written by the reviewer, never the operator. The ledger belongs to the engine
(`CTO_Seedance2.5_Higgsfield/AB-LEDGER.md` for Seedance).

## 12 · Workers and money

- **Brief workers through a file in their worktree**, then send one short pane line pointing at it; long
  pane messages arrive in fragments (a worker once spent half an hour firing the wrong scene while
  "reconstructing scattered relays"). The file says: *this file is the source of truth; ignore any partial
  pane message that disagrees with it.*
- **A worktree is frozen at task creation**: anything committed to main afterwards does not exist for it.
  Copy changed files into every live worktree and compare checksums. A worker that refuses an instruction
  because it cannot verify it is behaving correctly (one refused four times, right each time): find out why
  it cannot see what you can (`dev-spawn-protocol`).
- **Check delivery, not just generation**: a finished clip once sat uncollected on the platform for two
  hours while everyone believed it was done. Commit every asset id before downloading: ids cannot be
  recovered, files always can.
- Change one variable per test; piggyback a test on a fire you have to make anyway.
- Any paid generation: the director gets the exact $ first.

## Field notes
