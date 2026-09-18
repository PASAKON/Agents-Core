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
| Generate a SCENE / LOCATION plate | **0** — confirmed 2026-09-07, task-46e7c41b, cost-probe first |
| Attach ingredient chips | 0 |
| Navigate any tab (Scenes, Tools, Agent) | 0 |
| **Veo 3.1 Fast — 8s, 720p, 9:16, x1** | **20** — measured twice, matched the published table exactly |
| Veo 3.1 Lite | 10 (published, not yet measured here) |
| Veo 3.1 Quality | 100 (published; visible in the panel, never selected) |
| Download / re-export a clip | 0 |

**Image generation being free is the most valuable fact in this file.** Make
every character, prop and location plate in Flow, download them, and spend
credits only on video.

Scene/location plates were confirmed free on 2026-09-07 (task-46e7c41b) by
generating one image first and re-reading the balance: 210 -> 210. Still
unmeasured: whether Lite video is really 10.

**Every still this production needs is free.** Spend credits only on video.

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
8. **Attach the ingredients — and this is the hardest thing in the product.**
   Clicking a character tile in the `+` picker **navigates to that character's
   editor page**; it does not insert a chip. The only path that inserts a real
   chip (`<span class="mention-chip" data-entity-id="...">`) is:

   > tile's `⋮ more options` menu → click the **inner
   > `<span class="label">เพิ่มไปยังพรอมต์</span>` node**, not the outer
   > `<button>`

   The outer button carries stray `mat-mdc-menu-trigger` / `aria-expanded`
   attributes and **silently no-ops** on every method tried: real click, JS
   `.click()`, pointerdown/up+click dispatch, and ArrowDown+Enter keyboard nav.
   Even the correct inner-span target succeeded roughly **once in fifteen
   attempts** on 2026-09-07 — the insertion is racy in a way no operator has
   characterised yet. Budget for this. It cost task-46e7c41b most of its hour
   and blocked six planned stills entirely.

   The earlier recon (task-796a93f6) attached chips, including four at once,
   without difficulty — so this is flaky, not impossible. Treat a failed
   attach as normal and retry rather than as a blocker.
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
| First page load of flow.google.com incl. resize | 50 s | task-46e7c41b |
| Reading the credit balance from the account menu | ~115 s (2 failed menu-toggle attempts) | task-46e7c41b |
| **Still image generation, submit -> image visible** | **32 / 38 / 40 / 48 s** (4 samples, Nano Banana Pro) | task-46e7c41b |
| Renaming a Character | 286 s (UI fought back) | task-46e7c41b |
| Downloading one image | 25 / 82 / 85 / 266 s — wildly variable; two needed a fresh tab | task-46e7c41b |
| Full still-plate session (4 images made, 6 blocked) | **~70 min**, over its 60-min budget | task-46e7c41b |

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
| **The viewport reverts mid-session** | A correctly-resized tab silently went back to 2280x722 with no navigation in between. Screenshot pixels and `window.innerWidth` then disagreed by a ~0.688 scale factor (1568px shot for a 2280px CSS viewport). | Never click from raw `getBoundingClientRect()` coordinates. Click by element handle, or convert by the measured ratio. |
| **A focused contenteditable still drops the first keystroke** | A `.ProseMirror` composer confirmed as `document.activeElement` lost the next keystroke about half the time — text stayed as the placeholder, no error, no state change. | `el.focus()` via `javascript_tool` and the first keystroke via `computer` **in the same `browser_batch` call**, with no intervening tool call, not even a read. This single behaviour cost most of one task's budget. |

## What Flow does NOT have — stop looking for these

Verified absent across the toolbar, right-click menu, share panel, fullscreen
player, model dropdown and filter panel:

- ~~No first-frame or last-frame slot~~ — **WRONG, retracted 2026-09-07.**
  See "Start and end frames" below. The CTO inferred this from an operator's
  silence rather than from a measurement, told the CEO frame control was
  API-only, and the CEO found the control himself in about a minute. Do not
  repeat the mistake: an operator not mentioning a feature is not evidence the
  feature is absent.
- **No 1080p and no upscale control** on the account tested. The asset
  resolution facet offers only 720p and 360p, and both exports came out
  720x1280. Google's own credit table lists "1080p upscale = 0 credits" — it
  could not be reproduced. Treat 1080p in Flow as unavailable until someone
  finds the control.
