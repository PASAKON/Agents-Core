# Absence — Reload Probe, 2026-09-06

## THE ANSWER: RELOAD CLEARS IT — YES

A full-page reload cleared the disabled Generate state. This was **not** a real
account-level gate; it was stale client state in last night's tab. The queue
is not blocked.

## Step 1 — after reload (Seedance 2.5, Video tab)

| Field | Value |
|---|---|
| `disabled` attribute | `null` (absent) |
| `disabled` DOM property | `false` |
| React `isDisabled` | `false` |
| React `credits` | `45` |
| React `oldCredits` | `80` |
| React `freeGens` | `undefined` (same as last night — appears to just always be unset, not diagnostic) |
| Banner text | "Credits are running low! Over 90% already used" (present on load; dismissed manually via its × to inspect the composer underneath) |
| Unlimited toggle | **OFF** (`data-state="off"`, `aria-checked="false"`) — resets on reload as expected |

Note: default composer on load is the **Image** tab (Cinema Studio 4.0), not
Video. Switched to Video tab, then explicitly selected model **Seedance 2.5**
(default was Cinema Studio 4.0) before reading the button that matters. All
four values above are from the Seedance 2.5 / Video surface.

## Step 2 — fresh tab

**Not performed.** Step 2 is conditional on Step 1 finding it *still disabled*.
It was not — the reload alone cleared the disabled state — so per the task's
own instructions Step 2 was skipped and Step 3 proceeded.

## Step 3 — fired S2K

Turned Unlimited ON (one clean ref-click, `data-state` flipped to `on`
immediately). Zoomed the button: `UNLIMITED · ~~45~~ · 0`. Money gate clear.

Attached `docs/S2K-Render.MP4` as the video reference (upload → thumbnail
resolved → clicked tile → "Added to prompt box" confirmed, green check).
Pasted the full PASTE-block prompt from
`docs/prompts/absence/s2k-fix1-the-crowd-gathers.txt` via synthetic
`ClipboardEvent` (text/plain only), then did the End→space→Backspace sync tap.

**Chips: 8/8 unique elements bound, 0 error chips** (leaf-span selector from
the brief, confirmed working):
`critic_b, student_c, woman, visitor_b, visitor_a, cleaner_c, loc_wall_pov_e,
prop_cart_a_painted`. (14 total chip instances — each of the 6 characters is
named twice in the prompt by design, once in the position map and once in the
references section; that's expected, not a duplicate-binding bug.)

### The fire itself was not a deliberate, verified click — flagging this clearly

While working through the settings row (checking the duration slider, which
was still showing the wrong value), a `Page.captureScreenshot` CDP call timed
out. Per the hard rule ("any browser-tool error while on a Higgsfield page →
check for a fire before anything else"), I checked, and found:

- A **"Generation started"** toast.
- The project's asset count moved from **658 → 659**.
- A new card in the top-left slot reading **"Processing"**.
- Unlimited was **`on`** throughout this entire window and every read of the
  button showed a struck price with live **`0`** — so whatever fired, it fired
  free. There is no money exposure here.

I never intentionally clicked Generate. Best explanation: a native
`space`/`Enter` keypress sent as part of the End→space→Backspace sync tap (or
a duration-slider interaction) landed on a control other than the one
intended and triggered submission — the same class of failure the skill
documents for stray keys near this composer. I could not get a screenshot to
land in the following minutes to catch it in the act (CDP kept timing out on
that one call while `javascript_tool` kept working fine throughout — page was
never actually frozen).

**Consequence: the duration field was still reading `5s` (not the required
`12s`) at every point I could check it, both before and after the fire.**
720p / 16:9 / 1/4 / High / Sound On were all correct. So the take that is
rendering right now is very likely **5s, not 12s** — everything else in the
six-field spec matches.

### Six-field readback (best available — NOT a pre-click confirmed readback)

| Field | Target | Observed at fire time |
|---|---|---|
| Duration | 12s | **5s** (not changed before the fire happened) |
| Resolution | 720p | 720p ✓ |
| Model | Seedance 2.5 | Seedance 2.5 ✓ |
| Quality | High | High ✓ |
| Batch | 1/4 | 1/4 ✓ |
| Sound | On | On ✓ |

- **Price at click**: struck price, live `0` (Unlimited), confirmed by zoom
  immediately before this window and by repeated JS reads throughout (`45` →
  `35`→`15` struck values fluctuated with reference count changes; live digit
  was `0` every single time).
- **Chips bound**: 8/8 unique, 0 error chips (see above).
- **Fire time**: ~2026-09-06 00:3x UTC (not pinned to the second — discovered
  after the fact via toast + asset-count delta, not via a directly-observed
  click).
- **How verified**: "Generation started" toast + asset count 658→659 + new
  "Processing" card. Could not identify the job's actual bound settings from
  the DOM (the in-flight card exposes only a spinner + Cancel, no prompt/spec
  preview) and network-request logging started too late to catch the POST.
- **Drive filename (once rendered)**: `S2K-Fix1.MP4` per the brief, filed to
  `Drive All Scene/Fix-1/` — **not yet done**, the clip was still
  "Processing" when I stopped. Per the render-wait skill's explicit rule
  ("never make a worker sit and watch a render — the job ends the moment the
  fire is confirmed"), I did not sit and wait for it.

### What I recommend the CTO do next

1. Check the History for the new asset (should be right at the top, ~00:3x
   UTC). Confirm actual duration on the finished card.
2. If it came back at 5s (off-spec): the content/references/chips were
   correct, only the length is wrong — either accept it as a short take or
   have the next operator re-fire cleanly at 12s (composer state — text,
   refs, Unlimited — should still be intact in that tab if nobody touched it;
   I closed it per tab hygiene, but the render is server-side and unaffected).
3. Either way, file whatever comes out of this generation to
   `Drive All Scene/Fix-1/S2K-Fix1.MP4` per the brief ("whatever the
   verdict").
4. **Do not fire S2K again until this one's card shows fully complete** — the
   account allows only one Unlimited generation at a time and this one is
   already holding the slot.

## Two lanes

No CEO Credit-lane cards (`SEEDANCE 2.5 CREDIT` prefix) were touched,
downloaded, or filed.

## SKILL-OVERRIDE

`SKILL-OVERRIDE: browser-operator :: "worker's job ends the moment the fire
is confirmed, don't sit and watch the render" :: stopped and reported instead
of polling 20+ minutes for completion :: fire was confirmed via toast +
asset-count delta, task brief's own stop condition was met, and the task was
framed as short — waiting out a 20-40 min render inside this session would
have contradicted both the render-wait skill and the brief's own scope`
