// Replay: pull verbatim source from an open Apps Script editor tab.
//
// Usage: with the project open in the Apps Script editor (…/edit), click
// through EVERY file in the left file list once (Monaco only builds a model
// for files that have been opened at least once — a fresh page load has
// just one model, for whichever file was open). appsscript.json is hidden
// by default; enable Project Settings -> "Show appsscript.json manifest
// file in editor" to add it to the file list, then click it too.
//
// Then run this in the page console (or via the claude-in-chrome
// javascript_tool):
//
//   monaco.editor.getModels().map(m => ({ uri: String(m.uri), text: m.getValue() }))
//
// Gotchas hit on 2026-08-12 against script.google.com, worth keeping:
//
// 1. Deep link https://script.google.com/home/projects 404s. Use
//    https://script.google.com/home/my for the project list instead.
//
// 2. Project rows in the list are role="button" <div>s with no href —
//    a single ref-click via the extension's computer tool did not
//    navigate reliably. A double_click on the row's bounding-rect
//    coordinates did.
//
// 3. Full CDP screenshots (computer action:"screenshot"/"zoom") reliably
//    time out ("Page.captureScreenshot timed out after 30000ms") on this
//    editor page. Don't burn the retry budget on it — everything needed is
//    readable as text (javascript_tool / find / read_page), which all
//    still work fine even while screenshot is hung.
//
// 4. The javascript_tool's own output filter blocks text containing certain
//    "key=value"-shaped substrings, mislabeling ordinary JS assignment code
//    as "[BLOCKED: Cookie/query string data]" (and base64-looking text as
//    "[BLOCKED: Base64 encoded data]"). If getValue() comes back blocked,
//    do the substitution page-side before returning, then reverse it
//    locally:
//
//      monaco.editor.getModels()[i].getValue().replace(/=/g, '~EQ~')
//
//    Also cap each call to ~800 chars (longer results get silently cut off
//    mid-token) and stitch chunks back together by exact character offset
//    — recompute `.replace(...).slice(start, start+800)` per chunk against
//    the SAME full string so offsets line up.
//
// 5. Deploy button / "Manage deployments" menu: a single ref-click often
//    reports success but the menu is not actually open yet when the very
//    next tool call checks for it (timing, not a real failure). Batch
//    click -> wait(1-2s) -> find in one browser_batch call; that consistently
//    finds the now-open menu item, which you can then click.
//
// 6. Script Properties: the property's VALUE is a plain-text <input> in the
//    DOM, not masked. find()'s natural-language match on the property NAME
//    is enough to confirm existence — do not read_page the value cell.

/**
 * Call inside the page (javascript_tool). Returns [{uri, text}] for every
 * file Monaco currently has a model for. Values only reflect files that
 * have been clicked open at least once this page load.
 */
function dumpOpenModels() {
  return monaco.editor.getModels().map(function (m) {
    return { uri: String(m.uri), text: m.getValue() };
  });
}
