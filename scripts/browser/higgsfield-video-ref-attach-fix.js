// Higgsfield project-composer (ai-film-festival-3) video-reference attach —
// mechanical notes only. Paste into javascript_tool against the already-open,
// already-logged-in project tab. Built from task-f7ac7a01 (2026-09-06),
// S2K-Fix1 wave.
//
// Does NOT auto-click Generate — that stays under a model's live visual
// confirmation on purpose (higgsfield-unlimited-gen skill).

/*
 * SETUP (Seedance 2.5 video composer):
 *   1. Video tab already selected by default; click model chip -> "Seedance 2.5"
 *      in the "Featured models" list (defaults to Cinema Studio 4.0).
 *   2. Duration is a Radix ARIA slider, not a text field:
 *        const s = document.querySelector('[role="slider"]');
 *        s.focus();  // clicking it directly often lands on an overlay label
 *                    // bubble sitting ON TOP of the thumb -- JS .focus() is
 *                    // reliable, a `computer` click at the visual center is not.
 *        // then real ArrowRight/ArrowLeft keypresses, one per second of delta
 *   3. Paste prompt via synthetic ClipboardEvent (text/plain only) into the
 *      visible (getComputedStyle(e).visibility !== 'hidden') contenteditable
 *      -- there are 2, one is a decoy. Then real End, Space, BackSpace
 *      keypresses to force the framework's bound state to sync (a paste alone
 *      can leave visible text correct but bound state empty).
 *   4. Chip gate (selector current as of 2026-09-05):
 *        [...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')]
 *          .filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@'))
 *      Count UNIQUE values against `python3 scripts/prompt-lint.py --chips <sheet>`.
 *   5. Unlimited toggle: find via aria-label "Unlimited mode", click, verify
 *      data-state === "on". RESETS ON EVERY RELOAD/fresh-tab -- everything
 *      else (model/duration/resolution/quality/sound) can survive a reload's
 *      autosave, Unlimited never does. Re-verify last, right before Generate.
 *
 * ATTACHING THE VIDEO REFERENCE -- the hard part, confirmed end-to-end:
 *
 *   a. Upload via the "+" icon -> Uploads panel -> Videos tab -> the file
 *      input whose accept includes video/mp4 (find() by "file input for
 *      uploading video media" typically returns it directly). Wait for
 *      "Your upload is being verified" toast, then poll.
 *
 *   b. THE GRID DEFAULTS TO "Last used" SORT, NOT "Last created". If you (or
 *      anyone) previously clicked into a broken/rejected asset this session,
 *      THAT asset becomes "last used" and sorts to the front -- ahead of your
 *      fresh upload. Clicking the visually-first tile in that state attaches
 *      the WRONG (possibly REJECTED/dead) asset with zero visible error.
 *      Measured 3 times in one session before diagnosing this.
 *
 *   c. VERIFY BEFORE TRUSTING ANY TILE, every time, via byte-exact match:
 *        function srcAt(x,y){
 *          const el = document.elementFromPoint(x,y);
 *          let node = el, video=null;
 *          for (let i=0;i<10 && node;i++){
 *            const v = node.querySelector ? node.querySelector('video') : null;
 *            if (v){video=v;break;}
 *            node = node.parentElement;
 *          }
 *          return video ? (video.currentSrc||video.src) : null;
 *        }
 *        // hover the tile (real `computer` hover, not synthetic JS events --
 *        // synthetic pointerover/mouseover did NOT mount the lazy <video> in
 *        // this session), then read srcAt(centerX, centerY), then:
 *        const r = await fetch(candidateSrc, {method:'HEAD'});
 *        r.headers.get('content-length') // must equal the LOCAL file's exact
 *                                         // byte size (stat -f%z / wc -c)
 *      A byte-exact content-length match is conclusive. A mismatch (even a
 *      plausible-looking one, e.g. an older render of "the same" scene) means
 *      you are about to bind the wrong reference -- do not click it.
 *
 *   d. CLICK THE VERIFIED TILE WITH A REAL MOUSE CLICK (`computer` tool) at
 *      the same coordinate you just verified via elementFromPoint. A raw JS
 *      `.click()` on the DOM node is NOT equivalent here and reproduced the
 *      wrong-asset bug even when called on a node that `elementFromPoint`
 *      independently confirmed correct seconds earlier -- root cause not
 *      fully isolated, but the real-click path was reliable 2/2 times once
 *      the tile itself was byte-verified first.
 *
 *   e. Confirm attach via the "Added to prompt box" toast AND by reading the
 *      composer's own reference-tray <video> src (NOT the grid's) and
 *      re-running the same content-length HEAD check on it. The tray is the
 *      thing that actually gets sent to Generate -- verify THAT, not the grid.
 *
 *   f. If a wrong reference lands in the tray: hover it, click the X that
 *      appears (top-left of the 48x48 tray thumbnail), confirm chip count is
 *      unchanged (detaching a video can silently delete an adjacent Element
 *      chip's text per the existing hard rule -- recount every time), then
 *      retry from (b).
 *
 * GENERATE-CLICK DUPLICATE-FIRE TRAP (new finding, cost 3 extra image
 * generations in this session, ~$0.12, disclosed to CTO):
 *   A Generate click that shows NO "Generation started" toast and NO asset-
 *   count increment after 3-5 seconds is NOT reliably a no-op. In this
 *   session the FIRST click on GPT Image 2's Generate button produced no
 *   visible confirmation within 5s, was treated as a no-op, and a SECOND
 *   click was fired -- which DID show "Generation started". Minutes later,
 *   FOUR total new images existed instead of the intended ONE, meaning the
 *   "silent" first click (and possibly a third factor -- batch/retry
 *   behavior on the platform side) also fired for real, just delayed.
 *   FIX: after any Generate click with no immediate toast, wait a FULL 15-20
 *   seconds and re-check the asset count / toast history before deciding to
 *   retry. If you must retry, expect BOTH clicks may land, and say so
 *   up front rather than discovering it after the fact from a padded asset
 *   count. This generalizes the existing "wait 4-6s" guidance in
 *   higgsfield-image-gen.js -- 4-6s was not long enough in this session.
 *
 * VERIFICATION BEFORE EVERY GENERATE (video or image), no exceptions:
 *   - zoom screenshot (not DOM text) on the real Generate button: struck-
 *     through price then 0 for Unlimited video; a small live number (no
 *     strike) for a paid GPT Image 2 plate.
 *   - chip count unique === lint's expected count.
 *   - reference tray content-length-verified if a video ref is involved.
 *   - all six video fields read back fresh (model/aspect/resolution/
 *     duration/quality/sound) -- duration and resolution both silently
 *     reset to defaults across reloads/mode switches in this session.
 *
 * IMAGE MODE (GPT Image 2) SWITCH:
 *   The Image/Video toggle tab did not respond to a real `computer` click in
 *   this session (2/2 attempts). What worked: a synthetic PointerEvent
 *   sequence (pointerdown, mousedown, pointerup, mouseup, click, all
 *   bubbles:true/cancelable:true) dispatched via javascript_tool at the
 *   button's own rect center. This is a plain UI mode toggle, not a
 *   money-committing control, so the synthetic-event exception to "always
 *   use a real driving-tool click on priced buttons" applies here same as
 *   documented in higgsfield-image-gen.js for the Location/Prop composer.
 *   Composer then defaults to "Higgsfield Soul Cinema" -- Soul does NOT
 *   accept reference images at all (confirmed elsewhere in this repo). Must
 *   explicitly reselect "GPT Image 2" from the model dropdown before
 *   attaching any reference image.
 */
