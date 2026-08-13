# LinkReed — Brand Truth

**Status:** LOCKED (CEO approved 2026-08-04). Do not recompute or "improve"
these values inside a design task — raise changes with the CMO first.

**What LinkReed is:** an agentic AI link-in-bio builder. The user describes
what they want — colors, fonts, layout, vibe — and the AI designs the page,
the way a hired web designer would, instead of handing over a template
gallery to pick from.

**Positioning line:** "Your link page, art-directed by AI — not picked from
a template."

**Reference mood image:** watercolor + hand-ink editorial illustration
(brain/network study), CEO-approved 2026-08-04 for its *texture and
palette*, not its subject matter. See `reference_mood` at the bottom for
what was kept vs. what was swapped.

---

## 1. Brand personality & voice

Recalibrated 2026-08-04 to match the reference mood (warm, editorial,
hand-crafted) — **not** the punchy/fast SaaS voice drafted earlier in
concept work. This supersedes that draft.

1. **Thoughtful, not loud.** Sentences can breathe. No forced hype, no
   exclamation-point energy.
2. **Crafted, human.** Prefer "sketched," "drawn," "shaped," "taking form"
   over "generated," "powered by AI," "AI-driven."
3. **Quietly smart.** Editorial/essay tone, not SaaS-listicle tone.

**Do:**
- Short paragraphs, real sentences — not fragment-bullet marketing speak.
- Talk about the *result* (how the page looks/feels), not the mechanism.
- Let confidence come from restraint, not volume.

**Don't:**
- No "empower," "unlock," "seamless," "revolutionize," "leverage."
- No em dash in public-facing copy (org-wide rule, IRON §39 — AI tell).
- Don't oversell "AI" as the headline; it's the *how*, not the *what*.

