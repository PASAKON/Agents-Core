# REPORT task-407a64ce: spend-cap flags on the 8 Run Inbox tools

Branch `agent/developer-task-407a64ce`, base `origin/main` (fe80572e). Prerequisite for flipping
`RUN_INBOX_SPEND_LABEL` from warn to enforce.

## Read this before flipping to enforce

Five of the eight files do not meet the rule as the brief assumed. Two need a decision from you.

| File | What the brief assumed | What the code does | Effect under enforce |
|---|---|---|---|
| `tools/topview_wan3.py` | has the cap flag | `--max-credits` is a per-JOB gate (`cost > args.max_credits`, line 643). No running total. `jobs` takes many files, so a run can spend N x jobs. | A card with `--max-credits 3` passes the hub check, but the tool does not stop at 3 in total. Not changed (brief: "change nothing else"). Fix is about 6 lines: keep a running total, check `total + cost > N`, exit 3. |
| `tools/flow_music.py` | has the cap flag | Only `--max-credits-per-track`: checked AFTER a track is charged ("the UI shows no price before"), exits 1. I ran the hub's `tools/ask_run.py cap_flag_check` on `... --max-credits-per-track 20`: it returns `spend_cap_flag_ambiguous`. | No flow_music card can pass enforce: the hub refuses the flag name, and the tool has no `--max-credits`. Not changed. Needs a design call: the price is unknown before the click, so a run total needs a worst-case per-track cost. |
| `tools/bl_realfootage.py` | spends | Playwright capture of public broker pages, ffmpeg, PNG/MP4 to disk. No provider, no credit, no USD. | No cap flag added (nothing to cap). `allow_abbrev=False` only. |
| `tools/ilag_round.py` | spends | `scp` from winbox + contact sheet + Google Drive upload. No per-call charge. The paid ChatGPT work happens earlier, in `tools/chatgpt_images.py` on winbox. | Same: `allow_abbrev=False` only. |
| `scripts/champa/champa_fire.py` | credit-billed | Fires only on a label `Unlimited 0`; `QueueGuard.check` refuses any other label. Every click it can make costs 0. | Flag added and tested, but it can only trip on a priced label, which the guard already refuses. A belt on a tool that cannot spend. |

If you want a cap flag on `bl_realfootage` / `ilag_round` anyway, say so: it would be a flag that
checks a cost of 0, and I would rather not ship that without your word.

## Per tool

### tools/flow_shoot.py (`run` only)
- Unit: **credits**. Flow bills credits; the panel shows `N เครดิต`.
- Per-call cost: `browser.read_credit_estimate()`, read off the live panel right before Submit (an
  unreadable price already stops the whole run, "an unreadable price is not a free price").
- Flag: `run --max-credits N` (default None). `pull` and `status` make no paid call (`pull` refuses any
  credit-bearing download option), so they take allow_abbrev only.
