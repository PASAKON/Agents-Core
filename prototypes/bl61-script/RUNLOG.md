IB status of Tickmill: CONFIRMED by the CEO 2026-10-13 ("ไม่เคย ใช้ชื่อได้": the channel has never earned from Tickmill). Posting gate cleared; the record of his answer is STATUS.md (Approval, Q1). Nothing in the script depends on it (no link, rebate, IB mention or account CTA).

# EP61 RUNLOG - what one order really costs, Tickmill's own pages (task-d002e35e, script_writer, stage 1 of 3)

Stage 1 = script + real footage only. No paid API, no TTS, no lipsync, no Drive upload.
All times Asia/Bangkok (ICT = UTC+7). Contabo's own clock is CEST (ICT minus 5 h). Capture session 2026-10-13 18:49 to 19:02 ICT.
Host = Contabo, headless Chromium through Playwright, 1080x1920, locale th-TH, dpr 1. One browser job at a time, `free -m` checked before each run (about 1 GB free, 7.9 GB box).
Topic: JTBD A, the trader wants to feel they trade smart, not gamble. Mirrors EP60 (task-eb88fd7b): script + real footage only.

## Hypothesis (an ASSUMPTION, not verified)

The idea that a "what do I actually pay" episode earns watch-through and comments like the EP53/54 checklist episodes is an
assumption. Nothing in this task tests it. The test is the episode itself: read the 48 h numbers after posting
(watch-through, comments with the word เช็กลิสต์) against EP53/54 and decide then.

## What is in the folder

| file | what |
|---|---|
| `prototypes/bl61-script/SCRIPT.tsv` | 29 tagged lines: tag, text, shot id, beat, screen note |
| `prototypes/bl61-script/CAPTION.md` | caption in the กู voice + the §6b disclaimer + 3 on-screen search phrases |
| `prototypes/bl61-script/HEADLINE.md` | arm A headline (2 options), 3 backdrop shots, date stamp |
| `prototypes/bl61-script/TOPICS.md` | the 3 candidate pages that opened, 3 blocked sites, why Tickmill |
| `prototypes/bl61-script/cost_check.py` | the arithmetic, prints inputs and result, self-checks against the page's own examples |
| `prototypes/bl61-realfootage/shots.yaml` | the 7 shots, runnable with `tools/bl_realfootage.py` |
| `prototypes/bl61-realfootage/real/*.png` | 7 CENSORED stills, 1080x1920 |
| `prototypes/bl61-realfootage/REAL_MANIFEST.json` | covers[], captured_at, censored[], hand-added evidence_box |

Not committed on purpose: the runner's raw (uncensored) stills under `output/bl-realfootage/bl61/` (png is git-ignored).
Nothing in `real/` or the manifest points at them.

## Length

- 29 lines, **852 non-space spoken characters** (cap: 75 s = 855 at 11.4 chars/s). Counted by `"".join(text.split())` on column 2.
- Forecast: **74.7 s at 11.4 chars/s**, **70.4 s at 12.1 chars/s** (the whole-track rate measured on ~27-character lines in EP58 to EP60).
- Both are inside 75 s, but the 11.4 forecast leaves 0.3 s. If the voice comes out slower than 11.4, drop CURIOSITY-2 first (the "from means lowest" line) and keep CURIOSITY-3.

## cost_check.py output (quoted, run 2026-10-13)