- **No shot-list style storyboard.** There is still no way to type a shot list
  or order empty slots. But the Scenes ("ฉาก") tab is **not** the passive
  gallery the first recon called it — it is where the frames that feed the
  start/end slots are made. See below.
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

## Start and end frames — they DO exist in the web UI

Confirmed by the CEO from his own screen, 2026-09-07. The composer carries two
chips side by side with a swap arrow between them, sitting directly above the
"คุณต้องการสร้างอะไร" prompt field:

```
[ เริ่ม ]  ⇄  [ สิ้นสุด ]          เริ่ม = start frame,  สิ้นสุด = end frame
```

### The exact path (task-ecca0bc3, measured)

```
composer → settings pill (bottom-right, shows model/mode)
        → วิดีโอ tab
        → submode toggle:  [ เฟรม ]  [ องค์ประกอบ ]
```

**The default is `องค์ประกอบ` (Ingredients).** That single default is why the
first recon reported the feature as absent — it is one click away from the
chip UI, not hidden in a menu.

Click **`เฟรม`** and the composer's whole attach area is replaced by two slots:
`เริ่ม` (start) and `สิ้นสุด` (end), with a swap control between them whose
accessible name is `สลับเฟรมแรกและเฟรมสุดท้าย` — "swap first frame and last
frame".

### ⛔ THE CONSTRAINT THAT SHAPES EVERY SHOT: เฟรม and องค์ประกอบ are mutually exclusive

They are a **single-select toggle**. Choosing `เฟรม` removes the chip row and
the `+` ingredient picker entirely. Choosing `องค์ประกอบ` removes the frame
slots.

**In Flow you get consistent faces OR a consistent set. Never both in one
generation.**

| Mode | You lock | You lose |
|---|---|---|
| `องค์ประกอบ` | up to 3 characters/props | frame control — the set drifts |
| `เฟรม` | the exact opening (and closing) image | character references — faces drift |

This is a **Flow UI limit, not a Veo limit**. The API takes `image`,
`lastFrame` and `referenceImages` as separate parameters and accepts all of
them together. For any production that needs recurring faces in a recurring
place, that difference is the whole argument for scripting against the API.

Per-shot workaround inside Flow: pick the mode by what matters in that shot.
A face held in frame needs `องค์ประกอบ`. A wide, a cutaway, an object, a back
of a head, a shot that must cut cleanly from the last one — `เฟรม`.

### What the frame picker will actually show you

Clicking `เริ่ม` opens a dialog titled `เลือกรูปภาพเฟรม` with a project-scoped
dropdown, a search box and a sort control. It has **no upload button and no
drop zone**.

**Character/Ingredient-tagged images are EXCLUDED from this picker.** A project
holding only Characters shows `ไม่พบชิ้นงาน` — "no items found". A plain
untagged image generated in Image mode appears immediately and is selectable.

So: **a plate you want to use as a frame must be generated as a plain image in
Image mode, NOT saved as a Character.** An image can serve one role or the
other, not both. Plan which role each plate plays before you make it.

Uploading from disk: the project's `เมนูเพิ่มสื่อ` (Add media) menu has an
`อัปโหลด` item, but a trusted click on it opens an **OS-native file dialog**
(`document.hasFocus()` goes false, no `<input type="file">` ever enters the
DOM — consistent with `showOpenFilePicker()`). Neither the extension's
`file_upload` tool nor a synthetic JS click can drive it. Whether an uploaded
file then appears in the frame picker is **plausible but unverified**. Do not
plan around disk upload until someone proves it.

### Cost in เฟรม mode

The live estimate reads `การสร้างใช้ 20 เครดิต` — identical to `องค์ประกอบ`
mode for the same Veo 3.1 Fast / 9:16 / x1 config. Measured with both slots
empty; a before/after delta with an image actually attached is still unmeasured.

## Left sidebar — what each tab is for

`สื่อทั้งหมด` all media · `วิดีโอ` videos · `ตัวละคร` characters (Ingredients) ·
**`ฉาก` scenes — the start/end frame source** · `เครื่องมือ` tools ·
`ถังขยะ` trash · `ยุบ` collapse.

## Composer settings row — what it shows

`Agent` toggle on the left; on the right `วิดีโอ · 720p · 8 วินาที · [aspect] · x1`
and the submit arrow. 720p is the ceiling shown on a PLUS account.

## Account tier

The CEO's account badge reads **PLUS** (Google AI Plus), not Pro — visible
top-right beside the avatar. That means **200 credits per month**, i.e. ten
Veo 3.1 Fast clips. Plan every shoot against 200, not 1,000.

