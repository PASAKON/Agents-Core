---
name: higgsfield-unlimited-gen
description: Domain-specific safety rules and operating patterns for driving Higgsfield.ai (Seedance/AI video generation) in Unlimited Mode, where real credits must never be spent by accident. Trigger on /higgsfield-unlimited-gen and proactively whenever a C-level is about to delegate or drive browser work on higgsfield.ai, or when the request mentions "Higgsfield", "Seedance", "Unlimited mode video gen", "AI video generation credits", "jump-cut pass", or a Higgsfield History/Recreate/Rerun button. Supplements — does not replace — `browser-operator` (generic browser cost-discipline) and `dev-spawn-protocol` (generic DEV spawning): follow both of those plus everything here for any Higgsfield task. Do NOT fire for video generation on other platforms (fal.ai, Kling, Veo) — those have their own cost rules elsewhere.
---

# Higgsfield Unlimited-Mode Generation — Safety Rules

Every rule below was learned from a real incident in this org, not written
speculatively. Follow `browser-operator`'s general discipline (text-first,
zoom over screenshots, replay scripts) and `dev-spawn-protocol`'s spawn steps
first — this skill adds the Higgsfield-specific layer on top.

## What it does

Gives any C-level (CTO, CMO, CFO, CGO) driving or delegating Higgsfield.ai
video generation the exact button-level rules, editor gotchas, and wait
pattern that prevent (a) accidentally spending real credits when the task
must run Unlimited-only, and (b) a spawned DEV silently dying during a long
render wait.

## When to invoke

- Before delegating any `browser_operator` task whose target is
  `higgsfield.ai`.
- Before writing a task brief that mentions Seedance, Unlimited Mode, jump-cut
  generation, or a "Recreate"/"Rerun" History card.
- Before a C-level personally drives Higgsfield in Chrome for any reason.
- When continuing/resuming a multi-wave Higgsfield generation job started in
  a prior session.

## When NOT to invoke

- Video/image generation on any other platform (fal.ai, Kling, Veo, MeiGen,
  Nano Banana) — those aren't Higgsfield and don't share these UI traps.
