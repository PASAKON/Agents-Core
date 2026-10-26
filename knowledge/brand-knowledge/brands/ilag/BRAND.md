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

## The hook: a narrated fast-cut montage (CEO 2026-10-26, on trial from the pilot EP1)

The CEO, chat 26 Oct about 21:40 TH: "นี่คือ Hook แบบจีน แบบตัดถาพเร็วๆ / ชายคนนี้กินแกะ อย่างทั้งตัว ได้ภายใน ...
เค้าสามารถกินได้ทุกอย่าง .... ตาชั่งที่บ้าน เขาพัง .... เขาดื่มผมวัวหมดทั้งตัวจนหมดทุกวัน วันนี้เขาจะ กิน ....
พ่อของเขาต้องทำอะไรบางอย่าง -> แล้วเริ่มเริ่อง / ช่วง Hook ตัดสลับไว้ๆ ใช้หลาย Fotage เป็น Hookคนดูจะสนใจมากๆ
ลองใช้กับ ละครสั้น ILAG ดูได้นะ".

A narrator tells the viewer who this EP is about in six short lines, each wilder than the last, over a fast run of
shots, and stops just before today's event. It replaces the CMO's cold-open formula for 0-12 s (`CMO_Workflow_LakornSerial`
field note 2026-10-26). PROPOSED until the pilot's 72 h numbers are in.

| beat | his example | what the line does |
|---|---|---|
| 1 | "ชายคนนี้กินแกะทั้งตัวได้ภายใน ..." | who, and one trait pushed past normal, with a number |
| 2 | "เค้าสามารถกินได้ทุกอย่าง" | widens the trait |
| 3 | "ตาชั่งที่บ้านเขาพัง" | an object proves it, and it is funny |
| 4 | "เขาดื่มผมวัวหมดทั้งตัวจนหมดทุกวัน" | a daily habit, one step more absurd |
| 5 | "วันนี้เขาจะกิน ...." | today's event, left unfinished |
| 6 | "พ่อของเขาต้องทำอะไรบางอย่าง" | the pressure lands on someone else; hard cut into the story |

- **The voice:** one narrator in the third person ("ชายคนนี้", "เขา", "ซอยนี้"), present tense, one short line each, no
  silence between lines, the same narrator voice on every EP. Delivery as measured on the Thai narration channels: about
  14 Thai characters a second, the pitch lifted on the payoff word (Agents-Wikis
  `research/2026-10-23-thai-dub-chinese-drama-teardown.md` §4). Never imitate a real narrator's timbre.
- **The narrator engine (CEO 2026-10-26 about 23:15 TH, on the $0 demo task-ee1dbcf0):** "Hook 15 วิ แบบจีน อันนี้ผ่านเลย
  ติดแค่เสียง อาจจะต้องใช้ เสีนงจาก ElevenLab V4 นะให้ดูมี น้ำเสียง ขึ้นลง แบบ นักล้่าเรื่องตัวจริง". The demo's montage, lines
  and cards passed; its voice did not (edge-tts NiwatNeural sped up 32% to fit). The narrator is ElevenLabs v4 on fal,
  one call for all six lines so the rise and fall carries across them, never sped up afterwards; edge-tts is a $0
  stand-in for drafts only. Measured v4 Thai pace: 10.9 characters a second with pauses, 13.2 speech only (CnDrama EP1,
  13,855 characters, 25 Oct), so six lines that fit 15 s run about 160-175 characters, spaces not counted. Which v4 voice
  is the CEO's pick by ear (takes in `/opt/MoonieXHQ/Work/task-e58b9235/voice-v4/`): PENDING.
- **The pictures:** a new shot on every line, often two: 10-14 hard cuts in the first 12 s (about 0.7-1.5 s each), no
  transitions, a music bed under the voice. Each shot shows what its line says.
- **Where the shots come from:** moments from later in the same EP (a flash-forward), plus inserts that prove a fact
  (an object, a pile, a crowd). A shot with a named character comes from the EP's own shoot, so the face holds. An insert
  with no named character may come from a free lane once one is measured (the ChampaVeo PH).
- **Truth:** every line is true in this EP and is shown later in it. The hook never gives away the twist or the karma
  ending.
- **Text:** the narration is burned in as subtitles (`sub`); the watermark stays on, because these are story frames.
- **12-15 s:** the title sting (`title`), then the same-day rewind card (`rewcard`) into the story.
- **Why it suits us (CMO):** short shots need no lip sync and leave the AI no time to drift, so the first 15 s, where
  most viewers leave, becomes the cheapest and safest part of the EP.
- **Measure:** 3 s and 15 s retention at 72 h, against "ขายชื่อ" EP1-3 on the same Page.

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
