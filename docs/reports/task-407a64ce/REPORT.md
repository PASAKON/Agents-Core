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
