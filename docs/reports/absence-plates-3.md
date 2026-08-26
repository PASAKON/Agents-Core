# absence-plates-3

## JOB 1 — downloads (done)

| Asset id | Saved as | Confirmed on disk |
|---|---|---|
| `a7d8d116-3b08-442e-89a6-e58a014c8c81` | `/Users/gob/Desktop/absence-02-hall.png` | yes, 2.8MB |
| `92235ba9-f90f-493e-86f9-f86dc73c2123` | `/Users/gob/Desktop/absence-01-wall-crack.png` | yes, 1.8MB |
| `353e587e-40b2-435a-a6d5-8550e8fce828` | `/Users/gob/Desktop/absence-00-painting.png` | yes, 1.9MB |
| `ec45f919-7fa6-440e-aea7-d987bd140f1a` | `/Users/gob/Desktop/absence-00-tag.png` | yes, 2.0MB |

Hall (the gating shot) downloaded and reported first, per instructions.

Note: the tag-plate preview page hit two consecutive `CDP sendCommand
Page.captureScreenshot` timeouts (renderer briefly unresponsive; window also
stopped honoring resize_window, stuck at 728x420 CSS px). Per the
higgsfield-unlimited-gen skill's hard rule 7, checked Usage/Credits
immediately in a separate tab before doing anything else: paid balance read
1,844 — unchanged from the task brief's stated ~1,844, confirming the
timeouts caused no spend. Recovered by closing the frozen tab and opening a
fresh one (browser-operator skill's escalation ladder), which resolved it.

Separately: on the fresh tab, screenshots came back at 1456x840 px instead of
the CSS 1024x591 that `getBoundingClientRect()` reports — a scale mismatch
between `computer` click coordinates (screenshot pixel space) and JS-computed
coordinates (CSS pixel space). Two raw-coordinate download clicks silently
missed the button because of this. Fixed by switching to `find()` + ref-based
clicks, which are scale-safe. Flagging this as a general trap for any
future replay script: never mix JS-derived pixel coordinates with the
`computer` tool's click coordinates on this site — use refs.

## JOB 2 — tag verification (initial, before CEO rejection)

| Element | Color | Element id |
|---|---|---|
| project_absence_prop_painting | GREEN | 4bb356b1-7957-4585-b9b4-f45ab14a2e3a |
| project_absence_prop_tag | GREEN | 1670d9ef-1463-4bb2-804a-f53de2aa61f1 |
| project_absence_loc_wall_crack | GREEN | 2c52b541-327d-4d25-8aba-296ba3e787bb |
| project_absence_loc_hall_big | GREEN | 173cb410-60e3-43fe-b80d-baa946c0d001 |
| project_absence_loc_corridor | RED (expected — never generated) | — |

Method: pasted each tag as plain text into the Cinema Studio 4.0 (video-mode)
composer via synthetic ClipboardEvent, read the resulting DOM node's class
(`text-font-brand` lime = bound/green, `text-font-error` red = unbound) and
`data-beautiful-mention` attribute for the resolved element id.

**CEO rejected both location plates after seeing this table**, because a tag
resolving GREEN in the composer does not prove the ORIGINAL generation actually
used that reference. Root cause found on `loc_wall_crack` (asset
`92235ba9-f90f-493e-86f9-f86dc73c2123`): its stored prompt is **literally
truncated mid-word** (ends `...accidental d[TRUNCATED]`), with a bare raw-uuid
reference (`@1670d9ef-...`, no descriptive text around it) appended after the
cut. The previous operator almost certainly used a keystroke-`type()` action
instead of a paste, which the `higgsfield-unlimited-gen` skill documents as
truncating multi-paragraph Higgsfield prompts. The model never saw a properly
described plaque reference and invented one from scratch — exactly matching
what the CEO saw on screen (wrong screw count, wrong text layout, italic
"Valder").

## Platform finding — Soul Cinema composer cannot bind text-mention references (new, for the skill)

Confirmed on a completely fresh tab/session, multiple times, with the
project's Elements list pre-warmed via a `?elements=1` visit beforehand (ruled
out as a timing/cache issue):

