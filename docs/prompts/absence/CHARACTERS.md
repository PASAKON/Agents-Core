# The Absence of Meaning — Character Plates

Seven character sheets, one person per image, GPT Image Gen 2, Higgsfield project
`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (visible name
"The Valder Collection No.7"). Each is a 21:9 four-panel sheet (front action /
portrait / side profile / back), Medium quality, 1K, ~2 credits each. No
reference images used — every plate is an original character, first appearance.

**Spec change, CEO 07:52 (mid-session):** the four who argue (critic, oldman,
woman, student) each need ONE strong signature, different in KIND from the
other three (not just a different colour) — a carried object, a hat, glasses,
or an unmistakable proportion — so each is identifiable from a silhouette or
from behind with no face visible. The three extras (visitor_a/b/c) stay
deliberately ordinary: well dressed, unremarkable, no signature, so the four at
the wall stand out against them. This is reflected in the prompts below.

**Asset id note:** the composer's detail modal doesn't expose the asset UUID
as plain text (unlike the Soul Cinema plates in PLATES.md, this GPT Image 2
project view never changed the URL to a `?preview=<uuid>` form, and reading the
`<img src>` for the id was blocked as cross-origin query-string data). The
durable identifier for each plate is its **Element ID**, which is what actually
matters for future `@mention` binding — recorded below instead.

---

## 1 · `project_absence_char_critic` — the art critic

- **Element:** `project_absence_char_critic`, category Character, name "critic"
- **Model:** GPT Image 2, 21:9, Medium, 1K
- **References:** none (first appearance)
- **Cost:** 2 credits (1,821 → 1,819)
- **Signature (spec-change compliant):** something carried, held the same way
  every time — a slim black cane with an ivory knob, tucked under his arm,
  never used for walking.

**Prompt:**
```
A wide horizontal character reference sheet, aspect ratio roughly 2.4:1, four panels arranged side by side on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text. The same middle-aged man, same face, same clothes, in every panel: he wears a floor-length deeply saturated wine-burgundy coat, one large flat plane of colour, retrofuturist mid-century cut, no pattern-on-pattern, no modern clothing. His one unmistakable signature, present and held the exact same way in every panel: a slim black cane with a polished ivory-coloured knob handle, carried tucked under his free arm, never used for walking, purely an object of authority. Real human skin with natural texture and variation, a real weathered middle-aged face with real bone structure and asymmetry, no pale waxy stylised skin, no doll face, no airbrushed beauty-filter look, no CGI sheen.

Panel 1 (far left): full body, front view, standing with total authority, one hand raised and open toward something off-frame as if mid-sentence explaining, the cane held tucked under his other arm, chin slightly lifted -- a man utterly certain he is right, the loudest voice in the room.
Panel 2: large close-up portrait, head and shoulders only, expression of absolute certainty -- confident, direct eyes, level brows, caught mid-word.
Panel 3: full body, side profile, standing, continuing the same raised-hand explaining gesture, cane still tucked under his arm in the same position.
Panel 4: full body, viewed from directly behind, the cane's silhouette clearly visible tucked under his arm even from behind, same authoritative standing posture -- he must be identifiable from this back view by the cane and coat alone.

