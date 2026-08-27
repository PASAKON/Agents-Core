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

- **Asset id:** _(pending)_ · **Element:** re-point existing `project_absence_char_visitor_b`
- **Cost:** _(pending)_

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

**What the image actually shows:** _(pending)_

---

### 2.7 · `project_absence_char_visitor_c`

- **Asset id:** _(pending)_ · **Element:** re-point existing `project_absence_char_visitor_c`
- **Cost:** _(pending)_

**Prompt:**
```
A character reference sheet, ONE IMAGE divided into FOUR PANELS side by side in a single wide horizontal strip, aspect ratio approximately 2.4:1, all four panels on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props, no text anywhere.

The person: a visitor, 40s, stocky, brisk build and manner. Dressed functionally, like someone who is only passing through on their way to be somewhere else -- deliberately UNREMARKABLE, nothing the eye catches on, no signature detail of any kind. Not sinister, not military, not severe, simply practical. Genuinely human: real skin with real texture and variation, real bone structure, no doll face, no beauty-filter smoothing, no CGI sheen.

CLOTHING -- retrofuturist mid-century silhouette, the future as imagined in the 1960s (2001: A Space Odyssey, Tati's Playtime, Gattaca), never a literal period piece, never anything modern, but plain, functional and ordinary within that world: a simple short boxy jacket, practical rather than fashionable, cut from a moulded, seamless, faintly synthetic material -- vinyl or coated fabric, never woven wool -- in one deeply saturated flat colour, NEVER black and never a military/olive-drab green: deep plum aubergine. No hat. No gloves. Round-toe shoes. Nothing distinctive, nothing styled to draw the eye -- the whole point of this person is that they blend in.

JEWELLERY: almost nothing -- at most a plain worn watch. NO gold V, no brooch, no visible ornament.

BANNED: jeans, sneakers, trainers, hoodies, graphic tees, plastic zips, printed logos, baseball caps, anything reading as post-1970 or contemporary.

ACTION (panels 1 and 3): walking briskly, purposeful stride, looking at nothing in particular -- clearly on their way somewhere else.

Panel 1: full body, front view, in the action above, mid-stride. Panel 2: large close-up portrait, same ordinary, believable face. Panel 3: full body, side profile, same brisk-stride action. Panel 4: full body, seen entirely from behind -- same jacket, same colour, same stocky build. Same person, same face, same clothes in every panel.
```

**What the image actually shows:** _(pending)_

---

## Money log

Cap raised to 40 by CTO (approved going over the original 30; overage was cents on already-authorised work). Running total: 27 / 40 (JOB 1 hall v1 3 + hall v2 fix 3 + critic v1 3 + critic v2 fix 3 + oldman 3 + woman 3 + student 6 [accidental duplicate, disclosed above] + visitor_a 3).
