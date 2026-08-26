# Absence of Meaning — Character plates scope addition (CTO, mid-session)

Received verbatim mid-task-0cbd8900, after the 5 Soul location plates. Recorded here durably per "add never subtract" — do not paraphrase from memory when actually executing, re-read this file.

## Routing

Location/camera-control → Soul. **Character and Prop → GPT Image Gen 2.** Never mix models within one set. Finish all five locations in Soul first, switch model once, do all five characters in GPT Image Gen 2.

## New CEO rule — applies to every character

MAKE THEM AS HUMAN AS POSSIBLE. Real human skin tones with real variation, real human faces, real human proportions and real bone structure. No pale waxy stylised skin, no doll faces, no smooth airbrushed beauty-filter look, no CGI sheen. The retrofuturist world lives in the ARCHITECTURE and the CLOTHES, never in the people's bodies.

Every character must be DISTINCTIVE and memorable — but that distinctiveness comes from wardrobe, silhouette and dominant colour, NOT from making faces odd. Human faces, unforgettable clothes.

## Format — all five, identical

One wide horizontal CHARACTER REFERENCE SHEET per person, roughly 2.4:1, four panels side by side on a plain seamless light-grey studio background, soft even studio lighting, no environment, no props beyond what the character carries, no text.

- Panel 1: full body front
- Panel 2: large close-up portrait
- Panel 3: full body side profile
- Panel 4: full body from behind

Same person, same face, same clothes in every panel. Four views for the same credits as one — binds far more reliably.

Name exactly `project_absence_char_<name>`, file into the Character folder.

## The five

1. **`char_critic`** — the art critic, middle-aged, speaks with total authority, the loudest voice in the film. Appears in three scenes, must be instantly recognisable. One strong silhouette detail.
2. **`char_collector_a`** — a collector who arrives alone. Dark saturated suit, composed, unhurried, serious, the manner of someone who does not need to impress anyone.
3. **`char_collector_b`** — an elderly very rich collector. WHITE SUIT, chrome-topped walking cane, round dark glasses, a large diamond on one finger. Must NOT be confusable with Valder (extremely tall, extremely thin, bald, floor-length five-colour robe — existing character in this project).
4. **`char_wheelchair`** — OBSOLETE spec, superseded below, kept for record only: ~~a very old woman in a self-propelled wheelchair, layered worn knitwear, headscarf over cardigan over cardigan, a large canvas bag on her lap. CRITICAL: reads as POOR BUT CLEAN AND DIGNIFIED — pressed, cared-for, mended not soiled. Poor is not dirty. She bids a hundred million and the joke only lands if she has dignity.~~
5. **`char_cleaner`** — a working man, forties or fifties, building maintenance worker. TWO WARDROBE STATES in the one sheet: work clothes with a trowel in panels 1 and 3, a brand-new suit that does not quite fit him in panels 2 and 4. Clean and neat in both, never grimy.

## REVISION (CTO, later same session) — `char_wheelchair` overridden, "poor→dignified" is WRONG

The CEO reversed the wheelchair-woman direction entirely. Use this spec, not §4 above:

**`char_wheelchair`, current spec:** a very old woman in a self-propelled wheelchair (hand rims, keep it self-propelled) who looks EFFORTLESSLY COOL. Not poor, not pitiable, not sweet — cool. She is the single most self-possessed person in the film, and she is the one who bids a hundred million. The room misreads her as unimportant because she is old, in a wheelchair, and displays no wealth — and she has never once bothered to correct them. That is the character.

- Sharp, deliberate personal style: excellent tailoring in a restrained palette, a beautifully cut coat, dark glasses if it suits her, good silver jewellery, hair done exactly the way she wants it.
- Absolutely NO frailty signalling: no shawls, no headscarf, no bundles, no layered worn knitwear, no big canvas bag.
- Expression calm and completely unbothered — she has already decided something and is not going to discuss it.
- Genuinely old — deep lines, real age, a real human face. The point is not that she looks young; it's that she looks like she doesn't care what anyone in the room thinks.
- **Comes with a dog, every panel, all four views** — a large WHITE GOLDEN RETRIEVER (English cream), immaculately groomed, walking calmly beside the wheelchair, relaxed and well trained, never excited, never pulling. The dog belongs on her plate, not a separate element — she is never seen without it.

## SECOND TASK (same revision message) — restyle `project_valder_char_mother`, different project

Not part of the Absence set — this is an existing character in **The Valder Collection No.7** (a different Higgsfield project on this same account). The CEO wants the same poor→dignified overcorrection fixed there too.

- Current plate: faded pink dress with visible mending — reads as poverty. Wrong, per the same logic as above.
- New: a striking, well-dressed woman in her forties or fifties with real personal style. Cool, not poor.
- **Re-point the new image onto the SAME element UUID** so no prompt file needs editing — same re-point trick that worked on Valder before (see `higgsfield-image-gen.js` / Valder plate-fix scripts in `scripts/browser/` for the mechanic, if not already known).
- Same "as human as possible" rules apply: real skin, real faces, distinctiveness from wardrobe/silhouette not odd faces.
- This is a GPT Image Gen 2 job (Character), same as the Absence set.

## Rules carried over unchanged

Same money rules (paid balance vs free-allowance check per model — GPT Image Gen 2 is normally paid, ~0.2-2 credits/image per org reference data; confirm actual price on the button before each click), same reporting rules (PLATES.md entry per plate: element name, asset id, model, camera settings if any, exact prompt, one honest paragraph on what actually rendered). CEO approves images, never regenerate on taste — only on hard failure (error, blank/corrupt, content refusal), max 2 attempts.

## Status

Not started as of this note. Locations (Step 1 + Step 2, 5 plates) come first.
