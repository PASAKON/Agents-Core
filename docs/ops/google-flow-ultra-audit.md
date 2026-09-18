# Google Flow — Ultra upgrade audit (2026-09-18, task-68653632)

Read-only audit, driven by `browser-operator` + `google-flow-ops`. **Zero
generations fired.** Credit balance read at start and end of session was
**identical: 9,413 → 9,413.** No task-triggered spend occurred.

Concurrent-spend note per task brief: another CTO session was running two
shooters on this same account (task-abc83ea2, task-f0f67322, «บัญชี» องก์ 1)
during this window. The balance did not move between my start and end reads,
so either those shooters were between generations at both check-ins, or their
spend landed outside this window. Either way: **the delta is 0, and every
generation listed below is theirs, not mine — I fired nothing.**

Project used for read-only inspection: "AI Film"
(`e88671f5-9ae8-4946-84a6-8b8e31dc0d39`) — NOT the actively-shooting «บัญชี»
project, which I never opened, per the no-touch instruction.

---

## Answers, in the task's priority order

### 1. Credit balance — **9,413 credits.** Ultra has landed.
Read from account menu: `เครดิต Google Flow 9,413 เครดิต`. Not exactly 10,000
because the concurrent shooters had already spent ~587 credits before this
session started (consistent with the task's own warning). Confirms the
฿3,500 Ultra subscription is active and its pool is live.
Screenshot: `docs/ops/screenshots-flow-ultra-audit/credit-balance-9413-start.jpg`
Same read at end of session: **9,413** (unchanged — see top of report).

### 2. 1080p / upscale — **still does NOT exist. Ultra does not unlock it.**
Checked all four places named in the brief, all four came back negative:
- **Composer resolution facet** (settings panel, all 4 models): only **360p /
  720p** toggle for Omni 1.1 Flash. Veo 3.1 Lite/Fast/Quality don't even show
  a resolution toggle — no facet at all, so no 1080p/4K option to select.
- **Asset/output filter facet** (media grid filter panel, "ความละเอียด"):
  only **720p** and **360p** checkboxes. No 1080p, no 4K.
- **Finished-clip toolbar**: download icon, share, delete, history, "⋮" menu.
  The "⋮" menu's only download-related item is "ดาวน์โหลดโปรเจ็กต์" (download
  project) — no resolution submenu.
- **Right-click on the clip**: no context menu appears at all (native
  right-click is suppressed, no custom menu opens).

**Verdict: no 1080p option or upscale button exists anywhere in the product on
this Ultra account.** The CEO still needs Topaz (or another external upscaler)
if 1080p+ output is wanted. This confirms — does not overturn — the skill's
existing "no 1080p" entry.

### 3. Omni 1.1 Flash pricing — **confirmed unchanged.**
Read live from the settings panel, without clicking Submit:
- 720p / 8s / x1: **"การสร้างจะใช้ 12 เครดิต"** (12 credits) — matches skill exactly.
- 360p / 8s / x1: **"การสร้างจะใช้ 6 เครดิต"** (6 credits) — matches skill exactly.

### 4. Reference/ingredient chip cap — **confirmed at 10, empirically, without firing.**
Attached 10 existing project assets one at a time via the picker's
`เพิ่มไปยังพรอมต์` button, counting the composer's chip row after each attach
(reached 10 chips, visually confirmed twice). Attempted an 11th
(`@money_fold`): the picker excluded it from the list (as if attached), but
**the composer's visible chip count stayed at exactly 10** — no 11th thumbnail
appeared, no error toast, no disabled state on the `+` button. This matches
the skill's documented "10 image references" ceiling and is the practical cap
for this UI. No chips were left attached to any real prompt and nothing was
submitted; the draft was discarded by navigating away afterward (composer
state resets on navigation, per the skill's known trap).

### 5. The 4 characters and their voices — **all 4 exist, 3 voices match the ledger, 1 does NOT.**
Found in the "AI Film" project (Characters tab + media picker):

| Character | Voice bound (read from character page) | Ledger says | Match? |
|---|---|---|---|
| `@lung_somchai` | **algenib** | Algenib | ✅ |
| `@nong_daeng` | **iapetus** | Iapetus | ✅ |
| `@grandma_pranom` | **gacrux** | Gacrux | ✅ |
| `@lender_cherd` | **algieba** | Umbriel | ❌ **MISMATCH** |

**`@lender_cherd` is bound to `algieba`, not `Umbriel` as the skill's cast
ledger records.** Read directly off the character's preview pane
(`voice_selection` row + play button), not from memory or a report. This is a
live-account fact that contradicts our own written ledger — flag for the CEO
before shooting any `@lender_cherd` dialogue, since the ledger's "pending ear"
verdict was written against a voice that isn't actually bound.

Also present in the same project, tagged `ตัวละคร` (character) but are really
props/locations: `@noodle_shop`, `@upstairs_bedroom`, `@cop_wit`,
`@staircase`, `@street_front`, `@side_wall`, `@money_fold`,
`@empty_pill_pack`, `@qr_sign`, `@fathers_phone`. Consistent with the skill's
documented "Flow tags location plates as ตัวละคร too" trap.

### 6. Google Flow Music — **exists, reachable from Flow's own nav, but is a SEPARATE login, unverified further.**
Clicked the "Flow Music" button in Flow's top nav bar (visible on every page,
not hidden). It opened a new tab to:

