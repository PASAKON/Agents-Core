/**
 * scripts/browser/higgsfield-valder-s3-fire.js
 *
 * Replay notes for firing Valder Scene 3 multi-cut video takes,
 * task-d30b3d1c (2026-08-25), The Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP. Read higgsfield-valder-character-images.js and
 * higgsfield-valder-s2-fire.js first for the base paste/desync/verify
 * recipe -- this file only records what was NEW or DIFFERENT for Scene 3.
 *
 * Result this run: SUCCESS. Both takes fired, 0 credits spent (balance
 * 1,974 -> 1,974). All 3 location Elements were already correctly
 * re-pointed and 1 of 3 already had eligibility cleared before this task
 * started -- audit-first saved a repeat of Job 1/Job 2 work. See
 * docs/reports/valder-s3-fire.md for the full writeup.
 *
 * NEW FINDING 1: the eligibility-warning tooltip has a tiny, precise hit
 * target -- centre-of-chip hover/click is NOT it.
 *
 * A warned reference chip shows a small warning-triangle icon at rest.
 * Hovering (or clicking) anywhere in the general chip area triggers the
 * chip's own hover overlay (expand-icon + remove-X), which visually
 * REPLACES the warning triangle. The Radix tooltip with the literal text
 * "This asset needs an eligibility check before it can be used." plus a
 * "Check eligibility" button only appears when the hover lands on the
 * warning triangle's own small hit-box, which sits at a slightly
 * different point than the chip's visual centre.
 *
 * Reliable way to find it: don't eyeball pixel coordinates from a
 * screenshot. Query the DOM directly:
 *
 *   const cards = [...document.querySelectorAll('svg')].filter(s => {
 *     const r = s.getBoundingClientRect();
 *     return r.top > 500 && r.top < 600 && r.width < 30 && r.width > 5;
 *   });
 *   // convert each candidate's CSS-px rect to screenshot-px by the
 *   // screenshotWidth/innerWidth ratio (measured ~1.342 this session,
 *   // re-measure per session -- it is NOT devicePixelRatio), then
 *   // hover (not click) exactly on that point.
 *
 * A click that misses the triangle and lands mid-chip opens a harmless
 * full-asset preview modal (`?preview=<uuid>`-style overlay) instead --
 * not destructive, just close it via its own X button and retry the hover.
 *
 * NEW FINDING 2: duration slider step count from 5s was 15 ArrowRight
 * presses to reach 20s this session, not 11.
 *
 * The task brief's "press ArrowRight 11 times" figure did not match this
 * composer instance. Don't trust a fixed count -- read the slider's own
 * ARIA state and drive off that instead:
 *
 *   const s = document.querySelector('[role="slider"]');
 *   // {min: s.getAttribute('aria-valuemin'), max: ..., now: ...}
 *   s.focus();
 *   // then press ArrowRight (target - now) times via the driving tool,
 *   // and re-read aria-valuenow to confirm it landed exactly on target
 *   // before touching anything else.
 *
 * This matches higgsfield-valder-s2-fire.js's own "DURATION CONTROL
 * CORRECTION" note (typing digits directly does NOT work, each keystroke
 * is an increment/decrement nudge) -- this run adds that the *increment
 * count itself* also isn't a fixed constant worth hardcoding into a brief.
 *
 * NEW FINDING 3: disambiguating a concurrency-slot toast from a genuinely
 * stuck Unlimited toggle -- read three signals, not one.
 *
 * Take 2's first Generate click produced the toast "You can generate 1
 * unlimited video, image & audio generation at a time." This LOOKS like it
 * could be the toggle-stuck failure mode documented elsewhere in this repo
 * (higgsfield-unlimited-gen skill, hard rule 6), but it is a completely
 * different, benign, self-resolving condition. Distinguish them like this
 * BEFORE assuming a stuck toggle and escalating:
 *
 *   1. Read the toggle's own `data-state` right after the toast appears.
 *      If it still reads "on", the toggle itself is fine -- a stuck
 *      toggle would show `data-state="off"` or refuse to flip on a
 *      fresh ref-click.
 *   2. Read the Generate button's price. If it's still struck-through
 *      to 0 (not a live un-struck number), pricing/Unlimited state is
 *      not the problem.
 *   3. Open a SEPARATE scratch tab (don't touch the composer tab -- a
 *      reload there resets Unlimited back to off, per documented
 *      behaviour) and check whether your own most recent generation
 *      (by asset id) has actually finished:
 *        document.querySelector('[data-asset-id="<id>"]')
 *        // check for a real <img> or <video> child, no [title] flag
 *        // text, no "processing" in innerText.
 *      If it's still a bare spinner shell (no img, no video), that
 *      generation is legitimately still holding the account's single
 *      Unlimited concurrency slot -- this is expected, not a bug.
 *
 * If (1) and (2) both look normal and (3) shows a genuine in-flight job,
 * this is NOT the GH #102 stuck-toggle scenario -- do not escalate, do
 * not try alternate click techniques on the toggle. Just wait for the
 * in-flight job to finish (poll cadence below) and retry the identical
 * Generate click; it will fire cleanly once the slot frees.
 *
 * WAIT PATTERN USED THIS RUN (outside the documented 01:00-07:00 UTC fast
 * window -- checked at 09:13 UTC, so ~25-30 min actual render time):
 *   - Poll from a SEPARATE scratch tab only, never the composer tab.
 *   - Sleep in ~90s chunks via `.venv/bin/python -c "import time;
 *     time.sleep(90)"` (or a loop of several), never one long block --
 *     this keeps the agent able to notice and act on new messages between
 *     chunks rather than being unreachable for 20-30 minutes straight.
 *   - Between chunks, re-navigate the scratch tab fresh (full reload, not
 *     just a DOM re-query) and re-check the target asset id's card state.
 *     A stale tab can lag; a fresh navigate + re-query is the reliable
 *     read, matching the "long-lived tab lies about the concurrency slot"
 *     finding elsewhere in this repo.
 *   - Once the target card shows a real `<img>` (poster frame), a "New"
 *     badge, and no flag/processing text, treat it as complete and
 *     immediately go back to the composer tab to fire the next take --
 *     no need to wait for a `<video>` element to appear in the DOM (that
 *     loads lazily on hover/click, not on completion).
 *
 * SETTINGS PERSISTENCE THIS RUN: a full page navigate() (not just an
 * in-app folder click) preserved EVERYTHING except the Unlimited toggle --
 * model, mode, prompt text, all 8 reference bindings, aspect, resolution,
 * duration, quality, and sound all survived the reload untouched. This
 * matches some earlier waves and contradicts others (see
 * higgsfield-valder-s2-fire.js Wave 2's "reload behaves differently" note)
 * -- re-verify every single pill fresh after any reload regardless of what
 * a prior wave's session happened to show; it is not a fixed contract.
 */
