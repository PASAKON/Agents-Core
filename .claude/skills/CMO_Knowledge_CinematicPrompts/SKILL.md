---
name: CMO_Knowledge_CinematicPrompts
kind: knowledge
owner: CMO
verified: "2026-10-29"
refresh_after: "2026-11-29"
created_by: agent
author: {role: developer, date: "2026-10-29"}
audience: [cmo, cto, script_writer, prompt_engineer, browser_operator]
description: >-
  KNOWLEDGE — Pick ready cinematic video prompts: job -> style -> model -> prompt across 66 verified entries with free weekly source updates. Trigger on /CMO_Knowledge_CinematicPrompts, "cinematic prompt", "B-roll prompt", "prompt library", "หา prompt", "prompt หนังสั้น", "ILAG prompt". Adapt via CMO_Standard_Film_PromptFormat.
---

# Cinematic Prompt Library

Verified 2026-10-29 at internal prompts library (`references/prompts/`) and external source repositories (`references/sources.json`).

## 1 · Library Contents (66 Entries)

The library holds 66 ready cinematic prompt templates across 3 categories, 12 subcategories, and 4 engine targets:

- **Categories (66 total)**:
  - `broll` (24 entries): ambient cutaways, product visuals, nature, city rhythms, culinary close-ups, and market atmosphere.
  - `movie` (22 entries): dramatic sequences across thriller, drama, comedy, light horror, and romance.
  - `shortfilm` (20 entries): Thai everyday realism (10) and ILAG moral drama / lakorn confrontations (10).
- **Subcategories**:
  - `broll`: product (5), nature (5), city (5), food (5), market_life (4)
  - `movie`: thriller (5), drama (5), comedy (4), horror_light (4), romance (4)
  - `shortfilm`: thai_everyday (10), ilag_lakorn (10)
- **Model Support**: `seedance-2.5` (24), `wan-3.0` (21), `flow-omni-1.1` (15), and `any` (6). Model `any` matches every engine query.

## 2 · Picker Steps: Job -> Style -> Model -> Prompt

1. **Step 1: Inspect Library Breakdown (Job)**
   ```bash
   .venv/bin/python .claude/skills/CMO_Knowledge_CinematicPrompts/scripts/pick.py list
   ```
2. **Step 2: Find Matching Prompts (Style & Model)**
   ```bash
   .venv/bin/python .claude/skills/CMO_Knowledge_CinematicPrompts/scripts/pick.py find --job broll --style product --model seedance-2.5 --aspect 9:16
   ```
   Filters available: `--job <broll|movie|shortfilm>`, `--style <subcategory>`, `--model <seedance-2.5|wan-3.0|flow-omni-1.1|any>`, `--aspect <9:16|16:9|1:1>`, `--max-seconds <N>`, `--text <keyword>`.
3. **Step 3: Retrieve Ready Prompt Paste Block**
   ```bash
   .venv/bin/python .claude/skills/CMO_Knowledge_CinematicPrompts/scripts/pick.py show broll-product-01
   ```
4. **Step 4: Lint All Entries Before Production**
   ```bash
   .venv/bin/python .claude/skills/CMO_Knowledge_CinematicPrompts/scripts/pick.py lint
   ```

## 3 · How to Adapt an Entry

1. **House Format (`CMO_Standard_Film_PromptFormat`)**:
   - Every prompt begins with a first-line tech header: `<duration>s · <resolution> · <aspect> · ONE CONTINUOUS TAKE, NO CUTS, NO ZOOM`.
   - Structure follows two zones: notes above vs paste block below. State character facing, eyeline, and motion direction explicitly in camera terms.
   - Use dynamic physical verbs (snap, slide, pour, heave), front-load key subjects, and keep critical negatives short and targeted.
2. **Per-Model Rules**:
   - `CMO_Knowledge_Seedance2.5_Higgsfield`: Maximum 3-4 timed beats `[0s] [3s] [6s]`, set duration via Radix slider, never click Rerun, check struck-through price.
   - `CMO_Knowledge_Wan3.0_TopView`: Emphasize lighting direction, volumetric dust/water caustics, and physical surface textures for temporal stability.
   - `CMO_Knowledge_Flow_Omni1.1`: Use 720p base resolution, concise dialogue manner tags (≤5 words before `:"..."`), and audit burned text via `CMO_Gate_Flow_Omni1.1_FilmQC`.

## 4 · Quality, Safety, and Licensing Rules

1. **HARD — Never include blush, blushing, flushed, red face, red cheeks, red ears, rosy cheeks, หน้าแดง, or หูแดง in any prompt.**
   **Why hard:** safety or scope — `CMO_Gate_Flow_Omni1.1_FilmQC` and platform safety filters trigger false-positive NSFW / adult content violations on facial redness terms, aborting generation waves.
2. **HARD — Every depicted character must be an adult aged 18+. Never use child, minor, teen, schoolgirl, or typography characters « » — in prompts.**
   **Why hard:** safety or scope — legal compliance and child safety policies across all AI video generation platforms.
3. **Licensing Rule**:
   - Sources marked `ideas_only` or `templates_only` in `references/sources.json` are NEVER pasted verbatim.
   - Every prompt entry must be written in our own original words following MoonieX house standards.
   - The inspiration source and license must be logged in `references/SOURCES.md` and the entry's metadata.

## 5 · Weekly Source Updates

Run the free update check weekly ($0, stdlib urllib, read-only):
```bash
.venv/bin/python .claude/skills/CMO_Knowledge_CinematicPrompts/scripts/update_sources.py
```
Options:
- `--state <path>`: override default state file (`/opt/MoonieXHQ/Work/cineprompt/updates/state.json`).
- `--dry-run`: display planned source endpoints without network calls.
- `--with-data`: fetch `data_url` payloads when applicable.

**Reviewing Update Output**:
- The script generates `/opt/MoonieXHQ/Work/cineprompt/updates/review-<YYYY-MM-DD>.md`.
- Inspect each changed source: note `license` and `copy_ok`.
- For `ideas_only` or `templates_only` entries, extract concepts or staging ideas only; rewrite completely in original words and run `pick.py lint`.

## Field notes

