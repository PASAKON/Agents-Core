# Absence wave 2026-09-05 — S2C harvest + S2K fire

## Pre-flight: worktree was 207 commits behind main

Before touching Higgsfield, `git log HEAD..main --oneline` showed this
worktree's branch was **207 commits behind `origin/main`** — created from a
stale base. `docs/prompts/absence/s2k-fix1-the-crowd-gathers.txt`,
`docs/PREVIZ-ELEMENTS.md`, `docs/reports/valder-draft2-continuity.md`, and
`docs/S2K-Render.MP4` all named in the task brief did not exist anywhere in
this branch's history. `CRACK-CANON.md` never existed as a standalone file —
it's referenced only as a concept inside `valder-draft2-continuity.md`.

Ran `git fetch origin main && git merge main --no-edit` — clean merge, no
conflicts, all four named files landed. Verified by path before proceeding.
Flagging this for the reviewer since it's a recurring class of bug
(`feedback_create_task_worktree_stale_base` / `create_task_after_dependency_merge`
in org memory) and 207 commits is an unusually large gap.

## Step 1 — S2C-Fix1-take4

**Finished clean. Downloaded and filed.**

Per `docs/reports/absence-harvest-20260905.md`, S2C-Fix1-take4 was fired
2026-09-05 ~09:02 UTC using `docs/prompts/absence/s2c-fix1-pacing.txt`, and was
reported still-generating at report time (~12:01 UTC, ~180 min elapsed) — the
same state this task's brief described.

Opening a **fresh** Chrome tab (not the stale one the prior session had been
polling — see the "long-lived tab lies about the concurrency slot" note in
`higgsfield-unlimited-gen`) and searching `All assets` filtered to
Video + Today found the clip already complete:

- Prompt matched `s2c-fix1-pacing.txt` exactly (`@loc_hall_big_e`,
  `@project_absence_char_cleaner_c`, `@project_absence_prop_cart_a_painted`;
  paste-block text "20s · 720p · 16:9 · ONE LOCKED SHOT..." verbatim).
- Details panel: Model Seedance 2.5, Quality 720p, Bitrate High, Size
  1280x720, **Created September 5, 2026 at 4:10 PM** (ICT) = **09:10 UTC** —
  ~8 minutes after the 09:02 UTC fire.
- No "Rights verification required" banner on the card — checked the Info tab
  and the player directly; card is a normal finished asset with working
  Recreate/Reference/Download controls, not a rejection.
- Take 1-3 never fired (blocked pre-generation per the prior report), so this
  is unambiguously take 4 — the only S2C-Fix1 asset that exists.

