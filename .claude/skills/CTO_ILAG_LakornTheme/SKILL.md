---
name: CTO_ILAG_LakornTheme
description: "The one look of the ILAG ละครสั้นคุณธรรม channel (Page «ละครสั้นคุณธรรม by ILAG Studio»): navy + gold, approved by the CEO 2026-09-28 on EP4 «ขายฝากนาแม่». Covers the daily 'รู้หรือไม่?' knowledge poster (ChatGPT, 4:5, Page logo in the footer) and the 15-30 s Story clip with its end card, both made by tools/ilag_theme.py. Trigger on /CTO_ILAG_LakornTheme and on 'รู้หรือไม่', 'โปสเตอร์ความรู้', 'โพสความรู้', 'Story', 'สตอรี่', 'การ์ดท้ายคลิป', 'end card', 'ธีมช่อง', 'ธีมน้ำเงินทอง', 'Keep Theme'. Use instead of designing a new look, a local text composite, or a free-hand image prompt. Episode covers stay in CTO_ChatGPT-Image_LakornCover."
created_by: agent
author: {role: cto, date: "2026-09-28"}
audience: [cto, browser_operator, developer]
---

# ILAG lakorn theme — navy + gold

> "โปสเตอร์กับ Story ผ่านแล้ว นะ เราต้อง KEEP Theme ไว้นะ เป็นน้ำเงิน เหลือง แบบที่คุณทำ ทั้งโปสเตอร์ และ Card
> ที่แสดงบน Video เมื่อ Worker ทำออกมาเราจะได้แบบเดิม รวมถึง Font และการจัดวางด้วย / เขียนลง Skill ได้เลย
> สำหรับช่อง ILAG ละครสั้น เราจะใช้ธีมนี้เป็นหลัก" — CEO, 2026-09-28

Every value that decides the look is in `tools/ilag_theme.py`. Do not retype a colour, font size or box
position anywhere else; run the tool. A change to the theme is a CEO decision, and it lands in the tool first.

## Model scope — read first

**Proven on:** ChatGPT **Plus web UI** (gpt-image) through `tools/chatgpt_images.py` on the Mac automation
Chrome `http://127.0.0.1:9223`, for the poster. Pillow with raqm plus Sukhumvit Set, and ffmpeg, for the Story
card. One film: EP4 «ขายฝากนาแม่», 2026-09-28. ChatGPT spelled all the Thai correctly in that one poster (n=1).

The Story card is local and deterministic: the tool rebuilt the approved clip bit for bit (PSNR inf at 10 s
and 21 s). The logo step put the logo at the approved position and size (checked by eye). The poster prompt
is the approved prompt, plus the parts of the approved output that the prompt left to chance. **That pinned
version has not been fired yet (n=0).** Compare its first output with the reference. If it drifts, fire the
approved prompt verbatim from `approved-round1.json` and add a Field note.

## Reference — the look, on disk

`/Users/gob/MoonieXHQ/Assets/Agents/Core/ilag-theme/`

| file | what |
|---|---|
| `approved-poster-final-1080x1350.png` | the approved poster, logo pasted (md5 75300d04…) |
| `approved-poster-chatgpt-raw.png` | ChatGPT's 1122x1402 output before the logo |
| `approved-story-24s.mp4` | the approved Story, 24 s, end card from 19 s (md5 c8a673e7…) |
| `approved-story-card-overlay.png` | the card alone, 1080x1920 RGBA |
| `approved-round1.json` | the ChatGPT job, verbatim (`know-ep4-full` = the approved prompt) |

Plan (daily rhythm, 14-day calendar, accuracy rules): https://claude.ai/artifact/5rYdq8fP5AwhAebuo6aGrr
Law facts already checked: `mooniex:research/2026-09-28-did-you-know-film-law-facts.md`.

## Theme tokens (in `tools/ilag_theme.py`)

