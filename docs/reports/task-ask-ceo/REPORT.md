# task-4a53167b — the requester side of Run Inbox question cards (`ask`, `ask_ceo`)

Contract (read, not changed): `docs/design/run-inbox/QUESTIONS.md` in the live checkout
(`/opt/MoonieXHQ/Agents/Core`, not in this worktree) — §1, §2, §3, §3.1–3.3, §5, §6, §9.
Branch `agent/developer-task-4a53167b`, cut from origin/main 6ffb8069.

## WORKLOG

- **Base totals, before any edit** (interpreter `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`, worktree cwd):
  - `python -m pytest tests/test_ask_run.py tests/test_w42b_node_token_cards.py` → 127 passed.
  - `python -m pytest tests/test_spawn_coo.py` → 62 passed, 1 xfailed, 1 failed
    (`test_send_shares_the_letter_for_coo_but_not_for_other_roles`: `lib.db.ArchivedDB` — this
    worktree's process has no hub env; fails on a clean checkout, unrelated to this task).
  - `python scripts/test_org_tools_registry.py` (harness, ignored by pytest.ini) → 30 PASS, 0 FAIL.
- Read: QUESTIONS.md, tools/ask_run.py, tests/test_ask_run.py (FakeHub), lib/org_tools_registry.py,
  runners/cto_mcp_server.py, runners/cto.py (builds its tools from REGISTRY, so `ask_ceo` reaches it
  with no edit), scripts/lib/cxo_mcp_config.py (`_org_tool_names` = REGISTRY names).
