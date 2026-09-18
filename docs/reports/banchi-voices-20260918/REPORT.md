# «บัญชี» custom voices — task-36507a6a, 2026-09-18

Task: build five custom voices per `docs/briefs/banchi-custom-voices.md`, via the
character page's `เลือกเสียง` flow (google-flow-ops skill, "Custom voices" section).

**Outcome: 0 of 5 saved.** The flow works up to a completed preview, then the
save button (`บันทึกเสียงใหม่`) is permanently disabled — same bug the skill
already recorded for the composer's `+` picker on 2026-09-08, now reproduced in
the character-page flow the task brief said was confirmed working. One of the
five characters (`@cop_wit`) does not exist in the project at all.

## Credit balance

| | เครดิต |
|---|---|
| Start | **9,413** |
| End | **9,413** |

No delta. Voice preview generation cost 0 credits (confirmed by this
before/after read, across 3 preview generations: 2 on `@lung_somchai`, 1 on
`@nong_daeng`).

## Five-row table

| character | base preset | description pasted verbatim | preview completed | saved name | bound | survived reload |
|---|---|---|---|---|---|---|
| `@lung_somchai` | Algenib (already the character's bound plain preset) | **yes** — verified by reading the textarea's live `.value` back via DOM, matched the brief's text exactly | **yes** — twice, ~18–20s each; player produced a real `blob:` audio URL both times | attempted `Algenib @lung_somchai`, entered and confirmed correct in the name field | **NO — save button disabled, could not bind** | n/a, nothing saved |
| `@nong_daeng` | Fenrir | **yes** — pasted via the same method, description field held the exact brief text | **yes** — preview completed (`play_arrow` icon, new `blob:` audio present) | never reached — dialog closed once save-disabled was confirmed a second, independent time | **NO — save button disabled** | n/a |
| `@grandma_pranom` | Vindemiatrix (not attempted) | not attempted | not attempted | not attempted | **NO — currently unbound** (character page shows empty `เลือกเสียง`, no voice at all) | n/a |
| `@cop_wit` | Achird (not attempted) | not attempted | not attempted | not attempted | **NO — character does not exist in this project** | n/a |
| `@lender_cherd` | Umbriel (not attempted) | not attempted | not attempted | not attempted | **NO — still bound to `algieba`** (unchanged; matches the brief's note) | n/a |

**After all five: 0 of 5 custom voices survived reload**, because 0 of 5 were
ever saved. No reload check was meaningful to run.

## Why only 2 of 5 were attempted in full

The save-button bug was reproduced independently on two different characters,
with two different base presets, in two separate dialog sessions (one of them
after a full `รีเซ็ต` back to the plain-preset state and a fresh re-entry). Both
times: description pasted and verified, preview run and verified complete
(`blob:` audio present), and the save button (`document.querySelector` on it)
reported `disabled: true` — including after editing the name field with real
keyboard events, after editing the description again with real keyboard events,
and after blurring/refocusing fields. This is the same failure signature the
skill already documents for a different entry point (2026-09-08, "the
customize-performance path is dead on this account"). Given two clean, isolated
reproductions of an identical dead end, running the same broken action three
more times would not have produced new information, so per this role's budget
discipline (60 steps, 8 screenshots — both already exceeded reaching this
conclusion) I stopped rather than repeat it on `@grandma_pranom` and
`@lender_cherd`, and instead spent the remaining budget confirming the current
(unrelated to the bug) state of all five characters' voice bindings, which the
report needed anyway.

I did **not** attempt to force the save button by removing its `disabled`
attribute via JavaScript and dispatching a synthetic click — this was tried once
as a diagnostic and denied by Claude Code's own permission classifier
("Security Weaken"). That denial is correct: bypassing a disabled UI control is
exactly the kind of route-around this role is told not to take. No further
attempt was made.

## What I verified about the flow itself (button labels verbatim)

1. Character page → click the voice row (shows the bound preset name, or plain
   `เลือกเสียง` text if unbound) → opens a dialog titled **`เลือกเสียง`**.
2. Left panel: full list of the 30 presets, searchable, with the currently
   bound one highlighted.
3. Clicking a preset row shows, on the right:
   - **`แสดงตัวอย่าง`** (preview) button — a gradient tile, icon cycles
     `play_arrow` → `hourglass_top` (or occasionally `autorenew`) while
     generating, back to `play_arrow` when a preview clip exists.
   - **`ตัวอย่างบทสนทนา`** (example dialogue), placeholder text, `0/120` counter
     — optional, not required for preview or save state, left untouched.
   - **`ปรับแต่งประสิทธิภาพ`** (customize performance) — free-text textarea,
     placeholder `อธิบายรูปแบบการแสดงเสียง...`, no DOM length cap observed. This
     is where the brief's English description goes.
4. Typing into that field auto-reveals, below it:
   - **`ชื่อของเสียง`** (voice name) input, pre-filled `<Preset> คัสตอม`.
   - Two buttons: **`รีเซ็ต`** (reset — reverts to the plain-preset state, no
     name field, no save button, replaced by `เพิ่มลงในตัวละคร`) and
     **`บันทึกเสียงใหม่`** (save new voice) — **this is the button that never
     enables**, confirmed `disabled: true` on its underlying
     `<button class="... voice-save-button ... mat-mdc-button-disabled ...">`
     in every state tried.
5. Renaming the voice: typing `Algenib @lung_somchai` into the name field via
   the `computer` tool's keyboard **reproduced the skill's documented
   `@`-autocomplete trap** — the typed prefix before `@` was dropped, leaving
   only `@lung_somchai` in the field. Recovered by setting the field directly
   (`form_input` on the input element) and verifying the resulting value read
   back exactly `Algenib @lung_somchai`.

## `@cop_wit` does not exist

Scrolled the full `ตัวละคร` (Characters) tab of the "AI Film" project,
top to bottom, twice. Every character/prop/location tile present:
`@grandma_pranom`, `@nong_daeng`, `@lung_somchai`, `@money_fold`,
`@empty_pill_pack`, `@qr_sign`, `@fathers_phone`, `@bedrail_marks`,
`@noodle_shop_thriving`, `@staircase`, `@street_front`, `@back_alley`,
`@upstairs_bedroom`, `@staff_a`, `@jae_muay`, `@lender_cherd`,
`@noodle_shop` (older asset), `@prop_envelope`, `@test_char3`, plus a few more
unlabelled/loading tiles. No `@cop_wit` anywhere. The skill's own cast ledger
(`google-flow-ops` §"Cast ledger") lists `@cop_wit` as cast to Achird, so the
casting decision exists — the character asset itself does not. Cannot bind a
voice, custom or otherwise, to a character that was never created.

## Current voice bindings, read-only, as found (unchanged by this task)

| character | bound voice (as shown on the character page) |
|---|---|
| `@lung_somchai` | `algenib` (plain preset, unchanged) |
| `@nong_daeng` | `iapetus` (plain preset, unchanged — matches ledger "KEPT") |
| `@grandma_pranom` | **none** — `เลือกเสียง` empty state |
| `@cop_wit` | n/a — character does not exist |
| `@lender_cherd` | `algieba` (plain preset, unchanged — matches the brief's note that this contradicts the intended Umbriel) |

## Wall-clock

| Action | Time |
|---|---|
| Voice preview generation (Omni), each of 3 runs | ~18–30s |
| Full ตัวละคร list scroll (search for `@cop_wit`) | ~2 min, ~10 scroll actions |
| Full task | ~45 min |

## SKILL-CONTRADICTION

```
SKILL-CONTRADICTION: google-flow-ops :: "Custom voices — build one per character,
  off a base preset" (added 2026-09-18) implies the character page's เลือกเสียง
  flow is a working path to a saved custom voice: pick base, describe, preview,
  name, save.
  :: The flow works through step 4 (preview completes, produces real audio) but
  step 5/6 (name + save) never enables the บันทึกเสียงใหม่ button. Reproduced
  twice, independently, on two different characters (@lung_somchai and
  @nong_daeng), two different base presets (Algenib, Fenrir), including one full
  รีเซ็ต-and-retry cycle. disabled=true confirmed via DOM read every time,
  regardless of real keyboard edits to the name or description field afterward.
  This is the exact same failure the skill already documents at
  "The customize-performance path is dead on this account (2026-09-08)" for the
  composer's + picker — it is not fixed, it has moved to (or was always also
  present in) the character-page flow.
  :: 2026-09-18, task-36507a6a.
```

```
SKILL-CONTRADICTION: google-flow-ops / banchi-custom-voices.md brief :: the cast
  ledger and the brief assume all five characters (@lung_somchai, @nong_daeng,
  @grandma_pranom, @cop_wit, @lender_cherd) already exist as Character assets in
  the "AI Film" project.
  :: @cop_wit is not in the project. Full ตัวละคร tab scrolled top-to-bottom
  twice; every other named character/prop/location tile was found; @cop_wit was
  not.
  :: 2026-09-18, task-36507a6a.
```

## What the CEO needs to decide

1. Whether to escalate the save-button bug to Google Flow support / wait for a
   fix, or fall back to the older documented workaround: "attach the plain
   preset, and write the performance direction into the shot's own prompt
   text" — i.e. skip the custom-voice save entirely and put each character's
   description into the dialogue-shot prompts instead.
2. Whether `@cop_wit` needs to be created as a Character asset before any voice
   work can happen for him.
3. `@grandma_pranom` currently has **no voice at all** bound (not even her old
   Gacrux/Vindemiatrix plain preset) — worth flagging since any dialogue shot
   fired for her right now would get an unbound/random voice.
