# char_grandmother — replacement plate

Task: task-f4320f9e. Replaces a rejected attempt (chrome lounge chair, no wheels).

- **Asset id:** `5dd23a87-67f3-4452-8a69-e81045e19993`
- **Project:** https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3 (The Valder Collection No.7), Character folder
- **Model/settings:** GPT Image 2, 16:9, Medium, 2K — 2.5 credits
- **Reference:** `project_absence_loc_hall_big_d` (UUID `1a2cf503-4843-4aed-b4cb-d7cb8b919fa8`), for light/floor/wall only — bound via literal `@project_absence_loc_hall_big_d` in pasted prompt, verified via data-beautiful-mention.
- **Element name (to file):** `project_absence_char_grandmother`

## Fixes vs the rejected plate
- Explicit two-large-rear-wheels + two-small-front-castors, called out as visible in every panel including the rear panel.
- Cloth draped over head/shoulders (not just a scarf accent).
- Large dark smoked glasses, opaque.
- Deep violet as sole colour; no black on her; dark grey/oxblood shoes+gloves only.
- No gold V, no jewellery/fur/gold.

## Filed
- **Element:** `project_absence_char_grandmother` (Character category), created via card's "..." → Create Element (pre-populated image).
- **Drive:** `absence-char-grandmother.png` uploaded to `ALL DRAFT/YT: ILAG/Sorry, Sir/Element/` (flat, matching the flat pattern every prior plate there already used, not the empty Character/Location/Prop sub-folders from project setup — logged as an EXCEPTION in the project's `logs.txt`), file id `1NtDjT3s-ACXrtqHSu7rRv1Taq_Lr3s9r`, 5,332,262 bytes (matches the browser download exactly).
- The rejected prior attempt (`absence-char-grandma.png`, chrome lounge chair, no wheels) was left in place, per the "nothing gets deleted" rule for this branch.

## Honest flaw found on inspection
Gloves render **black**, not dark grey/oxblood as the spec requires ("Never black as her colour"). Everything else in the spec passed on inspection — wheels visible and unmistakable in all 4 panels including the rear, cloth fully covers hair, glasses opaque, violet is the sole saturated colour on coat/trousers, no gold V, no jewellery. CTO reviewed and decided: file as-is, no reshoot now (Scene 3 video render has priority on the account's one generation slot); the glove fix is queued.

## Prompt (as pasted, verbatim)
```
@project_absence_loc_hall_big_d — reference for this room's light, floor and wall material only; do not reuse its composition or contents.

A four-panel character reference study laid out in a 2x2 grid on one plain warm studio backdrop: top-left FRONT full body, top-right FACE close-up, bottom-left SIDE profile, bottom-right REAR view. The same character, same outfit, same seated pose, in all four panels — a continuity reference sheet, not a single scene.

THE CHAIR is a retrofuturist ELECTRIC wheelchair. TWO LARGE WHEELS at the rear and TWO SMALL CASTORS at the front — the wheels are unmistakable in every panel: real rims, real tyres, clearly visible from every angle, including the REAR panel where the two large rear wheels are the dominant visual element seen from directly behind. Moulded shell seat in brushed aluminium and cream, softly rounded, 1970s space-age optimism — nothing medical, nothing hospital. A control pod is mounted on the right armrest with real chunky, coloured, mechanical physical push-buttons — no screens, nothing digital. Slim chrome frame, low footplate.

SHE is elderly, small, sitting very upright and completely still, hands resting still on the armrests. A soft cloth is draped over her head and shoulders, covering her hair completely and falling loosely to the collarbone — worn like weather, or like privacy, not religious, not a hood. She wears large dark rectangular smoked glasses, worn indoors, opaque enough that her eyes cannot be read at all. Between the cloth and the lenses almost nothing of her face is legible — only her mouth and jaw are visible. She must read as completely unreadable.

Deep saturated violet is her one colour throughout: the head cloth, a plain long coat, trousers — nothing else on her is violet and nothing of hers is black. Shoes and gloves only are dark grey or oxblood. She wears no jewellery, no fur, no brand marking, no gold — her clothes are plain, well-worn and perfectly kept. She reads as cool, not wealthy, and must not be mistaken for one of the museum's collectors. No gold V mark anywhere on her or the chair — that mark belongs to museum staff alone.

Plain warm studio backdrop with even, neutral lighting appropriate to a character-reference sheet, but the overall palette and light quality echo the referenced hall: warm amber light, whites pushed slightly cool, shadows deep red-brown and never pure black. Terracotta terrazzo studio floor.

The image must look genuinely PHOTOGRAPHED, not rendered: fine film grain, soft halation around the brightest highlights, faint colour fringing at the frame edges. No HDR, no CGI sheen, no lettering, no logos, nothing recognisable or attributable to any real place or brand.
```
