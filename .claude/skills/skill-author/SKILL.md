---
name: skill-author
owner: CTO
origin: mooniex-org
scope: >-
  Scaffolds a new SKILL.md whose description actually fires — 9arm-style trigger
  format, refusal conditions, required body sections, naming and location rules.
  Authoring only; does not install, register, or route the resulting skill.
description: Author a new Claude Code skill whose description reliably triggers. Trigger on /skill-author and when the user asks to "create a skill", "write a skill", "make a SKILL.md", "scaffold a skill", or wants a recurring pattern codified.
created_by: human
audience: [all]
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
5. **Rules, tiered** — see below. Not a flat `Never X` / `Always Y` list.
6. **Output format** — show a literal example block so AI mimics it.

Optional but valuable:
- **Worked example** — full input → output walkthrough.
- **Reference** — link to related skills, code files, memory entries.

## Rules, tiered (ADR 0022 §7 — a skill must not cage the model)

**The principle:** a skill that says "you must do exactly X" removes the
model's judgement. That costs nothing on a weak model and costs real
capability on a strong one — **and we run only frontier models.** Facts the
model cannot derive, and cause→effect it can reason from, are pure gain.
Blanket mandates are a loss.

This is not something to copy from anywhere. Hermes does the opposite
deliberately — its own system prompt tells the model to load a skill *"even
if you think you could handle the task with basic tools"* and *"even for
tasks you already know how to do,"* and across its 58 bundled skills there
are ~460 mandate tokens against 4 uses of "judgment" and none of
"discretion." That posture is the price of supporting 300+ models down to a
local Llama — they must write for the weakest model they support. We do not
pay that price, so we must not inherit its side effect.

**The contract is binary, and that is deliberate:**

> A rule block is either **HARD**, and then it carries a **`Why hard:`**
> clause, or it is advice the model may override — and when it overrides, it
> says why.

There is no third tier. Do not build a scored/ratio classifier (`cage_ratio`
was proposed for this org and explicitly rejected — no variance across the
corpus, an undefended threshold, an unvalidated Thai mandate-word matcher,
no consumer). One rule, tagged one of two ways.

### The HARD test

A rule earns **HARD** only if the answer to at least one of these is yes.
Write the `Why hard:` clause from whichever answer was yes — that is the
whole clause, not a separate justification you invent afterward.

1. **Does breaking this rule spend money or consume a paid/limited
   resource** (credits, a rate-limited quota, a scarce account-wide slot)?
2. **Is the action irreversible** — no undo, no way to unfire it, no way to
   get back to the prior state once it happens?
3. **Is there a safety, legal, or scope-of-authorisation issue** — harm to a
   person, data, or system; consent/rights exposure; acting outside a bound
   the CEO or CTO explicitly drew?

If none apply, the rule is **advice**: state the fact or the cause→effect
reasoning, and let the model weigh it against the situation in front of it.
FACT (something the model cannot derive on its own) and WHY (a cause→effect
chain it can reason from) are the two shapes advice takes — both are free:
unenforced, unmeasured, and nothing in the authoring or review mechanism
reads them any differently from prose.

**An override is a signal about the skill, not misbehaviour by the model.**
When advice gets overridden, that is information — either the advice was
wrong for this situation, or the skill is missing a fact that would have
changed the model's call. Neither is a violation to police.

### Template

```markdown
## Rules

1. **HARD — <the rule, one sentence>.** <mechanism/detail as needed>.

   **Why hard:** <money | irreversible | safety/scope>, plus the specific
   consequence — cite the incident or the concrete failure mode if one exists.

2. <Advice, stated as FACT or WHY — no bullet-list "Never X, Always Y".
   State the fact plainly, or the cause and its effect, and trust the model
   to apply it.>
```

A skill with zero HARD rules is not a defect — most authoring/reference
skills have none. A skill that tags everything HARD probably has not asked
the three questions honestly.

## Naming

- **Slug:** kebab-case, no `ecc:` or other prefix unless plugin-namespaced.
- **Verb-first if action** (`debug-mantra`, `post-mortem`, `scrutinize`).
- **Noun if reference** (`postgres-patterns`, `motion-foundations`).
- **No version numbers** in name (`my-skill-v2`) — edit in place instead.

