---
name: CTO_Knowledge_Haiku
kind: knowledge
description: KNOWLEDGE — What Claude Haiku 5.5 is in the org (a learning lane on the Claude subscription, CEO 14 Oct), what its one trial measured, how it is used today, and what is still unknown. Folded weekly from the tool-value report. Trigger on /CTO_Knowledge_Haiku, "Haiku ช่วยได้แค่ไหน", "ส่ง Haiku", "haiku worker", "runner-fit haiku". Do NOT use it for the paid-API model choice (CFO_Rules_Finance, ADR 0009).
owner: CTO
audience: [cxo]
created_by: agent
author: {role: cto, date: "2026-10-14"}
improved_by: []
aka: []
verified: "2026-10-14"
refresh_after: "2026-10-21"
---

# Haiku 5.5: facts and measured fit

Folded every week from `tools/tool_value.py` (the Haiku rows and the `claude-haiku` runner-fit cell). One sighting is
a Field note. A line enters the body only when ≥2 runs agree (ADR 0026).

## What it is (checked 2026-10-14)

- **The model:** `claude-haiku-5-5`, on the CEO's Claude subscription.
- **A learning lane, not an outside bucket** (CEO, 14 Oct). Send it small, low-risk jobs on purpose and record each
  one in runner_fit (tool-value addendum, 14 Oct).
- **The one trial (11 Oct) failed.** It tested two jobs against Sonnet, with a bar of 0.90:
  - note drafting: 0.66;
  - report summaries: 0.72.
  No other job type has been tested. Moving a job to Haiku for good needs a new trial (plan
  `docs/plans/tool-value-weekly-and-enforcement-2026-10-13.md` §2.1).
- **The one live use:** zero-cost token counting with `claude -p --model claude-haiku-5-5`. The context-delta
  measurements in the report come from it.

## Use (measured, Contabo transcripts, deduplicated by message id)

| Window | Assistant messages | Share of Claude-family output tokens |
|---|---|---|
| 6–12 Oct | 1 | 0% |
| 13–14 Oct | 4 | 0.01% |

The Mac and winbox are not read yet.

## How to send it a job: no path yet

- **No worker path.** `tools/delegate.py` takes a Claude worker's model from its role in `policies/agents.yaml`; a task
  cannot pick a model.
- **The only Haiku role** is `probe`, on Haiku 4.5, and it is limited to `docs/ops/mesh-probe/`.
- **So a Haiku 5.5 worker needs one of:**
  - a Haiku role in `policies/agents.yaml`;
  - a per-task model in `tools/delegate.py`, which the PH (OrgRestructure) is editing.
  Until one lands, Haiku work is `claude -p --model claude-haiku-5-5` run by a C-level.

## Not yet measured

- **Does Haiku use move the Claude weekly %?** Unverified (addendum, 14 Oct). Record it; don't assume.
- **Runner-fit:** 0 records so far.

## Field notes
- 2026-10-14 [MISSING] dispatch — the CEO's "send Haiku small jobs on purpose" (14 Oct) has no dispatch path: delegate picks the model by role, and the only Haiku role (`probe`, 4.5) is fenced to mesh probes · evidence: tools/delegate.py `role_cfg.get("model")`, policies/agents.yaml `probe`, session cto-dd03bac1 · status: pending
