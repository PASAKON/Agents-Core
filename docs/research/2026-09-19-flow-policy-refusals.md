# What triggers a Google Flow / Veo generation refusal — and does it match our 3 blocked shots

**Method:** read-only, Google's own pages fetched directly where possible (verbatim quotes below), forum/blog reports used as leads and clearly labeled. All pages read **2026-09-19**. No accounts touched, no spend.

**The three refused shots** (Thai drama, Omni 1.1 Flash, องค์ประกอบ/Ingredients mode), all refused with only `การสร้างนี้อาจละเมิดนโยบายของเรา` ("this generation may violate our policy"), refunded, no reason given:

- **Shot 1** — man alone at a shophouse wall before dawn: *"ผมหาให้ครับ..."* / *"อย่าเพิ่งไปที่ร้านเลยครับ ลูกผมอยู่ที่นั่น"* (his son is at the shop). Earlier failed drafts had him pinned to the wall by an off-frame arm, then a long shadow over him.
- **Shot 6** — same man, dim bedroom, counting money aloud, mother asleep nearby, dialogue names her medicine shortfall. Prompt includes a paragraph stating the banknotes are invented theatrical prop money.
- **Shot 24** — same man at a counter, counting costs on fingers, dialogue: *"ค่ายาแม่ ห้ามแตะเด็ดขาด"* (this is mother's medicine money, never touch it).

Shots that **pass** with the same character/shop/prop-money paragraph: handing money back to a customer, a son asking if he's counting money, refusing payment. So plain "money" or "this character" is already ruled out by the task's own comparison set.

---

## 1. What Google's Generative AI Prohibited Use Policy actually lists

**Source:** https://policies.google.com/terms/generative-ai/use-policy — **"Last Modified: December 17, 2024"**, read 2026-09-19.

Four categories, quoted verbatim:

**"Dangerous or Illegal Activities"**
> "Relates to child sexual abuse or exploitation"
> "Facilitates violent extremism or terrorism"
> "Facilitates non-consensual intimate imagery"
> "Facilitates self-harm"
> "Facilitates illegal activities or violations of law"
> "Violates the rights of others, including privacy and intellectual property rights"
> "Tracks or monitors people without their consent"
> "Makes automated decisions that have a material detrimental impact on individual rights"

**"Security Compromise"**
> "Spam, phishing, or malware"
> "Abuse of, harm to, interference with, or disruption to Google's or others' infrastructure"
> "Circumvention of abuse protections or safety filters"

**"Sexually Explicit, Violent, or Hateful Activities"**
> "Hatred or hate speech"
> "Harassment, bullying, intimidation, abuse, or the insulting of others"
> "Violence or the incitement of violence"
> "Sexually explicit content"

**"Misinformation and Misrepresentation"**
> "Frauds, scams, or other deceptive actions"
> "Impersonating an individual without explicit disclosure"
> "Facilitating misleading claims of expertise in sensitive areas"
> "Facilitating misleading claims related to governmental or democratic processes"
> "Misrepresenting the provenance of generated content"

**Exception clause:** "Google may permit exceptions based on 'educational, documentary, scientific, or artistic considerations.'" — a fictional drama has a plausible claim to this, but it is a discretionary carve-out Google applies, not something a worker/creator can invoke to unblock a generation.

**Does a poor man in debt, or counting money for a sick parent, plausibly fall under any of these?**
- **Not documented as its own category at all.** Financial hardship, poverty, or a character being in debt is not named anywhere in this policy.
- The only categories with any plausible reach are **"Violence or the incitement of violence"** (category 3) — relevant only to the *earlier, since-removed* drafts of shot 1 (pinned to the wall, a threatening shadow), not to the final refused text — and **"Facilitates illegal activities"** (category 1) — a stretch, since none of the three shots depict or instruct an illegal act, only a man worried about money and a debt he owes.
- **Verdict: none of the four documented categories cleanly covers "a poor man counting money for his sick mother."** That theme is not a named violation anywhere in this policy.

---

## 2. Flow/Veo-specific guidance on refusals

**Flow's own help pages** name a feedback mechanism but never document *what* triggers a block:
- "Report a problem or send general feedback" (https://support.google.com/flow/answer/16353335, read 2026-09-19): describes "Flag output" (three-dot menu → select what's wrong → Submit) and "Send app feedback." No content about causes of refusal.
- "Get started with Google Flow" (https://support.google.com/flow/answer/16353333) links to the Prohibited Use Policy (§1 above) but adds nothing Flow-specific.

**Google DeepMind's own Veo prompting guide** (https://deepmind.google/models/veo/prompt-guide/, read 2026-09-19) covers framing, style, lighting, character description, location, action, dialogue — pure composition advice. **It contains no content-policy guidance, no list of disallowed themes, and no explanation of refusals at all.**

**Veo API docs** (https://ai.google.dev/gemini-api/docs/veo, read 2026-09-19):
> "Veo applies safety filters across Gemini to help ensure that generated videos and uploaded photos don't contain offensive content."
> "In EU, UK, CH, MENA locations, `allow_adult` is the only allowed value for `personGeneration`."
> Generated videos undergo "safety filters and memorization checking processes that help mitigate privacy, copyright and bias risks."

No breakdown of what "offensive content" means beyond that, and no per-category list.

**Gemini API safety settings** (https://ai.google.dev/gemini-api/docs/safety-settings, page shows **last updated 2026-09-17**, read 2026-09-19) — this is the underlying harm-classification layer Omni/Veo sit on:
- Four adjustable categories: **"Harassment"** ("Negative or harmful comments targeting identity and/or protected attributes"), **"Hate speech"** ("Content that is rude, disrespectful, or profane"), **"Sexually explicit"** ("Contains references to sexual acts or other lewd content"), **"Dangerous"** ("Promotes, facilitates, or encourages harmful acts").
- Critically: **"the Gemini API has built-in protections against core harms such as content that endangers child safety, and these types of harm are always blocked and cannot be adjusted."** This is a fifth, non-configurable layer sitting underneath the four adjustable ones — separately confirmed by a Gemini API reference listing `HARM_CATEGORY_CIVIC_INTEGRITY` as a fifth *configurable* category (elections/civic process), distinct again from the always-on child-safety layer.

**Conclusion for Q2: Google publishes no Flow/Veo-specific document naming concrete refusal triggers.** The closest thing to a mechanism explanation is the general Gemini API safety-settings page, which is not Flow-specific and predates/underlies the product rather than documenting it.

---

## 3. What other users report (anecdote — labeled throughout)

**USER-REPORTED — generic, unexplained refusals on mundane content**, from a Google AI Developer Forum thread (https://discuss.ai.google.dev/t/veo-flow-generation-issues-lost-credits-consistency-problems-and-excessive-failed-generations/147374, various dates in 2026, read 2026-09-19):
- NW94 (2026-05-22): the refusal message "does not explain WHY it failed," lists rejected mundane content — "characters walking, entering rooms, sitting at tables, adjusting bags, rooftop scenes, museum scenes, friends talking, everyday interactions" — and says "Nothing explicit. Nothing unsafe. Nothing extreme."
- SinCityCodeman (2026-07-22): a poker-dealer line ("Players, I'm gonna have to let you go now") was rejected, and a rephrase was rejected too. His read: **"Google seems to go with the idea that if it ANYTHING could even possibly be taken out of context...then it should be off-limits."**
- Andrew_Miller (2026-07-06): refusals disappeared after switching accounts — pointing at an inconsistent/noisy classifier rather than a deterministic content rule.
- Contrast with our case: this thread's users mostly report **credits NOT refunded** on a blocked generation ("75 credits later and I still dont have something useable" — Lee_Duke, 2026-07-06). Our three shots WERE refunded. That's a real discrepancy worth flagging — it may mean pre-render prompt-blocks (refunded, ours) and post-render failures (not refunded, theirs) are different failure modes, not the same one.

**USER-REPORTED — the closest documented analog to "mentioning a child in a distressing context"**, from a Google AI Developer Forum post (https://discuss.ai.google.dev/t/veo-3-1-image-to-video-blocks-wholesome-commercial-storyboard-child-safety-false-positive/131917, poster BogdanPi, 2026-03-13, read 2026-09-19):
- Scenario: a wholesome family commercial, "a grandfather and grandson walking on a forest path," using Veo 3.1 image-to-video.
- Exact errors, quoted: **"The input image contains content that has been blocked by your current safety settings for person/face generation. Support codes: 17301594"** and **"The prompt could not be submitted. This prompt contains sensitive words that violate Google's Responsible AI practices. Support codes: 58061214."**
- Poster's own testing: removing all textual references to "grandson"/minors and stripping the prompt to only camera/environment description **still failed** — i.e., in his case the block persisted even after the child-referencing text was gone, which argues the trigger (in his case) was the *reference image* containing a child, not merely the word "grandson."
- No Google staff reply, no resolution documented in the thread — several other users report the same pattern, which the thread frames as recurring.

**USER-REPORTED — another false-positive report on completely innocuous prompts**, from a Nano Banana Pro / Flow forum thread (https://discuss.ai.google.dev/t/nano-banana-pro-in-flow-false-policy-violation-on-normal-commercial-portrait-prompts/174894, poster Harsh_Sharma1, read 2026-09-19): prompts like *"Portrait of a smiling woman holding a notebook,"* *"Businesswoman in a modern office,"* *"Farmer in a wheat field"* refused with "This generation might violate our policies." Escalated to Google One Support (screen recordings, account verification, repro steps submitted) — **no resolution or root cause documented in the thread.**

**SPECULATION / secondary-source synthesis (not Google, not verified against Flow directly)** — two SEO/creator-blog articles compile crowdsourced "trigger word" theories:
- freevisualtools.com (https://freevisualtools.com/blog/sora-veo-content-violation-fix/, read 2026-09-19) claims: age words (young/teen/child/kid/baby) trip a child-safety classifier; restraint words (tied/bound/chained/trapped/captured/imprisoned) trip a bondage/abduction filter; distress words (crying/weeping/sad/depressed/despair) and isolation words (alone/abandoned/isolated) trip a self-harm classifier. It reuses the BogdanPi grandfather/support-code-17301594 case above as its example — that specific code is corroborated by the real forum post, but the general word-list claims are **the blog's own synthesis, not sourced from Google**, and were not independently verified here.
- yapper.so (https://yapper.so/articles/why-veo3-videos-get-rejected, dated 2025-07-19, read 2026-09-19) lists similar clusters (violence words: fight/attack/kill/weapon/blood/wound/injury/conflict; sexual words; hate speech; dangerous-activity words: suicide/drugs/theft) plus odd extras ("migrants," "political figures," "natural disasters," vague camera terms like "POV camera"). Explicitly presented by the article itself as user-reported pattern, not Google-confirmed.

**Checked and NOT found — non-English text as a documented or reported trigger.** No Flow/Veo-specific report surfaced connecting Thai (or any non-English) dialogue text to a higher refusal rate. General AI-safety research shows multilingual safety classifiers can behave less reliably outside English, but that is a property of language models generally, not something reported about Flow specifically. **Not documented, not evidenced for this product.**

**Checked and NOT found — real-currency depiction as a Flow/Veo trigger.** Broad AI-image-generator industry practice (unrelated tools) avoids reproducing exact real banknotes for counterfeit-deterrence reasons, but no Google Flow/Veo-specific statement or user report ties currency imagery to a block, and the task's own evidence already rules this out: shots that pass carry the identical "invented theatrical prop money" paragraph as the shots that fail.

**Checked and NOT found — financial distress/poverty/debt as a named or reported trigger**, searched directly; nothing surfaced. **Not documented.**

---

## 4. Is there a known false-positive pattern for mentioning a child or elderly dependent in a distressing context?

This is the leading hypothesis for our three shots (shot 1 mentions his son; shots 6 and 24 both mention his mother's medicine) — and it needs to be treated as a guess, per the task brief.

**What's actually established:**
- **GOOGLE-STATED:** there is a real, architectural fact that supports the *mechanism*: Google's own Gemini API safety docs state a **non-adjustable, always-on child-safety layer** sits beneath the four configurable harm categories (§2 above) — "core harms, such as content that endangers child safety... cannot be adjusted." This is exactly the kind of always-on classifier that would be tuned conservatively and could plausibly over-fire on a merely-mentioned, off-frame child in a worried context.
- **USER-REPORTED, imperfect analog:** the BogdanPi grandfather/grandson case is the closest real report of a "child-safety" refusal, but it was triggered (per the poster's own elimination testing) by a **reference image** containing a child, and persisted even after child-referencing **text** was removed — meaning that specific case argues against pure text-mention being the trigger. Our shot 1's son is never shown or referenced by any image chip — he's only named in spoken dialogue as being at a location, not depicted. This is a meaningfully different shape of "child mention" than the documented analog.
- **Nothing found, Google or anecdote, specifically about an elderly/sick dependent** (shots 6 and 24's mother) as a trigger category. No report anywhere ties "a sick or elderly relative mentioned in dialogue" to a refusal.

**Verdict: SPECULATION.** The always-on child-safety classifier's existence is GOOGLE-STATED and gives the hypothesis a plausible mechanism, and one USER-REPORTED case shows a real "child" false positive on the platform family — but no source, official or anecdotal, describes our exact pattern (a child or elderly person referenced only in spoken dialogue, never depicted, in an otherwise unremarkable domestic scene). This hypothesis is worth testing (e.g., re-firing shot 1's dialogue with "ลูกผม" replaced by a non-family-member noun, holding everything else constant) but is not confirmed by anything documented here.

---

## 5. Does Google document an appeal/feedback route, and has it worked for anyone?

- **Per-generation feedback exists but is not an appeal**: Flow's "Flag output" (three-dot menu → Flag output → select issue → Submit) and "Send app feedback" (https://support.google.com/flow/answer/16353335) report a problem; nothing in that page says a flagged/reported block gets reviewed and reversed, or that the content becomes generable afterward.
- **A true appeal process is documented, but at the account level, not the generation level**: Gemini Apps Help's Prohibited Use Policy enforcement page (https://support.google.com/gemini/answer/16625148, read 2026-09-19) states users can **"appeal the restriction by submitting an appeal using the link from the restriction notice or email"** — this is for account-level restrictions after a *confirmed* violation, not for getting a single blocked generation approved.
- **No verified case found of a single refused generation being successfully appealed/unblocked.** The Nano Banana Pro thread (§3) escalated a specific refusal to Google One Support with screen recordings, account verification, and repro steps — the thread documents the escalation but **not a resolution**. No other thread read here reports a successful reversal.
- **Verdict: "not documented" that appealing a single generation works.** A reporting channel exists (Flag output / Send feedback); a formal appeal exists only for account-level enforcement; nobody in the sources checked here reports getting a blocked shot approved through either path.

---

## Ranked shortlist of candidate triggers for our three shots

1. **SPECULATION** — An always-on, non-adjustable child-safety-adjacent classifier (GOOGLE-STATED to exist, §2) over-firing on a narrative that references a child (shot 1's "my son is there") or an elderly/vulnerable dependent (shots 6, 24's sick mother) even though neither is depicted, only spoken about. Plausible mechanism, no exact documented or reported match — closest analog (grandfather/grandson, §3/§4) involved a depicted child in a reference image, not a spoken mention.
2. **SPECULATION** — Broad, context-sensitive "financial desperation / a man alone at night worried about money for a sick relative" theme tripping an over-cautious classifier tuned near self-harm/distress content, consistent with multiple USER-REPORTED accounts of the classifier over-triggering on completely mundane scenes and one user's explicit theory that "if ANYTHING could even possibly be taken out of context... it should be off-limits" (SinCityCodeman, §3). No Google document names financial distress as a category at all.
3. **GOOGLE-STATED, but only explains discarded drafts** — "Violence or the incitement of violence" (§1) cleanly covers the *earlier, since-rewritten* versions of shot 1 (pinned to a wall by an off-frame arm, a threatening shadow) but does not explain why the final, non-violent version of shot 1 (or shots 6/24, which never had a violent draft) also failed.
4. **USER-REPORTED, unranked but real** — Simple classifier noise/inconsistency: multiple forum reports (Andrew_Miller switching accounts and refusals disappearing, §3) show the system is not fully deterministic. It's possible one or more of our three shots is a plain false positive with no stable content explanation, and an identical re-fire could succeed or fail unpredictably.
5. **Checked and ruled out / not evidenced** — real-currency depiction (ruled out by the task's own pass/fail comparison, §3), non-English/Thai dialogue text (no evidence found, §3), and "money" or "this character" generally (ruled out by the task brief itself).

**Bottom line:** none of Google's own published rules name a category that matches "a poor man counting money for his sick mother," or "a father worried his son is near danger." The strongest lead is architectural, not documented-as-a-rule: an always-on child-safety layer that is known to exist and known (from one forum case) to occasionally over-fire, applied here to a spoken-not-shown child/elderly reference in a financially desperate scene. That is a hypothesis worth testing empirically (isolate the variable: re-fire shot 1 with the son-reference line removed, holding everything else identical), not a confirmed cause.
