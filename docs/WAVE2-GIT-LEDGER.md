# Wave 2 — Git Is The Ledger

Implements ADR 0022 §4 and the playbook's Wave 2
(`org:decisions/0022-skill-governance-visibility-authorship-audit.md`,
`org:playbooks/skill-governance-implementation.md`). Wave 2 only — no Wave 3
Phase 2, 4, or 5 work is included. Builds on Wave 0 (merged), Wave 1 (merged,
provenance frontmatter + `skill-lint.py`), and Wave 3 Phase 1 (merged,
plugin-level skill visibility).

The premise, per the ADR: the CEO removed the approval gate for authoring a
skill. What makes that safe is **undo**, not review. A prior spec proposed a
bespoke append-only JSONL ledger plus a content-addressed blob store — that
was rejected. `.claude/skills/` is already git-tracked; commits are already
append-only; git objects already are the before/after copies. This wave does
not build a ledger. It makes git into one.

## 2.1 — The curator commits what it changes

`archive`, `restore`, `pin`, `unpin`, and the new `create` verb each end by
staging the skill directory(-ies) they touched and committing them:

```
skill-curator: <verb> <name>

Skill-Actor: <role>/<session-id>
```

Identity comes from `tools/agent_transport.py`'s existing
`current_identity()` — not a second identity source. `Identity.role` /
`Identity.session_id` map straight onto the trailer (`CEO`/`None` → `CEO/-`
when nothing is calling from inside a C-level or worker session).

The import is **lazy** (`_agent_transport()`, called only from inside
`_skill_actor()`/`create_skill()`), not a module-level import. Reason:
`scripts/test_skill_lint.py`'s own root-derivation test loads a *copy* of
`skill-curator.py` into a fake repo tree that has no `tools/` directory at
all — merely importing the module has to keep working there, and only a verb
that actually needs identity should pay that import's cost.

**Every mutating verb now requires a real git repo** — `_git_cwd()` walks
`owned_skills_dir` → `archive_dir` → `owned_skills_dir.parent` looking for
somewhere to run `git` from, and every `git add`/`commit`/`revert`/`status`
call is scoped with `--` to exactly the paths a verb touched, never a bare
`git add -A .` that could sweep up someone else's unrelated staged work.

A **no-op mutation commits nothing.** `unpin` on a skill that was never
pinned changes zero bytes (see 2.3 — `pinned: false` is never written, the
key is deleted instead), so `git diff --cached --quiet` short-circuits
before any commit — proven by
`test_skill_curator.py::test_noop_mutation_creates_no_commit`.

### The `create` verb

Reverses ADR 0018 §6, which put agent-authored skill creation explicitly out
of scope — ADR 0022 reverses that. `create_skill(paths, name, *,
description, audience)` writes a fresh `SKILL.md` stamped
`created_by: agent` and `author: {role, date}` from the calling identity,
then commits it the same way every other verb does. It does **not** apply
the audience-prefix naming convention itself (2.4) — that is the caller's
job when it picks `name`; the verb only refuses an unsafe or colliding
directory name.

Verified live (throwaway repo, not this checkout — see Demonstration below):
a skill produced by `create` passes `skill-lint.py check` with **zero
findings** on the first try.

## 2.2 — Three read verbs

| Verb | Implementation | ~lines |
|---|---|---|
| `history [--skill NAME]` | `git log --follow -- .claude/skills/<name>`, or `git log -- .claude/skills` for the whole tree when `--skill` is omitted | 9 |
| `undo <sha>` | `git revert --no-edit <sha>` | 6 |
| `drift` | `git status --porcelain -- .claude/skills` | 5 |

All three are thin wrappers — no bookkeeping of their own, because the
ledger IS git. `history` on an **archived** skill's name still works: git
log finds commits that touched `.claude/skills/<name>` historically even
though that path no longer exists at HEAD — demonstrated below and covered
by `test_history_of_archived_skill_still_shows_earlier_commits`.

### What `undo` does, per action type

| Action | What `undo <sha>` (git revert of that commit) does |
|---|---|
| `create` | Deletes the newly-created skill directory entirely — the skill never existed. |
| `archive` | Restores the skill to its pre-archive owned-dir location with its pre-archive content, byte-for-byte, and removes it from the archive dir. This is `git revert` reversing a rename-with-frontmatter-edit in one step. |
| `pin` / `unpin` | Reverts just the `pinned:` line change in that skill's frontmatter; nothing else moves. |
| A hand-edit that was later committed normally (not through the curator) | Reverts exactly that diff, like any other git revert — the ledger doesn't care who authored a commit. |

