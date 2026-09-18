# Google Flow commercial-use rights — video, preset voices, watermarking

**For:** a Facebook channel that will be monetised · **Account:** CEO's personal Google account, **Google AI Ultra** (Thailand, ฿3,500/mo), Flow accessed at flow.google.com. Not Workspace. Not a Cloud/Vertex API project.
**Method:** read-only. Google's own pages only, fetched/curled directly (not summarized-by-a-third-party), verbatim quotes below. Forum threads and blogs used as leads only, never as the answer. All pages read **2026-09-18**.
**Out of scope (already on record):** Flow Music (Lyria, flowmusic.app) — commercial rights not stated on its own product pages. See wiki `mooniex:playbooks/google-ai-ultra-benefits.md`. Not re-derived here except where it usefully contrasts with the video product (§1).

---

## 1. Flow video output (Veo 3.1 / Omni 1.1 Flash via the Flow UI, Ultra plan)

**Flow's own Help Center answers this exact question.** From "Get started with Flow" (support.google.com/flow/answer/16353333), the FAQ entry titled *"Can I use outputs of these tools for commercial purposes?"*:

> "The Terms of Service govern how these tools may be used, and must be consulted and followed in their entirety. Per those terms: Some of our services allow you to generate original content. Google won't claim ownership over that content."
> — https://support.google.com/flow/answer/16353333?hl=en, read 2026-09-18

That sentence is quoting the governing document, the main **Google Terms of Service** (policies.google.com/terms). Fetched directly, under "Content in Google services" → "Your content":

> "Some of our services allow you to generate original content. Google won't claim ownership over that content. Some content may not be suitable for everyone."
> — https://policies.google.com/terms?hl=en, read 2026-09-18

This is the current, consolidated ToS (the page's own asset path is tagged `tos_2024`, consistent with Google's May 22, 2024 rewrite — see §4). Signing in to Flow itself points here: Flow Music's own onboarding flow (documented on the same Ultra benefits page) has the user "Review the Terms of Service" linking to this exact `policies.google.com/terms` URL, not a separate Flow-specific document. There is no dedicated "Flow Terms of Service."

**What this establishes, and what it does not:**
- Google does **not** claim ownership of video you generate in Flow. This clears the first blocker to commercial use (you're not distributing content Google owns).
- Google does **not** state, anywhere I found, an affirmative sentence of the form "you may use this content commercially" for the video/image side of Flow. The FAQ answers the commercial-use question entirely by pointing at the ownership disclaimer plus "consult the Terms in their entirety" — it does not add a positive grant beyond that.
- Also governing: the **Generative AI Prohibited Use Policy** (policies.google.com/terms/generative-ai/use-policy, Last Modified December 17, 2024), linked directly from two places in Flow's own FAQ (the "user policies" entry and the Ultra benefits page's "Protected categories" bullet). Its scope line: "The following restrictions apply to your interactions with generative AI in the Google products and services that refer to this policy" — Flow refers to it, so it binds. It lists prohibited categories (CSAM, violence, fraud, impersonation-to-deceive, etc.) and states: "We may make exceptions to these policies based on educational, documentary, scientific, or artistic considerations, or where harms are outweighed by substantial benefits to the public." Nothing in it addresses commercial use or monetization as a category.

**A notable asymmetry, on Google's own page, same day, same account tier:** the Google One "Use Google AI Ultra" benefits page (support.google.com/googleone/answer/16286513) lists benefits per product as bullet lists. Raw HTML fetched directly (not AI-summarized) shows:

- Under **"Use Google Flow"** (the video product): a description of modes (Text to video, Ingredients to video, Frames to video, Text to image, Image to image), a credits-management link, a safety-features note, and a link to the Prohibited Use Policy. **No "Commercial use rights" bullet anywhere in this section.**
- Under **"Use Google Flow Music"** (the separate Lyria product, different sign-in at flowmusic.app): "30,000 monthly credits... All core features... Member badge... **Commercial use rights.**" — listed as its own bullet, verbatim, immediately before the link to flowmusic.app/pricing.

Google chose to write "Commercial use rights" as a named, itemized benefit for one product in the Ultra bundle and did not write it for the other, on the same page. That is evidence of a real distinction Google is drawing, not proof of a video-side prohibition — but it means the silence on the video side is a deliberate omission, not an oversight, and should not be read as "same as Music, just unwritten."

