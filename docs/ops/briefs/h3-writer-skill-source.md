# H3 Scene Writer skill: DRAFT (distilled 2026-10-02 from the CMO film skills)

Source for the studio default Writer Skill. CEO chose option B on 2026-10-02 (session cto-addb58de).
Source codes are listed below. Measured-on tags: [ANY] holds on any engine by its nature, [H3] measured on MiniMax H3, [FLOW] measured on Google Flow, [SD] measured on Seedance. A [FLOW] or [SD] rule is untested on H3.
SE = CMO_Gate_Story_SceneEngine · TMD = CMO_Standard_Story_ThaiMoralDrama · FP = CMO_Knowledge_Film_Production ·
PF = CMO_Standard_Film_PromptFormat · H3 = CMO_Knowledge_MiniMax_H3 · CON = CMO_Gate_Flow_Omni1.1_Continuity ·
LS = CMO_Workflow_LakornSerial · SDK = CMO_Knowledge_Seedance2.5_Higgsfield · MP = docs/prompts/MASTER-PROMPT-cinematic.md (doc, not a skill) ·
PQ = ComfyRunpod docs/PROMPT-QUALITY.md (doc, not a skill)

---

## PLAN — split the story into scenes (one call per story)

The story lines are the CEO's own and are fixed. Only choose where the scenes break, the bridges, and each end_state.

P1. Break where the story turns: a scene ends where a threat opens or resolves, or right after a reversal lands. Never break in the middle of an exchange. [ANY] (src: SE §4 Reversal "Sequence"; TMD Structure gate 2)
P2. Each scene ends on a live question or a turn in progress, never on atmosphere. That moment is its end_state. [ANY] (src: TMD §Length mid-roll rule; TMD gate 2; LS TEASER)
P3. Scene 1 puts the conflict, the want or the threat on screen in its first seconds, not mood. [ANY] (src: TMD gate 1; LS HOOK)
P4. A scene holds only what one clip can film: 3–4 timed beats; dialogue at about 2.5 words per second of beat, ≤12 words per line (Thai ≤ ~30 syllables per 8 s); each change of speaker costs a beat (two speakers in 6 s, three lines with two changes need ~10 s). Over capacity means more scenes, never fewer words. [SD/FLOW] (src: MP must-do 11; TMD §DENSITY ceiling; TMD §acts-while-speaking rule 4; PF §2.5)
P5. A long line (~5 s or more) followed by another character's reply in the same scene: split it by speaker. Scene A = the long line, with the listener reacting silently; scene B = the reply. Never shorten the line. [FLOW, H3 untested] (src: CON rule 10)
P6. A change of place or time starts a new scene. That scene opens by establishing it: a wide shot of the new place, or a clear marker for a time jump. [ANY] (src: TMD gate 6; CON Workflow 2)
P7. One scene = one continuous timeline. Two actions that happen one after the other with a gap between them are two beats, or two scenes. [ANY] (src: PF §1; TMD §acts-while-speaking rule 1)
P8. end_state lists who is where, which way each person faces, what they hold, wardrobe condition, light and weather. The next scene starts from exactly that. [ANY] (src: MP must-do 12; FP §9)
P9. Shorter clips keep faces and hands intact. When a split is a close call, choose more, shorter scenes. [H3 reasoning, not measured] (src: PQ §0)

## WRITE — film ONE scene (one call per scene)

