---
name: CMO_Workflow_LakornSerial
kind: workflow
owner: CMO
description: >-
  WORKFLOW — The ordered workflow for a ละครสั้นคุณธรรม Facebook SERIAL (Page "ละครสั้นคุณธรรม by ILAG Studio").
  Since CEO 2026-10-26: EPs of 10–20 min, each a complete case with a 15-second hook, a twist and a pull into the
  next EP, built with the channel kit (knowledge/brand-knowledge/brands/ilag) and an AI-mistake NG gag plus a
  blooper reel. Story → plates → 360p test → Flow shoot on winbox → QC + NG bank → per-EP cut with the kit →
  cover → post → Drive. Each step names the skill that owns its rules; the rules live there, not here.
  Trigger on /CMO_Workflow_LakornSerial and whenever a ละครสั้นคุณธรรม story is made as EPs, "ทำทีละ EP",
  "ซีรีส์ละครสั้น", "EP.2 ต่อ", "ตัด EP", "hook 15 วิ", "ฉากหลุด AI", "ตลาดนี้มีกรรม". Use instead of
  CMO_Workflow_ShortFilm (that one is the ILAG festival short film on Seedance / H3 / Wan, a different channel and
  engine).
created_by: agent
author: {role: cto, date: "2026-10-01"}
audience: [cmo, cto]
lifecycle: active
---

# ละครสั้นคุณธรรม serial — one EP a day

## The pattern since 2026-10-26 (CEO: Chinese-series EPs, AI-mistake comedy)

> "แบบ ซีรี่จีน เราทำ ตอนจบในตอน แค่ 10-20 นาทีต่อตอน … แต่ละ EP ต้องมี Hook ของตัวเองมี มีจุดพลิก หักมุม และให้น่าติดตามไปตอนถัดไป"
> "ควรจะต้องมี 15 วิสำหรับ Hook คนดู … คนดูชอบอะไรที่มันตลกๆ ผิดธรรมชาติ หรือตื่นเต้นๆ … ของเราจะเด่นกว่าตรงที่
> เราจะใช้ความผิดพลาดของ Ai ที่มนุษย์ดูแล้วมันตลก" — CEO, 2026-10-26

