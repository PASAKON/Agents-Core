---
name: CXO_Gate_RouteFirst
kind: gate
description: >-
  GATE — Before every delegate_task of a worker job: outside runners first (IRON §59 rule 7). What route.check_override v2 and the router enforce, the closed reason codes, how to write a brief the router reads right, and what the code does not catch. Trigger on /CXO_Gate_RouteFirst and on "pin to claude", "override:", "runner=", "model_hint", "IRON §59 rule 7", "pinned by hand", "router chose claude", "which runner", "delegate to codex/agy". Do NOT use for the merge itself (CTO_Gate_MergeChecklist) or for how a runner is spawned (CXO_Protocol_DevSpawn).
owner: CTO
audience: [cxo]
created_by: agent
author: {role: cto, date: "2026-10-13"}
improved_by: []
aka: []
---

# CXO_Gate_RouteFirst — run before every `delegate_task`

IRON §59 rule 7 (CEO 2026-10-14, Q-20261013-1745-f56c): while any outside bucket (agy-gemini,
agy-claude, codex, Jules) has room for an eligible job, the job does not go to a Claude
Sonnet/Opus worker. **The code enforces this; this skill says what the code checks.** That way a
refusal costs one edited line, and you know where the code is blind. Plan:
`docs/plans/tool-value-weekly-and-enforcement-2026-10-13.md` §4.

## Checks

### Gate 1 — a hand pin carries a reason code (code: `route.check_override`, refuses at delegate)
- **What counts as a hand pin** (routed roles only, `config/plans.yaml role_classes`: developer, tester):
  - `model_hint` is set; or
  - `runner` is set while `runner_model` is NULL; or
  - `runner='codex'` with `runner_model=''`, no `router:` in `delegate_log`, and no worktree yet.
- **To pass:** write `override: <code> <why>` on **line 1** of the description.
  - The rule says line 1. The code also accepts any line of the first block (lines 1–5, before the
    first blank line).
  - A line below a blank line is ignored.
  - The first word must be a code from this closed list:

  | Code | Use it when |
  |---|---|
  | `review` | Claude reviews or repairs another agent's code |
  | `security` | security-sensitive code or review |
  | `silent-wrong` | a wrong answer would ship unnoticed (a hub write, a cutover, a host pick) |
  | `claude-tool` | the job needs a Claude-only tool (§59 rule 2) |
  | `ceo-order` | the CEO ordered this runner. Also use it for a pin **to an outside runner** when the live router would pick wrong (see Gate 3) |
  | `ab-test` | a planned A/B between runners |
  | `box-bound` | the job must run on one machine |
  | `quota-handoff` | an outside runner hit its limit mid-job and a Sonnet worker finishes it on the same branch |

- **Refused:** free text and anything off the list.
  - "in-session", "CEO order" (the code is `ceo-order`), "runner=claude" and "A/B test" are all refused.
  - The refusal names the word it saw and prints the codes.
  - For a size S/M job on a repo in `config/jules.yaml`, with no secret or deploy words, the refusal
    also prints the Jules command.
- **Evidence:** after `delegate_task`, `delegate_log` does not start with `IRON §59 rule 7`.
- **Measured:** all 10 override lines in the 30 Sep sample (`tests/fixtures/w211_task_descriptions.json`)
  were free text, so v2 would have refused every one.

### Gate 2 — the brief says what it runs (code: `forecast.needs_shell`)
- If the brief names a command, only a shell runner may take it (`shell_runners`: claude, codex).
- What counts as a command:
  - `pytest`, `git fetch/pull/merge/rebase/cherry-pick/archive/worktree/checkout -b`
  - running Python (`python x.py`, `-m`, `-c`)
  - `infisical run`, `org-python.sh`, `with-org-db-env.sh`
  - the older markers: psql, docker, systemctl, ssh, curl, `npm `, `bash `, …
