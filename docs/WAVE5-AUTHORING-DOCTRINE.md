# Wave 5 — Authoring Doctrine (a skill must not cage the model)

Implements ADR 0022 §7 and the playbook's Wave 5
(`org:decisions/0022-skill-governance-visibility-authorship-audit.md`,
`org:playbooks/skill-governance-implementation.md`). Wave 5 only — Waves 0-2
already merged; Wave 4 (`task-085f7839`, `scripts/skill-report.py`,
`tools/skill_objection.py`, `runners/worker_mcp_server.py`) ran concurrently
and was not touched.

## The contract

> A rule block is either **HARD**, and then it carries a **`Why hard:`**
> clause, or it is advice the model may override — and when it overrides, it
> says why.

Money, irreversible actions, and safety/scope stay HARD. FACT (something the
model cannot derive) and WHY (a cause→effect chain it can reason from) stay
in `skill-author` as authoring advice — unenforced, unmeasured, free. There
is no third tier and no scored classifier.

**An override is a signal about the skill, not misbehaviour by the model.**
This sentence is now in `.claude/skills/skill-author/SKILL.md` verbatim.

## The HARD test

A rule earns **HARD** only if the answer to at least one of these is yes —
and the `Why hard:` clause is written from whichever answer was yes, not
invented separately afterward:

1. Does breaking this rule spend money or consume a paid/limited resource?
2. Is the action irreversible — no undo, no way to unfire it?
3. Is there a safety, legal, or scope-of-authorisation issue?

Full text, template, and the reasoning behind the binary shape (why no
`cage_ratio`) live in `.claude/skills/skill-author/SKILL.md` under "Rules,
tiered."

## 5.1 — `skill-author` changes

- Body-structure item 5 changed from `**Operating rules** — bullet list of
  guardrails (Never X, Always Y)` to `**Rules, tiered**`.
- New "Rules, tiered (ADR 0022 §7 — a skill must not cage the model)"
  section: the principle, the Hermes contrast, the contract quote, the HARD
  test, a template, and the verbatim override sentence.
- `skill-author`'s own "Operating rules" section is retitled "Rules" and
  tiered: one genuinely HARD rule (never scaffold under `~/.claude/skills/`
  — irreversible, outside git/curator/undo by construction) and four items
  restated as advice (FACT/WHY prose, no more bare `Never X` bullets).
- Built on Wave 2's existing "Audience prefix — NEW skills only" section and
  the `~/.claude/skills` removal — neither was touched or undone.

## 5.2 — Override capture (the line format + the read contract for Wave 4)

`runners/worker_init.py:_build_prompt` gained one paragraph, right before
`Begin.`:

```
If a skill you followed gave HARD-tagged rules, follow them as written. If it
gave advice (not HARD) and you judged the situation called for something
else, that's fine — just record it in your report as one line per override:
`SKILL-OVERRIDE: <skill> :: <rule> :: <did instead> :: <why>`
```

No new hook, no new log file, no settings paste. These lines land wherever a
worker's prompt already lands, retroactively readable:

- **`tasks.report`** (`state/tasks.db`) — the string a worker passes to
  `mcp__org__submit_report`. 582 populated rows today (Wave 4's count at spec
  time), one per finished task.
- **`state/logs/cto.log`** — if a worker also posts the line as a message
  back to its CTO (not guaranteed, but common for anything worth flagging
  live).

**Grep/parse contract, for Wave 4 or a follow-up to wire into
`skill-report.py`'s `obj`-style columns in one line:**

```
grep -oE 'SKILL-OVERRIDE: [^:]+ :: [^:]+ :: [^:]+ :: .+' <source>
```

Split on ` :: ` (space-colon-colon-space, exactly 4 parts) to get
`(skill, rule, did_instead, why)`. The line is free-text after the tag, so a
`::` inside `did_instead` or `why` would break the naive split — the four
fields were kept in this exact order, delimiter-first, specifically so a
consumer can `str.split(' :: ', 3)` (max 3 splits) rather than a strict
4-way split, which tolerates a stray `::` in the last field only. No
existing skill body or worker output currently contains `::`, so this is
untested against real data, not a guarantee.

## 5.3 — `scripts/skill-doctrine-lint.py`

Hand-run, `check [--json] [--skills-dir DIR]`, no `--strict`, never wired
into pre-commit (unlike `skill-lint.py`, which is). Detects a
`**HARD --`-tagged rule block with no `Why hard:` clause before the next
numbered rule or heading. One absolute defect count, threshold zero.

Detection is a narrow regex on the literal bold-open shape (`**HARD` followed
by whitespace then `:`/`—`/`-`), not a bare word match — three real false
positives were caught and fixed while authoring it against the live corpus
(narrative use of the word "HARD" in `skill-author`'s own new doctrine
prose, `session-merge`'s unrelated "HARD LIMIT" concept, and a sentence in
`higgsfield-unlimited-gen` *describing* the contract). All three are now
covered as regression tests in `scripts/test_skill_doctrine_lint.py`.

Not built, per the ADR — confirmed still true, not re-derived:

- **`cage_ratio`.** No variance across the corpus, an undefended 0.30
  threshold, an unvalidated Thai mandate-word matcher (`ต้อง`/`ห้าม`), no
  consumer.
