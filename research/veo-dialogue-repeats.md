# Why a Veo 3.1 character says a line twice, and what actually fixes it (2026-09-23)

refresh_after: 2027-03-23

**Question:** «จุดจบของเจ้าหนี้นอกระบบ» plays back with characters appearing to
say things twice. Our prompts restated the whole 25-word speaker description on
every line — 111 of 173 shots, nine of them three times. Is that the cause?

**Answer: no, and repeating the speaker description is the community's
recommendation, not a bug.** The reported cause of a repeated line is **where
the dialogue sits in the prompt**, not how often the speaker is named.

## What the sources say

Prompt Architects, *Dialogue Prompting in Veo 3.1*, asked directly what causes a
line to be spoken twice:

> "Almost always **position or budget**. **Move the quoted line into the first
> third of the prompt.** Long prompts near the 1,024-token limit risk dialogue
> being dropped or repeated."

The same guide says the opposite of the fix we tried:

> "Attach every line to a visual description, not to a name." Speaker
> description is **stated with each line, not once at the top** — it stops the
> model losing track of who is speaking.

Two more techniques from the same source:

- **Timestamps carve the 8 seconds into beats**, e.g. `[00:02-00:04] Reverse shot
  of her face` — each line gets its own window instead of competing for the clip.
- **Turn-taking verbs** — "replies", "adds", "turns to him" — stop the model
  speaking both lines or repeating one.
- Two lines plus two reaction beats in 8 seconds is already tight.

Separately, ApiPass on *unwanted* dialogue: **Veo handles negation badly** — "no
talking" can itself trigger speech — and JSON-structured prompts isolate audio
from picture. Matches what this production learned the hard way about
prohibitions losing to context.

## Measured against our own prompts, same day

| | ours | guidance |
|---|---|---|
| first quoted line's position in the prompt | **74%** | first third (<33%) |
| shots with dialogue past the halfway mark | **172 / 173** | — |
| prompt length | 292 words ≈ 409 tokens (max 651) | under the 1,024 limit |

So **budget is not our problem and position is** — in essentially every shot.
`tools/build_shotsheet.py` emits REF → SCENE (a 60-word location paragraph) →
SPEAK → RULE → CAM → STYLE, which puts the quoted lines near the end by
construction.

## What to do with this

1. **Revert the speaker-hoisting change** made earlier on 2026-09-23 — it removed
   per-line attribution the guidance says to keep, and a same-day A/B on shot 139
   showed no improvement (old 2 speech segments / 4.0s, new 3 / 4.2s).
2. **Move the dialogue block into the first third**, ahead of the location
   paragraph.
3. Add turn-taking verbs for two-speaker shots; consider `[00:0X-00:0Y]`
   timestamps for three-line shots.
4. Re-test on the same five shots, one runner at a time.

## Sources

- https://prompt-architects.com/blog/101-veo-dialogue-prompts
- https://apipass.dev/blogs/how-to-solve-veo-3-keep-generating-unwanted-dialogue
- https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1
- https://deepmind.google/models/veo/prompt-guide/
