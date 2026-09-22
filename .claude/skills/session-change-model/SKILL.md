---
name: session-change-model
owner: CTO
origin: mooniex-org
scope: >-
  Puts a C-level session back on the org standard model (Opus 5.5, 1M context,
  effort xhigh — CEO 2026-09-23) when it is running on anything lighter, by
  handing the CEO the exact /model and /effort commands to type. No tool lets
  the assistant switch its own model, and /model keeps the full session
  history. Shared by CTO/CFO/CGO/CMO. Tier table in
  decisions/0009-model-routing-policy.md.
description: Put a C-level session back on the org standard model (Opus 5.5 1M @ xhigh) when it is running lighter, and wait for CEO confirmation. Trigger on /session-change-model, when a C-level notices it is on Sonnet/an older Opus/GLM (old launcher, restart onto a stale default, a /model downgrade), or when a new model ships and the CEO asks to move to it.
created_by: human
audience: [cxo]
---

# Session Change Model — propose, confirm, hand off the exact command

**Standard since 2026-09-23 (CEO):** every C-level runs **Opus 5.5 with the 1M
context window at effort xhigh** (`claude-opus-5-5[1m]`, `policies/agents.yaml`).
Workers keep their own tiers — Sonnet 5 workers stay on Sonnet 5; the two
Opus workers (security_engineer, devops_engineer) run `claude-opus-5-5` @ xhigh.

So there is nothing to escalate *to* any more. This skill exists for the
cases where a C-level session is **below** the standard and should be put
back, and for the day a newer model ships and the CEO wants to move.

## Hard technical constraint — read this first

**No tool exists for the assistant to switch its own running model.** `/model`
and `/effort` are local commands the Claude Code CLI intercepts before they
ever reach the model as a turn — same mechanism as `/clear`, `/help`. This
skill cannot "execute" a switch on the CEO's behalf. Its entire value is in
the notice → confirm → tell-them-the-keystroke sequence below. Never claim
the switch happened until the CEO has typed it.

## When a session is below the standard — check before proposing

- [ ] Launched before 2026-09-23 on `claude-sonnet-5` (every C-level spawned
      that morning was; `ps -axo command | grep -- '--model'` shows the flag)
- [ ] Came back from `/terminal-restart` or a resume onto an older default
- [ ] Someone switched it down with `/model` for a cheap stretch of work
- [ ] Running on a GLM/other-provider offload (`CXO_MODEL_PROVIDER` set)
- [ ] Effort below xhigh (`/effort` shows the live value)

One match is enough to mention it. Surfacing it costs one line; the CEO can
decline.

## Propose — exact format

```
session นี้วิ่งอยู่บน <โมเดล/effort ปัจจุบัน> — ต่ำกว่ามาตรฐาน org
(Opus 5.5 1M @ xhigh ตั้งแต่ 23 ก.ย.)
ต้องการให้เปลี่ยนไหม?
```

Then **stop and wait** for a yes or no.

## On CEO confirm

Hand over the literal commands — this is the one step only the human can do:

```
พิมพ์ตอนนี้ได้เลย:
  /model claude-opus-5-5[1m]
  /effort xhigh

(หรือพิมพ์ /model เปล่าๆ แล้วเลือก "Opus 5.5 (1M context)" จาก picker)
```

History carries over in full; only the prompt cache resets, so the first
turn after the switch is slower and costs more — that is expected, not a bug.
`/effort` changes the live effort directly (verified 2026-09-23: the CEO ran
`/effort` → xhigh and it applied to the running session).

## On CEO decline

Continue at the current model. Say so plainly if it affects confidence in the
output. Don't re-propose on the same task unless its scope changes.

## After the switch lands

One short acknowledgment, then continue:

```
อยู่บน Opus 5.5 (1M) @ xhigh ต่อจากนี้
```

## Output format

```
🔼 MODEL — below org standard
Current : <model> @ <effort>
Standard: Opus 5.5 (1M) @ xhigh
Status  : PROPOSED — waiting for CEO confirm
```

After resolution, append one line: `Resolved: SWITCHED` / `Resolved: DECLINED`.

## Operating rules

- Source of truth: `policies/agents.yaml` (what the launchers actually pass)
  and `decisions/0009-model-routing-policy.md` (why). If they disagree, the
  yaml is what runs — fix the ADR.
- A newer model shipping is **not** a reason to switch on your own: the CEO
  decides the standard; this skill only hands over the command once he has.
- Worker tiers are set per role in `policies/agents.yaml` and apply on the
  next spawn. A worker that feels under-powered says so in its report and the
  CTO re-delegates it at a higher tier (see `roles/_worker_shared.md`) — not
  this skill.
- One proposal per session state. Wait for an explicit yes/no.

## Field notes

- 2026-09-23 [WRONG] whole skill — it assumed C-levels default to Sonnet 5 and escalate to Opus 5; the CEO made Opus 5.5 (1M) @ xhigh the C-level default and moved the Opus workers to Opus 5.5 @ xhigh, Sonnet workers unchanged. Rewritten from "escalate" to "restore the standard" · evidence: CEO order in session cto-a29c7576 (fork 7f03193e); `policies/agents.yaml` now resolves cto/cfo/cgo/cmo → `claude-opus-5-5[1m]` xhigh; `claude -p --model claude-opus-5-5[1m] --effort xhigh` answered OK headless · status: promoted
- 2026-09-23 [MISSING] §On CEO confirm — the old text said effort could not be changed live ("may need a relaunch with --effort"); `/effort` does change it in the running session · evidence: CEO ran `/effort` → "Set effort level to xhigh" in this session · status: promoted
