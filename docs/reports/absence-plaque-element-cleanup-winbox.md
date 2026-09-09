# Plaque cleanup — remove non-compliant `project_absence_prop_tag_100m` — winbox browser operator (task-2bbdd10b)

Cleanup of a non-compliant Element the CTO created by mistake (externally
edited image, forbidden by Rule 00 of `higgsfield-unlimited-gen`). Per
`docs/reports/absence-plaque-chain-winbox.md` (spawn 1 / task-54e019e3), the
Element was created and never used in any generated asset before its
reference chip was found to carry a "protected content" flag that refused
Generate — that finding is unrelated to this cleanup task, which is delete +
verify only.

## Browser setup

- Device: winbox-chrome (`815ddf16-36ea-4e0d-827a-f51e9ff85351`), selected via
  `select_browser`.
- Tab `1638444840` opened and claimed in `scripts/browser/tab_registry.py`
  under `task-2bbdd10b`. A second tab (`1638444841`) was opened partway
  through, for a genuinely fresh-tab verification (see "Odd finding" below);
  both were claimed.
- Window verified at 1920x855 desktop width on first navigation.
- Chain 2 (task-c72d5ba5)'s tab and jobs were never touched — never
  navigated, never clicked. Its job(s) were visible as "Processing" /
  "Generating" cards in the shared project grid throughout (normal, expected,
  not mine).
- **Never clicked Generate, never touched Unlimited/any paid control.**

## Step 1 — Delete the Element `project_absence_prop_tag_100m` — DONE

1. Opened `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3?elements=1`
   → Props tab. Confirmed via `javascript_tool` DOM scan that exactly two
   elements match `project_absence_prop_tag*` on this page: `project_absence_prop_tag_100m`
   (target) and `project_absence_prop_tag` (the CEO's original $2,000,000
   plaque — do not touch).
2. Clicked the `project_absence_prop_tag_100m` tile → detail panel opened,
   confirmed **Element ID `@project_absence_prop_tag_100m`, Category Prop,
   Name `project_absence_prop_tag_100m`, Created 44 minutes ago, Used in "The
   Valder ..."** — matches spawn 1's report exactly.
3. Clicked `···` (More) → **Delete**. Confirmation dialog read exactly
   **`Delete "project_absence_prop_tag_100m" from project?`** (verified the
   full un-truncated text via DOM query before clicking, since the visible
   text was truncated to `"project_ab..."`). Clicked **Delete** once.
   Toast: **"Element deleted."**

## Step 2 — Delete the source upload — DONE

1. Opened the composer's reference panel (`+` → Uploads → Images sub-tab),
   sorted **Last created** (not "Last used" — the skill's known trap:
   "Last used" sorts a previously-clicked asset to the front regardless of
   upload time). The most recently created image was the plaque: thumbnail
   read "THE ABSENCE OF MEANING / Valder / $100,000,000".
2. **First click on the tile added it to the prompt box as a reference chip**
   (this UI's single-click behavior on an Uploads tile, same trap spawn 1's
   report documented for the detail-modal path). Immediately removed the
   chip via its own `×` before doing anything else — composer verified empty
   before continuing. `SKILL-OVERRIDE` note below.
3. Located the tile's own hover-revealed trash-can icon (a small circular
   button distinct from the tile's own click-to-preview behavior; identified
   its exact DOM position via `javascript_tool` rather than guessing pixel
   coordinates a second time, since a mis-click had already fired the
   lightbox preview once). Clicked it.
4. Confirmation dialog: **"Delete upload? — This upload will be permanently
   deleted."** (generic wording, no filename echoed). Cross-checked the tile
   still visible behind the dialog was the plaque before confirming. Clicked
   **Delete**. Toast: **"Upload deleted."**

`SKILL-OVERRIDE: higgsfield-unlimited-gen :: implicit assumption that a
reference-panel tile only exposes preview/delete controls :: a plain single
click on an Uploads-tab image tile ADDS it as a composer reference chip (not
just preview) :: found this the hard way, removed the chip immediately via
its own × before it could be part of anything, never came close to Generate.
Recorded here so the next operator budgets for it: hover for the trash icon,
don't click the tile body.`

## Step 3 — Verify

1. **Elements page, full reload**: `project_absence_prop_tag_100m` absent
   from Props grid and from a full-page-text scan
   (`document.body.innerText.includes(...)` → `false`). The original
   `project_absence_prop_tag` ($2,000,000) confirmed still present and
   untouched, both visually (screenshot) and via DOM scan.
