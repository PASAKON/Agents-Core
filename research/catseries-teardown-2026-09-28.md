# «แมวซีรี่ย์» / «กาฟิวซีรีย์» Competitor Teardown — 2026-09-28

Task-8637dc69 (CEO, via CMO kickoff). Read-only Facebook research (no like/
follow/comment/share/join/message taken). Media (videos, frames, contact
sheets, info.json) saved only to
`/Users/gob/MoonieXHQ/Assets/Agents/Core/competitor-study/catseries-2026-09-28/`
and never committed to git — see §11.

**Evidence labels used throughout:** MEASURED = read directly off Facebook or
a downloaded file this session. PAGE'S OWN CLAIM = a number the page states
about itself (bio, pinned post) — not independently verified. ESTIMATE = a
number I derived by calculation from MEASURED inputs, with the method shown.
GUESS = my inference with no measurement behind it, used only where the task
explicitly allows a labeled guess for production-recipe items. "Not
measured" = ห้ามเดา — I did not guess a number where none was visible.

---

## CMO review, 2026-09-28 — corrections (read before the sections below)

The CMO checked the two open gaps on the downloaded files. Media stayed in Assets.

1. **Shot count in §5 and "low cut rate" in §6.6 are wrong.** On video 1577233167381395, ffmpeg scene detection at 0.3 found 5 cuts, and at 0.12 it still found 5. A frame strip at one frame every 6 s over 4–148 s shows a new shot in almost every frame. The detector misses these cuts because the whole episode shares one warm grade and one location. On video 1077573248092017, scene detection at 0.12 found 23 cuts, a mean shot of 5.0 s. Real pattern (MEASURED on 2 of 5): **short AI video clips of about 5–8 s each, so roughly 25–45 shots per 3–6 min episode.** It is not long static coverage and not still images.
2. **Audio is character dialogue in Thai, not narration** (MEASURED on 1 of 5, video 1577233167381395). faster-whisper `small` with the language set to th, VAD on and beam 1 ran on a 16 kHz mono WAV extracted first. It loaded in 1.3 s and transcribed 140 s of the 215 s clip before a 240 s timeout. 117 s of the 215 s is voiced. The lines are short spoken dialogue between the man, his wife and the cat's voice (for example "ผมขอน้ำนิดเดียวครับ", "ชื่อผมเหรอครับ"). The cat speaks in the first person. The worker's hang was most likely from feeding the 1440×2560 MP4 straight into the model. Extracting the WAV first works.
3. **§8 revenue method.** The "daily visitors" figure is not a view count, so do not use it as one. A simpler check: the 20 most recent reels on both pages total about 5.1M displayed views (MEASURED, §4). At the Wikis benchmark for SEA Facebook of ~$10 per 1M views (PRACTITIONER), the ~$3,000/month claim would need ~300M monetised views a month per page. Episodes run 2–6 min, which makes them eligible for in-stream ads. The in-stream RPM for a Thai audience is unknown, so the claim stays **UNVERIFIED**, neither proven nor disproven. Brand deals are confirmed as a second income line.

---

## 1. Answer first — 10 lines

1. **แมวซีรี่ย์ (Seriescat.99)**: 210,000 FB followers MEASURED (live count).
   Sister page **กาฟิวซีรีย์ (Gafiwseries)**: 44,000 FB followers MEASURED,
   explicitly labelled in its own bio as the "official backup page" of the
   main one.
2. **The formula, repeated across every one of the 5 videos sampled**: one
   consistent AI cat character ("กาฟิว", an orange tabby) as the recurring
   star, opening on a static title card with a bold headline + a one-line
   curiosity-gap subtitle, set in one simple location, structured as a
   misdirection ("looks bad/villainous") that resolves into a heartwarming
   reveal — see §6.
3. Top sampled reel: **1,000,000 views MEASURED** as shown on the live page
   today; the *same* clip's yt-dlp API `view_count` field reads **644,310** —
   two different real numbers from two different sources, not reconciled
   (§4). Every FB view figure in this report is one or the other, always
   labelled.
