# Run Inbox — `!` commands approved and run from the phone

**Status:** design for CEO decision (2026-09-25, cto-6ebacd0e). Nothing built yet.
**Extends:** the Ask Inbox proposal of 2026-09-23 (card kind C) and the Phone Login Relay that now
lives at `https://terminal.mooniex.com/relay` (MoonieX-Console `docs/relay.md`). Same front door,
same passkey auth, same peer federation, same Error-ID discipline.

## 1. What the CEO asked (2026-09-25)

> a worker writes a script → the command lands on the CEO's phone → the CEO reads it and taps Run
> on the phone → it runs on that machine immediately → nobody has to open that machine's screen
> ever again.

Today a `!` command (a human-authorised shell command outside the model's sandbox) can only be typed
at the machine it runs on, or into a Console chat session that happens to live on that machine.
The Run Inbox moves the **tap** to the phone and the **execution** to the target machine, and gives
the requesting agent the outcome as data.

## 2. The one rule

**The phone tap is the only authority, and what the CEO reads is byte-for-byte what runs.**
No agent approves, no batch, no "always allow", no edit after approval. This is the same line the
classifier draws for `!` today, kept — only the keyboard moves.

## 3. Shape

```
requester (any session / worker, any host)
   │  ask_run(host, script@sha | command, why, risk, timeout, expects_input)
   ▼
HUB  = MoonieX Console on Contabo (front door, passkey, tailnet-only)
   │  stores the card · classifies risk · pushes "1 new card" to the phone
   ▼
PHONE  https://terminal.mooniex.com/run
   │  card: host · requester · exact command · why · risk · TTL → [Run] [Deny]
   ▼
EXECUTOR = the Console peer ON the target host (never an ssh hop with credentials)
   │  contabo: the front door itself · mac: Console-Mac · winbox: relay-mode Console (task MooniexConsole,
   │  interactive logon session → GUI-needing commands work)
   │  pty (node-pty) · exact bytes (sha256 check) · timeout kills the process tree · output tail streamed
   ▼
RESULT  → hub record (exit, duration, redacted tail, Error ID on failure)
        → mailbox letter to the requester session · SomPong notification · phone shows ✓/✗
```

The phone never learns a peer's address (the existing handoff-cookie proxy carries the hop, exactly
like `/ws/relay`). Peers reach out to nobody: the hub calls them over the peer API they already run.

## 4. The card (data model, hub SQLite `run_asks`)