| token | value | where |
|---|---|---|
| `NAVY` | #0A1A38 (#061835–#0E1B3C measured) | poster text panel |
| `GOLD_METAL` | #E49C1D / #F7C440 / #FDE165 | "รู้หรือไม่?" headline gradient |
| `GOLD` | #F7C64E (#F6C048–#F9CD57 measured) | tip box, number discs, rules, divider |
| `CARD_BG` | #0C0D1E at 88 % | Story card box |
| `CARD_GOLD` | #F6C453 | card line 1 |
| `CARD_WHITE` / `CARD_CREAM` | #FFFFFF / #FFF4D6 | card lines 2 / 3 |
| font | Sukhumvit Set Bold (face 5) and Semi Bold (face 4), raqm layout | card; poster text is drawn by ChatGPT |

## Poster layout (4:5, delivered 1080x1350)

Top to bottom:
1. **Top ~40 %:** one character from the cast sheet, in the film's own place and light (EP4: golden-hour
   rice field). Face from the sheet, never invented.
2. **Navy panel** with thin gold rice-ear ornaments at the left and right edges.
3. **"รู้หรือไม่?"** very large, metallic gold, centred.
4. **Sub-headline**, white, centred, a thin gold line under it.
5. **Three numbered points**, white, left-aligned, each number in a gold disc with a navy digit.
6. **Tip box**: full-width rounded gold box, navy bold text, one line of advice.
7. **Footer** over a dim dusk rice-field strip, under a thin gold line. Two small white lines on the left:
   `ดูละครสั้น «<title>» ได้ที่เพจ` / `ละครสั้นคุณธรรม by ILAG Studio`. Then a vertical gold divider, then the
   Page logo in a circle on the right (ChatGPT draws an empty white circle, `logo` fills it).

## Story end card (1080x1920, last 5 s)

Rounded box (60, 1440)–(1020, 1740), radius 28, `CARD_BG`. Three centred lines:

| y | text | font | colour |
|---|---|---|---|
| 1520 | `ดูเต็มเรื่อง «<title>»` | Bold 60 | `CARD_GOLD` |
| 1610 | `ที่เพจ ละครสั้นคุณธรรม by ILAG Studio` | Semi Bold 44 | `CARD_WHITE` |
| 1680 | the open question | Semi Bold 40 | `CARD_CREAM` |

Encode: libx264 crf 20, preset medium, yuv420p, AAC 128k, +faststart.

## Workflow — the daily knowledge poster