## Contested — do not state these as fact

- **The 3-ingredient ceiling.** Google's blog says up to three references per
  prompt, and the API documents `referenceImages` max 3. But the Flow UI
  accepted **four** chips with no error, no greying and no silent drop
  (confirmed by DOM inspection and a page-wide search for limit language).
  Whether a ceiling is enforced at *generation* time is **untested** — settling
  it costs one Lite generation (10 credits) and is worth doing.

## Mid-session Google sign-out — it looks exactly like Flow being flaky

Observed 2026-09-07, task-4a59a1a4. The Chrome profile lost its Google session
part-way through a run. Every route — the direct project URL, the bare root,
a reload, a brand-new tab — silently redirected to the `/about` marketing
splash. Flow's own chrome never said "please sign in". It reads as a routing
bug and can burn ten minutes of debugging.

**The one-second test:** open `google.com` and look at the top-right corner.
An avatar means signed in; a "Sign in" button means the session is gone.
`myaccount.google.com` and `accounts.google.com/ServiceLogin` confirm it.

If signed out: **do not sign in.** File a blocker and stop — credentials are a
hard stop for this role, and only the CEO can restore the session.

Note that Higgsfield and other sites in the same Chrome keep working normally
when this happens, so "another operator is fine" is not evidence your session
is fine. Each site's login is independent.

## The MCP tab group can be destroyed mid-action

Once during the same run, `tabs_context_mcp` returned "No tab group exists for
this session" immediately after a submit click. The submit never reached
Google. Recovery: open a fresh tab, re-navigate, and **re-verify the composer
state from scratch** — the prompt text, the mode, and every chip. Never assume
a pre-destruction state survived.

Suspected contributing factor: four browser_operators were sharing this Chrome
at the time. Two is the org's working limit; beyond that, expect tab churn.

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


## Voices — lock one per character BEFORE shooting any dialogue (CEO 2026-09-08)

A drama dies if the father sounds like a different man each scene. Flow can fix
that, and the fix is a setup step, not a per-shot step. **Install a voice on
every speaking character first. Only then shoot dialogue.** A series that starts
shooting before its voices are fixed pays for those shots twice.

What Google documents (support.google.com/flow/answer/16353334):

- **Add (+) → Voices**, in the ingredients section.
- Preset voices, each with a free 10-second sample: hover, then click Play.
- **Custom voice**: choose a base preset, name it, and *describe* the change
  ("Make the voice sound slightly raspy with a New York accent").
- "To maintain a specific character's voice across multiple video clips, add a
  single-speaker voice reference to your prompt."
- Voice references work **only on generations that use ingredients**. A
  frame-only (เฟรม) shot cannot carry one, and errors if you try.
- Requires the model **Gemini Omni Flash 1.1**, not Veo 3.1 Fast.

Two rules that follow, and are not negotiable:

1. **A worker has no ears.** Never pick a voice by listening, never infer a
   voice's gender or age from its name, never write "sounds about right" in a
   report. Either use the custom-voice path and *describe* the voice in words
   (the description is text, which a worker can write and verify), or capture
   the preset list verbatim and let the CEO listen and name the choice. Copy UI
   strings exactly; do not translate them.
2. **One voice, one character, written down.** Record the chosen voice name (and
   the exact custom description) next to that character's APPEARANCE LOCK in the
   script, the same way the look is locked. A voice that lives only in someone's
   memory of a preview will not survive the next session.

## Casting a voice — the rules, the whole voice list, and the ledger (CEO 2026-09-08)

Everything needed to cast a voice is on this page. **Do not search the web for
it** — Google's own API docs are thinner than what is here (one adjective per
voice, no gender, no pitch), and the Flow UI labels below were read off the
CEO's own account.

### Rules

1. **One voice per character, and never the same voice twice in one story.**
   Two characters sharing a preset will read as the same person the moment they
   share a scene. Check the cast ledger before assigning.
2. **The C-level casts, not the worker.** The voice goes into the brief by name;
   a worker may only report that a preset is missing, never substitute on taste.
   A worker has no ears and must never claim it heard anything.
3. **Write it into the script** as a `VOICE LOCK:` line under the character's
   `APPEARANCE LOCK`, before any dialogue shot is fired.
4. **The CEO's ear is the only real evidence.** The labels get us a shortlist;
   the 10-second previews are free and speak Thai, so a doubtful cast is settled
   by listening, not by arguing from adjectives.