**Verdict for §1:** Google will not claim ownership of your Flow video output, and nothing in the Prohibited Use Policy singles out commercial/monetized use as forbidden. But Google has not published an affirmative "commercial use permitted" statement for Flow video the way it explicitly did for Flow Music on the same benefits page. This is a real gap, not an inferred one.

### Attribution requirement
Searched: Flow help center, main ToS, Prohibited Use Policy. **Not stated anywhere** — no attribution requirement ("include a credit," "link back to Google," etc.) appears in any of the three documents governing Flow output.

---

## 2. The 30 built-in preset voices

**Recurring-character use is Google's own documented, intended use case — not merely tolerated.** From Flow's Voices help page (support.google.com/flow/answer/16353334):

> "To maintain a specific character's voice across multiple video clips, add a single-speaker voice reference to your prompt."
> — https://support.google.com/flow/answer/16353334?hl=en, read 2026-09-18 (also independently confirmed in `.claude/skills/google-flow-ops/SKILL.md`, measured on this account 2026-09-08)

No separate synthesized-speech commercial license, royalty term, or usage cap exists for the audio side. Flow has no audio-specific Terms of Service — voice output is governed by the identical documents as video output (§1's main ToS ownership clause + the Prohibited Use Policy). I checked the Voices help page, the Get Started FAQ, the main ToS, and the Prohibited Use Policy specifically for an audio/speech carve-out; none exists.

**The one restriction that does bear on synthetic voice, from the Prohibited Use Policy** (same document as §1):

> "Impersonating an individual (living or dead) without explicit disclosure, in order to deceive."
> "Misrepresenting the provenance of generated content by claiming it was created solely by a human, in order to deceive."
> — https://policies.google.com/terms/generative-ai/use-policy?hl=en, read 2026-09-18

Read plainly: this restricts using a synthetic voice to impersonate a **real, identifiable person** without disclosure, and restricts claiming AI output is human-made, both "in order to deceive." It does not restrict casting a preset voice as a **fictional recurring character** in a drama — that is squarely inside the feature Google documents above. There is no requirement here to label content as AI-generated for a fictional-character use case; the disclosure requirement is tied to impersonation-to-deceive and false-provenance claims specifically, not to synthetic voice use in general.

**Not stated:** any voice-specific commercial restriction, any cap on how many episodes/minutes a bound voice may appear in, any distinction between "voice for a background character" vs "voice for a recurring lead."

---

## 3. SynthID / watermarking

**Invisible watermark — always present, cannot be meaningfully removed.** From Flow's own "Manage your Google Flow projects, assets & collections" help page and the Get Started FAQ (both fetched directly, verbatim):

> "Videos generated in Google Flow include an invisible SynthID watermark. This watermark identifies the content as AI-generated and should not be tampered with or removed."
> — https://support.google.com/flow/answer/16935308?hl=en, read 2026-09-18

> "All outputs generated in Google Flow using Veo, Omni, or Nano Banana include invisible SynthID watermarks. SynthID identifies AI-generated content by embedding digital watermarks directly into AI-generated content."
> — https://support.google.com/flow/answer/16353333?hl=en, read 2026-09-18

**Visible watermark — optional for this account.** Same FAQ entry, continuing directly from the sentence above:

> "To further help you identify AI-generated content, a visible watermark can be added to generated images and videos. You can control this with the "Visible watermarking" toggle in the drop-down menu under your profile picture. A visible watermark will be applied automatically if you reside in India, South Korea, or Vietnam."
> — https://support.google.com/flow/answer/16353333?hl=en, read 2026-09-18

**Thailand is not on that forced-visible list.** For this account, the visible ✦-mark is a toggle, not a default. The invisible SynthID mark is always present regardless of the toggle, per Gemini's own verification page:

> "The digital watermarks are not visible to users." / "If a SynthID watermark is detected, it means all or part of the image or video was created or edited by Google's AI models." / "The digital watermark will usually still exist even if the image, video, or audio is re-scaled, re-colored, compressed or altered in other ways." [with the caveat that] "there's still a chance that after many alterations the watermark won't be detected."
> — https://support.google.com/gemini/answer/16722517?hl=en, read 2026-09-18

**Does watermarking affect distribution or monetization?** **Not stated anywhere official.** I checked: the Gemini SynthID verification page, both Flow help pages above, the Prohibited Use Policy, and the main ToS. None of them ties the watermark (visible or invisible) to any distribution restriction, platform eligibility, or monetization gate — SynthID is described purely as a provenance/detection mechanism ("should not be tampered with or removed," i.e., don't strip it), not as a licensing condition. Whether the destination platform (Facebook/Meta) imposes its own AI-content-disclosure or monetization rules is a separate question outside Google's terms and outside this task's scope.

---

## 4. Consumer Gemini/Ultra terms vs Cloud/Vertex terms — which governs this account

**They are different documents, and the difference is confirmed, not assumed.** The API-side document (ai.google.dev/gemini-api/terms, "Gemini API Additional Terms of Service") is explicitly a **separate** governing document from the consumer one, scoped to developers using AI Studio / the paid API, with its own data-handling split between "Unpaid Services" and "Paid Services." It is not what a consumer signs when using flow.google.com.

Separately, Google Cloud's **"Pre-GA Offerings Terms"** — the term a low-quality AI-search summary surfaced, claiming it "explicitly prohibits commercial use of preview products like Veo 3" — is a **Google Cloud Platform / Vertex AI concept only**, defined in Cloud's own Service Specific Terms (cloud.google.com/terms/service-terms) and covering features Cloud badges "Early Access," "Alpha," "Beta," "Preview," or "Experimental" within GCP/Vertex. It has no textual connection to the consumer Flow product; nothing on any Flow or Google One page references it, and Flow's own FAQ answers the commercial-use question (§1) without any such carve-out. **I could not verify that claim on any official page and am flagging it as unsupported** — it appears to be the search summarizer conflating a Cloud/Vertex enterprise term with a consumer product because both involve "Veo."

**One more document explicitly does NOT govern this account, and this matters because older forum answers still cite it:** the original **"Generative AI Additional Terms of Service"** (policies.google.com/terms/generative-ai, Last Modified August 9, 2023) states its own supersession, in its own text:

> "We updated the Google Terms of Service on May 22, 2024 to cover AI-related topics. As of that date, these Generative AI Additional Terms of Service no longer apply, unless you're a business partner with a signed agreement that references these terms."
> — https://policies.google.com/terms/generative-ai?hl=en, read 2026-09-18

**For a consumer Google AI Ultra subscriber using flow.google.com, the governing set is:**
1. The main **Google Terms of Service** (policies.google.com/terms, the post-May-2024 consolidated version) — §1's ownership clause.
2. The **Generative AI Prohibited Use Policy** (policies.google.com/terms/generative-ai/use-policy) — the content-category restrictions.

**Not governing this account:** the archived Generative AI Additional Terms (superseded), the Gemini API Additional Terms of Service (developer/API-scoped), and any Google Cloud / Vertex AI Service Specific Terms including Pre-GA Offerings Terms (enterprise/Cloud-scoped).

---

## Where I looked (so "not stated" is checkable)

| Question | Pages checked |
|---|---|
| Video commercial use | support.google.com/flow/answer/16353333 · policies.google.com/terms · policies.google.com/terms/generative-ai/use-policy · support.google.com/googleone/answer/16286513 (raw HTML, both Flow and Flow Music sections) · support.google.com/googleone/answer/14534406 |
| Voice / recurring character | support.google.com/flow/answer/16353334 · policies.google.com/terms/generative-ai/use-policy |
| SynthID / watermark | support.google.com/gemini/answer/16722517 · support.google.com/flow/answer/16935308 · support.google.com/flow/answer/16353333 |
| Consumer vs Cloud/Vertex | policies.google.com/terms/generative-ai (archived) · ai.google.dev/gemini-api/terms · cloud.google.com/terms/service-terms (Pre-GA Offerings Terms scope, via search — Cloud-only, confirmed not to reference Flow) |

---

## Verdict

**CONDITIONAL (no Google-stated prohibition on commercial use of Flow video or preset-voice audio was found — Google disclaims ownership of your output and the only binding restrictions are the Prohibited Use Policy's content categories — but Google has not published the same affirmative "commercial use rights" statement for Flow video/voice that it explicitly publishes for Flow Music on the same benefits page. Recommend written confirmation from Google before committing ad revenue to it, given that gap is Google's own choice of wording, not this research's limitation.)**
