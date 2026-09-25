# TopView Wan3: how references and prompts actually work (read 2026-09-25)

Read-only research. Nothing registered, generated, paid, or submitted.
Sources: https://www.topview.ai/wan-3 , https://www.topview.ai/pricing ,
https://www.topview.ai/wan-3-vs-minimax-h3 , https://www.topview.ai/wan-3-vs-seedance-2 ,
https://www.topview.ai/guides/ai-video . JS-rendered pages read through the
r.jina.ai text proxy (curl on r.jina.ai/<url>), same method as
TOPVIEW-WAN3-RULES.md. TopView's own caveat, repeated on every Wan3 page:
"Alibaba's public model catalog does not currently confirm these as official
Wan 3.0 parameters" and the model is "closed public beta" as of launch
2026-08-06. Treat all Wan3 numbers below as Topview's own workflow-preview
claims, not an Alibaba spec sheet.

## 1. Modes and what each accepts

Page https://www.topview.ai/wan-3 lists three tabs: **Omni Reference, Image to
Video, Text to Video**. In TopView's own words:

- Core inputs: "Text . Image . Video . Audio"
- Extended context: "Documents . Webpages"
- Duration: "Up to 30 seconds" ("Projected 30s + Smart Duration")
- Resolution (as shown on the wan-3 landing page itself): "1080P . 720P"
- Aspect ratios: "16:9 . 9:16 . 1:1 . 4:3 . 3:4"

The two head-to-head comparison pages (wan-3-vs-minimax-h3, wan-3-vs-seedance-2,
both dated to the 2026-08-06 beta launch) give the fuller, numeric spec that
the landing page omits:

