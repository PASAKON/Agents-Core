# Tab-registry first use + S2N upload probe + S2M-Fix1-take2 check — 2026-09-04 (task-ed7051e8)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`
("The Valder Collection No.7") — confirmed via address bar/page title before
touching anything.

`git merge main` was a no-op against `origin/main` (behind, unpushed, same
pattern every recent operator on this repo has hit). The actual
`tab_registry.py`/`tab_guard.py` machinery and this wave's docs landed via
`git merge main` against the **local** `main` branch (fast-forward
123bcca..f962f13, 165 files).

## JOB 1 — claim tab

Opened exactly one tab, navigated it to the project URL, then:

```
python3 scripts/browser/tab_registry.py claim task-ed7051e8 53471827 "https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3"
→ claimed tab 53471827 for task-ed7051e8 (1 held)
```

## JOB 2 — orphan cleanup

`tabs_context_mcp` (twice, once fresh, once after a full page reload) showed
**only 1 tab total** — the one I had just opened and claimed. No pile of ~25
Higgsfield tabs was visible to this session.

`tab_registry.py list` confirms the registry itself has never held any other
claim — mine is the only entry that has ever existed in
`state/browser-tabs/`. So there is nothing to cross-reference against a prior
pile either; if the ~25 tabs the CEO saw still exist, they are not visible
from this session's MCP tab group.

Ran the orphan check anyway, on the one tab that exists, per instructions:

```
python3 scripts/browser/tab_registry.py orphans 53471827
→ SAFE TO CLOSE (1): 53471827
```

**Counts: 1 tab existed (mine) → 0 pre-existing orphans found → 0 tabs
closed → 1 tab remains (kept, on purpose — see Job 2 note below and the
instruction-conflict note under Issues).**

**Caveat on "no orphans found," honestly stated**: `tabs_context_mcp` only
enumerates tabs in *this session's own* MCP tab group. If the CEO's ~25-tab
pile lives in a Chrome window/tab-group this session was never handed, I
cannot see it from here and cannot certify it doesn't exist — I can only
certify that within the tab group I was given, there was nothing to clean
up. Worth a follow-up: have the CEO screenshot `chrome://` or a fresh
operator session confirm whether that pile is still physically open.

## Registry bug found — `_task_alive()` cannot find the tasks DB from a worktree

`tab_registry.py` resolves `ROOT` as `Path(__file__).resolve().parents[2]`,
which from any worker's checkout is the **worktree root**, not the main
repo. So `DB = ROOT / "state" / "tasks.db"` looks for
`<worktree>/state/tasks.db`, which does not exist — every worktree is its
own checkout without the shared task DB. The real one lives at
`/Users/gob/Projects/Agents/state/tasks.db`.

Confirmed live:

```
python3 scripts/browser/tab_registry.py list
→ STALE task-ed7051e8  1 tab(s)  [no tasks db]
      53471827  2026-09-04T09:56:58Z  https://...
```

That's `list` and `orphans` both reporting **my own live, actively-claimed
tab as stale/safe-to-close** — while this very session is running and the
tab is mine. Since every `browser_operator`/worker task runs from a
worktree, not the main checkout, `_task_alive()` can **never** successfully
find the DB in normal operation — it will always say "no tasks db" and
therefore always report every claim as not-alive. That defeats the entire
purpose of the registry: the one case it exists to prevent (closing a tab
another LIVE task still owns) currently can never be detected. I did not
patch this — flagging it here as requested since you wrote the registry
today.

**Suggested fix**: resolve the tasks DB path from a fixed location that
doesn't depend on `__file__`'s checkout (e.g. an env var the harness already
sets for every worker, or hardcode `/Users/gob/Projects/Agents/state/tasks.db`
if this tooling is Mac-only by design).

## JOB 3 — one upload probe

Uploaded `docs/S2N-Render.MP4` (4,255,680 bytes) once, via the project's
Seedance video composer → References → Uploads → the `video/mp4`-accepting
file input (there are 3 file inputs on this page; picked by `accept`
attribute per the higgsfield skill).

| Event | Time (UTC) | Elapsed |
|---|---|---|
| Upload fired | 09:58:50 | — |
| Toast: "Your upload is being verified. You can select it once verification completes." | 09:58:50–~10:02 | — |
| Found the tile still showing a **"Check eligibility"** pill (not yet attachable) | ~10:02 | ~3–4 min |
| Clicked "Check eligibility" → tile went to a **"Checking.."** spinner | ~10:03 | ~4–5 min |
| Re-checked: spinner gone, tile now a normal selectable asset | 10:05:28 | ~6.6 min |
| Clicked it → toast **"Added to prompt box"**, References counter went 0/50 → 1/50 | 10:05:28+ | ~6.6 min |

**Result: VERIFIED. The upload pipeline has recovered.** Total time from
upload to a usable, attachable asset: **~6.5 minutes**, well inside the
10-minute budget. This is the two-click "Check eligibility → attach" flow
the higgsfield-unlimited-gen skill documents for this composer surface.