- Stop: checked before the legacy `--credit-cap` (so the card's cap speaks when both trip), again inside
  `_submit_or_raise` as a backstop (`SpendCapReached`), prints `spend cap reached: spent X of N credits`,
  exit 3. The refusal re-fire is also a Submit and is capped; the first estimate stays counted (refunded
  in practice), which errs on the safe side.
- `--credit-cap` is still `required=True`, so a card must carry both: `--credit-cap N --max-credits N`.
  I ran `cap_flag_check` on exactly that command: it passes. If you want `--max-credits` alone to be
  enough, that changes `--credit-cap`'s required-ness; left for you.
- `allow_abbrev=False`: root parser, `run`, `pull`, `status`.

### scripts/higgsfield/gen_loop.py
- Unit: **credits** (Higgsfield).
- Per-call cost: the number on the Generate button right before the click, parsed with
  `credit_guard.parse_price` (last integer; `UNLIMITED · 140 0` is 0). **Unknown cost**: if the label cannot
  be read, the click is priced at 140, the largest per-call figure the Higgsfield code mentions (the list
  price in `parse_price`'s docstring). Constant `UNKNOWN_CLICK_CREDITS`.
- Flag: `--max-credits N`. Both clicks are capped: the first, and the "gen not started, retry click" one.
- `ensure_config` already refuses to run unless the button says Unlimited, so in normal use every click is
  0; the cap covers label drift and the retry.
- Stop: message, then `sys.exit(3)` after the Playwright `with` block closes.

### scripts/higgsfield/credit_fire.py
- Unit: **credits**. Per-call cost: the submit label's price, already parsed for the existing guard.
- Flag: `--max-credits N`, a per-run total. Separate from `--budget` on purpose: `--budget` sums the
  ledger across runs; the label's cap is "this run". Checked before `guard.check`.
- Parser is a `NonExitingArgumentParser`: a bad flag becomes `return 2`, not `SystemExit(2)`. Tests assert that.

### scripts/champa/champa_fire.py
- Unit: **credits**. Per-call cost: last integer on the submit label (`label_credits`; `Unlimited 0` is 0).
  A label with no number adds 0 and is refused by the guard before any click.
- Flag: `--max-credits N`, checked before `guard.check`. `--harvest` submits nothing, so it is not capped.

### tools/flow_music.py, tools/topview_wan3.py
`allow_abbrev=False` only, as briefed. See the table above for what is still wrong with them.

### tools/bl_realfootage.py, tools/ilag_round.py
`allow_abbrev=False` only (root parser and the `run` subparser in bl_realfootage).

## Files changed
- tools/flow_shoot.py, scripts/higgsfield/gen_loop.py, scripts/higgsfield/credit_fire.py,
  scripts/champa/champa_fire.py: `--max-credits` + `allow_abbrev=False`
- tools/flow_music.py, tools/topview_wan3.py, tools/bl_realfootage.py, tools/ilag_round.py: `allow_abbrev=False`
- tests/test_spend_cap_flags.py (new)
- docs/reports/task-407a64ce/REPORT.md (new)

## Other things found, not changed
- `--max-credits nan` is accepted by `topview_wan3.py` and `flow_music.py` (`type=float`): `cost > nan` is
  always False, so a NaN cap lets everything through. The four new flags refuse NaN, inf and negatives at parse time.
- I wanted one shared `tools/spend_cap.py`. `self_repo_guard` refused the new path (not in `touches`), so
  the small helper is repeated in each of the four files, as `gen_loop.py` already does with `flow_shoot.py`'s
  guards. Add the path to `touches` if you want it deduplicated.
- `docs/ops/flow-runner-USAGE.md` and `flow-on-winbox.md` do not mention `--max-credits` (outside `touches`).
- No caller in the repo's scripts, skills or docs passes an abbreviated flag (grepped every invocation of
  the eight tools); callers outside this repo are unknown.

## Tests
`tests/test_spend_cap_flags.py`: **37 passed**.
- Half A (8 files): each case first proves the abbreviation parses with abbreviations switched back on, then
  that it is rejected as shipped (SystemExit 2, or exit 2 for the two NonExiting parsers). Plus NaN/inf/
  negative/garbage caps refused, plain caps accepted.
- Half B (4 tools): stops before the call that would pass N, nothing after it, exit 3; a total exactly equal
  to N is allowed; no flag = unchanged; cap wins over the legacy cap / budget; gen_loop unknown-price and
  retry-click cases; flow_shoot `_submit_or_raise` backstop.
- No network, no spend: every provider env var stripped, `socket.connect` and `urlopen` raise, and the paid
  click is a stub (FlowBrowser stub, fake adapters, fake `playwright` module). `git status` after the run
  showed no stray file.
- Mutation check (the fix undone, the test must fail): 24 mutations, 24 caught: all 8 sources reverted;
  `allow_abbrev` removed from 9 parsers one at a time (incl. `pull` and `status`); `>` to `>=`; retry-click
  check removed; unknown price 140 to 0; cap check after the budget; running total never added (credit_fire,
  gen_loop); NaN accepted (all 4); backstop removed; exit 1 instead of 3; spend cap checked after the legacy cap.
- Related suites, one process: 625 passed (the new file + test_flow_shoot, credit_fire, credit_guard,
  gen_loop, champa_fire, champa_queue_guard, bl_realfootage, flow_music, topview_wan3, runner_workdir_dest,
  ask_run_spend, chatgpt_images, decide, decide_browser_sites, flow_cdp, flow_reupscale, test_video_to_drive).
- Not run: the full repo suite (main CI has known reds); a live `--help` or dry run of any tool (forbidden).

---

# Iteration 2 (CTO feedback, 2026-10-16)

Supersedes the `topview_wan3` and `flow_music` rows of the table above ("Not changed"). The first report is
left as written.

## What the CTO decided, and what is now in the code

| # | Decision | Done in | Exit / message |
|---|---|---|---|
| 1 | `topview_wan3 --max-credits` becomes a RUN total | `tools/topview_wan3.py` | `total + cost > N` before each Generate click: stop, print `spend cap reached: spent X of N credits`, exit 3 |
| 2 | `flow_music --max-credits N` run total, worst-track check before each click | `tools/flow_music.py` | `total + WORST_TRACK_CREDITS > N`: same message, exit 3 |
| 3 | `flow_shoot`: `--max-credits` alone is enough | `tools/flow_shoot.py` | argparse error (exit 2) if neither `--credit-cap` nor `--max-credits` |
| 4 | `bl_realfootage`, `ilag_round`: no cap flag | unchanged | they spend nothing, so they never carry a spend label |
| 5 | shared helper / docs | unchanged | helpers stay duplicated per file; I did not touch the docs |

### 1. tools/topview_wan3.py
- Unit stays **credits**. Per-call cost: the number on the visible Generate button, read again at the moment
  of the click (unchanged source).
- The old check was `cost > --max-credits` per job. Now `args.spent_credits` carries the run's total across
  every job file given; `spend_cap_exceeded(spent, cost, N)` runs where the old check was (before the balance,
  dialog and plan checks). `spent_credits += cost` is set right before the click (a click that lands is
  charged). A job read back as already `done`/`submitted`, a `--dry-run` and `--recover` never click, so they
  add nothing.
- `hazard_kind` is now `spend_cap` (was `over_cap`; nothing else in the repo reads `over_cap`). A first job
  dearer than N now exits 3 with the message (it exited 1 before).
- The comparison rounds to 6 decimals: `0.1 + 0.1 + 0.1` is `0.30000000000000004`, which would stop a run
  capped at exactly 0.3 one job early.
- `--max-credits` stays `required=True`; its parser type is now `spend_cap_arg` (finite and >= 0), so `nan`,
  `inf` and negatives are refused at parse time. Before, `--max-credits nan` was accepted and `cost > nan` is
  always False.

### 2. tools/flow_music.py
- Unit **credits** (the separate Flow Music pool).
- New `--max-credits N` (default None, same `spend_cap_arg`). Before each Generate click (after the balance/
  button gate and the dry-run return, before `save("submitted")`): if `spent + WORST_TRACK_CREDITS > N` the
  row is saved `stopped`/`spend_cap`, nothing is clicked, the message is printed, exit 3. At the click the
  total is reserved at `spent + WORST_TRACK_CREDITS`; when the track is `done` the reservation is replaced by
  the ACTUAL charge (`balance_before - balance_after`). If the balance cannot be read after the track, the
  reservation stays (worst case). If a finished track took the total past N (it charged more than assumed),
  the run stops right after it with the message and exit 3.
- **WORST_TRACK_CREDITS = 5.0.** Which source: the code. `tools/flow_music.py` states the price twice
  ("5 credits per Generate (30610 -> 30555 for 13 songs)", "about 5 per song"), and every recorded charge in
  the repo equals it: `docs/promo/topview-trailer/MUSIC-LEDGER.json` (12 rows at Length 1:00: eleven 5.0, one
  0.0) and `docs/scripts/khaoniao-ep1-music-ledger.json` (one 3:00 track, 5.0); `.claude/skills/CMO_Knowledge_
  Flow_Omni1.1` records "a 3-minute track costs the same as a 1-minute one". The two bigger numbers in the
  repo are **caps an operator chose, not prices**: 20 in the usage line and 10 in the CMO_Workflow_ShortFilm
  recipe. I did not take them as the worst case because a card that sets cap = estimate = 5 for one track
  would then never fire (0 + 10 > 5). **This is the one judgment call in iteration 2**: if you want the
  safer bound, change that constant to 10 (one line; tests read the constant, only the ledger-based test
  would then need its bound updated); the cost is that `--max-credits N` fires `floor(N/10)` tracks.
- `--max-credits-per-track` is kept as it was and still stops a run after a dearer track (exit 1) when given.
  **One necessary deviation from "keep it as it is":** it is no longer `required=True`. The hub reads any
  `--max-c…` word as a spelling of `--max-credits`, so `tools/ask_run.py cap_flag_check` refuses a command
  that carries `--max-credits-per-track` (see the output below), with or without `--max-credits` next to it.
  A spend-labelled flow_music card therefore cannot carry the flag at all, so the tool has to run without it.
  Rule now: at least one of the two flags (argparse error otherwise); with `--max-credits` alone the
  per-track cap defaults to `WORST_TRACK_CREDITS` (a track that charges more than assumed stops the run).
- Left alone: `--max-credits-per-track nan` is still accepted (`type=float`), which disables the per-track
  stop. The run total still holds because it is fed the measured charge.

### 3. tools/flow_shoot.py
- `--credit-cap` is no longer `required=True` (still `type=int`). `main()` raises an argparse error (exit 2,
  usage printed) for `run` when neither it nor `--max-credits` is given. `effective_credit_cap(credit_cap,
  max_credits)` gives `--credit-cap` when present (`0` is a real value, "never spend"; the tests that rely on
  `--credit-cap 0` still pass) and `--max-credits` otherwise; `cmd_run` uses it for the legacy cap check and
  both `_submit_or_raise` calls. `cmd_run` also returns 2 before building a browser if a caller skipped
  `main()` and passed neither. `pull` and `status` need no cap.
- With both flags nothing changes from iteration 1 (the spend cap is checked first and wins).

## `tools/ask_run.py cap_flag_check` (the hub's own check, run for real on the command shapes, unit `credits`)

```
None                       python3 tools/flow_music.py prompts.json --out out --max-credits 20
spend_cap_flag_ambiguous   python3 tools/flow_music.py prompts.json --out out --max-credits 20 --max-credits-per-track 20
spend_cap_flag_ambiguous   python3 tools/flow_music.py prompts.json --out out --max-credits-per-track 20
None                       python3 tools/flow_shoot.py run --sheet s.md --ledger l.tsv --dest d --max-credits 100
spend_cap_flag_missing     python3 tools/flow_shoot.py run --sheet s.md --ledger l.tsv --dest d --credit-cap 100
None                       python3 tools/topview_wan3.py a.wan3.json b.wan3.json --out out --max-credits 3
```
The first, fourth and sixth are pinned in `tests/test_spend_cap_flags.py`, and so is the `ambiguous` answer.

## Tests (iteration 2)
- `tests/test_spend_cap_flags.py`: **72 passed** (37 from iteration 1 + 35 new). No network, nothing spent:
  provider env stripped, sockets and `urlopen` raise, `TopViewBrowser` / `FlowMusicBrowser` / the Flow browser
  are stubs whose Generate/Submit is a counter, `prepare`, `wait_for_songs`, `collect`, `wait_for_clip` are
  stubbed. New cases: topview run total across jobs (stop at the exceeding job, nothing after, ledger row
  `stopped`/`spend_cap`), total == N allowed, one job dearer than N, float noise at exactly N, dry run
  uncapped, an already-done job costs nothing, `--max-credits` still required; flow_music stop before the
  click, total == N allowed, measured charge replaces the reservation, unreadable balance keeps the
  reservation, cap below one track fires nothing, a dearer track stops the run (exit 1 with the per-track
  default, exit 3 when it passes the cap), per-track flag alone unchanged (both its stop and its pass),
  both flags together, neither flag is an error, dry run uncapped, WORST_TRACK_CREDITS against the ledger;
  `--max-credits nan/inf` refused on the command line of all three; flow_shoot alone-parses, neither is an
  argparse error, pull/status need no cap, `effective_credit_cap` table (incl. `0`), a full `cmd_run` with
  `--max-credits` alone stops at N, `--credit-cap 0` not replaced by `--max-credits`, `cmd_run` with neither
  refuses before attaching; `cap_flag_check` on the three commands and the `ambiguous` answers.
  The message is asserted as a line of its own (the stop note embeds the same words).
- One test I wrote was wrong and caught by running it: five 0.6s add up to exactly 3.0, so it would have
  passed without the rounding; replaced by three 0.1s against a cap of 0.3, which does fail without it.
- Mutation check on the new code (the fix undone, the tests must fail): **24 mutations, 24 caught** (first run
  22 of 24: two assertions were too weak, fixed, then 24 of 24). topview: total never added, back to a per-job
  check, no rounding, exit 1 for 3, NaN accepted by the flag, `>` to `>=`, message not printed, flag no longer
  required. flow_music: reservation never replaced by the measured charge, pre-click check removed, worst
  track 0, no reservation at the click, overshoot check removed, neither-flag error removed, per-track
  default removed, exit 1 for 3, NaN accepted, `>` to `>=`, per-track flag required again. flow_shoot: `0`
  treated as unset, `--credit-cap` required again, no error on neither, `cmd_run` guard removed,
  `--max-credits` not used as the credit cap. The 23 mutations of iteration 1 (minus the "revert all 8
  sources" one, whose base moved) were rerun: 23 of 23 still caught.
- Related suites, one process (same list as iteration 1 + the new file): **660 passed**.
- Not run: the full repo suite; any tool against a real page.

## Open points for you
- WORST_TRACK_CREDITS 5 vs 10 (above).
- `.claude/skills/CMO_Workflow_ShortFilm/SKILL.md` line 241 tells the CMO to run `flow_music.py ...
  --max-credits-per-track 10 ...`. Under enforce that command carries a flag the hub refuses; a card needs
  `--max-credits <N>` instead. The skill is outside this task's touches, so I did not edit it.
- `docs/ops/flow-runner-USAGE.md` (yours, as you said): `run` no longer needs `--credit-cap`.
