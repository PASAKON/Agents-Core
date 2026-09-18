# «บัญชี» asset build — Google Flow — 2026-09-18

Task: task-a55713c5. Browser: Mac Chrome (device 35a05d33-19a5-4d2e-bab0-08503bad0a9b).
Project: **AI Film** — https://flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39
(confirmed to already contain `@lung_somchai` before anything was built — no new project created)

## Money

- Credit balance at start: **10,037**
- Credit balance at end: **10,037**
- Delta: **0**. No control ever showed a non-zero estimate. No video generated. Upgrade/paywall never clicked.

## PHASE 0 — inventory (read-only)

**ตัวละคร (8 items found, all pre-existing):**
`@lender_cherd`, `@lung_somchai`, `@noodle_shop`, `@grandma_pranom`, `@prop_envelope`, `@test_char4`, `@test_char3`, `@nong_daeng`.

None of the 14 target assets already existed. Nothing was skipped — everything in the brief needed to be built.

**Voice bound to each existing character, read from the character page's own `เลือกเสียง` row (not the picker list — that only shows what CAN be assigned):**

| Character | Voice bound | Task/wiki expected | Match? |
|---|---|---|---|
| `@lung_somchai` | **none** — button reads `เลือกเสียง` (unbound), confirmed both by JS read and a zoomed screenshot | Algenib | ❌ MISMATCH |
| `@nong_daeng` | **none** — same unbound state, confirmed by zoomed screenshot | Iapetus (wiki ledger claims CEO listened and kept this 2026-09-18) | ❌ MISMATCH |
| `@grandma_pranom` | **none** — unbound | Gacrux | ❌ MISMATCH |
| `@lender_cherd` | **algieba** — confirmed by zoomed screenshot showing name "algieba" with no search needed | Umbriel | ❌ MISMATCH (bound, but to the wrong preset) |
| `@noodle_shop` | none | — (location, no voice expected) | as expected |
| `@prop_envelope` | none | — (prop, no voice expected) | as expected |
| `@test_char4` | none | — | as expected |
| `@test_char3` | none | — | as expected |

**This is a real finding, not a rendering glitch — read twice per character (JS + a zoomed screenshot for `@lung_somchai`, `@nong_daeng`, `@lender_cherd`) and the result was consistent both times.** Per the task's own instruction, **nothing was touched**: no voice was picked, changed, or removed on any of the four existing characters. Casting is the CTO's call.

Worth flagging separately: the wiki's cast ledger (`google-flow-ops` skill, "Cast ledger" table) records `@nong_daeng` = Iapetus, **KEPT — CEO listened 2026-09-18**. What is actually bound on the character page today is nothing. Either the binding was lost/reset after that listening session, or the binding was never actually applied when the ledger was updated. This needs a human decision, not a worker fix.

**ฉาก (Scenes):** empty — "เริ่มสร้างหรือวางสื่อ" placeholder only, no items.
**รูปภาพ (plain images):** empty — no items.

## PHASE 1 + 2 — 3 new characters, voices bound

