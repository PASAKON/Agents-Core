# TraderMindset — Poster prompt (v2)

> Externalized verbatim from `scripts/trader_mindset_batch.py` (`PRE`, `ART_STYLES`,
> `SCENES`, `build_poster_prompt`) on 2026-06-11. Drives the fal gpt-image-2/edit call
> that bakes ONLY the short Thai hero word (hybrid policy, wiki §3.5 — long lines are
> never baked; they are composited later with the pinned IBM Plex Sans Thai font).
>
> The generator rotates `art_styles` and `scenes` per item (`idx % len`) so a round of
> 10 stays visually varied, then assembles `template`. Slots: `{{preamble}}`, `{{scene}}`,
> `{{style}}`, `{{hero_word}}`. `lessons_guidance` is appended (with a leading space) only
> when prior-round reject reasons are supplied; `{{lessons}}` is the reasons joined onto
> one line and marked non-rendering so the image model treats it as art direction.

## preamble

```text
Identity (Critical): strictly reference @image1 -- preserve the exact face, proportions, skin tone and hairstyle of the man; keep his black suit and black turtleneck; he must stay clearly recognizable. Palette STRICTLY deep navy (#0c1c2b) + warm champagne gold (#cdac65) only -- NO cyan, purple, magenta, teal or blue neon. Premium institutional fintech, photorealistic, 8k. 1:1 bold editorial personal-brand poster. Keep the TOP-RIGHT corner clean and empty for a logo. Do NOT add any logo, badge, English wordmark or watermark.
```

## art_styles

```text
a HUGE expressive hand-painted INK-BRUSH champagne-gold Thai display headline
a HUGE bold CHROME METALLIC 3D champagne-gold Thai display headline with glossy bevels
a HUGE bold rounded CALLIGRAPHY-style champagne-gold Thai display headline with flowing strokes
a HUGE ENGRAVED EMBOSSED champagne-gold Thai serif display headline with carved metal depth
a HUGE ART-DECO GEOMETRIC champagne-gold Thai display headline with inlaid gold-leaf facets and sharp angular strokes
```

## scenes

```text
The man stands three-quarter view, confident, in front of a wall of monitors showing gold candlestick charts on deep navy, blurred into warm gold bokeh, gold rim light.
The man sits at a trading desk, leaning back confidently, a large curved LED screen of gold candlestick charts blurred behind, warm gold key light.
Half-body, the man with arms crossed on a real navy trading floor at golden hour, gold bokeh, dramatic side rim light.
The man stands with hands in pockets by a dark penthouse window at night, city lights and gold candlestick reflections blurred into warm gold bokeh.
Close-up three-quarter portrait, the man adjusting his suit cuff, a softly glowing gold candlestick hologram floating beside him on deep navy, cinematic gold rim light.
```

## template

```text
{{preamble}} {{scene}} {{style}} '{{hero_word}}' fills the upper-left with bold textured strokes. Render ONLY that single Thai word as art -- do NOT draw any other sentence, sub-headline or small text anywhere. Keep the LOWER THIRD of the image a clean darker navy area with no text, reserved for a caption overlay added later. Render the hero word accurately and legibly.
```

## lessons_guidance

```text
Internal art-direction guidance (DO NOT render any of this as visible text on the image): {{lessons}} Keep the poster clean and on-brand.
```