```
INPUTS (all quoted from Tickmill's own pages, captured 2026-10-13)
  lots                         = 1
  contract size                = 100000 EUR            (raw-account page)
  pip                          = 0.0001                (EURUSD, 4 decimals)
  pip value, 1 standard lot    = 100000 x 0.0001 = 10.0000 USD   (channel arithmetic, not on the page)
  Classic: spread from 1.6 pips, commission 0 per lot per side
  Raw:     spread from 0.0 pips, commission 3 USD per lot per side, sides = 2
  swap: 0 by construction (trade opened and closed inside the day; page: swap is charged past 00:00 platform time)

Classic:
  spread     = 1.6 x 1 x 10.0000 = 16.00000  ->  $16.00
  commission = 0 x 1 x 2 = 0  ->  $0.00
  TOTAL (minimum, from the advertised 'from' numbers) = 16.00000  ->  $16.00

Raw:
  spread     = 0.0 x 1 x 10.0000 = 0.00000  ->  $0.00
  commission = 3 x 1 x 2 = 6  ->  $6.00
  TOTAL (minimum, from the advertised 'from' numbers) = 6.00000  ->  $6.00

SENSITIVITY (not spoken): Raw with the spreads-page typical 0.1 pip = 0.1 x 1 x 10.0000 + 6 = 7.00000 -> $7.00  (the page does not say which account its typical column is for)

SELF-CHECKS vs the page's own examples: pass
SCRIPT NUMBERS (สิบหกดอลลาร์ / หกดอลลาร์): match
```

Rounding happens only at the last print (Decimal throughout). "From" is said as "เริ่ม" in every spoken line; both totals are floors (CURIOSITY-2/3).

## Compliance read of the script (against CMO_Standard_BlackLiquidity_Script)

- No link, no rebate, no IB mention, no account CTA, no recommendation. CTA = comment 'เช็กลิสต์'.
- No "โกง", no verdict, no ranking, no "cheapest" or "best", no broker named but Tickmill. The two account types are two cards of one broker.
  The two totals ($16 and $6) are on screen together (allowed); there is no arrow and the voice does not say which is cheaper.
- Every number is attributed in voice and on screen (หน้าบัญชีเขียนว่า, หน้าเขาว่า, หน้าสเปกว่า, หน้าเขาเขียน, สูตรหน้าเขา) and the capture date is spoken (CONTEXT-3, "จดวันที่สิบสามตุลา") and stamped. The channel's own arithmetic is labelled "กูคิดเอง" (MAIN-2).
- SUMMARY-5 is the required line "กูไม่ได้แนะนำเจ้าไหน แค่ชี้วิธีดูให้เป็น", verbatim.
- Checklist of three (SUMMARY-2 to 4): read the account-type page; add spread + commission for the lot size you trade; ask the broker in writing what the swap is on their pair.
- Voice: กู (BL carve-out, IRON-RULES §37). No มึง. No em dash. TTS-readable: closed-up phrases, numbers as Thai words,
  brand "ติ๊กมิลล์" for the voice only (row `ติ๊กมิลล์: Tickmill` added to `brand-display.yaml`).
- The page's own CTAs (Create account, Open live account, Trade now, Try demo account, $30 Welcome Account) are pixelated in every still.
  The Log in button and the language/menu bar stay (not a call to open an account).

## Claim ledger (line, claim, page, capture time)

