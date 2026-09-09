Plaque Element `@project_absence_prop_tag_100m` is flagged "protected content" and Generate refuses the click — the CEO's mandated fix (bind the Element) cannot fire; the AB-LEDGER's only known workaround (drop to prose) would reproduce the exact garbled-plaque defect this task exists to fix.

## What happened

Step 0 (create the $100,000,000 plaque Element) succeeded cleanly: uploaded
`docs/plates/project_absence_prop_tag_100m.png`, created the Element via the
project's Elements page "Add new" dialog (Category Prop, Name/Element ID
`project_absence_prop_tag_100m`), and verified it resolves as a lime mention
chip with the correct thumbnail — 1/1 bound, exact selector match.

Step 1 (S15e-AB t2) was fully staged — 6/6 chips bound exactly matching the
sheet's lint output, 20s/720p/16:9/Sound On/High/Unlimited all verified,
Generate button zoomed and confirmed `UNLIMITED / struck ~140 / 0` — and
fired once. It did not fire: a toast read "Some reference elements may
contain protected content. Check eligibility or remove them to proceed." No
credit spent, no card created, no slot taken (confirmed clean).

Clicking the toast's own "Check eligibility" link (read-only) was followed
immediately by the viewport collapsing to 337x73 — the task's documented
lock-up trigger. Recovered via the mandated path (fresh tab, never resize;
tab registry updated). In the fresh tab, the flag on
`@project_absence_prop_tag_100m` was still present after 8s (not a
transient "Checking.." state). The **pre-existing** `@project_absence_prop_tag`
($2,000,000 version, already used in passing takes per the AB-LEDGER) showed
the identical toast when tested — so this is not specific to the newly
created Element.

## Why I stopped instead of working around it

The AB-LEDGER's only documented fix for a flagged-Element refusal (SC2, S2R)
is to remove the Element and carry the object as prose instead. But the
entire point of this task, per the CEO's 2026-09-10 02:40 instruction quoted
in every sheet's NOTES, is that prose-only plaques render garbled text —
that's the defect being fixed. Falling back to prose would silently
reproduce it across all four scenes in this chain (S15e-AB, S14, S15b,
S15c all bind this same Element). Substituting the fix for the very defect
it's meant to prevent is a scope call for the CEO/CTO, not something an
operator should decide alone.

## What I need

A decision on how to proceed: accept the prose fallback despite the known
risk, try re-creating the Element differently to see if that clears the
flag, or something else. Full evidence (screenshots, selector output, exact
sequence) is in `docs/reports/absence-plaque-chain-winbox.md`.

## State left behind

No composer left open — the fresh tab was closed after the isolated-chip
retest. Nothing staged live; the exact 6-chip/20s/Unlimited-ON composer
state needed for S15e-AB t2 is fully documented in the report so it can be
rebuilt without re-deriving anything once this is resolved. Steps 1-4 (and
the conditional Step 5) never fired. Step 0's Element exists and is usable
the moment this blocker clears.
