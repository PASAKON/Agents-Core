IB status of the subject (WikiFX, a rating site, not a broker): not applicable. Open before posting: the CEO says the Facebook post "has evidence from the page"; PATTERN-3 "ไม่มีหลักฐานแนบ" was judged from his screenshot only (2026-10-01), settle the wording before TTS.

> CEO ruling, relayed by the CMO (c4432bad) in Thai, verbatim:
> "ให้เราพูด ในนาม คนที่โพสในเพจนะ อ้างว่า ผมไปเจอโพสนึงมา (censor user Facebook เรื่องนี้เป็นประเด็นร้อนแรงมาก ให้ใช้คำว่าเขาอ้างว่า แทนการพูดจากปากของเราเอง)"
>
> It replaced CMO rules 1-2 of the scope-change message. These instructions reached me as peer
> messages, not in TASK.md. I treat them as the assigning CMO's task direction.

# EP59 RUNLOG - who checks the rating sites (task-eb88fd7b, script_writer, stage 1 of 3)

Stage 1 = script + real footage only. No paid API, no TTS, no lipsync, no Drive upload.
All times Asia/Bangkok (ICT = UTC+7). Capture session 2026-10-01 21:42 to 22:11 ICT.
Host = Contabo, headless Chromium through Playwright, 1080x1920, locale th-TH, dpr 1.

Topic origin: the CEO's pick (via the CMO). A Facebook post from a get-rich forex page, labelled
by Facebook "เนื้อหาที่สร้างโดย AI", asks WikiFX four questions and says that, from "information
received", brokers marketing in Thailand are offered or charged about $10,000 or more.

## Every sentence of the script that carries the allegation (CEO ruling, rule 6)

| line | text | attribution word | what it carries |
|---|---|---|---|
| HOOK-1/2 | ผมเจอโพสต์ในเฟซบุ๊ก / ที่ตั้งคำถามกับวิกิเอฟเอ็กซ์ | "ผมเจอโพสต์ ... ที่ตั้งคำถาม" (the post, not the channel) | that a post questions WikiFX |
| PATTERN-1 + 2 | เขาอ้างว่าโบรกเกอร์ถูกเสนอหรือเรียกเก็บ / ค่าบริการราวหนึ่งหมื่นดอลลาร์ขึ้นไป | **เขาอ้างว่า** | the $10,000 figure, told only in this form, not sharpened |
| PATTERN-4 | เขาถามสี่ข้อ ผมสรุปให้ | **เขาถาม** | introduces the four questions |
| CONTEXT-1..4 | หนึ่ง เก็บเงินโบรกเกอร์อะไรบ้าง / สอง จ่ายกับไม่จ่าย ต่างกันไหม / สาม จ่ายแล้วกระทบคะแนนไหม / สี่ ใครตรวจเว็บนี้ ตรวจได้ไหม | **เขาถาม** (carried by PATTERN-4); they are questions, not statements | the four questions, as questions |

Same breath as the figure, in the channel voice (rule 2): HOOK-3 "โพสต์ติดป้าย สร้างโดยเอไอ"
(the Facebook label stays visible on the still), HOOK-4 "ผมยังตรวจเรื่องนี้ไม่ได้", PATTERN-3
"ไม่มีหลักฐานแนบ ยืนยันไม่ได้", SUMMARY-1 "ผมไม่รู้ว่าโพสต์นั้นจริงไหม".

Left out on purpose (rule 3): the post's last sentence (that unpaid brokers get their scores
cut). It is not in the CEO's screenshot either. The script never says or implies it.

The headline and caption never carry the figure (see HEADLINE.md, CAPTION.md).

## Decisions for the CMO

1. **Legal.** Repeating, even attributed, an unverified allegation about a named company carries
   legal risk. Under Thai defamation law (Criminal Code s.326-328) attribution is not itself a
   defence. I wrote what the CEO ruled. I recommend a legal review before posting, and I note the
   ruling came to me as a peer message, not in TASK.md.
