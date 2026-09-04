# Absence — IV2c-Fix1, 2026-09-05

## Merge

Origin was 169 commits behind local `main` (the sheet, `upload_fix1.py`, and
`tab_registry.py` all lived only on local `main`). `git merge origin/main`
was a no-op; merged local `main` instead, per the task's own fallback
instruction. Fast-forward, clean, no conflicts.

## Lint

`python3 scripts/prompt-lint.py docs/prompts/absence/s-interview-iv2c-fix1.txt`
— exit 0, no output. Clean.

## Composer — six fields read back

Fired in `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`
("The Valder Collection No.7"), Video tab, model switched from the
Cinema-Studio-4.0 default to **Seedance 2.5** explicitly.

Settings drifted from the composer's own defaults mid-setup (720p reverted
to 480p, duration defaulted to 5s) — both caught and corrected before firing,
per the "composer silently resets" rule. Read back fresh immediately before
the click:

| Field | Value |
|---|---|
| Model | Seedance 2.5 |
| Resolution | 720p |
| Aspect | 16:9 |
| Duration | 20s (Radix slider, `aria-valuenow` moved 5→20 via 15× ArrowRight after a single thumb click) |
| Bitrate/Quality | High |
| Sound | On |

References: 1/1 attached — `@project_absence_char_dupe_interview_house`
resolved as a thumbnail chip (no red/unresolved text anywhere in the pasted
body). Prompt entered via synthetic `ClipboardEvent` paste into the real
(non-decoy, `visibility:visible`) contenteditable node, followed by
End→space→Backspace to force the Lexical state to bind. Verified via
`innerText` length (6640, matches source + Lexical paragraph breaks) and
exact first/last 80 characters against the sheet.

## Unlimited / price

Toggle was off by default; one clean `find()`-ref click flipped it to
`aria-checked="true"` / `data-state="on"` on the first attempt — no retry
techniques needed.

Price re-verified by **zoom** on the actual Generate button pixels (not a
JS text scrape, which the skill flags as unreliable on this composer)
immediately before the click:

**`UNLIMITED · ~~140~~ · 0`** — struck-through price, `0` charged. Confirmed
zero before clicking.

## Fire

Clicked Generate at **04:10:05 ICT**. "Generation started" toast, asset
count 637→638. Render finished at **~04:45 ICT** (≈35 min — outside the
01:00–07:00 UTC fast window per the skill's schedule; this fire was ~21:25
UTC the previous day, US evening/working hours, so the longer render matches
known platform load patterns, not a fault). Poll cadence: first check at 15
min (still rendering, expected), then every 5 min; verified with a page
reload rather than trusting the long-lived tab's cached spinner state after
four identical readings.

## Info icon / rights check

Opened the finished card's detail modal (`?preview=<uuid>`), Info tab.
**No "Rights verification required" banner anywhere in the panel** — Prompt,
Details, and Filed-in sections all present, no flag. Details confirm:
Model Seedance 2.5, Quality 720p, Bitrate High, Size 1280x720, Created
September 5, 2026 at 4:09 AM. Clean generation, no refusal, no re-fire
needed.

## Verdict against the four checks

The in-browser video preview never loaded (`readyState:0` even after
waiting — a page/extension quirk, not a clip problem), so I downloaded the
finished file directly (Download button → `~/Downloads/hf_20260904_210957_…mp4`,
15.3MB, `ffprobe` confirms 20.05s / 1280x720 h264) and pulled frames at 1,
5, 7.5, 8.5, 9.5, 10.5, 14, 18s with `ffmpeg` to inspect directly.

1. **Three crew, clearly different people** — **PASS.** Woman camera
   operator (seated, glasses, olive shirt), young man boom operator
   (standing, boom pole overhead, headphones), older bearded bald man
   (standing). All visually distinct as specified.
