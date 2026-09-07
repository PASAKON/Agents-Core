# «เงินที่พ่อตั้งใจหา» EP1 — production plan

Written 2026-09-07. Budget reality: **210 Flow credits left, no API access yet.**

## Already in hand — nothing is wasted

| Asset | Where | Cost already paid |
|---|---|---|
| `@lung_somchai` — 58, shopkeeper, blue apron | Flow Ingredient | 0 credits |
| `@nong_daeng` — 24, grey polo | Flow Ingredient | 0 credits |
| **clip1_v1.mp4** — envelope pushed across the counter, the son will not take it. 8.00s, 720x1280, Thai audio | `docs/reports/google-flow-recon-20260907/` | 20 credits |
| clip1_v2.mp4 — same shot, second take | same | 20 credits |

The two characters ARE the father and the son. The recon clip IS a beat of the
episode — the moment the father offers and the son refuses. It goes straight
into the teaser as shot 4, with two takes to choose between.

**Character handles are locked to what exists in Flow:**
`@lung_somchai` = พ่อสมชาย · `@nong_daeng` = ลูกชายแดง. No duplicates.

## The wall: Flow can shoot the teaser, not the episode

Flow's web UI has **no first-frame slot**. Frame chaining — the technique that
holds a set steady from shot to shot — exists only through the API.

| | Flow web | API |
|---|---|---|
| Make plates and references | ✅ free | paid |
| Shoot disconnected beats | ✅ | ✅ |
| Shoot a continuous scene with a stable set | ❌ | ✅ |

Seven beats that do not need to join is a teaser. **Shootable now.**
Sixty shots that must join is an episode. **Needs the API.**

## Phase 0 — free, do first

Image generation inside Flow measured at **0 credits**. Make everything,
download everything:

| Make | For |
|---|---|
| `@grandma_pranom` — 79, bedridden | cliffhanger |
| `@lender_cherd` — 45, dresses well | block C |
| `@prop_envelope` — flat-lit, plain ground | recurs in 4+ shots |
| `@noodle_shop_wide` — ONE clean wide photo of the shop | A/B test input, and the location reference if the test says it earns a slot |
| first-frame plates for the 6 unshot teaser shots | composition control |

**Verify while doing it:** only *character* images were measured at 0. Read the
balance before and after the first scene plate. If plates cost credits, this
phase has a price and the plan changes.

## Phase 1 — the 56-second teaser, 120 credits

| # | Beat | Shot | Status |
|---|---|---|---|
| 1 | HOOK | Father shoved against the shophouse wall, envelope falls. Lender's face never seen. | shoot |
| 2 | HOOK | ECU: a trembling hand closes around the envelope on wet pavement | shoot |
| 3 | PAYOFF | Father splits the day's takings, the larger pile into an envelope | shoot |
| 4 | PAYOFF | **Envelope pushed across the counter, the son will not take it** | ✅ **already shot** |
| 5 | PAYOFF | Father closes his son's fingers around it — the theme line | shoot |
| 6 | PAYOFF | Father turns back to blanching noodles. Says nothing. | shoot |
| 7 | CLIFFHANGER | Upstairs in the dark, the grandmother's eyes open; her hand moves under the pillow. Cut to black. | shoot |

```
6 shots x 20 credits = 120      leaves 90 credits = 4 retries
```

Veo 3.1 Fast, 8s, 9:16, 720p, audio on. Most of these seven are silent — only
shot 5, and possibly 3, carry dialogue.

## Phase 2 — assemble, free

- Choose between clip1_v1 and clip1_v2 for shot 4.
- Speed dialogue shots 1.10-1.15x, silent shots up to 1.25x, with `atempo` so
  Thai tones survive:
  `ffmpeg -i in.mp4 -filter_complex "[0:v]setpts=PTS/1.15[v];[0:a]atempo=1.15[a]" -map "[v]" -map "[a]" out.mp4`
- Concatenate → roughly 48-56 seconds.
- CTO reviews every frame; CEO watches and decides whether the format works.

## Phase 3 — the decision gate

Only after the CEO has watched the teaser:

| If | Then |
|---|---|
| The teaser works | Approve Gemini API billing → run the location A/B test (THB ~256) → shoot the remaining 53 shots via API (THB ~3,100-5,100) |
| The teaser does not work | Stop. 160 credits spent, already paid for. No upgrade, no API bill. |

That gate is the entire reason for shooting a teaser instead of an episode.

## Still open

The subscription is unresolved: the CEO reports THB 350/month, but Google AI
Plus in Thailand is THB 189 (200 credits) and AI Pro is THB 750 (1,000). The
balance read 250 at the start of the recon. Until the plan is confirmed, next
month's allowance is unknown and only the API path can be costed.
