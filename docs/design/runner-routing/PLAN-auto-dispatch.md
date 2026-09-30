# Auto-dispatch — the org picks the machine, the provider and the model (plan, 2026-09-30)

**Order:** CEO 2026-09-30, to CTO #24ca1c0a (quota side) with CTO #e6754203 (machine side).
**Status:** plan agreed between the two CTOs; building. **Rule it becomes:** IRON-RULES §59 (rewritten, R1).

> CEO (verbatim, abridged): "เมื่อ Spawn C-Level ออกมาแล้วเริ่มสั่งงาน … วิเคราะห์ว่าจะสั่งงานไปที่เครื่องไหน
> … เครื่องไหนใช้งานหนักอยู่แล้ว Ram + CPU หลีกเลี่ยงไปใช้อีกเครื่องนึง แล้วจะเอางานกลับมาผ่านช่องทางไหน Drive หรือ
> Github … Usage จะต้องรองรับทั้ง Claude Codex และ AGY … ใช้ตัวไหนดูจาก limit Weekly เป็นหลัก … คำนวณว่า Claude 20$
> Codex 20$ AGY 100$ มีโอกาส Hit Limit ไหม … ต้องมี Tools อยู่แล้วไม่ให้คำนวณสดทุกรอบ และ Tool จะต้องปรับเปลี่ยน Limit
> ได้ตลอดเวลา … เขียนเป็นกฎที่ Agent เห็นได้ง่ายและจะทำตามแน่นอน … ลดขั้นตอนการคิดสำหรับ Agent ออกไปสร้าง Tool และ
> API … ประหยัด Token ให้ได้มากที่สุด"

## 1. The target: one call, no thinking

A C-level creates the task and calls `delegate_task(task_id)` with **host and runner empty**. The tool
decides everything and writes one line to `delegate_log`:

```
dispatch: contabo · agy gemini-3.8-flash-high · bucket agy-gemini 98.9%→97.9% (M ≈1.0%) reserve 10% ok · return branch+REPORT.md · load 0.4/core ram 9.1 GB
```

The agent reads that line; it never ranks providers, reads quotas or checks RAM itself. An explicit
host or runner still wins (Flow on winbox, a CEO order, an A/B test) and is logged as `manual:`.

## 2. Quota buckets, not runners

A bucket is one limit that runs out. Candidates in `plans.yaml roles:` map to a bucket by runner and
model.

| bucket | plan | candidates | reader |
|---|---|---|---|
| `claude` | $20 (was $200 until 2026-09-29) | `claude:*` — **shared with every C-level session** | Contabo usage monitor |
| `codex` | $20 | `codex:*` | Contabo codex session logs |
| `agy-gemini` | $100, shared plan | `agy:gemini-*` | `agy /usage` group "Gemini Models" |
| `agy-claude` | same $100 plan, its own limit | `agy:claude-sonnet-4-6`, `agy:claude-opus-4-6-thinking`, `agy:gpt-oss-*` | `agy /usage` group "Claude and GPT models" |

agy's Claude models are **4.6**, not the 5.5 the org runs on Claude Code (`agy models`, 2026-09-30).

Measured 2026-09-30 ~02:10 BKK:

| bucket | weekly left | 5 h / daily left | weekly resets |
|---|---|---|---|
| claude | 73% | **8%** | 2026-10-06 |
| codex | 70% | unknown | 2026-10-05 |
| agy-gemini | 98.9% | 96.6% | 2026-10-06 |
| agy-claude | 100% | 100% | 2026-10-06 |

## 3. Forecast: "will this job hit the limit?" — precomputed, limits editable

- **Snapshot, not live reads.** A timer (every 10 min) writes `state/quota-snapshot.json` and appends
  `state/reports/quota-history.jsonl`. The router reads the snapshot when it is ≤ 15 min old; older, it
  falls back to today's cached live read. After the shared ledger (W1.10) the snapshot moves to a hub
  table so every box reads it without ssh.
- **Limits file, editable any time:** `config/limits.yaml`, one entry per bucket: `plan_usd`,
  `reserve_pct` (weekly share kept back; for `claude` it protects the C-level sessions),
  `min_5h_pct` (skip the bucket while its 5-hour window is below this). `tools/limits.py show | set
  <bucket>.<key> <value>` validates and writes it; no code change to move a limit.
