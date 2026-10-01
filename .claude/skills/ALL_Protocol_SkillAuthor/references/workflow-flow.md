# Workflow → Flow — the `flow.yaml` contract (v1)

Every `kind: workflow` skill carries **two files**: `SKILL.md` (the prose an agent reads) and `flow.yaml`
beside it (the graph a machine reads). The Console draws its Flow board from `flow.yaml`, the run side keys its
events on the node ids in it, and `scripts/flow-lint.py` checks it. One source, three readers: the agent, the
lint and the UI. CEO ruling 2026-10-02 ("แก้ไข" — bind the Control Room to the Workflow skill; the CTO sets
the format, the owners write their workflows in it). The board itself is planned in the ClaudeFlow Control
Room plan (CTO, 2026-10-02).

## 1 · What lives where — a fact sits in ONE file

| Fact | `flow.yaml` | `SKILL.md` |
|---|---|---|
| order, dependencies, node kind, tool, owner skill, provider, unit cost, verify, stage, trigger, budget, watcher | **only here** | not restated (it drifts) |
| how to do the step, the judgement, the traps, the CEO's taste | — | **only here** |
| the step's name | `name` | the step heading (must match, F12) |
| the gate | `gate`: one line, the pass condition the board shows | how to check it, as long as it needs |

An agent joining a run reads `STATUS.md` → its `node:` → that node in `flow.yaml` (tool, owner skill, verify) →
the matching `### Step` in `SKILL.md` (how) → the owner skill.

## 2 · The file

`.claude/skills/<Workflow skill>/flow.yaml`. Every key below; anything else is a typo (F2).

```yaml
schema: mooniex.flow/v1
flow: bl                                # id: [a-z][a-z0-9_]*, unique across all workflows, never renamed
name: Black Liquidity episode           # ≤40 chars — the board's title
skill: CMO_Workflow_BlackLiquidity      # = the folder this file sits in
owner: CMO                              # = the skill's owner:
goal: One sentence — why this automation exists (≤160 chars).
output: What is public when a run ends (a TikTok post with the cart link).
host: contabo                           # optional default for nodes: contabo | mac | winbox | cloud
trigger:
  kind: manual                          # manual | cron | queue | event
  by: CEO                               # manual: who starts a run
  # cron: "0 9 * * 1-5"                 # cron: 5 fields …
  # tz: Asia/Bangkok                    # … and the IANA zone, always (F9)
  # source: claudeflow:queue/bl         # queue | event: where items come from
watcher: CMO@contabo                    # role@host that watches every run
budget:
  cash_usd: 2.00                        # API credit one run may spend; required when any api/model node exists
  plan_usd_eq: 150                      # optional: agent-token ceiling per run, in API-equivalent USD
phases:                                 # optional; when present every node names one
  - {id: pre, name: Script and approval}
  - {id: gen, name: Generation}
nodes:
  - id: tts                             # [a-z][a-z0-9_]*, unique, stable (§6)
    name: Voice (TTS)                   # ≤24 chars — the card title
    does: Turns the approved script into the avatar's Thai voice track.   # one sentence, ≤120 chars
    phase: gen
    kind: api                           # §3
    after: [drive]                      # ids this node waits for; [] = a start node
    tool: claudeflow:pipelines/tts.py   # this repo: tools/x.py · another repo: <repo>:<path>
    provider: fal                       # the id the cost ledger uses
    unit_cost: {usd: 0.00058, per: second, source: claudeflow:docs/costs.md, date: "2026-09-30"}
    output: Work/<ep>/voice.wav
    verify: {cmd: "python tools/check_audio.py Work/<ep>/voice.wav"}   # exactly one of cmd | check | human
    gate: Duration within ±5% of the script estimate.
    on_fail: {retry: 2}                 # optional: {retry: n} | {retry_from: <ancestor id>, max: n}
    blockers: [credit, key, upstream]   # optional: what can stop it (§4)
    expect_min: 2                       # optional: typical minutes; the watcher flags 3× as late
    measured:                           # optional, append-only; newest last
      - {date: "2026-09-30", cost_usd: 0.04, minutes: 1.5, source: task-c32c40e8}
  - id: publish
    name: Publish
    does: Posts the approved cut to TikTok with the cart link.
    kind: code
    after: [review]
    tool: tools/bl_tiktok_cta.py
    verify: {check: "the post URL opens and the cart link is live"}
    release: true                       # the public-release node; at least one per flow (F5)
```

