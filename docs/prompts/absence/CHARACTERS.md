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
