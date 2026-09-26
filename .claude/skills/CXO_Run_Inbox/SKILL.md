---
name: CXO_Run_Inbox
description: "Put one shell command or one repo script on the CEO's phone for a tap (Run Inbox, terminal.mooniex.com/run): the CEO reads the exact bytes, taps Run, it runs on that host, and the result comes back to your session as a mailbox letter. Trigger on /CXO_Run_Inbox and whenever a step needs a human at the machine — a '!' command, a CLI login (claude /login, gh auth login, a device code), a script that must run as the operator, anything the auto-mode classifier refuses (secrets into .env, systemctl restart, a deploy) — or the moment you are about to write 'CEO please run this on <box>' or 'พิมพ์คำสั่งนี้'. Do NOT fire for browser logins (that is the login relay, terminal.mooniex.com/relay) or for commands your own sandbox can run. CEO 2026-09-26: the CEO runs commands from the phone ONLY — never hand a '!' command in chat; the Stop hook scripts/hook-phone-only-commands.py blocks a reply that does."
created_by: agent
author: {role: cto, date: "2026-09-25"}
audience: [cxo, worker]
---

# Run Inbox — one command, one tap, one host

You write a card; the CEO opens `terminal.mooniex.com` → tab **คำสั่ง** on the phone, reads the
exact bytes, taps **Run** (or Deny, or asks back); the hub runs it on the target host in a pty and the
result returns to your session. **The one rule:** the tap is the only authority, and what the CEO
reads is byte-for-byte what runs — no agent approves, no batch, no "always allow", no edit after
approval. Design: `docs/design/run-inbox/DESIGN.md`; hub facts: Console `docs/run.md`.

## Hosts (state on 2026-09-25)

| host | runs cards | how |
|---|---|---|
| `contabo` | **yes** (P1 live since 2026-09-25 17:05 UTC) | the hub's own executor |
| `winbox` | no — hub answers `501 peer_exec_not_yet` at creation | P2: executor on the peer |
| `mac` | no — same 501 | P2, after the Mac rebuild (its sshd is off) |

A card for winbox or the Mac never reaches the phone — the hub refuses it before storing anything.
There is no "old way" any more (Rule 0): the CEO does not sit at a machine to type. Until P2, a step on
the Mac or winbox goes one of two ways, and never as a `!` line:

- **Your own auto-mode classifier refused an action the CEO already ordered** (a delete, a post, a
  paid call he approved): ask for ONE approval sentence in chat that names the exact target — he
  types it on the phone — then run it yourself. Measured 2026-09-26: deleting the TEST post on the
  Mac's FB Chrome (CDP bound to 127.0.0.1:9230, so no Contabo card can reach it).
- **It truly needs a human at that box** (a login code, a secret into a file): say in one line
  "card impossible on <host> until P2", park it to LungNote with P2 as the unblocker, move on.
  Browser logins still go through the login relay (`terminal.mooniex.com/relay`).

[SUPERSEDED 2026-09-26 by CEO ruling, kept as history] ~~Until P2, those steps go the old way (the CEO
at that machine; browser logins via the login relay).~~

## Before the first card (facts you cannot derive)

