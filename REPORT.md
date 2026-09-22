# task-95eeb491 — MoonieX HQ migration step 4a (ADR 0028)

Moved everything under `~/Projects` EXCEPT `Agents/` (Agents-Core, the runtime —
step 4b, later, with its own rehearsal) into `~/MoonieXHQ`. Ran for real on the
Mac (this session's environment IS the real machine — same one steps ②③ ran
on for real, already merged).

## Before / after

| unit | before | after | branch/sha (unchanged) | dirty |
|---|---|---|---|---|
| Agents/Rules | `/Users/gob/Projects/Agents-Wikis` | `/Users/gob/MoonieXHQ/Agents/Rules` | main @ `4c0d9dc009` | 0 |
| Agents/Wikis | `/Users/gob/Projects/LLMs` | `/Users/gob/MoonieXHQ/Agents/Wikis` | main @ `2a5a8f9e68` | 0 (pushed +3 first) |
| Agents/Memory | `/Users/gob/Projects/Agents-Memory` | `/Users/gob/MoonieXHQ/Agents/Memory` | main @ `4816a84b5e` | 3 (pre-existing, unchanged) |
| Agents/Skills | `/Users/gob/Projects/mooniex-claude-skills` | `/Users/gob/MoonieXHQ/Agents/Skills` | main @ `4ca6e12e6b` | 1 (pre-existing `.DS_Store`, unchanged) |
| External/9arm-skills | `/Users/gob/Projects/external/9arm-skills` | `/Users/gob/MoonieXHQ/External/9arm-skills` | unchanged | — |
| External/agentkits-marketing | `…/external/agentkits-marketing` | `…/External/agentkits-marketing` | unchanged | — |
| External/arb-refs (no git) | `…/external/arb-refs` | `…/External/arb-refs` | n/a | — |
| External/cost-guardian-review | `…/external/cost-guardian-review` | `…/External/cost-guardian-review` | unchanged | — |
| External/diagram-design | `…/external/diagram-design` | `…/External/diagram-design` | unchanged | — |
| External/marketingskills | `…/external/marketingskills` | `…/External/marketingskills` | unchanged | — |
| External/wondelai-skills | `…/external/wondelai-skills` | `…/External/wondelai-skills` | unchanged | — |
| External/paperclip | `/Users/gob/Projects/mooniex-nohuman/paperclip` | `/Users/gob/MoonieXHQ/External/paperclip` | unchanged | — |
| UNKNOWN/mooniex-school | `/Users/gob/Projects/mooniex-school` | `/Users/gob/MoonieXHQ/UNKNOWN/mooniex-school` | n/a (3 files, no git) | — |
| Archive/NoHumanCompany | `/Users/gob/Projects/mooniex-nohuman` | **trashed** → `~/.Trash/hq-step4a-20260923T031930/mooniex-nohuman` | n/a | — |

`Agents/Core` (the runtime itself, `/Users/gob/Projects/Agents`) was never
touched, per the task brief — step 4b, later.

Two pushes happened (Phase A, before any move): `LLMs` main +3 → origin,
`mooniex-claude-skills` main +5 → origin. Both are the repos' own already-committed
work reaching their own already-configured `origin`; no history rewritten.

Compat symlinks created (5, `remove_at_step: 5` per this task's instruction —
step2/3 used 4):
- `/Users/gob/Projects/Agents-Wikis` → `.../Agents/Rules`
- `/Users/gob/Projects/LLMs` → `.../Agents/Wikis`
- `/Users/gob/Projects/Agents-Memory` → `.../Agents/Memory`
- `/Users/gob/Projects/mooniex-claude-skills` → `.../Agents/Skills`
- `/Users/gob/Projects/external` → `.../External` (**one** symlink for the
  whole directory, not one per clone — matches the task's instruction; the
  ~14 `~/.claude/skills/*` links that point INTO individual clones still
  resolve through it, verified live)

`paperclip` and `mooniex-school` get no compat symlink (their old parents —
`mooniex-nohuman`, deleted; a plain-files folder — never had one to begin with,
matching precedent: no other Archive/UNKNOWN item has one either).

## nohuman brand/ verification