5. **Score every verdict in the ledger.** A voice the CEO keeps earns +1. A voice
   the CEO orders changed earns −1. At −2 a voice is retired for that kind of
   role and must not be proposed again.

### Casting criteria, and which parts are guesses

In priority order:

1. **Sex must match the character.** The one field that is unambiguous data.
2. **Pitch band as a stand-in for age** — low for an older man, mid-low for a
   young man. **This is an inference, not data.** Nothing in Google's labels ties
   pitch to age; it is simply the best proxy available.
3. **The tone word separates characters who share a scene.** The father is
   gravelly and the lender smooth so they never blur together.
4. **Reject tone words that fight the character.** No "lively", "upbeat" or
   "excitable" for a man who is exhausted.

**What the labels do not contain: age, accent, or how well the voice handles
Thai.** Only three of the thirty carry any age signal at all — Gacrux "mature",
Leda "youthful", Fenrir "younger pitch" — and none of those three is a male
voice, so there is no documented "old man" preset to pick. Thai is listed as a
supported language, with nothing said per voice.

### All 30 presets, as the Flow picker labels them

| Voice | Label (verbatim) |
|---|---|
| Achernar | Female, soft, high pitch |
| Achird | Male, friendly, mid pitch |
| Algenib | Male, gravelly, low pitch |
| Algieba | Male, easy-going, mid-low pitch |
| Alnilam | Male, firm, mid-low pitch |
| Aoede | Female, breezy, mid pitch |
| Autonoe | Female, bright, mid pitch |
| Callirrhoe | Female, easy-going, mid pitch |
| Charon | Male, informative, lower pitch |
| Despina | Female, smooth, mid pitch |
| Enceladus | Male, breathy, lower pitch |
| Erinome | Female, clear, mid pitch |
| Fenrir | Male, excitable, younger pitch |
| Gacrux | Female, mature, mid pitch |
| Iapetus | Male, clear, mid-low pitch |
| Kore | Female, firm, mid pitch |
| Laomedeia | Female, upbeat, mid-high pitch |
| Leda | Female, youthful, mid-high pitch |
| Orus | Male, firm, mid-low pitch |
| Puck | Male, upbeat, mid pitch |
| Pulcherrima | Ungendered, forward, mid-high pitch |
| Rasalgethi | Male, informative, mid pitch |
| Sadachbia | Male, lively, low pitch |
| Sadaltager | Male, knowledgeable, mid pitch |
| Schedar | Male, even, mid-low pitch |
| Sulafat | Female, warm, mid pitch |
| Umbriel | Male, smooth, lower pitch |
| Vindemiatrix | Female, gentle, mid pitch |
| Zephyr | Female, bright, mid-high pitch |
| Zubenelgenubi | Male, casual, mid-low pitch |

### Cast ledger

Update this the moment the CEO reacts to a voice. Score starts at 0 and moves
±1 per verdict; the "verdict" column stays "pending ear" until a human has
actually listened.

| Story | Character | Voice | Score | Verdict |
|---|---|---|---|---|
| เงินที่พ่อตั้งใจหา | @lung_somchai (M, 58) | Algenib | 0 | pending ear — heard in shot58-omni |
| เงินที่พ่อตั้งใจหา | @nong_daeng (M, 24) | Iapetus | **+1** | **KEPT — CEO listened 2026-09-18, "เสียงถูกแล้ว"** |
| เงินที่พ่อตั้งใจหา | @grandma_pranom (F, 79) | Gacrux | 0 | pending ear |
| เงินที่พ่อตั้งใจหา | @lender_cherd (M, 45) | Umbriel | 0 | pending ear |

Shortlist held in reserve for an older-sounding man, if Algenib is rejected:
Enceladus (breathy, lower), Charon (informative, lower). Sadachbia is the only
other male at the lowest pitch band but "lively" fights the character.

## Sound: what can be steered and what cannot (2026-09-08)

The CEO's plan is to score the series in Suno and ElevenLabs, so what Flow needs
to deliver is the sound that genuinely happens in the scene, and nothing else.

**There is no off switch.** Omni Flash does not support negative prompts at all,
the Gemini API's Veo parameters carry no negativePrompt, and there is no mute,
no level control and no way to separate the audio Veo bakes into the clip.

What works instead:

- **Name only the diegetic sounds, positively.** Keep the script's
  `Ambient noise: ladle in broth.` line and let it carry the whole audio brief.
