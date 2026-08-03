---
name: skill-author
description: Author a new Claude Code skill with discoverable description, concrete triggers, and operating rules. Enforces 9arm-style description format so the skill actually fires when expected. Trigger on /skill-author and proactively whenever the user asks to "create a skill", "write a skill", "make a SKILL.md", "add a new skill", "scaffold a skill", or describes a recurring task pattern they want codified ("I keep doing X — turn it into a skill").
---

# Skill Author

Write SKILL.md files that **actually fire** when the trigger occurs and **don't fire** when it doesn't. Bad descriptions = dead skills.

## Description discipline

The `description:` line is the **only** thing Claude reads when deciding whether to auto-invoke. It must contain:

1. **One-sentence purpose.** What the skill does. Plain language.
2. **Explicit slash trigger.** `Trigger on /skill-name and proactively whenever...`
3. **5+ concrete phrases** the user is likely to type. Verbs, not categories.
4. **When NOT to fire** if there's a common false-positive.

### Template

```yaml
---
name: kebab-case-name
description: <one-sentence purpose>. Trigger on /<name> and proactively whenever the user <action 1>, <action 2>, says "<phrase 1>", "<phrase 2>", "<phrase 3>", or <context cue>. Do NOT fire when <false-positive>.
---
```

### Examples — good vs bad

**Bad** (vague, no triggers):
```
description: Helps with debugging code.
```
AI never invokes; "debug" alone is too generic.

**Good** (9arm `debug-mantra`):
```
description: Four-mantra debugging discipline — reproduce, trace the fail path,
falsify the hypothesis, cross-reference every breadcrumb. Recite the mantra
block verbatim at the start of any debugging session, then apply the four
steps in order before proposing any fix. Trigger on /debug-mantra and
proactively whenever debugging starts — user reports a bug, says something
is broken/throwing/failing, asks to debug/diagnose/investigate an issue, or
pastes a stack trace or error log.
```
AI knows exactly when to fire; phrases match real user speech.

## Body structure

Required sections:

1. **What it does** — one paragraph, mechanism-level.
2. **When to invoke** — bullet list of trigger phrases (expanded from description).
3. **When NOT to invoke** — false positives explicit.
4. **Steps / workflow** — numbered, in execution order. Each step has a refusal condition (when to stop and ask).
5. **Operating rules** — bullet list of guardrails (`Never X`, `Always Y`).
6. **Output format** — show a literal example block so AI mimics it.

Optional but valuable:
- **Worked example** — full input → output walkthrough.
- **Reference** — link to related skills, code files, memory entries.

## Naming

- **Slug:** kebab-case, no `ecc:` or other prefix unless plugin-namespaced.
- **Verb-first if action** (`debug-mantra`, `post-mortem`, `scrutinize`).
- **Noun if reference** (`postgres-patterns`, `motion-foundations`).
- **No version numbers** in name (`my-skill-v2`) — edit in place instead.

## Location

| Scope | Path | When |
|---|---|---|
| Global (all projects) | `~/.claude/skills/<name>/SKILL.md` | Cross-project discipline (debug-mantra). |
| Project | `<repo>/.claude/skills/<name>/SKILL.md` | Repo-specific workflow (cto-merge-checklist). |
| External link | symlink global → external clone | Imported from a curated source (9arm). |

## Refusal conditions

A good skill **refuses** when preconditions aren't met. Examples:
- `post-mortem` refuses without repro + root cause + validated fix.
- `debug-mantra` refuses to propose fix before reliable repro exists.
- `cto-merge-checklist` refuses merge if any gate fails.

Write the refusal explicitly: *"If X is missing, list what's missing and stop. Do not draft."*

## Common mistakes

- **Description = one short sentence.** Triggers won't match. Fix: expand to 5+ phrases.
- **Body is a wall of prose.** AI skips. Fix: bulleted steps, numbered workflow, code-block examples.
- **No refusal conditions.** Skill always tries, even when inputs are bad. Fix: add precondition gates.
- **Trigger overlaps another skill.** AI picks randomly. Fix: differentiate in description + add to CLAUDE.md skill-preferences section.
- **No worked example.** Output drifts. Fix: include one full input→output.

## Output flow when invoked

1. Confirm intent: "I'll scaffold a `<name>` skill at `<path>`. Trigger: `/<name>` + when user X. OK?"
2. On confirm → Write SKILL.md.
3. Verify: glob ensure no duplicate name.
4. Print the registered skill description so user can sanity-check trigger phrases.
5. If creating in project scope, suggest adding to `~/.claude/CLAUDE.md` skill-preferences if it overrides any `ecc:*` default.

## Operating rules

- **Never invent triggers** the user didn't confirm. Ask.
- **Never name a skill `helper`, `utility`, `tool`, `assistant`** — too vague, never fires.
- **One iteration is normal, three is a smell.** If user still revising description on third try, ask what scenario isn't matching.
- **Log new skills** to project memory (`reference_<name>.md` if cross-session importance).
