---
name: blackliquidity-script
description: >-
  Write the Thai script for a BLACK LIQUIDITY episode — the AI-avatar TikTok
  channel that exposes Forex and Ponzi scams. Use this whenever you are writing,
  rewriting or reviewing a BL script or a topic for one: the section structure
  the channel's episodes actually use, the compliance rules that govern how a
  broker may be named in a public post, and the rules for writing Thai that a
  TTS can read. Use it before touching `videoscript.js`'s prompt too, which must
  mirror these rules. Do NOT use it for cutting or editing a finished episode —
  that is `blackliquidity-cut` — and not for MYPASAKON, LUNGNOTE, TRADER UNCUT
  or ILAG, which are different channels.
audience: [cto, script_writer, developer]
created_by: agent
---

# Writing a BLACK LIQUIDITY script

The channel's voice is a blunt insider warning people about financial scams. The
episodes that worked are structured, not freeform, and the structure below is
measured from BL50 — not invented.

## The section structure

40 spoken lines, each one tagged, each one a single breath the avatar delivers:

| section | lines | job |
|---|---|---|
| `[HOOK-1..4]` | 4 | the claim that stops the scroll, in the first 3 seconds |
| `[PATTERN-1..4]` | 4 | the mechanics of the scam, stated flatly |
| `[CONTEXT-1..5]` | 5 | why now — an event, a court ruling, a number |
| `[MAIN-1..13]` | 13 | the body: the factors, the evidence, the named cases |
| `[CURIOSITY-1..5]` | 5 | the turn — what the audience does not know yet |
| `[SUMMARY-1..9]` | 9 | the checklist they can act on, then the close |

One line per tag, one idea per line. The editor cuts on these boundaries and the
lipsync parts are seated against them, so a line that carries two ideas becomes
a cut that lands in the middle of a sentence.

## Compliance — the part that is not style

Thailand's regulators aim at the **marketing layer**, and they describe conduct,
not vocabulary. BOT's statement of 25 Jun 2026 puts anyone who
**"โฆษณา ประกาศ หรือชักชวนประชาชน"** to trade FOREX under
**พ.ร.ก. การกู้ยืมเงินที่เป็นการฉ้อโกงประชาชน พ.ศ. 2527**, and writes no
carve-out for people who promise no returns. "โฆษณา" and "ประกาศ" sit on their
own, separate from "ชักชวน" — so not inviting anyone is not by itself enough.
DSI's June 2026 operation named **IBs**, not only brokers.

None of this is legal advice. It is why the following are rules rather than
preferences. Full background: memory `project-forex-thai-legal-exposure`, and
the CEO's ruling in `project-ceo-business-direction-2026-09`.

### The three that actually move risk

**1. Never name a broker the channel earns from, in a public post.**
The moment a rebate or IB relationship exists, "just mentioning it" stops being
credible, and it meets a second statute — พ.ร.บ.สัญญาซื้อขายล่วงหน้า 2546, acting
as agent for an unlicensed derivatives business, which needs no victim. The CEO's
own standing rule from 2026-09-17: affiliate links live in closed channels —
LINE OA, closed groups — never in a public post. A broker the channel earns
nothing from may be named as a factual example.

**2. Teach the check, do not rank the brokers.**
This is also the channel's strongest material. Write the criteria:

> "ก่อนเลือกโบรกเจ้าไหนก็ตาม เช็กสามอย่าง หนึ่ง ใบอนุญาตจากหน่วยกำกับจริง
> เข้าเว็บหน่วยงานนั้นแล้วค้นเลขใบอนุญาตเอง อย่าเชื่อโลโก้บนหน้าเว็บโบรก
> สอง จดทะเบียนที่ไหน ถ้าเป็นเกาะเล็ก แปลว่าไม่มีใครกำกับจริง
> สาม ลองถอนก้อนเล็กก่อนเสมอ"

**3. The CTA points at knowledge, never at an account.**
This is where "telling" turns into "soliciting". A content CTA is fine —
"คอมเมนต์คำว่า เช็กลิสต์ ถ้าอยากได้ตารางตรวจโบรก". An account CTA is not.

### Words

| never, in a public script | write instead |
|---|---|
| เปิดผ่านลิงก์ผม · ลิงก์ใต้คลิป | nothing — no link at all |
| รีเบท $x ต่อ Lot · deal ตรง | never mention what the channel earns |
| ทักมา · ทักใต้คลิป | "คอมเมนต์คำว่า …" for a piece of content |
| ใช้เจ้านี้ · แนะนำเจ้านี้ | "เกณฑ์ที่ควรดูคือ…" |
| สมัคร · เปิดบัญชี | "ก่อนตัดสินใจ ให้ตรวจ…" |

If a named broker appears at all, the line that follows it says the channel is
not recommending anyone:

> "ผมไม่ได้แนะนำให้ใช้เจ้าไหน แค่ชี้วิธีดูให้เป็น"

### What the on-screen label does and does not do

Every episode carries `.bl-legal` on every frame — "เนื้อหาเพื่อการศึกษา ไม่ใช่
คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง" (`blackliquidity-cut` §6b).
It states intent. It does not change conduct: a script that offers an affiliate
link is still offering one with a label underneath it.

### The licensed route, when it is wanted

