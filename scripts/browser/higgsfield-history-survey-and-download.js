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
 * no dialog. Measured this session: anywhere from 1 to 5 clicks needed,
 * with waits up to ~10s between clicks, before the file actually appears —
 * no error, no visible "processing" state change, it just silently doesn't
 * fire the download sometimes. One clip never triggered after 4 clicks /
 * ~35s and was left for a retry pass. This matches the browser-operator
 * skill's documented "clicks stop registering across the whole tab" failure
 * mode — a hard reload (full `navigate`, not SPA routing) sometimes but not
 * always unsticks it.
 *
 * Practical pattern that worked most often:
 *   navigate to `?preview=<id>` (full URL, not SPA nav)
 *   wait ~6-7s for the modal to actually render (readyState/DOM check)
 *   click Download
 *   wait, check ~/Downloads for a new file (`ls -lat ~/Downloads/*.mp4 | head -3`)
 *   if nothing new: click again, wait longer (up to ~10s), recheck
 *   after ~4-5 failed clicks over ~35s: flag it and move on, come back later
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
 */