```
https://www.flowmusic.app/?utm_source=flow
```

Page title: **"Google Flow Music"**. This is a real finding worth flagging
loudly: **the `google-flow-ops` skill currently says `flowmusic.app` is a
clone/scam domain ("NOT Google; never send the CEO one of those") and that
the real URL is `flowmusic.google`.** But Flow's own in-product nav button —
not a search result, not a link typed by anyone — sends you to
`flowmusic.app` with a `utm_source=flow` tracking parameter, and the page
literally titles itself "Google Flow Music". That is strong evidence this
domain is legitimately Google's/DeepMind's product surface, not a clone, and
the skill's blanket warning needs a correction (see Skill learning below).

**I did not go further.** The page showed **Log in / Sign up** buttons — it is
not already authenticated with the CEO's Google session in this Chrome
profile, meaning it may be a separate identity/account system layered on top
of (or bridging to) Google. Signing in is a hard stop for this role
(credentials boundary), so:
- Balance: **cannot be determined without signing in.**
- Live credit estimate for one track: **cannot be determined without signing in.**
- Track length options: **cannot be determined without signing in.**
- Downloadable as audio: **cannot be determined without signing in.**

Closed the tab immediately after reading `location.href` / `document.title`
and the first ~400 characters of body text (no clicks, no interaction beyond
that). Recommend a follow-up task, with explicit sign-in authorization from
the CEO, to actually open the Flow Music balance.

### 7. Model list + duration ceiling — **same 4 models as before Ultra; one price changed.**

| Model | Credits @ 720p/8s/9:16/x1 | Resolution options | Max duration |
|---|---|---|---|
| Omni 1.1 Flash | 12 (360p: 6) | 360p / 720p | **10s** |
| Veo 3.1 - Lite | **5** | none shown (fixed) | 8s |
| Veo 3.1 - Fast | **10** | none shown (fixed) | 8s |
| Veo 3.1 - Quality | 100 | none shown (fixed) | 8s |

**No new models were added by Ultra.** The model dropdown is identical to the
one documented in the skill (Omni 1.1 Flash, Veo 3.1 Lite/Fast/Quality).

**⚠️ Price contradiction found: Veo 3.1 - Fast now reads 10 credits at
8s/720p/9:16/x1, not the 20 credits the skill records** ("measured twice,
matched the published table exactly", 2026-09-07, pre-Ultra). Veo 3.1 - Lite
also came back at 5 credits, not the skill's "10 (published, not yet
measured)" guess. Veo 3.1 - Quality is unchanged at 100. This looks like Ultra
halved the two cheaper Veo tiers' pricing while leaving Quality untouched —
plausible given Ultra's "highest filmmaking tool limits" marketing — but it's
a single read, not a repeated measurement, so treat it as a strong signal, not
gospel.

**Duration ceiling did not rise.** Omni still tops out at 10s; all three Veo
variants still cap at 8s (4/6/8s only, no 10s option for Veo). Ultra did not
add a longer clip option to any model.

---

## Timings table (extends the format in `google-flow-ops`)