| line | claim | page + capture time (ICT, 2026-10-13) |
|---|---|---|
| HOOK-1, CURIOSITY-2 | Classic: "spreads from 1.6 pips and zero commissions"; table "Spreads From 1.6 pips", "Commissions Zero Commissions" | https://www.tickmill.com/trading/accounts-overview , 19:01 (tm-classic), 18:49 (tm-header) |
| HOOK-2 | Raw: "Spreads From 0.0 pips"; "$3 commission per lot per side" | same page, 19:01 (tm-raw), 18:49 |
| HOOK-3/4, CONTEXT-3 | Tickmill's own account-types page (name, logo); numbers are the page's own, on the stamped date | same page, 18:49 (tm-header) |
| PATTERN-1, MAIN-1 | FAQ "How do you calculate your transaction cost?": Trade Cost = Spread x Trade Size x Pip Value; practical example 1.2 pips x 1 mini lot x $1 = $1.20 | https://www.tickmill.com/conditions/spreads-swaps , 19:02 (tm-formula) |
| PATTERN-2 | FAQ "What are swaps?": overnight interest charges applied when you hold a position past 00:00 platform time | same page, 19:02 (tm-swaps) |
| CONTEXT-1/2 | Raw page example: "1 lot of EURUSD, which has a contract size of 100,000 EUR" | https://www.tickmill.com/trading/raw-account , 19:02 (tm-raw-example) |
| MAIN-2 | pip value $10 on one standard lot: **the channel's own arithmetic** (100,000 x 0.0001); the page's example is a mini lot at $1 | not on any page; cost_check.py |
| MAIN-3 | Classic page: "variable spreads starting from 1.6 pips and no commissions" | https://www.tickmill.com/trading/classic-account , 19:01 (tm-classic-para) |
| MAIN-4/5 | 1.6 x 1 x $10 = $16.00; commission $0.00; total $16.00 | cost_check.py |
| MAIN-6 | Raw page: "fluctuating spreads starting from 0.0 pips" | raw-account page, 19:02 |
| MAIN-7/8 | Raw page: "commission per side would be 3 USD and 6 USD round turn" | raw-account page, 19:02 |
| MAIN-9 | $0.00 + $6.00 = $6.00 | cost_check.py |
| SUMMARY-2/3/4 | the checklist: the channel's advice on how to read a page, no figure | none (not a claim about Tickmill) |

## NOT spoken (and why)

- **Swap numbers.** The spreads-and-swaps table prints swap figures with no unit stated. Not spoken and not in a still.
- **The table's "typical" EURUSD spread (0.1).** The page does not say which account the column is for. Printed in cost_check.py as a sensitivity only ($7.00), not spoken.
- **"One of the lowest in the world"** (Raw page, paragraph before the example). A ranking claim by the broker. The paragraph is hidden by selector in tm-raw-example, so it never reaches the frame.
- **The Wednesday triple swap** and any swap schedule: unlabelled units, and the example is intraday.
- **The Raw account "chart/raw spread" note** and the TradingView Raw account ($3.5 per lot per side): out of the two-account scope.
  The TradingView Raw card is visible at the right edge of tm-header and tm-raw/tm-classic crops; the voice never mentions it.
- **Tickmill's marketing adjectives** on the Classic page ("optimal trading conditions", "ultra-fast order execution") sit in tm-classic-para; the voice does not repeat them. They are Tickmill's words on Tickmill's page, not a ranking against other brokers.

## Unverified, or needs a human before posting

1. **IB status of Tickmill: unconfirmed.** CEO to confirm (top line).
2. **Licence and regulator NOT checked.** FCA, CySEC, ASIC and the Thai SEC registers block this host's IP. I did not try to get round it.
   The script does not say Tickmill is licensed or unlicensed and does not mention a regulator. Someone with access can check before posting if the CMO wants a licence line.
3. **The channel's $10 pip value (MAIN-2) is not on the page.** The page's own example uses a mini lot at $1; a standard lot is ten times it (100,000 x 0.0001 = $10, the textbook value on a USD-quoted pair). The voice says "กูคิดเอง". CMO to accept that step, or have the voice drop it.
4. **"From" is a floor.** Both totals are minimums. The voice says "เริ่ม" and CURIOSITY-2/3 say so out loud. Real spreads on the Raw account are not zero; the spreads page's typical column (0.1) would make Raw $7.00, not spoken.
5. **Round-turn commission** ($6) is used because the page itself writes "6 USD round turn". If a viewer opens and does not close the trade, they pay $3 only; the example assumes open and close.
6. **The pages carry no date of their own.** The capture date (13 ต.ค. 2569) is the date. If posting slips, re-capture the stills and re-run cost_check.py. Broker pages change without notice.
7. **Framing risk.** Showing $16 and $6 side by side invites "Raw is cheaper". The script says "ศูนย์ทั้งคู่ แต่ไม่ฟรีทั้งคู่" and the totals are floors, but the viewer can still read it that way. CMO to decide whether the two cards stay on screen together (the brief allows it).
8. **Tickmill's page text is English.** Each still shows the English text; the voice reads it in Thai. The editor should not add captions that restate the page as the channel's own claim.
9. **Partial other-broker risk: none seen.** The stills are Tickmill pages only; the footer in tm-swaps shows Tickmill's own navigation. No other broker is named in any frame.

