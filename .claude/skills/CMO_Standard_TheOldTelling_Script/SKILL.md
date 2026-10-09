---
name: CMO_Standard_TheOldTelling_Script
kind: standard
owner: CMO
aka: [old-telling-script, mythology-script-roadmap]
description: >-
  STANDARD — The road map for writing the script of a The Old Telling episode
  (the mythology and folklore series on the ILAG Studio YouTube channel) in ANY
  language, Thai first. Use it whenever you write, rewrite or review the
  narration of an Old Telling episode or sample minute in Thai, English,
  Spanish, German or Japanese, or when a new language is added: study ONE
  high-view channel in that language, read its top 5 videos, find what all five
  share, write the script in that shape, and pass a 3-native-reader
  comprehension test before any voice or render money. Holds the Thai result
  the CEO passed on 2026-10-09 (World of Legend). Do NOT use it for the film
  pipeline after the script is approved (that is `CMO_Workflow_ShortFilm`), for
  scene structure (`CMO_Gate_Story_SceneEngine`), or for BLACK LIQUIDITY and
  Thai moral dramas, which have their own script standards.
audience: [cmo, cto, script_writer]
created_by: agent
---

# Writing an Old Telling script, one road map for every language

CEO ruling 2026-10-09: the Thai script v3 passed ("V3 ผ่านแล้ว"), and every other language uses the same road map as Thai. Brand values (palette, taglines, hard rules) live in `knowledge/brand-knowledge/brands/the-old-telling/BRAND.md`; this skill holds only the process and the measured results.

## The road map (same for TH, EN, ES, DE, JA)

| Step | Do | Output | Gate |
|---|---|---|---|
| 1 One channel | Pick ONE channel in that language with the most views, in our own style: narrated legend or folklore stories. Reject channels that are one format among many, ghosts only, or a talking host. Never blend channels | channel id and why | none |
| 2 Top 5 | Pull its Popular list, read the 5 most-viewed videos that have a caption track in that language. Name the ranks that had none | 5 transcripts in the scratchpad | say which ranks were skipped |
| 3 What all five share | Count, per video: title pattern, how sentence one opens, any greeting or teaser, order of events, who speaks, narrator register, specifics (place, year, count), a rule the viewer applies to themself, how it ends, length and pace | a table of 9 findings with counts, labelled [M] measured or [A] assumed | a finding that 3 of 5 videos lack is not a finding |
| 4 Teardown note | Write wiki `research/<date>-cmo-<channel>-top5-style-teardown.md`: paraphrase only, no transcript copying, caption limits stated, what we copy and what we do not | the note | none |
| 5 Our script | One beat sheet for the story, then write this language fresh from it, never from another language's text. Fill a two-column table "the channel does / this script does". Count characters by code, never by eye | `SCRIPT-<LANG>.md` | `CMO_Gate_Story_SceneEngine` audit |
| 6 Comprehension | Three native readers see ONLY the title and the first 60 seconds of text, cold, and answer in writing: who is the story about, what happens to them, would you keep watching and why. Pass: at least two of three get the first two right with no help | pass or rewrite | **no voice or render spend before it passes** |
| 7 Spend | CEO approves exact dollars (voice) and compute units (H3), then the film pipeline | | CEO |

Do not offer a "% match to research" as a quality measure; the CEO rejected it. A habit checklist measures tricks used, not whether a viewer understands.

## Pulling the data (no API key)

- Channel id: `curl` the channel's `/about?hl=en` page, read `"externalId":"UC…"`. The first `channelId` on the page is often another channel (3 of 6 handles in 2026-10-09).
- Popular list: `https://www.youtube.com/playlist?list=UULP<id[2:]>`; or `yt-dlp --flat-playlist --print "%(id)s | %(view_count)s | %(duration_string)s | %(title)s" <list url>`.
- Captions: `yt-dlp --skip-download --write-auto-subs --sub-langs <lang> --sub-format json3 -o <id> <url>`. Never add `--print`: it simulates and writes nothing. `--list-subs` first.
- Auto-captions have no punctuation and misheard names. Use them for structure and counts only. User agent `MoonieX-research/1.0`, no personal data.

## Thai result (CEO passed v3, 2026-10-09)

Source: World of Legend โลกแห่งตำนาน (UCNP6pwOrjGmRYSrsVNUgQ_w, 3.18M subscribers), ranks 2, 3, 5, 6, 7 (ranks 1 and 4 had no Thai captions). Wiki `research/2026-10-09-cmo-world-of-legend-top5-style-teardown.md`. All five share:

1. Title is "ตำนาน" plus a name the viewer already owns.
2. No greeting and no teaser (0 of 5). A title card and music for 7 to 23 s, then sentence one states setting and subject plainly.
3. Chronological order, no flash-forward.
4. A cause the viewer can follow, often a small act with a huge price; the monster has a reason.
5. A real place, year or count (4 of 5 in the first minute).
6. A rule the viewer applies to themself ("if you answer pretty ...").
7. The voice changes every 30 to 60 s: narrator, short voiced character lines, witnesses.
8. The narrator speaks neutral written Thai; slang and humour live only in voiced characters. No นะ or เลย from the narrator.
9. The end returns to today and stops; one subscribe line at the very end.