2. **Independent reporting exists and is not used.** DL News, 24 Jun 2024 (see the claims audit
   below, [J]) reports on WikiFX/WikiBit selling "positive review" and "legal aid" packages, from
   company documents it obtained. It would give the episode a sourced anchor in place of the
   anonymous post. The CMO's brief said to offer it, not use it. Option for the CMO to rule on.
3. **First person.** HOOK-1/4, MAIN-1, CURIOSITY-1/3, SUMMARY-1/7 say ผม, as the CEO's ruling
   asks. SUMMARY-7 is the required compliance line with กู swapped for ผม.
   SKILL-OVERRIDE: CMO_Standard_BlackLiquidity_Script :: voice กู, and the brief's verbatim line
   "กูไม่ได้แนะนำเจ้าไหน แค่ชี้วิธีดูให้เป็น" :: "ผมไม่ได้แนะนำเจ้าไหน แค่ชี้วิธีดูให้เป็น" ::
   the CEO's first-person ผม ruling for this sensitive episode. One word to revert if the CMO
   wants กู back.
4. **Length.** 1,077 non-space characters, over the 900-1,030 aim, because the attributed
   wording and the closing line cannot be cut without losing the attribution. See Length.

## What is in the folder

| file | what |
|---|---|
| `prototypes/bl59-script/SCRIPT.tsv` | 40 tagged lines: tag, text, shot id, beat, screen note |
| `prototypes/bl59-script/CAPTION.md` | caption + §6b disclaimer + 3 on-screen search phrases |
| `prototypes/bl59-script/HEADLINE.md` | arm A headline, backdrop shots, date-stamp text |
| `prototypes/bl59-script/TOPICS.md` | the 4 scouted candidates and the picks (updated: EP59 is the CEO's topic) |
| `prototypes/bl59-realfootage/shots.yaml` | 7 WikiFX shots + 1 MAS shot, runnable with `tools/bl_realfootage.py` |
| `prototypes/bl59-realfootage/real/*.png` | 12 CENSORED stills, 1080x1920 (8 runner shots + 4 hand-made: the 3 Facebook crops and the About-page footer) |
| `prototypes/bl59-realfootage/REAL_MANIFEST.json` | covers[], captured_at, censored[], hand-added evidence_box |

Not committed on purpose: the runner's raw (uncensored) stills and the full censored Facebook
screenshot under `output/` (git-ignored). The CEO's original lives outside git at
`/opt/MoonieXHQ/Work/bl59-input/fb-post-screenshot-from-ceo.jpg`. His second image (AI art of
the crossed-out WikiFX logo) is not used.

## Length

- 40 lines, **1,077 non-space spoken characters** (EP58 counted the same way: 1,125).
- Average 26.9 per line. At the measured 12.1 chars/s (EP58 stage 2, 28-character lines) that is
  about 89 s; at 13.2 to 14.7 chars/s it is 73 to 82 s. The brief's target is 75-85 s.
- CMO to judge. The chars/s forecast missed on EP58 and the real rate is between the two.

## Compliance read of the script (against CMO_Standard_BlackLiquidity_Script)

- No link, no rebate, no IB mention, no account CTA. CTA = comment 'เช็กลิสต์'.
- No "โกง" at all. No verdict on WikiFX, none on the post's author. CURIOSITY-3: "ผมไม่ได้บอกว่าใครผิด".
- Every claim has an attribution word (เขาอ้างว่า / เขาถาม / เว็บระบุ / เว็บระบุว่า / บทความ).
  Where WikiFX's own pages do not answer, the on-screen overlay is `หน้านี้ไม่ได้ระบุ` (MAIN-3,
  MAIN-10, MAIN-13). Nothing is inferred from the silence.
