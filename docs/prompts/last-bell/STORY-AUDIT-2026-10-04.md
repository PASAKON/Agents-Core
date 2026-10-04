# THE LAST BELL — story audit (read-only, 2026-10-04)

Scope: story, structure, character logic, dialogue, what each shot communicates, continuation needs.
No image or video was opened. Verdicts on takes come from the QC TSVs only.

Citation keys (file:line):
- `BIBLE` `SCRIPT` `STORYBOARD` `CAST` `NOTES` `REFS` = `docs/prompts/last-bell/<name>.md` on origin/main.
- `A05:13` = `docs/prompts/last-bell/shots/A05.txt` line 13 on origin/main (line 9 = one-line summary,
  12 = THE FRAME, 13/14 = WHAT HAPPENS).
- `eye-C:8` = `Assets/Agents/Core/last-bell/work-a0a0aeec/lb_out/qc/eye-C.tsv` line 8; `stage1:43` = same dir `stage1.tsv`;
  `shots-E:24` = same dir `shots-E.txt`.
- `SE` = `.claude/skills/CMO_Gate_Story_SceneEngine/SKILL.md`; `WF` = `CMO_Workflow_ShortFilm/SKILL.md`;
  `FP` = `CMO_Knowledge_Film_Production/SKILL.md`; `PF` = `CMO_Standard_Film_PromptFormat/SKILL.md`;
  `QC` = `CMO_Gate_Champa_Seedance2.0_ShortMovieQC/SKILL.md`; `IR` = `Agents/Rules/IRON-RULES.md`.

Skills that own story and dialogue for this film: `CMO_Gate_Story_SceneEngine` (structure, IR:1072-1114),
`CMO_Workflow_ShortFilm` Step 2 (WF:115-120), `CMO_Knowledge_Film_Production` §1 story before shots (FP:28-32),
§8 every character acts and every dialogue clip is transcribed (FP:105-112), §10 the director decides every line
(FP:124-130), and `CMO_Standard_Film_PromptFormat` rule 3 for how a line is written into a prompt (PF:67-71).
`CMO_Knowledge_Cinematography_ShortMovie` has no story or dialogue rule (camera, light, colour only; its §6
continuity grammar is the only part that touches the cut). `CMO_Standard_Story_ThaiMoralDrama` is excluded by
the CEO for this film (NOTES:43-44).

---

## 1 · Skill compliance (CMO_Gate_Story_SceneEngine)

**Was the gate run before shooting? No record says it was.**
- grep of BIBLE, NOTES, STORYBOARD, SCRIPT, CAST for `SceneEngine`, `scene engine`, `§51`, `structure gate`,
  `story gate`: zero hits. The only gate named anywhere in the film docs is the QC gate, run after shooting
  (NOTES:154). There is no STATUS.md in the film folder, which WF:32 requires.
- The only engine-shaped artefact is the five-line spine (BIBLE:8-19) plus two verdict arcs (BIBLE:21-22). That is
  a story-level logline. IR:1104-1110 demands the five elements **for each scene** before a single prompt is
  written, and says a scene whose before/after verdict cannot be named "is not ready to generate".
- The bible still says "plot draft v1, not yet a locked script" (BIBLE:4). Its own schedule puts "Locked script"
  in week 2 (BIBLE:98), yet 40 shots went to the queue on 10-03 (NOTES:115-117). WF:116 says the gate runs
  "before any shot exists"; FP:30 says "A scene is prompted only after it passes the structure gate".
- The CEO approved the spine (NOTES:11-15) and delegated the script (NOTES:103, NOTES:119). Delegating the
  script does not waive the gate. IR:1112-1114 says a scene that fails the removal test is reported to the CEO,
  not quietly generated. No such report exists.
- Steps 4 and 5 were also skipped: no continuity table (QC:42-43 records that the named states lived only in
  CAST), and no previz.

**Per-scene audit** (verdicts use SE definitions: the obstacle must put something at risk (SE:46), a tactic must
return information (SE:52-56), at least one reversal per resolved sequence (SE:65), and a reversal with no
value shift is inert (SE:74)).

