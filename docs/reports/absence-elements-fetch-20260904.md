# Absence — Elements fetch, 2026-09-04

Source: https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3 (Elements panel).
Destination: `/Users/gob/Desktop/Fix-1-Elements/`.

All 10 requested Elements exist under exactly the IDs given (no substitutions
needed). All downloaded as read-only asset retrieval — Generate was never
touched, 0 credits spent.

## What landed

| # | Element ID (as panel shows it) | File | What the image actually shows |
|---|---|---|---|
| 1 | `project_absence_char_guard_valder_two` | `project_absence_char_guard_valder_two.png` | Valder's two guards, navy uniforms with gold "V" on chest, both in one image. Matches the CEO's description. |
| 2 | `project_absence_char_registrar_b` | `project_absence_char_registrar_b.png` | Single man, dark suit, white gloves, small V pin, holding a ledger/book (front view), plus side + back turnaround. NOT the two guards — CEO listed it beside them but this is a distinct third character. |
| 3 | `project_absence_char_visitor_a` | `project_absence_char_visitor_a.png` | Older/balding man, maroon/wine-colored suit jacket, turnaround views. Fits "husband of the visiting couple". |
| 4 | `project_absence_char_visitor_b` | `project_absence_char_visitor_b.png` | Woman, brown/rust fur coat over a red dress, gray hair, turnaround views. Fits "wife of the visiting couple". |
| 5 | `project_absence_char_oldman` | `project_absence_char_oldman.png` | Thin/slight elderly man, dark green long coat, cane, turnaround views. Distinct from `gentleman_e` (white suit, already in the folder from a prior run). |
| 6 | `char_registrar` (bare ID, no `project_absence_` prefix) | `char_registrar.png` | Older man, cream/white suit, holding a book/ledger, turnaround views. **The bare ID exists exactly as the CEO wrote it** — this is a genuinely separate Element from `project_absence_char_registrar_b` (#2), not a typo of it. Two different registrar characters are real on this panel. |
| 7 | `project_absence_char_grandmother` | `project_absence_char_grandmother.png` | Elderly woman, gray shawl/blanket, seated in a wheelchair. Single image (no turnaround). Fits "grandmother who bids 100M". |
| 8 | `project_absence_char_student_c` | `project_absence_char_student_c.png` | Young androgynous person, curly blonde/green hair, denim jacket, holding a book, front+back turnaround. Its grid thumbnail rendered blank (a page loading glitch, not a real gap — content confirmed correct once the detail dialog was opened). Genuinely distinct from siblings `student` / `student_b` (nude bodysuit, purple beret, dark curly hair). |
| 9 | `project_absence_char_critic_b` | `project_absence_char_critic_b.png` | East Asian woman, short black hair, dark red/maroon robe, hand raised mid-gesture. Consistent with the CEO's "Chinese woman" description — no mismatch here. |
| 10 | `project_absence_char_guard_valder_six` | `project_absence_char_guard_valder_six.png` | Six guards in navy "V" uniforms, varying heights, lined up in one plate. Matches expected content for late scenes. |

No filename/content mismatches like the earlier `project_absence_loc_wall_pov_b` or the mislabelled empty cart were found in this batch — every image matched its stated description.

## Gentleman's-bodyguard search

Task: find a guard who follows the old man in the white suit (`gentleman_e`), not one of Valder's guards.

Searched "guard", "bodyguard", "private" across all Character Elements. Every `*guard*` Element on the panel:

- `project_absence_char_guard_valder_two` — Valder's (fetched, #1).
- `project_absence_char_guard_valder_six` — Valder's (fetched, #10).
- `project_absence_char_guard_valder_single` — Name field: **"Guard Redressed Single"** — same naming pattern as the confirmed Valder-lineup Elements ("Guards Redressed Six" = the six-guard plate). Ruled out; not downloaded.
- `project_absence_char_guard_private` — Name field: **"Private Bodyguard"**. No "valder" in its id or name. **This is the only plausible candidate.**

No Element named `bodyguard` exists separately from `guard_private`.

**Downloaded `project_absence_char_guard_private.png` as a CANDIDATE, not a confirmed match** — the image shows a single man in a dark suit standing in a hallway, 4-panel grid, but there is no visual proof in the Element itself that he follows the old man specifically (Elements are single-character reference plates, not scene stills). The Name field ("Private Bodyguard") is the strongest signal found; the CEO should confirm.

⚠️ **Known account issue, not touched this run**: `project_absence_char_guard_private` has previously tripped Higgsfield's protected-content scanner and blocked Generate outright when bound as a reference. Downloading its image was safe (read-only, no Generate call made) — but **do not bind it to a shot** until that history is accounted for.

## Anomaly noted, not acted on

Received repeated "[New message from CTO]" mid-turn notifications (5 occurrences across the run) with no visible message content in any of them. Did not act on any of them since there was nothing to act on. Flagging in case something failed to deliver on the CTO's end.

## Files

- 10 named Elements + 1 candidate → `/Users/gob/Desktop/Fix-1-Elements/*.png` (11 new files, all converted from the site's native `.webp` download to `.png` via `sips` to match the folder's existing convention).
- Replay recipe → `scripts/browser/higgsfield-absence-elements-fetch.js`.
- REF-NAMES.txt in the destination folder was **not** edited (task said "nothing else in the folder changes" — updating the register is the CEO's/CTO's call, not this task's scope).