0. **Pick the fact.** It comes from an EP already posted, and it is checked against a primary source
   (law text, ฎีกา, the agency's own page) before it goes on a poster. Record the source in the research
   wiki. No source, no poster.
1. **Write the spec** (example: `examples/know-ep4-k1.spec.json`): `name`, `attach` (cast sheet), `character`,
   `scene`, `sub`, three `points`, `tip`, `title`. Keep each point to one sentence a farmer can read aloud.
2. `tools/ilag_theme.py poster-job <spec> <job.json>`, then
   `tools/chatgpt_images.py --cdp-url http://127.0.0.1:9223 --json <job.json> --out <dir> --timeout-s 600`.
   ChatGPT Plus is a flat fee: no credit ask needed.
3. **Check every Thai word** on the image against the spec, syllable by syllable, tone marks included. A wrong
   word is fixed in the same chat (`--continue`), never by painting over it.
4. `tools/ilag_theme.py logo <chatgpt.png> <final.png>`. It fetches the Page logo itself.
5. **Look at it next to `approved-poster-final-1080x1350.png`.** Same panel, same gold, same footer. If it
   drifts, see Model scope.
6. **Post** as the Page (see Rules 5 and 6): the photo with a short caption, then comment 1 and comment 2.

Comment 1: `ดูละครสั้น «<title>» เต็มเรื่องได้ที่นี่เลยครับ 👇 <EP link>`
Comment 2: `อยากฟังเรื่องไหนต่อ คอมเมนต์บอกกันมาได้เลยครับ แอดมินจะหยิบไปทำเป็นละครสั้นตอนต่อไป / แท็กเพื่อนที่ควรรู้เรื่องนี้ไว้ด้วยนะครับ`

## Workflow — the daily Story

1. Choose 15–30 s from Act 1 or Act 2: the hook plus the key message. **Never an Act 3 shot. Never the
   ending.** The CEO's rule: "ห้ามสปอยตอนจบ".
2. The question on the card is open: it asks what happens, it never answers it
   (EP4: `แม่คำปุนจะรักษานาไว้ได้ไหม?`).
3. `tools/ilag_theme.py story --film <final.mp4> --start <s> --dur <15-30> --title <title> --question <q> <out.mp4>`.
   The tool refuses a clip outside 15–30 s and a card line too long for the box.

## Rules

1. **HARD — one theme.** Colours, fonts, sizes and positions come from `tools/ilag_theme.py` and nowhere else.
   No per-post variations, no new template.
   **Why hard:** CEO ruling 2026-09-28, the channel's identity ("เราจะใช้ธีมนี้เป็นหลัก").
2. **Legal facts need a checked source.** Measured traps from the EP4 research:
   - Interest over 15 % a year on a ขายฝาก of farm land is โมฆะ (ฎีกา 5056/2562). Never write "ลดเหลือ 15%".
   - 1359 is สศค. (Mon–Fri 08.30–16.30) and does not cover ขายฝาก. ขายฝาก complaints go to กรมที่ดิน 0-2141-5555.
   - "ตาชั่งตรวจทุก 2 ปี" is unverified. Write "ดูวันหมดอายุบนเครื่องหมาย".
   - No fixed-price claims such as "น้ำขวดละ 100 ผิดแน่นอน".
   - 1784 (ปภ.) is 24 h, confirmed. 1599 is not re-verified.
3. **Do not set the poster text locally with the repo's Kanit.** The Kanit woff2 in the repo is a Thai subset
   with no "?", digits or Latin, so Pillow prints boxes. The rejected local composite is why ChatGPT draws the
   whole poster.
4. **The Page logo comes from the public Page's `og:image`.** The Graph `/{page}/picture` endpoint returns
   the grey default silhouette for this Page. `ilag_theme.py` does this and keeps a cached copy.
5. **Posting is approved.** CEO 2026-09-28: "หลังจากนี้ โพส ลง Facebook ได้เลย". Post without a per-post ask. The
   money, secrets and delete rules still apply, and `fb_reel_post.py` keeps its rules: publish once, never
   `--allow-repost`, exit 6 = never re-publish, exit 7 = stop.
6. **Comments go out as the Page, never as a person.** The comment box must read
   `แสดงความคิดเห็นในชื่อ ละครสั้นคุณธรรม by ILAG Studio`. `fb_reel_post.py` refuses anything else with exit 7.
7. **Posting times live in a LungNote note until a Cron system exists** (CEO: "เก็บเป็น Note ไว้ก่อน ค่อยมาสร้าง
   ระบบ Cron ทีหลัง"): 12:00 poster + comment 1 + comment 2 · 19:00 Story · 20:00 a new EP on its day.
8. **A recurring browser job is not a loop in a C-level tab** (IRON §42). Delegate it with a replay script.

## When NOT to invoke

- An episode cover or thumbnail: `CTO_ChatGPT-Image_LakornCover`.
- BLACK LIQUIDITY / MYPASAKON / TRADER UNCUT: other channels, other looks.
- ILAG festival films (Do Not Disturb, Sorry Sir): their Poster/ rules.

## Field notes

- 2026-09-28 [MISSING] §Rules 6 — EP4's Reel published and VERIFIED (videos/1973008630041783), but the
  first comment was refused before typing: the comment box read `Dorsine Gobb`. The Mac Chrome :9230 session
  had been left as the person after the groups work. The fix is the Page's own "สลับเลย" (switch now) button
  before any comment. A daily posting tool must do that switch itself and read the identity back · evidence:
  scratchpad `know/ep4_publish.log` EXIT 7 · status: pending
- 2026-09-28 [MISSING] §Poster layout — the approved prompt never asked for the dusk rice-field footer strip,
  the rice-ear ornaments or the gold number discs; ChatGPT added them. They are now written into the prompt so
  a second run keeps them. Untested (n=0) · evidence: `approved-poster-chatgpt-raw.png` · status: pending
