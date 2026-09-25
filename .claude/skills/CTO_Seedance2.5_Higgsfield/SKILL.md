---
name: CTO_Seedance2.5_Higgsfield
description: >-
  Everything measured about generating with Seedance on Higgsfield.ai: Seedance 2.5 (Unlimited and
  credit lanes), the 2.0 / 2.0 Fast / 2.0 Mini tiers, and Higgsfield's image models for plates. The
  money rules (never Rerun, read the struck-through price, one click on a paid control, Usage History
  after any error), Confirm Rights, the one-at-a-time Unlimited slot, the desktop-width lock, the
  Lexical prompt box and the duration slider, Elements and @Image1 references, a previz attached as
  @Video 1, what the face/copyright scanner kills, reference caps, model tiers and cost per second,
  the review loop, render-wait and wave rules for operators, and the «Sorry, Sir» A/B ledger
  (AB-LEDGER.md). Trigger on "Higgsfield", "Seedance", "Unlimited mode", "AI video generation
  credits", "jump-cut pass", "Confirm Rights", "ยิง Seedance", "ยิง Higgsfield", a Higgsfield History
  Recreate or Rerun button and /CTO_Seedance2.5_Higgsfield. Do NOT fire for Google Flow
  (CTO_Flow_Omni1.1_Ops, CTO_Flow_Omni1.1_Continuity, CTO_Flow_Omni1.1_FilmQC), MiniMax H3
  (CTO_MiniMax_H3), Wan 3.0 on TopView (CTO_Wan3.0_TopView), fal.ai, Kling or Veo; how a
  multi-shot film is run is CTO_Film_Production and how a prompt file is laid out is
  CTO_Film_PromptFormat.
created_by: agent
author: {role: developer, date: "2026-09-25"}
audience: [cto, cmo, cfo, cgo, browser_operator]
---

# Seedance 2.5 on Higgsfield

Measured on higgsfield.ai, 2026-08-12 → 2026-09-11: the Valder waves, «Sorry, Sir» (The Valder
Collection No.7) and «Do Not Disturb», on Seedance 2.5 (Unlimited and credit lanes), the 2.0 /
2.0 Fast / 2.0 Mini tiers, and Higgsfield's image models for plates. Every rule below was learned
from a real incident in this org, not written speculatively.

Only what was measured on Seedance or Higgsfield lives here. How a multi-shot film is run (story
gate, CAST.md, plates, re-shoot on change, tolerance, prose against reference, prohibitions,
judging by eye, the continuity check, what the director decides, the A/B entry, workers and money)
is `CTO_Film_Production`; how a prompt file is laid out is `CTO_Film_PromptFormat`. Follow
`browser-operator`'s general discipline (text-first, zoom over screenshots, replay scripts) and
`dev-spawn-protocol`'s spawn steps first — this skill adds the Higgsfield layer on top. The
«Sorry, Sir» A/B ledger lives beside this file: `AB-LEDGER.md`.

What it gives a C-level (CTO, CMO, CFO, CGO) driving or delegating Higgsfield video generation:
the exact button-level rules, editor gotchas, and wait pattern that prevent (a) accidentally
spending real credits when the task must run Unlimited-only, and (b) a spawned worker silently
dying during a long render wait.

## When to invoke

- Before delegating any `browser_operator` task whose target is `higgsfield.ai`.
- Before writing a task brief that mentions Seedance, Unlimited Mode, jump-cut generation, or a
  "Recreate"/"Rerun" History card.
- Before a C-level personally drives Higgsfield in Chrome for any reason.
- When continuing/resuming a multi-wave Higgsfield generation job started in a prior session.

## When NOT to invoke

- Video/image generation on any other platform (fal.ai, Kling, Veo, MeiGen, Nano Banana) — those
  aren't Higgsfield and don't share these UI traps. Google Flow is `CTO_Flow_Omni1.1_Ops`, MiniMax
  H3 is `CTO_MiniMax_H3`, Wan 3.0 on TopView is `CTO_Wan3.0_TopView`. Do not assume a rule here
  holds there.
- Higgsfield work that is explicitly credit-based/paid by design (not this org's normal mode) — if
  a task genuinely intends to spend credits, that's an `feedback_ask_before_paid_api` conversation
  with the CEO, not this skill.

## The incidents this is built from

**Incident 1 — Rerun auto-fire.** A DEV clicked **"Rerun"** on a History card, intending only to
load its references into the composer for editing. Rerun does two things at once with **zero
confirmation step**: loads the prompt into the composer, AND immediately fires a new generation of
the unmodified original prompt — at whatever pricing is currently showing, completely independent
of the Generate button or the Unlimited Mode toggle. It cost **130 real credits**, confirmed via
Higgsfield's own Usage History log (Account Settings → Usage): one entry that day read
`130 credits · Seedance 2.5 · Spent`, every other entry that day read
`Unlimited Seedance 2.5 · Spent` ($0). Reference: mooniex-agents task-eed61860, GH issue #45.

**Incident 2 — keystroke-type timeout auto-fired a paid generation with no click at all.** A DEV
entered a long multi-paragraph prompt (with blank lines between paragraphs) using a
keystroke-simulating "type" action instead of the mandated synthetic-paste technique (see Editor
gotchas). The type call errored out (`CDP sendCommand Input.dispatchKeyEvent timed out after
30000ms`). No Generate click ever happened — but when the DEV checked the page immediately after
the timeout, a generation was already in flight: Unlimited toggle already reset to OFF (from an
earlier page reload, as documented below), Generate button already reading a credit number,
spinner card already active. Best-available explanation at the time: a stray Enter/keydown leaked
out of the failed keystroke dispatch queue, and the composer treats Enter-in-composer as submit.
Cost **1 real credit**, auto-refunded by Higgsfield the same minute (`1 credit · Seedream 4.5 ·
Spent` then `+1 credit · Seedream 4.5 · Refunded`, both timestamped same minute — net $0, but a
real paid generation fired with zero deliberate action to gate against it, which the existing hard
rules did not anticipate).

**Root cause, confirmed** (superseding the original stray-Enter hypothesis): `type()` truncated the
prompt to its first sentence in three separate generations that session (8:03 PM, 8:05 PM, and
again at 9:16 PM even after switching to a shorter prompt) — confirmed each time by reading the
generated card's own Info/Prompt panel, which showed only the opening line, not the full character
description. The mechanism is `type()` itself, not a downstream Enter/submit side effect: a
keystroke-simulating type action against this Lexical editor is not reliable for multi-paragraph
text, full stop. **Validated fix**: switch to synthetic `ClipboardEvent` paste only (see hard rule
6) — confirmed clean in the same session (source 781 chars; three independent reads at
790/787/775, correct first/last 80 chars, no truncation). Reference: mooniex-agents task-7b4402d4.

## Rule 00 — FESTIVAL COMPETITION: PLATFORM-ONLY GENERATION

For any festival/competition project (both films are), **every image and every video asset must
be GENERATED on Higgsfield itself.** Externally created or externally edited pictures are not
eligible and may not be uploaded as Elements or used as final assets. (CEO, 2026-08-30, from the
festival rules.)

⚠️ **THIS BANS EXTERNAL GENERATION, NOT EXTERNAL POST-PRODUCTION. Do not read it as "no editing
outside Higgsfield" — that reading would stop you grading the film, and the rules explicitly allow
it.** Checked against the verbatim rules pulled 2026-09-09
(`docs/reports/higgsfield-festival-rules-20260909.md`, Official Rules §4):

> "External editing rules. External tools may be used for cutting and assembly, **color grading**,
> precise mask-based retouching, titles, transitions, compositing, and traditional (non-AI) 3D and
> animation."

> "Traditional (non-AI) tools are allowed … such as Blender, After Effects, **DaVinci Resolve**,
> Premiere, Photoshop, and similar — may be used freely at any stage of your film, **provided they
> are not used to generate new AI imagery.** Content produced in these tools counts as your own
> hand-made work."

So: **the cut, the grade, titles, masks and compositing are all fine outside the platform.** The
line is GENERATION. What Rule 00 actually forbids is laundering outside work back INTO a
generation — hand-building or retouching a plate and uploading it as an Element, which is what the
two deleted plaque walls were. Grading a finished clip is not that.

**Practical edge inside an allowed tool:** DaVinci Resolve ships AI features. Anything that
*invents pixels* (generative fill, detail-hallucinating upscale) is AI image generation happening
off-platform and is not allowed.

**And the question does not arise in the free version anyway — verified 2026-09-11.** Magic Mask,
AI Object Removal, Super Scale and IntelliTrack are all **Studio-only ($295)**. The free build has
no Neural Engine. So a free Resolve user physically cannot cross that line, which makes the free
tier the *safer* choice for a festival entry, not a compromise.

**What the free build DOES have, and it is the part that matters: the whole Fusion page** — a full
node-based compositor with paint, planar tracking and rotoscoping. Manual roto-and-patch is
unambiguously legal: the rules name "precise mask-based retouching" and state that "content
produced in these tools counts as your own hand-made work".

**The technique that makes this cheap on THIS film: most of our shots are locked off.** On a locked
frame you do not need tracking at all — lift a clean patch from another frame of the same clip and
hold it over whatever you are removing. Removing a stray figure or moving an object on a locked
shot is minutes of compositing, against ~100 credits and a dice-roll for a re-fire.

Practical consequences, learned the expensive way the same night:
- Hand-building or retouching a plate locally (PIL, Photoshop, anything) and uploading it is
  DISQUALIFYING — even when it is faster or more precise. Two hand-built price-plaque walls were
  built, uploaded, and had to be deleted on the CEO's order minutes later. (It happened again on
  2026-09-10 with a PIL-composed $100,000,000 plaque: AB-LEDGER 04:50.)
- The compliant route for a variant of an existing frame is an ON-PLATFORM image generation: bind
  the existing Element and prompt the change in, then zoom the output to verify (mirrored digits
  especially).
- External images may exist only as private reference for humans reading the docs — never
  uploaded, never bound, never in a deliverable.

Festival ruling (CEO 2026-08-30): Blender/AE are editing-class tools — a camera previz used as
`@Video 1` is allowed; generation still happens on Higgsfield.

## Rule 0 — GENERATE ONLY IN THE PROJECT THE CTO NAMED

Before every single Generate click, image or video, **check the address bar** and confirm you are
in the project the task brief named. A fresh tab does not inherit it, and neither does a tab
someone else opened.

Current mapping (CEO, 2026-08-30):

| Film | Project URL |
|---|---|
| **«Sorry, Sir» / The Valder Collection No.7** | `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` |
| **«Do Not Disturb» (DND)** | `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival` |

The two URLs differ by one character. Read the whole path, not the prefix.

**Why this cannot be caught downstream:** Elements are account-wide, so a clip fired in the wrong
project binds the right characters, the right room and the right props, and comes back looking
completely correct. Reviewing the footage will never reveal it. The URL is the only tell, and the
cost is discovering weeks later that a film's material is scattered across two projects.

Measured 2026-08-29/30: the three original «Sorry, Sir» task briefs carried the project URL; every
brief written after them dropped it. The early waves survived only because a browser tab happened
to be sitting in the right project already. The moment an operator opened its own tab,
generations began landing outside the film's project and nobody noticed until the CEO checked.

**So: the project URL belongs in every task brief, and the operator re-reads the address bar before
every fire.** If a brief does not name a project, stop and ask the C-level which one — do not guess
from what is already open.

## Hard rules — tiered (ADR 0022 §7 pass, 2026-09-02)

Every rule below is tagged **HARD** and carries a **`Why hard:`** clause per the ADR 0022 §7
contract — a rule block is either HARD-with-a-reason, or it is advice the model may override (and
says why when it does). Every rule in this section traces to a real credit loss or an
unrecoverable wrong-footage incident, so none of it is softened to make a doctrine point: money and
irreversibility are exactly the two carve-outs the ADR keeps binding.

[SUPERSEDED 2026-09-02] the old wording of rule 2, "confirm the Generate button reads bare
'Generate' with ZERO digits anywhere on it": a correctly working Unlimited *video* generation
legitimately shows digits, struck through (`Unlimited · ~~140~~ · 0`), as the Valder wave had
already documented (2026-08-19). An operator handed only the old rule would stop dead on a correct
button. Rule 2 now states the one table that governs both surfaces — VIDEO generate check, IMAGE
generate check — and it is the only place that table lives.

1. **HARD — Never click "Rerun"** (↻ icon, bottom-left row on a History/generation card). Banned
   entirely on every Higgsfield task, forever. Use **"Recreate"** instead (copy icon, top-right of
   the video thumbnail, appears on hover — confirm via its tooltip text before clicking) to load a
   card's prompt + references into the composer for editing; Recreate does NOT fire anything by
   itself.

   **Why hard:** money. Rerun auto-fires a generation with zero confirmation step, independent of
   Unlimited Mode's on/off state. Confirmed 130-credit charge, mooniex-agents task-eed61860, GH #45
   (Incident 1).

2. **HARD — Before every single Generate click, read the button's price signal correctly. A wrong
   reading is real money, and there is no undo after the click.**

   | Surface | Button reads | Meaning | Action |
   |---|---|---|---|
   | Seedance 2.5 VIDEO, Unlimited working | struck-through price then `0` (e.g. `Unlimited · ~~140~~ · 0`) | Unlimited applied | Click |
   | Seedance 2.5 VIDEO | bare `Generate`, no price shown at all | fine | Click |
   | Seedance 2.5 VIDEO | a live price, **no strike-through** | Unlimited is OFF | **STOP** — message the C-level |
   | GPT Image 2 (any plate) | a small live number, ~0.2–3 credits at 1K/Medium, no strike | normal — GPT Image 2 is metered on PLUS (plan exceptions: "What Unlimited covers") | Click, within the credit budget the brief gave you |
   | GPT Image 2 | an "Unlimited mode" control shown beside it | that is a $30 paid upsell, not our subscription | **Never click it** |

   **The struck-through number is not a fixed value and you should not expect 140.** It varies with
   the clip's length and quality settings — 137, 140, whatever that particular job would have cost.
   Do not stop because the number is unfamiliar. **Read exactly two things: is the price struck
   through, and is there a `0` after it.** Those two together mean Unlimited is applied and the
   click is free. (CEO, 2026-09-02.)

   The distinction that matters is **the strike-through, not the presence of digits.** A brief that
   says "zero digits anywhere" will stop a correct operator dead; one that says "any number means
   stop" is worse, because it trains the operator to ignore the real signal. Write the table. The
   Unlimited Mode toggle's apparent on/off state is **not sufficient on its own** — it silently
   resets to OFF after any full-page reload.

   ⚠️ **A JS TEXT-SCRAPE OF THE GENERATE BUTTON IS NOT A SUBSTITUTE FOR THE ZOOM, AND CAN BE FLATLY
   WRONG.** Measured 2026-08-28:
   `[...document.querySelectorAll('button')].find(b=>/generate/i.test(b.innerText))` matched a
   **stale duplicate button** reading `GENERATE8045` — struck 80, **live 45** — in the same second
   that a zoomed screenshot of the real, visible button clearly read `UNLIMITED / struck 60 / 0`.
   Same decoy-duplicate-element family as the prompt editor: **more than one element matches a
   loose text selector on this composer at any moment.**

   An operator trusting the scrape in the other direction — decoy says `0`, real button says `45` —
   fires a paid generation believing it is free.

   **Why hard:** money. Read the number off the pixels, never off the DOM — the zoom is
   load-bearing, not a formality, and there is no way to un-fire a generation once the click lands.