Recommending a broker in public, lawfully, has a door: **TFEX Selling Agent**
(ผู้แนะนำการลงทุนตราสารอนุพันธ์) is the licensed Thai equivalent of an IB —
sit the licence, affiliate with a licensed broker. **Bitkub's referral** (20% of
referred users' trading fees) sits under SEC supervision. Neither is urgent;
both are worth knowing exist before writing a script that wishes they did.

## Say it the way the viewer says it (CEO ruling 2026-09-23)

"อย่าใช้ศัพท์เทคนิคเยอะ เอาง่ายๆ ให้คนดูเข้าใจ". Write what the viewer would
say to a friend, not what an engineer would log:

| instead of | write |
|---|---|
| โดเมน · ทะเบียนโดเมน · WHOIS · DNS | ชื่อเว็บ · ที่จดชื่อเว็บ · "ไม่มีใครเป็นเจ้าของชื่อเว็บนี้แล้ว" |
| หน้าเออเรอร์ · เซิร์ฟเวอร์ล่ม | หน้าเว็บขึ้นว่าเข้าไม่ได้ |
| หน่วยงานกำกับ (on its own) | name it once ("หน่วยงานการเงินของอังกฤษ"), then plain words |

**Show the attempt, not just the result.** When the episode's point is something
we checked ourselves, the viewer follows the steps with us: "นี่คือหลักฐานตอนที่
กูพยายามเข้าเว็บ": each try is its own line with its own screen. The EP57 hook
the CEO wrote is the model: "ใครใช้โบรกนี้รีบเข้าเว็บเช็กด่วนเลย ตอนนี้แม่งปิดเว็บ
เข้าไม่ได้แล้ว นี่คือหลักฐานที่กูพยายามเข้าเว็บ", followed by what was tried.

## Writing Thai that a TTS can read

The script is read aloud by `fal-ai/gemini-3.1-flash-tts`, so it is an input to a
machine before it is prose.

**A space is a pause instruction.** Thai is written with no spaces between words;
the Royal Society keeps the small space for separating phrases and the large one
for ending a sentence. Spacing a phrase out word by word orders the model to stop
inside it — measured 2026-09-18, the same lines ran 47.8s spaced out against
38.2s written properly, and the CEO heard every stop. Write phrases closed up.
Spend a space only where a person draws breath.

**Transliterate Latin brand words**: ติ๊กต๊อก, เฟซบุ๊ก, ไลน์, เซนต์วินเซนต์,
วิกิเอฟเอ็กซ์. The Thai spelling is **for the voice only** (CEO 2026-09-23: "ตอนเรียกชื่อหรือใน
Script เขียนไทยได้เพราะโมเดลจะได้ออกเสียงถูก"). On screen the brand keeps its real spelling
(`WikiFX`, never `วิกิเอฟเอ็กซ์`). Every transliterated brand in a script must have a row
in `.claude/skills/blackliquidity-cut/brand-display.yaml`, the map the editor applies to captions. **But leave short letter+digit names alone** — V2, V3, 3D came
back worse transliterated ("วีทู" was read as "วิทูล").

**Write numbers as closed-up Thai words**: เก้าพันแปดร้อยยี่สิบห้า, not 9825 and
not spaced into pieces, or the model is free to read them digit by digit.

`prototypes/bl-model-bakeoff/tts/thai_tts_prep.py` applies all three
automatically and carries the reasoning; a script that goes through it does not
need to be hand-formatted, but a writer who knows the rules writes cleaner input.

## Before handing a script on

- every line carries its tag, one idea per line
- no broker the channel earns from is named
- no link, no account CTA, no mention of the channel's own rebate
- claims that name a person, company or number are checkable, and the script
  says where they came from
- the caption carries the long disclaimer (`blackliquidity-cut` §6b)

## Field notes
- 2026-09-23 [MISSING] §structure — how long a script will run: measured speech-only rate on the channel's Gemini voice is **16.6 chars/s** (EP54 16.64, EP55 16.62, silencedetect on the real TTS files). EP55: 2,470 spoken chars → a 167.66 s TTS track. Estimate from that, never from a finished cut's length divided by the script's characters. That shortcut gave the CTO 22 chars/s and a 110 s forecast that was 52 % off · evidence: task-77a2e043 RUNLOG.md · status: pending
- 2026-09-23 [WRONG] §structure — correction to the note above: 16.6 chars/s is SPEECH-ONLY. The full TTS track also carries the breath gaps between the 40 lines, so the whole-track rate is lower. It is ~13.2–14.7 chars/s: EP55 v1 2,470 chars → 167.66 s, v2 1,750 chars → 133.1 s. Forecast track length from the whole-track rate. The CTO used 16.6 and forecast v2 at 105 s against 133 s · evidence: task-77a2e043 RUNLOG.md (tts v2 line) · status: pending
- 2026-09-23 [MISSING] §Writing Thai for TTS — a transliterated brand was also shown on screen in Thai; the CEO ruled the Thai spelling is for the voice only and the screen shows the real brand spelling · evidence: CEO ruling 2026-09-23 (WikiFX) · status: promoted
- 2026-09-23 [MISSING] §plain words — the EP57 v1 script used โดเมน / ระบบทะเบียนโดเมนสาธารณะ / เออเรอร์; the CEO ruled plain words only and asked for the attempt to be shown step by step · evidence: CEO ruling 2026-09-23 on EP57 v1 · status: promoted
