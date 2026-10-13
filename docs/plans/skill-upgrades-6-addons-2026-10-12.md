# Skill upgrades from 6 Claude add-ons, written as our own (plan, 2026-10-12)

**Order:** the CEO, 12 Oct, relayed by SomPong: "อยากให้เอามาเขียนเป็น Skill ของเรามากกว่านะ เอามาปรับใช้กับองค์เรา ใน Skill CXO ที่เรามีอยู่แล้ว".
**Source:** SomPong `docs/research/2026-10-11-claude-plugins-6-repos-skill-upgrades.md` (SomPong 9e89fe9). Nothing was installed or run; the numbers in it are the projects' own.
**Owner:** CTO (Contabo, session f400a770). **Status:** waiting for the CEO's OK. Bulk edits land after the weekly quota resets on 13 Oct at 16:59 BKK.

> สรุปสั้น: 12 ข้อ → 7 ข้อเขียนเป็นกฎ (2 ข้อ HARD: 6, 7) + 1 ข้อเป็น fact (11) (ถ้า CEO OK แผนนี้ = CEO ruling), 4 ข้อลงเป็น Field note รอให้งานจริงของเรายืนยัน 2 ครั้งก่อน
> ข้อ 8 (Debugging) ไม่สร้าง skill ใหม่ แต่ใส่ใน roles/developer.md ที่มีอยู่แล้ว ตามคำ CEO "ใน Skill ที่มีอยู่แล้ว"
> gitleaks: แก้แล้ว 214b1816 (ไม่มี gitleaks = ตะโกนทุก commit). ที่เพิ่งเจอคือ Contabo ไม่มี pre-commit hook เลย → ข้อ G2 รอ OK

## How each item is tiered (ADR 0026 applied to outside sources)

An idea from someone else's repo is n=0 in our own runs. So:
- **Field note** (status `pending`, tagged `source: outside`) is the default. It is promoted when two of our own runs agree.
- **Rule now** only when our own record already has the evidence (cited below), or the change applies a rule the CEO already made. In both cases the CEO's OK on this plan counts as the ruling.
- **HARD** only if it passes the HARD test in `ALL_Protocol_SkillAuthor` (money, irreversible, safety/legal/scope). Everything else is advice that the model may override, saying why.

**Licences.** Ponytail (DietrichGebert) and Superpowers (obra) are MIT, so we credit them by name where we use their ideas. Anthropic's claude-security plugin is proprietary, so we take its ideas only and none of its text goes into this public repo. claude-code-security-review is MIT; we use only the built-in `/security-review` command it describes.

## The 12 items