### Audience prefix — NEW skills only (ADR 0022 §4)

Every brand-new org-authored skill's directory name gets prefixed with its
`audience:` role(s), e.g. `CTO_Higgsfield_Seedance2.5_Prompt`. This is a
naming mirror, not the routing mechanism — the `audience:` frontmatter field
is the actual authority (reports and visibility both compute from it), the
prefix just lets a human recognize who a skill is for while browsing
`.claude/skills/` directly.

**The 21 skills that predate this ADR are grandfathered permanently.**
**Never rename an existing skill directory and never `git mv` one** —
`~/.claude/skills` holds symlinks into this repo (`browser-operator`,
`mooniex-finance`, ...), and renaming the target dangles the link: the skill
vanishes with no error. 39+ files also reference skill names as literal
strings (including prompt text in `runners/`). This restriction applies to
every existing skill regardless of who authored it — it is a rename hazard,
not a grandfather clause for legacy naming style.

## Location

| Scope | Path | When |
|---|---|---|
| Project (the only sanctioned org location) | `<repo>/.claude/skills/<name>/SKILL.md` | Every org-authored skill — repo-specific or cross-project discipline alike. |
| External link | symlink global → external clone | Imported from a curated source (9arm). |

**`~/.claude/skills/<name>/` is no longer a sanctioned location for
org-authored skills (ADR 0022 §5).** A skill written there sits outside git,
outside `skill-curator.py`, and outside `undo` by construction — which
defeats the entire point of git-as-ledger (ADR 0022 §4): no commit, no
history, no revert. Always scaffold into `<repo>/.claude/skills/<name>/`, or
better, use `scripts/skill-curator.py create <name> --description ... --audience
...`, which stamps `created_by: agent` + `author:` from the calling identity
and commits the result for you. A purely personal, non-org skill (something
this org's curator/lint/undo machinery has no reason to ever touch) is the
only case still fine to keep under `~/.claude/skills/`.

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

## Rules

This skill follows its own doctrine above — a doctrine skill that doesn't
tier its own rules teaches the opposite of what it says.

1. **HARD — Never scaffold an org-authored skill under `~/.claude/skills/`.**
   See "Location" above.

   **Why hard:** irreversible-by-construction, not just risky. A skill
   written there sits outside git, outside `skill-curator.py`, and outside
   `undo` (ADR 0022 §4) — there is no ledger entry to revert, because there
   was never a commit.

2. Don't invent trigger phrases the user hasn't confirmed — ask instead. A
   description with guessed triggers either mis-fires on things the user
   never meant, or the real trigger phrase never made it in and the skill
   stays dead. Confirming first is cheaper than a silent non-fire.
3. Skip vague names (`helper`, `utility`, `tool`, `assistant`) — a
   description can be perfect and the skill will still never fire, because
   Claude can't tell from the name what domain it's even in.
4. One revision round on the description is normal; three is a smell worth
   naming out loud — at that point ask what concrete scenario still isn't
   matching, rather than iterating on wording blind.
5. Log a new skill to project memory (`reference_<name>.md`) when it carries
   cross-session importance — otherwise the next session has no way to know
   it exists outside of grepping `.claude/skills/`.

## Field notes

- 2026-09-25 [MISSING] §Description discipline — `tools/decide.py` builds the skill.route rules from the "Trigger on …." clause, split on commas and " and ". Until 72357fc8 the clause ended at the FIRST dot, so every engine-named skill with a version in its name (/CTO_Flow_Omni1.1_…, Seedance 2.5, Wan 3.0) routed on a fragment only; it now ends at a sentence stop. Side effect to write around: every comma-separated item becomes a standalone route, so a generic word in the list ("cache", "worktree" in disk-hygiene) routes any prompt that contains it; keep trigger items as phrases a user would type, not a list of nouns · evidence: both skill-split workers (task-c3e07fb1, task-e7cc2d83), fix 72357fc8 · status: pending