Node keys, all of them: `id name does phase kind after tool provider model role skill approver unit_cost
output verify gate on_fail blockers stage graduate release replaces host expect_min measured`. `model` is the
model id an `api`/`model` node calls; `measured` entries take `date cost_usd turns minutes source`.

## 3 · Node kinds

| kind | What runs | Uses tokens? | Required keys | Stage |
|---|---|---|---|---|
| `code` | a script, no model | no | `tool` | always auto (omit `stage`) |
| `api` | an external generation or data API (fal, Kling, ElevenLabs, OpenRouter image) | no — API credit | `tool`, `provider` | always auto |
| `model` | ONE model call, no agent loop (a one-shot scripter, a Jev decision) | yes | `tool`, `provider` | always auto |
| `agent` | a Claude session works the step with a skill | yes, many | `role`, `skill` | `agent` · `shadow` · `auto_review` |
| `human` | a person decides or approves | no | `approver` | none: approvals are not on the ladder |

`role` is a key of `policies/agents.yaml` (`cmo`, `video_editor`, `browser_operator` …). `skill` is an org skill
folder name. `approver` is `CEO` or a role key.

## 4 · Vocabularies

**Stages — the graduation ladder** (only `agent` nodes climb it):

| stage | Ships | Beside it | Needs |
|---|---|---|---|
| `agent` | the agent's output | nothing yet | — |
| `shadow` | the agent's output | the candidate runs on the same input; the scorer compares | `graduate.candidate` + `graduate.scorer` |
| `auto_review` | the candidate's output | an agent or the CEO spot-checks a sample | same |
| graduated | — | the node becomes `kind: code`/`model` with `tool:` = the candidate, **same id** | — |