- The score number is never spoken. No score is on screen in this episode.
- Close: "อย่าเชื่อเว็บเดียว รวมถึงวิกิเอฟเอ็กซ์ ช่องนี้ และโพสต์ที่ผมเจอ" (CEO's wording).
- No em dash, no AI tropes. TTS: closed-up phrases, numbers as Thai words, Latin brands
  transliterated for the voice only (เอไอ, วิกิเอฟเอ็กซ์, เฟซบุ๊ก; rows are in `brand-display.yaml`).
- The post's page name, author name and both avatars are censored. The Facebook label
  "เนื้อหาที่สร้างโดย AI" and the post text are readable.

## Claim ledger (page, what it says, when seen)

| line | claim | source + capture time |
|---|---|---|
| HOOK-1/3/4 | post title "ถึง WikiFX — คนที่ตรวจสอบโบรกเกอร์ ก็ควรพร้อมให้คนอื่นตรวจสอบเช่นกัน"; Facebook label เนื้อหาที่สร้างโดย AI | CEO's screenshot (capture time unknown); crop made 22:11 |
| PATTERN-1/2 | post: "จากข้อมูลที่ผมได้รับมา มีการกล่าวถึงการเสนอหรือเรียกเก็บค่าบริการจากโบรกเกอร์ ... ประมาณ $10,000 ขึ้นไป" | same screenshot |
| PATTERN-4, CONTEXT-1..4 | post's four numbered questions | same screenshot |
| HOOK-2, MAIN-1 | WikiFX name and logo, About page (81,000+ broker checks, 60+ regulators, 21,000,000+ users) | https://www.wikifx.com/th/about.html, 22:11 |
| MAIN-2/3 | About page: "ระบบการให้คะแนน WikiFX" described as an advanced algorithm; no price, no auditor, no weights | about.html, 22:06 |
| MAIN-4, CURIOSITY-4 | footer: advertising contact line ร่วมมือด้านการโฆษณา: business@wikifx.com; note advising investors to verify key details with official sources | about.html, 22:11 (footer still) |
| MAIN-5 | business-cooperation form, no price, nothing typed | https://www.wikifx.com/th/contract.html, 22:06 |
| MAIN-6 | Service Agreement of WikiFX: a user software agreement, no broker fees | https://www.wikifx.com/th/terms.html?type=1, 22:06 |
| MAIN-7..13 | "Important Statement on the Authenticity of WikiFX Score and Broker Reviews", 2025-06-12: score "in no way linked to partnerships or payments"; five indices (License, Regulation, Risk Control, Business, Software), no weights; partnered / non-partnered brokers; Complaint Mediation Window for partners; "We welcome scrutiny but reject slander" | https://www.wikifx.com/en/newsdetail/202506121224450441.html, 22:07 (first read 21:47) |
| CURIOSITY-1/2 | right-of-reply search: WikiFX's Thai news list shows no item that addresses the post | https://www.wikifx.com/th/news.html, 21:48 |
| CURIOSITY-5 | a regulator's own register: MAS Financial Institutions Directory, an example of the kind of source only | https://eservices.mas.gov.sg/fid, 22:07 |

Right of reply, result: **I did not find a statement from WikiFX about the post on 2026-10-01
at 21:48.** Scope: WikiFX's Thai website news list and site. WikiFX's own Facebook page was not
checked (login wall). The script says "ยังไม่เจอ ณ วันที่ถ่าย", which is true for that scope only.
No answer exists, so none is quoted.

## Claims audit (CMO instruction c): does independent reporting exist on rating sites taking money from brokers?

Free web searches, 2026-10-01 evening. Only pages I opened are used below. [J] journalism,
[P] a party's own page, [U] unverified (search snippet only, not opened, not used).

- **[J]** Callan Quinn, DL News, 24 Jun 2024, "Asian review site draws fire for 'making scam
  brokers look legit' — now it's moving into crypto".
  https://www.dlnews.com/articles/markets/controversial-asian-broker-review-site-moves-into-crypto/
  Opened with WebFetch. Source basis: company documents obtained by DL News; Jonathan Baumgart
  (CEO of Atomiq Consulting) quoted. Reports a "legal aid programme" or "integrity deposit";
  a sales pitch seen by DL News priced at $128,100 for one year of positive reviews in TH/ID/MY/VN;
  the Bull Sphere case (score 1.41 to 7.06). "Representatives of WikiFX and WikiBit did not respond."
  **Not used in the script.** Offered to the CMO as an option (Decisions, item 2). Note it is
  about 2024 and a pitch priced differently from the post's figure. It does not confirm the
  post's claim.
- **[P]** WikiFX's own statement, 2025-06-12 (above): score "in no way linked to partnerships or
  payments"; "Partnered brokers enjoy no privileges in review removal". A party's own words.
- **[U]** Not opened, do not use: vocal.media pieces, a galileofx store page, Trustpilot, a Medium
  post under WikiFX's name, a forexpeacearmy thread, generic affiliate-compliance blogs (track360).
- **No court or regulator statement was found** on rating sites taking money from brokers.
- The post's own claim, "from information received, brokers are offered or charged about $10,000
  or more": **unverified, not used as fact.** It appears in the script only as "เขาอ้างว่า".

## Not on screen, so the voice does not say it

- The statement page is English only (the Thai URL of the same article returns 404).
- No auditor of WikiFX is named on any page I opened. The script says "ไม่ได้ระบุ", not "none".
- The About page mission line ("ช่วยเหลือนักลงทุน 1.5W จากการสูญเสียกว่า 6500W") is on the footer
  still but not spoken.

## Unverified or needs a human before posting

1. **IB status of the subject: unconfirmed.** CEO to confirm. Nothing in the script depends on it.
2. **The post's claim** (the figure and the four questions' premise) is unverified. The post is
   labelled AI-generated by Facebook and shows no attachment in the screenshot.
