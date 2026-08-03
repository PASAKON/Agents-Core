# BrandPrompt TH — Brand Reference

Brand-asset reference library (like `mooniex/` and `tradonix/` in this same
folder — see those for pattern). New product, brand built from scratch this
session. Assets in `images/` are **manual composition** (HTML → Playwright
screenshot, local IBM Plex Sans Thai font) — no paid image-gen API used
(no `FAL_API_KEY` / MeiGen token available yet; see Blockers/Notes at bottom).

## Identity

- **Name:** BrandPrompt TH
- **Product:** AI JSON Prompt Pack — 100 prompts + 300 sample images. Thai
  SME owners edit a JSON file (text/colors) to generate their own on-brand
  posters, no designer needed. Price 500 บาท.
- **Facebook Page (live):** https://www.facebook.com/profile.php?id=61591732547818
  — category "โฆษณา/การตลาด".
- **Name meaning:** *Brand* (the outcome the customer wants) + *Prompt* (the
  mechanism that gets them there) — the product name already contains its
  own value proposition.

## Design process (moodboard → archetype → palette → typography → tokens)

This section documents the reasoning chain per task brief — palette and
typography were **derived from the brand meaning below, not picked for
looking nice.**

### 1. Archetype read
Brief specifies **Sage + Creator**, explicitly *not* Magician:
- **Sage** → the pack teaches/equips (100 structured prompts), credible and
  clear, not mysterious.
- **Creator** → the customer makes something real and tangible (their own
  poster) with their own hands, not a passive black-box output.
- **Not Magician** → no "AI does everything like magic" framing. The JSON
  file *shows its work* — editable, inspectable, honest about being a
  structured tool, not a trick.

### 2. Positioning read
"มืออาชีพแต่เข้าถึงง่าย" (professional but approachable), target = Thai SME
owners **without a design budget and not technical**. This is the opposite
end of the spectrum from a dev-tool audience — the brand has to feel like a
**craft/print product**, not a SaaS dashboard.

### 3. Moodboard direction (rejected vs. chosen)
- **Rejected:** neon green/cyan "AI-startup" gradient — brief explicitly
  bans this (reads as generic, cold, intimidating to a non-technical SME
  owner — the opposite of "เข้าถึงง่าย ไม่น่ากลัว").
  Also rejected on portfolio-collision grounds: it would read as a knockoff
  of nothing here, but "trust-blue-gradient SaaS" is exactly the genre the
  brief says to avoid.
- **Rejected:** navy + gold — already MoonieX's locked palette in this same
  repo (`../mooniex/BRAND.md`). Reusing it would make BrandPrompt TH read
  as a MoonieX sub-brand instead of its own product.
- **Rejected:** dark bg + glowing copper/amber — already TRADONIX's locked
  palette (`../tradonix/BRAND.md`), same collision risk, plus TRADONIX's
  mood (glowing 3D CGI, dramatic dark fintech) is a *trading* aesthetic —
  wrong register for a friendly SME design tool.
- **Chosen direction: "ink & paper."** Warm off-white paper background,
  near-black warm ink for text, one warm clay/terracotta accent. This reads
  as *craft and print* (stationery, a well-made workbook/manual) rather
  than *screen and code* — approachable to someone who has never opened a
  design tool, while the accent color still carries enough warmth/energy to
  not look like a boring template.

### 4. Palette + rationale (locked)

| Token | Hex | Role | Why |
|---|---|---|---|
| **Ink** | `#241E1A` | primary text / dark surfaces | Warm near-black (not pure `#000`) — soft, print-like, never feels cold/clinical. Doubles as the "structure" color (braces, code) — Sage = precise but not sterile. |
| **Paper** | `#F7F0E2` | primary background | Warm ivory, not `#FFFFFF`. Reads as *paper*, not *screen* — reinforces "you're making something tangible," and is gentle/non-intimidating for a non-technical audience. |
| **Clay** | `#C1502C` (gradient to `#D4693F` / `#9C3D22`) | primary accent — the "Brand" (finished output) | Warm terracotta, not bright/neon orange. Terracotta = handmade, human, craft-market color (Thai print/ceramic/textile association) — energetic enough to be a CTA color, warm enough to never read as corporate-cold or AI-generic. Deliberately *not* the same hue temperature as TRADONIX's brighter glowing amber-on-black — this sits matte/on-paper, not glowing/on-dark. |
| **Sand** | `#E7D9BF` | card/panel fill, dividers | Mid neutral between ink and paper — subtle depth without introducing a new hue. |
| **Taupe** | `#8B7E6A` | secondary/muted text | Low-emphasis copy (captions, disclaimers) — warm gray, not cool gray, stays inside the "paper" family. |

Two-color system on purpose (ink + clay), not three-plus accents — a small
SME buyer needs to reuse this confidently in Canva/JSON without a complex
palette to manage. Simplicity here **is** the "เข้าถึงง่าย" promise, applied
to the brand system itself, not just the marketing copy.

