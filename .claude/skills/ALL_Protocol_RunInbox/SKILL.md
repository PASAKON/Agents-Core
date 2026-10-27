---
name: ALL_Protocol_RunInbox
kind: protocol
owner: CTO
aka: [CXO_Run_Inbox]
description: "PROTOCOL — Put one shell command or one repo script on the CEO's phone for a tap (Run Inbox, terminal.mooniex.com/run): the CEO reads the exact bytes, taps Run, it runs on that host, and the result comes back to your session as a mailbox letter. Trigger on /ALL_Protocol_RunInbox and whenever a step needs a human at the machine — a '!' command, a CLI login (claude /login, gh auth login, a device code), a script that must run as the operator, anything the auto-mode classifier refuses (secrets into .env, systemctl restart, a deploy) — or the moment you are about to write 'CEO please run this on <box>' or 'พิมพ์คำสั่งนี้'. Do NOT fire for browser logins (that is the login relay, terminal.mooniex.com/relay) or for commands your own sandbox can run. CEO 2026-09-26: the CEO runs commands from the phone ONLY — never hand a '!' command in chat; the Stop hook scripts/hook-phone-only-commands.py blocks a reply that does. Also fire for any QUESTION to the CEO (a choice, go/no-go, 'which one?') when he is not typing in this chat: that goes on a question card he answers with a tap (ask_ceo / ask_run.py ask, CEO 2026-10-13) — never for a command, money or a secret."
created_by: agent
author: {role: cto, date: "2026-09-25"}
improved_by:
  - {role: developer, date: "2026-10-27", what: "waiting on a card is the background wait or the mailbox letter, never a timer (IRON-RULES §64, task-375ec9e9)"}
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
winbox's Claude CLI is already logged in (CEO 2026-09-28: "Window Login Claude นานแล้ว"), so no desk
login is waiting on P2 there.
There is no "old way" any more (Rule 0): the CEO does not sit at a machine to type. Until P2, a step on
the Mac or winbox goes one of two ways, and never as a `!` line:

- **Your own auto-mode classifier refused an action the CEO already ordered** (a delete, a post, a
  paid call he approved): ask for ONE approval sentence in chat that names the exact target — he
  types it on the phone — then run it yourself. Measured 2026-09-26: deleting the TEST post on the
  Mac's FB Chrome (CDP bound to 127.0.0.1:9230, so no Contabo card can reach it).
- **It truly needs a human at that box** (a login code, a secret into a file): say in one line
  "card impossible on <host> until P2", park it to LungNote with P2 as the unblocker, move on.
  Browser logins still go through the login relay (`terminal.mooniex.com/relay`).