Photographed like a real fashion/character turnaround reference sheet: crisp, clean, accurate colour rendition, flat even studio light throughout, no vignette, no film grain, no dramatic cinema lighting.
```

**What the image actually shows:** A strong result. Real, weathered middle-aged
face with a mustache and natural skin texture — no doll-face, no airbrush. The
wine-burgundy coat reads more like a long mandarin-collar robe/cassock than a
tailored "coat," but it is a single flat saturated plane of colour exactly per
the wardrobe language, and it is consistent across all four panels. **The cane
signature works well** — visible tucked under his arm in panels 1, 3 and 4,
including a clean, legible silhouette from directly behind (panel 4), so he is
identifiable from the back by cane + coat cut alone, satisfying the CEO's
unmistakable-from-behind requirement. **Panel 1's characteristic action reads
correctly**: one hand raised open toward off-frame, chin lifted, an explaining
gesture. Panel 2 portrait reads as confident/mid-word rather than a
theatrically "certain" expression, but it is in the right register. No hard
failure; kept on first generation.

---

## 2 · `project_absence_char_oldman` — the elderly gallery-goer

- **Element:** `project_absence_char_oldman`, category Character, name "oldman"
- **Model:** GPT Image 2, 21:9, Medium, 1K
- **References:** none (first appearance)
- **Cost:** 2 credits (1,819 → 1,817)
- **Signature (spec-change compliant):** a hat with a definite shape — a dark
  forest-green felt homburg with a tall crown and stiff curled brim, worn
  level and low every panel.

**Prompt:**
```
A wide horizontal character reference sheet, aspect ratio roughly 2.4:1, four panels arranged side by side on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text. The same elderly, well-dressed gentleman, same face, same clothes, in every panel: he wears a deeply saturated forest-green wool overcoat, one large flat plane of colour, retrofuturist mid-century cut, no pattern-on-pattern, no modern clothing. His one unmistakable signature, worn the exact same way in every panel: a dark forest-green felt homburg hat with a distinctive tall crown and stiff curled brim, set level and low, giving his head a very specific, instantly recognisable shape from any angle including directly behind. Real human skin with natural texture and age, a real elderly face with real wrinkles, real bone structure, no pale waxy stylised skin, no doll face, no airbrushed beauty-filter look, no CGI sheen. The manner of someone who has been coming to galleries for fifty years -- unhurried, composed.

Panel 1 (far left): full body, front view, caught mid-motion stepping back one pace, weight settled onto his back foot, head tilted slightly, taking something in from a distance with quiet scepticism.
Panel 2: large close-up portrait, head and shoulders only, hat clearly visible, a slight frown, unconvinced, studying something with a critical eye.
Panel 3: full body, side profile, continuing the same weight-back stepping-away pose, head tilted the same way.
Panel 4: full body, viewed from directly behind, the homburg's distinctive tall crown and brim shape clearly readable from behind, same stepped-back stance -- he must be identifiable from this back view by the hat's silhouette alone.

Photographed like a real fashion/character turnaround reference sheet: crisp, clean, accurate colour rendition, flat even studio light throughout, no vignette, no film grain, no dramatic cinema lighting.
```

**What the image actually shows:** Real elderly face — genuine wrinkles, age
spots, natural bone structure, no airbrushing. Forest-green coat and homburg
hat both render as a single clean saturated plane. **The hat signature works
very well**: identical tall-crown/curled-brim silhouette instantly legible in
all four panels, including panel 4 from directly behind, where the hat alone
makes him recognisable with zero face visible — this is exactly the CEO's
bar. **Two honest flaws.** First, the model added a brown leather briefcase in
panels 1 and 4 that was never in the prompt — harmless but unrequested.
Second, and more important: **the characteristic action does not clearly
read.** I asked for "stepping back one pace, weight on back foot, head
tilted" — what actually rendered is a normal mid-stride walking gait in
panels 1, 3 and 4, not a backward step. The portrait (panel 2) does carry the
right "slight frown, unconvinced" expression. This is a spec miss on the
action, not a hard failure (no error, not blank, no content refusal), so per
the task's no-taste-regeneration rule this was kept rather than regenerated —
flagging here for the CEO's call on whether it needs a redo.

---

## 3 · `project_absence_char_woman` — the woman who genuinely feels something

- **Element:** `project_absence_char_woman`, category Character, name "woman"
- **Model:** GPT Image 2, 21:9, Medium, 1K
- **References:** none (first appearance)
- **Cost:** 2 credits (1,817 → 1,815)
- **Signature (spec-change compliant):** glasses with a specific frame — large
  round tortoiseshell frames, always worn the same way.

**Prompt:**
```
A wide horizontal character reference sheet, aspect ratio roughly 2.4:1, four panels arranged side by side on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props, no text. The same woman in her forties or fifties, same face, same clothes, in every panel: she wears a deeply saturated deep-teal dress, one large flat plane of colour, retrofuturist mid-century cut, no pattern-on-pattern, no modern clothing. Her one unmistakable signature, worn the exact same way in every panel: large round tortoiseshell-frame glasses with a distinctive thick dark frame, an unusual and specific shape unlike ordinary glasses, always worn the same way, giving her head a very recognisable outline even in silhouette or from behind (visible as a thin dark temple arm line at the side of her head). She has real personal style. Real human skin with natural texture and variation, a real face with real bone structure, no pale waxy stylised skin, no doll face, no airbrushed beauty-filter look, no CGI sheen.

