---
name: CMO_Gate_Champa_Seedance2.0_ShortMovieQC
kind: gate
description: "GATE — Quality control for every clip of a SHORT MOVIE (one continuous story world, creatures, VFX, English dialogue) shot on champa Seedance 2.0: zero-image stage, a take-identity check, a 14-item eye checklist judged per act against the appearance lock and the named-state table, a cross-shot continuity pass, take choice, prompt-fixed re-shoots on the free lane, re-QC, one 540p file per act for the CEO. Trigger on /CMO_Gate_Champa_Seedance2.0_ShortMovieQC and on 'ตรวจคลิปหนังสั้น', 'QC หนังสั้น', 'ตรวจคลิป THE LAST BELL', 'ยิงคลิปที่ไม่ผ่านเกณฑ์', 'เลือกเทค', 'audit the short film', after any champa wave or re-shoot, and before a cut is assembled. Do NOT use for a Thai lakorn / short drama on Google Flow (CMO_Gate_Flow_Omni1.1_FilmQC) or a BLACK LIQUIDITY edit."
owner: CMO
created_by: agent
author: {role: cto, date: "2026-10-04"}
audience: [cmo, cto, browser_operator, video_editor, tester]
improved_by: []
aka: []
---

# Short-movie clip QC — champa · Seedance 2.0 — run before a cut is assembled

The CEO's order, 2026-10-04: QC the short movie with the lakorn rules first, then *"เอามาเขียน เป็นกฏ การตรวจคลิปของ
หนังสั้น … ที่ไม่ใช่ ละครสั้นเพราะมันอาจจะต้องตรวจมากกว่า เยอะเลย"*. This gate is that rule set. It keeps the four
stages of `CMO_Gate_Flow_Omni1.1_FilmQC` (cheap checks first, eyes only where they are needed, a 540p file per act,
lock and assemble once) and adds the checks a short movie needs.

## Why a short movie needs its own gate

Measured on THE LAST BELL, 2026-10-04: 41 planned shots, 50 takes on disk (40 first takes, 10 second takes).

| stage | what it found |
|---|---|
| 1. zero-image (duration, audio, caption band, line read-back) | **0 defects in 50 takes.** All 15.0 s with audio; caption band max 39 against GATE 80; every scripted English line read back at 0.79–1.0 |
| 2. eyes, per act | **19 failing takes; 14 shots with no usable take** (B04, C02, C07–C10, D03, E01, E02, E04, E06–E08, E10), plus D05 never shot: 15 of 41 shots (37 %) |

A lakorn on Flow fails in the dialogue and the face: a burned caption, a line said twice, the wrong face. Stage 1
catches most of that for free. A short movie fails in the **picture**: the weather, the size of a creature, which
way a body coils, who stands where, whether a bell is cracked yet. Stage 1 cannot see any of those, so on a short
movie the eye stage is the gate, and it needs a longer checklist. By act: A 0 of 8 shots without a usable take
(second takes saved 6 shots), B 1 of 7, C 5 of 10, D 1 of 6 plus the missing D05, E 7 of 10. The storm and the
creature acts fail most.

## Inputs — gather before stage 1 (all exist after pre-production)

- **Shot prompts** as jobs files (`[{"id": "<prefix><shot>", "prompt": "…", "refs": […]}]`); the id is the clip's file stem.
- **Cut list** — `<shot> <cut seconds> [path]`, from the rough cut. Judge only what is inside the cut.
- **Appearance lock** — the CAST table, item by item (THE LAST BELL: `docs/prompts/last-bell/CAST.md` on origin/main).
- **Named-state table** — what is true of each person and object per scene: dry or soaked, bell whole or cracked,
  eyes open or closed, time of day, weather. If the film has none, write it first (one line per scene). THE LAST
  BELL had it only inside CAST.md, and two lines contradicted the prompts (see rule 8).
- **Story beats** — one line per shot: what has to be understood when it ends.

## Checks

