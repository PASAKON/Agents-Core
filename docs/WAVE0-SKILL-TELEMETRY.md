# Wave 0 — Skill Usage Telemetry Fix

Fixes three live defects in `state/skill-usage.log` telemetry
(org:decisions/0022-skill-governance-visibility-authorship-audit.md,
org:playbooks/skill-governance-implementation.md §Wave 0). Wave 0 only — no
other wave touched.

## The defect (0.1)

`scripts/hook-skill-log.py` computed its log path as
`Path(__file__).resolve().parent.parent / "state" / "skill-usage.log"`. From a
git worktree, `__file__` is the **worktree's own copy** of the script, so
every worker's skill fire landed in `worktrees/<...>/state/skill-usage.log`
instead of the main repo. That file dies when the worktree is reaped or
merged. Separately, worktrees of *other* repos (mooniex-claudeflow,
comfy-runpod-worker, ...) carry no `.claude/settings.json` at all, so the hook
never ran there and those fires were lost entirely.

`scripts/hook-skill-log.py` now honours an `ORG_SKILL_LOG` env var (absolute
path) when set, falling back to the old worktree-relative behavior otherwise.
The fix only takes effect once the block below is registered at the
**user level** (`~/.claude/settings.json`) — that scope is per-machine, not
per-repo, so it is the only registration that reaches every worktree of every
repo, including the cross-repo ones with no project settings file at all.

**A worker or C-level cannot write `~/.claude/settings.json` itself** — the
permission classifier blocks agent writes to it (verified this session,
twice). A human (the CEO) has to paste this in by hand.

## CEO paste block — Mac

Target file: `~/.claude/settings.json` on the Mac (this is where the CEO's
own interactive sessions and every Mac-side worker/C-level spawn run).

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "ORG_SKILL_LOG=/Users/gob/MoonieXHQ/Agents/Core/state/skill-usage.log python3 /Users/gob/MoonieXHQ/Agents/Core/scripts/hook-skill-log.py"
          }
        ]
      }
    ]
  }
}
```

### Backup, then merge with jq

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak-$(date -u +%Y%m%dT%H%M%SZ) 2>/dev/null

[ -f ~/.claude/settings.json ] || echo '{}' > ~/.claude/settings.json

jq '.hooks.PostToolUse = ((.hooks.PostToolUse // []) + [{"matcher":"Skill","hooks":[{"type":"command","command":"ORG_SKILL_LOG=/Users/gob/MoonieXHQ/Agents/Core/state/skill-usage.log python3 /Users/gob/MoonieXHQ/Agents/Core/scripts/hook-skill-log.py"}]}])' ~/.claude/settings.json > ~/.claude/settings.json.tmp && mv ~/.claude/settings.json.tmp ~/.claude/settings.json
```

The `cp` line is a no-op (silently skipped) if `~/.claude/settings.json`
doesn't exist yet. The jq line **appends** a new array element to
`.hooks.PostToolUse` — it does not touch any other key, and does not remove
whatever hooks are already registered there (e.g. other plugin/ECC hooks).

### CEO paste block — Contabo VPS

