# Google Flow recon — 2026-09-07

Task: walk Google Flow (labs.google/fx/tools/flow → flow.google.com) end to end on the CEO's own Google AI Pro
account, project "AI Film", to answer whether it's viable for a Thai moral-drama series. Fixed content only, credit
cost measured at every step, hard cap 120 credits.

**Cumulative spend: 40 / 120 credits.** Character (Ingredient) image generation was free; only video generation
(Veo 3.1 Fast) charged, at 20 credits per 8s/720p/9:16/x1 clip, twice.

---

## A. INPUT → OUTPUT

| Feature | Input | Output / format |
|---|---|---|
| New Project | Name "AI Film" typed into project title field | Project workspace at `flow.google.com/project/<uuid>` |
| Character (Ingredient) — `@lung_somchai` | Full English text prompt, model "Nano Banana Pro" | One 4:5 photorealistic portrait image, stored as a named "ตัวละคร" (Character) asset |
| Character (Ingredient) — `@nong_daeng` | Same, second prompt | Same — one portrait image |
| 3rd/4th ingredient test — `@test_char3`/`@test_char4` | Two more throwaway character prompts | Two more portrait images (used only to test the ceiling) |
| Ingredient attach to composer | Click character card → "เพิ่มไปยังพรอมต์" (Add to prompt) | A lime/avatar "chip" appended above the prompt textbox |
| Video shot | Fixed 8s/9:16 prompt, Veo 3.1 - Fast, both character chips attached, x1 | One 8.00s h264 video, 720×1280, 24fps, AAC stereo audio track present, downloadable as .mp4 |
| Video re-run (variance test) | Identical prompt + identical chips, fired a second time | A second, visually different 8s clip stored as a "version" of the same asset card |
| Download | Top-toolbar download icon, or right-click → "ดาวน์โหลด" (Download) on the timeline clip | `.mp4` file to the OS Downloads folder — no resolution or format picker was ever shown |
| Upscale search | Toolbar `⋮`, share icon, model dropdown, right-click context menu, fullscreen player, "pen_magic" icon, Filter panel's "ความละเอียด" (resolution) filter | **No 1080p / upscale control found anywhere.** Resolution filter chips only list 720p and 360p — no 1080p tier exists in the account's asset taxonomy at all |

---

## B. COST — the table

All deltas read from `เครดิต Google Flow N เครดิต` in the account menu, verified twice per the honesty rule
(before AND after each paid step).

| # | Action | Credits before | Credits after | Delta |
|---|---|---|---|---|
| 0 | Session start (project not yet created) | 250 | 250 | — |
| 1 | Create project "AI Film" | 250 | 250 | **0** |
| 2 | Generate Character 1 (`@lung_somchai`, Nano Banana Pro, 4:5 portrait) | 250 | 250 | **0** |
| 3 | Generate Character 2 (`@nong_daeng`, same model) | 250 | 250 | **0** |
| 4 | Generate 2 more throwaway characters for the 4-ingredient ceiling test | 250 | 250 | **0** |
| 5 | Attach 4 ingredient chips to one prompt (no generation fired) | 250 | 250 | **0** (nothing to spend — no generation happened) |
| 6 | Open Scenes ("ฉาก") tab, Tools tab, Agent-instructions panel — pure navigation | 250 | 250 | **0** |
| 7 | **Generate video, shot #1** — Veo 3.1 Fast, 8s, 720p, 9:16, x1, both real characters attached | 250 | 230 | **20** |
| 8 | Upscale to 1080p | — | — | **not applicable — no upscale control exists (see A and E)** |
| 9 | **Generate video, shot #2** (identical prompt+chips, variance test) — same settings | 230 | 210 | **20** |
| — | Download clip 1 (top-toolbar export) | 210 | 210 | **0** |
| — | Download clip 1 again (right-click "ดาวน์โหลด" re-export, smaller bitrate) | 210 | 210 | **0** |
| — | Download clip 2 (version-2 export, delayed ~15s, required a page reload to un-stick) | 210 | 210 | **0** |
| | **TOTAL SPENT** | **250** | **210** | **40 / 120 cap** |