- **Delete "No music." from the prompt.** Google's own prompting guide says to
  describe what you do not want rather than instruct with "no" or "don't", and
  naming music at all is a way to invite it. Our shot prompts still carry that
  line; strip it on the next pass.
- **Silent shots get muted in the edit.** A shot with no dialogue loses nothing
  by having its whole track replaced with our own ambience and score, which
  removes any risk of an unwanted bed. Only dialogue shots have to keep Veo's
  audio, because the voice is welded to it.

## Which model for a drama: Omni Flash, not Veo 3.1 Fast (2026-09-08)

Veo 3.1 **Quality** is out of the question for a character series regardless of
budget: it cannot use ingredients at all, so it cannot hold a face. The real
choice is between the two that can.

| | Gemini Omni Flash 1.1 | Veo 3.1 Fast |
|---|---|---|
| Voice lock | yes | no |
| Max length | 10s | 8s |
| Video-to-video editing | yes | no |
| Cheap draft | 360p at half cost | none |
| Ingredients (face lock) | yes | yes (8s only) |
| Raw visual finish | second | first |
| Cost, 720p 8s | **12 credits** | 20 credits |
| Cost, 720p 10s | 15 credits | n/a |
| Cost, 360p draft | 6 at 8s, 7 at 10s | none |

Veo Fast makes the prettier frame. Omni Flash makes the thing a viewer can
follow: the same voice every scene, a quarter more story per credit, and a way
to fix a near-miss without re-rolling it. For a dialogue-driven series the
features outweigh the finish, and the gap in finish is small — one third-party
matched test of eight prompts scored Omni 4.124 against Veo 3.1 Fast's 4.009.
That is a blog, not a measurement of our own material; the settling test is one
shot we already own, re-shot on Omni with the same ingredients, compared side by
side against the Veo version.

Unverified as of 2026-09-08, and each one can change this: whether the AI PLUS
plan exposes Voices at all, what Omni Flash costs per generation on this
account, and whether the Gemini/Vertex **API** can set a voice (no voice
parameter is documented — if the API cannot, an API-scale episode loses voice
lock and the whole plan changes).

### Chip attach: the ⋮ menu is gone (2026-09-08, task-0793785a)

The "open the tile's more-options menu, click the inner label node, expect it to
work about once in fifteen tries" path no longer exists — an asset row is a bare
`<button class="asset-item" role="option">` with no nested menu button. **Single
-click the row; a preview pane opens to the right with its own full-width
`เพิ่มไปยังพรอมต์` button; click that.** Three attachments, three first-try
successes, including the voice preset. If a future session sees the ⋮ menu
again, both paths belong here — but do not spend a 7-fail streak hunting for a
menu that is not on screen.

A voice chip reports `disabled: false` as soon as two other ingredients sit
beside it, which is the practical confirmation that a voice is live for that
generation. Check it before firing.

### Measured on the account, 2026-09-08 (task-e3bf2fa9, read-only, 0 credits)

- **Voices is live on the PLUS tier.** The Add-ingredient picker's categories
  are ทั้งหมด · รูปภาพ · วิดีโอ · **เสียง** · ตัวละคร · รูปโปรไฟล์ · การอัปโหลด.
  No upgrade wall anywhere near it.
- **The model is called "Omni 1.1 Flash" in the UI**, not "Gemini Omni Flash
  1.1". It is the account default and reappears on every project reload, so a
  task that wants Veo must select Veo every time.
- **Omni Flash undercuts Veo 3.1 Fast**: 12 credits at 720p/8s against Veo's
  20, 15 at 720p/10s, and a 360p draft at 6 and 7. Ingredient chips and the
  เฟรม/องค์ประกอบ toggle are unchanged when it is selected.
- **The 30 presets carry written labels** — name plus "Male, gravelly, low
  pitch" and so on. Nobody has to listen to choose one. Pick from the label,
  record the name.
- **A voice attaches as a CHIP, not as text.** `เพิ่มไปยังพรอมต์` adds a
  `<flow-audio-ingredient-chip>` to the ingredient bar and leaves the prompt box
  untouched (its innerText still reads the placeholder). The chip is **inert on
  its own** — tooltip "องค์ประกอบเสียงต้องมีองค์ประกอบอื่นๆ จึงจะทำงานได้" — so a voice
  only works alongside a Character or other ingredient in the same generation.
