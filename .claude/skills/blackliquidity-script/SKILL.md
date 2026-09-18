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
วิกิเอฟเอ็กซ์. **But leave short letter+digit names alone** — V2, V3, 3D came
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
