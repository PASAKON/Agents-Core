# PLATE — `prop_valder_study_b` · THE PAINTING DUPE DROPS
CEO 29 Aug: `project_absence_prop_valder_study` uses the WRONG image. The real
painting is the one standing in Dupe's cart.

## Upload this reference
`docs/prompts/absence/REF-painting-from-cart.png` — the canvas cropped
straight out of `@prop_cart_b`. Bind `@prop_cart_b` as well.

**Do not describe this painting from memory.** Every earlier spec was written
from memory and every one was wrong: first 90x70 landscape, then "corrected"
to 70x90 portrait, and the face described as heavy impasto with a blade-scrape.

## What it actually is
- **LANDSCAPE, about 1.1 : 1 — very slightly wider than tall, nearly square.**
  Roughly 80 cm wide by 72 cm tall.
- **Thin black frame**, a few centimetres deep, plain, no moulding, no gilt.
- **A flat matte geometric abstract**: interlocking curved and angular blocks
  in rust red, burnt orange, ochre, cream, sage green, dusty pink, terracotta,
  with one black wedge low-centre. Poster-flat and chalky.
- **No impasto, no visible brushwork, no scrape, no texture relief.**

## The prompt
```
16:9 landscape, 2K. A single framed painting photographed straight on, flat to
camera, filling most of the frame against a plain neutral studio background.

KEEP SAME the painting in the reference image: KEEP SAME its proportions
(landscape, about 1.1:1, very slightly wider than tall), KEEP SAME every
colour, KEEP SAME the arrangement of the coloured blocks, KEEP SAME the thin
plain black frame, KEEP SAME its flat matte poster-like surface.

It is a geometric abstract: interlocking curved and angular blocks in rust
red, burnt orange, ochre, cream, sage green, dusty pink and terracotta, with
one black wedge low in the composition. The paint is flat and chalky with no
visible brush texture.

Clean, even, shadowless studio lighting. The whole canvas visible, nothing
crossing or overlapping it.

NEGATIVE: no portrait orientation, no painting taller than wide, no square
canvas, no impasto, no thick paint, no visible brushstrokes, no palette-knife
texture, no scrape marks, no varnish gloss, no gilt frame, no ornate frame, no
wide frame, no mount or matboard, no glass reflection, no cleaning cart, no
chrome rail crossing the canvas, no cart parts, no people, no hands, no wall
behind it, no gallery, no readable text, no signature, no HDR, no CGI sheen
```

## Note on the reference
A chrome cart rail crosses the canvas in the source crop. The prompt tells the
model to leave it out; check the output has a clean, unobstructed canvas.

## After it exists
Repoint `s2-accident.txt` and `s7-s9.txt` (SCENE 8b) from
`@project_absence_prop_valder_study` to the new Element, then re-fire S2.
