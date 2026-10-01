IB status of Weltrade: unconfirmed, CEO to confirm before posting

# EP58 RUNLOG - Weltrade (task-cc4df7f0, script_writer, stage 1 of 3)

Stage 1 = script + real footage only. No paid API, no TTS, no lipsync, no Drive upload.
All times Asia/Bangkok. Capture session 2026-10-01 18:02 to 18:42 ICT (11:02 to 11:42 UTC).
Host = Contabo, headless Chromium through Playwright, 1080x1920, locale th-TH, dpr 1.

## What is in the folder

| file | what |
|---|---|
| `prototypes/bl58-script/SCRIPT.tsv` | 40 tagged lines. tag, text, shot id, beat, screen note |
| `prototypes/bl58-script/CAPTION.md` | caption with the §6b disclaimer + 3 on-screen search phrases |
| `prototypes/bl58-realfootage/shots.yaml` | the 13 shots, runnable with `tools/bl_realfootage.py` |
| `prototypes/bl58-realfootage/real/*.png` | 13 CENSORED stills, 1080x1920 |
| `prototypes/bl58-realfootage/REAL_MANIFEST.json` | covers[], captured_at, censored[], hand-added evidence_box |

Not committed on purpose: `output/bl-realfootage/bl58/*/raw.png` are the UNCENSORED raw
screenshots the runner keeps next to each still. They stay untracked. Nothing in `real/`
or the manifest points at them.

## Length

- v2 (CMO length correction: 70 to 85 s of speech, about 950 to 1,200 characters, from the
  28-post Studio export; posts over 120 s have a lifetime-view median of 381 vs 1,805 for <=70 s).
- 40 lines, 1,125 non-space spoken characters (1,151 with spaces). Shortest line 20, longest 34,
  average 28.1. All 40 tags kept, same shot mapping, same on-screen evidence as v1.
- Whole-track forecast at 13.2 to 14.7 chars/s: **76.5 to 85.2 s**. Speech-only at 16.6
  chars/s would be 67.8 s, which is not the track length (breaths between 40 lines).
- v1 was 1,388 characters (94.4 to 105.2 s). Lines were tightened, none dropped. Facts kept:
  43 complaints, 3-week wait, 1 Oct check, two WikiFX profiles, 2023 survey, Belize headline.
  Dropped for length only: "ฝากเข้าได้" in PATTERN-2 and "ส่วนตัว" in MAIN-10.
- The hook is not built on "90% search traffic" (28-day figure only).
- `tools/bl_checker.py` cannot check a script. It takes `--video --beats`, so it needs a
  rendered MP4 plus a beats JSON. Not run. The structure was checked by hand: 40 unique
  tags, 4/4/5/13/5/9 per section, one idea per line, no em dash, no crude words, no link.

## Compliance read of the script (against CMO_Standard_BlackLiquidity_Script)

- No link, no rebate, no IB mention, no account CTA. CTA = comment a word for a checklist.
- No "use it" / "do not use it". The only word for that is the required line
  SUMMARY-7: "กูไม่ได้แนะนำให้ใช้เจ้าไหน แค่ชี้วิธีดูให้เป็น".
- No "โกง". Every claim is attributed: วิกิเอฟเอ็กซ์ว่า / ตามวิกิเอฟเอ็กซ์ / คนหนึ่งว่ากับอีกคนรอ /
  มีคนอ้างว่า / ผลสำรวจสรุปว่า. PATTERN-4 and MAIN-1 say it is the complainants' words and
  that the channel cannot confirm them. SUMMARY-2 says the channel did not test a withdrawal.
- The WikiFX Facebook art is not on screen. No number was copied from it.
- Voice: กู is used (as EP57), under the IRON-RULES §37 carve-out for this channel. No มึง.
- WikiFX's own warning card says "โปรดหลีกเลี่ยง" (please avoid). That is WikiFX's text on
  screen, in the frame. The voice does not repeat it (CONTEXT-2 says only that the warning
  comes from a low score). CMO to decide whether that on-screen phrase is acceptable.

## Claim ledger (page, what it says, when seen)