- **Cost table:** `state/cost-table.json`, the share of a bucket's weekly one job uses, by bucket,
  model and size. Seeded with estimates (below) and replaced by learned values once a cell has ≥ 5
  samples. The learner uses only snapshot windows with **one** job on that bucket, or splits the
  delta evenly across concurrent jobs (#e6754203's note: overlap makes deltas noisy).
- **Size** is inferred, not asked: `S` = ≤ 2 touches and brief < 1,500 chars; `L` = > 6 touches or
  brief > 6,000 chars; else `M`. `create_task(size=…)` overrides.
- **Verdict:** `after = weekly_left − cost`. `ok` when `after ≥ reserve_pct` and the 5 h window ≥
  `min_5h_pct`; else `will_hit` and the candidate is skipped. Also a **burn-rate projection**
  (last 24 h of history): "at this rate the bucket reaches the reserve on <date>, before/after reset".
  If every candidate is `will_hit`, the task stays pending with the reason and the CEO is told once.

Seed costs (estimates [E], from the 2026-09-29/30 runs; replace as samples arrive):

| bucket | S | M | L |
|---|---|---|---|
| claude (Sonnet 5.5 worker) | 3% | 8% | 20% |
| codex | 1% | 3% | 8% |
| agy-gemini | 0.3% | 1% | 3% |
| agy-claude (Sonnet 4.6) | 1% | 3% | 8% |

Default limits (the CEO changes them with `tools/limits.py`): claude reserve 50%, min 5 h 30%;
codex reserve 20%; agy-gemini reserve 10%; agy-claude reserve 10%.

## 4. Machine pick (#e6754203)

- **Load per box** — reuse the `hosts` table (`lib/db.py`: free_gb, ram_free_gb, running,
  max_workers, provides, probed_at) and `tools/node_dispatch.py probe`. Add CPU load per core and the
  installed runners (`shutil.which` claude/codex/agy); a 60 s timer on each box.
- **pick_host** (`lib/router.py`, W2.6): the box provides what the job needs, probe ≤ 60 s old,
  running < max_workers, the project has `paths.<host>` in `config/projects.yaml`, then the lowest
  load. Behind `ORG_HOST_ROUTER`; on after the shared ledger (W1.10). Until then the hub's own box is
  the default, as today.
- **One call site:** `tools/delegate.py` host resolution calls `route.plan(role, size)` → ranked
  candidates → `router.pick_host(candidates, needs)` → the first candidate a box can run.

## 5. How the work comes back

| what | channel | who flips the row |
|---|---|---|
| code, text, any size | branch `agent/<runner>-<task>` + `docs/reports/<task>/REPORT.md` | W1.5 branch poller → `review` |
| image, video, audio, any size; any other binary > 1 MB | Google Drive per `CXO_Rules_GDrive_Filing`; the link goes in REPORT.md | same |

REPORT.md always has three headings: Files changed · What was done · Blockers. The launchers refuse to
commit media extensions (gate in the tool, #e6754203).

## 6. Work plan

| id | what | owner | touches | after |
|---|---|---|---|---|
| Q1 | agy both groups → buckets; `plans.yaml buckets:`; router ranks by bucket and returns it | 24ca1c0a → worker | tools/quota.py, tools/route.py, config/plans.yaml, their tests | — |
| Q1b | the chosen model reaches the CLI: `tasks.runner_model` column, the router writes it, `agy_local` uses it (Mac); then `agy:claude-sonnet-4-6` joins `dev_general` | 24ca1c0a → worker | lib/db.py (tasks only), tools/delegate.py `_route_runner`, runners/agy_local.py, runners/worker_init.py, config/plans.yaml | Q1; lib/db.py serialized with H1 |
| Q2 | snapshot writer + reader + timer files (launchd, systemd) | 24ca1c0a → worker | tools/quota.py, tools/route.py, scripts/com.mooniex.quota-snapshot.plist, deploy/systemd/quota-snapshot.{service,timer} | Q1 |
| Q3 | `config/limits.yaml`, `tools/limits.py`, `tools/forecast.py`, `route.plan()` + `--plan` CLI | 24ca1c0a → worker | new files + tools/route.py | Q2 |
| H1 | probe: CPU per core + runners; 60 s timers | e6754203 | tools/node_dispatch.py, lib/db.py | — |
| H2 | `lib/router.py pick_host` + the delegate call site, flag `ORG_HOST_ROUTER` | e6754203 | lib/router.py, tools/delegate.py | Q3, H1 |
| H3 | media gate in the W0.6 report step; the Contabo agy command takes `--model` from the row instead of the hardcoded `gemini-3.8-flash-high` | e6754203 | scripts/spawn-worker-remote.sh, windows/spawn-worker.ps1 | — |
| R1 | the rule: IRON §59 as a short card, playbook, DevSpawn §0, role files | 24ca1c0a | Agents-Rules, skills | Q3, H2 |
| ON | switch `ORG_HOST_ROUTER` on | e6754203 | env | W1.10 cutover |

Workers are routed by the router itself (IRON §59); the CTOs review and merge.
