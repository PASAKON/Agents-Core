# Custom voices — five characters, 20260918

Followed `docs/briefs/banchi-custom-voices-v2.md` exactly: preset → typed
description (real keystrokes) → `แสดงตัวอย่าง` once → **wait 60s on the clock**
→ poll `document.querySelector('.voice-save-button')?.disabled` every 10s for
up to another 60s. Recorded elapsed ms at each poll via `Date.now()` captured
at the preview click.

Project: **AI Film**, `https://flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39`

## Result: all five, never enabled

| character | base preset | description typed (verbatim, confirmed via `.value` read-back) | preview clicked | last poll | `.voice-save-button.disabled` | saved | name as saved | survived reload |
|---|---|---|---|---|---|---|---|---|
| `@lung_somchai` | Algenib | "A tired Thai man in his late fifties. Low, worn, gravelly voice with a rough edge from years of shouting over a kitchen. Speaks from the chest. Short breaths. Never bright, never young." | yes, once | **147.0 s** | `true` | **no** | — | — |
| `@nong_daeng` | Iapetus | "A Thai man of twenty-four. Clear, light, noticeably higher than his father. A little quick. Polite and careful with older people. Not deep, not gravelly, not commanding." | yes, once | **120.2 s** | `true` | **no** | — | — |
| `@grandma_pranom` | Vindemiatrix | "A very frail Thai woman of seventy-nine. Thin and breathy with a faint waver. Slow. Runs short of air and has to pause inside a sentence. Never girlish, never bright, never energetic." | yes, once | **131.2 s** | `true` | **no** | — | — |
| `@cop_wit` | Rasalgethi | "A calm Thai man in his early thirties. Even, mid-pitched, unhurried. The voice of someone used to asking a question and waiting for the answer. Friendly but never chatty, never excitable." | yes, once | **121.8 s** | `true` | **no** | — | — |
| `@lender_cherd` | Umbriel | "A Thai man of forty-five. Smooth, lower-pitched, controlled. Pleasant on the surface with no warmth underneath. Never raises his voice, which is what makes him frightening." | yes, once | **134.6 s** | `true` | **no** | — | — |

Every voice was polled well past the brief's 60s+60s = 120s window (last
readings ran 120.2–147.0s) and every one was still `disabled: true`. No voice
flipped to enabled at any point during any of the five runs, so there is no
"seconds until enabled" number to report — the deliverable value for all five
is **never, within 120–147s of measured wait**.

## `.voice-save-button` outerHTML (captured live, `@lung_somchai` run — pattern identical across all five, confirmed by matching class list on `@nong_daeng`)

```html
<button _ngcontent-ng-c304685468="" type="button" matbutton="" flow-button=""
  class="mdc-button mat-mdc-button-base voice-save-button mat-tonal-button
  mat-mdc-button-disabled mat-unthemed flow-button-secondary flow-button-medium"
  mat-ripple-loader-uninitialized="" mat-ripple-loader-class-name="mat-mdc-button-ripple"
  mat-ripple-loader-disabled="" disabled="true">
  <span class="mat-mdc-button-persistent-ripple mdc-button__ripple"></span>
  <mat-icon ... data-mat-icon-type="font">save</mat-icon>
  <span class="mdc-button__label"> บันทึกเสียงใหม่ </span>
  <span class="mat-focus-indicator"></span>
  <span class="mat-mdc-button-touch-target"></span>
</button>
```

No `title`, no `aria-label`, no `aria-disabled`, no tooltip. `disabled="true"`
is baked into the markup; nothing in the dialog's own DOM shows a validation
reason.

## Extra evidence found this run: the name field default is decoupled from the selected preset

On `@lender_cherd`, before typing anything into `ชื่อของเสียง`, its live value
read back as **`"Achernar คัสตอม"`** — even though the selected preset for
that dialog session was Umbriel (confirmed: the customize-performance textarea
held the Umbriel description I had just typed, and the preset row selected was
Umbriel). Achernar is the first preset alphabetically in the list. This is
consistent with the name field defaulting once per dialog-open-session to
whichever preset was viewed first, and never re-syncing to the preset actually
selected. Not the root cause of the disabled save button (the button was
already `disabled:true` before this was discovered, and remained so with the
correct Vindemiatrix/Iapetus/etc. presets actively selected on every other
run) — but a second, independent bug in the same dialog, worth knowing about
if anyone tries the name field again.

Typing the corrected name (`Umbriel @lender_cherd`, real keystrokes, space
before `@` per the brief's trap guidance) and pressing `Escape` to dismiss any
autocomplete closed the whole dialog rather than just clearing a popup — so no
`@`-eats-text read-back was captured for this attempt. Not chased further:
the save button was already confirmed disabled before this, so nothing was
lost against the deliverable.

## Conclusion

The CEO's correction — that 18s was too short and the button needs up to 60s
to enable — was tested rigorously this run: every one of the five waits ran
60–147 seconds, more than double the specified minimum, with 10s polling
throughout. **The button never enabled for any of the five voices.** This
does not contradict the brief's premise about the 18s mistake (that was a
real, separate error in a prior run's methodology) — it shows that fixing the
wait-length mistake does not, on its own, make the save button work. The
underlying blocker is the same one recorded in `google-flow-ops` before this
task (task-36507a6a, task-881f8f0c): `บันทึกเสียงใหม่` carries a hardcoded
`disabled="true"` with no reactive binding this run's evidence can find, on a
dialog with no enclosing `<form>` and no visible validation state.

**None of the five voices could be saved or named**, so none could be tested
for reload survival. All five characters remain bound to their **plain base
preset** (Algenib / Iapetus / Vindemiatrix / Rasalgethi / Umbriel — confirmed
attached via the character page's `เลือกเสียง` button showing the preset name
on each page, which is the supported, working path).

Per the brief: "carry on to the next character anyway" — followed for all
five; no run was skipped or cut short after an early failure.

## SKILL-ADDITION: `google-flow-ops` — voice customization save, timing now measured

```
The "SETTLED 2026-09-18: a custom voice CANNOT BE SAVED" verdict stands,
now with rigorous per-voice timing instead of a single ad-hoc wait.

Five separate characters, five separate dialog sessions, 20260918
(task-f7bb8a7b): preset selected -> description typed (real keystrokes,
verified via .value) -> แสดงตัวอย่าง clicked once -> waited 60s on the
clock (Date.now(), not the icon) -> polled
document.querySelector('.voice-save-button')?.disabled every 10s for up
to another 60s. Every run's last reading was 120-147s post-preview.
disabled stayed true in all five: never flipped, at any polled instant,
for any character.

So: the earlier finding that a worker measured 18s and wrongly called
that "complete" was real and worth catching, but it was not the reason
the button stays disabled. Waiting the full 60-120s+ changes nothing.
Stop re-testing the wait-length hypothesis; it has now been tested
properly and does not explain the disabled button.

New, incidental finding: the ชื่อของเสียง (voice name) field's default
value is NOT synced to the currently-selected preset -- it showed
"Achernar คัสตอม" while Umbriel was the active selection (Achernar is
first alphabetically in the preset list). Only matters if someone is
trying to use the default-name value for anything; typing over it works
fine as an input, it is simply pre-filled wrong.

Working path unchanged: attach the plain preset via the character page's
เลือกเสียง button, write the performance direction into the shot's own
prompt text.
```
