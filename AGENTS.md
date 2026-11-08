# Agents Org Runtime — Antigravity (AGY) Entry Point

@[CLAUDE.md](CLAUDE.md)

---

## Antigravity (AGY) Runtime & CardRun Rules (Mandatory on every AGY session)

Every session running on Antigravity (Desktop App, IDE, or `agy` CLI on Mac, Contabo, and Winbox) shares the same central org memory (`Agents/Memory/`), rules (`Agents/Rules/IRON-RULES.md`), skills (`Agents/Core/.claude/skills/`), and Run Inbox (`terminal.mooniex.com/run`) as Claude Code:

1. **Always use CardRun (`tools/ask_run.py` or `tools/agy_card_run.py`) for CEO questions and commands:**
   - **Never** use the IDE `ask_question` tool to ask the CEO a question, and **never** leave a question or a `!` command waiting in chat (CEO 2026-09-26 & 2026-10-30, skill `ALL_Protocol_RunInbox`).
   - Raise a **Question Card** (`Q-...`) immediately whenever a decision/choice belongs to the CEO:
     ```bash
     /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/ask_run.py ask \
       --question "<คำถามสั้นกระชับ ≤90 ตัวอักษร>" \
       --option "<ตัวเลือกที่ 1>" --option "<ตัวเลือกที่ 2>" \
       --recommend 1 --why "<เหตุผล ≤90 ตัวอักษร>"
     ```
   - Raise a **Command Card** (`RUN-...`) whenever a command requires CEO approval or runs on another host:
     ```bash
     /Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/ask_run.py create \
       --host <contabo|mac> --command "<command>" \
       --why "<เหตุผล ≤90 ตัวอักษร>" --expected "<ผลลัพธ์ที่คาดหวัง>" --risk <green|amber|red>
     ```
2. **Automatic Session Binding & Reactive Wakeup (Zero Polling):**
   - `tools/ask_run.py` and `tools/agy_card_run.py` automatically detect this AGY conversation (`ANTIGRAVITY_CONVERSATION_ID` / `ANTIGRAVITY_LS_ADDRESS`), bind `state/agy-sessions/<box>.json`, and start a detached background watcher (`watch_card`) on Mac/Winbox (or `mail_wake.py` on Contabo).
   - After raising a card, print the Card ID and `https://terminal.mooniex.com/run#<id>` in one short line and **end your turn immediately**.
   - The moment the CEO taps the card on `/run`, `wake_session()` wakes this exact Antigravity Desktop App window (via `agentapi send-message`) or headless `agy` CLI conversation (via `agy -p --conversation <uuid>`) automatically with the CEO's answer and notes.
