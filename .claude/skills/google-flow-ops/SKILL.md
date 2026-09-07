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
