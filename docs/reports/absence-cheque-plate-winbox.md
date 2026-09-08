# Absence prop plate — THE CHEQUE (100,000,000) — 2026-09-09, winbox

Task: task-cb28dcfb. Goal: ONE 16:9 still image of the S15e cheque prop,
registered as an Element named exactly `project_absence_prop_cheque`. ZERO
paid actions.

## Model / settings

- Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`
  ("The Valder Collection No.7"), composer switched from its default Video
  (Seedance 2.5) to **Image** mode.
- Model: **Kling O1** (Image) — the same free-image recipe used for the car
  plate on 2026-09-07 (`docs/reports/absence-plate-car-20260907.md`).
- Settings: 16:9, **2K** (highest free quality tier — 1K/2K both selectable
  with Unlimited on, no price change), batch 1/4.
- **Unlimited toggle switched ON.** Price zoomed on the Generate button
  immediately before every click: bare `UNLIMITED`, zero digits, both
  attempts. Confirmed via a real screenshot `zoom` (not a DOM text scrape —
  the skill's own hard rule, since a decoy button can carry a stale price).
- All assets counter: 734 → 735 (attempt 1) → 736 (attempt 2). No credit
  ledger movement observed or expected (Kling O1 Unlimited is the account's
  free-image path, confirmed in `higgsfield-unlimited-gen` skill's "Free
  IMAGE plates" section).

## Prompt (pasted exactly, verbatim per the task brief)

> A single plain cream-coloured bank cheque lying flat on a grey knitted
> handbag, photographed straight from above in soft warm gallery light.
> Printed thin lines on the cheque, an old bank's plain layout with no logo,
> no bank name and no other readable text. Across the amount line,
> handwritten large and perfectly legible in blue fountain-pen ink:
> 100,000,000. Below it a small ink signature scrawl. Beside the cheque, a
> slim black fountain pen, uncapped. Photoreal, 35mm, fine film grain,
> shallow depth of field, the cheque sharp.

Entered via synthetic `ClipboardEvent` paste (text/plain only) into the
real (non-decoy, `visibility:visible`) Lexical contenteditable, verified
exact 530-char length + first/last-80-char match against source both times,
followed by the End→space→Backspace desync-bind tap before every Generate
click (net text change zero, confirmed by re-reading length after).

## Attempts

1. **Attempt 1** (asset `eea73862-feda-4a40-b359-426b2d8b9a71`): fired,
   completed ~80s later, no safety flag. Zoomed the amount line in the
   detail panel: it read **`100,00,000`** — only two digits in the middle
   group, i.e. ten million, not one hundred million. Defective per the
   task's exact-digits requirement.
2. **Attempt 2** (asset `cf01c3ac-7b50-4f10-9dad-9b1c2a7b3126`): re-fired
   the identical unmodified prompt (composer state re-verified unchanged:
   same 530-char text, same Kling O1/16:9/2K/Unlimited spec, price re-zoomed
   zero-digit immediately before the click). Completed ~40s later, no
   safety flag. Zoomed the amount line: reads **`100,000,000`** exactly —
   three groups of three digits, matches the task requirement precisely.
   **Picked this one** (task allows at most two attempts; this cleared on
   the second).

One tool-call timeout occurred while polling attempt 2's render (a
`computer wait` call). Per the higgsfield-unlimited-gen hard rule ("any
browser-tool error while on a Higgsfield page → check state before anything
else"), re-read the page immediately via `javascript_tool`: asset count and
card state were both unchanged from the last known-good read, confirming no
side effect from the timeout — the tab itself was just briefly slow to
respond, no page reload or navigation occurred.

## Element registration

- Opened attempt 2's detail view → its own "..." menu (not the grid-hover
  stack) → **Create Element**. Dialog arrived pre-populated with the
  correct asset, no upload needed.
- Category: **Prop** (selecting it auto-prefixed Element ID to
  `prop_my-element` — the documented auto-prefix quirk).
- Name and Element ID both set to exactly `project_absence_prop_cheque` via
  a native value-setter + `input`-event dispatch (coordinate typing is
  unreliable on these fields per the skill's own note) — corrected the
  auto-prefixed value, verified by re-reading both fields before Create.
- Toast: **"Element created."**

## @-picker confirmation (video composer)

Switched the composer to **Video** mode (Seedance 2.5 — did NOT touch
Generate there; that surface is priced, `GENERATE 140 130`, no strike-
through, completely untouched). Pasted `@project_absence_prop_cheque test`
into the real contenteditable and applied the same End→space→Backspace tap.
Result: the mention resolved to a **lime `text-font-brand` chip**
(`@1d4cb7e2-e8b8-4531-a2a7-44714f220bdd`), confirmed both by
`document.querySelectorAll('[data-beautiful-mention]')` and by a screenshot
zoom showing the lime-colored chip text. **Confirms the Element is live in
the @-picker.** Composer cleared afterward (Ctrl+A + Delete ×2, verified
down to a single trailing newline) — no generation of any kind fired on
this composer.

## Download

- Downloaded via the asset-grid card's own hover download icon (2nd icon in
  the stack: heart / download / copy / reference / more).
- File: `hf_20260908_212337_cf01c3ac-7b50-4f10-9dad-9b1c2a7b3126.png`,
  landed in `~/Downloads` (outside the worktree, per role convention).
- Copied into the worktree at
  `docs/prompts/absence/generated/project_absence_prop_cheque.png`.
- **Size**: 6,490,865 bytes (6.19 MB).
- **Dimensions**: 2720×1536 (16:9), confirmed both by the platform's own
  detail-panel metadata and by re-opening the local file with PIL.
- **MD5**: `e932dc7c5b495b6405345c3ea4cb6aac`

No Drive token on this box — per the task, the CTO pulls this file from the
worktree and files it under `Element/`.

## Element summary

| Field | Value |
|---|---|
| Element Name | `project_absence_prop_cheque` |
| Element ID | `project_absence_prop_cheque` |
| Category | Prop |
| Source asset | `cf01c3ac-7b50-4f10-9dad-9b1c2a7b3126` |
| Model | Kling O1 Image, 2K, 16:9, Unlimited |
| Attempts | 2 (1 defective, 1 accepted) |
| Picker check | @-mention resolves to a lime chip in the Video composer |

No paid action taken at any point; no rights-verification banner appeared.
