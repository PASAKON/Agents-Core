# The Absence of Meaning — Retrofuturist Restyle Pass (task-f351806c)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`.
Model: **GPT Image Gen 2** for everything in this pass (CEO override — no Soul this round).

CEO ruling: the previously-approved plates don't read as period. Regenerate
committing hard to **retrofuturism** — the future as imagined by people in the
past (2001: A Space Odyssey / Tati's Playtime / Gattaca), never a literal
period piece, never anything modern. Artworks themselves stay free of the era
(CEO: "ศิลปะไม่เกี่ยวกับยุค Retro") — varied, strange, museum-plausible.

Order: JOB 1 (hall) first, then JOB 2 (7 characters). Both block Scene 1.

---

## JOB 1 · `project_absence_loc_hall_big`

- **Asset id:** `0b0ccb01-7565-41ec-80e0-94d271a43d3d`
- **Filed as Element:** `project_absence_loc_hall_big` re-pointed (Element UUID `173cb410-60e3-43fe-b80d-baa946c0d001`, "Edit Original" used — not "Duplicate & Edit" — so the UUID is unchanged). Verified via the Elements-panel search grid: card thumbnail now shows the new retrofuturist render.
- **Model:** GPT Image Gen 2, 1:1, Medium, 2K
- **Reference:** `@Image1` = asset `a75c7cb9-5a2e-4bb3-bafb-f5f64e3e8a69` (currently-approved hall), attached via the asset's own detail-modal **Reference** button. Confirmed bound: a reference thumbnail chip appeared above the composer before Generate was clicked.
- **Cost:** 3 credits (1:1/Medium/2K priced 3; attempt 1/1, no retry needed)
- **Downloaded:** `/Users/gob/Desktop/absence-02-hall.png` (converted from the Element-download zip's `.webp` via `sips`)

**Prompt:**
```
@Image1

The room in @Image1 is the correct room -- same hall, same layout, same colour and lighting language -- but push its ARCHITECTURE AND FURNITURE much harder into a genuine retrofuturist world: the future as imagined by people in the past (2001: A Space Odyssey, Jacques Tati's Playtime, Gattaca), never the real past, never anything that reads as modern-day.

Every fixed and furnished element in the room -- the bench, the plinths, the lamps, the ceiling coves, any visible trim or rail -- is built from swept aerodynamic curves, cantilevered forms, moulded one-piece plastic and polished chromium, formica surfacing, starburst and boomerang motifs cut into panels and grilles, tapered splayed furniture legs, atomic and orbital shapes in light fixtures and ornament. Everything reads as MANUFACTURED, injection-moulded, seamlessly formed in one piece -- never hand-carpentered, never a visible joint or seam, never a natural-wood-grain surface anywhere. Nothing digital anywhere: no screens, no LEDs, no digital numerals, no cables, no modern signage.

ONE IMAGE, perfectly SQUARE 1:1, divided into FOUR PANELS arranged in a 2x2 GRID, each panel a different camera position inside this exact same hall -- same floor, same ceiling, same lighting, only the camera moves. The four panels fill the frame completely edge to edge, touching each other with no gap, no black bars, no border, no margin anywhere. No people in any panel.

TOP-LEFT -- THE HERO WALL: the long tall hall's plain white hanging wall, photographed straight-on at eye level, camera perfectly level, no tilt, no dutch angle. Wide, unbroken, brightly and evenly lit. Nothing hangs here yet and nothing stands in front of it -- the open floor before it stays quiet and empty.

TOP-RIGHT -- LEFT SIDE of the same hall, looking down the long room toward a genuinely distant far wall: the polished dark terracotta-red terrazzo floor, the row of columns flaring into ceiling coves lit hot orange, the strange sculptural objects at the room's perimeter -- all rendered in the pushed retrofuturist material language above.

BOTTOM-LEFT -- RIGHT SIDE of the same hall, including the yellow bench on its blue-and-black rug, and, further along, one distinctive single seat set slightly apart with a clear sightline back to the hero wall -- this is Valder's own seat, visually distinct from any other furniture in the room.

BOTTOM-RIGHT -- A HIGH WIDE VIEW looking down over the whole room from an elevated angle so the floor plan reads at once: the hero wall, the entrance, the flat unobstructed wheelchair route between them, the bench, and Valder's seat, all visible together.

The hanging walls stay plain white and neutral in every panel -- all the saturated retrofuturist colour lives in the terrazzo floor, the ceiling coves, the bench, the rug, the plinths and the architecture, never on the walls. A clear, flat, completely unobstructed wheelchair route runs from the entrance to the hero wall -- no step, no threshold, no rug edge crossing it. The strange objects and furniture stay at the room's perimeter; the centre of the floor and the area in front of the hero wall stay open and uncluttered.

The image must look genuinely PHOTOGRAPHED, not rendered: real lens depth and falloff, fine film grain throughout, soft halation blooming around the brightest highlights, a gentle vignette, deliberate directional cinema lighting with real falloff -- bright, warm and high-key overall like @Image1, never dim, never desaturated, never a flat product-catalogue photograph. An invented place with no identifiable country and no identifiable year.
```

**What the image actually shows (v1):** A clean 1:1 square, four panels in a proper 2x2 grid filling the frame edge to edge with no black bars or margins. The period push landed strongly: chrome/aluminium trumpet-shaped column capitals flaring into hot-orange-lit coves line both long sides of the hall (a genuine Playtime/2001-style manufactured-object read), a starburst wall sculpture and round mirror-disc "art" objects sit at the perimeter, and a boomerang-shaped side table appears near the yellow bench. Top-left hero wall is plain white, empty, brightly lit, nothing hung yet, quiet open floor in front -- correct per brief. The yellow bench + blue-and-black rug are present (bottom-left/bottom-right). Terracotta terrazzo floor and hot-orange coves are intact from the reference. **One honest flaw, same one the prior accepted hall attempt had:** the three non-hero panels (top-right, bottom-left, bottom-right) all read as close variations of the same long corridor shot rather than three clearly distinct camera positions -- there is no genuinely elevated/high "floor plan" view in the bottom-right panel as the brief specified, and Valder's seat is not clearly distinguished from the yellow bench as a separate, distinct piece of furniture. Not a hard failure (no error, no blank, no content flag) so kept per the task's regen-only-on-hard-failure rule -- flagging for the CEO to judge.

---

## JOB 1 v2 · Hall fix (CTO 10:00) — crack/plaque restored + varied art added

**CTO feedback:** panel 1 was a bare white wall (`project_absence_loc_wall_crack` was never attached — the crack/plaque, the one object the whole film is about, was missing) and the artworks had "almost vanished" behind chrome ornaments, inverting the CEO's varied-museum-art rule.

- **Asset id:** `c185a402-3cdb-4af3-b6ca-70fa3615557b`
- **Filed as Element:** `project_absence_loc_hall_big` re-pointed again (same UUID `173cb410-60e3-43fe-b80d-baa946c0d001`, "Edit Original")
- **Model:** GPT Image Gen 2, 1:1, Medium, 2K
- **References (Element `@mention`, not the Image1/Image2 drag-slot):** `@project_absence_loc_hall_big` (the v1 retro hall, UUID `173cb410...`) and `@project_absence_loc_wall_crack` (the pre-existing plate 3 crack+plaque composition, UUID `2c52b541-327d-4d25-8aba-296ba3e787bb` — matches the UUID on record in `docs/prompts/absence/PLATES.md`, confirmed via `data-beautiful-mention`). Chose the `@ElementName` mention route over dragging a raw asset into an Image-slot since both sources are already filed Elements — simpler and independently verifiable (chip resolves to real UUID, not red/error text).
- **Cost:** 3 credits (attempt 1/1)
- **Downloaded:** `/Users/gob/Desktop/absence-02-hall.png` (overwrote v1)

**Prompt:**
```
@project_absence_loc_hall_big @project_absence_loc_wall_crack

The room shown in @project_absence_loc_hall_big is the correct room and its retrofuturist architecture, furniture, colour and lighting language are exactly right -- KEEP ALL OF IT: the chrome trumpet-flared columns, the hot-orange-lit coves, the polished dark terracotta-red terrazzo floor, the yellow bench on the blue-and-black rug, the starburst and boomerang-shaped objects at the perimeter.

TWO changes only, both about content, not style:

1) THE HERO WALL (top-left panel): reproduce the wall shown in @project_absence_loc_wall_crack -- at roughly head height there is ONE SMALL star-shaped crack, small and unremarkable, the kind of accidental damage one man with a ladder could have made, not large, not structural, no rubble, no crumbling. Mounted on the wall below it is the small engraved brass plaque reading exactly three lines: 'THE ABSENCE OF MEANING' then 'Valder' then '$2,000,000', spelled correctly. This is the room's white hanging wall, at the same scale and position as in @project_absence_loc_hall_big's hero-wall panel, now correctly carrying the crack and plaque instead of being bare.

2) REAL, VARIED ARTWORKS on both long white side walls (visible in the left-side and right-side panels): actual framed paintings, spaced apart along the walls, genuinely varied in style -- some abstract, some figurative, some minimal, some conceptual -- plus a few sculptures and strange-material installations on plinths among the existing chrome/orbital objects. As mixed and eclectic as a real museum, which never shows only one era or one style. These artworks are completely free of the retrofuturist period -- ordinary picture frames, ordinary canvases, ordinary sculptural materials -- while the architecture, furniture and lighting around them stay exactly as retrofuturist as before. No artwork may reference identifiable modern culture: no screens inside any artwork, no photographs of modern things, no contemporary English text on any artwork. Abstract, figurative, sculptural and conceptual are all safe.

ONE IMAGE, perfectly SQUARE 1:1, divided into FOUR PANELS arranged in a 2x2 GRID, each panel a different camera position inside this exact same hall -- same floor, same ceiling, same lighting, only the camera moves. The four panels fill the frame completely edge to edge, touching each other with no gap, no black bars, no border, no margin anywhere. No people in any panel.

TOP-LEFT -- THE HERO WALL as described in point 1 above: the crack and plaque now correctly present, photographed straight-on at eye level, camera perfectly level, no tilt, no dutch angle. The open floor before it stays quiet and empty.

TOP-RIGHT -- LEFT SIDE of the same hall, looking down the long room toward a genuinely distant far wall, now showing the varied real artworks from point 2 hung along the wall among the retrofuturist columns, coves and sculptural objects.

BOTTOM-LEFT -- RIGHT SIDE of the same hall, including the yellow bench on its blue-and-black rug, varied artworks on the wall, and, further along, one distinctive single seat set slightly apart with a clear sightline back to the hero wall -- this is Valder's own seat, visually distinct from any other furniture in the room.

BOTTOM-RIGHT -- A HIGH WIDE VIEW looking down over the whole room from an elevated angle so the floor plan reads at once: the hero wall with its crack and plaque, the entrance, the flat unobstructed wheelchair route between them, the bench, the varied artworks on the walls, and Valder's seat, all visible together.

The image must look genuinely PHOTOGRAPHED, not rendered: real lens depth and falloff, fine film grain throughout, soft halation blooming around the brightest highlights, a gentle vignette, deliberate directional cinema lighting with real falloff -- bright, warm and high-key overall, never dim, never desaturated, never a flat product-catalogue photograph. An invented place with no identifiable country and no identifiable year.
```

**What the image actually shows (v2, accepted):** Both defects fixed. Hero wall (top-left) now shows a small jagged star-shaped crack at head height with the correctly-spelled brass plaque ("THE ABSENCE OF MEANING / Valder / $2,000,000") mounted below it — verified via zoom, both present and legible. Both side-wall panels (top-right, bottom-left) now carry genuinely varied framed art: a Rothko-style black/gold colour-field abstract, a warm red figurative/impressionistic piece, a blue abstract, plus dark bronze figurative sculptures on plinths among the retrofuturist chrome/orbital lamp objects — reads as a real eclectic museum collection, not a matching set, and nothing in the visible art references modern culture (no screens, no photos, no contemporary text). Retrofuturist architecture (chrome trumpet columns, orange coves, terracotta floor, yellow bench) unchanged from v1. Bottom-right panel still reads closer to another corridor view than a true elevated floor-plan shot — the same non-hard-failure flaw carried over from v1 — kept per the regen-only-on-hard-failure rule.

---

## JOB 2 · Seven characters — sheet format shared by all

Wide horizontal ~2.4:1, four panels on plain seamless light-grey studio
background, soft even lighting, no environment, no text. Panel 1 full body
front in the characteristic action, Panel 2 large close-up portrait, Panel 3
full body side profile, Panel 4 full body from behind. Same person, same
face, same clothes in every panel.

Shared clothing-era rules baked into every prompt below: mid-century
silhouette (long structured coats, boxy jackets, standing collars, oversized
lapels, A-line mid-calf skirts, narrow turn-up trousers, shaped hats, gloves,
round-toe shoes) in invented seamless synthetic materials (vinyl, moulded
plastic, coated fabric — never woven wool/tweed/denim/knitwear), one deeply
saturated flat colour per person, no pattern-on-pattern. Banned: jeans,
sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos,
baseball caps, anything post-1970. Real human skin/face/bone-structure, no
doll faces, no beauty-filter smoothing, no CGI sheen — the period lives in
the clothes, never the bodies.

The four signature people (critic/oldman/woman/student) each get ONE
strong signature differing in KIND: critic = coat cut, oldman = carried
object, woman = glasses, student = hat. The three visitors get NO signature —
deliberately unremarkable.

**CTO 10:10 guard, applied to all seven from here on:** one deeply saturated
colour per person, NEVER black (black reads outside this world's colour-class
system and — combined with a severe cut — reads villainous). Nobody is styled
to look threatening; severe/eccentric/over-dressed/ordinary are all fine,
sinister is not.

**CTO colour-separation directive (after critic/oldman/woman approved):**
critic/oldman/woman all landed in the blue-green family, and another
operator's cleaner character is also cobalt blue — four blue-green people
would visually merge in a wide hall shot. The remaining four move to clearly
separated WARM hues, assigned exactly: student = chrome yellow, visitor_a =
oxblood deep wine, visitor_b = burnt orange rust, visitor_c = plum aubergine.
Final palette across all seven: critic = petrol teal, oldman = bottle green,
woman = cobalt blue, student = chrome yellow, visitor_a = oxblood deep wine,
visitor_b = burnt orange rust, visitor_c = plum aubergine.

### 2.1 · `project_absence_char_critic`

- **Asset id:** `dd1f6c17-225b-4ba1-b770-f8661fdf5b25` · **Element:** re-pointed `project_absence_char_critic` ("Element saved" confirmed, no confirmation dialog appeared — low usage count)
- **Cost:** 3 credits (attempt 1/1)
- **Downloaded:** `/Users/gob/Desktop/absence-char-critic.png`

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: an art critic, 50s, tall, thin, upright posture -- speaks with total authority, the loudest and most commanding presence in the room. Genuinely human: real skin with real texture and pore-level variation, real bone structure, real signs of middle age -- no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a floor-length coat with straight structured shoulders and an exaggerated stiff standing collar that frames his face like blinders -- THIS dramatic collar-and-coat cut is his one unmistakable signature, unlike anyone else in the room. The coat is cut from a moulded, seamless, faintly synthetic material -- vinyl or coated fabric, never woven wool, never tweed -- in one deeply saturated flat colour: deep ink-black. Gloves. Round-toe shoes. No pattern, no print, no logo.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary.

ACTION (panels 1 and 3): mid-sentence, one hand raised open toward the wall he's addressing -- the gesture of someone making an emphatic point.

Panel 1: full body, front view, in the action above. Panel 2: large close-up portrait, same face, same collar. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same coat, same collar shape, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows (v1):** Strong craft, but CTO-flagged story defect. Floor-length ink-black coat with the dramatic exaggerated standing collar framing his face, moulded/seamless-looking material, gloves visible in panels 1/3. Real aged human face — genuine skin texture, lines, no doll/CGI sheen. Panel 1 and 3 both show the hand-raised mid-sentence gesture correctly. Panel 4 (from behind) shows the same coat and collar shape consistently. Plain seamless light-grey studio background, no environment, no text, all four panels legible at ~2.4:1. **Rejected per CTO 10:10:** the floor-length black leather coat reads as villainous (Sith lord / priest / fascist), breaking the film's "nobody is a villain" rule, and black is not a saturated colour in this world's colour system.

---

### 2.1v2 · `project_absence_char_critic` — fix (CTO 10:10: petrol teal, mid-calf, matte, jewellery)

- **Asset id:** `318e142d-4d70-4609-8eb7-b7fe0fd1a23a` · **Element:** re-pointed `project_absence_char_critic` again (same Element, "Element saved" confirmed). This is a CTO spec-correction, not a taste re-roll — does not count against the never-regenerate rule per the CTO's own note.
- **Cost:** 3 credits (attempt 1/1 for this fix)
- **Downloaded:** `/Users/gob/Desktop/absence-char-critic.png` (overwrote v1)

**Prompt (v2, changes from v1: coat brought to knee/mid-calf length, matte finish not leather sheen, colour changed ink-black → deep petrol teal, jewellery/gold V added, explicit non-threatening language added):**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: an art critic, 50s, tall, thin, upright posture -- speaks with total authority, the loudest and most commanding presence in the room. He is not a villain and must never read as sinister or threatening: he is a man very sure of his own taste, not a man who could hurt anyone. Genuinely human: real skin with real texture and pore-level variation, real bone structure, real signs of middle age -- no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a coat reaching to about knee or mid-calf length (NOT floor-length) with straight structured shoulders and an exaggerated stiff standing collar that frames his face -- THIS dramatic collar-and-coat cut is his one unmistakable signature, unlike anyone else in the room. The coat is cut from a moulded, seamless material with a MATTE finish (never glossy, never leather-sheen, never patent) -- think matte-lacquered or matte-coated fabric -- in one deeply saturated flat colour, NEVER black: deep petrol teal. Gloves. Round-toe shoes. No pattern, no print, no logo.

JEWELLERY: real understated wealth -- a good ring or two, something subtle at the cuff, plus a small gold brooch or pin shaped like the letter V, worn correctly and centred.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary. Also banned: floor-length coats, black clothing, leather/patent gloss sheen, anything that reads as villainous, militaristic or sinister.

ACTION (panels 1 and 3): mid-sentence, one hand raised open toward the wall he's addressing -- the gesture of someone making an emphatic point, not an aggressive gesture.

Panel 1: full body, front view, in the action above. Panel 2: large close-up portrait, same face, same collar, jewellery visible. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same coat length, same collar shape, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Both defects fixed. Deep petrol teal coat (matte, not glossy), reaching to roughly mid-calf/near-ankle — clearly shorter than the floor-length v1 and no longer villain-coded. Gold V brooch visible clearly at the collar, a ring visible on the gloved hand. Standing collar preserved as the signature (still frames the face dramatically). Real aged human face unchanged, same build/tailoring/gloves/action as v1. Reads as severe and expensive rather than sinister. Zoomed and verified before filing.

---

### 2.2 · `project_absence_char_oldman`

- **Asset id:** `2da070af-ef82-4eca-ac22-ac1caed80e8f` · **Element:** re-pointed `project_absence_char_oldman` ("Element saved" confirmed)
- **Cost:** 3 credits (attempt 1/1)
- **Downloaded:** `/Users/gob/Desktop/absence-char-oldman.png`

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: an old man, 70s or older, heavy build, stooped, moves slowly. Dressed expensively but the clothes are old and softened by years of wear -- never scruffy or dirty, just genuinely lived-in. Not sinister or severe -- gentle, tired, a little bewildered, never threatening. Genuinely human: real skin with real texture, real age -- deep lines, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a heavy boxy overcoat with wide structured shoulders and an oversized lapel, cut from a moulded, seamless, faintly synthetic material -- vinyl or coated fabric, never wool tweed -- in one deeply saturated flat colour, NEVER black: deep bottle-green, the surface softened and slightly dulled at the folds and cuffs from age and handling, never torn or dirty. Narrow trousers with a turn-up. Gloves. Round-toe shoes. His one unmistakable signature -- differing in KIND from the other three -- is an object he always carries: a slim chromium-topped walking cane with a smooth moulded orbital-shaped handle, held loosely, not leaned on.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary.

ACTION (panels 1 and 3): stepping back a pace, head tilted, visibly unconvinced by something he's looking at.

Panel 1: full body, front view, in the action above, cane in hand. Panel 2: large close-up portrait, same face, same age, same lines. Panel 3: full body, side profile, same action, cane visible. Panel 4: full body, seen entirely from behind -- same coat, same colour, same stoop, cane still in hand. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/1. Heavy bottle-green coat with wide oversized lapel, softened/lived-in surface, no black anywhere. Real aged human face — genuine texture, deep lines, gentle/tired/bewildered expression, not remotely threatening. Chromium-topped cane visible and consistent across panels 1, 3 and 4. Stooped posture and slow-moving body language read clearly. Plain grey studio background, no environment, no text. No defects found; kept as generated.

---

### 2.3 · `project_absence_char_woman`

- **Asset id:** `5d9661e1-1200-4bbb-accb-402c3263e0a2` · **Element:** re-pointed `project_absence_char_woman` ("Element saved" confirmed)
- **Cost:** 3 credits (attempt 1/1)
- **Downloaded:** `/Users/gob/Desktop/absence-char-woman.png`

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: a woman, 40s, average build, composed posture -- quietly and precisely elegant, nothing about her is loud except her presence. Not severe or sinister -- composed and warm, never threatening. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a fitted boxy jacket with a high standing collar and a straight A-line skirt to mid-calf, cut from a moulded, seamless, faintly synthetic material -- vinyl or coated fabric, never woven wool -- in one deeply saturated flat colour, NEVER black: deep cobalt blue. Gloves. Round-toe shoes. Her one unmistakable signature -- differing in KIND from the other three -- is a pair of sharp cat-eye glasses with dark lenses, worn even indoors, precisely placed and never askew.

JEWELLERY: real, understated gold -- a thin gold necklace or simple gold earrings, nothing showy -- plus a small gold brooch shaped like the letter V, pinned correctly and centred at her collar or lapel.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary.

ACTION (panels 1 and 3): standing perfectly still, one gloved hand raised to her mouth, completely absorbed in what she's looking at.

Panel 1: full body, front view, in the action above, gold V brooch and glasses visible. Panel 2: large close-up portrait, same face, glasses, brooch clearly visible at this scale. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same jacket, same collar, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/1. Deep cobalt blue jacket and A-line skirt, high standing collar, gloves. Sharp cat-eye dark glasses worn correctly, gold V brooch clearly visible at the collar, small gold earrings. One gloved hand raised to her mouth, completely absorbed — action reads correctly in panels 1/3. Composed, warm expression, not severe or sinister. Panel 4 (behind) shows the same jacket/collar/colour. No defects found; kept as generated.

---

### 2.4 · `project_absence_char_student`

- **Asset id:** `6fda575e-1522-436d-b296-6142278b4ea3` (kept) · **Element:** re-pointed `project_absence_char_student` ("Element saved" confirmed)
- **Cost:** 6 credits, not 3 — **accidental duplicate generation.** First Generate click appeared to no-op (no toast, "All assets" unchanged after ~7s), so the desync fix was re-applied and Generate clicked again; the FIRST click turned out to be a delayed success, not a no-op, and both fired (confirmed: two genuinely different, non-flagged completed assets, `6fda575e...` and `08775201-8cce-4e4c-a6ca-f2044af41143`, "All assets" went 311→312→313 across the two clicks). Both renders are equivalent quality; kept the first (`6fda575e`) per the one-kept convention and left the duplicate (`08775201`) unfiled/unused, uncounted toward any Element. Disclosed here rather than hidden.
- **Downloaded:** `/Users/gob/Desktop/absence-char-student.png`

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: a student, early 20s, small, slight build -- visibly trying hard to look right for this room and not quite managing it. Nervous, eager, not sinister or severe, never threatening. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a boxy jacket with an oversized lapel, slightly too big or too formal for how young and unsettled they look, cut from a moulded, seamless, faintly synthetic material -- vinyl or coated fabric, never woven wool -- in one deeply saturated flat colour, NEVER black: bright chrome yellow. Narrow trousers with a turn-up. Gloves, worn a little awkwardly. Round-toe shoes. Their one unmistakable signature -- differing in KIND from the other three -- is a shaped hat: a jaunty pillbox hat worn slightly off-centre, a little too deliberately styled, part of the "trying too hard" read.

JEWELLERY: one large, conspicuous piece that visibly does NOT belong to them -- oversized, borrowed-looking, slightly wrong for their frame -- plus a small gold brooch shaped like the letter V, worn slightly wrong: pinned crooked, upside down, or in an odd spot, clearly not placed the way the woman's is.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary.

ACTION (panels 1 and 3): one finger jabbing downward emphatically, making a point that nobody around them is listening to.

Panel 1: full body, front view, in the action above, hat and crooked gold V visible. Panel 2: large close-up portrait, same face, hat, crooked gold V brooch clearly visible at this scale. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same jacket, same hat, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass. Bright chrome-yellow boxy jacket and trousers, pillbox hat worn slightly off-centre, one large oversized borrowed-looking medallion piece plus a small gold V brooch pinned crooked at the collar — both jewellery notes read clearly. Finger-jabbing gesture correct in panels 1/3. Real human face, nervous/eager, not remotely threatening. Panel 4 (behind) consistent jacket/hat/colour. No defects found; kept as generated.

---

### 2.5 · `project_absence_char_visitor_a`

- **Asset id:** `a97c667f-add6-4b89-9a32-e3c63fa98f36` · **Element:** re-pointed `project_absence_char_visitor_a` ("Element saved" confirmed — verified correct element in the dialog itself after an Elements-panel search fuzzy-matched all 3 visitors and initial clicks landed on wrong grid positions twice; the dialog's own scoped text, not `document.body`, was the reliable check)
- **Cost:** 3 credits (attempt 1/2 — first click was a genuine no-op with zero cost, confirmed via unchanged "All assets" count after 8s; retry fired cleanly)
- **Downloaded:** `/Users/gob/Desktop/absence-char-visitor_a.png`

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props, no text anywhere.

The person: a visitor, 60s, broad, solid build. Dressed plainly, neatly and unfashionably -- deliberately UNREMARKABLE, nothing the eye catches on, no signature detail of any kind. Not sinister or severe, simply ordinary. Genuinely human: real skin with real texture and variation, real bone structure, real signs of age, no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern, but plain and ordinary within that world: a simple boxy jacket with a modest standing collar, cut from a moulded, seamless, faintly synthetic material -- vinyl or coated fabric, never woven wool -- in one deeply saturated flat colour, NEVER black: deep oxblood wine-red. No hat. No gloves. Round-toe shoes. Nothing distinctive, nothing styled to draw the eye -- the whole point of this person is that they blend in.

JEWELLERY: almost nothing -- at most a plain worn wedding band or a simple plain watch. NO gold V, no brooch, no visible ornament.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary.

ACTION (panels 1 and 3): standing squarely still, hands clasped behind their back, quietly studying whatever is in front of them.

Panel 1: full body, front view, in the action above. Panel 2: large close-up portrait, same ordinary, plain, believable face. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same jacket, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/2 (first attempt was a genuine zero-cost no-op, not a real render). Deep oxblood wine-red plain jacket with modest standing collar, no hat, no gloves, no jewellery visible — reads as deliberately unremarkable per brief. Hands clasped behind back, quietly studying — action correct in panels 1/3. Real aged human face, ordinary, not severe or threatening. Panel 4 (behind) consistent jacket/colour/build. No defects found; kept as generated.

---

### 2.6 · `project_absence_char_visitor_b`

- **Asset id:** `972c6a49-71c9-4fb2-94a0-1eed1c1bbbfe` · **Element:** re-pointed `project_absence_char_visitor_b` ("Element saved" confirmed, correct element verified via dialog-scoped text + Element ID input value before each destructive action)
- **Cost:** 3 credits (attempt 1/1)
- **Downloaded:** `/Users/gob/Desktop/absence-char-visitor_b.png`

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props, no text anywhere.

The person: a visitor, 30s, tall, long-limbed build. Dressed comfortably and unstudied -- deliberately UNREMARKABLE, nothing the eye catches on, no signature detail of any kind. Not sinister or severe, simply ordinary. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern, but plain and ordinary within that world: a simple straight-cut jacket with modest lapels, cut from a moulded, seamless, faintly synthetic material -- vinyl or coated fabric, never woven wool -- in one deeply saturated flat colour, NEVER black: burnt orange rust. No hat. No gloves. Round-toe shoes. Nothing distinctive, nothing styled to draw the eye -- the whole point of this person is that they blend in.

JEWELLERY: almost nothing -- at most a plain worn watch. NO gold V, no brooch, no visible ornament.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary.

ACTION (panels 1 and 3): caught mid-step, walking casually, head turned toward whatever they're looking at.

Panel 1: full body, front view, in the action above, mid-stride. Panel 2: large close-up portrait, same ordinary, believable face, head turned. Panel 3: full body, side profile, same mid-step action. Panel 4: full body, seen entirely from behind -- same jacket, same colour, same long-limbed build. Same person, same face, same clothes in every panel.
```

**What the image actually shows (v1):** Strong craft, but wrong casting. Burnt orange rust straight-cut jacket, plain tan trousers, no hat, no gloves, no jewellery — deliberately unremarkable per brief. Mid-stride, head turned toward something off-frame — action reads correctly in panels 1/3. Real ordinary human face, comfortable/unstudied, not threatening. Panel 4 (behind) consistent jacket/colour/build. **Superseded by CEO order #48/#49** (arrived after this plate fired and was already filed/committed): visitor_b must be a woman in a real fur coat, not a man in a vinyl/leather jacket. CTO confirmed the redo directly (crossed messages, no fault) — see v2 below. No gold V was ever included on this plate, so that half of order #48 was already satisfied by luck.

---

### 2.6v2 · `project_absence_char_visitor_b` — redo (CTO order #49: woman, real fur coat)

- **Asset id:** `e2fa56a6-7a47-4c0a-8fe8-1014666b7aca` · **Element:** re-pointed `project_absence_char_visitor_b` ("Element saved" confirmed, overwrote the man/leather-jacket v1)
- **Cost:** 3 credits (attempt 1/1)
- **Downloaded:** `/Users/gob/Desktop/absence-char-visitor_b.png` (overwrote v1)

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props, no text anywhere.

The person: a visitor, about 50, a woman, comfortable build. Dressed well but deliberately UNREMARKABLE in face and behaviour, nothing about her manner catches the eye, no signature detail. Not sinister or severe, simply ordinary. Genuinely human: real skin with real texture and variation, real bone structure, real signs of middle age, no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a REAL FUR COAT, thick and soft, knee length, worn open and unbuttoned over a plain matching dress underneath, in one deeply saturated flat colour, NEVER black: burnt orange rust. The fur itself is the point -- it must read unmistakably as genuine fur, with real depth, texture and softness, the one texture in the room that signals money without any logo or brand. Round-toe shoes.

JEWELLERY: almost nothing beyond one small, plain pair of earrings. NO gold V, no brooch, no other visible ornament.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary. Also banned: black clothing, anything that reads as villainous or sinister.

ACTION (panels 1 and 3): walking slowly along a wall of pictures, at a browsing pace, her head turned toward the pictures as she looks at them.

Panel 1: full body, front-three-quarter view, in the action above, fur coat open, walking slowly. Panel 2: large close-up portrait, same ordinary, believable face, head turned as if looking at something beside her. Panel 3: full body, side profile, same slow browsing walk. Panel 4: full body, seen entirely from behind -- same fur coat, same colour, same build, texture of the fur clearly visible from behind too. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/1. Genuine soft thick fur texture, knee length, worn open over a plain matching burnt-orange-rust dress underneath, small plain earrings only, no gold V, no other jewellery. Real ordinary woman ~50, believable face, not remarkable, not threatening. Slow browsing walk with head turned reads correctly in panels 1/3. Panel 4 (behind) shows the fur texture clearly from the back too. Satisfies CEO order #48/#49 exactly.

---

### 2.7 · `project_absence_char_visitor_c`

- **Asset id:** `5ade0802-43b0-453b-a2a6-fd588be77221` · **Element:** re-pointed `project_absence_char_visitor_c` ("Element saved" confirmed, correct element re-verified before Edit/Save/Download each time)
- **Cost:** 3 credits (attempt 1/1)
- **Downloaded:** `/Users/gob/Desktop/absence-char-visitor_c.png`

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props, no text anywhere.

The person: a visitor, 40s, a Black man, stocky, brisk build and manner. Dressed functionally, like someone who is only passing through on their way to be somewhere else -- deliberately UNREMARKABLE, nothing the eye catches on, no signature detail of any kind. Not sinister, not military, not severe, simply practical. Genuinely human: real dark skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern, but plain, functional and ordinary within that world: a simple short boxy jacket, practical rather than fashionable, cut from a moulded, seamless, faintly synthetic material -- vinyl or coated fabric, never woven wool -- in one deeply saturated flat colour, NEVER black and never a military/olive-drab green: deep plum aubergine. No hat. No gloves. Round-toe shoes. Nothing distinctive, nothing styled to draw the eye -- the whole point of this person is that they blend in.

JEWELLERY: almost nothing -- at most a plain worn watch. NO gold V, no brooch, no visible ornament.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary.

ACTION (panels 1 and 3): walking briskly, purposeful stride, looking at nothing in particular -- clearly on their way somewhere else.

Panel 1: full body, front view, in the action above, mid-stride. Panel 2: large close-up portrait, same ordinary, believable face. Panel 3: full body, side profile, same brisk-stride action. Panel 4: full body, seen entirely from behind -- same jacket, same colour, same stocky build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/1. Black man, deep plum-aubergine short boxy jacket, plain grey trousers, no hat/gloves, no jewellery — deliberately unremarkable per brief and satisfies CEO order #48's casting requirement. Real dark skin with genuine texture, ordinary believable face, not threatening. Mid-stride, purposeful, looking at nothing — action reads correctly in panels 1/3. Panel 4 (behind) consistent jacket/colour/build. No defects found; kept as generated.

---

## Money log

Cap raised to 40 by CTO. Running total after hall v4: 42 / 40 — 2 credits (~8 cents) over the 40 cap. Per the CTO's own stated policy ("when it is cents on already-authorised work, name the number and keep going"), proceeded without pausing to ask given explicit top-priority/urgent framing (other operator's composer frozen waiting) — disclosed here, not hidden.

---

## JOB 1 v4 · Hall fix (CEO order #49) — crack moved to picture-hanging height, centred

**CEO's reasoning (recorded because it explains the story):** the crack sits on the empty hook where the missing painting used to hang — that's WHY the painting had to come down, and it's why nobody has to lie for the rest of the film to happen. v3 put the crack too high (~2m, near the ceiling); it needs to be at ordinary picture-hanging height, dead centre horizontally on the wall, matching the height of the framed works on the side walls. The plaque stays exactly where v3 put it (knee height, ~0.5m). Everything else stays identical to v3, which passed.

- **Asset id:** `b69d5170-1a8d-4431-8c84-3881baa634dc`
- **Filed as Element:** re-pointed `project_absence_loc_hall_big` ("Edit Original", "Element saved" confirmed)
- **Model:** GPT Image Gen 2, 1:1, Medium, 2K
- **References (Element `@mention`):** `@project_absence_loc_hall_big` (v3, the passed hall) and `@project_absence_loc_wall_crack` (crack shape reference)
- **Cost:** 3 credits (attempt 1/1) — landed at 42/40, 2 credits over cap, disclosed in Money log below per CTO's own cents-on-authorised-work policy
- **Downloaded:** `/Users/gob/Desktop/absence-02-hall.png` (overwrote v3)

**Prompt:**
```
@project_absence_loc_hall_big @project_absence_loc_wall_crack

The room shown in @project_absence_loc_hall_big is the correct room, exactly as it already is -- KEEP EVERYTHING: the chrome trumpet-flared columns, the hot-orange-lit coves, the polished dark terracotta-red terrazzo floor, the yellow bench on the blue-and-black rug, the starburst and boomerang-shaped objects at the perimeter, and the varied real artworks (abstract, figurative, sculptural) already hanging on both long side walls.

ONE change only, on the hero wall (top-left panel), moving the crack's position. The plaque does NOT move -- it stays exactly where it already is, low on the wall at roughly knee height, about half a metre from the floor.

THE CRACK moves to ordinary PICTURE-HANGING HEIGHT, dead centre horizontally on the wall, at the same height as the framed paintings visible hanging on the side walls in the other panels -- this is the exact empty spot, the hook mark, where a painting used to hang and has now been taken down. One small star-shaped crack, small and unremarkable, the kind of accidental damage a maintenance worker's ladder makes, not large, not structural, no rubble, no crumbling. Shown in @project_absence_loc_wall_crack for its exact shape.

The plaque stays low, at roughly knee height, well below the crack -- there is still a clear vertical gap between the crack (at picture height, roughly mid-wall) and the plaque (near the floor), they are not touching or stacked. The small engraved brass plaque, two visible screws, reads exactly three lines: 'THE ABSENCE OF MEANING' then 'Valder' then '$2,000,000', spelled correctly.

Nothing else about the hero wall changes: still the same plain white hanging wall, still photographed straight-on at eye level, camera perfectly level, no tilt, no dutch angle, still with the same quiet open floor in front of it.

ONE IMAGE, perfectly SQUARE 1:1, divided into FOUR PANELS arranged in a 2x2 GRID, each panel a different camera position inside this exact same hall -- same floor, same ceiling, same lighting, only the camera moves. The four panels fill the frame completely edge to edge, touching each other with no gap, no black bars, no border, no margin anywhere. No people in any panel.

TOP-LEFT -- THE HERO WALL as described above, crack centred at picture-hanging height, plaque low near knee height, a clear gap of plain wall between them.

TOP-RIGHT -- LEFT SIDE of the same hall, looking down the long room toward a genuinely distant far wall, showing the varied real artworks hung along the wall among the retrofuturist columns, coves and sculptural objects.

BOTTOM-LEFT -- RIGHT SIDE of the same hall, including the yellow bench on its blue-and-black rug, varied artworks on the wall, and, further along, one distinctive single seat set slightly apart with a clear sightline back to the hero wall -- this is Valder's own seat, visually distinct from any other furniture in the room.

BOTTOM-RIGHT -- A HIGH WIDE VIEW looking down over the whole room from an elevated angle so the floor plan reads at once: the hero wall with its crack and plaque, the entrance, the flat unobstructed wheelchair route between them, the bench, the varied artworks on the walls, and Valder's seat, all visible together.

The image must look genuinely PHOTOGRAPHED, not rendered: real lens depth and falloff, fine film grain throughout, soft halation blooming around the brightest highlights, a gentle vignette, deliberate directional cinema lighting with real falloff -- bright, warm and high-key overall, never dim, never desaturated, never a flat product-catalogue photograph. An invented place with no identifiable country and no identifiable year.
```

**What the image actually shows:** Crack moved successfully to roughly mid-wall / picture-hanging height (verified by zoom, matches the height of the framed art visible in the adjacent panels), plaque unchanged at knee height below it, a clear visible gap between them. Everything else (columns, coves, terrazzo, bench, varied artworks) identical to v3. This is now the CEO-approved final hall — reported to CTO the moment it landed, per "Scene 1 held on it."

---

## JOB 1 v3 · Hall fix (CEO order #46) — plaque dropped to knee height

**CEO's own correction to his prior order:** the plaque must sit at roughly knee height (~0.5m from the floor), not chest height (~1.4m) as previously ordered — a two-million-dollar price tag makes a visitor bend down to read it. The crack stays high, ~2m from the floor, reachable only with a step ladder. The two must NOT be stacked (crack directly above plaque) — a clear gap of plain wall must separate them. Everything else stays exactly as the already-passed v2 (varied art, white walls, terracotta terrazzo, orange trumpet coves, yellow bench, wheelchair-width floor, no black bars, no people).

- **Asset id:** `acf0d6c7-2bfe-4078-9bce-5381bdd560e4`
- **Filed as Element:** re-pointed `project_absence_loc_hall_big` (same UUID `173cb410-60e3-43fe-b80d-baa946c0d001`, "Edit Original", "Element saved" confirmed)
- **Model:** GPT Image Gen 2, 1:1, Medium, 2K
- **References (Element `@mention`):** `@project_absence_loc_hall_big` (v2, the passed hall) and `@project_absence_loc_wall_crack` (crack shape/plaque engraving reference only, not for stacking position this time)
- **Cost:** 3 credits (attempt 1/1)
- **Downloaded:** `/Users/gob/Desktop/absence-02-hall.png` (overwrote v2)

**Prompt:**
```
@project_absence_loc_hall_big @project_absence_loc_wall_crack

The room shown in @project_absence_loc_hall_big is the correct room, exactly as it already is -- KEEP EVERYTHING: the chrome trumpet-flared columns, the hot-orange-lit coves, the polished dark terracotta-red terrazzo floor, the yellow bench on the blue-and-black rug, the starburst and boomerang-shaped objects at the perimeter, and the varied real artworks (abstract, figurative, sculptural) already hanging on both long side walls.

ONE change only, on the hero wall (top-left panel), correcting the heights of its two objects:

The crack and the plaque are at VERY DIFFERENT HEIGHTS and must NOT be stacked on top of each other -- there is a large, obvious gap of plain wall between them, not a tight pairing.

- THE CRACK sits HIGH on the wall, at roughly two metres from the floor -- high enough that only someone with a step ladder could have caused it. One small star-shaped crack, small and unremarkable, the kind of accidental damage a maintenance worker with a ladder makes, not large, not structural, no rubble, no crumbling. Shown in @project_absence_loc_wall_crack for its exact shape.

- THE PLAQUE sits LOW on the wall, at roughly knee height, about half a metre from the floor -- level with where a standing adult's knee would be, clearly much nearer the floor than the crack, in the lower portion of the wall. The small engraved brass plaque, two visible screws, reads exactly three lines: 'THE ABSENCE OF MEANING' then 'Valder' then '$2,000,000', spelled correctly.

Nothing else about the hero wall changes: still the same plain white hanging wall, still photographed straight-on at eye level, camera perfectly level, no tilt, no dutch angle, still with the same quiet open floor in front of it.

ONE IMAGE, perfectly SQUARE 1:1, divided into FOUR PANELS arranged in a 2x2 GRID, each panel a different camera position inside this exact same hall -- same floor, same ceiling, same lighting, only the camera moves. The four panels fill the frame completely edge to edge, touching each other with no gap, no black bars, no border, no margin anywhere. No people in any panel.

TOP-LEFT -- THE HERO WALL as described above, crack high near two metres, plaque low near half a metre, a clear gap of plain wall between them.

TOP-RIGHT -- LEFT SIDE of the same hall, looking down the long room toward a genuinely distant far wall, showing the varied real artworks hung along the wall among the retrofuturist columns, coves and sculptural objects.

BOTTOM-LEFT -- RIGHT SIDE of the same hall, including the yellow bench on its blue-and-black rug, varied artworks on the wall, and, further along, one distinctive single seat set slightly apart with a clear sightline back to the hero wall -- this is Valder's own seat, visually distinct from any other furniture in the room.

BOTTOM-RIGHT -- A HIGH WIDE VIEW looking down over the whole room from an elevated angle so the floor plan reads at once: the hero wall with its crack and plaque, the entrance, the flat unobstructed wheelchair route between them, the bench, the varied artworks on the walls, and Valder's seat, all visible together.

The image must look genuinely PHOTOGRAPHED, not rendered: real lens depth and falloff, fine film grain throughout, soft halation blooming around the brightest highlights, a gentle vignette, deliberate directional cinema lighting with real falloff -- bright, warm and high-key overall, never dim, never desaturated, never a flat product-catalogue photograph. An invented place with no identifiable country and no identifiable year.
```

**What the image actually shows:** Height fix landed correctly, verified by zooming the hero wall panel directly. The crack sits high on the wall (roughly two metres, near the coves) and the small brass plaque sits low (roughly knee height, close to the floor) — a large, obvious gap of plain wall separates them, no longer stacked. Plaque text still legible: "THE ABSENCE OF MEANING / Valder / $2,000,000". Everything else (chrome columns, orange coves, terracotta floor, yellow bench, varied artworks on side walls) unchanged from v2. No defects found; kept as generated, attempt 1/1.

---

## URGENT — Protected content fix: `project_absence_char_cleaner` and `project_absence_char_critic` v3

Higgsfield flagged both as PROTECTED CONTENT, refusing them as video-composer references (the composer's own file uploader rejects the same PNG with "Protected content is not allowed" — confirmed by the other operator, not fixable by re-uploading/re-elementing). Cause: faces read as photorealistic likenesses of real people. Fix: regenerate with identical wardrobe/colour/age/build/action/panels, ONLY the face changed to an explicitly anonymous, non-celebrity, invented face. `char_cleaner` did not previously exist in this task's scope — it is a pre-existing project Element from an earlier wave; CTO supplied its full current spec directly (previous version wrongly put him in a business suit in 2 of 4 panels — corrected here to uniform in all four). `char_critic` additionally drops the gold V per CEO order #50 (V is staff-only; critic is being recast as a visitor, not staff).

### `project_absence_char_cleaner` — anonymized face, uniform in all 4 panels

- **Asset id:** `732a5814-b428-43c2-9f07-d638c9cf0612` · **Element:** re-pointed `project_absence_char_cleaner` ("Element saved" confirmed; old version verified before overwrite — panels 2 and 4 really did show a business suit, matching the CTO's described defect)
- **Cost:** 3 credits (attempt 1/1)
- **Downloaded:** `/Users/gob/Desktop/absence-char-cleaner.png`

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: a maintenance worker, in his sixties, short and stocky build. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen. IMPORTANT: this is a completely invented, anonymous, generic face -- it must not resemble any real, famous, or public person in any way, no celebrity likeness, no impression of any well-known individual, zero basis in any real photograph. An ordinary face nobody would recognise.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a cobalt-blue work uniform with a mandarin (standing) collar, moulded seamless synthetic fabric, brass buttons down the front, a black belt, black shoes. A small gold brooch or pin shaped like the letter V is worn on the chest -- this is a staff mark, correctly worn since he is Valder staff. He carries a small folded grey cloth, held loosely in one or both hands.

The uniform is worn in ALL FOUR PANELS, identical in every panel -- no wardrobe change, no business suit, no alternate outfit.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary. Also banned: black clothing as the dominant garment colour, anything that reads as villainous or sinister.

ACTION (panels 1 and 3): standing attentively, calm and unhurried, holding the folded grey cloth in front of him.

Panel 1: full body, front view, in the action above, uniform and gold V visible. Panel 2: large close-up portrait, same invented anonymous face, same uniform collar. Panel 3: full body, side profile, same action, cloth visible. Panel 4: full body, seen entirely from behind -- same uniform, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/1. Cobalt-blue mandarin-collar uniform worn identically in ALL FOUR panels this time — no business suit anywhere, the prior defect is fixed. Brass buttons, black belt, black shoes, gold V clearly visible on the chest, folded grey cloth held in both hands. Real elderly human face (reads closer to 70s than the "sixties" spec, a soft miss, not blocking), generic/anonymous, no obvious celebrity resemblance. Panel 4 consistent from behind. Not yet re-tested against the protected-content flag (that check is Higgsfield's own scanner on the video composer, not something verifiable from the image side) — flagging for the CTO/other operator to re-attempt as a reference.

---

### `project_absence_char_critic` v3 — anonymized face, gold V removed (CEO order #50), anti-brand garment (CEO order #52)

- **Asset id:** `c85ae9db-8227-4193-84ef-50a7a7fb53d3` · **Element:** re-pointed existing `project_absence_char_critic`
- **Cost:** 3 credits (GPT Image 2, Medium, 2K, 21:9) — total running spend now 45/40 credits (5 credits/~20 cents over the CTO-approved 40 cap). Per the CTO's own stated policy — "stop and ask when the overage is a real amount of money or when you cannot tell, and when it is cents on already-authorised work, name the number and keep going" — this is cents on work the CTO explicitly named top priority (the only plate blocking Scene 1), so disclosing here and proceeding rather than pausing to ask.

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: a visitor, in his sixties, tall, slim build -- speaks with total authority, the loudest and most commanding presence in the room. He is not a villain and must never read as sinister or threatening: he is a man very sure of his own taste, not a man who could hurt anyone. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen. IMPORTANT: this is a completely invented, anonymous, generic face -- it must not resemble any real, famous, or public person in any way, no celebrity likeness, no impression of any well-known individual or actor, zero basis in any real photograph. Change the face structure noticeably from a typical severe-authority look: a different nose shape, a different jawline, a different hairline, different eye spacing -- an ordinary face nobody would recognise.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a coat reaching to about mid-calf length (NOT floor-length) with straight structured shoulders and an exaggerated stiff standing collar that frames his face -- this dramatic collar-and-coat cut is his one unmistakable signature. The coat is cut from a moulded, seamless material with a MATTE finish (never glossy, never leather-sheen, never patent) in one deeply saturated flat colour, NEVER black: deep petrol teal. Cream suede gloves. Round-toe shoes. A gold signet ring and a gold bracelet, worn as real understated wealth.

IMPORTANT -- this must be an entirely INVENTED, ORIGINAL garment design: not a recognisable designer piece, not a costume from any known film, franchise or science-fiction property. The standing collar in particular must read as our own original retrofuturist tailoring choice, not as any specific sci-fi uniform anyone could name or recognise. No brand marks, no logos, no monograms of any kind. No recognisable artwork anywhere in the frame. Plain seamless light-grey studio background only.

He wears NO gold V of any kind -- he is a visitor, not Valder staff, and the V mark belongs to staff only. No brooch, no pin, nothing on the chest.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary. Also banned: floor-length coats, black clothing, leather/patent gloss sheen, anything that reads as villainous, militaristic or sinister, any gold V or staff mark of any kind, any recognisable designer garment or film/franchise costume, any brand mark or logo.

ACTION (panels 1 and 3): mid-sentence, one hand raised open toward the wall he's addressing -- the gesture of someone making an emphatic point, not an aggressive gesture.

Panel 1: full body, front view, in the action above. Panel 2: large close-up portrait, same invented anonymous face, same collar, ring and bracelet visible, no V. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same coat length, same collar shape, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/1. Four panels verified: front (raised open hand, mid-sentence), close-up portrait (gold signet ring + gold bracelet visible, cream suede glove), profile (same gesture), back view (same coat length/collar/colour/build). Matte petrol-teal coat, mid-calf (not floor-length), stiff standing collar reading as invented tailoring rather than any nameable sci-fi uniform, no brand marks/logos/monograms, no gold V anywhere on the garment. Face is a new invented anonymous man — swept-back steel-grey hair, different nose/jaw/hairline/eye-spacing from the rejected v1/v2 — reads as an ordinary severe-but-non-threatening face, not a celebrity likeness. No safety-flag title on the asset card. Not yet re-tested against Higgsfield's own protected-content scanner (that check only runs when the other operator stages this as a reference on the video composer) — flagging for the CTO to confirm the flag has cleared before Scene 1 references it.

---

### `project_absence_char_woman` v2 — gold V removed, anti-flag treatment (CEO order #53)

- **Asset id:** `3054ae95-a8e1-40a6-addc-0d6579bdea89` · **Element:** re-pointed existing `project_absence_char_woman`
- **Cost:** 3 credits (GPT Image 2, Medium, 2K, 21:9) — running total now 48/40 credits (8 credits/~32 cents over cap). Order #53 is the CEO's own explicit call to move all three visitor-V removals before Scene 1 rather than after, so this spend is cents on already-authorised top-priority work; disclosing and continuing per the CTO's standing policy, no pause.

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: a woman, about fifty years old, slim build, dark hair worn in a high chignon. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen. IMPORTANT: this is a completely invented, anonymous, generic face -- it must not resemble any real, famous, or public person in any way, no celebrity likeness, no impression of any well-known individual or actress, zero basis in any real photograph. An ordinary face nobody would recognise, with its own distinct nose shape, jawline, hairline and eye spacing.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a glossy electric cobalt-blue leather suit with a high funnel collar, fitted jacket, and an A-line skirt to mid-calf. Long cobalt-blue leather gloves reaching past the elbow. Black cat-eye sunglasses worn indoors. Gold dome earrings. Low cobalt-blue heels.

IMPORTANT -- this must be an entirely INVENTED, ORIGINAL garment design: not a recognisable designer piece, not a costume from any known film, franchise or science-fiction property. No brand marks, no logos, no monograms of any kind. No recognisable artwork anywhere in the frame. Plain seamless light-grey studio background only.

She wears NO gold V of any kind anywhere -- not at the collar, not as a brooch, not on a glove, nothing on the chest. She is a visitor, not Valder staff, and the V mark belongs to staff only.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary. Also banned: black clothing as the main garment colour, anything that reads as villainous, militaristic or sinister, any gold V or staff mark of any kind, any recognisable designer garment or film/franchise costume, any brand mark or logo.

ACTION (panels 1 and 3): standing completely still, one gloved hand raised to her mouth, absorbed in thought, not smiling, not distressed -- quiet concentration.

Panel 1: full body, front view, in the action above. Panel 2: large close-up portrait, same invented anonymous face, same sunglasses, same funnel collar, gold dome earring visible, no V. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same suit, same skirt length, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/1. Four panels verified: front, close-up (cat-eye sunglasses, gloved hand raised to mouth, gold dome earring, high chignon), profile, back (same suit/skirt length/colour/build). Glossy cobalt-blue leather suit, high funnel collar, no gold V anywhere on garment or as a brooch. Face largely obscured by sunglasses in front/profile panels (consistent with the "worn indoors" spec) — chin/mouth area visible in close-up reads as an ordinary anonymous face, not a celebrity likeness. No safety-flag title on the asset card.

---

### `project_absence_char_student` v2 — gold V removed, anti-flag treatment (CEO order #53)

- **Asset id:** `b88aa328-a57f-4018-8081-bcf8af5cede2` · **Element:** re-pointed existing `project_absence_char_student`
- **Cost:** 3 credits (GPT Image 2, Medium, 2K, 21:9) — running total now 51/40 credits (11 credits/~44 cents over cap). This closes out CEO order #53 (all three visitor V-removals — critic, woman, student — done before Scene 1 rather than during the render window). Cents on already-authorised top-priority work per the CTO's standing policy; disclosing in full here and in the completion report to the CTO.

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: a young woman, about twenty-two years old, slight build, short dark curly bob, large anxious eyes. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen. IMPORTANT: this is a completely invented, anonymous, generic face -- it must not resemble any real, famous, or public person in any way, no celebrity likeness, no impression of any well-known individual or actress, zero basis in any real photograph. An ordinary face nobody would recognise, with its own distinct nose shape, jawline, hairline and eye spacing.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a chrome-yellow leather trouser suit with an oversized pointed collar. A flat yellow pillbox hat. Cream gloves. Cream ankle boots. A very large round gold medallion worn on a gold chain -- this medallion is her one unmistakable signature.

IMPORTANT -- this must be an entirely INVENTED, ORIGINAL garment design: not a recognisable designer piece, not a costume from any known film, franchise or science-fiction property. No brand marks, no logos, no monograms of any kind. No recognisable artwork anywhere in the frame. Plain seamless light-grey studio background only.

She wears NO gold V of any kind anywhere -- not at the collar, not as a brooch, not on a glove, nothing on the chest. She keeps her large round gold medallion; that is her signature, and it is not a V, not V-shaped, and reads clearly as a plain round disc. She is a visitor, not Valder staff, and the V mark belongs to staff only.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary. Also banned: black clothing as the main garment colour, anything that reads as villainous, militaristic or sinister, any gold V or staff mark of any kind, any recognisable designer garment or film/franchise costume, any brand mark or logo.

ACTION (panels 1 and 3): leaning forward from the waist, one gloved finger jabbing downward, face urgent -- an anxious, insistent gesture.

Panel 1: full body, front view, in the action above. Panel 2: large close-up portrait, same invented anonymous face, same pillbox hat, same oversized pointed collar, gold medallion and chain clearly visible, no V. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same suit, same hat, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/1. Four panels verified: front, close-up (large round gold medallion + chain clearly visible, oversized pointed collar, pillbox hat, anxious wide eyes), profile (leaning forward, finger jabbing down), back (same suit/hat/colour/build). Chrome-yellow leather suit, cream gloves and boots. No gold V anywhere — medallion reads clearly as a plain round disc, not V-shaped. Anonymous invented face, not a celebrity likeness. No safety-flag title on the asset card.

---

## Order #53 status — all three visitor gold-V removals complete

`char_critic` v3, `char_woman` v2, `char_student` v2 all filed, downloaded, committed. Running spend: 51/40 credits (11 credits/~44 cents over the CTO-approved cap), fully disclosed per-plate above as cents on already-authorised top-priority work. None of the three re-tested against Higgsfield's own protected-content scanner from the image side (that check only runs when staged as a video reference) — flagging for CTO confirmation before Scene 1 fires.

---

### `project_absence_char_critic` v4 — full recast, Asian woman in fur coat (CEO order #54)

- **Asset id:** `61a0de1a-c62f-4164-87ac-6c2c1a4e779d` · **Element:** re-pointed existing `project_absence_char_critic`
- **Cost:** 3 credits (GPT Image 2, Medium, 2K, 21:9) — running total now 54/40 credits (14 credits/~56 cents over cap). Order #54 recasts the character entirely; Scene 1 is held on this and order #55, so treating both as cents on already-authorised top-priority work per the CTO's standing policy, disclosing and proceeding.
- **Colour choice:** deep saturated **magenta** fur (chosen over ochre/ultramarine to avoid collision — ochre reads too close to the existing oxblood/burnt-orange earth-tone family, ultramarine too close to the woman's cobalt blue leather; magenta is the only one of the three options with no existing wardrobe neighbour in this cast).

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: an Asian woman, in her sixties, tall, slim build -- speaks with total authority, the loudest and most commanding presence in the room. She is not a villain and must never read as sinister or threatening: she is a woman very sure of her own taste, not someone who could hurt anyone. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen. IMPORTANT: this is a completely invented, anonymous, generic face -- it must not resemble any real, famous, or public person in any way, no celebrity likeness, no impression of any well-known individual or actress, zero basis in any real photograph. An ordinary face nobody would recognise, with its own distinct nose shape, jawline, hairline and eye spacing.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a real fur coat reaching to about mid-calf length (NOT floor-length), full and voluminous, with a high dramatic collar that frames her face -- this dramatic fur-and-collar cut is her one unmistakable signature. The fur is in one deeply saturated flat colour, NEVER black: deep saturated magenta. Cream suede gloves. Round-toe heels. A gold signet ring and a gold bracelet, worn as real understated wealth.

IMPORTANT -- this must be an entirely INVENTED, ORIGINAL garment design: not a recognisable designer piece, not a costume from any known film, franchise or science-fiction property. No brand marks, no logos, no monograms of any kind. No recognisable artwork anywhere in the frame. Plain seamless light-grey studio background only.

She wears NO gold V of any kind -- she is a visitor, not Valder staff, and the V mark belongs to staff only. No brooch, no pin, nothing on the chest.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary. Also banned: floor-length coats, black clothing, anything that reads as villainous, militaristic or sinister, any gold V or staff mark of any kind, any recognisable designer garment or film/franchise costume, any brand mark or logo.

ACTION (panels 1 and 3): mid-sentence, one gloved hand raised open toward the wall she's addressing, chin slightly lifted, mouth open mid-sentence -- the gesture of someone making an emphatic point, not an aggressive gesture.

Panel 1: full body, front view, in the action above. Panel 2: large close-up portrait, same invented anonymous face, same fur collar, ring and bracelet visible, no V. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same coat length, same collar shape, same colour, same build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** Strong pass, attempt 1/1. Four panels verified: front (raised open hand, role/action preserved), close-up (Asian woman, invented anonymous face, gold ring + bracelet, cream glove, mouth open mid-sentence), profile (same action), back (same coat length/collar/colour/build). Deep saturated magenta fur, mid-calf, dramatic collar, no gold V anywhere, no brand marks/logos. No safety-flag title on the asset card.

---

### `project_absence_char_student` — colour redesign, 3 candidate versions for CEO to pick (CEO order #55)

Not filed to the `project_absence_char_student` Element — this is a selection round, the CEO picks one and only the winner gets pointed. Identity/action/medallion/no-V/anti-flag treatment held constant across all three; only the two-tone colour scheme changes. Base prompt (shared, colour line swapped per version):

```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text anywhere.

The person: a young woman, about twenty-two years old, slight build, short dark curly bob, large anxious eyes. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen. IMPORTANT: this is a completely invented, anonymous, generic face -- it must not resemble any real, famous, or public person in any way, no celebrity likeness, no impression of any well-known individual or actress, zero basis in any real photograph. An ordinary face nobody would recognise, with its own distinct nose shape, jawline, hairline and eye spacing.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern: a leather trouser suit in [BASE COLOUR], with an oversized pointed collar and cuffs in [ACCENT COLOUR] -- a two-colour block combination, [BASE COLOUR] body with saturated [ACCENT COLOUR] collar, cuffs, and a flat [ACCENT COLOUR] pillbox hat. [BASE COLOUR] gloves. [ACCENT COLOUR] ankle boots. A very large round gold medallion worn on a gold chain -- this medallion is her one unmistakable signature. She is the only person in this room who wears more than one saturated colour -- everyone else wears exactly one -- and that combination is deliberate: it marks her out as the odd one among the collectors.

IMPORTANT -- this must be an entirely INVENTED, ORIGINAL garment design: not a recognisable designer piece, not a costume from any known film, franchise or science-fiction property. No brand marks, no logos, no monograms of any kind. No recognisable artwork anywhere in the frame. Plain seamless light-grey studio background only.

She wears NO gold V of any kind anywhere -- not at the collar, not as a brooch, not on a glove, nothing on the chest. She keeps her large round gold medallion; that is her signature, and it is not a V, not V-shaped, and reads clearly as a plain round disc. She is a visitor, not Valder staff, and the V mark belongs to staff only.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary. Also banned: black clothing as a main garment colour, anything that reads as villainous, militaristic or sinister, any gold V or staff mark of any kind, any recognisable designer garment or film/franchise costume, any brand mark or logo.

ACTION (panels 1 and 3): leaning forward from the waist, one gloved finger jabbing downward, face urgent -- an anxious, insistent gesture.

Panel 1: full body, front view, in the action above. Panel 2: large close-up portrait, same invented anonymous face, same pillbox hat, same oversized pointed collar, gold medallion and chain clearly visible, no V. Panel 3: full body, side profile, same action. Panel 4: full body, seen entirely from behind -- same suit, same hat, same two-tone colour scheme, same build. Same person, same face, same clothes in every panel.
```

**v1 — cream + scarlet red.** Asset `0077f5d7-d453-4a2e-9b76-5399421c26fb`. Downloaded to `/Users/gob/Desktop/absence-char-student-v1-cream-scarlet.png`. 3 credits. Cream body, saturated scarlet collar/cuffs/hat/boots. Gold medallion clear, no V, no flag.

**v2 — silver-grey + bright turquoise.** Asset `cdb107f6-64f5-4a6b-88a5-349e7ce66ebb`. Downloaded to `/Users/gob/Desktop/absence-char-student-v2-silvergrey-turquoise.png`. 3 credits. Silver-grey body, saturated turquoise collar/cuffs/hat/boots. Gold medallion clear, no V, no flag.

**v3 — blush pink + deep violet.** Asset `6b1ff94a-4fcf-4ac3-b73d-d7aa1509c9d6`. Downloaded to `/Users/gob/Desktop/absence-char-student-v3-blushpink-violet.png`. 3 credits. Blush-pink body, saturated violet collar/cuffs/hat/boots. Gold medallion clear, no V, no flag.

Colour choices avoid collision with the rest of the cast (cobalt/woman, magenta/critic, petrol-teal/oldman, chrome-yellow/original-student, oxblood, burnt-orange, plum). Running total after all three: 66/40 credits (26 credits/~$1.04 over the CTO-approved cap). This is the largest overage of the session — order #55 explicitly asked for 2-3 full generations to choose from, which is inherently more than a single-plate spend, and Scene 1 is held on both order #54 and #55 together per the CTO's top-priority framing. Disclosing the full number rather than rounding down.

**CEO's pick: v3, blush pink + violet.** Element `project_absence_char_student` re-pointed to asset `6b1ff94a-4fcf-4ac3-b73d-d7aa1509c9d6`. (The CTO initially staged v2 silver-grey/turquoise as the CTO's own most-likely-path pick while the CEO's answer was pending; that swap was cancelled before saving once the CEO's actual answer — v3 — came in, so v2 was never filed.) Verified via re-opened Element dialog: Element ID `@project_absence_char_student` correct, "Last changes: just now", blush-pink body with saturated violet collar/cuffs/hat/boots, gold medallion visible, no gold V anywhere.

---

## Working-around a stuck composer tab (CTO urgent, post-Scene-1-prep)

The video-composer tab (driven by the other operator) had cached the OLD `project_absence_char_critic` and `project_absence_char_student` bindings — a full clear+re-paste still resolved to the pre-recast teal-coat critic and yellow-suit student, and the old critic still carried its protected-content flag. A fresh tab would have reset the Unlimited toggle with the CEO out of the building, so instead of touching that tab: created two brand-new Elements under names the composer tab has never seen, pointing at the same already-approved, already-generated assets. No new generation, 0 additional credits.

- **`project_absence_char_critic_b`** — Category Character. Points at asset `61a0de1a-c62f-4164-87ac-6c2c1a4e779d` (the CEO-approved magenta-fur-coat recast, order #54). Verified via Element dialog: correct Element ID, Asian woman, deep magenta fur, gold ring over cream glove, no gold V.
- **`project_absence_char_student_b`** — Category Character. Points at asset `6b1ff94a-4fcf-4ac3-b73d-d7aa1509c9d6` (the CEO-picked v3, blush pink + violet). Verified via Element dialog: correct Element ID, blush-pink suit, violet collar/cuffs/hat/boots, gold medallion, no gold V.

Both created via the asset card's own "Create Element" action (not a re-point of the existing `_critic`/`_student` Elements, which stay as they are) — no generation involved, running credit total unchanged at 66/40.

---

## Two more fresh-name Elements — hall_big and visitor_c, same trick (CTO urgent)

Composer was missing/refusing `project_absence_loc_hall_big` and `project_absence_char_visitor_c`. Same fix: new Element names, no new generation, 0 additional credits, original Elements untouched.

- **`project_absence_loc_hall_big_b`** — Category Location. Points at asset `b69d5170-1a8d-4431-8c84-3881baa634dc` (JOB 1 v4, CEO order #49 — crack centred at picture-hanging height, plaque low near the floor, clear gap between them). Verified via Element dialog: correct Element ID, and zoomed on the hero-wall panel to confirm crack position exactly matches the v4 spec (not the v3 near-ceiling position). NOT v3 (`acf0d6c7`) or earlier.
- **`project_absence_char_visitor_c_b`** — Category Character. Points at asset `5ade0802-43b0-453b-a2a6-fd588be77221` (the approved visitor_c). Verified via Element dialog: correct Element ID, Black man ~55, plum aubergine leather jacket, grey trousers, walking mid-stride, no gold V.

Running credit total unchanged at 66/40.