Panel 1 (far left): full body, front view, standing very still, one hand raised to her mouth, fingers lightly touching her lips, completely absorbed in something off-frame, quiet and still -- she is the one who genuinely feels something.
Panel 2: large close-up portrait, head and shoulders only, glasses clearly visible, an expression on the edge of tears but dignified and composed -- no sobbing, no mugging, just quiet, real emotion held with control.
Panel 3: full body, side profile, standing still, same hand-at-mouth gesture, same absorbed stillness.
Panel 4: full body, viewed from directly behind, the distinctive glasses' temple arm visible at the side of her head, same still standing posture -- she must be identifiable from this back view by her glasses' silhouette and posture.

Photographed like a real fashion/character turnaround reference sheet: crisp, clean, accurate colour rendition, flat even studio light throughout, no vignette, no film grain, no dramatic cinema lighting.
```

**What the image actually shows:** Excellent result. Real, expressive middle-
aged face with natural skin texture and true personal style. Deep-teal dress
renders as a single clean saturated plane per the wardrobe language. **Panel
1's characteristic action reads correctly and strongly**: standing very still,
one hand at her mouth, genuinely absorbed — this is the clearest "acting"
result of the four so far. Panel 2's portrait nails the brief precisely: on
the edge of tears but dignified, no sobbing, no mugging, held with real
control — a standout. The large round tortoiseshell glasses are bold and
distinctive in panels 1-3. **Honest flaw, and an important one for the CEO's
call:** in panel 4 (directly from behind), her hair is worn up and covers her
ears entirely — the glasses' temple arms are **not visible at all** from a
true back view. This is a structural limitation of "glasses" as a signature
type: unlike a hat, cane, or oversized coat, glasses sit on the front of the
face and by definition cannot be seen in a pure from-behind shot unless the
head is turned or hair explicitly reveals the temple. From this back panel
she is only identifiable by dress colour, hair colour/style and build — not
by the chosen signature itself. Not a hard failure (nothing wrong with the
image itself), but worth flagging: the CEO's own signature-type list includes
glasses, yet it may be the one type that cannot satisfy the "recognisable
...from behind, with no face visible" requirement on its own.

---

## 4 · `project_absence_char_student` — the art student

- **Element:** `project_absence_char_student`, category Character, name "student"
- **Model:** GPT Image 2, 21:9, Medium, 1K
- **References:** none (first appearance)
- **Cost:** 2 credits (1,815 → 1,813)
- **Signature (spec-change compliant):** an unmistakable proportion — an
  oversized, borrowed-looking coat with long sleeves meant to swallow her
  hands, giving her a swamped, boxy silhouette nobody else in the film has.

**Prompt:**
```
A wide horizontal character reference sheet, aspect ratio roughly 2.4:1, four panels arranged side by side on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props, no text. The same young woman, about twenty years old, same face, same clothes, in every panel: an art student at a gallery opening above her price bracket, dressed slightly wrong for it. She wears a deeply saturated cobalt-blue coat, one large flat plane of colour, retrofuturist mid-century cut, no pattern-on-pattern -- the coat itself is right, but it is a hand-me-down or borrowed piece, noticeably too large for her. Her one unmistakable signature, present in every panel: an unmistakable PROPORTION mismatch -- the coat's sleeves are cut long and full, swallowing her hands completely so only her fingertips peek out past the cuffs, giving her a distinctive oversized, swamped silhouette instantly different from anyone else in the film. Cheaper, mismatched layers are visible at the collar and hem, poking out from under the coat, giving away that she doesn't quite belong in this room. Real human skin with natural texture, a real young face with real bone structure, no pale waxy stylised skin, no doll face, no airbrushed beauty-filter look, no CGI sheen.

