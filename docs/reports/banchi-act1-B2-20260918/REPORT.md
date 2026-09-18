# «บัญชี» Act 1 — B2 (shots 25–48) — Shoot Report

Operator: MAC Browser Operator (task-f0f67322). Google Flow project "AI Film"
(`e88671f5-9ae8-4946-84a6-8b8e31dc0d39`), same Chrome, same tab group the other
operator (shots 1–24, task-abc83ea2) was using at the same time. **One tab
used throughout** (with one documented exception, see Issues).

## Pre-flight

- Read `.claude/skills/google-flow-ops/SKILL.md` in full before starting.
- Re-read `docs/scripts/banchi-ACT1.md` fresh (not from memory) — confirmed the
  bottom-of-file summary saying shots 39–48 "ยังยิงไม่ได้" (not shootable) was
  **stale**: commit `a88140aa` had already filled @cop_wit's real appearance
  from the generated plate. `python3 tools/shotsheet_lint.py` → **PASS**, 48/48
  shots carry dialogue.
- Confirmed signed in as pass.gob1@gmail.com, ULTRA tier, balance **9,953
  credits** before the first submit.
- Confirmed settings already at the required defaults on load: Omni 1.1 Flash
  · องค์ประกอบ · 9:16 · 720p · 8 วินาที · x1 — verified in the settings panel
  before shot 25 and spot-checked several times through the run; never
  touched Upgrade/Subscribe/Buy credits.

## Shot table — attach, submit, chips, download

All 24 shots (25–48) were fired in numeric order in a single pass. Chips are
listed left-to-right in the order attached, which is the `<IMAGE_REF_N>`
order.

| shot | submit (approx, HH:MM:SS) | chips attached, in order | downloaded |
|---|---|---|---|
| 25 | 16:04:16 | @lung_somchai, @nong_daeng, @noodle_shop | ✅ shot-25.mp4 |
| 26 | 16:05:31 | @nong_daeng, @staircase | ✅ shot-26.mp4 |
| 27 | 16:06:28 | @nong_daeng, @grandma_pranom, @upstairs_bedroom | ❌ **not retrieved** |
| 28 | 16:08:xx | @grandma_pranom, @upstairs_bedroom, @nong_daeng (off-frame, voice only) | ✅ shot-28.mp4 |
| 29 | 16:09:xx | @grandma_pranom, @upstairs_bedroom | ✅ shot-29.mp4 |
| 30 | 16:10:xx | @nong_daeng, @grandma_pranom, @upstairs_bedroom | ❌ **not retrieved** (see Issues) |
| 31 | 16:11:xx | @grandma_pranom, @upstairs_bedroom, @nong_daeng (off-frame, voice only) | ✅ shot-31.mp4 |
| 32 | 16:12:xx | @grandma_pranom, @nong_daeng, @upstairs_bedroom | ✅ shot-32.mp4 |
| 33 | 16:13:xx | @nong_daeng, @grandma_pranom, @upstairs_bedroom | ❌ **not retrieved** |
| 34 | 16:14:xx | @lung_somchai, @noodle_shop | ✅ shot-34.mp4 |
| 35 | 16:15:xx | @lung_somchai, @noodle_shop | ✅ shot-35.mp4 |
| 36 | 16:16:xx | @lung_somchai, @noodle_shop | ✅ shot-36.mp4 (re-read from disk, see CTO letter note) |
| 37 | 16:17:xx | @nong_daeng, @lung_somchai, @noodle_shop | ✅ shot-37.mp4 |
| 38 | 16:19:xx | @nong_daeng, @noodle_shop | ❌ **not retrieved** (see Issues) |
| 39 | 16:21:xx | @cop_wit, @noodle_shop | ✅ shot-39.mp4 |
| 40 | 16:22:xx | @cop_wit, @noodle_shop | ✅ shot-40.mp4 |
| 41 | 16:23:xx | @lung_somchai, @noodle_shop | ✅ shot-41.mp4 |
| 42 | 16:26:xx | @cop_wit, @noodle_shop | ✅ shot-42.mp4 |
| 43 | 16:29:xx | @lung_somchai, @noodle_shop | ✅ shot-43.mp4 |
| 44 | 16:31:xx | @cop_wit, @lung_somchai, @noodle_shop | ✅ shot-44.mp4 |
| 45 | 16:33:xx | @cop_wit, @lung_somchai, @noodle_shop | ✅ shot-45.mp4 |
| 46 | 16:38:xx | @cop_wit, @lung_somchai, @money_fold, @noodle_shop (4th disabled, see Findings) | ❌ **not retrieved** |
| 47 | 16:40:xx | @lung_somchai, @money_fold, @noodle_shop | ✅ shot-47.mp4 |
| 48 | 16:42:xx | @nong_daeng, @lung_somchai, @noodle_shop | ✅ shot-48.mp4 |

