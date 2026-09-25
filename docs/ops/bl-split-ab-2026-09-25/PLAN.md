# BL split-by-dead-air A/B — plan (CEO 2026-09-25)

> "การแบ่งตัด ตาม Death Air หรือ Air time ที่เสียงพูดหายไปน่าจะช่วยได้ และให้ CTO เป็นคน Merge ·
> Video Editor 1/2/3 ตัดแค่ช่วงเวลาใดเวลานึง จาก Skill เดียวกัน · เอามาประกอบ ต้องต่อกัน ไม่มีฉากดำกั้น ·
> ไม่ฟิกว่า 1 Video จะต้องแบ่งกี่ช่วง แต่แบ่งตาม Death Air · แบบแรกตัดแบบติดกัน แบบสองตัดแบบช่วยกันแล้วเอามารวมกัน"

Owner: CTO 211633a8 (took over the BL editor pipeline from CTO 91a17eb2 the same day).
Episode: BL EP57 (XXLMARKETS), 153.0 s, audio `Work/task-501f1d89/in/ep57/audio-hq.mp3` (current voice;
the "โบรก" re-voice is spliced into the winner afterwards, same timestamps).

## Why it should help (measured, 2026-09-25)
A worker's bill is its context re-sent on every turn. EP57's single editor: 760 turns, 467.7M tokens,
$99.79 API-equivalent (deduped); its 39 images alone were re-sent ~44M tokens. Cost grows faster than
the length of the job, so N short sessions should cost less than one long one. That is the hypothesis
this test can fail.

## The two arms
| | Arm 1 — ต่อเนื่อง | Arm 2 — ช่วยกัน |
|---|---|---|
| editors | 1 video_editor, 0-153 s | N video_editors in parallel, one segment each |
| N | 1 | falls out of the dead-air split (EP57 estimate 3-5) |
| merge | none | CTO runs `tools/bl_merge.py` (a script, no model work) |

Identical in both: skill + template version, fixture, model (Sonnet 5), brief text except the time
range, the Jev loop (plan -> freeze -> final, the CEO's "A Editor + train Jev"), host (Contabo),
image policy. Arms run one after the other, never together, so neither slows the other. Renders on
Contabo (4 cores, 7 GB) are serialized with one lock.

## Dead-air split rule (no fixed count)
- Candidates: pauses >= 0.45 s from `silencedetect=n=-35dB:d=0.3` on the episode audio
  (EP57: 55 pauses >= 0.3 s, longest 0.89 s).
- Forbidden: a pause inside one visual block that spans several lines (e.g. EP57's checklist card
  129.38-141.48 s).
- Walk forward: from the previous cut, take the longest allowed pause between +25 s and +50 s; if none,
  the longest pause after +25 s. The cut is the pause midpoint, floored to the 30 fps frame grid.
- The number of segments is whatever this produces.

## Segment contract (what makes the joins invisible)
- Each segment covers exactly [t0, t1) with a plate on screen every frame; the last plate holds to t1,
  the first starts at t0. No fade in or out at a segment edge.
- Same template, same caption style, same encoder settings (1080x1920, 30 fps) so segments concat with
  `-c copy`. Video only per segment; the master audio is muxed once at merge.

## Merge gates (the CTO refuses to ship on any failure)
1. Frame count = floor(153.0 x 30) +/- 1.
2. Zero empty or black frames at 30 fps, including single-frame dips (whole-frame mean drop vs its
   neighbours) — the 4 fps gate missed one at EP57 76.37 s.
3. Seam check +/- 3 frames around every join.
4. One caption style across the episode.
5. Audio offset < 40 ms against the master.

## Measured per arm
Deduped tokens (sum over every editor) + $ API-equivalent, turns, wall time (Arm 2 = slowest segment +
merge), images read and their token cost, Jev decisions / applied / wrong-at-gate, checker verdict,
merge gates, and the CEO's eye on the two finals (the deciding vote).

## Order of work
0. **Fix the skill before either arm runs** (both arms must start from the corrected kit):
   the EP55 caption chip becomes the template's only caption style in every mode (§6d "small chip above
   the head" superseded by the CEO 2026-09-25); plates hold until the next plate; the 30 fps single-frame
   gate and the one-caption-style gate go into the checker.
1. Tooling: `tools/bl_split.py`, `tools/bl_merge.py`, full-episode fixture + per-segment spawn in
   `tools/bl_ab_run.py`. One developer task.
2. Arm 1 run -> measure.  3. Arm 2 run -> CTO merge -> measure.  4. Report to the CEO with both clips.
