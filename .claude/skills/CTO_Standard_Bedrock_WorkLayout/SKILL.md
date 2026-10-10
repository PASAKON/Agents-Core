---
name: CTO_Standard_Bedrock_WorkLayout
kind: standard
description: "STANDARD — How to lay out Minecraft Bedrock add-on work for workers: split, brief, runner, evidence, review. Trigger on /CTO_Standard_Bedrock_WorkLayout and on \"วางงาน Bedrock\", \"แบ่งงานให้ Worker\", \"brief Minecraft\", \"Deep Caller task\". Spawn mechanics stay in CXO_Protocol_DevSpawn."
owner: CTO
created_by: agent
author: {role: cto, date: "2026-10-05"}
audience: [cto]
---

# What a good Bedrock work layout is

The CEO, 2026-10-05: *"สำหรับโปรเจคแรกมันคือการเรียนรู้ลองผิดลองถูกปรับปรุงหลายอย่าง เขียน Skill วางงาน แบบไหนดีแบบไหนไม่ดี
... ถ้าถามแล้วต้องตรวจสอบได้ จะได้ออกแบบ Skill ได้ถูก"*. So every line here points at evidence you can open.

**Where the evidence lives:** repo `PASAKON/MoonieX-Bedrock`.

| Path | Holds |
|---|---|
| `docs/briefs/<task-id>.md` | the exact brief each worker received |
| `docs/reports/<task-id>/REPORT.md` | what the worker says it did |
| `docs/learning/trials.jsonl` | one row per worker run: what actually happened, and the CEO's verdict |
| `docs/learning/LESSONS.md` | the lesson table this skill is folded from (ids G1–G6, B1–B9) |

A lesson enters the spec below only with two runs that agree, or a CEO ruling. One run stays in Field notes.
Worker spawn mechanics (routing, reopen, merge, the launcher media gate) belong to `CXO_Protocol_DevSpawn`;
this skill only points at them.

## The spec (each item checkable)

1. **Brief shape** (LESSONS G3, 7 runs). Every brief has, in this order:
   - the job verb (CREATE / CHANGE / CONFIRM);
   - why, in the CEO's own words;
   - the shared contract (item 2);
   - what the task owns and must not touch;
   - the gates as exact commands. A worktree under `Agents/Core/worktrees/` runs pytest as
     `pytest tests -q -c /dev/null --rootdir=. --confcutdir=.`: plain `pytest tests` takes Agents/Core's
     pytest.ini and `tools` package and fails `test_sky_tour.py` falsely (4 runs: task-b3540bea,
     task-811d6a5f, task-ea4e3a1b, task-20215157);
   - the report: `docs/reports/<task-id>/REPORT.md`, first line `# REPORT <task-id>`, files changed, gates
     run, what it could not check, and a `## Skill learning` section.

   Check: open the brief and find each heading.
2. **One contract block, pasted into every parallel brief.** It holds the ids, bone names, events, the
   namespace, and which task owns each shared file (`en_US.lang`, each loot table). Two tasks never own the
   same file. Check: `check_collisions` is empty before `create_task`. (Evidence: LESSONS G2, 1 round of 5
   tasks with 0 merge conflicts. It is in the spec because the merge tooling needs disjoint `touches`
   anyway; the quality of the block itself is still a field note.)
3. **Runner by job type** (LESSONS G1, 10 runs). JSON, Script API and logic tasks go to codex on Contabo:
   content right at the first pass, 0 content reopens. Model and animation jobs that need a study round so
   far ran on agy on the Mac (field note G5, n=1).
   **A brief for agy on the Mac states its command limit** (LESSONS B8, 2 runs): it may run only
   `<Agents-Core>/.venv/bin/python -m pytest` and read-only commands; a bare python, node or the build
   aborts the run with no files. So the brief says to generate every file from inside a test, and that the
   CTO runs validate, build and the viewer after merge. Evidence: task-c602b857 did this and merged;
   task-bc504a72 was not told and died.
4. **Every pack file is traceable** (CEO ruling 2026-10-05, *"ทุกการกระทำ ต้อง ตรวจสอบย้อนหลังได้ทั้งหมด"*).
   The brief tells the worker to run `python3 tools/provenance.py record` in the same commit as the file.
   Paid calls are logged with `tools/provenance.py call`. `provenance/ENFORCE` is on, so `validate.py`
   R12 fails a file without a row. Check: `python3 tools/provenance.py check packs/abyss` prints nothing.
   Deleting or renaming a pack file: the tool has no `remove` or `move` command, so drop or move the row through
   its own `save()` (it writes the write-ahead `remove` / `move` event to `log.jsonl`), never by editing
   `assets.jsonl` by hand (rule, 2 runs: task-ea4e3a1b `move`, cto-369faf85 MoonieX-Bedrock e9d6275 `remove`).
