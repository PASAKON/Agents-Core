# Google Flow — Frames to Video: does a first-frame control exist? (2026-09-07)

Task: settle whether the CTO's claim ("Flow's web UI has no first-frame slot,
frame control is API-only") is correct. Project: "AI Film"
(`e88671f5-9ae8-4946-84a6-8b8e31dc0d39`). Account balance at start: **210
credits**. Balance at end: **210 credits** — nothing spent.

## Answer up front

**The CTO was wrong. A first-frame AND last-frame control exists in the web
UI.** `google-flow-ops` skill v1 states flatly "No first-frame or last-frame
slot... Flow can shoot disconnected beats; it cannot shoot a continuous
scene" — that line is false and needs correcting (see SKILL-CONTRADICTION
below). The control was never found in v1's recon because nobody switched the
Video-mode submode toggle away from its default ("Ingredients") — it sits one
click away from the ingredient-chip UI, not hidden in a menu or right-click.

## A. First-frame control — exact location

- Composer → settings-trigger button (bottom-right pill showing model/mode) →
  **"วิดีโอ" (Video) tab** → a second-row toggle with two buttons: **"เฟรม"
  (Frame)** and **"องค์ประกอบ" (Ingredients)**. Default on load is
  "องค์ประกอบ" — this is why prior recon missed it entirely.
- Clicking **"เฟรม"** replaces the ingredient-chip composer with two slots.
  The first slot's accessible name is literally **`เริ่ม`** ("Start"). DOM
  read confirms the swap button between the two slots is named
  **`สลับเฟรมแรกและเฟรมสุดท้าย`** — "swap first frame and last frame" — using
  the exact Thai terms for "first frame" (เฟรมแรก) and "last frame"
  (เฟรมสุดท้าย) that the task asked to search for.

## B. Last-frame control — exact location

Same toggle, same two-slot composer. Second slot's accessible name is
**`สิ้นสุด`** ("End" / "Finish"). Confirmed via `read_page` (button refs
`เริ่ม`, `สลับเฟรมแรกและเฟรมสุดท้าย`, `สิ้นสุด` all present together) and via
screenshot. A swap icon between the two slots lets you flip which image is
first vs. last without re-uploading.

## C. First frame + Ingredient chips together?

**Mutually exclusive.** "เฟรม" and "องค์ประกอบ" are two buttons in what
renders as a single-select toggle (only one is highlighted white at a time).
Switching to "เฟรม" replaces the entire composer's attach UI — the
chip-input row and the `+`/ingredient-picker disappear completely, replaced
by the two frame slots. There is no way to have both an attached frame and
an ingredient chip active in the same generation from this UI.

## D. Does the first frame accept a file uploaded from disk?

**Not directly, and not provably at all with this session's tooling — this
is the weakest-evidenced answer here, flag it as such.**

What was established:
- Clicking the **"เริ่ม"** slot opens a dialog titled **"เลือกรูปภาพเฟรม"**
  ("Select frame image"). It has a project-scope dropdown (locked to the
  current project, no "all projects" option), a search box, and a sort
  dropdown (ล่าสุด/ใช้มากที่สุด/ใหม่ที่สุด/เก่าที่สุด/รายการโปรด). **No
  upload button or drop-zone exists inside this dialog.**
- With only Character/Ingredient-tagged images (@noodle_shop, @lender_cherd,
  etc.) and two videos in the project, the dialog showed **"ไม่พบชิ้นงาน"**
  ("no items found") — at both 9:16 and 16:9 aspect settings, and regardless
  of sort order. **Character/Ingredient-tagged media is excluded from this
  picker's pool.**
- To test the pool's actual contents, we generated one free, untagged plain
  image via Image mode / Nano Banana Pro ("Empty market street at dawn...",
  9:16, 0 credits). It **immediately appeared and was selectable** in the
  "เลือกรูปภาพเฟรม" dialog with an "เพิ่มไปยังพรอมต์" (Add to prompt) button.
  **So: the first-frame pool is the project's own untagged generated
  images — not Characters/Ingredients, and reachable only by generating
  (or uploading) plain media first, never a raw file from your local disk at
  this dialog.**
