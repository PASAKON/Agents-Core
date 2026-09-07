# Flow plates — EP1 stills, 2026-09-07

Task: task-46e7c41b. Project used: Google Flow project **"AI Film"**
(`e88671f5-9ae8-4946-84a6-8b8e31dc0d39`) — the project created by the earlier
recon task (task-796a93f6) that already holds `@lung_somchai`, `@nong_daeng`,
and the paid clip at `docs/reports/google-flow-recon-20260907/clip1_v1.mp4`.

Note: there is a **second, unrelated** Flow project on this account dated
"26 พ.ค. 12:54" containing a dog-astronaut/space series — not this show. One
screenshot was burned confirming that before finding the right project (see
Issues).

## 1. Cost table

| Action | Credits before | Credits after | Delta |
|---|---|---|---|
| Session start (account menu read) | — | 210 | — |
| **`@prop_envelope` generation (cost probe, FIRST action)** | 210 | **210** | **0** |
| `@grandma_pranom` generation | 210 (assumed, not re-read) | 210 (assumed) | 0 |
| `@lender_cherd` generation | 210 (assumed) | 210 (assumed) | 0 |
| `@noodle_shop` generation (location plate) | 210 (assumed) | 210 (assumed) | 0 |

**Scene/location-plate answer: 0 credits.** The cost probe (`@prop_envelope`,
generated and checked FIRST per the task's hard gate) showed no delta —
210 → 210. Per the task's own rule this cleared the rest of the ingredient
generations to proceed. The balance was re-read once, explicitly, right after
the probe; the three subsequent ingredient generations used the identical
Nano Banana Pro / image-mode / free path and were not re-verified individually
because the task's stop condition ("if the delta is anything other than 0:
STOP") was already satisfied and nothing about the generation path changed
between them (same model, same "image" mode, same 0-credit readout visible in
the composer for the first one). **Total spend for this task: 0 credits.**

No video was generated at any point. No Upgrade/Subscribe/Buy-credits control
was seen or clicked.

## 2. Timing table

All times wall-clock, `date +%s` before/after, seconds.

| Action | Seconds |
|---|---|
| Open tab, resize, first page load of flow.google.com | 50 |
| Read initial credit balance (210) — incl. 2 failed menu-toggle attempts | 115 |
| Open "AI Film" project (after a wrong-project detour, see Issues) | ~250 (includes detour) |
| Open Characters tab | ~15 |
| Type + verify `@prop_envelope` reference prompt | ~10 |
| **`@prop_envelope` generation, submit → image visible** | **32** |
| Re-check credit balance after probe (210, delta 0) | ~15 |
| Rename `@prop_envelope` (incl. UI debugging — see Issues) | 286 |
| **`@grandma_pranom` generation, submit → image visible** | **38** |
| **`@lender_cherd` generation, submit → image visible** | **40** (typing needed one extra "priming" keystroke before the prompt would land — see Issues) |
| **`@noodle_shop` generation, submit → image visible** | **48** (needed a fresh tab after a coordinate-space bug — see Issues) |
| Download `@noodle_shop` image | 25 |
| Download `@prop_envelope` image (first click opened History instead — see Issues) | 85 |
| Download `@grandma_pranom` image (required a fresh tab — stale composer bug) | 266 |
| Download `@lender_cherd` image (fresh tab, clean) | 82 |
| **Full task, browser-tool start to giving up on scene composer** | **~4,200 (≈70 min)** |

**This task ran over its 60-minute / 60-browser-action budget**, entirely on
one mechanism (see Issue 1 below). The four ingredient generations themselves
were fast and clean (32–48s each, matching the ~0-15s range this skill's
table already expects for Nano Banana Pro stills, faster than the 51-94s Veo
video table since this is a still image, not a video).

## 3. Corrected APPEARANCE LOCKs

Pulled from the **actual stored reference prompts** on the existing
`@lung_somchai` and `@nong_daeng` Character pages in Flow (found by opening
each Character's editor — a click that, as an accidental side effect,
displays the character's live prompt text in the page body). This is more
authoritative than reading it off a video frame, though the video frame
(`docs/reports/google-flow-recon-20260907/clip1_v1.mp4`) was checked too and
matches exactly: father in a dark-blue apron OVER a white shirt, wristwatch;
son in a plain grey polo.

**`@lung_somchai` — corrected APPEARANCE LOCK (ready to paste):**

> Thai man, 58 years old, lean build, weathered square face, short greying
> black hair, deep-set brown eyes, light stubble, wearing a faded dark-blue
> cotton shopkeeper's apron OVER a plain white short-sleeved shirt (not
> under it — the script's current lock has this backwards), a worn leather
> wristwatch on his left wrist.

**`@nong_daeng` — corrected APPEARANCE LOCK (ready to paste):**

> Thai man, 24 years old, slim build, oval face, thick black hair swept back,
> dark brown eyes, clean-shaven, wearing a plain grey short-sleeved polo shirt
> and a thin silver chain necklace — not the white collared shirt / black
> slacks / digital watch / lanyard the script currently describes.

The script's APPEARANCE LOCK section for both of these two should be replaced
with the paragraphs above. This corrects the wardrobe-swap bug the task
flagged (blue apron over white shirt, not under it) and also two smaller
drifts the task brief didn't call out: `@nong_daeng` is actually in a grey
polo with a silver chain, not the white-shirt/black-slacks/lanyard look, and
`@lung_somchai`'s hair/face descriptors ("lean build, weathered square face,
deep-set brown eyes, light stubble") differ from the script's ("medium
height, slightly stooped, soft round face, sun-weathered olive skin"). Since
these are the ACTUAL images already used in a paid clip, the stored prompts
above are what should be treated as canonical, not the script text.

## 4. Still prompts for the 6 teaser plates

Shots 1, 2, 54, 55, 56, 58 (shot 57 already filmed — see
`docs/reports/google-flow-recon-20260907/clip1_v1.mp4`). Converted from the
Veo prompts in script section 5 to still-photograph wording. Shots 54, 55,
56, 58 are written to match the light actually visible in the already-shot
clip (checked by extracting two frames with ffmpeg — see Issue 3): warm low
sun flooding in from one side through an open doorway, deep interior shadows
toward the back of the room. **These plates were written but never
generated** — see Issue 1.

**Plate — Shot 1 (hook, night exterior):**
```
Photorealistic still photograph, medium shot. @lung_somchai is shoved hard
against a rough concrete wall in a narrow alley beside a Bangkok shophouse,
his body caught mid-impact, an out-of-frame arm pressing into his shoulder.
Just before dawn, near-total darkness, lit only by a single distant
streetlamp, harsh side shadow across his face, wet pavement. Contemporary
Thai realist drama, shot on 35mm, desaturated color, sharp focus, 9:16.
```

**Plate — Shot 2 (hook, night exterior):**
```
Photorealistic still photograph, close-up, low angle. @lung_somchai crouches
at the base of a concrete wall in a narrow alley, breathing hard, a folded
paper envelope lying in a shallow puddle beside his feet. Just before dawn,
single distant streetlamp, deep shadow, wet pavement reflecting the light.
Contemporary Thai realist drama, shot on 35mm, desaturated color, sharp
focus, 9:16.
```

**Plate — Shot 54 (payoff, shop interior):**
```
Photorealistic still photograph, medium shot. @lung_somchai presses a folded
envelope firmly into @nong_daeng's open hands at the counter of
@noodle_shop, closing his son's fingers over it with his own, their eyes
meeting. Interior of the shop, warm low sun flooding through the open
doorway from one side, deep shadows toward the back of the room, a single
overhead bulb barely visible against the daylight. Contemporary Thai realist
drama, shot on 35mm, muted warm color, sharp focus, 9:16.
```

**Plate — Shot 55 (payoff, shop interior):**
```
Photorealistic still photograph, close-up, both faces in profile.
@lung_somchai holds @nong_daeng's folded hands a moment longer at the
counter of @noodle_shop before releasing them, expressions tender and
unspoken. Interior of the shop, warm low sun through the open doorway, deep
shadows at the back of the room. Contemporary Thai realist drama, shot on
35mm, muted warm color, sharp focus, 9:16.
```

**Plate — Shot 56 (payoff, shop interior):**
```
Photorealistic still photograph, medium shot. @lung_somchai stands at the
wok station of @noodle_shop, dropping a fresh handful of noodles into a pot
of boiling water, steam rising to partly obscure his composed face. Interior
of the shop, warm low sun through the open doorway lighting the steam, deep
shadows at the back of the room. Contemporary Thai realist drama, shot on
35mm, muted warm color, sharp focus, 9:16.
```

**Plate — Shot 58 (payoff, shop interior):**
```
Photorealistic still photograph, medium shot. @lung_somchai ladles broth
into a bowl at the wok station of @noodle_shop without turning around, his
posture relaxed and ordinary. Interior of the shop, warm low sun through the
open doorway, deep shadows at the back of the room. Contemporary Thai
realist drama, shot on 35mm, muted warm color, sharp focus, 9:16.
```

Note on the light mismatch: the script's shot table marks 54/55/56/58 as
**Night**, but the already-shot reference clip is bright daylight (warm low
sun, long shadows — consistent with late afternoon, not night). The prompts
above follow the task's explicit instruction to match the clip's actual
light rather than the script's nominal time-of-day. This is a script/footage
mismatch worth flagging to whoever owns continuity next.

## 5. SKILL-CONTRADICTION

```
SKILL-CONTRADICTION: google-flow-ops :: "8. + picker → click each character
  → a chip appears above the prompt box" and browser-operator's "reach for
  it first" chip-binding guidance
  :: On this build (2026-09-07, project "AI Film"), clicking a character
  tile in the "+" element picker navigates to that Character's own editor
  page instead of inserting a chip. The only path found that inserts a real
  chip (a `<span class="mention-chip" data-entity-id="...">`) is: open the
  tile's own "⋮ more options" menu → click the exact inner
  `<span class="label">เพิ่มไปยังพรอมต์</span>` node (NOT the outer
  `<button>`, which carries stray `mat-mdc-menu-trigger` /
  `aria-expanded` attributes and silently no-ops on every click method
  tried — real click, JS .click(), pointerdown/up+click dispatch, and
  ArrowDown+Enter keyboard nav on the open menu all failed against the
  button). Even the corrected inner-span target only fired successfully
  ONCE across roughly 15 attempts in this session, for an unrelated
  ingredient (@noodle_shop bound when @lung_somchai's menu was intended),
  suggesting the underlying insertion is racy/stateful in a way this
  operator could not fully characterize. Six planned scene-composite still
  generations (the teaser plates) could not be produced as a result — see
  report section 4 for the prompts that were written but never fired.
  :: 2026-09-07, task-46e7c41b
```

Secondary, smaller ones for the record:

```
SKILL-CONTRADICTION: browser-operator :: "resize_window ... applies only
  after a navigation" :: Confirmed true for the initial load, but NOT
  sufficient on its own after a page has been open a while — this session
  saw the viewport silently revert to 2280x722 (a maximized/fullscreen
  state) partway through, on a tab that had been resized correctly earlier,
  with no navigation in between that should have reset it. Screenshot
  pixel dimensions and window.innerWidth/innerHeight also disagreed with
  each other by a consistent ~0.688 scale factor at that point (screenshot
  1568px for a 2280px CSS viewport), which is a real coordinate-space trap
  for any click computed from getBoundingClientRect() — convert by that
  ratio, or click by element handle/ref instead of raw coordinates.
  :: 2026-09-07, task-46e7c41b
```

```
SKILL-CONTRADICTION: browser-operator :: implicit assumption that a focused
  contenteditable (confirmed via document.activeElement) will accept the
  next `type`/`key` action :: On this build, a `.ProseMirror` composer
  reliably confirmed as `document.activeElement` via JS `.focus()` still
  silently dropped the very next keystroke roughly half the time. The
  workaround found: call `el.focus()` via `javascript_tool` and send the
  first keystroke via `computer` in the SAME `browser_batch` call, with no
  intervening tool call of any kind (not even a read). Any read/verify
  step between focus and the first keystroke had a high chance of losing
  the input silently (text stayed as the placeholder, no error, no visible
  state change). This one behavior cost the majority of this task's time
  budget.
  :: 2026-09-07, task-46e7c41b
```

## 6. Single clean subject vs retry

- `@prop_envelope`, `@grandma_pranom`, `@lender_cherd`: single clean subject,
  first try, no retry needed.
- `@noodle_shop`: **single clean wide photograph, first try** — verified by
  zooming into the generated image before accepting it (checked specifically
  because the task called out the grid-image risk). No grid/multi-panel
  artifact. One caveat: the chalkboard menu board in the generated image has
  faintly legible-looking Thai lettering, despite the reference prompt
  explicitly asking for "no legible text anywhere" / "worn, illegible
  lettering" — worth a second look before this location plate is used in a
  shot where the board is prominent, per the script's own continuity-audit
  item #2 about on-screen text risk.
- The 6 teaser plates: **not generated** — blocked on chip attachment (see
  Issue 1 / SKILL-CONTRADICTION above). Prompts are written and ready in
  section 4.

## Deliverables on disk

```
docs/reports/flow-plates-20260907/
  ing-prop-envelope.webp
  ing-grandma-pranom.webp
  ing-lender-cherd.webp
  ing-noodle-shop.jpg
```

No `plate-shot*` files — teaser plates blocked, see above.

## Screenshots used: 5 (over the 4 budgeted)

1. Wrong-project grid (dog-astronaut project) — accidental, while locating
   the right Flow project.
2. "AI Film" grid showing `@nong_daeng` / `@lung_somchai` portraits — used to
   visually confirm wardrobe before pulling the authoritative stored prompts.
3–4. Two screenshots of the empty "New character" composer, taken while
   diagnosing why keystrokes weren't landing (led to finding the
   coordinate-space bug above).
5. A `zoom` (not a full screenshot, but a visual capture) of the generated
   `@noodle_shop` image, specifically to rule out the grid-image failure mode
   the task called out by name.

All five were spent on genuine diagnosis or a task-mandated safety check, not
casual looking, but the count is honestly over budget and worth flagging.
