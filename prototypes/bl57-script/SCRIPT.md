# BLACK LIQUIDITY EP57 v2 — เว็บหาย ไม่มีใบอนุญาต (XXLMARKETS)

Rewrite of v1 (merged 2026-09-23) around the CEO's own hook and his own
framing: the episode is our real investigation, told step by step, with a
real screenshot behind each step wherever one exists. v1's WikiFX research
still holds — see `research/xxlmarkets-wikifx-fca-domain-202609.md` — this
pass adds two new real captures and reorders/rewrites every line around the
CEO's verbatim hook and the "show the attempt" instruction in
`.claude/skills/blackliquidity-script/SKILL.md`.

The CEO's words that drove this rewrite (verbatim, from the task brief):

> "EP 57 เริ่มต้นแบบนี้ได้ — ใครใช้โบรคนี้รีบเข้าเว็บเชคด่วนเลย ตอนนี้แม่ง(?)ปิดเว็บ
> ไม่ได้แล้ว นี่คือหลักฐานที่กูพยายามเข้าเว็บ -> ลองอะไรบ้างล่อคนดูไปได้เลย
> อย่าใช้ศัพท์เทคนิคเยอะ เอาง่ายๆ ให้คนดูเข้าใจ"
>
> "แนบหลักฐานแคปหน้าจอ เหมือน AI กำลังเจออะไรบางอย่าง แล้วเอามาเขียนเป็นเรื่อง
> realistic เข้าไปอีก"

## What changed from v1

- **Hook is now the CEO's own words**, cleaned into speakable Thai
  (HOOK-1..4), not the "เว็บหาย" framing v1 opened with.
- **The whole first third of the script is now the attempt itself** —
  PATTERN-1..4 (typed the URL directly, tried `www.`/`https://`, same
  result both times) and CONTEXT-1..5 (checked who owns the name — no
  current owner, but a real registration history back to 2022) — instead of
  leading with WikiFX's verdict the way v1 did. This follows the skill's
  new "Say it the way the viewer says it" section: show the attempt, not
  just the result.
- **Plain words throughout**: "ชื่อเว็บ" not โดเมน, "หน้าเว็บขึ้นว่าเข้าไม่ได้"
  not เออเรอร์/เซิร์ฟเวอร์ล่ม, "หน่วยงานการเงินของอังกฤษ" named once (MAIN-12)
  then never repeated as jargon. v1 used โดเมน/เออเรอร์/ระบบทะเบียนโดเมน
  publicly — the CEO ruled against that on v1 (see skill Field notes).
- **Four new real captures this pass** (below) replace v1's attributed-only
  gaps AND the PATTERN section's spoken-only gap with our own direct
  evidence — including the direct-visit screenshot the CEO's hook itself
  promises ("นี่คือหลักฐานที่กูพยายามเข้าเว็บ").
- **Beat balance improved**: v1 was 11 show / 4 cta / 22 verdict / 3 hook.
  v2 is **20 show / 1 cta / 15 verdict / 4 hook = exactly 50% show**, up
  from v1's 27.5% (see "Beat balance" below).
- **Length**: 2,026 spoken chars, shorter than v1's 2,308.

## The four new real captures (this pass)

Two taken live via Claude-in-Chrome (2026-09-23 ~22:38-22:39 +07), two by
the CTO via headless Chrome after reviewing this script's first draft
(2026-09-23 ~22:50-22:52 +07). All four added to
`prototypes/bl57-realfootage/REAL_MANIFEST.json` with `evidence_box` +
`captured_at`, all well under 1 MiB, none need censoring (no personal
data, no ads, no other-broker content in frame):

