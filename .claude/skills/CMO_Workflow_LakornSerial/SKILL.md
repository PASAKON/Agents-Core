---
name: CMO_Workflow_LakornSerial
kind: workflow
owner: CMO
description: >-
  WORKFLOW — The ordered workflow for a ละครสั้นคุณธรรม Facebook SERIAL (Page "ละครสั้นคุณธรรม by ILAG Studio"):
  one story split into ~3-minute EPs, one EP posted per day, every EP = a 3-second hook, then the story, then a
  follow-me end card "EP.N ติดตามได้ที่เพจ …". Story → plates → 360p test → Flow shoot on winbox → QC → per-EP cut
  → cover → post → Drive. Each step names the skill that owns its rules; the rules live there, not here.
  Trigger on /CMO_Workflow_LakornSerial and whenever a ละครสั้นคุณธรรม story is made as EPs, "ทำทีละ EP",
  "ซีรีส์ละครสั้น", "EP.2 ต่อ", "ตัด EP", "hook 3 วิ". Use instead of CMO_Workflow_ShortFilm (that one is the ILAG
  festival short film on Seedance / H3 / Wan, a different channel and engine).
created_by: agent
author: {role: cto, date: "2026-10-01"}
audience: [cmo, cto]
lifecycle: active
---

# ละครสั้นคุณธรรม serial — one EP a day

## The pattern (CEO 2026-10-01, film 5 «ขายชื่อ»)

> "อยากให้ ทำทีละ EP มากกว่า และเขียนทีละตอนมีผล สรุปเป็นของตัวเอง เริ่มต้น 3 วิต้องน่าตื่นเต้น น่าติดตาม
> Hook ที่ดี … ต่อจากนั้นดำเนินเรื่องตามปกติ และจบท้ายด้วยการชวนติดตาม -> จบท้ายด้วย EP.2 ติดตามได้ที่เพจ ....
> ใส่ Logo ใส่ ภาพให้เรียบร้อย … ค่อยทำ EP.2 ต่อจาก EP.1 โดยโครงสร้างเดิม … Loop จนครบทุก EP"
> "วันนี้ ลง 3+- นาที EP.1 · พรุ่งนี้ 3+- นาที EP2 · วันต่อไป 3 นาที EP สุดท้าย"

Every EP, in this order:

| part | length | what |
|---|---|---|
| HOOK | ~3 s | the most gripping line/moment of the story (a flash-forward is fine), cut on a spoken line |
| STORY | ~3 min | the EP's own arc; it must make sense to someone who never saw the previous EP |
| TEASER | last shot | ends on a question the next EP answers |
| END CARD | ~4 s | cover art darkened + red pill "EP.N+1" + "พรุ่งนี้ 20:00 น." + "ติดตามได้ที่เพจ ละครสั้นคุณธรรม by ILAG Studio"; the last EP says "จบบริบูรณ์" + follow line instead |

**Write and ship EP by EP.** Write EP1, shoot it, post it; then EP2 on the same structure; loop until the last EP.
Do not write and shoot the whole series before the first post. Each EP's script is a self-contained summary:
it re-states in dialogue what the viewer needs from earlier EPs (story rules: CMO_Standard_Story_ThaiMoralDrama).

## Steps

1. **Story, one EP.** CMO_Standard_Story_ThaiMoralDrama (dialogue density, overflow acting). Pick the 3-second
   hook line while writing, not at the edit. Lint: `tools/shotsheet_lint.py`.
2. **Pre-scan the dialogue for Flow's filter** before any credit (CTO_Flow_Omni1.1_Ops). Film 5 field data: lines
   with บัญชี / เปิดบัญชี / ยืมชื่อ / ค่าหัว / ค่าแผงค้าง, a scam caller's instructions ("โทรไปบอกว่า…พัวพันคดี"),
   gambling ("ติดพนันบอล") and a stated amount inside a scam call were refused; a refused generation is never
   charged. Rewrite, keep a list, report the rewrites afterwards.
3. **Plates** (free, ChatGPT on winbox :9224) → **one 360p test round** (≤20 cr) → **shoot 720p** on winbox Flow
   :9226 with the pc-lease (winbox-pc-lease). Log every spend: `tools/credit_ledger.py`.
4. **QC** each clip: `tools/film_transcript.py <dir> --lang th` (script coverage per shot) +
   `tools/burned_text_scan.py <dir>`; look at frames only to confirm a flagged defect (CMO_Gate_Flow_Omni1.1_FilmQC).
5. **Cut the EP:** hook clip (trimmed to the spoken line, ~3 s) + story shots in order + end card. ffmpeg concat,
   1080×1920, 24 fps, AAC 48 kHz. Reference: film 5 EP1, 3:03.
6. **Cover:** CMO_Procedure_ChatGPTImage_LakornCover, one cover per series with an "EP.N" pill; reuse it as the
   end-card background.
7. **Post** one EP per day at the agreed time (20:00 default): `tools/fb_reel_post.py` dry-run first, then publish
   once; never repost, never edit. Caption = 2-line hook + question + "«ชื่อเรื่อง» EP.N | ละครสั้นคุณธรรม" +
   "EP.N+1 พรุ่งนี้ 20:00 น." + help line (real hotline only) + "(ละครสร้างด้วย AI)" + hashtags.
   First comment = a question to the viewer + one "รู้ไว้ใช่ว่า" fact + next-EP time.
8. **Drive:** the EP folder (CXO_Rules_GDrive_Filing): final, cover, end card, clips, logs.txt, md5.

## Field notes
- 2026-10-01 [n=1] film 5 was shot as one 9-minute EP before this pattern; recut into 3 EPs at the script's
  built-in cliffhangers (every ~3 min), hook taken from a later shot · evidence: ep5 EP1 cut · status: pending