- Resolution: **480p / 720p / 1080p** (480p is missing from the wan-3 landing
  page's own "Resolution" module but present on both comparison pages and in
  the pricing table's per-model credit list, e.g. "Wan 3.0 480p 1.2 credits/4s")
- Duration: "Up to 30s in a single continuous shot", stepped per second across
  a "2-30s range"
- **Reference Inputs: "up to 10 images, 5 videos, 5 audio (20 combined)"**
  (quoted identically on both comparison pages, contrasted with MiniMax H3's
  9/3/3/15 and Seedance 2.0's 9/3/3/15 on Topview)
- Native audio: "Flagged on Topview across both text-to-video and
  reference-to-video generation" for Wan3, but whether Wan3 actually
  *generates* audio itself versus only accepting an audio reference is not
  stated plainly anywhere; the wan-3 FAQ hedges: "Whether audio reference or
  native sound is available depends on the current model mode in Topview, so
  confirm the live controls."
- No file-size or exact format (mp4/mov, jpg/png, etc.) limits are published
  for Wan3 references on any page found.

## 2. How a reference is tied to the prompt (your main question)

**Answer: positional `@` tags on the upload slot number, not a named/custom
library.** Confirmed two ways:

- The platform-wide mechanic, from the official product guide
  (https://www.topview.ai/guides/ai-video, "Omni Reference" section), quoted
  exactly: *"Select the video model and upload **reference images or
  videos**."* then *"Input the prompt for the video. Type **"@"** to
  reference the files you have uploaded directly within the prompt."*
- The wan-3 landing page's own live-looking demo widget shows this exact
  mechanic in miniature: you upload a "Reference image", then the Direction
  textbox (character counter shown as "Direction 513/3500", implying a 3500-
  character cap) auto-inserts an inline chip of the thumbnail followed by the
  literal text **"@Image 1"** which you then continue writing around.

The two "Same Prompt, Two Models" comparison pages (wan-3-vs-minimax-h3,
wan-3-vs-seedance-2) show TopView's own actual example prompts using a
second, related but different-looking token style: **`<<<Image1>>>`,
`<<<Image2>>>`, `<<<Image3>>>`, `<<<Audio1>>>`** (no space, triple angle
brackets, auto-numbered by upload order), e.g.:

> "HAORAN, the young man from <<<Image1>>>, and XIAOYU, the young woman from
> <<<Image2>>>, run into each other on the sidewalk in front of the cafe from
> <<<Image3>>>..."

> "The five dancers from <<<Image1>>>, keeping each dancer's exact face,
> hairstyle and outfit, perform street dance ... choreographed to the music in
> <<<Audio1>>> ... Use the ORIGINAL audio from <<<Audio1>>> unchanged; audio
> reference only, not visual reference."

> "Input references: <<<Image1>>> for character appearance ... <<<Image2>>>
> for boss appearance ... References are design sheets only: do NOT render
> the sheet layout, labels, swatches, scale panel or grey background. Extract
> character design only."

So: **no `@Name`, no `[1]`-style bracket-number, and no saved/reusable
character-or-Element library for Wan3 references.** Every reference is a
per-generation upload, auto-numbered `Image1/Image2/.../Audio1/...` in upload
order, and you write your own character/prop name in prose right after citing
the tag ("HAORAN, the young man from <<<Image1>>>"), exactly the way you'd
caption a photo, not the way Higgsfield's `@Name` Elements work. The wan-3
FAQ's own prompt-writing advice: *"Name each uploaded reference and explain
its job, then list the details that must remain consistent so the model does
not have to guess which source has priority."* "Name" here means describe/
label it in your prose, not assign it a custom `@handle`.

The only saved, reusable libraries found anywhere on TopView are for the
**separate Avatar product**, not Wan3: "Product Avatar: Unlimited saved
Product Avatars, supports using your photo as an avatar" and "Saved Video
Avatars: Up to 200/1,000 saved avatars" (pricing page, all plans). Team plan
also lists a "Shared asset library, board & Brand Kit" under Collaboration.
Whether either of these plugs into Wan3's Omni Reference slots, or is a
completely separate feature (talking-head avatars only), is **not
documented and not confirmed** anywhere read in this pass.

## 3. Shot-level direction: yes, confirmed, two written forms

The wan-3 landing page names this explicitly as a parameter: **"Prompt scope:
Shot-level direction. Describe camera, action, performance, pacing, sound, and
continuity constraints in one creative brief."** Its own worked example
("Photoreal Story Sequence"): *"Maintain the actor's face, coat, silver case,
compartment layout, and vocal tone through an establishing shot, two dialogue
close-ups, a corridor tracking shot, and a final reveal."* That form is plain
sequential prose, no timestamps.

TopView's own example prompts on the comparison pages show a second, more
literal form with explicit in-prompt timestamps, both used as real Wan3 test
prompts:

- Bracket form: `[0-4s] ... [4-8s] ... [8-12s] ... [12-15s]` (Ensemble Acting
  Comparison prompt)
- Labeled-timeline form: `Timeline: 0.0-3.0s | Face-off <description> 3.0-8.0s
  | Homing missile gauntlet <description> 8.0-15.0s | Face-to-face
  point-blank finish <description>` (Game Boss Battle Comparison prompt)

Both are single prompts fed to one Wan3 generation call, i.e. this is how you
write "an establishing shot, two dialogue close-ups, a corridor tracking shot"
etc. as one multi-shot brief for one render.

## 4. Credit costs and plans

**Per-second Wan3 cost, from the pricing page's own comparison table**
(https://www.topview.ai/pricing), cross-confirmed by the comparison pages'
"Pricing Signal" rows:

| Resolution | Base cost | With 20% OFF (Business/Ultra/Team annual) |
|---|---|---|
| 1080p | "4 credits/4s" = **1 credit/sec** | not discounted on this page |
| 720p | "2 ... 1.6 credits/4s 20% OFF" = **0.5 credit/sec base, 0.4 credit/sec discounted** | yes, 20% off Wan3 720p (and Seedance 2.5 720p) |
| 480p | "1.2 credits/4s" = **0.3 credit/sec** | not discounted on this page |

Comparison page confirms the range directly: *"On Topview, 0.3-1 credits/sec
across 480p-1080p"* and, comparing to Seedance 2.0, *"At matching resolutions,
Wan 3.0 is priced lower per second than Seedance 2.0 on Topview (e.g. 0.5 vs 1
credit/sec at 720p)."*

**Plans** (https://www.topview.ai/pricing, annual billing view; sticker price
shown crossed out is the monthly-billed price):

| Plan | Monthly-billed price | Annual-billed effective price | Credits |
|---|---|---|---|
| Pro | **$29/mo** | $16/mo ($192/yr, 44% off) | **960 credits/year, all upfront** (= 80/mo, matches the $29-for-80-credits figure you already had) |
| Business | $75/mo | $44/mo ($528/yr, 41% off) | 3,000 credits/year, all upfront |
| Ultra | $150/mo | $50/mo ($599.9/yr, 66% off) | 500 credits/month, **expires monthly**, not annual lump sum |
| Team | $180/seat/mo | $56/seat/mo ($672/yr/seat, 68% off) | 500 credits/seat/month, expires monthly |
| Enterprise | custom | custom | "Custom API credits per seat/mo" |

Ultra and Team (only) also include **"Wan 3.0 720P 365 Days Unlimited"**
generation for one year, listed under each plan's "60-DAY UNLIMITED SEEDANCE
2.5 & 2.0" bullet block (odd heading, but Wan3 720p unlimited is in that list
for Ultra and Team; not listed for Pro or Business).

**Top-up packs**, FAQ quoted exactly: *"We offer multiple credit packs (e.g.
250 / 600 / 1000). The exclusive 1000-credit pack offers the lowest per-credit
price and is reserved for Ultra Annual and Business Annual subscribers."*
Top-up credits "are valid for 24 months from the purchase date, no monthly
reset, no automatic expiry on renewal."

## 5. Prompt-writing guidance TopView publishes for Wan3

No dedicated Wan3 blog post or PDF guide was found (searched
topview.ai/blog and topview.ai/guides; only general "AI Video" and
comparison-page content came up). The guidance that does exist is on the
wan-3 landing page itself, FAQ "What should a good Wan 3.0 prompt include?",
quoted in full: *"Describe the subject, story beats, action, camera,
lighting, performance, sound, pacing, and final composition. Name each
uploaded reference and explain its job, then list the details that must
remain consistent so the model does not have to guess which source has
priority."*

Step-by-step flow (same page, "How to try Wan 3.0 for free online"):
1. "Enter a Prompt: Describe your video idea, including the subject, scene,
   visual style, motion, camera direction, sound, and intended duration."
2. "Generate the Video: Review the editable direction and reference image,
   check which model and settings are currently available, then start the
   generation workflow."
3. "Review and Export."

Three named "WAN 3.0 PROMPT EXAMPLES" on the same page (30-Second Product
Launch, Digital World Explainer, Photoreal Story Sequence) all follow the same
recipe: name each reference by role in one clause, state the shots/beats in
order, then close with an explicit "preserve/maintain X, Y, Z" consistency
list. The full worked prompts quoted on the two comparison pages (see section
2 and 3 above) are TopView's most concrete real examples of finished Wan3
prompt syntax, including negative/"Avoid ..." tails at the end of each ("Avoid
static camera, slow pacing, ... rendering the reference sheet layout or text
... subtitles, watermark, UI, gore").

## Could not confirm without a logged-in account

- Whether the live Wan3 generator UI actually enforces 10 images / 5 videos /
  5 audio (20 combined), or whether that is marketing copy on the comparison
  pages not matched by the real upload widget (which on the wan-3 landing
  page only demos a single "Reference image" slot).
- Whether 480p is genuinely selectable for Wan3 in the live UI (present in
  pricing table and comparison pages; absent from the wan-3 landing page's
  own "Resolution" module).
- Whether the `<<<ImageN>>>`/`<<<AudioN>>>` token style or the `@Image N`
  token style (or both, depending on context) is what the current live
  Direction box actually inserts/accepts; both appear on official TopView
  pages but were not seen in the same screenshot.
- Whether Wan3 generates audio natively at all, versus only accepting audio
  as a reference/timing track. TopView's own FAQ leaves this open.
- Whether the Product Avatar / Video Avatar saved libraries, or the Team
  plan's "shared asset library, board & Brand Kit," can be pulled into a Wan3
  Omni Reference slot as a reusable named character, or are scoped only to
  the separate Avatar/talking-head tool.
- Exact file-size and format limits for Wan3 reference images/videos/audio
  (none published on any page found).
- Live per-second Wan3 credit cost inside your actual account tier (the table
  above is the public pricing-page comparison table, not a screenshot of a
  logged-in generation screen).