- **Paste-based auto-resolve** (`@project_absence_prop_tag` pasted as plain
  text) renders **RED** (`text-font-error`) in the **Higgsfield Soul Cinema**
  composer (Image mode), for both a Prop and a Location element. The identical
  paste resolves **GREEN** in the **Cinema Studio 4.0** (Video mode) composer
  on the same project, same session.
- **Real `@` keystroke**: typing a bare `@` in the Soul Cinema composer never
  opens an autocomplete dropdown at all — confirmed with `computer.type()`,
  both a single `@` and a full `@project_absence_prop_tag` string. No
  suggestion list ever appears.
- **Elements panel → right-click card → "Use"**: this DOES attach a correct
  reference-image thumbnail to the composer's reference strip (verified
  visually — the plaque thumbnail rendered correctly), but the accompanying
  inline text it inserts is the **raw uuid** (`@1670d9ef-...`), and that text
  still renders **RED**, not green.
- **Switching the model dropdown from Soul Cinema to GPT Image 2, with no
  other change**, immediately converted the same red raw-uuid mention into a
  **GREEN, human-readable** `@project_absence_prop_tag` chip. GPT Image 2's
  composer resolves plain-text `@name` mentions via paste correctly, on the
  first try, no warm-up needed.

Net: **Soul Cinema's text-mention binding is broken for this project** (or at
least was, throughout this session). GPT Image 2's is not. Per CEO ruling
2026-08-27 05:15, both rejected location plates were rebuilt on GPT Image 2
instead of chasing the Soul bug further, and — per the CEO's standing model-
consistency rule — **both** locations come from GPT Image 2, not one from
each, so the location set stays internally consistent for intercutting.

## Location plate redos (GPT Image 2)

**Wall-crack, attempt 1 — done, then rejected again by CEO for crack size.**
Model: GPT Image 2, Medium, 1K, 2 credits. `@project_absence_prop_tag` verified
GREEN before generating. Fixed the wrong-plaque problem, but the crack itself
was drawn as a long diagonal fracture spanning most of the wall with visible
floor debris — the CEO's brief had said "visible from across a room," which
this took too literally. CEO verdict: reads as earthquake damage, not an
accident; his own fault for the wording, not the operator's.

**Wall-crack, attempt 2 — done, accepted.**
`/Users/gob/Desktop/absence-01-wall-crack.png` (overwrote attempt 1). Same
model/settings/plaque reference, crack rewritten to CEO's corrected spec: a
small, LOCAL crack roughly the size of a spread hand, near painting height, a
little chipped plaster right at the impact point, **zero rubble on the
floor**. Confirmed visually against the CEO's own test ("could one man with a
ladder have done this by accident") — result is a short, thin, hand-scale
crack with one hairline branch, clean floor. `@project_absence_prop_tag`
re-verified GREEN before this generation too.

**Element re-filed.** Used the asset's `...` menu → **Assign to element** →
searched `wall_crack` → selected the existing `project_absence_loc_wall_crack`
Element → Assign. This points the Element at the NEW (small-crack) asset
instead of creating a duplicate Element. Re-verified by pasting
`@project_absence_loc_wall_crack` fresh: renders GREEN (`text-font-brand`)
with a reference thumbnail that visually shows the new small-crack
composition, not the old big-crack one.

**Hall four-panel sheet — done, accepted (no correction requested on this
one).** `/Users/gob/Desktop/absence-02-hall.png` (overwrote the rejected
single-view hall). One wide image, four panels: hero wall (referencing
`@project_absence_loc_wall_crack`, so it inherits whichever crack version was
current at generation time — this was generated using the FIRST wall-crack
attempt, before the CEO's size correction landed; the hero-wall panel's crack
has not been individually re-checked against the corrected small-crack spec),
left side, right side (a distinctive red/maroon chair visible — candidate for
Valder's seat, sightline toward hero wall), high overhead (full floor plan
readable, same chair visible from above). White walls with other framed art
and sculptures, retrofuturist terrazzo floor and starburst ceiling motifs, no
people. Model: GPT Image 2, Medium, 1K, 2 credits.