- **Any mandate-vocabulary matcher** ("must", "never", "always" counting).
  FACT/WHY advice is deliberately unmeasured; counting how forceful it
  sounds would resurrect the same rejected metric under a different name.
- **A Tier-0 mechanical tagging commit** across the 21 pre-Wave-5 skills —
  it existed only to de-noise `cage_ratio`, which doesn't exist.
- **A `--strict` mode or any pre-commit wiring.** Exit non-zero is fine;
  refusing to write a skill is not (CEO decisions 4 and 10).

## 5.4 — `higgsfield-unlimited-gen` before/after

This is the one exception to "retrofit on next edit, not big-bang" — done on
its own merit because it governs real money and was the most mandate-dense
skill in the corpus.

### Bug fixed: zero-digits vs strike-through contradiction

**Before** (old Hard rule 3): *"confirm it reads bare 'Generate' with ZERO
digits anywhere on it… If any number shows, do not click."*

**Also before**, deep in the same file's "Findings from the Valder wave"
section (already correctly written, just never reconciled with rule 3):
*"Do not carry the 'zero digits' rule over from image tasks… A brief that
says 'zero digits anywhere' will stop a correct operator dead."* A working
Unlimited video generation legitimately shows a struck-through price plus
`0` (`Unlimited · ~~140~~ · 0`) — which has digits. The two sections of the
same file directly contradicted each other; an operator handed only the old
rule 3 would refuse a correct, free generation.

**After** (new Hard rule 2): one table, the only place this logic lives now:

| Surface | Button reads | Meaning | Action |
|---|---|---|---|
| Seedance 2.5 VIDEO, Unlimited working | struck-through price then `0` | Unlimited applied | Click |
| Seedance 2.5 VIDEO | bare `Generate`, no price at all | fine | Click |
| Seedance 2.5 VIDEO | live price, **no strike-through** | Unlimited OFF | **STOP** |
| GPT Image 2 (any plate) | small live number, no strike | normal — images are never Unlimited | Click within budget |
| GPT Image 2 | an "Unlimited mode" control beside it | $30 paid upsell, not our subscription | **Never click** |

The distinguishing signal is now named explicitly: **the strike-through, not
the presence of digits.**

### Tiering — 7 rules, all stayed HARD, none softened

The brief warned specifically not to soften money/irreversibility rules to
make a doctrine point. Applying the 3-question HARD test to each of the 7
"Hard rules" honestly returned yes on at least one question for every one of
them — none were demoted to advice:

| # | Rule | Why it's genuinely HARD |
|---|---|---|
| 1 | Never click "Rerun" | **Money** — auto-fires a generation with zero confirmation; confirmed 130-credit charge (task-eed61860, GH #45) |
| 2 | Read the price signal correctly before Generate (the fixed table above) | **Money** — no undo after the click lands |
| 3 | Confirm the Rights-verification banner, nothing else | **Scope/authorisation** — the CEO-bounded permission must not be widened by inference; an operator once correctly refused a *relayed* version of this same approval |
| 4 | One Unlimited video at a time; never force a stuck concurrency toast | **Money** — forcing a workaround means clicking near a live, potentially priced composer (the exact pattern that cost $10.80 in rule 5's incident) |
| 5 | Toggle unresponsive: stop after one clean attempt | **Money** — every extra click technique near a priced button is itself a money risk; two real 135-credit charges landed this way |
| 6 | Never use keystroke-`type()` for prompt text; paste only | **Money/irreversible** — a truncated prompt fires immediately; no catching it before Generate, only redoing it, and one real credit charge fired from this exact failure with zero deliberate click |
| 7 | Any browser-tool error → check Usage History first | **Money** — Usage History is the only ground truth for whether a charge landed; a failed tool call is not evidence either way |

One real gap found and fixed while tiering: rule 6 as originally drafted in
this pass was missing its own `Why hard:` clause — caught by running
`skill-doctrine-lint.py` against the file during authoring, which is exactly
the workflow it exists to support.

Everything else in the 1,300+-line file (incident logs, editor gotchas, the
Valder-wave findings, render-scheduling data) was left untouched — it is
already written as FACT/WHY narrative, not blanket `Never X` mandates, and
Wave 5's brief scoped the retrofit to "fix the contradiction" plus "tier its
rules" (the numbered Hard-rules block), not a full-file rewrite.

## What was wrong in the brief

The brief's own §7 quote already documented the zero-digits/strike-through
contradiction as something to fix, but the file's "Findings from the Valder
wave" section had *already* written the correct struck-through logic weeks
earlier — the bug wasn't a missing fact, it was two true sections that had
never been reconciled into one instruction. Worth naming because it's the
same failure mode ADR 0022 §7 is about: the file had judgement-respecting,
well-reasoned advice sitting right next to a blanket mandate that
contradicted it, and nothing forced them to agree until this pass.

Also: `runners/worker_init.py:_build_prompt`'s six-step "Instructions" list
ends immediately in `Begin.` with no trailing free-text section before it in
the original — the override-line instruction had to be inserted as a new
paragraph between step 6 and `Begin.` rather than as a 7th numbered step,
since it isn't a step to perform, it's a standing convention for whenever it
applies.