Panel 1 (far left): full body, front view, caught mid-interjection, one arm extended with the oversized sleeve drooping, index finger jabbing downward and out from within the long cuff to underline a point, chin forward, earnest and urgent -- a point nobody in the room is listening to.
Panel 2: large close-up portrait, head and shoulders only, an earnest, slightly defiant expression, young and sincere, unwilling to back down.
Panel 3: full body, side profile, continuing the same downward jabbing-finger gesture, oversized sleeve visible drooping past her wrist.
Panel 4: full body, viewed from directly behind, the oversized coat's swamped silhouette and long drooping sleeves clearly readable from behind -- she must be identifiable from this back view by the coat's exaggerated oversized proportion alone.

Photographed like a real fashion/character turnaround reference sheet: crisp, clean, accurate colour rendition, flat even studio light throughout, no vignette, no film grain, no dramatic cinema lighting.
```

**What the image actually shows:** Good result. Young, real face with a
sincere, slightly defiant expression in the portrait — matches the brief.
Mismatched cheaper layers (a plaid shirt collar, a grey pleated skirt hem,
patterned socks) are clearly visible under and past the cobalt coat, exactly
selling "dressed slightly wrong for the room." **The proportion signature
partially reads**: the coat itself is visibly oversized, boxy and roomy —
clearly bigger than a normal fit — and this silhouette carries through
strongly to panel 4 (directly behind), where the wide, cocoon-like shape is
the most identifiable thing about her from that angle. **One honest miss**:
the specific detail I asked for — sleeves so long they swallow her hands,
fingertips barely peeking out — did not render in panel 1; her arm is
extended in the pointing gesture and her whole hand is visible, cuff pulled
back naturally by the motion, not drooping over it. **Panel 1's characteristic
action (mid-interjection, one finger jabbing downward) reads only
partially** — her arm is extended and her hand is pointing, but the gesture
reads more as reaching/pointing forward than a sharp downward jab. Not a hard
failure; kept on first generation, flagged for the CEO.

---

## THE THREE EXTRAS — deliberately ordinary, per CEO spec

The following three are the people who look at the real art properly. Per the
CEO's 07:52 spec change they carry **no signature, no memorable silhouette** —
deliberately unremarkable so the four at the wall stand out against them.

---

## 5 · `project_absence_char_visitor_a` — the quiet man studying

- **Element:** `project_absence_char_visitor_a`, category Character, name "visitor_a"
- **Model:** GPT Image 2, 21:9, Medium, 1K
- **References:** none (first appearance)
- **Cost:** 2 credits (1,813 → 1,811)
- **Signature:** deliberately none — plain moderately-saturated slate-grey suit,
  ordinary proportions.

**Prompt:**
```
A wide horizontal character reference sheet, aspect ratio roughly 2.4:1, four panels arranged side by side on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props, no text. The same quiet middle-aged man, same face, same clothes, in every panel: plainly and well dressed, an ordinary gallery visitor with no distinguishing feature -- a simple, moderately saturated slate-grey suit, single flat plane of colour, retrofuturist mid-century cut, ordinary proportions, no hat, no glasses, nothing carried, nothing unusual about his silhouette. He is deliberately unremarkable: well dressed and believable, nothing the eye catches on, someone you would not pick out of a crowd. Real human skin with natural texture, a real ordinary face with real bone structure, no pale waxy stylised skin, no doll face, no airbrushed beauty-filter look, no CGI sheen.

