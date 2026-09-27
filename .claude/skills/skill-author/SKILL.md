---
name: skill-author
kind: protocol
owner: COO
origin: mooniex-org
scope: >-
  How the org creates, updates, renames, splits and retires a skill: the seven kinds, the name, the
  frontmatter contract, step-by-step procedures, a body template per kind, and descriptions that fire.
description: PROTOCOL — Create, update, rename, split or retire an org skill — the 7 kinds, the <ROLE>_<Kind>_<Topic> name, step-by-step procedures and a body template per kind. Trigger on /skill-author and on "สร้าง skill", "อัปเดต skill", "เปลี่ยนชื่อ skill", "แยก skill", "create a skill", "write a SKILL.md". Not for imported public skills.
created_by: human
audience: [all]
improved_by:
  - {role: cto, date: "2026-09-27", what: "kinds, naming, create/update/rename procedures, templates (CEO rulings 2026-09-27)"}
---

# Skill Author — how the org makes and keeps a skill

A skill is worth having only when an agent can tell from its **name and description alone** whether to open
it, and when opening it tells the agent exactly what to do. This file is the procedure. The decisions behind
it: `docs/org/SKILL-KINDS-2026-09-27.md` (the CEO approved the seven kinds, the naming and the rename phases on
2026-09-27), ADR 0022 (governance: audience, authorship, the frontmatter contract), ADR 0026 (Field notes and
evidence tiers), ADR 0018 (lifecycle and the curator). The owner of this process is the COO.

## 0 · Is it ours?

- **Imported public skills are out of scope** until the CEO sorts them (CEO 2026-09-27): content-idea-generator,
  de-ai-ify, homepage-audit, marketing-principles, positioning-basics, social-card-gen, video-ad-analysis,
  voice-extractor. Do not tag, rename or edit them. They carry no `created_by`.
- Everything else under `.claude/skills/` is an org skill and follows this file.

## 1 · The seven kinds — every org skill has exactly one

| Kind | What it is | Test question | The body must carry |
|---|---|---|---|
| **Rules** | The org's binding rules only; no outside facts; a rule changes only by a CEO ruling | Is breaking it a violation? | each rule HARD with `Why hard:` or stated as advice |
| **Knowledge** | Facts about an outside system, read or measured at the source, plus lessons learned from mistakes | Can it turn false when the outside world changes? | source and date per fact; `verified:` in frontmatter |
| **Workflow** | One project end to end, from nothing to public release; points to the skills that own each step | Does it start from nothing and end at a public release? | per step: gate, owner skill, tool; no rules of its own |
| **Procedure** | One bounded task, input → one output, usually with a script | Can it be done in one sitting for one deliverable? | input, output, the script, how to verify |
| **Standard** | What a good deliverable looks like; used to write it and to check it | Does it define what good output looks like? | the spec, a check, good vs bad example |
| **Gate** | A check before a risky step; ends in pass / fail and refuses on fail | Does it end in pass / fail? | each check with its evidence, the verdict block |
| **Protocol** | How the org itself runs: sessions, terminals, spawning workers, logins, skills, role playbooks | Is it about running the org rather than the work? | trigger, steps, who is involved, what it never does |

If two answers are yes, the kind is the **main content: why an agent opens this skill.** A skill whose
content genuinely serves two kinds is two skills, or falls under §8.

## 2 · The name: `<ROLE>_<Kind>_<Topic>`

- **ROLE** — the lane that owns and mainly uses it: `CTO` (code, infra, deploy), `CMO` (content, film, posters,
  posts), `CGO` (metrics, A/B, funnels), `CFO` (money), `COO` (portfolio, routing, the org system).
  `CXO` = every C-level uses it. `ALL` = everyone, workers included. A worker role in capitals
  (`BROWSER_OPERATOR`, `VIDEO_EDITOR`) only for that role's own playbook.
- **Kind** — exactly one of the seven words above, capitalised as shown.
- **Topic** — PascalCase words joined by `_`; an engine or platform keeps its version and name:
  `Seedance2.5_Higgsfield`, `Wan3.0_TopView`, `Flow_Omni1.1`.
- Examples: `CMO_Knowledge_Seedance2.5_Higgsfield` · `CXO_Rules_GDrive_Filing` · `CTO_Gate_MergeChecklist` ·
  `ALL_Rules_Approvals` · `CMO_Workflow_ShortFilm`.