`graduate: {candidate: <path>, scorer: <path>, bar: "<the promotion bar>"}`. No scorer, no promotion (F10).
Default bar until the CEO rules on it (one of the plan's five open decisions): shadow → auto_review after 10
consecutive runs with the scorer passing 10/10 at ≥95% of the agent's score and 3 samples the CEO approved;
auto_review → graduated after 20 clean runs; back one step on 2 failures in the last 10.

**Blocker codes** — what a node can stop on, and who must act. The board paints red for the CEO, orange for
the agent.

| Red — waits for the CEO | Orange — the watcher fixes it |
|---|---|
| `credit` (402, balance out) · `login` (a web session lost, a QR or 2FA) · `key` (API key expired or revoked) · `quota` (a plan window spent) · `money` (a spend that needs his OK) · `account` (suspended, banned) | `bug` (the tool threw) · `verify_fail` · `upstream` (5xx or timeout after retries) · `input` (an earlier node's output is bad) · `rate_limit` (wait and retry) |

A run escalates an orange blocker to red when the watcher fails it twice.

**verify** — exactly one key: `cmd` (a command; exit 0 passes), `check` (what the watcher looks at),
`human` (who confirms: `CEO` or a role key).

## 5 · Binding to SKILL.md

`SKILL.md` keeps one heading per node, under `## The steps`, in an order where every node comes after all of its
`after` nodes:

```
### Step <n> · <node name> [node: <id>]
```

`<n>` counts up by one from the first step; `<node name>` equals the node's `name`. A `### Step` heading with no
`[node: …]` tag is an error in a workflow that has a `flow.yaml` (F12).

## 6 · Changing a flow

- **A node id never changes**: run history (`flow_node_runs`) and every STATUS.md key on it. To rename, give the
  new node `replaces: [<old id>]`; `flow-lint.py check --base <rev>` reports an id that vanished without one.
- **Graduating a node** keeps its id and changes its `kind` and `tool` (§4).
- **A new required key or a changed meaning** is a new schema (`mooniex.flow/v2`) with a migration note here.
- Commit the two files together: `skill(<name>): …` per ALL_Protocol_SkillAuthor §5.

## 7 · The rules — `scripts/flow-lint.py` (skill-lint code 18)

A lint, never a gate (ADR 0022 decisions 4 and 10). Every finding names its rule.

| Rule | Checks |
|---|---|
| F1 | a `kind: workflow` skill has `flow.yaml` beside `SKILL.md`; it parses to a mapping; `skill` = the folder name |
| F2 | `schema` is `mooniex.flow/v1`; no key outside §2 at the top, in a node, or in its sub-maps |
| F3 | `flow` matches `[a-z][a-z0-9_]*` and no other workflow uses it |
| F4 | node ids match `[a-z][a-z0-9_]*` and are unique; a `replaces` id is not also live; with `--base`, no id vanished without a `replaces` |
| F5 | every `after` id exists; no cycle; at least one `release: true`; every node reaches a release node; `retry_from` names the node itself or an ancestor |
| F6 | `kind` is one of five with that kind's required keys (§3); `phase` names a declared phase; `on_fail` and `blockers` use §4's shapes and codes; `owner` = the skill's `owner:`; `watcher` is `<role>@<host>` |
| F7 | every node has `verify` with exactly one non-empty key of `cmd`, `check`, `human` |
| F8 | money: an `api`/`model` node names a `provider`; a flow with one has `budget.cash_usd` |
| F9 | trigger: `kind` in the four; `cron` needs a 5-field `cron` and an IANA `tz`; `manual` needs `by`; `queue`/`event` need `source` |
| F10 | stage: `agent` nodes carry one of the three; `shadow`/`auto_review` carry `graduate.candidate` and `graduate.scorer`; other kinds carry none or `auto` |
| F11 | `tool`, `graduate.candidate`, `graduate.scorer` exist in this repo (a `<repo>:` path is not checked); `skill` is an org skill; `role` and a role `approver` are keys of `policies/agents.yaml` |
| F12 | SKILL.md has exactly one `### Step <n> · <name> [node: <id>]` per node, numbered from the first by one, names equal, in an order that respects `after`; no untagged `### Step` |
| F13 | sizes: flow `name` ≤40, `goal` ≤160, node `name` ≤24, `does` ≤120 and one line |
| F14 | every `unit_cost` and `measured` entry carries `source` and a `YYYY-MM-DD` `date`; no value looks like a secret |

```bash
python scripts/flow-lint.py check                       # every workflow skill
python scripts/flow-lint.py check CMO_Workflow_ShortFilm --base origin/main
python scripts/flow-lint.py export CMO_Workflow_ShortFilm   # the JSON the board draws (§8, §9)
```

## 8 · How the board reads it

| On the board | From |
|---|---|
| Flow list row | `name`, `goal`, `owner`, `trigger` (the schedule in words), `watcher`, `budget` |
| Column / lane header | `phases` (order as written) |
| Node card: title · tag | `name` · `kind` + `provider` (api/model), `role` (agent), `approver` (human) |
| Node card badge | the effective stage (§9) |
| Arrows | `after` |
| Node detail panel | `does`, `tool`, `skill`, `provider`, `unit_cost`, `output`, `verify`, `gate`, `on_fail`, `blockers`, `stage`, `graduate`, `measured`, `host` |
| Run colours, the running dot, blocker red/orange | run events, never the file; events carry `{flow, run, node}` ids from this file |

## 9 · Computed values — defined once, so the board and the reports agree

`flow-lint.py export` is the reference implementation; the Console computes the same numbers.

- **depth** — 0 for a start node, else 1 + the largest depth among its `after` nodes; the board's column.
- **effective stage** — `code`/`api`/`model` → `auto`; `human` → `human`; `agent` → its `stage`.
- **auto % by steps** — non-human nodes whose effective stage is `auto` or `auto_review` ÷ all non-human nodes.
- **cost per run** — the sum, per node, of its newest `measured.cost_usd`; a node with none is listed as
  unknown, never guessed.
- **auto % by cost** — the cost of auto nodes ÷ the known cost per run.

## 10 · STATUS.md — the run's state (until run events replace it)

```
flow: <flow id> · run: <YYYY-MM-DD>-<slug>
node: <current node id> · state: running | waiting:<approver> | blocked:<blocker code>
done: [<node ids>]
blocker: <code> — <one line>        # empty when none
spent: $<cash> API · <turns> turns
```