4. **The story is not fan-submitted.** The page's own pinned post (MEASURED,
   read today) states the writing team invents the stories itself, and that
   some episodes are "loosely inspired" by real events in the actual cat's
   life — never crowd-sourced from fans.
   **[SUPERSEDED 2026-09-28, CMO]** The page now does take fan stories: the
   «กาแฟ» episode caption reads "ดัดแปลงจากเรื่องจริงที่แฟนเพจส่งมาให้เราร่วมจดจำ"
   (adapted from a true story a fan sent in) — MEASURED, caption in
   `comments/video-meta-ytdlp.json`. See `docs/plans/khaoniao-roadmap-90d-2026-09-28.md` §1.
5. Revenue signals found: the page claims **70,000–80,000 daily
   visitors** (PAGE'S OWN CLAIM, pinned post dated 17 Sep); at least 1 of the
   5 sampled videos is a direct in-narrative product-placement/affiliate
   clip with a burned-in "สั่งเลย" (order now) CTA (MEASURED, contact
   sheet); the page's own market-post copy admits **"แบรนด์ที่ทางเพจมีข้อตกลงอยู่"**
   (brands the page has agreements with) — MEASURED quote, confirms paid
   brand deals exist as a real income channel beyond platform ad-share.
6. **CEO's ~$3,000/month claim**: pure FB-ad-revenue math (§8) lands at
   roughly **$30–125/month for Seriescat.99 alone** — an ESTIMATE with wide
   uncertainty, built on the only Thailand-adjacent RPM benchmark found. That
   is far short of $3,000/month. The claim only becomes plausible once the
   confirmed brand-deal income (point 5) is added — platform ads alone do
   not get there.
7. **The dog/other-animal AI-drama niche is essentially empty.** 4 live
   Facebook searches today plus a prior 2026-09-17 scan of 8 similar Thai
   pages (kept as a cross-check, see §9) found **zero** dog-specific
   AI-drama page at anywhere near Seriescat's scale — the largest adjacent
   results are generic "ละครสั้น AI" pages with no animal branding, or real
   pet-lifestyle pages that are not AI-drama at all.
8. **Production**: photorealistic AI-generated video, 5–20 hard cuts per
   116–362s episode (ffmpeg scene-detection, MEASURED), all 5 clips carry an
   AAC audio track (MEASURED via ffprobe) — but the actual dialogue/audio
   transcript is **not measured this session**: faster-whisper hung twice
   (small model and tiny model) and was killed both times; flagged as a
   tooling failure in §10 and the skill-learning block, not a time-budget
   skip.
9. **Page Transparency (creation date, admin country) is not visible for
   either page** — 2 URL paths tried this session, neither rendered it; this
   matches the identical finding in the 2026-09-17 prior scan of 8 comparable
   pages, so it is very likely a structural gap in how FB renders
   Transparency for this page type, not a one-off failure.
10. **Recommendation direction for MoonieX's animal channel**: copy the
    *formula* (single consistent character + misdirection-to-heartwarming
    twist + title-card hook + simple 1–2 location setting), not the cat
    niche itself — the niche is crowded, but no equivalent dog/other-animal
    competitor currently exists at this scale.

---

## 2. Page facts — both pages

| | แมวซีรี่ย์ (Seriescat.99) | กาฟิวซีรีย์ (Gafiwseries) |
|---|---|---|
| Followers (FB, live count today) | **210,000** (2.1 แสน) — MEASURED | **44,000** (4.4 หมื่น) — MEASURED |
| Followers (FB, stated in page's own bio) | 190,000 — PAGE'S OWN CLAIM | not separately stated |
| Category | ครีเอเตอร์วิดีโอ (Video Creator) — MEASURED | ครีเอเตอร์คลิป Reels (Reels Creator) — MEASURED |
| Location | Chiang Mai, Thailand, 50140 — MEASURED | not rendered this session — not measured |
| Positioning | Primary page ("หลัก") — PAGE'S OWN CLAIM | "เพจสำรองอย่างเป็นทางการของ 'แมวซีรี่ย์'" (official backup page) — MEASURED |
| Contact | catseries.online@gmail.com · 080-2969731 — MEASURED | shares main page's contact per its bio — not separately listed |
| YouTube (self-reported) | 110,000 subs — PAGE'S OWN CLAIM | not stated |
| TikTok (self-reported) | 110,000 followers — PAGE'S OWN CLAIM | not stated |
| Instagram (self-reported) | 23,000 followers — PAGE'S OWN CLAIM | not stated |
| WhatsApp broadcast (self-reported) | 150,000 — PAGE'S OWN CLAIM | not stated |
| Page Transparency (creation date, admin country) | **not visible** — Ad Library returned no results; `/about_profile_transparency` re-rendered the normal About tab; no Transparency item in either "•••" menu | **not visible** — same result, same 2 paths tried |
| Daily visitors (self-reported) | 70,000–80,000/day — PAGE'S OWN CLAIM (pinned post, 17 Sep 2026) | not stated |

Both pages' "not visible" Page Transparency finding matches the identical
result recorded against 8 different Thai AI-drama pages on 2026-09-17
(`research/fb-thai-ai-drama-pages.md`, this worktree) — consistent across 10
pages and 2 separate sessions, so treated as a structural limit of this FB
surface for this page type rather than a search failure.

---

## 3. Cadence + post mix

- Most recent Seriescat post at capture time: **9 hours old**, 1,500
  reactions, 60 comments shown — MEASURED.
- The 5 downloaded episodes' upload dates (yt-dlp `upload_date`, MEASURED):
  2026-07-21, 2026-08-29, 2026-09-08, 2026-09-12, 2026-09-15 — span **~2
  months**, all in the top-10-by-views list, so cadence *between hits* cannot
  be read from this alone; it is not a complete post log.
- **A full chronological 30-post cadence scan could not be completed.** The
  ordinary FB feed virtualizes past roughly 10–15 rendered items even after
  repeated scroll/reload/wait cycles — the same class of DOM-virtualization
  problem the Reels tab hit (§10), and consistent with the prior session's
  note that FB's feed and Reels surfaces do this. Not measured beyond the
  single dated data point above.
- **Post mix is not 100% drama**: one of Seriescat's top-10 reels-by-views
  slots is a monthly "ฝากร้าน" (free community classifieds) post rather than
  a story episode — MEASURED, seen directly on the page. At least 1 of the 5
  downloaded drama episodes is itself a disguised product-placement/affiliate
  post (§5, §6) — so "drama" and "commerce" are not cleanly separate
  categories on this page.

---

## 4. Reel views — measured tables

### 4a. Seriescat.99 — top 10 reels, page-displayed view counts (MEASURED, live, today)

| Rank | Views (page display) |
|---|---|
| 1 | 1,000,000 |
| 2 | 970,000 |
| 3 | 950,000 |
| 4 | 130,000 |
| 5 | 120,000 |
| 6 | 97,000 |
| 7 | 79,000 |
| 8 | 73,000 |
| 9 | 58,000 |
| 10 | 20,000 |

Sum of these 10: **3,497,000** views.

### 4b. Gafiwseries — top 10 reels, page-displayed view counts (MEASURED, live, today)

| Rank | Views (page display) |
|---|---|
| 1 | 450,000 |
| 2 | 310,000 |
| 3 | 250,000 |
| 4 | 200,000 |
| 5 | 180,000 |
| 6 | 90,000 |
| 7 | 72,000 |
| 8 | 42,000 |
| 9 | 33,000 |
| 10 | 9,700 |

Sum of these 10: **1,636,700** views.

Both lists are the **10 most recent** reels by the Reels tab's own order
(FB does not expose per-reel dates in this view), not confirmed to be a
calendar month — see §10. This tab genuinely capped at 10 items again this
session despite scroll/reload attempts, matching the prior run's documented
finding.

### 4c. The 5 downloaded videos — three independent view-count sources, never reconciled

| Video ID | Page | Page display (live, today) | yt-dlp title-scrape (at download time) | yt-dlp `view_count` API field | Reactions (title-scrape) |
|---|---|---|---|---|---|
| 1098656909290931 | Seriescat | 1,000,000 | "1M views" | **644,310** | 47,000 |
| 1577233167381395 | Seriescat | 970,000 | "972K views" | **467,314** | 70,000 |
| 1055430417282185 | Seriescat | 950,000 | "950K views" | **534,322** | 74,000 |
| 1077573248092017 | Gafiwseries | 450,000 | "459K views" | **249,917** | 34,000 |
| 1527978345737352 | Gafiwseries | 310,000 | "313K views" | **178,007** | 19,000 |

Page-display and yt-dlp's title-scrape agree closely (both are FB's own
rendered "view" figure, sampled a few weeks apart, expected to have grown
slightly). The `view_count` API field is consistently **45–72% lower** than
the displayed figure across all 5 clips — likely a different internal
counting definition (e.g. unique plays vs. impressions). **Not reconciled,
per the task's own instruction** — reported as two labelled MEASURED numbers.

---

## 5. Five video breakdowns

| | 1098656909290931 | 1577233167381395 | 1055430417282185 | 1077573248092017 | 1527978345737352 |
|---|---|---|---|---|---|
| Page | Seriescat | Seriescat | Seriescat | Gafiwseries | Gafiwseries |
| Upload date | 2026-08-29 | 2026-09-08 | 2026-09-15 | 2026-09-12 | 2026-07-21 |
| Duration | 361.8s (6:02) | 215.4s (3:35) | 208.2s (3:28) | 123.3s (2:03) | 115.8s (1:56) |
| Shot count (ffmpeg scene-detect, MEASURED) | 15 | 5 | 5 | 20 | 5 |
| Views (page / API) | 1,000,000 / 644,310 | 970,000 / 467,314 | 950,000 / 534,322 | 450,000 / 249,917 | 310,000 / 178,007 |
| Reactions | 47,000 | 70,000 | 74,000 | 34,000 | 19,000 |
| Title/hook | "กาฟิว ผู้เสียสละ… แนวร้าย" (Gafiw the Sacrificer… villain-type) | "กาแฟ แมวที่ผมไม่เคยคิดจะเลี้ยง" (Coffee, the cat I never meant to keep) | "งานในฝันรออยู่ แต่ใครจะรอฟิว?" (The dream job is waiting, but who'll wait for Fiw?) | "รองเท้าคู่เก่าที่ตาไม่ยอมเปลี่ยน" (The old shoes grandpa won't replace) | "แมวจร คาบถุงยาหนี!" (Stray cat runs off with a bag of medicine!) |
| Setting | Rural Thai wooden house, grandmother + 2 daughters | Rural wooden house exterior/porch, one adult man | Urban condo hallway at night, young office worker | Rural wooden house, elderly grandfather | Pharmacy + wet-market street, pharmacist + elderly woman |
| Twist / misdirection | Cat looks aggressive toward the family, actually protecting/warning them | Cat quietly cared for by a man; framed as "Gafiw playing the role of Coffee" (meta caption) | Man appears to be choosing career over the cat; ends caring for it | Grandpa "won't buy new shoes" — actually buys the cat's collar/tag instead; embeds a product CTA | Cat looks like it stole medicine; actually running it to a sick grandmother |
| Audio | AAC track present (MEASURED, ffprobe) | AAC present | AAC present | AAC present | AAC present |
| Transcript | **not measured** — whisper failure, see §10 | not measured | not measured | not measured | not measured |

---

## 6. The formula (repeats across all 5)

1. **One consistent AI character carries the whole franchise** — the same
   orange tabby cat design (visible collar/tag, consistent face/markings)
   recurs across all 5 videos and both pages. MEASURED from contact sheets.
2. **Cold-open title card**: every video opens on a near-static frame with a
   large bold Thai headline plus a one-line curiosity-gap subtitle, before
   any character moves — a classic short-form retention hook, present in all
   5 samples.
3. **Misdirection → heartwarming reveal structure**: every one of the 5 sets
   up an ambiguous or "bad-looking" premise (villain cat, theft, refusing to
   buy shoes, choosing a career, "sacrifice") that resolves into a loving or
   selfless act. Zero exceptions in the sample.
4. **Simple, low-location-count settings**: 1–2 locations per episode (rural
   wooden house, condo hallway, market street) — never a multi-location
   production.
5. **Persistent brand watermark** in every frame across all 5 clips
   (recurring page logo bug, visible on every contact sheet) — brand
   consistency and a soft anti-repost mark.
6. **Low cut rate relative to runtime**: 5–20 hard cuts across 116–362s (one
   cut roughly every 15–70s), consistent with mostly-static dialogue coverage
   rather than fast-cut action editing.
7. **Commerce is woven into the narrative, not separated from it**: at least
   1 of 5 sampled episodes carries a direct product CTA inside the story
   itself, not as a separate ad post.
8. **Recurring human cast across episodes** (grandmother/family in one
   cluster of episodes, a different grandfather in another) builds a
   "cinematic universe" around the cat, encouraging fans to follow for the
   next installment rather than treating each clip as standalone.

---

## 7. Production recipe — with GUESS labels

- **Video generation**: photorealistic style, consistent character across
  dozens of episodes and 2 pages. **GUESS**: a Veo3/Kling/Runway-class AI
  video model with some form of reference-image or ID-conditioning workflow
  to hold the cat's design consistent — exact tool never disclosed, this is
  inference from output quality and consistency only, not a measurement.
- **Character consistency**: MEASURED that it holds (same cat design across
  all 5 samples and both pages); GUESS on the method (reference-conditioned
  generation vs. a trained character LoRA — cannot tell from output alone).
- **Editing**: 5–20 scene cuts per 116–362s clip — MEASURED (ffmpeg
  scene-detection, threshold 0.3).
- **Audio**: AAC track present in all 5 downloaded clips — MEASURED
  (ffprobe). Whether the audio is spoken Thai dialogue, music/SFX only, or a
  mix is **not measured this session** — see §10 for why.
- **Title card + hook subtitle**: burned-in graphic text card opens every
  video — MEASURED.
- **Watermark**: small recurring logo bug present in every frame of every
  sampled clip — MEASURED.
- **Locations**: rural Thai wooden house (2/5), urban condo hallway (1/5),
  pharmacy + wet market street (1/5), rural house exterior (1/5) — MEASURED,
  small and cheap-to-imply location count per episode.
- **Runtime**: 116–362s (median of this 5-clip sample ≈ 208s) — MEASURED.
  Not confirmed representative of the full catalogue.

---

## 8. Revenue estimate + verdict on the CEO's ~$3,000/month claim

**What's directly confirmed (MEASURED):**
- The page's own pinned post claims 70,000–80,000 daily visitors — PAGE'S
  OWN CLAIM, not independently verifiable from outside the account.
- The page's own copy admits ongoing paid brand-deal agreements exist
  ("แบรนด์ที่ทางเพจมีข้อตกลงอยู่") — MEASURED quote, a real income channel.
- At least 1 of 5 sampled episodes is itself a disguised
  product-placement/affiliate post — MEASURED.
- No FB Ad Library entries, no visible shop plugin, no visible
  Stars/subscription button, no other on-page monetization signal found.

**Ad-revenue-only estimate (ESTIMATE, wide uncertainty — method shown in
full so it can be checked or corrected):**

1. No Thailand-specific Facebook RPM figure exists in the org's own prior
   research (`research/2026-09-28-ai-drama-ad-revenue-by-country.md`
   explicitly states: *"No reliable Thai-audience drama RPM found"*). The
   closest MEASURED Thai benchmark is a **blended YouTube RPM of $0.37 per
   1,000 views** (Dynamoi, music-heavy sample — an imperfect proxy, flagged
   in the source doc itself).
2. That same doc gives two Facebook-specific RPMs for comparable
   non-English markets: Portuguese (Brazil) **$0.02/1,000** against a
   long-form YouTube RPM of $0.58 (≈3.4% of YouTube LF), and Spanish
   (Mexico) **$0.06/1,000** against ~$0.47 (≈13% of YouTube LF).
3. Applying that 3.4%–13% FB-to-YouTube ratio to the Thai $0.37 YouTube
   figure gives an **ESTIMATED Thai Facebook RPM of roughly $0.013–$0.048
   per 1,000 views**. This stacks two uncertainties (cross-country ratio,
   and applying a long-form ratio to short-form Reels) and could plausibly
   be off by several multiples in either direction — treat as an order-of-
   magnitude check, not a precise figure.
4. Using the page's own claimed 70,000–80,000 daily visitors as a rough
   proxy for monthly reach (≈ 2.1M–2.4M/month — PAGE'S OWN CLAIM, and
   "visitors" is not the same thing as "monetized video views," a real gap):
   **2.1M–2.4M × $0.013–$0.048 / 1,000 ≈ $27–$115/month for Seriescat.99
   alone.**

**Verdict**: pure Facebook ad-share income, on this math, is nowhere near
$3,000/month for either page — off by roughly 25–100×. The CEO's figure is
**not plausible from FB ad revenue alone**, but **is plausible once the
confirmed brand-deal income and any off-platform channels (WhatsApp
broadcast to 150k, YouTube, TikTok — all separately monetizable, none
measured here) are included.** This report cannot see actual ad-manager
earnings from outside the account — that number is inherently unmeasurable
externally, and no guess is offered for it.

---

## 9. Saturation table (≤10 pages)

Combines today's 4 live searches (หมาซีรีย์ / ละครสั้นหมา AI / น้องหมา
ละครสั้น / ละครสั้นสัตว์ AI) with the most relevant rows from the prior
2026-09-17 scan (`research/fb-thai-ai-drama-pages.md`, this worktree,
labelled accordingly).

