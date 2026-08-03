# MoonieX — Brand Reference

Brand-asset reference library (like claudesign per-brand refs). One+ sample per content
type in `images/`; add more over time — more refs = more variety for AI to match the theme.
Captured 2026-06-09.

## Identity
- **Name:** MoonieX (Forex trading school / member system; รองรับ **Exness / XM**).
- **Logo:** gold crescent-moon + pagoda mark (`mooniex-webapp/public/brand/logo-mark.png`)
  + **MOONIEX** wordmark. In-folder logo refs:
  `images/logo-lockup-vertical-navy.png` (moon over MOONIEX, vertical) ·
  `images/logo-lockup-moon-wordmark-navy.png` (moon + MOONIEX wordmark, navy bg).
  Transparent built lockups: `Agents/output/personal-brand/lockup-*.png`.
- **Channels:** Live Discord · Facebook Page · LINE OA `@mooniex`.

## Palette (LOCKED — see memory `mooniex-poster-recipe`)
- Background: deep **navy** `#0c1c2b` (→ `#0a1622`), dramatic dark.
- Accent: **champagne gold** `#cdac65` (gradient `#e6d0a3 → #cdac65 → #766540`), glowing gold.
- Atmosphere: gold circuit lines, faint candlestick + binary `0101`, corner HUD panels.
- HARD: **NO cyan / purple / teal / blue neon** (off-brand "trust gradient").
- Text: white + bold gold; key word emphasized in gold (or red for high-emphasis hooks).

## Typography
- Thai brand font = **Prompt** (`--font-sans`). Bold gold headlines. Infographic forecast
  colors: green = up, red = down.

## Samples in `images/`
| Sample | Type | Style |
|---|---|---|
| `tradetech-sample.png` | **TradeTech** (`autogen-tradetech.js`) | navy+gold circuit bg, glowing gold/blue hero objects (robot, laptop, HUD panels), bold gold Thai hook, MOONIEX wordmark footer. Tool/EA promo. |
| `economic-calendar-sample.png` | **Economic Calendar** (`autogen.js`) | "ปฏิทินข่าว" infographic — calendar header, event cards (time pill, ★ impact, green↑/red↓), navy+gold, MOONIEX footer. |
| `tradermindset-sample.png` | **TraderMindset** (`mooniex_poster.py`) | personal-brand quote poster — CEO character + HUGE art-headline keyword + navy+gold trading-room bokeh + moon+MOONIEX lockup top-right. |
| `spcx-ipo-news-sample.png` | **News event** (`spcx_poster.py`, 2026-06-12) | CEO-approved news-promo template — MASSIVE chrome-silver English headline (SpaceX-wordmark style, upright, ≤78% width, top-right kept clear), no people, hero rocket/object + gold plume + crescent moon, smaller gold Thai line, bottom row of 4 gold-outline pill badges (facts), moon lockup top-right. Chrome-silver allowed as bridge accent for space/tech news; navy+gold still dominant. |
| `fed-warsh-news-sample.png` | **News/macro alert** (`output/mooniex-posters/fed-warsh/poster.html`, 2026-06-18, CEO-approved+posted) | Text-led macro-event poster, **$0 HTML→Chrome @2x, NO gen**. Vivid-red **LIVE "ข่าวด่วน"** badge (top), 2-line gold-gradient Thai headline, **real public-figure portrait** in gold-ring circle (fetched via Wikipedia REST `originalimage`, public-domain govt photo — never gen faces) + name/role chip, **3-row color-coded scenario ladder** (🟢 ลด/up · 🟡 คง/flat · 🔴 ขึ้น/down). Moon lockup top-left, date chip top-right. NO on-image footer (it clips) — link `mooniex.com/tools`, รองรับ Exness·XM, CFD disclaimer go in the **caption**. |
| `fed-warsh-result-sample.png` | **News/macro result recap** (`output/mooniex-posters/fed-warsh/result.html`, 2026-06-18) | Post-event variant of the alert. Gold **"✓ ผลออกแล้ว"** badge, twist headline, same portrait chip, a gold **verdict band** (decision + rate), then a **market-reaction ladder** (gold/stocks ▼ red, dollar ▲ green per up=green/down=red). Same template family — clone, swap copy. Publish path: `scripts/post-fed-warsh.js` / `post-fed-result.js` (Postforme → MoonieX TradeTech). |

## Layout cues
MOONIEX wordmark/lockup as footer (bottom-center) or top-right corner (TraderMindset). Bold
Thai hook, premium institutional fintech mood, 1:1 square for feed. "รองรับ Exness / XM" where
relevant.

## Categories to add (library grows over time)
- **event / giveaway** — gold-ring giveaway poster ("ลุ้นรับแหวนทองคำฟรี", navy + gold
  candlestick bg, gold-ring hero, moon logo + Exness/XM, Discord/FB/LineOA `@mooniex`).
- **live / class** — "LIVE TRADING — Demand & Supply Zone" (dark bg, TradingView/SMC chart
  screenshot framed in gold, red LIVE badge, gold checklist, Discord CTA, MOONIEX footer).
  *(both pasted inline — not on disk; save to Desktop/Downloads + give filename to add.)*

## Poster Build — Must-Pass Checklist (CEO rejects, 2026-06-16)
Run BEFORE every MoonieX poster render. Hard-fail gates — a miss = reject.

1. **Logo top-right = REAL moon + PAGODA lockup.** Use
   `mooniex-webapp/public/brand/logo-mark.png` (gold crescent + pagoda) or the cached
   transparent lockup `output/personal-brand/lockup-vertical.png` (moon+pagoda over MOONIEX).
   Old method = `scripts/mooniex_logo.py` → `stamp_corner()`.
   ❌ NEVER an improvised plain crescent / hand-built moon SVG — instant reject.
2. **$ amounts = glossy 3D gold ("เงาวับ").** Match the printed rebate posters
   (`assets/brand-refs/mooniex-rebate-posters/xm-15usd.jpg` / `exness-8usd.jpg`): bright gloss
   gradient (near-white top → champagne → deep gold) + 3D extrude (stacked dark-gold
   drop-shadows). ❌ flat / dark / matte gold numbers = reject.
3. **Study the old gen first.** Open existing posters in
   `assets/brand-refs/mooniex-rebate-posters/` + `output/mooniex-posters/` and mirror their
   lockup placement, glossy-number treatment, and gold richness before building new.
4. **Brand-strict = overlay, never bake.** gpt-image-2 (fal) gens the SCENE ONLY (no text,
   no numbers, no logos). Overlay exact $ values, broker logos, Thai copy and the real lockup
   CRISP via HTML/PIL. Never let gen bake numbers / logos / Thai — it garbles them.
5. **Tokens locked:** navy `#0c1c2b`, champagne gold `#cdac65`, font **Prompt**. NO cyan / teal /
   purple / blue neon.
6. **Pipeline:** HTML → Chrome headless screenshot `--force-device-scale-factor=2` (crisp text);
   scene overlaid behind a navy scrim. Text layer = $0. Scene gen only when it adds value.
