---
name: session-change-model
owner: CTO
origin: mooniex-org
scope: >-
  Proposes an escalation and hands the human the exact /model command to type — no
  tool lets the assistant switch models directly, and /model preserves full session
  history. Enforces the tier table in decisions/0009-model-routing-policy.md.
  Shared by CTO/CFO/CGO/CMO, all defaulting to Sonnet 5.
description: Propose a mid-session model escalation (Sonnet 5 → Opus 5) and wait for CEO confirmation. Trigger on /session-change-model and when a session on a lighter tier hits architecture, security, prod-deploy, final-merge, or cross-project work, or under-delivers twice.
created_by: human
audience: [cxo]
---

# Session Change Model — propose, confirm, hand off the exact command

CTO/CXO sessions now default to Sonnet 5 (see `decisions/0009-model-routing-policy.md`
— cheaper, "near-Opus on coding," fine for routine orchestration). Some tasks
genuinely need Opus 5. This skill is the calibrated bridge: recommend
escalation out loud, get an explicit yes, then tell the CEO exactly what to
type. It never silently escalates and never silently stays under-powered
either.

## Hard technical constraint — read this first

**No tool exists for the assistant to switch its own running model.** `/model`
is a local command the Claude Code CLI intercepts before it ever reaches the
model as a turn — same mechanism as `/clear`, `/help`. This skill cannot
"execute" a switch on the CEO's behalf. Its entire value is in the propose →
confirm → tell-them-the-keystroke sequence below. Do not imply or claim the
switch happens automatically once the CEO says yes — it happens the moment
they type the command themselves.

## Escalation triggers — check before proposing

Match against `decisions/0009-model-routing-policy.md` § Tier criteria:

- [ ] Architecture/system design call
- [ ] Security-sensitive code
- [ ] Anything prod-deploy-adjacent
- [ ] Final merge review / go—no-go decision
- [ ] Wiki/ADR writing requiring judgment
- [ ] Cross-project orchestration reasoning
- [ ] **Self-detected**: already attempted the same subtask twice at the
      current tier without a result you'd stand behind — this is the
      "Sonnet recognizes its own struggle" case, not just a static topic match

One match is enough to propose. Don't wait for several — surfacing it early
costs nothing (the CEO can decline), staying silent on a Tier-1 task costs
quality.

## What NOT to do

- Don't keep working a Tier-1-shaped task at the current tier without ever
  asking — that's the failure mode this skill exists to close.
- Don't propose more than once per threshold crossing. If the CEO already
  said no for this task, don't re-ask on the same task — flag it again only
  if the task's scope genuinely changes.
- Don't claim the switch is "done" before the CEO has actually typed it.

## Propose — exact format

```
งานนี้เริ่ม [เหตุผลสั้นๆ ตรงกับ trigger ที่ match — เช่น "แตะ prod deploy",
"ต้องตัดสินใจ architecture", "ลองมา 2 รอบบน Sonnet ยังไม่ได้ผลที่มั่นใจ"]

แนะนำเปลี่ยนเป็น Opus 5, effort: xhigh
ต้องการให้เปลี่ยนไหม?
```

Then **stop and wait**. Do not proceed with the heavy work on the current
tier while waiting for an answer — that defeats the point.

## On CEO confirm

Hand over the literal command — this is the one step only the human can do:

```
พิมพ์ตอนนี้ได้เลย:
  /model opus

(ไม่แน่ใจ alias ตรง — พิมพ์ /model เปล่าๆ แล้วเลือก "Opus 5" จาก picker ก็ได้)

History เต็มไหลต่อ ไม่หาย — แค่ prompt cache รีเซ็ต รอบแรกหลัง switch
อาจช้า/แพงขึ้นนิดนึงเพราะอ่าน history ใหม่ทั้งหมด ไม่ใช่บั๊ก

Effort: พอ switch ครั้งแรกในเซสชันนี้ Opus จะใช้ effort default ของตัวเอง
(ปกติคือ xhigh ตรงกับที่แนะนำอยู่แล้ว) — เช็คอีกทีถ้าต้องการระดับอื่นเจาะจง
(Opus 5 default effort ยังไม่ verify ว่าเปลี่ยนจาก 4.8 หรือไม่ — เช็คใน picker ถ้าไม่ชัวร์)
[ยังไม่ verify ว่ามีวิธีตั้ง effort สดระหว่าง session นอกจากค่า default ของโมเดล —
ถ้าต้องการ effort เจาะจงจริงๆ อาจต้อง relaunch ด้วย --effort flag แทน]
```

## On CEO decline

Continue at the current tier. Say so plainly if it affects confidence in the
output ("ทำต่อบน Sonnet — ถ้าผลออกมาไม่ชัวร์ จะแจ้งอีกที"). Don't re-propose
on the same task unless its scope changes.

## After the switch lands

One short acknowledgment, then continue normally — don't re-litigate the
decision or repeat context the history already carries:

```
อยู่บน Opus 5 ต่อจากนี้
```

## Output format

```
🔼 MODEL ESCALATION — <trigger matched>
Current : Sonnet 5
Proposed: Opus 5 @ xhigh
Reason  : <one line, specific to this task>
Status  : PROPOSED — waiting for CEO confirm
```

After resolution, append one line: `Resolved: SWITCHED` / `Resolved: DECLINED (stayed Sonnet 5)`.

## Operating rules

- Source of truth for tiers and effort levels: `decisions/0009-model-routing-policy.md`.
  If that ADR's table changes, this skill's trigger list and recommended
  effort value should be re-checked against it.
- Shared across CTO/CFO/CGO/CMO — all four C-level roles default to Sonnet 5
  with Opus 5 escalation per the ADR, so this skill applies to any of them,
  not just CTO.
- This skill governs **interactive CTO/CXO ↔ CEO sessions only**. Worker
  (DEV) tier escalation mid-task is a different mechanism — non-interactive
  workers can't pause to ask the CEO live. That path is: DEV flags "exceeded
  what I could handle at this tier" in its completion report → CTO re-delegates
  the task at a higher tier on the next iteration (extension of the existing
  CTO review step in `roles/cto.md`, not this skill).
- One proposal per escalation. Wait for an explicit yes/no — never assume
  silence means either answer.