Sanity check against the task's published numbers: Veo 3.1 Fast = 20 credits — **matched exactly**, both times, at
8s/720p/9:16/x1. The Fast/Quality/Lite cost differential was visible live in the settings panel before commit:
Quality would have shown "100 เครดิต" (never selected, per instruction). Image/Ingredient generation cost, which
was NOT published, measured out to **0 credits** for both the Nano Banana Pro portraits and the two throwaway test
portraits — 4 image generations, 4 × 0 = 0.

## C. AUTOMATIC — what Flow does with no further input once you press go

- Renders the video end-to-end (no manual per-frame or per-second intervention) — 8s clip finished in **~51s
  wall-clock** on the first run, **~94s** on the second.
- Binds attached Ingredient chips into the shot automatically — no manual per-frame reference painting.
- Assigns a human-readable auto-title to the asset from the prompt text ("Shopkeeper pushing envelope acro…").
- Groups repeat generations of the same prompt+ingredients as **versions of one asset card**, with a small
  version-selector strip at the top, rather than cluttering the media grid with duplicate cards.
- Live-updates the credit-cost estimate in the settings panel as you change model / resolution / duration /
  quantity — before you commit to spending anything.
- Deduplicates the ingredient picker: once a character is attached to the current prompt, it disappears from the
  "+" picker's list until removed, which is also how we proved chips were bound vs. dropped.

## D. MANUAL — what a script could not do

- Navigating discrete UI panels: Characters tab → New Character → type prompt → click generate → wait → rename —
  all click-by-click, no batch character-creation flow.
- **Re-attaching ingredient chips after any action that reloads/rebuilds the composer.** Expanding the prompt
  textbox by scrolling, or clicking the composer's "×", silently drops every attached chip with zero warning —
  this happened twice during the walk and both times required manually re-opening the "+" picker and re-selecting
  each character by name before firing. A script blindly firing after such an action would generate a shot with
  **no character references at all** and nobody would know until reviewing the frames.
- Manually toggling model (Nano Banana Pro for stills, Veo 3.1 - Fast for video — 4 models are listed: Omni 1.1
  Flash, Veo 3.1 Lite, Veo 3.1 Fast, Veo 3.1 Quality) and manually re-verifying it stuck, because switching tabs
  or reloading silently resets to the account default (Omni 1.1 Flash).
- Manually setting aspect ratio to 9:16 and quantity to x1 every time — these are NOT sticky defaults across new
  prompt sessions in this account.
- Manually re-verifying the live credit estimate immediately before clicking Generate — the number moves every
  time a setting changes, exactly as the cost-discipline rule warns.
- Manually retrying the download for the second generated version: its export got stuck on "Exporting your
  scene…" indefinitely; only a full page reload plus a second click actually completed it (~15s later).

## E. AI CAN'T — hard ceilings, missing controls

- **No upscale-to-1080p control exists anywhere in the reachable UI** for this account/product state — not on
  the toolbar, not in the right-click menu, not in the share panel, not in the fullscreen player, not as a model
  variant. The asset filter's own "ความละเอียด" (resolution) facet only offers **720p** and **360p** — 1080p is
  not a resolution class the product currently tracks for this account. Every exported file, both generations,
  came out at native 720×1280. **We could not confirm the task's "1080p upscale = 0 credits" claim because the
  feature was not discoverable** — treat that published number as unverified for this account tier.
- **No pre-generation storyboard/shot-list tool.** The "ฉาก" (Scenes) tab is a passive filtered gallery of
  already-generated media — it shows "เริ่มสร้างหรือวางสื่อ" (start creating or paste media) when empty. There is
  no way to create an empty ordered slot, type a shot list, or plan a sequence of shots before any clip exists.
  Storyboarding in Flow means: generate the shots, then they land in the Scenes filter after the fact.
