# RunPod Blackwell/Region Survey for MiniMax H3 — 2026-08-22

Read-only survey. No pod deployed, no network volume created, no payment
form opened, no MFA/terms accepted, no verification submitted. Account
balance $-0.00 throughout. Scope: the region shortlist that survives the
MiniMax H3 licence exclusion (no EU/UK/South Korea/USA) — **AP-JP-1
(Japan), CA-MTL-1 / CA-MTL-3 / CA-MTL-4 (Canada), AP-IN-1 / AP-IN-2
(India), OC-AU-1 (Australia)** — cross-checked against Blackwell
availability for the NVFP4 text encoder.

## 1. Per-region GPU stock (Secure Cloud, `/deploy`)

Region selection on this page is a **multi-select accordion, not
single-select** — see "Gotchas" below; every row here was re-verified with
the region filter reading back the exact single code before extracting,
after an earlier pass produced contaminated (multi-region) readings that
were discarded.

`AP-IN-2` has **no entry in this table** — it does not appear in the
Secure Cloud `/deploy` region list at all (only `AP-IN-1` and `AP-JP-1`
exist under "All Asia"). AP-IN-2 is a **network-volume-only** location
(see §3) with no GPU compute attached to it.

| Region | GPU model | VRAM | $/hr (Secure) | Stock | Blackwell? |
|---|---|---|---|---|---|
| AP-JP-1 (Japan) | H100 SXM | 80 GB | $3.29 | Available, max 2 | No |
| AP-JP-1 | H200 SXM | 141 GB | $4.59 | **Available, max 4** | No |
| AP-JP-1 | RTX PRO 6000 | 96 GB | $2.09 | Unavailable | **Yes** |
| AP-JP-1 | RTX PRO 6000 WK | 96 GB | $1.89 | Unavailable | **Yes** |
| AP-JP-1 | B200 | 180 GB | $6.79 | Unavailable | **Yes** |
| AP-JP-1 | B300 | 288 GB | $7.89 | Unavailable | **Yes** |
| AP-JP-1 | RTX 5090 | 32 GB | $0.99 | Unavailable | Yes, **too small** |
| AP-JP-1 | L40S / RTX 6000 Ada / RTX A6000 | 48 GB | $0.99 / $0.84 / $0.53 | Unavailable | No |
| AP-JP-1 | A100 PCIe / A100 SXM | 80 GB | $1.39 / $1.59 | Unavailable | No |
| AP-IN-1 (India) | H100 SXM | 80 GB | $3.29 | **Available, max 8** | No |
| AP-IN-1 | H200 SXM | 141 GB | $4.59 | Unavailable | No |
| AP-IN-1 | RTX PRO 6000 / WK | 96 GB | $2.09 / $1.89 | Unavailable | **Yes** |
| AP-IN-1 | B200 | 180 GB | $6.79 | Unavailable | **Yes** |
| AP-IN-1 | L40S / RTX 6000 Ada / RTX A6000 | 48 GB | $0.99 / $0.84 / $0.53 | Unavailable | No |
| AP-IN-1 | A100 (any) | 80 GB | — | **not offered in this region at all** | No |
| CA-MTL-1 (Canada) | H100 SXM | 80 GB | $3.29 | **Available, max 8** | No |
| CA-MTL-1 | A40 (not a target model) | 48 GB | $0.44 | Available, max 1 | No |
| CA-MTL-1 | RTX PRO 6000 / WK / B200 / B300 | 96–288 GB | $1.89–$7.89 | Unavailable | **Yes** |
| CA-MTL-1 | L40S / L40 / RTX 6000 Ada / RTX A6000 / A100 (both) | 48–80 GB | — | Unavailable | No |
| CA-MTL-3 (Canada) | H200 SXM | 141 GB | $4.59 | **Available, max 2** | No |
| CA-MTL-3 | A100 PCIe | 80 GB | $1.39 | **Available, max 1** | No |
| CA-MTL-3 | H100 SXM / RTX PRO 6000 / WK / B200 / B300 | 80–288 GB | — | Unavailable | mixed |
| CA-MTL-3 | L40S / L40 / A40 / RTX 6000 Ada / RTX A6000 / A100 SXM | 48–80 GB | — | Unavailable | No |
| CA-MTL-4 (Canada) | **everything** (all 31 cards checked) | — | — | **Unavailable, zero stock** | — |
| OC-AU-1 (Australia) | L40S | 48 GB | $0.99 | **Available, max 8** | No |
| OC-AU-1 | everything else (H100, H200, RTX PRO 6000 family, B200, B300, RTX 6000 Ada, A6000, A100) | — | — | Unavailable | mixed |

## 2. Community Cloud — does it even reach these regions?