- **Token.** A C-level session on Contabo reads `~/.config/mooniex/run-inbox.token` (0600, written by
  the Console's `scripts/run-inbox-deploy.sh`); `RUN_INBOX_TOKEN` in the env wins over the file.
  Never print it, never commit it (`*.token` is gitignored). The hub decides your class from the
  token, never from `--role`; the worker token may create scripts only.
- **The CLI is one stdlib file**, `tools/ask_run.py`, on origin/main since b2830b3c. On a checkout
  that is behind (the shared Contabo tree often is), take the file from origin instead of merging:
  `git -C /opt/MoonieXHQ/Agents/Core fetch -q origin && git show origin/main:tools/ask_run.py > "$S/ask_run.py"`
  (`$S` = your scratchpad) and run that copy with `.venv/bin/python`.
- **MCP tools** `ask_run` / `ask_run_wait` are in the org registry for sessions launched after
  2026-09-25 (the allowlist is registry-driven); a session started earlier uses the CLI.
- Hub URL: `RUN_INBOX_URL` (default `https://terminal.mooniex.com`). Your mailbox name goes in
  `--session <role>-<id>` (default from the launcher env) — that is where the result letter lands.

## How to ask

```bash
P=.venv/bin/python; A=tools/ask_run.py   # or "$S/ask_run.py" from the git show above
# C-level, freeform — sent byte-for-byte:
$P $A create --host contabo --command "systemctl status mooniex-console" \
  --why "check the Console after the restart" --expected "active (running)" \
  --risk green --timeout 60 --session cto-6ebacd0e --role cto
# worker or C-level, a script pinned to a PUSHED commit (args after --):
$P $A create --host contabo --script Agents-Core@<sha>:scripts/contabo_blueprint.sh -- --out state \
  --why "weekly blueprint capture" --expected "state/contabo-blueprint-<date>/ committed" --risk amber --timeout 900
# then block on it (exit 0 = done · 1 = failed / denied / expired / cancelled · 4 = --max-wait ran out; prints the tail):
$P $A wait RUN-20260925-1632-0bfe --max-wait 1800
```

`create` prints the id and the phone URL — put both in one chat line so the CEO knows a card is
waiting. Other verbs: `list` (own cards), `cancel <id>` (own, pending only), `tail <id>` (live
output over SSE), `--dry-run` (prints the JSON, sends nothing), `--expects-input` when the process
will wait on stdin (a login code the CEO types on the phone), `--cwd`, `--shell`, `--env-key NAME`
(a name the executor may pass through — never a value; TOKEN/SECRET/PASSWORD-like names make the
card red).

## What the CEO sees, and what comes back

- The card: host · risk colour · your `--why` and `--expected` · the exact command (a script shows
  its first 40 lines and its `repo@sha`) · the "sha256 ตรวจแล้ว" label. Buttons: Run · Deny · ask back.
- Clocks: pending expires **30 min** after creation; approved but not started within 60 s goes back
  to pending ("กดรันอีกครั้ง"); the run itself is killed at `--timeout` (default 300 s, max 21600).
- The result: a mailbox letter `state/inbox/<session>/RUN-<id>.json` on the hub's box (Contabo),
  drained by hook-inbox on your next prompt; `wait` prints the redacted output tail (64 KB max).
  Email threads are P3 — today the hub only writes an outbox stub.
- Error ID = the card id `RUN-YYYYMMDD-HHMM-xxxx`. Details on the hub: Console
  `node scripts/run-error.js RUN-…` (who / when / host / sha256 / exit / stage — never output or stdin).

## Risk — the hub computes it; your claim can only raise it

- **green** = the whole command is ONE plain read-only command from the allowlist (`ls`, `cat`,
  `git status|log|diff`, `df`, `du`, `systemctl status`, `docker ps`, `tail`, `grep`,
  `bash scripts/contabo_blueprint.sh`) with no `; | > $() \`` — passkey session.
- **amber** = everything else that writes files or state — passkey session.
- **red** = delete (`rm -r`, `reset --hard`, `clean -f`, docker rm/prune), force push, crontab /
  schtasks delete, `/etc/`, `.ssh`, `.env`, `secrets`, `sudo`, `curl … | sh`, DROP/dropdb,
  shutdown/reboot, `systemctl stop|restart|disable|mask|kill` — a fresh Face ID (≤120 s, single use).

## Rules

0. **HARD — commands reach the CEO on the phone only.** Every command or script the CEO has to run
   goes as a Run Inbox card. Never write a `!` command, a "พิมพ์คำสั่งนี้", or "run this on <box>"
   in chat — not in a code block, not inline. For the Mac and winbox before P2, see §Hosts.
   Enforced in the tool, not only here: `scripts/hook-phone-only-commands.py` (Stop hook) blocks a
   reply that hands one and makes you rewrite it. Bypass `PHONE_ONLY_GUARD=off` only to repair the
   hook itself.

   **Why hard:** CEO ruling 2026-09-26 — "ส่งคำสั่งมาที่ terminal.mooniex.com/run … เขียน Skill
   บังคับใช้ได้เลย … เพราะฉะนั้นจะรัน command ผ่านมือถือเท่านั้น". He is not at a keyboard; a `!`
   line in chat is a step nobody can take.

1. **HARD — the CEO's tap is the only authority.** Never approve, batch, retry until approved, or
   ask for a standing "always allow"; the org token cannot approve and the design forbids it.

   **Why hard:** scope of authorisation — the tap is the same line the auto-mode classifier draws
   for `!`; an agent-side approval would turn every card into a blank cheque.

2. **HARD — nothing secret-shaped in a card** (command, args, cwd, why, expected): a token shown on
   the phone, in the ledger or in an email thread cannot be unshown. Reference an env NAME or an
   Infisical path instead; the CLI refuses obvious shapes, not every shape.

   **Why hard:** irreversible exposure of a credential.

3. A card lives 30 minutes. Issue it when the CEO is holding the phone (one chat line with the id),
   or it expires unread — the first live card did exactly that on 2026-09-25 (created 00:32
   Bangkok, expired 01:02, CEO asleep). Expired = re-issue once he says he is there; never nag.

4. One action per card, and `--why` / `--expected` written for a thumb on a phone: one line each,
   the outcome, no jargon (CEO 2026-09-25: "กระชับเท่านั้น").

5. A script beats a long command line. The card pins `repo@sha:path` and shows the first 40 lines,
   so the reviewer reads what the CTO merged — a shell one-liner carries quoting traps the phone
   cannot show, and a worker cannot send one anyway.

6. The run is `bash -lc <command>` as the service user (root on Contabo), env = PATH/HOME/LANG/TERM
   plus your named `--env-key`s only, cwd = `--cwd` or `$HOME`. `PAGER=cat` is preset; anything else
   interactive (`apt` without `-y`, a TTY prompt) hangs until the timeout kills it — pass the flags
   yourself, or use `--expects-input` when the CEO is meant to type the answer.

## When not to

- A browser login (Google, Facebook, TikTok …) → the login relay at `terminal.mooniex.com/relay`.
- A command your own sandbox can run → run it; the phone is for what only a human at the box may do.
- winbox or the Mac until P2 lands — the hub refuses, so do not promise the CEO a card there; use
  the two routes in §Hosts (approval sentence in chat, or park), never a `!` line.

## Reference

`docs/design/run-inbox/DESIGN.md` (design, CEO decisions §11, nav §12, CLI §13) · Console `docs/run.md`
(set-up, wire shapes, risk table, limits) · `tests/test_ask_run.py` · memory `project-ask-inbox-design`.

## Field notes

- 2026-09-25 [COSTLY] §Rules.3 — first live card RUN-20260925-1632-0bfe expired unapproved after the 30-min TTL; the CEO was not at the phone · evidence: hub ledger pending→expired, result letter in state/inbox/cto-6ebacd0e/ · prevented by: issue only when the CEO says he is holding the phone; P1.1 = requester-chosen TTL · status: pending
- 2026-09-25 [MISSING] §Before the first card — on Contabo, workers run as the same user as C-level sessions (root), so a worker can read the C-level token file; the hub classes by token, not by role · evidence: run-inbox-deploy.sh writes /root/.config/mooniex/run-inbox.token; workers spawn as root · fix: launcher exports the WORKER token as RUN_INBOX_TOKEN and the C-level file moves out of the worker's reach (P1.1) · status: pending
- 2026-09-26 [MISSING] §Rules.0 — the CTO handed the CEO a `!` command for a Mac-only delete; the CEO ruled commands run from the phone only and ordered the rule enforced · evidence: CEO ruling 2026-09-26 (session cto-89aa4de2, TEST post 4116998775270501), hook scripts/hook-phone-only-commands.py · status: promoted