Profile 1 = https://www.wikifx.com/th/dealer/9161578493.html (the profile in the brief)

| line | claim on screen | source + capture time |
|---|---|---|
| HOOK-1/2, CONTEXT-3 | logo, name Weltrade, score 3.73/10, grade D | profile 1, 18:41 |
| MAIN-7 | green label อยู่ในการกำกับดูแล on the logo tile | profile 1, 18:41 |
| HOOK-3/4, CONTEXT-1/2 | card "คำเตือน: ระดับคะแนนอยู่ในระดับต่ำ โปรดหลีกเลี่ยง", "ได้รับร้องเรียนจากผู้ใช้ทั้งหมด 43 รายการ", date 2026-10-01 | profile 1, 18:41 |
| MAIN-3/4/5 | licence box: FSCA, South Africa, derivatives licence (EP), licensed entity WELTRADE SA (PTY) L... (the page truncates it; full text WELTRADE SA (PTY) LTD read from the page text), licence no. 50691; tab ผิดปกติ 2 | profile 1, 18:41 |
| MAIN-4/12 | basic-info: registered Saint Lucia, 20+ years, company Weltrade Ltd | profile 1, 18:35 |
| PATTERN-1, MAIN-6 | abstract of the 29 Apr 2026 article: 43 complaints in 3 months, main repeated problem = cannot withdraw, licence revoked in some countries | 202604298924908012, 18:38 |
| PATTERN-2 | complaint, tag ปัญหาการถอนเงิน, 2025-12-31, Andorra: deposits fine, withdrawal blocked with verification and country excuses | exposure/detail/COG20251231202513916192344, 18:34 |
| PATTERN-3 | complaint, 2025-09-04, Malaysia: 3 weeks, "under review by the finance department" | exposure/detail/COG20250904085434501137992, 18:35 |
| CONTEXT-4/5, MAIN-13 | 30 Sep 2026 article: "$22,067 คือยอดเงินที่นักเทรดรายหนึ่งพยายามถอนออกจาก Weltrade แต่กลับถอนไม่ได้เลย", contents line "ใบอนุญาตเบลีซถูกเพิกถอน" | 202609302364545921, 18:41 |
| MAIN-8..11 | WikiFX Survey "การเยี่ยมชม WELTRADE ในแอฟริกาใต้ - ไม่พบสำนักงาน", dated 2023-11-06, a private residence, owner had never heard of the name, broker not present | survey/97378304c7, 18:41 |
| CURIOSITY-1..4 | profile 2: stamp ยังไม่มีการกำกับดูแล, registered Saint Vincent and the Grenadines, "ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์", score 2.04/10 | dealer/5381662917, 18:36 |

## Not on screen, so the voice does not say it

- The paragraph in profile 1's company text that says the Belarus (NBRB) and Belize (FSC)
  licences are revoked and the FSCA one is "overdue" sits behind an expand arrow. The runner has
  no click action, so MAIN-5 to MAIN-7 were rebuilt from what is visible (the ผิดปกติ 2 tab,
  the April abstract, the green label). The header chip "เบลารุส ... ถูกยกเลิก" seen at probe
  time did not show in the cropped stills.
- The company-profile first sentence (initially registered in Saint Vincent) was in a planned
  shot `weltrade-profile-text`. Dropped: the long smooth scroll to it risked the blur boxes
  and the crop landing in different places, and a mis-placed blur is a privacy failure.
- Systemgates Ltd. as the company of profile 2, and "SYSTEMGATES CAPITAL LTD. (Belize)" listed as a
  related company on profile 1. Seen in page text, not framed, so the voice does not name it.

## Unverified or needs a human before posting

1. **IB status of Weltrade: unconfirmed.** CEO to confirm. Nothing in the script depends on it.
2. **FSCA register not self-checked.** The real register is an embedded app at
   `/Entity-Persons-Search/?iframe_target=financial-services-providers` that needs typed
   input, the same wall as EP57's FCA attempt. Licence no. 50691 is WikiFX's figure, not
   confirmed at the regulator. The script tells the viewer to check it themselves.