**19 of 24 clips downloaded and verified** (`ffprobe`: every file exactly
`duration=8.000000`, 720p, in
`docs/reports/banchi-act1-B2-20260918/clips/shot-NN.mp4`).

**5 clips fired correctly (chips + prompt confirmed before submit, dialogue
verified) but the .mp4 was not retrieved: shots 27, 30, 33, 38, 46.** These
exist in the project and were paid for — they are not missing generations,
they are missing *downloads*. See Issues for why, and what the next operator
should do.

Every chip attach, for every one of the 24 shots, was verified by **zooming
into the chip thumbnail row** (or, once confirmed safe, by the picker's own
exact-string search returning a single match) — never by row label or type
alone, per the skill's HARD rule. `@noodle_shop` vs `@noodle_shop_thriving`
was checked explicitly every single time `@noodle_shop` was attached (both
exist in this project).

## Credit ledger

The account's Flow-credit balance is **shared** with the other operator
(task-abc83ea2, shots 1–24), running concurrently in the same tab group. The
deltas below are combined spend, not mine alone.

| checkpoint | balance | delta | my own running total (12cr/shot estimate) |
|---|---|---|---|
| before shot 25 | 9,953 | — | 0 |
| after shot 32 (8 fired) | 9,761 | −192 | 96 |
| after shot 41 (17 fired) | 9,557 | −204 | 204 |
| after shot 48 (all 24 fired) | 9,413 | −540 total | 288 |

My own spend never got close to the 340-credit cap — final estimate **288
credits for 24 submits** (all 720p/Omni 1.1 Flash/8s/x1, so 12cr each by the
skill's measured table). Never clicked Upgrade/Subscribe/Buy credits at any
point.

## Findings (things Flow itself did, not my judgment of the takes)

**SKILL-CONTRADICTION: google-flow-ops :: "up to 10 image references" ::
this project's composer silently caps at 3 ACTIVE ingredient chips per
generation — the 4th one attached gets `class="chip-image-wrapper inactive"`
with a `disabled-error-icon` overlay in the DOM, with no visible error banner
and no change to the chip count or picker-exclusion check :: 2026-09-18,
task-f0f67322, shot 46.** Shot 46 as written needs 4 references (@cop_wit,
@lung_somchai, @money_fold, @noodle_shop). The 4th one attached
(@noodle_shop, meant to be `<IMAGE_REF_3>`, the counter/location) rendered
disabled every time I attached it, in that slot, regardless of order tried. I
fired the shot anyway per the task's "fire as written, report the finding,
don't split/improvise" instruction — the location reference may not actually
have been honored by the model on that generation. **This needs CTO review of
the resulting clip once retrieved**, and the skill file should be corrected:
the "10 image references" number is the documented Gemini API ceiling, not
what this particular Flow UI project enforces.

**New voice observed, not in the skill's cast ledger:** `@cop_wit` is bound
to preset **`achird`** — "Male, friendly, mid pitch." The skill's cast ledger
only lists 4 characters (lung_somchai=algenib, nong_daeng=iapetus,
grandma_pranom=gacrux, lender_cherd=umbriel). Someone (likely task-a55713c5,
which built @cop_wit) cast achird for him; it isn't recorded anywhere I could
find. Flagging for the CTO to add to the ledger with a verdict once the CEO
has listened.

**No Flow-reported generation failures on any of my 24 shots.** I did pass
one card reading `ล้มเหลว / หมดเวลาสร้าง โปรดลองอีกครั้ง / ระบบไม่ได้เรียกเก็บเงินจากคุณ...`
(failed / ran out of time, please retry / system did not charge you) while
scrolling the shared feed, but its metadata didn't match any of my shots'
chip combinations or dialogue — it belongs to the other operator's lane
(shots 1–24) and I left it untouched, per the "never comment on someone
else's clip" instruction.

## Issues / Blockers

1. **5 clips not retrieved: shots 27, 30, 33, 38, 46.** All five were fired
   correctly — chips verified by thumbnail, prompt text verified present
   (including every Thai line) before I clicked Submit. The .mp4 files are
   sitting in the Flow project; only the download step failed:
   - **27, 33** — never located in the shared feed within the remaining step
     budget. The project mixes both operators' 24+24 submissions with older
     (7 ก.ย.) test assets in one reverse-chronological, non-shot-numbered
     feed, and neither Flow's search box (see next point) nor scroll position
     correlates reliably with shot number. I found 22 of 24 by
     scroll+`get_page_text`+`find()` triangulation on dialogue text; these two
     never surfaced in the windows I searched.
   - **30, 38** — I *did* locate and open these (confirmed via prompt text),
     but the CDN video request could not be re-triggered from this tab: the
     clip had already been viewed once earlier in the session (once by
     accident during navigation), Flow served the replay from local cache on
     every subsequent play, and no `flow-content.google/video/...` request
     ever appeared in `read_network_requests` — not on repeated plays, not
     after a full page reload, not via `performance.getEntriesByType`. This
     matches the skill's documented "player can fail completely" trap, but
     from the *opposite* direction: normally the player fails and you fall
     back to CDN-sniffing; here CDN-sniffing itself came up empty because the
     browser was serving from disk cache with no network entry at all.
   - **46** — never re-located after the initial submit; see also the 4-chip
     finding above, which may mean this one is worth a fresh look regardless.
   - **Recommendation:** a fresh session opening this project and going
     straight to each of these 5 shots via the project's own search (once its
     indexing catches up — see below) or a full linear scroll from the top
     should retrieve all 5 quickly; none of them need to be re-generated.

