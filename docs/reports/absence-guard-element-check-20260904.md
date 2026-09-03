# Absence guard-Element check (task-2e5077b9)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (The Valder Collection No.7)
Read-only task. Zero generations fired, zero uploads, zero cost.

## Question 1 — does an Element point at the new bodyguard asset?

**Answer: (b).** A SEPARATE new Element exists. It does not overwrite/re-point
the old `guard_private` Element — both exist side by side, as two distinct
characters.

| | Old Element | New Element |
|---|---|---|
| Handle | `@project_absence_char_guard_private` | `@project_absence_char_guard_private_v2` |
| Name (panel) | "Private Bodyguard" | "Bodyguard (redesigned)" |
| Category | Character | Character |
| Created | 6 days ago | 3 hours ago |
| Last changes | 1 day ago | 3 hours ago |
| Image | grey-haired man, clean-shaven, museum/gallery background, ordinary suit — no sunglasses, no gloves | heavy-set man, dark sunglasses, white gloves, all-black suit — matches the task's description exactly |
| Asset UUID (from thumbnail path) | `dbd40616-2a78-4bea-9ffe-fa13b4c15e67` | `93923e8d-64b5-47cd-b6d6-0c77389d95ce` |

The new Element's asset UUID (`93923e8d-64b5-47cd-b6d6-0c77389d95ce`) matches
the filename the operator saved locally **exactly**. Confirmed by reading the
Element's own detail-panel thumbnail `<img src>` path, not by inference:
`/user_39AwuuLxRPQ20d5TQbk4NU0bWsp/hf_20260903_183329_93923e8d-64b5-47cd-b6d6-0c77389d95ce_min.webp`.

Read from the panel itself:
- Elements panel -> Characters tab -> searched "guard" -> 7 matches returned
  (`_v2`, `guard_valder_two`, `guard_private` (old), `guard_valder_single`,
  `guard_valder_six`, `valder_char_guards_12`, `valder_char_guard`).
- Clicked "Bodyguard (redesigned)" card -> detail panel -> `ELEMENT ID:
  @project_absence_char_guard_private_v2`, `Category: Character`, `Name:
  Bodyguard (redesigned)`, `Created: 3 hours ago`.
- Separately clicked "Private Bodyguard" card -> confirmed it is untouched:
  `ELEMENT ID: @project_absence_char_guard_private`, `Created: 6 days ago`,
  `Last changes: 1 day ago` (i.e. not touched today), and its bound image is
  visibly a different person entirely.

**Consequence for prompts**: every prompt already using the old handle
`@project_absence_char_guard_private` still gets the OLD face. Nothing picks
up the new look "for free." Any scene that wants the redesigned bodyguard
must be written (or edited) to bind `@project_absence_char_guard_private_v2`
specifically.

**Old image reachability**: yes, still reachable — nothing was deleted. The
old Element `@project_absence_char_guard_private` still exists, is still
Active, and its detail panel still renders its original image
(`dbd40616-2a78-4bea-9ffe-fa13b4c15e67`) without issue.

## Question 2 — does the redesigned face still trip the protected-content scanner?

**Staged, did not fire.** Per the hard stop in the brief, Generate was never
clicked.

Steps:
1. Own tab, resized to 1024x768 (verified `innerWidth/innerHeight` = 1024x647
   after Chrome's toolbar overhead).
2. Opened the project's Video composer, switched model from the default
   Cinema Studio 4.0 to **Seedance 2.5** (the model the scanner behavior was
   measured against on 2026-09-02).
3. Located the real (visible) Lexical editor node — the composer renders a
   hidden decoy `contenteditable` alongside it; filtered by
   `getComputedStyle(el).visibility === 'visible'` before touching anything.
4. Entered `@project_absence_char_guard_private_v2 ` via synthetic
   `ClipboardEvent` paste (text/plain only — no `type()`, per the
   higgsfield-unlimited-gen hard rule against keystroke entry truncating/
   desyncing prompt text), then `End` -> `space` -> `Backspace` to force the
   pasted text to bind to the app's real form state (the documented
   paste-doesn't-always-bind gotcha).
5. The tag resolved immediately: rendered as **highlighted mention text**
   (not the red "unresolved" state the higgsfield-unlimited-gen skill
   documents), and a reference thumbnail appeared above the prompt box
   showing the correct redesigned-bodyguard image.

**Result: no protected-content warning appeared anywhere** —
- Zoomed the reference-thumbnail chip directly: clean image, no warning
  triangle, no red border, no overlay icon of any kind.
- Scanned the full page's rendered text (`document.body.innerText`) for
  `protect|flag|nsfw|sensitive|policy|violat|scan|content warning|block|
  celebrity|likeness` — no hits (one incidental match on the word "review",
  unrelated UI text elsewhere on the page, not attached to the chip or the
  Generate button).
- Screenshot evidence saved: `docs/reports/absence-guard-element-check-20260904-composer.jpg`.

**This is not a full confirmation, and I want to be explicit about the gap.**
The brief itself describes the old-Element failure as blocking **Generate
outright** — i.e. the scanner may only trigger server-side at submission
time, not at chip-staging time. Everything checkable without clicking
Generate came back clean, but that is a necessary, not sufficient, test.
Per the brief's own instruction ("if the only way to learn the answer would
be to fire, then STOP and say so") — **I did not fire, so whether the
redesign actually clears the scanner at generation time is still unverified.**
The passive signal (clean chip, no pre-flight warning) is a good sign but not
proof.

## One thing that contradicts an assumption in the brief

Not part of either question, but observed and worth flagging: with the
staged `@project_absence_char_guard_private_v2` reference and Seedance 2.5
selected, the Generate button read **`80` (struck through) / `45`** — a
struck-through price with a non-zero live number, not the clean
struck-then-`0` that means Unlimited is fully applied, and not a live
unstruck price either (which would mean Unlimited is flatly off). This is a
third state the higgsfield-unlimited-gen skill's price table doesn't cover.
I did not investigate further (no toggle was touched, no click was made) —
flagging it only so whoever fires this scene next re-checks the price
fresh immediately before clicking, per the skill's own standing rule, rather
than assuming Unlimited is active because the prior operator's session had it
on.

## Files

- `docs/reports/absence-guard-element-check-20260904.md` — this report.
- `docs/reports/absence-guard-element-check-20260904-composer.jpg` — screenshot
  of the staged composer (resolved chip, reference thumbnail, unfired Generate
  button).

## Replay script

None. This was a one-off read-and-verify task (Elements panel lookup + a
single staged, unfired composer). Nothing here is a repeatable flow worth
scripting — the next time this needs checking, the handles will have changed
again.
