# REPORT task-f443d2f6: identity resolution fails closed

## Change
`tools/agent_transport.py`: `current_identity()` and `_resolve_sender_role()`
used to return the CEO for a process with no org identity in its env. Now they
raise `PermissionError` ("refused: this process has no org identity ..."),
unless the process is the CEO's own marked command. No other identity changes.
`_resolve_sender_role()` now also labels a worker `<role>#<task>`. It used to
fall through to "CEO", the same label `send_to_worker.send` already got from
`current_identity()`.

## Marker
No CEO marker existed anywhere in this repo or in MoonieX-Console, so this adds
one: `ORG_AS_CEO=1` (`agent_transport.CEO_MARKER`). It counts only when:
- its value is exactly `1`, and
- the env has none of these keys, whatever their value: `CXO_ROLE`,
  `CXO_SESSION_ID`, `CXO_SESSION`, `CTO_SESSION_ID`, `CTO_SESSION`,
  `ORG_SESSION_ID`, `ORG_PH_*`, `WORKER_*`, `CLAUDECODE`.

Every C-level, PH and worker launcher exports at least one of those, and Claude
Code sets `CLAUDECODE=1` in every command it runs. So a session's env, or
anything that inherits it, can never resolve as the CEO, even if it carries the
marker.

**Who sets it: no launcher or service.** The CEO writes it into the command
itself, e.g. a Run Inbox card `ORG_AS_CEO=1 python -m tools.send_to_cxo cto "..."`.
The card's bytes are approved with Face ID, and the Console executor
(`src/run/executor.js` `buildRunEnv`) passes only PATH/HOME/LANG/TERM/pagers.
A marked command from his own terminal works the same way.

Limit: an env flag stops accidental inheritance, not a deliberate same-user
process. On both machines every agent runs as the same OS user. The real
boundary stays the classifier plus Face-ID cards
(docs/design/org-restructure-p2.md, "Next security item").

## Callers of the fallback (line numbers at 531ca4b5)
Direct:
- tools/agent_transport.py:128 `_resolve_sender_role`, :169 `current_identity`.
- tools/send_to_cxo.py:601 spawn, :833 send, :872-873 label, :881 PH owner, :897 PH send. The CLI already maps PermissionError to exit 4.
- tools/send_to_worker.py:311-312 send. The CLI caught only ValueError, so a refusal is a traceback, exit 1.
- lib/ceo_report.py:347 report_to_ceo. Raises in a bare env.
- tools/skill_objection.py:82 raise_objection. Raises in a bare env.
- tools/spawn_ph.py:106 (catches → refused), tools/portfolio.py:285 (catches → read-only; the CEO `force` release at :356 now needs the marker), scripts/skill-curator.py:527 (catches → actor `unknown/-`).
- lib/org_tools_registry.py:337-353 MCP `send_to_cxo`. Runs inside a session's MCP server, so it has a session env and is unaffected.

Relied on the fallback, not the CEO:
- runners/watchdog.py:288-296 `_send_ping` runs `python -m tools.send_to_worker` in the unit's own env (deploy/systemd/mooniex-watchdog.service, scripts/com.mooniex.agents-watchdog.plist). That env has no identity, so **status-check pings to silent workers are now refused** (logged as a warning). Fix proposed below, not applied.
- runners/watchdog.py:967 → tools/delegate.py:731/876: in the watchdog's env the kickoff letter is refused. It is wrapped in try/except, and the worker starts without it.

Not affected (each sets its own identity or reads its own env): runners/relay_mcp_server.py:930 and runners/mac_agent.py:397 (the CEO's Telegram/LINE relay, explicit `secretary` identity), tools/tool_value.py:1612-1643 (sets `cto/tool-value`), scripts/hook-inbox.py:85, tools/ask_run.py:383, lib/mailbox.py:624. Console chat types into tmux and calls no sender.

## Tests
- New: tests/test_identity_fail_closed_opus.py (61 tests). Covers: a bare env is refused; the marked command, including in exactly the Run-card env, is the CEO; the marker next to any session key, or inside a worker / half-worker / C-level / PH env, changes nothing; worker, C-level, CTO and PH resolve as before; `send_to_cxo` from a bare env writes nothing and the CLI exits 4.
- 65 existing tests in 13 files sent from a bare env meaning "the CEO". They now use a `ceo_command` fixture in conftest.py that sets the marker and strips session keys. Two assertions of the old behaviour were rewritten: skill-curator actor, PH briefing.
- The 14 touched test files, with the worker and Claude Code env stripped: 1038 passed, 0 failed.
- 58 identity/mail test files, run from this worker's env: 2886 passed, 2 failed, 205 skipped. Before the change: 2821 passed, 6 failed. All 6 came from this worker's env, not the code. 4 of them pass now. The 2 left are tests/test_ph_on_mac.py::test_card_command_passes_ask_run_checks (ask_run refuses inside a worker) and tests/test_tool_value.py::test_send_to_coo (live-integration guard).

## Not done / not verified
- Blocked by the self-repo guard: these paths were not in this task's touches:
  - runners/watchdog.py: ping as `cto/watchdog` when the env has no identity.
  - tools/send_to_worker.py: CLI exit 4 on PermissionError, plus docstring. Edited in the worktree, uncommitted.
  - tools/send_to_cxo.py: docstring. Edited in the worktree, uncommitted.
  - lib/ceo_report.py: return `rejected:` instead of raising.
  - tools/portfolio.py:41: the docstring still says a bare env is the CEO.
- Not verified:
  - Whether the CEO runs org senders unmarked anywhere else (Mac terminal, Claude app).
  - Whether Claude Code sets `CLAUDECODE` for hooks and MCP servers, not only for Bash commands.
  - The node-dispatch process env.
  - Whether the Console executor's `bash -lc` profile adds a session key.
  - No live service was run.
- Out of scope, flagged: `ceo` is in the `c_level` roster (policies/agents.yaml:323, lib/config.py:63), so `CXO_ROLE=ceo` plus any session id resolves as a CEO-roled C-level. Not the fallback, so left unchanged.
