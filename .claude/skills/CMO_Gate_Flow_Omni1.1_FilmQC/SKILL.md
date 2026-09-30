---
name: CMO_Gate_Flow_Omni1.1_FilmQC
kind: gate
owner: CMO
aka: [CTO_Flow_Omni1.1_FilmQC]
description: >-
  GATE — Quality control for an AI film shot in Google Flow (Omni 1.1 Flash): the per-act
  loop that found every defect of «จุดจบของเจ้าหนี้นอกระบบ» cheaply — mechanical
  audit with zero images (transcript, pixel caption scan, duration), reading the
  dialogue back before any claim about it, one contact sheet per act for
  faces/clothes/posture, a 540p file per act for the CEO, lock what passes,
  assemble once. Trigger on /CMO_Gate_Flow_Omni1.1_FilmQC and proactively
  after any Flow shoot or re-shoot — 'ตรวจคลิป', 'audit the film', 'check the
  shots', 'ส่งให้ดูทีละองก์', 'ประหยัด token ตรวจภาพ', 'ซับขึ้น', 'พูดซ้ำ', 'หน้าเพี้ยน',
  or before assembling a cut. Do NOT fire for Higgsfield/Seedance clip review (its
  failure modes differ) or for editing a BLACK LIQUIDITY episode (CMO_Procedure_BlackLiquidity_Cut).
created_by: agent
author: {role: cto, date: "2026-09-23"}
audience: [cmo, cto, browser_operator, video_editor, tester]
---

# Film QC — Google Flow · Omni 1.1 Flash

## Model scope

Read `CMO_Knowledge_Flow_Omni1.1` §Model scope first: what "proven on" means and the [ANY] / [FLOW] tags.
For this skill: the tools themselves (`film_transcript.py`, `burned_text_scan.py`, ffmpeg contact
sheets) are generator-agnostic [ANY]. What they are *looking for* — burned Thai captions, a line said
twice, a REF_1 face drifting, a clip that vanished from the feed — are Omni 1.1 Flash habits [FLOW]. On
Seedance, calibrate the scan's GATE and re-learn the defect list before trusting a clean report.

## What it does

A four-stage loop per act, cheapest first, so eyes (and image tokens) are spent only
where a cheaper check cannot see:

| stage | tool | images | cost | sees |
|---|---|---|---|---|
| 1. mechanical | `tools/film_transcript.py`, `tools/burned_text_scan.py`, `tools/clip_review.py` (ffprobe duration) | 0 | ~3 s + 0.4 s a clip, free | a line missing, said twice, a caption burned in, wrong length, a silent clip |
| 2. contact sheet | ffmpeg, 3 frames a shot, ~8 shots an image | 1 per ~8 shots | one image read | wrong face, wrong clothes, someone lying down, wrong person in frame, day/night |
| 3. CEO review | 540p file per act (8-14 MB) sent into the chat | 0 for us | the CEO's time | taste, pacing, anything we missed |
| 4. lock + assemble | concat of already-normalised clips | 0 | 2 min | — |

## When to invoke

- Right after a `flow_shoot.py run` or `pull` finishes — before anything is uploaded as current or assembled.
- The CEO reports "ซับขึ้น", "พูดซ้ำ", "หน้าเพี้ยน", "ชุดเปลี่ยน", or a timestamp in the cut.
- Before a full assembly.
- Before any claim about what a clip says (see "Reading the dialogue back").

## When NOT to invoke

- Before shooting — `CMO_Gate_Flow_Omni1.1_Continuity` gates the sheet.
- Higgsfield/Seedance clips, BLACK LIQUIDITY edits — different failure modes and tools.

## Workflow

