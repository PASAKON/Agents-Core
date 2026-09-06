// Replay script for the Grok Imagine Thai-lipsync evidence run (task-7c61848e).
// NOT fully automatable end-to-end: the account hit a free-tier video cap after
// exactly ONE generation on 2026-09-06 (Library showed 0 prior videos today
// before the run, and the SuperGrok paywall appeared on generation #2), so a
// script that fires N clips back to back will just get walled on #2. Use this
// as a step-by-step driver, running it once per day / once per available slot,
// not as a batch job.
//
// Run with the claude-in-chrome MCP tools driving a tab at this URL, or adapt
// the selectors below into a Playwright/Puppeteer script if a persistent
// Grok session cookie is ever exported for headless use.

const STEPS = {
  url: 'https://grok.com/imagine',

  // 1. Sign-in check: if the composer area still shows "Sign in / Sign up"
  //    text after a hard reload + a genuinely fresh tab (not just this tab
  //    reloaded), STOP - do not sign in, file a blocker.
  signedInCheck: () => {
    // get_page_text on <main>; absence of "Sign in" / "Sign up" strings and
    // presence of "New project" means signed in.
  },

  // 2. Cookie banner (Thai locale seen 2026-09-06): click "ปฏิเสธทั้งหมด"
  //    ("Reject all"). Selector: find("Reject all cookies button") -> a
  //    <button> containing exactly that Thai text. Must click via its ref,
  //    NOT by fixed coordinate - the banner overlaps template cards below it
  //    and a coordinate click can land on a card instead (happened once this
  //    run, navigated to /imagine/template/imagine-background-removal).

  // 3. Switch composer to Video mode: a radiogroup labelled "Generation mode"
  //    with radio buttons "Image" / "Video" / "Agent". Click the one whose
  //    accessible name is exactly "Video" (find query:
  //    "Video mode toggle radio button in composer toolbar").

  // 4a. IMAGE-TO-VIDEO clip: locate the file input via find("attach/upload
  //     image file input"), which returns a <input type="file"> element
  //     (NOT the "Upload" button next to it - that just opens the OS picker,
  //     unusable from automation). Call file_upload with that ref and the
  //     absolute path to the reference image. Confirm attach via JS:
  //       document.querySelectorAll('img[src^="blob:"]').length > 0
  //     A 46x46 blob thumbnail appears above the composer on success.

  // 4b. TEXT-ONLY clip: do NOT touch the file input. On a genuinely fresh
  //     /imagine page load there is no attached image and no "Remove image"
  //     button - verified via JS before typing. If a previous image is still
  //     attached, click the button with aria-label "Remove image" first.

  // 5. Click the prompt textarea (find: "prompt textarea for imagine
  //    composer" - a ProseMirror contenteditable div, not a real <textarea>)
  //    then use the `type` action to enter the prompt.
  //    GOTCHA (hit twice this run): the FIRST `type` call into a freshly
  //    re-rendered composer can silently drop all but the first character
  //    (contenteditable re-render race). ALWAYS verify immediately after
  //    typing:
  //      document.querySelector('[contenteditable="true"]').innerText
  //    and compare byte-for-byte against the intended prompt (Thai included).
  //    If it doesn't match: click the field, select-all is unreliable here
  //    too (cmd+a followed by Delete left stale content in one case) - use
  //    triple_click on the text to select the paragraph, Backspace, click
  //    again, then retype. Re-verify.

  // 6. Settings sanity before firing (all were already correct defaults on
  //    2026-09-06, but re-verify every run - see the skill's "re-verify at
  //    the moment you commit" rule):
  //      - duration pill "6s" should look selected (lighter background)
  //      - resolution pill "480p" should look selected
  //      - the button with aria-label "Video audio" should have
  //        aria-pressed="true" (audio ON)
  //    None of these expose a clean aria-checked/data-state on this build;
  //    the visual "which pill is light vs dark" check plus the audio
  //    button's aria-pressed are the only reliable reads found.

  // 7. Click the button with aria-label "Submit" (icon-only up-arrow, no
  //    visible price/credit text was found anywhere on the page pre- or
  //    post-generation on this account).

  // 8. FIRST-RUN-ONLY GOTCHA: the very first video generation ever on a
  //    fresh account triggers two sequential modal dialogs AFTER the first
  //    Submit click and BEFORE generation actually starts:
  //      a) "Please confirm your age" / prefilled birth year / "Continue"
  //      b) "Birth Year: <year> - ... won't be able to change it later" /
  //         "Save"
  //    Submit must be clicked AGAIN after both modals clear - the original
  //    click does not queue, it's consumed by opening modal (a). This is a
  //    one-time-per-account gate; expect it to be absent on later runs.
  //    Treat it as a human decision point the first time it's seen, not
  //    something to auto-click through - confirm with the requester before
  //    proceeding, even though on this build it turned out to be mandatory
  //    infrastructure (not a ToS/OAuth grab) prefilled with the account's
  //    own true birth year.

  // 9. Poll for completion: JS check `!!document.querySelector('video')` and
  //    absence of the "Generating NN%" text in document.body.innerText.
  //    Took under 15s for a 6s/480p clip on 2026-09-06.

  // 10. Download: find("download icon button for the generated video") on
  //     the result page -> click. Lands in ~/Downloads as
  //     grok-video-<conversationId>.mp4. Copy into the deliverable folder
  //     immediately - filename carries no clip-identifying info.

  // 11. FREE-TIER CAP (the load-bearing finding of this run): on
  //     2026-09-06 this account's Library showed ZERO prior Grok Imagine
  //     videos before this run, and clicking Submit for the SECOND
  //     generation redirected to https://grok.com/imagine#subscribe and
  //     rendered a SuperGrok pricing modal (Lite $10/mo, SuperGrok $30/mo,
  //     Plus $100/mo, Heavy $300/mo) instead of generating. That means the
  //     effective free cap that day was ONE video per 24h on this account,
  //     not the five assumed in the task brief. NEVER click any button
  //     inside that modal (all of them read "Upgrade to ..."). Close it via
  //     the "x" in the top-right corner (fixed coordinate top-right ~24px
  //     inset worked; prefer finding the close button by ref if repeating).
  //     If this modal appears, STOP - do not retry generation, file a
  //     blocker/note, and report exactly which generation number triggered
  //     it.
};

module.exports = STEPS;
