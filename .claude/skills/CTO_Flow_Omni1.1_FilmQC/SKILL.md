---
name: CTO_Flow_Omni1.1_FilmQC
description: >-
  Quality control for an AI film shot in Google Flow (Omni 1.1 Flash): the per-act
  loop that found every defect of «จุดจบของเจ้าหนี้นอกระบบ» cheaply — mechanical
  audit with zero images (transcript, pixel caption scan, duration), reading the
  dialogue back before any claim about it, one contact sheet per act for
  faces/clothes/posture, a 540p file per act for the CEO, lock what passes,
  assemble once. Trigger on /CTO_Flow_Omni1.1_FilmQC and proactively
  after any Flow shoot or re-shoot — 'ตรวจคลิป', 'audit the film', 'check the
  shots', 'ส่งให้ดูทีละองก์', 'ประหยัด token ตรวจภาพ', 'ซับขึ้น', 'พูดซ้ำ', 'หน้าเพี้ยน',
  or before assembling a cut. Do NOT fire for Higgsfield/Seedance clip review (its
  failure modes differ) or for editing a BLACK LIQUIDITY episode (blackliquidity-cut).
created_by: agent
author: {role: cto, date: "2026-09-23"}
audience: [cto, browser_operator, video_editor, tester]
---

# Film QC — Google Flow · Omni 1.1 Flash

## Model scope

Read `CTO_Flow_Omni1.1_Ops` §Model scope first: what "proven on" means and the [ANY] / [FLOW] tags.
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

- Before shooting — `CTO_Flow_Omni1.1_Continuity` gates the sheet.
- Higgsfield/Seedance clips, BLACK LIQUIDITY edits — different failure modes and tools.

## Workflow

1. **Mechanical, zero images.** [ANY] Standing rule, CEO 2026-09-23: *"ต้องเชคตลอด Audit แบบไม่ต้องดูภาพ
   หรือดูให้น้อยที่สุด"* — after every batch, before anything is assembled or uploaded as final, run the
   three free local checks. Frames are opened only for the shots a check has already named.

   | check | tool | catches | cost |
   |---|---|---|---|
   | what the clip **says** | `tools/film_transcript.py` | line said twice, line dropped, script repeating itself | ~3 s/clip |
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
   was re-fired for this exact defect and came back with different garbage in the same place, so a
   re-fire alone is not a fix and every re-fire has to be re-scanned.

   **The free fix comes before the paid one.** Veo puts the caption in the bottom ~81–90% of the height,
   below every face. Crop the top 80% of the frame, centred, and scale back up
   (`crop=trunc(iw*0.8/2)*2:trunc(ih*0.8/2)*2:trunc(iw*0.1/2)*2:0,scale=<w>:<h>:flags=lanczos`): the shot
   becomes a slightly tighter close-up, the caption is gone, 0 credits. Re-fire only a shot whose action
   lives in that bottom band (hands on a counter, a phone held low) — and re-scan it after.
2. **Contact sheet per act.** [ANY] 3 frames a shot (≈0.5 s, middle, ≈7 s), ~8 shots an
   image. Look only for what stage 1 cannot see: faces vs the plate, clothes, posture,
   who is in frame, time of day. Put the plate next to the frames when a face is in
   question.

   **The APPEARANCE LOCK is the ground truth, not the neighbouring shot.** When three shots disagree,
   "which one is wrong" is unanswerable by comparing them to each other — there is no reference among
   them. The script's `APPEARANCE LOCK` line for that character IS the reference. Check each shot against
   that text, item by item (apron colour, whether it is over or under the shirt, hair, stubble, watch,
   which wrist), and the answer is a count, not an opinion. This costs nothing and can be run
   retroactively on every clip ever shot.
3. **A pulled clip gets one frame looked at before it counts.** [FLOW] `pull` finds a
   card by its dialogue; a re-shot scene keeps its dialogue, so it fetched the OLD take
   of 149 and 151 and the ledger marked them verified. Use `pull --search <phrase only
   the new prompt has>`.
4. **CEO review per act.** 540p (`scale=540:960`, crf 26) files of 8-14 MB go into the
   chat directly; the chat refuses files over 30 MB, so a full 24-min film goes as 4
   parts. Drive is slow to process long 1080p video — the CEO asked for per-act files
   for exactly that reason.
