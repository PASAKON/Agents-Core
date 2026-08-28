# VIDEO QUEUE — authoritative, 2026-08-28 17:35

My tmux relays have been arriving fragmented — your own commit says
"reconstruct scattered CEO relays". **This file is the source of truth. Ignore any
partial pane message that disagrees with it.** I will update this file and ping
you with one short line whenever it changes.

## RULES

- **Never let the generate slot sit idle.** CEO, 17:05. Unlimited video costs
  nothing, so a clip we later re-shoot is free — an idle slot is not.
- **One take per scene.** No second takes of anything.
- **Tolerance: 10–20% drift is fine.** Things must *read* as the same, not match
  pixel for pixel.
- **Pre-fire gate, every time:** 720p · 16:9 · duration set with the ArrowRight
  slider and read back · all refs bound with thumbnails zoomed · Generate price
  read off a **zoomed screenshot**, never a JS scrape.
- File to `All Scene/<SCENE>/`. Commit the asset id **before** downloading.
- Watch every clip and describe it shot by shot.

## FIRE IN THIS ORDER

These need **no** plate that is still being remade:

1. **S13** — `s13-the-back-door.txt` · 25s · exterior behind the museum ·
   refs `loc_exterior` `char_valder` `char_workman` · 51 spoken words so the
   duration must genuinely hold 25s
2. **S1C** — `s1-angles.txt` · 8s · the cart detail · refs `loc_hall_big_e` if it
   exists yet, otherwise `loc_hall_big_d`, plus `prop_cart_b` (`bc89ef6c`)
3. **S1F** — `s1-angles.txt` · 8s · the hands · room barely visible
4. **S1A** — floor-level · 10s
5. **S1B** — waist up · 10s
6. **S1G** — past the column · 10s

**BOTH LOCATION PLATES NOW EXIST (18:00).** Every prompt file has been swept onto
the new names and re-synced to your worktree, md5-verified. Re-read any prompt
before firing it. Story order from here:

7. S3 (`s3-interpretations.txt`) → S4 → S5 → S6 → S7 → S8a → S8b → S8c → S9 →
   S10 → S11 → S12 → S15 → S16 → S17 → S18 → S1D → S1E

## ELEMENT SWAPS — use the new names everywhere

| old | new |
|---|---|
| `prop_cart` | **`prop_cart_b`** ✅ exists |
| `char_woman_b` | **`char_woman_c`** ✅ exists |
| `char_gentleman` | **`char_gentleman_e`** ✅ exists |
| `loc_hall_big_d` | **`loc_hall_big_e`** ✅ exists |
| `loc_wall_pov_c` | **`loc_wall_pov_d`** ✅ exists |

## WAITING ON THE CEO — do not invent these

S14's dialogue. Everything else in the film is written.