- Higgsfield work that is explicitly credit-based/paid by design (not this
  org's normal mode) — if a task genuinely intends to spend credits, that's
  an `feedback_ask_before_paid_api` conversation with the CEO, not this skill.

## The incident this is built from

A DEV clicked **"Rerun"** on a History card, intending only to load its
references into the composer for editing. Rerun does two things at once with
**zero confirmation step**: loads the prompt into the composer, AND
immediately fires a new generation of the unmodified original prompt — at
whatever pricing is currently showing, completely independent of the
Generate button or the Unlimited Mode toggle. It cost **130 real credits**,
confirmed via Higgsfield's own Usage History log (Account Settings → Usage):
one entry that day read `130 credits · Seedance 2.5 · Spent`, every other
entry that day read `Unlimited Seedance 2.5 · Spent` ($0). Reference:
mooniex-agents task-eed61860, GH issue #45.

## Hard rules — non-negotiable, no exceptions

1. **Never click "Rerun"** (↻ icon, bottom-left row on a History/generation
   card). Banned entirely on every Higgsfield task, forever. It auto-fires a
   generation with no confirmation.
2. **Use "Recreate" instead** (copy icon, top-right of the video thumbnail,
   appears on hover — confirm via its tooltip text before clicking) to load
   a card's prompt + references into the composer for editing. This does
   NOT fire anything by itself.
3. **Before every single Generate click, with no exceptions**: zoom into the
   Generate button itself and confirm it reads bare **"Generate"** with
   **ZERO digits anywhere on it** (not "Generate ✦ 130", not any number). If
   any number shows, do not click — stop and message the C-level. The
   Unlimited Mode toggle's apparent on/off state is **not sufficient on its
   own** — it silently resets to OFF after any full-page reload, which is
   the exact gap that caused the incident above.
4. **One generation at a time.** Wait for full completion (card shows
   Recreate+Rerun options and full resolution/duration/aspect-ratio
   metadata, no "Processing"/"Generating" state) before starting the next.
   No parallel generations, ever.
5. **Concurrency toast with no visible in-flight job**: if Higgsfield shows
   a "1 unlimited generation at a time" toast and nothing in your own
   History is actually generating, don't force through it or guess a
   workaround. Message the C-level and wait.

## Editor gotchas (Higgsfield's prompt box is Lexical/contenteditable)

- **Clearing**: use a real Cmd/Ctrl+A + Delete keypress via the driving
  tool. `document.execCommand('selectAll')`/`delete` does **not** actually
  clear it — measured behavior is append, not replace.
- **Entering text**: synthetic `ClipboardEvent` paste with
  `DataTransfer.setData('text/plain', ...)` **only**. Also setting
  `text/html` causes a double-paste bug (content inserted twice). Verify the
  resulting text length before ever touching Generate.
- **Recreate button reliability**: its on-screen position shifts with
  thumbnail width (cards with different reference-image counts render
  different thumbnail widths), and it only mounts in the DOM on real hover,
  not just CSS-hidden — hover-then-verify via tooltip text every time,
  don't trust a fixed coordinate or a cached element reference. A click can
  also silently no-op even on a DOM-valid reference for no clear reason —
  verify the composer actually loaded the target card's distinctive text
  before proceeding, retry once if not.
- **History pagination**: the list is server-paginated, not just
  virtualized — `scrollHeight` grows as you scroll toward the bottom
  (measured: 24k→48k→72k+ px). Don't assume a fixed scene/card count from
  what's initially rendered; scroll to the true end and re-read before
  concluding "that's everything."

## The render-wait pattern (prevents silent DEV death)

A DEV task once died with zero report and zero checkpoint ~34 minutes after
spawn — worktree files frozen at spawn timestamp, pid no longer running,
watchdog record showing `silent_seconds: 2019`. Root cause: it was waiting
on a self-scheduled wake/notification for the long render (10-16 min
typical per generation) instead of actively polling — that mechanism does
not reliably fire for a spawned DEV subprocess, so it sat silent until an
external watchdog killed it, invisible to the C-level the whole time.
Reference: task-036de9ea.

**Fix — bake this into every Higgsfield task brief:** never rely on a
scheduled-wake/timer/notification for the render-wait step. Use an active
sleep-and-check loop instead:
- First check after **10 minutes**.
- Second check **5 minutes** after that.
- Every **3 minutes** after that until the card shows completion.

This produces periodic visible activity instead of one long silent gap that
looks indistinguishable from a crash.

## Operating pattern for multi-generation jobs

- **Split into waves capped at ~5 generations each**, spawned as separate
  tasks/DEV sessions rather than one long-running session. Screenshots stay
  in context for the rest of a session and get re-sent every later turn —
  capping wave size caps that growth.
- **Maintain a reusable replay-helper script**
  (e.g. `scripts/browser/higgsfield-jumpcut-gen.js`) covering the mechanical
  flow: locate card → clear+paste prompt → verify zero-digit Generate
  button → click → poll. It deliberately does **not** auto-click
  Recreate/Unlimited-toggle/Generate itself — those three stay under a
  model's live tooltip/visual confirmation on purpose, since automating
  them away would defeat the safeguard that exists because of the incident
  above. Each wave should read this script first and append new findings to
  it (numbered, dated) rather than re-deriving technique from scratch.
- **Scope discoveries are a C-level decision, not a DEV guess.** If a DEV
  reports something that changes scope (a scene count that doesn't match
  the brief, an undocumented content set sitting in History) — surface it
  plainly to the CEO/C-level and get an explicit call before generating
  anything against the new information. Don't reconcile it yourself.

## Task-brief checklist

When writing a `create_task` description for a Higgsfield `browser_operator`
task, include:
- [ ] The 5 hard rules above, verbatim or paraphrased — especially the
      Rerun ban and the zero-digit Generate check.
- [ ] The editor gotchas if the task involves writing new prompt text.
- [ ] The 10min → 5min → 3min-repeating poll schedule for any render wait.
- [ ] Explicit scope boundaries — what NOT to touch (other scenes, other
      projects mixed into the same History, the tracking artifact).
- [ ] Stop-and-ask conditions: any number on the Generate button, an NSFW
      flag repeating, a result needing creative/brand judgment, anything
      about the page behaving unexpectedly.
- [ ] Pointer to the existing replay script if one exists for this project.

## Reference

- Incident + full fix history: mooniex-agents task-eed61860 (Wave 1, credit
  incident), task-1ecf3dd2 (Wave 2), task-76d3ce0d (Wave 3), task-036de9ea
  (Wave 4, silent-death incident). GH issue #45.
- Related skills: `browser-operator` (generic browser cost-discipline),
  `dev-spawn-protocol` (generic DEV spawn steps).