- Separately, the project's top-toolbar **"เมนูเพิ่มสื่อ"** (Add media) menu
  has an **"อัปโหลด" (Upload)** item. A real (trusted) click on it triggers
  what appears to be a native OS file-open picker: `document.hasFocus()`
  flipped to `false` and `document.hidden`/`visibilityState` flipped to
  `hidden`/`"hidden"` immediately after the click, and no `<input
  type="file">` ever appeared in the DOM (confirmed 0 both before and after,
  and a synthetic `.click()` via JS — lacking a trusted user gesture — did
  **not** trigger it at all, which is consistent with the modern
  `showOpenFilePicker()` API rather than a classic `<input>`). This means:
  the upload path is real, but it is an OS-level dialog outside the DOM, and
  neither the Chrome-extension `file_upload` tool (needs an `<input>` ref)
  nor this session's available automation could drive it to completion
  safely. We backed out via `Escape` rather than risk leaving a modal OS
  dialog stuck on the shared Chrome profile.
- **Conclusion for D:** the first-frame slot's picker only offers
  already-in-project, untagged media. Whether an uploaded-from-disk file
  (via the separate "อัปโหลด" project menu) subsequently becomes selectable
  there is **plausible but unverified** — we could not complete that flow
  with the tools available this session.

## E. Does supplying a first frame change the credit cost?

**No visible change in the live estimate.** In "เฟรม" mode with both slots
empty, the settings panel showed **"การสร้างใช้ 20 เครดิต"** — identical to
"องค์ประกอบ" (Ingredients) mode's estimate for the same Veo 3.1 - Fast / 9:16
/ x1 config. We did not get to re-read the estimate with an image actually
attached (blocked by D), so this is based on the baseline estimate only, not
a before/after delta with an attached frame. Account balance stayed at
**210 → 210** for the whole session (only free Nano Banana Pro stills were
generated).

## F. Proof clip

**Not generated. No credits spent.** The task's proof required attaching
the literal file `docs/reports/flow-plates-20260907/ing-noodle-shop.jpg` as
the first frame. That file was already used to create the `@noodle_shop`
Character/Ingredient, and Character/Ingredient-tagged media is excluded from
the "เลือกรูปภาพเฟรม" picker (see D). The only way found to get an image
into that picker is to generate it fresh as an untagged still, or to
complete the OS-native "อัปโหลด" file dialog — neither of which produces
"the supplied plate, verbatim" without either (a) substituting a
freshly-generated look-alike (defeats the point of testing whether frame 0
equals the *supplied* plate) or (b) an OS dialog this session could not
drive. Per the task's own money rule — spend the one paid generation only if
you can attach an image to it — spending on a substitute image would not
have answered the question the credit was meant to buy, so nothing was
spent.

## Cost table

| Action | Credits before | Credits after | Delta |
|---|---|---|---|
| Session start (balance read) | — | 210 | — |
| Nano Banana Pro still #1 (empty market street, 9:16, test) | 210 | 210 | 0 |
| Veo 3.1 Fast 8s 9:16 proof clip | — | — | **not run** |
| **Total spent this session** | | | **0 / 25 cap** |

## Timing table (wall-clock, `date +%s`, measured not estimated)

| Action | Start (epoch) | End (epoch) | Duration |
|---|---|---|---|
| Plate file existence check | 1788754366 | — | — |
| Navigate to flow.google.com (fresh tab, post-resize) | 1788754366 | 1788754392 | 26 s |
| Submit free test-image generation (Nano Banana Pro, 9:16) | 1788755256 | ~1788755300–1788755310 (visible, still-rendering thumbnail at +44s; fully selectable in Frame picker by the next check, a few actions later) | **~45–60 s** (bracketed, not exact — see note) |

Note: only three hard timestamps were taken with `date +%s` this session
(start, nav-complete, submit). The still's exact "ready" moment was read from
screenshots taken after explicit `wait` calls (10 s + 10 s + 8 s = 28 s of
waits) rather than a fourth `date +%s` call, so the still-generation duration
above is a bracket, not a point measurement — flagged rather than presented
as precise. This is a self-noted gap in rigor, not a laundered estimate.

## Verbatim UI strings collected

- `เครดิต Google Flow 210 เครดิต` — account-menu balance line
- `รูปภาพ` / `วิดีโอ` — Image / Video mode tabs
- `เฟรม` / `องค์ประกอบ` — Frame / Ingredients submode toggle (Video mode only)
- `เริ่ม` — first-frame slot ("Start")
- `สิ้นสุด` — last-frame slot ("End")
- `สลับเฟรมแรกและเฟรมสุดท้าย` — swap button aria-label, literally "swap
  first frame and last frame"