| part | length | what |
|---|---|---|
| HOOK | 15 s | the most absurd, funny or exciting moments of THIS EP, told as a narrated fast-cut montage (CEO 2026-10-26 evening: six narrator lines, a new shot on every line, stopping just before today's event; ilag BRAND.md §The hook); it closes on the title sting (kit `title`) |
| STORY | 10–20 min | one complete case (story rule 1) with a turn and a twist; a kit card on every time jump, new place and first appearance of a named character |
| PULL | last beat | a new question that the next EP answers |
| END CARD | ~4 s | kit `end`: ติดตามตอนต่อไป + EP.N+1 + the open question + time + Page name; the last EP of a season says "จบบริบูรณ์" |
| BLOOPER REEL | 20–40 s | kit `blooper` header, then takes the AI really got wrong (from the NG bank) |

The kit and its rules (watermark, time cards, NG stamp limits) are in `knowledge/brand-knowledge/brands/ilag/BRAND.md`.
The table below is the 2026-10-01 pattern. Its hook length, EP length and one-EP-a-day cadence are superseded; the
rest of it (write and ship EP by EP, each EP self-contained) still holds.

## The pattern (CEO 2026-10-01, film 5 «ขายชื่อ») [SUPERSEDED 2026-10-26 for hook, EP length and cadence]

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

1. **Story, one EP.** CMO_Standard_Story_ThaiMoralDrama (dialogue density, overflow acting). Write the 15 s hook
   while writing, not at the edit: the narrator's six lines (ilag BRAND.md §The hook) with the shot under each line,
   every line paid off later in the EP. Lint: `tools/shotsheet_lint.py`.
   [SUPERSEDED 2026-10-26] Pick the 3-second hook line while writing.
2. **Pre-scan the dialogue for Flow's filter** before any credit (CTO_Flow_Omni1.1_Ops). Film 5 field data: lines
   with บัญชี / เปิดบัญชี / ยืมชื่อ / ค่าหัว / ค่าแผงค้าง, a scam caller's instructions ("โทรไปบอกว่า…พัวพันคดี"),
   gambling ("ติดพนันบอล") and a stated amount inside a scam call were refused; a refused generation is never
   charged. Rewrite, keep a list, report the rewrites afterwards.
3. **Plates** (free, ChatGPT on winbox :9224) → **one 360p test round** (≤20 cr) → **shoot 720p** on winbox Flow
   :9226 with the pc-lease (winbox-pc-lease). Log every spend: `tools/credit_ledger.py`.
4. **QC** each clip: `tools/film_transcript.py <dir> --lang th` (script coverage per shot) +
   `tools/burned_text_scan.py <dir>`; look at frames only to confirm a flagged defect (CMO_Gate_Flow_Omni1.1_FilmQC).
   Keep the **NG bank**: every funny failed take gets one line in the EP folder's `ng-bank.md` (shot id, what the AI got wrong, keep/drop) instead of being thrown away. It feeds the NG gag and the blooper reel.
5. **Cut the EP:** 15 s hook + title sting + story shots in order + end card + blooper reel, with the kit cards from
   `knowledge/brand-knowledge/brands/ilag/templates/` (watermark on every story frame, a card on every jump).
   ffmpeg, 1080×1920, 24 fps, AAC 48 kHz, every segment with the same pixel format and SAR before a concat copy.
   [SUPERSEDED 2026-10-26] hook clip (trimmed to the spoken line, ~3 s) + story shots + end card. Reference: film 5
   EP1, 3:03.
6. **Cover:** CMO_Procedure_ChatGPTImage_LakornCover, one cover per series with an "EP.N" pill; reuse it as the
   end-card background.
7. **Post** an EP once it is cut and the CEO has watched it, at 20:00 by default. The end card and the caption name
   the real day of the next EP ("พรุ่งนี้" only when the next EP is already cut). `tools/fb_reel_post.py` drives the
   Reels composer and has only carried EPs of about 3 min: dry-run a 10–20 min file before the first long post.
   Dry-run first, then publish once; never repost, never edit. [SUPERSEDED 2026-10-26] one EP per day. Caption = 2-line hook + question + "«ชื่อเรื่อง» EP.N | ละครสั้นคุณธรรม" +
   "EP.N+1 <วัน> 20:00 น." + help line (real hotline only) + "(ละครสร้างด้วย AI)" + hashtags.
   First comment = a question to the viewer + one "รู้ไว้ใช่ว่า" fact + next-EP time.
8. **Drive:** the EP folder (CXO_Rules_GDrive_Filing): final, cover, end card, clips, logs.txt, md5.

## Field notes
- 2026-10-01 [MISSING] film 5 was shot as one 9-minute EP before this pattern; recut into 3 EPs at the script's built-in cliffhangers (every ~3 min), hook taken from a later shot · evidence: 72acc21a · status: pending
- 2026-10-01 [COSTLY] §Steps 7 — `fb_reel_post.py --resolve-permalink` is a separate resolve-ONLY mode (no upload, no Share); publish mode already resolves the permalink itself. Four runs (19:30–00:28) each polled 30 min and posted nothing; the real publish took 4 min · evidence: ep5 EP1 videos/1376542657800427 · status: pending
- 2026-10-01 [WRONG] §Steps 7 — first comment: `REFUSED: comment text not found after submit` (exit 7) came back while the comment was live on the post; second false exit 7 in a day (12:00 poster too). Check the post page before treating 7 as a failure · evidence: ep5 EP1 post · status: pending
- 2026-10-02 [MISSING] §Steps 1 — recutting one long script into EPs leaves the LAST EP on the source's cliffhanger with nobody's ending written (film 5 S68 "นั่นมันชื่อแม่ผม"); the final EP needs its own closing act (story rules 7-8) written and shot before its post day · evidence: 7c5e7510 (S69-78) · status: pending
- 2026-10-02 [MISSING] §Steps 3 — winbox Chrome :9226 is shared: the CMO's stock `flow_shoot.py` takes the FIRST flow tab and runs without a pc-lease. Before opening a tab or firing, check `netstat -ano | findstr :9226` + the owning python's command line, and queue behind a live run · evidence: CMO khaoniao EP3 run on :9226 at 19:26, film 5 EP3 shoot queued behind it · status: pending
- 2026-10-03 [MISSING] §Steps 7 — a `--comment-only` rerun after a failed comment step posted the EP2 first comment a second time. Facebook collapses a long comment ("ดูเพิ่มเติม") and the collapse fell on line 2, so the idempotency check, which matched the first line only, missed the live comment. Fixed in dbe0a59e (it now scans every run of lines). Until that has run clean twice: after any comment-step error, look at the post's comments before rerunning. Facebook also offers no pin control for a Page's own reel comment; a blocked pin click is now logged "not pinned", not a failure · evidence: EP2 post 2026-10-02, PR #203 · status: pending
- 2026-10-26 [MISSING] §The pattern — proposed by the CMO, not yet measured (n=0; the pilot EP measures it): the 15 s hook as 0–3 s cold open on the EP's most absurd or exciting moment, 3–8 s the stakes in one line, 8–12 s the question the EP answers, 12–15 s title sting, then the same-day rewind card into the story; a micro-hook at least every 60 s; two peaks, each followed by a comic reset; mid-roll marks on live questions; the last 45 s open the next EP's question · evidence: kit demo ilag-kit-demo-v1.mp4 (44 s), CEO chat 2026-10-26 (CMO session d55bf0c1), knowledge/brand-knowledge/brands/ilag/BRAND.md; its 0–12 s cold open was replaced the same evening by the CEO's narrated montage (ilag BRAND.md §The hook), the rest still waits on the pilot · status: pending
- 2026-10-26 [COSTLY] §Steps 5 — a concat copy of segments with different pixel formats silently loses frames in some readers: the NG-slam segment (from JPEG stills) came out yuvj420p with SAR 1:1 while the footage segments were yuv420p, and a 2 fps review sheet dropped the first 6 s. Fix: `setsar=1,format=yuv420p` on every segment plus `-color_range tv` at encode, and convert stills with `scale=in_range=pc:out_range=tv` · evidence: ilag kit demo v1, ffprobe frame pix_fmt at 1 s vs 6.5 s · status: pending