## Scene engine note (IRON-RULES §51)

Applies: this is a narrated piece with a turn. Value shift: before = "zero means free" (the viewer reads 'zero commissions' / 'spreads from 0.0'), after = "zero in the headline, money in the sum" ($16 on one account, $6 on the other, both floors). The reversal is MAIN-4/5 vs MAIN-9 against HOOK-1/2. The scene can lose PATTERN-2/PATTERN-3 without breaking the chain to the goal (they only protect the "no swap" assumption), which is why they are the first cut if the voice runs long after the 855-char cap.

## Censor and framing checks (every one of the 7 stills looked at, full size)

| still | what is in frame | censor check |
|---|---|---|
| tm-header | header, logo, hero, "Compare trading accounts", 3 cards | Create-account button (top) and hero button pixelated; per-card CTA bars pixelated; footnote strip pixelated. No other broker. TradingView Raw card visible on the right (see NOT spoken) |
| tm-classic | Classic card, text and table | CTA bar pixelated. Left edge of Raw card visible at the right |
| tm-raw | Raw card, text and table | CTA bar pixelated. Edges of neighbouring cards visible |
| tm-classic-para | Classic page paragraph, heading, a stock photo of a man's arm at the top | no CTA in frame. Marketing adjectives visible (see NOT spoken) |
| tm-raw-example | Raw page, first paragraph, worked example | the "one of the lowest" paragraph hidden (blank band); button at the bottom pixelated |
| tm-formula | FAQ opened to the cost formula | top Create-account and Ready-to-start buttons pixelated; no other broker |
| tm-swaps | FAQ opened to "What are swaps?" | same; the footer link list shows Tickmill's own nav only; one pixelated block in the footer (a banner) |

- No personal data in any frame (no account number, no email, no phone). The first capture run produced two unusable stills (the text-based CTA censor widened to the whole card and made solid blocks; the crop sat on the wrong card). Both were fixed (below) and re-captured; the superseded stills are not in `real/`.
- The cookie banner and the chat widget are hidden (visibility only) in every still.

## Tool change (separate commit, droppable)

`tools/bl_realfootage.py`, four small additions needed by this episode, all optional per shot and defaulting to the old behaviour:
- `click_texts`: open a collapsed FAQ item by its exact label (a DaisyUI collapse opens through the checkbox next to its title; falls back to a non-exact match; a failure now prints to stderr instead of passing silently).
- `settle_ms` (default 900): wait after the scroll-into-view. Tickmill's swiper moves the card for ~2 s; with 900 ms the crop and the censor boxes were measured on a different frame than the screenshot (a button stayed readable under a misplaced pixelate band).
- `crop: {frame_only: true}`: scroll to and measure the target but keep the whole frame, for content wider than the 9:16 crop cap (a full-width FAQ row).
- `tests/test_bl_realfootage.py`: 33 passed (no new test added for these options: see Not checked).

## Environment notes

- The `text:` censor rules of the runner widen to the whole card (up to 700 px), so use `selector:` rules for buttons.
- `networkidle` on Tickmill's accounts page timed out once in three runs (30 s); the still from the run that succeeded (18:49) is the one used.
- WebFetch is blocked by the research-cache hook; the scout used Playwright. The cwd-guard hook blocks `cd` into a subfolder (use absolute paths).
- `pgrep -f "<runner name>"` inside a Monitor matches the Monitor's own command line and never ends; wait on the runner's PID instead.