`verify_nohuman_brand()` did a **fresh `git clone --depth 1`** of
`https://github.com/PASAKON/MoonieX-NoHumanCompany.git` into a scratch temp
dir (never trusted the local `.git`), then `diff -rq --exclude=.git` against
the working tree's `brand/`. **Result: clean, 0 differences.** `paperclip`
(already its own clone, gitignored by the parent) was moved out first;
the rest of the directory (`brand/`, `.git`, `.gitignore`, `README.md`,
`.claude/`, `.DS_Store`) was then moved to
`~/.Trash/hq-step4a-20260923T031930/mooniex-nohuman/` (never `rm`).

## Links repointed (by kind)

- **Code files rewritten (15):** `CLAUDE.md`, `claude-home/hooks/office-inbox.mjs`,
  `claude-home/hooks/office-pretool.mjs`, `claude-home/hooks/office-userprompt.mjs`,
  `claude-home/mcp/mooniex-coord/index.mjs`, `claude-home/settings.json`,
  `config/wikis.yaml`, `docs/HOOKS-gateguard-category.md`, `docs/memory-repo.md`,
  `scripts/claude_home_migrate.py`, `scripts/hook-research-gate.py`,
  `scripts/research-file.py`, `scripts/test_hook_cwd_guard.py`,
  `scripts/test_hook_research_gate.py`, `tools/memory_sync.py`.
  (This task's own verification grep, re-run after: **0 hits**, see below.)
- **`claude-home/skills.txt` rows rewritten (21):** 14 backed by `External/*`
  clones + 7 backed by `Agents/Skills` (`mooniex-claude-skills`), rewritten to
  literal `/Users/gob/MoonieXHQ/...` targets (not a new `$HQ` macro) —
  `scripts/install-claude-home.sh` untouched, all 21 confirmed `linked` (0
  drift) by `--check` below.
- **hq.yaml `compat_links` (5)** — listed above.
- **hq.yaml `items:` `current:` fields patched (9):** 7 external clones +
  paperclip + mooniex-school. Plus **1** Archive item (`NoHumanCompany`
  `current` → `null`, `action` text updated to record the trash).
- **The `~/.claude/projects/-Users-gob-Projects-Agents/memory` symlink (1)**
  repointed directly: was `/Users/gob/Projects/Agents-Memory`, now
  `/Users/gob/MoonieXHQ/Agents/Memory`. No PermissionError — the auto-mode
  classifier did not block it.
- **`tools/memory_sync.py`**: no literal path to edit — `default_memory_dir()`
  computes the path and reads whatever the symlink points at via
  `os.readlink`; repointing the symlink (above) *is* its new default,
  confirmed live (`memory_sync.resolve_repo_path(link)` →
  `/Users/gob/MoonieXHQ/Agents/Memory`, `memory_sync.pull(link)` → "Already
  up to date.", rc 0).

Verification grep (task's own, re-run after all edits):
```
$ git grep -I -l -E '/Users/gob/[Pp]rojects/(Agents-Wikis|LLMs|Agents-Memory|mooniex-claude-skills|external|mooniex-nohuman|mooniex-school)(/|"|$| )' -- . ':!docs/reports' ':!docs/briefs' ':!docs/ops'
(no output, exit 1)
```

## Denials / blockers

**None.** nohuman's brand/ diff came back clean (no STOP triggered), and the
memory symlink repoint was not denied by the auto-mode classifier.

## Manifest

`state/hq-step4a-migration-20260923T031930.json` (29 ops: move×13, symlink×5,
preflight×4, push×2, nohuman_brand_verify×1, trash×1, memory_symlink_repoint×1,
yaml_backup×1, yaml_edit×1). hq.yaml backup:
`state/hq-step4a-yaml-backup-20260923T031930.yaml`. Both are gitignored
machine-local rollback input (mirrors step2/3's own pattern; added the two
missing glob lines to `.gitignore`).

## `hq.py doctor` (verbatim)

```
$ /Users/gob/Projects/Agents/.venv/bin/python /Users/gob/MoonieXHQ/scripts/hq.py doctor
hq doctor: clean — disk agrees with the map
```

## `install-claude-home.sh --check` (verbatim, relevant excerpt)

```
— skills (claude-home/skills.txt is the map)
  linked   skills/blackliquidity-cut
  linked   skills/blue-ocean-strategy
  ... (all 46 rows) ...
  linked   skills/obviously-awesome
  linked   skills/mooniex-seo
  linked   skills/mooniex-content
  ... 
```
Every one of the 21 rows this task rewrote (and all 46 total) reports
`linked`, **zero drift**. The full run also reports 9 unrelated problems —
**pre-existing, not caused by this task**:
- 6 `DRIFT` on core entries (`CLAUDE.md`, `settings.json`, `hooks`,
  `commands`, `mcp/mooniex-coord`, `tools`) — an artifact of running the
  check from this **unmerged worktree**: the live `~/.claude` symlinks point
  at the real `/Users/gob/Projects/Agents/claude-home` (main branch's
  checkout), not this worktree's copy. Resolves automatically at merge —
  nothing to fix here.
- 2 `MISSING` under `reel-editor-th` (`.venv`, `assets/mooniex-broll`) — never
  provisioned in this environment, unrelated to any path this task touched.

## Tests

`pytest scripts/ tests/ --import-mode=importlib -p no:warnings --ignore=scripts/test_skill_doctrine_lint.py`
— **1543 passed, 0 failed, 18 skipped** (main's last measured baseline: 1527
passed / 15 skipped — pass count only rose: +19 from
`test_hq_migrate_step4a.py`, the skip delta is pre-existing/environmental
(`ORG_TEST_DB_URL` / `.venv`-at-root gated tests, unrelated to this task) and
was already present before any of this task's changes). Ran clean **after**
the real `--apply`, not just against the fixture.

One regression was caught and fixed during repoint: `--repoint` rewrote a
literal path inside `scripts/test_hook_cwd_guard.py`'s test *input* command,
which broke that test's own assertion (checking for a fragment of the same
string it had just rewritten) — fixed the assertion in the same commit.

## Notes for reviewer

- `scripts/claude_home_migrate.py`'s one-time cap-P typo-fix (already run,
  historical — its own docstring says so) became a tautological no-op after
  repoint (`s.replace(new, new)`, since both the "wrong" and "right" sides of
  its lowercase-typo check collapsed onto the same new canonical path once
  `LLMs` moved out from under `/Users/gob/Projects` entirely). It is 100%
  inert (branch never fires) and satisfies grep-clean; not worth a deeper
  rewrite for genuinely dead one-time code, but flagging in case you'd rather
  delete that block outright in a follow-up.
- `scripts/research-file.py`'s `RESEARCH_LIBRARY` default was (and, after the
  mechanical rename, still is) `.../Agents-Wikis/research` → now
  `.../Agents/Rules/research` — but hq.yaml's own `keeps:` field says the
  research cache (`research/`) belongs under `Agents/Wikis`, not
  `Agents/Rules`. This mismatch **predates** this migration (confirmed: it
  already pointed at the "wrong" repo by folder name before the move); this
  task only repointed the literal path, it did not audit or fix that
  pre-existing possible bug. Worth a separate look.
- `config/wikis.yaml`'s two comments that said "folder rename comes at HQ
  step 4" / "local folder still LLMs/ until HQ step 4" were stale now that
  this step actually ran — updated them in the same edit (adjacent line, not
  scope creep beyond a comment).

## Skill learning

- MISSING [hq-filing §Migration] : a per-item "own path never gets its own
  compat symlink, only a SHARED parent does" case (External's 7 clones) needs
  a *different* resumability check than the row case — `old.resolve() ==
  new.resolve()` alone misses "old already gone, new already holds the
  content, but the shared parent hasn't been symlinked yet" (crash mid-way
  through moving several clones out of one directory). Fixed by falling back
  to `not old.exists() and new.exists()` · evidence: task-95eeb491,
  `hq_migrate_step4a.py:already_migrated`, caught by
  `test_apply_resumes_after_external_clone_already_migrated`.
- MISSING [hq-filing §Migration] : verifying an archived repo's working
  tree against "the repo's HEAD" should mean a **fresh clone of the GitHub
  origin**, not the local `.git` — the local repo can have valid-looking
  clean status while still holding unpushed commits. Already stated in this
  task's brief; folding it as a named pattern since step 5 (Agents-Core) may
  have a similar archive/delete decision later · evidence: task-95eeb491,
  `verify_nohuman_brand()`.
- COSTLY [no owner] : a mechanical text-substitution repoint tool needs to
  know when a literal old-path string appears as *test input data* whose
  *assertion* also checks for a fragment of that same string — the rewrite is
  correct but the paired assertion silently goes stale. Cost: one full test
  suite run + fix cycle to catch it (would have shipped a broken test
  otherwise) · prevented by: after any mechanical repoint, grep the touched
  test files for their own literal-string assertions near the line that
  changed, not just re-run the suite and hope a failure surfaces it.
