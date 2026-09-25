# Brief: split the Seedance film skills into CTO_Seedance2.5_Higgsfield (CEO-approved 2026-09-25)

## Step 0 · sync first
Your worktree may be cut from a stale local main. Run `git fetch origin && git merge --ff-only origin/main`
(or `git merge origin/main` if ff fails), then confirm `.claude/skills/CTO_Film_Production/SKILL.md` and
`docs/ops/skill-film-inventory-2026-09-25.md` exist. If either is missing, stop and report.

## Why
CEO: film skills must be named by engine (like `CTO_Flow_Omni1.1_Continuity`), shared rules live once, and
"ห้ามเขียนวนซ้ำกัน ... worker อ่าน A ได้เนื้อหา 100% พอไปอ่าน B กลับได้แค่ 10% เพราะ 90% ที่เหลือเหมือน A หมดเลย แบบนี้
การเขียน Skill ผิดตั้งแต่แรก". He approved the structure with "OK".

## Already done (do not redo, do not copy from them)
The CTO wrote the shared and new-engine skills (commit b2ee0d4d):
- `.claude/skills/CTO_Film_Production/SKILL.md`: the engine-agnostic film discipline (CAST.md, plates,
  re-shoot on change, tolerance, prose vs reference, prohibitions, countable motion + judge by eye,
  continuity check, director decides, A/B entry, workers/money).
- `.claude/skills/CTO_Film_PromptFormat/SKILL.md`: the prompt-file format (two zones, block order, one name,
  each reference once, manner tag, negatives, pre-fire grep, build.py).
- `CTO_MiniMax_H3`, `CTO_Wan3.0_TopView`.
Read all four first. Anything they already say must NOT appear again in your output: point to them.

## Evidence
`docs/ops/skill-film-inventory-2026-09-25.md`: every section of every old film skill with the engine it was
measured on and every overlap/conflict (section 2 items 3, 4, 9, 10, 11, 15, 22-26, 29-32, 34, 38, 40, 41 are
yours).

## Job
1. Create `.claude/skills/CTO_Seedance2.5_Higgsfield/SKILL.md` (frontmatter like
   `CTO_Flow_Omni1.1_Continuity`: name, description with triggers and a "Do NOT fire for" line naming the
   other engine skills, `created_by: agent`, `author: {role: developer, date: ...}`, `audience`).
   It holds ONLY what was measured on Seedance / Higgsfield, taken from:
   - `higgsfield-unlimited-gen/SKILL.md` (the platform: buttons, money, Unlimited, slot, project URLs,
     rights banner, review loop, workers, previz upload, field notes);
   - `ai-film-production/SKILL.md` sections that are Seedance-measured and NOT in CTO_Film_Production:
     §1 one face per plate (the scanner facts), §2 never let the slot sit idle, §7b's measurements if you
     keep any beyond what CTO_Film_PromptFormat rule 5 says, §10 names and the copyright gate, §11b's
     shot-motion.sh numbers, §14 model tiers, §14b cost per second;
   - the Seedance-only parts of `docs/prompts/absence/PROMPT-STYLE.md` and `AUTHORING-RULES.md` that are
     not already in CTO_Film_PromptFormat (e.g. the video chip bound once, previz ≥ 1280x720, "no music" in
     the audio line, no sound at start or end).
   - Move `ai-film-production/AB-LEDGER.md` to `CTO_Seedance2.5_Higgsfield/AB-LEDGER.md` with `git mv`
     (history kept) and dedupe it against §14 (inventory item 3) and its own repeats (item 40).
2. **Every idea once.** Remove the internal repeats the inventory lists for HF (item 38: the price-reading
   table x3, wave cap x2, 90 s sleep cap x3, mobile viewport x3, video-ref upload x3, poll cadence, "Images
   always cost credits" vs the free-plates notes) and for AB-LEDGER (item 40). Where two copies conflict,
   keep the later measured one, put the dropped claim under a `[SUPERSEDED]` line with its evidence, and
   list every such decision in your report.
3. **Resolve the conflicts on your side** (inventory item 26 reference caps for Seedance: one table with
   each number and its date/evidence; item 34 pricing: keep the dated measurements, mark the others;
   item 25 review loop vs operator description: CTO_Film_Production §8 already rules "the CTO looks at
   frames"; keep only the Higgsfield-specific mechanics).
4. **Old names become redirect stubs, not deleted:** `higgsfield-unlimited-gen/SKILL.md` and
   `ai-film-production/SKILL.md` each shrink to frontmatter (same `name`, description starting "MOVED:")
   plus 5-10 lines saying where each part now lives. 102 repo files and 8 memory files cite
   `higgsfield-unlimited-gen`; the stub keeps those links alive. Do not edit those 102 files.
5. `docs/prompts/absence/PROMPT-STYLE.md` and `AUTHORING-RULES.md`: add a 3-line header at the top pointing
   to CTO_Film_PromptFormat (general) and CTO_Seedance2.5_Higgsfield (Seedance-only); do not delete their
   history.
6. Scripts and tests that read these skills BY PATH or assert their names (inventory §3: `scripts/prompt-lint.py`,
   `scripts/skill-lint.py` + its tests, `config/decisions/browser.*.yaml`, `tools/jev_lab.py`,
   `tests/test_decide_browser_sites.py`, `scripts/higgsfield/gen_loop.py`, `scripts/browser/higgsfield-*.js`):
   grep each; if it loads a section by path or heading, point it to the new file; if it only names the skill
   in a comment or a route id, leave it (the stub exists). Run the full `pytest` and both
   `scripts/skill-lint.py check` and `scripts/skill-doctrine-lint.py check`; report the results with counts.

## Rules
- Move, never copy. After the job, `grep` your new file for three distinctive sentences from
  CTO_Film_Production and CTO_Film_PromptFormat: zero hits expected.
- Do not change what a rule means. Shorten wording only where a copy is being removed.
- Keep every field note (move it with its section); keep the "Why hard:" tiers (ADR 0022 §7).
- Touch only: `.claude/skills/CTO_Seedance2.5_Higgsfield/`, `.claude/skills/higgsfield-unlimited-gen/`,
  `.claude/skills/ai-film-production/`, `docs/prompts/absence/PROMPT-STYLE.md`,
  `docs/prompts/absence/AUTHORING-RULES.md`, and the scripts/tests you must repoint (list them).
- A parallel worker is doing the same for the Flow skills (`google-flow-ops`, `CTO_Flow_*`,
  `thai-moral-drama`, LakornCover): never touch those files.

## Report (REPORT.md)
A table: every section of the old files → where it went (new file + heading, or "removed: duplicate of X",
or "[SUPERSEDED] by Y"). Line counts before/after. Every conflict decision. Test and lint output. Commits.