- **A command the CEO ordered on winbox that a PEER cannot run** (its classifier refused it, and winbox has no
  token): a contabo card whose line runs over `ssh winbox`. The peer writes the exact bytes as a script in its own
  folder and proves the transport with a read-only verb. The C-level reads the script, pins it by sha256 (the
  card's line compares `certutil -hashfile <path> SHA256` before anything runs, exit 3 on a mismatch) and raises
  the card verbatim. Never tell the CEO to press it at the desk while this route works. Runs:
  RUN-20261014-0549-4910 and RUN-20261023-0122-f1a5 (CookieRun ESC hold cleared, farm restarted, exit 0 both).

[SUPERSEDED 2026-09-26 by CEO ruling, kept as history] ~~Until P2, those steps go the old way (the CEO
at that machine; browser logins via the login relay).~~

## Before the first card (facts you cannot derive)

- **Token.** A C-level session on Contabo reads `~/.config/mooniex/run-inbox.token` (0600, written by
  the Console's `scripts/run-inbox-deploy.sh`); `RUN_INBOX_TOKEN` in the env wins over the file.
  Never print it, never commit it (`*.token` is gitignored). The hub decides your class from the
  token, never from `--role`; the worker token may create scripts only. On Contabo that split is not
  in force yet (checked 2026-09-28): workers run as root too and no launcher exports a worker token,
  so a worker reads this same C-level file, and only the CLI still refuses `--command` when
  `WORKER_TASK_ID` is set (fix = P1.1: the launcher exports the worker token, the file moves out of a
  worker's reach). Workers still send pinned scripts only (CEO decision 1, 2026-09-25, DESIGN §11);
  on Contabo the hub cannot stop a worker that goes around the CLI.
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

**≤5 lines, enforced (CEO 2026-10-14: ≤5 lines total, alert only, plain words, detail in a linked
file).** `--why` + `--expected` together are at most 5 lines of at most 90 chars; an empty line counts,
a lone link may run to 200, and the command bytes do not count (the CEO approves them as they are).
`create` and the MCP `ask_run` refuse more (exit 2); no flag skips it (`lib/ceo_text.py`).

`create` prints the id and the phone URL — put both in one chat line so the CEO knows a card is
waiting. Other verbs: `list` (own cards), `cancel <id>` (own, pending only), `tail <id>` (live
output over SSE), `--dry-run` (prints the JSON, sends nothing), `--expects-input` when the process
will wait on stdin (a login code the CEO types on the phone), `--cwd`, `--shell`, `--env-key NAME`
(a name the executor may pass through — never a value; TOKEN/SECRET/PASSWORD-like names make the
card red).

## What the CEO sees, and what comes back

- The card: host · risk colour · your `--why` and `--expected` · the exact command (a script shows
  its first 40 lines and its `repo@sha`) · the "sha256 ตรวจแล้ว" label. Buttons: Run · Deny · ask back.
- Clocks: a pending card expires by the risk the hub gives it: **green 24 h, amber 8 h, red 1 h**
  (CEO 2026-10-13, question card Q-20261013-2052-3bee). A claim the hub raises gets the shorter life.
  The API takes `expires_in_s` (at least 600): less is kept, more is cut to green 7 d, amber 24 h,
  red 4 h. `ask_run.py` sends none, so a card gets its risk's default. Approved but not started
  within 60 s goes back to pending ("กดรันอีกครั้ง"); the run itself is killed at `--timeout` (default 300 s, max 21600).
- The result: a mailbox letter `state/inbox/<session>/RUN-<id>.json` on the hub's box (Contabo),
  drained by hook-inbox on your next prompt; `wait` prints the redacted output tail (64 KB max).
  Email threads are P3 — today the hub only writes an outbox stub.
- **The letter wakes nobody** (rule, 3 runs). Console `src/run/notify.js` writes the file and stops, so a
  session that raised a card and then went idle stays idle after the tap; the result waits for its next
  prompt. Right after `create`, start `bash scripts/hub/org-python.sh tools/ask_run.py wait <id>` with
  `run_in_background`: it polls every 5 s and the session is told when the card ends. That one command, or the
  RUN-<id> letter at the next prompt, is the whole wait: never poll a card on a timer (IRON-RULES §64). Runs:
  RUN-20261022-0425-29c8 (PH#7dc, 22 Oct); 27 Oct, PH#d5e (results of the #468, #474 and #475 merge
  cards unread, idle from 04:23 TH) and PH#47c (RUN-20261026-1615-1f03 unread, idle from 23:15 TH).
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

3. A card lives by its risk: green 24 h, amber 8 h, red 1 h. A green or amber card can wait for him
   to come back. A red card is short on purpose, because a root command written hours ago may no
   longer fit the box: issue it when the CEO is holding the phone (one chat line with the id).
   Expired = re-issue once he says he is there; never nag. `[SUPERSEDED 2026-10-13]` "A card lives
   30 minutes. Issue it when the CEO is holding the phone … or it expires unread" — beaten by the
   CEO's ruling on Q-20261013-2052-3bee: at 30 min, 31 of 96 cards had expired unread (Console 810b108).

4. One action per card, and `--why` / `--expected` written for a thumb on a phone: one line each,
   the outcome, no jargon (CEO 2026-09-25: "กระชับเท่านั้น"). The hub caps each at 500 characters
   (Console `src/run/create.js` `MAX_TEXT`): longer is refused `400 invalid_why` / `invalid_expected`.

5. A script beats a long command line. The card pins `repo@sha:path` and shows the first 40 lines,
   so the reviewer reads what the CTO merged — a shell one-liner carries quoting traps the phone
   cannot show, and a worker cannot send one anyway.

6. The run is `bash -lc <command>` as the service user (root on Contabo), env = PATH/HOME/LANG/TERM
   plus your named `--env-key`s only, cwd = `--cwd` or `$HOME`. `PAGER=cat` is preset; anything else
   interactive (`apt` without `-y`, a TTY prompt) hangs until the timeout kills it — pass the flags
   yourself, or use `--expects-input` when the CEO is meant to type the answer.

## Question cards — a question the CEO answers with a tap (CEO 2026-10-13)

> "Session ไหนติด blocker ตอนการให้ฉันอนุญาต ก่อนเริ่มส่ง มาใน /run ได้เลย หรือถ้ามีคำถาม
> ส่งคำถามทิ้งไว้ จะเข้าไปกดตอบ เป็นคำถามแบบกดตอบได้นะ"

**≤5 lines, enforced (CEO 2026-10-14: ≤5 lines total, alert only, plain words, detail in a linked
file).** The question + `why` together are at most 5 lines of at most 90 chars, for a lone card and for
each item of a group. Option labels are buttons and keep their own limit. `ask` / `ask_ceo` refuse more.

A question for the CEO (a choice, a go/no-go, "which one?") goes on a **question card** whenever he is
not typing in your chat at that moment. Do not leave it in chat to wait, and do not hand it to SomPong to
relay. On /run → **คำถามรอตอบ** he reads who is asking (role · session · host), the why, and 2–4 options
(one may carry **แนะนำ**). He taps one, may add a short note, and taps ส่งคำตอบ. There is no Face ID:
answering a question is not a run.

```bash
python3 tools/ask_run.py ask --question "Ship the Console fix tonight or tomorrow 09:00?" \
  --option "Tonight" --option "Tomorrow 09:00" --recommended 1 \
  --why "Tests are green. Tonight means a Console restart at 22:00 TH."
python3 tools/ask_run.py wait Q-20261013-1102-a3f9   # 0 answered · 1 expired/cancelled · 4 max-wait ran out
```

MCP: `ask_ceo(question, options, why, recommended)`, then `ask_run_wait(id)` (it takes `Q-…` ids).
Contract: `docs/design/run-inbox/QUESTIONS.md`.

**Several questions → one group (CEO 2026-10-14: "ตอบให้ครบแล้ว กดส่ง trigger แค่รอบเดียวพอ ประหยัด token
ด้วย").** Two to six questions you have at the same time go in ONE call, not one card each:

```bash
python3 tools/ask_run.py ask --batch questions.json   # [{question, why, options:[…], recommended, free_text}, …]
python3 tools/ask_run.py wait QG-20261014-0400-c0de   # returns when none is pending; 0 = all answered
```

MCP: `ask_ceo(questions=[{question, why, options, recommended, free_text}, …])`, then
`ask_run_wait(QG-…)`. He answers them on /run and sends once; you get ONE letter (one wake) for
everything he sent you. Each question still has its own `Q-…` id and record: cite that id for
each decision (QUESTIONS.md §10).

1. **HARD — a question card never stands in for a command card.** Anything that runs a command, spends
   money or touches a secret goes on a command card (`ask_run`; red = fresh Face ID). That holds even
   after the CEO has said yes to a question about it. The tool and the hub refuse a question or option
   that reads like a command (backticks, `&&`, a pipe, flags, paths, a first word such as `sudo`, `git`,
   `docker`, `systemctl`) or that names an amount (`$`, `฿`, `บาท`, `credits`). Never reword to get
   past that check. Send the command card.

   **Why hard:** a question tap carries no Face ID, so it must never authorise anything a Face ID
   protects.

2. **HARD — only the CEO answers.** The answer route accepts his passkey session and nothing else. No
   session, worker, mailbox letter or peer can write an answer, and there is no answer verb. The record
   of his decision is the hub: `ask_run wait Q-…` returns `answered_by`, `answered_at` and the sha256 of
   exactly what he read. The mailbox letter only wakes you. When you act on his answer, or a peer
   relays it, cite the `Q-…` id. That record is what a reviewer or a classifier checks.

   **Why hard:** a question card exists to be the CEO's own decision on record. An answer that anything
   else could write would make every relayed "he said yes" unverifiable.

3. Raise it at once and put one chat line out (id + link + the question). Never ask whether you may
   ask. While it is pending, do not ask the same thing again in chat.
4. It lives 24 h by default (`--expires-h`, max 168), because he comes back to it later. If it
   expires, ask once more on a fresh card.
5. Write for a thumb: the question on one line (≤90 chars), each option ≤120 chars, and a `why` that
   says what happens on each choice. Mark your recommendation with `--recommended N`. `ask` refuses a
   longer or multi-line question (`invalid_question`) for every item of a `--batch` too: question +
   `why` stay within 5 lines, and the detail goes in a linked file.
6. C-level only. A worker writes its question into its report, and its C-level asks.
7. Hosts: a question needs the run-inbox token, which Contabo C-levels have. The Mac and winbox have no
   token yet, so there you ask in chat as before and say why.

## When not to

- A card that does not pass the filter in `ALL_Rules_Approvals` §Before anything reaches the CEO: if he already
  decided it, already granted it or approved the same thing before, act on it and cite the id. A card that
  passes starts its why with the reason word (`money`, `secret`, `deletion`, `his-name`, `his-account`,
  `org-rule`, `login`, `his-choice`, `no-op`).
- A browser login (Google, Facebook, TikTok …) → the login relay at `terminal.mooniex.com/relay`.
- A command your own sandbox can run → run it; the phone is for what only a human at the box may do.
- winbox or the Mac until P2 lands — the hub refuses, so do not promise the CEO a card there; use
  the two routes in §Hosts (approval sentence in chat, or park), never a `!` line.

## Reference

`docs/design/run-inbox/DESIGN.md` (design, CEO decisions §11, nav §12, CLI §13) · Console `docs/run.md`
(set-up, wire shapes, risk table, limits) · `tests/test_ask_run.py` · memory `project-ask-inbox-design`.

## Field notes

- 2026-09-25 [COSTLY] §Rules.3 — first live card RUN-20260925-1632-0bfe expired unapproved after the 30-min TTL; the CEO was not at the phone · evidence: hub ledger pending→expired, result letter in state/inbox/cto-6ebacd0e/ · prevented by: issue only when the CEO says he is holding the phone; P1.1 = requester-chosen TTL (not in tools/ask_run.py yet) → §Rules.3 (already the body's text, incident included) · status: promoted
- 2026-09-25 [MISSING] §Before the first card — on Contabo, workers run as the same user as C-level sessions (root), so a worker can read the C-level token file; the hub classes by token, not by role · evidence: run-inbox-deploy.sh writes /root/.config/mooniex/run-inbox.token; workers spawn as root · fix: launcher exports the WORKER token as RUN_INBOX_TOKEN and the C-level file moves out of the worker's reach (P1.1) → §Before the first card, Token (re-checked 2026-09-28: every claude process runs as root, no launcher sets RUN_INBOX_TOKEN, ask_run.py falls back to ~/.config/mooniex/run-inbox.token) · status: promoted
- 2026-09-26 [MISSING] §Rules.0 — the CTO handed the CEO a `!` command for a Mac-only delete; the CEO ruled commands run from the phone only and ordered the rule enforced · evidence: CEO ruling 2026-09-26 (session cto-89aa4de2, TEST post 4116998775270501), hook scripts/hook-phone-only-commands.py · status: promoted
- 2026-10-01 [MISSING] §cancel — once the CEO has pressed Run, the requester can no longer cancel the card (hub 403 `requester_cancels_pending_only`); an `--expects-input` card that has become obsolete just sits waiting for input until its timeout. Tell the CEO not to type into it, or send the card only when its plan is final · evidence: RUN-20261001-1421-f9ff (superseded by the KeyFetch route) · status: pending
- 2026-10-01 [MISSING] §Hosts — a Mac C-level has no Run Inbox token, and a copy of `tools/ask_run.py` outside the repo fails (it reads `policies/agents.yaml` relative to itself). What worked for every Contabo card from the Mac (G1 cutover + session resume): pipe the card body over ssh and create it on Contabo — `ssh mooniex-vps 'cd /opt/MoonieXHQ/Agents/Core && .venv/bin/python tools/ask_run.py create --host contabo --shell bash --cwd /opt/MoonieXHQ/Agents/Core --command "$(cat)" --why … --expected … --risk … --timeout N --session <sid> --role cto' < card.sh`, and wait the same way (`ask_run.py wait <RUN-id> --max-wait N`) in a background shell · evidence: RUN-20261001-2142-e16e, RUN-20261001-2145-3cad, RUN-20261001-2152-2250, RUN-20261001-2202-3ea7 (session cto-e6754203) · status: pending
- 2026-10-02 [MISSING] §Hosts — a Contabo card's `wait` output prints the box's local time, CEST (UTC+2), while the card id carries UTC: RUN-20261001-2234-730a was created 22:34 UTC and `wait` printed `00:34:33 pending`, `01:04:08 expired`. Convert before quoting a time to the CEO (TH = UTC+7 = CEST+5) · evidence: RUN-20261001-2234-730a, session cto-e6754203 · status: pending
- 2026-10-02 [MISSING] §create — a card's command is capped at 8000 characters (MoonieX-Console `src/run/create.js` `MAX_COMMAND = 8000`); a 9,409-byte script was refused with `ask_run: hub refused (400: command_too_long)` and nothing was created. Measure with `wc -c` before `create`; over the cap, split by job into two cards (each readable on the phone) rather than parking the script in a file the card only names · evidence: session cto-e6754203, cards RUN-20261002-0112-c96a + RUN-20261002-0112-56cf · status: pending
- 2026-10-02 [WRONG] §Rules.3 — "Expired = re-issue once he says he is there; never nag" assumes a new card reaches the CEO. It does not: the Console sends nothing on create (no web push anywhere in src/ or public/; the mail is a stub, docs/run.md "Nothing is sent in P1"), so an unseen card expires in silence and a re-issue is just as silent. While a session waits on him, re-create on expiry and keep ONE chat line with the live ids; the nag to avoid is a repeated chat line, not a card. Keep the exact `create` and `wait` commands in a file beside the card script, because a context compaction turns them into `...` and recovering them from the transcript took 6 calls · evidence: RUN-20261002-0143-e759/-dabf expired 02:13Z untapped, re-created as RUN-20261002-0215-f942/-5251 (session cto-e6754203); Console src/run/lifecycle.js:43 queueMail(new) only appends to data/run-mail-outbox.jsonl (60 unsent lines on Contabo) · status: pending
- 2026-10-02 [MISSING] §Risk — `red` makes the CEO look twice at `systemctl restart|stop`, but nothing says what a restart on Contabo can take with it: every C-level, worker and SomPong pane runs in ONE root tmux server, and `systemctl restart mooniex-sompong.service` at 02:38:35Z (session e106b78b, after card RUN-20261002-0234-f4ec) killed 5 C-levels and worker task-cc55e620, because sompong-supervise.sh had started that server inside the service's cgroup. Before a card (or a command) that restarts or stops a Contabo service, run the two cgroup one-liners in Agents-Core CLAUDE.md §"Contabo — one tmux server holds every session"; if the service holds the server or any pane, do not send it, tell the CEO · evidence: session cto-e6754203 (diagnosis from the journal; live server moved into org-tmux.scope 16:27 TH without a restart; hook scripts/org-tmux-adopt.sh) · status: pending
- 2026-10-03 [MISSING] §Hosts mac — on the Mac, `ask_run` fails in the client before the hub's 501: "ERROR: no token: set RUN_INBOX_TOKEN or create /Users/gob/.config/mooniex/run-inbox.token (mode 0600)". Same outcome as the table (no card on the Mac until P2), different first error; do not go looking for the token · evidence: task-c99d48d6 Colab CLI sign-in, session addb58de · status: pending
- 2026-10-03 [MISSING] §Hosts mac — a copy-paste CLI OAuth the Mac needs can be done on CONTABO instead: install the CLI there (`python3 -m venv /opt/colab-cli && /opt/colab-cli/bin/pip install google-colab-cli==0.7.4`), send an `--expects-input --timeout 1800 --risk amber` card that runs the login (`colab sessions 2>&1`), the CEO opens the printed URL on the phone and pastes the code into the card, then pull the token file from the Mac (`scp -p mooniex-vps:/root/.config/colab-cli/token.json ~/.config/colab-cli/` + chmod 600; Mac sshd is off so Contabo cannot push). Worked first try in 49 s; no agent saw the code or the token · evidence: RUN-20261002-2027-e98e, task-c99d48d6 unblocked (session cto-addb58de) · status: pending
- 2026-10-13 [MISSING] rule 4 — a command card whose `why` ran to ~620 characters came back `400 invalid_why`; 290 and 470 were accepted. The hub's limit is 500 characters for `why` and `expected` (Console `src/run/create.js` `MAX_TEXT = 500`, JS string length); a question card allows `why` ≤ 1000 and `question` ≤ 300 · evidence: CTO #268a7843 (RUN-20261013-1303-0ff6, RUN-20261013-1229-496a), Console 397e4ca create.js:25,98 → rule 4 · status: promoted
- 2026-10-14 [MISSING] §Question cards — `ask` refuses a card whose `why` holds a CLI flag (`refused: command_shaped … a CLI flag`), even when the flag is only described inside a rule summary. Write the flag in words ("a written force reason") · evidence: Q-20261013-1917-0fa2, first attempt refused · status: pending
- 2026-10-14 [MISSING] §Question cards — a question card cannot be amended after it is raised, and the CEO can tap within seconds (one answer came 22 s after the raise). A condition sent in chat after the card is not part of what he agreed to. Put every condition in the card's question or why before raising · evidence: session cto-e106b78b, the 2026-10-13 17:4x cards · status: pending
- 2026-10-14 [MISSING] §Rules — a card whose why said "add the two keys in Infisical first, then tap" was tapped before the keys were added, and it failed ("has no secret …", RUN-20261013-2023-62fe, 03:25 Thai). The CEO reads the card as the whole job. Raise a verify card only after he has done the step (a question card first), or make the card itself the step · evidence: session cto-e2f1563f, followed by Q-20261013-2026-f2ac · status: pending
- 2026-10-14 [MISSING] rule 5 — the rule gave the 300-character limit but not that `ask` refuses a longer or multi-line question with `invalid_question` (each item of a `--batch` too), nor where the detail goes (`why`, which may hold newlines); a peer asked for it once the batch went live · evidence: tools/ask_run.py:601 (QUESTION_MAX = 300, :134), `why` newline allowance :630-636, SomPong letter 2026-10-14, session cto-2235643e → rule 5 · status: promoted
- 2026-10-14 [MISSING] waiting — `ask_run_wait` with `max_wait_s` above 1800 dies in the background with "MCP server \"org\" tool \"ask_run_wait\" sent no response or progress for 1800s; aborting": the tool sends no progress while it waits, and the client's MCP idle timeout is 1800 s. Seen twice (max_wait_s 2940 and 3540). Keep `max_wait_s` ≤ 1500 on the MCP tool; for a longer wait run the CLI `tools/ask_run.py wait <id>` as ONE background command (a Bash job, so no MCP idle timeout), not a timed re-check (the 14 Oct advice, replaced 27 Oct by IRON-RULES §64) · evidence: RUN-20261013-2150-e745, RUN-20261013-2214-e175 (cto-afe760fe) · status: pending
- 2026-10-14 [MISSING] §Question cards — the "CEO's window" (taps within 30 min until 04:00 TH, then ~13:00–14:00 TH) matters for red Run cards, which live 1 h; a question card lives 24 h by default (`expires_h` up to 7 days), so it goes up at once with `expires_h` set to the decision's deadline, not held for the window. A PH asked for its arming question to be raised "in the 13:00–14:00 window"; raised at 09:37 TH instead with expires_h=23 · evidence: Q-20261014-0237-7d8b (CTO Main cto-c34459eb, PH SpendGuard #6c487e37) · status: pending
- 2026-10-14 [MISSING] §Question cards — `ask_ceo` refuses a `why` that contains `&&` or `||` ("command_shaped … a question is not a command"), even when the command is one the CEO must type himself on a machine with no Run card (the Mac). Put such lines in the chat report, and have the card say "the 2 lines in the CTO chat" · evidence: refusal then Q-20261014-0402-6bd9 (Mac resume of #f39cb080/#671f688f), CTO Main cto-c34459eb · status: pending
- 2026-10-14 [MISSING] §Question cards — a "yes, the permission is set" answer is a decision, not proof: Q-a5bb was answered "ตั้งแล้ว — ยกการ์ด M4 มาเลย", and the re-raised red card RUN-20261014-0455-4cf9 still stopped at its first step with the same Infisical 403 ("not allowed to create on secret-folders"). Before re-raising a red card that depends on a grant, put the grant's read-only probe as the card's first step (fail closed, nothing changed), and put the exact UI path to the missing permission in the question's `why` (Q-20261014-0545-71bb did) · evidence: cto-c34459eb, cards c80d → 4cf9 → b407 · status: pending
- 2026-10-14 [MISSING] §When to raise — an action a PEER's classifier refused (PH CookieRun: app pipe `night {clear_hold:true}` refused [Auto-Mode Bypass], even with the CEO's question-card answer as its source) goes on the C-level's Run card, never run by the C-level itself: the peer writes the exact bytes to a file and proves the transport with a read-only verb, then the C-level pins any script the line calls by sha256 (certutil -hashfile on winbox) and raises the card verbatim · evidence: cto-c34459eb, Q-20261014-0512-a5df → RUN-20261014-0549-4910; second run RUN-20261023-0122-f1a5 (CEO 2026-10-23 "PH ไม่รู้จักส่ง /run มา บน window") → §Hosts · status: promoted
- 2026-10-14 [MISSING] §How to ask (`--expects-input`) — the stdin box types into the card's pty, and the pty's echo lands in the stored output_tail, the live stream and the requester's letter. A tool that reads a SECRET from a card must turn ECHO off first, print 'ready' only then, and refuse input already waiting (it was typed early and echoed). A plain `readline()` put the test password in the output under a pty · evidence: PR #288 §2b round 1 B1 (`tools/winbox_vnc_rotate.py` read_password), session cto-c34459eb · status: pending
- 2026-10-14 [COSTLY] §Before the first card — RUN-20261014-0628-c8a4 failed on a 404 because Infisical had moved `/api/v1/workspace/<id>/permissions`. The session cannot call the API as the machine identity to test the route, so a card that calls a third-party route should try the current route and fall through on 404 from the first version · evidence: RUN-c8a4, fix PR #285 (d832d1e0), re-raised RUN-20261014-0653-86de · status: pending
- 2026-10-14 [MISSING] §Hosts mac — question cards hit the same wall as command cards: origin `tools/ask_run.py ask`/`list --questions` on the Mac fails "no token", also when run through `scripts/hub/with-org-db-env.sh` (the Infisical env does not carry RUN_INBOX_TOKEN), and the Mac main checkout has no `ask_ceo`. Under the CEO 2026-10-14 ruling (every question to Run), a Mac session sends question + 2–4 options to CTO Main, who raises the card · evidence: session cto-671f688f 13:1x TH, claude-home/CLAUDE.md 0b7cc3d9 · status: pending
- 2026-10-14 [MISSING] §How to ask — an `--expects-input` card whose script waits for a typed value cannot tell "nothing typed yet" from "half a line typed": the pty is in canonical mode (ICANON), so FIONREAD reports 0 bytes until Enter, and a poll on FIONREAD alone times out on a CEO who is still typing. Wait on a line read with a long timeout (≥1800 s, see the input-card memory) and never treat FIONREAD 0 as "no input" · evidence: PR #288 review round 2 M-1 (tools/winbox_vnc_rotate.py), card RUN-20261014-0736-d6b8 · status: pending
- 2026-10-14 [WRONG] §Rules — a guard inside a card like `pgrep -f 'codex app-server' && { echo 'codex app-server is running'; exit 1; }` matches the card's OWN shell, because the card's argv (and its echo text) contains the phrase, so the card refuses itself on every run. Write the pattern as `[c]odex app-server` and keep the bare phrase out of every echo/why line of that card · evidence: RUN-20261014-0738-1abd failed at the guard with nothing changed; the re-raised RUN-20261014-0739-c9fb with `[c]odex` ran, exit 0 · status: pending
- 2026-10-14 [MISSING] §Question cards — a money GO cannot go on a question card: `ask_ceo` refuses a question or option that names money, and the tool text sends spend to a command card. The working shape (CMO RUN-20261014-0742-f99a, CTO RUN-20261014-0751-1c3d) is an amber command card whose command only appends a dated line to a ledger file: `printf "%s CEO GO: <what>, cap <$>\n" "$(TZ=Asia/Bangkok date "+%F %H:%M TH")" >> <dir>/CEO-GO.txt`. The tap is the decision and the file is the record that spend code can check · evidence: those two cards · status: pending
- 2026-10-14 [COSTLY] §expects-input cards — an input card at --timeout 1800 still died E_TIMEOUT at the password prompt ("type the new 8-character password now"): the CEO did not get to it within 30 min. Nothing changed (the tool reads the password before acting), but the whole card had to be re-raised; re-raised at 3600. Second sighting after the 600 s one in memory feedback_run_inbox_input_cards_need_time; a password card wants 3600 s from the start · evidence: RUN-20261014-0736-d6b8 (failed), RUN-20261014-0824-5d06, session cto-c34459eb · status: pending
- 2026-10-14 [MISSING] §Question cards — a Project Head cannot post a question card: `ask_run.py ask` refuses it with "question_needs_c_level: a question card is for C-level sessions … this requester is role 'project_head'", and `ask_ceo` is not in a PH's tool list. So the CEO-only question a PH needs goes to its C-level, which posts it for the PH, cites the Q- id back, and relays the answer. Don't tell a PH to post its own question card · evidence: PH#f35 CookieRun refusal 08:36Z, posted by the CTO as Q-20261014-0836-cc76, session cto-c34459eb · status: pending
- 2026-10-14 [MISSING] §create — since the 5-line rule (#305/#306, `lib/ceo_text.py`), `--why` must be ONE line of ≤90 characters, and each Thai character counts as one. Two cards were refused (a 107-char and a 95-char line) before they were raised. Draft the why at ≤80 characters · evidence: cto-c34459eb 14 Oct 16:5x–17:0x TH · status: pending
- 2026-10-22 [MISSING] §Result — `tools/ask_run.py list` (with or without `--json`) cuts each card's `command` to 200 characters, so a C-level checking a Project Head's card before telling the CEO to tap it sees only the start. The full bytes come from the hub's one-card GET: `json.loads(ask_run._request('GET', ask_run.ASKS_PATH + '/<id>').read())['command']` (run through `scripts/hub/org-python.sh`) · evidence: RUN-20261022-0425-29c8 (422 characters; list showed 200), CTO Main #c34459eb · status: pending
- 2026-10-22 [MISSING] §Result — the result letter wakes nobody by itself: Console `src/run/notify.js` writes `state/inbox/<session>/RUN-<id>.json` and stops, and no mail-wake timer runs on Contabo (`systemctl list-timers --all`, 22 Oct), so a box that raised a card and went idle stays idle after the CEO's tap. Right after `create`, start `bash scripts/hub/org-python.sh tools/ask_run.py wait <id>` in the background (`run_in_background`); the session is told when the card ends · evidence: RUN-20261022-0425-29c8 (ran 04:51Z; PH#7dc still idle at 05:04Z, woken by CTO Main over SendMessage), RUN-20261022-0501-7618 (CTO Main's background wait returned at exit) · 2nd and 3rd runs 27 Oct (PH#d5e, PH#47c) → §What the CEO sees · status: promoted
- 2026-10-26 [MISSING] §Rules — an approval-only card authorises nothing that runs later. RUN-20261026-1318-7bd8 was `echo "CEO approves: ... fal cap $0.25"`; the CEO tapped it, and two hours later the classifier still refused the worker's own fal call, because a tapped echo is not the action. Put the paid command itself on a labelled spend card: `python3 <script>.py ... --max-usd N` as one simple command, run from `--cwd`. A loop of calls goes inside the script, which must stop before the cap. Second trap on the same card: the label's balance comes from the spend guard, and its fal reading has been 0.0 in every snapshot since 14 Oct (fal calls still went through on 25 Oct), so every fal card fails `spend_cap_over_balance` until that is fixed (CTO told 26 Oct). Never declare a balance you have not read · evidence: task-7a7d1a66 pane 22:03 TH, dry run 23:00 TH, /opt/MoonieXHQ/Work/cn-series/voice/v3/run_takes.py; a second echo card of the same shape the same evening, RUN-20261026-0920-aedc (CnDrama EP02 Colab render, approved 10:11Z, not run yet) · status: pending
- 2026-10-26 [MISSING] §create — a card's lifetime follows its risk and `ask_run` takes no TTL: a red card expired 1 h after it was raised, an amber one 8 h (RUN-20261026-1621-f8fb red 16:21Z → 17:21Z; RUN-20261026-1615-1f03 amber 16:15Z → 00:15Z). `expected` is held to 90 characters like `why`. A red card raised late at night is gone by morning; raise it again then · evidence: RUN-20261026-1621-f8fb, RUN-20261026-1615-1f03 · status: pending
- 2026-10-26 [COSTLY] §Hosts — a contabo card that runs a command on winbox over `ssh winbox` goes through cmd.exe, which cuts a command line at 8,191 characters. Ship a .ps1 file, check its sha256 on winbox in the card line, and run the file · evidence: session cto-d405e3e2 2026-10-26 (winbox CTO relaunch) · status: pending
- 2026-10-26 [MISSING] §who — `command='…'` cards are for C-level roles only (`policies/agents.yaml` c_level). A Project Head raises a script card at a pushed sha, or sends its C-level a `blocker` with the exact line when the step needs root or a restart (CTO job 6) · evidence: the `ask_run` tool doc; session cto-d405e3e2 2026-10-26 · status: pending
- 2026-10-26 [MISSING] §How to ask — the skill never says how a SPEND card must look under the hub's enforce mode, which has been on since 16 Oct (drop-in spend-label.conf). There a labelled `--command` card is refused (`spend_needs_script_card`), and so is a script card with a `--cwd` (`spend_script_cwd_set`). The one shape that runs is `--script <repo>@<origin/main tip>:<path>.py` with the cap flag in its args, for a `.py` listed in that repo's own `config/spend-tools.txt` at the tip (Console docs/run.md §Spend label). Agents-Core's list was empty, so no spend card could run anywhere. Two runners built in Work/ that night could never have passed: the CMO's ILAG voice runner and PH#351's EP02 render runner. The first entry offered for listing is PR #469, `tools/fal_tts.py` · evidence: PH 3511068d dry-run 26 Oct 23:35 TH, PR #469, Console src/run/script.js spendToolCheck · status: pending
- 2026-10-27 [MISSING] §What the CEO sees, and what comes back — a script card refused `E_SCRIPT_NOT_PUSHED` seconds after a merge to the same repo is the runner's race, not an unpushed commit: Console `src/run/script.js` fetchScriptBytes fetches, then compares the local origin/<branch> tip with a fresh `ls-remote`, so a push landing between the two fails the check for any commit. The CEO tapped a Colab script card (pinned at origin/main's tip) and a `gh pr merge` card 2 s apart; the merge moved main and the script card never started (no spend). Recovery: check the script is unchanged and still in spend-tools.txt at the new tip (`git diff --quiet <old> <new> -- <path>`), re-raise pinned at the new tip, and tell the CEO why he taps again · evidence: RUN-20261027-0005-3efd (approved 00:52:44.6Z, refused 00:52:50.6Z), PR #480 merged 00:52:48Z by RUN-20261027-0018-0e78; reported to CTO #fresh · fix: Console #41 (cea9f25a, CTO 27 Oct 02:19Z) re-checks the heads, live after the next Console restart; until then the recovery above stands · status: pending
- 2026-10-27 [MISSING] §How to ask — Flow credits have no card form. `ask_ceo` refuses an option that names credits (`money_needs_command_card`); a winbox card is refused by the hub (501 `peer_exec_not_yet`, P2); a Contabo card that reaches winbox over ssh is a command card, which the spend-label rule refuses; and `config/spend-tools.txt` does not list `tools/flow_shoot.py`, which still carries a second cap flag (`--credit-cap`). What works today is §Hosts, first bullet: the CEO types one approval sentence in the chat of the session that runs the shoot, naming the target (EP, clip count, Flow on winbox, credit cap), and that session runs flow_shoot with `--max-credits`, which checks the cap before every Submit and exits 3. A card route needs the winbox executor plus flow_shoot without `--credit-cap` (the CTO is filing the gap) · evidence: PH#d5e letter 27 Oct 02:43Z (ILAG EP1, 82 clips, cap 5,000), CTO letter 03:06Z · status: pending
