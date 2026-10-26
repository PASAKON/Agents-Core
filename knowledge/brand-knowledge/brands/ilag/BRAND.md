# ILAG — ละครสั้นคุณธรรม by ILAG Studio

Owner: CMO. Written 2026-10-26 (CMO Ging).

The palette marked LOCKED is the FB theme the CEO approved on 2026-09-28 (`tools/ilag_theme.py`, skill
`CTO_ILAG_LakornTheme`). Everything marked **PROPOSED** is channel kit v1. The CEO asked for it on 26 Oct:
"ช่วยออกแบบให้หน่อยและทำมาให้ดู เพื่อเอาไว้เป็นกฎถาวรในการทำช่อง". The kit becomes LOCKED tile by tile, once
he answers by tile number. Until he answers, the pilot EP may use v1 as it is. Do not redesign a tile he has not
rejected.

## What the brand is

- FB Page «ละครสั้นคุณธรรม by ILAG Studio», id 61594116376333. It posts Thai moral dramas made with AI: the
  wrongdoer meets karma, and the family comes through. The story rules are in `CMO_Standard_Story_ThaiMoralDrama`.
- CEO, 26 Oct 2026: the Page is back on, because followers are rising (+2–4 a post). The new format runs 10–20 min
  per EP. Each EP is complete in itself, opens with a 15 s hook, has a twist, and pulls into the next EP. Our edge
  is AI mistakes that make people laugh: "AI ไปตบหน้าตัวละครผิดตัว … ตำรวจจับผิดคน … การตีลูกบอล มีการเปลี่ยนฝั่ง".
