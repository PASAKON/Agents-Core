# Absence — S15a-2 "THE ROOM DECIDES" Fix-1, t1 — GATE FAILED, STOPPED BEFORE FIRE

2026-09-08 · task-c6d20a5e · sheet: `docs/prompts/absence/s15a2-fix1-the-room-decides.txt`

## Outcome: STOP — did not open a browser tab, did not fire

Per FIRE-PLAYBOOK.md §0: "Mismatch → STOP and report; never fire from a stale
sheet." One of the four literal gate checks named in the task brief did not
match.

## Gate results (paste block only, `PASTE FROM HERE` → `PASTE STOPS HERE`)

| Gate | Expected | Actual | Result |
|---|---|---|---|
| `prompt-lint.py` exit code | 0 | 0 | PASS |
| Unique `@` names | 12 | 12 | PASS |
| `HARD CUT` count | 2 | 2 | PASS |
| depth/gaze pattern `nearest\|extreme foreground\|very front\|floating\|toward the mark\|backs to the room` | 0 | **1** | **FAIL** |

`prompt-lint.py --chips` confirms the same 12 names, all with an Element
reference in the sheet.

### The one mismatch

Line (paste block, guard-grouping sentence):

> "THE THREE BODYGUARDS STAND TOGETHER, shoulder to shoulder in one small
> group at the frame edge **nearest** their masters — Valder's two navy
> guards and Carrington's man in black side by side..."

This reads as a positional description ("the guard group is at the frame
edge closest to Valder/Carrington"), not a camera depth-cheat instruction —
it is not describing anything nearest-to-camera, foreground-compressed, or
floating. It may well be a false positive against the banned-pattern list.

I did not adjudicate that myself. The task names this as a hard gate with an
expected value of 0, and the playbook's own instruction for a gate mismatch
is to stop and report rather than fire from a sheet that doesn't clear the
checks as written — the same rule exists precisely because a prior take
(S15a-1, this same scene's first half) was already FLAGGED for a
choreography/framing issue, so a second unresolved framing-adjacent flag on
the continuation half warranted a human call, not an operator override,
especially with tonight's credit-lane balance already under investigation.

## Everything else, not attempted

Per the STOP, none of the following were performed: tab claim, banner
dismissal, six-field setup, paste/chip binding, previz, balance read, fire,
polling, download, md5, Drive filing, frame checks. No browser tool was
called this task.

## Recommendation for CTO / sheet owner

Either:
1. Confirm the "nearest their masters" phrasing is an acceptable use (it
   does not touch camera framing) and re-approve the sheet as-is so the next
   operator can fire without re-litigating this, or
2. Reword to something like "at the frame edge closest to their masters" or
   drop "nearest" entirely, if the gate is meant to catch this literally
   regardless of context.

## Notes

- `git merge main`: branch was already up to date with main (HEAD includes
  34e2142 per task's own >= floor). No merge needed.
- CTO sent a mid-turn message during this task; its body never rendered in
  this session's context (system reminder announced it but carried no
  content). Flagging in case something was missed.

## SKILL-OVERRIDE

None. Followed FIRE-PLAYBOOK.md §0 gate-mismatch rule as written.