1. **`real/xxlmarkets-direct-visit-error.png`** and
   **`real/xxlmarkets-www-visit-error.png`** — the direct-visit attempt
   itself, the evidence the CEO's hook promises. `tools/bl_realfootage.py`
   (Playwright) and Claude-in-Chrome's own screenshot tool both fail to
   screenshot Chrome's native connection-error page on NXDOMAIN (see "What
   could not be captured in the first draft" below for the full trail).
   The CTO's fix: launch real Chrome itself headless
   (`--headless=new --lang=th`, a fresh temp profile, `--window-size=540,960
   --force-device-scale-factor=2` for a clean 1080x1920 still, and
   `--screenshot=<out>.png <url>`) — Chrome's own screenshot flag captures
   whatever the page renders, including its own error page, where the
   extension APIs both refuse. Both stills show Chrome's Thai-UI error page:
   headline "ไม่สามารถเข้าถึงเว็บไซต์นี้" + "ไม่พบที่อยู่ IP ของเซิร์ฟเวอร์
   xxlmarkets.com" (or `www.xxlmarkets.com`) + `ERR_NAME_NOT_RESOLVED`. Used
   for PATTERN-1..4 — "IP"/"DNS" stay in the screenshot's own text and are
   never spoken, per the skill's plain-words rule.
2. **`real/whois-domain-history.jpg`** — who.is's own "Domain History
   Archive" page for xxlmarkets.com (reached via the "History" tab on the
   WHOIS lookup, not a guessed URL — the first guess at
   `who.is/domain-history/...` 404'd, the real path is `who.is/history/...`).
   Shows, in the site's own words: "4 snapshots spanning 2022–2026." A
   second, independent confirmation of the same fact `whois-no-match.png`
   already carried, from a different page on the same tool — used for
   CONTEXT-5.
3. **`real/fca-register-search-spinner.jpg`** — our own direct visit to the
   FCA's Financial Services Register (`register.fca.org.uk/s/search?q=XXLMARKETS`).
   v1's research (`research/xxlmarkets-wikifx-fca-domain-202609.md`) had
   already tried this and found the query registers (tab title updates to
   "XXLMARKETS - Search Firms - FCA Register") but the results panel never
   resolves a firm card. This pass reproduced that exact same result
   independently. Used for MAIN-12 — turns what was previously only
   WikiFX's attributed claim ("even the local FCA shows no results") into
   something the channel can show it tried directly, honestly labelled as
   inconclusive (we don't know if the spinner means "not listed" or just
   "the page is broken"), while keeping WikiFX's separate claim as its own
   attributed line (CURIOSITY-3).

## What could not be captured in the first draft, and how it got solved

The line "กูลองพิมพ์ชื่อเว็บนี้ใส่เบราว์เซอร์ตรงๆเลย → หน้าเว็บขึ้นว่าเข้าไม่ได้"
(PATTERN-1/2) had no screenshot behind it in the first draft of this
script, on purpose, not by oversight. xxlmarkets.com returns NXDOMAIN
(confirmed independently by `dig`, `whois`, `curl`, and a live browser
visit — see the research doc). Two automation surfaces both refused to
screenshot the resulting error state:

- `tools/bl_realfootage.py`'s `page.goto()` hard-fails on NXDOMAIN instead
  of capturing whatever error page Chrome renders (v1's finding).
- Claude-in-Chrome's own screenshot tool errors with "Frame with ID 0 is
  showing error page" (v1's finding, reproduced again in this pass's first
  draft).
- This pass's first draft also tried the macOS-native fallback the task
  brief suggested (`screencapture -l <window id>` against the real Chrome
  window) — AppleScript could not find any window or tab holding the
  xxlmarkets.com page at all, meaning the automation browser used by
  those two tools is not an on-screen, natively-screenshotable window.