**My read: the prior session's "still generating at 180 min" was reading a
stale tab, not the real state.** The clip actually finished in ~8 minutes,
consistent with this project's normal render times, and had been sitting done
for hours by the time this task started. This matches a documented failure
mode in `higgsfield-unlimited-gen` ("A long-lived tab lies about the
concurrency slot") — the prior session had one tab open across a 3+ hour poll
window.

Downloaded: `hf_20260905_091020_80bbfe6e-7c91-47b3-b0a3-d90226054b24.mp4`
(20,518,526 bytes; filename timestamp `091020` matches the Created time
exactly). Filed to Drive `All Scene/Fix-1/` via
`scripts/gdrive-bridge/upload_fix1.py` as **`S2C-Fix1-take4.MP4`**
(19.6 MB uploaded): https://drive.google.com/file/d/1lNnaOeYF1iz6jk_lQGtsVrcR61Z55pa6/view
— logged to the project `logs.txt` by the same script call.

Because it had already finished, **the Unlimited slot was free** — step 2 was
not blocked.

## Step 2 — S2K-Fix1

**Fired. Still generating at report time — outcome not yet known.**

Sheet: `docs/prompts/absence/s2k-fix1-the-crowd-gathers.txt`, fired exactly as
written (paste block extracted programmatically between its own markers,
byte-verified length 10047, pasted via synthetic `ClipboardEvent` — no
`type()` used anywhere).

**Six-field readback, verified twice** (once after building, once fresh
immediately before the click, both via full-text DOM scrape plus a pixel zoom
of the actual button — not the decoy Cinema Studio 4.0 button that also
matched a loose selector):

| Field | Value |
|---|---|
| Duration | **12s** (set via the ARIA slider: focused the thumb, `ArrowLeft` x8 from the leftover 20s, verified `aria-valuenow="12"`) |
| Resolution | 720p |
| Model | Seedance 2.5 |
| Quality | High |
| Aspect / quantity | 16:9 · 1/4 |
| Sound | On |

**Price at click**: zoomed pixel screenshot of the real Generate button read
`UNLIMITED · ~~84~~ · 0` — struck-through, zero live cost. (Note: the
composer's Unlimited toggle had reset to OFF on page navigation, as this
project's skill documents; re-enabled it once, `data-state` flipped to `on`
on the first click, re-verified before firing.)

**Previz**: `docs/S2K-Render.MP4` (2,793 KB) uploaded as the video reference.
Verification took under ~20 seconds (toast → "Checking.." → real thumbnail
showing the position-map previz with DUPE/COLLECTOR_A/STUDENT labels visible)
— well inside the 10-20 minute outage-ladder window, so the outage ladder was
not needed; the clip fired **with** the previz attached. One care point: the
composer had a leftover reference from an earlier accidental "Copy" click on
the S2C card (which had pre-filled the composer with S2C's own prompt+ref) —
cleared the text with Cmd+A/Delete and explicitly deselected that stray
reference in the upload picker before attaching S2K's own previz, so only the
correct file rode as `@Video 1`.

**Chip count: 8/8 bound, 0 error chips.** Ran the mandated selector:

```js
[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')]
  .filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@')).length
```
→ returned **14**, not 8. This is not a selector failure — the sheet mentions
six of the eight Elements twice each (once in the POSITION MAP block, once in
REFERENCES) and two once each (the location and the prop, which aren't in the
position map), so 6×2 + 1 + 1 = 14 individual bound chip spans covering
exactly the 8 unique handles `prompt-lint.py --chips` expects. Breakdown
confirmed programmatically — all 8 unique `@project_absence_*` handles
present, each with the expected occurrence count, zero unbound/red text, zero
`.text-icon-error` spans. `python3 scripts/prompt-lint.py
docs/prompts/absence/s2k-fix1-the-crowd-gathers.txt` also ran clean (exit 0).

**Fire time: 2026-09-05T13:27:38Z** (~20:27:38 ICT). Confirmed fired: `All
assets` count incremented 654→655 and a new processing card appeared at the
top of the grid immediately after the click; no error/rejection text
appeared anywhere on the page afterward.

**Info-icon check / REVIEW ORDER verdict: not yet possible.** The clip was
still generating (processing card, no thumbnail yet) when this task's step
budget and scope ("STOP AFTER THESE TWO") were reached. I did not wait on it
— per the task's own instruction and this project's "never let a worker sit
and watch a render" rule, checking a finished clip is a separate, cheap
action for a later pass. **This is the one open item**: whoever checks next
should open the card's info icon (copyright-rejection check), verify it
against the sheet's own REVIEW ORDER (couple = two women / man in maroon
alone / crying is small / no dialogue / break is the aperture only / camera
dead still / six people no extras), and file it to Drive `All Scene/Fix-1/`
as `S2K-Fix1.MP4` **whatever the verdict is**, per the sheet's own filing line
and this task's "file every clip including failures" rule.

## Filing

- `S2C-Fix1-take4.MP4` — filed, Drive link above. Done.
- `S2K-Fix1.MP4` — **not yet filed.** Clip was still rendering at report time.
  Nothing to download yet; no placeholder was created.

## Two lanes

Scanned the grid for `SEEDANCE 2.5 CREDIT`-prefixed cards while browsing —
saw none active in the visible range during this session's work. Did not
touch, download, or file anything outside the two cards named above.

## Unresolved, stated plainly

**S2K-Fix1's render outcome is unknown as of this report.** It was correctly
fired (all pre-flight checks passed, price confirmed zero, chips confirmed
8/8) but has not finished. The next operator or check-in should: open the
project, find the newest processing/finished card, run the info-icon
copyright check, compare against the REVIEW ORDER, download, and file to
`All Scene/Fix-1/S2K-Fix1.MP4` regardless of verdict. Per this task's "STOP
AFTER THESE TWO" instruction, I did not start S2L, S2P, or anything else.

## Replay / tooling notes

- `scripts/gdrive-bridge/upload_fix1.py <local> <name> [note]` — used as-is,
  no changes needed, still the right tool for filing a Fix-1 clip.
- `scripts/browser/tab_registry.py` — claimed tab on open, released and
  closed on completion; no orphaned tabs left behind.
- No new replay script written. This wave was two one-off, judgment-heavy
  actions (recognize which finished card is S2C among many similar-looking
  gallery clips; build the S2K composer state field-by-field) that don't
  reduce to a fixed script without losing the judgment calls (matching the
  card by its unique prompt/reference set, deciding the stray reference had
  to be removed). The mechanical pieces (base64-safe paste, ARIA-slider
  duration set, six-field readback scrape) are documented step-by-step above
  for whoever picks this up next.

## SKILL-OVERRIDE

None. Followed `browser-operator`, `higgsfield-unlimited-gen`, and
`ai-film-production` as written; the outage ladder wasn't invoked because the
previz verified well inside its window.