`restore` (the pre-existing ADR 0018 lifecycle verb — bring an archived
skill back into the owned dir) is **not** the same thing as undoing an
`archive` commit, even though the two often produce the same end state.
`restore` is the curator's own semantic un-archive action, and it commits
its own new commit (`skill-curator: restore <name>`) rather than reverting
the old `archive` one. Both are demonstrated below; both restore the
skill's content byte-for-byte, because `restore` deletes exactly the two
frontmatter lines `archive` added (`lifecycle:`, `archived_at:`) instead of
overwriting them with `lifecycle: active` — same trick as a clean revert,
implemented directly rather than through git.

## 2.3 — The sidecar is deleted

**Checked before deleting, per the brief: `state/skill-usage.json` has never
been written.** `find state/` in this worktree shows only `state/locks/` and
`state/logs/` — no `skill-usage.json` anywhere, and no prior wave's tests or
docs reference its content ever having existed. Nothing to migrate.

Removed: `_load_state()`, `_save_state()`, `CuratorPaths.state_path`. The
`names |= set(existing_state.keys())` line at the old `skill-curator.py:306`
— the hazard the brief named by name, where any non-skill key in that state
would enumerate as a phantom skill — is gone along with the dict it read
from. There is no replacement mechanism that could reintroduce the same
shape: `build_portfolio()` now derives every name from `_scan_skill_dir()`
(the owned dir, the archive dir) plus `skill-report.py`'s own discovery,
never from an arbitrary externally-writable key set.

`pinned`, `lifecycle`, and `archived_at` now live in each skill's own
`SKILL.md` frontmatter, written via a new line-level `_patch_frontmatter()`
helper — not a full `yaml.safe_dump` re-flow, deliberately: a re-dump would
reformat every hand-written block scalar (`description: >-`, `scope: >-`)
in the file, which is far more blast radius than a lifecycle-field patch
needs. It only ever touches unindented top-level `key: value` lines, so an
indented continuation line of a block scalar is never mistaken for one.

**`lifecycle` in frontmatter is a record, not a second source of truth.**
`build_portfolio()` decides archived-vs-active purely from which directory a
skill's `SKILL.md` is physically under (`archive_dir` vs `owned_skills_dir`)
— exactly like before, when the sidecar's own `lifecycle` field was already
subordinate to that same filesystem check. The frontmatter field exists so
`git log`/`git show` on an archived skill's file is self-explanatory to a
human reading it later; nothing computational depends on it agreeing with
reality, and it can't — a hand-edited or stale value there is caught by
`drift`, not silently trusted.

`_backup_skill()`'s `copytree` into `state/skill-curator-backups/` is
**unchanged, left in place this wave**, per the brief — retire it only once
`undo` is proven in real use.

## 2.4 — Prefix: new skills only