3. **Two WikiFX profiles for one name, two scores.** 3.73 (profile 1) and 2.04 (profile 2);
   an older 2.42 appears in July 2026 articles. The voice names no score. The numbers on screen
   move, so re-read both before posting.
4. **The $22,067 figure comes from an article built on profile 2's data** (it quotes 2.04, 16
   complaints in 3 months, a revoked Belize licence). The line CONTEXT-5 attributes it to "a
   user" and says in MAIN-1 that the channel cannot confirm it. The article headline says
   "หลักหมื่น", which fits. The complainant is not named in the article.
5. **43 is "รายการ" (entries), on profile 1's card.** The April article says 43 complaints in
   3 months, the card says 43 in total. Same number, different windows. HOOK-4 says
   "ข้อร้องเรียนสี่สิบสามรายการ", matching the card, with no time window. Re-check the count on
   the day, it changes.
6. **The survey is dated 2023-11-06.** MAIN-9 says the year out loud. The finding is nearly
   three years old and may have changed.
7. **WikiFX is the only source for every claim.** WikiFX itself is a commercial rating site.
   The script says "วิกิเอฟเอ็กซ์ว่า" throughout and never states a finding as the channel's own.
8. The green label on profile 1 ("อยู่ในการกำกับดูแล") conflicts with the red card. The
   script shows both (MAIN-7) and states neither as fact.
9. Where profile 1 is a South Africa FSCA record, the licence holder name differs from the
   profile name. MAIN-4 says so as a fact about the page, not as a finding about the firm.

## Censor and framing checks (every one of the 13 stills looked at, full size)

- The broker's website and email are pixelated by regex (exact text range) in every frame
  that carries them. Profile 1 and 2 headers, basic-info boxes: checked.
- Complaint pages: username and avatar pixelated, complaint ids not on screen, the evidence
  screenshot (broker email, trading history) hidden by selector.
- Survey page: WikiFX's field photos and map hidden (they show a street sign), street name and
  number pixelated in the English and the Thai line. Photos on the profile page are hidden
  too (`.dealer-survey-container`).
- No other broker's name, no promo banner, no app-download card, no Chrome extension popup in
  any still. The Chinese "切换" bar is hidden by the reused hygiene block.
- WikiFX's own nav "Download" button appears in the top bar of the full-viewport frames. It is
  WikiFX's app button, not a broker promo. Flagged, left in.
- Frames framed by the tool's 9:16 window (756x1344 cap) cut the page edges on wide content;
  that is why the complaint and survey frames use the full viewport instead and the editor
  zooms into the top third.
- `promo` censor profile NOT applied to `wikifx-article-sep-amount` on purpose: it blanks any
  `$` figure of 4+ digits and would hide the claim.

## Environment fixes made on this host (not in the repo)

- No Thai font on Contabo, so every Thai glyph rendered as a box. Installed Noto Sans Thai (OFL)
  into `~/.fonts` and ran `fc-cache`.
- No CJK font, so WikiFX's full-width colon "：" rendered as a box in the licence box.
  Installed Noto Sans SC (OFL) into `~/.fonts`.
- curl to wikifx gets 403, Playwright gets 200. The runner uses Playwright, fine.
- The venv python (`/opt/MoonieXHQ/Agents/Core/.venv/bin/python`) has PIL, playwright and yaml.
  System python3 has none of them.

## Runner log

Every runner line from this task, oldest first. Runs before 18:34 were framing iterations that I
reviewed by eye and threw away (crops cutting the page edge, the broker-site censor blurring whole
containers, the survey street name left sharp in the Thai line). The stills in `real/` come from
the runs at 18:34 to 18:41 (SKIP = unchanged from the run before):