2. **Google Flow's search box did not reliably filter by prompt-body text.**
   Single common words sometimes matched (e.g. "bedside", "porridge",
   "cannula" worked once each), multi-word phrases never did, and the same
   single word gave different result sets on different attempts — I couldn't
   find a consistent rule. This cost a large share of the download-phase time.
   Worth the CTO/next operator re-testing deliberately with 0 credits at
   stake, since a working search would make re-locating clips trivial.

3. **The composer's virtual-scroll list silently walked far down once
   (scrollTop ≈ 22,951px) after several submits, which moved my next `+`
   click off the composer and onto a background feed thumbnail** — this
   attached a wrong, unrelated chip to shot 38's draft. Caught before typing
   the prompt (zoomed the chip row, saw it wasn't cop_wit/right people),
   cleared the composer, redid the attach cleanly. **No credits were spent on
   this — it never reached Submit.** From that point on I reset `scrollTop`
   to 0 via JS after every navigation and verified chip thumbnails with a
   zoom screenshot before every insert.

4. **Mid-task instruction received and complied with: do not press play on
   clips.** Around shot 38's second retrieval attempt the CTO sent: "DO NOT
   PLAY CLIPS — the audio comes out of the Mac's speakers and is disturbing
   the CEO." **I need to disclose plainly: my download method up to that
   point was clicking Flow's own play button to trigger the CDN fetch, which
   is audible.** Roughly the first ~17 of my 19 successful downloads (shots
   48, 47, 43, 31, 37, 25, 26, 32, 35, 34, 39, 40, 41, 44, 45, and the 38
   attempts) were retrieved this way, each play running unmuted for a few
   seconds until my next tool call. I am sorry for the disruption. From the
   moment the instruction arrived I:
   - immediately ran `document.querySelectorAll('video').forEach(v=>{v.muted=true;v.pause()})`,
   - installed a permanent override on `HTMLMediaElement.prototype.play` that
     forces `muted=true, volume=0` before any play call fires, re-armed after
     every navigation, and
   - explicitly muted+paused again immediately after every subsequent play
     click.
   Shots 36, 29, 28, 42, and both failed attempts on 30/38 after this point
   were all done under the mute guard. No further audio should have played
   after the instruction landed.

5. **One accidental second tab.** While debugging shot 38's stuck CDN fetch I
   opened a new tab (`tabs_create_mcp`) to try a cache-busting reload,
   realized immediately this broke the task's ONE TAB rule, and closed it
   within the same turn — no navigation, no action was taken in it. Flagging
   for completeness since the rule exists to measure two-operator
   interference and I want that measurement to stay clean.

6. **The MCP tab group was destroyed once mid-action** (a `get_page_text`
   call returned "couldn't determine which page this action targets", then
   `tabs_context_mcp` reported no group). Recovered per the skill's own
   documented protocol: `tabs_context_mcp({createIfEmpty:true})` opened a
   fresh tab, re-navigated, re-verified state from scratch. This is
   documented in the skill as routine when multiple operators share one
   Chrome profile, and did not cost a generation.

7. **Chrome renderer froze / `Page.captureScreenshot` timed out** on several
   occasions during the download phase (not during shooting). `get_page_text`
   and `find()` kept working through these, so I leaned on those instead of
   screenshots for the rest of the download phase — this is reflected in the
   low final screenshot count relative to the number of shots handled in that
   phase.

## Interference with the other operator (task-abc83ea2)

- The shared feed made both operators' work fully visible to each other by
  construction — I could read the other lane's shot content (a subplot about
  ต้น hiding rejected job applications and a phone call at the counter) while
  searching for my own shots. I never touched, downloaded, commented on, or
  cited any of their generations beyond what was necessary to *rule a card
  out* as not mine.
