# FIRE PLAYBOOK — «Sorry, Sir» Unlimited fires (browser_operator)

Every fire brief says "follow FIRE-PLAYBOOK.md" and gives only: scene, sheet,
duration, chip count, previz file, Drive filename, review items. Everything
below applies to every fire. Written 2026-09-06 23:05 from the day's passes.

PROJECT: https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3 ONLY
("The Valder Collection No.7"). UNLIMITED video only — zoom the button, ZERO
digits. ZERO PAID ACTIONS: nothing priced above a struck-through zero, no
image generation, never click a paid control twice, never touch the CEO's
cards (they start `SEEDANCE 2.5 CREDIT`), leave the NSFW-rejected S2M take-3
card alone. Seedance 2.5 Unlimited grant expires Sep 9 — and the plan flips to
Plus on Sep 7 at 18:18 ICT, after which the grant may stop: every fire before
then is free, so never let the slot idle.

## 0 · Worktree
`git merge main` first. Run the sheet's gate greps on the PASTE BLOCK ONLY:
`awk '/PASTE FROM HERE/{p=1;next} /PASTE STOPS HERE/{p=0} p' <sheet>` piped to
grep — the notes above/below the block are never pasted and may quote banned
words. Expect: `NO WIDER THAN THE RED DOOR` → 1 on wall-POV sheets;
`nearest|extreme foreground|very front|floating|toward the mark|backs to the room`
→ 0. Mismatch → STOP and report; never fire from a stale sheet.

## 1 · Browser
- WINDOW WIDTH TRAP (2026-09-07 17:35): a Chrome window that is 1440 px wide LOOKS fine but the extension side panel eats ~300 px, so window.innerWidth lands near 1140 and Higgsfield silently switches to its mobile layout — Generate DISABLED, freeGens undefined, and it looks exactly like a stuck previz check. Two operators lost 30+ min to it this afternoon. The CTO's OS guard now re-widens whenever the window is under 2000 px (it was wrongly set at 1400). Operator rule: a DISABLED Generate → read window.innerWidth FIRST; under 1280 → wait 60 s for the guard, re-read, then continue.
- RENDER TIME IS A MEASUREMENT, NOT A CONSTANT (2026-09-07 16:15): the skill's 35-40 min norm and 90-min cancel line come from earlier days; today every render — Unlimited and credit lane alike (SC1 13:18→~15:10, SC2 13:44→~15:10) — were only DISCOVERED at ~15:10 — the operator was busy with plates, so 85-110 min was discovery time, not render time; SC3 (credit lane) fired 16:15 and landed 16:37, 22 min. Meanwhile two Unlimited renders in a row sat in "Processing" 95+ and 117+ min — so on 2026-09-07 the CREDIT lane was fast and the UNLIMITED lane was the one stalling. Before cancelling a long render, compare it with the OTHER renders fired the same day; cancel only when it is an outlier against today's own times or shows an error. S2S-B t1 was cancelled at 95 min this afternoon on the old line and probably would have landed.
- TWO Higgsfield tabs at most on this Mac (measured 2026-09-07 14:36: three operator tabs → load 13-15 on 8 cores, swap 2.5 GB, every tab 'renderer stuck' / 'input desync' / composer vanishing; closing one tab → load 7, Chrome CPU 3%). The CTO pauses the third operator; if you are told to PAUSE, close your tab and make no browser calls until RESUME.
- NEVER quit or restart Chrome (HARD, 2026-09-07): the window is shared with the other operators; a frozen tab → close your own tabs, one fresh tab, else STOP and report. The render lives server-side and survives your tab.
- claude-in-chrome ONLY. NEVER call computer-use (screenshot/click/type/clipboard) or ask
  for Finder / clipboardWrite: the permission dialog it raises blocks the whole pane
  silently — S2I t1 sat 40 minutes on one (2026-09-07 00:15). Paste = javascript_tool
  synthetic ClipboardEvent on the focused contenteditable; if that will not bind, type @.
- Fresh tab, claim it in the tab registry, release it at the end. Never touch,
  reload, resize or close another worker's tab or the window size.
- Maximise (>= 1280) and PROVE it: `({w: window.innerWidth, h: window.innerHeight})`
  — only the readback counts; `resize_window` has lied. Below 1280 = the
  mobile lockup (no Unlimited, Generate disabled) → close the tab, open another.
- WINDOW TOO NARROW AND NOTHING WORKS? (2026-09-07 10:15) `resize_window` lies,
  `window.open` popups are blocked, Cmd+minus zoom is refused by the tool, and
  with only the 13" screen (1440 pt) plus the extension side panel (~300 px)
  the viewport cannot reach 1280. Tell the CTO — the fix is from the OS:
  `osascript -e 'tell application "Google Chrome" to set bounds of window id
  <id> to {-420, 0, 1860, 900}'` (a window wider than the screen is allowed);
  list windows first with `bounds of every window` / `URL of active tab`.