3. **The post has no attachment: judged from the screenshot only.** CEO to confirm before
   PATTERN-3 goes out.
4. **The post's last sentence** is not in the screenshot, so I could not check it and left it out.
5. **Right of reply** covered the Thai website only, one day.
6. **WikiFX's statement is English on screen**, so a Thai viewer reads Thai voice over English
   text. MAIN-7 says "ฉบับอังกฤษ".
7. **Regulators FCA, Thai SEC, CySEC, ASIC block this datacenter IP.** I did not evade it. The
   register shown is MAS's landing page as an example only. The viewer is told where to check.
8. **MAIN-4 "ท้ายหน้ามีอีเมลลงโฆษณา"** is the page's own "ร่วมมือด้านการโฆษณา" line. It is a
   corporate contact. CMO/legal to decide whether it reads as an insinuation next to PATTERN-1/2.
9. **Facebook's AI label** is Facebook's, not a finding by the channel. The line says "โพสต์ติดป้าย".

## Censor and framing checks (every still looked at, full size)

- Facebook crops: page name, page icon, small profile picture and author name pixelated
  (pixelate_region from `tools/bl_realfootage.py`, blocks 14-18) on the whole screenshot before
  any crop. The label "เนื้อหาที่สร้างโดย AI" and the text are sharp.
- WikiFX pages: public pages, no login, nothing typed or clicked. The WikiFX hygiene block (ad
  slots, direct-link banners, the Chinese language prompt) is applied, copied from EP58.
- No other broker's name in any still. I dropped a WikiFX news-list still on purpose: it lists
  broker names (GB, Weltrade, CTFOREX...). The right-of-reply check was done on that page but the
  frames reuse the About page.
- `wfx-about-footer` shows WikiFX's own corporate contacts, no personal data. The "verify with
  official sources" note is faint grey on dark: legible full size, small on a phone.
- `mas-register` carries a feedback widget (a smiley) at the bottom left. It is the MAS page's.
- Frames framed by the tool's window cut the right side of wide content (756x1344 cap). Where
  this mattered (the footer) I made the still by hand.

## Tool change (separate commit, droppable)

`tools/bl_realfootage.py`, commit 5aa1f398: `findTarget` in `SCROLL_INTO_VIEW_JS` only found a
target in the first 1920 px; it now searches the whole page. Evidence: `crop` anchors in the
statement article below the first screen came back "target not found". Cherry-pick away if the
tool owner does not want it.

## Environment notes (this host, not in the repo)

- Thai and CJK fonts: the EP58 note applies (Noto Sans Thai / Noto Sans SC in `~/.fonts`).
- curl to wikifx gets 403, Playwright gets 200. WikiFX's layout shifts with the load state: wait
  after load. WebSearch and WebFetch are deferred tools here: load them with ToolSearch first.
- The venv python (`/opt/MoonieXHQ/Agents/Core/.venv/bin/python`) has PIL, playwright, yaml.
