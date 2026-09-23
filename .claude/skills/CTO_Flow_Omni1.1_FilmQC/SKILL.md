---
name: CTO_Flow_Omni1.1_FilmQC
description: >-
  Quality control for an AI film shot in Google Flow (Omni 1.1 Flash): the per-act
  loop that found every defect of «จุดจบของเจ้าหนี้นอกระบบ» cheaply — mechanical
  audit with zero images (transcript, pixel caption scan, duration), one contact
  sheet per act for faces/clothes/posture, a 540p file per act for the CEO, lock
  what passes, assemble once. Trigger on /CTO_Flow_Omni1.1_FilmQC and proactively
  after any Flow shoot or re-shoot — 'ตรวจคลิป', 'audit the film', 'check the
  shots', 'ส่งให้ดูทีละองก์', 'ประหยัด token ตรวจภาพ', 'ซับขึ้น', 'พูดซ้ำ', 'หน้าเพี้ยน',
  or before assembling a cut. Do NOT fire for Higgsfield/Seedance clip review (its
  failure modes differ) or for editing a BLACK LIQUIDITY episode (blackliquidity-cut).
created_by: agent
author: {role: cto, date: "2026-09-23"}
audience: [cto, browser_operator, video_editor, tester]
---

# Film QC — Google Flow · Omni 1.1 Flash

## Model scope — read this first (CEO 2026-09-23)

**Proven on:** Google Flow · **Omni 1.1 Flash** (Veo 3.1 family) · องค์ประกอบ mode ·
720p 9:16 · Thai dialogue generated in-clip · «จุดจบของเจ้าหนี้นอกระบบ», 186 shots.

| tag | meaning |
|---|---|
| **[ANY]** | the loop and the tools work on any clip from any generator |
| **[FLOW]** | a failure mode measured on Omni 1.1 Flash — on Seedance/Kling/Grok it may not exist, or look different |

The tools themselves (`film_transcript.py`, `burned_text_scan.py`, ffmpeg contact
sheets) are generator-agnostic [ANY]. What they are *looking for* — burned Thai
captions, a line said twice, a REF_1 face drifting, a clip that vanished from the
feed — are Omni 1.1 Flash habits [FLOW]. On Seedance, calibrate the scan's GATE and
re-learn the defect list before trusting a clean report.

## What it does

A four-stage loop per act, cheapest first, so eyes (and image tokens) are spent only
where a cheaper check cannot see:

| stage | tool | images | cost | sees |
|---|---|---|---|---|
| 1. mechanical | `tools/film_transcript.py`, `tools/burned_text_scan.py`, ffprobe duration | 0 | ~3 s + 0.4 s a clip, free | a line missing, said twice, a caption burned in, wrong length |
| 2. contact sheet | ffmpeg, 3 frames a shot, ~8 shots an image | 1 per ~8 shots | one image read | wrong face, wrong clothes, someone lying down, wrong person in frame, day/night |
| 3. CEO review | 540p file per act (8-14 MB) sent into the chat | 0 for us | the CEO's time | taste, pacing, anything we missed |
| 4. lock + assemble | concat of already-normalised clips | 0 | 2 min | — |

## When to invoke

- Right after a `flow_shoot.py run` or `pull` finishes — before anything is uploaded as current or assembled.
- The CEO reports "ซับขึ้น", "พูดซ้ำ", "หน้าเพี้ยน", "ชุดเปลี่ยน", or a timestamp in the cut.
- Before a full assembly.

## When NOT to invoke

- Before shooting — `CTO_Flow_Omni1.1_Continuity` gates the sheet.
- Higgsfield/Seedance clips, BLACK LIQUIDITY edits — different failure modes and tools.

## Workflow

1. **Mechanical, zero images.** [ANY]
   `python3 tools/film_transcript.py <dir>` and `python3 tools/burned_text_scan.py <dir>`.
   A caption hit or a line count mismatch is a suspect, not a verdict: the transcript
   splits one line into two segments often (a false "extra line"), and whisper spells
   Thai loosely ("ตูลัด" for ตำรวจ). A repeated phrase inside one segment is the real
   repeat signal.
2. **Contact sheet per act.** [ANY] 3 frames a shot (≈0.5 s, middle, ≈7 s), ~8 shots an
   image. Look only for what stage 1 cannot see: faces vs the plate, clothes, posture,
   who is in frame, time of day. Put the plate next to the frames when a face is in
   question.
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

## Rules

1. **HARD — Do not report a count from a detector that has not been checked on known
   hits and known misses.** The first caption scan (OCR) reported 14 captioned shots to
   the CEO; one contact sheet showed 11 were fabric and wood grain — it was 3.

   **Why hard:** scope — a number sent to the CEO drives what he approves and pays for
   (14 re-shoots ≈ 170 credits against 3 real ones); a wrong count is a wrong decision
   made on our word.

2. A vanished clip is Flow deleting it, not the runner failing. [FLOW] "new card found
   but download not ready" then `timeout`, and the batch is gone from the feed: read the
   newest feed batches before re-firing. What Flow deletes is in `google-flow-ops`.

3. Look to confirm, not to find. [ANY] Images are for the shortlist stage 1 cannot
   judge. Finding the 3 captioned shots took one strip image after the pixel scan; a
   frame-by-frame look at 186 clips would have cost ~150× more for the same answer.

4. What this loop still misses — say so in every report. [ANY] Faces, clothes and
   posture are judged by eye on a sampled frame; the CEO still caught 106 (hair), 149/151
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

- Tools: `tools/film_transcript.py`, `tools/burned_text_scan.py`, `tools/flow_shoot.py pull --search`
- Evidence: `docs/scripts/banchi-RETRO.md`; google-flow-ops "Every shoot ends with a mechanical audit"
- Pre-shoot: `CTO_Flow_Omni1.1_Continuity` · story: `thai-moral-drama`

## Field notes