Panel 1 (far left): full body, front view, standing squarely and still, hands clasped behind his back, genuinely studying something off-frame, unhurried and calm.
Panel 2: large close-up portrait, head and shoulders only, a calm, attentive expression, quietly absorbed, unremarkable and ordinary.
Panel 3: full body, side profile, standing still, same hands-clasped-behind-back posture, same unhurried attentiveness.
Panel 4: full body, viewed from directly behind, hands still clasped behind his back, an ordinary, unremarkable standing posture with nothing distinctive about his silhouette.

Photographed like a real fashion/character turnaround reference sheet: crisp, clean, accurate colour rendition, flat even studio light throughout, no vignette, no film grain, no dramatic cinema lighting.
```

**What the image actually shows:** Clean, strong result — exactly on brief.
**Panel 1's characteristic action reads perfectly**: standing squarely, hands
clasped behind his back, calm and unhurried. The plain slate-grey suit and
ordinary bone structure read as genuinely unremarkable — nothing the eye
catches on, per spec. Panel 4 (directly behind) shows the same clasped-hands
posture; he is not meant to be "identifiable" by a signature (the extras
carry none by design), but the pose is at least consistent and legible from
behind. No flaws worth flagging; kept on first generation.

---

## 6 · `project_absence_char_visitor_b` — the woman browsing the wall

- **Element:** `project_absence_char_visitor_b`, category Character, name "visitor_b"
- **Model:** GPT Image 2, 21:9, Medium, 1K
- **References:** none (first appearance)
- **Cost:** 2 credits (1,811 → 1,809)
- **Signature:** deliberately none — plain moderately-saturated tan-ochre coat,
  ordinary proportions.

**Prompt:**
```
A wide horizontal character reference sheet, aspect ratio roughly 2.4:1, four panels arranged side by side on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props, no text. The same woman, same face, same clothes, in every panel: an ordinary gallery visitor with no distinguishing feature -- a moderately saturated soft tan-ochre coat, single flat plane of colour, retrofuturist mid-century cut, ordinary proportions, no hat, no glasses, nothing carried, nothing unusual about her silhouette. She is deliberately unremarkable: well dressed and believable, nothing the eye catches on, someone you would not pick out of a crowd. Real human skin with natural texture, a real ordinary face with real bone structure, no pale waxy stylised skin, no doll face, no airbrushed beauty-filter look, no CGI sheen.

Panel 1 (far left): full body, front-ish view, caught mid-step walking slowly along a wall of pictures, head turned to one side toward something off-frame, moving at an unhurried browsing pace.
Panel 2: large close-up portrait, head and shoulders only, a mild, interested expression, quietly looking at something, ordinary and unremarkable.
Panel 3: full body, side profile, continuing the same slow mid-step walking pose, head turned toward the wall.
Panel 4: full body, viewed from directly behind, an ordinary, unremarkable walking posture with nothing distinctive about her silhouette.

Photographed like a real fashion/character turnaround reference sheet: crisp, clean, accurate colour rendition, flat even studio light throughout, no vignette, no film grain, no dramatic cinema lighting.
```

**What the image actually shows:** Strong, on-brief result. **Panel 1's
characteristic action reads clearly**: caught mid-step walking, head turned
toward the wall at a relaxed browsing pace. Portrait carries a mild,
interested expression exactly as asked. Tan-ochre coat is a single flat
saturated plane, appropriately less visually loud than any of the four who
argue. Panel 4 (directly behind) shows a plain, unremarkable walking posture
— correctly forgettable. No flaws worth flagging; kept on first generation.
