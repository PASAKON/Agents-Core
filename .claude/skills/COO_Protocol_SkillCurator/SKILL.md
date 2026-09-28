---
name: COO_Protocol_SkillCurator
kind: protocol
owner: COO
aka: [skill-curator]
origin: mooniex-org
scope: >-
  Tells a C-level when and how to run scripts/skill-curator.py — the ADR 0018
  lifecycle CLI (status/propose/archive/restore/pin/unpin), plus create (ADR
  0022 Wave 2), notes and index. Does not run the CLI unattended (no daemon,
  ADR 0017). For the raw usage dashboard (top-used,
  never-used, stale, cold) with no lifecycle state, see scripts/skill-report.py
  instead — that script is unchanged by this one.
created_by: human
description: PROTOCOL — Review skill telemetry and act on stale/unused skills without touching anyone else's repo. Trigger on /COO_Protocol_SkillCurator, "curate skills", "archive unused skills", "skill lifecycle", "which skills are dead", or as a one-line nudge from /session-close when skills are proposed for archive.
audience: [cxo]
---

# Skill Curator — turn telemetry into a lifecycle

`scripts/skill-report.py` already tells you *what* is unused. This CLI is the
next step: it proposes what to *do* about it, and lets you act — without ever
risking another project's repo through a symlink.

## The ownership hazard, in one sentence

`~/.claude/skills/` holds skills we author (`Agents/.claude/skills/`, real
directories) alongside skills we merely *use* (symlinks into
`external/wondelai-skills`, `external/9arm-skills`, `external/marketingskills`,
`.agents/skills`, `mooniex-claude-skills`, …). The curator may only ever
mutate the former. It refuses anything that resolves through a symlink out of
`.claude/skills/`, and refuses anything not marked `created_by: agent` in its
frontmatter (absent means human — every skill written before this ADR is
protected automatically).

## When to run it

- A C-level wants to know what's dead weight in the always-loaded skill list
  (context budget — ADR 0015).
- `/session-close` surfaced "N skills proposed for archive" and you want the
  detail before acting.
- Periodically, as upkeep — there's no cron for this (ADR 0017: no daemon).
  Running it is a human decision, every time.

## Verbs

```
.venv/bin/python scripts/skill-curator.py status          # lifecycle table, read-only
.venv/bin/python scripts/skill-curator.py propose         # what WOULD transition, and why — mutates nothing
.venv/bin/python scripts/skill-curator.py archive <name>  # move to the archive dir (only created_by: agent)
.venv/bin/python scripts/skill-curator.py restore <name>  # bring an archived skill back
.venv/bin/python scripts/skill-curator.py pin <name>      # exempt from every future transition
.venv/bin/python scripts/skill-curator.py unpin <name>    # undo pin
.venv/bin/python scripts/skill-curator.py create <name> --kind <kind> --owner <C-level> --description "…" --audience <tokens>
                                                          # new org skill, lint-clean (ALL_Protocol_SkillAuthor §4)
.venv/bin/python scripts/skill-curator.py notes           # Field notes: pending / stale / contested per skill (ADR 0026)
.venv/bin/python scripts/skill-curator.py index           # rewrite docs/org/SKILL-INDEX.md (skill-lint code 16)
```

`.venv/bin/python`, not `python`: there is no `python` on PATH on Contabo, and a system `python3` without
`yaml` fails in a way that reads like "no findings" when grepped. `notes` reads only the first
`## Field notes` heading outside fenced code — skill-lint code 17 flags a second one. How a note line is
written and closed: ALL_Protocol_SkillAuthor §5 step 1.

`propose` is the default-safe verb — run it first, always. `archive` is the
only verb that touches a skill's files, and only ever an agent-authored one
that isn't pinned; it backs up before moving and is reversible via `restore`.

## Reading `propose` output

Output splits into two sections:

- **Proposed transitions** — `created_by: agent` skills the curator could
  actually archive. Anything an agent authored via `create` lands here; skills
  written by a human never do.
- **Informational only** — everything else that looks stale or never-used but
  is human-authored (or absent `created_by`, which defaults to human). The
  curator will never propose *archiving* these; if one genuinely needs
  cleanup, that's a manual `git rm`, not a curator action.

Never skip straight to `archive` on a name you saw in `propose` — re-run
`propose` first if time has passed. Lifecycle state is derived from
`state/skill-usage.log` (append-only, written by `hook-skill-log.py`) plus each
skill's own **frontmatter** (`pinned`, `created_by`, `audience`). The old
`state/skill-usage.json` sidecar was deleted in Wave 2 — it had never once been
written, and pin state now lives with the skill it protects.

## What this skill does not do

- Does not decide *what* a skill should say. `create` scaffolds a compliant,
  stamped skill; the content is the caller's judgement.
- Does not touch anything outside `.claude/skills/` in this repo — no
  `external/*`, no plugin marketplaces, no `~/.claude/skills/` symlinks
  themselves.
- Does not run on a schedule. If you want the "N proposed for archive" nudge,
  that's `/session-close` calling `propose` at close time, not this CLI
  running unattended.

## Field notes

- 2026-09-22 [MISSING] §Verbs — nothing listed pending / stale / contested Field notes across the portfolio, so `notes` was added · evidence: session cto-0e8d80b8, ADR 0026 · status: promoted
- 2026-09-25 [MISSING] §lint — the field-note lint rejects an annotated status (`status: promoted (CEO ruling 2026-09-25)`) even though the promotion needs its ruling recorded; write `status: promoted` bare and put the ruling inside the note text (three notes flagged today: CTO_Gate_MergeChecklist:119/130, session-save:174) · evidence: task-a40d2d8e Skill learning, skill-lint output 2026-09-25 22:5x; still true 2026-09-28 (`parse_field_notes` wants ` · status: <word>` at line end) → ALL_Protocol_SkillAuthor §5 step 1, the note format's owner (1cf93ed0); pointer in §Verbs · status: promoted
- 2026-09-28 [MISSING] §notes — `skill-curator.py notes` cuts names to 32 characters, so a verify grep on a full name (`BROWSER_OPERATOR_Protocol_Playbook`) matches nothing; widen the column or grep the prefix · evidence: fold worker, session 14cc900f → fixed in the tool: the column is sized to the longest name (fa93b382, test_notes_verb_prints_long_skill_names_whole) · status: promoted
- 2026-09-28 [MISSING] §notes — `skill-curator.py notes` (and skill-lint code 8) read only the FIRST `## Field notes` section, so a second heading hides every note under it: CXO_Protocol_DevSpawn showed 16 pending while the file held 48 · evidence: `field_notes_section` stops at the next `## ` line; fold worker ac30624b, session 14cc900f; lint code 17 now flags a second heading (a33e6258) → §Verbs · status: promoted
- 2026-09-28 [WRONG] §notes — `field_notes_section` also matched `## Field notes` inside fenced code, so ALL_Protocol_SkillAuthor's §9 templates stood in for its real Field notes and neither code 8 nor `notes` read them; the finder now skips fenced code, and lint code 17 flags a second real heading → fixed in the tools · evidence: a33e6258, scripts/test_skill_curator.py::test_field_notes_section_skips_headings_inside_code_fences · status: promoted