### Stage 1 — zero images (minutes, free)
`tools/shortmovie_qc.py stage1 --clips <dir> --jobs <jobs.json …> --out <qc>/stage1.tsv`. The tool reports duration,
audio and its mean level, the caption-band pixel score (`tools/burned_text_scan.py`), and a read-back of each quoted
line. The language is chosen per line (English for dialogue, Thai for a Thai song) with VAD on. A clip with no
quoted line is transcribed in auto mode, so unexpected speech shows in `heard`.
- Passes when: duration matches the job, audio is present, no `CAPTION?` flag, every line scores ≥ 0.8, and
  `tail_voice` is `-`. A score below 0.8 is a NOTE for ears, not a FAIL, until someone has listened.
- `tail_voice` lists voice (speech, song, hum; silero VAD) that ends inside the last 3 s of the clip. Any entry is a
  FAIL: the prompt broke `CMO_Standard_Film_PromptFormat` rule 13 (quiet tail) and the editor cannot cut cleanly.
  First run: 5 of 53 takes (A05 t1 and t2 Yai's hum, B01 t2, E03, E04's lullaby); music-only clips stayed empty.
- A Thai **sung** line reads back badly (E04 lullaby 0.39, heard as near-Thai syllables). Judge a song by ear.
- `Thanks for watching!` at 0.0–2.0 s on a music-only clip is a whisper hallucination. Re-read with VAD off before
  calling it speech: C10 and D03 came back as `BOOM!`, the bell and thunder hits.

### Stage 2 — take identity (seconds, free)
Before any eye looks at quality, prove each file is the shot it claims to be.
- md5 of every take of a shot must differ. A re-shot prompt can fetch the OLD card. `lb_harvest.py` now refuses
  identical bytes, but check on disk anyway.
- The middle frame must show the shot's own action. On 2026-10-03, `lb-A03.mp4` held A04's bell-ringing and
  `lb-A04.mp4` held A03's run: two cards harvested seconds apart came back swapped. The duplicate check cannot
  catch that; only a look at the action does. The harvester now skips a card when more than one download link is
  visible.

### Stage 3 — the eye checklist, one judge per act (the gate itself)
`tools/shortmovie_qc.py sheets --clips <dir> --cuts <list> --prefix <prefix> --out <qc>/sheets` makes 3 frames per
take (0.5 s, cut/2, cut − 0.5 s), 8 takes per image, take 1 on the first row. Give one judge per act (a subagent on
the free side of the budget, run in parallel) the act's sheets, the shot prompts, the lock, the named-state table
and the cut lengths. The judge may pull more frames from inside the cut, and writes
`<qc>/eye-<act>.tsv` with columns `take · verdict (PASS / NOTE / FAIL / UNSURE) · reason ≤ 25 words · better take`.
Each take is judged on all 14 items:

