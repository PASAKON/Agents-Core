# Wave 4 — skill audit + objections

Companion to ADR 0022 (`org:decisions/0022-skill-governance-visibility-authorship-audit.md`)
§5/§6 and `org:playbooks/skill-governance-implementation.md` Wave 4. Records
the column definitions, the session-id join finding, and why objections are
signal while task outcome is smoke.

## 4.1 — `scripts/skill-report.py` columns

| Column | Definition | Source |
|---|---|---|
| `/wk` | `count / weeks_since_first_fire`, where `weeks_since_first_fire` is floored at `1.0` week. Measured from **that skill's own first fire** (`_first_fires()`), not the log's global start — a skill added last week does not look dead next to one added in June. The 1-week floor stops a skill fired 3× in its first hour from reporting an absurd instantaneous rate. | `_first_fires(entries)` + `_fires_per_week()` |
| `updated` | `git log -1 --format=%cI -- <skill_dir>/SKILL.md`, run with `cwd=skill_dir` so a symlinked skill (e.g. `~/.claude/skills/browser-operator -> this repo`) resolves through the symlink to the real repo before git runs. Verified live against the real portfolio (see below) — every owned skill in the top-20 printed `updated` correctly. | `_git_updated_at()` |
| `obj` | `open/total` from `tools/skill_objection.py`'s `summary(days=30)`. `open == total` always — see §4.2/4.3 below for why. | `_objection_summary()` |

`_skill_locations()` replaces the old name-only `_discover_skills()` as the
single source of skill→path resolution (that function now derives its
return value from this one). `tools/skill_objection.py` reuses it via the
same dynamic hyphenated-filename import `scripts/skill-curator.py` already
uses for this file, instead of re-walking the owned/user/plugin trees a
third time.

### `--brief`

Prints **zero bytes** when there is nothing to report — `never_used` skills
never count as "something to report" (see §4.4). Demonstrated live:

```
$ python scripts/skill-report.py --brief        # against the real 507-line log (18 stale)
  skill-report: 18 stale — run scripts/skill-report.py for detail

$ python scripts/skill-report.py --brief         # against an empty log, zero objections
$                                                 # <- zero bytes, exit 0. Confirmed programmatically:
#   bytes printed: 0
#   exit code: 0
```

### Worktree log folding

`_iter_log_lines()` folds `state/skill-usage.log` with every
`worktrees/*/state/skill-usage.log`, deduped by raw line, before
`_load_log()` parses anything. This is belt-and-suspenders per ADR 0022 §5 —
Wave 0 already fixed the hook to log to the main repo directly; this is what
keeps the report honest if that registration ever regresses again.

### Verified against the real log

`state/skill-usage.log` is 508 lines (504 legacy 3-field, 4 new 4-field) as
of this task. `scripts/skill-report.py` (no args) rendered all 20 top-used
rows plus stale/cold/never-used sections without crashing on the legacy
lines: `available=292 used=49 never_used=266 total_fires=507 stale=18
open_objections=0`.

## 4.2 — `tools/skill_objection.py`

`raise_objection(skill, conflict, did_instead, blocked=False)` resolves the
author from `skill`'s frontmatter (`author.role`, absent → `cto`), writes one
`skill_objection` event via the existing `db.log_event` (no schema change),
and adds one LungNote to-do addressed to that role via
`scripts/lib/mcp_call.py` (fail-open — a LungNote outage never blocks the
durable DB event, proven by
`test_raise_objection_completes_when_lungnote_is_down`).

`summary(days=30)` and `list_objections(limit)` back the CLI's `summary`/
`list` verbs and the `obj` column. **No `resolve` verb** — completing the
LungNote to-do is the resolution (ADR 0017: a human runs that verb).

Wired as `mcp__org__skill_objection` on `runners/worker_mcp_server.py`, with
the matching grant added to `_BASE_WORKER_TOOLS` — **that constant lives in
`runners/worker_init.py`, not `worker_mcp_server.py`** (the task brief named
the wrong file; see "Brief corrections" below).

## 4.3 — the session-id join (verified, not assumed)

`state/skill-usage.log` column 3 is the raw Claude **session UUID**
(`event["session_id"]` from the PostToolUse hook), not a task id. Checked
read-only against the real `state/tasks.db` and the real log:

| Target | Matches | Notes |
|---|---|---|
| `tasks.session_id` | **58 / 240** (24%) | worker/DEV sessions — a real fire's session id lands directly on the task row it ran under |
| `c_level_sessions.session_id` | **0 / 240** | different namespace: this column holds the short 8-char tmux id, never the full Claude UUID |
| `c_level_sessions.resume_uuid` | **9 / 240** | only populated when a CXO session is closed through the lifecycle tooling |
| **any of the above** | **67 / 240 (~28%)** | |