- **The 3-ingredient ceiling described in the task brief does not exist as a hard UI block.** We attached 4
  distinct Ingredient chips (2 real characters + 2 throwaway test characters) to a single prompt with zero error,
  no greying-out, and no silent drop — confirmed by DOM inspection (4 chip elements present) and by a page-wide
  text search for limit/maximum language, which returned nothing. Whether a ceiling is enforced only at
  *generation* time (not attach time) is untested — we removed the extra chips before firing to stay on-spec, so
  this could not be verified further without spending credits on an off-spec shot.
- **No way to upload your own voice track or replace the dialogue audio.** The composer's "Ambient noise" /
  dialogue instructions are text-only prompt content baked into generation — there is no audio-upload control
  anywhere in the video composer.
- **No batch/queue for lining up multiple shots.** Every generation is a single fire-and-wait action; there is no
  visible "queue 10 shots" control. (We did not test whether opening N tabs would parallelize N generations — out
  of scope for a single-operator walk.)
- **No whole-episode export.** There is no "export project" or "export timeline" control that assembles multiple
  clips into one file — only per-clip/per-version download. Multi-scene assembly, if it exists, was not
  discoverable within this walk's budget.
- **Prompts are not saved as reusable templates.** No "save as template" affordance was found; the closest thing
  is the six example-prompt cards shown on the blank Character page, which are Google's own presets, not
  user-savable.
- **The clearest hint of an automation/API surface** is the "Agent" toggle in the composer and its
  "คำสั่งสำหรับ Agent" (Instructions for Agent) panel, with a global "Agent Settings" page offering a
  confirm-every-time vs. fully-autonomous toggle and default aspect/quantity settings. This is an in-app
  autonomous-generation mode, not a documented public API — no REST/webhook/CLI surface was visible anywhere in
  the UI.

## Free-of-charge extra findings

- **Batch/queue**: none found (see E).
- **Whole-episode export**: none found (see E).
- **Saved/reusable prompt templates**: none found (see E) — only Google's own example cards.
- **API/automation hint**: the "Agent" mode + "Agent Settings" (confirm-before-create toggle, default video
  aspect/resolution) is the only automation-shaped surface in the product; it is in-app, not an external API.

---

## Honesty notes

- We can hear nothing — every audio claim above is limited to "an AAC audio stream is present" (ffprobe-verified),
  never what the dialogue sounds like.
- Every credit number in the cost table was read from the account menu at least twice (once before, once after)
  before being recorded.
- The upscale finding is reported as "not found," not "does not exist" — we searched every reachable surface
  within the action budget but cannot rule out a control hidden behind an unexplored menu.

## What went wrong

- **Composer state is fragile.** Twice, an unrelated UI action (expanding the prompt textbox, clicking the
  composer's "×") silently cleared both attached character chips with no warning dialog. Caught both times only
  because we re-verified chip count via the "+" picker (excluded = attached) before firing — see skill note
  "Count the reference chips before you fire."
- **`window.innerWidth`/`resize_window` only took effect after a full page navigation**, not on the initial load —
  screenshots before that point were captured at the browser's maximized size (~1456×840) rather than the
  requested 1024×768, inflating a few early screenshot costs.
- **The second video's download hung** on "Exporting your scene…" indefinitely; a full page reload was required
  before a retry succeeded, ~15s later. Not spend-related (download is a free action) but worth flagging as an
  export-flow reliability gap.
- Ran out of the practical exploration budget before confirming whether the 3-ingredient ceiling (if any) applies
  only at generation time — see E.

## Deliverables in this folder

- `clip1_v1.mp4` — shot #1, top-toolbar export, 720×1280, 8.00s, h264+aac
- `clip1_v1_reexport.mp4` — shot #1, right-click re-export (smaller bitrate, same resolution/duration)
- `clip1_v2.mp4` — shot #2 (variance test), 720×1280, 8.00s, h264+aac
- `01-video1-editor-downloaded.jpg`, `02-credits-final-210.jpg`, `03-video2-variance-frame.jpg` — screenshots