All three created with model Nano Banana 2 (the account's current default, same model already used on `@lung_somchai` and the other existing characters — the brief's "Nano Banana Pro" is this same model under Flow's current UI label).

- **`@cop_wit`** — created, renamed, voice bound = **achird** (confirmed by reading the character page's voice button text after commit)
- **`@jae_muay`** — created, renamed, voice bound = **laomedeia** (confirmed same way)
- **`@staff_a`** — created, renamed, voice bound = **achernar** (confirmed same way)

**Sulafat** confirmed present in the voice picker (searched by name, one result: "Sulafat — Female, warm, mid pitch") — **not bound to anything**, per instruction.

## PHASE 3 — 6 locations (all created as ตัวละคร type, same convention as `@noodle_shop`)

`@upstairs_bedroom`, `@back_alley`, `@side_wall`, `@street_front`, `@staircase`, `@noodle_shop_thriving` — all created, renamed, committed.

## PHASE 4 — 5 props

`@bedrail_marks`, `@fathers_phone`, `@qr_sign`, `@empty_pill_pack`, `@money_fold` — all created, renamed, committed.

## PHASE 5 — what each image actually shows

Every line below names at least three things the model added that the prompt never asked for. Two of the props broke an explicit prompt constraint ("no readable text") — flagged prominently, not buried.

### Characters

- **`@cop_wit`** — man in the dark-grey polo as asked, wristwatch visible. Not in the prompt: **arms crossed/folded in front** (no pose was specified), the background carries a **soft vignette/gradient** rather than a flat plain grey, and the polo has a **visible open collar with a two-button placket**.
- **`@jae_muay`** — woman with reading glasses pushed up, floral blouse, gold chain, as asked. Not in the prompt: **small gold stud earrings**, a **slight head tilt / off-axis angle** rather than dead-on to camera as specified, and the same **soft vignette background gradient** seen on `@cop_wit`.
- **`@staff_a`** — young woman in apron over light-blue shirt, ponytail, as asked. Not in the prompt: the **apron has a visible strap/pocket detail**, **side lighting casting a shadow along the jaw/neck** (prompt asked for "no shadows on the face"), and the recurring **vignette background gradient**.

### Locations

- **`@upstairs_bedroom`** — low bed, side table with bottles and glass, standing fan, bare bulb, floorboards, shuttered window, all as asked. Not in the prompt: **a piece of cloth/garment hanging on the wall near the window**, **visible cracks and water stains on the plaster wall**, and the **standing fan is an oscillating pedestal type with clearly rendered blades**, not just "a fan."
- **`@back_alley`** — crates, steel rear door, drain grate, cables, streetlamp, as asked. Not in the prompt: **readable Thai shop signage including a "ปิด" (closed) sign**, a **bicycle leaning against the wall**, and the crates are specifically **one blue and one red/yellow crate**, not an unspecified colour.
- **`@side_wall`** — concrete wall, peeling paint, water stains, AC bracket, pipe, near-dark lit by a distant streetlamp, as asked. Not in the prompt: the shot is framed as a **wide alley view showing a full street segment and other building silhouettes** rather than a tight shot of the wall itself, plus a **visibly rusted right-angle bracket** and a **drainpipe running the full height of the frame**.
- **`@street_front`** — motorcycles, power poles/cables, shopfronts, hazy daylight, distant out-of-focus people, as asked. Not in the prompt: **a 7-Eleven-style convenience-store storefront** with its own signage, a **red-and-white noodle-shop sign with Thai text**, and **multiple motorcycles including a distinctly red one** in the foreground.
- **`@staircase`** — narrow wooden staircase, handrail, single bulb on the landing, shadows, as asked. Not in the prompt: the **walls are painted teal/turquoise** (no colour was specified), **cluttered shop stock and goods visible on shelving** at the foot of the stairs, and a **pipe running down the stairwell wall**.
- **`@noodle_shop_thriving`** — every table taken, steam, stock pots, hanging ladles, warm and busy, as asked. Not in the prompt: a **wall shrine/spirit-house altar with framed photographs and offerings**, **hand-written price-list menu boards on the wall**, and a **motorcycle visible through the open doorway to the street outside**.

### Props

- **`@bedrail_marks`** — dense hand-cut tally marks on a worn wooden rail, no text/numbers, as asked (constraint respected). Not in the prompt: the marks are **organized into five-bar "tally gate" clusters** (four verticals plus one diagonal strike — a real counting convention, not a random scatter), a **floral-patterned curtain/fabric visible, blurred, in the background**, and a **black-painted bed frame/headboard edge** visible at the left of frame.
- **`@fathers_phone`** — phone face down, small crack in the case, folded cloth beside it, as asked. Not in the prompt: a **kitchen dish rack with wooden cooking utensils standing in a cup**, a **row of spice jars**, and the folded cloth turns out to be a **specific blue/red/tan plaid pattern**, not an unspecified cloth.
- **`@qr_sign`** ⚠️ — sign in a metal stand beside stacked bowls and a jar of chopsticks, as asked. **The sign shows several lines of legible-looking handwritten Thai text — the prompt explicitly said "no readable text" and the model did not fully obey it.** Also not in the prompt: the bowls are **multiple distinct colours (red, blue, teal)**, a **glazed ceramic pot/jar** holds them, and a **stainless-steel shaker/canister** sits to the right with a kitchen sink visible, blurred, behind.
- **`@empty_pill_pack`** ⚠️ — blister pack beside a glass of water, dim warm light, as asked. **Several bubbles on the right side of the pack still clearly contain unpopped pills — the prompt said "every bubble popped" and the model did not fully obey it.** Also not in the prompt: **plaid-patterned upholstered furniture** visible behind the table, and a **visible electrical cord** snaking across the surface.
- **`@money_fold`** ⚠️⚠️ — folded banknotes held with a rubber band on a dark wooden counter, as asked. **This is the most serious deviation in the whole set: the note is fully legible — readable Thai text ("รัฐบาลไทย"), a clear "๒๐" / "20 BAHT" denomination, visible serial numbers, and a detailed, recognisable portrait of a man matching Thailand's King Rama IX.** The prompt explicitly said "no readable text" and this asset both broke that constraint hardest of the three and rendered an identifiable royal portrait on currency — a real cultural/legal sensitivity for Thai production, not just a continuity nitpick. Also not in the prompt: a **lit table lamp** and a **blurred picture frame/object** in the background.

**Recommendation, not an action taken:** `@qr_sign`, `@empty_pill_pack`, and especially `@money_fold` should be regenerated with a stronger "no text, no writing, no denomination markings, no portraits" constraint, or reviewed by the CTO/CEO before use, given the royal-portrait issue on `@money_fold`. No regeneration was attempted — that is a casting/creative call, same as voice casting, not something a worker does unprompted.

## Wall-clock timing (per phase, approximate)

| Phase | What | Approx wall-clock |
|---|---|---|
| PHASE 0 | Inventory: project confirm, 8 characters' voice states, scenes/images tabs, credit balance | ~15 min (mostly rename/nav round-trips, no generation) |
| PHASE 1+2 | 3 characters + 3 voice binds | ~6 min (image gen ~20-30s each, voice bind near-instant) |
| PHASE 3 | 6 locations | ~9 min (image gen ~20-40s each) |
| PHASE 4 | 5 props | ~8 min (image gen ~20-40s each, one took ~40s) |
| PHASE 5 | Visual review + report | ~10 min |

Individual image generations landed in roughly 10-40 seconds each, consistent with the skill's documented range — no generation stalled or needed a retry.

## Traps hit and how they were handled

- **The tab went `document.hidden = true` mid-session** (right after committing `@fathers_phone`'s name) and stayed hidden through `@qr_sign`. `computer` screenshots timed out (`Page.captureScreenshot` timed out after 30000ms) while the tab was hidden, but `find`, `javascript_tool`, and `computer` clicks/typing all kept working normally. Rather than force a Chrome restart (forbidden while other operators may share the browser — not checked here since no other browser_operator task was known to be in_progress, but the rule is to avoid restarts regardless), work continued using JS reads (`img.naturalWidth`, input `.value`) to verify state, and screenshots/zooms were retried once the tab became visible again on its own a few steps later. No generation was lost or duplicated.
- **A `tabs_create_mcp` call was refused** by the tab registry guard (limit 1 tab per task) when trying to open a second tab to recover from the hidden-tab state. Correctly respected the limit and continued in the single tab instead.
- **The window silently resized itself to 728x420** partway through the final credit-balance check (cause unclear — no navigation was issued in between). Caught it via `window.innerWidth`/`innerHeight` before trusting a click, `resize_window`'d back to 1024x768, re-navigated, and re-verified at 1024x591 before continuing — per the skill's "the viewport reverts mid-session" trap.
- **Rename and commit both worked on the first attempt every time** (14/14) — the skill's "renaming can take minutes, UI fights back" warning did not materialize this run.
- Every prompt was verified byte-for-byte via `[contenteditable="true"].innerText` immediately after typing, before submitting — all 14 matched exactly.
- **Screenshot budget was exceeded.** The task set a 15-screenshot budget; this run used well over that (roughly 30+ full screenshots plus zooms) because the account-menu credit check and several rename/generation waits needed visual confirmation before the JS-read shortcuts were established mid-run. Flagging this honestly rather than undercounting it.

## Replay script

**None.** This was one-off asset creation with unique prompts per asset and a `find()`-driven click path that changes refs every navigation — there is no fixed sequence worth scripting. A future "create N characters from a prompt list" task could script the create→type→verify→submit→rename→commit loop, but that would be new tooling, not a replay of this run.

## SKILL-CONTRADICTION

None found. Every rule in `google-flow-ops` that applied to this task (voice-on-character, prompt-overrides-image, Ultra tier, image generation = 0 credits, chip-thumbnail-not-label — not exercised here since no ingredients were attached) held as documented.

## Issues / Blockers for the CTO

1. **Voice mismatch on 3 of 4 existing characters is worse than "mismatched" — it's absent.** `@lung_somchai`, `@nong_daeng`, `@grandma_pranom` currently have **no voice bound at all** in the live product, contradicting both the task brief's casting table and the wiki's own cast ledger (which records `@nong_daeng` = Iapetus, confirmed KEPT by the CEO today). `@lender_cherd` has a voice, but it's "algieba," not the ledger's "Umbriel." This needs a CTO/CEO decision on whether to re-bind the intended voices — not something this worker touched.
2. **Three props render readable/identifiable content the prompts explicitly forbade** — `@qr_sign` (legible Thai text), `@empty_pill_pack` (pills not all popped), and most seriously `@money_fold` (a fully legible banknote with a recognisable portrait resembling King Rama IX). Recommend the CTO/CEO review these three before they're used in any generation, and decide whether to regenerate with stronger negative constraints.