Per the job's own instruction, stopped here — **did not fire a generation.**
Deselected the reference immediately after confirming it (References back
to 0/50) so the composer is left clean, in case anyone opens this tab next
expecting an empty prompt box.

One process note: right after upload, while hunting for the correct tile in
the Videos-filtered panel, I mis-clicked an unrelated *existing* video
("OLDMAN") and it got added as a reference (1/50). Caught it immediately via
the References counter, deselected it (clicked its checkbox, never the
trash icon next to it — did not risk deleting an existing project asset),
back to 0/50 before touching anything else. No harm done, but worth naming:
identifying "the tile I just uploaded" among many similar-looking video
thumbnails, sorted by "Last created," is genuinely error-prone by eye. What
actually worked reliably was a DOM search for the live `"Check eligibility"`
text and reading its ancestor's `aria-label` (a uuid) — that's how I found
and confirmed the right tile before clicking it for real.

## JOB 4 — S2M-Fix1-take2 status

Per the prior wave's own report
(`docs/reports/absence-s2m-retake-s2n-wave-20260904.md`), S2M-Fix1-take2 was
**fired 2026-09-04 14:47:42 ICT** (07:47:42 UTC) and was already at 96+
minutes when that report was written.

Found its card: **top-left position in the project's main asset grid** —
the only card showing a processing state (spinner icon top-left). Confirmed
this is a real in-progress generation, not a stale-tab illusion, by doing a
**full page reload** and re-checking: same spinner, same state, before and
after reload.

**No info icon is present on this card.** I looked specifically because the
task warned a copyright rejection can be invisible and the card can *look*
complete — but this card does not look complete. It shows only two icons: a
loading spinner (top-left) and, confirmed via a hover-tooltip DOM read
(`"Cancel"` / `"Cancel"`), a **Cancel button** (top-right, the circle-slash
icon). Higgsfield does not appear to expose an info/details icon on a card
that is still actively processing — that control only shows up (per the
skill notes and my own observation on completed cards elsewhere in the same
grid) once a generation finishes, succeeds, fails, or gets flagged. I did
**not** click the Cancel button — per the task's explicit instruction and
the skill's standing rule, that decision is the CEO's/CTO's, not mine.

**Current state, as of this report (10:09:43 UTC / 17:09:43 ICT):**
- Still showing the processing spinner, no thumbnail, no info icon, no
  completion metadata.
- Elapsed since Generate click: **~142 minutes** (2h 22m), up from the ~96
  minutes the prior report recorded — confirms this is not a display
  artifact, it is genuinely still rendering (or hung) server-side.
- A Cancel affordance exists on the card but was left untouched, as
  instructed.
- Nothing to download, file to Drive, or score against the review order
  (`docs/prompts/absence/s2m-fix1-registrar-welcome.txt`) yet — the clip has
  not completed. No verdict is possible on it today.

This is the second consecutive report to find S2M-Fix1-take2 in exactly this
state; it has now been rendering for well over two hours. That is a
CTO/CEO call (cancel-and-retry vs. keep waiting), not an operator one — I am
only reporting the current state, as instructed.

## Tab left open, registry claim NOT released — instruction conflict, resolved in favor of the more specific rule

The task brief has two conflicting instructions:

1. Job 2: **"KEEP ONE TAB on [this URL] — the one you claimed... I want to
   be able to watch its card."**
2. "BEFORE YOU REPORT": **"Close the tab you opened, then... `tab_registry.py
   done <task-id>`."**

I followed (1) and did **not** follow (2) as written: the tab (53471827) is
still open on the project page, and the registry claim under
`task-ed7051e8` is still held (I did not run `done`).

**Why**: (1) is the specific, reasoned instruction — it names exactly why
(a live server-side render, CEO wants eyes on the card) and explicitly notes
closing tabs wouldn't even cancel the render, so there's no safety reason to
close it. (2) reads as the generic template close-out step, written before
the KEEP-one-tab carve-out, and following it literally would undo (1).
Releasing the registry claim would be actively harmful given the DB bug
above: with `_task_alive()` unable to ever confirm a live owner, an
unclaimed tab is indistinguishable from a truly-orphaned one to the next
operator who runs `orphans` — releasing the claim on a tab someone
explicitly asked to keep open would make it a target for exactly the
cleanup this task just ran. So the tab stays open and stays claimed under
`task-ed7051e8` until the CEO/CTO says otherwise or this task is formally
closed out another way.

Flagging this plainly rather than picking silently, per the report
requirement to note conflicting instructions.

## Registry usability notes (asked for explicitly)

- **`claim`/`orphans`/`list` all read cleanly and did what the docstring
  says** — good ergonomics, clear exit codes, clear printed guidance
  (`owner` even prints the exact `tmux send-keys` command to use). No
  complaints about the CLI surface itself.
- **The one real defect is the DB path bug above** — worth fixing before
  this tool is trusted at scale, since right now it silently can't do the
  one dangerous check it exists for (detecting a genuinely live owner).
- Everything else about the flow (claim on open, orphans before closing,
  done on release) is straightforward once the DB bug is fixed.