The passed script is `docs/prompts/the-old-telling-ep1/SCRIPT-TH.md` v3. Our deliberate deviations from the channel: serious tone with no comic skits (CEO), and the brand ritual line at 0:15.

## Other languages

| Language | Channel to study | Status 2026-10-09 |
|---|---|---|
| TH | World of Legend | done, v3 passed |
| EN | Mysteries of Mythology | top-5 teardown done (wiki `research/2026-10-09-cmo-mysteries-of-mythology-top5-script-teardown.md`); English script not yet through step 6 |
| ES, DE, JA | not chosen | step 1 not done. One channel per language |

- Do not carry a Thai finding into another language. "No greeting" is a Thai result from one channel; measure it again on the channel you pick.
- Each language keeps the same beat sheet (facts, order, source) and gets its own title pattern, register, sentence one, specifics and tagline.
- The CEO reads Thai only. For ES, DE and JA the comprehension readers must be native; a Thai back-translation helps the CEO review but is not the test. No price for native readers yet.
- Check the "name the viewer already owns" finding first: Orpheus has almost no Thai-original audience (11K to 20K). Look up demand in the target language before choosing the first story there.

## Traps seen

- A literal translation of the English line read as nonsense to a Thai reader (v0).
- Plain but literary Thai bored the CEO (v1).
- A mystery cold open with an unnamed "he" left the CEO unable to say what the story was (v2).
- A blend of 5 channels has no key success (v2 method).
- Character counts: ElevenLabs v4 Thai reads about 10.9 characters per second including spaces. Count with code; two hand counts were wrong.

## Before handing a script on

- [ ] Sentence one names who and what, with a name or picture the viewer already knows.
- [ ] Every claim traces to a pre-1931 source, named in the beat table.
- [ ] Characters counted by code, seconds computed.
- [ ] Step 6 passed by native readers.
- [ ] No em dash in public text; no red face or red ears; adults 18+.

## Field notes

Append only; see ADR 0026 for tiers. (none yet)
- 2026-10-09 [MISSING] §Other languages — CEO ruling after the first cut (his words: all text, character voice and picture text in the video are English; dubbing is a separate track per wanted language; no burned-in subtitles because YouTube makes auto captions; characters speak little, in English, and the line is the translation of what the Thai script says). So the master of an episode is ENGLISH, and TH, ES, DE, JA are dub tracks laid on the same picture, made only when asked; the road map above still writes each language fresh, but the picture is built from the English script. Dub lines must fit the English shot times, so the dub script is written against the cut, not before it · evidence: CEO message 2026-10-09 (session cmo-f76492bf), SCRIPT-EN.md v4 · status: pending
- 2026-10-09 [MISSING] §Other languages — CEO waived native readers for the English minute-one sample (his words: 'ได้เลย' to reading a Thai back-translation and judging step 6 himself). Scope: this sample only; ES, DE and JA still need native readers. Put the Thai back-translation in SCRIPT-<LANG>.md so he can judge · evidence: CEO message 2026-10-09, SCRIPT-EN.md · status: pending
- 2026-10-10 [MISSING] §Pulling the data — check every myth fact against the pre-1931 text before it goes in a script: Perseus serves English translations by plain curl with UA MoonieX-research/1.0 (Ovid, Metamorphoses, Brookes More 1922: doc=Perseus:text:1999.02.0028:book=10:card=1 and book=11; Virgil, Georgics English: doc=Perseus:text:1999.02.0058:book=4:card=453 and card=494, the page shows the Latin ed. Greenough 1900 so confirm the translator; Plato, Symposium, Jowett 1871: gutenberg.org/cache/epub/1600/pg1600.txt, search 'apparition'). Strip tags with python -I and grep. Found: Ovid says ankle (not heel), 7 DAYS on the river bank and 3 YEARS shunning women; Virgil says 7 MONTHS (our v3 line is Virgil) and that she was fleeing a man (Aristaeus) when the snake struck; Plato says the gods gave him only a phantom because he was a coward. Sources disagree, so name the poet in each claim · evidence: cmo-f76492bf SCRIPT-TH-FULL.md facts table · status: pending
- 2026-10-10 [MISSING] §Spend approval — the CEO asked to 'read the real telling text that goes into TTS' after being shown ACT tables (id, picture, source, sound columns). He cannot judge a script from a table. Every approval ask for voice money must carry a clean read-aloud text: only the sentences the voice will read, in order, one per line, character lines marked, no ids or notes, names and numbers spelled exactly as TTS will read them · evidence: CEO message 2026-10-10 (session cmo-f76492bf), SCRIPT-TH-FULL.md · status: pending