**Tagline candidates (pick at launch, don't lock yet):**
- "Ideas, drawn into a page."
- "Your page, sketched by AI, shaped by you."
- "Not a template. Your page."

---

## 2. Color — two tiers, don't mix their jobs

The reference image's full wash palette is **decorative/illustration only**.
Product UI runs on a narrower, higher-contrast functional set pulled from
it. This split exists because the brief was explicit: the shipped product
must be minimal, mobile-first, with very few buttons — a busy multi-hue UI
would fight that.

### Functional (UI — buttons, text, surfaces)
| Token | Hex | Use |
|---|---|---|
| `paper` | `#F3EEE3` | primary background (light) |
| `paper-raised` | `#FBF8F1` | cards/sheets sitting above paper |
| `ink` | `#211D1A` | primary text, primary logo color |
| `ink-soft` | `#5B554C` | secondary text, captions |
| `dusk` (accent / CTA) | `#3C5468` | the ONE button color — primary actions only |
| `dusk-hover` | `#2E4252` | pressed/hover state of `dusk` |
| `hairline` | `#D9D0BF` | dividers, borders — never pure grey |

Dark mode surfaces (product, not marketing pages):
| Token | Hex | Use |
|---|---|---|
| `ink-bg` | `#1C1815` | dark background |
| `ink-bg-raised` | `#26211C` | dark cards |
| `paper-text` | `#F3EEE3` | text on dark |
| `dusk-dark` | `#7C99B8` | accent lifted for contrast on dark bg |

### Decorative (illustration, hero art, marketing only — never on buttons/UI chrome)

Re-sampled 2026-08-04 directly from pixel data in the CEO's reference file
(`~/Desktop/mindmap-illustration.jpg`) after the first pass read as too
olive/pastel. These are the corrected, verified values.

| Token | Hex | Use |
|---|---|---|
| `wash-blue` | `#4A6171` | ink-wash illustration (left zone) |
| `wash-teal` | `#577B71` | ink-wash illustration (top-mid transition — teal-green, not olive) |
| `wash-terracotta` | `#8A5150` | ink-wash illustration (top-right zone) |
| `wash-plum` | `#55323C` | ink-wash illustration (right-mid zone, deepest accent) |

**Rule:** if a designer reaches for `wash-*` on a button, nav bar, or form
field, that's a brand violation — those three exist only inside
illustration/hero art. The product surface stays `paper` + `ink` + one
`dusk` accent. This is what makes "few buttons, each one matters" actually
read as minimal instead of decorated.

---

## 3. Typography — Thai + English pairing

Two roles only: **Display** (headlines, wordmark, hero lines — used
sparingly) and **UI/Body** (everything else: buttons, nav, paragraph text,
forms). Never use Display for body copy or UI chrome — it's a headline
instrument, not a workhorse font.

| Role | English | Thai |
|---|---|---|
| Display | **Fraunces** (SemiBold 600 / Italic 500 for accent words) | **Noto Serif Thai** (SemiBold 600) |
| UI / Body | **Inter** (Regular 400 / Medium 500 / SemiBold 600) | **Anuphan** (Regular 400 / Medium 500 / Bold 700) |

Why this pairing: Fraunces carries the same warm, slightly hand-cut
character as the ink-wash illustration without being a novelty/display
gimmick font — it has a soft, brush-adjacent optical quality at larger
sizes. Noto Serif Thai is its closest Thai-script equivalent in weight and
mood (a real serif, not a faux one) — use it for Thai headlines only, never
long-form Thai body copy (Thai serifs lose legibility fast at small sizes).
Inter and Anuphan are both clean, humanist, mobile-legible UI faces that sit
quietly under the display face without competing — Anuphan specifically
because it reads as modern Thai product type, not government-form Sarabun.

**Rules:**
- Display face appears at most once or twice per screen (hero line, page
  title). Everything else is UI/Body.
- Don't mix Fraunces Italic into long sentences — it's for single accent
  words/phrases only.
- Minimum body size 15px mobile / 16px desktop — Anuphan and Inter both hold
  up fine there; don't go smaller for "minimal" reasons, that hurts usability.

---

## 4. Logo

### Wordmark
`linkreed` — all lowercase, Fraunces SemiBold (600), tight tracking
(-1% to -2%), set in `ink` (or `paper` on dark surfaces). No tagline baked
into the lockup. Lowercase is deliberate — matches the "sketched, human,
unpolished-on-purpose" voice; an uppercase/title-case wordmark would read
too corporate for this brand.

### Mark
A single ink-brush stroke shaped like a bending reed blade, with one solid
node at the point where it bends — the moment a line becomes a shape. One
stroke, one node. This is a deliberate reduction from the original
reference image's brain/network-of-many-nodes motif: multiple nodes read as
generic "AI network" (the most overused visual in the category); a single
line + single node reads as "one idea, taking form" and stays unique to
LinkReed.

Construction: `viewBox 0 0 100 100`, stroke `ink` (or `dusk` as an
alternate single-color use on `paper`), stroke-width 6, round caps/joins,
no fill on the blade; node is a filled circle, radius 4.

```
M 22 88 C 16 60 24 34 46 18 C 57 10 68 8 78 13
+ filled circle at (78, 13) r=4
```

### Lockup rules
- Default lockup: mark to the left, wordmark to the right, gap = mark's own
  width x 0.4.
- Clear space around the full lockup (mark+wordmark or mark alone) = height
  of the mark on all sides. Nothing crosses that boundary — no button, no
  text, no illustration.
- Minimum size: mark alone never smaller than 20px tall (favicon/app-icon
  floor); full lockup never smaller than 24px tall.
- On dark surfaces, both mark and wordmark switch to `paper` (#F3EEE3), not
  `dusk` — keep it monochrome, don't recolor the mark to an accent hue.

### Don't
- Don't add more nodes to the mark ("looks unfinished" is not a valid
  reason to add complexity back — the single node is the point).
- Don't put the mark inside a colored badge/rounded square container —
  it stands on its own line, no container shape.
- Don't stretch, skew, or rotate the mark.
- Don't recolor the mark into `wash-blue`/`wash-sage`/`wash-rose` — those
  are illustration colors only, never the logo.

---

## 5. Layout & product principles

Set 2026-08-04, CEO-mandated: **minimal, mobile-first, few buttons but
every one load-bearing.**

- Design mobile viewport first (375-414px), then scale up — not the
  reverse. Every screen gets checked at mobile width before desktop.
- A screen earns a button by being the only way to do that action. If two
  buttons do overlapping jobs, cut one. No secondary/tertiary button rows
  "just in case."
- One accent color (`dusk`) for all primary actions. If everything is an
  accent-colored button, nothing is — this is why the palette split in §2
  exists.
- Generous whitespace over dense information. This is a brand built on
  restraint; a cluttered screen contradicts the positioning line before any
  copy does.
- Illustration (`wash-*` palette, ink-brush texture) lives in hero
  sections, empty states, and onboarding — never inside the working
  product chrome (dashboard, editor, published page). The user's *own*
  published page should look like their page, not like a LinkReed poster.

---

## 6. Must-pass checklist (run before shipping any customer-facing asset)

- [ ] No `wash-*` color used on a button, nav bar, input, or any UI chrome
- [ ] Only one accent color (`dusk`) driving primary CTAs on the screen
- [ ] Display face (Fraunces / Noto Serif Thai) used for headline only, not body
- [ ] Wordmark is lowercase, mark has exactly one node
- [ ] Checked at mobile width (375px) before anything else
- [ ] No em dash in the copy
- [ ] No AI-generic language ("powered by," "seamless," "unlock")

---

## reference_mood

CEO-provided reference (2026-08-04): watercolor + ink editorial brain/network
illustration. **Kept:** paper texture, ink-brush line quality, muted wash
palette, editorial/premium mood, hand-crafted (not generated) feel.
**Dropped:** the brain + multi-node network subject itself — flagged by CMO
as the most generic visual in the AI-product category; replaced with the
single-stroke reed mark in §4. CEO acknowledged the flag, chose to keep full
mood/texture/palette, subject swap accepted as the resolution.

**Correction (2026-08-04, same day):** first-pass wash palette was hand-eyeballed
and read wrong — olive-green instead of teal, pale pink instead of
terracotta/plum. CEO flagged "not the color tone," rejected once, said
"exactly like in the image." Re-sampled with Pillow directly against the
source JPG (region-cropped, quantized, near-white/near-black excluded) —
§2's `wash-*` values above are pixel-verified, not estimated. If this brand
needs re-sampling again, use that method, not visual guessing.