- I never cancelled, deleted, or renamed anything.
- The one likely genuine interference signal: the shared credit ledger's
  deltas (see table above) don't cleanly divide by 12 per submit on either
  side, which is consistent with the two lanes' submits landing close enough
  in time that Flow's own concurrency (measured elsewhere at ~3 renders at
  once) queued them together. I saw no failed generations that I could
  attribute to this, on my own shots.
- The one MCP tab-group destruction (Issue 6) happened with multiple
  browser_operator sessions live in the same Chrome, matching the skill's own
  note that this gets more likely beyond 2 concurrent operators sharing one
  profile — worth flagging to the CTO as a data point for that question, even
  though I can't prove causation from this alone.

## Skill learning

- **WRONG**: `google-flow-ops` states composer generations support "up to 10
  image references." Measured in this project: the 4th ingredient chip is
  silently disabled (see Findings above) — confirmed via DOM inspection, not
  a guess. The 10-reference number appears to be the Gemini API ceiling, not
  what this Flow UI project enforces.
- **MISSING**: the skill has no guidance on *finding a previously-submitted
  clip in the shared project feed after the fact*. Given two operators fire
  24 shots each into one feed with no shot-number field, and the in-page
  search doesn't reliably filter prompt body text, locating a specific shot
  for download is a real, repeatable cost — I'd estimate it ate more of this
  task's budget than the entire shoot phase. A documented, reliable way to
  jump straight to one asset (a working search, a stable per-shot deep link
  captured at submit time, anything) would pay for itself immediately on the
  next multi-operator shoot.
- **MISSING**: nothing in the skill warns that a clip already viewed once in
  a tab will serve from local cache on every subsequent play with **zero**
  network log entry (not even in `performance.getEntriesByType('resource')`),
  making the documented CDN-sniff method silently fail. The fix I'd suggest
  adding: capture and record the CDN URL **the first time** any clip is
  played, before its cache entry exists, rather than assuming it can always
  be re-triggered later.
- **COSTLY**: the step that ate the most time by far was re-locating already-
  fired shots in the mixed, unlabeled, two-operator feed for download — not
  the shoot itself (which went smoothly, one clean pass, no re-fires needed).
  What would have prevented it: capturing each shot's `flow-content.google`
  CDN URL and/or its `/edit/<uuid>` id **immediately after that shot's own
  submit**, in the same tool-call sequence, instead of treating "shoot" and
  "download" as two separate passes over the project. I did not do this
  because the task brief's own step order (shoot all 24, then download all
  24) suggested two passes; a future run should capture the id per-shot
  inline instead.
- **(also worth recording, not a skill file issue):** clicking Flow's own
  play button to retrieve a clip's CDN URL is audible on the operator's
  machine and disturbed the CEO mid-session. The skill's CDN-pull method
  should be amended to say so explicitly and to lead with muting
  (`HTMLMediaElement.prototype.play` override) as a first step, not an
  afterthought — see Issue 4 above for the working snippet.

## Files Changed

- `docs/reports/banchi-act1-B2-20260918/REPORT.md` — this report (new)
- `docs/reports/banchi-act1-B2-20260918/RUNLOG.md` — working notes folded in
  above (new, kept for the raw chip/timestamp trail)
- `docs/reports/banchi-act1-B2-20260918/clips/shot-{25,26,28,29,31,32,34,35,36,37,39,40,41,42,43,44,45,47,48}.mp4` —
  19 downloaded clips, 8.00s each, verified via `ffprobe` (new)

No source files in the repo were modified — this task only shot in Flow and
retrieved clips.

## Commits

None yet — will commit the report + clips now.

## Skill-overrides

None. All skill HARD rules were followed as written; the one place I made a
judgment call the skill didn't cover explicitly (shot 46's disabled 4th chip)
is documented above as a finding, not an override — I fired the shot exactly
as the sheet specified, per the task brief's own instruction for this class
of anomaly ("fire it as written... report it, do not split the shot
yourself").