| # | check | evidence that passes it | LAST BELL failures |
|---|---|---|---|
| 1 | Cast identity against the lock, item by item: face, hair, every garment, jewellery metal, props | each lock item named and seen | A05 t2 gold bangles where the lock says brass, never gold |
| 2 | Extras do not copy a lead's signature costume | one wearer of each signature item | white jacket + gold chain doubled the Governor: B04 t2, D03, B01 t2 (minor) |
| 3 | Creature form: head count, colour, crest, no species drift | matches the creature sheet | E10 two heads + long manes (Chinese dragon); E04 pearl-white scales, not jade |
| 4 | Named states for this scene | every state in the table holds | E01 bell not cracked; E08 the Naga's eyes open; E04 Kaew dry where she must be soaked |
| 5 | Weather and time of day against the act's grade | sky, rain and light match the grade line | C02, C09, C10, E01 sunset or calm gold sky inside a storm act; E06 opens on sunset |
| 6 | Each timed beat `[Ns]` happens, in order, inside the cut, and nothing the prompt forbids happens | each beat seen in a frame | C07 Kaew grabs and pulls a rope written as snapped out of reach |
| 7 | Who is where: the location of every person | matches THE FRAME line | E02 Mek in the pavilion, not at the chedi base; E08 Mek at the rail, not in a boat |
| 8 | Geometry and scale of the big things, relative to the set | the spatial relation holds (around, behind, taller than) | E06/E07/E10 the coil sits in the city centre, not around its edge; C08 the wave is a thin line, not a mountain; D03 the head rams the barge, not the tail |
| 9 | Facing, direction of movement, eyeline; nobody looks into the lens | FilmQC rule 6 on every sampled frame | B01 t1 and B04 the Governor talks to the lens |
| 10 | Camera move against the first line (locked, orbit, crane, push) | the move is seen across the 3 frames | A01 t1 dives to water level instead of holding the aerial (NOTE) |
| 11 | Dialogue: the line is heard, in its language, by the right speaker | stage 1 score plus the mouth on the speaker | none failed; A07 t2 read "Let again bell girl" (0.82), a NOTE |
| 12 | No text anywhere in frame: captions mid-frame (15–45 % height) too, signs, watermarks | nothing readable | none in 50 takes; keep the check, the band scan does not cover mid-frame |
| 13 | Take identity (stage 2) | the action is this shot's | A03/A04 t1 swapped |
| 14 | Story beat: would a viewer understand what the shot must say? | the beat line holds without sound | C02 shows a dry porch scene, not people clinging to flooded roofs |

### Stage 4 — cross-shot continuity (one pass in cut order, after the per-act verdicts)
Read the chosen takes in order and check what no single-shot judge sees:
- a state that changes must change once and stay changed (E10 opens on the bell hanging whole after E08 has it broken);
- a prop must look the same in every shot (E04 mallet head dark, E08 crimson);
- the weather sequence must make sense (C07–C08 storm, then C09 calm gold sun);
- the creature must keep one design from its first shot to its last.

### Stage 5 — take choice and the re-shoot list
- Per shot, pick the take with no FAIL and the fewest NOTEs; a NOTE take is used, not re-shot.
- A shot with no usable take is re-shot. Fix the prompt for a **systematic** defect (weather from a reference,
  geometry, creature drift, a costume doubled); a plain re-roll only for **variance** (one glance at the lens, a
  beat that lands late).
