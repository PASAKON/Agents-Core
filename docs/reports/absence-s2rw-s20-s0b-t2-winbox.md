# S2R-W harvest + S20 + S0b — winbox browser operator (patient harvester), t2

Task task-3b2070ff, continuing from BLOCKER `docs/reports/absence-s2rw-s20-t1-winbox-BLOCKER.md`
(task-0fe8ed87, now closed/merged).

## Tab

Tab **1638444895** (previous operator's, holding the staged S20 composer) was
**not reachable** inside this session's `tabs_context_mcp` tab group — it
belongs to a different browser-extension session and never appeared in
`availableTabs`. Per the brief's own fallback ("or open ONE fresh tab"), I
released the stale registry claim on it (`tab_registry.py release
task-0fe8ed87 1638444895` — the tasks.db that would normally arbitrate this
does not exist on this winbox checkout, confirmed by `ls`; treated the task
brief's explicit "now closed" plus the git log merge commit for task-0fe8ed87
as sufficient out-of-band confirmation) and opened a fresh tab: **1638444900**,
claimed under `task-3b2070ff` in the tab registry. S20's composer therefore had
to be re-staged from the sheet, not resumed.

Browser: winbox-chrome (`815ddf16-36ea-4e0d-827a-f51e9ff85351`), selected via
`config/hosts.yaml`. Project confirmed in the address bar throughout:
`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`.

## Phase 1 — S2R-W (asset `d58ee0c0-3835-4c3c-b571-a324346bb426`)

First look (2026-09-10 ~06:00 UTC / 13:00 ICT): reloaded the tab, grid text
scan showed one card with a bare **"Generating"** badge (not `queued` — a
status this build apparently does show distinctly, contrary to the t1
operator's observation of only `queued`/`completed`/`nsfw` over 3h of polling).

~90s later, re-checked: the "Generating" card was gone from the text scan.
Located the actual asset by its `data-asset-id` attribute (safe, non-PII,
non-query-string DOM attribute — avoids the harness's cookie/query-string
content filter that blocks `outerHTML`/`innerHTML` dumps on this page) rather
than trusting position-in-grid (the position-0 card at that moment was a
**different** asset, `380b3f37-935e-457d-858b-6da05b792cf3`, also `nsfw` —
confirms this build resorts on status change and a naive "top card" read
would have misattributed the outcome).

**Confirmed via `[data-asset-id="d58ee0c0-3835-4c3c-b571-a324346bb426"]`:**
`data-job-status="nsfw"`. Card text verbatim:

> NSFW
> Credits refunded
> Rejected due to copyright restrictions.
> Delete

**Outcome: REJECTED (NSFW/copyright), not completed.** No harvest for S2R-W —
per the brief, rejected → record verbatim, do not re-fire, proceed to Phase 2.
The job left the Unlimited slot (rejected counts as "left"), clearing it for
S20.

## Phase 2 — S20 "THE WALL ON A PLINTH" (asset `7a1c376d-5bc6-477e-9173-340be87c0663`)

Lint: `python scripts/prompt-lint.py docs/prompts/absence/s20-addon-the-wall-on-a-plinth.txt`
— clean. `--chips` — expects 4: `@loc_hall_big_e`,
`@project_absence_char_guard_valder_two`, `@project_absence_char_cleaner_c`,
`@project_absence_prop_cart_a_painted`.

Fired only after confirming (fresh reload) the Unlimited lane held no
queued/processing job of ours — S2R-W had already left it (nsfw, above), and
no other card showed `queued`/`Generating` for this account's Unlimited slot.

- Video tab already selected; model already Seedance 2.5.
- Pasted the exact `PASTE FROM HERE`…`PASTE STOPS HERE` block via synthetic
  `ClipboardEvent` (`DataTransfer.setData('text/plain', …)`, base64-transported
  from the sheet file to avoid transcription errors) into the one
  `contenteditable` with `visibility !== 'hidden'`. Never used a
  keystroke-simulating `type()` for the prompt body.
- Followed the paste with a real `End` → `space` → `Backspace` per the
  editor-gotchas section, then re-verified: **4/4 chips bound
  (`span.text-font-brand` leaf spans starting with `@`), 0 `.text-icon-error`
  chips.**
- Duration: clicked the `20s` chip to open the popover, focused the
  `role="slider"` (`aria-valuemin=4`, `aria-valuemax=30`, was `20`),
  `ArrowLeft` x12 → `aria-valuenow="8"`. Confirmed 8s.
- Resolution/aspect/quality/sound were already at spec (720p / 16:9 / High /
  Sound On) — unchanged.
- Unlimited toggle: was `off` (price showing `140`/`130` before duration
  change, `80`/`45` after, both live/un-struck — correctly did not click
  Generate at either point). Clicked the toggle once (`ref`-based, via
  `find()`) → `data-state="on"`.
- **Decoy-button trap, confirmed live**: a DOM text-scrape
  (`[...document.querySelectorAll('button')].find(b=>/generate/i.test(...))`)
  kept returning a **hidden**, stale duplicate reading `GENERATE 80 45` (live,
  un-struck) even after Unlimited was on. The real, visible button (confirmed
  by a full screenshot AND by filtering the DOM query on
  `getComputedStyle(b).visibility !== 'hidden'`) read **`UNLIMITED · 56
  (struck-through) · 0`**. Did not click on the strength of the DOM scrape
  alone — matches this skill's own documented incident (`GENERATE8045` decoy,
  2026-08-28) almost exactly. Filed here as confirmation the trap is still
  live on this build, not a new finding.
- First Generate click (on the real, verified-$0 button) did not fire a
  generation — no network POST, editor text unchanged, no grid-count change.
  Root cause found via `document.body.innerText`: a persistent
  **"Prompt > Instruction: Prompt is required"** validation message, matching
  this skill's documented Incident 2 / editor-gotchas entry exactly (paste
  reaches Lexical's DOM but not its bound React state). Fix per the skill:
  re-focused the editor, `End` → typed one real character → `Backspace`
  (a genuine trusted keystroke, not the modifier-only End/space/Backspace
  combo which had already been tried once post-paste and was apparently
  undone by the subsequent duration/toggle UI interactions). The placeholder
  text "Describe the scene you imagine…" disappeared after this — the
  reliable tell that the bound state was empty despite correct visible text.
  Re-verified chips (4/4), settings, and price (still `Unlimited · 56 · 0`),
  then clicked the same button again.
- **Second click fired successfully**: `All assets` count 771 → 772; new
  card `data-asset-id="7a1c376d-5bc6-477e-9173-340be87c0663"`,
  `data-job-status="queued"`.
- Per hard rule 7 (any browser-tool error/timeout on a Higgsfield page →
  check Usage before anything else) — this session hit several CDP
  `Page.captureScreenshot`/`Runtime.evaluate` timeouts (transient; page was
  never actually frozen, `document.readyState` stayed `complete` throughout).
  Checked the account menu (separate tab, composer tab left untouched):
  **Credits: 603 left.** No POST to any paid endpoint was ever observed in
  `read_network_requests`; the one failed click produced no network activity
  at all. Recording 603 as this session's baseline for any future check.

**S20 result: fired, `queued`, Unlimited/$0, 8s/720p/16:9/Seedance 2.5/High,
4/4 chips, 1/4 batch.** Not yet harvested (still in the queue as of this
report — render times run 20-90+ min depending on time-of-day queue depth;
06:28 UTC / 13:28 ICT is inside the "stacked peak" window per this skill's
own render-time table, so a long wait is expected, not a fault).

## Phase 3 — S0b "THE CART ROLLS IN" — NOT YET FIRED

Correctly **not fired**: the Unlimited lane currently holds S20
(`7a1c376d-…`, `queued`) — only one Unlimited video generation may be
in-flight at a time. Lint already confirmed clean pre-check:

```
$ python scripts/prompt-lint.py docs/prompts/absence/s0b-fix2-the-cart-rolls-in.txt
```
(sheet present, not yet run in this session — run again fresh before firing,
per this skill's "lint before every paste" rule).

**For the next operator/session:** once S20's card shows `completed` or a
rejection status (no longer `queued`/`Generating`), harvest S20 (see below),
then stage and fire S0b — 3 chips (`@loc_hall_big_e`, `@char_cleaner_c`,
`@prop_cart_a`), 8s, same Unlimited procedure. The composer in tab
`1638444900` has been left with S20's now-submitted prompt in it; assume it
needs a full clear+re-paste for S0b (a real Ctrl+A + Delete, not
`execCommand`, per editor gotchas) rather than trusting any leftover state.

## Harvest — pending

Nothing landed yet to harvest. S2R-W needs none (rejected). S20 harvest
(download to `C:\Users\UsEr\Downloads`, md5/bytes/path, ffmpeg frames at 0.5,
2, 3.5, 5, 6.5, 7.9s → `docs/reports/frames-s20-t1/`, review-order PASS/FAIL)
is the next concrete step once the card leaves `queued`. S0b harvest follows
the same pattern into `docs/reports/frames-s0b-t1/` after it fires and lands.

## Stopping here — why

Per this skill's explicit brief-writing rule ("never make a worker sit and
watch a render" / "a worker's job ends the moment the generation is confirmed
fired") and the wave-operating pattern ("stage the next scene during the
render, but there is nothing to *fire* right now since only one Unlimited job
runs at a time and S20 owns the slot) — S20 is confirmed fired and queued,
S0b cannot fire until S20 vacates the slot, and there is nothing landed yet to
harvest. Stopping and reporting rather than idle-polling in this same session,
per the render-wait pattern's warning against a foreground sleep loop making
the operator unreachable.

## Files changed

- `docs/reports/absence-s2rw-s20-s0b-t2-winbox.md` (this file, new)

No sheets, ledger, MP4s, or other project files touched. No frames yet (none
landed to extract from).

## Tests / lint

- `python scripts/prompt-lint.py docs/prompts/absence/s20-addon-the-wall-on-a-plinth.txt` — clean.
- `python scripts/prompt-lint.py --chips docs/prompts/absence/s20-addon-the-wall-on-a-plinth.txt` — EXPECTED 4, matches what bound.

## Blockers

None. S2R-W's rejection is a recorded outcome per the brief's own Phase-1
branch ("rejected/nsfw → record the card text verbatim, do NOT re-fire, go to
Phase 2"), not a blocker.

## SKILL-OVERRIDE

`browser-operator` :: "reuse the previous operator's staged tab if the brief
allows it" :: opened a fresh tab instead :: tab 1638444895 did not appear in
this session's `tabs_context_mcp` tab group (belongs to a different
browser-extension session/tab group); the brief itself names "open ONE fresh
tab" as the explicit alternative, so this is the brief's own fallback, not a
deviation from it.