| field | meaning |
|---|---|
| `id` | `RUN-YYYYMMDD-HHMM-xxxx` (same family as `RLY-…` error ids) |
| `host` | `contabo` · `mac` · `winbox` (a registered peer id) |
| `requester` | session id + role + task id (from the org token that created it) |
| `kind` | `script` = `repo@sha:path args…` (workers) · `command` = free text (C-level sessions only, decision 1) |
| `shell` | `bash` · `powershell` · `cmd` — fixed per host default, overridable |
| `cwd`, `env_keys` | working dir; names of env vars the executor may pass through (never values) |
| `why`, `expected` | one line each, shown on the card ("เพื่อ…" / "ผลที่ควรเห็น…") |
| `risk` | `green` read-only · `amber` writes files/state · `red` deletes, secrets paths, money, prod, `curl…\|sh`, `--force` — **computed by the hub from the command**, the requester's claim can only raise it |
| `timeout_s`, `ttl_s` | default 300 s run / 30 min pending → `expired` |
| `sha256` | of the exact command bytes (or of the script file at `sha`) — the executor refuses a mismatch |
| `status` | `pending → approved → running → done \| failed` · `denied` · `expired` · `cancelled` |
| `approved_by`, `approved_at`, `started_at`, `finished_at`, `exit_code` | audit |
| `output_tail` | last 64 KB, **secret values redacted** (shape-aware filter, same family as the blueprint's) |
| `error_id` | `RUN-…` on failure; full record via `node scripts/run-error.js RUN-…` and `GET /api/run/errors/:id` |

## 5. Phone UI (`/run`, next to the Login tab)

1. **Inbox list** — pending cards first (badge = count), then running, then today's results.
   Each row: host chip · risk colour · first line of the command · requester · TTL countdown.
2. **Card** — host, requester, **the exact command** in monospace (scroll + copy), for a `script` the
   path@sha, args and the first 40 lines of the script as the target host sees it, `why`,
   `expected`, risk badge with the reason the hub gave it, expected duration.
   Buttons: **Run** (passkey session; `red` asks for a fresh Face ID ≤ 2 min old), **Deny** (+ one-line
   reason that goes back to the requester), **Ask** (sends a question to the requester's mailbox, card
   stays pending).
3. **Running** — live output tail (SSE), elapsed time, **Cancel** (kills the tree).
   An **input box appears only when** the process is waiting on stdin or the ask declared
   `expects_input` — this is how `claude /login` works from the phone: the output shows the login URL
   → tap it → finish in the phone browser → paste the code into the box → it goes to the same pty (the
   PKCE code is bound to that process, so this is the only place it can go). The hub never stores what
   was typed there.
4. **Result** — ✓ exit 0 + duration, or ✗ plain-Thai reason + **Error ID** with Copy; "ส่งผลกลับให้ <requester> แล้ว".
   Icons (Tabler), never emoji. One card at a time on screen; horizontal scroll never.

## 6. Requester side (Agents-Core)

- `tools/ask_run.py` + org MCP tool `ask_run(host, script|command, why, risk="amber", timeout=300,
  expects_input=False)` → returns the id at once (no blocking turn); `tools/ask_run.py wait <id>`
  polls the hub; the hub also drops a mailbox letter (`state/inbox/<session>/RUN-<id>.json`) when the
  card ends, so a worker that yielded its turn is woken the normal way.
- **Workers may only submit `kind=script`**: a path inside a repo at a pushed commit. The executor
  fetches that sha on the target host, so what the CEO read is what runs, and "a worker wrote a
  script" always means "reviewed by the CTO, on GitHub, restorable" (scratchpad is not storage).
- Ask text containing a secret-shaped value is **rejected at creation** (the requester must reference
  an env name or Infisical path instead) — nothing that would show a token on the phone is stored.
- A requester can cancel its own pending card; it can never approve.

## 7. What it refuses to do (mirror of relay §5)

- Run anything whose bytes differ from the approved record (sha256), or any card past its TTL, or
  an approval older than 60 s without a re-confirm tap.
- Accept an approval from anyone but the CEO's passkey (approver allowlist); `red` without a fresh
  Face ID; any auto-run, batch, or "remember my choice".
- Be a terminal: no free typing except the stdin box while a run is active; no file transfer; no
  scheduling; no second process per card; no output beyond the tail.
- Store stdin text, secret values, or unredacted output; log more than who/when/host/command hash/
  exit/duration on the hub; the target host keeps its own append-only `state/run_ledger.jsonl` so the
  two records can be cross-checked.
- Delete an IRREPLACEABLE path (registry class) unless the registry shows a verified Drive copy —
  IRON §58 rule 1 applies to phone-approved commands too.

## 8. Why each machine runs its own commands

| host | executor | why |
|---|---|---|
| contabo | the front-door Console (node-pty) | it is already root's process on the box |
| mac | Console-Mac peer | Mac sshd is off by design (measured 2026-09-23); the peer already federates |
| winbox | relay-mode Console (`CONSOLE_MODE=relay`, task `MooniexConsole` at logon, `tailscale serve`) | runs inside the CEO's logon session, so commands that need the desktop (Claude login, Chrome, BlueStacks) work; today's `CONSOLE_MODE=relay` disables node-pty — the run module re-enables it for this one purpose |

No ssh keys travel, no new inbound ports: the hub speaks to peers over the tailnet URL they already
serve, and a fresh box only needs the bootstrap + the Console install to start taking cards — which
turns the winbox re-OS runbook's human steps into phone taps (Machine Contract, ADR 0031).

## 9. First use cases (the order to prove it)

1. **`claude /login` on winbox** (blocking CTO e1e3d3ef today): a `red`-free interactive card with
   `expects_input` — the CEO finishes it from the phone; no Windows Terminal.
2. Re-run a committed script on winbox (`windows/winbox-reinstall/rebuild/*.ps1`, `doctor_setup.cmd`).
3. Contabo ops the classifier refuses to let a session run (a private config into the repo, a
   service restart) — the CEO reads the exact line and taps.
4. Mac: `scripts/mac_blueprint.sh` / `mac_restore.sh --dry-run` once Console-Mac is back.

## 10. Phases

| phase | scope | where | size |
|---|---|---|---|
| P1 | hub module `src/run/` + SQLite + `/run` page + SSE + Contabo executor + `tools/ask_run.py` + org MCP tool + mailbox letter + Error IDs + tests | Console + Agents-Core | 1 developer task |
| P2 | peer executors (Mac, winbox) via the peer API; node-pty in relay mode; stdin input box; kill tree on Windows (`taskkill /T`) | Console | 1 task (after the winbox relay-mode Console lands — another CTO's work today) |
| P3 | SomPong push, risk classifier tuning, `red` step-up, registry-aware refusal, output retention job | Console + Agents-Core | 1 task |

$0 to build (org agents), no new services, no new secrets (the org token for `ask_run` is the one
the org MCP already carries; peers use their existing peer auth).

## 11. CEO decisions (answered 2026-09-25 in chat)

1. **Freeform commands: C-level sessions only; workers submit repo scripts only.** ("ตามนั้น")
2. **Notify channel = EMAIL**, not Telegram (CEO: Telegram notifications are muted; email tags and
   searches back in time far better). Implementation: the hub sends from the CEO's Gmail
   (pass.gob1@gmail.com) — one-time consent is a human step (can go through the login relay), the
   credential lives in the secrets bundle, never in the repo. One thread per card: subject
   `[RUN][<host>][<risk>] <first line> — RUN-<id>`; the result is sent as a reply in the same
   thread so Gmail groups them and labels/filters apply retroactively. The new-card mail carries
   one link straight to the card on `/run`. P3's "SomPong push" is replaced by this.
3. **Approval strength: passkey session for green/amber, fresh Face ID for red.** ("ตามนั้น")
4. **Output retention: 30 days, tail only, secrets redacted.** ("ตามนั้น")
5. **Order approved:** P1 on Contabo now; P2 the moment the winbox relay-mode Console lands. ("OK")
6. **Mockup approved ("ผ่าน", 2026-09-25)** — tab name as drawn: **"คำสั่ง"**. Canvas (6 screens, tappable
   flow): https://claude.ai/artifact/GCmexryuJbybMGX2jKg2Gr — source backup in
   `docs/design/run-inbox/mockup/` (Terminal / Main / Card / Running / ResultOK / ResultFail `.dc.html`).
   P1 build is GO.

## 12. Navigation between the three surfaces (CEO 2026-09-25, added after the mockup)

The CEO asked for buttons between `terminal.mooniex.com` (sessions), `/relay` (login) and `/run`
(commands) and a way back, with no URL editing — and warned: thumbs, no small buttons, nothing
that is not needed, terse copy only.

- **One bottom bar, 3 equal cells, 56 px tall, on the three top-level pages only** (`index.html`,
  `relay.html`, `run.html`). The whole cell is the button (≈130×56 px, well over the 44 px minimum).
  Icon 20 px + one word: **Terminal · เข้าระบบ · คำสั่ง**. Active cell in the accent colour; the
  `คำสั่ง` cell carries the pending-card count as a small badge (from `GET /api/run/asks?status=pending`,
  polled every 30 s; hidden when 0). Bottom placement = the thumb zone on a phone; `env(safe-area-inset-bottom)`
  padding like the relay page already uses.
- **Back inside a surface = the page's own top-left 44 px arrow** (card → inbox, relay flow → target
  list). Between surfaces there is no separate back button: tapping another cell IS the way back, so
  nothing extra is added.
- **Shared partial, not three copies:** `public/js/nav.js` + a block in `public/css/console.css`
  render the bar from one place; each page includes one `<script src="/js/nav.js" data-active="run">`
  line. No new dependencies, no framework.
- The terminal page keeps its full screen; the bar takes 56 px and sits above the phone keyboard
  when it is open. If the CEO finds it in the way there, the fallback is a bar that hides while the
  terminal has focus — not in P1 unless asked.
- Words on the bar and on cards stay one or two words; no explanatory text anywhere on the phone
  pages except the plain-Thai failure reason and the Error ID line (§5).

## 13. Requester CLI

`tools/ask_run.py` (stdlib only, runs on any box's `python3`). Every C-level session also has
`mcp__org__ask_run` / `mcp__org__ask_run_wait` from the org MCP server (`lib/org_tools_registry.py`,
served by `runners/cto_mcp_server.py`). They run the same code, and the launchers pre-approve them
because the org allowlist is built from that registry. Hub = `RUN_INBOX_URL` (default
`https://terminal.mooniex.com`). Token = `RUN_INBOX_TOKEN`, else `~/.config/mooniex/run-inbox.token`.
The file must be 0600 and is refused if other users can read it. The token is never printed, and
redirects are refused, so it only goes to the hub. Nothing here approves: the CEO's tap is the
only authority.

**A worker asks to run a committed script.** Workers can only ask for scripts:

    git push origin HEAD            # the executor fetches that sha from origin
    python3 tools/ask_run.py create --host contabo \
        --script Agents-Core@9df4e185:scripts/contabo_blueprint.sh \
        --why "weekly capture" --expected "prints state/contabo-blueprint-<date>/" --risk green
    RUN-20260925-1612-ab12
    https://terminal.mooniex.com/run#RUN-20260925-1612-ab12
    python3 tools/ask_run.py wait RUN-20260925-1612-ab12

Script arguments go last, after `--`, for example `--script repo@sha:path -- --quick "two words"`.

**A C-level session asks for a freeform command.** `--command` is refused for any role outside
`c_level` in `policies/agents.yaml` (today ceo, cto, cmo, cgo, cfo). The CLI and MCP tools refuse
first, then the hub (403 `freeform_needs_c_level`). A process with `WORKER_TASK_ID` set cannot
claim a C-level role:

    python3 tools/ask_run.py create --host contabo --command "systemctl restart mooniex-console" \
        --why "pick up the new env key" --expected "active (running)"

`--dry-run` prints the JSON body and sends nothing. It needs no token. Other flags: `--timeout`
(run seconds, default 300), `--expects-input`, `--shell`, `--cwd`, `--env-key NAME` (repeatable,
names only), `--task`, `--session`, `--role`.

**Refused before anything is sent (exit 2).** The CLI refuses an ask with a secret-shaped value in
any field. That covers the key family of `scripts/contabo_blueprint.sh`'s final pass (a
token/secret/password/api_key/private_key/client_secret/access_key key given a literal value, or a
`BEGIN … PRIVATE KEY` block) and known token shapes (GitHub, `sk-…`, Slack, AWS, Google, GitLab,
JWT, `Bearer <literal>`). Name the variable instead. `GH_TOKEN="$GH_TOKEN" ./x.sh` and
`--env-key GH_TOKEN` both pass. A literal value does not.

**How the requester learns the result:**

1. `wait <id>` polls every 5 s, then prints a status line and the last 40 output lines. Exit codes:
   0 done · 1 failed, denied, expired or cancelled · 2 refused here · 3 no token or hub error · 4
   `--max-wait` ran out. The MCP tool `ask_run_wait {id}` returns the same record, with
   `terminal: false` if `max_wait_s` (default 600) runs out first.
2. When the card ends, the hub writes `RUN-<id>.json` into `state/inbox/<requester.session>/` on
   the hub's own machine. `requester.session` is the mailbox name `<role>-<id>` (`cto-6ebacd0e`,
   `dev-task-8669cf28`). The CLI works it out from the session env the same way
   `scripts/hook-inbox.py` finds its own mailbox, so that hook picks the letter up on the
   session's next prompt.
3. `tail <id>` streams the live output (SSE `state|output|end`) while it runs.

`list [--status pending]` shows only your own asks. `cancel <id>` withdraws your own pending ask.
