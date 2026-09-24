# TopView AI Film Screening (SSFF & ASIA): rules as read 2026-09-24

This is a DIFFERENT, NEW challenge from the already-documented
`docs/promo/TOPVIEW-WAN3-RULES.md`. Launched today, 2026-09-24. Read-only,
nothing registered or submitted.

Source: the page's own API (`activityCenter.list` then `activityCenter.detail`,
input `{"slug":"topview-ai-film-festival-open-call"}`, no JSON-wrapper needed,
unlike some trpc calls) plus the Terms and FAQ on Notion. Notion pages are also
JS-rendered; plain curl and WebFetch both returned only the word "Notion", so
they were read through the r.jina.ai text-extraction proxy
(`https://r.jina.ai/<notion-url>`) instead.

- Page: https://www.topview.ai/activity/topview-ai-film-festival-open-call
- Terms: https://vagabond-science-61e.notion.site/Topview-AI-Film-Screening-Terms-3e555a0d359180aaae15dd59e9e05c7d
- FAQ: https://vagabond-science-61e.notion.site/Topview-AI-Film-Screening-FAQ-3e555a0d359180ed822fc78ca15aa9ce
- FAQ's own closing line points to a THIRD document not linked from the page:
  "Read the complete Topview AI Film Showcase Event Terms" at
  https://udu133ckhp.feishu.cn/wiki/SrJkweVxNiYpthkNOl3c9TIhnGb (Feishu wiki,
  not fetched, out of scope for this pass, flagged under "could not read").

Other TopView activities found via `activityCenter.list` (one line each):
`topview-wan3-challenge` = the already-documented Wan3 Challenge, still ONGOING.
`topview-30s-challenge` = $15,000 cash + credits, ran Aug 4-31 2026, status
AWARDED (closed, old, not a new challenge).

## What it is

Not a competition. TopView + Short Shorts Film Festival & Asia (SSFF & ASIA,
Academy-recognised since 2004) invite complete AI-made short films for a
curated screening at SSFF & ASIA 2026 Autumn. No ranking, no votes; "passing
initial review does not guarantee selection for festival screening."

## Dates (Thai time, UTC+7)

Terms/FAQ give dates as "(UTC)"; the raw API fields (`startAt`,
`submissionEndAt`) already equal the Thai-time conversion (confirmed by
cross-check), so both agree below.

| | UTC | Thai |
|---|---|---|
| Submissions open | 24 Sep 00:00 | **24 Sep 07:00** |
| Submissions close | 22 Oct 23:59:59 | **23 Oct 06:59** |
| Selection confirmation | ~4 Nov (see conflict) | **4 Nov** (API: 4 Nov 20:00 Thai-equivalent) |
| Screening (SSFF & ASIA) | - | **8 Nov 2026** (time/venue TBA) |
| "Event end date" (credit calc only, does not move any deadline) | 25 Oct | **25 Oct** |

**Conflict:** the page's own rendered summary says "Selection confirmation:
**November 5**, 2026." Terms says "Selection confirmation: **November 4**,
2026." FAQ says "Selection will be confirmed on **November 4**, 2026." The raw
API field `estimatedResultAt` also reads 4 Nov. Three sources against one, so
we plan on **4 Nov**.

## Prizes: no fixed pool, per-film, no fixed count of winners

- Every submission that **passes initial review**: **100 TopView Credits.**
- Every film **ultimately selected for the SSFF & ASIA screening**: **US$5,000
  cash + 1,000 TopView Credits** (cumulative with the 100, so **1,100 credits**
  total for a selected film).
- No stated cap on how many films get selected; the program is "approximately
  70 minutes" total, "not the duration of an individual film or a fixed number
  of selected films."
