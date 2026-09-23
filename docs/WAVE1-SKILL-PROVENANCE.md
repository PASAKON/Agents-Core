# Wave 1 — Skill Provenance (frontmatter contract + lint + pre-commit)

Implements ADR 0022 §3 and the playbook's Wave 1
(`org:decisions/0022-skill-governance-visibility-authorship-audit.md`,
`org:playbooks/skill-governance-implementation.md`). Wave 1 only — no Wave 2,
3, 4, or 5 work is included. Builds on Wave 0 (merged, sha `308bbf1`).

## 1.1 — The frontmatter contract

| Key | Values | Notes |
|---|---|---|
| `audience` | list of role keys from `policies/agents.yaml`, or the group tokens `all` / `cxo` / `worker` | who the skill is FOR — the routing key Wave 3 will read |
| `created_by` | **exactly** `human` or `agent` | the curator's gate depends on this staying a two-value enum |
| `author` | `{role: <role>, date: <ISO date>}` | the rich stamp. **Lazy** — see below |
| `improved_by` | list, optional, append-only | for Wave 4's objection loop |
| `aka` | list, optional | preserves telemetry across a future rename |

Existing keys (`name`, `description`, `owner`, `origin`, `scope`) were left
exactly as they were on every file — `created_by` and `audience` were
appended immediately before the closing `---`, nothing reordered.

`author:` was **not** added to any of the 21 backfilled skills. It's lazy by
design (a skill gains it the next time someone with real authorship
information edits it) and this task has no way to source who actually wrote
each of the 21 — inventing it would be exactly the kind of unsourced claim
the brief warned against. Objections on an un-authored skill route to its
`owner:` field, same as before.

## Group tokens, derived at runtime — never hardcoded

`scripts/skill-lint.py:load_role_groups()` reads `policies/agents.yaml` and
computes three sets from `roles.<key>.{model, level}`:

- **`all`** — every role whose `model` is not `null` (i.e. every role that
  can actually run a Claude session).
- **`cxo`** — of those, the ones with `level: c`.
- **`worker`** — of those, the ones with `level: w`.

`ceo` has `level: c` but `model: null` ("the user — no LLM" — a skill can
never run inside a CEO session, since CEO never runs one), so it is excluded
from every group by a *property test* (has a model), not by hardcoding the
string `"ceo"`. This derivation was verified against the real
`policies/agents.yaml` and produces `cxo == {cto, cfo, cgo, cmo}` — which
matches, verbatim, what two real skills already say in their own text
(`session-change-model`: "Shared by CTO/CFO/CGO/CMO"; `higgsfield-unlimited-gen`:
"any C-level (CTO, CMO, CFO, CGO)"). `config/agents.yaml` does not exist and
was not created — `policies/agents.yaml` is the only source, per the task's
hard constraint.

## 1.2 — `scripts/skill-lint.py`

New file. `python scripts/skill-lint.py check [--json] [--skills-dir DIR]`.
Five finding codes, exactly as specified:

1. missing `SKILL.md`
2. unparseable frontmatter
3. `name` != directory basename
4. `created_by` outside `{human, agent}`
5. `audience` token not a known role or group

Reuses `skill-curator.py`'s `_resolve_within()` / `CuratorError` (imported by
path, same pattern `skill-curator.py` already uses to reuse
`skill-report.py`'s `_discover_skills()`) for the symlink refusal, rather than
a second implementation. A symlink directly under `.claude/skills/` — even
one that points *inside* `.claude/skills/`, not just one escaping it, since
that's what the curator itself refuses — is reported separately as
`refused`, never linted, never crashes the run. This was exercised against
**real repo state**, not only a fixture: `.claude/skills/ai-video-storyboard`
is a genuine pre-existing symlink (an external import, not one of the 21
owned skills), and it shows up as `refused` on every real run.

**Exit code reflects `findings` only, not `refused`.** A refused symlink was
never an owned skill to begin with — `skill-curator.py`'s own `status`/`propose`
scan silently excludes symlinks the same way (`_scan_skill_dir` filters
`is_symlink()` out before the caller ever sees them). Making `refused` count
toward exit status would mean `check` could never exit 0 on this repo as it
stands today, which isn't what "clean" should mean.

