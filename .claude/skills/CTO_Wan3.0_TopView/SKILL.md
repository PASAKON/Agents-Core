---
name: CTO_Wan3.0_TopView
description: >-
  Generating with Wan 3.0 on TopView (topview.ai): how references are written (positional, no Element
  library), the 3,500-character Direction box, prices and plans, several shots in one generation, the
  TopView Wan3 Challenge rules, and the checklist for turning a MiniMax H3 previz prompt into a Wan3 prompt.
  Trigger on /CTO_Wan3.0_TopView and whenever a task says Wan3, Wan 3.0, TopView, "Topview Wan3
  Challenge", "ส่งประกวด TopView", "แปลง prompt ไป Wan3", "@Image 1", or prepares final footage for the
  ILAG trailer. Do NOT fire for the H3 previz itself (CTO_MiniMax_H3), Seedance/Higgsfield
  (CTO_Seedance2.5_Higgsfield) or Google Flow (CTO_Flow_Omni1.1_Ops); prompt-file layout lives in
  CTO_Film_PromptFormat.
created_by: agent
author: {role: cto, date: "2026-09-25"}
audience: [cto, browser_operator]
---

# Wan 3.0 · TopView

**Status: no Wan3 generation has been measured by this org yet.** Every fact below is TopView's own page,
pricing table, FAQ or contest text (read 2026-09-23/25). The first real generation must record what it
actually did here, in Field notes, before anything is built on these claims.

Sources, with URLs and verbatim quotes: `docs/promo/TOPVIEW-WAN3-REFERENCES.md` (model, references, prices)
and `docs/promo/TOPVIEW-WAN3-RULES.md` (the challenge). This skill is the working summary; those files are
the evidence.

## 1 · Rules

1. **HARD: every paid generation needs the CEO's OK with the exact credits and $ first.**
   **Why hard:** money. On Pro, 720p costs 0.5 credit per second (80 credits = 160 s).
2. **HARD (challenge entries): the primary video must be generated with Wan3 on TopView, in our TopView
   project.** Other tools may make reference images (our ChatGPT plates are allowed if we hold the rights;
   keep each chat link as the licence record) and edit the cut, but a still or a clip from another model
   does not count as Wan3 footage.
   **Why hard:** scope; an entry that breaks it is disqualified, and "the organizer may verify the creation
   process, Topview project, and material licenses".

## 2 · References: positional, not named

- There is **no saved Element library** for Wan3. Each generation takes its own uploads: up to 10 images,
  5 videos, 5 audio (20 files), per TopView's page; the live caps are unverified.
- A reference is cited by its **upload order**: `@Image 1` (inserted by the UI when you type `@`) or
  `<<<Image1>>>` / `<<<Audio1>>>` (TopView's own example prompts). Which token the live box accepts is
  unverified: check it on the first generation.
- Name the subject in prose right after the tag and give the reference its job, as TopView's FAQ asks:
  "Name each uploaded reference and explain its job, then list the details that must remain consistent."

## 3 · The Direction box

- **3,500 characters maximum** (the counter reads "Direction 513/3500").
- Several shots in one generation are allowed ("shot-level direction"), written as prose, as `[0-4s] ...`
  brackets, or as `Timeline: 0.0-3.0s | ...`.
- Up to 30 s per generation (2-30 s), 480p / 720p / 1080p, aspect 16:9, 9:16, 1:1, 4:3, 3:4.
- Whether Wan3 makes its own sound is unconfirmed.

## 4 · Prices and plans (topview.ai/pricing, 2026-09-25)

| | per second | notes |
|---|---|---|
| 1080p | 1 credit | |
| 720p | 0.5 credit | 0.4 with the 20 % off on Business, Ultra or Team annual |
| 480p | 0.3 credit | may not be selectable for Wan3 |

Pro $29/month = 80 credits (annual $16/month, 960 credits upfront) · Business $75 ($44 annual, 3,000/yr) ·
Ultra $150 ($50 annual, 500/month) and Team list **"Wan 3.0 720P 365 Days Unlimited"** · top-up packs
250 / 600 / 1000 credits, valid 24 months.

## 5 · From an H3 previz prompt to a Wan3 prompt (the ILAG pipeline)

The shot is crafted on H3 (`CTO_MiniMax_H3`); the Wan3 prompt is derived from the H3 file that passed. The
two engines are different, so check each step on the first generation and write down what held.

1. **List the uploads in order** from the H3 file's `@handles` (first mention first), and upload the same
   single-panel pictures (Drive `Element/`, `ref-*.png` and the location plates). 10 images at most.
2. **Replace each `@Handle` with its position** (`@Image 1`...), keeping the fixed name after it:
   `@Image 2 THE YOUNG ONE, ...`.
3. **Fit 3,500 characters.** Our H3 paste blocks run about 4,600. Cut in this order: the house negatives
   wall first, then shorten the reference descriptions (the picture carries the look), then merge the
   STATE, PARTICLES and grade lines into one sentence each. Never cut the beats, the dialogue or the camera
   line.
4. **Remove the H3 studio markers** (`overall_soundscape:` and `non_diegetic_music: none.`) and state the
   sound in plain words ("Sound: only the characters' own voices and breathing; no music, no ambience").
5. **Set** 720p (the challenge floor), 16:9, and the shot's seconds; one generation per H3 shot, unless
   several shots are deliberately joined with shot-level direction.
6. **Before the first paid run, one short test** (a few seconds) to learn which reference token works
   and whether dialogue is spoken, then write it in Field notes.

## 6 · The TopView Wan3 Challenge (summary; full text in TOPVIEW-WAN3-RULES.md)

Submission closes **28 Sep 06:59 Thai time** (Terms 6.1.2 says 22 Sep; two sources say 27 Sep UTC) · at
least 30 s, 720p or better, any aspect · made after 4 Sep 2026 · the official challenge watermark on the
video · a public post with `#TopviewAI #Wan3 #TopviewWan3Challenge` and TopView's account tagged · the form
wants title, 16:9 cover, creator name, profile image, post link, TopView project link, video file up to
500 MB · judging: creativity 30, use of Wan3 25, story and emotion 20, shareability 15, audio and visual
quality 10 (CEO: these weights are the film's design brief) · $15,000 over 16 prizes.
The other TopView call (AI Film Screening, SSFF & ASIA, closes 23 Oct): `docs/promo/TOPVIEW-FILMFEST-RULES.md`.

## Field notes