- **The customize-performance path is dead on this account (2026-09-08).**
  Typing into `ปรับแต่งประสิทธิภาพ` removes `เพิ่มไปยังพรอมต์` and reveals a save
  flow: a name field pre-filled `"<Preset> คัสตอม"`, `รีเซ็ต`, and
  `บันทึกเสียงใหม่` — and that save button was found **permanently disabled**,
  across two characters, ~10 minutes of attempts, after editing the name, after
  previewing. `รีเซ็ต` reliably restores the working plain-preset flow. So:
  **attach the plain preset, and write the performance direction into the shot's
  own prompt text.** That is better anyway — the direction then lives in the
  script, under version control, instead of inside Google's account state.
- **One "not found" is not proof a preset is gone.** A search for Algenib
  returned ไม่พบชิ้นงาน and the list skipped it alphabetically; a freshly opened
  picker minutes later showed it in place. Same `document.hidden` virtual-scroll
  trap. Reopen before concluding anything is missing.
- **Selecting a preset opens a panel, it does not attach immediately**:
  a preview button, `ตัวอย่างบทสนทนา` (example dialogue, maxlength 120),
  `ปรับแต่งประสิทธิภาพ` (customize performance, a free-text description with no
  DOM length cap), then `เพิ่มไปยังพรอมต์` (add to prompt). **There is no name
  field in the plain flow** (one appears only in the broken save flow above) — the voice is not a saved named object, it is
  text added to the prompt. So the durable artifact is the preset name plus the
  performance description, written into the script beside the APPEARANCE LOCK.
- **Long virtualized lists can be unreadable on winbox.** The tab reported
  `document.hidden === true` for a whole session on two different tabs, which
  froze `cdk-virtual-scroll-viewport` rendering (scrollTop and scrollIntoView
  did nothing) and made screenshots time out about half the time. The fix that
  works: use the panel's own search box, which substring-matches the full data
  set and re-renders regardless of scroll state.

## winbox findings 2026-09-07 (task-ef3995a1, first real shoot on Windows Chrome)

Measured on winbox; the rest of this skill was measured on the Mac. Full
report: `docs/reports/teaser-shoot-winbox-20260907.md`.

- **`resize_window` never takes effect on winbox** — innerWidth stayed 1920
  through repeated resize+navigate cycles. Screenshots cost 1.5–2.3k tokens
  each there, not ~800. Prefer JS reads over screenshots on that host.
- **Money buttons need a trusted click.** JS `element.click()` opens pickers
  and menus but did NOT fire เริ่มสร้าง (no card, no balance change). Submit
  with the `computer` tool's click, then confirm the balance moved.
- **Inline `@handle` in a prompt truncates `computer` typing** — the
  ProseMirror @-autocomplete swallows everything after the `@`. Type prompts
  that contain `@handle` with `document.execCommand('insertText', false, text)`
  after placing the caret at the end; verify `innerText` before submit.
- **Agent mode can be ON by default** (chip text exactly `Agent`,
  aria-pressed true). While on, the settings icon opens การตั้งค่า Agent, not
  the per-shot panel. Click the Agent chip off first.
- **Export hang can take 2 reloads / ~9 min.** And ดาวน์โหลดฉาก inside the
  Scenebuilder saves a direct `.mp4`, not the grid card's `.zip` — check
  Downloads for both.
- **A tab can collapse to 98x74 / hidden mid-session** and then time out on
  screenshots. Open a fresh tab, close the broken one, continue there.
- **Chip attach in องค์ประกอบ mode had a 7-fail streak** (coordinates verified
  each time, reload did not help). Budget for it: 3-chip shots took ~10 min
  each. Stop at 5 consecutive failures and reload the project, not the tab.
- **Plates must be 9:16.** A landscape start frame is padded with grey bars
  and the whole clip inherits them (shot 1). Check the plate's aspect in the
  รูปภาพ tab before binding it as เริ่ม.

### winbox, run 2 additions (task-5d0bd2fa, 2026-09-07)

Second shoot on the same box, 39 minutes for 4 clips against the first run's 76
for 4 — the findings above are what made the difference. Three more:

- **Never click at a `getBoundingClientRect()` coordinate on winbox.** The
  screenshot is scaled down from the real viewport by a ratio that changes with
  tab state (~0.688 one run, ~0.82 the next), so a DOM rect points somewhere
  else entirely. Click only at coordinates read off a fresh screenshot. On this
  box a `find()` ref click failed to toggle the Agent chip for the same reason;
  a pixel click at the chip worked. This is a better explanation of the run-1
  "money buttons need a trusted click" finding than trustedness is.
