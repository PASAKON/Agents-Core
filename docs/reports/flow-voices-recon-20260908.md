# Flow Voices Recon — 2026-09-08

READ-ONLY RECON, task-e3bf2fa9. Zero credits spent. Deep link:
`https://flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39` (the
teaser project, plates and Ingredients @lung_somchai, @nong_daeng,
@noodle_shop already live there).

## 1. Credit balance

- **Start: 50 เครดิต** ("เครดิต Google Flow 50 เครดิต", read from the account
  menu, `pass.gob1@gmail.com`).
- **End: 50 เครดิต** — unchanged. Verified by re-opening the account menu
  after all testing and reading the same string.
- No generation was fired, no priced control was clicked. The only actions
  taken (attaching/removing an ingredient chip, opening menus, changing
  settings-panel radios to read cost estimates) are the free actions this
  skill file's cost table already documents as 0 credits.

## 2. Is there a "Voices" entry under the Add (+) button in Ingredients?

**Yes.** With the composer in `องค์ประกอบ` (Ingredients) submode, clicking
the Add ingredient button (`เพิ่มองค์ประกอบลงในช่องพรอมต์`) opens a category
picker whose category-navigation tabs are, verbatim:

```
ทั้งหมด (all) · รูปภาพ (image) · วิดีโอ (video) · เสียง (voice, icon
"voice_selection") · ตัวละคร (character) · รูปโปรไฟล์ (profile picture) ·
การอัปโหลด (upload)
```

`เสียง` is a first-class category alongside `ตัวละคร` (Characters), not a
sub-item hidden under something else. The account is **PLUS tier** (badge
next to avatar reads "PLUS"), so the feature is present at least at the PLUS
level — this does not test whether a lower tier than PLUS also has it, since
there is no lower tier to compare against on this account.

## 3. Full preset voice list, verbatim

**30 presets total**, alphabetical by name. Confirmed complete: the picker
list is `cdk-virtual-scroll-viewport` (Angular virtual scrolling) and only
render ~15 DOM nodes at a time; the search/filter box in the same panel does
a substring match over the *entire* underlying data set (confirmed by
searching single letters and getting hits far outside the visible scroll
window, e.g. searching "z" surfaced "Zephyr" and "Zubenelgenubi" with the
list scrolled to the top). Every name below was read directly off a live
filtered result, not inferred. No voice was played; only the text was read.

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

Notes on the data, not guesses:
- One voice ("Pulcherrima") is explicitly labelled **"Ungendered"**, not
  male/female — copied verbatim, not an inference.
- No language or accent tag appears on any entry — only gender/ungendered,
  a one-or-two-word tone descriptor, and a pitch band (high / mid-high / mid
  / mid-low / low / lower / younger). The docs' claim of "language, gender,
  age, accent, style" tags is **only partially true on this account**: gender
  and a style-ish tone word are present; no explicit language, age, or accent
  field exists anywhere in the UI.
- I did not hear any preview — every string above was read as text
  (`textContent`) off the live DOM, never inferred from the name.

## 4. Custom-voice flow

**Yes, it exists**, and it lives inside the same detail panel that opens the
moment you select any one preset from the Voices list (selecting a preset
does not immediately attach it — it opens a side panel first). The panel's
verbatim UI, top to bottom:

1. A preview swatch (colour gradient) with a **`แสดงตัวอย่าง`** (Show/Play
   preview) button.
2. **`ตัวอย่างบทสนทนา`** (Example dialogue) — a `<textarea>`,
   `maxlength="120"`, counter shown as **`0 / 120`**. Its placeholder/default
   sample text (verbatim, this is the TTS demo line Google ships, not
   something I typed):
   > สวัสดี ขอแนะนำฟีเจอร์ใหม่ ตอนนี้ฉันสามารถอ่านออกเสียงข้อความนี้ด้วยเสียงที่เป็นธรรมชาติคล้ายกับเสียงของมนุษย์ได้แล้ว