2. **Reveal reads as a house, not a studio** — **MIXED, flag for CTO
   review.** A window with daylight and trees is visible at the edge of
   frame during the whip-pan blur (10.5s), which does link the space to
   the house's exterior. But the crew-reveal frame itself (8.5–9.5s) is
   dominated by vertical wood-slat acoustic paneling, two exposed
   grip-style LED panel stands, a gear cart, and travertine riser steps —
   none of Dupe's frame's specific furnishing signatures (built-in shelving
   with vases, marble fireplace surround, sunken plum velvet seating) are
   visible in this angle. It reads more like a lit backstage/production
   area than a continuation of the warm daylight house interior the sheet
   demanded ("match it exactly... the same sunken plum seating, the same
   warm wood"). This is the exact defect the take exists to fix, present in
   a softer form. I'm reporting the evidence, not self-certifying a pass —
   per the review-loop policy this goes to CTO with the exact prompt.
3. **Camera visibly pointed back at Dupe inside the pan** — **PASS.**
   Professional cinema camera on tripod, lens pointed toward camera/us,
   operator's hand on focus ring.
4. **Only the light-dropper frozen, other two returning to work** —
   **PARTIAL.** Camera operator (looking through eyepiece) and boom
   operator (boom raised, "bringing it back into position") both read as
   working, matching the brief. But **no fallen light stand is visible on
   the floor anywhere in frame** — both LED stands are upright and lit
   normally — and the third crew member (older bearded man) is posed with
   both hands out in an open/explaining gesture rather than "staring frozen
   at the floor where the stand went over, hands still half-raised." The
   banned "light stand seen falling" negative was honored, but the staging
   detail that gives his pose meaning (a visible fallen stand to react to)
   didn't render, so his gesture reads more like mid-conversation than
   shocked-and-frozen.
5. **Dupe's own frame clean 0-7s and 10-20s, never reacts** — **PASS.**
   Frames at 1s, 5s, 14s, 18s all show Dupe alone, no gear, same calm flat
   expression and hand pose throughout — no reaction to the crash.
6. **One whip pan and back, nothing else** — **PASS.** Confirmed via motion
   blur at 7.5s (out) and 10.5s (back), single camera move each direction,
   no other move detected across the sampled frames.

**Net: 4 clear passes, 2 flagged for CTO's own frame-level review** (studio
signature elements without the fallen-stand staging cue). Not declaring this
take a pass or fail myself — filing it either way per the no-exceptions rule
and handing the exact prompt to CTO as the review loop requires.

## Filing

Uploaded via `scripts/gdrive-bridge/upload_fix1.py` to
`All Scene/Fix-1/` as **`IV2c-Fix1.MP4`** (14.6MB):
https://drive.google.com/file/d/1spy8lHou_UGtqplH9k2q881QfaYTg6kx/view

No verdict in the filename, filed regardless of the mixed read above.

## Prompt used (for CTO review, verbatim from the sheet's paste zone)

See `docs/prompts/absence/s-interview-iv2c-fix1.txt` between the
`PASTE FROM HERE` / `PASTE STOPS HERE` markers — pasted unchanged, byte
length and first/last 80 chars verified against source before firing.

## Re-probe: video-ref upload

Ran per "IF YOU FINISH AND HAVE TIME." Fresh tab, `ai-film-festival-3`
project, Video composer, uploaded `docs/S2O-Render.MP4` (3.6MB) via the
references panel's file input (`accept` includes `video/mp4`).

- **04:53:46 ICT** — upload accepted, "Uploading…" spinner tile appeared in
  the Uploads → Videos panel.
- **05:02:53 ICT** (9m7s) — spinner gone, but **no tile for the upload
  exists anywhere** — not in Recent, not in Videos, not in All. References
  still reads 0/50. No error toast, no "Checking.." stuck state like the
  three prior probes documented; this time the upload simply vanished after
  the initial "Uploading…" stage with nothing to show for it.
- **05:03:24 ICT** — stopped at the ~10-minute mark as instructed.

**Verdict: still down**, ~9–10 minutes elapsed, new failure signature
(silent disappearance rather than a stuck "Checking.." spinner) but same
practical conclusion — no usable reference attaches. Did not retry with a
different file or tab; that ground is covered by earlier probes per the
task's own instruction.

## Notes / oddities

- Three "[New message from CTO]" mid-turn pings arrived with no body (the
  documented worker-mailbox empty-notification bug). Checked `TASK.md` each
  time — unchanged from the original brief throughout. No action taken;
  flagging per protocol.
- The task brief's stated preconditions ("the sheet lints clean, it binds
  exactly one Element... IV2c is not on Drive") were true on local `main`
  but the worktree was created from a stale/behind base and none of the
  referenced files existed until the local-main merge. The task anticipated
  exactly this ("If origin is behind, merge from local main") so this
  wasn't a blocker, just worth recording — a worktree base can drift behind
  local main even when origin itself is far behind both.
- The in-browser video preview modal never loaded playable frames
  (`readyState:0`, `networkState:2` stuck) for this clip in this Chrome
  session — worked around by downloading and inspecting via `ffmpeg`/
  `ffprobe` directly, which is also the file needed for Drive filing anyway.
