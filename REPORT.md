## Summary

Read-only recon of Google Flow's Voices feature on the CEO's account, per
task-e3bf2fa9. Zero credits spent (50 → 50, verified both ends). Answered all
8 required items in `docs/reports/flow-voices-recon-20260908.md`:

1. Credit balance: **50 at start, 50 at end** — unchanged.
2. **Yes**, a `เสียง` (Voices) entry exists under the Add (+) ingredients
   picker, as a first-class category alongside Characters/Images/Video.
3. **Full preset list captured: 30 voices**, verbatim name + gender/tone/pitch
   label each (Achernar → Zubenelgenubi). No sound was played; all text-only.
4. Custom-voice flow **exists**: pick a preset → a 120-char sample-dialogue
   box + a "Customize performance" description field (no char limit found) +
   "Add to prompt". **No separate "name" field was found** — a discrepancy
   worth flagging against the docs. Nothing was created/saved.
5. Model is called **"Omni 1.1 Flash"** in this UI (not "Gemini Omni Flash
   1.1"), is the account default. Live costs read (never submitted):
   720p/8s=12, 720p/10s=15, 360p/8s=6, 360p/10s=7 credits — 360p is ~half
   cost, confirming the docs' claim. It's cheaper than Veo 3.1 Fast (20@8s).
6. Ingredient chips and the เฟรม/องค์ประกอบ toggle are **unchanged** with
   Omni Flash selected — nothing disappears.
7. **No plan-tier gating text found** anywhere near Voices/Omni Flash; only
   the generic low-credit-pool upgrade banner (unrelated to this feature).
8. **2 of the allowed 3 screenshots taken**: (1) voice list + custom-voice
   panel together, (2) model picker with all 4 models + live 12-credit
   estimate.

A significant technical issue shaped this run: the winbox Chrome tab reported
`document.hidden === true` for the entire session (on two different tabs),
which intermittently broke `screenshot`/`zoom` (CDP timeouts) and completely
broke the Voices list's Angular virtual-scroll rendering (scrollTop changes
and `scrollIntoView` produced no DOM update). Worked around this by using the
picker's own search box, which does a full-dataset substring match and
re-renders correctly regardless — that's how all 30 names were recovered.
Full writeup and a `SKILL-CONTRADICTION` note are in the report file.

## Files Changed

- `docs/reports/flow-voices-recon-20260908.md` (new — the deliverable)
- `REPORT.md` (new, this file)

No application code touched. No composer/project state left changed: a test
voice chip (Achernar) was attached during verification and explicitly
removed before finishing; a pre-existing `@nong_daeng` chip was left as
found.

## Commits

See `git log` on this branch — one commit adding the report + this file.

## Tests

N/A — read-only recon task, no code changed.

## Issues / Blockers

None that block the task — all 8 required items were answered. One
non-blocking finding worth the CTO's attention (also filed as a
SKILL-CONTRADICTION in the report):

- **winbox tab was `document.hidden` for the whole session**, on a freshly
  opened tab, with normal `innerWidth`/`innerHeight` and while being the
  correct `selectedTabId`. This is a different failure mode than the
  skill's existing "tab collapses to 98x74" note. It made screenshots flaky
  (worked ~1/3 to 1/2 tries) and completely broke `cdk-virtual-scroll-viewport`
  re-rendering (any long virtualized list, not just Voices, would hit this).
  Recommend the skill note the search-box-substring-match workaround for
  future long-list reads on this host.

## Notes for Reviewer

- The model's literal UI name is "Omni 1.1 Flash", not "Gemini Omni Flash
  1.1" as the task/docs phrase it — same feature, different exact string.
  Flagged in the report rather than silently normalized.
- The docs say custom voices are "named" — no name field was found in the
  panel that opens after picking a base preset. Possible the name step comes
  later (e.g. renaming the resulting chip), but that wasn't reached since
  creating a custom voice was out of scope.
- One voice, "Pulcherrima", is explicitly labelled "Ungendered" rather than
  Male/Female — copied verbatim from the UI, not a paraphrase.