3. **`ปรับแต่งประสิทธิภาพ`** (Customize performance) — a static label, not a
   toggle, directly over a second `<textarea>` (2 rows, **no `maxlength`
   attribute found** — unlike the field above, this one is not
   character-capped at the DOM level):
   placeholder **`อธิบายรูปแบบการแสดงเสียง...`** ("Describe the voice
   performance style...") — this is the "describe a modification" field the
   docs mention (e.g. "make it sound raspy with a New York accent").
4. **`เพิ่มไปยังพรอมต์`** (Add to prompt) — the confirm button.

**Discrepancy vs. the docs:** the docs say you "name it" as part of the
custom-voice flow. **No separate name field exists in this panel** — I
searched every `<input>`/`<textarea>` on the page while the panel was open
and found only the two textareas above plus the general search box. Naming
may happen at a later step (e.g. renaming the resulting chip, the way a
Character/Ingredient plate gets renamed after creation) but that step was
not reached — creating one was explicitly out of scope for this task.

**I did not create a custom voice.** Selecting "Achernar" to open this panel
did attach an ingredient-style chip to the composer (see §6) — it was removed
before finishing, see below.

## 5. Gemini Omni Flash 1.1 — presence, cost, 360p draft option

- **Model name in this UI is "Omni 1.1 Flash"**, not "Gemini Omni Flash 1.1"
  — the word order and "Gemini" prefix from the docs do not appear anywhere
  in the model picker. This is the same model the docs mean (it is the one
  the Voices feature requires), just a different exact string. Reporting the
  literal UI string per instructions.
- **It is the account's default model** — it was already selected on fresh
  project load, before I touched anything, matching this skill file's
  existing note that the model resets to "Omni 1.1 Flash" on reload.
- Full model list in the picker (`เลือกกลุ่มผลิตภัณฑ์โมเดล` dropdown),
  verbatim, in order: **Omni 1.1 Flash, Veo 3.1 - Lite, Veo 3.1 - Fast,
  Veo 3.1 - Quality.**
- **Live credit-estimate readings for Omni 1.1 Flash** (read from
  `การสร้างจะใช้ N เครดิต` next to the settings panel, never submitted):

  | Resolution | Duration | Cost |
  |---|---|---|
  | 720p | 8s | **12 credits** |
  | 720p | 10s | **15 credits** |
  | 360p | 8s | **6 credits** |
  | 360p | 10s | **7 credits** |

  360p is close to exactly half of 720p at the same duration (6/12 = 0.50,
  7/15 ≈ 0.47 — the 10s figure rounds down rather than landing on the exact
  half of 7.5). This matches the docs' "360p draft at half cost" claim
  closely enough to confirm it, with the caveat that Google appears to floor
  the result rather than track it exactly.
- **Comparison to the known Veo 3.1 Fast baseline (20 credits at 8s,
  measured elsewhere):** Omni 1.1 Flash at 8s/720p is **12 credits — 8
  cheaper than Veo Fast**, not the same price. The docs never claim price
  parity, but this is worth stating since nothing in the docs gives Omni's
  price at all — that was this task's job.
- These numbers were identical whether the submode was `เฟรม` or
  `องค์ประกอบ` (12 credits either way at 8s/720p/x1) — cost is driven by
  resolution/duration/model, not by which composer submode is active.

## 6. Does picking Omni Flash change what the composer offers?

**No — the ingredient chips and the เฟรม/องค์ประกอบ submode toggle are both
still there and both still work with Omni 1.1 Flash selected.** Everything in
this recon (browsing @lung_somchai/@nong_daeng/@noodle_shop as ingredient
tiles, opening the Voices category, opening the custom-voice panel) was done
with Omni 1.1 Flash as the active model — it was never switched to a Veo
model at any point, because it didn't need to be; nothing in the ingredients
UI was greyed out or hidden under it.

One thing IS Omni-specific: the **`เสียง` (Voices) category itself only
makes sense to attach under Omni**, per the docs' claim that "voice
references work only on generations that use ingredients" — I did not test
firing a generation with a voice chip attached under a Veo model to see
whether it errors, since that would require an actual submit click, which is
out of scope for a zero-spend recon.

## 7. Plan-tier gating text

**None found.** Scanned the full page text for "Ultra", "Pro", "upgrade to…"
and the Thai equivalents while the Voices panel, the custom-voice panel, and
the model/settings panel were all open. The only upgrade-flavoured text
anywhere is the generic low-credit banner, which is about the monthly credit
pool, not about voices or Omni Flash specifically:

> เครดิต Google Flow เหลือน้อย เครดิตจะรีเซ็ตทุกเดือน หรืออัปเกรดเพื่อรับเพิ่มตอนนี้
> ("Google Flow credits are running low. Credits reset every month, or
> upgrade to get more now.")

No text anywhere ties Voices, custom voices, or Omni Flash to a specific
plan tier above what this PLUS account already has.

## 8. Screenshots (2 of the allowed 3 taken)

1. Voice list (Achird→Erinome visible) **and** the custom-voice/performance
   panel for the selected preset (Achernar), both in one shot — the
   `ตัวอย่างบทสนทนา` 0/120 field, `ปรับแต่งประสิทธิภาพ` label + description
   field, and `เพิ่มไปยังพรอมต์` button are all visible.
2. The model picker open (all four models listed) with the settings panel
   below it showing 360p/720p, duration, quantity, and the live
   `การสร้างจะใช้ 12 เครดิต` estimate.

A third screenshot (project overview) was taken earlier for orientation but
is not one of the three requested captures and isn't attached here — the two
above cover everything the task asked for.

## Technical note for the next operator: this tab ran `document.hidden` the
entire session

`document.visibilityState` read `"hidden"` from the very first `wait` after
navigation through to the end of the task, on **two separate tabs**
(including a fresh one opened specifically to clear it, per this skill's
existing "tab collapses to 98x74" note). This did not match that documented
trap — `innerWidth`/`innerHeight` were normal (1568x744 / 1920x911), and the
tab was always `tabs_context_mcp`'s `selectedTabId`. The practical effect:

- **`computer screenshot` / `zoom` frequently timed out** (30s CDP timeout,
  "renderer may be frozen") when called right after a click, but usually
  succeeded on a retry a few seconds later. Pattern looked like the
  underlying Chrome window being occluded/backgrounded on the Windows
  desktop rather than a page-level freeze — `window.focus()` reported
  `document.hasFocus() === true` even while `visibilityState` stayed
  `"hidden"`.
- **This broke `cdk-virtual-scroll-viewport` rendering specifically.**
  Setting `scrollTop` (and even manually dispatching a `scroll` event) on the
  Voices list's virtual-scroll container updated `scrollTop` but never
  re-rendered the DOM window of visible options — consistent with Angular's
  virtual-scroll update path being gated behind rendering that a hidden tab
  throttles. `scroll_to` (i.e. `scrollIntoView` on a ref) had the same
  no-op result.
- **Workaround that worked:** the panel's own search/filter textbox performs
  a substring match against the full underlying dataset regardless of scroll
  position, and re-renders fresh results at the top of the (now short)
  virtual window every time — which does re-render correctly even in this
  state. All 30 voice names were recovered this way, not by scrolling.
- **Ordinary clicks, radio toggles, tab navigation, and text reads all
  worked fine** despite the hidden state — only the virtual-scroll list was
  actually broken by it. Screenshot commands worked intermittently (roughly
  1-in-3 to 1-in-2 tries, no clear pattern), and text-based reads
  (`javascript_tool`, `read_page`) worked every time.

SKILL-CONTRADICTION: google-flow-ops :: "resize_window never takes effect on
winbox — innerWidth stayed 1920" (implying screenshots are just expensive,
not broken) :: on this run the winbox tab was `document.hidden` for the
entire session regardless of resize, which intermittently broke
`screenshot`/`zoom` outright (CDP timeout) and fully broke the Voices list's
virtual scroll (no re-render on `scrollTop` change or `scrollIntoView`);
text-based reads were unaffected and became the only reliable way to read a
long virtualized list. :: 2026-09-08, task-e3bf2fa9.

## Composer state left as found

One voice chip (Achernar) was attached to the shared composer while testing
§4/§6, then explicitly removed (clicked its `cancel` icon) once confirmed —
`document.querySelectorAll('img[alt="voice_selection"]')` returned 0 at the
end of the session. A pre-existing character chip (`@nong_daeng`, icon
`accessibility_new`) was already present in the composer before I opened the
Voices picker and was left untouched, since it was not something this task
added. No prompt text was typed, no generation was submitted, no settings
were left changed (resolution/duration were poked to read costs and are back
at the account defaults — 720p/8s/x1 — since navigating away/reopening resets
to those anyway).

## Steps used

Well under the 40-minute wall-clock budget. Browser action count: ~55 tool
calls (higher than the nominal 35-step target), driven almost entirely by the
hidden-tab issue above — screenshot retries, and working around the broken
virtual scroll via per-letter search probes instead of one scroll pass. No
step was spent on anything the task told me to avoid (no Generate/Upgrade/
Subscribe click, no Scenebuilder, no History, no test generation).
