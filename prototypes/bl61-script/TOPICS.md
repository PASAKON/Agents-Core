# BL EP61 broker-page scout (task-d002e35e, script_writer)

Job: one broker's OWN public page with two account types (a spread-only one and a raw-spread-plus-commission one),
numbers visible, no login, not one of the brokers already used in EP53-60 (BingX, Weltrade, XXL Markets, GVD Markets,
GB/Goldenburg, plus the EP59 rating-site topic; XM and Exness are excluded as the two brokers the repo says the channel
may earn from, wiki `2026-09-28-brief-forex-ib.md`).

Scouted 2026-10-13 about 13:10 to 13:40 Europe/Berlin (= 18:10 to 18:40 ICT) on Contabo, headless Chromium (Playwright),
public pages only, no login, no click beyond opening a collapsed FAQ item. Repo and wiki grep for each name below:
zero hits for Tickmill, Fusion Markets; IC Markets appears once in a wiki research file as a market reference for IB rates
(not as a broker the channel works with).

## The 3 candidates that opened

| # | broker | page(s) | captured (ICT) | numbers the page shows | verdict |
|---|---|---|---|---|---|
| 1 | **Tickmill** | https://www.tickmill.com/trading/accounts-overview , https://www.tickmill.com/trading/raw-account , https://www.tickmill.com/trading/classic-account , https://www.tickmill.com/conditions/spreads-swaps | 2026-10-13 18:32 to 19:02 (scout), stills 18:49 to 19:02 | Classic: spreads from 1.6 pips, Zero Commissions. Raw: spreads from 0.0 pips, $3 per lot per side. Raw page's own worked example: 1 lot EURUSD, contract size 100,000 EUR, 3 USD per side, 6 USD round turn. FAQ gives the cost formula (Trade Cost = Spread x Trade Size x Pip Value, mini-lot example) and says swaps are charged past 00:00 platform time, per standard lot | **CHOSEN** |
| 2 | IC Markets (ic.com / icmarkets.com) | https://www.ic.com/en/trading-accounts/overview , https://www.ic.com/en/trading-pricing/spreads | 2026-10-13 18:38 to 18:40 | Standard: $0 commission. Raw Spread: spreads from 0.0 pips, $3.5 per lot per side. Also Raw Pro $1.5 and Raw Pro+ $1.0 per side (the cards print "$0.0" for the spread). A cTrader/TradingView account charges $3 per 100,000 USD traded, with a worked EURUSD example of $3.90 + $3.93 = $7.83 | rejected: four commission schemes on one page, two of them priced on notional value, so one clean 1-lot example does not exist; cards carry typos ("$0.0 pips") |
| 3 | Fusion Markets | https://fusionmarkets.com/Trading/Products-and-accounts , https://fusionmarkets.com/Trading/Forex-cfd-spreads | 2026-10-13 18:39 to 18:40 | Zero: spreads from 0 pips, "industry-leading $4.50 commission" (per what is not stated on the page text I read). Classic: from 0.9 pips, zero commission | rejected: the commission basis (per lot, per side or round turn) is not stated next to the number, and the page prints ranking claims ("industry-leading", a ForexBenchmark comparison "as of 1 October 2026") that would put a ranking on screen |

## Blocked, so not usable (not evaded)

| broker | URL | result (2026-10-13) |
|---|---|---|
| FP Markets | https://www.fpmarkets.com/trading/accounts/ | HTTP 403, Cloudflare "Sorry, you have been blocked" |
| Pepperstone | https://pepperstone.com/en/trading/account-types/ | HTTP 403, CloudFront "Request blocked" |
| Vantage | https://www.vantagemarkets.com/trading/account-types/ | HTTP 403, Cloudflare bot check |

The regulators' registers (FCA, CySEC, ASIC, Thai SEC) also block this host's IP, as on EP58 to EP60. I did not try to get
round any of these blocks.

## Why Tickmill

1. **The page does the arithmetic's hard part itself.** Its Raw page states, for exactly the trade this episode shows
   (1 lot EURUSD, contract size 100,000 EUR), "3 USD per side and 6 USD round turn". Its FAQ gives the cost formula
   (Spread x Trade Size x Pip Value) and defines the swap. The channel adds one step (pip value on a standard lot = $10,
   a tenth-lot multiplication of the page's own $1 mini-lot figure), and says so in the voice.
2. **Two account types of one broker, same page family, the numbers sit in plain cards:** Classic "from 1.6 pips, zero
   commissions" and Raw "from 0.0 pips, $3 per lot per side". The point "the advertised number is not the cost" is
   visible without ranking any broker: each card's headline number (zero commission, 0.0 pips) is not the total.
3. **Dated.** No Tickmill page prints its own date (the spreads table is live). The date is the capture time, stamped on
   screen and spoken (13 Oct 2026). That is the best available here; the other two pages are no better dated.
4. **No ranking claim on the crops.** Tickmill's raw page does say "one of the lowest in the world" in the paragraph before
   the example. The shot list hides that paragraph so the sentence never reaches the frame.
5. **IB status unconfirmed.** Tickmill runs an Introducing Broker programme (its footer lists it). Nothing in the repo or
   wiki says the channel has a relationship with it. The CEO should confirm before posting (RUNLOG).