```
2026-10-01T18:20:31+07:00 | weltrade-header ok -> weltrade-header/weltrade-header.png
2026-10-01T18:20:45+07:00 | weltrade-warning ok -> weltrade-warning/weltrade-warning.png
2026-10-01T18:23:57+07:00 | weltrade-header ok -> weltrade-header/weltrade-header.png
2026-10-01T18:24:14+07:00 | weltrade-warning ok -> weltrade-warning/weltrade-warning.png
2026-10-01T18:24:26+07:00 | wikifx-article-apr ok -> wikifx-article-apr/wikifx-article-apr.png
2026-10-01T18:24:36+07:00 | weltrade-complaint-1 ok -> weltrade-complaint-1/weltrade-complaint-1.png
2026-10-01T18:24:44+07:00 | weltrade-complaint-2 ok -> weltrade-complaint-2/weltrade-complaint-2.png
2026-10-01T18:24:55+07:00 | wikifx-article-sep ok -> wikifx-article-sep/wikifx-article-sep.png
2026-10-01T18:25:06+07:00 | wikifx-article-sep-amount ok -> wikifx-article-sep-amount/wikifx-article-sep-amount.png
2026-10-01T18:25:17+07:00 | weltrade-licence ok -> weltrade-licence/weltrade-licence.png
2026-10-01T18:25:27+07:00 | weltrade-registration ok -> weltrade-registration/weltrade-registration.png
2026-10-01T18:25:36+07:00 | weltrade-profile-text ok (crop target not found, used full frame) -> weltrade-profile-text/weltrade-profile-text.png
2026-10-01T18:25:46+07:00 | weltrade-survey ok -> weltrade-survey/weltrade-survey.png
2026-10-01T18:25:54+07:00 | weltrade-survey-detail ok -> weltrade-survey-detail/weltrade-survey-detail.png
2026-10-01T18:26:06+07:00 | weltrade2-header ok -> weltrade2-header/weltrade2-header.png
2026-10-01T18:26:16+07:00 | weltrade2-info ok -> weltrade2-info/weltrade2-info.png
2026-10-01T18:26:26+07:00 | weltrade2-licence ok -> weltrade2-licence/weltrade2-licence.png
2026-10-01T18:29:17+07:00 | weltrade-header ok -> weltrade-header/weltrade-header.png
2026-10-01T18:29:31+07:00 | weltrade-warning ok -> weltrade-warning/weltrade-warning.png
2026-10-01T18:29:40+07:00 | wikifx-article-apr ok -> wikifx-article-apr/wikifx-article-apr.png
2026-10-01T18:29:47+07:00 | weltrade-complaint-1 ok -> weltrade-complaint-1/weltrade-complaint-1.png
2026-10-01T18:29:54+07:00 | weltrade-complaint-2 ok -> weltrade-complaint-2/weltrade-complaint-2.png
2026-10-01T18:30:05+07:00 | wikifx-article-sep ok -> wikifx-article-sep/wikifx-article-sep.png
2026-10-01T18:30:15+07:00 | wikifx-article-sep-amount ok -> wikifx-article-sep-amount/wikifx-article-sep-amount.png
2026-10-01T18:30:29+07:00 | weltrade-licence ok -> weltrade-licence/weltrade-licence.png
2026-10-01T18:30:42+07:00 | weltrade-registration ok -> weltrade-registration/weltrade-registration.png
2026-10-01T18:30:55+07:00 | weltrade-profile-text ok -> weltrade-profile-text/weltrade-profile-text.png
2026-10-01T18:31:08+07:00 | weltrade-survey ok -> weltrade-survey/weltrade-survey.png
2026-10-01T18:31:22+07:00 | weltrade2-header ok -> weltrade2-header/weltrade2-header.png
2026-10-01T18:31:35+07:00 | weltrade2-info ok -> weltrade2-info/weltrade2-info.png
2026-10-01T18:31:45+07:00 | weltrade2-licence ok -> weltrade2-licence/weltrade2-licence.png
2026-10-01T18:34:23+07:00 | weltrade-header ok -> weltrade-header/weltrade-header.png
2026-10-01T18:34:37+07:00 | weltrade-warning ok -> weltrade-warning/weltrade-warning.png
2026-10-01T18:34:49+07:00 | wikifx-article-apr ok -> wikifx-article-apr/wikifx-article-apr.png
2026-10-01T18:34:57+07:00 | weltrade-complaint-1 ok -> weltrade-complaint-1/weltrade-complaint-1.png
2026-10-01T18:35:06+07:00 | weltrade-complaint-2 ok -> weltrade-complaint-2/weltrade-complaint-2.png
2026-10-01T18:35:16+07:00 | wikifx-article-sep ok -> wikifx-article-sep/wikifx-article-sep.png
2026-10-01T18:35:24+07:00 | wikifx-article-sep-amount ok -> wikifx-article-sep-amount/wikifx-article-sep-amount.png
2026-10-01T18:35:36+07:00 | weltrade-licence ok -> weltrade-licence/weltrade-licence.png
2026-10-01T18:35:48+07:00 | weltrade-registration ok -> weltrade-registration/weltrade-registration.png
2026-10-01T18:36:06+07:00 | weltrade-profile-text ok -> weltrade-profile-text/weltrade-profile-text.png
2026-10-01T18:36:15+07:00 | weltrade-survey ok -> weltrade-survey/weltrade-survey.png
2026-10-01T18:36:26+07:00 | weltrade2-header ok -> weltrade2-header/weltrade2-header.png
2026-10-01T18:36:35+07:00 | weltrade2-info ok -> weltrade2-info/weltrade2-info.png
2026-10-01T18:36:46+07:00 | weltrade2-licence ok -> weltrade2-licence/weltrade2-licence.png
2026-10-01T18:38:28+07:00 | SKIP weltrade-header (unchanged, outputs present)
2026-10-01T18:38:28+07:00 | SKIP weltrade-warning (unchanged, outputs present)
2026-10-01T18:38:38+07:00 | wikifx-article-apr ok -> wikifx-article-apr/wikifx-article-apr.png
2026-10-01T18:38:38+07:00 | SKIP weltrade-complaint-1 (unchanged, outputs present)
2026-10-01T18:38:38+07:00 | SKIP weltrade-complaint-2 (unchanged, outputs present)
2026-10-01T18:38:38+07:00 | SKIP wikifx-article-sep (unchanged, outputs present)
2026-10-01T18:38:38+07:00 | SKIP wikifx-article-sep-amount (unchanged, outputs present)
2026-10-01T18:38:52+07:00 | weltrade-licence ok -> weltrade-licence/weltrade-licence.png
2026-10-01T18:38:52+07:00 | SKIP weltrade-registration (unchanged, outputs present)
2026-10-01T18:39:06+07:00 | weltrade-profile-text ok -> weltrade-profile-text/weltrade-profile-text.png
2026-10-01T18:39:06+07:00 | SKIP weltrade-survey (unchanged, outputs present)
2026-10-01T18:39:06+07:00 | SKIP weltrade2-header (unchanged, outputs present)
2026-10-01T18:39:06+07:00 | SKIP weltrade2-info (unchanged, outputs present)
2026-10-01T18:39:06+07:00 | SKIP weltrade2-licence (unchanged, outputs present)
2026-10-01T18:41:21+07:00 | weltrade-header ok -> weltrade-header/weltrade-header.png
2026-10-01T18:41:28+07:00 | weltrade-warning ok -> weltrade-warning/weltrade-warning.png
2026-10-01T18:41:28+07:00 | SKIP wikifx-article-apr (unchanged, outputs present)
2026-10-01T18:41:28+07:00 | SKIP weltrade-complaint-1 (unchanged, outputs present)
2026-10-01T18:41:28+07:00 | SKIP weltrade-complaint-2 (unchanged, outputs present)
2026-10-01T18:41:28+07:00 | SKIP wikifx-article-sep (unchanged, outputs present)
2026-10-01T18:41:36+07:00 | wikifx-article-sep-amount ok -> wikifx-article-sep-amount/wikifx-article-sep-amount.png
2026-10-01T18:41:47+07:00 | weltrade-licence ok -> weltrade-licence/weltrade-licence.png
2026-10-01T18:41:47+07:00 | SKIP weltrade-registration (unchanged, outputs present)
2026-10-01T18:41:55+07:00 | weltrade-survey ok -> weltrade-survey/weltrade-survey.png
2026-10-01T18:41:55+07:00 | SKIP weltrade2-header (unchanged, outputs present)
2026-10-01T18:41:55+07:00 | SKIP weltrade2-info (unchanged, outputs present)
2026-10-01T18:41:55+07:00 | SKIP weltrade2-licence (unchanged, outputs present)
```