5. **Lock what passes.** A passed act is not re-shot or re-cut again.
6. **Assemble once**, at the end, from clips normalised once (1080×1920, 24 fps,
   AAC 48 k) into `Work/<task>/tmp/norm/`; `ffmpeg -nostdin` inside any `while read`
   loop, or it eats the list.

## Reading the dialogue back — never diagnose audio you have not read back

The rule is `CTO_Film_Production` §8. On Flow: **if a claim is about what a clip SAYS, produce the
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
   `shot · t_start · t_end · heard · scripted · match` for every line.
2. **Read the `heard` column against the `scripted` column.** Three different defects fall out, and they
   have three different fixes:
   - heard ≈ scripted, and the script itself says it twice → **the script is wrong**, fix the writing, do
     not touch the prompt.
   - heard repeats something the script says once → **the render is wrong**, re-fire, then look at the
     prompt.
   - a scripted line has nothing heard for it → **a line was dropped**, which no silence-based check can
     see at all.
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

2. A vanished clip is Flow deleting it, not the runner failing. [FLOW] "new card found
   but download not ready" then `timeout`, and the batch is gone from the feed: read the
   newest feed batches before re-firing. What Flow deletes is in `CTO_Flow_Omni1.1_Continuity`
   §What Flow silently deletes.

3. Look to confirm, not to find (`CTO_Film_Production` §8). [ANY] On banchi, finding the 3 captioned
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
- Platform: `CTO_Flow_Omni1.1_Ops` · pre-shoot: `CTO_Flow_Omni1.1_Continuity` · story: `CTO_Story_ThaiMoralDrama`

## Field notes