### 5. Typography (locked)
- **Thai display/body: IBM Plex Sans Thai** (`assets/fonts/IBMPlexSansThai-{Regular,SemiBold}.ttf`,
  OFL-licensed, already vendored in this repo — see `OFL-IBMPlexSansThai.txt`
  in the same folder, so it's free for the customer to reuse commercially
  too). Humanist grotesk, highly legible at small sizes, professional
  without being cold — the "Sage" read (clear, credible) without the
  "generic AI SaaS" font choice (avoided the ultra-geometric/rounded
  startup-font cliché).
- **Monospace accent: system monospace (Menlo used for local renders;
  production recommendation `IBM Plex Mono`** — same super-family as the
  Thai font, so the type system stays unified. Used **only** for the `{ }`
  JSON-structure marks and code snippets — never for body Thai — so the
  "editable structure" symbolism stays a deliberate accent, not the whole
  brand voice.

### 6. Symbolism → logo concept
Brief suggests exploring `{ }` / `[ ]` from JSON to signal "editable
structure," contrasted against a finished poster. Rather than treat that as
a separate graphic device, it's baked directly into the **wordmark**:

> **Brand{Prompt}**

The product name literally becomes the logo — "Brand" in the Thai/Latin
display face (the human, finished side) wrapping "Prompt" in monospace
inside literal JSON braces (the structured, editable side). No visual
metaphor needed beyond the typography itself — it's the clearest possible
expression of "structure in, brand out," and it's memorable/ownable in a
way a generic bracket icon alone wouldn't be.

## Logo & lockups

- `images/logo-mark.png` — standalone icon: rounded-square clay gradient,
  paper-colored `{ }` monospace glyph, centered. Used as favicon / avatar
  base. Scales down cleanly (tested at profile-picture size).
- `images/logo-wordmark-light.png` — full lockup on paper bg: **Brand{Prompt}**
  + small clay "TH" pill badge + one-line descriptor.
- `images/logo-wordmark-dark.png` — same lockup on ink bg, for dark
  placements (cover photo, dark social templates).
- **"TH" badge:** small clay pill, always paired with the wordmark —
  distinguishes this from any future non-Thai-market variant of the
  product without needing a second full identity.

## Facebook Page assets (current 2026 FB spec)

- `images/fb-profile-picture.png` — **512×512px** (upload min; FB displays
  170×170 desktop / 128×128 mobile, crops to a circle). Mark is centered
  with generous padding so the circular crop never clips the braces.
- `images/fb-cover-photo.png` — **1200×630px** (current recommended upload
  size; desktop displays ~820×312, mobile ~640×360). Layout keeps the
  **bottom-left ~250×250px clear** — that's where the profile picture
  overlaps the cover on desktop — headline block sits upper-left instead,
  stat line moved to bottom-right for the same reason (first draft had it
  bottom-left and it was fixed after visual review).

## Sample: brand system in use

- `images/sample-post-json-to-poster.png` (1080×1080, feed-square) — split
  composition: raw JSON config on the ink panel (left) → the finished
  poster it produces on the clay panel (right), with "แก้ JSON → ได้โปสเตอร์ใหม่"
  underneath. This is the single image that sells the product's mechanic in
  one glance, and is the reference for any future FB/ad creative for this
  brand — structure-vs-output is the recurring layout motif, not a one-off.

## Voice cues (for future copy on this brand)
- Never oversell "AI magic" — always show the mechanism (JSON in, poster
  out). Matches Sage+Creator, not Magician.
- Plain, warm Thai — short sentences, no jargon a non-technical shop owner
  wouldn't use themselves.
- CTA tone: "แวะมาชม" / "ลองเลย" style — inviting, not hard-sell.

## Blockers / Notes for future agents

- **No paid image-gen key available this session** (no `FAL_API_KEY`, no
  MeiGen token) — all assets above are manual HTML/CSS → Playwright
  screenshot composition, not AI-generated. If/when a gen key is approved,
  the `sample-post-json-to-poster.png` concept is the one worth extending
  into a real multi-variant hero set (different shop types), but the
  current asset is production-usable as-is, not a placeholder.
- **Design source path in the task brief did not exist on disk**:
  `/Users/gob/Projects/mooniex-claudesign/.od/projects/52891810-d464-4ef7-9d09-639e69d86a7b/`
  — the project row exists in `.od/app.sqlite` (`name=BrandPrompt TH,
  skill_id=blog-post`) but has no generated project folder yet (no prior
  design session created one). Brand built directly from the CMO brand
  brief in TASK.md instead — no existing design was overwritten or ignored.
- IBM Plex Mono is not vendored locally (only Sans Thai is) — local renders
  substitute system Menlo for the monospace accent, visually near-identical
  slab-mono. Recommend vendoring `IBM Plex Mono` alongside the existing
  Sans Thai files if this brand's asset production continues, to match the
  Playwright render pipeline exactly to what a customer would see if they
  reused the type system.