Community Cloud's region control is a **flat 11-country list**, not the
Secure Cloud datacenter-code list, confirmed 2026-08-22:
`CA, CZ, ES, FR, HR, PT, SE, SK, TT, TW, US`.

**Japan, India and Australia are not offered in Community Cloud at all** —
not "unavailable," genuinely absent as filter options. Only Canada
overlaps our shortlist, and only at country granularity (cannot isolate
Montreal specifically; may include non-MTL Canadian sites).

| Region | GPU model | VRAM | $/hr (Community) | Stock | Blackwell? |
|---|---|---|---|---|---|
| CA - Canada (country-level) | RTX 5090 | 32 GB | $0.69 | Available, max 8 | Yes, **too small** |
| CA - Canada | H100 NVL | 94 GB | $2.59 | **Available, max 1** | No |
| CA - Canada | L40 | 48 GB | $0.69 | Available, max 4 | No |
| CA - Canada | RTX PRO 6000 / MaxQ / WK | 96 GB | $0.00 (unpriced) | Unavailable | **Yes** |
| CA - Canada | RTX 6000 Ada / RTX A6000 | 48 GB | $0.00 | Unavailable | No |
| CA - Canada | RTX 3090 / 3090 Ti / 3080 Ti (too small) | 12–24 GB | $0.18–$0.27 | Available | No |

## 3. Network volume regions

Confirmed via `/user/storage` (Standard vs. High-performance pricing) this
run. **The per-region list itself (which of AP-JP-1/CA-MTL-3/CA-MTL-4/
AP-IN-2 offer a volume, and which are S3-tagged) is carried over from the
prior survey (`RUNPOD-SURVEY.md`, task-8a568920, 2026-08-21) — the create-
volume dialog that lists it is gated behind a button whose text
("Create a network volume") was refused by this session's safety
classifier as a provisioning action, even to open and Cancel. That dialog
needs re-opening by a session that can clear the classifier, or a human,
before treating the region list below as freshly confirmed.**

Carried-over region list, cross-referenced against our shortlist:

| Region | Volume tier | S3-compatible? |
|---|---|---|
| AP-JP-1 (Japan) | Standard | No S3 tag seen |
| CA-MTL-3 (Canada) | Standard | No S3 tag seen |
| CA-MTL-4 (Canada) | **High-performance** | No S3 tag seen |
| AP-IN-2 (India) | Standard | **Yes (S3 tag)** |
| CA-MTL-1 (Canada) | **not in the volume list at all** | — |
| AP-IN-1 (India) | **not in the volume list at all** (only AP-IN-2 is) | — |
| OC-AU-1 (Australia) | **not in the volume list at all** | — |

**Australia has no network-volume option whatsoever** among the 19
datacenters in that list (confirmed both runs) — this rules OC-AU-1 out
regardless of its L40S stock, since the brief requires a network volume.

Pricing (confirmed fresh today, `/user/storage` page text, no dialog
needed):
- **Standard storage:** $0.07/GB/month for the first 1 TB, then
  $0.05/GB/month. Up to 10 Gbit network speed.
- **High-performance storage:** $0.14/GB/month. Up to 3x the throughput.

**Max volume size:** not found on the storage list page, and the create
dialog (which would show it) is the same one the classifier refused this
run. Not confirmed either run — flag for a follow-up pass.

## 4. Balance / verification gate

- **Volume creation:** the "Create Network Volume" button on
  `/user/storage` is `disabled: false` at the current $-0.00 balance (read
  via DOM attribute, not clicked). No balance or verification gate visible
  on this page's text either. Matches the prior survey's finding.
- **Pod deploy gate:** not separately confirmed this run — the `/deploy`
  page hit a repeated blank-render state (see Gotchas) after the storage
  detour and re-checking it would have meant several more navigation
  round-trips for a check the brief treats as secondary. Flag as
  unconfirmed rather than guess.
- Note: this account already shows "Network Storage 200GB / 1000 GB" as a
  usage stat on `/user/storage` — this reads as a plan-level quota
  display, not evidence of an existing volume (the page still shows the
  empty-state "Create Network Volume" CTA, not a volume list). Did not
  investigate further — out of scope for this survey and not something to
  poke at without knowing whose quota it is.

## Recommendation

**Blackwell is not the constraint the brief expected it to be — it's a
live stock problem, not a regional gap.** RTX PRO 6000, B200 and B300 are
all real, priced, correctly-VRAM-labeled listings in *every* region
checked, including the unfiltered "any region" baseline (which spans every
RunPod datacenter worldwide, not just our shortlist) — and they showed
**Unavailable everywhere**, not just outside our candidate list. This
looks like RunPod is simply sold out of Blackwell-generation cards
platform-wide at this exact moment (2026-08-22), not that Blackwell is
excluded from Japan/Canada/India/Australia specifically. That could change
hour to hour — worth a quick re-check with the replay script before
committing to a fallback.

