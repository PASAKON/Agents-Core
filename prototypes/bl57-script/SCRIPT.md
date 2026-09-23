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
- **Two new real captures this pass** (below) replace two of v1's
  attributed-only gaps with our own direct evidence.
- **Beat balance improved**: v1 was 11 show / 4 cta / 22 verdict / 3 hook.
  v2 is 16 show / 1 cta / 19 verdict / 4 hook (see "Beat balance" below —
  still short of the brief's "at least half" target, and why, is explained
  there rather than papered over).
- **Length**: 2,026 spoken chars, shorter than v1's 2,308.

## The two new real captures (this pass)

Both taken live via Claude-in-Chrome, 2026-09-23 ~22:38-22:39 +07, added to
`prototypes/bl57-realfootage/REAL_MANIFEST.json` with `evidence_box` +
`captured_at`, both well under 1 MiB, neither needs censoring (no personal
data, no ads, no other-broker content in frame):

1. **`real/whois-domain-history.jpg`** — who.is's own "Domain History
   Archive" page for xxlmarkets.com (reached via the "History" tab on the
   WHOIS lookup, not a guessed URL — the first guess at
   `who.is/domain-history/...` 404'd, the real path is `who.is/history/...`).
   Shows, in the site's own words: "4 snapshots spanning 2022–2026." A
   second, independent confirmation of the same fact `whois-no-match.png`
   already carried, from a different page on the same tool — used for
   CONTEXT-5.
2. **`real/fca-register-search-spinner.jpg`** — our own direct visit to the
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

## What could not be captured, and why (same finding as v1, now confirmed twice)

The line "กูลองพิมพ์ชื่อเว็บนี้ใส่เบราว์เซอร์ตรงๆเลย → หน้าเว็บขึ้นว่าเข้าไม่ได้"
(PATTERN-1/2) has no screenshot behind it, on purpose, not by oversight.
xxlmarkets.com returns NXDOMAIN (confirmed independently by `dig`, `whois`,
`curl`, and a live browser visit — see the research doc). Both automation
surfaces available to this session refuse to screenshot the resulting
error state:

- `tools/bl_realfootage.py`'s `page.goto()` hard-fails on NXDOMAIN instead
  of capturing whatever error page Chrome renders (v1's finding).
- Claude-in-Chrome's own screenshot tool errors with "Frame with ID 0 is
  showing error page" (v1's finding, reproduced again this pass).
- This pass also tried the macOS-native fallback the task brief suggested
  (`screencapture -l <window id>` against the real Chrome window) —
  AppleScript could not find any window or tab holding the xxlmarkets.com
  page at all, meaning the automation browser is not an on-screen,
  natively-screenshotable window either.

That is now two independent sessions hitting the identical wall. Per the
real-footage-capture skill's own rule and the task's HARD line ("invent
nothing for drama"), the honest choice is to leave PATTERN-1..4 as
spoken-only (avatar full frame) rather than fabricate a "recreation"
graphic that risks being mistaken for a real screenshot — the task brief
sanctions a kinetic graphic explicitly for the SUMMARY checklist only, not
for standing in as evidence. The true result is instead proven by the two
real screenshots that follow it immediately: WikiFX's own note that the
site is inaccessible (MAIN-2) and the who.is history (CONTEXT-3..5).
**Flagging for whoever owns `tools/bl_realfootage.py`**: NXDOMAIN/error-page
capture is a real, twice-confirmed gap for any future episode whose subject
site is fully down, not just slow — the tool should catch the navigation
error and capture the browser's own connection-error page instead of
throwing.

## Beat balance

| beat | v1 | v2 |
|---|---|---|
| hook | 3 | 4 |
| show | 11 | 16 |
| verdict | 22 | 19 |
| cta | 4 | 1 |

v2 folds the SUMMARY checklist (3 lines) into `show` per the brief's own
carve-out ("The checklist at the end can be `show` with a kinetic
graphic"), which is why `cta` drops to 1 (just SUMMARY-8, the
comment-keyword line — still tagged `cta` since it's the direct-to-camera
ask, not a graphic). 16/40 = 40% show, up from v1's 27.5%, using all 9 real
captures now on file (7 from v1 + the 2 new ones above) — every one of them
reused across 2 lines where the still genuinely proves two distinct claims
(the score/country crop, the warning banner, the who.is title/history
crop, the third-party card's headline/subscore crop). The brief's "aim for
at least half" is not met; the shortfall is entirely the PATTERN section
(4 lines, no real footage possible — see above), and inventing graphics
there was judged a bigger risk than falling short of the ratio.

## Sources — every claim, checked live 2026-09-23

| claim | source | checked | result |
|---|---|---|---|
| Score 1.99/10, "ยังไม่มีการกำกับดูแล", UK, 2-5 years, "ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์", warning banner text, website-inaccessible note | WikiFX Thailand dealer profile: https://www.wikifx.com/th/dealer/3697715948.html | WebFetch 2026-09-23 (v1), re-read at full resolution from the captured stills this pass | Confirmed by eye against the real screenshots used in MAIN-2/5/7/8/9/10/11 |
| xxlmarkets.com is inaccessible | this channel's own re-check: `dig`, `dig @8.8.8.8`, `whois -h whois.verisign-grs.com`, `curl -I`, and a live Claude-in-Chrome visit, 2026-09-23T14:36 UTC (v1); reproduced again this pass at ~2026-09-23T22:38 +07 | run live both passes | NXDOMAIN + registry "no match" both times. Screenshot of the error state itself not obtainable either time (see above) |
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
below the v1 entries, with the exact times of both new captures and the
native-screencapture fallback attempt that also failed to find a
screenshotable window.

## What the viewer should be able to check themselves

1. Type `xxlmarkets.com` into a browser right now — it will not load.
2. Look up the site name at a free website-checking tool — no current
   registration, only historical snapshots back to 2022.
3. Search "XXLMARKETS" on WikiFX (wikifx.com) — same score, same
   "no license" finding.
4. Use the same two tools (WikiFX + a free domain-history tool) to check
   any other broker before depositing — this is exactly the checklist
   SUMMARY-4/5/6 walks through.