The CEO's hook explicitly promises this exact evidence ("นี่คือหลักฐานที่กู
พยายามเข้าเว็บ"), so leaving it spoken-only was a gap, not an acceptable
outcome — the CTO's review flagged it (`CTO-FEEDBACK.md`) and supplied the
fix: a *separate* headless real-Chrome process (not Playwright, not the
Claude-in-Chrome extension) launched with `--headless=new --lang=th` and
`--screenshot=<out>.png <url>`, which captures whatever Chrome itself
renders, including its own connection-error page, because it is Chrome
doing the rendering and the screenshotting in one step rather than a
second surface trying to read back Chrome's internal error-frame state.
Both direct-visit stills are now real captures, see above. **Still
flagging for whoever owns `tools/bl_realfootage.py`**: switching that
tool's own capture path to the same headless-Chrome-native-screenshot
method (instead of Playwright's `page.goto()` + `page.screenshot()`) would
close this gap for every future episode, not just this one.

## Beat balance

| beat | v1 | v2 (first draft) | v2 (final) |
|---|---|---|---|
| hook | 3 | 4 | 4 |
| show | 11 | 16 | **20** |
| verdict | 22 | 19 | 15 |
| cta | 4 | 1 | 1 |

**20/40 = exactly 50% show**, meeting the brief's "aim for at least half"
target, once PATTERN-1..4 flipped from verdict to show with the two new
direct-visit captures. v2 also folds the SUMMARY checklist (3 lines) into
`show` per the brief's own carve-out ("The checklist at the end can be
`show` with a kinetic graphic"), which is why `cta` is 1 (just SUMMARY-8,
the comment-keyword line — still tagged `cta` since it's the
direct-to-camera ask, not a graphic). All 11 real captures on file are
used (9 from before this fix + the 2 direct-visit stills), 7 of them
reused across 2 lines where the still genuinely proves two distinct claims
(the score/country crop, the warning banner, the who.is title/history
crop, the third-party card's headline/subscore crop, and now both
direct-visit error pages covering their "tried it" line and their
"here's what happened" line).

## Sources — every claim, checked live 2026-09-23

| claim | source | checked | result |
|---|---|---|---|
| Score 1.99/10, "ยังไม่มีการกำกับดูแล", UK, 2-5 years, "ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์", warning banner text, website-inaccessible note | WikiFX Thailand dealer profile: https://www.wikifx.com/th/dealer/3697715948.html | WebFetch 2026-09-23 (v1), re-read at full resolution from the captured stills this pass | Confirmed by eye against the real screenshots used in MAIN-2/5/7/8/9/10/11 |
| xxlmarkets.com is inaccessible | this channel's own re-check: `dig`, `dig @8.8.8.8`, `whois -h whois.verisign-grs.com`, `curl -I`, and a live Claude-in-Chrome visit, 2026-09-23T14:36 UTC (v1); reproduced again this pass at ~2026-09-23T22:38 +07; direct-visit screenshot obtained by the CTO via headless Chrome, 2026-09-23T22:50-22:52 +07 | run live, three passes | NXDOMAIN + registry "no match" every time, now with a real screenshot of Chrome's own error page for both xxlmarkets.com and www.xxlmarkets.com (PATTERN-1..4) |
| The domain WAS registered before and has since lapsed (2022-2026 history) | who.is: https://who.is/whois/xxlmarkets.com and https://who.is/history/xxlmarkets.com | Claude-in-Chrome live visit, both v1 and this pass | "We don't have a current record" + "4 historical WHOIS/RDAP snapshots... from 2022 to 2026" on both pages, worded slightly differently each time |
| "Even the local FCA shows no results about it" | WikiFX's own EN summary text — attributed to WikiFX, not independently confirmed | attempted independently both passes: register.fca.org.uk (spinner never resolves, now captured as a real screenshot — MAIN-12) and fca.org.uk/scamsmart (bot-detection challenge, not bypassed, per hard rule) | Still not independently verified — now shown honestly as "we tried, it didn't render" rather than left as prose in a research doc only |

Full research writeup with every command and its raw output:
`research/xxlmarkets-wikifx-fca-domain-202609.md`.

## Length forecast

- Total spoken characters: **2,026** (40 lines) — shorter than v1's 2,308
- Speech-only @ 16.6 chars/s: **122.0 s**
- Whole-track (with breath gaps between lines) @ 13.2-14.7 chars/s:
  **137.8 s – 153.5 s**

## Brands

