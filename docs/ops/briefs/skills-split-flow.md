# Brief: de-duplicate the Flow film skills; rename google-flow-ops and thai-moral-drama (CEO-approved 2026-09-25)

## Step 0 · sync first
Your worktree may be cut from a stale local main. Run `git fetch origin && git merge --ff-only origin/main`
(or `git merge origin/main` if ff fails), then confirm `.claude/skills/CTO_Film_Production/SKILL.md` and
`docs/ops/skill-film-inventory-2026-09-25.md` exist. If either is missing, stop and report.

## Why
CEO: film skills must be named by engine (like `CTO_Flow_Omni1.1_Continuity`), shared rules live once, and
"ห้ามเขียนวนซ้ำกัน ... worker อ่าน A ได้เนื้อหา 100% พอไปอ่าน B กลับได้แค่ 10% เพราะ 90% ที่เหลือเหมือน A หมดเลย แบบนี้
การเขียน Skill ผิดตั้งแต่แรก". He approved the structure with "OK".

## Already done (do not redo, do not copy from them)
The CTO wrote the shared and new-engine skills (commit b2ee0d4d): `CTO_Film_Production` (engine-agnostic
film discipline: CAST.md / one written look quoted into every shot, plates, re-shoot on change, tolerance,
prose vs reference, prohibitions, judge by eye with mechanical checks to FIND audio/text defects,
transcribe dialogue, continuity check, director decides, A/B, commit ids, one variable per test),
`CTO_Film_PromptFormat`, `CTO_MiniMax_H3`, `CTO_Wan3.0_TopView`. Read them first. Anything they already say
must NOT appear again in your output: point to them.

## Evidence
`docs/ops/skill-film-inventory-2026-09-25.md`: every section, its engine and every overlap/conflict. Yours:
section 2 items 1, 2, 5, 6, 7, 8, 12, 13, 14, 16-22, 26 (the Flow numbers), 27, 28, 33 if it touches you, 39, 42.

## Target
- `google-flow-ops` → **`CTO_Flow_Omni1.1_Ops`** (new directory with the content; `git mv` is fine for the
  body, then recreate a stub at the old path). The Flow platform: selectors, chips, models, costs, downloads,
  voices, Thai text, runner.
- `CTO_Flow_Omni1.1_Continuity` and `CTO_Flow_Omni1.1_FilmQC` stay; each keeps only what the other two do not.
  The mechanical audit (tools table, "OCR said 14, it was 3" once, never diagnose audio unread) lives in
  FilmQC only; what Flow deletes / night on a day plate / wardrobe / REF_1 live in Continuity only; Ops points
  to them. The shared "Model scope, read this first" block (item 12) is written once (in Ops) and pointed to.
- `thai-moral-drama` → **`CTO_Story_ThaiMoralDrama`**: story and the Structure gate only. Its "Production
  constraints" and prop-money text that restate Flow rules (items 7, 8) are removed and pointed to Ops or
  Continuity. Resolve the two conflicts (item 7 prop money: GFO measured words failing on 6 clips → an
  Element is the fix; item 8 Thai text: GFO's measurement wins) and list them.
- `CTO_ChatGPT-Image_LakornCover`: remove its duplicate of the cover layout (item 13) on one side only and
  its restatement of the uniform rule (item 2); keep the name.
- Engine-agnostic material that is already in CTO_Film_Production (item 5 CAST/asset sheet principle,
  item 6 prose over reference, item 15 commit the id, item 18 transcribe, item 19 bisect) is removed from the
  Flow skills; keep only the Flow-specific mechanics (e.g. the ASSET SHEET format, Flow's download id capture).
- Conflicts inside Ops (item 39: chip cap stated five ways, which model to select, voice material over 9
  headings, download failure x4, free stills x4; item 28 test-fire resolution): one statement each, later
  measurement wins, the dropped one under `[SUPERSEDED]` with its evidence; list every decision.

## Old names stay alive as stubs
`google-flow-ops/SKILL.md` and `thai-moral-drama/SKILL.md` shrink to frontmatter (same `name`, description
starting "MOVED:") plus lines saying where each part now lives. 70 repo files cite `google-flow-ops`;
**`tests/test_decide.py` asserts `"google-flow-ops" in ids`** for a skill.route decision: either keep that
route id pointing at the stub or update the decision config + test to the new name, and say which.
`thai-moral-drama` is symlinked on the Mac through `claude-home/skills.txt`: add a row for
`CTO_Story_ThaiMoralDrama` beside the old one. `tools/shotsheet_lint.py`, `tools/continuity_sheet.py`,
`tools/flow_shoot.py`: repoint only if they read a skill file by path.

## Rules
- Move, never copy. After the job, grep the Flow skills for three distinctive sentences of
  CTO_Film_Production: zero hits expected.
- Do not change what a rule means; keep every field note with its section; keep the "Why hard:" tiers.
- Touch only: `.claude/skills/google-flow-ops/`, `.claude/skills/CTO_Flow_Omni1.1_Ops/`,
  `.claude/skills/CTO_Flow_Omni1.1_Continuity/`, `.claude/skills/CTO_Flow_Omni1.1_FilmQC/`,
  `.claude/skills/thai-moral-drama/`, `.claude/skills/CTO_Story_ThaiMoralDrama/`,
  `.claude/skills/CTO_ChatGPT-Image_LakornCover/`, `claude-home/skills.txt`, and the configs/tests/tools you
  must repoint (list them).
- A parallel worker is doing the Seedance skills (`higgsfield-unlimited-gen`, `ai-film-production`,
  `CTO_Seedance2.5_Higgsfield`, `docs/prompts/absence/*`): never touch those files.
- Run the full `pytest`, `scripts/skill-lint.py check`, `scripts/skill-doctrine-lint.py check`; report counts.

## Report (REPORT.md)
A table: every section of the old files → where it went (new file + heading, "removed: duplicate of X", or
"[SUPERSEDED] by Y"). Line counts before/after per file. Every conflict decision. Test and lint output.
