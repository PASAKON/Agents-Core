# Valder video — wave 6 brief (paste-ready)

Written 2026-08-26 16:10 by CTO while wave5 was still healthy, so the handoff
costs no thinking time when wave5 approaches 250k tokens. Update the "state at
handoff" block from wave5's final report, then delegate.

---

## The job

Fire Higgsfield Seedance 2.5 video for «The Valder Collection No.7», the GFF
entry due **3 Sep 2026, 23:59 PT**. Prompts are on `main` in
`docs/prompts/valder/<scene>-multicut.txt`. One clip per scene, 20s, 720p,
16:9, Sound On, **Unlimited ON**.

## The one rule that overrides story order

**Fire ONE take of every uncovered scene before any second take of a covered
one.** Current coverage lives in `docs/reports/valder-clip-inventory.md`.

A film with thin coverage everywhere can be cut. A film missing ten scenes
cannot. S1 already has 6 takes and S1B has 4 — do not add to them.

## State at handoff — UPDATE THIS BLOCK BEFORE DELEGATING

- Covered: _(from wave5 report)_
- Still uncovered, in fire order: _(remaining of S4 S4B S4C S5 S5B S6 S7A S7B)_
- In flight when wave5 stopped: _(scene + clip id, or none)_
- Browser state: _(which tab holds the composer, what is attached)_

## Pre-flight is already done — do not redo it

Every remaining scene is at or under the 9-element ceiling (max 8), and all 26
distinct `@project_valder_*` tags resolve to a real plate. Verified offline
2026-08-26. **If a scene fails to fire, the cause is runtime, not the prompt
file.** Do not audit element counts or tag spelling.

## Fire sequence, every scene

1. Attach the scene's elements. Plain `@project_valder_*` tags bind; the
   `@[name](uuid)` bracket form does not.
2. **Scan the reference strip for warning triangles and click every one.** That
   triangle IS the "Check eligibility" control the protected-content toast
   refers to. Expect more than one. This is a normal step, not an exception —
   a periodic rescan flags assets that worked yesterday.
3. Paste the prompt with a synthetic `ClipboardEvent`. **Never** use a
   keystroke `type()` — it truncates multi-paragraph text silently, confirmed
   3-for-3. Filter contenteditable candidates by
   `getComputedStyle(el).visibility !== 'hidden'` first; there is a decoy editor
   that accepts pastes and discards them.
4. Re-apply the desync fix immediately before Generate, not at staging time:
   focus → Selection API cursor to end → REAL Space → REAL BackSpace.
5. Verify the paste three ways (`innerText`, `__lexicalTextContent`, editor
   state JSON) against the source length and first/last 80 chars.
6. **Zoom the Generate button and confirm it reads bare `Generate` with ZERO
   digits.** The Unlimited toggle's apparent state is not sufficient — it
   silently resets to OFF after any page reload. If any number shows, stop and
   message the CTO. Never click "Rerun" (↻); use "Recreate" instead.
7. Fire, record the clip asset id, wait.

## Waiting

One generation at a time, account-wide. Renders take 35-50 min outside the
01:00-07:00 UTC window (Europe and US asleep) and ~25 min inside it. A slow
render is the clock, not a bug — check the time before investigating anything.

**A long-lived tab lies about the slot.** If Generate returns "1 unlimited
generation at a time" with nothing visibly rendering, open a FRESH tab and look
again before concluding anything. Open a fresh composer tab every 3-4
generations.

**90-minute rule:** past 90 minutes a card is a zombie. Cancel it, record why,
move to the next scene.

## Skip authority

The CEO authorised skipping: "มีอะไรให้ตัดสินใจเอง หรือข้ามไปยิง Sence อื่นก่อน
ได้เลย". If a scene will not fire after a genuine attempt, **skip it, record
why, move on.** Never let one scene stall the queue. The standing order is
"ห้ามหยุด Generate Video Unlimited เด็ดขาด" — the slot must never idle.

## Three scenes break the pattern

- **S-V** is one uncut 20s take, not a multi-cut. No `=== HARD CUT ===`.
- **S1B shot 3** is the ONLY slow-motion shot in the entire film. The crowd is
  slowed too — a continuous slow-motion take, not a frozen crowd with one
  moving object.
- **S7B** is 8 shots; shot 8 is `loc_aerial`, static, no push-in.

## Crowd rule

Crowds must be **loose and scattered, never in formation**. No rally lines, no
rows, no anyone facing camera together. The CEO rejected an earlier clip for
this: "คนที่เดินดูเหมือนมนุษย์ต่างดาว". The cause was wording in our own prompt,
not the model.

## Reporting

Keep a table in `docs/reports/valder-video-wave6.md`:

```
| Scene | Take | Clip asset id | Status |
```

**That header wording matters** — the CTO's inventory tooling counts only rows
from tables headed `Clip asset id`, because a raw UUID grep sweeps in plate
(still image) ids and overstates coverage by ~2x. It already did once.

Commit as you go. Do not hold clip ids in context — a worker that dies with
uncommitted ids loses them. Heartbeat to the pane every ~90s so the CTO's
30-minute checks can see you are alive.

## Hard money rules

Credits sit at ~1,918 and must not move by video-scale amounts. Video under
Unlimited is 0. Images are 0.2-2 credits. A blocked protected-content attempt
costs nothing (client-side refusal, zero network calls). If any control near a
priced Generate button will not respond, **stop after ONE clean attempt and
message the CTO** — two 135-credit charges once landed from trying more click
techniques next to a live priced button.

## Stale refs

Re-query elements after any DOM re-render. A stale `find()` ref once landed a
click on the logout link and logged the whole account out.
