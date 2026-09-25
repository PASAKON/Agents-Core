# Brief — Run Inbox P1a: the hub, the `/run` page and the local executor (MoonieX Console)

Design (read first, all of it): Agents-Core `docs/design/run-inbox/DESIGN.md` (§2 the one rule, §4 data model,
§5 phone UI, §7 refusals, §11 CEO decisions, §12 navigation) and the approved mockup source
`docs/design/run-inbox/mockup/*.dc.html` (the look: fonts, colours, spacing, copy — copy it, do not redesign).
Repo: MoonieX-Console, your worktree is a branch `run-inbox-p1` cut from the LOCAL main (which is 21 commits
ahead of GitHub — the live code). Read `docs/relay.md`, `src/app.js`, `src/routes/pages.js`, `src/routes/api.js`,
`src/relay/routes.js` + `src/relay/errors.js` (Error-ID discipline), `src/auth/middleware.js`, `src/db.js`,
`src/peer/client.js`, `public/relay.html` + `public/js/relay.js` + `public/css/console.css`, `test/relay-*.test.js`
(house test style, incl. `relay-no-emoji.test.js` and `relay-no-logging.test.js`). English in code and commits;
Thai copy on the page exactly as the mockup.

## Deliverables

1. **Store** — additive `CREATE TABLE IF NOT EXISTS run_asks` in `src/db.js` (same idempotent pattern as
   `vault_entries`): id `RUN-YYYYMMDD-HHMM-xxxx`, host, requester_json, kind (`script`|`command`), command
   (the exact text that runs; for `script` the rendered `bash <path> args…` line), script_json (repo, sha,
   path, args), shell, cwd, env_keys_json, why, expected, risk (`green`|`amber`|`red`), timeout_s, expires_at,
   sha256 (of `command` bytes), status (`pending`|`approved`|`running`|`done`|`failed`|`denied`|`expired`|`cancelled`),
   approved_by, approved_at, started_at, finished_at, exit_code, output_tail (≤64 KB, redacted), error_id,
   deny_reason, created_at. Helpers in `src/run/store.js`.
2. **API** in `src/run/routes.js`, mounted in `src/app.js` next to `relayApiRouter`:
   - Auth: operator cookie (`requireAuthApi`) for everything; **org token** (`RUN_INBOX_ORG_TOKEN` from
     `config.js`/`.env`, `Authorization: Bearer …`, constant-time compare) may ONLY create, read its own
     requester's asks, cancel its own pending ask, and read events. Approve / deny / input are operator-only.
   - `POST /api/run/asks` body `{host, kind, command?, script?:{repo,sha,path,args[]}, shell?, cwd?, env_keys?,
     why, expected?, risk?, timeout_s?, expects_input?, requester:{session,role,task?}}` → `201 {id,status,risk,expires_at}`.
     Refuse: `400 secret_shaped_value` when any field matches the secret-shape regex (assignment of a
     token/secret/password/api_key/private_key/client_secret/access_key to a non-empty value, or a
     `BEGIN … PRIVATE KEY` block); `403 freeform_needs_c_level` when kind=command and requester.role is not
     one of cto/cfo/cxo/ceo; `400` when host is not this Console's own host id (P2 adds peers: return
     `501 peer_exec_not_yet` for a known peer id). Risk = max(requester's claim, classifier): `red` on
     `rm -rf|Remove-Item .*-Recurse|del /s|git push --force|docker (volume|system) (rm|prune)|crontab|schtasks /Delete|
     /etc/|\.ssh|\.env|secrets|sudo|curl .*\| *(ba)?sh|pg_dropdb|DROP (TABLE|DATABASE)` (case-insensitive,
     keep the list in `src/run/risk.js` with tests); `amber` default; `green` only when the requester says
     green AND the command matches a read-only allowlist (`ls|cat|git (status|log|diff)|df|du|systemctl status|
     docker ps|tail|grep|bash scripts/contabo_blueprint.sh|python3 tools/machine_doctor.py … check`).
   - `GET /api/run/asks?status=pending|running|done|all&limit=50` → list (org token: own only);
     `GET /api/run/asks/count` → `{pending}`; `GET /api/run/asks/:id` → card (tail redacted).
   - `POST /api/run/asks/:id/approve` (operator; `red` needs a fresh WebAuthn assertion — reuse the vault's
     Face-ID step-up if one exists, else a `reauth_at` no older than 120 s from the login session; document
     which) → sets approved, starts the executor at once; `409` when not pending or past `expires_at`.
   - `POST /api/run/asks/:id/deny {reason}` · `POST /api/run/asks/:id/cancel` (kills the tree when running)
     · `POST /api/run/asks/:id/input {text}` (operator, running only; written to the pty with `\n`;
     NEVER stored or logged — add a test like `relay-no-logging`).
   - `GET /api/run/asks/:id/events` — SSE: `state`, `output` (redacted chunk), `end {exit_code, duration_ms}`;
     the phone page uses it for the live tail.
   - `GET /api/run/errors/:id` + `scripts/run-error.js` — same shape as the relay's `RLY-` records (who/when/
     host/command sha/exit/duration/stage; never output, never input).
   - Expiry sweep every 60 s: pending past `expires_at` → `expired`; approved-not-started > 60 s → back to
     `pending` with a note (re-confirm rule, §7).
