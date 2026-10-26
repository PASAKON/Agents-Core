# ILAG — ละครสั้นคุณธรรม by ILAG Studio

Owner: CMO. Written 2026-10-26 (CMO Ging); v2 the same evening.

**Theme v2 is LOCKED by the CEO (chat, 2026-10-26):** "Theme ILAG ที่อยากได้จริงๆ อยากได้ เป็น ทอง ขาว ดำ / ทองสำหรับ
พวก font ขอบ หรือจุด เด่น จุดตัด / ส่วน ขาว ดำ เป็น สี หรือ พื้นหลังต่างๆ ให้อารม์ เหมือน YIN YANG ตัวดี ตัว ร้าย เหมือน
ดอกบัว ใน โลโก้ของเราที่มี ส่วนขาวและ ส่วนที่ดำ". It supersedes the navy and gold theme of 2026-09-28. `tools/ilag_theme.py`
and skill `CTO_ILAG_LakornTheme` still draw navy until they are moved (PH IlagLakorn). Do not make a new navy piece.

The channel kit is **PROPOSED**. The CEO asked for it on 26 Oct ("ช่วยออกแบบให้หน่อยและทำมาให้ดู เพื่อเอาไว้เป็นกฎถาวรใน
การทำช่อง"). He did not pick from sheet v1 and asked to see every picture with his fixes in (Q-20261026-1017-d075).
Sheet v2 (20 tiles) went to him on 26 Oct. A tile becomes LOCKED when he answers its number. Until then the pilot EP
uses v2 as it is. Do not redesign a tile he has not rejected.

## What the brand is

- FB Page "ละครสั้นคุณธรรม by ILAG Studio", id 61594116376333. It posts Thai moral dramas made with AI: the
  wrongdoer meets karma, and the family comes through. The story rules are in `CMO_Standard_Story_ThaiMoralDrama`.
- CEO, 26 Oct 2026: the Page is back on, because followers are rising (+2–4 a post). The new format runs 10–20 min
  per EP. Each EP is complete in itself, opens with a 15 s hook, has a twist, and pulls into the next EP. Our edge
  is AI mistakes that make people laugh: "AI ไปตบหน้าตัวละครผิดตัว … ตำรวจจับผิดคน … การตีลูกบอล มีการเปลี่ยนฝั่ง".
- **Four pillars, in every EP at once** (CEO 26 Oct: "เน้น ให้ คุณธรรม แง่คิด ความรู้ และ มุขตลกไปพร้อมๆ กัน ในช่องของเรา"):

  | pillar | carried by |
  |---|---|
  | คุณธรรม | the story itself: do good, get good; do wrong, meet karma |
  | แง่คิด | the `lesson` card before the end card |
  | ความรู้ | at least one `fact` pop-up "รู้ไว้" with a fact the viewer can use (law, money, health), checked before it airs |
  | มุขตลก | the AI-glitch gag (`ng` → `rew` → `take2`) and the blooper reel |

- A sister identity is the ILAG Studio YouTube "The Stamp" (red rubber stamp #B8322A, live since 2026-08-07). Kit v1
  borrowed its red for the NG stamp; v2 drops the red, because the CEO's palette is gold, white and black only. The
  `stamp-v2-*` pictures belong to that channel, not to this Page.

## Palette (v2, CEO 2026-10-26)

Gold is for type, borders, highlights and cut points. White and black are the grounds. The good side is white and the
evil side is black, like the two halves of the lotus in the logo.

| token | hex | status | use |
|---|---|---|---|
| BLACK | `#0A0A0A` | LOCKED | the evil side; card grounds, plates, the watermark pill, the sheet |
| WHITE | `#FFFFFF` | LOCKED | the good side; the good character's card, the lesson plate, the top half of the split |
| GOLD | `#F7C64E` | LOCKED | flat gold: borders, rules, tags, pills, small text, number badges |
| GOLD_METAL | `#FDE165` → `#F7C440` → `#E49C1D` | LOCKED | gold display type and the seam of the split, top to bottom |
| STAMP_GOLD | `#E8B230` | PROPOSED | NG stamp ink (red in v1; the CEO can ask for red back) |
| INK | `#111111` | PROPOSED | text on white and on gold fills |
| MIST | `#C9C9C9` | PROPOSED | second lines on black (flashback, blooper header) |

The split: white over black with an S-shaped gold seam, the logo sitting on the seam (`render_kit.py` `split()`).
It is the ground of the title sting and the end card.

[SUPERSEDED 2026-10-26 by the CEO's v2 theme] NAVY `#0A1A38`, CARD_CREAM `#FFF4D6`, CARD_BG `#0C0D1E` @ 88% (LOCKED
2026-09-28), and v1's STAMP_RED `#B8322A`, INK `#231F1C`, PAPER `#F6EEDD`, and the sepia flashback.

## Type (PROPOSED; every file is OFL, in `templates/fonts/` with `OFL.txt`)

| font | role |
|---|---|
| Taviraj Bold / SemiBold / Medium | time cards, place names, character names, EP titles, end card: the lakorn voice |
| Anuphan (variable) | second lines (role, time of day), subtitles, the "รู้ไว้" text |
| Chakra Petch Bold / SemiBold | the machine voice: NG stamp, "เทค 2", "กรอกลับ", the "รู้ไว้" tag |
| Cinzel (variable) | the ILAG wordmark and EP pills only |

Sukhumvit Set (the 2026-09-28 poster font) is an Apple system font. It stays for posters made on the Mac only.
Nothing rendered on Contabo or winbox may use it.

Thai under gold gradient text: `background-clip:text` cuts off tone marks (่ ้ ๊ ๋) unless the line has padding above it.
The kit pads `.gold` by .34em above and pulls it back with the same negative margin. Keep that pair on any new gold Thai
line. Gold type on the white half carries a thin black outline (`.ol`), or it does not read.

## Logo (LOCKED)

The Page's own profile picture is the logo: gold 3D "ILAG" over a lotus split light and dark, thorns on the dark half,
in a gold ring, on a black square (`images/ilag-page-logo-1080.jpg`). CEO 2026-10-26: "ILAG เรามี Logo อยู่แลวนะ
ไม่ต้องทำใหม่".
- `logo.png` (1001×1001, transparent) is the same picture lifted off its black square by `templates/cut_logo.py`:
  the disc inside the ring stays opaque and the glow beyond it becomes see-through gold. Nothing is redrawn.
  It is rebuilt in the work folder (`REBUILD.md` step 0), not kept in git (1.4 MB, ADR 0030).
- Never redraw, recolour, re-letter or crop it inside the ring. Smallest use is 120 px (the watermark); below that it
  turns to mush.
- [SUPERSEDED 2026-10-26] Kit v1's flat redraw `emblem.svg` / `ilag-emblem-1024.png` was rejected by the CEO and removed.

## The kit: 20 tiles on sheet v2, and when each is used

| # | element (`kit.tpl.html?el=`) | text pattern | when |
|---|---|---|---|
| 1 | `emblem` logo page | the logo on the split, ILAG STUDIO, the pillars, 220 and 120 px sizes | reference only |
| 2 | `wm` watermark | logo 120 px + "ILAG" in gold + "ละครสั้นคุณธรรม" in white, black pill with a gold rim, top-left at (30, 162) | every story frame; not on the title sting or the end card |
| 3 | `fonts` | fonts and swatches | reference only |
| 4 | `skip` time skip | "<จำนวน><หน่วย>ต่อมา", gold on a black vignette | every forward jump in time |
| 5 | `rewcard` same-day rewind | "ย้อนกลับไปเมื่อ<เช้านี้>" | straight after the 15 s hook, back to the start of the day |
| 6 | `flash` + `ftag` flashback | black-and-white grade + "ย้อนกลับไปเมื่อ<สามปีก่อน>" in white + "ความทรงจำของ<ชื่อ>"; gold-rimmed tag "อดีต" top-right | the whole time we are in the past |
| 7 | `now` back to the present | "ปัจจุบัน" | first shot after a flashback |
| 8 | `place` | "<สถานที่>" / "<วัน> <เวลา> น." lower-left, gold bar | first time a location appears in an EP |
| 9 | `name` wrongdoer's card | black ground, name in gold, role in white, gold pill "ฉายา: ..." | first appearance of a wrongdoer in an EP |
| 10 | `namegood` good character's card | white ground, name in black, role in dark grey, gold pill | first appearance of a good character in an EP |
| 11 | `title` title sting | the split + logo on the seam + season name in gold + gold EP.N pill + EP title in white (no quote marks) + tagline in gold | 0:12-0:15, closing the hook |
| 12 | `fact` "รู้ไว้" | gold tag + one or two lines on black with a gold edge, lower-left | at least once per EP, where the story touches a usable fact |
| 13 | `ng` NG stamp | gold stamp "AI หลุด" / NG / "ILAG STUDIO" + black tape with a gold edge saying what the AI got wrong | the AI-glitch gag, at most 2 per EP |
| 14 | `rew` rewind | "กรอกลับ" + scanlines | straight after the NG stamp |
| 15 | `take2` | clapper "เทค 2" on black with a gold edge | over the corrected take |
| 16 | `lesson` takeaway | "ข้อคิดจากตอนนี้" in gold + one line on a white plate with a gold rim | 4-5 s before the end card, every EP |
| 17 | `blooper` header | "ฉากหลุด AI" / "ทุกฉากต่อจากนี้คือเทคที่ AI พลาดจริงระหว่างถ่าย" | after the end card, before the blooper reel |
| 18 | `end` end card | the split; ติดตามตอนต่อไป / the open question in black on white / logo / EP.N+1 / "<วัน> 20:00 น." (the real day; "พรุ่งนี้" only when the next EP is cut) / "ละครสั้นคุณธรรม by ILAG Studio" | last 4 s of the story |
| 19 | `sub` subtitles | Anuphan, white on a 45% black box, lower third | burned in on the pilot EP from the script's own lines (CMO 2026-10-26); its 72 h numbers decide after |
| 20 | `safe` Reels safe zones | — | check every overlay against it before render |
| — | `bltag` | gold dot + "ฉากหลุด AI" top-right | over every blooper clip |

## Hard rules

1. Every story frame carries the watermark, and every jump in time carries a card. A jump without a card fails QC.
2. Every piece of on-screen text is set by us from this kit. The video model never draws text: prompts carry the
   "no text" line.
3. No em dash in on-screen text, captions or comments (IRON §39), and no `« »` in any Thai text (CEO 2026-10-26).
   A title alone on a card takes no quote marks; inside a sentence it takes straight quotes "...".
   `scripts/check-post-text.sh` refuses both.
4. **The NG gag is a role or logic error:** the wrong man slapped, the wrong man arrested, players changing sides.
   Never body horror (melting faces, extra limbs). Never on a victim's pain, and never inside the moral climax.
   At most two per EP.
5. **The blooper reel says "จริง", so it holds only takes the AI really got wrong.** QC keeps an NG bank: every
   funny failed take is tagged with its shot id and what went wrong, instead of being thrown away.
6. The caption keeps "(ละครสร้างด้วย AI)" (`CMO_Workflow_LakornSerial` step 7).
7. **Every EP carries all four pillars** (table above). QC asks for each one: the lesson card, at least one checked
   fact, the gag. A "รู้ไว้" fact that is not checked does not air.
8. **Colour:** gold, white and black only. Good on white, evil on black. No navy, cream, red or sepia in a new piece.
9. **The logo is the Page's own** (§Logo). Never redrawn.

## Files

- `templates/kit.tpl.html` holds every element and is selected with `?el=<id>`.
- `templates/render_kit.py` renders it to `kit.html`, then uses Playwright to make `overlays/<id>.png` (1080×1920,
  transparent).
- `templates/compose_sheet.py` builds the numbered 20-tile contact sheet over real frames (`out/ilag-kit-sheet-v2.jpg`).
- `templates/build_demo.py` cuts the 44 s demo from "ขายชื่อ" EP1 (`out/ilag-kit-demo-v2.mp4`). It runs anywhere
  ffmpeg runs: winbox renders it in about a minute; Contabo needs the render lock.
- `images/ilag-page-logo-1080.jpg` is the logo; `templates/cut_logo.py` makes the transparent `logo.png` from it.
  `templates/fonts/` holds the OFL fonts and `OFL.txt`. Rebuild steps: `templates/REBUILD.md`.
- Sheet v1 and demo v1 went to the CEO on 2026-10-26 and were not picked. Sheet v2 and its 20 tiles went the same
  evening. Their masters go to the ILAG Drive folder: the PH files them under `CXO_Rules_GDrive_Filing`.