1. **Mechanical, zero images.** [ANY] Standing rule, CEO 2026-09-23: *"ต้องเชคตลอด Audit แบบไม่ต้องดูภาพ
   หรือดูให้น้อยที่สุด"* — after every batch, before anything is assembled or uploaded as final, run the
   three free local checks. Frames are opened only for the shots a check has already named.

   | check | tool | catches | cost |
   |---|---|---|---|
   | what the clip **says** | `tools/film_transcript.py` | line said twice, line dropped (banchi sheets only: §Reading the dialogue back), script repeating itself | ~3 s/clip |
   | text **burned into the picture** | `tools/burned_text_scan.py` | Veo writing its own Thai captions, mangled (pixel gate, not OCR) | ~0.4 s/clip |
   | duration / audio present | `tools/clip_review.py` | wrong length, silent clip | fast |

   ```bash
   python3 tools/burned_text_scan.py <act dirs...> --out audit/burned.tsv
   python3 tools/film_transcript.py  <act dirs...> --out audit/transcript.tsv
   ```

   A caption hit or a line count mismatch is a suspect, not a verdict: the transcript
   splits one line into two segments often (a false "extra line"), and whisper spells
   Thai loosely ("ตูลัด" for ตำรวจ). A repeated phrase inside one segment is the real
   repeat signal.

   **Why this is not optional.** On 2026-09-23 the finished film had **3 of 173 shots (29, 43, 115)
   carrying mangled Thai subtitles Veo invented** — «ไม่ใส่ถั่วทอกใช่ไห เวิทย์», «แล้วมูลนนั่ติกินหู้ร้กาอกิทย์» —
   and nobody had asked for subtitles. The CEO found them by watching. **It survives a re-shoot**: shot 43
   was re-fired for this exact defect, with a no-subtitles negative (`NOT["nosubs"]`) and the line
   rewritten as spoken, and captioned on 3 of 3 takes, different garbage in the same place each time
   (scan score 286 on take 3). Neither a re-fire nor the negative is a fix, and every re-fire has to
   be re-scanned.

   **The free fix comes before the paid one.** Veo puts the caption in the bottom ~81–90% of the height,
   below every face. Crop the top 80% of the frame, centred, and scale back up
   (`crop=trunc(iw*0.8/2)*2:trunc(ih*0.8/2)*2:trunc(iw*0.1/2)*2:0,scale=<w>:<h>:flags=lanczos`): the shot
   becomes a slightly tighter close-up, the caption is gone, 0 credits. Re-fire only a shot whose action
   lives in that bottom band (hands on a counter, a phone held low) — and re-scan it after.
2. **Contact sheet per act.** [ANY] 3 frames a shot (≈0.5 s, middle, ≈7 s), ~8 shots an
   image. Look only for what stage 1 cannot see: faces vs the plate, clothes, posture,
   who is in frame, time of day. Put the plate next to the frames when a face is in
   question.

   **Keep the size; nothing in the tools enforces it.** «ตาชั่งของเสี่ย» ACT2 went to the CEO after one
   sheet of 24 clips × 4 tiny frames: it caught S51 (the villain's cream polo turned dark with the
   wardrobe chip attached, so a chip does not make the clothes check optional) but missed S27 wheeling
   the platform scale away as her cart and S40 walking out through a closed car door, both plain on the
   rule-sized sheets — 32 credits of re-shoots after a CEO round instead of before it.

   **The APPEARANCE LOCK is the ground truth, not the neighbouring shot.** When three shots disagree,
   "which one is wrong" is unanswerable by comparing them to each other — there is no reference among
   them. The script's `APPEARANCE LOCK` line for that character IS the reference. Check each shot against
   that text, item by item (apron colour, whether it is over or under the shirt, hair, stubble, watch,
   which wrist), and the answer is a count, not an opinion. This costs nothing and can be run
   retroactively on every clip ever shot.
