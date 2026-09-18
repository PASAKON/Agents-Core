# «บัญชี» — settle WHY `บันทึกเสียงใหม่` is disabled. One character. ZERO credits.

## The job

Find out, with evidence, whether Flow's custom-voice **save** button is broken
(Google's fault, escalate) or whether we have been driving the form wrong
(our fault, fixable today). Produce a probe table. Do **not** try to build five
voices — this task's deliverable is the answer, not the voices.

## What the last run established (task-36507a6a, merged)

- The character page → voice row → `เลือกเสียง` dialog path is real.
- Typing into `ปรับแต่งประสิทธิภาพ` reveals `ชื่อของเสียง` (pre-filled
  `<Preset> คัสตอม`), `รีเซ็ต`, and `บันทึกเสียงใหม่`.
- Preview generation works and produces real audio. It costs **0 credits**
  (9,413 → 9,413 across 3 previews).
- `บันทึกเสียงใหม่` reported `disabled: true` in every state tried.

## Why that is not yet a verdict — the untested hypothesis

That run set field values with `form_input` / direct DOM value assignment, and
verified them by reading `.value` back. **Angular Material forms do not observe
a programmatic `.value` write.** The `FormControl` stays pristine and empty, so
the form stays invalid and the save button stays disabled forever — while a
preview built from the DOM value still works perfectly. That single detail
explains every symptom seen, and it has never been tested.

Second, smaller hypothesis: the intended name `Algenib @lung_somchai` contains
`@`, which triggered an autocomplete that ate the text before it. `@` may be
rejected by the field outright.

## Hard rules for this task

1. **No DOM writes. Anywhere. At all.** Every character that lands in a field is
   typed through the `computer` tool's keyboard. No `form_input`, no
   `javascript_tool` assignment, no `.click()`, no `removeAttribute`. If a field
   ends up wrong, clear it with real keys (`cmd+a`, then `Delete`) and retype it.
   This rule is the entire point of the task — breaking it destroys the result.
2. `javascript_tool` is allowed for **reads only**: `.value`, `.disabled`,
   `.className`, `.getAttribute(...)`. Never a write.
3. **Zero credits.** Preview is free and proven. Never press Submit in the
   composer. Read the balance at the start and at the end and report both. If
   anything anywhere shows a credit cost, stop and report.
4. Do not change any character's existing voice binding except as a variant
   below explicitly requires, and say in the report what you changed.

## The probe

Character: **`@lung_somchai`**. Base preset: **Algenib** (already his binding).

After **every** lettered step, read and record both of these:

```js
document.querySelector('.voice-save-button')?.disabled
document.querySelector('.voice-save-button')?.className
```

The resulting table is the deliverable.

### Variant A — real keystrokes, no `@` in the name

- **A1** open the character page → click the voice row → dialog `เลือกเสียง`
- **A2** click **Algenib** in the preset list
- **A3** click into `ปรับแต่งประสิทธิภาพ` and **type** (real keys):
  `Warm, tired, low-pitched older man. Speaks slowly and gently, with long pauses.`
  then read `.value` back to confirm it landed
- **A4** ← record save state
- **A5** click into `ชื่อของเสียง`, `cmd+a`, `Delete`, then **type**
  `Algenib lung somchai` (deliberately **no `@`**)
- **A6** ← record save state
- **A7** click `แสดงตัวอย่าง`, wait for the preview to complete (icon returns to
  `play_arrow`)
- **A8** ← record save state
- **A9** if it is enabled: click `บันทึกเสียงใหม่`, then **reload the page** and
  report whether the saved voice exists and is bound. **Stop here — that is the
  answer.**

### Variant B — only if A8 is still disabled. Press `รีเซ็ต` first.

Identical to A, except **never touch the name field** — leave it at its
pre-filled `Algenib คัสตอม`. Type the description with real keys, run the
preview, record the save state. This isolates whether editing the name is what
breaks it.

### Variant C — only if A or B succeeded

Repeat the winning variant, but name it `Algenib @lung_somchai` (the CEO's
convention). The `@` will probably open an autocomplete — try dismissing it with
`Escape` and continuing. Report whether an `@` name can be saved at all, and if
not, what the closest legal name is. Do not fight this for more than ~5 steps.

### Variant D — only if A and B both stay disabled

Stop typing and gather the product's own explanation. Read and quote verbatim:
- `title`, `aria-label`, `aria-disabled`, `matTooltip` on the save button
- any sibling/parent error, hint or helper text in the dialog
- the button's full `outerHTML`
- whether the dialog sits inside a `<form>`, and if so that form's classes
  (`ng-invalid` / `ng-valid` / `ng-pristine` / `ng-dirty`)

## Stopping condition

Stop the moment a save succeeds, or when A, B and D are done. Nothing else.

## Budget

50 steps, 6 screenshots. **Answer in text**, not pictures.

## Deliverable

`docs/reports/banchi-voice-probe-20260918/REPORT.md` containing:
1. the probe table (step → `disabled` → `className`)
2. the verbatim tooltip / aria / helper text from Variant D, if it ran
3. credit balance before and after
4. a one-line verdict, exactly one of:
   - `VERDICT: METHOD` — ours, save works when driven with real keystrokes
   - `VERDICT: PRODUCT` — Google's, save cannot be enabled by any input method