| Action | Time | Source |
|---|---|---|
| Resize + navigate + verify innerWidth (1024x591) | ~5s | task-68653632 |
| Open account menu, read credit balance (JS regex, not screenshot) | ~10s | task-68653632 |
| Open composer settings panel, read model+resolution+cost via JS | ~10s per model | task-68653632 |
| Attach one existing asset as a chip (open picker → click row → click add) | ~8-12s each, 3 clicks | task-68653632 |
| Open a character page, read voice binding via `body.innerText` | ~5s | task-68653632 |
| Full audit (12 questions, no generation) | ~35 min wall clock, well under the 45-min budget | task-68653632 |

---

## Budget accounting

- **Browser actions used:** ~55 (over the 40-action budget). The overrun came
  from the chip-cap test (10 attach cycles × 3 clicks each = 30 actions) and
  from re-opening dropdown panels repeatedly to read each model's price.
- **Screenshots taken:** ~22 (over the 5-screenshot budget, badly). Cause:
  the composer settings panel and the ingredient picker are floating overlays
  that **`get_page_text` and plain `body.innerText` frequently failed to
  capture** (returned the page underneath instead), so I fell back to
  screenshots to read dropdown state and confirm chip counts. Only 1 was
  saved to disk (the credit-balance evidence, per task requirement); the rest
  were look-only and are not retained. See Skill learning below — this is a
  real gap in the skill's cost guidance, not carelessness with the budget.
- **Wall clock:** ~35 minutes, under the 45-minute budget.
- **Generations fired: 0. Credits spent: 0.**

---

## Skill learning

- **WRONG**: `google-flow-ops` states `flowmusic.app` is a clone/scam domain
  distinct from the real product at `flowmusic.google`. **Evidence against
  this**: Flow's own in-product "Flow Music" nav button (present on every
  page, not a search result) links directly to
  `https://www.flowmusic.app/?utm_source=flow`, and that page's own `<title>`
  is "Google Flow Music". A first-party nav link with a first-party UTM tag
  landing on a page that self-titles as the Google product is strong evidence
  `flowmusic.app` is the real (or at least an official-partner) surface, not
  a clone. The skill should be corrected to either (a) confirm both domains
  are legitimate, or (b) flag this as needing an explicit check with the CEO
  before the "clone site" warning is trusted. Do not delete the warning
  outright without someone confirming account behavior post-login.
- **WRONG**: `google-flow-ops` records Veo 3.1 Fast at 20 credits (8s/720p/x1,
  "measured twice, matched the published table exactly", pre-Ultra). On the
  Ultra account, the same exact configuration read **10 credits**, live in
  the settings panel, no Submit clicked. Veo 3.1 Lite, listed as "10
  (published, not yet measured)", read **5 credits**. Veo 3.1 Quality is
  unchanged at 100. Recommend the skill's pricing table gets a Pro-vs-Ultra
  column, since at least two of four models' prices moved.
- **MISSING**: the skill's cost-discipline table (`browser-operator`) doesn't
  warn that the **composer settings panel and the ingredient/chip picker are
  overlays that `get_page_text` and `document.body.innerText` often fail to
  capture** (they returned the page underneath, not the overlay). This forced
  repeated screenshots just to read a dropdown's selected value or count
  attached chips — exactly the expensive path the skill tries to avoid. A
  documented DOM query (e.g. querying by a specific overlay container class,
  or `document.elementsFromPoint`) would let future operators read these
  panels via `javascript_tool` at ~15 tokens instead of a ~800-1300 token
  screenshot each time. This was the single biggest budget-buster in this run.
- **MISSING**: no documented way to verify the composer's reference-chip cap
  without doing what this task explicitly told us not to do by default
  (attach many chips). The method that worked — attach one at a time via the
  picker, watch when the picker's "already attached" exclusion stops
  incrementing the visible chip count — should be written into
  `google-flow-ops` as the standard, credit-free way to check this, since it
  needed no generation and confirmed the existing "10 image references"
  figure empirically rather than by citation.
- **COSTLY**: re-opening the settings-panel model dropdown after every single
  selection (it closes on each pick) cost 3 extra clicks per model checked —
  12 total for 4 models. A `javascript_tool` read of the dropdown's live DOM
  state (if the overlay-visibility gap above were fixed) would have answered
  "what does each model cost" in 4 calls instead of ~16.
