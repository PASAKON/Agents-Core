# S2L-Fix1 click-time bisect — 2026-09-04

Task: task-53a7edc4. Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`.
Prompt source: `docs/prompts/absence/s2l-fix1-collector-arrives.txt` (PASTE block, unchanged every round).
Video reference: `docs/S2L-Render.MP4`, attached as `@Video 1` every round.

## What this bisect was actually testing, and what it found instead

The task brief was built around the **pre-generation asset scanner** that refused the
original S2L submission instantly, before any render, with the exact wording
*"Some assets may contain protected content. Remove or replace them to proceed."*
The plan was to bisect the nine Elements by binding subsets and watching for that
same instant refusal.

**That pre-generation refusal never occurred in any of the four rounds below.**
Every round passed the click-time check and showed "Generation started." The
bisect instead surfaced a completely different, separate failure mode — Round 3
rendered fully and was then **rejected post-render by a copyright filter**, a
mechanism the task brief had already flagged as distinct from the pre-gen
scanner ("a different mechanism from the output filter that refused S2-Fix1 and
S2C take 1 after a full render"). Round 4, an independent repeat of Round 3's
exact reference set, rendered clean with no rejection at all.

**Net result: the original pre-gen "protected content" refusal was not
reproduced. The unrelated post-render copyright rejection that did appear once
was not reproducible on an immediate retry with the identical set — it looks
transient, not tied to any fixed Element or pair of Elements.**

## Round-by-round table

| Round | Reference set (+ @Video 1 always) | Price at click | Outcome |
|---|---|---|---|
| 1 | HISTORY only (4): `char_cleaner_c`, `prop_cart_a_painted`, `loc_hall_big_d`, `loc_wall_pov_e`. The 5 NO-HISTORY characters carried as plain prose (tag `@` stripped) instead of bound chips. | UNLIMITED · ~~140~~ · **0** | **Accepted at click** ("Generation started"). Rendered clean. No rejection. |
| 2 | HISTORY (4) + `char_woman`, `char_student_c`, `char_visitor_b` (7 total). `char_visitor_a` and `char_critic_b` carried as prose only. | UNLIMITED · ~~140~~ · **0** | **Accepted at click.** Rendered clean. No rejection. |
| 3 | **All 9** — exact original unmodified prompt, every tag bound: HISTORY (4) + `char_woman`, `char_student_c`, `char_visitor_b`, `char_visitor_a`, `char_critic_b`. | UNLIMITED · ~~140~~ · **0** | **Accepted at click** ("Generation started", no pre-gen refusal). Rendered fully, then **rejected post-render**. Exact wording: **"Rejected due to copyright restrictions."** No file produced. |
| 4 | Identical to Round 3 — independent re-submission of the exact same 9-ref set, ordered by the CTO to test whether Round 3's rejection was deterministic or transient. | UNLIMITED · ~~140~~ · **0** (re-verified fresh immediately before click) | **Accepted at click.** Rendered fully (unusually long: ~70+ minutes, vs ~13–20 min for Rounds 1/2). **Clean — no rejection.** Normal playable card with working Download/Recreate/Reference controls. |

Bind counts, verified programmatically before every click by scanning the
composer's resolved `@project_absence_*` mention nodes (never trusted by eye):
Round 1 = 4, Round 2 = 7, Round 3 = 9, Round 4 = 9.

## How Round 3's rejection was actually found

The rejection was **not visible anywhere in the composer** and not flagged by
any toast at click time. The finished card in the asset grid showed an
eye-slash icon over a blacked-out thumbnail with no play button — visually
distinct from every other finished card. Clicking the card's own small **(i)
info badge** (bottom-right overlay on the tile itself, NOT the composer's
prompt-panel info icon) opened a popup reading:

> **Rejected due to copyright restrictions.**
> `@Video 1`
> 20s · 720p · 16:9 · ONE LOCKED SHOT. …

with only **Copy prompt** and **Delete** actions available — no Download, no
Recreate-from-here in the normal sense. This state survived a full page reload
of the tab, confirming it is real server-side state, not a client rendering
glitch.

Round 4's finished card was checked the same way (hover for the info badge,
then opened the full preview modal) and showed no such banner — a completely
normal card with Download/Recreate/Reference/heart/share controls all present
and working.

## Six-field verification for every take that rendered

All four rounds: **20s · 720p · 16:9 · Seedance 2.5 · High · Sound On**,
confirmed both on the composer pills immediately before each click and, for
the three that produced files, via `ffprobe` on the downloaded MP4:

| Take | Resolution | Duration | Local file (kept, not deleted) | Drive |
|---|---|---|---|---|
| Round 1 → `S2L-Fix1.MP4` | 1280×720 | 20.04s | `~/Downloads/S2L-Fix1.MP4` | `All Scene/Fix-1/S2L-Fix1.MP4` |
| Round 2 → `S2L-Fix1-take2.MP4` | 1280×720 | 20.05s | `~/Downloads/S2L-Fix1-take2.MP4` | `All Scene/Fix-1/S2L-Fix1-take2.MP4` |
| Round 3 | — | — | none produced | none — rejected, not downloadable |
| Round 4 → `S2L-Fix1-take4.MP4` | 1280×720 | 20.05s | `~/Downloads/S2L-Fix1-take4.MP4` | `All Scene/Fix-1/S2L-Fix1-take4.MP4` |

Per the CTO's standing instruction issued mid-task, **all local copies were
kept, not deleted**, for his own review. Takes 1 and 2 were originally deleted
after Drive verification (per the task brief's original instruction, which
predated the CTO's standing-instruction change) and were re-downloaded from
Drive back into `~/Downloads` once that instruction changed, confirmed
byte-identical by matching file size to the Drive listing.

## Content review (Rounds 1, 2, 4 — the three that rendered)

All three visually match the scene brief on inspection of the opening frame:
Dupe and his painted cart far left; the bound characters present and dressed
correctly (blue coat collector not yet arrived in the opening frame, as
scripted — she enters at [3s]); the black wall-crack silhouette correctly in
the extreme foreground with everyone behind it. Full frame-by-frame review
against the six-point checklist in the task brief (crack-in-front, contained
shock, five-at-the-wall spacing, maroon-suit-arrives-last, camera stillness,
one line of dialogue) was not completed beyond the opening-frame check — that
is a CTO/CEO creative-review step, not part of this click-time bisect.

## Conclusion

1. **The original pre-generation "protected content" scanner refusal did not
   reproduce in any of the four rounds.** Every round — including the exact
   original 9-Element prompt, twice — passed the pre-generation check cleanly.
   Whatever caused the original S2L refusal is either no longer present, was
   specific to conditions this bisect did not reproduce (a stale asset state,
   a since-changed Element binding, or a scanner that has since cleared the
   set), or was itself non-deterministic.
2. **A separate, unrelated failure mode surfaced once**: Round 3 was rejected
   post-render by a copyright filter. This is not the same mechanism the task
   was built to investigate.
3. **That rejection did not repeat on an immediate identical retry** (Round 4,
   ordered by the CTO specifically to test this). Per the CTO's own framing:
   *"If Round 4 also fires clean, the earlier refusal was transient and we
   stop treating any character as the culprit."* Round 4 fired clean. **No
   character or fixed pair of characters is implicated as a culprit** —
   `char_visitor_a` and `char_critic_b`, the two Elements that distinguish
   Round 2 (clean) from Round 3 (rejected), do not reproducibly trigger a
   rejection when present together, since the identical set rendered clean
   the very next attempt.
4. **Net recommendation**: treat both incidents (original pre-gen refusal, and
   Round 3's post-render rejection) as transient/non-deterministic rather than
   tied to any specific Element. No Element needs to be replaced or dropped
   from future S2L fires on this evidence. If either refusal type recurs, log
   the exact wording and the exact reference set at that moment — this report
   found no fixed rule that predicts either.

## SKILL-OVERRIDE notes

- `higgsfield-unlimited-gen` :: "prompt text unchanged, only bound references
  change" (JOB 1 instruction) :: interpreted as: keep every word identical
  except drop the leading `@` from a tag when that Element should NOT be bound
  this round (turning `@project_absence_char_x` into plain
  `project_absence_char_x` text) :: because Higgsfield's paste-autoresolve
  binds any exact `@project_absence_*` string it finds in pasted text — there
  is no way to keep the literal `@`-tag present in the words while also
  keeping the Element unbound, so dropping only the `@` character is the
  smallest possible change that satisfies both "unchanged text" and "different
  binding" simultaneously. Verified round-by-round via DOM inspection that
  exactly the intended tags resolved into chips each time, none extra.
