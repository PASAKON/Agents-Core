/**
 * scripts/browser/higgsfield-valder-final-two.js
 *
 * Replay notes for firing Valder's final two clips (Scene 4 take 2, Scene 2
 * take 2), task-a505bd00 (2026-08-25), The Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP. Read higgsfield-valder-s2-fire.js and
 * higgsfield-valder-s3-fire.js first for the base paste/desync/verify
 * recipe -- this file only records what was NEW this run.
 *
 * Result: SUCCESS. Both takes fired and completed. 0 credits spent (1,974 ->
 * 1,974). Generation A (Scene 4 take 2): c4c9174d-4f01-4642-9009-007d43b1d047,
 * ~21 min render. Generation B (Scene 2 take 2):
 * a1fd6c07-b067-4e8c-b64e-ebe7653ff6ec, ~24 min render.
 *
 * NEW FINDING: verify asset existence/status/prompt via the account's own
 * API, not by clicking the card open. This run, real `computer` clicks on a
 * card at coordinates verified correct via `elementFromPoint` (landing
 * inside the exact target `data-asset-id` element's own subtree)
 * intermittently opened a DIFFERENT asset's detail panel -- a specific,
 * reproducible wrong id (`cf198b5c-5c98-46ac-9be7-fb43fea6396e`), not random
 * noise. This is NOT the documented decoy-DOM bug family: a duplicate-
 * position check (`getBoundingClientRect` bucketed by position) found zero
 * overlapping elements, only one node per `data-asset-id` in the DOM. Root
 * cause not confirmed -- plausibly a virtualized-grid hit-test computing
 * click target from pixel position independently of the currently-rendered
 * DOM, which can drift out of sync with what's on screen.
 *
 * THE FIX: skip the card UI entirely for verification. The page already
 * authenticates via Clerk; grab its session token and hit the job endpoint
 * directly:
 *
 *   const token = await window.Clerk.session.getToken();
 *   const res = await fetch(`https://fnf-api-gw.higgsfield.ai/fnf/jobs/${assetId}`,
 *     {headers: {Authorization: 'Bearer ' + token}});
 *   const data = await res.json();
 *   // data.status ("completed" | "queued" | "in_progress"), data.is_viewed,
 *   // data.params.prompt (full text), data.created_at, data.user_id, etc.
 *
 * This is read-only (a GET against the same endpoint the page's own React
 * code calls -- confirmed by watching `read_network_requests` after a
 * successful card-view: `GET /fnf/jobs/{id}` is exactly what the app fires),
 * uses no credentials beyond the already-authenticated session, costs one
 * `javascript_tool` call (~15-50 tokens) instead of several screenshots and
 * failed clicks, and is immune to whatever causes the click-mismatch bug.
 * Use it any time a task needs to know "does asset X exist / is it done /
 * what's its saved prompt" -- reserve real clicks for things the API can't
 * tell you (visual judgment calls, Recreate, Check eligibility, Generate
 * itself).
 *
 * The folder id for this project's "All assets" view (needed for the
 * members/v2 endpoint, which is folder MEMBERS/people, NOT assets -- don't
 * use it for asset listing, it was a dead end this run):
 * `50d2d839-9cc6-41c5-9e08-bb8df41f4e06`. To list the currently-loaded asset
 * cards' ids cheaply (virtualized, ~24 in DOM at once regardless of total):
 *
 *   [...document.querySelectorAll('[data-asset-id]')].map(el =>
 *     el.getAttribute('data-asset-id'))
 *
 * The credit balance shown via `GET /fnf/workspaces/wallet`
 * (`credits_balance` field) is a DIFFERENT, larger number than the
 * account-menu "Credits: N left" figure this project has always tracked
 * (measured this run: wallet API said 3,000, UI said 1,974, both read at the
 * same moment). Do not use the wallet API for the before/after credit check
 * this project's task briefs always want -- open the avatar menu
 * (`find('user account avatar button')`, click, read
 * `document.body.innerText.match(/[\d,]+\s*left/i)`, close via a click
 * elsewhere on the page, NOT Escape, per the Wave 4 tab-group-destruction
 * warning in higgsfield-image-gen.js) and use that number.
 *
 * CONFIRMED AGAIN, no new findings: the desync fix (focus editor -> Selection
 * API cursor-to-end -> real Space -> real BackSpace, applied fresh
 * immediately before every Generate click, re-applied even after a prompt
 * sat staged for 20+ minutes during a prior render) worked on the first
 * Generate click both times this run. Duration slider: this run's default
 * was 5s and each ArrowRight press moved it by exactly 1s (5->6->7...->20,
 * 14 presses after the first) -- confirmed via reading the popover's own
 * displayed `\d+s` text after the batch, not assumed.
 *
 * WARM-UP PATTERN CONFIRMED: staged Generation B's prompt (clear + paste +
 * verify 7/7 bindings) in the SAME composer tab immediately after
 * Generation A's Generate click was confirmed fired, while A rendered
 * server-side for ~21 minutes. The composer tab was never navigated away, so
 * none of the settings (model/mode/aspect/resolution/duration/quality/
 * sound/Unlimited) reset -- only needed to re-apply the desync fix fresh and
 * re-verify the zero-digit/struck-through price immediately before B's
 * actual click. Saved the entire settings-rebuild + re-paste sequence from
 * B's critical path.
 *
 * Scene 1 v3 reshoot (task-be7868a5, 2026-08-26): two takes of the SAME
 * ~23,600-char multi-cut prompt (7 hard-cut shots, 8 Elements), folder
 * "Sence 1" (project's own typo, not ours). Result: SUCCESS, both takes
 * fired and completed, 0 credits (1,974 -> 1,974). Take A:
 * 825450f4-8eef-4d3f-b12c-3d4f27319aa2 (~28.5 min: queued 0-19.5min,
 * in_progress 19.5-28.5min). Take B:
 * 13c82d2d-4dca-4063-bbf6-1a843aa23dd5 (~33 min: queued 0-24min,
 * in_progress 24-33min -- both notably longer than the prior wave's
 * ~21-24min, still well inside the 90-min cancel threshold, no action
 * needed).
 *
 * NEW FINDING: composer settings and folder navigation survived from a
 * PRIOR SESSION, not just within-run. On fresh folder load this run, the
 * pill row already read Seedance 2.5 / References / 16:9 / 720p / 20s /
 * High / Sound On with ZERO manual pill changes needed (only Unlimited
 * itself needed toggling, since that one resets on reload per the
 * documented hard rule). This contradicts the general "in-app navigate
 * resets duration/quality to 5s/1080p" folklore -- treat every pill as
 * needing FRESH verification via a visibility-filtered button-text scan
 * regardless of what folklore predicts, since it can go either way.
 *
 * QUOTE-ESCAPING TRAP when embedding a long prompt (with its own embedded
 * "quoted dialogue") into a javascript_tool call: `JSON.parse("...")` with
 * manually-escaped `\"` inside the call text broke -- the transport layer
 * apparently unescapes `\"` -> `"` once before the JS ever sees it, so
 * `JSON.parse("Seedance...)` lost its opening quote and threw
 * `SyntaxError: Unexpected token 'S'`. FIX: use a raw JS template literal
 * (backticks) instead and paste the prompt text completely unescaped --
 * real double/single quotes inside backticks need no escaping at all.
 * Only check first: the prompt must contain no literal backtick or `${`
 * sequence (true of every prompt seen on this project so far). Verified
 * clean: sourceLen after paste matched the source file's exact character
 * count (23613) before this trap was even hit, then editor
 * innerText/mentions matched post-fix.
 *
 * Editor focus does NOT survive a Generate click. After Take A's Generate
 * click, a same-tab `cmd+a`/`Delete` clear silently no-op'd (editor
 * innerText stayed at its post-paste length) because focus had moved off
 * the editor onto the button. Fix: re-run the visible-editor lookup and
 * `el.focus()` via JS immediately before ANY subsequent clear/paste in the
 * same composer session, don't assume focus persists from an earlier step
 * even seconds prior.
 *
 * The "All assets" folder counter lags behind the actual new-card
 * insertion by a few seconds after a Generate click (stayed at the
 * pre-click count immediately after the toast, still correct after a 3s
 * wait once re-read). The `[data-asset-id]` grid's own card ORDER (newest
 * first) updated correctly before the counter did -- when correlating a
 * fresh Generate to its asset id, prefer reading the top card id and
 * verifying it via the `GET /fnf/jobs/{id}` API over trusting the counter
 * delta alone if they disagree.
 */