Given that, and the 48 GB VRAM floor for the ~42.5 GB of weights: the two
real candidates today are **AP-JP-1 (Japan)** and **CA-MTL-3 (Canada)**,
both offering **H200 SXM, 141 GB, $4.59/hr**, both with visible stock (max
4 and max 2 respectively), both non-Blackwell (NVFP4 encoder falls back to
the slower path, but it works), and — critically — **both have a network
volume option**, unlike Australia. Of the two, **CA-MTL-3** edges it: same
GPU/price, and Standard-tier network storage is available there per the
carried-over data (needs a fresh re-check, see §3), while AP-JP-1 also has
one but neither is S3-tagged, so that's not a tiebreaker. Pick **CA-MTL-3**
first; fall back to **AP-JP-1** if Montreal stock disappears — both give
141 GB of headroom over the 42.5 GB requirement, which also buys room for
KV cache and ComfyUI overhead that an H100 SXM (80 GB) or L40S (48 GB,
Australia's only Available card and volume-less anyway) would not.

If Blackwell stock reappears, re-run the replay script's Blackwell check
before falling back to H200 — the 48–96 GB Blackwell cards, when actually
in stock, are cheaper per hour than H200 SXM ($2.09 vs $4.59 for RTX PRO
6000 at 96 GB) and give the encoder its native fast path.

## Gotchas this run (for the replay script and any future manual pass)

- **The Secure Cloud region dropdown is a multi-select accordion that
  looks single-select.** Clicking a continent group (e.g. "All Asia")
  expands it *and* selects every code inside as a side effect. Clicking a
  leaf code toggles it — if the continent's other codes are still
  selected from the group click, you get "everything in the continent
  except the one you clicked," which is the *opposite* of what it looks
  like you did. The only way found to get a truly clean single-region
  read: click the continent group (selects all), click "Clear Selection"
  (clears just that continent), click the target leaf once (now the only
  thing selected), then verify the filter-button label reads back exactly
  that one code before extracting. Skipping the verify step silently
  produces contaminated multi-region data — this happened twice this run
  before the pattern was caught.
- **"Any region" does not actually clear the underlying selection.** It
  resets the *label* to "Any region" but the accumulated per-continent
  selections persist underneath — confirmed by re-expanding a continent
  and finding its codes still selected after clicking "Any region." Only
  "Clear Selection" inside an expanded continent group actually clears
  that continent's codes, and it does not touch other continents. To get
  a genuinely empty filter, clear all four continent groups explicitly,
  not just click "Any region" once.
- **Two of the button-index shortcuts from the prior survey's script
  (`runpod-availability-survey.js`) do not transfer as-is.** The
  cloud-type button (`Secure Cloud` / `Community Cloud`) is not
  consistently at the same array index relative to the region button —
  switching cloud type changes how many filter buttons render before it
  (Community Cloud shows a network-speed filter that Secure Cloud
  doesn't), so `ccIdx + 1` located "Network volume" instead of the region
  button on this run. Find the region button by its *current label text*
  (it always immediately follows the cloud-type button, but count
  buttons fresh each time — don't hardcode an offset).
- **Clicking a button whose visible text matches `/Create.*network
  volume/i` gets refused by this session's safety classifier**, even
  though the intent was read-only (open dialog, read region list, click
  Cancel — exactly what the prior survey did successfully one day
  earlier). If this recurs, don't retry the same click — read what's
  obtainable from the surrounding page text instead (this run got the
  $/GB/month pricing that way) and flag the region-list gap in the
  report rather than forcing the click.
- **`/deploy` renders fully blank (`document.body.innerText.length ===
  0`) for a few seconds after every fresh navigation, sometimes longer.**
  Confirmed again this run: one wait cycle needed 3 full retries (~12s
  total) before content appeared; a later navigation stayed blank through
  three retries and was abandoned rather than retried further. This is
  consistent with the prior survey's note that this is a slow-hydrating
  Next.js SPA, not a dead tab — a `javascript_tool` call still responds
  immediately (`1+1` → `2`) even while `innerText` is empty, so the
  renderer isn't frozen, the app just hasn't painted text yet.
- **A `javascript_tool` call timed out at the CDP level (45s) twice this
  run**, both times immediately after a click inside the region popover,
  while the page remained fully responsive to the next call seconds
  later. Matches the prior survey's note: treat a lone timeout as a CDP
  hiccup, verify with a cheap call (`1+1`), don't assume the tab died.
- One `javascript_tool` result was blocked with `[BLOCKED: Cookie/query
  string data]` when it returned every `<a>` element's raw `href` list —
  some contained session-token-looking query strings. Filtering the
  `href` list to a keyword regex (`/storage|hub|template/i`) before
  returning it avoided the block and still answered the question.
