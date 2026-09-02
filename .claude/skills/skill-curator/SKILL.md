---
name: skill-curator
owner: CTO
origin: mooniex-org
scope: >-
  Tells a C-level when and how to run scripts/skill-curator.py — the ADR 0018
  lifecycle CLI (status/propose/archive/restore/pin/unpin). Does not run the
  CLI unattended (no daemon, ADR 0017) and does not build agent-authored skill
  creation (ADR 0018 §6, out of scope). For the raw usage dashboard (top-used,
  never-used, stale, cold) with no lifecycle state, see scripts/skill-report.py
  instead — that script is unchanged by this one.
created_by: human
description: Review skill telemetry and act on stale/unused skills without touching anyone else's repo. Trigger on /skill-curator, "curate skills", "archive unused skills", "skill lifecycle", "which skills are dead", or as a one-line nudge from /session-close when skills are proposed for archive.
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
python scripts/skill-curator.py status              # lifecycle table, read-only
python scripts/skill-curator.py propose              # what WOULD transition, and why — mutates nothing
python scripts/skill-curator.py archive <name>       # move to the archive dir (only created_by: agent)
python scripts/skill-curator.py restore <name>       # bring an archived skill back
python scripts/skill-curator.py pin <name>           # exempt from every future transition
python scripts/skill-curator.py unpin <name>         # undo pin
```

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