- The one exception is `tools/agy_browse.py` on the browser_agy lane.
- **agy on Contabo is file-only.** Headless agy denies every command, so a brief whose first step
  runs one ends with exit 0 and no output (task-0156526f).
  - An agy brief asks for files only and says "the reviewer runs the tests".
  - Never name pytest or a git verb in it, not even as text to avoid.
- **The detector reads text, not intent.** A brief that quotes a shell word reads as a shell job,
  even when the word appears only as text about the job (task-7b431b10).
  - When you must quote one, pin the runner yourself (Gate 1, `ceo-order`).
- **Evidence:** the `router:` line names a runner that can do what the brief asks.

### Gate 3 — read the router's line after every delegate (code: `route.plan`, pressure rule)
- **The pressure rule** (`pressure_rule: true` in plans.yaml):
  - Each outside bucket's reserve is scaled by Claude's weekly share left. The emptier Claude is,
    the deeper outside runners may go.
  - An `ok` outside runner always ranks ahead of an `ok` Claude.
  - With Claude's quota unreadable, there is no scaling.
- **Check:** `delegate_log` reads `router: <runner> <model> [<bucket>] — …`.
  - If it names claude while an outside runner fits the job, stop the worker at once (tmux session
    + pid), cancel the row and re-create it pinned with `override: ceo-order`.
  - On 13 Oct, before the rule was live, the router ranked claude above codex by headroom
    (86% vs 69% left, task-88e23258).
- **Evidence:** the runner named is outside, or the task carries a code from Gate 1.

### Gate 4 — a quota stop is a handoff, never a silent fallback
- An outside task that stopped on its runner's limit is finished by a Sonnet worker on the same
  branch with `quota-handoff`, keeping the partial work.
- Its runner_fit says fail = limit and the % done (Q-20261013-1748-5efe).
- Never re-pin it to Claude by hand without the code.
- **Evidence:** a new task whose line 1 is `override: quota-handoff …` and whose line 2 merges the
  outside branch.

### Gate 5 — every outside job ends with one `runner_fit`
- Record `runner_fit` (hub event, schema 1) with these fields:
  - runner, model, bucket, job type, size
  - pass / redo / fail and the fail reason
  - why, minutes, iteration
  - `first_pass`: a merge with no reopen and no reviewer fix
- A failure becomes a field note in that runner's Knowledge skill (n=1), and a rule only at n≥2
  (ADR 0026).
- **Evidence:** one `runner_fit` event per closed outside task.

## What the code does not catch (the Monday report shows it instead)
- **A hand pin that also writes `runner_model`** looks routed.
  - The report lists tasks that have a `runner` and no `router:` line.
- **`ORG_ROUTER=off`** turns the gate and the router off, for repair only. It is **not logged
  yet**, though plan §4.3 M1 says it should be.
  - The place to log it is `tools/delegate.py:_route_runner`. Agree the order with whoever holds
    delegate.py before editing it.
- **A C-level's own `Agent` calls** never reach `delegate_task`.
  - The M2 hook logs them for 3 days, then blocks a dev-shaped call without a reason (Q-20261013-1745-f56c).
- **The C-level session's own tokens:** no router touches them. The lever is one job per session.

## Output
```
Gate 1 (pin has a code)       : PASS — line 1 "override: <code>" / N/A — not pinned / FAIL — <word> is not a code
Gate 2 (brief matches runner) : PASS — <runner> can run what the brief asks / FAIL — <command> in an agy brief
Gate 3 (router line read)     : PASS — router: <runner> [<bucket>] / FAIL — claude while <outside> fits
Gate 4 (quota stop)           : N/A — no limit / PASS — quota-handoff task-<id>
Gate 5 (runner_fit)           : PASS — event logged / FAIL — task closed without one
Verdict: PROCEED / STOP pending <reason>
```

## Refusal
Any FAIL stops the delegate or the close. Fix the line or the brief, then delegate again.

## Field notes