3. **Executor** `src/run/executor.js` (local host only in P1): `node-pty` (already a dependency) spawning
   `bash -lc <command>` (shell per ask; `cmd`/`powershell` only on win32) as the service user, cwd default
   `$HOME`, env = process.env filtered to `PATH HOME LANG TERM` + `env_keys`; before spawning, re-hash the
   stored `command` and refuse on mismatch (§7); `script` kind: `git -C <clone of script.repo> fetch -q origin
   <sha>` then `git show <sha>:<path>` into a temp file under `data/run-tmp/<id>/`, run it with `args` (clone
   paths from `config.js` map `RUN_INBOX_REPOS="Agents-Core=/opt/MoonieXHQ/Agents/Core,…"`); timeout → kill
   the process group (`detached:true`, `process.kill(-pid, 'SIGKILL')`); output ring buffer 64 KB, each chunk
   passed through `src/run/redact.js` (shape-aware: value only, key kept) before storage and before SSE;
   ledger line appended to `data/run-ledger.jsonl` on every state change (id, ts, state, sha256, exit, ms —
   no output, no input). On end: status done/failed, `error_id` on failure, mailbox letter (below), notify stub.
4. **Result routing** `src/run/notify.js`: (a) mailbox letter — when `RUN_INBOX_AGENTS_CORE` points at an
   Agents-Core checkout on this box, write `<that>/state/inbox/<requester.session>/RUN-<id>.json` (id, status,
   exit_code, duration, error_id, tail ≤ 4 KB) — else log and skip; (b) **email stub**: append the would-be
   message `{to, subject:"[RUN][<host>][<risk>] <first line> — RUN-<id>", thread_id: id, body}` to
   `data/run-mail-outbox.jsonl` for both the new-card and the result events. P3 wires Gmail; P1 must not
   touch any Gmail credential.
5. **Page** `public/run.html` + `public/js/run.js` (+ a section in `public/css/console.css`): the mockup's
   screens 1–4 as ONE page with views (inbox list · card · running · result), served at `GET /run` by
   `src/routes/pages.js` behind the same auth as `/relay`. Live tail via the SSE endpoint; input box only
   while `running` (and shown first when `expects_input`); Error ID with a copy button; countdowns from
   `expires_at`. Icons inline SVG, **no emoji** (extend `relay-no-emoji.test.js` to `run.html`/`run.js`).
6. **Navigation bar** (DESIGN §12): `public/js/nav.js` renders the 3-cell bottom bar (Terminal · เข้าระบบ ·
   คำสั่ง, 56 px, whole cell tappable, safe-area padding, active cell from `data-active`, badge from
   `GET /api/run/asks/count` every 30 s, hidden when 0) — included with ONE line in `index.html`, `relay.html`,
   `run.html`. Touch nothing else on those two existing pages; keep their layouts intact (add bottom padding
   so the bar covers nothing).
7. **Tests** (vitest, run with `/opt/node-v22/bin/npx vitest run` — node 20 on PATH cannot run this
   codebase): risk classifier table, redaction, sha256 refusal, TTL/expiry sweep, auth matrix (operator vs org
   token vs none; org token cannot approve), create → approve → run → end with a fake executor, SSE framing,
   input never logged, no-emoji on the new page, `count`. Existing tests stay green.
8. **Docs**: `docs/run.md` in the Console (how to create the token, the env keys `RUN_INBOX_ORG_TOKEN`,
   `RUN_INBOX_REPOS`, `RUN_INBOX_AGENTS_CORE`, the API table, the Error-ID reader, what P2/P3 add).

## Must not
- Deploy, restart `mooniex-console.service`, or edit the live checkout's `.env`; no real email; no peer
  execution; never store/log input text or unredacted output; no new npm dependency without saying why;
  no `cd` in compound shell commands (hook); nothing over 1 MiB.
- Do not touch `src/relay/**` behaviour; the nav include is the only edit to `relay.html`/`index.html`.

## Finish
Commit(s) on `run-inbox-p1` in your worktree (message prefix `run:`), ending with the attribution lines the
CTO gives you. Report: files changed, `vitest run` output verbatim (counts), the auth matrix as tested, the
risk table, open questions, and a `## Skill learning` section (WRONG/MISSING/COSTLY with skill §, or `- (none)`).
