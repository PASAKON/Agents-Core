---
name: spawn-web-designer
owner: CTO
origin: mooniex-org
scope: >-
  Boots the open-design daemon and web UI at localhost:3000 via
  scripts/spawn-web-designer.sh so the CEO can design hands-on. This is the
  CEO-driven path — the CTO autonomous route is delegate_task web_designer.
description: Open the Web Designer surface for the CEO to design directly. Trigger on /spawn-web-designer and when the CEO says "spawn web designer", "เปิด web designer", "เปิดหน้าออกแบบ", "open the designer".
created_by: human
audience: [cto]
---

# Spawn Web Designer — CEO hands-on design surface

The CEO wants to design something **themselves** in the open-design
(claudesign) Web UI. This skill just boots that surface. It is the
**§4b CEO-driven path** in `playbooks/web-designer.md` — distinct from the
CTO autonomous `delegate_task web_designer` flow (§4a), which spawns a
claude agent in an iTerm tab and needs no Web UI.

Per memory [[web-designer-harness-vs-developer]]: CEO-driven = this script;
CTO autonomous = `delegate_task`. Don't confuse them.

## Do this

Run the boot script — don't ask, just run it:

```bash
bash /Users/gob/Projects/Agents/scripts/spawn-web-designer.sh
```

It (headless by default):
1. starts the open-design **daemon** on port `7456`,
2. starts the **web UI** (Next.js) on port `3000`,
3. waits for port 3000, then opens `http://localhost:3000` in the browser.

The CEO then prompts the design interactively in that browser tab.

## Flags the CEO may add

| Flag | Effect |
| --- | --- |
| `--status` | show running state (daemon/web ports, pids, logs) |
| `--stop` | kill daemon + web |
| `--restart` | stop then start |
| `--no-open` | start but don't open the browser |
| `--with-iterm` | also open iTerm log tabs (debug) |

Map natural language: "เช็คว่ารันอยู่ไหม" → `--status`; "ปิด" / "stop" →
`--stop`; "รีสตาร์ท" → `--restart`.

## After running, confirm briefly

State that the open-design app is up at **http://localhost:3000** (daemon
on 7456) and the browser opened. If `--status` shows it already running,
say so instead of double-starting (the script is idempotent — it no-ops if
the ports are already open).

## Notes / failure modes

- Needs `pnpm` on PATH and the project dir
  `/Users/gob/Projects/mooniex-claudesign/` (the script checks both and
  exits with a clear message if missing).
- Logs: `state/web-designer/daemon.log` + `web.log` (in the Agents repo).
  If port 3000 never opens within 60s, tail `web.log`.
- This surface is for **CEO hands-on** use. To have an agent build a design
  artifact autonomously, use `delegate_task` on a `web_designer` task with
  the claudesign **project UUID** in the description (playbook §4a / §9) —
  not this skill.
