---
name: google-flow-ops
description: >-
  Operating rules for driving Google Flow (labs.google / flow.google.com, Veo
  3.1) — the measured click path, the credit costs, the traps that silently
  waste a generation, and what the product simply does not have. Trigger on
  /google-flow-ops and proactively whenever a C-level is about to delegate or
  drive browser work on Google Flow, or the request mentions "Google Flow",
  "Veo", "Ingredients to Video", "Scenebuilder", "Flow credits", or generating
  video on the CEO's Google AI subscription. Supplements — does not replace —
  `browser-operator` (generic browser cost discipline) and
  `dev-spawn-protocol`. Do NOT fire for Higgsfield/Seedance work
  (`higgsfield-unlimited-gen` owns that) or for fal.ai / Grok / Kling.
---

# Google Flow — operating rules

**v1, seeded 2026-09-07 from task-796a93f6 (one full recon walk, 40 credits).**
Everything below was measured on the CEO's own account, not read off a blog.
Where a number is unmeasured it says so.

This file is the Flow equivalent of `higgsfield-unlimited-gen`. It exists so the
second worker does not have to rediscover what the first one paid to learn.

## Money — the rules that come before everything

- Flow spends the CEO's **monthly Google AI credit pool**. There is no separate
  Flow subscription. Credits **do not roll over**.
- **Never click Upgrade / Subscribe / Buy credits / Get more credits.** A
  paywall or upsell gets closed with its own `x` and quoted verbatim in the
  report.
- **Read the balance before you start and after every action that might cost.**
  The balance lives in the account menu as `เครดิต Google Flow N เครดิต`.
  Record the delta. The deltas are a deliverable, not a formality.
- **Read the live credit estimate in the settings panel immediately before
  clicking Submit.** It updates as model / resolution / duration / quantity
  change, and those settings are not sticky (see Traps).
- Never select **Quality** unless the task names it. One Quality click is 100
  credits — five Fast shots.

## Measured costs (2026-09-07)

| Action | Credits |
|---|---|
| Create a project | **0** |
| Generate a Character / Ingredient image (Nano Banana Pro, 4:5) | **0** — measured 4 times |
| Attach ingredient chips | 0 |
| Navigate any tab (Scenes, Tools, Agent) | 0 |
| **Veo 3.1 Fast — 8s, 720p, 9:16, x1** | **20** — measured twice, matched the published table exactly |
| Veo 3.1 Lite | 10 (published, not yet measured here) |
| Veo 3.1 Quality | 100 (published; visible in the panel, never selected) |
| Download / re-export a clip | 0 |

**Image generation being free is the most valuable fact in this file.** Make
every character, prop and location plate in Flow, download them, and spend
credits only on video.

Unmeasured and worth measuring on the next run: whether **scene/location** plates
are also 0 credits (only *character* images were measured), and whether Lite is
really 10.

## The shortest path — 12 steps, do them in this order

1. Open a **fresh tab**. `flow.google.com` (labs.google/fx/tools/flow redirects
   there). Chromium browsers only.
2. `resize_window` to 1024x768 — **and know it only takes effect after a full
   page navigation**, not on the initial load. Resize, then navigate.
3. Read and record the credit balance from the account menu.
4. New project → type the name.
5. Characters tab → New Character → paste the reference prompt → model
   **Nano Banana Pro** → generate (free) → rename to the handle. Repeat per
   character/prop/location.
6. Back in the composer, set the model to **Veo 3.1 - Fast**. It does not
   persist — see Traps.
7. Set aspect ratio **9:16** and quantity **x1**. Neither is sticky.
8. `+` picker → click each character → a chip appears above the prompt box.
9. **Count the chips before you fire.** The picker hides characters that are
   already attached, so an attached character is one that has *disappeared*
   from the list. A missing chip means the shot generates with no reference
   and nobody finds out until the frames are reviewed.
10. Paste the prompt. Verify the Thai text survived, byte for byte, by reading
    `innerText` of the `[contenteditable="true"]` element — do not trust the
    visual.