- FIRST ACTION in the composer: close the banner "Credits are running low!
  Over 90% already used" with its own (x). It is an upsell; it returns on every
  reload and covers the Unlimited toggle. Never act on it, never click
  "elsewhere" to dismiss it (that selects an asset card and collapses the composer).
- Video tab (the composer opens in Image mode — switch first, confirm nothing
  fired) → Seedance 2.5 explicitly → 16:9 · 720p · the brief's duration (ARIA
  slider, ArrowRight, never typed) · High · Sound On. Setting the duration
  RESETS Unlimited: toggle Unlimited AFTER the six fields, then zoom the
  button: `UNLIMITED · ~~<price>~~ · 0`. A toggle click that "does nothing"
  hit a cover — `document.elementFromPoint(x,y)`, close the cover by its own
  control, click the real toggle via javascript_tool. The zoomed screenshot is
  the authority; a JS scrape can read a decoy element.
- PROMPT: paste ONLY the block between "PASTE FROM HERE" and "PASTE STOPS
  HERE" with the base64 synthetic paste, then the End→space→Backspace tap so
  Lexical binds the chips (worked on S2L t6, S2K t2, S2M t4). Chip gate:
  `python3 scripts/prompt-lint.py --chips <sheet>` gives the unique names; the
  composer must show them lime:
  `[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@')).length`
  — count unique names, 0 red/unresolved '@'. If the paste leaves names
  unresolved, bind each by typing @ and selecting (slow — say so).
- PREVIZ (if the brief names one): attach via the reference panel's file
  input, verify the platform's reported size equals `ls -l`'s byte count (the
  picker's "Last used" sort shows a stale asset first). readyState 0 /
  "Checking eligibility" on the tile is BENIGN when the byte count matches and
  Generate is enabled — S2H t1 fired that way and rendered (2026-09-07). Fire.
  10-minute cap only when Generate stays DISABLED → remove it and fire without
  it, flagging the take. Removing a stuck tile can leave Generate disabled — a
  reload clears that but resets Unlimited; re-toggle, re-zoom, re-count chips
  (a detach can silently delete an adjacent chip).
- FIRE: Generate is the very last action with nothing in flight. Verify by a
  "Generation started" toast AND a NEW Processing card (spinner, top of the
  grid, visible under the Today + Generated filter). The asset count is only a
  cross-check: READ IT AFTER THE PREVIZ IS ATTACHED — an uploaded reference
  counts as an asset, and S2D t1 waited 70 minutes on a "fire" that was the
  previz upload (2026-09-07 04:12); the CEO may fire on the Credit lane at any
  time, so confirm YOUR card. No toast after 60 s → reload, count cards; only
  if the count did not change, one JS `.click()` on the $0 button, and say so.

## 2 · After the fire
Poll every 5 minutes with a reload (a stale tab lies; if background sleeps get
killed by low memory, poll anyway). Renders took 30-55 min today. Finished
card shows "NSFW / Credits refunded / sensitive content" → screenshot, STOP,
report, do not re-fire. Otherwise: IDENTIFY YOUR CARD FIRST — open its Info panel and match the
Created time to your fire time and the prompt text to your sheet; the top
card is often another worker's clip (S2S t1 filed S2R's clip under S2S's
name, 2026-09-07 09:02). Then download → `md5` it against every mp4 already
in ~/Downloads (a match = wrong card, start over) → ffprobe 1280x720 /
duration → file to
Drive All Scene/Fix-1/ under the brief's filename with
`scripts/gdrive-bridge/upload_fix1.py` (appends the logs.txt line). Whatever
the verdict, it is filed.

## 3 · Checks (frames at 0.5s, 3s, mid, end — `ffmpeg -ss <t> -i <file> -frames:v 1 <png>`, LOOK)
Wall-POV sheets: 0 THE MARK — one small solid-black star-shaped crack over the
far red door, as close to 1x the door as it comes (today's rolls: 1x-3x; a 5x
monster or an arm across a face = FLAGGED), off every face. 0b faces to the
lens, not backs/profiles to the far door. 0c every named character present.
Then the sheet's own REVIEW ORDER. Report PASS/FLAGGED per item with the size
in words and the frame paths. Then STOP — one fire per task.

## 4 · Report
docs/reports/<brief's path> — innerWidth readback, banner closed yes/no, six
fields, price zoom, paste method + chip count, previz yes/no + byte check, fire
time + how verified, render duration, NSFW yes/no, info-icon, Drive filename +
link, verdicts with frame paths, anything odd. Commit, submit_report, STOP.

## 5 · Pipelining (proven 2026-09-07 09:55)
The Unlimited lane renders ONE generation at a time — a second fire is refused
with the toast "You can generate 1 unlimited video, image & audio generation at
a time" (not queued). So the NEXT scene's worker should build its composer
(fields, paste, chips, previz, Unlimited zoom) WHILE the previous render runs,
then retry Generate every 5 minutes until the slot frees. The refusal costs
nothing; the slot idles for zero minutes.