2. **Uploads → Images grid, full reload**: sorted Last created; the plaque
   thumbnail no longer appears — the most-recent slot is now occupied by the
   next-most-recent upload (a portrait shot), one position earlier than
   before.
3. **Composer mention test — odd finding, resolved**: in the *same* tab used
   for steps 1–2 (which had only been soft-navigated, not hard-reloaded,
   between the delete and this test), typing `@project_absence_prop_tag_100m`
   **did** surface an autocomplete suggestion and **did** form a lime mention
   chip — with a warning-triangle badge on the reference thumbnail, tooltip
   **"This asset needs an eligibility check before it can be used."**
   (`data-beautiful-mention="@27b311ba-568c-47a3..."`, a stale UUID). This
   looked like the deletion might not have taken full effect, so before
   reporting anything I opened a **second, genuinely fresh tab**
   (`1638444841`, full navigation, never previously touched this project) and
   repeated the exact same test: typing `@project_absence_prop_tag_100m`
   there produced **no autocomplete dropdown and no chip at all** — plain
   text only. **Conclusion: the deletion is effective server-side; the first
   tab's chip was a stale client-side mention-cache artifact left over from
   before the delete, not evidence of an incomplete deletion.** Composer
   cleared (Ctrl+A, Delete) in both tabs with nothing ever fired — no
   Generate click, no reference left bound.
4. Screenshots taken at each stage (before-delete Element detail panel,
   after-delete Props grid, after-delete Uploads grid, the stale-chip finding,
   the clean fresh-tab result) — kept in this session's screenshot history,
   not saved to disk (no `save_to_disk` requested; task did not ask for
   files, only a report).

## Names/ids removed

- Element: **`project_absence_prop_tag_100m`** (Category: Prop, "THE ABSENCE
  OF MEANING / Valder / $100,000,000" plaque), deleted from project «The
  Valder Collection No.7» / `ai-film-festival-3`.
- Upload: the source image of that Element (same $100,000,000 plaque
  thumbnail), most-recently-created image in the project's Uploads library
  at the time of deletion. Higgsfield's delete-upload dialog does not echo a
  filename/id, so no separate id string exists to record beyond "the
  most-recently-created image, confirmed by thumbnail before every click."

Nothing else was touched: `project_absence_prop_tag` (the $2,000,000
original), all other Elements, all other uploads, and every generation card
in the grid (including chain 2's in-flight jobs) were left exactly as found.

## Files changed

- `docs/reports/absence-plaque-element-cleanup-winbox.md` (this file)
- No sheets, plates, AB-LEDGER, or other project files touched.

## Tests run

- N/A (browser cleanup task, no code changes).

## Issues / Blockers

None. Both deletions succeeded, both were verified by reload, and the one
odd/confusing signal (a stale chip resolving in the original tab) was run to
ground with a second fresh-tab test rather than reported as a blocker — see
"Odd finding" in Step 3.

## Notes for Reviewer

- The stale-mention-chip behavior in Step 3 is worth folding into
  `higgsfield-unlimited-gen` or `browser-operator`: a soft page navigation
  (SPA route change) is **not sufficient** to refresh the composer's
  mention/autocomplete cache after deleting an Element — a genuinely fresh
  tab (or a hard reload, untested here) is needed to get a trustworthy
  "does this still resolve" answer. Verifying "no chip" in the same tab that
  did the deleting can give a false positive.
- One tab (`1638444841`) could not be closed via the MCP tool — after closing
  the first of two tabs, the session's tab group was auto-removed by Chrome
  (per the tool's own documented behavior: "If you close the group's last
  tab, Chrome auto-removes the group"), and the second tab dropped out of
  this session's trackable group before it could be closed in turn. Its
  composer was left empty (no chip, no bound reference, nothing fired) before
  this happened. Both tabs were released from `tab_registry.py` (`done
  task-2bbdd10b`). If that tab is still open in the shared Chrome window, it
  is a harmless orphan — safe to close per the tab-registry orphan rule.

## Replay Script

- path: none
- covers: n/a — this was a one-off cleanup of a specific mistakenly-created
  Element and its upload, not a repeatable flow.

## Browser Actions

- route: step 3 (own tab) — task named the exact Elements/Uploads pages and
  wanted precise DOM confirmation of two specific deletions; no API exists
  for this.
- steps_used: ~35 / 40 budget
- screenshots_taken: ~14 (window 1920x855 desktop; not shrunk, since every
  action here was state-changing — deletes and a composer check — and the
  skill requires desktop width for any state-changing click)
- pages_visited: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3?elements=1`,
  `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`
