# «บัญชี» voice-save probe — real keystrokes only, task-881f8f0c

Character: `@lung_somchai`, base preset **Algenib** (existing binding).
Project: "AI Film" (`flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39`).
Every field write in this run was a real `computer` keyboard event — no
`form_input`, no DOM `.value =`, no synthetic `.click()`. `javascript_tool`
was used for reads only (`.value`, `.disabled`, `.className`, attributes).

## Credit balance

| | เครดิต Google Flow |
|---|---|
| start | **9,413** |
| end | **9,413** |

Delta: **0**. Two previews run (one per variant), both free, matching the
prior run's measurement. Submit in the video composer was never pressed.

## Probe table

| Step | Action | `.voice-save-button` disabled | className |
|---|---|---|---|
| A1 | Open `@lung_somchai` → click bound `algenib` voice row → `เลือกเสียง` dialog opens | *(button not yet rendered — plain flow only shows `เพิ่มลงในตัวละคร`, `disabled:false`)* | `detail-add-to-prompt-btn` |
| A2 | Click **Algenib** in preset list (already selected) | — | — |
| A3 | Click into `ปรับแต่งประสิทธิภาพ`, type (real keys) the performance description; read `.value` back | value confirmed landed verbatim | — |
| A4 | Record save state after A3 | `true` | `...voice-save-button mat-mdc-button-disabled...` |
| A5 | Click `ชื่อของเสียง`, `cmd+a`, `Delete`, type `Algenib lung somchai` (no `@`); read `.value` back | value confirmed landed verbatim (`Algenib lung somchai`) | — |
| A6 | Record save state after A5 | `true` | `...voice-save-button mat-mdc-button-disabled...` |
| A7 | Click `แสดงตัวอย่าง`, wait for icon `hourglass_top` → `play_arrow` (~18s) | preview completed successfully | — |
| A8 | Record save state after A7 | `true` | `...voice-save-button mat-mdc-button-disabled...` |
| — | A9 not run: button still disabled at A8 | | |
| B0 | Click `รีเซ็ต` | name field disappears, performance field clears, `.voice-save-button` not present in DOM (plain-preset flow restored) | — |
| B1 | Click into `ปรับแต่งประสิทธิภาพ`, type (real keys) the same performance description — **name field never touched**; read `.value` back | value confirmed landed verbatim | — |
| B2 | Record save state after B1 (name field auto-reappeared, pre-filled `Algenib คัสตอม`, untouched by us) | `true` | `...voice-save-button mat-mdc-button-disabled...` |
| B3 | Click `แสดงตัวอย่าง`, wait for `hourglass_top` → `play_arrow` (~20s) | preview completed successfully | — |
| B4 | Record save state after B3 | `true` | `...voice-save-button mat-mdc-button-disabled...` |

Variant C skipped per brief (only runs if A or B succeeded — neither did).

## Variant D — the product's own explanation

Read directly off the live DOM of `.voice-save-button` after Variant B:

```html
<button type="button" matbutton="" flow-button=""
  class="mdc-button mat-mdc-button-base voice-save-button mat-tonal-button
         mat-mdc-button-disabled mat-unthemed flow-button-secondary flow-button-medium"
  mat-ripple-loader-uninitialized="" mat-ripple-loader-class-name="mat-mdc-button-ripple"
  mat-ripple-loader-disabled="" disabled="true">
  <span class="mat-mdc-button-persistent-ripple mdc-button__ripple"></span>
  <mat-icon ... data-mat-icon-type="font">save</mat-icon>
  <span class="mdc-button__label"> บันทึกเสียงใหม่ </span>
  <!---->
  <span class="mat-focus-indicator"></span>
  <span class="mat-mdc-button-touch-target"></span>
</button>
```

- `title`: `""` (empty)
- `aria-label`: `null`
- `aria-disabled`: `null`
- `matTooltip` / `ng-reflect-message`: `null`
- Sibling/parent text in the same control row: `restart_alt\nรีเซ็ต\nsave\nบันทึกเสียงใหม่` — no hint or helper text anywhere near the button
- Whole-dialog scan for `.mat-mdc-form-field-error, .error, [class*="error"], mat-hint, mat-error`: **zero matches** — no validation error is rendered anywhere in the dialog
- `btn.closest('form')`: **`null`** — the dialog is not wrapped in a `<form>` element at all, so there is no `ng-invalid`/`ng-valid`/`ng-pristine`/`ng-dirty` class to read
- Checked in case of a hidden gate: a `g-recaptcha-response` textarea exists and **does carry a populated token** — but it is a page-wide Google reCAPTCHA element (1 iframe, 4 recaptcha-class divs), not scoped to this dialog, so it is not evidence of anything voice-specific.

**Conclusion of Variant D: the button carries no explanation of any kind.** No
tooltip, no aria state, no inline error, no form validity class to inspect. It
is simply hard-coded `disabled="true"` regardless of what real, verified-landed
input the two form fields hold.

## Verdict

Both required text fields (`ปรับแต่งประสิทธิภาพ` performance description and
`ชื่อของเสียง` voice name) were driven with real keyboard events exactly as the
brief mandates, and both were independently confirmed to hold the typed value
by reading `.value` straight off the live `<textarea>`/`<input>` elements —
not assumed, not read from a screenshot. This rules out the task's lead
hypothesis (Angular Material not observing a programmatic `.value` write):
there was no programmatic write anywhere in this run, and the save button
stayed `disabled: true` in every one of the 6 recorded states across both
Variant A (renamed, no `@`) and Variant B (name untouched, left at the
pre-filled preset name). The `@` hypothesis was never reached as a distinct
cause because Variant B — which never touches the name field at all — already
reproduces the same permanently-disabled state as Variant A.

`VERDICT: PRODUCT`
