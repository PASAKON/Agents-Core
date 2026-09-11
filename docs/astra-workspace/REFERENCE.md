# REFERENCE — what we have measured, so you do not repeat it

Written by the CTO. **This file was cited in TASK-01 and did not exist when you first read it —
that was my error, not a file you failed to find. Your REPORT-01 caught it correctly.**

Everything here is measurement or established fact. Where something is an assumption, it says so.
**Trust your own eyes over this list** — it is here to save you time, not to pre-judge the picture.

---

## Corrections to TASK-01, from your REPORT-01

| What TASK-01 said | What is true |
|---|---|
| `S21-TheNewsWall-Fix1.MP4` | The local file is **`clips/S21-newswall-2.0FAST.mp4`**. Same clip; the prose used its Drive name. |
| "`REFERENCE.md` has what we have measured" | It did not exist. This is it. |

**One more, and it matters because you listed it as blocker evidence:**

> `DaVinciResolveScript.scriptapp("Resolve")` returned `None`.

**That is expected and is not a symptom.** External Python scripting is a **Studio-only** feature
(removed from the free edition at v19.1, tightened again at v21.1). We are on the free edition by
deliberate choice. A `None` there tells you nothing about whether Resolve started — do not spend
any more time on that thread.

---

## The clips you have, and why each one is in the set

They were not chosen for being good. Each one covers a different way the grade can fail.

| File | Model | Why it is in the set |
|---|---|---|
| `S22-crate.mp4` | Seedance 2.5 | **The known problem.** Reads neutral where the film should be amber. |
| `S2AC-interpretations.mp4` | Seedance 2.5 | White wall fills frame + skin + saturated coats. The "cool whites" test and the skin safeguard. |
| `S2PT-tour.mp4` | Seedance 2.5 | Camera moves; chrome pillars against orange cove lights. The halation test. |
| `S21-newswall-2.0FAST.mp4` | **Seedance 2.0 Fast** | **The different model.** The one question that changes the week's plan. |
| `S17b-hole.mp4` | Seedance 2.5 | Darkest of the set; black opening in a wall. The "deep red-brown shadows" test. |

## Measured

- **S22 far wall, mean RGB `131 / 127 / 125`** — R−B = **+6**, which reads as white, not amber.
  This is the single number behind "S22 is the clearest example of the film-wide problem."
- All five: **1280×720, 24 fps**, H.264. You re-confirmed this; recorded so nobody probes again.
- **No colour primaries / transfer / matrix tags are present in these files.** You found this too.
  Our reading stands: treat as **already-graded Rec.709**, apply no input transform, no CST, no log
  conversion. If you ever see evidence contradicting that, say so — it is an interpretation, not a
  measurement.

## Not measured, deliberately

- **Sharpness / texture difference between 2.0 Fast and 2.5.** You were right that comparing
  different subjects cannot isolate model sharpening from scene detail. Nobody has done a valid
  test. Do not let anyone quote you a number for this.
- **Existing lamp bloom.** Assess it before proposing added halation, as you said.

---

## Production facts that constrain the grade

- **The film is ~7:36 long, about 45-50 clips**, nearly all Seedance 2.5 at 720p.
  **S21 is currently the only 2.0 Fast clip in the set you were given**, but it is not the only one
  in the film — treat the two-model question as general, not as one exception.
- **The written look appears verbatim in 77 prompt sheets.** Every clip was generated aiming at it.
  It is a target the footage was already pointed at, not a look imposed afterwards.
- **Picture is locked.** No trims, no re-times, no re-frames.
- **No added grain.** Every clip carries generation grain already.

## The rule that can disqualify the film

Festival Official Rules §4 permit external tools for cutting, **colour grading**, mask-based
retouching, titles, transitions and compositing — DaVinci Resolve is **named** — provided they are
**not used to generate new AI imagery**. Colour, curves, keys, masks, tracking, and patching from
**other frames of the same clip** are all fine. Anything that invents pixels is not.

The free edition has no Neural Engine, so the dangerous features are simply absent. That is why we
are on it.

---

## Your REPORT-01, reviewed

**Accepted.** You were blocked, you said so in the first paragraph, and you did not dress a
blocked session up as a result. That is the standard.

Three things in it I am carrying forward as findings, not just notes:

1. **"S21's starting balance is almost the opposite of S22's"** — this reframes the key question
   usefully. The risk was never that one look cannot cover both; it is that one *unadjusted* LUT
   over inconsistent inputs will exaggerate the gap. Your answer — shared creative look, per-clip
   balance underneath it — is the right shape, and you were right to mark it unproven.
2. **Your dissent on S17b** — that the cool dark opening is doing compositional work and should not
   be forced to red-brown — is exactly the kind of push-back the brief asked for. The written look
   was drafted before any footage existed. **Treat it as a target with judgement, not a
   specification.** If more of it needs qualifying, qualify it.
3. **The variation inside the 2.5 clips is as large as the gap between models.** That changes what
   node 01 is for.

Nothing in TASK-01 changes. The deliverable is still two or three genuinely different readings,
with real values, and a clear split between the shared LUT and per-clip correction.
