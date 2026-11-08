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

## Step 2: Inspect & Verify Pre-Flight Environment Readiness (`preflight` + `inspect`)

Run `preflight` and `inspect --save` with the target project name (e.g. `CnDrama`, `CookieRun`, `ExpertAdvisor`, `KhaoHomSurvival`, `ChampaVeo`), short session ID (e.g. `3511068d`, `4ae68058`), or task ID (`task-xxxx`):

```bash
# 1. Verify Host-Affinity, In-Place Environment Readiness (.venv / node_modules / disk), and Transfer Limits:
/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/agy_takeover.py preflight "<target>"

# 2. Extract full state & save handoff bundle:
/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/agy_takeover.py inspect "<target>" --turns 12 --save
```

This extracts and verifies:
1. **Host-Affinity & Pre-Flight Readiness (`READY` vs `BLOCKED_WRONG_HOST` / `MISSING_ENV`)**:
   - **HARD RULE (`stay_on_host`)**: "Takeover" means switching the **Brain/Runner from Claude Code to AGY IN-PLACE on the original host and working directory (`cwd`)**, NEVER copying a host-pinned project (`CookieRun` on `winbox`, `EA`/MT5 on `contabo`+`winbox`, `Console`/`CnDrama` on `contabo`) to an unprovisioned machine.
   - **ZERO Package Reinstall**: Always use the pre-installed Python `.venv` (`venv_python` reported by `preflight`) and existing `node_modules` in `cwd`. **NEVER run `pip install` or `npm install` from scratch.**
2. **Transfer & Large-File Limits (Pointer-Only / Zero File Copy)**:
   - **Takeover Context Limit**: `<= 600 KB` JSONL tail + `<= 4 KB` brief (`0 bytes` of project files or media copied across hosts).
   - **Git Commit Limit**: `<= 1 MB` per binary; all media extensions (`.mp4`, `.mov`, `.png`, `.wav`, `.onnx`) blocked unless in `.media-allow`.
   - **Sparse Worktrees (`ADR 0030`)**: Tracked media `> 100 KB` automatically skipped on worker checkout.
   - **Large Files (`> 1 MB` to multi-GB)**: Leave in-place on the host (`~/MoonieXHQ/Work/<task>/` or `C:\Users\passg\cookierun-bot\label_review\`) and pass **only the file path pointer**, or use Google Drive / `rclone` (`CXO_Procedure_GDrive_BulkTransfer`).
3. **Original Session Brief** (`state/ph-briefs/project_head-<id>.md`)
4. **Drained Mailbox Messages** (`UserPromptSubmit` hook notifications that arrived on the exact turn Claude hit its limit)
5. **Last 12 Conversation Turns** & **Active Claude Skills** (`.claude/skills/<SkillName>/SKILL.md`)

## Step 3: Load the Matching Claude Skills (`SKILL.md`)

Read every `SKILL.md` listed under **Active Claude Skills** in the inspect output (located in `/Users/gob/MoonieXHQ/Agents/Core/.claude/skills/<SkillName>/SKILL.md` or `/opt/MoonieXHQ/Agents/Core/.claude/skills/<SkillName>/SKILL.md`). Follow their gates and procedures exactly as Claude Code would.

## Step 4: Execute the Remaining Work IN-PLACE on 100% AGY

Always execute commands **on the host that owns the session (`source_host`) inside its existing `cwd`**:
- **Mac (`mac`)**: Work directly in `cwd` using the pre-installed `.venv` Python.
- **Contabo (`contabo`)**: Run commands in-place over `ssh mooniex-vps 'cd <cwd> && ...'` or resume via the persistent AGY PH Brain:
  ```bash
  /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/agy_takeover.py resume "<target>"
  ```
- **Winbox (`winbox`)**: Run commands in-place over `ssh winbox` inside `<cwd>` (e.g. `C:\Users\passg\cookierun-bot` using `C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe` or `C:\Users\passg\AppData\Local\Programs\Python\Python311\python.exe`). Never move `CookieRun` or `MT5` execution off `winbox`.

## Step 5: Raising CardRun (`RUN-...` / `Q-...`) & Auto-Triggering AGY

To raise a Command Card or Question Card from AGY (or bind the taken-over Claude mailbox `<role>-<sid>` so the CEO's tap on `terminal.mooniex.com/run` wakes your AGY session automatically):

```bash
# Bind a taken-over mailbox (e.g. cto-6ebacd0e) to this AGY conversation:
.venv/bin/python tools/agy_card_run.py register --session <role>-<sid> --role <role>

# Raise a Command Card (auto-registers session + auto-triggers AGY when CEO taps Run):
.venv/bin/python tools/agy_card_run.py create --host contabo \
  --command "<command>" --why "<reason>" --expected "<expected>" --risk amber

# Raise a Question Card (auto-registers session + auto-triggers AGY when CEO taps Answer):
.venv/bin/python tools/agy_card_run.py ask \
  --question "<question>" --option "<opt1>" --option "<opt2>" --recommended 1 --why "<why>"
```
