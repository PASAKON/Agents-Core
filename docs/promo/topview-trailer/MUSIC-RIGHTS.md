# Flow Music soundtrack — rights check for TopView Wan3 Challenge + monetized YT/FB

Research only, read-only, nothing spent/signed-in/edited. Read 2026-09-26.
Account: pass.gob1, Google AI **Ultra** plan → Flow Music **Member** tier (confirmed live, see §3).

## Verdict

**(a) TopView Wan3 Challenge entry: YES, WITH CONDITIONS.**
**(b) Later use in monetised YouTube/Facebook videos: YES, WITH CONDITIONS.**

No Google document found prohibits commercial use of Flow Music output. Google
disclaims ownership of your generated tracks (§1) and its own support page
lists "Commercial use rights" as a named benefit of the Member tier the
pass.gob1 Ultra account is on (§3) — a stronger, more explicit statement than
exists for Flow *video* output (per our 2026-09-18 research file, which found
only silence, no equivalent phrase, on the video side).

## Conditions to meet

1. **Keep the generation record.** TopView: "The organizer may verify the
   creation process, Topview project, and material licenses of shortlisted
   entries" (`docs/promo/TOPVIEW-WAN3-RULES.md`, line 101, from the contest's
   own rules page). Keep the Flow Music session/project link and a
   screenshot/proof the account is Ultra→Member — that pairing is the actual
   licence evidence, since the commercial-use grant is tied to that tier
   specifically (only the Ultra/Member page was checked; Free/Starter/Plus
   were not independently verified to carry the same bullet — do not assume
   they do).
2. **Do not strip/tamper with the SynthID watermark** embedded in the audio.
   Confirmed first-party that Flow Music's model is watermarked (§2). The
   explicit instruction "should not be tampered with or removed" was found
   stated for Flow's sibling video product, not on a Flow-Music-specific
   page — treat as the same house rule, but note it is not verbatim-confirmed
   for audio.
3. **Stay inside the Generative AI Prohibited Use Policy's content
   categories** (fraud, non-consensual impersonation, deceptive
   human-provenance claims, etc.) — not a practical issue for an instrumental
   score, but it is the actual binding restriction, not commercial use per se.
4. **No attribution-to-Google requirement exists** in anything read — none
   needed on the video or the post.
5. **No Google-mandated "disclose as AI-generated" rule** applies to a
   non-deceptive use (the only disclosure duty in the Prohibited Use Policy is
   tied to impersonation/false-provenance-to-deceive, not to plain AI music
   use). TopView's own audio rule is just "must be licensed," which this
   satisfies. Whether YouTube's or Meta's *own* platform monetization/AI-label
   policies impose anything further is a separate question this task did not
   research — flagging the gap rather than guessing.

## Which terms actually apply — ProducerAI/Riffusion vs. Flow Music

`www.flowmusic.app/terms` and `/privacy` **301-redirect** to
`policies.google.com/terms` and `policies.google.com/privacy` (verified live,
`curl -L`, final URLs confirmed) — the same consolidated Google Terms of
Service that governs Flow video (per our 2026-09-18 research). **Flow Music
carries no separate ProducerAI/Riffusion-specific terms page today.**
ProducerAI (built on Riffusion, at producer.ai) was Google's earlier product
under this same DeepMind/Google Labs line; Google's own blog post announcing
it ("ProducerAI: Your music creation partner, now in Google Labs",
blog.google) is a *different, earlier* article from the one announcing
Lyria 3.5 in Flow Music (Jul 29 2026, same blog) — Flow Music is the current,
live product and the one this account uses; the ProducerAI post is cited
below only for its first-party SynthID sentence, not as governing law.

## Quotes with URLs

**§1 — Ownership (current, live-fetched from the actual ToS text):**
> "Some of our services allow you to generate original content. Google won't
> claim ownership over that content."
— https://policies.google.com/terms (fetched via flowmusic.app/terms redirect, 2026-09-26)

**§2 — SynthID / watermark, first-party, Lyria-specific:**
> "SynthID embeds a watermark into any audio generated or published through
> our AI music generation model Lyria or the podcast generation feature of
> Notebook LM. It's inaudible to the human ear, and can't be altered by common
> modifications like adding noise, MP3 compression, or changing the speed of
> the track."
— https://deepmind.google/models/synthid/ (Google DeepMind, read 2026-09-26)

Also first-party (Google's own blog, predecessor product, same watermark tech):
> "All outputs from ProducerAI are embedded with SynthID, our imperceptible
> watermark for identifying Google AI-generated content."
— https://blog.google/innovation-and-ai/models-and-research/google-labs/producerai

**§3 — Commercial use, tied to plan tier (support.google.com, live-fetched,
Google AI Ultra benefits page, the "Use Google Flow Music" section):**
> "Members of Google AI Ultra get the benefits of Google Flow Music's Member
> plan: 30,000 monthly credits (~6,000 songs) ... All core features. Member
> badge. ... Early access to new features. **Commercial use rights.**"
— https://support.google.com/googleone/answer/16286513?hl=en, read 2026-09-26

Note: the phrase "commercial use rights" does **not** appear anywhere in the
underlying `policies.google.com/terms` text itself (checked directly — the
only hit for "commercial" there is an unrelated glossary definition of
"business user"). It is Google's own characterization, on an official Help
Center benefits page, of what the Member tier grants — a real first-party
statement, but a support-page description rather than a contract clause.

**§4 — Prohibited Use Policy (binds Flow Music the same way it binds Flow
video — the flowmusic.app app bundle itself links directly to this exact
URL as its usage-policy reference, confirmed by inspecting the site's own
JS):**
> "Misrepresenting the provenance of generated content by claiming it was
> created solely by a human, in order to deceive."
— https://policies.google.com/terms/generative-ai/use-policy, read 2026-09-26

**§5 — TopView's own music rule** (`docs/promo/TOPVIEW-WAN3-RULES.md`):
> FAQ, verbatim: "Can I use music, images, or other third-party assets? Yes,
> but you must own the rights or have valid licenses—including for music,
> images, video, fonts, characters, trademarks, likenesses, and voices."
> Terms 7: "The entry must be original to the entrant, or the entrant must
> have obtained all necessary permissions for any music, images, video ...
> included in the work."

## What could not be checked / flagged, not guessed

- Whether Free/Starter/Plus Flow Music tiers also carry "Commercial use
  rights" was **not independently verified** — only the Ultra/Member page was
  read. Don't rely on that grant if the account tier changes.
- No Flow-Music-specific help page states "do not remove the watermark" in
  those words (that sentence was found only on Flow's video FAQ). Treated as
  the same policy by inference, not confirmed verbatim for audio.
- YouTube's and Meta's own AI-content-disclosure/monetization policies were
  not researched here — out of scope for this task, and a real open question
  before relying on Google's rights alone for monetized use.
