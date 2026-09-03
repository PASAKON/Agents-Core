# Absence — cart-with-painting plate (2026-09-03)

## Why

The film needs Dupe's cart in two states: empty (`project_absence_prop_cart_a`,
CEO-verified) and painting-racked. No wheels+painting cart existed anywhere on
the account — confirmed by a prior worker's full Props sweep (Active + Drafts).
CEO approved exactly ONE paid image generation to make it:
"ถ้าหาไม่เจอ ให้เราสร้างใหม่เลย อนุมัติ 1 รูป".

## References bound

- `@project_absence_prop_cart_a` — the cart (CEO-verified, wheeled).
- `@project_absence_prop_valder_study_b` — the painting (CEO-verified).

Both resolved as green chip thumbnails in the composer before Generate (no red
unresolved text — confirmed via DOM color scan).

## Model / settings

- Model: **GPT Image 2** (Soul Cinema does not accept reference images —
  switched per skill rule).
- Quality: **Medium**, Resolution: **1K** (1024x1024). Started at default
  2K/High = 8.5 credits; stepped down to the standard plate spec, landing at
  **1.5 credits** — in line with this project's normal ~0.2-3 credit range for
  a single plate, so did not need to stop and ask.
- Aspect: Auto (composer defaulted to a 1:1 square; cart_a's own reference
  photo is not perfectly square, so the two plates are close but not
  pixel-identical in framing — noted for CTO review, not a hard-requirement
  miss).

## Prompt used (verbatim, pasted via synthetic ClipboardEvent, no `type()`)

```
@project_absence_prop_cart_a exactly as shown, unchanged in every part: Dupe's cleaning cart with its burnt-orange metal body, chrome tube frame, one red mop head and one cream mop head clipped to the side, an orange plastic bucket holding a folded cloth and a scrub brush, four labelled bottles on the top shelf (Degreaser, Floor Cleaner, Glass Cleaner, and a clear spray bottle), a stack of folded white cloths, a small brush, a folding step-ladder strapped to the right side panel, and a gold letter V on the front panel. The cart stands on its FOUR CASTOR WHEELS, clearly visible, carrying the full weight of the cart -- absolutely no tapered furniture legs, no splayed wooden legs, no feet, no plinth.

The only difference from the reference: @project_absence_prop_valder_study_b, the landscape abstract painting (thin black frame, flat matte geometric blocks of rust red, burnt orange, ochre, cream, sage green and dusty pink with one black wedge shape, no brush texture, no impasto), now stands upright in the cart's front rack, face outward toward camera, held in place by the rack -- not leaning against the cart, not on the floor, not lying flat. The painting is the same size relative to the cart as it is on the wall -- do not enlarge or shrink it.

Same plain off-white seamless studio backdrop as the reference. Same three-quarter side view camera angle as the reference. Same soft even studio lighting as the reference. Same framing and scale as the reference photo, so this image and the reference cut together as one object shown in two states.

ONE cart only, ONE painting only. No people, no room, no museum, no text, no watermark, no other props added, no duplicate carts, no duplicate paintings, no second cart, no second painting.
```

Verified bound before click: `innerText` 1761 chars, `__lexicalTextContent`
1768 chars, first/last 80 chars matched source — no truncation.

## Price actually charged

**1.5 credits**, read directly off the Generate button pixels immediately
before the click (not scraped from DOM text). One generation, one click — no
Rerun, no retries.

## Result

- **New asset generated** in the correct project (`ai-film-festival-3` / "The
  Valder Collection No.7" — confirmed via address bar before firing).
- **Element created** via the detail-modal `...` → Create Element route (per
  skill — never the grid hover menu).
- **Element ID (read off the panel, not guessed): `project_absence_prop_cart_a_painted`**
- Category: Prop. Name: "Dupe cart with painting". Status: Active (just now).
- Downloaded and saved to
  `/Users/gob/Desktop/Fix-1-Elements/project_absence_prop_cart_a_painted.png`
  (converted from the platform's native .webp to .png to match the folder's
  existing convention).

## Verdict — my own read

**Both hard requirements are met:**
- **Four castor wheels**, clearly visible carrying the full cart, confirmed by
  zooming both the left pair and right pair separately — no tapered legs, no
  feet, no plinth.
- **Painting stands upright in the rack**, face outward, visibly held between
  the rack's horizontal rails — not leaning, not flat, not on the floor.
- Every other cart detail (burnt-orange body, chrome frame, both mop heads,
  bucket, four labelled bottles, folded cloths, brush, strapped ladder, gold
  V) matches `cart_a` exactly.
- One cart, one painting, no people/room/museum/text/watermark.
- Off-white backdrop, three-quarter view and lighting match `cart_a` closely.

**One thing to flag for CTO, not a hard-requirement failure:** the composer's
`Auto` aspect defaulted to a 1:1 square crop; `cart_a`'s own photo is not
exactly square, so the two plates are a close but not pixel-perfect framing
match. Flagging per the standing review-loop rule rather than judging it
myself — my read is this is fine for a two-state cutaway, not disqualifying.

This is the org's ONE approved generation for this plate. Not regenerated.