- เอ็กซ์เอ็กซ์แอลมาร์เก็ตส์ → `XXLMARKETS` (row already in `brand-display.yaml`)
- วิกิเอฟเอ็กซ์ → `WikiFX` (row already in `brand-display.yaml`)
- No new brand rows needed. FCA (register.fca.org.uk) is spoken only once,
  as "หน่วยงานการเงินของอังกฤษ" (never spelled out as an acronym on screen or
  in speech), so it does not need a brand-display row.

## Compliance checklist

- No broker the channel earns from is named.
- No link, no account CTA, no rebate/income mention, no MoonieX mention.
- No em dash anywhere in the spoken column (checked programmatically).
- CTA points at knowledge only: SUMMARY-8, "คอมเมนต์คำว่า เช็กเว็บโบรก"
  (unchanged from v1 — same keyword, same reply pack).
- One line each stating the channel is not recommending anyone (MAIN-13,
  SUMMARY-7) and that no fraud claim is made without evidence (MAIN-13).
- แม่ง/มึง/กู used per the CEO's explicit instruction in this task's brief
  ("Keep his words. แม่ง/มึง/กู are the CEO's own register for this
  channel") — this is the established BLACK LIQUIDITY voice, already
  reviewed and merged in v1 and prior episodes, not a departure from the
  role's general no-crude-language rule.

## Capture log summary (this pass)

Full v1 capture log: `prototypes/bl57-script/RUNLOG.md` (unchanged, 6 tool
captures + 1 third-party still, contact-sheet review, evidence_box pass).
This pass's additions are logged in the same RUNLOG.md file, appended
below the v1 entries: the failed screenshot attempts on the first draft,
the two who.is/FCA captures, then the CTO's review and the two headless-
Chrome direct-visit captures that closed the gap.

## What the viewer should be able to check themselves

1. Type `xxlmarkets.com` into a browser right now — it will not load.
2. Look up the site name at a free website-checking tool — no current
   registration, only historical snapshots back to 2022.
3. Search "XXLMARKETS" on WikiFX (wikifx.com) — same score, same
   "no license" finding.
4. Use the same two tools (WikiFX + a free domain-history tool) to check
   any other broker before depositing — this is exactly the checklist
   SUMMARY-4/5/6 walks through.

## v2.1: the CEO's review, 2026-09-23 23:25 (edited by the CTO)

CEO: "Script ขาดเล็กน้อย เราไม่ได้เฉลยว่าคือโบรกอะไร … เราสอนเขาก็จริง เราต้องบอกเขาด้วยว่าคืออะไร แต่ถ้าภาพ
บอกอยู่แล้วอาจจะให้ภาพเป็นตัวเล่าเรื่องได้ เราใช้คำว่ามึงดูภาพเอาเองประมาณนั้น"

- HOOK-1 now opens on the XXLMARKETS name + logo (WikiFX profile header), so the viewer sees WHICH
  broker from the first frame.
- HOOK-3 ("นี่คือหลักฐาน…") shows the 22:50 error page as it is said. HOOK-2 stays full frame.
- HOOK-4 → "โบรกตัวนี้ชื่อ เอ็กซ์เอ็กซ์แอลมาร์เก็ตส์ มึงดูภาพเอาเอง" over the CEO's WikiFX card (credit on screen).
- PATTERN-1 is new: what it is, from WikiFX's own company profile ("เป็นโบรกฟอเร็กซ์ ที่วิกิเอฟเอ็กซ์บอกว่า
  เปิดที่อังกฤษตั้งแต่ปีสองพันยี่สิบเอ็ด ให้เทรดทั้งค่าเงิน หุ้น และสินค้า"). Leverage and spread are deliberately
  not said, because they read as promotion. The old PATTERN-1/2 are merged into PATTERN-2.
- Totals: 40 lines, show 23 / verdict 15 / hook 1 / cta 1, 2,088 spoken chars (≈126 s speech-only, 142-158 s whole track).
- Editor note: PATTERN-1's evidence_box must cover the company-profile paragraph of
  `wikifx-profile-website-inaccessible`, not only the "Note" line. Measure it on the still at the cut.