5. **Every worker run is recorded** (CEO ruling 2026-10-05, this skill's own request). When the CTO creates
   or reopens a task, it exports the brief to `docs/briefs/`. When it reviews the run, it adds a
   `trials.jsonl` row, including for failed and cancelled runs. Check: every Bedrock task id in
   `list_tasks(project='mooniex-bedrock')` has a brief file and a trials row.
6. **Gates passing is not quality** (CEO ruling 2026-10-05: QA is the CEO, then Champ, then the partner).
   A lesson about how a model, animation or texture looks enters this skill only with the CEO's verdict in
   `trials.jsonl`.
7. **Other people's skills are on trial, not adopted** (CEO ruling 2026-10-05). Workers read
   `docs/reference/community-skills/` read-only, never run their scripts or the paid APIs they mention, and
   list in the report which files they read and which rules they applied. Only a rule that wins an A/B
   comparison the CEO judged gets written into this skill.
8. **Review on the merged branch, and expect the launcher to drop media.** See `CXO_Protocol_DevSpawn`
   §3d (LESSONS G6 and B1, 2 runs each).
9. **In-game tests go through a tool, not typed commands** (CEO ruling 2026-10-05, *"อยากให้ทำ Tools มาก่อน
   ไว้ใช้ สำหรับทดสอบ ระบบทั้งหมดที่คุณทำออกมา ดีกว่าการ มานึ่งพิม คำสั่งทีละ คำสั่ง"*). Every system a
   task adds (mob, biome, stage, item, loot) gets a button in the dev test pack in the same task. A brief
   that adds a system without a button fails the check below.
   **`/locate` always takes `minecraft:<name>`** (CEO ruling 2026-10-05): `/locate biome minecraft:warm_ocean`,
   never the bare name. Our own biomes (`mooniex_abyss:*`) gave a syntax error with `/locate` on 1.26.5203;
   reach them from the vanilla biome they replace (`minecraft:deep_lukewarm_ocean`,
   `minecraft:warm_ocean`, `minecraft:lukewarm_ocean`).
10. **Every reference link gets a ledger row** (CEO ruling 2026-10-07, *"บังคับใช้กับทุกลิ้งที่เป็น Reff และข้อมูล"*).
   A link, picture or data file handed over as a reference is recorded with its URL and our analysis in
   `docs/reference/links.jsonl` (`tools/refs.py add`) in the same turn. A brief that passes a link on quotes the rule.
   Full rule: `CTO_Rules_Bedrock_References`. Check: `python3 tools/refs.py check` prints `ok`.

## The check (60 seconds, before `delegate_task`)

- Brief has items 1, 2 and 4.
- `check_collisions` is empty.
- The runner matches item 3, or the brief says why not.
- The task id gets its `docs/briefs/` export in the same turn.

## Good vs bad (real)

- **Good:** `docs/briefs/task-2fa691ad.md`, the 10 animations. It has a contract block, an own-review round
  and exact gates. It merged at the first pass (`edab1a5`), and the review round caught a real bug (the eye
  clip restarted on every state change).
- **Bad:** the first grey-box batch, task-86d42c46 to task-086aaec1. It was created with a role and hosts the
  org would not spawn, and all four were cancelled before any work (`Agents-Core 0837735e`).

## Field notes

- 2026-10-05 [MISSING] §spec 7 — a worker's own review round (first pass, review, adjust, recorded in the report) found a real bug before submit · evidence: task-2fa691ad REPORT, LESSONS G4 · status: pending
- 2026-10-05 [MISSING] §spec 3 — a model job with a study doc (3 variants, preview PNGs, recorded adjust rounds) gave the CTO and the CEO something to judge by eye · evidence: task-c602b857, docs/design/04-model-study.md, LESSONS G5 · status: pending
- 2026-10-05 [WRONG] §spec 8 — the CTO first blamed the workers for missing PNGs and wrote a rule saying so; the launcher had unstaged them. Read the launcher before writing a rule about worker behaviour · evidence: Agents-Core 11c600b2 flipped by 97dad04f, LESSONS B2 · status: pending
- 2026-10-05 [MISSING] §spec 3 — a claude worker on Contabo waits on the folder-trust prompt, and the classifier refuses the remote keystroke that answers it; use codex there · evidence: task-b22580bf, LESSONS B3 · status: pending
- 2026-10-05 [MISSING] §spec 3 — the agy sandbox on the Mac cannot run node, `tools/build.py` or a browser; the brief must say the CTO runs those gates · evidence: task-c602b857, LESSONS B8; second run task-bc504a72 (bare python aborted the run, no files) agreed, promoted to §spec 3 · status: promoted
- 2026-10-05 [COSTLY] §spec 4 — a ledger task run in parallel with content tasks was 39 rows out of date at merge time; re-check the ledger after the last merge of a round · evidence: task-f285db14, LESSONS B7 · status: pending
- 2026-10-05 [MISSING] §spec 7 — downloaded community skills could not be pushed into the repo until the CEO typed an approval sentence; ask for it before downloading · evidence: MoonieX-Bedrock 4aaf0cf, LESSONS B9 · status: pending
- 2026-10-06 [MISSING] §The check — a lane brief that calls a paid API through `infisical_setup.py run <project> prod --as mac` cannot start on the Mac: `/etc/infisical` does not exist there, so both PixelLab lanes failed with "missing credentials: /etc/infisical/mac.env" and made code-only options (0 generations, $0). Before assigning a lane that needs a key, run `python3 tools/infisical_setup.py status` on the host that will run it, or route the key call through Contabo · evidence: task-b3540bea, task-811d6a5f (both workers hit it independently) · status: pending
- 2026-10-06 [MISSING] §The check — a Bedrock worktree under `Agents/Core/worktrees/` makes pytest take `Agents/Core/pytest.ini` as rootdir, and `Agents/Core/tools/__init__.py` shadows the Bedrock `tools` package, so `tests/test_sky_tour.py` fails with ModuleNotFoundError while a clean export passes. Three runs saw the failure (task-b3540bea, task-811d6a5f, task-ea4e3a1b; agy's fe5187f even edited the test to dodge it); the gate that works is `pytest tests -q -c /dev/null --rootdir=. --confcutdir=.`, so a brief should name that command · evidence: task-ea4e3a1b REPORT (295 passed), sky-tune 863b1f1; promoted 2026-10-06 to spec item 1 after the 4th run (task-20215157, 303 passed with the flags) · status: promoted
- 2026-10-06 [MISSING] §spec R12 provenance — `tools/provenance.py` has no `move` or `remove` command, but a renamed file leaves a stale row that fails R12; the worker hand-wrote a `move` event (an earlier one exists from task-d384cf8a with no tool behind it) · evidence: task-ea4e3a1b provenance/log.jsonl; second run cto-369faf85 2026-10-08 (4 ring textures removed through provenance.save, e9d6275) agreed → §spec 4 · status: promoted
- 2026-10-06 [MISSING] §spec 4 provenance — commit the generator before `provenance.py record`: the row's `source_sha` is the last commit touching the tool, so recording first stamps the old sha. A regenerated file needs `record` (its old row moves to history); a hand-edited file needs `edit` · evidence: task-20215157 (sun.png row source_sha 15041c5, the codex row in history) · status: pending
- 2026-10-06 [MISSING] §spec 1 — a brief that moves tools into the repo must list every helper file those tools call; the task-3ec4c8cc brief named the tools but not gridsheet.py, deploy_sky.ps1 or contentlog.ps1, and the worker found them by reading the scripts · evidence: task-3ec4c8cc REPORT, sky-tools 80d2b46 · status: pending
- 2026-10-06 [MISSING] §spec 1 gates — a "grep finds nothing" gate must name hits already there at the base, or scope to the owned folder, and use `grep -I` (pycache matches otherwise); tools/gen_sky_tex_options.py:24 matched before task-3ec4c8cc started · evidence: task-3ec4c8cc REPORT · status: pending
- 2026-10-06 [MISSING] §review — the CTO gate re-run on a branch merged onto its moving base can fail for reasons the branch does not own: node 81/2 on sky-tools+sky-tune, both failures (sunTint T00, haze tint) reproduce on origin/sky-tune alone; run the base alone before blaming the branch · evidence: task-3ec4c8cc trials row, origin/sky-tune 6fe8ab0 · status: pending
- 2026-10-07 [MISSING] §spec 2 — one Bedrock particle effect carries one texture, so a contract that gives one particle id to three sprites cannot be built; give one id per sprite (cloud_bank, cloud_bank_1, cloud_bank_2) · evidence: task-0df52b06 669d643 · status: pending
- 2026-10-07 [MISSING] §spec 1 — a brief that adds an fx category or a sprite must list the files that enumerate them (docs/design/sky/CONTRACT.md FX list, docs/testing/SKY-TESTS.md, the effect count in tests/test_sky_particles.py, style_lint's folder scan); otherwise tests break and the worker edits files outside its lane · evidence: task-0df52b06 2ec8cbd, fd18049 · status: pending
- 2026-10-07 [COSTLY] §spec 4 — rebasing a branch after `provenance.py record` leaves rows whose `source_sha` is no longer on the branch, and `check` still passes; re-record after every rebase · evidence: task-0df52b06 73ded21 · status: pending
- 2026-10-07 [MISSING] §spec 1 Brief shape — a brief that adds a `tools/skytune` module must list `tests/test_skytune_guard.py` as owned: its MODULES list fails on any unlisted file. Two runs needed the line without being told · evidence: task-9d4e21d1, task-de2d51db · status: pending
- 2026-10-07 [MISSING] §spec 1 Brief shape — a byte-for-byte port brief names the env the original runs with (`SKYTUNE_REPO` / `SKYTUNE_CONCEPTS` / `SKYTUNE_CAPS`): the original elfit found its caps next to itself and needed a scratch symlink to run · evidence: task-de2d51db · status: pending
- 2026-10-07 [COSTLY] §spec 4 provenance — `retune_particles` in draw_vanilla_style.py rewrites particle JSON `size` from the `PARTICLE_FILES` rows, so a hand-edited size is lost on the next generator run unless the row changes; only `N * variable.scale` and `(a + variable.particle_X * b) * variable.scale` survive `scale_expr`. Brief fx workers to change the row, then check the JSON regenerates byte-identical (`--root <scratch copy>`) · evidence: task-222da532, task-e7485779 (both changed rows; CTO regenerate check identical) · status: pending
- 2026-10-07 [COSTLY] §spec 1 — no shared offline particle projector or renderer, so each fx worker (night, near, sun aim) rebuilt one in scratch; a tools/ projector (spot to camera basis, billboard render, colour-class measure) would save that · evidence: task-e7485779, task-222da532 · status: pending
- 2026-10-07 [COSTLY] §spec 2 — two parallel fx lanes with disjoint briefs still both edited runtime.js's import line, the COLORS row and the night lines of `activeRates`; the second merge needs a rebase. Give one lane the shared rows, or plan the merge order up front · evidence: sky-nightfx af36eb0 vs sky-nearfx 7668c63 (trial merge, 3 hunks) · status: pending
- 2026-10-07 [WRONG] §spec 4 provenance — my note above ("check the JSON regenerates byte-identical with --root <scratch copy>") proves nothing as written: `retune_particles` rewrites existing files in place, so an untouched copy compares equal whether or not the generator owns the file. Perturb every target file in the scratch copy first (append a byte), run the generator, then compare; a file still perturbed is owned by another generator (cloud_bank*.json by draw_clouds.py) · evidence: task-a7541a42 (20 rewritten identical, 3 cloud_bank stayed perturbed); the nightfx/nearfx checks earlier on 2026-10-07 were unperturbed · status: pending
- 2026-10-07 [COSTLY] §spec 4 provenance — rebasing a branch whose first commit was already merged upstream (cherry-picked to its own branch) replays its provenance log rows; the conflict resolver keeps both sides, so the rows appear twice. Drop the merged commit (`git rebase --onto <its parent> <it>`), then dedupe exact log lines and check `git diff origin/<base> -- provenance/log.jsonl` has no `-` lines · evidence: task-e2fd5a33, MoonieX-Bedrock d2911e5. Second sighting 2026-10-07 (cto-369faf85): cherry-picking 3 unmerged commits onto a newer main conflicted in `provenance/log.jsonl` twice; both sides only appended different rows, so deleting the markers (a union) was right, then a json-parse of every line and `provenance.py check` · evidence: MoonieX-Bedrock sky-art-gpt4 5a7a010 · status: pending
- 2026-10-07 [MISSING] §spec 4 — a tool that writes dev-only files into a pack (wcal_*.json fogs) needs the never-commit rule enforced in the tool (refuse while staged/tracked, `clean` unstages) and in a gate test, because the tool folder's .gitignore cannot reach the pack · evidence: task-1840ca96, MoonieX-Bedrock c5adb6a · status: pending
- 2026-10-07 [MISSING] §spec 10 — CEO ruling: every reference link, picture or data file gets its URL + our analysis in docs/reference/links.jsonl in the same turn ("บังคับใช้กับทุกลิ้งที่เป็น Reff และข้อมูล"); rule body added on the CEO's word · evidence: Agents-Core 8ed343c7, MoonieX-Bedrock refs-ledger 5053e48 · status: promoted
- 2026-10-08 [MISSING] §spec 1 gates — a test that compares the shipped pictures with a builder reading an art folder outside the repo (HQ Assets) fails on every other checkout once that folder runs ahead of the pack (a scene painted but not yet shipped): compare only the pictures the pack ships, and skip when the folder is absent · evidence: cto-f39cb080 confirm35 report (test_cloud_bg failed on their merge), MoonieX-Bedrock b4a8425 · status: pending
- 2026-10-08 [MISSING] §spec 4 provenance — `provenance/assets.jsonl` holds one row per path (a re-record replaces it), so its merge conflicts are not the log's union: take, per path, the side that changed the row since the merge base, and stop if both did. Two branches that regenerate different files of the same folder conflict on neighbouring rows every merge (3 times in one night). Seen by two sessions independently: cto-f39cb080 ("per-path rows merged" on sky-ringl2-merge 04b09f8) and cto-369faf85 (MoonieX-Bedrock 6a20cb6, b10e27c, 757ec03; the script is 20 lines: `git show :1:/:2:/:3:provenance/assets.jsonl`, dict by path, sorted). Third sighting 2026-10-10: a union merge of assets.jsonl left two rows for the same path, and the per-path resolve fixed it (MoonieX-Bedrock 553a602, cto-369faf85) · status: pending
- 2026-10-09 [MISSING] §spec 4 provenance — a generator that ships byte copies of another generated file (ringN2: ten `ring_sun_eKK.png` copies of `ring_sun.png`, each with an emissive texture_set) goes stale in a merge when the other branch rebuilt the source: sky-ringl2-merge had regenerated `ring_sun.png` (297 to 268 B), and the merged tree failed `test_the_shipped_files_are_the_generators_output` and `test_ringn2_dlit_copies_are_the_cutouts_with_an_emissive_texture_set_each`. After a merge that touches generated pack files, rerun their generators (`python3 tools/skytune/cloud_ring.py` rewrote only the ten copies) and `provenance.py record` the rewritten files before the gates (n=1) · evidence: f39 merge pytest 2 failed 2026-10-09 01:18; fix f3e2658 on MoonieX-Bedrock sky-cloud-ring-prep, 2305 passed · status: pending
- 2026-10-09 [WRONG] §spec 4 provenance — the per-path merge of assets.jsonl (note 61a447fd, merge_prov.py) wrote the file EMPTY when git had already auto-merged it: a cleanly merged file has no :1/:2/:3 stages, so `git show :N:path` returns '' for all three. Merge a provenance file only when `git ls-files -u -- <path>` is non-empty; the script now checks that (tested on a synthetic repo) · evidence: f39 merge of sky-ring-golden-air 1960bac, Assets/MoonieX/Bedrock/sky/scratch-cto-369faf85-2026-10-08/merge_prov.py · status: pending
- 2026-10-10 [MISSING] §spec 1 — a brief that lets a worker add a new kind of file to `sky_tex` (the texture pack) must list `tools/validate.py` in what it owns: the texture-pack allowlist (R7/R14) refuses any file it does not name, so the gate cannot pass without a narrow exception there · evidence: cto-f39cb080 worker ship-biomes, MoonieX-Bedrock e8bdc7b (64 `RP/biomes/*.client_biome.json`) · status: pending
- 2026-10-10 [MISSING] §spec 1 — in-session sibling workers share one scratchpad: ship-cleanup overwrote ship-fixes' `scratchpad/edit_logic.py` after it had run. Give each lane a file-name prefix for scratch scripts in the brief · evidence: cto-f39cb080 workers ship-fixes (switched to `shipfix_*`) and ship-cleanup, 2026-10-10 · status: pending
- 2026-10-10 [MISSING] §review — parallel lanes that both pass their gates can still break each other's tests by meaning, not by text: ship-fixes renamed the status tail field `underwater=` to `uw_tune=`, ship-tune's new tests asserted the old name, and 4 tests failed only after both merged (no text conflict in the tests). Run node on the merged branch after every lane merge, not only on each branch · evidence: MoonieX-Bedrock sky-basics d98cf1b (fixed in the merge commit) · status: pending
- 2026-10-10 [COSTLY] §spec 1 — adding a built-in default to a hook-driven runtime breaks every older test that assumes a bare world (about 40 in `sky_core_runtime`); the harness needs an off switch (`defaultTune:null`). A brief that adds a default should name that switch · evidence: cto-f39cb080 worker ship-tune, MoonieX-Bedrock 86b1ea2 · status: pending
