# Collector A's gold V is in the PLATE, not the prompt — decision needed

**CTO, 2026-08-30 ~19:45, night shift.** Confirmed, not suspected.

## What happened
S5 take1 was flagged for a gold "V" on Collector A's cobalt coat. The prompt was
then hardened to the maximum — "her cobalt coat is PLAIN — no insignia of any
kind", "no gold V or monogram or emblem on any visitor's clothing", "no gold V on
any visitor (the registrar's V is correct)", plus an explicit warning naming the
take1 miss. **S5 take2 rendered the V again**, in the same place, from ~8s to the
end. I pulled take2 from Drive and read the frames myself.

The operator then opened the Element at full resolution and confirmed:
**a gold "V" pin is baked into the `@project_absence_char_woman` plate itself.**

## Why more prompt wording cannot fix it
A negative steers generation; a bound Element supplies pixels. There is nothing
left to add — the prompt already bans it three ways plus a warning.

## Blast radius
`@project_absence_char_woman` is bound in **10 places across 4 prompt files** —
`s-arrivals.txt`, `s4-s5.txt`, `s7-s9.txt` (S8a/S8b/S8c/S9), `s6-s18.txt`.
**Nearly all of those scenes are already shot and filed as keepers**, so the V is
already in the can, repeatedly and consistently.

## The decision — CEO's, not the CTO's or the operator's

| | Cost | Consequence |
|---|---|---|
| **A · Regenerate the plate without the V** | plate credits | Future scenes clean, but she no longer matches the ~8 keepers already delivered — a continuity break inside one film |
| **B · Declare the V canon and stop fighting it** | zero | Nothing to redo. Requires relaxing "no gold V on any visitor" for her specifically, so the prompts stop banning something the plate guarantees. A collectors' pin is a defensible reading in this world |
| **C · Regenerate the plate AND reshoot her scenes** | plate + ~8 renders | Fully clean and consistent; the most expensive path by far |

**The facts lean toward B** — the V is already consistent across the delivered
footage, and B is the only option that costs nothing and breaks nothing. But this
is a look decision about the CEO's own film, so it waits for him.

## What was NOT done, deliberately
- **S5 was not re-fired.** CEO standing rule: a take that missed is filed, not
  reshot; breadth beats polish.
- **The plate was not regenerated.** That spends credits and is the CEO's call.
- **`s4-s5.txt` was not edited.** A one-line ⛔ note belongs at the
  `@project_absence_char_woman` reference telling the next person to stop
  hardening the prompt — but the operator is mid-wave reading that exact file,
  so the edit waits for the CEO's OK rather than changing live production text
  under a running agent at night.