`.claude/skills/skill-author/SKILL.md` (the prompt skill, not code) gained a
"Audience prefix — NEW skills only" subsection: a brand-new skill's
directory name is prefixed with its `audience:` role(s)
(`CTO_Higgsfield_Seedance2.5_Prompt`, the ADR's own example). The field
remains the authority — reports and visibility both compute from
`audience:`, never by parsing the name string — the prefix is a naming
mirror for humans browsing the directory.

**No existing skill directory was renamed, and no `git mv` was run.** The
21 pre-ADR skills are grandfathered permanently, called out explicitly in
the skill text: `~/.claude/skills` holds symlinks into this repo
(`browser-operator`, `mooniex-finance`, …), and renaming the target dangles
the link — the skill vanishes with no error, and 39+ files reference skill
names as literal strings.

## 2.5 — `skill-author` loses its global write path

Same file's "Location" table dropped `~/.claude/skills/<name>/SKILL.md` as a
sanctioned location for org-authored skills, with an explicit note why: a
skill written there sits outside git, outside `skill-curator.py`, and
outside `undo` by construction, which defeats this entire wave. The table
now points at `<repo>/.claude/skills/<name>/SKILL.md` exclusively, and
recommends `skill-curator.py create` as the preferred path (it stamps
identity and commits automatically). A purely personal, non-org skill is
still fine under `~/.claude/skills/` — that was never this wave's concern.

## The honest limit

**A skill edited and never committed is unrecorded.** CEO rule 4 forbids
the gate that would force a commit on every edit, so there is no mechanism
in this repo that *guarantees* a hand-edit lands in git. `drift` is the
detection half, not a prevention: `git status --porcelain -- .claude/skills`
is one command, and it will show a modified-but-uncommitted `SKILL.md` the
moment anyone runs it — but nothing runs it automatically. Between a
hand-edit and the next `drift` call (or the next `git status` anyone happens
to run), that change is real on disk and invisible to `history`/`undo`
alike. This is the deliberate trade the ADR makes: no gate, so also no
guarantee — only a cheap, always-available way to go check.

### Closed: a mutation landing with no ledger entry at all (CTO iter-1)

A narrower, worse failure mode than the one above nearly shipped in this
wave's first iteration: not a hand-edit that skips the curator, but the
curator *itself* moving a skill on disk with `git add` staging it and then
never committing. `_skill_actor()` was called **inside** the commit message
f-string — after `shutil.move`/`_backup_skill()` and after `git add` had
already run. If identity lookup raised (reproduced with `scripts/skill-curator.py`
copied into a throwaway repo with no `tools/` package: `ModuleNotFoundError:
No module named 'tools'`), the move and the `git add` had already happened
and the exception propagated before `git commit` ever ran — a skill gone
from its owned location, staged, and un-committed. `drift` still caught the
resulting `git status --porcelain` line, but that is exactly the
untracked-mutation state this wave exists to prevent, produced by the
curator's own commit path rather than an outside hand-edit.

Closed by two changes, both required together:

1. **Order.** Every mutating verb (`archive`, `restore`, `pin`/`unpin` via
   `_set_pinned`, `create`) now resolves its actor as the first line of the
   function, before `_resolve_within`, `_backup_skill`, any `shutil.move`,
   or any frontmatter write. `_commit_skill_mutation` takes the resolved
   `actor: str` as a parameter instead of calling `_skill_actor()` itself
   from inside the commit message.
2. **`_skill_actor()`/`_current_identity_safe()` cannot raise.** The
   `tools.agent_transport` import and `current_identity()` call are wrapped
   in a broad `except Exception`, logged to stderr, and fall back to an
   `_UnknownIdentity` (`role="unknown"`, `session_id=None`) — producing a
   `Skill-Actor: unknown/-` trailer rather than blocking the verb. CEO
   rule 4 forbids a gate that would refuse authoring over identity trouble,
   so the fallback keeps the verb completing; what changed is that the
   *filesystem* mutation and the *commit* are now atomic with respect to
   this specific failure — either both happen (real or fallback actor), or
   neither does.

Point (1) is what actually closes the reported defect (fail-closed: nothing
moves before the actor is known); point (2) is defense in depth so an
identity-lookup failure degrades to an honest trailer rather than becoming
a reason to refuse a mutation the CEO already said should never be gated.
Tests: `test_actor_resolution_failure_leaves_filesystem_untouched` (proves
the ordering — even a raise from `_skill_actor()` itself leaves the tree
byte-identical, nothing staged, no commit) and
`test_identity_lookup_failure_falls_back_to_unknown_actor_and_verb_completes`
/ `test_archive_completes_with_fallback_actor_when_identity_lookup_fails`
(prove the fallback trailer and that the verb still completes) in
`scripts/test_skill_curator.py`.

## Demonstration (throwaway repo, not this checkout)

```
$ python -c "... curator.create_skill(paths, 'demo-skill', description='Demonstration skill for Wave 2 docs.', audience=['cto']) ..."
CREATE -> .../owned/demo-skill
--- SKILL.md after create ---
---
name: demo-skill
description: "Demonstration skill for Wave 2 docs."
created_by: agent
author: {role: developer, date: "2026-09-01"}
audience: [cto]
---

# demo-skill

Demonstration skill for Wave 2 docs.

$ python -c "... curator.archive_skill(paths, 'demo-skill') ..."
ARCHIVED, owned exists: False
ARCHIVED, archive exists: True
--- SKILL.md after archive ---
---
name: demo-skill
description: "Demonstration skill for Wave 2 docs."
created_by: agent
author: {role: developer, date: "2026-09-01"}
audience: [cto]
lifecycle: archived
archived_at: "2026-09-01T16:58:51.695056+00:00"
---
...

$ git log --format='commit %H%n%B---------------'
commit 135804cd332c2048d6b4666d18b3fa7ea98d04dc
skill-curator: archive demo-skill

Skill-Actor: developer/task-demo123
---------------
commit 7c50d057c12976b87aa055f805c01e08d05bea38
skill-curator: create demo-skill

Skill-Actor: developer/task-demo123
---------------

$ python -c "... curator.undo_mutation(paths, '135804c...') ..."
UNDO OUTPUT: [main d1db9a7] Revert "skill-curator: archive demo-skill"
 1 file changed, 2 deletions(-)
 rename {archive => owned}/demo-skill/SKILL.md (75%)
owned exists after undo: True
archive exists after undo: False

$ diff <(git show 135804c^:owned/demo-skill/SKILL.md) owned/demo-skill/SKILL.md
IDENTICAL to pre-archive git blob    # zero diff lines -- byte-for-byte

$ echo "hand-edited" >> owned/demo-skill/SKILL.md
$ python -c "... curator.detect_drift(paths) ..."
 M owned/demo-skill/SKILL.md

$ python -c "... curator.history_skill(paths, 'demo-skill') ..."
commit d1db9a7  Revert "skill-curator: archive demo-skill"
commit 135804c  skill-curator: archive demo-skill
                Skill-Actor: developer/task-demo123
commit 7c50d05  skill-curator: create demo-skill
                Skill-Actor: developer/task-demo123
```

Every command above ran against `/private/tmp/.../scratchpad/wave2-demo`, a
git repo created and destroyed for this demonstration only — nothing in it
touched this checkout's own `.git` or `.claude/skills/`.

## Tests

`scripts/test_skill_curator.py` gained 18 tests for Wave 2, all against a
throwaway `tmp_path` git repo (`_make_paths()` now calls `_git_init()`,
which runs `git init` plus local-only `user.email`/`user.name`/
`commit.gpgsign=false` config — never the real checkout's git config):

- commit trailer content (`Skill-Actor: <role>/<session-id>`) for `archive`,
  `pin`+`unpin`, `create`
- a no-op mutation produces no commit
- `create` stamps identity + passes `skill-lint.py` with zero findings
- `create` refuses a colliding name and a path-traversal name
- identity falls back to `CEO/-` when no worker/C-level env is set
- `history` (with and without `--skill`), including for an archived skill
- `undo` reverses an `archive` and restores content byte-for-byte (the
  acceptance criterion, also reproduced live above); `undo` on a bad sha
  raises `CuratorError`
- `drift` is empty right after a commit, and detects a hand-edit

Existing invariant tests (symlink refusal, human-authored read-only, pinned
exemption, backup-before-mutation, archive/restore round-trip) all still
pass unchanged in intent — `_make_paths()` and the round-trip test's
sidecar-JSON assertion were updated to match the new frontmatter-based
storage, nothing else.

`scripts/test_skill_lint.py` is unchanged in count; `skill-lint.py` itself
gained two finding codes (6 `bad-pinned`, 7 `bad-lifecycle`) that existing
fixtures don't trigger (they never set those keys), so no existing
assertion needed to change.

`pytest`: **850 collected, 849 passed, 1 skipped, 0 failed** (≥835 required;
skip is pre-existing and unrelated to this task).

## What was wrong in the brief

Nothing load-bearing. Two small things worth flagging for whoever reads this
next:

- The brief's literal `git add -A --` framing (2.1) undersells one real
  edge case: `git add -A -- <path>` **fails** with "did not match any
  files" if `<path>` was never tracked by git in the first place and no
  longer exists on disk (e.g. archiving a skill that was only ever a
  filesystem write, never committed). In production this never happens —
  `.claude/skills/` has been git-tracked since Wave 0, so every real skill's
  old location is already tracked before any mutating verb ever runs on it.
  It **does** happen in a naive test fixture (`_write_skill()` alone never
  commits), so `_commit_skill_mutation()` treats that one specific failure
  shape as a no-op for that path rather than a hard error, instead of
  assuming every `touched` path is always already tracked.
- `_set_pinned()` writes `pinned: true` on `pin` but **deletes** the
  `pinned` key entirely on `unpin`, rather than writing `pinned: false`.
  The brief doesn't specify this either way; deleting is what makes "unpin
  a skill that was never pinned" a genuine no-op (matching the "no-op
  mutation commits nothing" behavior the ADR wants elsewhere), and it keeps
  `pin` → `unpin` byte-identical to before either ran, same symmetry
  `archive` → `restore` already has for `lifecycle`/`archived_at`.