Names and identity
W1. Each character, place and prop has ONE fixed name, used every time (a character's name is their @handle). No pronouns and no synonyms ("he", "the man") for a named character. [ANY] (src: PF §3.1; MP E4)
W2. Refer to each character by @handle. The studio attaches the character sheet to the shot itself: never restate it, never contradict it, never write "same as before". [ANY, adapted to the studio's "do not restate" rule, scenegen.ts characterSheetBlock] (src: MP E5; FP §2; CON §look sheet)
W3. Never describe a character against their reference picture. A different state (soaked, hurt, changed clothes) is written out as a state. Name the garment; a "bare <body part>" phrase spreads to more skin than asked. [FLOW] (src: MP E2; FP §3; CON rule 4, note 2026-09-27 "neck bare")
W4. Everything visible is declared: every person, animal and prop on screen is named, or the model invents one. State the count ("exactly two people in the room") AND where each person stands. The count alone did not hold; placement did. [SD, H3 drew one man twice] (src: MP E3; SDK §IRON RULE; H3 §6)
W5. Put characters in their positions from the first frame. Avoid a beat that moves a character across the set while a crowd is in frame. [H3] (src: H3 §6)
W6. In wide or aerial shots, keep the character pictures out and describe small distant figures in words. [H3] (src: H3 §6)

Camera and action
W7. Use 3–4 timed beats that add up to the clip length. Write each beat in this order: shot size + angle, then NAME + countable physical action + direction, then camera move, then light/atmosphere. [SD] (src: PF §2.5; MP Part 5)
W8. One framing and one camera move per beat. H3 switched framing mid-beat and skipped an asked-for tilt-up. [H3] (src: H3 §6)
W9. Use physical verbs (grip, slide, pour, slam). Never "becomes", "begins to", "seems to", and never "intense"/"cinematic" without a countable action. [SD] (src: PF §3.4; MP NEVERs 4–5)
W10. Say where every face points, in camera terms: facing the camera, back to us, profile looking left. H3 turned characters to the lens when this was not said. Keep screen direction the same across scenes. [H3] (src: H3 §6; PF §3.5; MP must-do 9)
W11. Give size against something in the frame ("no wider than the door"), not with depth words. [SD] (src: PF §3.5; SDK §Size)
W12. Describe the set in full sentences: surfaces, the light source, what is behind and beside the subject. Otherwise the reference's own background becomes the set. Name every light, the time of day and the weather; keep them the same across a sequence. A location line shorter than the character line drifts. [FLOW; H3 reasoning] (src: CON §set drifts; MP must-do 8; PQ §7c)

Acting
W13. Every person in frame has their own continuous action, different from the others, and reacts to what is said; nobody stands still waiting for a line. Write the speaker's 2–4 physical beats during the line, then "the whole time X talks, Y …", then Y's reply with its own gesture. [FLOW] (src: FP §8; TMD §Overflow acting)
W14. Act WHILE speaking: the action and the line happen in the same instant. Never write "then". No silent actions ("pauses", "lets out a breath", "considers"). [FLOW] (src: TMD §acts-while-speaking 1–3)
W15. In the action line, name the speakers in the order they speak. [FLOW] (src: TMD §acts-while-speaking 5)
W16. Put emotion early and physically: face, voice and body for EVERY person in frame, with an intensity of 1–5, placed in the scene sentence rather than as a trailing adjective. Show heat, embarrassment or arousal by action (looks away, bites the lip, rubs the back of the neck). NEVER write blush, flushed, red face, red cheeks or red ears. [FLOW + H3 HARD] (src: TMD ⛔Emotion, with its "face red" example removed; H3 §2 rule 5)

Dialogue and sound
W17. Keep every quoted line verbatim, in its original language. Format: NAME, manner of ≤5 words: "line". A longer direction goes in its own sentence before the line. [SD, held on H3] (src: PF §3.3; H3 §6)
W18. State an off-screen speaker as off-screen, and keep the visible character's lips closed. [H3 doc] (src: PQ §5 Speaker ids)
W19. Sound: world sounds only (studio adds the no-music block). No on-screen text, subtitles, logos. [ANY] (src: MP must-do 10, NEVER 6; H3 §5 Audio)

Continuity and wording
W20. Write the scene as CONTINUING the previous end_state, not restarting it; a chained segment reuses the same character set. [H3 doc] (src: PQ §8; MP must-do 12)
W21. A ban needs a replacement: say what to show instead. Use few, aimed negatives. Never write a negative that describes the unwanted image, or one that forbids what the scene asks for. [SD/ANY] (src: FP §7; PF §3.6, §3.8)
W22. Keep notes, file names, dates and tool words (upload, plate, reference, prompt) out of the scene text. [SD] (src: PF §3.7; MP NEVER 7)
W23. Close every scene with: no blush, no red cheeks, no red ears, even natural skin tone. [H3 HARD] (src: H3 §2 rule 5)

## AUDIT CHECKLIST — yes/no per finished scene (cheap model)

A1. Each character has one name only; no he/she/the man used for a named character. (W1)
A2. Characters are named by @handle; appearance is not restated, only a changed state (wet, hurt, changed clothes). (W2, W3)
A3. Every beat states a framing and where each face points. (W7, W10)
A4. Every person in frame has an action in every beat; nobody only stands, waits or watches. (W13)
A5. None of the words "then", "pauses", "begins to", "becomes", "seems to" appears. (W9, W14)
A6. Every dialogue line reads NAME, manner (≤5 words): "line", in its original language. (W17)
A7. The stated people count matches the named people, and each has a position. (W4)
A8. The scene opens at the previous end_state and ends at its own end_state, followed by the HANDOFF line. (W20, P8)
A9. No blush/flushed/red face/red cheeks/red ears anywhere; closing negation present. (W16, W23)
A10. No negative forbids something the body asks for. (W21)
A11. The set is described in ≥2 sentences, with its light source named. (W12)
A12. No on-screen text, subtitles or tool words. (W19, W22)

## STYLE: REAL vs CARTOON

### REAL (photoreal people), from the skills and docs:
R1. Never a real person's likeness or a real brand. Here "real people" means photoreal characters, not lookalikes. (src: MP NEVER 10)
R2. Hands: keep them separated and clear of the face and torso; prefer slow, continuous movement; medium shots over tight hand close-ups. [H3 doc] (src: PQ §0)
R3. Skin realism: use the pores and matte-skin tokens only. Never "freckles" or "natural redness" (that breaks the H3 red-face rule). [H3] (src: H3 field note 2026-09-28; PQ §2a)

### CARTOON
Cartoon: MISSING. No skill covers an animated or cartoon visual style. TMD's "การ์ตูน" means a cartoon-evil villain, not a look. The only near-reference is MP E6: when the cast is not human, add a species line and ban the default species. The lines below were NOT taken from any skill:
C1. [proposed, not from skills] Every scene gets one STYLE line naming the medium (e.g. "2D hand-drawn animation, flat cel shading, clean ink outlines"), pasted verbatim like a look line. Never mix in photoreal words (pores, 35mm, film grain).
C2. [proposed, not from skills] Cartoon characters need reference pictures drawn in that same style; a photo reference plus cartoon words fights itself (the picture wins, W3).
C3. [proposed, not from skills] Cartoon allows exaggerated acting (big gestures, squash and stretch). R2 and R3 do not apply.
