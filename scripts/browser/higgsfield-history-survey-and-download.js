/**
 * Higgsfield project History — survey a date range + download clips.
 * Built during task-cf982bd0 («Sorry, Sir» Drive reconciliation, 31 Aug/1 Sep).
 *
 * This is NOT a fire-and-forget script (per higgsfield-unlimited-gen skill,
 * Generate/Recreate/Unlimited-toggle stay under live model confirmation on
 * purpose). It documents the manual technique, all measured this session, so
 * the next operator doesn't re-derive it from scratch.
 *
 * ============================================================
 * 1. FILTER TO A DATE RANGE — read-only, no risk
 * ============================================================
 * Click Filter (top right) -> Date range -> Custom range -> click start day
 * then end day in the calendar -> Activity -> Generated (excludes uploads /
 * reference plates). Chip label may say e.g. "August 30 - September 1" even
 * though the calendar only highlighted 31 and 1 — TRUST the calendar detail
 * view, not the truncated chip text.
 *
 * ============================================================
 * 2. DO NOT SCROLL-AND-CLICK GRID THUMBNAILS BY COORDINATE
 * ============================================================
 * Measured this session: the composer panel (bottom-right, "Describe your
 * scene...") has a much larger invisible click-catching DOM box than its
 * visible painted area, AND it overlaps most of the grid below row 1 at
 * normal window sizes. A CSS `zoom` trick to shrink the grid and see more
 * rows makes screenshot-pixel <-> CSS-pixel coordinate math ambiguous and
 * WILL misfire clicks onto the wrong card. Coordinate-based grid clicking
 * is also just flaky in general on this SPA (~30-50% failure rate even on
 * a clean unobstructed target) — clicks silently no-op with no error.
 *
 * THE FIX: open ONE card from the grid (top-left area, offset a little
 * below-right of its "Last viewed"/"New" badge to dodge the badge's own
 * dead click zone), then use ArrowRight / ArrowLeft inside the opened
 * lightbox to step through EVERY asset in the filtered set, in the same
 * order the grid renders them. No more grid clicking needed after that.
 * Verify by reading `location.href.split('preview=')[1]` after each press.
 *
 * ============================================================
 * 3. READING PROMPT / SCENE / RESOLUTION / TIMESTAMP PER CARD
 * ============================================================
 * The right-side Info panel has PROMPT (collapsed — click "See all" to
 * expand for scenes whose first non-blank line is an @element-tag list
 * rather than a "SCENE N —" header) and DETAILS (Model / Quality / Bitrate
 * / Size / Created). There is NO duration field in this panel — Higgsfield
 * does not expose clip duration anywhere in the DOM. Get duration from the
 * downloaded file via ffprobe instead (see step 5).
 *
 * Extraction snippet (paste into javascript_tool once a card is open):
 *
 *   function findByText(txt){return [...document.querySelectorAll('*')]
 *     .filter(e => e.children.length===0 && e.textContent.trim()===txt);}
 *   function panelRoot(){
 *     const created = findByText('Created');
 *     if (!created.length) return null;
 *     let root = created[0];
 *     for (let i=0;i<10;i++){ root = root.parentElement; if(!root) break; }
 *     return root;
 *   }
 *   const root = panelRoot();
 *   const promptFirstLine = root.innerText.split('\n')
 *     .find(l=>l.trim().length>0 && !['PROMPT','Copy'].includes(l.trim()));
 *   const details = root.innerText.split('DETAILS')[1] || root.innerText;
 *   JSON.stringify({promptFirstLine, url: location.href.split('preview=')[1],
 *     detailsRaw: details.split('\n').map(s=>s.trim()).filter(Boolean).slice(0,12)});
 *
 * "Created" is shown in the account's LOCAL timezone (ICT, UTC+7 for this
 * org). Keep that in mind vs. the UTC timestamps Google Drive's API returns
 * — see step 5, this cost a full wrong conclusion this session.
 *
 * ============================================================
 * 4. CRITICAL: the "asset id" in the URL is NOT the id in the
 *    downloaded filename, and Drive matches on the LATTER
 * ============================================================
 * `?preview=<uuid>` in the URL is a folder-item / display id.
 * The actual downloaded file is named `hf_<UTC-timestamp>_<uuid2>.mp4`
 * where uuid2 is a DIFFERENT uuid — the raw generation-job id. Google
 * Drive's existing filing convention (`absence-<SCENE>-take<N>-<uuid2-8chars>...`)
 * uses uuid2, not the preview-url uuid. You cannot know whether a clip is
 * already on Drive from the preview-url id alone — you must download it
 * (or otherwise obtain uuid2) and check its 8-char prefix against Drive.
 *
 * Confirmed this session: `?preview=d32a9428-...` (Higgsfield UI: "Created
 * August 31, 2026 at 12:30 AM") downloaded as
 * `hf_20260830_173005_09bf269e-....mp4`. UTC 17:30:05 Aug 30 + 7h = ICT
 * 00:30 Aug 31 — consistent, same asset, genuinely different id scheme.
 * `09bf269e` was already filed to Drive as
 * `absence-S18a-take1-09bf269e-FLAGGED-5s-not-20s.mp4` (uploaded ~44 min
 * after generation). So this specific clip was ALREADY DONE, not new.
 *
 * ============================================================
 * 5. TIMEZONE TRAP when reconciling against Drive
 * ============================================================
 * Google Drive's API `createdTime` is UTC. Higgsfield's UI "Created" field
 * is ICT (UTC+7) for this org. A naive same-calendar-day compare between
 * the two WILL misclassify items in the ~7-hour band near midnight ICT —
 * e.g. a Drive file stamped `2026-08-30T22:41` UTC is actually
 * `2026-08-31 05:41 AM` ICT, i.e. already "the next day" by the org's own
 * clock. Always convert Drive's UTC to ICT (+7h) before comparing against
 * a "which day was this generated" boundary Higgsfield or the CEO stated
 * in local time.
 *
 * ============================================================
 * 6. DOWNLOADING — the Download button is flaky, budget for retries
 * ============================================================
 * With a card open: Info tab -> "Download" button (bottom of the right
 * panel, below Recreate/Reference). Downloads straight to ~/Downloads with
 * no dialog.
 *
 * ⚠️ DO NOT `computer.click` this button by screenshot coordinates. Measured
 * this session: the button's screenshot-pixel position drifts between page
 * loads even at a FIXED requested window size (1200x800 in every case), by
 * enough to miss the button outright — confirmed via
 * `getBoundingClientRect()` showing the real center 190px away from where a
 * previous successful click had landed. The screenshot-to-CSS-pixel ratio is
 * also NOT uniform between width and height (e.g. rx=1.15, ry=1.39 measured
 * once), so hand-computed coordinate math from an old screenshot silently
 * drifts wrong. A `find()` ref-based click had the SAME low success rate as
 * raw coordinates in this session — this is not a coordinate problem.
 *
 * ✅ THE FIX: drive it via `javascript_tool`, not `computer`:
 *   const btn = [...document.querySelectorAll('button')]
 *     .find(b => b.textContent.trim() === 'Download');
 *   btn.click();
 * This is dramatically more reliable than any pointer-based click for this
 * specific button (real success rate near 100% within 1-2 attempts, vs.
 * needing 3-5+ coordinate clicks and sometimes never firing at all).
 *
 * Even with `.click()`, still budget for retries and delayed completion:
 *   navigate to `?preview=<id>` (full URL, not SPA nav)
 *   wait ~6-10s for the modal to actually render — `btn` may be `undefined`
 *     even after `document.readyState === 'complete'`; poll/retry the query
 *     rather than trusting readyState alone
 *   `btn.click()` via javascript_tool
 *   wait, check ~/Downloads for a new file (`ls -lat ~/Downloads/*.mp4 | head -3`)
 *   if nothing new after ~7s: click again once
 *   if STILL nothing after a second click: open a genuinely FRESH TAB
 *     (`tabs_create_mcp`, not SPA-navigate the same tab) and retry there —
 *     measured this session: items stuck after repeated clicks on a
 *     long-lived tab succeeded on the very first click of a new tab, more
 *     than once. This matches the browser-operator skill's "a long-lived tab
 *     lies about state" guidance, extended to the Download button.
 *   ⚠️ A click can also succeed with a LONG delay (~20s+) that lands only
 *     after you've already navigated on to the NEXT item. If a later item's
 *     download produces a filename whose uuid doesn't match what you expect,
 *     check whether it actually matches the PREVIOUS item's asset (compare
 *     the UTC timestamp in the filename, +7h for ICT, against that earlier
 *     item's own "Created" field) before concluding something is wrong.
 *   Per standing CTO guidance: an asset whose own preview never renders a
 *     frame (fully black main viewer, not just a dark-toned scene) is a
 *     broken asset, not a click problem — flag and skip after one retry,
 *     don't keep hammering it.
 *
 * ============================================================
 * 7. FILING TO DRIVE
 * ============================================================
 * Use `scripts/drive-find.py` (read) and `scripts/gdrive-bridge/ilag_sync.py`'s
 * `api()` / `upload()` helpers (see that file) for the actual Drive write —
 * this project's Drive root differs from the ilag_sync.py DEFAULT
 * (`DRIVE_ROOT_ID` there is hardcoded to "Do Not Disturb"). For «Sorry, Sir»
 * / The Valder Collection No.7:
 *   project root:  1eJH1p789LLfufpSgWF47KeHziUxOHxPh  (ALL DRAFT/YT: ILAG/Sorry, Sir (The Valder Collection))
 *   All Scene:     1KMD0xsVe691SSh5eCAWM_QDOJMbzRNyJ
 * Scene sub-shots (S8a/b/c/d, S18a/b, S12a/b/c) file into the SAME BARE
 * folder their siblings already use (e.g. "S8" holds every S8a/b/c/d take,
 * "S18" holds every S18a/b take, "S12" holds every S12a/b/c take) —
 * confirmed by walking the actual folder contents, not by folder name
 * alone. Always resolve the target folder id fresh and verify by listing
 * it, per the skill's standing warning that sub-shot folders drift.
 *
 * ⚠️ DUPLICATE FOLDER NAMES EXIST. This project has TWO Drive folders both
 * literally named "S5" under All Scene — one holds the real take1/take2
 * files, the other is an empty leftover with only a stray "v1-no-door"
 * subfolder. A naive `{name: id}` dict built from listing All Scene's
 * children will silently pick whichever one the API happens to return last.
 * Before uploading, list the CANDIDATE folder's own children and confirm it
 * already contains that scene's earlier takes — never trust a name match
 * alone when more than one folder shares the name.
 *
 * ============================================================
 * 8. A SECOND OPERATOR CAN FILE TO THE SAME FOLDERS WHILE YOU WORK
 * ============================================================
 * If another browser_operator is generating/filing in this same project
 * concurrently (a normal situation per the skill — they hold the Unlimited
 * render slot, you're doing read-only reconciliation), they can upload a
 * clip to Drive mid-session with the EXACT filename you were about to use.
 * Measured this session: a fresh re-scan of Drive right before uploading
 * found `absence-S18b-take1-6a6377db-...` already present — filed by the
 * other operator between when this session first surveyed Drive and when it
 * got around to uploading. Re-scan Drive immediately before every upload
 * batch (not just once at the start of the session) and skip anything that
 * already matches your target uuid — don't assume your earlier snapshot is
 * still current, especially for a wave that ran long.
 */
