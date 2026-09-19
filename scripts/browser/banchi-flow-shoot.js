// Replay notes for shooting a batch of Omni 1.1 Flash / องค์ประกอบ shots in
// Google Flow project "AI Film" (flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39).
// Written for task-083d64b5 (banchi Act1 shot-06/24 + Act2 shot-35/36).
//
// This is a claude-in-chrome playbook (javascript_tool + find + computer),
// not a standalone node/puppeteer script — Flow requires a real Google
// session cookie in the operator's own Chrome, so there is nothing to run
// headless. Follow the steps below verbatim; call out any place the DOM has
// visibly changed since 2026-09-19.
//
// ── Lessons this run paid for ──────────────────────────────────────────────
// 1. USE A FRESH TAB PER SHOOTING SESSION. A tab that has opened several
//    /edit/<id> pages and navigated back to the project root can silently
//    degrade: computer.screenshot starts timing out ("renderer may be frozen
//    or unresponsive") and computer.left_click stops actually focusing/
//    activating elements (document.activeElement stays BODY even though
//    elementFromPoint confirms the click landed on the right node). No error
//    is ever thrown. If clicks stop registering, don't fight it — open a new
//    tab (tab_registry.py release/claim, since the tab guard caps 1/task) and
//    re-navigate. It is not a Flow bug, it reproduced across two different
//    Flow pages in the same tab.
// 2. THE MAIN LIBRARY GRID ("สื่อทั้งหมด", no search applied) does NOT
//    navigate to /edit/<id> on a single click reliably in this build — it
//    just shows a hover toolbar (heart/rotate/⋮). Use a real DOUBLE-click on
//    the thumbnail to open the editor. (Earlier reports describing a single
//    click working were on a *search-filtered* result grid, a different
//    component.)
// 3. The top-bar search box (aria-label="ค้นหา") did not reliably filter by
//    typed dialogue text this run — typing into it after clicking at a
//    screenshot-derived coordinate sometimes lands on the WRONG input (the
//    project-title field at x≈68). Locate it by
//    `document.querySelector('input[aria-label="ค้นหา"]')` and click by that
//    rect, not by re-using an old screenshot's coordinate. Even when it does
//    accept text it did not visibly filter the grid in this run — don't rely
//    on it. Identification is done by the OWN GRID's newest-first order
//    (your shot is always the top-left tile right after you submit) plus the
//    prompt-text verification in step 6, never by search.
// 4. Chip attach behaviour is genuinely bimodal within one session — the
//    FIRST attach right after a fresh `+` open sometimes commits on a single
//    click of the picker row with no visible "add" step; every attach after
//    that opens the preview pane and needs the explicit
//    `เพิ่มไปยังพรอมต์` button click. Screenshot after every attach and act on
//    what you see, don't assume either path.
// 5. A stray click on a picker row can bind the WRONG asset (e.g. a leftover
//    video-ingredient chip from a previous shot). Always read back
//    `document.querySelectorAll('img[alt="รูปภาพองค์ประกอบตัวละคร"], img[alt="รูปภาพองค์ประกอบวิดีโอ"]')`
//    and check the COUNT and the src TAIL (last ~15 chars, stable per asset)
//    against what you expect before typing the prompt. If the count or the
//    tails are wrong, click the composer's own "x" (top-right of the chip
//    row) to clear everything and start the attach sequence over — cheaper
//    than trying to remove one bad chip.
// 6. IDENTIFY A CLIP BY ITS PROMPT, NEVER BY THUMBNAIL/TITLE, before
//    downloading — this is also in the google-flow-ops skill, restated here
//    because it is the step that actually prevents filing the wrong shot:
//      document.querySelectorAll('*') text match on a distinctive Thai line
//      from THIS shot's own dialogue → confirm the ancestor's full text also
//      starts with the right `Use <IMAGE_REF_0> as the character reference
//      for <handle>` opening.
// 7. Voice is bound to the CHARACTER, not typed per shot. Before firing any
//    shot with a disputed-voice character, open its row in the ingredient
//    picker and read the preview card's voice line (e.g. "Umbriel
//    @lender_cherd") — it is a live fact, not something to trust from a
//    ledger or a script file. Report a mismatch; never rebind it yourself.
//
// ── Per-shot sequence ───────────────────────────────────────────────────────
// 0. ONE TIME per tab: mute script (paste after every navigate):
`
(() => { const mute = el => { el.muted = true; el.volume = 0; };
  const all = () => document.querySelectorAll('video,audio');
  all().forEach(mute);
  document.addEventListener('play', e => mute(e.target), true);
  new MutationObserver(() => all().forEach(mute)).observe(document.documentElement, { childList: true, subtree: true });
})()
`;
// 1. Navigate to the project URL (root, no /edit/).
// 2. find() "add ingredient plus button in prompt composer" -> click it.
//    (Fallback coordinate on a 1512x792 screenshot: ~(469, 723-731) —
//    the composer's own row shifts a few px depending on whether a shot is
//    mid-render above it, so prefer the find() ref when it resolves.)
// 3. For each chip in ATTACH order: screenshot the open picker, locate the
//    @handle row (it's sorted "recently used" first, not alphabetically —
//    read the row, don't assume position), click it, screenshot the preview
//    pane and confirm the character/location image + (for a person) the
//    voice line, then click "เพิ่มไปยังพรอมต์" (or notice it already
//    auto-attached — see lesson 4).
// 4. Read back the chip count + src tails (lesson 5) before typing anything.
// 5. Open composer settings pill (find "settings trigger button showing ...")
//    -> click it -> find the "<N> วินาที" radio matching the shot's own
//    heading -> click it -> click the pill again to close the panel.
//    Model/mode/aspect/resolution/quantity default correctly to Omni 1.1
//    Flash / องค์ประกอบ / 9:16 / 720p / x1 on this project; verify, don't
//    assume, by reading the pill's textContent.
// 6. Click the prompt box at a coordinate around (750, 675-683) — NOT via
//    find()+ref, which resolved to unfocusable elements this run — then
//    verify `document.activeElement` is a `contenteditable="true"` DIV
//    before typing. If it's still BODY, click again 5-10px lower/higher.
// 7. Insert the prompt with `document.execCommand('insertText', false, TEXT)`
//    in the SAME javascript_tool call as nothing else (no intervening click),
//    immediately after confirming focus. Read back innerText length + first
//    ~50 / last ~40 chars to confirm the whole prompt landed byte-for-byte.
//    Do NOT use the `computer.type` action for a multi-paragraph prompt —
//    the literal blank-line newlines it sends can misfire on this composer
//    (observed once: it silently navigated to an unrelated existing asset's
//    edit page instead of typing anything).
// 8. Re-read chip count + settings pill one more time (lesson: an open
//    settings panel or a picker close can occasionally drop a chip).
// 9. find() "submit button เริ่มสร้าง" -> click it. Confirm via JS
//    that the chip row emptied and the editable's innerText collapsed to
//    length 1 (placeholder) — that's the tell the submit actually fired.
// 10. To grab a finished clip: from the project root (double-click, lesson
//     2) or straight after a submit (the freshly generated tile sits at
//     grid position 0, top-left), open the tile, verify by prompt text
//     (lesson 6), then find() "download button for this clip" -> click ->
//     find() "720p resolution menu item" (or whatever matches the shot's
//     own render resolution) -> click -> wait ~8s -> check `ls -lt
//     ~/Downloads` for the new file (Flow names it descriptively, e.g.
//     `Man_counting_money_in_bedroom_<timestamp>.mp4`).
// 11. Append `<shot>\t<exact filename>` to the deliverable tsv immediately,
//     not batched to the end.
//
// ── Fragile selectors to watch on the next run ─────────────────────────────
// - `[aria-label="ทริกเกอร์การตั้งค่า"]` — the composer settings pill.
// - `img[alt="รูปภาพองค์ประกอบตัวละคร"]` / `img[alt="รูปภาพองค์ประกอบวิดีโอ"]`
//   — chip thumbnails inside the composer (both alt strings appear; a
//   character AND a tagged location both use the ตัวละคร alt).
// - `[contenteditable="true"]` — the one true prompt box; there is also an
//   unrelated `input[type=text]` for the project title ("AI Film") that a
//   naive selector can grab instead.
