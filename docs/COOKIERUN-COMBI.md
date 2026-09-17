# Cookie Run — the Combi the bot farms with

Read off the live game on winbox, 2026-09-17. Saved in-game as preset
**`MONEYFARM`** (Combi Management → row 1 of 6) so there is one name to point at
instead of five rows all called "Combi".

**Game: CookieRun: Classic** (`com.devsisters.crg` v26.8.02) — *not* OvenBreak.
The 300K coin-farm guides that come up first in search are OvenBreak's Sorbet
Shark strategy and describe a different game with different physics, cookies and
UI. Footage of it is not usable for anything here.

## MONEYFARM

| Slot | Item | What it does |
|---|---|---|
| Cookie | **Potato Salad Cookie** — S, Lv.8 | skill Salad Bomb Lv.8 |
| Relay #2 | **Buttercream Choco Cookie** — B, Lv.8 | **+25% Coins** |
| Pet | **Tater Trader** — S, Lv.8 | Speed Coins, Giant Jellies · **Coin Creation Lv.8** |
| Treasure 1 | **Tasting Spoon +9** | +4% base speed · Mini Magnetic Aura |
| Treasure 2 | **Bread Bag Clip +9** | +8% base speed as Giant · **60% chance Silver→Gold coins as Giant** (capped) |
| Treasure 3 | **Golden Piece of Cake +9** | +5% base speed · +8% Coins |
| Combi Bonus | Mini Magnet, Giant: +Speed | |

Every treasure is at +9 (max evolved). The whole set is built around the Giant
state: Bread Bag Clip only pays while Giant, and it is the "double coin" rule the
CEO refers to.

Account: **GoB**, level 62, all-time best 448,653,360, 85.5M coins banked.

## The number that sets the target

**The same Combi, played by hand with no collisions and a clean relay swap,
makes 300K+ per run. The CEO has done it.** The bot, on that same Combi, ends
rounds at 55–81K.

So the 4–5× gap is not the loadout. It is entirely how the run is played, and
that is what a model can move. Recent v5 rounds measure 146–198 s with **1–5
hits each** (mean ≈ 3.7) and a death every round; the v8 goal the CEO set is zero
hits, zero falls, anticipatory jumps.

## What this means for training video

YouTube has plenty of CookieRun: Classic coin-farm footage and **most of it is
useless to us, in a way that would not show up in any training metric**: the
best-paying farm runs are AFK runs. "30K+ Autorun Coins Farm Trick", Yugwa +
Slapstick at ~70K "with zero manual input" — those videos are 56–80K precisely
*because* nobody presses anything, which is the same poison that sank every v8
arm when two keyless takes contributed 12.8% never-press rows.

Take video only when:

1. **Cookie matches** — Potato Salad Cookie.
2. **Pet matches** — Tater Trader.
3. **Treasures**: 1–2 of the 3 matching is good enough; deviation is tolerable.
4. **The player is actually playing** — real presses, not an AFK/autorun farm.

(CEO, 2026-09-17.)

## How this was read

`windows/cookierun_probe.py` + the `MooniexCookieRunProbe` scheduled task — the
app's pipe can start and stop the bot but cannot click or look at the screen, and
plain ssh lands in session 0 where the game window does not exist.

Two traps worth keeping:

- **Run it under `pythonw`, never `python`.** A console window opens on top of
  the game and the first screenshot came back with a black rectangle over a
  quarter of the board.
- **BlueStacks does not type into the game's field.** Text goes to an Android IME
  strip at the top of the screen and only lands when Enter commits it. The
  overlay showed `MONEYFARM` while the field underneath still read `Combi` —
  verify the field, not the typing.

And one that cost the farm half an hour: **closing a dialog is not the same as
having closed it.** The probe's last step clicked the X on Combi Management with
no screenshot after it, the navigator has no template for that screen, and the
preflight dry round that follows any code change then could not reach a run —
so the app refused to release the bot. Always end a probe plan with a shot.