| # | File · section | The change, in our words | Tier | Evidence | Blast radius (who behaves differently) |
|---|---|---|---|---|---|
| 1 | `roles/developer.md` · Coding Discipline | A new branch in a parser, money math, an auth or security check, or a script that deletes or posts gets one small test or assert. Check that it fails without the change. (Idea: Ponytail v5, MIT.) | Rule, advice | Related, ours: a replay script merged without ever being run had 3 bugs that were found live (44b9d54e, task-d206afca). Outside: Ponytail's own benchmark, 68→98% | Every `developer` worker spawned after landing, on any machine (`runners/worker_init.py` reads the role file at spawn) |
| 2 | `roles/developer.md` · Pre-work Checklist, new step 5 | Before the first edit, list what the change reaches: callers, the tests that cover it, fixtures, config, exports. Paste the list into Notes for Reviewer. (Ponytail.) | Rule, advice | Extends the existing rule "grep every caller" in the same file. Ours: none counted | `developer` workers |
| 3 | `roles/_worker_shared.md` · Report Format | Add a `## Not checked / risk` section: 1–2 lines on what the worker did not verify. "none" is allowed only with a reason. `CTO_Gate_MergeChecklist` Gate 1 then expects the section. (Ponytail.) | Rule, advice | It is a report format, so it only applies prospectively. Ours: none counted | **Every worker role** (developer, tester, browser_operator, video_editor, web_designer, devops, security…), plus CTO merge reviews |
| 3b | `roles/developer.md` · lines 45–end | Delete the stale copy of "Shared DEV Conventions". `_worker_shared.md` is already prepended at spawn (`worker_init.py:489-490`, `spawn-worker-remote.sh:352`), and the copy is older: it is missing rule 9, "ask before you spend". | Cleanup | diff of origin/main 7f7d6ca6 | `developer` workers read the conventions once instead of twice |
| 4 | `CTO_Gate_MergeChecklist` · Gate 2 | **The new test must fail when the fix is reverted.** For a bug-fix branch, run its new test against the base code and quote both lines: fails on base, passes on the branch. A test that passes on both proves nothing. (Idea: Superpowers, MIT.) | Rule, advice | Ours, 2+ runs: Gate 2's "a pass that cannot fail" (0cf98ec5, b2830b3c). Used today on 214b1816: 4 of the 6 new tests fail on base | CTO sessions merging a bug fix (Mac + Contabo). Cost: 1 extra test run per merge |
| 5 | `CTO_Gate_MergeChecklist` · new 4c | Concrete-case review: read the callers of every changed function. Every finding names the input or state that breaks it (`X=… → wrong Y`). A finding without one is a question, not a reason to reopen. (Ponytail.) | **Field note** | No case of ours yet where a vague finding cost a round | (until promoted) CTO reviews |
| 6 | `CTO_Gate_MergeChecklist` · new Gate 2b | A branch that touches auth, secret handling, routes, hooks, `.github/`, or anything in a public repo (Agents-Core, Agents-Rules) gets `/security-review` on its own diff and a gitleaks scan of `<base>..<branch>`. Paste both verdicts. A hit is reported as file:line only (item 7). Never run on an outside contributor's PR (the action is not hardened against prompt injection). | **Rule, HARD** (irreversible: a pushed secret in a public repo is leaked for good) | Ours: a credential-shaped literal in a local Contabo commit was caught only by a hand scan, and that push has been held since 10 Oct | CTO merges that touch those paths: about 1 extra review run each. Needs gitleaks on the reviewing box (G2) |
| 7 | `CTO_Procedure_KeyFetch` · Rules, new 7 | When a scan or review finds a key: report the file:line and the key type, never the value or any part of it. Then tag it `leaked` in Infisical and rotate it (new key → Infisical → verify → revoke). | **Rule, HARD** (irreversible) | Applies the CEO's secrets rule of 25–26 Sep (CLAUDE.md "Secrets"). Ours: the a60f1744 scan was reported at file level | Anyone running KeyFetch or a leak scan (CTO, browser_operator, developer) |
| 8 | `roles/developer.md` · Coding Discipline (**not** a new skill) | Debugging: reproduce first, find the root cause, then fix. After 3 fixes that did not work, stop: write BLOCKER.md with what was tried and hand back to the C-level. (Superpowers.) | Rule, advice | The CEO asked for "skills we already have"; `ALL_Protocol_SkillAuthor` §4.1 says an owner already exists (developer.md "Bug fix = root cause"). A role file loads on every spawn, a skill only on trigger | `developer` workers |
| 9 | `CXO_Protocol_DevSpawn` · §8 | Cap on fix rounds: round 4 goes to a fresh worker on a stronger model, round 5 means re-plan. **This conflicts with the current rule** "iteration 3 → escalate to the CEO" (`roles/cto.md`, MergeChecklist operating rules). (Superpowers.) | **Field note** (it would change a CEO-facing rule) | Outside only | (if promoted) CTO sessions; round 4 costs an Opus run instead of a CEO turn |
| 10 | `CXO_Protocol_DevSpawn` · §3d | No placeholder briefs: no "handle edge cases", "tests as needed" or "TBD". Each acceptance item names the test, command or URL that proves it. (Superpowers.) | **Field note** | Ours n=1: "State the job, not just the target" (memory: a worker swapped CREATE for CONFIRM) | (if promoted) every brief the CTO writes |
| 11 | `session-save` · How to run it, new step 0 | Before saving, check `wc -lc` on MEMORY.md. Past 180 lines or 22 KB, warn and move lines into a sub-index. Claude Code loads only the first 200 lines / 25 KB, and the overflow is dropped without a warning. | Fact (Knowledge line with its source; confirm against code.claude.com/docs memory page at landing) | Contabo today: 104 lines, 16.8 KB, under the cap | Every C-level that runs `/session-save` |
| 12 | `ALL_Protocol_SkillAuthor` · §4 Create | For a new Gate or Rules skill, first run the task once without the skill and record what went wrong. That run is the skill's first piece of evidence. (Superpowers.) | **Field note**, low | Outside only | (if promoted) anyone who authors a skill |

## Found along the way

| # | What | Status | Blast radius |
|---|---|---|---|
| G1 | `scripts/install-git-hooks.sh`: a missing gitleaks is loud (a warning on every commit, and the installer exits 2 unless `ALLOW_NO_GITLEAKS=1`). The stanza is replaced on every run. | **Landed 214b1816**: 17 tests passed; 4 of the 6 new tests fail against the old installer | Any box that re-runs the installer. A box without gitleaks prints a warning on every commit |
| G2 | **Contabo has no pre-commit hook at all** (`.git/hooks/pre-commit` is absent), and gitleaks is absent too. Proposal: install gitleaks (pinned release, sha256 checked against the release's checksums file) into `/usr/local/bin`, then run the installer in `/opt/MoonieXHQ/Agents/Core`. | Waits for the CEO's OK | **Every commit on Contabo, by every session and worker**: gitleaks + skill-lint + media-guard (scope from `config/storage-policy.yaml`) start running. A media file or key-shaped string will block a commit that passes today |
| G3 | Contabo sessions read skills from local main, which is 195 commits ahead of origin with the push held over a60f1744. Text landed on origin reaches Contabo only after `git merge origin/main` into local main (local only, no push), as was done on 10 Oct. | Do it after each landing | All Contabo C-levels and workers |

## How it lands (after the CEO's OK; bulk after 13 Oct 16:59 BKK)

1. One detached worktree off `origin/main`. One commit per file, using the ADR 0026 format: `skill(<name>): rule|note — <what> — evidence <…>`.
2. Gate per `CTO_Gate_MergeChecklist`: `scripts/skill-lint.py check` is clean for each touched skill; regenerate `docs/org/SKILL-INDEX.md` if the curator says it is stale; run the §4 step-7 path check; scan for invisible characters; confirm no line was copied from the proprietary plugin (this text is written fresh).
3. `git push origin HEAD:main` → `merge-base --is-ancestor`. Never push local main, never `merge_task` (a60f1744 hold).
4. G3: merge origin/main into Contabo local main. Report the shas to SomPong.

## Not taken (from the research, unchanged)
Installing any plugin, including Superpowers, Ponytail, Claude Code Setup and the security plugin: their hooks inject into every session, including SomPong and the CMOs. OmniRoute and the Caveman proxy are out in any form (ToS, CVE-2026-88062, prompts sent to unknown providers). Also left out: the "1% chance → must invoke a skill" rule, brainstorm Q&A before every build, deleting code written before its test, a scheduled full-codebase security scan, and auto-fix or auto-push by any tool.
