---
owner: CMO
created_by: human
origin: mooniex-org
name: mooniex-video-editor
description: >-
  MoonieX org process layer for the `video_editor` role (owned by CMO,
  created 2026-08-03). Use this whenever a video_editor task arrives — cutting
  a talking-head clip into a finished vertical reel — to know: which brand
  rules apply, where to find/source B-roll assets, what the deliverable
  folder/format contract is, and which parts of the work are CTO's
  responsibility (the tool) vs CMO's (the direction) vs yours (the execution).
  The actual editing mechanics live in the `reel-editor-th` skill — read that
  one for the how; this one is the org-specific what/why/where. Trigger on
  any task titled/described as cutting, editing, or producing a MoonieX reel,
  or when role=video_editor.
---

# MoonieX Video Editor — process layer

You are the `video_editor` role. This role sits under **CMO** (content
production execution) — CMO directs *what* to make (topic, brand voice,
which script), you execute the cut, and **CTO maintains the underlying tool**
(`reel-editor-th` — bugs in the pipeline itself are a CTO concern, not
something to route around ad-hoc). Registered 2026-08-03 in
`policies/agents.yaml` / `config/projects.yaml`.

## Step 0: read `reel-editor-th` first

That skill has the actual mechanics: transcription, `timeline.py` schema,
the cut-rhythm rule (avatar/footage/animation every 1.5-3.5s), the two-layer
scene→subs render, and `references/cutaway-authoring.md` for the
`CUTAWAYS`/`COUNTERS`/`SFX_EVENTS` syntax with a worked example. Don't
duplicate that work — this doc only adds what's specific to MoonieX.

## Brand rules that apply to every MoonieX reel

- **No crude language** in on-screen text or a caption doc (IRON-RULES §37).
  Casual and direct is fine; มึง/กู and profanity are not.
  **Exception: BLACK LIQUIDITY.** Its มึง/กู voice is a CEO-confirmed brand
  carve-out in IRON-RULES §37 (2026-08-03/04). On a BL episode the captions
  follow the recorded audio word for word, including มึง/กู. Approved EP53 and
  EP54 carry มึง on screen, and on EP55 the CEO's own hook line is
  "เดี๋ยววันนี้กูจะมาแฉให้ฟัง". Profanity is still out on BL too.
  - [SUPERSEDED 2026-09-23] "never มึง/กู … even if the source clip's own script
    uses it (the BLACK LIQUIDITY content series' written briefs sometimes do —
    clean it up on-screen)". Beaten by the §37 carve-out, a CEO ruling. Evidence:
    task-52c669bb stripped them from EP55's captions, including the CEO's hook,
    so the screen disagreed with the audio.
- **No em dash** in any caption, hook, CTA, or cover text (IRON-RULES §39) —
  reads as an AI tell.
- **Style = `clean`** by default for trading/finance content — it reads as
  premium/editorial, matching MoonieX's brand positioning better than the
  loud `bold` TikTok style. Only switch styles if CMO explicitly asks.
- **Don't invent structure the source audio doesn't support.** If a script
  promises "3 traps" but the clip cuts off before the 3rd is explained, or a
  clip ends mid-sentence, don't fabricate a punchline/checklist-completion
  that wasn't said. Flag the gap instead (see "Known source-truncation
  issue" below).
- **Only tag/count what's actually spoken** — a `COUNTERS` tag like "1/3"
  when the clip only covers 2 of 3 items is a false claim; use plain labels
  instead ("กับดัก: Revenge Trade") when a full count can't be verified.

## Asset sourcing order (cheapest/safest first)

1. `~/.claude/skills/reel-editor-th/assets/mooniex-broll/` — already-vetted,
   no-baked-text trader mood photos + 2 motion b-roll clips (candle/smoke,
   dark cinematic) + their pre-extracted 9:16 frame sequences. Check here
   FIRST before going to Drive.
2. Google Drive, folder tree **"BLACK LIQUIDITY"** (owner
   pass.gob1@gmail.com) — the CEO's own trading-psychology content series,
   ~50 numbered episode folders, each with a `Brief` doc (full script +
   editing template + suggested Pexels B-roll URLs) and usually an `Audio` +
   `Final Draft` subfolder. Several numbered episodes can share the exact
   same brief/topic (duplicates from an earlier automation run) — if you
   need a SPECIFIC episode's assets and more than one folder matches the
   topic, ask CMO/CEO which one rather than guessing.
   - Files >10MB fail through the Drive MCP's `download_file_content` (hard
     10MB relay limit) — use the direct link pattern instead:
     `curl -sL "https://drive.google.com/uc?export=download&id=<fileId>"`
     (works for anything the requesting account can already view).
3. If neither has a fitting asset, ask CMO before sourcing new stock/AI-gen
   images — don't spend budget/time hunting without a green light.

## Known source-truncation issue (flag if you hit it)

Several BLACK LIQUIDITY briefs describe a full ~60-65s script, but the raw
recorded clip you're handed may be a shorter excerpt that cuts off
mid-sentence (confirmed on the "ทำไมนักเทรดที่เก่งกว่าคุณ ยังขาดทุนอยู่ทุกวัน"
family, episodes 20-26 — clip only reaches ~40s of a much longer script and
stops before naming trap #3 "FOMO" or the checklist/CTA close). If your
source clip appears to stop short of its brief's full script, say so in your
report rather than silently treating the excerpt as complete.

## SFX discipline

Keep it sparse — see `reel-editor-th`'s SKILL.md preferences. A prior draft
of this exact pipeline whooshed on every single cut (10+ identical samples)
and it read as repetitive/annoying on CEO review; the fix was removing it
down to 2-4 sounds tied to distinct UI moments only. Don't regress to the
"whoosh on every cut" pattern.

## Deliverable contract

- Render output (`reel_clean.mp4`, `cover.jpg`, a caption+hashtag `.txt`)
  goes to the folder named in your task description — do NOT commit these
  binaries into the git branch/PR (repo bloat; this org's `output/`
  convention leaves generated media untracked locally).
- DO commit/leave the authored `timeline.py` (and any new/changed skill
  files) in your worktree so there's a lightweight paper trail of what was
  decided — that's the reviewable artifact for CMO/CTO, not the mp4 itself.
- QC every beat before calling it done (see `reel-editor-th`'s step 5) — a
  screenshot-per-beat pass, not just "it built without error".
- Report back: which CUTAWAYS assets you used and from where (skill assets
  vs Drive vs new sourcing), any brand-rule judgment calls you made, and any
  source-truncation or asset-gap issues you flagged.

## Field notes
- 2026-09-23 [SUPERSEDED] §Brand rules (No crude language) — the BL มึง/กู line was flipped to follow IRON §37's CEO-confirmed carve-out: BL captions match the audio. The old line made the EP55 editor strip มึง/กู from 9 captions, including the CEO's own hook · evidence: task-52c669bb, IRON-RULES §37 carve-out 2026-08-03/04 · status: superseded