**Flag for CTO/CEO:** the hall's hero-wall panel likely still shows the
too-large crack from attempt 1, since it was generated before the size fix.
Not re-generated in this session because no correction was requested on the
hall specifically — surfacing this now rather than assuming it's fine.

**Wall-crack, attempt 3 — done, then session HELD by CEO before a verdict.**
`/Users/gob/Desktop/absence-01-wall-crack.png` (overwrote attempt 2; asset id
`a2c2af3f-6fe3-4275-b7a2-eb86f4d83956`). CTO relayed a further CEO note: the
accepted small crack (attempt 2) had lost the hall's room — wood parquet
floor instead of terrazzo, a white skirting board, no ceiling, flat
directionless light — so it would not intercut with the accepted hall sheet.
Regenerated with **three references attached and verified GREEN**:
`@project_absence_loc_hall_big`, `@project_absence_prop_painting`,
`@project_absence_prop_tag`. Kept the crack and plaque exactly as attempt 2;
changed only the room to inherit the hall's terrazzo floor, checkered rug
motif, warm directional lighting and decor. Re-filed to the Element via
Assign to element, re-verified GREEN with the correct (terrazzo) thumbnail.

**Then CEO put this specific plate on HOLD** before confirming attempt 3 —
he now prefers the original colourful-room look over the terrazzo gallery
look and is sending updated direction. Per CTO instruction: stopped
generating, left the browser exactly as it was (no further navigation/clicks
past this point), and committed this report. **`absence-01-wall-crack.png`
on disk right now is attempt 3 (terrazzo room) — this is NOT yet CEO-confirmed
and may be replaced again once the new spec lands.** Do not treat this file
as final without checking for a follow-up report.

## JOB 3 — corridor generation

Not started — put on hold before reaching this. Hall (accepted) and the
wall-crack Element (attempt 3, unconfirmed) are the current state; corridor is
next once the wall-crack question is resolved.

## Credits

- Paid balance: 1,830 left (was 1,844 at task start). My own spend this
  session: 8 credits across four generations (wall-crack attempts 1/2/3 + the
  hall sheet, 2 credits each at Medium/1K/GPT Image 2) — well inside the
  10-credit cap. The further drop from 1,838 to 1,830 (4 credits) was NOT my
  action: two additional four-panel gallery-hall-style assets appeared in the
  project mid-session that I never generated (different composition from
  anything in my prompts) — almost certainly the other operator's concurrent
  work on this same shared project, per the task brief's warning that another
  operator's tab was open on it. Flagging rather than assuming.
- Soul free allowance: not touched this session (stayed on GPT Image 2 per
  CEO ruling), so still ~4,995 per the original brief.

## Green/red table (final state, this session)

| Element | Color | Notes |
|---|---|---|
| project_absence_prop_painting | GREEN | unchanged |
| project_absence_prop_tag | GREEN | unchanged |
| project_absence_loc_wall_crack | GREEN | re-filed to attempt-3 (terrazzo room) asset; **unconfirmed, on hold** |
| project_absence_loc_hall_big | GREEN | re-filed to the new four-panel asset (via regeneration, same Element); accepted |
| project_absence_loc_corridor | RED | not generated — JOB 3 not started |

## HOLD — session paused here

CTO instruction received mid-session: CEO prefers the original colourful-room
look over the terrazzo-gallery look for the wall-crack plate and is sending
new direction. Stopped all browser actions at this point, left the tab open
and untouched (last state: composer cleared, sitting on the project's asset
grid), and committed this report. Awaiting the new spec before doing anything
further.

## Tab

Tab title at time of writing: "Cinema Studio 4.0 — Direct Every Detail | Higgsfield"