- Credits: issued within 7 business days after 25 Oct 2026 (the admin "event
  end date"), to the TopView account used to submit, valid 1 year from issuance.
- Cash: **Terms/FAQ say "within 30 business days after the required identity,
  selection eligibility, tax, and payment information has been verified."**
  **The page's own summary blurb instead says "within 15 business days after
  the required information is confirmed."** Contradiction; plan on 30 business
  days (2 sources) but don't be surprised by an earlier payout.

## Entry rules

- Each creator may submit **up to two films**; posting the same film on
  multiple platforms does not count as a second submission.
- **At least 80% of the finished film's SHOTS (by shot count, not duration)
  must be made with TopView.** Exact FAQ formula: "Percentage of Topview-made
  shots = Number of shots made with Topview ÷ Total number of shots in the
  finished film × 100%. For example, a 50-shot film must have at least 40
  shots made with Topview." No specific TopView *model* is required (unlike
  Wan3 Challenge, which locks to the Wan3 model specifically) - any TopView
  tool/model counts.
- Other tools allowed for: editing, voiceover, music, color grading, subtitles.
- Length: **longer than 3 minutes**, no stated maximum. 1080p. **Both the film
  and its cover image must be 16:9** (Wan3 allowed any aspect ratio; this one
  does not).
- Genre: none restricted - "narrative, animation, science fiction, fantasy,
  suspense, experimental, documentary, and music films" all eligible.
- Made-after date: "Films must be created after this event begins" = after
  24 Sep 2026. Anything shot/rendered before that, including our existing ILAG
  episodes, does not qualify.
- **"Films that have previously won awards on other platforms or in other
  competitions are not eligible."** (Terms and FAQ, same wording both places.)
  See the double-entry section below - this is the one clause that actually
  bites on the Wan3 question.
- No watermark requirement is mentioned anywhere in page, Terms, or FAQ
  (Wan3 required an official watermark on the video; this challenge is silent
  on watermarking).
- Subtitles: **both English and Japanese required**, "accurate, legible,
  synchronized"; selected films must deliver the subtitle files/versions per
  later instructions.
- Publish on social media, tag official TopView account, hashtags
  `#TopviewAI` and `#TopviewSSFF& ASIA` (exact string as it appears in all
  three sources, including the odd space/ampersand - almost certainly a
  broken hashtag in TopView's own copy; read literally it will not function
  as one clickable tag on most platforms).
- **Contradiction on which platforms count:** the page's step-by-step summary
  says "Publish the film on at least one of **X, Instagram, YouTube or
  TikTok**." Terms and FAQ (both) say "Publish the film on at least one of
  the following platforms: **X, Instagram, or YouTube**" - **TikTok is absent**
  from both authoritative documents. Treat TikTok-only posting as risky.
- Official accounts to tag: X (Global) @TopviewAIhq, X (Japan) @TopviewAIJP,
  TikTok @topviewaiofficial, Instagram @topviewaiofficial, YouTube
  @TopviewAIOfficial.
- Submission form fields (from `publishedSubmissionForm`, live schema):
  Work title, Author name, Published links (textarea), Work video (FILE,
  **max 200 MB**, mp4/mov/webm, **must be 16:9**), Author avatar (FILE, image,
  jpg/png, max 200 MB), Discord Account (optional text), Cover (FILE, image,
  16:9, jpg/png, max 200 MB), Project Link (text), and **"Follow official
  account and repost contest screenshot"** (FILE, image, jpg/png, required) -
  this follow+repost proof requirement appears only in the live form, not in
  the page text, Terms, or FAQ; budget for it anyway since the form enforces it.
- 200 MB is a tight ceiling for a 3+ minute 1080p file; plan compression.
- Registration is disabled (`registrationEnabled: false`) - there is no
  separate free-credit-request phase like Wan3's; you go straight to the
  submission form. No free/sponsored TopView credits are offered for making
  the entry, only the 100/1,000-credit *rewards* described above.

## Judging criteria (exact wording, Terms)

| Weight | Criterion |
|---|---|
| 30% | Storytelling and emotional expression |
| 25% | Direction and cinematic language |
| 20% | Visual and sound quality |
| 15% | Substantial use of TopView |
| 10% | Screening suitability and rights compliance |

"These criteria support film selection and do not constitute public rankings
or competition awards." Follower counts, likes, and views explicitly do not
determine selection (FAQ).

## Rights / licence

- Submitting does not transfer copyright. TopView/festival get permission for
  review, promotion, in-person screening, and "agreed" online distribution -
  scope (channels, territories, duration) is separately confirmed with the
  rights holder before any actual public use.