| Scene | Goal | Obstacle (at risk · scale) | Tactic | Reversal | Value shift | Verdict |
|---|---|---|---|---|---|---|
| A · city of bells (A01–A08) | No goal for anyone. Kaew does her job (A03:9, A04:9) and learns a rhythm (A05:13). The story goal (BIBLE:9-10) has not appeared yet | None until the omen (A08:12), which threatens nothing anyone is pursuing | None | None. A08 turns calm into omen but nobody is judged | None | **FAIL.** No jeopardy means no scene (SE:45). Removal test (SE:36): A02, A03 and A07 can go and the chain holds. Plants that survive: A04 (she rings bells), A05/A06 (rhythm, "one song"), A08 (omen) |
| A07 (shot) | Mek teases | none | none | Kaew turns uneasy at the water (A07:13). Missing in both takes (eye-A:14-15) | none | **FAIL.** Its only turn was never rendered, and its line pays off nowhere (§4) |
| B · storm and Governor (B01–B07) | Kaew decides to ring the great bell (B03:13 grips mallet; B05:13 "decides") | Storm, global (B01:13). Bridge to the chedi cut, local: the path (B04:13) | Goes to Yai and takes THE MALLET (B06:14). The bridge cut does not force this: she already owns a mallet (B03:13) | Bridge cut (B04:13), general form, shifts only the Governor | Governor: greedy → cruel. That deepens a verdict B01:13 already gave ("for those who can pay"); it does not reverse it. Kaew: none | **PARTIAL.** Mek's shout is a working micro-tactic (B02:13: no answer = no help). Kaew's goal is internal. Her decision (B05:13) is not in the cut (eye-B:8: no run-off inside 8 s) |
| B06 (shot) | Yai arms Kaew | Yai "too weak to climb" (B06:9) | hand-over | none | none | **FAIL as written.** "Too weak to climb" implies Yai was the one meant to ring the bell. Nothing in A sets that up |
| C · the crossing (C01–C10) | Reach and ring the great bell before the wave (BIBLE:9-10) | Flood (C01), boat smashed (C03:13), gale (C05/C06), rope gone (C07:14), mallet slips (C09:13). All local | Boat (C01: nobody is shown deciding or asking Mek), climb wreckage (C04:13), climb with a line (C05:13), mallet → bare palms (C09:13) | **None inside C.** Every tactic succeeds; none fails and returns information (SE:52-56) | None. Kaew starts brave and ends brave. C02:13 "she does not stop" is the only character beat, and it is unused | **FAIL as a sequence.** It passes only if C+D count as one sequence, with D's reversal closing it. **C07 is a fake obstacle:** the rope is gone, but she already holds the mallet (B06/B07), so nothing is at risk (SE:46) |
| D · the chain (D01–D06) | The goal is achieved: the Naga rises (D01:14). Kaew gets no new goal until E | The Naga turns destructive (D03:13 "the storm doubles"). Whole goal at risk on paper | Kaew reads the engraving (D04:13). That is a discovery, not a tactic | Form 1, my own act flips on me (SE:60). Ringing to save the city freed the threat (BIBLE:15-16) | BIBLE:21 "brave child → the one who doomed the city". **Not visible:** the only victim is the villain (D03:13), the crowd cheers (D01:14, D02:13), and the wave was already coming before the bell (C08:12) | **FAIL: inert reversal** (SE:74, SE:201, IR:1108-1110). Also an order contradiction: the Naga rises (D01) and attacks (D03) while still banded. The bands break only at D06, "in the same instant as the bell" cracks (D06:13, D05:13) |
| E · the lullaby (E01–E10) | Stop the Naga and save the city | Naga's head at the pavilion: Kaew's life, local (E01:14). The wave: the city, global (E06:13) | Lullaby rhythm (E04:14). It is a reasonable guess only if the viewer links the engraving, the line "one song" (E03:14) and the subtitle "Naga" (BIBLE:90). It works first try | The destroyer becomes the wall (E06:13), form 2/3 | Naga "monster → wall" (BIBLE:22). "Monster" was never shown (D), so on screen it reads guardian → guardian. Kaew "doomer → keeper": the first half was never earned. "Keeper" is never shown or said (§3 #19) | **PARTIAL.** Structure present, shift weak. The outcome is exactly what the legend promised (B03:13), so the twist cancels itself |

Trajectory check (SE:76): Kaew's on-screen verdict runs bell girl → brave → brave → (told guilty) → gentle →
keeper. One step is spoken, never shown, and nothing deepens. Yai, Mek and the Governor each have one fixed
verdict for the whole film.

---

## 2 · Structure (shot ids, start times from STORYBOARD:9-49)

| Beat | Shots | When | Note |
|---|---|---|---|
| Foreshadow | A08 | 1:10 | Lagoon turns yellow, fish flee, bells stop (A08:12) |
| **Inciting incident** | B01 (+B02) | 1:20 | The Governor announces the hundred-year storm and abandons the poor (B01:13) |
| Goal locks / plot point 1 | B03 → B04 → B05 → B06 | 1:40–2:22 | Legend (B03:13), bridge cut (B04:13), the look at the chedi (B05:13), the mallet (B06:14). Kaew's decision is never said or clearly shown |
| Rising action | C01–C08 | 2:28–3:38 | Pure escalation, no reversal |
| False victory / midpoint | C09–C10, D01–D02 | 3:38–4:23 | The bell rings, the Naga rises, the crowd cheers |
| **Turning point (twist)** | D03 → D04 → D05 → D06 | 4:23–5:01 | The Naga smashes the barge; the engraving shows a naga in chains; "No... I woke it"; the bell cracks; the neck bands fall. 68 % into the cut |
| Dark moment | E01–E02 | 5:01–5:19 | Eye to eye with the Naga; "Kaew, run!" |
| **Climax** | E03 → E04 → E05 → E06 → E07 | 5:19–6:12 | Memory, lullaby, the eye closes, the coil wall, the wave breaks |
| **Ending** | E08 → E09 → E10 | 6:12–6:46 | Dawn: Kaew beside the sleeping Naga, the bell broken; Yai at peace; aerial; title |

Cut time is 6:46 against a target of "about 8 minutes" (STORYBOARD:3, BIBLE:3, NOTES:17, NOTES:39).

---

## 3 · Character logic and plot holes (what a viewer will ask)

1. **The twist undoes itself.** The legend says ring the bell, the Naga rises and holds back the sea (B03:13). The
   film does exactly that: C09 → D01 → E06/E07. The chain reveal (D04–D06) changes no outcome; it only adds a song.
   A viewer leaves thinking "so the old man was right".
2. **The Naga never hurts the city.** Its only act of violence capsizes the villain's barge (D03:13), which the
   audience cheers along with the rooftop crowd (D01:14, D02:13). "No... I woke it" (D05:13) is therefore a girl
   regretting a success. The verdict "she doomed the city" (BIBLE:21) has no image behind it.
3. **The storm comes before the bell.** The omen (A08), the announcement (B01), the black sky (B04) and the
   mountain wave (C08:12) all happen before Kaew strikes (C09). "The storm was the Naga all along" (BIBLE:16) is
   never put on screen; the only hint is "the storm doubles" (D03:13), in a shot that failed QC (eye-DE:4). If the
   Naga slept in chains, who made the storm? If the Naga blocks a wave that existed before it woke, it is a
   guardian and the twist is false. If the wave is its own, it is blocking itself.
4. **The chain breaks after the creature is already loose.** The Naga rises at D01 and attacks at D03 with its
   bands on. They burst at D06, timed to the bell's crack at D05 (D06:13). So the chain never held it.
5. **Yai knew, and said nothing.** The lullaby she hums in A05:13 begins "นอนเถิดนาคา" ("Sleep now, great Naga") and
   says "the bell will sing you to sleep" (BIBLE:85-86, BIBLE:90). She knew the bell's song put the Naga to sleep.
   She still hands over the mallet (B06:14) and lets Kaew leave believing the legend. That is hidden agency
   (SE:61) left unused, and it raises a question the film never answers.
6. **"Ring it right" is never visibly broken.** C09:13 shows wild striking. No beat shows Kaew starting the rhythm
   and abandoning it, so the viewer cannot connect "rang it wrong → enraged" with "rang it right → calmed". The
   setup and payoff exist only in the writer's head.
7. **The mallet has no function.** Kaew already owns a mallet (A03:12, B03:13). Yai's red-thread mallet has no
   stated power. It slips away (C09:13), she finishes bare-handed, and it reappears in E04:14 and E08:12 without
   being picked up. B06/B07 spend 18 s on a ceremony for a prop that does nothing.
8. **The rope-is-gone obstacle is fake.** C07:14 is solved before it appears, because she already holds the mallet.
9. **Kaew → Yai → Mek has no connective tissue.** She decides at the broken bridge (B05), shows up at Yai's (B06),
   then is suddenly in Mek's boat (C01:12). Nobody asks Mek, and Mek never agrees.
10. **The Governor's motive for cutting the bridge** (B04:13) is unreadable. His barges leave by water, and a
    crowd cannot follow a barge over a bridge to an island. The cut only works if the island is the refuge or he
    wants to stop the bell. Neither is set up, so it reads as a device to create Kaew's obstacle. BIBLE:57-58
    says "so the crowd cannot follow", and the picture does not support even that.
11. **Mek teleports.** He is thrown into the water (C03:13); only Kaew crosses the wreckage (C04:12). Then he is at
    the chedi base holding a rope tied to her waist (C05:12). Where did a rope come from after a shipwreck? Next he
    is back on a floating beam (D02:12), back at the base (E02:12), then rowing "a small boat" at dawn (E08:14),
    though his boat was smashed (C03:13). Four positions, no transitions.
12. **The waist rope does nothing.** Paid out from the base of a tall chedi (C05:9), it cannot catch a fall near
    the top, and it hangs slack at E02:12. It also muddles "the bell rope" (C07).
13. **"Late again, bell girl!"** (A07:13) comes in the afternoon, after she has rung the morning bell on time
    (A04). Late for what? It is never paid off.
14. **The fish flee toward the open sea** (A08:12), which is toward the storm and the Naga. Fleeing into the danger
    tells the viewer the danger is inland.
15. **The wave's clock stops.** It is on the horizon at C08 (3:31). It is not seen again through D, and at E06
    [10s] it "arrives on the horizon" (E06:13), still on the horizon 2+ minutes later.
16. **The hero is absent from her own climax.** E05, E06 and E07 have no Kaew (E05:12, E06:12, E07:12). She neither
    watches nor reacts as the wave hits.
17. **Kaew is passive at the twist.** The bell cracks by itself while she whispers (D05:13); she does not break it.
18. **Kaew's stake is generic.** She loses nothing personal. Yai's house is never shown flooding (B06:12 shows only
    rain leaking), so the "save the city" goal has no face. The child with the small bell in C02:13 is the one
    personal hook, and it is never paid off.
19. **"Keeper" is undefined.** The word exists only in BIBLE:80 and STORYBOARD:47. On screen a girl sits by a
    sleeping serpent. The world rule (asleep a hundred years, storm every hundred years, who wakes or calms it
    next time) is never said or shown.
20. **Yai's last shot reads as her death** (E09:13 "smiles and closes her eyes, at peace"). Nobody reacts, and Kaew
    never returns to her. If Yai dies, the film skipped its emotional payoff; if she lives, the shot misleads.
21. **The Governor and the class theme go nowhere.** "For those who can pay" (B01:13) has no paying passengers
    shown (B04:12), and the Governor is never seen again after the capsize (D03:13).
22. **The legend comes from a stranger.** An unnamed walk-on with no reference image (NOTES:123) delivers the
    film's key belief. Yai, who already owns the song, is the natural source.
23. **Continuity of states the story depends on:** E10 shows the bell hanging whole after E08 broke it
    (NOTES:169). CAST says the bell is cracked "from D3" while D05 cracks it (NOTES:168, CAST:19). Kaew should be
    soaked in E04 and is dry (eye-DE:10).

---

## 4 · Dialogue (every spoken line; SCRIPT:7-17)

English is the film language; the Thai lullaby is the one exception (SCRIPT:3).

| Shot | Who | Line | Necessary? | In character? (CAST:9-13) | Tells what the picture shows? | Take / read-back |
|---|---|---|---|---|---|---|
| A05 | YAI | "Every bell in this city has a voice. The great one has only one song." | **Yes.** Plants E03/E04; "the great one" means the bell now and the Naga later | Yes (warm, sly, knowing) | No | 1.0 (stage1:11) |
| A05 | KAEW | "Which song?" | Yes, it triggers the hum | Yes (quick) | No | 1.0 (stage1:11) |
| A07 | MEK | "Late again, bell girl!" | **No.** Orphaned, and it contradicts A04 | Yes (cheeky) | No | The chosen t2 reads "Let again bell girl", 0.82 (stage1:14). Listen, or cut |
| B01 | GOVERNOR | "The storm of a hundred years is coming. My barges leave at dusk, for those who can pay." | Yes: the storm, the cycle and the villain in one line | Yes (smug, greedy) | No (the storm is not yet visible) | The chosen t2 reads "leave at desk", 0.91 (stage1:18). Listen |
| B02 | MEK | "And the rest of us?" | Partly. It voices the abandoned poor; could be shouted off-screen over B01 | Yes (loud, loyal) | No | 0.79, heard "for the rest of us!" (stage1:20). "And" lost |
| B03 | OLD BOATMAN | "Ring the great bell, and the Naga will rise to hold back the sea." | The content is necessary; **the speaker is wrong** (§3 #22). The line also comes literally true at E06/E07, so it is not a false belief, and the twist depends on it being one | n/a (no CAST row) | No | 0.98, heard "Nanga" (stage1:21) |
| B06 | YAI | "If you ring it, ring it right." | Yes, the plant for E04. Its failure (C09) is never shown (§3 #6) | Yes | No | 0.95, heard "bring it right" (stage1:25). Listen |
| D05 | KAEW | "No... I woke it." | **Weak.** She says the thing she set out to do (B03). It does not state the twist (the bell held the Naga) | Yes (guilty) | It narrates her face; adds nothing | **Never shot until 10-04** (NOTES:131, NOTES:164) |
| E02 | MEK | "Kaew, run!" | Yes, it makes her staying a choice (BIBLE:17) | Yes (scared) | No | **0.0, nothing heard** (stage1:43). Mek in the wrong place (eye-DE:8). QC's claim "every line read back 0.79–1.0" (QC:26) is wrong for this clip |
| E03 | YAI (memory) | "The great one has only one song." | **Yes, the key to the tactic** | Yes | No (verbatim echo of A05, fine for a memory) | **Line falls outside the cut:** heard at 11.9–14.7 s (stage1:44), but the cut is the first 8 s (shots-E:24, STORYBOARD:42) |
| E04 | KAEW (sings, Thai) | the four-line lullaby (BIBLE:85-88) | Yes, the climax | Yes (tender) | Line 3, "three slow, one fast", names the rhythm she is tapping. Acceptable in a song | **Four sung lines crammed into [4s]–[12s]** (E04:14): 8 s for a lullaby. Read-back 0.39 (stage1:45). The take is FAIL (eye-DE:10) |

What is missing from the spoken track:
- Kaew never states her goal. Her two English lines are a question and a regret. One line at B06 ("I'll ring the
  great bell") would lock the goal and turn Yai's line into an answer.
- Nobody says what the bell really was. The twist rests on one engraving glimpsed by lightning (D04:13).
- Nobody explains the bridge, nobody asks Mek for help, and nobody says "keeper".
- Prompt-format nit (PF:67): E04's tag "KAEW, singing softly in Thai, to the eye:" is over 5 words; A07's line
  is fused to a long action clause. Neither is a story problem.

---

## 5 · What the audience sees vs what it communicates

| Act | Sees | Communicates | Does not communicate |
|---|---|---|---|
| A | A gold-green floating city, a girl running and ringing a bell, a grandmother teaching a rhythm, a boy teasing, fish fleeing | Kaew is the bell girl. Three slow, one fast. "One song". Something is wrong | Why the great bell matters, who Mek is to her, that the omen has anything to do with a Naga |
| B | A fat man on a gold barge, a boy shouting, an old man pointing, barges leaving, a bridge falling, a girl staring, a mallet handed over | Storm coming. The rich flee. A legend. The road is cut | Why the bridge is cut, that Kaew decided, why this mallet, who Yai is to the bell |
| C | A boat in a flood, families on roofs, a shipwreck, a climb, a mountain wave, a girl beating a bell bloody, a shock ring | She is brave and will not stop; a clock is running | Any setback that changes her plan, what Mek is doing, the danger of ringing it wrong |
| D | A jade serpent rising, cheering, the barge smashed, a chained naga engraving, a whisper, the bell cracking, neck bands falling | The Naga is real, the villain is punished, Kaew feels guilty | Why waking it is bad (no innocent is harmed), that the storm is the Naga, why the bands break after it rose |
| E | An eye at the pavilion, a boy screaming, Yai in memory, a song, an eye closing, a ring of scales, a wave breaking, dawn, Yai smiling, aerial | The song calms the Naga, it protects the city, the girl bonded with it | What "keeper" means, whether Yai lives, why a guardian needed calming, where Kaew is during the wave |

**CUT / MERGE list** (seconds are cut lengths from STORYBOARD)

| Shot(s) | Action | Why |
|---|---|---|
| A02 (7 s) | **CUT** | A01 [5s] already swings thousands of bells (A01:12). Nothing new |
| A03 + A04 (20 s) | **MERGE → one ~10 s shot** (or trim A03 to 4 s) | A03 never reaches the tower in the cut (eye-A:7). A04 carries the job |
| A07 (10 s) | **CUT, or REWRITE** | The line is orphaned and the unease beat is missing in both takes (eye-A:14-15). Keep only if the line plants the omen and Mek's boat |
| B02 (8 s) | **MERGE** into B01 as an off-screen shout plus a 3 s reaction | Saves a shot; same information |
| B03 (10 s) | **MERGE the legend into Yai** (A05 continuation or B06) and cut the walk-on | Yai becomes the source of legend, song and warning (§3 #5, #22) |
| B07 (6 s) | **CUT**, unless the mallet gets a rule | The prop does nothing (§3 #7) |
| C05 + C06 (17 s) | **MERGE → one 10 s climb** | C06's slip is an obstacle with no consequence |
| C07 (8 s) | **CUT.** Move "she looks out to sea" into C08 as her POV | Fake obstacle (SE:46), and the take is FAIL (eye-C:8) |
| D02 (8 s) | **CUT, or relocate** Mek to the chedi base | Repeats D01's cheer and breaks Mek's geography (§3 #11) |
| D03 (12 s) | **REWRITE**: keep the barge, add the coil crushing the C02 rooftops (the child's bell drops into the water) | The only way the twist's verdict "she doomed them" can land (§3 #2) |
| D04 + D05 (18 s) | **MERGE → one 15 s standalone shot** (lightning shows the engraving → line → crack) | Removes the only continue shot, and with it the frame bug in §6 |
| D06 (8 s) | **MOVE** before D01, or cut | Fixes the order (§3 #4) |
| E02 (6 s) | **MERGE**: "Kaew, run!" off-screen over E01 | The line is not heard in the take anyway (stage1:43) |
| E03 (8 s) | **REPLACE with A05 t1 footage**, 2.6–8.6 s (stage1:11), graded as memory | The generated take's line is outside the cut (stage1:44). Re-using A05 costs nothing and matches exactly |
| E08 tail + E10 (≈ 6 s + 12 s) | **MERGE**: end E08 on Kaew and the Naga; let E10 alone carry the aerial | E08 [9s] already cranes up to "the sleeping coil around it" (E08:14), the same image as E10 |
| E09 (7 s) | **KEEP only with a clear payoff** (Yai taps the rhythm back, alive), else cut | It reads as death with no reaction (§3 #20) |

---

## 6 · Scenes that need more than 15 s of continuous action

Continuation method on file: the previous clip's frames at −1.0 s, −0.5 s and the last frame go into the last 3
slots (REFS:16-19, NOTES:34). That leaves 6 slots for the other references (REFS:14). A change of location gets
no continue frames (REFS:20).

**Frame bug to fix first.** The continue frames are taken from the end of the 15 s render (`-sseof`, REFS:21), but
the cut uses only the first N seconds (STORYBOARD:3). D05 was fired on D04's last 3 frames (NOTES:164), at
14.0/14.5/15.0 s, while D04 is cut at 8 s (STORYBOARD:37). So 6 s of unseen action sit between D04's last cut
frame and D05's first frame. For any continuation, either use the parent clip in full to 15 s, or extract the
continue frames at cut−1.0, cut−0.5 and cut.

| # | Scene / shots | Why one 15 s clip is not enough | What the continuation must carry | Cut-away / B-roll to hide the join |
|---|---|---|---|---|
| 1 | **E04 lullaby** → E04a + E04b (continue) | Four sung lines plus the tap twice. A lullaby runs about 5 s a line, so 20–25 s. The current prompt crams it into 8 s (E04:14, read-back 0.39) | E04a: tap, then lines 1–2. E04b, from E04a's last 3 frames: lines 3–4, the final tap, the wind falling. Same light, same soaked state, same cracked bell | **Parallel cross-cut with Yai** singing lines 1–2 in memory (A05 set, warm lamp), so Kaew picks the song up from Yai, a duet across time. Or E05 (the pupil widening) between the halves. Or the C02 child tapping three slow, one fast on her small bell |
| 2 | **C09 the bell until her hands bleed** → C09a + C09b (continue) | "Until her hands bleed" is a duration. 14 s plays as four swings. It is also where "ring it right" must visibly break (§3 #6) | C09a: she starts in the rhythm, three slow, one fast; the wave rises; she panics and bashes; the mallet slips. C09b: bare palms, red on the bronze, the sound growing, the shock ring starting | **Cross-cut**: the wave advancing (a new angle of C08), Mek at the base looking up, the C02 family as the child's small bell starts ringing by itself |
| 3 | **D03 the cheer turns** (rewrite) → D03a + D03b | Cheer, then the coil sweeps the rooftops, roofs collapse, screams. Too many events for one clip, and it carries the twist's verdict | D03a: the coil over the rooftops, the cheer dying. D03b: the C02 family's roof gives way; the small bell falls into the water | **Kaew's face** at the pavilion watching (a new 4–5 s shot). Her seeing it earns "I woke it" |
| 4 | **D04 + D05 engraving → realisation → crack** | 18 s across two shots, with the frame bug above | Best fix: **merge** into one 15 s standalone (engraving 0–5 s, line 5–9 s, crack 9–13 s, step back) | If kept as two: an insert of the Naga's neck bands straining. The two actions are tied ("same instant", D06:13), so the cross-cut is motivated |
| 5 | **A05 lesson + legend** (if the legend moves to Yai) → A05a + A05b (continue) | Rhythm, two lines, the hum and the legend line come to about 25 s | A05b continues from A05a's last 3 frames: Yai stops humming and tells the legend, ending on Kaew's eyes | **A06** (the hands insert) already sits between them and hides the join |
| 6 | **B04 bridge cut** → B04a + B04b | Clouds, barges leaving, ropes slashed, the bridge dropping, the Governor's look: five events in 12 s. Both takes FAIL with cutters on the falling section (eye-B:6-7) | B04a: barges leave, men slash the ropes, the Governor's back. B04b: the empty middle section sags and drops | **Reaction cut-away**: the crowd on the bank and Kaew watching (the B05 angle). No continue frames needed |
| 7 | **C03 → C04 shipwreck → wreckage** | Continuous action in the same place, now split with no link; Mek's fate is lost here (§3 #11) | C04 continues from C03's last 3 frames (cut point, not file end): Kaew surfaces, grabs a beam, Mek pushes her toward the steps and is swept the other way. That fixes his later position | An insert of the mallet sinking and her hand catching it, or an underwater POV of the wreckage |
| 8 | **E06 → E07 coil and wave** | The coil closes, rises, the wave arrives and breaks: two shots with an angle change, so no continuation is needed. But the hero is absent (§3 #16) | — | **New ~6 s shot of Kaew** at the pavilion, still tapping, watching the coil rise, cut between E06 and E07 |

Length effect: #1, #2, #3, #5 and #8 add about 50–60 s. The CUT/MERGE list removes about 50–60 s. The cut stays
near 6:46, still about 1:15 short of the 8-minute target (BIBLE:3). Close the gap with story (the D03 rewrite, a
Kaew–Mek beat before C01, a closing beat with Yai), not with more scenery.
