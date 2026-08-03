# TRADER UNCUT — Voice & Pacing Guide (v1.0)

Derived empirically from full transcripts of the 5 benchmark videos (channel
"Uhas Trader", the CEO's stated editor/tonal reference — see
`design-templates/trader-uncut/BRAND.md` in mooniex-claudesign for visual
brand, this file is the missing narration counterpart). Source transcripts:
`knowledge/content-knowledge/skills/trader-story-scripts/transcripts/01_*`
and `06_*`, plus three pulled specifically for this analysis (CHCg-CgpwmE,
DhfZPfxajrU, ozgszb410iM — not yet added to the swipe file, ask CTO if you
need the raw text).

**Target length: 8–12 minutes.** At 130–150 Thai wpm that's roughly
**1,050–1,800 words** of narration — 3–5x longer than the EP1/EP2 pilot
scripts (320–450 words). The gap isn't padding for its own sake — the
benchmark videos earn their length through specific, repeatable techniques
below. Use them; don't just write more sentences per beat.

## Do NOT copy verbatim

- Uhas Trader's own brand jingle ("you have ดอทคอมเราคือเพื่อนแท้นักเทรด")
  and their specific broker ad-read (Exness/XM affiliate pitch) are their
  IP/business, not ours. Structure only — see `roles/script_writer.md`
  Hard Rule on plagiarism.
- Never lift their actual sentences. These 5 are reference for *shape*,
  not text to paraphrase-adjacent.

## The structural recipe (8 beats, in this order)

1. **Cold-open hook (0:00–0:15)** — state the core numbers immediately,
   before any greeting: starting capital → what happened → ending
   amount → timeframe, framed as astonishing. Close with a one-line
   teaser ("เรื่องราวจะเป็นอย่างไร เดี๋ยวเราจะมาดูกันในคลิปนี้"). No
   preamble, no "สวัสดีครับ" yet — the hook comes before the greeting.

2. **Brand stamp + CTA (short)** — TRADER UNCUT's own sting/CTA placeholder
   (`{{AFFILIATE_LINK}}` context), analogous to their jingle+ad-read slot,
   but ours, not theirs. Keep this block short (10–15 sec worth) — it's a
   stamp, not a sales pitch.

3. **Formal greeting + topic restate** — "สวัสดีครับ/ค่ะ... เนื้อหาในวันนี้..."
   restates the hook a second time, slightly more descriptively. This
   second pass is deliberate — it lets viewers who skipped the cold open
   still get oriented.

4. **Backstory / biography (the single biggest length driver)** — who is
   this person, how did they get here, early struggles or failed
   attempts, personality/daily-routine details if known and relevant.
   The Takashi Kotegawa video (wH87_AlQi7Q) spends the majority of its
   ~29 min here: wake time, what he eats, whether he has a car, family
   life — granular personal detail, not just a resume. For TRADER UNCUT
   stories where this level of biographical detail isn't verifiable
   (per script_writer's no-fabrication rule), substitute with **verified
   context instead of invented personal detail** — market conditions,
   career facts, the specific decision that led here — never invent
   biographical color to fill time.

5. **Step-by-step real-time walkthrough (the second biggest length
   driver)** — narrate the event's own timeline like a commentator, not
   as a summary. ozgszb410iM narrates an 8-hour live stream almost
   minute-by-minute: "ตอนนี้ติดลบอยู่ที่... ผ่านมา 1 ชั่วโมงครึ่งแล้ว...
   ตอนนี้เข้าสู่ชั่วโมงที่ 4..." — running numbers, escalating tension,
   explicit "ดูกันต่อไปว่าจะเกิดอะไรขึ้น" pacing cues between updates.
   Apply this to whatever real timeline the research brief supports
   (market hours, the specific day's price action) — don't invent a false
   blow-by-blow if the sources don't support that granularity; use what's
   verified and pace it like this technique rather than summarizing it in
   two sentences.

6. **Mechanics explainer aside** — when the story depends on a concept
   the audience might not know (leverage, margin call, short-selling),
   stop and explain it with a worked numeric example before continuing.
   DhfZPfxajrU spends ~4-5 min explaining leverage with a concrete
   $20,000-at-40x example before returning to the story, and the narrator
   explicitly says why: "ผมอยากที่จะทำความเข้าใจตรงกันก่อน" (I want us on
   the same page first). This is a legitimate technique, not a digression
   — use it once per script for the single most load-bearing mechanic.

7. **Narrator persona, not neutral third-person** — critical structural
   difference from what EP1/EP2 currently do. All 5 benchmarks narrate in
   first person ("ผม") as a host reacting to and analyzing someone else's
   story, not a flat documentary voiceover. The host inserts: his own
   opinion, his own comparable trading experience ("ผมเองก็เทรดช่วงนั้น
   เหมือนกัน... ราคาผมปิดที่ 27... ผมได้ +3,000 ผมก็ไปแล้ว"), skepticism
   he addresses directly ("หลายคนอาจสงสัยว่าบัญชีนี้จริงไหม..."), and
   explicit risk caveats woven through, not just bolted on at the end.
   TRADER UNCUT should adopt a **host-narrator layer** — a consistent "ผม"
   voice reacting to and unpacking the story — rather than pure
   third-person narration. This does not mean inventing a fake personal
   trading anecdote; it means writing the analytical/reactive commentary
   the research actually supports ("what's notable here is...", "this is
   the same failure pattern as...") in first person.

8. **Aftermath → lesson → sign-off** — what happened after the climax
   (career/financial consequences if known and verified), then explicit
   risk-management lesson pulled from the story, then CTA + tease next
   episode + ask for topic suggestions in comments. Engagement CTAs
   (like/subscribe) appear at least twice — once early, once at the end —
   not just once.

## Register / verbal texture

- **Direct address is constant.** "คุณผู้ฟัง" (or equivalent) appears in
  nearly every paragraph — this is what makes narrated-monologue feel
  conversational. Don't let long biographical/mechanical sections drift
  into pure exposition without checking back in with the audience.
- **Numbers always get localized.** Every foreign-currency or large
  figure is immediately converted and restated in Thai baht
  ("...เยน ถ้าตีเป็นเงินไทยก็ประมาณ..."). Do this every time a new
  currency/large number appears, not just once at the top.
- **Spoken-Thai particle density is high** (นะครับ/เนาะ/ครับ on nearly
  every clause) — write for the ear, not the page. This is a floor, not
  a ceiling — TRADER UNCUT's own documentary tone (per BRAND.md) can be
  slightly less filler-heavy than Uhas Trader's very casual register, but
  should still read as spoken, not written.
- **Pacing cues are explicit and frequent**: "เรามาดูกันว่าจะเป็นอย่างไร
  ต่อ", "ก่อนที่เราจะไปพูดถึง...เรามาทำความเข้าใจ...ก่อน" — these aren't
  filler, they're the seams that let a single story sustain 10+ minutes
  without losing the viewer. Use them between beats, especially before/
  after the mechanics-explainer aside and at each step of the real-time
  walkthrough.

## What this means for cutaway density

Longer runtime needs proportionally more cutaway beats than the EP1/EP2
pilots' ~6. Budget roughly one cutaway every 45–75 seconds of narration
for an 8-12 min script (i.e. ~8-16 beats total) — enough to keep a
narrated-stock-footage format visually alive across the longer runtime,
matching the video_editor pipeline's cut-rhythm expectations
(`roles/video_editor.md`).
