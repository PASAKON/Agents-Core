---
name: CMO_Standard_HumanVoice_TH
kind: standard
description: "STANDARD — Final pass on Thai text we publish for outsiders (captions, first comments, comment replies, LINE groups, chatbot templates): Thai AI tells with real before/after, banned characters, lines that stay. Trigger on /CMO_Standard_HumanVoice_TH and \"ให้ดูเป็นมนุษย์\", \"ตอบคอมเม้นต์\", \"ไลน์กลุ่ม\", \"โพสต์สาธารณะ\". Not for spoken dialogue."
owner: CMO
created_by: agent
author: {role: cmo, date: "2026-10-13"}
audience: [cmo, content_strategist, script_writer, browser_operator]
---

# What human-sounding Thai looks like when we publish it

CEO 2026-10-14 (via SomPong): everything the org writes for outsiders (LINE groups, public posts, comment
replies, chatbots) should read as human as possible. This is the **Thai companion** to the `humanizer` skill
(github.com/blader/humanizer, MIT, 26 patterns, English only). Humanizer supplies the method and the pattern
families; this file supplies what those patterns look like in Thai, the characters the CEO has banned, and the
lines that must never be touched. It is a **last pass on final text**, never a drafting tool.

## When to run it, and when not

- Run it on the final text of: Facebook/YouTube/TikTok captions, first comments, comment replies (`docs/promo/REPLY-VOICE.md`
  says whose voice), LINE group messages, public posts, chatbot reply templates (`CXO_Knowledge_LINE_Messaging`).
- Do NOT run it on: spoken dialogue in a film script (Mimi speaks in short rhymes on purpose), a quoted line, a title,
  a proper name, a promo code, a deliberate parody. The Friday clip's "ข่าวด่วนในบ้าน: พบสุนัขดำนั่งเฝ้าประตู…" is a news
  parody on purpose: that is the page's voice, not a tell.
- **A writing sample beats this list.** If the page or the CEO already has real posts in the voice, match them
  (Mimi: the posts live in the `mimi-*` caption and comment files under `docs/scripts/`; the CEO: `docs/promo/REPLY-VOICE.md` and `Wikis/voice-samples/`).
  When a rule below fights the sample, the sample wins and you say so in one line.