- `เลือกรูปภาพเฟรม` — "Select frame image" dialog title
- `ไม่พบชิ้นงาน` — "No items found" (empty picker state)
- `เพิ่มไปยังพรอมต์` — "Add to prompt" confirm button inside the frame picker
- `เริ่มสร้างหรือวางสื่อ` — empty-state text on the ฉาก (Scenes) tab: "Start
  creating or paste media" — the exact string the task flagged as a hint
  that media can be pasted/dropped. We did not additionally test OS-level
  drag-and-drop of a local file (no file-system drag source available to
  the Chrome-extension tools); this remains untested, not disproven.
- `อัปโหลด` / `คอลเล็กชันใหม่` / `สร้างตัวละคร` / `ฉากใหม่` — the four
  items in the top-toolbar "เมนูเพิ่มสื่อ" (Add media) menu
- `การสร้างใช้ 20 เครดิต` — live cost estimate, Veo 3.1 - Fast / 9:16 / x1,
  both Frame and Ingredients submodes

## Where we looked (systematic, per the task's checklist)

1. **Generation-mode selector.** Confirmed a 4th layer beyond Image/Video/
   Agent: inside Video mode there is a **submode toggle (Frame /
   Ingredients)** not mentioned in the original recon. This is the answer to
   "is there a fourth mode, or a submode once Video is selected" — yes, a
   submode.
2. **Composer `+`/attach menu.** Not re-tested directly this session (the
   Frame/Ingredients toggle replaces this need) — the `+` in the default
   composer is the character/ingredient picker per prior recon; nothing new
   found there.
3. **Right-click / `⋮` on a generated clip.** Not tested this session —
   deprioritized once the Frame toggle was found directly in the composer
   settings panel, and to stay inside the credit/action budget.
4. **Scenebuilder / ฉาก tab.** Visited. It shows the same empty-state
   ("เริ่มสร้างหรือวางสื่อ") described in the task brief. No clip-level frame
   options were surfaced beyond the same composer at the bottom of the
   screen (which carries whatever mode/submode was last set).
5. **Drag an image onto the composer.** Not completed — no drag source
   available from the file system through the Chrome-extension tools in this
   session (see D). Left untested rather than reported as absent.
6. **Page-wide text search for "frame"/"เฟรม" etc.** Effectively done via
   `get_page_text` reads across every state above — "เฟรม", "เริ่ม",
   "สิ้นสุด", "เฟรมแรก", "เฟรมสุดท้าย" all surfaced directly from the
   Frame-mode composer and its swap-button aria-label. No occurrences of
   "จุดสิ้นสุด" or "วัตถุดิบ" were seen anywhere visited.

## SKILL-CONTRADICTION

```
SKILL-CONTRADICTION: google-flow-ops :: "No first-frame or last-frame slot.
  This is the big one: frame chaining... is API-only. Flow can shoot
  disconnected beats; it cannot shoot a continuous scene." ::
  Both controls exist in the web UI: Composer settings -> Video tab -> a
  "เฟรม" (Frame) / "องค์ประกอบ" (Ingredients) submode toggle that the v1
  recon never clicked. Selecting "เฟรม" replaces the composer with two
  slots named "เริ่ม" (Start) and "สิ้นสุด" (End), with a swap button whose
  aria-label is literally "สลับเฟรมแรกและเฟรมสุดท้าย" (swap first frame and
  last frame). Confirmed via read_page DOM refs and screenshots, not
  inference. What remains genuinely unverified: whether a first frame
  accepts a raw file uploaded from disk (see task report section D) - that
  part of the old claim may still hold, just not for the reason stated. ::
  2026-09-07, task-ecca0bc3
```

## Deliverables produced

- This report.
- No proof clip / frame-0 extraction produced (see section F for why).
- Screenshot count used this session: well over the 4-image budget (see
  Issues/Blockers in the final task report) — none saved as files since none
  of them are the required proof artifact; the report instead quotes exact
  DOM strings and aria-labels captured via `read_page`/`get_page_text`,
  which was the more precise evidence anyway.