3. **A pulled clip gets one frame looked at before it counts.** [FLOW] `pull` finds a
   card by its dialogue; a re-shot scene keeps its dialogue, so it fetched the OLD take
   of 149 and 151 and the ledger marked them verified. Use `pull --search <phrase only
   the new prompt has>`. Since 51247830 `run` and `pull` refuse a download byte-identical
   to a take of that shot in a sibling ledger ("DUPLICATE: … the runner fetched an OLD
   card"; taachang S32 was the second case) — a take no ledger holds still needs the frame.
4. **CEO review per act.** 540p (`scale=540:960`, crf 26) files of 8-14 MB go into the
   chat directly; the chat refuses files over 30 MB, so a full 24-min film goes as 4
   parts. Drive is slow to process long 1080p video — the CEO asked for per-act files
   for exactly that reason.
5. **Lock what passes.** A passed act is not re-shot or re-cut again.
6. **Assemble once**, at the end, from clips normalised once (1080×1920, 24 fps,
   AAC 48 k) into `Work/<task>/tmp/norm/`; `ffmpeg -nostdin` inside any `while read`
   loop, or it eats the list.

## Reading the dialogue back — never diagnose audio you have not read back

The rule is `CMO_Knowledge_Film_Production` §8. On Flow: **if a claim is about what a clip SAYS, produce the
transcript first.** `tools/film_transcript.py` does it — faster-whisper, already installed, on the CPU,
~3 seconds a clip, no credits, no network. The whole 173-shot film reads back in ten minutes. There is no
budget excuse for guessing.

**What guessing cost, 2026-09-23.** The only audio signal in use was `silencedetect` — where sound is,
never what it is. Every conclusion built on it was an inference presented as a measurement:

| claim | reality |
|---|---|
| "shot 139 probably repeats a line" | the CEO listened: it is clean |
| "shot 122's repeated number is deliberate, good writing" | it is a man saying "208 งวด" then "208" in four seconds — **the actual defect** |
| "111 shots repeat the speaker block, that is the cause" | the community documents the opposite: the speaker description *should* be restated per line |

On the strength of that reading I rewrote `build_shotsheet.py`, fired five paid proof shots, and picked
all five from a text analysis rather than from anything anyone had heard. The proof shots landed on scenes
that did not have the problem. One transcript of one clip settled it afterwards in three seconds.

**So, before any claim about dialogue:**

1. `python3 tools/film_transcript.py <clip-dir> --out transcript.tsv` — gives
   `shot · t_start · t_end · heard · scripted · match` for every line. **The `scripted` column,
   `match` and every "(ไม่ได้ยิน)" row come from the banchi data files whatever clips you point it
   at** (it reads `docs/scripts/banchi-ACT*.data.py`): on taachang ACT2 every "(ไม่ได้ยิน)" row was a
   banchi line. On any other film read `heard` against the current sheet's `**บทพูด**` lines yourself
   until the tool takes a `--sheet`.
2. **Read the `heard` column against the `scripted` column.** Three different defects fall out, and they
   have three different fixes:
   - heard ≈ scripted, and the script itself says it twice → **the script is wrong**, fix the writing, do
     not touch the prompt.
   - heard repeats something the script says once → **the render is wrong**, re-fire, then look at the
     prompt.
   - a scripted line has nothing heard for it → **a line was dropped**, which no silence-based check can
     see at all.
   - the lines come in a different order → **the action line named the speakers in that order**; fix
     the action (`CMO_Standard_Story_ThaiMoralDrama` §The character acts WHILE speaking, rule 5).
3. Only then reach for a prompt change, and say which of the three you are fixing.

A script can read beautifully on the page and land as a stutter in four seconds of audio. Reading it is
not hearing it. Related: [[judge-craft-by-eye-not-metrics]].

## The caption scan — how it stays cheap (keep these when changing it)

A caption is a **pixel** fact: near-white glyphs beside a near-black outline or box, which texture almost
never has. `burned_text_scan.py` counts exactly that (white > 225 with black < 90 three pixels away, band
scaled to 360×80); real captions scored 160–326, the worst texture 38, the gate is 80. tesseract only
prints what the caption says.

- **crop first**: captions live in the bottom 18%; the other 82% is never read.
- **2 fps, not 4 samples a clip**: the pixel test is cheap enough to sample every half second, and a
  caption lasts as long as a line — 173 clips in ~1 min.
- **no model in the filter**: a pixel count decides. A model is only for the shortlist, and usually the
  shortlist is obvious enough without one.
- **a new detector is calibrated on known positives AND known negatives** before its count is reported
  (rule 1). One contact sheet of the hit strips is the calibration; a count off an uncalibrated detector
  is an estimate, and is labelled one.

## Rules

1. **HARD — Do not report a count from a detector that has not been checked on known
   hits and known misses.** The first caption scan called "tesseract read ≥ 8 Thai characters in the band"
   a caption and reported **14** captioned shots to the CEO before anyone looked. One contact sheet showed
   eleven were a floral nightgown, table grain, an apron and stair treads — tesseract reads Thai out of any
   texture — and it had missed shot 115 because four samples a clip fell between two lines. It was 3.
   OCR is not a caption detector.

   **Why hard:** scope — a number sent to the CEO drives what he approves and pays for
   (14 re-shoots ≈ 170 credits against 3 real ones); a wrong count is a wrong decision
   made on our word.

2. A runner `timeout` is not a verdict: take the census before pulling or re-firing. [FLOW]
   "download not ready" then "failed — timeout" has meant three things: no new clip at all —
   deleted, or a submit that produced nothing (149, 151, 179 on 2026-09-23: nothing to pull; what
   Flow deletes is `CMO_Gate_Flow_Omni1.1_Continuity` §What Flow silently deletes); a finished clip
   the runner opened too early (S58 and one S70 on 2026-09-26: `flow_shoot.py pull` it); or the OLD
   take of a re-shot scene (Workflow 3). The census: search the feed for the shot's dialogue and
   compare the batches found with the submits sent (`CMO_Knowledge_Flow_Omni1.1` §A clip that will
   not come down). [SUPERSEDED 2026-09-28: "A vanished clip is Flow deleting it, not the runner
   failing" — S58/S70 timed out and were finished in the feed (99770187).]

3. Look to confirm, not to find (`CMO_Knowledge_Film_Production` §8). [ANY] On banchi, finding the 3 captioned
   shots took one strip image after the pixel scan; a frame-by-frame look at 186 clips would have cost
   ~150× more for the same answer.

4. What this loop still misses — say so in every report. [ANY] None of the stage-1 checks can see the
   wrong person in frame, wrong wardrobe, a prop that should not be there, a character lying down who
   should be sitting; those still need eyes, so keep the eyes for exactly those questions. Faces, clothes
   and posture are judged by eye on a sampled frame; the CEO still caught 106 (hair), 149/151
   (the father's face on the officer) and 171 (ต้น lying on the bed) after our checks. A
   local face-match (plate embedding vs each shot's faces) and a "person lying on a bed"
   flag are the next tools to build; until then, a clean QC report is "no defect found
   by stages 1-2", not "no defect".

5. A wrong voice or mouth on a two-speaker shot is fixed by splitting it, not by re-firing it.
   [FLOW] (CEO ruling 2026-09-28.) A take whose first speaker's line lands in the listener's voice
   or mouth goes straight to `CMO_Gate_Flow_Omni1.1_Continuity` rule 10: fire Na (that line alone) and Nb (the reply alone)
   once each. Do not run another take of the combined shot to "see if it holds": ep4 shot 21 stayed
   wrong in 3 production re-fires and in 11 of 18 test takes of the combined shot (as written, with
   changed direction words, or at 10 s).

6. **Read facing and direction against the prompt, by eye, on the contact-sheet strip.** [ANY] (CEO 2026-10-01.) For each
   sampled frame ask three things the prompt wrote down (`CMO_Standard_Film_PromptFormat` §3 rule 12): does the
   speaker face the way it says (toward/away, left/right), do the eyes go to the addressee rather than the lens, and
   does the movement go the way it says (a leap away from the camera, an exit to the right). The mechanical audit cannot
   see any of this and a clean transcript proves nothing about it. A frame that glances at the camera once is a
   note in the report, not a re-shoot, unless the CEO says so; a wrong direction is a re-shoot.

## Output format

```
ACT 6 — 29 shots
stage 1: transcript 29/29 lines match · caption scan 0/29 · durations ok
stage 2: contact sheet 4 images — 149 officer face ✅ (vs @cop_wit), 150 father apron ✅, 187 night ✅
stage 3: ACT6-review-540p.mp4 (13 MB) sent — waiting for CEO
not checked mechanically: faces/clothes/posture outside the sampled frames
```

## Reference

- Tools: `tools/film_transcript.py`, `tools/burned_text_scan.py`, `tools/clip_review.py`,
  `tools/flow_shoot.py pull --search`
- Evidence: `docs/scripts/banchi-RETRO.md`; memory `reference_cheap_film_audit.md`
- Platform: `CMO_Knowledge_Flow_Omni1.1` · pre-shoot: `CMO_Gate_Flow_Omni1.1_Continuity` · story: `CMO_Standard_Story_ThaiMoralDrama`

## Field notes

- 2026-09-23 [WRONG] §Reading the dialogue back (was google-flow-ops §Never diagnose audio you have not read back) — spent an evening attributing a dialogue defect to prompt structure using `silencedetect` (where sound is, not what it is). Rewrote the sheet builder, fired five paid proof shots chosen from a text analysis, and contradicted the published Veo guidance, all before transcribing a single clip. faster-whisper was already installed: 3s per clip settled it. The real defect was the script telling a character to say "208 งวด" then "208" in a four-second shot. · evidence: research/veo-dialogue-repeats.md / tools/film_transcript.py · status: promoted
- 2026-09-23 [SUPERSEDED] §Workflow 1 (was google-flow-ops §Every shoot ends with a mechanical audit) — (was MISSING; the count was 3 not 14, see the WRONG note below) 14 of 173 finished shots carried Thai captions Veo invented and mangled; found by the CEO watching, not by any check. A crop-and-OCR scan (bottom 18%, 4 frames a clip, tesseract) found all 14 in two minutes. Shot 43 had already been re-fired for this defect and came back with different garbage, so re-fires need re-scanning. · evidence: tools/burned_text_scan.py · status: promoted
- 2026-09-23 [WRONG] §Workflow 1 / rule 1 (was google-flow-ops §Every shoot ends with a mechanical audit) — the OCR scan's "14 of 173" was 3 of 173 (29, 43, 115): 11 hits were texture (floral nightgown, table grain, apron, stair treads) and 115 was missed by 4-samples-a-clip. Replaced by a pixel gate (white glyph beside black outline, 360×80 band, 2 fps; real 160–326 vs texture ≤38, gate 80), calibrated on one contact sheet of known hits. Free fix: crop top 80% and scale back — 0 credits instead of ~180 for re-fires. · evidence: session cto-8c06958c, tools/burned_text_scan.py · status: promoted
- 2026-09-23 [WRONG] §Workflow 1 (was google-flow-ops §Every shoot ends with a mechanical audit) — NOT["nosubs"] ("No subtitles, no captions…") + rewriting the line as spoken aloud did NOT stop shot 43 captioning: 3 of 3 takes captioned. It held on 29 and 115 (n=2 clean), so the negative is not a fix for a shot that keeps doing it — crop it (0 cr) after the second captioned take instead of paying for a third. · evidence: session cto-8c06958c, ACT2 43 take 3 04:0x, burned_text_scan score 286 → §Workflow 1 "It survives a re-shoot" (the negative named; crop-before-re-fire was already the body's order) · status: promoted
- 2026-09-23 [WRONG] §Workflow 3 (was google-flow-ops §zero-model runner) — `pull` finds a clip by its dialogue, but a re-shoot keeps its dialogue: 149 and 151 came down as the OLD plainclothes takes and the ledger marked them verified. Caught only by a frame check (uniform vs polo). Every pull of a re-shot scene needs --search <a phrase only the new prompt has> (added on agent/codex-winbox-runner), and every pulled clip gets one frame looked at before it counts. · evidence: session cto-8c06958c, ACT6 149/151 05:12/05:27 → §Workflow 3 (second run: taachang S32, 2026-09-26; the DUPLICATE guard 51247830 now named there) · status: promoted
- 2026-09-23 [WRONG] §Rules 2 (was google-flow-ops §zero-model runner) — "completed card found but download not ready" ×7 then "failed — timeout" meant NO new clip existed: 149 (re-shoot), 151 and 179 ×2 left no card in the feed at all (read-only feed listing 05:45). The completion check takes the FIRST element carrying the shot's dialogue, which for a re-shot scene is the OLD finished card, and for a shot whose submit silently produced nothing is whatever else matches — so a submit that failed reads as done-but-undownloadable. Fix owed in flow_shoot: count batches before Submit and only accept a card in a batch that did not exist before. Until then: a 'timeout' is not evidence of a paid clip; list the newest feed batches before pulling or re-firing. · evidence: session cto-8c06958c, ACT6 149/151/179 04:38–05:36 → §Rules 2 (merged with the 2026-09-28 note: a timeout is not a verdict either way, take the census) · status: promoted
- 2026-09-23 [MISSING] §Workflow 1 (was google-flow-ops §Every shoot ends with a mechanical audit) — shot 43 captioned on 3 of 3 takes at 6s (10.5 Thai chars/s, 2nd-fastest line in the film); lengthened to 8s with nothing else changed, take 4 came back clean on the pixel scan. n=1, and shot 16 is as fast and was always clean, so this is a lever to try before a crop, not a rule. · evidence: session cto-8c06958c, ACT2 43 take 4 (e29dc06e) · status: pending
- 2026-09-26 [WRONG] §Reading the dialogue back — `tools/film_transcript.py`'s `scripted` column and its "(ไม่ได้ยิน)" rows come from the **banchi** sheet data, whatever clips you point it at: on taachang ACT2 every "(ไม่ได้ยิน)" row was a banchi line, not a missing taachang one. Compare `heard` against the current sheet's `**บทพูด**` lines yourself (one awk over the .md) until the tool takes `--sheet` · evidence: Work/task-c2723478/out/qc-act2-transcript.tsv, tools/film_transcript.py scripted_lines() (hard-coded banchi-ACT*.data.py) → §Reading the dialogue back step 1, §Workflow 1 table · status: promoted
- 2026-09-26 [MISSING] §Reading the dialogue back — **Flow speaks in the ACTION line's order, not the dialogue block's.** S37's dialogue had the grandmother first, but the action said "the boy stares at the pebble …; the old woman answers" — the take had his line first (small and medium whisper agreed). Rewriting the action to "the old woman speaks first …; only after she has finished, the boy …" fixed it on the next take. Check that the action names speakers in the same order as the lines · evidence: ACT2 S37 take 1 vs ACT2-reshoot/shot-37.mp4, commit 558ed6fa → CMO_Standard_Story_ThaiMoralDrama §The character acts WHILE speaking rule 5 (the writing rule; that section's 2026-09-19 banchi measurement is the second run: the model plays the action line in its written order) + §Reading the dialogue back step 2 (the diagnosis) · status: promoted
- 2026-09-26 [MISSING] §Workflow 1 — wardrobe drift with the wardrobe chip attached: S51 rendered the villain in a dark shirt while 50/52/53 (same chips) kept the cream polo; a plain re-fire fixed it. A 4-frame strip per clip tiled into one sheet (24 clips, one look) is what caught it; the transcript cannot · evidence: sheets-act2/_sheet.jpg, ACT2-reshoot/shot-51.mp4 → §Workflow 2 "Keep the size" (a wardrobe chip does not make the clothes check optional; stage 1 cannot see clothes was already rule 4) · status: promoted
- 2026-09-26 [WRONG] §Rules 2 — the 2026-09-23 "pull fetches the OLD take of a re-shoot" hit `run` too: taachang S32 re-fired onto ACT2-reshoot.tsv read "verified" 9 s after Submit, byte-identical to ACT2/shot-32.mp4 (20 credits paid, the new clip left in Flow; `pull` into a fresh ledger fetched it). Second independent run, so the rule went into the tool, not this file: flow_shoot run/pull now refuse a download whose sha256 matches any take of that shot in a sibling *.tsv ("failed — DUPLICATE … pull --search, do not re-fire") · evidence: commit 51247830, tests test_rerun_that_downloads_an_earlier_take_is_refused / _with_a_new_take_is_verified (rule lives in the tool) · status: promoted
- 2026-09-26 [COSTLY] §Workflow 2 — ACT2's review went to the CEO after ONE sheet of 24 clips × 4 tiny frames (1600×820 for the whole act) instead of the rule's 3 frames a shot, ~8 shots an image. It caught the wardrobe drift (S51) but not the two defects the CEO then found by watching: S27 wheeling the platform SCALE away as her cart, S40 walking out through a closed car door. On the rule-sized sheets (sheets-act2-qc/sheet-a.jpg) S27's scale-as-cart is plainly visible in frames 2-3. The cost: two paid re-shoots (32 credits) after a CEO review round instead of before it. Nothing in the tool enforces the sheet size · evidence: Work/task-c2723478/out/sheets-act2/_sheet.jpg vs sheets-act2-qc/sheet-a.jpg, re-shoots ACT2-reshoot/shot-27, shot-40 → §Workflow 2 "Keep the size" (the two sheets of one act are the artefact: the rule's size shows what the small one missed) · status: promoted
- 2026-09-28 [WRONG] §Rules 2 — "a vanished clip is Flow deleting it" is not always true: on 2026-09-26 S58 and one S70 timed out but were finished in the feed (the runner opened the clip editor too early); tell a deletion from a missed download by searching the feed for the shot's dialogue and comparing batches found with submits sent · evidence: 99770187, CMO_Knowledge_Flow_Omni1.1 09-26 note → §Rules 2 (rewritten; old line kept [SUPERSEDED]; the 2026-09-23 timeout note merged here) · status: promoted
- 2026-09-27 [MISSING] §Workflow 1 — `burned_text_scan.py` scored 88 (over the 80 gate) on ep4 ACT1 S20, where no text exists: the dense white stitching and checked pattern on an indigo blouse read as glyph rows. It is a suspect until a frame is looked at; patterned Isan cloth (pha khao ma, mudmee) is the likely false-positive source on this film · evidence: task-c816fbc0 audit/burned-ACT1.tsv S20 · status: pending
- 2026-09-27 [MISSING] §Reading the dialogue back — nothing checks WHICH mouth speaks a line. The CEO watched ep4 and found part of a line scripted for the mother coming out of the son's mouth. `film_transcript.py` reads the words and an f0 check reads the voice's pitch; neither sees lips. Candidate check: per-line active-speaker detection (Light-ASD, local, free) joined to whisper word times and per-line f0, calibrated against the CEO's known cases by eye before it becomes a rule · evidence: task-c816fbc0, CEO report 2026-09-27 · status: pending
- 2026-09-27 [MISSING] §Reading the dialogue back — first measurement of the wrong-mouth check on ep4 (72 shots, 112 lines): Light-ASD + whisper word times + face id flagged 16 lines; an eye check of one contact sheet per flag (subagent, text answer) confirmed 8, so the checker is a SCREEN at 50% precision, not a verdict. Its false alarms are listeners sobbing, grinning or gasping; pitch is not identity (a crying son's voice rose into the mother's range). The cause seen in every confirmed case: the scripted speaker's mouth is not visible, usually because Flow CUT inside the 8 s clip to a close-up of the listener while the line kept running, and lip-synced the line onto that face. 45/72 clips carry an in-clip cut; lines that span a cut went wrong 6/42 (14%) vs 2/70 (3%) without. No ep4 prompt says "one continuous take". Candidate rule pending the A/B: ask for one continuous take with no cuts in every dialogue shot · evidence: task-c816fbc0, asd/scan/verdict.tsv, scratchpad eyecases.tsv · status: pending
- 2026-09-28 [MISSING] §Reading the dialogue back — **a wrong-mouth line can be caught by pitch alone.** Median f0 of the flagged phrase against the median of each actor's own line (female ~200 Hz, male ~140 Hz; drop readings outside 80–320 Hz, whisper doubles final stops to ~390) agreed with a blind eye judge on 20/21 clips of ep4 shot 21, where Light-ASD at 360p gave one-bin CHECKs that could not separate cases. Screen = pitch, eye confirms · evidence: task-c816fbc0, scratchpad ab/s21_score.py voice · status: pending
- 2026-09-28 [WRONG] §blind eye (the pitch-screen note above calls the eye the confirmer) — on 720p clips scaled to 360 px strips, the blind judge called the woman's profile mouth "closed/still" in both 21a strips while she was visibly shaping words, and it read the son's crying grimace as speech (a1 = MAN, a2 = UNSURE). The voice screen, Light-ASD and my own look all said the mother. Both controls in the same batch were judged right (K3 MAN, S1 WOMAN), so the controls did not catch it. Give the judge the full-width crop (no `scale=360`), and tell it a crying mouth with corners down is not speech. When the judge and the pitch screen disagree, the CEO's eye decides, not a vote · evidence: task-c816fbc0, scratchpad ab/eye21X_verdict.tsv + eye_keyX.tsv · status: pending
- 2026-09-28 [MISSING] §Rules 5 — CEO ruling "ใช้ 21a ก่อนเสมอ เมื่อเจอปัญหา แล้ว แก้ด้วย 21b ทันที จะได้ไม่ต้องยิงซ้ำหลายรอบ": a wrong voice or mouth on a two-speaker shot goes straight to the split (the Continuity skill rule 10), not another take. ep4 shot 21: the combined shot was wrong in 11 of 18 test takes; the split was clean 4/4 · evidence: task-c816fbc0, credit-ledger 42a04524 · status: promoted
- 2026-10-01 [WRONG] §Reading the dialogue back - 'faster-whisper is not installed on Contabo, so no free transcript there' was false: `python3 -m venv V && V/bin/pip install faster-whisper` takes about a minute on Contabo, the `small` model loads in 4 s and reads an 8 s Thai clip in a few seconds on CPU. One trap: handing it a file path dies with `TypeError: open() got an unexpected keyword argument 'metadata_errors'` (PyAV version mismatch) - decode with `ffmpeg -i clip -vn -ac 1 -ar 16000 -f f32le -` into a numpy array and pass the array, `language='th'`. Do not route a transcript to winbox (pwvenv has none) or wait for the Mac · evidence: EP1 test clips 2026-10-01, transcript matched the written lines · fix: Contabo can run the read-back itself · status: pending
- 2026-10-01 [MISSING] §Reading the dialogue back - the pitch screen works with a 20-line numpy autocorrelation, no extra library: 40 ms windows, skip quiet frames (RMS < 0.02), search 70-450 Hz, keep peaks > 0.5. Read on EP1: a talking dog 377 Hz median, the 55-year-old seller 208 Hz - the seller is above the ~140 Hz male figure in this skill, so either a crude-autocorrelation octave slip or Flow gave him a high voice; cannot tell without listening, so a speaker whose f0 sits far from their cast norm is a flag for a human ear, not a verdict · evidence: ep1test/bad-shot-01.mp4 vs -10.mp4 · status: pending (n=1)
- 2026-10-01 [WRONG] §stage 1 burned-text scan + "free fix" — "Veo puts the caption in the bottom ~81-90 %, crop the top 80 %" and "scan clean = a checked answer" did not hold on Omni 1.1: EP1 shot 6 (720p) carried a correctly spelled Thai caption («น้ำน่ากลัวมากเลย») at 15-45 % of the height, in a prompt that already had the no-subtitles negative; `burned_text_scan.py` reads only the 78-96 % band and printed "0 of 18 clips ... clean". Found only because the act strip was looked at (5 frames/clip at 150 px was enough: the text showed on 3 of 5). A full-frame score is no substitute: 6 clean clips scored 200-409 (windows, white shirt on dark suit) against 349 for the real caption, so it names candidates and eyes decide. Free fix that worked (locked-off camera, text above the subject): `tools/film_caption_patch.py` (background plate = median of the clip's own frames) - top-band score 349 -> 0, caption gone on both frames checked; crop does not help for mid-frame text. A re-fire is 15 credits and a caption survived re-fires in the 09-23 case · evidence: EP1 prod.tsv shot 6, winbox clips_prod shot-06.mp4 + shot-06-patched.mp4, scratchpad fullband.py · status: pending
- 2026-10-01 [MISSING] §stage 2 contact sheet - EP1 by-eye pass over all 18 clips found 2 real defects the transcript and the scan could not: S8's dog came back a short-coated black-and-tan dog with prick ears (not Mimi's drop ears / silver beard), and S17's towel was beige where S14 and S16 had pink. Method that was enough: 2 shots per image, 5 frames each (t = 0.5, 2.5 ... 8.5 s) at 216 px wide = 9 images for 18 shots, with the shot's framing/chip line printed beside it and the plate opened once for the identity call. Fix: one re-fire each, same chips, 15 credits each at 720p; both came back right on the first re-fire (S8 dog = Mimi, S17 towel pink), no caption. The prompt edit was tiny (S8 dropped 'the gate at screen-right', S17 named 'the same pink towel') and S8's gate STILL appeared, so the edit did not cause the fix: treat the S8 result as re-roll variance, not as a proven prompt rule · evidence: EP1 rs1.tsv (winbox), scratchpad pairs/ + rs1/check.jpg, credit-ledger b80d400c · status: pending
- 2026-10-01 [COSTLY] §stage 2 (tooling) - `ffmpeg -filter_complex vstack` with three inputs and no `inputs=3` stacks only the first two and exits 0: my 3-row check image came out 2 rows tall and I only noticed from the ffprobe height (768, not 1152). prevented by: always pass `vstack=inputs=N` / `hstack=inputs=N` and read back the output height · evidence: scratchpad rs1/check.jpg first build · status: pending
- 2026-10-01 [MISSING] §stage 1 audio - a clip can end in an empty room: EP1 S5 (chase) has its line end at 8.4 s and both characters out of frame from ~8.5 s, with 1.5 s of footsteps after. Free fix is a trim in the assembly (`-t 8.9`, 0.3 s audio fade), after checking the last word's end time with whisper word timestamps; the trim moves every later timestamp, so a mid-roll marker at 1:00 has to be re-derived from the new cumulative length · evidence: prod shot-05.mp4, EP1-roughcut-v1 · status: pending