11. Re-read the live credit estimate, then click Submit (icon-only,
    `aria-label="Submit"`).
12. Wait, then download via the top-toolbar download icon or right-click →
    ดาวน์โหลด.

## Measured timings — extend this table on every run

| Action | Time | Source |
|---|---|---|
| Veo 3.1 Fast 8s render, run 1 | **~51 s** | task-796a93f6 |
| Veo 3.1 Fast 8s render, run 2 | **~94 s** | task-796a93f6 |
| Second clip's export | hung indefinitely; a full page reload then a retry completed it ~15 s later | task-796a93f6 |
| Full walk: project + 4 characters + 2 videos + downloads | ~40 min, well over a 30-action budget | task-796a93f6 |

**Every Flow task must record wall-clock per action and append to this table.**
An operator that reports "it took a while" has failed the reporting bar.

## Traps — each one silently costs a generation

| Trap | What happens | What to do |
|---|---|---|
| **Chips drop silently** | Expanding the prompt textbox, or clicking the composer's `x`, clears **every attached ingredient chip** with no warning. Happened twice in one hour. | Re-count chips via the `+` picker immediately before every Submit. Never fire off a remembered chip state. |
| **Model resets** | Switching tabs or reloading silently returns the model to the account default (Omni 1.1 Flash). | Re-select Veo 3.1 - Fast and read it back before every fire. |
| **Aspect and quantity are not sticky** | 9:16 and x1 revert across prompt sessions. | Set and verify both every time. |
| **Export hangs** | "Exporting your scene…" can sit forever. | Full page reload, then click download again. Costs nothing but time. |
| **resize_window is late** | Applies only after a navigation; early screenshots come out at ~1456x840 and cost far more visual tokens. | Resize, navigate, then screenshot. |

## What Flow does NOT have — stop looking for these

Verified absent across the toolbar, right-click menu, share panel, fullscreen
player, model dropdown and filter panel:

- **No first-frame or last-frame slot.** This is the big one: frame chaining,
  the technique that holds a set steady between shots, is **API-only**. Flow can
  shoot disconnected beats; it cannot shoot a continuous scene.
- **No 1080p and no upscale control** on the account tested. The asset
  resolution facet offers only 720p and 360p, and both exports came out
  720x1280. Google's own credit table lists "1080p upscale = 0 credits" — it
  could not be reproduced. Treat 1080p in Flow as unavailable until someone
  finds the control.
- **No pre-generation storyboard.** The Scenes ("ฉาก") tab is a passive gallery
  of media that already exists. There is no empty ordered slot, no shot list,
  no way to plan a sequence before generating it.
- **No whole-episode export.** Per-clip download only. Assembly happens outside.
- **No batch or queue.** One fire, one wait, every time.
- **No saved prompt templates.** Google's example cards are presets, not
  user-savable.
- **No audio upload.** Dialogue and ambience are prompt text only; you cannot
  supply a voice track.
- **No public API from inside the product.** The closest surface is the in-app
  **Agent** mode with an "Instructions for Agent" panel and a global Agent
  Settings page offering confirm-every-time vs fully-autonomous. Unexplored —
  the next operator with budget should map it, because it is the only
  automation-shaped thing in the UI.

## Contested — do not state these as fact

- **The 3-ingredient ceiling.** Google's blog says up to three references per
  prompt, and the API documents `referenceImages` max 3. But the Flow UI
  accepted **four** chips with no error, no greying and no silent drop
  (confirmed by DOM inspection and a page-wide search for limit language).
  Whether a ceiling is enforced at *generation* time is **untested** — settling
  it costs one Lite generation (10 credits) and is worth doing.

## How this file changes

A worker who finds a rule here to be wrong does **not** edit this file — workers
cannot write skills. It reports the contradiction in its own report, in this
shape, and the C-level updates the skill:

```
SKILL-CONTRADICTION: google-flow-ops :: <the rule as written>
  :: <what actually happened, with the evidence>
  :: <date, task id>
```

A contradiction backed by a screenshot or a DOM read wins over anything written
here. A contradiction backed by a memory does not.
