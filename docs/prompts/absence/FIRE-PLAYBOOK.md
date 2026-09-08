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
`extreme foreground|very front|floating|toward the mark|backs to the room|(crack|mark|star|plaque)[^.]{0,30}nearest|nearest[^.]{0,30}(crack|mark|star|plaque)`
→ 0. Mismatch → STOP and report; never fire from a stale sheet.

NARROWED 2026-09-08, after a bare `nearest` produced three false positives in one
night and no true positive on record. It stopped S15a-2 before firing on "at the
frame edge nearest their masters" (where three bodyguards stand), it fired again on
the SC5 rewrite an hour later, and it sits on two legitimate lines in S2R-B ("DUPE,
nearest the camera"). The gate exists to catch the MARK being floated up near the
lens instead of sitting on the wall at its stated size, so `nearest` is now scoped
to the mark and its synonyms. Everything the gate was built to catch it still
catches: "the crack floats nearest the lens" matches, ordinary blocking prose does
not. Verified 0 across all 43 sheets at the time of the change.

An operator who hits a mismatch STILL stops and reports — do not adjudicate a gate
hit yourself, even one that looks obviously positional. That call is the CTO's, and
S15a-2's operator was right to stop.

- RUN EVERY §0 GATE ON FLATTENED TEXT. Pipe the paste block through `tr '\n' ' '`
  before grepping. A phrase that wraps at a line break is invisible to a
  single-line grep: on 2026-09-08 alone it hid "two gold front teeth", "the
  registrar in his black suit" and "the nearest person to / the crack" from the
  CTO's own gate, and in each case a worker's flattened grep found it. The
  flattened form:
  `awk '/PASTE FROM HERE/{p=1;next} /PASTE STOPS HERE/{p=0} p' <sheet> | tr '\n' ' ' | grep -oiE '.{0,60}(<pattern>).{0,60}'`
  and read each hit in context — the gate is a prompt to look, not a verdict.

## 0b · After editing a sheet, grep the paste block for the OPPOSITE of what you just wrote

A prompt describes an object ONCE. The way that rule actually gets broken is not by
writing a second description on purpose — it is by adding a new positive instruction
and leaving an old negative in place that contradicts it. Twice on 2026-09-08 that
cost a whole take.

- S2G take 3: canon rule 6 was added asking for lines "solid and heavy like ink", and
  four lines below it the same block still said "no thick heavy arms". The model split
  the difference and rendered a solid core with thin tapering arms — worse than the
  take before it.
- S2G takes 2 and 3: the brass plaque was banned from the shot while being named four
  times inside the same block, including as the size anchor ("no wider than the plaque
  beneath it"). It appeared in both takes.

So after every sheet edit, before committing, grep the PASTE BLOCK for the antonyms
and for the noun you just banned:

    blk() { awk '/PASTE FROM HERE/{p=1;next} /PASTE STOPS HERE/{p=0} p' "$1"; }
    blk <sheet> | grep -inE 'thin|thick|heavy|hairline|fine|solid'   # weight words
    blk <sheet> | grep -ic '<the noun you just banned>'              # expect 0

If a banned object still appears anywhere in the block, delete every mention, including
the one in the negatives — naming a thing in a prohibition is what puts it on screen.
Replace the ban with a positive statement of what occupies that place instead.

## 1 · Browser
- A DISABLED GENERATE IS USUALLY THE TAB, NOT THE PREVIZ SERVICE (measured 2026-09-07 18:15). Two tabs sat with Generate disabled for 20-40 min after attaching a video reference, and one stayed disabled even after the video tile was removed — tab-local state, not the eligibility check. A FRESH tab with the same 7 chips and the same library previz tile had Generate ENABLED within a minute. Order of moves: innerWidth (>= 1280) → hover the button for its reason → if still disabled with all references in place, close the tab and rebuild in ONE fresh tab before ever blaming the previz or firing bare.
- WINDOW WIDTH TRAP (2026-09-07 17:35): a Chrome window that is 1440 px wide LOOKS fine but the extension side panel eats ~300 px, so window.innerWidth lands near 1140 and Higgsfield silently switches to its mobile layout — Generate DISABLED, freeGens undefined, and it looks exactly like a stuck previz check. Measured 17:40: the S2R-JC tab read innerWidth 1440 with the window at 1440, so on this Mac the side panel does NOT shrink innerWidth and 1440 is safe; the trap only bites when innerWidth itself is under 1280. The CTO's OS guard now fires only under 1300 px: macOS keeps clamping the off-screen window back to 1440, and re-widening every 90 s re-lays out pages that operators have staged, for no benefit when 1440 already clears 1280. Operator rule: a DISABLED Generate → read window.innerWidth FIRST; under 1280 → wait 60 s for the guard, re-read, then continue.
- RENDER TIME IS A MEASUREMENT, NOT A CONSTANT (2026-09-07 16:15): the skill's 35-40 min norm and 90-min cancel line come from earlier days; today every render — Unlimited and credit lane alike (SC1 13:18→~15:10, SC2 13:44→~15:10) — were only DISCOVERED at ~15:10 — the operator was busy with plates, so 85-110 min was discovery time, not render time; SC3 (credit lane) fired 16:15 and landed 16:37, 22 min. Meanwhile two Unlimited renders in a row sat in "Processing" 95+ and 117+ min — so on 2026-09-07 the CREDIT lane was fast and the UNLIMITED lane was the one stalling. Before cancelling a long render, compare it with the OTHER renders fired the same day; cancel only when it is an outlier against today's own times or shows an error. S2S-B t1 was cancelled at 95 min this afternoon on the old line and probably would have landed.
- TWO Higgsfield tabs at most on this Mac (measured 2026-09-07 14:36: three operator tabs → load 13-15 on 8 cores, swap 2.5 GB, every tab 'renderer stuck' / 'input desync' / composer vanishing; closing one tab → load 7, Chrome CPU 3%). The CTO pauses the third operator; if you are told to PAUSE, close your tab and make no browser calls until RESUME.
- THE "UNLIMITED PAUSED" BANNER IS NOT THE LANE (measured 2026-09-08 00:36). The
  subscription page carries a payment-failed notice saying Unlimited generations are
  paused, and it is misleading: in the composer the Unlimited toggle was present,
  enabled and clickable, and with it ON the Generate button priced the render at
  UNLIMITED / struck-through / 0. S2S-B had already fired free at 23:34 the same
  night and rendered in 46 minutes. Never refuse to fire on the strength of that
  banner — read the toggle and the button price instead, and fire when the button
  shows zero digits. The button is the authority on what you are about to spend.
- NEVER END YOUR TURN WHILE A RENDER IS UNRESOLVED (HARD, measured 2026-09-08
  01:16). S2G's operator fired at 00:48, checked once at 01:11, wrote itself
  "check again in 10 min", and ended its turn — with that reminder still sitting
  UNSENT in its own input line. Nothing was scheduled. The process stayed alive at
  idle, the tmux session was healthy, the task read `in_progress`, and every
  liveness check passed, so the failure is invisible from outside: the render
  would have landed and sat unnoticed until morning. A self-addressed note is not
  a timer. Stay inside ONE turn: check the grid, and while it is still Processing,
  start a background wait and check again, repeatedly, until the card is finished
  or you hit a real error. The operator is the first line of defence.

  HOW THE CTO TELLS ASLEEP FROM WAITING, in one line of the pane's status bar
  (measured 2026-09-08 01:59, with both cases on screen minutes apart). A finished
  turn prints `· done H:MM`. If that same line ALSO says `N shell still running`, a
  background wait is live and the harness re-invokes the worker when it exits — that
  is the correct pattern and needs no action, even with an unsent nudge sitting in
  the input line, which is what S15a-1 looked like. If `· done H:MM` appears with NO
  shell running, nothing is scheduled and the worker is asleep — S2G looked exactly
  like that at 01:11 and its render would have sat there until morning. The stall
  watch alerts on that combination within three minutes rather than waiting half an
  hour for a pane to look quiet.
- DO NOT ADD A WORSE TAKE UNDER A NAME THAT ALREADY HOLDS A BETTER ONE (HARD, 2026-09-08
  06:52; the reason below was CORRECTED at 07:20 after actually listing the folder).
  The upload script does NOT overwrite — it creates a NEW Drive file with the same
  name. So a second upload never destroys the first; it leaves two files with identical
  names, and the editor cannot tell which one passed. As of 07:20 that had already
  happened five times: S15a2-RoomDecides-Fix1.MP4 exists three times, and
  S15a1-Shield-Fix1.MP4, S2Eb-Fix1.MP4, S2G-Fix1.MP4 and S2S-Fix1.MP4 twice each.
  So before uploading, compare your take against what the sheet's TAKE LOG records for
  the take already filed. If yours is worse on any criterion that one passed, DO NOT
  UPLOAD: report the comparison to the CTO and leave Drive alone. EQUAL IS ALSO A
  REASON NOT TO UPLOAD — if both takes fail the same criterion, the new file adds
  nothing but a second clip the editor cannot tell from the first. Upload only when
  your take is BETTER on something. Nothing is lost by
  waiting — every take stays in ~/Downloads under its hf_ name and the take log says
  which is which.
  I originally wrote this rule believing take 3 had destroyed take 2. It had not. The
  rule stands, the reason is duplicate names rather than lost footage, and no clip has
  ever been lost on Drive.
- THE DRIVE FILENAME IS THE SCENE NAME AND NOTHING ELSE (HARD, 2026-09-08). Every
  clip goes to All Scene/Fix-2/ named for its scene — S2G-Fix1.MP4,
  S15a1-Shield-Fix1.MP4, S2S-B-Fix1.MP4 — and that is true of failures too. Do NOT
  append a verdict, a defect list, or anything else to the name; S2G take 2 was
  uploaded as "S2G-Fix1-FLAGGED-plaque-and-mark.mp4" on a "house convention" that
  does not exist. The verdict lives in the TAKE LOG, the report and the logs.txt
  line, never in the filename — the editor finds a clip by its scene, and a name
  that changes with the verdict cannot be found or overwritten by the next take.
  Inventing a naming pattern also breaks the gdrive-filing skill, which forbids new
  structure without the CEO's approval. If you have already uploaded under a wrong
  name, report the exact name and file id and change NOTHING: renaming and deleting
  on Drive are the CTO's to authorise, with the CEO's say-so.
- A POLL IS NOT A REPORT. While a render is in flight you send NOTHING — not "still
  rendering", not "waiting on a 5-min chunk", not "polling ~20 min". Three operators
  did that tonight, several times each, and every one of those messages arrives in the
  CTO's context as an interruption that says nothing the CTO cannot already see from
  the pane. Report on a STATE CHANGE only: it fired, it landed, it was rejected, you
  are blocked, two instructions conflict. A long silence while you work is correct and
  expected — the CTO watches your process directly and learns you died faster than you
  could tell it.
- NEVER PUT alert(), confirm() OR prompt() IN A JS SNIPPET — not even in your own
  throwaway test (HARD, 2026-09-08 07:05, after it happened). A JS modal blocks the
  extension for that tab and there is no extension call that can dismiss it. Use
  console.log and read it back with read_console_messages.
  RECOVERY, and it does NOT need a human: the modal blocks that ONE tab, not the
  browser — every other tab still answers, which is why the frozen tab's title is
  still readable. Close the frozen tab with tabs_close addressed BY TAB ID (never by
  clicking into it, never with computer-use); Chrome discards a pending dialog when
  the tab closes. Release the registry claim, claim ONE fresh tab, rebuild the
  composer. Only if tabs_close itself errors do you stop and report. Nothing is lost
  as long as no Generate click was made.
- HOW TO TEST WHETHER A CUT IS REAL — SWEEP, NEVER SAMPLE ONE PAIR (2026-09-08).
  Seedance renders continuous seconds and places a cut NEAR the nominal timestamp, not
  on it, so extracting one frame either side of the written time can straddle the cut
  and report a dead cut that is actually there. That happened on S14b: sampling
  5.4s/5.6s around a nominal 5.5s cut gave 1.35 against a 1.53 baseline, reading as
  failed, while a sweep showed the real boundary at ~5.4s scoring 51.17 against a
  median step of 2.39 — 21x. A false fail costs a re-fire, so use the sweep:

    for t in $(seq 0.2 0.2 <duration>); do ffmpeg -v error -ss $t -i CLIP \
        -frames:v 1 scan/f$t.png -y; done
    # then: greyscale mean-abs-diff between consecutive frames,
    # median = normal motion; anything above ~3x median is a real boundary

  Report the boundary TIMESTAMPS you find, not a pass/fail against the nominal time.
  A clip whose sweep shows no step above ~3x median has no working cut at all — that
  is the S2R-JC failure, where every "cut" scored below the within-shot baseline.
  A snap zoom also shows as a cluster of high steps; that is expected where the sheet
  asks for one, and it is distinguishable because it spans several consecutive steps
  rather than one.
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
- A LONG RENDER IS NOT A DEAD RENDER, AND CANCELLING IS WHY WE CANNOT TELL.
  The only long card ever allowed to finish was S2I take 1: 185 minutes, then it
  landed CLEAN — 20.04s, 17.5 MB, green "Ready", filed as S2I-Fix1.MP4
  (docs/reports/absence-wave-20260907-s2i-t1.md). Every other long card on this
  lane (95, 100, 152 min on 2026-09-07; S14 at 154 min on 2026-09-08) was
  CANCELLED before it finished, so not one of them is evidence of failure — the
  cancel is precisely what destroyed the evidence. As of 2026-09-08 there is NO
  observed case of a card on this lane failing on its own, and one clear case of
  one landing at 185 minutes.
  So the default is TO LET IT RUN. Report at 60 minutes because the number is
  useful, but do not read it as "the lane is stalled" — that inference is exactly
  backwards, and it cost the CTO a 154-minute S14 render on 2026-09-08 that was
  plausibly ~30 minutes from landing.
  Cancel ONLY as a throughput decision the CTO makes explicitly with the
  arithmetic stated: clips remaining x expected minutes against the hours left.
  Never cancel on the theory that the card is dead.
- EVERY DURATION IS FREE ON UNLIMITED, INCLUDING 20s (measured 2026-09-08 12:13
  on S14). The button read `UNLIMITED · ~~140~~ · 0` at 20s — the strike-through
  number rises with duration and the charged number stays 0. So a long take is
  not a credit decision: pick the duration the scene needs. On the CREDIT lane
  the same fire would be 140, which is why a non-zero digit is always a STOP.
- PROMPT: paste ONLY the block between "PASTE FROM HERE" and "PASTE STOPS
  HERE" with the base64 synthetic paste, then the End→space→Backspace tap so
  NEVER HAND-TRANSCRIBE THE BASE64 (S15b t1, 2026-09-08, 25 minutes lost): an
  ~12 KB base64 string retyped into a javascript_tool call corrupted a single
  byte twice ("navy" → "njöy"). Compute the paste block's sha256 in Bash from
  the sheet, split the base64 into length-verified chunks, assemble them in the
  page, decode, and compare the hash BEFORE dispatching the ClipboardEvent. The
  hash match is the gate; a length match is not.
  Lexical binds the chips (worked on S2L t6, S2K t2, S2M t4). Chip gate:
  `python3 scripts/prompt-lint.py --chips <sheet>` gives the unique names; the
  composer must show them lime:
  `[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@')).length`
  — count unique names, 0 red/unresolved '@'. If the paste leaves names
  unresolved, bind each by typing @ and selecting (slow — say so).
- THREE ELEMENTS ARE FLAGGED AND MAKE HIGGSFIELD REFUSE THE GENERATE CLICK
  OUTRIGHT (warning triangle on the tile): `project_valder_char_villagers_poor`,
  `prop_croc_bag`, `prop_car`. They are not "risky", they are a hard stop — the
  fire never starts. Carry what they held as PROSE in the paste block instead,
  and never re-add the chip "to be safe".
  MATCH THEM ON A WORD BOUNDARY. `prop_car` is flagged; **`prop_cart_b` is a
  DIFFERENT, UNFLAGGED Element** — it is Dupe's cart with the painting on it,
  and it is load-bearing in S15b / S15c / S16 (the grandmother is buying what
  is on that cart). A grep for `prop_car` with no boundary reports it as
  flagged and would delete the scene's subject. Use
  `grep -E 'project_valder_char_villagers_poor|prop_croc_bag|prop_car([^t]|$)'`
  (CTO, 2026-09-08 — caught this on my own gate before it reached a sheet).
- A SHEET THAT SAYS "the reference video" REQUIRES ITS PREVIZ (S2S t2, 2026-09-08):
  before the browser, `grep -c 'reference video' <sheet>`; if > 0 the previz file
  named in the sheet's NOTES (e.g. docs/S2S-Render.MP4) MUST be attached and its
  byte count verified, whatever the brief says. Without it the model has no
  distance cue and puts the named subject in the near foreground.
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
Drive All Scene/Fix-2/ under the brief's filename with
`scripts/gdrive-bridge/upload_fix1.py` (appends the logs.txt line; its default
destination is Fix-2 since 2026-09-08). Whatever the verdict, it is filed.
- FIX-2 IS THE SECOND EDIT AND FIX-1 IS CLOSED (CEO 2026-09-08 18:30: "ฉากที่สร้าง
  ในวันนี้จนถึงจบโปรเจคใส่ Fix-2 … เป็นการ Edit ครั้งที่ 2"). Every clip generated
  from 2026-09-08 onward files to Fix-2 (id 1rkCQ5SSZeOvyX-0UZXe3OvBtFhObHrkw).
  The filename keeps its -Fix1 suffix — that is the scene's name, not the folder.
  A brief that still says Fix-1 is stale; Fix-2 wins.

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
OBSERVED 2026-09-08 20:55 — TWO UNLIMITED RENDERS RAN AT ONCE. S2S fired 20:22
and was still spinning when S2S-B's retry was ACCEPTED (asset 727→728, toast,
card) at ~20:55 after ~30 min of refusals. So the refusal appears to gate
QUEUED generations, not rendering ones: once the first card leaves the queue
and is actually rendering, a second Unlimited fire can queue behind it. One
observation, not a rule yet — keep pipelining exactly as below (the retry
loop costs nothing) and log the next time it happens or fails to.
The Unlimited lane renders ONE generation at a time — a second fire is refused
with the toast "You can generate 1 unlimited video, image & audio generation at
a time" (not queued). So the NEXT scene's worker should build its composer
(fields, paste, chips, previz, Unlimited zoom) WHILE the previous render runs,
then retry Generate every 5 minutes until the slot frees. The refusal costs
nothing; the slot idles for zero minutes.