- **A download can silently walk to another clip.** Clicking download on a
  clip's edit page starts the preview playing, and Flow's own carousel can
  auto-advance to an unrelated clip mid-export; the export toast then belongs to
  whatever is now on screen. Re-check the page title against the intended shot
  right after clicking download, and re-navigate to `/edit/<id>` if it drifted.
- **Budget the export hang per download, not per session.** It hit all four
  downloads, 1-2 reload cycles each, worst case ~7 minutes.

**Verify grade, not just geometry.** Run 2's bonus re-fire of shot 1 against a
fresh 9:16 plate came back correct in every mechanical check the worker ran
(8.00 s, 720x1280, audio present, no padding) and still unusable: the clip is
black-and-white while the rest of the teaser is colour. A shot only passes if it
also matches the neighbouring shots' colour and grade, and a plate generated from
a prompt that does not pin the look will drift. Say the look in the plate prompt,
and compare frame 0 against a neighbouring shot before calling a re-fire good.

## The download button is dead — go straight to the CDN URL (2026-09-18, task-860620fc)

**On this account the toolbar download icon is a silent no-op.** Across roughly
six attempts in one session — ref-based clicks, DOM text-node clicks, and
coordinate clicks, including the resolution flyout (270p/720p/1080p/4K) —
**Chrome's own downloads history recorded zero entries.** No error, no toast, no
feedback of any kind.

This is **not** the documented "export hangs, reload and retry" trap. That one
at least shows `Exporting your scene…`. This shows nothing at all, which means
an operator can spend ten minutes believing a download is in flight when nothing
was ever started.

**Do not use the download button. Do this instead:**

1. Play the clip. Flow's own player fetches a signed CDN URL
   (`flow-content.google/video/<id>?...`).
2. `read_network_requests` to capture that URL.
3. `curl` it.
4. `ffprobe` the result to confirm it is the clip you wanted.

Verified byte-identical to what the player streams. Three clips pulled this way
on 2026-09-18 with no failures, against a download button that never produced a
single file.

## Chip attach is inconsistent, not fixed (correction to the 2026-09-08 note)

The 2026-09-08 entry says single-clicking an asset row opens a preview pane with
its own `เพิ่มไปยังพรอมต์` button, three first-try successes. **Both behaviours
occur, in the same session, on the same account:** the first attach of a session
on a fresh tab attached the chip immediately with no preview pane and no second
click; every attach after that opened the preview pane and needed the documented
second click.

So: **click the row, then look at what actually happened** rather than assuming
either path. Count the chips afterwards — the picker hides what is already
attached, so a successful attach is an item that has disappeared from the list.
Neither behaviour is a failure; assuming one of them is what cost time.

## Chrome tab-group destruction is routine when sessions share a browser

The tab group was destroyed three times in one session on 2026-09-18, with other
browser_operator and developer sessions live in the same Chrome. Each recovery
followed the existing protocol — fresh tab, re-navigate, re-verify composer state
from scratch — and none of them cost a generation. **Treat it as weather, not as
an incident**, but never assume composer state survived one.

## Prompt syntax: Omni is not Seedance — `<IMAGE_REF_N>` goes INSIDE the sentence (2026-09-18)

Three shots were fired on 2026-09-18 with chips correctly attached — Flow's own
post-hoc ingredient panel confirmed all of them, voice included — and the
character's face, hair and the entire location still drifted between shots.

The chips were never the problem. **The prompts were written in Seedance
grammar.** We wrote `@nong_daeng speaks in Thai` and attached chips without
telling the model what each one was for. Google's own Omni guide names that as
the common failure: *"uploading several references and assuming the model knows
which one controls the face, which one controls the outfit, which one controls
the scene."*

**Omni's documented convention is `<IMAGE_REF_N>` written inline, at the point in
the sentence where that subject is mentioned.** Google's own example:

```
"in the style of <IMAGE_REF_0> a woman <IMAGE_REF_1> is walking"
"[0-3s] Starting with woman <IMAGE_REF_0>, she is holding <IMAGE_REF_1>
 [3-6s] Then we see the man <IMAGE_REF_2>"
```

Four rules follow, and all four were being broken:

1. **`<IMAGE_REF_N>` is indexed by ATTACH ORDER.** Attach deliberately, in the
   order the prompt references them, and verify each one landed before the next.
2. **Say what each reference is for** — "use `<IMAGE_REF_0>` as the character
   reference for the face and hair, `<IMAGE_REF_1>` as the location reference for
   the interior and its layout."