- Humanizer is not vendored into Agents-Core yet (the CTO's job, COO briefs it). Until then read the copy at
  `/opt/MoonieXHQ/Projects/MoonieX/SomPong/.claude/skills/humanizer/SKILL.md`, in its **embedded mode**: final text only,
  no commentary, no "audit" section in the output.

## The pass (4 steps, in this order)

1. **Facts list.** Write down every number, time, name, link, code and claim in the text. After the pass the list
   must be identical (step 4 checks it).
2. **Humanizer, embedded mode.** The families that carry over to Thai: staging and filler openers, uniform rhythm,
   inflated or promotional wording, decoration (emoji, bullets, bold), leftover template phrases, and the wrong
   reader (writing at the audience instead of to one person).
3. **The Thai tells below.** Fix each one you find; leave alone what is not there. A clean text comes out unchanged.
4. **Gates:** `bash scripts/check-post-text.sh <file>` (the characters), then the facts list, then read it aloud once.

## The spec

1. **HARD, characters.** None of `—` `–` `…` `“ ” ‘ ’` `« »` `·` `→ ←` `×` in text published in the CEO's or ILAG's name.
   Use a line break or a space, `-` , `...`, straight quotes. Rule and reasons: `docs/promo/WRITING-RULES.md`; enforced by
   `scripts/check-post-text.sh`. For the Mimi page I apply it too (the page is run from the CEO's family account and the gate
   exists); the CEO may rule otherwise.
   **Why hard:** a post under his name cannot be un-seen once public, and the em dash is the clearest AI tell on a Thai phone
   keyboard (CEO ruling 2026-09-17).
   **`« »` reach further (CEO 2026-10-26, verbatim: "เราไม่ใช้ <<>> กันใน ภาษาไทย นะ").** No Thai text we write carries them:
   on-screen cards and subtitles, scripts, captions, pages and messages for the CEO, and our own docs where they quote
   Thai (write "..." there too, so the habit does not leak into output). Use straight quotes "..." where a quote mark
   is needed. A title standing alone on a card takes none. Real case: ILAG kit v1 tile 10 drew «ตบผิดคน» and the end card
   in `tools/ilag_theme.py` drew ดูเต็มเรื่อง «title». Both were fixed on 26 Oct, and 130 lines in our skills, the ILAG brand files and the theme tool were switched to "...".
2. **HARD, lines that stay word for word.** The AI-disclosure sentence ("ภาพและเสียงสร้างด้วย AI", "ถ้าเสียงมีมี่เพี้ยนตรงไหนขออภัยด้วย")
   and the true-story line ("ดัดแปลงจากเรื่องจริงในบ้านของเรา"). Only the separator between them may change.
   **Why hard:** the AI label is a platform and honesty requirement; softening or dropping it is a policy violation.
3. **HARD, no new facts.** The pass changes how a sentence is said, never what it claims. Never add an age, a date, a
   count, a quote or a feeling the source did not state, and never make a claim about the real family or Mimi that
   the CEO has not given.
   **Why hard:** these are claims about real people, in the CEO's name.
4. **Particles belong to the page.** Mimi's admin voice is female and warm (นะคะ, ค่ะ). Do not flip it to ครับ, and do not put a
   particle on every line (see tell 6). The BL/IB chatbot voice is ครับ: keep it, two or three times per message, not per line.
5. **One ask per post.** A caption invites one thing, once. (Mon 12 Oct caption invited three times:
   "ช็อตไหน…ที่คุณชอบที่สุด?", "บอกเป็นตอนกับช็อตก็ได้…", "เล่าให้มีมี่ฟังใต้โพสต์นี้ได้เลย".)
6. **Phone shape.** Short lines, one idea per line, a break where a person would pause. A comment sent as one
   run-on paragraph gets line breaks. Emoji only where a real person would put one, never as a bullet.
   **Caution, comments posted by `tools/fb_cdp_do.py`:** in the Facebook comment box Enter sends. A newline typed by the tool may
   post the comment cut after its first line, and nobody has tested Shift+Enter there. Until a test action has proved a
   multi-line comment lands whole, first comments and replies stay ONE paragraph (captions in a post composer take line breaks fine).

## Thai AI tells

Each row says what to look for and the fix. **Examples are labelled REAL (from our files, path given) or
CONSTRUCTED (written to show the tell; the Mimi corpus does not contain it).** Of the ten tells, our own Mimi
text holds only the first four; the rest have not shown up there. Do not invent a tell to have something to fix.

| # | Tell | Fix |
|---|---|---|
| 1 | A banned character (—, –, ·, …, « ») inside a sentence or between two lines | Break the line or use a space. Never drop the information the dash carried |
| 2 | A parenthesis used as a side note in a sentence, copied from English style | Say it as part of the sentence, or drop it if the reader does not need it |
| 3 | Copy-paste template: the same opener on every episode's first comment | Keep the disclosure sentence word for word (spec 2), vary or shorten the rest |
| 4 | One run-on block with no breaks, a pile of "ค่ะ" facts | Line breaks at the pauses (spec 6) |
| 5 | "ไม่ใช่แค่ X แต่ยัง Y", "ไม่เพียงแต่…ยังช่วย…" used to inflate | Say Y. Keep the contrast when it is real information (see good vs bad, case 6) |
| 6 | Every line ends with ครับ/ค่ะ/นะคะ | Particle on the lines where a person would say it, none elsewhere |
| 7 | Staging openers: "มาดูกันเลยว่า…", "สรุปง่ายๆ คือ…", "ในยุคที่…" | Start at the point |
| 8 | Stacked connectives: "นอกจากนี้ ที่สำคัญคือ… อย่างไรก็ตาม…" | One "แต่" or nothing; let line breaks do the work |
| 9 | Translated-English word order: passive "ถูก…โดย…", "เป็นเรื่องจริงที่ว่า…", "การที่…ทำให้…" | Active, spoken: who did what |
| 10 | A closer that repeats the point ("สรุปแล้ว…"), emoji/bullet decoration, a stock call to action | Cut it, or replace with the one real ask (spec 5) |

## Before and after

**1 · REAL, Wed 14 Oct caption** (`docs/scripts/mimi-post-w2-wed-caption.txt`; tells 1, 2 and a repeated "เล่า"):
- Before: "น้องสาวกลับบ้านทุ่มหนึ่งทุกวัน — เป็นเรื่องจริงของบ้านเรา ส่วนที่เหลือเราแต่งเติมเป็นเรื่องเล่า เล่าเป็นตอนที่ 5 (18 ช็อต ต่อกันเป็น 3 นาที)"
- After: "น้องสาวกลับบ้านทุ่มหนึ่งทุกวัน อันนี้เรื่องจริงของบ้านเรา ที่เหลือเราแต่งเติมเอง เลยเอามาเล่าเป็นตอนที่ 5 ยาว 3 นาที ต่อกัน 18 ช็อต"

**2 · REAL, EP6 first comment** (`docs/scripts/mimi-ep6-first-comment.txt`; tells 3, 4, and "เรื่องจริงของบ้านเราคือ" as a translated "The truth is:"):
- Before: "ตอนที่ 6 ของบ้านเรา ขอบคุณที่ดูจนจบนะคะ ภาพและเสียงในคลิปสร้างด้วย AI ถ้าเสียงมีมี่เพี้ยนตรงไหนขออภัยด้วย เรื่องจริงของบ้านเราคือ มีมี่ชอบเห่าและวิ่งไล่รถขายผัก คนแถวนั้นก็กลัวกัน แต่พอแม่เรียก มีมี่กลับมาทุกครั้ง ส่วนคลิปกล้องวงจรปิดกับสิ่งที่มีมี่พูดเราแต่งเติมเอง"
- After (applied 13 Oct; disclosure sentence and facts unchanged; kept as ONE paragraph on purpose, see the line-break caution under spec 6):
  "ตอนที่ 6 ขอบคุณที่ดูจนจบนะคะ ภาพและเสียงในคลิปสร้างด้วย AI ถ้าเสียงมีมี่เพี้ยนตรงไหนขออภัยด้วย ที่บ้านจริงๆ มีมี่ชอบเห่าและวิ่งไล่รถขายผัก คนแถวนั้นก็กลัวกัน แต่พอแม่เรียก มีมี่กลับมาทุกครั้ง ส่วนคลิปกล้องวงจรปิดกับสิ่งที่มีมี่พูดเราแต่งเติมเองนะคะ"

**3 · REAL, EP6 / Friday reels captions** (`docs/scripts/mimi-ep6-reels-caption.txt`, `docs/scripts/mimi-friday-news-reels-caption.txt`; tell 1, the separator only):
- Before: "ดัดแปลงจากเรื่องจริงในบ้านของเรา · ภาพและเสียงสร้างด้วย AI"
- After: two lines, same words, "ดัดแปลงจากเรื่องจริงในบ้านของเรา" / "ภาพและเสียงสร้างด้วย AI"
- Friday: "คลิปพิเศษตัดจากตอนที่ 5 · ตอนใหม่เสาร์นี้ 19:30 น." becomes two lines, the second "ตอนใหม่เสาร์นี้ 19:30 น."

**4 · REAL, Mon 12 Oct caption** (`docs/scripts/mimi-post-w2-mon-caption.txt`; spec 5, three invitations; already published, kept as a lesson):
- Before: "ช็อตไหนใน 5 ตอนแรก ที่คุณชอบที่สุด? / บอกเป็นตอนกับช็อตก็ได้ หรือเล่าสั้น ๆ ว่าช็อตนั้นทำให้คุณยิ้มตรงไหน / รวมช็อตเด็ดของทั้ง 5 ตอนอยู่ที่หน้าเพจ / เล่าให้มีมี่ฟังใต้โพสต์นี้ได้เลย"
- After: "ช็อตไหนใน 5 ตอนแรกที่คุณชอบที่สุด? / บอกเป็นตอนกับช็อตก็ได้ เล่าให้มีมี่ฟังใต้โพสต์นี้เลย / รวมช็อตเด็ดทั้ง 5 ตอนอยู่ที่หน้าเพจ"

**5 · REAL, BL/IB verify chatbot** (`/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/src/verify-checker.js` line 336; read only, not edited, the chatbot wiring is the CTO's):
- Before: "⚠️ ยังไม่พบบัญชี {broker} {id} ครับ / ขอให้ตรวจสอบขั้นตอนอย่างละเอียดอีกครั้ง: / ✅ เปิดบัญชีจริงที่ {broker} เรียบร้อยแล้ว (ไม่ใช่แค่ลงทะเบียนเบื้องต้น) / ✅ Affiliate Code = MNFUNDS … / ✅ ประเภทบัญชี = MT5 Standard … / ✅ MT5 ID … / ถ้าข้อใดข้อหนึ่งผิด ต้องเปิดบัญชี … ใหม่ …ครับ"
- After (codes, account types and the 4 checks unchanged): "ยังไม่เจอบัญชี {broker} {id} เลยครับ ลองเช็กตามนี้อีกทีนะครับ / 1. เปิดบัญชีจริงกับ {broker} เรียบร้อยแล้ว (ไม่ใช่แค่สมัครเบื้องต้น) / 2. Affiliate Code ใส่ MNFUNDS ตัวใหญ่ทั้งหมด ไม่มีช่องว่าง / 3. ประเภทบัญชีเป็น MT5 Standard (ไม่ใช่ MT4 หรือ Micro) / 4. MT5 ID ที่ส่งมาเป็นบัญชีที่เพิ่งเปิดใหม่ ไม่ใช่บัญชีเก่า / ถ้าข้อไหนไม่ตรง ต้องเปิดบัญชี {broker} ใหม่ ใส่รหัส MNFUNDS แล้วส่ง MT5 ID ใหม่มาให้ครับ"
- Judgement kept: the contrast "ไม่ใช่แค่…" stays in checks 1 and 3 because it tells the trader which mistake to look for. That is information, not inflation.

**6 · CONSTRUCTED (tells 5 to 10 are not in our files):**

| Tell | Before | After |
|---|---|---|
| 5 | มีมี่ไม่ใช่แค่หมาที่น่ารัก แต่ยังเป็นสมาชิกสำคัญของครอบครัวเรา | มีมี่เป็นหมาดำของบ้านเรา และเป็นหนึ่งในครอบครัวด้วย |
| 7 | มาดูกันเลยว่าทำไมมีมี่ถึงวิ่งไล่รถขายผักทุกวัน | ทำไมมีมี่วิ่งไล่รถขายผักทุกวัน (this is the real EP6 caption line) |
| 7 | ในยุคที่ AI สร้างได้ทุกอย่าง ซีรีส์นี้ดัดแปลงมาจากเรื่องจริง | ซีรีส์นี้ดัดแปลงจากเรื่องจริงในบ้านเรา ภาพและเสียงสร้างด้วย AI |
| 8 | นอกจากนี้ ที่สำคัญคือมีมี่กลับมาทุกครั้งที่แม่เรียก อย่างไรก็ตาม คนแถวนั้นก็ยังกลัว | มีมี่กลับมาทุกครั้งที่แม่เรียก แต่คนแถวนั้นก็ยังกลัวอยู่ |
| 9 | เป็นเรื่องจริงที่ว่ามีมี่ถูกกลัวโดยคนในละแวกนั้น | คนแถวนั้นกลัวมีมี่จริงๆ ค่ะ |
| 6 | ขอบคุณที่ติดตามนะคะ ดูตอนใหม่ได้เลยนะคะ อย่าลืมกดติดตามนะคะ | ขอบคุณที่ติดตามนะคะ ตอนใหม่ศุกร์นี้ 19:30 |
| 10 | สรุปแล้ว มีมี่ชอบวิ่งไล่รถ แต่ก็กลับมาทุกครั้งที่แม่เรียก 🐶✨ | (cut: the post already said it) |

## The check (60 seconds)

```bash
bash scripts/check-post-text.sh <draft.txt>         # characters: must print ผ่าน
```
Then compare the facts list from step 1 with the final text (same numbers, times, names, codes, same disclosure
sentence), and read the text aloud once: where you would not say it that way, change it. If nothing was wrong,
the text goes out unchanged and you say "no change" (a pass that rewrites everything is itself a tell).

## Good vs bad

- **Bad:** "🐶✨ ตอนใหม่มาแล้ว! 🎬 ไม่ใช่แค่ความน่ารัก แต่ยังเต็มไปด้วยความประทับใจ ในยุคที่ AI ครองโลก — ดูกันเลย! 💕"
  (decoration, inflation, staging, banned dash, a claim the page cannot back).
- **Good (real, Thu 15 Oct):** `docs/scripts/mimi-post-w2-thu-caption.txt` first two lines: "ตอนใหม่ ทำไมมีมี่วิ่งไล่รถขายผักทุกวัน ทั้งที่ใครๆ ก็กลัว? /
  ดูวันและเวลาที่โปสเตอร์ได้เลยนะคะ". One question, one pointer, no decoration. Its only fault is the separator in the disclosure line (tell 1).

## Field notes
- 2026-10-13 [MISSING] §the pass, field test 1 (3 unpublished Mimi drafts, before vs after in the examples above): (a) the Thai tell phrases "ไม่ใช่แค่ / ในยุคที่ / มาดูกัน / สรุปง่ายๆ / ที่สำคัญคือ / อย่างไรก็ตาม / นอกจากนี้" have 0 hits in every `mimi-*` caption and comment file and in `docs/promo`, so tells 5 to 10 are CONSTRUCTED only; the real faults in our Mimi text were banned characters (`check-post-text.sh` fails 17 of 24 caption/comment files, 15 still fail after this pass: the Tue and Wed captions carry "—", every caption carries "·"; those posts are published or scheduled and were NOT edited), a repeated first-comment template, one run-on comment, and three invitations in the Mon caption; (b) the pass fixed the two reels captions and the EP6 first comment (gate clean, facts and disclosure lines identical); (c) a multi-line comment was NOT used because Enter sends in the Facebook comment box and Shift+Enter through `tools/fb_cdp_do.py` is untested; (d) the planned run on the next live recap comment is still to do. · evidence: this commit, `bash scripts/check-post-text.sh` over `docs/scripts/mimi-*` · status: pending