3. **HARD — "Rights verification required" banner: click Confirm Rights, every time. Do not
   escalate, do not ask, do not hold the clip.** Standing CEO approval, 2026-08-28. A finished card
   sometimes carries this banner and will not download until it is confirmed.

   This is not a legal risk transfer and not the CEO's signature on anything — the banner asks
   whether we own the content, and we do: we wrote the prompt, and the clip is generated from it.
   His words: *"กดเองได้เลย… เพราะเราเป็นคนสร้าง Promt คุณก็เขียนขึ้นมาเอง."* The flag comes from
   the same automated Face/IP scanner described under "The face and copyright scanner" below — it
   fires on *resemblance*, not infringement, and rescans retroactively, so a clip that passed an
   hour ago can be flagged now. Confirming states the true thing: nothing here was copied from
   anyone.

   **What this does NOT authorise:** buying anything, renewing a plan, accepting new terms of
   service, or any other consent dialogue. Those all still stop and go to the C-level. This
   approval covers only the rights banner on generated clips in this project.

   **Why hard:** the scope of what is and isn't authorised here is CEO-bounded and must not be
   widened by inference — an operator that once correctly refused a relayed (not written) version
   of this same approval was right to refuse it, which is exactly why the boundary is written here
   instead of passed down verbally.

4. **HARD — One Unlimited VIDEO generation at a time; never force through a stuck concurrency
   toast.** Wait for full completion (card shows Recreate+Rerun options and full
   resolution/duration/aspect-ratio metadata, no "Processing"/"Generating" state) before starting
   the next video. If Higgsfield shows a "1 unlimited generation at a time" toast and nothing in
   your own History is generating, don't force through it or guess a workaround — message the
   C-level and wait.

   ⚠️ **"Unlimited is free, so there is no urgency to cancel a long render" is wrong, and it was
   reasoned out loud by an operator on 2026-09-05 while a clip sat at 93 minutes.** Money is not
   the cost being paid. The slot is serial and account-wide, so one over-long render blocks *every*
   clip behind it — that operator had the next clip fully staged and could not fire it. A 90-minute
   render against a 35-40 minute norm has already cost an hour of queue whether or not it ever
   completes.

   So the threshold is about the QUEUE, not the bill. Past it, decide deliberately: cancel and
   re-fire, or keep waiting because this specific clip is worth the block — and say which, and
   why, in your status line. What is not acceptable is waiting by default because it is free.

   And know what killing things does NOT do: **a generation survives the death of the agent that
   started it.** Killing the worker does not cancel the render or free the slot. Only cancelling it
   in the browser does, which means only the operator holding that tab can unblock the queue — a
   C-level cannot do it from outside, and reaping the worker just loses the staged next clip.

   **A paid GPT Image 2 generation does NOT contend for that slot**, and holding image work behind
   a rendering video wastes hours. Measured 2026-08-28 on the «Sorry, Sir» wave: Scene 2 fired as
   an Unlimited Seedance video at 05:50 and was still rendering at 06:30, and during that window
   **two separate operators each fired and completed a paid image plate** — `char_grandmother`
   (asset `5dd23a87`) and `char_gentleman`. Neither saw a concurrency toast. The slot is scoped to
   **unlimited** generations only; paid ones queue independently. **Video work serialises; image
   work runs alongside it.** Verify once, then run both lanes in parallel: standing an image
   operator down "until the video clears" cost forty minutes of two workers.

   **What actually causes a toast with nothing visibly running** (measured 2026-08-12,
   task-cda4f469): the slot is **account-wide, not project-wide**, and a generation survives the
   death of the agent that started it. Killing a DEV does not cancel its in-flight render — that
   job keeps running server-side and holds the slot until it finishes on its own, roughly 20
   minutes for a 20-second Seedance clip. Two read-only checks resolve it: look at the
   account-level generations feed (not just the current project's History — a job in any other
   project holds the same slot and is invisible from inside one project), and check the most
   recent Usage entry's timestamp — under ~20 minutes old is the holder; wait it out. The toast
   itself costs nothing, confirmed.

   **Why hard:** money, by the same path as rule 5 below — guessing a workaround around a stuck
   slot means clicking near a live, potentially priced composer, and that is exactly the pattern
   that cost $10.80 in a real incident.

5. **HARD — If the Unlimited toggle won't respond, stop after the FIRST clean attempt. Do not
   escalate through more click techniques.** Real incident, 2026-08-14 (task-f693a4ee, GH #67): the
   toggle was stuck off, so the Generate button stayed priced (`Generate180135`) for the whole
   session. The operator never intended to click it and correctly never clicked it on purpose — but
   while troubleshooting the toggle it tried seven different techniques in succession (ref click,
   raw-coordinate click, keyboard focus+Space+Enter, click-drag, hover, double-click, zoom+click),
   and **two real 135-credit charges landed anyway**, $10.80 total, most likely because one of
   those techniques — probably the keyboard Enter press — landed on the adjacent Generate button
   instead of the switch (the two sit 40–50px apart).

   **The fix:** one ref-based click attempt on the exact toggle element via `find()`. If
   `data-state` doesn't flip, **stop entirely and message the C-level** — do not try a second
   technique, do not try raw coordinates, do not try keyboard input near the composer.

   **Standing escalation policy, CEO-set 2026-08-14: any control an operator cannot reliably click
   goes to the CTO, not back into more operator retries.** The CTO asks the CEO to fix it by hand in
   the real Chrome window. The operator's job at that point is to **leave the browser open exactly
   as it is** — no navigate, no refresh, no retry, no close — and report the composer's exact
   current state (text present, element chips attached, toggle state).

   ⚠️ **SCOPE OF THAT POLICY — corrected 2026-09-06 after it cost six hours.** The "no refresh, no
   retry" rule exists because retrying near a composer whose price is NOT verified can land a
   charge. It applies to a stuck *toggle* and to any composer showing a live number. **It does NOT
   apply to a Generate button that is `disabled` while the price reads struck-through zero** —
   there is nothing to accidentally spend, and a `disabled` attribute is a *diagnostic*, not a
   hazard. On 2026-09-06 an operator found exactly that (`disabled=""`, `credits: 0`, price
   `~~84~~ → 0`), cited this rule, left the tab untouched, and reported an account-level blocker.
   The CTO accepted it. Nobody reloaded the page. The queue sat idle for six hours with the film
   three days from due. The very first thing the next operator did was reload, and it proceeded to
   fire.

   **For a `disabled` button at a verified $0 price the order is:** reload the tab → read the four
   values again (`disabled`, `isDisabled`, `freeGens`, `credits`) → if still disabled, open a FRESH
   tab on the same URL and read them a third time → only then report it as account-level, with all
   three readings. Never restart Chrome (CEO rule). A blocker report that does not show the reload
   and the fresh-tab readings is not finished, and the CTO should send it back rather than escalate
   it. **The CEO clicks Generate himself in this scenario, not the operator** — the final
   money-committing click moves to a human hand whenever the automated path has already failed
   once. This generalizes past the Unlimited toggle to any stuck control on a priced surface.

   **Once the CEO has fixed the toggle by hand, that composer tab becomes protected — proceed on
   it, but never navigate it away, refresh it, or close it, for the rest of the session.** A page
   reload silently resets Unlimited back to off, so leaving this exact tab would force the CEO to
   walk over and click it by hand a second time. Need to check Usage, History, or anything else
   mid-queue? **Open a separate tab for that** and leave the composer tab exactly as the CEO left
   it.

   **Why hard:** money. Every additional click technique tried near a priced Generate button is
   itself a money risk, independent of what you're aiming at — confirmed twice in the reference
   incident.

6. **HARD — Never enter prompt text with a keystroke-simulating "type" action. Synthetic-paste
   only.** Confirmed 3-for-3 failure rate in one session (task-7b4402d4, Incident 2): every
   `type()`-entered multi-paragraph prompt silently truncated to a fragment, which then got
   submitted as a real generation with wrong subject matter. Use `ClipboardEvent` paste **only**,
   every prompt, no exceptions, especially prompts with blank lines between paragraphs (most of
   ours).

   **Why hard:** money, and silently. A truncated prompt does not fail — it fires a real, paid
   generation of the wrong thing, and the operator only finds out after the credits are gone. 3 for
   3 in one session.
   - **Do NOT also dispatch a synthetic `input` event after the paste.** Tested and confirmed
     harmful: Lexical's own paste handler already inserts the text, and a follow-up synthetic
     `input` event causes a **second** insertion — the text appears duplicated in the editor. Paste
     alone is sufficient and binds correctly to the framework's real state.
   - **FIRST pick the right node — there is a decoy editor.** Measured 2026-08-12 (task-cda4f469):
     the composer renders **two overlapping `contenteditable` elements**, and a paste aimed at the
     wrong one lands silently with no error and no visible text. The reliable tell is
     **`getComputedStyle(el).visibility === 'hidden'` on the decoy**. Nothing cheaper works:
     bounding rect, offset position, and the presence of `__lexicalTextContent` are **identical on
     both nodes**, so every naive "find the contenteditable" selector has a coin-flip chance of
     hitting the dead one. Filter candidates by computed visibility before touching anything.

     This very likely explains the earlier incident where a card's saved prompt contained only its
     first line — at the time it was blamed on keystroke truncation. Treat a mysteriously empty or
     partial saved prompt as decoy-editor first, `type()` second.
   - **DURATION IS NOT A TEXT FIELD AT ALL — IT IS A RADIX ARIA SLIDER. Never type into it.**
     Measured 2026-08-28 on the «Sorry, Sir» wave, at a cost of four unusable clips and four wrong
     diagnoses.

     The signature that something was wrong: **two fixed output values, no error anywhere.**

     | Clip | Target | Actual |
     |---|---|---|
     | S2, S3 | 20s | **20.04s** |
     | S4, S9, S17, S18 | 15 / 20 / 25s | **11.04s every time** |

     DOM inspection settled it. The control is `role="slider"` · `aria-valuemin="4"` ·
     `aria-valuemax="30"` · `aria-valuenow` · `tabindex="0"`, and the visible "20s" is a
     **read-only `<span>` beside it**. Typing was never landing anywhere real — and the `4s` that
     kept reading back was simply `aria-valuemin`, the slider sitting at its floor.

     **The method that works, confirmed exact:** click the slider thumb once to focus it, then send
     **`ArrowRight` once per second** from the current `aria-valuenow`. 16 presses took it cleanly
     from 4 → 20, verified by `aria-valuenow="20"` and the visible label agreeing.

     **Four theories were burned before anyone inspected the DOM**, and every one of them was
     plausible: a stale composer tab (a fresh tab reproduced it on the first attempt), a lapsed
     Unlimited entitlement (plan active, usage log all `Unlimited` with no digits), a platform-side
     duration cap, and — mine — that the duration box had the same decoy-contenteditable structure
     as the prompt editor. It does not: the page holds only **two** such nodes, the prompt editor's
     own real+decoy pair, and neither is anywhere near the duration popover.

     **Inspect the control before theorising about the value.** One DOM query would have replaced
     four hours of hypotheses.
   - **Verify via three independent reads before every Generate click**: `element.innerText`,
     `element.__lexicalTextContent` (or equivalent Lexical-exposed text property), and — the
     authoritative one — `editor.getEditorState().toJSON()` if you can reach the editor instance.
     **These three do not save you from the decoy** — run them on the decoy and they agree with
     each other perfectly, on empty content. They only mean something once the visibility check
     above has selected the real node. Compare all three against the source prompt's length and
     first/last ~60-80 characters. `innerText` alone is not enough — it can show complete text
     while the framework's real bound state (what actually gets serialized into the Generate API
     call) is empty or truncated. This is the actual mechanism behind Incident 2, not a stray-Enter
     theory (that was an earlier, superseded hypothesis).

7. **HARD — Any browser-tool error or timeout while on a Higgsfield generation page — of any kind,
   not just during text entry — means your next action is checking Usage History, before anything
   else.** A timeout does not mean nothing happened; the underlying page action may have partially
   or fully completed regardless of what the tool call reported back. Don't assume a failed call =
   no side effect.

   **Why hard:** money. Usage History is the only ground truth for whether a charge landed — a
   failed tool call is not evidence either way, and skipping this check is how a real charge goes
   unnoticed.

## HARD · Paid controls: one click, never a retry (2026-09-06)

The "$0 button: JS `.click()` fallback / retry if no toast after 5 s" guidance is for the UNLIMITED
VIDEO button only. On 2026-09-06 an operator applied it to the paid image composer — no toast after
5 s, clicked again — and FOUR images fired (~3 credits unplanned). Image generations show nothing
for longer than 5 s.

- Anything priced above a struck-through zero: ONE click. Then wait 60 s, reload, count the asset
  grid (or watch the network POST). No second click without a count that says nothing fired.
- Disclose every unplanned credit to the CEO with the exact number.
- Rejected extra images stay in the project — no delete authority.

## HARD · Desktop width before every state-changing action

### Maximise the window before every Generate click — root cause found by the CEO 2026-09-06

**A "disabled" Generate button with `freeGens: undefined` is the signature of Higgsfield's MOBILE
LAYOUT, and the mobile layout is what you get when the viewport is too narrow. The cause was our
own window size, not the account.**

What happened: a worker shrank the window (the `browser-operator` skill teaches resizing to
1024x768 or smaller to cut screenshot tokens). Below Higgsfield's desktop breakpoint the composer
re-renders as the mobile version, in which Unlimited does not exist — so React reports
`freeGens: undefined`, `credits: 0`, the button carries `disabled=""`, and the price can still
*display* as a struck-through zero from stale state. The operator read that as an account gate.
The CTO accepted it and parked the queue for six hours, three days from the film's deadline, and
wrote two wrong hypotheses (subscription lapsed / credits gate the button) into this skill. **Both
were wrong.** The CEO restored the window to full size and the button worked immediately.