Same registration, different absolute paths, done separately on the VPS's own
`~/.claude/settings.json` (a completely different file on a different
machine — this repo lives at `/opt/mooniex-agents` there, per this repo's own
root `CLAUDE.md`):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "ORG_SKILL_LOG=/opt/mooniex-agents/state/skill-usage.log python3 /opt/mooniex-agents/scripts/hook-skill-log.py"
          }
        ]
      }
    ]
  }
}
```

Same `cp` + `jq` steps as above, run on the VPS, with `/opt/mooniex-agents`
substituted for `/Users/gob/MoonieXHQ/Agents/Core`.

## Which key, replace or add?

The paste goes under `.hooks.PostToolUse` in `~/.claude/settings.json` — a
**different file** from this repo's own `Agents/.claude/settings.json`. It
**adds** a new array element to `~/.claude/settings.json`'s own
`hooks.PostToolUse` (creating the whole `hooks.PostToolUse` path if that user
settings file has no hooks yet). It does **not** replace, touch, or remove
the `PostToolUse` → `Skill` entry already registered in this repo's
`.claude/settings.json` (read before writing this doc — that file has exactly
one `PostToolUse` block, matcher `Skill`, running
`python3 "${CLAUDE_PROJECT_DIR:-$PWD}"/scripts/hook-skill-log.py` with no env
override). Both files, both entries, stay active at once after the paste.

## Does that mean double logging?

**Yes, but only for a session running directly in the main repo checkout**
(e.g. a CTO/CEO session at `/Users/gob/MoonieXHQ/Agents/Core` itself, not a
worktree). There, the project-level entry's old default
(`${CLAUDE_PROJECT_DIR}/scripts/hook-skill-log.py`, no `ORG_SKILL_LOG`) still
resolves its worktree-relative fallback to the *same* file the new user-level
entry targets (`state/skill-usage.log` next to the main checkout). Both hooks
fire per `Skill` call, both append a line → every fire from a non-worktree
session gets counted twice in `skill-report.py`'s totals.

For a **worktree** session of this repo, there's no double-count in the main
log specifically: the project-level entry still strands its line in that
worktree's own local `state/skill-usage.log` (same bug as before, just
now redundant since the user-level entry already wrote the correct copy to
the shared log) — harmless to the aggregate numbers, but it does mean the
stray-file problem this task was asked to fix keeps recurring and would need
another 0.2-style sweep periodically if the project-level entry stays.

**Recommendation: remove the project-level entry** (the `PostToolUse` →
`Skill` block in this repo's `.claude/settings.json`) once the CEO confirms
the user-level paste is live (fire any skill, `tail -1 state/skill-usage.log`
in the main repo, confirm one new line). This is deliberately **not** done in
this task/PR: removing it now, before the CEO has pasted the user-level
block, would go completely dark on skill telemetry in the gap between merge
and paste — that's exactly what the `ORG_SKILL_LOG` fallback in
`hook-skill-log.py` is belt-and-braces against (it keeps today's behavior,
imperfect but present, until the real fix is registered). Removing the
project-level entry is a one-line follow-up PR/commit to
`.claude/settings.json`, not a `~/.claude/settings.json` paste, so it can't be
bundled into the same clipboard action above — track it as a fast follow-up
once the CEO confirms the paste is working.

## Recovery (0.2) — already run once, this session

Command (run once, from `/Users/gob/MoonieXHQ/Agents/Core`, **not** wrapped in a
script per the task brief):

```bash
cat worktrees/*/state/skill-usage.log >> state/skill-usage.log \
  && sort -u -o state/skill-usage.log state/skill-usage.log
```

Measured counts (2026-09-01, this session):

| | count |
|---|---|
| Main repo log, before | 424 lines |
| Stranded worktree files found | 38 files |
| Stranded lines, total | 79 lines |
| Stranded lines, unique (`sort -u`) | 79 (no dupes among themselves) |
| Main repo log, after | **503 lines** (424 + 79, exact) |
| Duplicate lines after merge (`sort \| uniq -d`) | **0** |

A timestamped backup of the pre-recovery log was taken and deleted after the
503/0-dupes result was verified. All 503 lines are still 3-field TSV — the
recovered fires predate the role column below, same as the rest of the
pre-existing log.

## Role column (0.3)

`scripts/hook-skill-log.py` now writes 4 TSV fields instead of 3:

```
<ISO timestamp>\t<skill name>\t<session id>\t<role>
```

Role resolution, in order: `WORKER_ROLE` env var (already exported by
`runners/worker_init.py` for every worker — no change needed there), then
`CXO_ROLE` (already exported by `scripts/cxo-claude.sh` for every C-level
role, and by `scripts/cto-claude.sh` which sets `CXO_ROLE=cto`), then `-` if
neither is set.

**Deviation from the literal task text, done deliberately:** the brief said
to "export `WORKER_ROLE`... in `scripts/cto-claude.sh`, `scripts/cxo-claude.sh`"
but also said to reuse an existing name rather than introduce a second source
of truth. Reading those two scripts, `CXO_ROLE` already carries exactly this
fact for every C-level session — exporting a second `WORKER_ROLE` var there
would be the second source of truth the brief warned against, so
`hook-skill-log.py` reads `CXO_ROLE` as its fallback instead, and neither
shell script was touched. A C-level session with no role at all (bare
`claude`, not launched through the org's launchers) still legitimately
records `-`, as the brief specifies.

Both readers (`scripts/skill-report.py`, `scripts/skill-curator.py`) were
updated to parse the 4th field, padding it to `-` for the existing 3-field
legacy lines rather than crashing — verified against a mixed-width fixture in
`scripts/test_hook_skill_log.py` and `scripts/test_skill_curator.py`.

## Demonstration

`scripts/test_hook_skill_log.py::test_main_writes_to_org_skill_log_from_inside_a_worktree_copy`
reproduces the exact bug scenario end-to-end: the hook script is copied into a
fake worktree tree (so its own `__file__`-derived default would strand the
fire there), `ORG_SKILL_LOG` is set the way the paste above sets it, and the
test asserts the fire lands in the shared log — not the worktree's stray
copy — with all 4 fields populated including the worker's role.