**This is a lint, not a gate**: exiting non-zero on a real finding is fine
(that's what makes `check` useful in CI or by hand); it never refuses to
write a skill, and it carries no `--strict` flag or other mode a future
caller could wire into a gate — `scripts/test_skill_lint.py::test_cli_has_no_strict_flag`
asserts that surface stays absent, not just that today's call doesn't use it.

### The silent-coercion fix (`skill-curator.py:_created_by`)

Behavior is unchanged — an invalid `created_by` still coerces to `"human"`,
fail-closed, same as before. What changed: a **present but invalid** value
now prints a `WARNING:` line to stderr naming the file and the bad value,
before returning. Absent `created_by` (the normal case for every
pre-ADR-0022 skill) still warns nothing — only a value that's actually wrong.

Demonstrated live during this task with the exact fixture value the brief
names:

```
$ python scripts/skill-lint.py check --skills-dir /tmp/fixture/.claude/skills
[4] bad-created-by: bad-skill: created_by='cto' is not 'human' or 'agent' (a role belongs in author:, never here -- ADR 0022 section 3)

$ python -c "... curator._created_by(Path('/tmp/fixture/.claude/skills/bad-skill')) ..."
WARNING: /tmp/fixture/.claude/skills/bad-skill/SKILL.md: created_by='cto' is not 'human' or 'agent' -- coercing to 'human' (see ADR 0022 section 3: the role belongs in author:, never in created_by)
_created_by() returned: human
```

Both are covered as pytest fixtures too:
`scripts/test_skill_lint.py::test_role_valued_created_by_is_code_4` and
`scripts/test_skill_curator.py::test_created_by_role_value_warns_on_stderr_but_still_coerces_to_human`.

## 1.3 — Pre-commit wiring

**New tracked file: `scripts/install-git-hooks.sh`.** No tracked installer
existed for the pre-commit hook before this task — the repo's gitleaks guard
(added 2026-07-20) had been hand-placed directly in `.git/hooks/pre-commit`,
which is itself untracked (`.git/hooks/` is never committed by git). On a
fresh clone, neither the gitleaks guard nor a skill lint would exist until
someone ran an installer — this script is that installer, for both.

**Install with:**

```bash
sh scripts/install-git-hooks.sh
```

Idempotent (marker-guarded, safe to re-run), and resolves the shared
`.git/hooks/` directory via `git rev-parse --git-common-dir` rather than a
hardcoded repo path — works identically from the main checkout or any
worktree, and on the Mac (`/Users/gob/MoonieXHQ/Agents/Core`) or Contabo
(`/opt/mooniex-agents`) alike.

The hook it writes runs `scripts/skill-lint.py check` **only when staged
paths touch `.claude/skills/`**, and never blocks the commit (`|| true`) —
CEO decisions 4 and 10 forbid an authoring gate in any form, and a blocking
pre-commit hook is a gate wearing a different hat.

### Three real bugs found and fixed while wiring this, not theoretical

1. **The original hand-written gitleaks hook ends with a bare `exit 0`.**
   Appending anything after that line makes it dead code — git never reaches
   it. The installer now strips a trailing standalone `exit 0` before
   appending a new stanza (every run, not just first install) and re-adds one
   final `exit 0` at the very end, so ordering never matters again.
2. **`command -v gitleaks >/dev/null 2>&1 || exit 0` (the original form) also
   kills the whole script**, not just the gitleaks check, on any machine
   without `gitleaks` on PATH — which would have silently disabled
   skill-lint too on a fresh Contabo clone before `gitleaks` is installed
   there. Rewritten as `if command -v gitleaks; then ... fi` — same behavior
   when gitleaks is present, independent of sibling stanzas when it isn't.
3. **`.venv` and `scripts/skill-lint.py` do not live at the same root when a
   worktree is committing.** `.venv` is gitignored and exists only in the
   main checkout; `scripts/skill-lint.py` must come from **the worktree
   actually being committed** (it can be on a branch whose `.claude/skills/`
   or lint tool differ from main's — that's the content actually being
   staged). The hook now resolves these two roots separately: the script via
   `git rev-parse --show-toplevel`, the Python interpreter via
   `git rev-parse --git-common-dir`'s parent. Verified end-to-end by staging
   a real skill change in this worktree and running the live hook directly —
   see Demonstration below.

Bare `python3` is never used for the lint step — only `.venv/bin/python` if
it exists (hard constraint #4: bare `python3` has no PyYAML). If `.venv` is
missing, the stanza silently no-ops, same failure style as gitleaks' own
`command -v` guard.

### Demonstration (this session, this worktree)

```
$ sh scripts/install-git-hooks.sh
installed: gitleaks guard stanza
installed: skill-lint stanza
pre-commit hook ready: /Users/gob/MoonieXHQ/Agents/Core/.git/hooks/pre-commit

$ git add .claude/skills/browser-operator/SKILL.md
$ sh "$(git rev-parse --git-common-dir)/hooks/pre-commit"
...no leaks found...
[refused] ai-video-storyboard: ... (informational, not a finding)
0 findings -- clean. 1 refused entry ...
$ echo $?
0

$ git add scripts/install-git-hooks.sh   # a non-skill path
$ sh "$(git rev-parse --git-common-dir)/hooks/pre-commit"
...no leaks found...                      # skill-lint did not run at all
$ echo $?
0
```

Both staged sets were `git reset` back afterward — nothing from this
demonstration was committed as part of it.

## 1.4 — Backfill

**Correction to the task brief: the real count is 21 org skills, not 22.**
`scripts/skill-curator.py::_scan_skill_dir(owned_skills_dir)` — the same
function the curator itself uses to enumerate owned skills — returns exactly
21 real directories under `.claude/skills/` on this branch (post Wave-0
merge, sha `308bbf1`). `ai-video-storyboard` is a **symlink** there (into an
external skills source), which is why it's correctly excluded from that
count — same as it's excluded from the curator's own `status`/`propose`
scan. The ADR's "22" and "1 of 22 carries `created_by`" figures were most
likely a snapshot taken at a different point in time (possibly before or
independent of Wave 0's merge); this task backfilled all **21** real skills.
`skill-curator` was the one that already carried `created_by: human` — it
only needed `audience:` added.

**Also incorrect in the brief: "5 have no `owner`" — the real count is 4.**
Measured directly (`grep -m1 '^owner:'` across all 21): 15 skills have
`owner: CTO`, 2 have `owner: CFO` (`gdrive-filing`, `mooniex-finance`), and 4
have no `owner` field at all (`ai-film-production`, `blender-previz`,
`browser-operator`, `higgsfield-unlimited-gen`). 15 + 2 + 4 = 21.

**One pre-existing YAML bug fixed as a side effect:**
`higgsfield-unlimited-gen/SKILL.md`'s `description:` was an unquoted plain
YAML scalar containing a literal `): follow` — a bare colon-space inside an
unquoted scalar is invalid YAML (confirmed: `skill-lint.py` reported it as
finding code 2, unparseable frontmatter, on the very first real run, before
any backfill). Reformatted as an equivalent `>-` folded block scalar with
**identical text**, no content change — this is a syntax fix, not the "bulk
rewrite of skill bodies" the brief says not to do. Whether this bug ever
affected anything else (Claude Code's own skill loader, `skill-curator.py`'s
`_read_frontmatter`, which silently swallows a `YAMLError` into `{}`) wasn't
investigated further — out of scope for this task, flagged here for whoever
next touches that file.

### The 21-skill audience table

Read each skill's actual content, not its name or `owner:` field (the
"owner is not audience" trap the brief warned about, measured against
15×CTO / 2×CFO / 4×none — a mechanical `owner → audience` mapping would have
mis-stamped nearly every skill in the repo).

| Skill | `audience` | Reason |
|---|---|---|
| `ai-film-production` | `cxo` | Description: "whenever a C-level is directing" a film — generic, not restricted to one C-level |
| `blender-previz` | `all` *(needs human decision — see below)* | No `owner:` field, no role named anywhere in the body; only "the CEO approves," which is approval, not driving |
| `browser-operator` | `browser_operator` | Description names "the org's `browser_operator` role" verbatim |
| `cto-merge-checklist` | `cto` | `owner: CTO`; body titled "# CTO Merge Checklist"; gates `merge_task`, which CTO runs in this repo |
| `dev-spawn-protocol` | `cto` | Description: "Required steps when CTO spawns a DEV agent" |
| `gdrive-filing` | `cxo` | `owner: CFO`, but rules apply to whichever C-level session the CEO asks to file something — not restricted to CFO in the trigger phrases |
| `higgsfield-unlimited-gen` | `cto, cmo, cfo, cgo` | Body states verbatim: "Gives any C-level (CTO, CMO, CFO, CGO)" |
| `mooniex-finance` | `cfo` | `owner: CFO`; description names "CFO" explicitly; org finance authority |
| `session-change-model` | `cxo` | Scope states verbatim: "Shared by CTO/CFO/CGO/CMO" |
| `session-close` | `cxo` | Generic C-level session exit gate (IRON §35); same `/session-*` family as `session-change-model`'s explicit sharing |
| `session-list` | `cxo` | Description: "List past CTO/CXO sessions" |
| `session-merge` | `cxo` | Generic cross-session context carry for any C-level chat |
| `session-open` | `cxo` | Generic session charter (IRON §35) for any C-level session |
| `session-restart` | `cxo` | Rebuilds "a C-level chat's" tmux+claude stack; same family as `terminal-open`/`terminal-restart` |
| `session-save` | `cxo` | Parks "this session" for any C-level; generic `/session-*` family |
| `session-worktree` | `cxo` | Work-breakdown recap for whichever C-level session runs it |
| `skill-author` | `all` | ADR 0022 explicitly opens skill authorship to every role with no pre-approval; the body itself names no role restriction and addresses a generic "user" |
| `skill-curator` | `cxo` | Scope states verbatim: "Tells a C-level when and how to run scripts/skill-curator.py" |
| `spawn-web-designer` | `cto` | Scope contrasts this CEO-driven path directly against "the CTO autonomous route"; boots the surface from the CTO chat that talks to the CEO |
| `terminal-open` | `cxo` | Description: "Bring back the Mac iTerm window for a C-level chat" |
| `terminal-restart` | `cxo` | Same iTerm/tmux/claude stack family as `terminal-open`/`session-restart`, for any C-level session |

### Audience needs a human decision

- **`blender-previz`** — genuinely unclear. Unlike every other skill in this
  repo, it has no `owner:` field *and* no role is named anywhere in its body
  — only "the CEO approves every generation," which is an approval gate, not
  a statement of who drives the Blender/SSH tooling itself. Set to `all` as
  the honest default rather than guessing `cto` from the pattern that every
  *other* technical tool in this repo happens to be CTO-owned (exactly the
  kind of inference the brief said not to make). **CTO: please settle
  whether this should be `cto`-only, or genuinely `all`.**

No other skill was ambiguous enough to need this — the rest each had
explicit or near-verbatim textual evidence (quoted in the table above) for
their assignment.

## Tests

`scripts/test_skill_lint.py` (new, 30 tests) covers all five finding codes
independently, symlink refusal (including a symlink pointing *inside* the
owned dir, not only one escaping it), role/group derivation from both the
real `policies/agents.yaml` and a synthetic fixture, root-derivation
portability (copies the tool to a throwaway directory that is neither
`/Users/gob/MoonieXHQ/Agents/Core` nor `/opt/mooniex-agents` and asserts it tracks
its own new location), the CLI end-to-end (`check`, `--json`,
`--skills-dir`), and that no `--strict` flag exists.

`scripts/test_skill_curator.py` gained 3 tests for the `_created_by` warning
fix (role value warns + still coerces; valid values never warn; absent value
never warns) — added there rather than to `test_skill_lint.py`, since they
exercise `skill-curator.py`'s own function and the existing file is already
organized by curator invariant.

## Acceptance checklist

- [x] `python scripts/skill-lint.py check` — 0 findings across all 21 real
      skills (1 informational `refused` entry for the pre-existing
      `ai-video-storyboard` symlink, which does not affect exit code)
- [x] Deliberate `created_by: cto` fixture — lint catches it (code 4), curator
      warns instead of coercing silently (demonstrated above + tested)
- [x] Symlink under `.claude/skills/` is refused, consistent with the curator
      (demonstrated against real repo state, not just a fixture)
- [x] Pre-commit path survives a fresh clone — tracked installer
      (`scripts/install-git-hooks.sh`), install line documented above
- [x] `pytest` — **821 passed, 1 skipped, 0 failed** (788 baseline + 33 new:
      30 in `test_skill_lint.py`, 3 in `test_skill_curator.py`)
- [x] This document
