# Brief — Run Inbox P1b: the requester side in Agents-Core (`tools/ask_run.py` + org MCP tool `ask_run`)

Design (read first): `docs/design/run-inbox/DESIGN.md` §2, §4, §6 (requester side), §7, §11, and the API
contract below (the same one the Console side, P1a, is building in parallel — do not invent fields).
Read `tools/decide.py` (house CLI style), `claude-home/mcp/mooniex-coord/index.mjs` (how org MCP tools are
declared and how they read env/paths), `tools/work_archive.py` (ledger/log style), `state/inbox/` usage in
`tools/` (mailbox letters). English (IRON §56). Your worktree branch is cut from local main; run
`git fetch origin && git merge --ff-only origin/main` FIRST so you have `docs/design/run-inbox/` (pushed today).

## API contract (hub = MoonieX Console, base URL `RUN_INBOX_URL`, default `https://terminal.mooniex.com`)
Auth: `Authorization: Bearer <token>`; token read from `RUN_INBOX_TOKEN` env, else the file
`~/.config/mooniex/run-inbox.token` (0600; never printed, never committed). The org token can only create,
list/read its own asks, cancel its own pending ask, and stream events — it can never approve.
- `POST /api/run/asks` `{host, kind:"script"|"command", command?, script?:{repo,sha,path,args[]}, shell?, cwd?,
  env_keys?[], why, expected?, risk?:"green"|"amber"|"red", timeout_s?:300, expects_input?:false,
  requester:{session, role, task?}}` → `201 {id, status:"pending", risk, expires_at}`;
  `400 {error:"secret_shaped_value"}`, `403 {error:"freeform_needs_c_level"}`, `501 {error:"peer_exec_not_yet"}`.
- `GET /api/run/asks?status=&limit=` → `{asks:[…]}` (own only); `GET /api/run/asks/:id` → card;
  `POST /api/run/asks/:id/cancel`; `GET /api/run/asks/:id/events` → SSE `state|output|end`.
- Result also arrives as a mailbox letter `state/inbox/<session>/RUN-<id>.json` on the hub's box.

## Deliverables
1. `tools/ask_run.py` — verbs: `create` (flags `--host`, `--script repo@sha:path -- args…` OR `--command "…"`
   (the CLI refuses `--command` unless `--role` is cto/cfo/cxo/ceo — the hub enforces it too), `--why`,
   `--expected`, `--risk`, `--timeout`, `--expects-input`, `--task`; requester.session from `CTO_SESSION_ID`/
   `ORG_SESSION_ID` env or `--session`; prints the id and the phone URL `…/run#RUN-…`), `wait <id>` (poll
   `GET /api/run/asks/:id` every 5 s until a terminal state, exit code = 0 for done, 1 for failed/denied/expired/
   cancelled, prints the tail), `list`, `cancel <id>`, `tail <id>` (SSE stream to stdout). Refuses to send a
   payload containing a secret-shaped value (same regex family as `scripts/contabo_blueprint.sh`'s final
   pass) BEFORE the network call. stdlib only (urllib). `--dry-run` prints the JSON and calls nothing.
2. MCP tool `ask_run` in `claude-home/mcp/mooniex-coord/index.mjs`: same inputs, calls the same API (Node
   `fetch`), returns `{id, url, risk, expires_at}` — and `ask_run_wait {id}` returning the terminal record.
   Keep the tool descriptions short and state the one rule: "the CEO's tap is the only authority; the tool
   never approves".
3. `tests/test_ask_run.py` — a local fake hub (http.server thread) covering create/wait/cancel/list, the
   secret-shape refusal, the role gate, the token file vs env precedence, `--dry-run` (no network).
4. `docs/design/run-inbox/DESIGN.md` §13 "Requester CLI" (one screen: examples for a worker script ask and a
   C-level freeform ask, how a worker learns the result).
5. `windows/`: nothing in P1b (winbox executes in P2).

## Must not
No network calls in tests; no token in the repo (add `.gitignore` line for `*.token` if missing); no `cd`
in compound shell commands; nothing over 1 MiB; do not edit the Console repo.

## Finish
Commit on your branch (`ask_run:` prefix), attribution lines from the CTO, push nothing to origin
(the CTO merges). Report: files, `pytest tests/test_ask_run.py -q` verbatim, an example `--dry-run` payload,
open questions, `## Skill learning`.
