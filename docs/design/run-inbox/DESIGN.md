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
6. **Tab name: pending** — the CEO asked for a mockup first. Canvas (5 screens, tappable flow):
   https://claude.ai/artifact/GCmexryuJbybMGX2jKg2Gr — source backup in
   `docs/design/run-inbox/mockup/` (Main / Card / Running / ResultOK / ResultFail `.dc.html`).
   P1 build starts after the CEO approves the mockup (or orders changes).
