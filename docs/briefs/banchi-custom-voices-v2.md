# Five custom voices — the CEO's own procedure. ZERO credits.

## Read this first: why the last attempt concluded the wrong thing

Three runs reported `บันทึกเสียงใหม่` as permanently disabled and the CTO wrote
it up as a dead product feature. **That was wrong, and the CEO corrected it.**

The button is not broken. It enables only **after the model has finished
processing a preview**, and that takes **30 seconds to a minute**. The last run
pressed preview, watched the icon go `hourglass_top` → `play_arrow` after about
**18 seconds**, called that "preview complete", checked the button and found it
disabled. The icon coming back is **not** the completion signal. The run measured
the wrong thing and then generalised from it.

So the single most important instruction in this brief is: **after pressing
preview, wait on the clock, not on the icon.**

## The procedure, per the CEO

For each of the five voices below:

1. Open the character page → click the voice row → dialog `เลือกเสียง`.
2. Select the **base preset** named in the table.
3. Click into `ปรับแต่งประสิทธิภาพ` and **type** the description (real keystrokes
   — no `form_input`, no DOM value writes). Read `.value` back to confirm.
4. Press **`แสดงตัวอย่าง`** — the tile with the play icon. **Once.**
5. **Wait 60 seconds of wall clock.** Not 18. Not "until the icon changes". Sixty.
   Then poll `document.querySelector('.voice-save-button')?.disabled` every 10
   seconds for up to another 60 seconds.
   **Record the elapsed time at which it flips to `false`** — that number is a
   deliverable, it goes in the skill so nobody re-derives it.
6. Once it is enabled: set `ชื่อของเสียง` to the exact name in the table, then
   click **`บันทึกเสียงใหม่`**.
7. **Reload the page** and confirm the saved voice exists and is bound to that
   character. A voice that does not survive a reload did not save.

## The five

| character | base preset | save as | description to type |
|---|---|---|---|
| `@lung_somchai` | **Algenib** | `Algenib @lung_somchai` | A tired Thai man in his late fifties. Low, worn, gravelly voice with a rough edge from years of shouting over a kitchen. Speaks from the chest. Short breaths. Never bright, never young. |
| `@nong_daeng` | **Iapetus** | `Iapetus @nong_daeng` | A Thai man of twenty-four. Clear, light, noticeably higher than his father. A little quick. Polite and careful with older people. Not deep, not gravelly, not commanding. |
| `@grandma_pranom` | **Vindemiatrix** | `Vindemiatrix @grandma_pranom` | A very frail Thai woman of seventy-nine. Thin and breathy with a faint waver. Slow. Runs short of air and has to pause inside a sentence. Never girlish, never bright, never energetic. |
| `@cop_wit` | **Rasalgethi** | `Rasalgethi @cop_wit` | A calm Thai man in his early thirties. Even, mid-pitched, unhurried. The voice of someone used to asking a question and waiting for the answer. Friendly but never chatty, never excitable. |
| `@lender_cherd` | **Umbriel** | `Umbriel @lender_cherd` | A Thai man of forty-five. Smooth, lower-pitched, controlled. Pleasant on the surface with no warmth underneath. Never raises his voice, which is what makes him frightening. |

## Traps

- **The `@` in the name field opens an autocomplete that eats your typing.** It
  swallowed the text *before* the `@` last time, leaving `@lung_somchai` out of
  `Algenib @lung_somchai`. Type it, press `Escape` to dismiss the popup, and
  **read `.value` back** before saving. Fix with real keys only if it is wrong.
- **Real keystrokes everywhere.** No `form_input`, no `javascript_tool` value
  assignment. `javascript_tool` is for reads only.
- **Do not read the credit balance** from the account menu — it is flaky and cost
  a run 25 minutes. Nothing here costs credits: previews were measured free
  (9,413 → 9,413 across three previews).
- Never press Submit in the video composer.

## If one of them still will not enable

Report it **for that voice**, with the elapsed seconds you waited and the
button's `outerHTML` — and **carry on to the next character anyway**. One
stubborn voice is not evidence about the other four, and that inference is
exactly what went wrong last time.

## Budget

70 steps, 5 screenshots. Answer in text. Waiting is not a step — a 60-second
wait costs one tool call.

## Deliverable

`docs/reports/banchi-voices-v2-20260918/REPORT.md`:
1. a row per voice: saved yes/no · **seconds until the save button enabled** ·
   name as saved · survived reload yes/no
2. the exact name string read back from the field before saving
3. a `SKILL-ADDITION:` block giving the real rule, so the skill stops claiming
   this feature is dead