- **Exception — commands the CEO types himself** keep their short names (`session-open`, `session-close`,
  `session-save`, `session-list`, `session-merge`, `session-restart`, `session-worktree`,
  `session-change-model`, `terminal-open`, `terminal-restart`, `relay-login`); their kind lives in the
  frontmatter only. This is the CTO's recommendation; confirm it with the CEO before rename Phase 4.
- Existing skills are renamed only through §6, in the approved phases. Never rename one on the side.

## 3 · Frontmatter — the contract

```yaml
---
name: <exactly the directory name>
kind: <rules | knowledge | workflow | procedure | standard | gate | protocol>
description: <KIND IN CAPITALS> — <one-sentence purpose>. Trigger on /<name> and on "<phrase>", "<phrase>", ... <Do NOT … when a sibling competes>.
owner: <CTO | CMO | CGO | CFO | COO>
audience: [<role keys from policies/agents.yaml, or all | cxo | worker>]
created_by: agent            # exactly human | agent
author: {role: <role>, date: "<YYYY-MM-DD>"}
improved_by: []              # append-only: {role, date, what}
aka: []                      # every former name; keeps telemetry across a rename
verified: "<YYYY-MM-DD>"     # Knowledge only: the day the facts were last checked at the source
refresh_after: "<YYYY-MM-DD>"  # Knowledge only: when they must be checked again
---
```

`skill-lint` checks this contract and **reports; it never blocks** — ADR 0022 records the CEO's decisions 4
and 10 (no approval gate in any form), so the pre-commit hook ignores its exit code on purpose. Reading the
report is the COO's job. A lint code for `kind:` is part of the COO's rollout and does not exist yet.

## 4 · Create — eight steps

1. **Search for an owner first.** `grep -il "<topic words>" .claude/skills/*/SKILL.md` and read the two
   closest. If a skill already owns the topic, stop here and go to §5: a second skill on one topic is the
   duplication the CEO ruled out on 2026-09-25.
2. **Pick one kind** with the test questions in §1. If the content spans two kinds, plan two skills or apply §8.
3. **Name it** by §2 and check for a collision: `ls .claude/skills | grep -i "<topic>"`.
4. **Scaffold** with `python scripts/skill-curator.py create <name> --description "<…>" --audience <tokens>`;
   it stamps `created_by` and `author` and commits. Add `kind:` (and `verified:` for Knowledge) by hand.
5. **Write the body** from the kind's template in §9. Every fact carries its source and date; every rule is
   either HARD with `Why hard:` or advice (see "Rules, tiered" below).
6. **Write the description** (see "Description discipline" below): the kind word first, the "Trigger on"
   clause with phrases the CEO actually typed, a "Do NOT" clause when a sibling skill competes.