- A sister identity is the ILAG Studio YouTube "The Stamp" (red rubber stamp #B8322A, live since 2026-08-07). The
  NG stamp in this kit borrows it on purpose, so the two channels read as one studio.

## Palette

| token | hex | status | use |
|---|---|---|---|
| NAVY | `#0A1A38` | LOCKED | card and end-card ground, emblem disc |
| GOLD | `#F7C64E` | LOCKED | flat gold (rules, small text) |
| GOLD_METAL | `#FDE165` → `#F7C440` → `#E49C1D` | LOCKED | gold text and ring gradient, top to bottom |
| CARD_CREAM | `#FFF4D6` | LOCKED | second lines on navy, the good half of the lotus |
| CARD_BG | `#0C0D1E` @ 88% | LOCKED | story end-card box (poster workflow) |
| STAMP_RED | `#B8322A` | PROPOSED | NG stamp, nickname pill on the name card, EP pill |
| INK | `#231F1C` | PROPOSED | flashback vignette |
| PAPER | `#F6EEDD` | PROPOSED | the "อดีต" tag and its clock icon |

## Type (PROPOSED; every file is OFL, in `templates/fonts/` with `OFL.txt`)

| font | role |
|---|---|
| Taviraj Bold / SemiBold / Medium | time cards, place names, character names, EP titles, end card: the lakorn voice |
| Anuphan (variable) | second lines (role, time of day) and subtitles |
| Chakra Petch Bold / SemiBold | the machine voice: NG stamp, "เทค 2", "กรอกลับ", REC tag |
| Cinzel (variable) | the ILAG wordmark only |

Sukhumvit Set (the 2026-09-28 poster font) is an Apple system font. It stays for posters made on the Mac only.
Nothing rendered on Contabo or winbox may use it.

Thai under gold gradient text: `background-clip:text` cuts off tone marks (่ ้ ๊ ๋) unless the line has padding above it.
The kit pads `.gold` by .34em above and pulls it back with the same negative margin. Keep that pair on any new gold Thai
line.

## Emblem (PROPOSED)

`templates/emblem.svg` (master render `images/ilag-emblem-1024.png`) is a flat vector derived from the Page's
photographic profile picture:
- a gold double ring on a navy disc, with a kranok flame finial at 12 o'clock;
- a lotus split down the middle: cream on the left (good), dark with thorns and drips on the right (evil);
- gold sparkles on the good side;
- "ILAG" set in Cinzel.

Never recolour the two halves, and never place the emblem on a photo without its navy disc. Never use the
photographic Page logo at watermark size: below about 120 px it turns to mush.

## The kit: 17 tiles on sheet v1, and when each is used

| # | element (`kit.tpl.html?el=`) | text pattern | when |
|---|---|---|---|
| 1 | `emblem` | — | profile picture, cover, title sting, end card |
| 2 | `wm` watermark | emblem + "ILAG" + "ละครสั้นคุณธรรม", top-left at (34, 164), 58% | every story frame; not on the title sting or the end card |
| 3 | `fonts` | — | reference only |
| 4 | `skip` time skip | "<จำนวน><หน่วย>ต่อมา" e.g. หนึ่งเดือนต่อมา | every forward jump in time |
| 5 | `rewcard` same-day rewind | "ย้อนกลับไปเมื่อ<เช้านี้>" | straight after the 15 s hook, back to the start of the day |
| 6 | `flash` + `ftag` flashback | sepia grade + "ย้อนกลับไปเมื่อ<สามปีก่อน>" + "ความทรงจำของ<ชื่อ>"; clock tag "อดีต" top-right | the whole time we are in the past |
| 7 | `now` back to the present | "ปัจจุบัน" | first shot after a flashback |
| 8 | `place` | "<สถานที่>" / "<เวลา> น. · <วัน>" lower-left | first time a location appears in an EP |
| 9 | `name` name card | name in gold / role / red pill "ฉายา: …" | first appearance of each named character in an EP, Chinese-series style |
| 10 | `title` title sting | emblem + «season» + red "EP.N" pill + «EP title» + tagline | 0:12–0:15, closing the hook |
| 11 | `ng` NG stamp | "AI หลุด" / NG / "ILAG STUDIO" + a tape line saying what the AI got wrong | the AI-glitch gag, at most 2 per EP |
| 12 | `rew` rewind | "◀◀ กรอกลับ" + scanlines | straight after the NG stamp |
| 13 | `take2` | clapper "เทค 2" | over the corrected take |
| 14 | `blooper` header | "ฉากหลุด AI" / "ทุกฉากต่อจากนี้คือเทคที่ AI พลาดจริงระหว่างถ่าย" | after the end card, before the blooper reel |
| 15 | `end` end card | ติดตามตอนต่อไป / EP.N+1 / the open question / "<วัน> 20:00 น." (the real day; "พรุ่งนี้" only when the next EP is cut) / "ละครสั้นคุณธรรม by ILAG Studio" | last 4 s of the story |
| 16 | `sub` subtitles | Anuphan, lower third | proposal: the CEO decides whether we burn them in |
| 17 | `safe` Reels safe zones | — | check every overlay against it before render |
| — | `bltag` | "● ฉากหลุด AI" top-right | over every blooper clip |

## Hard rules

1. Every story frame carries the watermark, and every jump in time carries a card. A jump without a card fails QC.
2. Every piece of on-screen text is set by us from this kit. The video model never draws text: prompts carry the
   "no text" line.
3. No em dash in on-screen text, captions or comments (IRON §39).
4. **The NG gag is a role or logic error:** the wrong man slapped, the wrong man arrested, players changing sides.
   Never body horror (melting faces, extra limbs). Never on a victim's pain, and never inside the moral climax.
   At most two per EP.
5. **The blooper reel says "จริง", so it holds only takes the AI really got wrong.** QC keeps an NG bank: every
   funny failed take is tagged with its shot id and what went wrong, instead of being thrown away.
6. The caption keeps "(ละครสร้างด้วย AI)" (`CMO_Workflow_LakornSerial` step 7).

## Files

- `templates/kit.tpl.html` holds every element and is selected with `?el=<id>`.
- `templates/render_kit.py` renders it to `kit.html`, then uses Playwright to make `overlays/<id>.png` (1080×1920,
  transparent) and the 1024 emblem.
- `templates/compose_sheet.py` builds the numbered contact sheet over real frames.
- `templates/build_demo.py` cuts the 44 s demo from «ขายชื่อ» EP1. It runs anywhere ffmpeg runs: winbox renders it
  in about a minute; Contabo needs the render lock.
- `templates/emblem.svg` is the emblem master. `templates/fonts/` holds the OFL fonts and `OFL.txt`.
- `images/ilag-emblem-1024.png` is the emblem render.
- Sheet v1 (`ilag-kit-sheet-v1.jpg`) and the demo (`ilag-kit-demo-v1.mp4`) went to the CEO on 2026-10-26. Their
  masters go to the ILAG Drive folder: the PH files them under `CXO_Rules_GDrive_Filing`.
