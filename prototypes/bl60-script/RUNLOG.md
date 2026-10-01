IB status of GB (Goldenburg): unconfirmed, CEO to confirm before posting

# EP60 RUNLOG - GB / Goldenburg (task-eb88fd7b, script_writer, stage 1 of 3)

Stage 1 = script + real footage only. No paid API, no TTS, no lipsync, no Drive upload.
All times Asia/Bangkok (ICT = UTC+7). Capture session 2026-10-01 21:37 to 21:42 ICT.
Host = Contabo, headless Chromium through Playwright, 1080x1920, locale th-TH, dpr 1.
Topic origin: pick #2 of the 4 scouted candidates (TOPICS.md); chosen by the CMO (c4432bad). GVD Markets is the reserve.

## What is in the folder

| file | what |
|---|---|
| `prototypes/bl60-script/SCRIPT.tsv` | 40 tagged lines: tag, text, shot id, beat, screen note |
| `prototypes/bl60-script/CAPTION.md` | caption + §6b disclaimer + 3 on-screen search phrases |
| `prototypes/bl60-script/HEADLINE.md` | arm A headline, backdrop shots, date-stamp text |
| `prototypes/bl60-realfootage/shots.yaml` | the 11 shots, runnable with `tools/bl_realfootage.py` |
| `prototypes/bl60-realfootage/real/*.png` | 11 CENSORED stills, 1080x1920 |
| `prototypes/bl60-realfootage/REAL_MANIFEST.json` | covers[], captured_at, censored[], hand-added evidence_box |

Not committed on purpose: the runner's raw (uncensored) stills under `output/bl-realfootage/bl60/`
(png is git-ignored). Nothing in `real/` or the manifest points at them.

## Length

- 40 lines, **1,028 non-space spoken characters** (EP58 counted the same way: 1,125). Shortest
  line 18, longest 39 (SUMMARY-7, the required compliance line), average 25.7.
- Forecast: 12.1 chars/s (EP58 measured, 28-character lines) gives 85 s; at 13.2 to 14.7 chars/s,
  70 to 78 s. The brief's target is 75-85 s.

## Compliance read of the script (against CMO_Standard_BlackLiquidity_Script)

- No link, no rebate, no IB mention, no account CTA. CTA = comment 'เช็กลิสต์'.
- No "โกง", no verdict. Every claim is attributed: วิกิเอฟเอ็กซ์ระบุ / บทความว่า / เขียนว่า /
  ติดป้าย / ข้างล่างว่า / ผู้ใช้เขียน / ผลสำรวจ. MAIN-4 says "นี่คือที่วิกิเอฟเอ็กซ์เขียน"; PATTERN-4
  says the channel cannot confirm the user's claim; SUMMARY-2 says the channel has not checked the register.
- The number on the score badge is never spoken. It is on screen and moves.
- The complaint amount is not spoken: the page says 80,000 with no currency.
- Line SUMMARY-7 is the required line "กูไม่ได้แนะนำเจ้าไหน แค่ชี้วิธีดูให้เป็น", verbatim.
- Voice: กู (BL carve-out, IRON-RULES §37). No มึง. No em dash. TTS-readable: closed-up phrases,
  numbers as Thai words, brands transliterated for the voice only (จีบี, ไซเซค, โกลเดนเบิร์ก, วิกิเอฟเอ็กซ์;
  rows added to `brand-display.yaml`).
- WikiFX's own warning card says "โปรดหลีกเลี่ยง". It is WikiFX's text on screen; the voice does not repeat it.
  CMO to decide whether that on-screen phrase is acceptable (same open point as EP58).

## Claim ledger (page, what it says, when seen)

| line | claim | source + capture time |
|---|---|---|
| HOOK-1/4, CONTEXT-1/2, MAIN-1 | WikiFX profile of GB: Goldenburg logo, red label ยังไม่มีการกำกับดูแล + stamp, score badge (1.38/10 at capture, not spoken) | https://www.wikifx.com/th/dealer/8341918460.html, 21:37 |
| HOOK-2 | red card "คำเตือน: ระดับคะแนนอยู่ในระดับต่ำ ... โบรกเกอร์นี้ไม่มีการกำกับดูแลฟอเร็กซ์ที่ถูกต้อง", date 2026-10-01 | same profile, 21:37 |
| MAIN-2/3/4 | licence box "ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์"; overview row "ใบอนุญาตในการกำกับดูแลกำลังถูกตั้งข้อสงสัย" | same profile, 21:37 |
| MAIN-5/6 | basic info: Cyprus, 5-10 years, company Goldenburg Group Limited | same profile, 21:37 |
| MAIN-9/10 | related company GOLDENBURG GROUP LTD (Cyprus) with tag ยกเลิกการจดทะเบียน | same profile, 21:39 |
| HOOK-3, CONTEXT-3/4 | article title "โบรกเกอร์ GB เคยอยู่ใต้ CySEC แต่ใบอนุญาตถูกเพิกถอน! มีอะไรอยู่เบื้องหลัง", page age "10h" | https://www.wikifx.com/th/newsdetail/202610019604717978.html, 21:38 |
| MAIN-7/8 | licence under GOLDENBURG GROUP LTD, CySEC Forex Execution License (STP), no. 242/14, effective 14 July 2014 | same article, 21:38 |
| MAIN-11/12/13 | "สถานะใบอนุญาตปัจจุบันคือ ถูกเพิกถอน (Revoked)"; no licence with effect remains; check the latest status with CySEC directly | same article, 21:38 |
| CONTEXT-5, CURIOSITY-1/2 | article names Cyprus Securities and Exchange Commission (CySEC); GB operates through GB Finance UK Ltd, registered in the UK, while the licence was GOLDENBURG GROUP LTD's | same article, 21:38 |
| CURIOSITY-3/4 | WikiFX survey 2019-05-31, tag Good: Goldenburg Group Limited "fully licensed under CySEC, CIF 242/14" | https://www.wikifx.com/th/survey/104771d952.html, 21:38 |
| PATTERN-1/2/3 | complaint 2021-02-03: cannot withdraw, contact lost, funds frozen, amount "80,000" with no currency; the page also holds a Chinese machine-translation line | https://www.wikifx.com/th/exposure/detail/202102035922794080.html, 21:41 |

