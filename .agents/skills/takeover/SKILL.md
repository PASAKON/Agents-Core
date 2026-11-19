---
name: takeover
description: >-
  Emergency Claude Code to AGY session takeover across Mac, Contabo, and Winbox.
  Use this skill whenever the user types /takeover, asks to pick up stalled or
  quota-stopped Claude Code work, or wants to continue a previous Claude Code
  session (Project Head, C-level, or Worker) on Mac, Contabo, or Winbox using
  AGY and existing Claude skills.
---

# Emergency Claude Code -> AGY Takeover (`/takeover`)

When Claude Code hits its weekly/5-hour quota limit (or login expires), follow these exact steps to take over any in-progress session from **Mac**, **Contabo (`mooniex-vps`)**, or **Winbox (`winbox`)** using 100% AGY and the repo's existing Claude skills (`.claude/skills/`).

## Step 1: Scan All Hosts (`mac`, `contabo`, `winbox`)

If the user did not specify a project or session ID (e.g. they just typed `/takeover`), scan all 3 hosts immediately:

```bash
/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/agy_takeover.py scan --limit 10
```
*(On Contabo, use `/opt/MoonieXHQ/Agents/Core/.venv/bin/python /opt/MoonieXHQ/Agents/Core/tools/agy_takeover.py scan --limit 10`.)*

Present the stalled/quota-stopped sessions (`🚨 LIMIT`) clearly and ask which session/project they want to take over (or proceed immediately to Step 2 if they already named a project/session/host).

## Step 2: Inspect & Extract the Previous Claude Session's Full State

Run `inspect --save` with the target project name (e.g. `CnDrama`, `KhaoHomSurvival`, `ChampaVeo`, `SafeRestart`), short session ID (e.g. `3511068d`, `4ae68058`), or task ID (`task-xxxx`):

```bash
/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/agy_takeover.py inspect "<target>" --turns 12 --save
```

This extracts:
1. **Original Session Brief** (`state/ph-briefs/project_head-<id>.md`)
2. **Drained Mailbox Messages** (`UserPromptSubmit` hook notifications that arrived on the exact turn Claude hit its limit and were never acted upon)
3. **Last 12 Conversation Turns** (user prompts, assistant replies, and tool calls from the host's `.claude/projects/**/*.jsonl`)
4. **Active Claude Skills** (`SKILL.md` paths in `.claude/skills/<SkillName>/SKILL.md`)

## Step 3: Load the Matching Claude Skills (`SKILL.md`)

Read every `SKILL.md` listed under **Active Claude Skills** in the inspect output (located in `/Users/gob/MoonieXHQ/Agents/Core/.claude/skills/<SkillName>/SKILL.md` or `/opt/MoonieXHQ/Agents/Core/.claude/skills/<SkillName>/SKILL.md`). Follow their gates and procedures exactly as Claude Code would.

## Step 4: Execute the Remaining Work on 100% AGY

Depending on which host owns the session:
- **Mac (`mac`)**: Work directly in `/Users/gob/MoonieXHQ/Agents/Core` or the task's worktree.
- **Contabo (`contabo`)**: Run commands over `ssh mooniex-vps 'cd /opt/MoonieXHQ/Agents/Core && ...'` or hand the session to the persistent AGY PH Brain:
  ```bash
  /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/agy_takeover.py handoff-to-brain "<target>"
  ```
- **Winbox (`winbox`)**: Run commands over `ssh winbox` (using `C:\Users\passg\AppData\Local\Programs\Python\Python311\python.exe -` or PowerShell in `C:\Users\passg\mooniex\repo\MoonieX-Agents`).

## Step 5: Raising CardRun v2 (`RUN-...` / `Q-...`) as `💻 PH#<id> · <Project>`

Per CEO rule (2026-11-16), AGY sessions **never** send cards in the name of `CTO` or `CMO`. They always send as `role="project_head"` with the taken-over project name (`--project <ProjectName>`) and lane (`--lane <cto|cmo|coo|cfo|cgo>`), displaying **`💻 PH#<id> · <ProjectName>`** on `terminal.mooniex.com/run`.
Running `agy_takeover.py inspect "<target>"` automatically binds this AGY session to `project_head-<short_id>` with its `project` and `lane`.

```bash
# Explicitly bind or update a taken-over project identity on this AGY conversation:
.venv/bin/python tools/agy_card_run.py register \
  --session project_head-<sid> --role project_head --project <ProjectName> --lane <cto|cmo>

# Raise a Command Card v2 (auto-registers session + auto-triggers AGY when CEO taps Hold-to-Run):
.venv/bin/python tools/ask_run.py create --host contabo \
  --project <ProjectName> --lane <cto|cmo> \
  --what "<หัวข้อ ≤40 ตัวอักษร>" --does "<คำสั่งนี้ทำอะไร ≤70 ตัวอักษร>" --impact "<ผลกระทบ ≤70 ตัวอักษร>" \
  --command "<command>" --why "<reason>" --expected "<expected>" --risk amber

# Raise a Question Card v2 (auto-registers session + auto-triggers AGY when CEO taps Answer):
.venv/bin/python tools/ask_run.py ask \
  --project <ProjectName> --lane <cto|cmo> \
  --what "<หัวข้อ ≤40 ตัวอักษร>" --does "<สิ่งที่ต้องการตัดสินใจ ≤70 ตัวอักษร>" --impact "<ผลกระทบ ≤70 ตัวอักษร>" \
  --question "<question>" --option "<opt1>" --option "<opt2>" --recommended 1 --why "<why>"
```