Sample confirmed match: session `03bd0cbd-504f-4f76-acc7-05a0f88e998c` →
`task-036de9ea` (`browser_operator`, `status=done`).

**The join works, but only covers ~28% of logged fires, dominated by
worker/DEV sessions.** C-level (CTO/CFO/CMO/CGO) fires are essentially
unjoinable today because `c_level_sessions.session_id` is a different id
space than the log's session column, and `resume_uuid` only backfills on a
clean session close. Task-outcome smoke (§4.4/playbook 4.4) is therefore
**not implemented as a column** — reporting it only for the joinable ~28%
and silently dropping the rest would look like a defect rate over the whole
portfolio when it is really a defect rate over "worker sessions that
happened to close cleanly." Per the brief: say so and stop, rather than
ship a correlation that cannot be computed honestly.

## 4.4 — objections are signal, task outcome is smoke

**Objections are the signal.** They are a human-or-agent judgement that a
skill was actually wrong, and they are the only true *outcome* measure
either this system or Hermes has. Hermes measures whether a skill was
*opened*, never whether it *worked* — every one of its counters sits inside
a success gate.

**Task outcome is smoke, not signal**, for the reason in §4.3: the join that
would connect a fire to its task's terminal status only resolves for ~28%
of fires, so a "task X failed after firing skill Y" correlation would be
computed over a biased subsample and silently misrepresented as portfolio-
wide if shipped as a column. Not built this wave.

**Silence alone must never be sufficient to archive a skill** — adopted
verbatim from Hermes' own curator ("'use=0' is not evidence a skill is
valuable; it's absence of evidence either way"). Encoded as
`test_silence_alone_never_archives_a_skill` in
`scripts/test_skill_objection.py`: a skill with zero fires and no git
history to judge it by gets **no proposal at all** from the real,
unmodified `scripts/skill-curator.py` logic — not "stale", not "archived" —
because there is no basis to judge it. `scripts/skill-report.py` mirrors
this in its own `--brief`/dashboard output: `never_used` skills get their
own explicitly-labeled, non-alarming section and never trigger `--brief`'s
one-line summary on their own.

## Brief corrections found while implementing

Every DEV on this ADR so far has found at least one error in the brief it
was handed. This wave's:

1. **`_BASE_WORKER_TOOLS` lives in `runners/worker_init.py:55`, not
   `runners/worker_mcp_server.py`.** The brief said "One MCP tool on
   `runners/worker_mcp_server.py` ... plus the matching `_BASE_WORKER_TOOLS`
   grant in the same commit" as if both lived in the same file. They don't —
   `worker_mcp_server.py` only defines the `@mcp.tool()` functions;
   `worker_init.py` is what builds the `claude` CLI's `--allowed-tools`
   argv. `runners/worker_init.py` was not in this task's declared
   `touches`, so `self_repo_guard` refused the edit; reported to the CTO via
   `dev_message` requesting the touch be added.
2. **`scripts/test_send_to_cto.py` does not monkeypatch `db.DB_PATH`** — it
   isolates `lib.mailbox.INBOX_ROOT` / `tools.agent_transport.LOCKS_DIR` /
   `tools.send_to_cto.STATE_DIR` instead, none of which touch the task
   queue. `scripts/test_dev_message.py` is the file that actually does
   `monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")`, and is
   the pattern `scripts/test_skill_objection.py` follows.
3. **`config/worker.mcp.json` (committed, not generated) hardcodes
   `/Users/gob/Projects/Agents`** in the `org` and `lungnote` server
   entries' `command`/`args`/`cwd` — the exact hard-constraint-1 violation
   this task was told to avoid introducing, except it already exists
   upstream of anything this wave touches. On Contabo
   (`/opt/mooniex-agents`) this would make every worker's `org` + `lungnote`
   MCP servers fail to spawn. Out of scope for Wave 4 (not named in §4.1–
   4.4, and `runners/worker_init.py`/`config/` were not in this task's
   `touches`) — flagging for a follow-up rather than fixing silently.

## Test coverage

`scripts/test_skill_objection.py`, 12 tests: `raise_objection` writes exactly
one event and one LungNote to-do addressed to the resolved author; absent
`author:` → `cto`; a LungNote outage never blocks the DB write;
`summary()`/`list_objections()` ordering and windowing; the silence-never-
archives invariant; `ROOT` is derived, not hardcoded (hard constraint 1).

`pytest`: **864 passed, 1 skipped** (baseline 853 — no regressions).
