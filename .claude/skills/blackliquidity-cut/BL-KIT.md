# BLACK LIQUIDITY — video kit

Theme and component catalogue for the channel's motion graphics. Everything here is
inline in `index.html` under the `BL KIT` banner; this file is the map, so a designer
can extend the kit without reading the whole composition.

## Theme (CEO 2026-09-18: "ดำ แดง ขาว, แดงเน้นเป็นเรืองแสงแบบนีออน")

| token | value | where it came from |
|---|---|---|
| `--ink` | `#07080A` | ground, darker than the footage's own `#0B0A0A` so the plate reads as black |
| `--red` | `#E0202F` | brand red |
| `--neon` | `#FF2D40` | the glowing red — every emissive edge uses this, never `--red` |
| `--white` | `#F4F6F7` | body text |
| `--yellow` | `#F4DF14` | measured off the ฿1300 reference edit's keyword colour |
| `--muted` | `#98A0A8` | labels, captions |
| `--glow-s/m/l` | 3 box-shadow ramps | neon bloom at three intensities |

Red is **always** emissive: anything using `--neon` carries a `--glow-*` shadow and a
`text-shadow`. A flat red line is off-theme.

## Safe area — the phone crops the frame (measured 2026-09-18)

| token | value | means |
|---|---|---|
| `--safe-left` | `120px` | below this the phone crops it away (`x < 97` is not rendered at all) |
| `--safe-top` | `252px` | above this is TikTok's own For You / Following nav |
| `--safe-right` | `240px` | content ends at `x = 840`; the like/comment rail owns `x 873-983` |
| safe bottom | `y = 1500` | TikTok's caption block starts at `y ~1550`, its scrub bar at `y ~1789` |

A 9:16 video is scaled to **cover** a 19.5:9 screen — it is not letterboxed, so
97px of each side is gone. `.blk` is bound to these variables; `.blk.wide` pulls
the right margin back to 120 and is only legal for a block that ends above
`y = 900`. Gate it with `python3 scripts/bl_tools.py safezone cut/index.html`,
never by looking at the preview — the preview shows the whole frame and the
phone does not.

Fixed positions that follow from it: brand bug `right: 150px; top: 310px`, logo
`height: 60px`; legal label `y = 1430`; subtitle layer `y = 1300`. A text block
whose `top` is under 900 carries `.blk.wide` (right margin back to 120) so it is
centred on the frame; everything lower keeps 240 and stays clear of the rail.

## Motion grammar — not negotiable, it is measured

Taken frame by frame off the editor the CEO paid ฿1300 (see the memory note
`reference-reverse-engineer-editor-motion`):

- **Every reveal is `expo.out`.** Fitted RMSE 0.0078 on a strikethrough and 0.0479 on a
  text wipe, against 0.1104 for the next-best curve.
- **Text arrives by `clip-path` wipe, left to right — never a fade.** The reference's
  text hits full luminance on its first visible frame.
- **Rules, strikes and connectors `scaleX`/`scaleY` from a left/top origin.**
- Chips and cards stagger at 110–160 ms.

## Catalogue

### Frames
| class | what |
|---|---|
| `.bl-frame` | neon border box with an outer bloom |
| `.bl-bracket` | four corner brackets, no full border — for callouts |
| `.bl-redact` | solid black bar with a neon edge, for hiding a value |

### Lines
| class | what |
|---|---|
| `.bl-rule` | horizontal sweep rule, `scaleX` from left |
| `.bl-vline` | vertical connector, `scaleY` from top |
| `.bl-strike` | strikethrough, `scaleX` from left |
| `.bl-div` | static hairline divider |

### Surfaces
| class | what |
|---|---|
| `.bl-card` | claim card: left neon edge, name, claim, corner badge |
| `.bl-rulecard` | big numbered rule: index disc, headline, detail |
| `.bl-stat` | one large figure plus a label |
| `.bl-row` | checklist row with a tick disc |
| `.bl-chip` | small pill, `.hot` variant for the flagged one |

### Text
| class | what |
|---|---|
| `.bl-xl / .bl-lg / .bl-md / .bl-sm` | 104 / 82 / 62 / 44 px, all with the black outline |
| `.wipe` | the clip-path reveal wrapper |
| `.y` / `.n` | yellow keyword / neon keyword |

### Backgrounds
| class | what |
|---|---|
| `.bl-bg` | flat ink with a top neon wash |
| `.bl-bg.grid` | adds a faint neon grid |
| `.bl-bg.scan` | adds horizontal scanlines |

## Helpers in the composition script

`wipe(sel,at,dur)` · `sweep(sel,at,dur)` · `drop(sel,at,dur)` · `pop(sel,at,stagger)` ·
`show(sel,at)` · `hide(sel,at)` — all default to `expo.out`.

## Extending it

Add the class here and in the `BL KIT` style block, then use it from a `BLOCKS` entry.
Do not introduce a new easing or a non-emissive red without saying why.