- 2026-09-23 [WRONG] §Reading the dialogue back (was google-flow-ops §Never diagnose audio you have not read back) — spent an evening attributing a dialogue defect to prompt structure using `silencedetect` (where sound is, not what it is). Rewrote the sheet builder, fired five paid proof shots chosen from a text analysis, and contradicted the published Veo guidance, all before transcribing a single clip. faster-whisper was already installed: 3s per clip settled it. The real defect was the script telling a character to say "208 งวด" then "208" in a four-second shot. · evidence: research/veo-dialogue-repeats.md / tools/film_transcript.py · status: promoted
- 2026-09-23 [SUPERSEDED] §Workflow 1 (was google-flow-ops §Every shoot ends with a mechanical audit) — (was MISSING; the count was 3 not 14, see the WRONG note below) 14 of 173 finished shots carried Thai captions Veo invented and mangled; found by the CEO watching, not by any check. A crop-and-OCR scan (bottom 18%, 4 frames a clip, tesseract) found all 14 in two minutes. Shot 43 had already been re-fired for this defect and came back with different garbage, so re-fires need re-scanning. · evidence: tools/burned_text_scan.py · status: promoted
- 2026-09-23 [WRONG] §Workflow 1 / rule 1 (was google-flow-ops §Every shoot ends with a mechanical audit) — the OCR scan's "14 of 173" was 3 of 173 (29, 43, 115): 11 hits were texture (floral nightgown, table grain, apron, stair treads) and 115 was missed by 4-samples-a-clip. Replaced by a pixel gate (white glyph beside black outline, 360×80 band, 2 fps; real 160–326 vs texture ≤38, gate 80), calibrated on one contact sheet of known hits. Free fix: crop top 80% and scale back — 0 credits instead of ~180 for re-fires. · evidence: session cto-8c06958c, tools/burned_text_scan.py · status: promoted
- 2026-09-23 [WRONG] §Workflow 1 (was google-flow-ops §Every shoot ends with a mechanical audit) — NOT["nosubs"] ("No subtitles, no captions…") + rewriting the line as spoken aloud did NOT stop shot 43 captioning: 3 of 3 takes captioned. It held on 29 and 115 (n=2 clean), so the negative is not a fix for a shot that keeps doing it — crop it (0 cr) after the second captioned take instead of paying for a third. · evidence: session cto-8c06958c, ACT2 43 take 3 04:0x, burned_text_scan score 286 · status: pending
- 2026-09-23 [WRONG] §Workflow 3 (was google-flow-ops §zero-model runner) — `pull` finds a clip by its dialogue, but a re-shoot keeps its dialogue: 149 and 151 came down as the OLD plainclothes takes and the ledger marked them verified. Caught only by a frame check (uniform vs polo). Every pull of a re-shot scene needs --search <a phrase only the new prompt has> (added on agent/codex-winbox-runner), and every pulled clip gets one frame looked at before it counts. · evidence: session cto-8c06958c, ACT6 149/151 05:12/05:27 · status: pending
- 2026-09-23 [WRONG] §Rules 2 (was google-flow-ops §zero-model runner) — "completed card found but download not ready" ×7 then "failed — timeout" meant NO new clip existed: 149 (re-shoot), 151 and 179 ×2 left no card in the feed at all (read-only feed listing 05:45). The completion check takes the FIRST element carrying the shot's dialogue, which for a re-shot scene is the OLD finished card, and for a shot whose submit silently produced nothing is whatever else matches — so a submit that failed reads as done-but-undownloadable. Fix owed in flow_shoot: count batches before Submit and only accept a card in a batch that did not exist before. Until then: a 'timeout' is not evidence of a paid clip; list the newest feed batches before pulling or re-firing. · evidence: session cto-8c06958c, ACT6 149/151/179 04:38–05:36 · status: pending
- 2026-09-23 [MISSING] §Workflow 1 (was google-flow-ops §Every shoot ends with a mechanical audit) — shot 43 captioned on 3 of 3 takes at 6s (10.5 Thai chars/s, 2nd-fastest line in the film); lengthened to 8s with nothing else changed, take 4 came back clean on the pixel scan. n=1, and shot 16 is as fast and was always clean, so this is a lever to try before a crop, not a rule. · evidence: session cto-8c06958c, ACT2 43 take 4 (e29dc06e) · status: pending
- 2026-09-26 [WRONG] §Reading the dialogue back — `tools/film_transcript.py`'s `scripted` column and its "(ไม่ได้ยิน)" rows come from the **banchi** sheet data, whatever clips you point it at: on taachang ACT2 every "(ไม่ได้ยิน)" row was a banchi line, not a missing taachang one. Compare `heard` against the current sheet's `**บทพูด**` lines yourself (one awk over the .md) until the tool takes `--sheet` · evidence: Work/task-c2723478/out/qc-act2-transcript.tsv · status: pending
- 2026-09-26 [MISSING] §Reading the dialogue back — **Flow speaks in the ACTION line's order, not the dialogue block's.** S37's dialogue had the grandmother first, but the action said "the boy stares at the pebble …; the old woman answers" — the take had his line first (small and medium whisper agreed). Rewriting the action to "the old woman speaks first …; only after she has finished, the boy …" fixed it on the next take. Check that the action names speakers in the same order as the lines · evidence: ACT2 S37 take 1 vs ACT2-reshoot/shot-37.mp4, commit 558ed6fa · status: pending
- 2026-09-26 [MISSING] §Workflow 1 — wardrobe drift with the wardrobe chip attached: S51 rendered the villain in a dark shirt while 50/52/53 (same chips) kept the cream polo; a plain re-fire fixed it. A 4-frame strip per clip tiled into one sheet (24 clips, one look) is what caught it; the transcript cannot · evidence: sheets-act2/_sheet.jpg, ACT2-reshoot/shot-51.mp4 · status: pending
- 2026-09-26 [WRONG] §Rules 2 — the 2026-09-23 "pull fetches the OLD take of a re-shoot" hit `run` too: taachang S32 re-fired onto ACT2-reshoot.tsv read "verified" 9 s after Submit, byte-identical to ACT2/shot-32.mp4 (20 credits paid, the new clip left in Flow; `pull` into a fresh ledger fetched it). Second independent run, so the rule went into the tool, not this file: flow_shoot run/pull now refuse a download whose sha256 matches any take of that shot in a sibling *.tsv ("failed — DUPLICATE … pull --search, do not re-fire") · evidence: commit 51247830, tests test_rerun_that_downloads_an_earlier_take_is_refused / _with_a_new_take_is_verified (rule lives in the tool) · status: promoted