**The rule, and it is HARD:**

1. **Before every Generate click, maximise the window** — or resize to at least 1280 wide — **and
   verify it took:**
   ```js
   ({w: window.innerWidth, h: window.innerHeight})   // w must be >= 1280
   ```
   `resize_window` has returned success without changing anything before (2026-08-27); the JS
   readback is the only proof.
2. **Then verify the desktop composer is actually present:** the Unlimited toggle exists, the price
   reads struck-through zero, and the Generate button has **no** `disabled` attribute. If any of the
   three is missing at >= 1280 wide, open a fresh tab at that width and check again.
3. **`disabled` + `freeGens: undefined` = check `innerWidth` FIRST.** Do not reason about credits or
   subscriptions until the window is proven wide and the symptom survives. Ninety-nine times in a
   hundred it will not survive.
4. **Shrinking the viewport for cheap screenshots is still fine — for reading.** Restore desktop
   width before any state-changing action on this site: toggling Unlimited, attaching a reference,
   and above all clicking Generate.

### The window can shrink on its own; `resize_window` can lie (2026-09-06)

Twice in one session the window fell below 1280 during reference-panel work with no resize call,
and `resize_window(1600,1000)` returned success while `window.innerWidth` read 764. Below 1280 the
composer is the mobile lockup ("Mobile Access Coming Soon"). Recovery that worked both times: close
the tab, open a fresh one, read `window.innerWidth` back. The tool's return value proves nothing —
only the readback counts, before every Generate.

**A tab whose viewport has collapsed to a stuck mobile layout cannot be repaired — open a fresh
tab.** Measured 2026-08-27 (task-f4305098, a 728x420 layout): `resize_window` returned success and
changed nothing, so the operator had no error to react to; the page kept rendering the mobile
composer, where several controls do not exist at all. Seen again on 2026-09-10 as a ~126×67
"MOBILE ACCESS COMING SOON" collapse, twice, on two fresh tabs (AB-LEDGER 17:10); the worker
recovered each time with a fresh tab, never a resize.

[SUPERSEDED 2026-09-06] the 2026-08-27 "728x420 mobile layout" note described the symptom
correctly and the cause not at all: the cause is the window width (above).

## HARD · The Unlimited toggle can be COVERED — a click that "does not flip it" landed on the cover (CEO 2026-09-06)

**The cover has a name (CEO 2026-09-06 12:15): the banner "Credits are running low! Over 90%
already used".** It is an UPSELL, not a fault: Higgsfield shows it whenever the account's paid
credits are more than 90% used, on EVERY new tab and EVERY reload, and keeps showing it until the
billing cycle resets or the CEO tops up (CEO 2026-09-06). It sits over the toggle/price area and is
what three workers were clicking on. FIRST ACTION in the composer, on every tab and after every
reload, before Unlimited, before pasting: close that banner with its own (x). Closing it is safe
and wanted. Never act on its message — Unlimited video spends no credits, so it is never a blocker
and never a reason to report "credits".

Three workers in one day reported "clicked the Unlimited toggle once, it did not flip". The CEO,
watching the screen, saw the cause: a toast (or the reference panel, an upload tile, a modal) was
sitting over the toggle, and the click hit the cover. Before calling the toggle broken:

1. Screenshot and look at what is over it; `document.elementFromPoint(x, y)` at the toggle's centre
   names the element on top.
2. Close the cover by ITS OWN close control (the toast's X, the panel's collapse). Never click
   "somewhere else" to dismiss it — a stray click selects an asset card and collapses the composer
   (seen 12:20 today).
3. If the cover is fixed, click the toggle's real input/button element via `javascript_tool`, then
   verify by the price readback: struck price + 0.

A reload also clears a toast but resets Unlimited to off — re-toggle after.

### Treat "Unlimited is broken" from an operator as unconfirmed

One operator reported the toggle stuck in both its original tab and a fresh tab, which triggered a
switch to paid generation. The CEO checked personally minutes later: the account was fine the
whole time. It was client-side state in that operator's browser.

Before accepting a broken-toggle report and changing the cost model, get a human to confirm on the
real screen. The recovery ladder stays: one ref click → one fresh tab → stop and escalate. But
escalate as "this operator cannot flip it", never as "the account is broken".

## What Unlimited covers, and what a fire costs

**Read the button (hard rule 2), never a remembered number or a remembered plan.** Three readings,
in date order; the later one wins where they disagree.

### 2026-08-27 — the CEO: "เรา Unlimited แค่ 2.5 Seedance"

Our Unlimited applied to Seedance 2.5 and nothing else, and it had an end date he had already
given. **GPT Image 2 was NOT Unlimited and never was** (the plan then was PLUS).