- Must hold rights to all music, fonts, images, footage, likenesses, voices.
- **Explicit warning, quoted: "A license to use music from a social media
  platform's library does not necessarily cover in-person festival
  screenings; creators must verify the scope of their licenses."** This
  matters for us specifically if we reuse TikTok/IG in-app royalty-free
  tracks - those licences likely do not cover a real theatrical screening.
- Real person's likeness/voice needs "appropriate authorization"; brand
  placements and third-party materials must be disclosed.
- Selection/certificate "do not automatically confer eligibility for Academy
  Awards consideration or nomination" - only wins in designated competition
  categories at the actual festival carry that, and this call is not a
  competition category.

## Reference images from other tools: not addressed directly, same inference as Wan3

Neither Terms nor FAQ says anything about non-TopView still images (e.g. a
ChatGPT-made character reference) used as an input to a TopView generation.
By the same logic as the Wan3 doc: the 80% test counts *shots*, and a shot
generated by TopView (even fed a non-TopView reference image as input) should
count as a TopView-made shot; a non-TopView image used directly on-screen as a
static shot would not. This is our inference, not a quoted rule - treat it as
unconfirmed until we ask TopView or see it enforced.

## CRUCIAL: can one film enter BOTH this challenge and the Wan3 Challenge?

**The documents are silent on simultaneous/concurrent entry.** Nowhere in the
page, Terms, or FAQ of either challenge does TopView mention the other
challenge, an "only one TopView contest" rule, or a "not submitted elsewhere"
clause aimed at cross-entry. No exclusivity language exists to quote.

The one clause that actually touches this is retroactive, not preventive,
quoted exactly (Terms and FAQ, same wording): **"Films that have previously
won awards on other platforms or in other competitions are not eligible."**
Consequence for us: Wan3 results land ~30 Sep 2026 (Thai time), before this
Film Screening's 23 Oct 2026 (Thai time) submission close. If our entry *wins*
a Wan3 cash prize, that same work would then have "previously won an award in
another competition" and, read literally, becomes ineligible to submit here
afterward. If it does not win Wan3 (or we submit here before the Wan3 result
is announced), nothing in either document forbids entering both.

Practically the two are unlikely to be the literal same deliverable anyway:
Wan3 wants >=30s, any aspect ratio, Wan3-model-specific; this one wants >3 min,
16:9 only, 80%-by-shot-count TopView (any model). A combined/extended 16:9 cut
of the Wan3 material, run past 3 minutes, could satisfy both tool-use tests,
but would need to clear the length and aspect-ratio bar separately, and would
carry the "already won a Wan3 prize" risk above if the Wan3 entry wins first.

## Contradictions found (recap)

1. Selection-confirmation date: page says 5 Nov; Terms, FAQ, and raw API all
   say 4 Nov. Plan on 4 Nov.
2. Cash-payout turnaround: page says 15 business days; Terms and FAQ both say
   30 business days. Plan on 30.
3. Eligible platforms: page includes TikTok (4 platforms); Terms and FAQ list
   only X, Instagram, YouTube (3 platforms, no TikTok).
4. The submission form requires a "follow + repost" screenshot upload that is
   not mentioned as a rule anywhere in the page text, Terms, or FAQ.

## Could not read

- The FAQ's own linked "complete Topview AI Film Showcase Event Terms" on
  Feishu (https://udu133ckhp.feishu.cn/wiki/SrJkweVxNiYpthkNOl3c9TIhnGb) - a
  different document from the Notion Terms page fetched above, not opened in
  this pass. The FAQ says this Feishu doc, not the Notion one, is "the
  complete" terms, and that "if these Terms conflict with the event page,
  these Terms will prevail" (Notion Terms' own closing line) - so there may be
  a fourth layer of detail or another contradiction sitting in that Feishu doc.
- Public gallery is empty (`"publicGallery":{"enabled":true,"entries":[]}`) -
  challenge launched today, nothing submitted yet, so no competitive-landscape
  read is possible yet (unlike Wan3's 155-entry gallery).