| Page | Followers | Niche | Animal-branded? | Date measured |
|---|---|---|---|---|
| แมวซีรี่ย์ (Seriescat.99) — the subject of this report | 210,000 | Cat AI drama | Yes, cat | 2026-09-28 |
| กาฟิวซีรีย์ (Gafiwseries) — sister page | 44,000 | Cat AI drama | Yes, cat | 2026-09-28 |
| มี ซีรีย์ | 530,000 | Generic drama/entertainment | No | 2026-09-28 |
| ละครหนังสั้น Ai | 68,000 | Generic AI drama | No | 2026-09-28 |
| ละครสั้น AI (Nonthaburi, #5 in prior scan) | 44,000 | Generic AI drama, claims daily eps | No | 2026-09-17 |
| ซีรีย์ AI เรื่องนี้มีพีค | 130,000 | Generic AI drama (romance/horror/twist) | No | 2026-09-28 |
| น้องอั้ม ละครสั้น | 140,000 | Real-pet lifestyle (not AI-generated) | Human-presented pet content | 2026-09-28 |
| น้องหมา เค้าบอกว่า | 120,000 | Dog-branded, content type not confirmed | Yes, dog (branding only) | 2026-09-28 |
| สัตว์หลุดโลก AI | 12,000 | Funny-animal clips, not narrative drama | Yes, mixed animals | 2026-09-28 |
| แมวติดซีรีย์ | 11,000 | Cat content, not confirmed AI-drama | Yes, cat | 2026-09-28 |

**Reading**: no page in either search round is a dog-specific AI-drama
franchise anywhere near Seriescat's scale. "น้องหมา เค้าบอกว่า" (120k) is the
one dog-branded page worth a follow-up look, but its content type (AI-drama
vs. real dog clips) was not confirmed this session — flagged, not guessed.
The cat niche (Seriescat + Gafiwseries combined, 254k) has no comparably
sized peer in this data; the generic "ละครสั้น AI" space is more populated
(11k–530k range) but not animal-specific.

---

## 10. What could not be measured, and why

- **Audio transcripts for all 5 videos.** faster-whisper hung twice this
  session: once with the `small` model (killed after ~16 minutes of CPU time
  stuck on the first, 362s video, zero output), once again after switching to
  the `tiny` model (killed after ~8+ minutes, still stuck on the same first
  video before even finishing that one file). A follow-up run with the
  transcript step removed entirely completed scene-detection + contact
  sheets for all 5 videos in under 15 seconds total — confirming the hang was
  specifically in faster-whisper's transcribe step on this machine/venv, not
  a slow scene-detection or a genuinely large workload. Not re-attempted a
  third time, per the task's own "stop and report rather than loop" rule.
  Flagged in the skill-learning block below as a COSTLY/environment finding.
- **Page Transparency (creation date, admin country) — 0 of 2 pages.** Meta
  Ad Library returned no results; the `/about_profile_transparency` URL
  re-rendered the ordinary About tab; neither page's "•••" menu offered a
  Transparency option. Matches the identical finding against 8 other Thai
  AI-drama pages on 2026-09-17.
- **Full 30-post chronological cadence.** The ordinary feed virtualizes past
  roughly 10–15 rendered posts even after repeated scroll/reload/wait
  cycles — the same DOM-virtualization limit the Reels tab hit. Only a
  single dated data point (one 9-hour-old post) plus the 5 downloaded clips'
  upload dates were captured.
- **Like/comment counts for 15 of the 20 total reels sampled.** Only the 5
  downloaded videos carry a reactions figure (from yt-dlp's title-scrape);
  yt-dlp's structured `like_count`/`comment_count` fields returned `None`
  for all 5. The other 15 reels (10 per page minus the 5 downloaded) have
  view counts only, no engagement figures.
- **TikTok / YouTube / Instagram actual measured stats.** Only the page's
  own self-reported bio numbers were captured (110k/110k/23k) — these
  accounts were not independently visited this session, so the figures
  carry no independent verification.
- **Exact revenue figure.** Never publicly visible from outside the FB
  account; inherently unmeasurable externally. See §8 for the bounded
  estimate offered instead.
- **Admin team size / identity beyond the public contact email and phone
  number.** Not visible from a public page view.
- **Whether "น้องหมา เค้าบอกว่า" (120k, §9) is an AI-drama competitor or a
  different content type.** Not opened this session — flagged as a
  worthwhile follow-up, not guessed.

---

## 11. Asset paths (local only — never committed to git)

```
/Users/gob/MoonieXHQ/Assets/Agents/Core/competitor-study/catseries-2026-09-28/
├── breakdown.json                  — scene counts + contact-sheet paths for all 5 videos
├── videos/
│   ├── 1098656909290931.mp4 (+ .info.json)
│   ├── 1577233167381395.mp4 (+ .info.json)
│   ├── 1055430417282185.mp4 (+ .info.json)
│   ├── 1077573248092017.mp4 (+ .info.json)
│   └── 1527978345737352.mp4 (+ .info.json)
├── contact-sheets/
│   ├── 1098656909290931_contact.jpg
│   ├── 1577233167381395_contact.jpg
│   ├── 1055430417282185_contact.jpg
│   ├── 1077573248092017_contact.jpg
│   └── 1527978345737352_contact.jpg
└── frames/                         — empty, unused this session
```

This markdown file is the only file from this task committed to git.

---

## Skill learning

- COSTLY [browser-operator | no owner] : faster-whisper (`small`, then
  `tiny`) hung indefinitely transcribing a downloaded competitor .mp4 in this
  venv — no crash, no error, just no progress — burning roughly 25 minutes of
  a 90-minute budget across two attempts before being killed both times ·
  evidence: task-8637dc69, PIDs 43504 (small, killed at ~16 min CPU / 0
  progress) and 48918 (tiny, killed at ~8+ min CPU / 0 progress on the same
  first video) · fix: probe faster-whisper against a short (~10s) known-good
  clip before committing it to a multi-video batch job, and wrap the
  `transcribe()` call itself in a hard per-video timeout (e.g. `perl -e
  'alarm N; exec @ARGV'`) so one stuck file cannot consume the whole
  session's time budget — a script-level try/except around the whole batch
  does not help because the hang never raises.
- MISSING [browser-operator §Facebook Reels tab] : the skill does not
  document that FB's Reels tab caps at roughly 10-11 rendered items
  regardless of scroll/reload/wait cycles · evidence: task-8637dc69 (this
  session, both pages) and the 2026-09-17 prior scan of 8 pages
  (`research/fb-thai-ai-drama-pages.md`) hitting the identical wall · fix:
  document the cap explicitly so a future operator stops after 2-3 tries
  instead of extensively retrying past it.
- (none) : everything else in the existing browser-operator guidance (id-diff
  via `a.pathname` regex, javascript_tool-first discipline, decide-before-
  screenshot) held up as documented this run.