This skill once claimed the opposite ("Unlimited covers IMAGES too — corrected 2026-08-19… do not
tell an operator to expect a charge on plates"). **That was wrong and it cost real time.** On
2026-08-27 an operator read it, went looking for an Unlimited toggle beside GPT Image 2, found the
paid *upsell* control that sits there, saw it open a $30 purchase page, and correctly refused to
buy — then stalled for eight minutes filing a blocker against a system that was working perfectly.
The whole detour came from the skill.

Two consequences an operator must internalise:

- **On a VIDEO generate, any live number at all means STOP.** The only safe reading is
  struck-through-then-zero.
- **On an IMAGE generate, a small live number is CORRECT, not a fault.** About 3 credits (~3 at
  2K/Medium, ~2 at 1K/Medium) is what a GPT Image 2 plate cost and what every plate in «Sorry, Sir»
  cost. An operator that halts on it is halting on normal operation.

[SUPERSEDED] the 2026-08-27 heading "IMAGES ALWAYS COST CREDITS": Kling O1 images are free with
their own Unlimited toggle (2026-09-07), and on Ultra Annual GPT Image is 365-day unlimited
(2026-09-13). It still holds for GPT Image 2 on PLUS. Check which plan is live before reasoning
about an image price.

### 2026-09-07 — free IMAGE plates on Kling O1 (proven, tasks bc7f8d5d / 63fc0684)

- Image tab → model **Kling O1** (Image) → switch its **Unlimited toggle** on → the Generate button
  reads bare `UNLIMITED`, no digits. Credits 513 → 513 after the click; the account's "Free
  generations in total" counter ticks up instead.
- The **UNLIMITED badge on a model card is not the toggle.** GPT Image 2 carried the badge and still
  showed a 6.5-credit price on the button. Zoom the button; digits = paid = STOP.
- Higgsfield Soul Cinema shows a "free generations" counter (4,995 seen) — also $0, but Kling O1 is
  the recipe that has been run twice. (Soul takes no references: "Image plates" below.)

### 2026-09-13 — what the plan page actually says

Read off `higgsfield.ai/pricing` in a logged-in browser (the page is JS-rendered — WebFetch returns
metadata only, so this cannot be checked from a VPS):

**Seedance is NOT in the unlimited list of ANY published plan.** It sits in its own card,
`ACCESS TO SEEDANCE MODELS · Seedance 2.5 1080p Full access · Seedance 2.0 4K Full access` — "full
access" means *allowed to use*, metered as normal. The Seedance 2.5 Unlimited this org has been
running on is a **promotional window**, not a plan entitlement. When it lapses, Seedance goes back
to costing credits and nothing on the pricing page restores it.

The plan-level unlimited list (Ultra Annual, `+7 unlimited & free generation models`):

| Model | Grant |
|---|---|
| Seedream 5.0 Lite · Flux.2 Pro (1K) · Seedream 4.5 (4K) · Nano Banana · Kling O1 Image · **GPT Image** | **365 unlimited** |
| Nano Banana Pro (2K) · Nano Banana 2 (2K) · Kling 3.0 | 7-day unlimited |
| Soul V2 & Cinema | 10,000 free gens |
| **Seedance 2.5 / 2.0** | **none — metered** |

**Two consequences that invert older guidance:**

1. **On Ultra Annual, GPT Image is unlimited for 365 days.** The 2026-08-27 reading above ("a
   ~3-credit number on an image generate is correct and expected") is true on PLUS (the plan this
   org was on when it was written) and **false on Ultra Annual**. Check which plan is live before
   reasoning about an image price.
2. **`Unlimited paid parallel generations` is now listed on both PLUS and Ultra.** That is the
   serial-slot bottleneck from hard rule 4 — one 93-minute render blocking every clip behind it.
   Re-test the concurrency claim before planning a wave around serialisation.

Footer caveats worth carrying: unlimited/free grants work **only on higgsfield.ai**, never via
MCP/CLI, Canvas or Supercomputer; and "unlimited usage may be subject to dynamic speed adjustments
during high-traffic periods."

### What a fire costs — the readings on file

The click is governed by hard rule 2 (the strike-through and the `0`, never a remembered number).
These readings are for planning and for the ask-before-paid conversation with the CEO:

| Date | What | Reading | Source |
|---|---|---|---|
| 2026-08-13 | 2.5 · 20 s · 720p, Unlimited on | struck **450 → 0** ("$18 a clip at the $0.04 rate") | composer, Scene 9C day |
| 2026-08-14 | 2.5, toggle stuck off | two **135-credit** charges = $10.80 | Usage History (hard rule 5) |
| 2026-09-10 | 2.5 · 720p · credit lane | 5 s **33** · 10 s **65** · 15 s **98** · 20 s **130** (charged 130 twice that day; refused fires were refunded) | composer (AB-LEDGER 16:10, 12:45) |
| 2026-09-10 | 2.0 · 720p | 5 s **23** · 10 s **45** · 15 s **68** · 20 s not offered (caps at 15 s) | same |
| 2026-09-10 | 2.0 Fast · 720p | ~**17** per 5 s; **53** at 15 s (lab); **28** at 8 s (S21) | same; AB-LEDGER 16:35, 19:35 |
| 2026-09-10 | 2.0 Mini · 720p | **38** at 15 s | AB-LEDGER 16:50 |

[SUPERSEDED as a "before value"] 450 struck for a 20 s 720p 2.5 clip (2026-08-13: "450 struck
through means the toggle is working; 450 *not* struck through is $18 about to leave the account").
The composer read 130 for the same length and resolution on 2026-09-10. The stake behind the check
is unchanged: a live, unstruck number is money about to leave the account.

### Reading the credit ledger — screen by magnitude, not by model name

The account total is **cumulative and shared**, so it rises for reasons that have nothing to do
with the video pipeline. Chasing it as a single number produces false alarms: on 2026-08-13 it
read 339.2 credits / $13.568 against a 21.8 / $0.872 baseline confirmed the day before — a 15x jump
that looked alarming and was entirely benign. (The rule body under this heading was never written;
the heading is the rule.)

## Model tiers — choose the model by what the shot has to carry (CEO 2026-09-10)

Measured on Higgsfield the same afternoon, same 15-second prompt, same three Elements, fired back to
back on the credit lane (`s2rq15-lab-the-bids-jumpcut-15s.txt`, AB-LEDGER 16:10–16:50):

| | Seedance 2.5 | 2.0 Fast | 2.0 Mini |
|---|---|---|---|
| credits, 15 s 720p | 98 | **53** | **38** |
| max duration | 30 s | 15 s | 15 s |
| render | 11-19 min | **~4.5 min** | **~3.5 min** |
| bitrate, same 720p/15 s | — | **17.0 Mbps** | **4.3 Mbps** |
| file size | — | 32 MB | 8 MB |
| `@Element` chips | yes | **yes** | yes |
| Unlimited grant covers it | yes | no | no |

Toggling Unlimited on a 2.0 model opens a purchase modal; 2.0 costs credits even while a 2.5 grant
is live. Mini has no High/Medium/Low quality control at all — that row is simply absent from its
settings.

**Both cheap tiers bind Elements.** That was the question that could have ruled them out and it did
not. 2.0 Fast held a face from an Element across three hard cuts, and held a second character from
PROSE alone across two more, with the five spoken lines in the right order.

**The CEO's read, which is the one that decides casting a model to a scene (2026-09-10):**
"Fast ดีกว่า Mini มาก และเห็นได้ชัดว่าถูก Upscale มา สีสันสดใสกว่าต้นฉบับมาก เหมาะกับการเป็นฉากที่
ไม่ควรมีตัวละครเป็นฉากในจินตนาการ และฉากที่ไม่มีผลกับผล เป็นฉากเริ่ม"

So: **2.0 Fast looks upscaled — colour reads more saturated and the image sharper than the source
grade.** That is a feature for some shots and a defect for others.

- **Give 2.0 Fast:** establishing shots, opening images, imagined or dreamed scenes, inserts with no
  cast, anything where a heightened look is welcome and continuity with the graded footage does not
  matter.
- **Keep 2.5 for:** any shot that has to cut against other 2.5 footage inside the same scene, and
  any beat carrying the story.
- **2.0 Mini** is the cheapest, the fastest and visibly the weakest — treat it as a draft tier.
  Measured against Fast on the identical prompt: **a quarter of the bitrate** (4.3 vs 17.0 Mbps),
  **16-18% less colour saturation**, higher edge energy at lower bitrate (over-sharpening and
  compression, not real detail), skin that reads waxy on a large face, and it **ignored the framing
  spec** — asked for a face filling sixty percent of frame height it pulled back to roughly
  forty-five. Its cut timing drifted furthest too (cuts at 1.7 / 3.5 / 5.4 / 7.5 / 10.4 s against a
  script of 2.5 / 5 / 7.5 / 10 / 12.5, leaving a 4.6-second final shot). It still bound all three
  Elements, held both faces across every cut, and spoke all five bids in order — so it is usable,
  just not for anything a viewer looks at closely.

**Never mix models inside one scene** — on the colour and bitrate numbers above, which were
measured like-for-like on an identical prompt. That part stands.

[SUPERSEDED 2026-09-11] the background argument for it — that the tiers stage the background
differently (asked for "a plain cream wall, softly out of focus, nothing else in frame", 2.5 gave a
plain soft wall while 2.0 Fast rendered the whole hall with its columns). S2R-Q rendered BOTH inside
one 2.5 generation (AB-LEDGER 2026-09-11 00:15). **Background staging is a per-shot variable, not
a model discriminator**: never use it to infer which tier produced a clip, and never accept "the
background looks like the hall" as evidence a sheet was fired on the wrong model. The original
observation was a single-sample coincidence read as a rule.

**When the free queue is jammed, render time beats price.** On a day when the Unlimited lane
returned nothing for six hours, a paid 2.0 Fast fire came back in four and a half minutes. Getting
the shot at all is worth more than the discount.

## Platform cost, normalised to baht per second (2026-09-13)

Credits are not comparable across platforms — only money per second of finished video is. Measured
off both dashboards the same afternoon (฿34/$):

| Seedance 2.0 Mini · 720p | ฿/sec | note |
|---|---|---|
| Dreamina Standard, first month | 0.92 | ฿748 → 13,840 cr |
| **Dreamina Standard, normal** | **1.53** | ฿1,246 → 13,840 cr · matches their published $0.046/s |
| Dreamina Advanced, normal | 1.38 | ฿2,490 → 30,745 cr |
| Higgsfield PLUS ($39/mo annual) | 3.36 | 1,000 cr/mo · 38 cr per 15 s |
| Higgsfield ULTRA ($99/mo annual) | 2.84 | 3,000 cr/mo |
| **Higgsfield while an Unlimited promo is live** | **0.00** | nothing beats zero |

**Dreamina is roughly 2.2x cheaper per second than Higgsfield on the same model — and that is the
wrong reason to choose it.** What the cheap number does not buy:

- **The free tier cannot produce one clip.** Measured: balance 80 credits, cheapest video (2.0 Mini
  / 720p / 5 s) costs 85. Secondary sources claiming "225 free credits a day / 2-3 clips" did not
  match the real account. Never quote a free tier you have not read off the dashboard.
- **Free-tier downloads carry a Dreamina watermark** — removing it is a paid feature.
- **720p is the only resolution** on 2.0 Mini there; Higgsfield runs 2.5 at 1080p and 2.0 at 4K.
- **The 85 was struck through from 200.** If that is an introductory rate, the real price is
  40 cr/s ≈ ฿3.60/sec and the advantage disappears entirely. Re-check before committing.
- Dreamina's consistency system is "Omni reference" (2.5 advertises up to 50 refs there; this
  skill's Higgsfield numbers are under "Reference caps"). **Unproven on this production** — do not
  assume it replaces @Element until a scene has been shot with it.

**So: Dreamina for disconnected short social clips, Higgsfield for the film.** And while any
Unlimited window is live, per-second pricing is irrelevant — generate there.

Reference point for heavy 2.5 use: Artlist $499/yr unlimited 2.5 beats Dreamina's 2.5 rate past
about **6 minutes of footage a month**, but brings no Element system.

**Elsewhere, for reference** (read from the providers' pages 2026-09-13, not measured on an
account): no provider gives Seedance unlimited free. Artlist $499/yr (2.5, fair-use + parallel
caps) · Creaa $599/15d, $999/30d · TopView ~$50/mo annual, 60-day window, 720p cap (TopView's own
pricing table, read 2026-09-25, is in `CTO_Wan3.0_TopView` §4: the 60-day window is Seedance, the
365-day 720p unlimited is Wan3) · OpenArt $175-240/mo but capped at **5 seconds and 480p**, useless
for film · Jimeng 即梦 260 daily credits but needs a Chinese phone or Douyin account.

[SUPERSEDED] "Dreamina (CapCut, ByteDance-official) 225 free credits/day ≈ 2-3 Seedance 2.0 clips"
(the 2026-09-13 source list): the same afternoon's dashboard read gave a balance of 80 credits
against an 85-credit cheapest clip (above).

## Reference caps — count before delegating, not after

| What | Number | Date | Evidence | Standing |
|---|---|---|---|---|
| Seedance 2.0, Elements | **9** — a tenth is silently refused, not warned about | 2026-08-14 | confirmed live | the 2.0 cap |
| Seedance 2.5, references | **50** | 2026-08-27 | CEO: "Higgsfield ได้มากสุด 50 REF" (and he had said it before) | **the planning ceiling for 2.5** |
| `@Video 1` + Element mentions in one 2.5 prompt | 11 (1 video + 10 Elements) accepted | 2026-08-30 | task-58f2d7b4 | measured; not a ceiling |
| Largest reference set in one prompt that rendered on this film | 16 | 2026-09-05 | S2Q ("identical sixteen references") | measured; not a ceiling |
| "Higgsfield's 16" | 16 | 2026-09-13 | the Dreamina comparison ("Platform cost") | **unverified**: no refusal at 16 or above was ever recorded |
| Seedance 2.0 Fast / Mini | bound all 3 asked | 2026-09-10 | model lab | not a cap test |

**The ceiling for Seedance 2.5 is 50 references; nine is the 2.0 cap.** A CTO once planned around a
nine-element ceiling that does not exist and wrote weaker scenes because of it. Do not ration
references. [SUPERSEDED] any org note before 2026-08-27 claiming nine for 2.5. If a 2.5 composer
ever refuses a reference below 50, record the count here with its date.

### What 50 unlocks — one reference per person

One character per plate is `CTO_Film_Production` §3. With 50 slots it extends to the whole cast:
**every character who does anything gets their own individual plate.** No group plates for anyone
who acts.

That is not a nicety, it is the difference between directing and hoping. A group plate of eight
people cannot be directed: write "one of them raises a hand toward the wall" and the model has no
idea which one, so it invents. With one plate per person you write `@char_critic raises a hand
toward the wall while @char_student shakes her head` and both land.

CEO's rule, verbatim: **"REF ที่ดี ต้องมี 1 REF / 1 คน / 1 ภาพ"** — one reference, one person, one
image. **"แม้แต่ตัวประกอบ ก็ต้องมี REF"** — even the extras.

Group plates still have one honest use: an undifferentiated mass in the deep background that
performs no action. The moment a body needs to do something specific, it needs its own plate.

## The face and copyright scanner (measured on «Sorry, Sir»)

### One face per plate — what the scanner kills

The most expensive lesson of the wave. Content scanners match on human faces. **Three plates died
permanently in one day**, each with a terminal verdict and no re-check control left in the UI:

| Plate | Faces in it | The fix that worked |
|---|---|---|
| a *location* plate | six people standing in it | regenerate the location **with nobody in it** |
| a character plus his two bodyguards | three | regenerate as a **solo portrait**, guards bound separately |
| two journalists sharing a camera | two | **split into two plates, one face each** — both passed first try |

So the one-character plate and the empty location plate of `CTO_Film_Production` §3 carry a second
reason here: **design every plate with at most one face**, because that removes what the scanner
catches. It fires on *resemblance*, not infringement.

**The scan is retroactive.** A plate that passed at 10:41 was terminally dead by 11:47 with nothing
changed. **A plate is never banked.** So: **make a plate and fire every scene that needs it in one
unbroken loop, same operator, no handoff.** The gap between creating a plate and using it is pure
risk.

### A rejection: find the trigger

A refused fire reads `NSFW · Credits refunded · Rejected due to copyright restrictions` on the card
(Unlimited fires are refunded too). The refusal never names what it objected to. Suspects in the
order the measurements put them:

1. **A reference IMAGE** (S2R, 2026-09-07 — the amendment the ledger made to this rule): three fires
   of one sheet were rejected, two with the previz and one without; the same text with one prop
   chip (a crocodile handbag, which reads as protected trade dress) moved into prose rendered. On a
   copyright rejection, **diff the sheet's chips against every sheet that rendered ON THE SAME LANE
   and drop the never-rendered props first**; the prose keeps the prop in the scene.
2. **A chip that shows the warning triangle before firing.** The toast reads "Some reference
   elements may contain protected content. Check eligibility or remove them to proceed". There is
   no per-Element eligibility control to clear it, and one click is refused client-side. Do not
   click twice hoping — **move that object into prose in the same sentence position** and
   re-verify the chip count (SC2, 2026-09-07: fired first click, credits 461 → 409 exactly).
   Flagged so far: `prop_croc_bag`, `prop_car`, `char_guard_private` (v1, retired),
   `project_absence_prop_tag` (the CEO's original plaque plate, AB-LEDGER 2026-09-10 04:50).
3. **A bound character Element at large face size is a risk factor, not a proven cause** (the paid
   ladder, AB-LEDGER 2026-09-10 11:45 → the 13:40 correction). Framing was ruled out (the same 13
   chips were rejected wide and close); chip count was ruled out (13 chips rendered on 2026-09-08);
   the Madame's Element was bound in every rejection, but the same Element had passed on this lane
   twice. What IS measured: the prose version of that character passed two for two and rendered
   consistently shot to shot. The check reads the OUTPUT, so the same prompt can go either way.
4. **Names — the second suspect, not the first.**

[SUPERSEDED 2026-09-07] "it was the name" as the measured cause of S2Q (2026-09-05: "with three
strings changed and nothing else … the identical prompt, identical sixteen references, identical
blocking and identical cuts generated clean on the first try"): confounded — the name strip and the
move to the credit lane happened in the same fire (AB-LEDGER S2Q, S2R). Keep names as the second
suspect.

**When you do suspect a name: names are not the risk, a COLLISION is.** A generator's copyright
filter reads proper nouns in your prompt text and matches them against real people and real works.
Invented names pass all day — in the same film `Valder` and `Carrington` are spoken out loud in a
dozen rendered clips and nothing has ever objected to them. What gets refused is the invented name
that happens to land on somebody or something notable. It looks random, so the first instinct is to
re-fire. The director's framing, and it is the correct one: **do not stop using names — find the
one that collided.**

**Diagnose it from the files you already have, before you fire anything.**

1. **List every proper noun in the paste block.** There are usually about four. Strip `@handles`
   first so Element ids do not pollute the scan.
   ```bash
   python3 - <<'PY'
   import re,pathlib
   b = pathlib.Path(SHEET).read_text().split("PASTE FROM HERE",1)[1].split("PASTE STOPS HERE",1)[0]
   print(sorted(set(re.findall(r"(?<!^)\b([A-Z][a-z]{2,})\b", re.sub(r"@\S+"," ",b), re.M))))
   PY
   ```
2. **Cross the list against what has already rendered.** A name that appears in a clip sitting on
   the drive is cleared by evidence and needs no test. On that wave two of the four names had
   rendered in seven scenes and three scenes respectively; the two untested names appeared in six
   sheets, **and not one of those six had ever rendered.** The untested strings and the blocked
   clips were the same set. That is the diagnosis, and it costs nothing.
3. **Change only the names.** One variable, or the result means nothing.
4. **A full strip proves the name was the trigger. It does not tell you WHICH WORD.** An honorific
   and a surname are two variables — clear both at once and you have a working clip and no
   knowledge. If the answer matters, split them across clips you have to fire anyway: keep the
   honorific and change the surname on the next scene, and one render answers it at no extra cost.
   Never spend a render on a test you could have piggybacked.

**A name in the prose counts, not just a name in dialogue.** Sister scenes were assumed to be a
free control because nobody says the name out loud in them — but it was written into their
blocking lines, position maps and reference descriptions, and a filter reads the whole prompt. They
were carrying the same risk, not testing it. **Grep the paste block, never reason from the
dialogue.**

**When one name is cleared, sweep every sheet that carries it** — the string lives in more prompts
than the one in your hand.

Give the invented name a plain descriptive stand-in (`THE WOMAN IN GREEN`) and keep the real one in
the sheet's notes so the story is not lost. The director decides whether to keep hunting for a
usable name or ship the descriptive one.

## The composer

### A long-lived tab lies about the concurrency slot — open a fresh one every 3-4 generations

The single largest time sink measured on this project, and it looks exactly like a server-side
problem while being purely client-side.

Observed 2026-08-13 across a four-hour session: Generate kept returning the "1 unlimited generation
at a time" toast, with a card apparently stuck on `Processing` that survived hard reloads. It read
as a zombie generation holding the account slot. **It was not.** A brand-new tab showed every card
already finished, no `Processing` badge anywhere, and the ledger confirmed nothing had billed. The
render had completed long before; the aging tab was holding stale state for both the badge render
and whatever the client consults to decide the slot is busy.

The same staleness produces two other symptoms that look unrelated:

- **The Unlimited toggle stops registering clicks** — coordinate click, ref click and double ref
  click all leave it at `aria-checked=false`. More clicks never help. A fresh tab fixes it
  immediately.
- **A processing-text check returns "none" and Generate still toasts.** The DOM and the true
  server-side slot state have drifted apart, so the page's own evidence is worthless.

**Do not treat any of these as things to wait out.** Waiting cost roughly ten minutes per clip
across a 26-clip queue before the cause was found, and it corrupted the pace estimate reported
upward — what looked like 20-minute renders was mostly waiting on a slot that was already free.

Rules:

- **Open a fresh tab every 3-4 generations, proactively, before anything looks wrong.** Close the
  old one. This is routine hygiene, not troubleshooting.
- **Never accept these as evidence the slot is free:** the `Processing` badge, the absence of
  processing text, or any cached element reference. A freshly loaded tab is the only reliable
  check.
- **If the toggle reads `aria-checked=false` after a click, go straight to a new tab** rather than
  clicking again.
- Escalation order: hard reload → new tab → STOP and report. Quitting or restarting Chrome is a
  CTO-only decision (browser-operator HARD rule, 2026-09-07): the window is shared and a restart
  wipes every other operator's staged composer. A frozen tab never loses a render — the job lives
  server-side.
- A tab whose viewport collapsed to the mobile layout: "Desktop width" above.
- **Clicks can stop registering across the whole tab, ref-based ones included.** Same session.
  Nothing errors — every call reports success and the page simply never responds. If two
  consecutive clicks produce no DOM change, stop clicking and hard-reload; more attempts near a
  priced Generate button is exactly the pattern that cost $10.80 in the toggle incident (hard rule
  5).

### The composer silently resets its settings — check the spec, not just the price

Hard rule 2 covers the Unlimited toggle resetting to OFF. **It is not the only control that
drifts.** Observed 2026-08-13 on Scene 9C: the resolution had silently reverted to **480p** between
generations, caught only because the operator re-read the settings before clicking rather than
trusting them.

This is a different class of failure from the credit rules, and more insidious, because nothing
stops it:

- A 480p clip **completes normally**, shows a normal card, downloads normally, and mirrors to Drive
  normally.
- It costs nothing, so no money check catches it.
- It is off-spec footage that surfaces at **edit time**, after the account's one-at-a-time serial
  slot has already been spent producing it.

**Re-verify the full spec immediately before every Generate click**, the same way the price check
is done — not just the Unlimited toggle. For «Sorry, Sir» the locked spec was **20s / 720p /
Seedance 2.5 / High / Sound ON** (CEO: *"ปรับ ค่าเป็น 20s 720p Seedance 2.5 High 1/4 SOund ON
Seedance 2.5 เสมอ"*). A 1080p drift was caught the same way on S19 (AB-LEDGER 2026-09-10 10:05).

Also read it back on **completed** cards, which display their real resolution and duration: a clip
generated off-spec earlier is invisible until someone looks for it.

### Editor gotchas (Higgsfield's prompt box is Lexical/contenteditable)

Paste-only entry, the decoy editor and the three reads are hard rule 6. Beyond those:

- **Clearing**: use a real Cmd/Ctrl+A + Delete keypress via the driving tool.
  `document.execCommand('selectAll')`/`delete` does **not** actually clear it — measured behavior is
  append, not replace.
- **Entering text**: the synthetic `ClipboardEvent` paste sets
  `DataTransfer.setData('text/plain', ...)` only. Also setting `text/html` causes a double-paste bug
  (content inserted twice). Verify the resulting text length before ever touching Generate.
- **A correct paste can still fail to reach the app's form state.** Measured 2026-08-12
  (task-cda4f469): Generate was refused four times in a row with the literal error **"Prompt >
  Instruction: Prompt is required"** while the editor demonstrably held the text — read-back gave
  `innerText` 2216 chars and `__lexicalTextContent` 2417 chars, correct content, right node, decoy
  already filtered out. The paste reaches Lexical but never binds to the React state Higgsfield
  validates against, so the app believes the field is empty. **Do not read this error as a content
  rejection or a bad prompt** — the identical text had generated successfully minutes earlier. It
  showed up specifically on the *second consecutive submission of the same prompt*.
- **For any repeat of a prompt that already generated once — a spare, a retry, a second variant —
  do not paste at all. Use Recreate.** Hover the successful card's thumbnail, confirm the tooltip
  reads Recreate (never Rerun), and click it. Higgsfield loads its own prompt and references
  through its own code path, which fills the form state correctly by construction: no paste, no
  decoy, no desync. Confirmed working immediately after four paste failures on the same shot. It is
  also faster than pasting. If Recreate is genuinely unavailable, reload the page fully and paste
  into a clean composer.
- **A full page reload does NOT clear the desync on its own** — measured 2026-08-27
  (task-f4305098), directly contradicting the fallback sentence above, which was written from a
  session where the reload happened to coincide with a recovery. The operator reloaded fully,
  pasted into a clean composer, and Generate still refused with the same "Prompt is required".
  **What actually forced the bind was a real trusted keystroke after the paste: `End`, then
  `space`, then `Backspace`.** A synthetic paste alone never produces the keydown React listens
  for; those three keys leave the text byte-identical while generating genuine trusted key events,
  so the bound state catches up to the visible text.
- **Make the three-key tap a routine step after every paste**, not a recovery move — it costs one
  call and removes the whole failure class before you ever look at the Generate button. It does not
  conflict with the ban on `type()` for prompt *content*: the ban exists because keystroke entry
  truncates multi-paragraph text, and these three keys enter no text at all.
- **Recreate button reliability**: its on-screen position shifts with thumbnail width (cards with
  different reference-image counts render different thumbnail widths), and it only mounts in the
  DOM on real hover, not just CSS-hidden — hover-then-verify via tooltip text every time, don't
  trust a fixed coordinate or a cached element reference. A click can also silently no-op even on a
  DOM-valid reference for no clear reason — verify the composer actually loaded the target card's
  distinctive text before proceeding, retry once if not.
- **History pagination**: the list is server-paginated, not just virtualized — `scrollHeight` grows
  as you scroll toward the bottom (measured: 24k→48k→72k+ px). Don't assume a fixed scene/card count
  from what's initially rendered; scroll to the true end and re-read before concluding "that's
  everything."
- **Paste-only is not enough — the SOURCE of the bytes matters too.** An operator on 2026-09-10
  nearly fired S0b from a **hand-typed** base64 string instead of the one its own extraction step
  had written to a file. It was caught only because the landed text measured **4521 characters
  against 4513 in the source**, and it was caught before any chip check or Generate click. A prompt
  corrupted this way passes every downstream check — chips still bind, the price still reads zero,
  the clip still renders — and the defect surfaces days later as "the model ignored the sheet".
  **The rule: never hand-transcribe prompt bytes at any stage.** Extract the PASTE block to a file,
  base64 it from that file, paste it, then read the landed length back and compare it to the source
  length. Equal or clear and redo. Length is the cheapest check there is and it is the only one that
  catches a corrupted source.

### Tab hygiene

Lives in the `browser-operator` skill, under "Tabs — claim what you open, close what you claimed".
It is not a Higgsfield rule; it was merely found here. The one Higgsfield-specific consequence: the
stale-`@Video` binding failure ("Attaching a previz" below) only reproduces in a tab that has
already touched more than one video asset, so a fresh tab per fire is a real defence and not just
tidiness.

## Elements and references

Read what a plate depicts before binding it, and never re-point a reference: `CTO_Film_Production`
§3. What follows is how Higgsfield binds.

### The easy way to attach a reference: drag the asset in, then use @Image1 / @Image2

**Read this before doing anything with Elements.** It is simpler than everything below it and it
sidesteps the entire Element-naming problem.

Reported by the CEO from the live UI, 2026-08-27, after an operator had spent hours fighting red
tags:

> "2 Image นี้มีอยู่แล้วในนั้น ใช้เป็น Ref ได้โดยการลากมาวาง ไม่ต้อง Create Element ID
> หลังจากลากวางใช้ @Image1 + @Image2 สำหรับอ้างอิง"

**Any image already in the project can be dragged straight into the composer and used as a
reference. No Element needs to be created and nothing needs a name.** Once dropped, the images are
addressed positionally in the prompt text as `@Image1`, `@Image2`, and so on, numbered in the order
they were dropped.

```
1. Find the asset in the project grid.
2. Drag it into the composer's reference area and drop it.
3. Repeat for each reference you want.
4. Write the prompt using @Image1, @Image2 … to refer to them.
5. Generate.
```

**Why this matters more than it sounds.** Everything else here about attaching references —
creating an Element, naming it exactly, typing `@project_name_thing`, watching for red text, the
detail-modal-versus-hover-menu trap, the folder-scoped autocomplete — exists to solve a problem
this mechanism does not have. The named-Element path is for things you tag repeatedly across many
prompts. **For "use this specific image as a reference right now", drag and drop is the correct tool
and it is far more reliable.** Two full nights on this project were lost to red tags that turned out
to mean "you never created the Element", when the operator could have dragged the image in and
moved on.

**When you still want a named Element.** Named Elements are still right for **recurring cast,
locations and props** that get tagged in dozens of prompts across a film — you want
`@project_x_char_valder` to mean one fixed thing everywhere. Use the named path for those, and
drag-drop for one-off references.

### RED tag text in the composer = the Element does not exist. Look at the colour.

Spotted by the CEO from a screenshot, 2026-08-27, after an operator spent a whole cycle generating
against references that were never attached.

**A resolved tag renders as a mention chip. An unresolved tag stays as plain text in RED.** That
colour is the fastest, cheapest check available and it is visible without zooming:

| What you see | What it means |
|---|---|
| Tag rendered as a chip / thumbnail appears in the reference strip | Bound. Good. |
| **Tag still plain text, coloured RED** | **Not bound. The Element does not exist under that name.** |

**Check the tag colour before every Generate.** A red tag means the model never sees that
reference — it silently generates from the prose alone, produces something plausible, and the
failure is invisible in the output. **Element naming is not uniform** either: on «Sorry, Sir» most
Elements carried a shared prefix, one did not, and the mention silently failed to bind. Read the
real mention off the panel.

**The cause is almost always this: generating an image is NOT creating an Element.** These are two
separate steps in Higgsfield and it is easy to do the first and believe you have done the second:

1. **Generate an image.** It lands in the project's asset grid. At this point it has an asset id —
   and **no Element name at all.** `@your_name` will not resolve to it, because there is nothing to
   resolve.
2. **Create an Element from that image and NAME it.** Only now does the plain `@name` tag bind.

An operator that generates ten plates and never does step 2 has ten images and zero usable
references. Every prompt tagging them comes out red.

**So: after generating any plate that a later prompt will tag, create the Element and name it
immediately, then verify by typing the tag and watching it become a chip.** Do not batch the
naming for later — the whole point of a chain-of-reference build is that each plate is attachable
by the time the next one is generated. Use the detail-modal route below, never the grid hover menu.

### The @ dropdown is folder-scoped — but PASTE is not. Paste the whole prompt.

Typing `@project_valder_char_son` in the Scene-1 folder composer silently returned nothing, even
though that Element existed and resolved fine in its own folder. The composer's `@` autocomplete is
**folder-scoped**.

That finding is real, and for most of one wave it was read as "cross-folder elements must be
attached through the Elements panel." **That conclusion was wrong, and acting on it cost more time
than the original problem.** Measured 2026-08-19 across three consecutive clips: a plain-text paste
whose body already contains the literal `@project_valder_*` strings **auto-resolves every one of
them into real attached reference thumbnails, across folders**, with no Elements panel involved.
Reference counts came out 9 / 8 / 8, matching each source card exactly.

**Default flow — use this:**
1. Clear the composer (real Cmd+A then Delete, including leftover mention chips).
2. Paste the entire prompt in one synthetic `ClipboardEvent`, tags included.
3. Count the reference thumbnails.
4. Generate.

**Fallback, only when the tag text is genuinely absent from the prompt:**
1. Open the Elements panel.
2. Find the element's card (switch tabs — Characters / Locations / Props).
3. **Right-click the card → "Use".**

A small warning icon may appear on the reference thumbnail immediately after attaching. It is
transient and clears itself — re-check before treating it as a failure. (A warning *triangle* that
stays and a toast about protected content are the scanner: "A rejection: find the trigger" above.)

**Do not build a prompt by inserting elements first and typing text around them.** It attaches the
references in an order that does not match the source text, and on 2026-08-19 a whole composer had
to be torn down and re-pasted because of it. Text first, always; the tags carry themselves.

Related: the folder-scoped Elements picker also **under-reports what exists.** To see everything on
the account, open the project root with `?elements=1`.

Open question (AUTHORING-RULES rule 9): whether the composer makes a chip at every `@token`
mention or only at the first was never fire-tested. Until it is, `CTO_Film_PromptFormat` rule 2
(each reference once) is the rule.

### Creating an Element: use the detail-modal path, never the grid hover menu

The folder-grid hover `...` menu is unreliable — the composer's floating prompt-preview panel
overlaps it and swallows the click. What works every time:

click the card → it opens `?preview=<uuid>` → the `...` at the **bottom-right of that modal** →
Create Element.

And the New Element dialog's **Name / Element ID inputs do not accept coordinate clicks.** Set them
with a native value setter plus an `input` event dispatch via JS. That is a single atomic set, not
char-by-char, so it is not a `type()` risk and it is approved.

### Element IDs are GLOBAL across the account

A short name like `@Mother` resolves to whichever element on the whole account owns that name —
usually one from an older project — and the clip renders with the wrong face while looking
completely normal. Nothing errors.

Every element needs a **Name** (human label) and an **ID** (what goes in the prompt, all lowercase).
Prompts always reference the ID. Convention adopted 2026-08-18: `project_<slug>_char_*` /
`_loc_*` / `_prop_*`.

When renaming an existing sheet, replace suffixed tags first (`@Father-Scarf` before `@Father`) or
the shorter token eats the longer one.

### A bound reference keeps the OLD asset when you re-point its Element

Measured 2026-08-27 (task-66d5a582), and it is the most dangerous failure on this list because
**nothing errors and the finished clip looks fine** — it is just the wrong film. (The rule — never
re-point, use a new name — is `CTO_Film_Production` §3; this is the Higgsfield mechanism and the
fire-time check.)

A reference binds to a specific **asset** at the moment you attach it, not to the Element name.
Re-pointing that Element afterwards updates the Element and leaves the attached reference exactly
as it was. The chip stays green. The name still reads correctly. Only the thumbnail betrays it, and
only if someone looks.

On this job four Elements were re-pointed to regenerated plates during a single staging session.
Two of them — the recast critic and the recolored student — were still showing the replaced
versions in the strip minutes before Generate. Firing would have produced a scene starring two
characters the CEO had already rejected, with no error anywhere to explain it.

**The fix is never a refresh.** Remove the reference completely and re-add it, so it binds to the
current asset.

**Fold this into the fire sequence**, next to the warning-triangle scan:

> Before Generate, zoom EVERY reference thumbnail and confirm it shows the version you actually
> intend. Any plate regenerated during this session is suspect by default — remove and re-add it
> rather than trusting the chip.

The tell to watch for is a plate that has been through several versions in one day. A
first-generation Element is safe; a re-pointed one is not.

## Image plates

### Higgsfield Soul does not accept reference images at all

Measured 2026-08-27 on the «Absence of Meaning» plate chain. **Soul Cinema cannot take Element
references.** This is not a technique problem — the capability is absent from that composer.

Both paths were tried, one clean attempt each, and both failed:

| Path | Result in Soul |
|---|---|
| Paste the prompt with `@element_name` inside it | Tag stays **plain red text**. Never resolves. |
| Type a real `@` to trigger the native autocomplete | **No dropdown appears at all.** Tag stays red. |

The paste-auto-resolve behaviour documented above is real, but it was measured on the **Seedance /
video composer**. Soul is a different composer and does not share it. Do not assume a technique
carries between them.

**What this costs you, and the rule.** A red tag generates silently: the model never sees the
reference, invents something plausible from the prose, and the output looks perfectly fine. On this
project it produced a brass plaque that was a completely different object from the reference plate
— different proportions, different typography, missing the screws — and noticing that mismatch was
the only reason anyone caught it.

**CEO's standing ruling, 2026-08-27: if a plate needs reference images, generate it with GPT Image
Gen 2, not Soul.** A bound reference matters more than Soul's photographic quality, because plates
that have to intercut inside one film have to actually match each other.

This overrides the model-routing rule (Location → Soul, Character/Prop → GPT Image Gen 2) where the
two collide: **routing by asset type loses to the reference requirement.** A location that must
inherit from an earlier plate goes to GPT.

And whichever way you go, **the whole set goes together** — never one location from Soul and another
from GPT. Different models give different light, texture and colour response, and a film whose
locations came from two models will not cut together; viewers feel some shots are not the same
place without being able to say why.

Soul remains the right choice for a location that stands alone and needs no reference.

### The free plate recipe (Kling O1, proven 2026-09-07)

Model and toggle: "What Unlimited covers" above. Plate recipe: three views (front 3/4 centre, side
left, rear 3/4 right) on a plain warm-grey studio backdrop, no people, no badge/plate/text, 16:9,
count 1.

## Attaching a previz as `@Video 1` (Seedance 2.5)

The CEO's generation standard (2026-08-30): **Video ref (camera) + Elements
(faces/costumes/location) + prompt (model control) = full control.** A Blender previz MP4 (see
`blender-previz`) rides the composer as `@Video 1`. Every step below was executed and verified for
real — task-58f2d7b4 (2026-08-30), the project composer task-17fba11f (2026-09-03), the upload path
tasks d188f5bc blocked / dcaef051 fixed (2026-09-09); the gotchas are measured, not guessed.

This is the project's own embedded composer (e.g.
`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`), a different surface from
`scripts/browser/higgsfield-jumpcut-gen.js`'s `/ai/video` jump-cut editor — same account, same hard
rules, different DOM.

1. **The composer is embedded at the bottom of the project's asset-grid page** (no separate URL)
   behind an Image/Video tab toggle. Click "Video". **The model DEFAULTS to Cinema Studio 4.0** —
   open the model dropdown and select Seedance 2.5 explicitly, every fresh composer.
2. **Decoy twins everywhere on this page**: two "Video" tabs, two "References" buttons, and TWO whole
   composer panel instances (a hidden Cinema Studio one and the visible Seedance one — the first DOM
   match is the wrong one). Filter every candidate by
   `getComputedStyle(el).visibility === 'visible'` before clicking or pasting; `find()` alone cannot
   tell them apart.
3. **Upload through "+" → Uploads → Videos, into that tab's own file input.** Click the composer's
   **"+"** (references mode pill) → the reference panel opens with Uploads / Elements / Generations /
   Liked tabs → **Uploads → Videos** sub-tab → use THAT tab's own `<input type=file>` (a third input
   on the page; pick it by panel context, not by `accept`) → `mcp__claude-in-chrome__file_upload`
   with that ref. Synthetic drag-and-drop CANNOT work for a real filesystem file — page JS can't
   fabricate a File object; don't attempt it.

   [SUPERSEDED 2026-09-09] the 2026-08-30 instruction "the panel's `<input type=file>` whose `accept`
   includes `video/mp4` (the page has THREE file inputs — pick by accept attribute)". Spawn 1 on
   2026-09-09 lost 35 minutes and blocked because it fed the previz to the composer's own
   `<input type=file>` (and the References picker's inputs): the tile spun, the toast "Your upload is
   being verified. You can select it once verification completes" sat there for 90 s+, no
   eligibility pill, no asset, no error — four times across three fresh tabs, with CDP screenshot
   timeouts on top. The file was fine (S2P's 4.5 MB previz had attached the same way earlier; a
   1.5 MB re-encode changed nothing). The panel path above worked twice (S2AJ 20:12, S2PT 22:15).
4. **The file must be readable by the operator's session.** An org-repo absolute path gets refused
   by the upload sandbox, and `cp` out of the org repo trips self_repo_guard. CTO: stage the MP4
   INTO the worktree at task creation. Operator fallback that measured clean:
   `dd if=<org path> of=<scratchpad path>` (or `base64 -i … -o …`).
5. **Wait for verification — 1–3 minutes for a 20 s 720p file.** Toast "Your upload is being
   verified"; the tile spins as "Checking.." and is UNCLICKABLE. Wait for the spinner tile to become
   a real thumbnail in the Uploads grid sorted **"Last created"** — not the default "Last used",
   which does not surface a video that was uploaded but never yet used as a reference, and which
   sorts a previously-clicked asset to the front regardless of upload time. The "being verified"
   toast can linger after success — a red herring, not a failure.
6. **Byte-match before EVERY attach click:** `fetch(video.currentSrc, {method:'HEAD'})` →
   `content-length` == local file size (`scripts/browser/higgsfield-video-ref-attach-fix.js` has the
   technique). Then click the tile → toast "Added to prompt box" + green checkmark. On the
   2026-09-03 surface that was a **two-click flow**: after the upload finished, hovering showed a
   "Check eligibility" pill; click that pill first, it flips to a `Checking..` spinner (a
   **second**, separate wait, several seconds), and only after that clears does clicking the tile
   actually attach it — clicking the tile before this resolves is a silent no-op that looks like
   nothing happened. In the 2026-09-09 Uploads → Videos path the pill may NOT appear — "Added to
   prompt box" fires directly. Confirm the reference tray's `<video>` `currentSrc` byte-matches
   before pasting.
7. **A stale reload can leave a BROKEN video chip that looks identical to a working one.** Confirmed
   the jump-cut script's existing finding ("prompt draft survives reload, Unlimited toggle does
   not") on this surface too — but here the survived chip can be an **empty placeholder**: a rounded
   box with no thumbnail, hover shows only expand/× icons, and `document.elementsFromPoint()` at that
   box finds a real `<video>` node inside it with `readyState:0` and `currentSrc:""` — i.e. attached
   to nothing. Visually indistinguishable from "still loading" at a glance. **Fix: remove it (×) and
   re-attach fresh** from Uploads → Videos, sorted "Last created".
8. **A `@mention` trigger typed right after clicking near an existing chip pill can silently land on
   the wrong node and substitute an unrelated mention.** Reproduced once: clicking at a point that
   was actually *on/inside* the previous chip's pill, then typing `@Video`, produced a completely
   unrelated `@Mother` chip in the text — no error, no dropdown shown in the screenshot taken right
   after. Root cause: the click did not focus the real contenteditable (confirmed via
   `document.activeElement.tagName === 'BODY'` afterward) — a `cmd+a` at that point selects the
   *whole page*, not the editor, which is the tell that focus never landed. **Fix: after every click
   meant to place the cursor in the prompt box, verify
   `document.activeElement.getAttribute('contenteditable') === 'true'` before typing anything** — if
   it isn't, the click landed on a decoy/chip and must be retried at a provably empty point in the
   text flow. Convert the click coordinate from `getBoundingClientRect()` (CSS px) using the measured
   screenshot-to-viewport ratio (`screenshotWidth / window.innerWidth`, **1374/1024 ≈ 1.342** that
   session — re-measure per session, it tracks devicePixelRatio) rather than eyeballing screenshot
   pixels, since the two coordinate spaces differ.
9. **Mention syntax is literally `@Video 1`.** Typing `@Video` in the prompt box surfaces a dropdown
   entry "Video 1"; selecting it makes a green chip, exactly like Element mentions. Element chips
   coexist alongside it unchanged. (Typing the short `@Video` trigger is fine — the type() ban is
   about multi-paragraph content; build the surrounding prompt with the synthetic-paste technique as
   always, then End→space→Backspace to force state sync.)
10. **Settings-row scroll order for this composer**, reached by repeated clicks on the `>` chevron at
    the row's right edge: References dropdown → aspect ratio (16:9 etc) → resolution (720p etc) →
    duration (the same ARIA slider as hard rule 6 — click the thumb, then `ArrowRight`/`Left` once
    per second, never type into it) → **batch size** (shows as `N/4` — confirmed via `find()` label
    text "Increase/Decrease batch size", this is NOT the quality tier, do not confuse the two) →
    quality tier (High/etc, a separate control further right) → Sound On/Off → Unlimited toggle.
    **Reload preserves duration/resolution/batch-size/quality/sound; it does NOT preserve
    Unlimited** — re-verify the whole row, not just Unlimited, after any reload, since a broken video
    chip (step 7) is also a reason you might reload mid-task.
11. **Clear a leftover video reference before a sheet that says "No previz".** The reference tray
    survives a model switch and a re-paste. Remove it with its hover-revealed × and confirm
    `document.querySelectorAll('video')` returns nothing visible. (Clicking an Uploads-tab image tile
    once also ADDS it as a reference chip — remove it via its × before anything else: AB-LEDGER
    2026-09-10 05:05.)
12. Everything else is unchanged: Unlimited $0 zoom-check before Generate, one generation at a
    time, never Rerun.

### Prompt authoring for a video reference (CEO rules, 2026-08-30)

The prompt must do three jobs, in this order, or the model randomises:
1. **Describe the video's camera in words too** — beat-for-beat with timestamps, ending "No other
   camera movement exists in this shot." The chip alone is not enough; the text tells the model what
   to copy from it.
2. **POSITION MAP every figure** — one line per proxy: what it looks like in the video (colour +
   floating label) = which Element replaces it. A proxy without a mapping line is a slot the model
   fills with a stranger.
3. **Declare the ref camera-only**: "@Video 1 carries ONLY camera path, timing, and positions. It is
   NOT a style reference" — then restate grade/light/texture from the film's standard block.
   Otherwise the gray previz look bleeds into the render.

The character prompt itself stays exactly as the scene file wrote it — the video blocks ADD to it,
never replace it. **The video is a CHIP exactly ONCE — the composer BUGS on a second `@Video 1`
mention (CEO measured it live, 2026-08-30).** One prompt supports one video mention, full stop. The
first mention is the chip; every later reference in the prompt is plain words ("the reference
video"), never a mention. **A warning about it counts as a mention too**: when writing this rule
into a prompt file, never type the token — write "the video chip is bound at its first mention
only" (`s1-angles.txt:82-85` broke the rule in the sentence that declared it; AUTHORING-RULES rule
4). And because under the paste marker the chip exists only through the attach step, the operator
verifies the slot's name before firing: if the composer names it anything but "Video 1", every
sentence that points at it points at nothing. Budget: the 11-chip mix in "Reference caps" was
accepted; state in the brief which element to drop if the composer refuses the 11th. And it bears
repeating: **UNLIMITED GENERATE ONLY** — the video ref changes nothing about money rules.

### A video reference beats the prose (measured)

`CTO_Film_Production` §6 leaves this to the engine skill. On Seedance, `@Video 1` carries speed and
blocking, and it wins over the words:

- **S2C** (2026-09-05): the previz proxy was moving at 5.67 m/s; three takes of "HE NEVER RUNS" ran.
  The take that walked also had the previz re-cut to walking speed (AB-LEDGER S2C).
- **S2PT takes 1-3** (2026-09-10): one previz coordinate put Dupe ahead of his cart; eleven prose
  negatives lost three times; the fix was the coordinate (AB-LEDGER "S2PT · takes 1-3 → 4").
- **S3a take 2** (2026-09-10): a two-camera marker-bound previz as Video 1 fixed "locked camera"
  where prose alone did not (AB-LEDGER 04:05).

So when a defect survives prose hardening, check the previz first: measure its speed in m/s, and
verify every proxy is VISIBLE in the previz render (`world_to_camera_view` plus a look), not merely
present.

### Previz files

- **Resolution at least that of the output: 1280x720 for a 720p fire** (measured 2026-09-03,
  AUTHORING-RULES "previz ≥ output"). S1C fired three times, ~26 min each, and every one died with
  the generic error *"change your input files or prompt"*, after every other hypothesis had been
  ruled out (all 33 previz files 16:9, S1C not the largest, bitrate 5th of 33, no second `@Video`
  anywhere). Re-rendered at 1280x720 with nothing else touched (same camera, same 8 s, same 192
  frames), take 4 passed (`absence-S1C-take4-023e91c3-PASS-8s-720p.mp4`). Higgsfield never states
  this anywhere (help center 74 articles, docs 20 pages, the full OpenAPI spec searched): it is our
  measurement for 720p output; at 1080p assume the floor moves with the output and measure again.
  Check with `python3 scripts/previz-check.py` before using any previz as a reference.
- **Keep the file small anyway** (≤ ~1.5 MB, ~150–600 kbps, faststart): faster verification, same
  frames. The brief for a previz scene should name the upload path above.

## Seedance video edit — it has a grammar, and guessing it fails (2026-09-11)

Seedance 2.5 can edit an already-rendered clip instead of re-shooting it. **My first edit prompt
produced no change at all**, and the reason was not the wording quality — it was that edit mode has
a documented instruction format I had never read. Researched afterwards against ByteDance's model
docs and third-party API references; the three mistakes below are all mine.

**1. LEAD WITH AN EDIT VERB. This is the switch that turns edit mode on.** The model watches for
`edit` · `remove` · `add` · `replace` · `change to` · `restyle` · `relight`. Leading with one of
these tells it to preserve the source and modify it; without one it may treat the text as an
ordinary generation prompt. My prompt opened "MOVE THE BRASS PLAQUE DOWN THE WALL" — **`move` is not
on the list**, and nothing happened.

**2. NAME THE VIDEO INSIDE THE PROMPT.** The documented shape is literally:
`Edit @Video1: <what changes>. Keep <what stays> unchanged.`
Attaching the clip to the composer is not enough — the instruction text itself refers to `@Video1`.
Mine never mentioned it.

**3. IN EDIT MODE REFERENCES ARE `@Image1`, NOT ELEMENT NAMES.** Reference images are passed
positionally and addressed as `@Image1`, `@Image2` — e.g. "replace the man's jacket with the one in
@Image1". I used `@project_absence_prop_tag`, a Higgsfield Element mention, which is the composer's
system, not the edit surface's.

**WHAT IT CAN AND CANNOT DO — the capability list matters as much as the grammar.** Documented
operations: **restyle · remove an element · replace an element · swap the background · time-scoped
edits** (`between 0:02 and 0:04, add …`). The model's stated job is to preserve **subject identity,
composition and motion**.

⚠️ **"Move this object" is not on that list, and it fights the model's purpose** — repositioning is
a change of composition, which is the thing it is built to hold still. **Decompose a move into the
two operations it does support: REMOVE it from the old place and ADD it in the new one,** in one
prompt, and say explicitly that the finished clip contains exactly one of the object.

**Other rules from the docs worth keeping:** describe changes bidirectionally (from A to B, not just
"make it B"); fence the edit by naming what stays, spatially and temporally; masks and region
selection are NOT required; and it works best on short focused inputs of roughly 4–15 seconds, not
long multi-shot clips.

**Still unverified for us:** whether Higgsfield's UI exposes this grammar the same way the API does,
what an edit costs, and whether output quality matches the original. Read the price off the button
like any other fire.

## Writing a prompt for Seedance — what `CTO_Film_PromptFormat` leaves to the engine

The file layout, the paste-block order, one name per character, each reference once, the manner
tag, the negatives and the 60-second pre-fire read are `CTO_Film_PromptFormat`. On Seedance, add:

### IRON RULE OF PROMPT WRITING — every character appears EXACTLY ONCE

CEO-set 2026-08-30 («ใส่ไว้เป็นกฏเหล็กของการเขียน Prompt เลย») after duplicate characters appeared
across MULTIPLE scenes — S4 rendered two Dupes with two carts, and it was not an isolated case.
Seedance duplicates a character whenever the prompt gives it two independent reasons to draw the
same person (a binding + an unbound description, a group noun + a named member, or — the worst case
— a video-ref proxy + its mapped character).

Every prompt, no exceptions, carries BOTH halves:

1. **In the beats**: state the count in words wherever a character could be inferred twice — "his
   TWO guards and no others", "there is exactly ONE Dupe in this shot".
2. **In the negatives, verbatim**: `no duplicate characters, no twins, no character appearing twice`
   — plus, when a video ref is attached: `no proxy rendered as an extra person`.

For video-ref prompts the position map must close the loop explicitly: "one proxy, one person —
never both a mapped character AND a leftover gray figure." A proxy without a mapping line is a
duplicate waiting to happen.

Reviewers: a duplicated character is a FLAG-worthy defect — label the take
(`-FLAGGED-duplicate-<who>`), file it, move on, per the review loop.

**Measured since (2026-09-08/09): the count is necessary, not sufficient.** S15a-1 t1 and S2S-B t2
carried the count in capitals and still duplicated; what held was placement — say WHERE every
person-chip stands and who holds the opposite side of frame, and give every person-chip a
wardrobe sentence (AB-LEDGER S15a-1, S15b, the grandmother); two characters sharing one reference
need two positions, not a count (AB-LEDGER S16, S2R-JC). Both halves above stay mandatory and
`scripts/prompt-lint.py` checks them.

### PRE-FIRE — lint the prompt before you paste it, every time

CTO-set 2026-09-03, after S1C burned two operator sessions and three renders on a defect a human
review missed by eye: a block of guidance the CTO added to stop an earlier mistake sat *inside the
text the operator pastes*, and it described the very things it was banning. Whatever is pasted into
the composer IS the prompt — notes, take ids, `(CEO ...)` stamps and all.

**Before firing any prompt, and before committing a new or edited prompt block, run:**

```bash
python3 scripts/prompt-lint.py path/to/the-file.txt --shot S1C
```

It flags operator/CTO/CEO guidance sitting in the pasteable text, a second `@Video` mention in one
shot, quoted strings that read like a reference declaration, bans written as a description of the
banned image, a negative that contradicts a reference in the same block, and a prompt with two or
more character chips that lacks the IRON RULE's two halves. Exit code non-zero means something in
that text would corrupt generation — fix it before pasting, don't paste around it. False positives
happen (the tool says so in its own output); use judgement, don't silence the check. The two zones
and the 60-second read are `CTO_Film_PromptFormat` §1 and §4; the defect history is
`docs/prompts/absence/AUTHORING-RULES.md`.

### The sound line

Sound is always stated (`CTO_Film_PromptFormat` §2 item 6). On Seedance the line is
`room tone, <one foley detail>, no music` — leave it out and you get car-ad score (PROMPT-STYLE
template, 2026-08-28). **"No music" goes in every scene.** Every scene also carries the
audio-endpoint ban, a CEO-approved "forever-line" of 2026-08-21, restored into every scene by the
2026-08-31 sweep (`docs/prompts/absence/videoref-inserts.txt:1`):

    NO SOUND AT THE START OR THE END: the clip opens mid room-tone with no intro sting or riser, and simply stops with no tail, swell or fade.

Other engines word sound differently; do not carry this line to them (their skills say how).

### Camera and cuts

- **Operator vocabulary only**: dolly, push-in, locked-off, whip pan, lateral track; never "the
  camera moves" (PROMPT-STYLE rule 4, from Higgsfield's own Seedance guide). The camera lock in the
  tech header is `CTO_Film_PromptFormat` §2 item 1.
- **A cut cannot carry a change.** A change asked for ACROSS a cut does not render — write it as
  motion the camera sees inside a shot — and a cut described as "same frame, the clock jumps"
  renders as no cut at all: a cut needs a visible change of framing or subject (AB-LEDGER S2R-JC,
  2026-09-09). Cuts that change the framing or the face land (S2AJ, S2AP, S15e-AB, S2R-Q).
  [SUPERSEDED 2026-09-09] "Seedance generates twenty CONTINUOUS seconds; it has no concept of a cut"
  (S2R-JC diagnosis, 2026-09-08): take 4 and the later passes above show a cut renders when
  something visible changes across it.

### Dialogue

The manner tag and the dialogue negatives are `CTO_Film_PromptFormat` rule 3 (measured here: S15a
take 1 spoke its stage direction aloud). On Seedance, keep lines short: long monologues drift out of
lip-sync; split them across beats (PROMPT-STYLE rule 5).

### Size and gaze — what was measured (2026-09-06/07)

The rule is `CTO_Film_PromptFormat` rule 5. Measured here:

- With depth words ("the nearest thing to the lens / extreme foreground / floating at the very
  front") a mark the prose called "SMALL… about the size of a hand" rendered 4-5x too big on two
  consecutive takes (S2K t1, S2M t2): the model was doing perspective correctly — a near object is
  big in frame, and "a hand" is a world size it cannot place. Anchored to the red door in the same
  frame ("NO WIDER THAN THE RED DOOR AND NO TALLER THAN THE RED DOOR, exactly as the picture has
  it"), it came out about 1x (S2M 3b). Five takes on the same anchor then rolled between 1x and 3x
  the door: if the editor needs one identical object across cuts, an overlay at edit time is the
  only exact tool; the prompt gets you "small" (AB-LEDGER S2M).
- Layering ("in front of everyone") is fine once; emphasis ("the nearest thing to the lens") is a
  size order. Emphasis sentences ("the whole joke is this tiny mark") make the thing bigger, not
  smaller. Cut them.
- Do not tie people's gaze to an object whose depth you left ambiguous — "turned toward the mark"
  sent a whole crowd to face the far door (S2M t3b); "with their backs to the room" read as backs to
  us when the camera stood where the wall was (S2N t2).
- [SUPERSEDED for image plates, 2026-09-07] "never as a world measurement (a hand, 30 cm)": on an
  image plate with nothing in frame to scale against, metres plus a RATIO held on the first try
  ("about 5 metres long and 2 metres tall … two and a half times as long as it is high", prop_van
  t3, b6c1562), while a human landmark ("as tall as a standing man's shoulder", t2) let the object
  grow (AB-LEDGER prop_van). In a video shot, anchor to something in the frame.

## The review loop — the operator never self-certifies a clip

CEO-set 2026-08-30. The verdict is the CTO's own look (`CTO_Film_Production` §8); this is the
Higgsfield pipeline around it. It is a loop, not a line:

**Generate → CTO inspects frames → fix the prompt → hand back → regenerate → operator reports WITH
the exact prompt used → CTO passes.**

- The operator sends every finished clip to the CTO **together with the exact prompt text that
  produced it** — not a summary. The prompt is what gets debugged; a summary cannot be.
- **Every clip is saved to Drive whether it passes or fails**, always, with a `-FLAGGED-<reason>`
  suffix when it missed. Nothing is discarded, ever.
- The CTO opens frames personally (`video-see.sh screen` → `t1` sheet → full-res on doubt) and
  checks: duplicate characters, location, camera angle, and anything the prompt explicitly banned
  that appeared anyway.
- Duplicates are fixed on sight. Everything else goes to the CEO as a batched question rather than a
  unilateral fix.

Why: an operator's written review reported four clips clean that were not. S8c had two Valders
standing side by side; S5 wore a gold V its own prompt banned in words. Both survived a green report
and neither survives a look. The review lessons measured since (headcounts and props counted at
full resolution in two frames, a first-vs-last lock test, a content probe for same-lens cuts) are
in `AB-LEDGER.md`.

[SUPERSEDED 2026-08-30] ai-film-production §9 (2026-08-28): "Require a shot-by-shot description of
every delivered clip" from the operators as the review. The loop above moved the verdict to the
CTO's frames; an operator's description is input, never the pass.

## Measuring motion on a Seedance take

The rule — count the motion, look first, a number only confirms — is `CTO_Film_Production` §8. What
was measured here, on S2AC (2026-09-11):

- "IT NEVER SETTLES AND IT NEVER PAUSES. Somebody is always crossing somebody else." came back with
  five people standing in the same spots at 1 s, 8 s and 15.5 s, waving their arms — a posed group
  photograph with busy hands. Position is expensive; hands are free.
- v2 carried four counted crossings verbatim and came back exactly as static — it was also bound to
  the wrong location, a corridor instead of a flat wall, and a corridor funnels a crowd into a clump
  no instruction can undo. v3 changed the plate and nothing else about the crossings, and the group
  genuinely rearranged: the student crossed from far-left to front-centre by 4 s, Dupe walked from
  far-left to dead centre by 11 s, the magenta and cobalt pair swapped sides.

`scripts/shot-motion.sh <clip>` compares the people-band of the opening frame against later ones.
Measured 2026-09-11:

| clip | 7 s | 12 s | 15.5 s | |
|---|---|---|---|---|
| S2AC take 1 (failed) | 10% | — | 10% | flat |
| S2AC take 2 (failed) | 11% | 9% | 11% | flat |
| S2PT take 4 (real movement) | 44% | 46% | 54% | rising |

**The TREND is the signal, not the level.** A real scene drifts progressively further from its
opening frame as it runs. A tableau sits the same distance from its opening forever — which is
exactly what a still image with waving hands looks like to this measurement. Two takes of the same
sheet returned 10% and 11%: that reproducibility is what proves the prompt is the cause and not the
dice.

Caveat: the number is only comparable **on a locked camera**. A tracking shot changes its whole
background and inflates the reading (S2PT's camera moves, which is part of why it scores so high) —
use it to compare takes of one shot, never to rank different shots against each other. And it
comes after the look, never instead of it: the eye said *the staging is timid, they are not using
the room, and the prop is buried* where "10% change" only said *it did not move*.

## Render time is a function of WHEN you generate — schedule the wave for Europe's night

Measured across a single 14-hour wave on 2026-08-13. Render time is not a constant and it is not
degrading equipment; it tracks the platform's queue depth, which tracks European waking hours.

| Local (ICT, UTC+7) | UTC | Europe (CEST) | Render |
|---|---|---|---|
| 08:36 – 13:33 | 01:36 – 06:33 | 03:36 – 08:33, night | **20–25 min** |
| 13:57 | 06:57 | 08:57, waking | **137 min, never finished — cancelled** |
| 16:26 | 09:26 | 11:26 | **50+ min** |
| 18:33 | 11:33 | 13:33, midday | worst |

**It does not degrade gradually — it changes at the hour Europe wakes up.** Every fast clip landed
while Europe was asleep; the first pathological render started at 06:57 UTC and nothing recovered
after that.

Practical consequences:

**The window is 01:00–07:00 UTC and nothing else.** Work it out from all three user bases, not just
the one that happened to break the wave:

| UTC | Europe | US East | US West | Load |
|---|---|---|---|---|
| 07:00–16:00 | **working** | morning→afternoon | morning | stacked peak |
| 16:00–01:00 | evening→night | **working** | **working** | US peak |
| **01:00–07:00** | **asleep** | **asleep** | **asleep** | **the window** |

`01:00–07:00 UTC` is **08:00–14:00 ICT** — six hours, about 14 clips at 25 minutes each.

- **Schedule long waves for 08:00–14:00 ICT.** Spawn the operator ~07:30 so the first prompt is
  staged and verified before the window opens.
- **Thai overnight is the WRONG answer** even though it feels like the natural time to run an
  unattended job. 00:00–08:00 ICT is 17:00–01:00 UTC, which is US East afternoon plus US West full
  working day — their peak, not a lull. Recorded because that was the first conclusion drawn from
  this data and it was wrong: it fitted the European evidence and ignored America entirely.
- The same queue costs 2–5x more wall-clock outside the window.
- **A slow render is not a bug.** Before investigating anything client-side, check the clock. On
  2026-08-13 an afternoon went into changing the polling method, pipelining prompt setup and
  restarting Chrome twice, all chasing a variable that lived on the platform's side.
- **The 90-minute cancel rule still applies** (hard rule 4), but expect to use it far more often
  during European daytime, and expect a normal render to take 50+ minutes rather than 25. Do not
  read that as a stuck card.
- The account's one-generation-at-a-time slot makes this compound: at 25 min a 20-clip queue is ~9
  hours, at 50 min it is ~18, and a single 137-minute zombie blocks everything queued behind it.

Credit safety is unaffected — the ledger stayed flat at $0 throughout, and a slow render costs
nothing. This is purely throughput and scheduling.

## Workers, waves and the slot

How to brief a worker, and why its checkout cannot see later commits: `CTO_Film_Production` §12
and `dev-spawn-protocol`. The rest was measured on Higgsfield waves.

### Never let the generation slot sit idle

Where video generation is unlimited, **a clip costs nothing and an idle slot costs time — and time
is the only thing a deadline actually spends.** CEO rule, 2026-08-14, and again on «Sorry, Sir» in
four words — *"อย่าให้คิว Generate ว่าง"* — after I paused a video lane to avoid making clips that
would later be re-shot. He was right: a re-shot clip is free; the hour the slot sat empty is not.
Seedance 2.0 / 1080p / 15s runs **~30 minutes per clip on average** — the CEO's own figure, stated
as the reason every idle minute is expensive even though the credits are free.

- The moment a card finishes, fire the next one immediately.
- If the *next scripted item's* prompt isn't ready yet — the CTO is still writing it — **do not wait
  idle for it.** Generate whatever *is* already written and ready instead (a spare take of a scene
  already generated, or any other queued item that has real prompt text), then come back to the
  scripted order once the CTO catches up. Example the CEO gave: the CTO is still writing Scene 12,
  but a spare take of Scene 11 is ready to fire — fire that, don't sit waiting on 12. Only stop
  firing entirely when nothing anywhere is ready to generate. **No permission needed for this, and
  it isn't capped at one extra take either** (CEO, same instruction, elaborated): while waiting on
  the next scripted prompt, re-generate an already-written scene as many times as useful, past the
  normal real+spare pair, since Unlimited costs nothing. If that scene needs 2 footage variants,
  generating more than that during idle wait time is fine too — more usable footage for the editor,
  at zero cost, is never wasted. Keep every extra take, same as always.
- Keep a standing list of shots that depend on **no** pending asset, and fire those whenever the
  queue would otherwise stall.
- Paid image generation runs alongside the unlimited video slot (hard rule 4).
- Pre-stage the next prompt while the current one renders (below).
- **Do not let a non-generating task hold the queue.** An Element-registration task ran 30 minutes
  without touching the generate slot while the account sat idle. Registration, verification and
  reporting are all free — schedule them *during* a render, never instead of one. If a task's
  remaining work does not generate, and something generatable is ready, stop it and fire the
  generation.

### When the grant is expiring: the button decides, not the clock (2026-09-11)

An Unlimited grant with an end date creates a predictable way to lose free clips, and it is the
*cautious* operator who loses them.

**The charge is decided at the moment you click, not while the render runs.** A generation fired
at 06:55 against a 06:59 deadline is free even if it lands at 07:30. So:

- **Keep firing right up to the boundary.** Do not stop early to "leave room" for a render to finish
  — that reasoning silently throws away a whole slot. On the "Sorry, Sir" grant expiry this was
  worth one extra clip out of the last hour.
- **The stop condition is the price on the button, never the time.** Struck-through price then `0`
  = fire, whatever the clock says. A live unstruck price = stop, whatever the clock says. It may
  flip before the stated deadline or after; only the pixels know.
- **Never click to find out.** If the read is ambiguous, treat it as live and stop.
- **Do not fall back to the credit lane when it flips** unless the C-level has said so for that
  specific session. "The free window closed" is not authority to start spending.

Pair this with the stage-during-render pattern below: stage the next prompt while the current one
renders, fire the instant the card completes, harvest afterwards. Harvesting needs no slot — doing
it before firing wastes ten to fifteen minutes of a slot that, near a deadline, you cannot get back.

### Operating pattern for multi-generation jobs

- **Waves are capped at ~5 generations — a hard cap, not a suggestion, and a CEILING, not a
  target.** Spawn a separate task/DEV session per wave rather than one long-running session.
  Screenshots stay in context for the rest of a session and get re-sent every later turn — capping
  wave size caps that growth, and every extra turn a long-lived DEV takes costs more than the last
  one because its own history keeps growing. **Missed 2026-08-14**: a 14-clip / 7-scene queue was
  handed to one task instead of split into three ~5-clip waves; the CEO caught it live and had it
  split mid-flight. When writing a task brief, count the clips before delegating — if it's more than
  ~5, split it before spawning, not after.
  **The floor is not one.** Measured 2026-08-30 on «Sorry, Sir»: an operator shot one scene, cited
  "the wave cap", and submitted its report, leaving the account's single generation slot idle across
  a full respawn. At one scene per worker every scene pays that respawn, which on a deadline is the
  most expensive thing an operator can do. Run the wave out to the cap unless something actually
  stops you — nothing ready to fire, a blocker, or genuinely low context. While a render is in
  flight, stage the NEXT scene's prompt so it fires the moment the slot frees. When you do stop — at
  the cap, or genuinely low on context — say in the report EXACTLY which scene is next and what state
  the composer is in, so the next operator resumes without re-deriving anything.
- **Maintain a reusable replay-helper script** (e.g. `scripts/browser/higgsfield-jumpcut-gen.js`)
  covering the mechanical flow: locate card → clear+paste prompt → verify the struck-through-then-0
  Generate button → click → poll. It deliberately does **not** auto-click
  Recreate/Unlimited-toggle/Generate itself — those three stay under a model's live tooltip/visual
  confirmation on purpose, since automating them away would defeat the safeguard that exists because
  of the incidents above. Each wave should read this script first and append new findings to it
  (numbered, dated) rather than re-deriving technique from scratch.
- **Scope discoveries are a C-level decision, not a DEV guess.** If a DEV reports something that
  changes scope (a scene count that doesn't match the brief, an undocumented content set sitting in
  History) — surface it plainly to the CEO/C-level and get an explicit call before generating
  anything against the new information. Don't reconcile it yourself.

### Never make a worker sit and watch a render (2026-08-19)

A generation runs server-side whether or not anyone watches it. A worker parked in a 90-second
sleep loop for 25 minutes produces nothing, burns context, holds a tmux session, and loses
everything it knows if it dies. **A worker's job ends the moment the generation is confirmed
fired.** Checking the finished clip is a separate, cheap action the C-level does later on a timer.

One exception: if the fire is *not* confirmable, the worker stays until it knows one way or the
other. An unconfirmed fire is the one state nobody can reconstruct after the fact.

**Better still — warm up the next job during the render** (CEO's idea, and the sharper version of
the same insight). Setup is what costs wall-clock: opening a tab, setting
model/duration/resolution/quality/aspect/sound/Unlimited, pasting a 7,000-character prompt, waiting
for mentions to resolve, counting thumbnails, verifying every field. All of that can happen while
the previous clip renders, so the actual order collapses to *read the price, click*. If there is an
approved next job, stage it; if there isn't, report and exit.

This also names the real bottleneck: warm-up only has something to chew on if approved prompts are
queued ahead of the render slot. Run the storyboard pipeline ahead of the video pipeline, always.

### The render-wait pattern (prevents silent worker death)

When a worker must wait — it has an approved next clip staged to fire the moment the slot frees, or
its fire is not yet confirmable — this is how. [SUPERSEDED 2026-08-19] waiting on a render with
nothing staged to fire next, which this pattern assumed when it was written (2026-08-12/14): with no
approved next job the worker reports and exits (above).

A DEV task once died with zero report and zero checkpoint ~34 minutes after spawn — worktree files
frozen at spawn timestamp, pid no longer running, watchdog record showing `silent_seconds: 2019`.
Root cause: it was waiting on a self-scheduled wake/notification for the long render (10-16 min
typical per generation) instead of actively polling — that mechanism does not reliably fire for a
spawned DEV subprocess, so it sat silent until an external watchdog killed it, invisible to the
C-level the whole time. Reference: task-036de9ea.

**Root cause, confirmed 2026-08-12 (task-cda4f469): a spawned DEV's shell blocks standalone
`sleep`.** This is the whole reason the failure keeps happening. The DEV is told to "wait 10
minutes", discovers it cannot sleep, and falls back to the one mechanism left to it — a scheduled
wake or background timer — which does not reliably fire for a spawned subprocess. It then sits
announcing its intention instead of doing anything. Two operators were killed on one wave for this
before the cause was found; both had been reporting "Pacing N minutes, then checking directly" every
few minutes without ever once reading a card. Do not diagnose this as laziness or insubordination —
it is an environment constraint, and the operator usually cannot see it either.

**Fix — bake all of this into every Higgsfield task brief:**

1. **Never rely on a scheduled wake, background timer, or notification.**
2. **The poll loop IS the wait.** Each cycle, actually re-read the card, the Usage page and the
   target folder. Those page reads take real wall-clock time and produce evidence instead of
   silence. Pacing is a by-product of doing the checks, not a thing to arrange before doing them.
3. If a hard delay is genuinely needed, `sleep` alone will be refused — use
   `.venv/bin/python -c "import time; time.sleep(180)"` from the worktree. **Cap any single sleep
   at ~90 seconds and repeat it, never one long block**: a longer one blocks the poll loop past the
   point where a finished render can be noticed promptly, and makes the operator unreachable (next
   section).
4. **Cadence, CEO-set 2026-08-14: first check ~20 minutes after clicking** (a render never finishes
   before ~20 min, so checking at 10 wastes a turn for nothing), **then every 5 minutes.** This
   governs how often you *look* at the render status — the 90s sleep-chunking above is unrelated and
   still applies underneath it, so you stay reachable to messages between checks without checking
   the page itself any more often than this. (Measured for Seedance 2.5 on the Unlimited lane; the
   2.0 tiers land in ~4.5 / ~3.5 min: "Model tiers".)

**Order of operations matters more than the interval: CHECK → REPORT → WAIT.** Both dead operators
inverted it (announce → wait → wake → announce) and therefore never checked anything.

**Make the reporting contract mechanical, not adjectival.** "Report concrete state, not intent" is
too vague — an operator will read "Pacing 6 minutes, then re-checking" as concrete. Instead require
three literal values in every message, including when nothing has changed:
- the literal text on the card being watched,
- minutes elapsed since the Generate click,
- the current Usage total, as a number, against a stated baseline.

A message that lacks those three is a failed report regardless of how detailed it otherwise looks.

### Pre-stage the next prompt during the wait — CEO rule, 2026-08-14

Loop, per clip: **click Generate on clip A → immediately paste clip B's prompt into the composer,
staged and ready, while A renders → sleep on the 20-then-5min cadence above → when A's card
completes, click Generate on the already-staged clip B prompt right away → repeat, staging clip C
during B's render.**

The point is to spend the render's dead time on next-prompt prep instead of doing that work cold
after waking. Editing the composer text box does not touch the in-flight render (A is already
committed server-side) and does not touch the Unlimited toggle, so this is safe to do inside the
protected composer tab.

**Staging early does not relax the checks that happen at the actual click.** Re-verify the
struck-through-then-0 Generate button and the element count fresh at the moment you click B,
exactly as if it had just been pasted — do not treat "I already checked this when I staged it" as
sufficient. The checks exist because state can change silently; a prompt sitting staged for 20+
minutes gets no exemption from that.

**A long sleep makes the operator unreachable, and that is indistinguishable from a hang.** A
foreground sleep blocks the agent's whole turn; messages the C-level types into the tab sit unread
in the input buffer until it ends. Measured 2026-08-14 (task-0ee4a20a): the operator fired Scene
10-D correctly — price check passed, all 10 chips intact — then entered a single
`time.sleep(600)`. Three CTO questions went unanswered across 83 minutes while the pid stayed alive
and the DB heartbeat kept moving. Reaching the same 10 minutes as seven 90-second sleeps would have
let it surface and answer between each one.

**Before treating a silent operator as stalled, read its tab.** It is non-invasive, costs nothing,
and shows exactly what the agent is doing — including a sleep in progress and how far through it
is:

```bash
osascript -e 'tell application "iTerm2"
 repeat with w in windows
  repeat with t in tabs of w
   set s to current session of t
   if (name of s) contains "<task-id>" then return (contents of s)
  end repeat
 end repeat
end tell' | tail -35
```

Do this BEFORE pinging again and long before killing. In the case above it immediately showed a
correct Generate click and a running sleep; the C-level had already sent three unnecessary messages
and was one step from killing an operator that was working perfectly.

### Messages to a worker

**The worker mailbox delivers notifications with no body.** Hit repeatedly across five operators in
one night: the agent sees `[New message from CTO]`, reports "no visible content to act on", and goes
back to sleep. Two operators burned 30–45 minutes each waiting on replies that had already been
sent.

**Reply through channels the operator actually reads:**
- **Append to its `TASK.md`** in the worktree. This worked every single time.
- **Comment on the GH blocker issue** it filed — operators poll their own issue.
- Send the mailbox ping too, but only as a pointer: "read the end of TASK.md".

Write this into the brief itself so the operator knows to re-read TASK.md when it gets an empty
notification.

**Every pane message kills the worker's background wait.** Workers time render polls with a
background `sleep`; typing interrupts it. One worker eventually stopped polling altogether and sat
idle waiting for me, with the slot free. **Relay only to change something. Never to ask for
status** — read its reports, its worktree commits, or `tmux capture-pane`.

### Prune the safety gates, or they compound into an hour (2026-08-19)

Every gate in this skill was bought with a real incident, and the natural instinct is to add one
each time and never remove any. On 2026-08-19 that instinct turned a single Generate click into **50
minutes**: verify four settings fresh, re-find the button rather than reuse a ref, open a separate
tab to check for stale state, walk a two-branch decision tree, reapply the desync fix. Every one of
those was individually justified. Stacked unconditionally, they were absurd, and the generate queue
sat idle the whole time.

Split them, and run only the first group every time:

- **Money gates — always, no exceptions.** Read the price on the button immediately before the
  click. Confirm the reference thumbnail count. Confirm the quantity stepper. These prevent
  spending, and spending is not recoverable.
- **Diagnostic gates — only when something already looks wrong.** Fresh-tab stale-state checks,
  decision trees for branch cases, re-verifying settings that were verified two minutes ago and
  nothing has touched since. These are for debugging a symptom, not a preflight ritual.

When a brief grows past roughly a screen of checks, that is the signal to prune, not to add. And say
in the brief which gates are mandatory and which are conditional — a worker given a flat list will
run all of them, correctly, forever.

### Task-brief checklist

When writing a `create_task` description for a Higgsfield `browser_operator` task, include:
- [ ] The 7 hard rules, verbatim or paraphrased — especially the Rerun ban, the struck-through
      price check (rule 2's table), paste-only text entry, and the check-Usage-History-after-any-error
      rule.
- [ ] The project URL (Rule 0) and the desktop-width check.
- [ ] The editor gotchas if the task involves writing new prompt text.
- [ ] The 20-then-5-minute poll cadence for any render wait, and whether the worker stays for a
      staged next clip or exits at the confirmed fire.
- [ ] Explicit scope boundaries — what NOT to touch (other scenes, other projects mixed into the
      same History, the tracking artifact).
- [ ] Stop-and-ask conditions: a live (unstruck) price on the Generate button, an NSFW flag
      repeating, a result needing creative/brand judgment, anything about the page behaving
      unexpectedly, any browser-tool error while on a Higgsfield page.
- [ ] Which safety gates are mandatory and which are conditional.
- [ ] Pointer to the existing replay script if one exists for this project.

[SUPERSEDED] two items of the original checklist: "the 10min → 5min → 3min-repeating poll schedule"
(replaced by the CEO's 20-then-5 cadence of 2026-08-14) and "any number on the Generate button" as a
stop condition (replaced by rule 2's strike-through reading, CEO 2026-09-02).

## Uploading project assets (audio into a project folder) — measured 2026-09-09 (task-c44853c9)

The festival rules want every audio file inside the submission project. What actually works from a
browser_operator:

1. **Create the folder** from the project's LEFT sidebar "Add folder" → modal "New Folder" → type the
   name (placeholder "My folder") → "Create". Folders then show in that sidebar next to the
   auto-made Watermarks folder.
2. **`mcp__claude-in-chrome__file_upload` only reads files the session may read.** A path under
   Downloads is refused ("only files this session is allowed to read can be uploaded"). Copy the
   file into the session's own scratchpad directory first, then upload from there — no `/add-dir`
   prompt.
3. **Use the top-banner Upload input** (`accept=""`) on the folder page. The composer's References
   picker is a different file input on the same page (`accept="image/*,video/mp4,...,audio/*"`) and
   attaches the file as a generation reference instead of a project asset.
4. **Hard cap ~10 MB per `file_upload` call**, enforced by the browser bridge, not by Higgsfield;
   batching does not help. Anything larger must be transcoded under 10 MB (WAV → MP3 320k lands a
   100 s cue at ~4 MB) or dragged in by a human. Uploads are free; the asset counter rises by exactly
   the number of files landed — read it before and after.

## Reference

- Incident + full fix history: mooniex-agents task-eed61860 (Wave 1, credit incident),
  task-1ecf3dd2 (Wave 2), task-76d3ce0d (Wave 3), task-036de9ea (Wave 4, silent-death incident),
  task-7b4402d4 (keystroke-timeout auto-fire, Incident 2 above). GH issue #45, #47.
- Valder wave findings (2026-08-19, `ai-film-festival-3`, project `project_valder_*`): five stalls
  on UI behaviour no brief anticipated; each fix is in the section it belongs to.
- Related skills: `browser-operator` (generic browser cost-discipline), `dev-spawn-protocol`
  (generic DEV spawn steps), `blender-previz` (the `@Video 1` previz), `CTO_Film_Production` (the
  film), `CTO_Film_PromptFormat` (the prompt file).
- Moved here on 2026-09-25 from `higgsfield-unlimited-gen` and `ai-film-production` (both now
  redirect stubs). Hard rules 1-7 keep their numbers.

## Field notes