- Write each fix as the smallest edit that names the defect (THE LAST BELL: `lb_build_rs1.py` in the work set):
  - scope each location reference to "take its shape only, never its sunlight, sky or weather";
  - put "no sun, no sunset, no golden hour, no clear sky" in the negatives of a storm shot;
  - state the spatial relation in plain words ("one huge ring in the sea around the outer edge of the city, every
    house inside the ring");
  - name the forbidden act ("KAEW never holds the rope");
  - limit a signature costume to one wearer ("only one man in a white jacket", extras "in plain brown");
  - add the creature negative ("one head only, jade-green scales, no mane, no antlers, no legs, never white").
- Change the prompt's heading line (line 2): the harvester keys on it, so the new card stays distinct from the old one.
- Keep every prompt ≤ 2,000 characters: champa refuses 2,001 (measured 2026-10-03).
- Order the queue: missing shots first, then the shots the story stands on (the creature's climax, the lullaby),
  then the rest.
- Fire only through the free-lane guard (`lb_fire.py`: `is_free_label`, Unlimited on, queue below 8). A paid
  render needs the CEO's OK with the exact cost (`ALL_Rules_Approvals`).

### Stage 6 — re-QC and lock
Each harvested re-shoot goes through stages 1–3 again, judged alone and against its neighbours in the cut. A take
that passes is locked: its name goes in the cut list. Nothing is assembled until every shot in the act is locked.

### Stage 7 — the CEO's file
One 960x540 file per act in cut order, sent with the act's verdict table. The CEO judges by eye; never open with a
computed number.

## Output

```
ACT E — 10 shots, 10 takes
Gate 1 (zero-image)      : PASS — 10/10 15.0 s with audio, caption band max 24, lines 1.0 / 0.39 (sung Thai, by ear)
Gate 2 (take identity)   : PASS — md5 distinct, actions match shot ids
Gate 3 (eye checklist)   : FAIL — E01 #4 #5, E02 #7, E04 #3 #4, E06 #8, E07 #8, E08 #4 #7, E10 #3 #8
Gate 4 (continuity)      : FAIL — E10 bell whole after E08 broken; mallet head E04 vs E08
Gate 5 (re-shoot list)   : 7 re-shoots queued, free lane, priority E04 E06 E07 E10 E08 E01 E02
Verdict: STOP — act E not locked; 7 re-shoots pending re-QC
Not checked: motion between sampled frames, sound mix, lip sync on English lines, pacing across the cut
```

## Refusal

Any FAIL in gates 1–4 for a shot stops that shot from the cut. Name what failed and the fix that was queued. Never
call an act clean when only stages 1–2 ran.

## Rules

1. **HARD — Never report a count from a detector that has not been checked on known hits and known misses.**
   Inherited from FilmQC rule 1. Here: whisper's "Thanks for watching!" on two music clips would have read as two
   clips with stray speech.
   **Why hard:** a number sent to the CEO drives what is re-shot and paid for.

2. **A reference image carries its weather into the shot.** Every pavilion shot fired with `loc_bell_pavilion`, a
   sunset sheet, came back with sun or a calm gold sky in a storm act (C09, C10, E01). Scope every location
   reference and add the storm negatives. Runs: 1 (THE LAST BELL); promote after a second film agrees.

3. **Spatial relations must be written as relations, and checked as relations.** "Coils around the city" became a
   small coil beside the chedi in E06, E07 and E10. Write where the thing is, relative to things the model knows
   (the outer edge, every house inside). Then check that relation, not just "the creature is in frame". Runs: 1.

4. **One judge per act sees the act; only the continuity pass sees the film.** Four act judges missed nothing
   inside their acts, yet E10's whole bell after E08's broken one needs the cut order. Run stage 4 every time.

5. **Second takes are worth firing on a free lane before re-writing anything.** In act A, second takes fixed 6 of
   8 shots with the same prompt. A prompt rewrite is for a defect that appears in every take.

6. **Night queue: queued is not lost.** champa's free lane holds jobs until 09:00 Thai time and delivers within
   about two hours after that; a queued card shows "Unlimited · อยู่ในคิว" at a frozen 94 % and no "เพิ่มเติม" button.
   Do not re-fire a queued shot.

7. **Say what this loop still misses, every report.** Motion between sampled frames (a limb that morphs at 3.2 s),
   the sound mix, lip sync on English lines, and pacing across the cut. A clean report means "no defect found by
   stages 1–4", not "no defect".

8. **A conflict between the lock and a prompt goes to the director, not into a verdict.** B06's prompt asks for
   Kaew soaked while the lock says dry in acts A–B; the lock says the bell is cracked "from D3" while D05/D06 crack
   it. Do not fail a take for obeying its prompt. Fix the source, then judge.

## Reference

- Tools: `tools/shortmovie_qc.py`, `tools/burned_text_scan.py`
- Sister gate (lakorn on Flow): `CMO_Gate_Flow_Omni1.1_FilmQC` · workflow: `CMO_Workflow_ShortFilm` step 8 ·
  craft: `CMO_Knowledge_Cinematography_ShortMovie` · engine: `CMO_Knowledge_Seedance2.5_Higgsfield`
- Evidence: THE LAST BELL QC 2026-10-04, work set `Assets/Agents/Core/last-bell/work-a0a0aeec/lb_out/qc/`
  (`stage1.tsv`, `eye-A.tsv`, `eye-B.tsv`, `eye-C.tsv`, `eye-DE.tsv`); re-shoot builder `lb_build_rs1.py`

## Field notes

- 2026-10-04 [MISSING] new gate — first run on THE LAST BELL (41 shots, 50 takes): stage 1 found 0 defects and the eye stage found 14 shots without a usable take plus 1 never shot; rules 2, 3 and 5 rest on this one film · evidence: session cto-671f688f, `lb_out/qc/eye-*.tsv`, re-shoot round `lb_jobs_rs1.json` (15 jobs) · status: pending
- 2026-10-04 [COSTLY] stage 3 — four act judges ran in parallel, 6–10 min each, about 570k subagent tokens in all; the sheets themselves cost one image per 8 takes. A local check for weather (mean saturation and hue of the top third against the act's grade) could pre-flag rule 2 shots for free · evidence: session cto-671f688f · status: pending
- 2026-10-04 [MISSING] stage 1 — the gate had no check for the end of the clip; Yai's hum in A05 was cut off at the end of the 15 s and nothing flagged it until the CEO did. Added `tail_voice` (silero VAD, voice ending in the last 3 s) to `tools/shortmovie_qc.py stage1` and made it a FAIL, after the CEO's quiet-tail ruling (`CMO_Standard_Film_PromptFormat` rule 13) · evidence: `lb_out/qc/stage1-v2.tsv` 5 of 53 · status: promoted
- 2026-10-04 [MISSING] stage 3 item 2 (one of each character) — `scripts/prompt-lint.py:424-425` checks duplicates only when two or more `@…char_…` chips are bound, so it never runs on champa `@ภาพN` prompts; the Governor doubled in 3 of the 5 takes that bind his sheet (B01 t2, B04 t2, D03) with a group noun ("his men", "servants") and no clothes for the extras. Round 2 applies the Seedance 2.5 fix (dress and place every extra, "the only person in white or gold", "exactly ONE", verbatim negatives) and A/B-tests the 5-panel sheet against a single-panel crop · evidence: docs/prompts/last-bell/DUPLICATE-LESSONS-2026-10-04.md, eye-B.tsv, eye-DE.tsv · status: pending
- 2026-10-04 [WRONG] rule 6 "holds jobs until 09:00 Thai time and delivers within about two hours after that" — on 10-04 the page banner read "Seedance และ MiniMax H3 (Unlimited) ปิดปรับปรุงชั่วคราว 09.00 - 22.00 จนกว่าการอัปเดตจะเสร็จสิ้น" and no LAST BELL job finished between 11:42 and 20:40 (16 queued, the oldest 14.5 h, one card frozen at 89 %). The free lane can be closed by day, not only held by night. Before calling a job stuck, read the banner from the page text (`pg.inner_text("body")`, search "ปิดปรับปรุง" / "Unlimited"); the harvester log ("todo=16 saved=0") cannot tell a closed lane from a broken harvest · evidence: session 671f688f probe 20:38, lb_out/harvest_rs1.log · status: pending
- 2026-10-05 [WRONG] rule 6, second sighting after the 2026-10-04 note — "closed 09:00–22:00" does not mean open at night. The same banner was still on the page at 06:44 on 10-05, and the 8 jobs already queued sat at "อยู่ในคิว AI 94%" from before 22:35 until after 06:34 with no clip out, right through the 22:00–09:00 window. Judge the lane by whether the card % moves between two reads 15 min apart, not by the hours in the banner · evidence: session 671f688f, work-a0a0aeec/lb_out/status.log (every 15 min, 00:57–06:34, unchanged) · status: pending
- 2026-10-05 [COSTLY] whole queue — the harvester only sees finished cards (a Play button), so a failed or stuck job is invisible until someone reads the page by hand. 7 jobs that were in flight when maintenance began failed and were refunded ("AI คืนจำปาแล้ว สร้างไม่สำเร็จ") without any log line. What worked: a read-only probe that classifies the card text in front of each job heading (failed / queued NN% / other) and a change-only 15-min watcher run under nohup (`lb_status.py`, `lb_watch_status.sh` in the LAST BELL work set). The harvester should write a "fail" event itself so the feeder can re-queue under a new id · evidence: session 671f688f, the 7 jobs re-queued as -r2 on 10-04 · status: pending
