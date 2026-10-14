# COO gate — SomPong delegates its own research workers

CEO card **Q-20261013-1948-4a33** (option 1, 2026-10-13): SomPong (the COO, unix user `sompong`) may
create and delegate `researcher`, `data_analyst` and `browser_operator` workers itself, never a code
role. Workers run as root like the CTO's (card Q-20261013-2010-091c); `data_analyst` and
`browser_operator` stay held until they have a box like the researcher's (card Q-20261013-2111-5ff5).

```
SomPong session (uid sompong)
  └ "org" MCP = runners/coo_mcp_server.py      no credential; one JSON line per call
        │  /run/org-coo-gate/gate.sock          SO_PEERCRED: only sompong's uid and root
        ▼
  org-coo-gate.service → runners/coo_gate.py   user org-coo-gate, hub role org_coo
        │  writes: pending coo tasks, two request events, its own charter
        ▼
  hub (Postgres) ◄── org-coo-dispatch.service → runners/coo_dispatch.py   root, hub owner
                         │  one worker at a time, only with ≥ 1 GB free
                         ▼  tmux coo-<id8> in the shared server
                      runners/coo_worker.py → bwrap box → codex | agy Argon | Claude Sonnet
```

## The role allowlist is enforced three times (CTO_Gate_MergeChecklist §4b)

| entry point | guard |
|---|---|
| `runners/coo_gate.py` `op_create_task`, `op_delegate_task` | `lib/coo_policy.check_role` before any hub write; the dispatcher checks again before a worker starts |
| `lib/db.create_task` (every Python path that inserts a task) | `coo_policy.check_role(owner_role, role)` right after the owner is resolved |
| the hub, for anything `org_coo` writes | trigger `org_coo_guard` (`org_coo_role.sql` §5): only pending coo tasks for the three roles, three event kinds, its own charter |

`org_coo` holds INSERT on the create columns of `tasks`, INSERT on `events`, SELECT on `tasks`,
four `c_level_sessions` columns plus UPDATE of `charter`, and SELECT on the `live_hosts` /
`live_sessions` columns the live list needs. Nothing else: no UPDATE of a task, no DELETE, no other
table. The SQL proves it at the end of every run (§6).

## The research box (`runners/coo_worker.py`)

bwrap, root mapped to uid 1000 in a new user namespace, all capabilities dropped, environment cleared.
Read-only: `/usr`, an allowlist of `/etc`, Agents/Wikis, Agents/Rules, Agents/Core and Projects/.
Hidden in those trees: every `.git`, untracked and ignored files (`.env`, `state/`, `worktrees/`,
`.venv`), and Core's changes not yet on `origin/main`, except research notes. Writable: `/work` only
(the task's folder). `/root` is empty except the one runner's own auth file. Network is on (the web is
the job). Findings 2026-10-14, same two-part question in the box:

| runner | web | result |
|---|---|---|
| codex `--search exec -s read-only` | built-in web search | correct, 2.6 min (the live test) |
| agy `gemini-4-argon-high --mode plan` | `read_url` only with `runners/coo_agy_settings.json` (headless agy denies every read without a rule; root's own rules allow pytest and the browser tool, so the box binds its own) | correct version, wrong file count (67 of 71), 7 min; once returned a 95-character "waiting for subagent" line, which `is_report` now rejects |
| claude Sonnet, Read/Grep/Glob/WebSearch/WebFetch only, no MCP | WebSearch + WebFetch | correct, 1 min |

Order (`config/plans.yaml` class `research`): codex, Argon, Sonnet. A run with no report falls through.

## Install, rotate, remove (each a Run card, red risk)

1. Grants (applied 2026-10-14, re-run after any change to the SQL):
   `python3 tools/infisical_setup.py run Agents-Core prod --as contabo -- .venv/bin/python deploy/coo-gate/org_coo_role.py --grants-only`
2. Rotation (the old org_coo password leaked: `/run/sompong-coo/org-db.url` is readable by `sompong`,
   and commit a60f1744 holds a literal). Needs contabo write on Infisical Org-Coo (card
   Q-20261013-2053-bf0f). Folder `/gate`, so nothing that reads Org-Coo's root path receives the new value.
   **Probe first, on the same card:** `org_coo_role.py` changes the Postgres password BEFORE `put` stores
   the URL, so a 403 on `put` would lose the new password and the running gate would fail on its next
   reconnect. `python3 tools/infisical_setup.py mkdir Org-Coo prod gate --as contabo` makes the folder if
   missing, then always creates and deletes a nested `probe-<hex>` folder (fail-closed: an existing
   `/gate` cannot skip the write): chain it with `&&` in front of the rotation so a missing grant stops the
   card before anything changes. If `put` still fails after the rotation, run the same card again (mkdir
   is idempotent; the rotation mints a fresh password). Then:
   `python3 tools/infisical_setup.py run Agents-Core prod --as contabo -- .venv/bin/python deploy/coo-gate/org_coo_role.py | python3 tools/infisical_setup.py put Org-Coo prod ORG_DB_URL --stdin --path /gate --as contabo --comment "COO gate hub URL (role org_coo)" --meta provider_name=org-postgres-org_coo --meta console_url=- --meta scope=org_coo --meta expires=never --meta owner=cto`
3. Install or re-point: `bash deploy/coo-gate/install.sh install /opt/MoonieXHQ/Agents/Core /gate`
   Rollback: `bash deploy/coo-gate/install.sh uninstall`. Status: `install.sh status`.
4. SomPong's next session start loads the new "org" server (`scripts/lib/cxo_mcp_config.py`, role coo).
5. Then, with SomPong's owner: drop the `coo-org-db-cred` ExecStartPre from `mooniex-sompong.service`
   and the dead `ORG_DB_URL` at Org-Coo's root path.

## Residual risks

- The box shares the host network: a runner can reach services on localhost (CDP ports, the hub's
  tailnet port without a password). It holds no secret but its own runner login.
- A runner can read its own auth file (codex `auth.json`, Claude `.credentials.json`; agy's rules do
  not allow `/root`). A page that talks it into sending that file out is the main injection risk;
  `secret_hits` stops it in the report, not in a fetch.
- Files under a directory closed to "other" (Projects/MoonieX/ClaudeFlow, mode 700, another owner)
  are unreadable in the box; the researcher says it cannot read them.
- A masked file still shows in a listing; reading it fails (EACCES).
