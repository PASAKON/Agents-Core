# Agents Org Runtime — Antigravity (AGY) Entry Point

@[CLAUDE.md](CLAUDE.md)

@[../Memory/MEMORY.md](../Memory/MEMORY.md)

---

## Antigravity (AGY) Runtime & CardRun v2 Rules (Mandatory on every AGY session)

Every session running on Antigravity (Desktop App, IDE, or `agy` CLI on Mac, Contabo, and Winbox) shares the same central org memory (`Agents/Memory/`), rules (`Agents/Rules/IRON-RULES.md`), skills (`Agents/Core/.claude/skills/`), and Run Inbox (`terminal.mooniex.com/run`) as Claude Code:

1. **Always send in the name of `PH` + Project Name (NEVER as `CTO` or `CMO`) and use CardRun v2 brief fields:**
   - **Never** send a card in the name of `CTO` or `CMO` from AGY. All AGY sessions send as `role="project_head"` with `--project <ProjectName>` and `--lane <cto|cmo|coo|cfo|cgo>` so `terminal.mooniex.com/run` displays **`💻 PH#<id> · <ProjectName>`** (with the Mac `💻` emoji and lane badge).
   - **Never** use the IDE `ask_question` tool to ask the CEO a question, and **never** leave a question or a `!` command waiting in chat (CEO 2026-09-26, 2026-10-30 & 2026-11-16, skill `ALL_Protocol_RunInbox`).
   - Raise a **Question Card** (`Q-...`) immediately whenever a decision/choice belongs to the CEO:
     ```bash
     /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/ask_run.py ask \
       --project "<ProjectName>" --lane "<cto|cmo>" \
       --what "<หัวข้อสั้น ≤40 ตัวอักษร>" --does "<สิ่งที่ต้องการตัดสินใจ ≤70 ตัวอักษร>" --impact "<ผลกระทบ ≤70 ตัวอักษร>" \
       --question "<คำถามสั้นกระชับ ≤90 ตัวอักษร>" \
       --option "<ตัวเลือกที่ 1>" --option "<ตัวเลือกที่ 2>" \
       --recommended 1 --why "<เหตุผล ≤90 ตัวอักษร>"
     ```
   - Raise a **Command Card** (`RUN-...`) whenever a command requires CEO approval or runs on another host:
     ```bash
     /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/ask_run.py create \
       --host <contabo|mac|winbox> --project "<ProjectName>" --lane "<cto|cmo>" \
       --what "<หัวข้อคำสั่ง ≤40 ตัวอักษร>" --does "<คำสั่งนี้ทำอะไร ≤70 ตัวอักษร>" --impact "<ผลกระทบ ≤70 ตัวอักษร>" \
       --command "<command>" \
       --why "<เหตุผล ≤90 ตัวอักษร>" --expected "<ผลลัพธ์ที่คาดหวัง>" --risk <green|amber|red>
     ```
2. **Automatic Session Binding & Reactive Wakeup (Zero Polling):**
   - `tools/agy_takeover.py inspect`, `tools/ask_run.py`, and `tools/agy_card_run.py` automatically detect this AGY conversation (`ANTIGRAVITY_CONVERSATION_ID` / `ANTIGRAVITY_LS_ADDRESS`), bind `state/agy-sessions/project_head-<sid>.json` with `project` and `lane`, and start a detached background watcher (`watch_card`) on Mac/Winbox (or `mail_wake.py` on Contabo).
   - After raising a card, print the Card ID and `https://terminal.mooniex.com/run#<id>` in one short line and **end your turn immediately**.
   - The moment the CEO taps the card on `/run`, `wake_session()` wakes this exact Antigravity Desktop App window (via `agentapi send-message`) or headless `agy` CLI conversation (via `agy -p --conversation <uuid>`) automatically with the CEO's answer and notes.
3. **Claude <-> AGY Direct Messaging Bridge (`tools/send_to_agy.py`):**
   - When a Claude session (e.g. `cto-fresh`, `cmo-<sid>`, `project_head-<sid>`) sends a message into this AGY room (arriving as a high-priority `<SYSTEM_MESSAGE>`), reply directly from within the workspace (never `cd /tmp/...`):
     ```bash
     /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/send_to_agy.py reply <claude-box> "<reply>"
     ```
   - To list or message another AGY room across Mac, Contabo, or Winbox:
     ```bash
     /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/send_to_agy.py list
     /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/send_to_agy.py send <agy-box|uuid> "<message>"
     ```
