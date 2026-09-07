# Flow Voices Installed — 2026-09-08

Task task-879d0324 (browser_operator). CEO order: install a fixed voice on every
speaking character before the next shoot. **0 credits spent, no generation
fired.** Deep link: `https://flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39`.

`route: step 3 (browser action required) — task needs live UI interaction
(selecting voice presets, typing a customization, reading back the actual
attach behavior); no API or prior script exists for this.`

Browser: `select_browser` with `815ddf16-36ea-4e0d-827a-f51e9ff85351` (winbox
Chrome), per `config/hosts.yaml`, done before `tabs_context_mcp` as instructed.

## Credit balance

- **Start: "เครดิต Google Flow 50 เครดิต"** — read from the account menu
  (avatar → account panel), verbatim string.
- **End: "เครดิต Google Flow 50 เครดิต"** — unchanged. Re-read the same way
  after all four characters were tested and the composer was cleared.
- No priced control was clicked. เริ่มสร้าง (Generate) was never touched.

## Read this before the per-character table — two corrections to the task's own premise

Both were found empirically in this session (recon never actually completed an
"add to prompt" — its own report says so explicitly: "I did not create a
custom voice... creating one was explicitly out of scope"). Neither is a
criticism of the recon; this is genuinely new ground.

### 1. Typing a performance description does NOT keep "เพิ่มไปยังพรอมต์" — it swaps in a broken "save new voice" flow

Steps 2–3 of the task assume: type into `ปรับแต่งประสิทธิภาพ`, then click
`เพิ่มไปยังพรอมต์`. That button is **not present** once you type into
`ปรับแต่งประสิทธิภาพ`. The panel instead becomes:

- `ชื่อของเสียง` (Voice name) — a **name field that does exist**, pre-filled
  `"<Preset> คัสตอม"` (e.g. `"Algenib คัสตอม"`) — this directly overturns the
  recon's "no name field" finding, but only in this specific sub-flow.
- `รีเซ็ต` (Reset) — works reliably, reverts to the plain preset and restores
  `เพิ่มไปยังพรอมต์`.
- `บันทึกเสียงใหม่` (Save new voice) — **found permanently disabled** in every
  attempt: after typing the full performance description, after typing a
  single test character, after editing the name field with real keystrokes,
  after clicking `แสดงตัวอย่าง` (preview) and waiting 6+ seconds for it to
  finish. Never became clickable. Confirmed disabled via
  `document.querySelector('.voice-save-button').disabled === true` every time.

**Practical effect: the free-text "customize performance" path cannot be
completed in this session.** I could not get any of the four characters'
performance descriptions actually saved/attached through this sub-flow.

```
SKILL-CONTRADICTION: google-flow-ops :: "Custom voice: choose a base preset,
name it, and describe the change" (implying this path is usable end-to-end)
:: the live panel does expose a name field (contradicting flow-voices-recon-
20260908.md §4's "no name field exists"), but its "บันทึกเสียงใหม่" (Save new
voice) button is unconditionally disabled in this session regardless of name-
field edits, description text, or previewing — never became clickable across
~10 minutes of retries on two different characters. :: 2026-09-08,
task-879d0324.
```

### 2. "เพิ่มไปยังพรอมต์" does not insert any text into the prompt box — it attaches a chip, and the chip starts disabled

Clicking `เพิ่มไปยังพรอมต์` on an **unmodified** preset (no typed
customization) works and is reliable. But it does not write anything into the
`[contenteditable="true"]` prompt field — verified directly:

```js
document.querySelector('[contenteditable="true"]').innerText
// -> "คุณต้องการสร้างอะไร"   (the unchanged placeholder, both before and after)
document.querySelector('[contenteditable="true"]').innerHTML
// -> only the placeholder span + ProseMirror trailing-break, no inserted content
```

What actually gets added is a **`<flow-audio-ingredient-chip>`** element (same
component family as Character/Ingredient chips) in the composer's ingredient
bar, above the text field — not inside it. Its icon carries class
`chip-container disabled`, and hovering it shows the tooltip **"องค์ประกอบเสียง
ต้องมีองค์ประกอบอื่นๆ จึงจะทำงานได้"** ("a voice ingredient needs other
ingredients to work") — consistent with the documented rule that a voice
reference only functions alongside another ingredient (e.g. a Character chip)
in the same generation, but new confirmation that the chip is inert/disabled
by itself and stays that way until another ingredient joins it.

```
SKILL-CONTRADICTION: google-flow-ops / task premise :: "the durable artifact
is... the exact string Flow inserts into the prompt box" (i.e. voice
attachment writes literal text into the contenteditable) :: it does not — it
attaches a `<flow-audio-ingredient-chip>` object outside the text field; the
contenteditable's innerText/innerHTML is provably unchanged
(`คุณต้องการสร้างอะไร` placeholder only) before and after attaching. There is
no "verbatim inserted prompt string" to capture as text; the reference lives
as a UI-level chip, and (per §6 of the recon and the tooltip observed here)
stays inert until another ingredient is attached alongside it. :: 2026-09-08,
task-879d0324.
```

### 3. The earlier "Algenib is missing from the picker" reading was a rendering glitch, not real absence — confirms the recon's documented winbox trap

Mid-session, searching `เสียง` for "Algenib" returned `ไม่พบชิ้นงาน` (no items
found) and the unfiltered alphabetical list skipped straight from Achird to
Algieba. A fresh picker open minutes later showed Algenib correctly, in its
proper alphabetical slot, label intact ("Male, gravelly, low pitch"). This
matches `flow-voices-recon-20260908.md`'s own technical note: this tab ran
`document.hidden === true` for the entire session (confirmed again here:
`document.hidden` was `true` immediately after every navigation), which
intermittently breaks `cdk-virtual-scroll-viewport` re-rendering. **No
substitution was needed or made** — all four CTO-assigned presets exist
exactly as named. Lesson for the next operator: a single "not found" on this
box is not sufficient evidence a preset was removed; reopen the picker fresh
before concluding a preset is gone.

## Per-character result

All four presets were verified present with their exact labels, then attached
to the composer via the base (non-customized) `เพิ่มไปยังพรอมต์` flow — the
only flow proven to work in this session (see finding #1 above). The intended
performance description for each is recorded below and written into the
script's VOICE LOCK line, but **could not be committed into Flow's own
"customize performance" mechanism** — the CEO or a future operator will need
to either retry `บันทึกเสียงใหม่` once the product fixes it, or achieve the
same intent by writing the performance description into the shot's own video
prompt text (outside the Voices panel) alongside the attached voice chip.

| Character | Preset | Label (verbatim) | Performance description (intended; not committed via Save — see finding #1) | Attach result |
|---|---|---|---|---|
| @lung_somchai | **Algenib** | Male, gravelly, low pitch | Speaks Thai. A tired 58-year-old Thai noodle-shop owner. Low, gravelly, unhurried. Warm underneath but holding something back. Never raises his voice. | Chip attached via base flow, confirmed via `flow-audio-ingredient-chip` in DOM, then cleared with ล้างพรอมต์ before moving on |
| @nong_daeng | **Iapetus** | Male, clear, mid-low pitch | Speaks Thai. A 24-year-old Thai man, recently graduated. Clear and direct, a little tight with held-back emotion. Respectful when speaking to his father. | Chip attached via base flow, confirmed, then cleared |
| @grandma_pranom | **Gacrux** | Female, mature, mid pitch | Speaks Thai. A frail 79-year-old Thai woman, seriously ill. Thin, breathy, slow. Short phrases, running out of air. Gentle. | Chip attached via base flow, confirmed, then cleared |
| @lender_cherd | **Umbriel** | Male, smooth, lower pitch | Speaks Thai. A 45-year-old Thai money lender. Smooth, controlled, friendly on the surface with a threat underneath. Never shouts. | Chip attached via base flow, confirmed, then cleared |

No CTO-assigned preset needed substitution — all four exist in the picker
verbatim (see finding #3). Composer was cleared with `ล้างพรอมต์` after each
character; confirmed via
`document.querySelectorAll('mat-icon')` filtered for text `voice_selection`
returning `0` before moving to the next, so the four never piled up together
at any point.

## Screenshot

One representative screenshot was captured of the customize panel with
Algenib selected and the intended performance description typed into
`ปรับแต่งประสิทธิภาพ` (before finding #1's dead end was discovered): visible
in that shot are the preview swatch, `ตัวอย่างบทสนทนา` (0/120, untouched), the
typed `ปรับแต่งประสิทธิภาพ` text, and the `ชื่อของเสียง` field reading
"Algenib คัสตอม" with `รีเซ็ต` / `บันทึกเสียงใหม่` (disabled) — this is the
exact panel state finding #1 describes. It was not saved to a file (this
report describes it in place of an attached image, consistent with how
`flow-voices-recon-20260908.md` reported its own screenshots).

## Budget

- **Steps used:** well over the nominal 40-step target — this task turned into
  a live investigation of two undocumented product behaviors (the disabled
  Save button, and the chip-not-text attach mechanism), which the recon
  explicitly had not tested. Roughly 90 browser tool calls across the session,
  including two tab restarts after the known winbox traps (a collapsed
  308x115 tab, and one MCP tab-group destruction) both recovered per the
  skill's documented procedure.
- **Screenshots taken:** well over the "1 screenshot" target during
  troubleshooting (confirming panel states, the disabled-button investigation,
  the collapsed-tab recovery). Only one is described above as the deliverable
  per the task's actual ask.
- **Window size:** 1920x911 native; `resize_window` was not attempted since
  the skill documents it as a no-op on this host.

## Replay script

**None.** This flow is not stable enough to script yet: the customize/save
path is broken (finding #1), the base attach path produces a disabled chip
whose only observed unlock condition is "another ingredient present" (not
tested further — out of scope for a 0-credit task), and the picker's virtual
scroll is unreliable on this host (finding #3). A script written against
today's DOM would encode a disabled Save button as if it were normal. Once the
CEO/product side resolves finding #1, a replay script for "attach preset X,
type description Y, save" would be worth writing.

## Notes for reviewer

- This task's own premise (§ of TASK.md: "the durable artifact... is the
  exact string Flow inserts into the prompt box") does not hold on the live
  product — see finding #2. The VOICE LOCK lines added to the script record
  the preset + intended performance description instead, since no inserted
  prompt string exists to copy.
- The CEO should be told directly that `บันทึกเสียงใหม่` is dead in this
  session before scheduling any dialogue shoot that assumes a saved custom
  voice — the shoot can still proceed with the four *base* presets attached
  (no custom performance tuning), which is what the script now locks.