## Not on screen, so the voice does not say it

- The article's FCA paragraph (a consumer-credit record, not a forex licence) is in a still but not spoken.
- The 80,000 amount; the poster's location label (pixelated).
- The related-company card's registration number and "Established 2019-02-23".
- The article's last paragraph ("not a safe option ..."): WikiFX's verdict, not repeated in the voice.

## Unverified or needs a human before posting

1. **IB status of GB: unconfirmed.** CEO to confirm. Nothing in the script depends on it.
2. **Licence status NOT checked at the regulator.** CySEC's register blocks this host's IP (FCA, Thai SEC,
   CySEC and ASIC all did). I did not evade it. Licence no. 242/14 and "Revoked" are WikiFX's words.
   SUMMARY-2 says so. Someone with access should look it up before posting.
3. **Entity names are inconsistent on WikiFX's own pages**: Goldenburg Group Limited (profile),
   GOLDENBURG GROUP LTD (article, related company), GB Finance UK Ltd (article, UK). CURIOSITY-1/2 states
   only that two names appear in one article. It does not say they are, or are not, one firm.
4. **The 2021 complaints** are two posts by one username on one day, from a poster whose location label
   reads Hong Kong (pixelated on the still). The currency is not stated. The script says "ผู้ใช้เขียน" and
   "คนเดียว วันเดียว" (PATTERN-3), not "complaints".
5. **The 2019 survey** said licensed and tagged Good. It is seven years old and was not re-verified. The script
   says "ตอนนั้นเขียนว่ามีใบ" and nothing more.
6. **The score moves** (1.38 at capture). The voice never says it; re-read the screen before posting.
7. **WikiFX is the only source for every claim**, and it is a commercial rating site (see EP59).
8. The survey page text mentions another broker (hidden or pixelated); the bottom cards of the profile page
   name other brokers (XTB, MEXC, FXTM). They are below the first screen of every still and not in frame.
9. The article's page age says "10h" on 1 Oct; the voice says "ล่าสุด", not a date.

## Censor and framing checks (every one of the 11 stills looked at, full size)

- The broker's website, email and phone are pixelated by regex (exact text range) in every frame
  that carries them (header, warning, licence, basic, related, revoked paragraph, complaint).
- The related-company box: clone list and officer names hidden by selector.
- Complaint page: username and avatar pixelated by the `complaint_user` selector profile (the avatar
  heuristic misses this older page template). The poster's location label next to the date is pixelated
  by hand (`pixelate_region`, block 6) after the runner; the date stays readable. Text is small at full
  viewport: the editor zooms into the top third.
- Survey page: field photos and map hidden, the street address and the other broker's name pixelated.
- Article stills: WikiFX's embedded images hidden (the hygiene block), which leaves blank bands
  (`gb-article-oct`, `gb-article-revoked`, `gb-related`). The editor zooms; nothing is lost.
- The grey bar inside `gb-article-revoked` is a censored website name (broker link as text).
- Frames framed by the tool's window (756x1344 cap) cut the right side of wide content (profile-page stills).
- The WikiFX hygiene block and the censor profiles are reused from EP58 verbatim, plus
  `broker_contact`, `people`, `survey_address`, `other_broker`, `complaint_user` (shots.yaml).

## Tool change (separate commit, droppable)

`tools/bl_realfootage.py`, commit 5aa1f398: the scroll-into-view helper only found a target in the first
1920 px; it now searches the whole page. Needed for the article paragraphs on this episode.

## Environment notes

Same as EP58/EP59: fonts in `~/.fonts`, curl 403 vs Playwright 200, the venv python has PIL/playwright/yaml.
The runner log was not saved to a file; capture times above come from the manifest.
