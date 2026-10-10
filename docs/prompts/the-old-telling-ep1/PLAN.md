# The Old Telling EP1, first minute: PLAN v0

STATUS UPDATE 2026-10-11 (ACT 4 to 6 PICTURES DONE): CEO 10-10 night "ทำ ARCT 4-6 ต่อได้เลย อณุมติ CU เพิ่มอีก 200". 51 shots (16 + 19 + 16) fired as 51 one-card batches, all rendered; 1 retake used (ACT 6 s06a: first take showed a detailed woman's face, retake = veiled silhouette, passed), 1 failed Colab take re-run (ACT 5 s09b). Colab OFF, balance 814.78 -> 775.63 = 39.15 CU (ACT 1-3 29.13 + 39.15 = 68.28 of the 300 CU series cap). Edit fixes planned in build_act456_edit.py: ACT 4 s09 crop (two small skulls bottom-left), ACT 6 s03a starts at 1.2 s (face in profile). Planned lengths (reading-speed estimate, real voice will move them): ACT 4 113.1 s, ACT 5 133.9 s, ACT 6 102.6 s. Smoke render with stand-in audio passed (A/V durations equal, 1080p 24 fps). WAITING ON CEO: (1) voice OK $0.2282 (2,853 chars, text in READ-ALOUD-ACT4-6.md), then ACT 4-6 + full EP1 cut are a ~15 min job; (2) Drive folder yes (hard rule 3), takes of ACT 1-6 not backed up yet.
STATUS UPDATE 2026-10-10 (ACT 3 DONE): 18 shots rendered (s03 and s11a retaken once, s02 re-queued after a failed Colab take), Colab OFF, balance 832.05 -> 814.78 = 17.27 CU, series total 29.13 of the 100 CU cap. Voice: Orpheus line $0.0053 + Teller $0.0752 (CEO "OK เสียง" over the $0.25 cap), series voice about $0.2675. Assembled by `build_act3_edit.py` (107.1 s, -16.6 LUFS, A/V equal), provenance `ACT3-th-provenance.json`. Sent to the CEO: ACT 3 540p and joined ACT 1+2+3 540p (4:28), not yet watched. 1080p masters only in the scratchpad until the CEO says where they are filed. Known flags: s11b small campfires, s10 figures not checked at full size. Next: CEO verdict; ACT 4 to 6 need scripts (about $0.19 more voice, the cap must be lifted) and a CU figure.
STATUS UPDATE 2026-10-10 (ACT 2 DONE): all 14 shots rendered, 3 retakes (s03 once, s04 twice: lit torch, then modern suits on the guests), Colab OFF, balance 843.91 -> 832.05 = 11.86 CU of the 100 CU cap. Assembled by `build_act2_edit.py` (99.4 s, -17 LUFS), provenance in `ACT2-th-provenance.json`. 540p sent to the CEO, not yet watched. Final 1080p lives only in the scratchpad until the CEO says where it is filed. Next: CEO verdict on ACT 1 and ACT 2; ACT 3 to 6 need a passed Thai script and a new voice cap.
STATUS UPDATE 2026-10-10 (CEO OK): CEO "อณุมัต 100CU" = Colab cap for this series' picture work is now 100 CU (was 25). ACT 2 fired the same day: 14 queue rows s01..s15, all colab, 1080p, ids in `h3-fired-act2.json` (s04, s10, s14 got a reference, the studio refuses a first scene with no @handle). Expected about 9.6 CU. Spent so far is read from the Colab balance after the batch.
STATUS UPDATE 2026-10-10 (later): ACT 1 v2 sent (CEO caught the missing voice on the 'Seven months later' card; Teller line added, commit d783474f; rule 'picture text that matters is also spoken' in BRAND.md). ACT 2 picture planned as 14 new H3 shots (90.75 s requested, 1080p) plus a 6 s montage cut from the owned clips: `build_act2.py` writes `shots2/` (dry run clean, grep clean). NOT fired: waiting for the CEO's OK on the CU figure (expected about 9.6 CU, cap 15, of the 25 approved, 15.1 left). Colab off.
STATUS: 2026-10-10 ACT 1 and ACT 2 Thai scripts PASSED by the CEO; Thai TTS for both made (voice $0.1167 this batch, cumulative about $0.186 of the $0.25 cap). ACT 1 Thai cut DONE and sent (61.6 s, ACT1-th-provenance.json): king shot e05 rendered on Colab (0.43 CU by balance, guard estimate max 0.91), Colab OFF confirmed 08:42. Waiting for the CEO to watch ACT 1 and hear ACT 2. ACT 3 to 6 not written (need his pass and a new voice cap: about $0.27 vs $0.064 left). Last agent: cmo-f76492bf, 2026-10-10.

CEO order 2026-10-09: "ลองทำ ฉากจริง สไตล์ภาพจริง เนื้อเรื่องจริง เสียงภาพจริง (เฉพาะภาษาไทยก่อน). ทำมา 1 นาทีให้ดูเลย. ใช้ Skill การทำภาพยนตร์เลย. ถ้าจำเป็นต้องมีเสียงพูดของตัวละคร ให้ใช้เทคนิคเดียวกับเสียงภาพของละครสั้น เพียงแต่ปรับเปลี่ยนเป็น Eleven Lab v4 อย่างเดียว. ทำ 1080P 15s x 4."

## How it is made (CMO_Workflow_ShortFilm steps, only the ones this minute needs)

| Step | What | Tool | Cost | Gate / CEO time |
|---|---|---|---|---|
| 0 Brief | this plan | | $0 | CEO OK on the 4 questions |
| 2 Story | script + scene-engine audit (SCRIPT-TH.md v3) + 3-reader comprehension gate | | $0 | three Thai readers pass the gate, then CEO approves the script, 5 min |
| 3 Plates | 6 pictures, one photograph each: Orpheus face, Orpheus full body, lyre, underworld stair, Teller's room, dusk river with the far ridge. New entities in a new group "The Old Telling", none from the library | ChatGPT runner on winbox 9224 (`tools/chatgpt_images.py`) | $0 | contact sheet, CEO approves by number, 10 min |
| 4 Shot plan | 4 shots = 4 clips, 4 independent cards, hard cuts in the edit (no chain: clip 1 changes room) | continuity table | $0 | none |
| 5 Previz | skipped: no hard camera move | | | |
| 6 Prompts | house format, generated from data, dry run + 60-second check + `shotsheet_lint.py`; entity refs counted by `savedRefs` | CMO_Standard_Film_PromptFormat | $0 | cost table to the CEO (HARD) |
| voice | Teller narration + Orpheus' line, ElevenLabs v4 Thai only. Audition 3 stock voices on one sentence, CEO picks by ear | fal `elevenlabs/tts/eleven-v4` (script from the 2026-10-09 test) | cap $0.25 | CEO listens, 5 min |
| 7 Wave 1 | one back-to-back batch of 4 cards at quality 1080p (mode r2v_max, 1920x1088), 15 s each, on Colab. Queue all 4 before it starts, so the VM never idles | `POST /api/scenes/enqueue`, one-card batches | about 11 CU | none |
| 8 QC | one numbered contact sheet, start / middle / end frame per clip, eye check then numbers (`CMO_Knowledge_Film_Production` section 8); ASR check that his line was said | `tools/film_transcript.py` | $0 | CEO marks keepers |
| 9 Edit | assemble 4 clips, lay Teller narration over (not bound to H3), mix, grade with a house LUT, first-3-seconds test, Thai subtitle file; deliver 1080p master + 540p preview | ffmpeg, `film_cut_assemble.py`, `film_music_mix.sh` (no music) | $0 | CEO watches the minute |

## The voice technique (same as the short dramas, path B, with ElevenLabs v4)

- Path B (CEO 2026-10-05, measured 10-05 and 10-07): the character's spoken line is synthesised first, passed to H3 as a reference audio with marker `fully_copy`, the prompt carries a `Speech timing:` block, and H3 moves the mouth during the render. No lip-sync post pass.
- What changes: the studio's automatic voice step calls Seed Audio on fal. Here the line is made by the ElevenLabs v4 script and attached to the card through the studio's `audios` field, so Seed Audio is not called and no code change is needed. If the card route refuses it, the Mac CTO swaps the provider (his lane).
- Only the character's line goes into H3. **The Teller's narration is never bound to H3**: it is a voice-over, and bound audio would make the people on screen mouth it. Narration is mixed in the edit. Prompt carries `non_diegetic_music: none` and its own soundscape block.
- Voice casting: three stock voices on one sentence, CEO chooses by ear. The Teller and Orpheus get different voices.

## Money (HARD: nothing fires before the CEO says yes to these numbers)

| Item | Estimate | Basis | Cap I ask for |
|---|---|---|---|
| ElevenLabs v4 voice | $0.041 for one full narration read (515 characters at $0.08 per 1,000) | measured price, 2026-10-09 | **$0.25** (3 reads, audition, Orpheus line, takes) |
| Plates | $0 | free runner | $0 |
| H3 on Colab, 4 clips at 1080p | about 2.6 CU per clip, 10.4 CU, plus about 0.5 CU VM setup = **about 11 CU** | **ESTIMATE [A].** 540p measured 0.74 CU and 297 s per 15 s clip; 1080p on RunPod measured 1,033 s median (n=30), 3.5 times longer. 1080p has never run on Colab | **25 CU** (one retake round of 2 clips included). Balance read live today: 887.48 CU, so 2.8% of it |
| Fallback if 1080p fails on Colab | RunPod: 4 x about $0.94 + about $0.38 pod boot = **about $4.15** | RunPod median 1,033 s per clip at $3.29/h | not requested; needs the CEO to open the pod |

Plan for the unknown: the first card is queued alone as a probe. If it fails or runs out of memory I stop and report; I do not re-fire (a refire is a new spend).

## Risks

- **1080p on Colab is untested.** Biggest unknown. Probe first.
- Face and prop consistency across 4 independent cards: identity comes from the entity refs, plus one signature prop (lyre) and one lighting rule (the only warm light is on him).
- Thai lip-sync of one short word on ElevenLabs audio: n=0 for ElevenLabs, n=1 for Gemini TTS. Drop the line if the mouth fails; the cut still works with narration only.
- Thai names read by the voice (ออร์เฟอุส, ยูริไดซี) are my spelling; the CEO's ear decides.
- Studio state today: :4100 up, pod off, Colab off, balance 887.48. The Mac CTO owns the UI and the API; I only queue my own cards.

## Questions for the CEO (recommended answer first)

0. **Thai first story.** Evidence from World of Legend: every top video is a name the Thai viewer already owns; Orpheus is not. Keep Orpheus (plates and script ready, weak Thai pull) or switch the Thai test to Medusa (a monster with a backstory, about 1.47M views on that channel, needs new plates and a new script)? Recommend: ask before any spend; if the goal is Thai views, Medusa.
1. Script v3 OK, or edit? It must pass the 3-reader gate first (SCRIPT-TH.md). Recommend: OK, then change words by ear after the voice audition.
2. Orpheus speaks one word ("ยูริไดซี!") with H3 lip-sync? Recommend: yes, it is the cheapest test of path B with ElevenLabs.
3. Money: voice cap $0.25, Colab cap 25 CU (about 11 expected). Recommend: yes.
4. 16:9 for this minute (the series is long-form)? Recommend: yes; a 9:16 teaser is a later cut.
