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

## JOB 3 — corridor generation

Not started — corridor generation is scheduled after both location redos are
confirmed on disk, per the updated CEO priority.

## Credits

- Paid balance: 1,844 (confirmed via Account menu → Credits, mid-JOB-1)
- Soul free allowance: not yet checked

## Tab

Tab title at time of writing: "Cinema Studio 4.0 — Direct Every Detail | Higgsfield"