7. **Check it:** `.venv/bin/python scripts/skill-lint.py check` shows nothing for this skill; every path,
   tool and skill name it mentions exists:
   ```bash
   F=.claude/skills/<name>/SKILL.md
   grep -oE '`(tools|docs|scripts|runners|lib|config|roles)/[^` ]+`' $F | tr -d '`' | sort -u | while read p; do [ -e "${p%%<*}" ] || echo "MISSING $p"; done
   ```
   and any script it tells an agent to run has been run once.
8. **Commit** `skill(<name>): new — <what> — evidence <task-id / sha / the CEO's words>`, push, tell the CEO
   in one line, and add a pointer in the matching memory index when it matters across sessions.

## 5 · Update — six steps

1. **Evidence tier (ADR 0026).** One sighting is a Field note, appended under `## Field notes`:
   `- <date> [WRONG|MISSING|COSTLY] §<section> — <what> · evidence: <task-id / sha / path> · status: pending`.
   The rule body changes only on ≥2 independent runs agreeing, a CEO ruling, or an artefact proving the old
   rule cannot work. A rule flipped twice in 30 days is CONTESTED: frozen until the CEO rules.
2. **Edit the owner skill only.** When the same rule sits in two skills, keep it in the owner and leave a
   one-line pointer in the other.
3. **A replaced rule keeps its old line** as `[SUPERSEDED <date>]` with the evidence that beat it.
4. **Knowledge:** bump `verified:` and `refresh_after:` whenever a fact is re-checked at the source.
5. **A second kind creeping in** → §8.
6. **Change everything the edit contradicts in the same commit** — negatives, examples, the description.
   Commit `skill(<name>): note | rule | flip — <what> — evidence <…>`.

## 6 · Rename — one phase at a time, each skill the same way

The CEO approved the rename table and its phases on 2026-09-27 (`docs/org/SKILL-KINDS-2026-09-27.md`,
"Rename plan"). Per skill, all in the phase's single commit:

1. `git mv .claude/skills/<old> .claude/skills/<new>`; set `name: <new>`; add `<old>` to `aka:`; add `kind:`;
   put the kind word first in the description.
2. Find every literal reference: `grep -rlF "<old>" --exclude-dir=.git --exclude-dir=worktrees --exclude-dir=node_modules .`
   Live files change (other skills, `roles/`, `scripts/`, `tools/`, `runners/`, `lib/`, `config/`, hooks,
   `CLAUDE.md`); dated history (reports, old briefs, research) may keep the old name. **A hook keyed on the
   name** (for example `scripts/hook-gdrive-skill-gate.py` on `gdrive-filing`) changes in the same commit, or
   it goes silent.
3. Leave a redirect stub at the old name for 30 days (§9, Redirect stub).
4. The slash command changes with the name, and `tools/decide.py` routes on the "Trigger on /<name>"
   clause: say both in the report.
5. On the Mac, `~/.claude/skills` holds symlinks into the repo; a renamed directory dangles them with no
   error and the skill disappears. After the pull, list them (`ls -la ~/.claude/skills | grep -- '->'`) and
   re-point. Contabo has none.
6. `skill-lint` and the full test suite; commit `skill(<new>): rename — from <old> — phase <n>, CEO approval
   2026-09-27`; report the phase before starting the next.

## 7 · Retire — redirect stubs and archive

A stub stays 30 days, or until `grep` of live files finds no reference, then goes through
`python scripts/skill-curator.py archive <old>` (ADR 0018), never `rm`. The four stubs from the 2026-09-25
split (ai-film-production, google-flow-ops, higgsfield-unlimited-gen, thai-moral-drama) are rename Phase 0.

## 8 · A skill that mixes Rules and Knowledge

For each rule inside a Knowledge skill ask: **"if we stopped using this platform tomorrow, would the rule
still be true?"**
- **No** — it exists because of how that platform behaves (never click Rerun on Higgsfield: it fires at once
  and bills). Keep it inside the Knowledge skill as a HARD line with `Why hard:`. Split off, it loses the fact
  that explains it, and whoever opens the platform skill must meet it there.
- **Yes** — it is an org rule (the CEO's OK with the exact amount before any spend). It lives in ONE Rules
  skill (`ALL_Rules_Approvals`); the Knowledge skills keep a one-line pointer.

Split a skill in two only when (a) an org rule is repeated across skills, (b) the file is so large its rules
are buried, or (c) one part changes weekly and the other almost never (gdrive-filing: rules vs the folder map).
Split a too-large skill of one kind by topic, not by kind.

## 9 · Body templates — copy the one for the kind, then fill

**Rules**
```
# <What this governs>
<Who it binds and when it applies — one paragraph.>
## Rules
1. **HARD — <the rule, one sentence>.** <detail>
   **Why hard:** <money | irreversible | safety or scope> — <the incident or the failure mode>.
2. <Advice, stated as a fact or a cause and its effect.>
## When the CEO changes a rule
<Record his words verbatim here, old line kept as [SUPERSEDED].>
## Field notes
```

**Knowledge**
```
# <Platform or system>
Verified <date> at <source URL or task-id that measured it>.
## <Topic> — facts, each with its date and source
## Rules that exist because of this platform (HARD + Why hard)
## Org rules that apply here → ALL_Rules_Approvals (pointer only)
## Field notes
```

**Workflow**
```
# <Project type> — end to end
## How an agent joins (STATUS.md → current step → owner skill)
## Rules that hold on every step (pointers; HARD only for money / platform rules)
## Day plan (Day | steps | gate at end of day | CEO time)
## Step <n> · <name> — Do · Owner skill · Tool · Output · Gate
## STATUS.md template
```
The model: `CTO_Film_Workflow` (to become `CMO_Workflow_ShortFilm`).

**Procedure**
```
# <The deliverable>
Input: <…> · Output: <file, where> · Tool: `<script path>`
## Steps (numbered; each with the stop condition)
## Verify (the command, and what "done" looks like)
## Failure modes seen (dated)
```

**Standard**
```
# What a good <deliverable> is
## The spec (numbered, each checkable)
## The check (`<lint command>` or a 60-second read-through)
## Good vs bad (one of each, real)
```

**Gate**
```
# <Gate> — run before <the risky step>
## Checks (each: how to check, the evidence that passes it)
## Output
Gate 1 (<name>) : PASS — <evidence> / FAIL — <what> / N/A — <why>
Verdict: PROCEED / STOP pending <reason>
## Refusal: any FAIL stops the step; say what is missing.
```

**Protocol**
```
# <How the org does X>
Trigger: <when this runs>
## Steps
## Who is involved (roles, machines)
## What it never does
```

**Redirect stub** (at the old name, 30 days)
```
---
name: <old>
kind: <same kind>
description: MOVED to <new> on <date>. Read that skill; this stub is removed on <date + 30>.
lifecycle: active
---
MOVED: this skill is now `<new>` (<why, one line>). Remove after <date + 30> or once no live file names it.
```

## Description discipline

The `description:` line is the **only** thing Claude reads when deciding whether to invoke a skill, and
`tools/decide.py` builds its routes from the "Trigger on …" clause. It must contain:

1. **The kind word first**, in capitals: `RULES —`, `KNOWLEDGE —`, `WORKFLOW —`, `PROCEDURE —`,
   `STANDARD —`, `GATE —`, `PROTOCOL —`.
2. **One-sentence purpose.** What the skill does, plain language.
3. **Explicit slash trigger:** `Trigger on /<name> and …`.
4. **Phrases the user actually types**, verbs not categories, the CEO's own words where they exist (Thai and
   English). Every comma-separated item becomes a route, so a bare noun ("cache") routes any prompt that
   contains it.
5. **When NOT to fire**, if a sibling skill competes.
6. ≤350 characters (ADR 0022): the description is the only body text that costs context in every session.

**Bad** (vague, no triggers): `description: Helps with debugging code.` — "debug" alone never matches.
**Good** (9arm `debug-mantra`): purpose, the mantra, then "Trigger on /debug-mantra and proactively whenever
debugging starts — user reports a bug, says something is broken/throwing/failing, asks to
debug/diagnose/investigate an issue, or pastes a stack trace or error log."

Don't invent trigger phrases the user hasn't used — ask instead. A guessed trigger either fires on things
nobody meant or leaves the real phrase out, and the skill stays dead.

## Body structure (every kind)

1. **What it does** — one paragraph, mechanism-level.
2. **When to invoke / when NOT to** — explicit, false positives named.
3. **Steps** — numbered, in execution order, each with its refusal condition (when to stop and ask).
4. **Rules, tiered** — below; never a flat `Never X` / `Always Y` list.
5. **Output format** — a literal example block the agent can mimic.
6. Optional: a worked example (input → output) and references (skills, code, memory).

A good skill **refuses** when its preconditions are missing: *"If X is missing, list what's missing and stop.
Do not draft."* (`cto-merge-checklist` refuses a merge when a gate fails.)

## Rules, tiered (ADR 0022 §7 — a skill must not cage the model)

A skill that says "you must do exactly X" removes the model's judgement: it costs nothing on a weak model and
real capability on a strong one, and we run only frontier models. Facts the model cannot derive, and cause →
effect it can reason from, are pure gain; blanket mandates are a loss. (Hermes mandates on purpose because it
supports 300+ models down to a local Llama; we do not pay that price and must not inherit its side effect.)

**The contract is binary:** a rule is either **HARD**, and then it carries a **`Why hard:`** clause, or it is
advice the model may override — and when it overrides, it says why. No third tier, no scored classifier
(`cage_ratio` was proposed and rejected).

**The HARD test** — at least one must be yes, and the `Why hard:` clause is that answer:
1. Does breaking it spend money or consume a paid or limited resource?
2. Is the action irreversible?
3. Is there a safety, legal or scope-of-authorisation issue (harm, consent, acting outside a bound the CEO
   drew)?

Otherwise it is advice, written as a FACT (something the model cannot derive) or a WHY (cause → effect). An
overridden piece of advice is information about the skill, not misbehaviour: either the advice was wrong
here, or a fact is missing. A skill with zero HARD rules is normal; one that tags everything HARD has not
asked the three questions honestly.

## Location

| Scope | Path | When |
|---|---|---|
| Org skill | `<repo>/.claude/skills/<name>/SKILL.md` | every org-authored skill |
| External link | symlink global → external clone | imported from a curated source (9arm) |

`~/.claude/skills/<name>/` is not a place for org skills (ADR 0022 §5): outside git, the curator, lint and
`undo`. A purely personal skill the org's machinery has no reason to touch is the only thing that may live
there.

## Common mistakes

- **One-sentence description.** Triggers never match → add the phrases people type.
- **Body is a wall of prose.** Agents skip it → numbered steps, code blocks, tables.
- **No refusal conditions.** The skill runs on bad input → add the precondition.
- **Trigger overlaps another skill.** The agent picks at random (measured 2026-09-27: 2 of 7 skills loaded in
  one CTO session were read and not used — a generic "storyboard" skill and a redirect stub) → a name that
  says role, kind and topic, and a "Do NOT" clause.
- **The same rule in several skills.** They drift apart → one owner, pointers elsewhere (§5.2, §8).
- **No worked example.** Output drifts → one full input → output.

## Output when invoked

1. State the plan in one line: kind, name, owner, audience, triggers — and the owner skill you searched for.
2. Write the file (§4 or §5), run the checks in §4.7, commit.
3. Print the final description so the CEO can check the trigger phrases, and the commit sha.

## Rules

1. **HARD — Never scaffold an org-authored skill under `~/.claude/skills/`.**
   **Why hard:** irreversible by construction — outside git, `skill-curator.py` and `undo` (ADR 0022 §4), so
   there is no commit to revert.
2. **HARD — Rename an existing skill only through §6, inside an approved phase.**
   **Why hard:** irreversible-silent — a renamed directory dangles the Mac's `~/.claude/skills` symlinks and
   the skill disappears with no error; a hook keyed on the old name stops firing without a sound.
   `[SUPERSEDED 2026-09-27]` "Never rename an existing skill directory and never `git mv` one; the 21 skills
   that predate ADR 0022 are grandfathered permanently" — replaced by the CEO's ruling that names must say
   role, kind and topic, with the rename table and phases he approved on 2026-09-27 ("OK ตามนั้น"); the hazard
   that motivated the ban is now step 5 and step 2 of §6.
3. One revision round on a description is normal; three means you are iterating blind — ask which real
   scenario still doesn't match.
4. Log a new skill in the matching memory index when it matters across sessions; otherwise the next session
   finds it only by grepping.

## Field notes

- 2026-09-25 [MISSING] §Description discipline — `tools/decide.py` builds the skill.route rules from the "Trigger on …." clause, split on commas and " and ". Until 72357fc8 the clause ended at the FIRST dot, so every engine-named skill with a version in its name (/CTO_Flow_Omni1.1_…, Seedance 2.5, Wan 3.0) routed on a fragment only; it now ends at a sentence stop. Side effect to write around: every comma-separated item becomes a standalone route, so a generic word in the list ("cache", "worktree" in disk-hygiene) routes any prompt that contains it; keep trigger items as phrases a user would type, not a list of nouns · evidence: both skill-split workers (task-c3e07fb1, task-e7cc2d83), fix 72357fc8 · status: pending
- 2026-09-27 [SUPERSEDED] §1 §2 §6 §Rules 2 — rewritten on the CEO's rulings of 2026-09-27: seven kinds ("เห็นด้วยทั้ง 7 หมวดหมู่"), names that say role, kind and topic, the rename table and its phases ("OK ตามนั้น"), the mixed-skill rule, and the COO as owner of this process ("เขียน skill สำหรับการสร้าง skill ... เวลาที่ COO หยิบไปใช้จะได้ใช้งานได้ทันที"). The "never rename" rule is kept above as SUPERSEDED · evidence: docs/org/SKILL-KINDS-2026-09-27.md, CTO session 14cc900f · status: promoted
