/**
 * scripts/browser/higgsfield-valder-press-split.js
 *
 * Replay notes for splitting the dead `char_press` Element (terminal
 * Face/IP verdict, two journalists in one plate) into two single-face
 * Elements, task-6d6361ed (2026-08-28), The Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP. Thin addendum to higgsfield-image-gen.js (base
 * paste/desync/verify recipe) and higgsfield-valder-neighbor-regen.js
 * (Element creation/re-point) -- read those first, this file only records
 * what was NEW or notable this run.
 *
 * Result: 2/2 first-attempt, no reshoot needed, neither flagged. GPT Image 2
 * / 16:9 / Medium / 2K, 2.5 credits each, 5 credits total. Both Elements
 * filed and both PNGs delivered to Drive.
 *   - char_press_a (reporter, petrol blue): asset feb18927-d07e-471a-9758-
 *     29e3cec2a0aa, Element @project_absence_char_press_a
 *   - char_press_b (camera operator, rust orange): asset f4498e2b-ad9e-
 *     4561-9a7c-83ccee0cfa8e, Element @project_absence_char_press_b
 *
 * CONFIRMING THE DEAD ELEMENT'S FLAG STATE (per task's "confirm which
 * state" instruction):
 *   Opened @project_absence_char_press's own Info panel (Elements tool ->
 *   search "press" -> click the 2-journalist card). No "Check eligibility"
 *   control, warning-triangle icon, or any Face/IP text anywhere on the
 *   Element's own surfaces -- checked via a single javascript_tool DOM dump
 *   of the open [role="dialog"] plus a title-attribute scan for
 *   /face|ip|eligib|flag|protect/i, both came back empty. This is the SAME
 *   absence higgsfield-valder-neighbor-regen.js documented for a different
 *   Element ("second operator in a row who could not find it") -- this run
 *   makes three. Did not chase further: task's own table already states
 *   char_press's verdict is terminal, and the Element panel offering no
 *   eligibility control at all is consistent with that, not with a pending
 *   re-check (which per the task brief would show a clickable button).
 *   Did NOT reproduce the actual composer-side red tooltip (would have
 *   required attaching the dead reference in a video composer, touching
 *   scope this task didn't need) -- the absence-of-control finding above
 *   was judged sufficient corroboration without spending extra steps.
 *
 * STEP 1 -- generation (project-root composer, NOT a specific folder):
 *   1. Own tab, project root URL (no /folders/<uuid> segment). Composer
 *      loaded in VIDEO mode by default (Cinema Studio 4.0 / 1080p / 16:9,
 *      GENERATE showing a live credit price -- did not touch it).
 *   2. Switched to Image mode via the small "Image" icon stacked above
 *      "Video" at the bottom-left of the composer (NOT the top-nav "Image"
 *      tab, which is a different page). First click at the Video label's
 *      y-coordinate missed and left it in Video mode -- always re-screenshot
 *      after this click and confirm the settings row actually changed
 *      before trusting it landed.
 *   3. Model defaulted to "Higgsfield Soul Cinema" -- opened the model
 *      picker pill, selected "GPT Image 2" from the list. Per the
 *      higgsfield-unlimited-gen skill, Soul Cinema does NOT accept
 *      reference images at all; this task needed the location reference
 *      attached, so GPT Image 2 was mandatory, not a preference.
 *   4. Quality defaulted to High (GENERATE showed 8.5) -- clicked the
 *      Quality pill, selected Medium (GENERATE dropped to 2.5, matching the
 *      task's stated expected cost exactly). Aspect ratio defaulted to
 *      Auto -- opened that pill, scrolled the dropdown (it's taller than
 *      the visible list), selected 16:9. Resolution was already 2K, no
 *      change needed.
 *   5. Paste (synthetic ClipboardEvent, text/plain only) onto the visible
 *      (non-decoy) contenteditable landed correctly on the FIRST attempt
 *      both times -- normalized length matched source exactly (1155/1159
 *      and 1230/1234 chars, whitespace-collapse difference only) on first
 *      read-back.
 *   6. The prompt's own body contained the literal string
 *      "@project_absence_loc_hall_big_d" (the shared location reference
 *      both plates attach) -- auto-resolved into a bound mention chip on
 *      paste, no manual @-picker needed. Verified via
 *      `[...editor.querySelectorAll('[data-beautiful-mention]')]
 *        .map(m => m.getAttribute('data-beautiful-mention'))`
 *      both times -- resolved to the same UUID
 *      (@1a2cf503-4843-4aed-b4cb-d7cb8b919fa8) on both prompts, confirming
 *      it's the same location Element both times.
 *   7. Desync fix (focus + Selection API cursor-to-end + real Space + real
 *      BackSpace) applied once immediately before each Generate click.
 *      Fired cleanly on the FIRST attempt both times -- no no-op cycle.
 *   8. Generate clicked via `find`-ref (not raw JS .click()), per the
 *      money-committing-button convention. "Generation started" toast +
 *      "All assets" counter increment (376->377, 377->378) confirmed both
 *      fires within the same javascript_tool read.
 *   9. Poll `[data-asset-id]` top card's `data-job-status` every ~20-25s
 *      (matches higgsfield-valder-neighbor-regen.js's "much shorter than
 *      video" finding for GPT Image 2 / Medium / 2K single images -- both
 *      completed within one 20-25s poll cycle, no need for the long video
 *      cadence here).
 *
 * STAGING THE SECOND PROMPT DURING THE FIRST RENDER (per the
 * higgsfield-unlimited-gen skill's "pre-stage the next prompt" pattern --
 * applies to paid image gen too, not just Unlimited video):
 *   Immediately after firing char_press_a, cleared the composer (real
 *   Cmd+A + Delete, left 1 stray newline -- acceptable, matches prior
 *   waves' observed "one pass often leaves 1 stray char") and pasted
 *   char_press_b's prompt while A was still `in_progress`. Re-verified the
 *   mention chip and the fresh Generate button price (still 2.5, settings
 *   hadn't drifted) immediately before actually clicking B -- did NOT treat
 *   the earlier staging-time check as sufficient, per the skill's explicit
 *   warning that a staged prompt gets no exemption from the pre-click
 *   checks.
 *
 * VERIFYING AGAINST HOUSE RULES (opened each card via
 * ?preview=<asset-id>, NOT the grid thumbnail -- click the visual CENTER of
 * the thumbnail, not its top-left corner, which hits the selection
 * checkbox instead):
 *   Both cards rendered as a clean single-row 4-panel sheet (front full
 *   body / face close-up / side profile / rear) at full size in the
 *   preview dialog -- no need for `zoom` on sub-regions, the modal's own
 *   render was large enough to judge every panel directly, including skin
 *   texture and the rear panel's presence. Checked against every line in
 *   the task's HOUSE RULES section directly off this one full-size view:
 *   four panels present (rear included), real age/skin variation, one
 *   saturated colour per person (petrol blue coat / rust orange jacket,
 *   neither black), no lanyard/badge/logo, no gold V, camera fully
 *   analogue (no screens/LEDs/cables/battery packs visible), background
 *   matches the attached location reference (terracotta terrazzo, warm
 *   amber light, visible columns). Both passed on the first generation,
 *   no reshoot needed.
 *
 * FILING AS ELEMENTS (per higgsfield-image-gen.js Wave 9's "Create
 * Element" card-menu finding -- confirmed working again here):
 *   From the open preview dialog, the "..." (More) button at bottom-right
 *   of the action row -> "Create Element" opens the New Element dialog
 *   PRE-POPULATED with that exact asset already attached (no upload step).
 *   - Category dropdown: click the pill to open, click "Character" in the
 *     list. NOTE this run: the FIRST click on "Character" silently did NOT
 *     take on one of the two dialogs (a re-screenshot showed the dropdown
 *     re-opened with "Auto" still checked) -- always re-screenshot after
 *     selecting a category option and confirm the pill text actually
 *     changed before touching Name/Element ID, exactly the same
 *     stale-dropdown caution higgsfield-image-gen.js Wave 9 already
 *     documented for this same Category control.
 *   - Name / Element ID inputs: native value-setter + `input` event
 *     dispatch via JS (coordinate typing does not register on these two
 *     fields, confirmed again). Selector this run: find the input by
 *     `placeholder === 'Enter element name'` for Name and
 *     `placeholder === 'e.g. char_oli_v1'` for Element ID -- more reliable
 *     than matching on current `.value`, since (oddly) the Name field
 *     arrived on one of the two dialogs already showing "Press A" as a
 *     real value before any script touched it (cause unconfirmed -- not a
 *     result of this script, which threw and aborted before writing
 *     anything the first time it ran; left as an open question for the
 *     next operator rather than a confirmed finding).
 *   - Element ID convention followed: `project_absence_char_press_a` /
 *     `_b`, consistent with the dead `project_absence_char_press` and the
 *     project's adopted `project_<slug>_char_*` scheme.
 *   - "Element created." toast confirmed both times immediately after
 *     Create.
 *
 * DOWNLOAD + DRIVE FILING:
 *   Download button in the preview dialog -> "Preparing download" ->
 *   lands in ~/Downloads as `hf_<UTC-timestamp>_<asset-id>.png`. Verified
 *   via `ls -lat ~/Downloads` (Bash) matching the asset id from the card's
 *   `data-asset-id` / preview URL. Copied (not moved) into
 *   `.../ALL DRAFT/YT: ILAG/Sorry, Sir/Element/` as `absence-char-press-a.png`
 *   / `absence-char-press-b.png` -- byte-for-byte size match confirmed
 *   between the Downloads original and the Drive copy.
 *   Asset ids (commit these before anything else touches the composer --
 *   ids cannot be recovered, files always can):
 *     char_press_a: feb18927-d07e-471a-9758-29e3cec2a0aa
 *     char_press_b: f4498e2b-ad9e-4561-9a7c-83ccee0cfa8e
 *
 * SCOPE NOTE: another operator owned the video composer tab in the same
 * Chrome throughout this run, per the task brief. This run opened its own
 * tab via `tabs_context_mcp` (which returned only a single "New Tab" --
 * the other operator's tab was not visible in this session's tab group at
 * all, so there was never a risk of touching it) and never navigated,
 * refreshed, or closed anything outside that tab.
 */
