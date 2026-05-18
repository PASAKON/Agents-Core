# Agents/ — Virtual Org for /Users/gob/Projects/

Multi-agent orchestration. Hierarchical: CEO (you) → CTO → DEVs.

Lives at `/Users/gob/Projects/Agents/` — single top-level home for all
agent control + infra.

## Architecture

```
CEO (you)
 └─ CTO (Opus 4.7) — orchestrator, reviewer, sole git-merger
     ├─ Backend DEV (Sonnet 4.6)
     ├─ Frontend DEV (Sonnet 4.6)
     ├─ DevOps DEV (Sonnet 4.6)
     └─ QA (Haiku 4.5)
```

## Key Concepts

- **Wiki** at `/Users/gob/Projects/LLMs/` — read by all, write by C-level only.
- **Per-task worktree** — every DEV gets isolated git worktree on a dedicated branch.
- **CTO is sole merger** — DEVs cannot push to main or delete branches.
- **SQLite task queue** at `state/tasks.db` — single source of truth.
- **Append-only logs** at `state/logs/` — observability via `tail -f`, tmux, or TUI.

## Active Projects (Phase 1)

- mooniex-claudeflow
- mooniex-webapp (Desk-A)
- LLMs (the wiki — C-level write only)

Add a project: append to `config/projects.yaml`.

## Quick Start

```bash
cd /Users/gob/Projects/Agents
source .venv/bin/activate            # one-time: bash scripts/setup.sh
python main.py --init                # one-time
python main.py "build /health endpoint for mooniex-claudeflow"

# separate terminal — pick one:
python dashboard.py                  # TUI (Textual)
bash scripts/watch.sh                # 4-pane tmux
tail -F state/logs/cto.log           # raw log stream
```

Optional shell aliases:
```bash
echo 'source /Users/gob/Projects/Agents/scripts/aliases.sh' >> ~/.zshrc
# then: agents-run "..."  agents-dash  agents-watch  agents-status
#       agents-chat       — interactive CTO REPL in current terminal
#       agents-spawn      — open iTerm window: CTO chat + 2 log tabs
#       agents-dev-logs   — tail all *_latest.log dev streams
```

## Chat with the CTO

Multi-turn conversation with the CTO instead of one-shot requests.

**Inline (current terminal):**
```bash
agents-chat              # picker: resume prior session or start new
agents-chat --new        # always fresh
agents-chat --last       # resume most recent
agents-chat --resume <session_id>
```

Slash commands inside the REPL: `/help /exit /new /list /resume <id> /stats
/tasks /clear`. Multiline input: end a line with `\`.

**Spawn dedicated iTerm window (3 tabs):**
```bash
agents-spawn             # tab1=CTO chat, tab2=cto.log, tab3=dev logs
agents-spawn --last      # passes --last through to cto_chat
```

The CTO REPL keeps a persistent `ClaudeSDKClient` open across turns and
auto-persists conversation history via the SDK session store, so `--resume`
or the picker brings back full context from prior runs. When the CTO
delegates, DEV reports stream into `state/logs/*_latest.log` (tab 3 of
`agents-spawn`), and the final summary prints back in the CTO chat tab.

## Permission Model

| Tool                | CTO | DEV | QA  |
|---------------------|:---:|:---:|:---:|
| wiki_read           | yes | yes | yes |
| wiki_write          | yes | no  | no  |
| create_task         | yes | no  | no  |
| delegate_task       | yes | no  | no  |
| review_diff         | yes | no  | no  |
| merge_task (+ push) | yes | no  | no  |
| Read / Glob / Grep  | yes (anywhere) | yes (cwd=worktree) | yes (cwd=worktree) |
| Write / Edit / Bash | yes (anywhere) | yes (cwd=worktree) | yes (cwd=worktree) |

Full matrix: `policies/permissions.md`.

## Layout

```
/Users/gob/Projects/Agents/
├── runners/             python entrypoints
│   ├── cto.py             orchestrator
│   └── dev.py             generic worker
├── roles/               system prompts (markdown)
│   ├── cto.md
│   ├── frontend_dev.md
│   ├── backend_dev.md
│   ├── devops.md
│   ├── qa.md
│   └── _dev_shared.md     shared DEV report format
├── tools/               MCP tools agents can call
│   ├── wiki.py            read=all, write=C-level
│   ├── worktree.py        git worktree per task
│   ├── delegate.py        CTO spawns DEV subprocess
│   └── git_ops.py         merge + push (C-level only)
├── policies/            permissions
│   ├── agents.yaml        role → model + flags
│   └── permissions.md     human-readable matrix
├── prompts/             reusable prompt fragments (future)
├── lib/                 infra (db, logger, notify, config loader)
├── config/              projects.yaml (project registry)
├── state/               runtime data
│   ├── tasks.db           SQLite queue
│   ├── logs/              per-agent append-only logs
│   ├── reports/           finalized reports
│   └── locks/             lock files
├── worktrees/           isolated git worktrees per task
├── scripts/             setup.sh, watch.sh, aliases.sh
├── main.py              CEO entrypoint
├── dashboard.py         Textual TUI
└── requirements.txt
```

## Adding a Role

1. Append to `policies/agents.yaml`:
   ```yaml
   roles:
     designer:
       level: w
       model: claude-sonnet-4-6
       can_write_wiki: false
       can_merge: false
       can_push: false
       workspace_only: true
   ```
2. Create `roles/designer.md` with responsibilities + report format.
3. Add `designer` to `agents_allowed` in relevant projects (`config/projects.yaml`).

CTO can now delegate to designer.

## Adding a Tool

1. Add `tools/<name>.py` with pure functions.
2. Register `@tool(...)` wrapper in `runners/cto.py` (CTO-level) and/or
   `runners/dev.py` (DEV-level), routing through a permission gate.
3. Add tool ID to `allowed_tools=[...]` in the runner.
4. Document in `policies/permissions.md`.