3. **The chip is a hint, not a lock. Describe the appearance in text anyway** —
   hair length, clothing, build, the set's fixed features. The shot that came out
   right had a rich set description; the shot that drifted had a thin one, and
   neither described the character at all.
4. **Drop "No music."** Google's guide says describe what you want rather than
   instruct with negatives, and naming music invites it. Our prompts carried that
   line for months.

Up to **10 image references and 3 video references** per generation are allowed —
far more than the 3 we assumed. And *"attach everything before the first
generation, because adding references mid-conversation destabilizes a scene that
was holding together."*

## The APPEARANCE LOCK is the ground truth, not the neighbouring shot

When three shots disagree, "which one is wrong" is unanswerable by comparing them
to each other — there is no reference among them. The script's `APPEARANCE LOCK`
line for that character IS the reference. Check each shot against that text, item
by item (apron colour, whether it is over or under the shirt, hair, stubble,
watch, which wrist), and the answer is a count, not an opinion.

This costs nothing and can be run retroactively on every clip ever shot.

## Voice: the API cannot do it at all, so Flow's UI is the only path

`gemini-omni-1.1-flash` went GA on 2026-08-27 and its documentation states
**"Uploading audio references is unsupported"** and **"Voice editing is not
supported."** The API does accept `<IMAGE_REF_N>`, `<FIRST_FRAME>` and
`<LAST_FRAME>` together, which the Flow UI refuses to do — so the trade is real
and it cuts both ways:

| | face + set lock together | voice lock |
|---|---|---|
| Flow UI | no — `เฟรม` and `องค์ประกอบ` are mutually exclusive | yes, via the chip |
| Gemini API | **yes** | **no, documented as unsupported** |

A dialogue-driven series therefore cannot use the API for its speaking shots, and
cannot frame-lock them in Flow. If voice lock turns out unreliable in practice,
the better architecture is silent generation with frame lock plus a TTS voice we
own — which locks the voice completely instead of steering it.

### Price, for the same model, measured 2026-09-18

| route | per second of finished video |
|---|---|
| Flow on Ultra (฿3,500 / 10,000 credits, Omni at 1.5 cr/s) | **฿0.53** |
| Flow on Pro (฿750 / 1,000 credits) | ฿1.13 |
| Gemini Omni API, 720p | $0.10 ≈ **฿3.50** |

**The subscription is several times cheaper than the API for the same model.**
Going API-first is a capability decision (frame lock), never a cost one.

## ⛔ Verify a chip by its THUMBNAIL, never by its row label (2026-09-18, task-8ea0576a)

**Flow tags the location plate as `ตัวละคร` (character) in this project.** All
three of `@nong_daeng`, `@lung_somchai` and `@noodle_shop` carry the identical
category label in the `+` picker, and the composer's ingredient panel exposes
**no `@handle` name anywhere in its DOM** — every character icon carries only the
generic `alt="รูปภาพองค์ประกอบตัวละคร"`.

So a natural-language or label-based click picks the wrong asset **silently**.
Measured: a `find()` match for "the @nong_daeng row" attached the **noodle-shop
interior plate** instead, and every check that had been trusted up to that point
still passed — the chip count was right, the type was right, the picker-exclusion
was right. Only zooming into the chip's thumbnail showed it was the wrong image.

**This almost certainly explains the character drift blamed on prompt syntax.**
An earlier shoot verified its chips by count and type, reported "3 chips, matches
the script exactly", and came back with the wrong character in the wrong shop.
Its own report had already admitted the limit — *"the DOM count check only proves
type and count, not which character"* — and nobody acted on that sentence.

### The rule

1. **Use the picker's search box**, not a label match or a natural-language row
   reference. Type the handle.
2. **Look at the preview image before you click add**, and at the chip's
   thumbnail after. Zoom if the thumbnail is small. A face must look like a face,
   a location like a location.
3. **Then** confirm picker-exclusion (the item disappears from the list).
4. Record the attach ORDER, because `<IMAGE_REF_N>` is indexed by it.

Count, type and exclusion together still do not tell you *which* asset bound.
Only the image does.

### What this costs the earlier conclusion

The retake that fixed the drift changed **two** things at once — the prompt
syntax *and* the chip-verification method — so the fix is proven but its cause is
not attributed. The wrong-asset bug is now the likelier culprit. Do not write
"prompt syntax was the cause" anywhere until a shoot isolates it.
