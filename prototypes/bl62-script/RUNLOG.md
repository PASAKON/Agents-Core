# EP62 RUNLOG - CXM case, a trader's three open questions (W1 script_writer for PH #13db8720, stage 1)

Stage 1 = script + censored real stills only. No paid API, no TTS, no lipsync, no Drive upload. Spend $0.
Times Asia/Bangkok (Contabo clock is CEST, minus 5 h). Started 10:44 ICT 14 Oct 2026, deadline 12:15.
Source: /opt/MoonieXHQ/Assets/Agents/Core/bl-realfootage/bl62-cxm-source/ (SOURCE.md, fb-post-text.jpg, fb-post-infographic.jpg, messenger-permission.png). Permission note in SOURCE.md read; the poster agreed 10:37.

## Files

| file | what |
|---|---|
| prototypes/bl62-script/SCRIPT.tsv | 26 tagged lines: tag, text, shot id, beat, screen note |
| prototypes/bl62-script/CAPTION.md | caption + section 6b disclaimer + check-post-text.sh output |
| prototypes/bl62-script/HEADLINE.md | one headline look, 2 options, backdrop |
| prototypes/bl62-realfootage/real/*.png | 3 censored stills 1080x1920 |
| prototypes/bl62-realfootage/REAL_MANIFEST.json | stills, source, what was censored |

Raw/uncensored material stays in /opt/MoonieXHQ/Assets/... (outside the repo); the generator script is in the scratchpad, not committed.

## Length

- 26 lines, **877 non-space spoken characters** (`"".join(text.split())` on column 2; target 820-880).
- Forecast delivered (chars / 12.5, EP61 measure, includes the 1.15x speed-up): **70.2 s**.
- Cross-check at the old raw track rates: 76.9 s at 11.4 chars/s, 72.5 s at 12.1 chars/s (before the 1.15x speed-up).
- First draft was 1,238 chars (99 s); cut to 26 lines. Dropped: the 2-hour/phone detail beyond HOOK-2, the "no bot" detail beyond PATTERN-2, her fairness line (holding long / phone does not by itself prove anything; she says it in the post), the "which order" detail of the journal.
  If the voice runs long, drop CURIOSITY-1 first.

## Stills (made from fb-post-text.jpg with a PIL script, 1179x1628 source)

| still | what is in frame | censored |
|---|---|---|
| cxm-post-full | whole post, scaled to 1080 wide on a dark canvas | profile photo, poster name, the two title lines (the one with the word Scammer and her crude line) blurred (pixelate 28 px + gaussian 14). CXM stays visible. Facebook's AI label stays visible |
| cxm-post-claim | the 'Ep1..' headline + the phone / 2 hours paragraph | header and title lines are outside the crop (and blurred in the source before cropping) |
| cxm-post-account | the CXM Direct / Cent account paragraph + the own-money paragraph | same |

I looked at cxm-post-full and cxm-post-account at full size: no readable name, no face. cxm-post-claim crop starts below the header (y 330 of the source); not re-opened after render, geometry only.
No evidence boxes drawn in the manifest (empty list).

## The AI infographic

Not used anywhere: no still, no backdrop. Facts quoted from the post text only. Where the infographic's figures overlap the text (184,841; 30,000; 116 pages are in the TEXT, not the graphic) I used the text. The text cards (CONTEXT-1/2/5, MAIN-4) are plain graphic cards, labelled เธอเล่าว่า.

## Hard lines, how each was met

1. **Identity hidden**: no name, no page name, no 'Bombie Everywhere', in script/caption/headline (grep checked: no Lek, Wachira, Bombie). Photo + name blurred in the full still, cropped out of the others. CXM / CXM Direct visible and spoken (as ซีเอ็กซ์เอ็ม).
2. **We report**: lines say เธอเล่าว่า / เธอว่า / ตามที่เธอเล่า / ซีเอ็กซ์เอ็มแจ้งในอีเมลว่า (HOOK-3, CONTEXT-3 each carry the source: the post). No scam / โกง / scammer / ติดคุก (grep clean); her crude line and her title are not spoken and are blurred on screen. Angle = her 3 questions (order, latency in ms, which rule) + 4 checks (terms on toxic trading, small withdrawal test, journal + screenshots, company and regulator). MAIN-5 says the channel has not heard CXM's side.
3. **AI label**: infographic not shown; the post's AI label remains visible in cxm-post-full; screen label for stills is ภาพจากโพสต์ต้นทาง.
4. **No link / CTA**: CTA is the knowledge one (คอมเมนต์ เช็กลิสต์). No hashtag with the broker name. check-post-text.sh passes on CAPTION.md (output quoted there).
5. **Numbers**: only the post's, attributed. Spoken: เกือบหกล้านบาท, ราวหนึ่งแสนแปดหมื่นสี่พันดอลลาร์, สามหมื่นดอลลาร์, หนึ่งร้อยสิบหกหน้า, สองชั่วโมง, ยี่สิบสองกันยายน. Exact 18,484,191.83 US cent only in the CONTEXT-1 screen note. No arithmetic of ours.

## Open questions / lines I am unsure about

1. **Voice spelling and brand-display.yaml**: the script says ซีเอ็กซ์เอ็ม. brand-display.yaml has NO row for it, and it already has `เอ็กซ์เอ็ม: XM`, which is a SUBSTRING of ซีเอ็กซ์เอ็ม, so the caption pass would show 'ซีXM'. Editor/CMO: add `ซีเอ็กซ์เอ็ม: CXM` ABOVE the XM row (longest first). I did not touch that file (other folder).
2. **XM-style collision risk for TTS**: "ซีเอ็กซ์เอ็ม" may be read oddly; check the first TTS take. Fallback is letter names with no spaces.
3. **HOOK-3 / CONTEXT-3** state that CXM's email said it, as the post says. We have not seen the email. If the CMO wants it tighter, change to 'เธอเล่าว่าอีเมลของซีเอ็กซ์เอ็มบอกว่า'.
4. **The poster's gender**: 'เธอ' follows the post ('หนู', 'ค่ะ') and her permission reply. HOOK-1's screen note says "a Thai woman trader" for the on-screen text; if CMO prefers no gender, use 'เจ้าของโพสต์'.
5. **Voice**: กู used in MAIN-5 and SUMMARY-6 (channel voice, EP61 precedent), no มึง.
6. **SUMMARY-5**: 'หน่วยกำกับ' is used once, plainly; CMO may add the name of a regulator if wanted. The script does not claim CXM is or is not licensed (not checked; regulators block this host).
7. **Date**: '22 กันยายน' spoken without the year; the post is dated 2026.
