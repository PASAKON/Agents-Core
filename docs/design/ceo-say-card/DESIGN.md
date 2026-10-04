# "CEO says to session" Run card: design for the CEO's decision

**Status:** design only; nothing is built. Written 2026-10-04 by CTO #e106b78b (Contabo).
**Order:** CEO via COO, 4 Oct ~14:0x TH: "ส่งให้ CTO ออกแบบได้เลย".
**Review asked of:** MAC CTO #e6754203 (Org Mesh hub; the peer API in §10 is theirs to schedule).
Estimates are marked [E]. Everything else was read from code or logs on 2026-10-04.

## 1. The problem (measured)

- When COO relays a CEO decision with SendMessage, it arrives in the target session as a
  `<cross-session-message>`. Claude Code tells every session that a peer cannot grant escalation.
  That rule is right, and the session's classifier refuses the relayed approval.
- Seen 5+ times this week: WINDOWS CTO #2c6b9f03, MAC CTO #671f688f, MAC CTO #e6754203, and the
  Chatudo CTO and CMO. Also in this session: a hosts.yaml edit made on a peer's word was refused as
  "Instruction Poisoning" (2026-10-04).
- So the CEO has to find each session and type into it himself.
- Run cards cannot carry the message today, for two reasons:
  1. They run shell commands; they do not deliver words.
  2. Only Contabo executes. A card for `mac` or `winbox` answers `501 peer_exec_not_yet` (Console
     `src/run/create.js:127`).

## 2. What already exists and is reused

| Piece | Where | What it gives us |
|---|---|---|
| Console chat into a session | Console `src/tmux/bridge.js` `write()`, into the session's tmux pty | His phone typing already enters a session as a **real user turn**, and classifiers accept it today. |
| Run card | Console `src/run/{create,routes,executor}.js` | A pending card with a 30-min expiry. The phone returns the sha256 of the bytes it **showed**; a mismatch returns 409 (`routes.js:143-147`). |
| Face ID step-up | Console `src/run/stepup.js` | A WebAuthn assertion with user verification required. One challenge per card per operator, 120 s, single use. |
| Peer API (P2) | Run Inbox DESIGN §P2, Console `docs/run.md` §11 | The hub calls Console-Mac and the winbox relay-mode Console. **Not built**: it answers 501. |
| Prompt hooks | `claude-home/settings.json` `UserPromptSubmit` | Already run on every prompt in every session. |

## 3. Recommendation

1. **COO or any C-level creates a card.** New Run card kind `say`. It carries the target session
   id and the exact text.
2. **The CEO approves with Face ID.** His phone shows the target (id, role, topic) and the full
   text, and he scans his face.
3. **His passkey signs the exact card.** The WebAuthn challenge is not random: it is the sha256 of
   the card (id, target, text hash, expiry). So the assertion is a signature over exactly that
   card. The key that makes it lives on his phone / iCloud Keychain, off every machine we run.
4. **The target host's Console delivers it.** It pastes the text into the target session's tmux
   pane, the same path his Console chat uses today, under a one-line header that carries the proof.
5. **A hook in every session checks it.** A `UserPromptSubmit` hook verifies the proof against his
   passkey **public** key, which is committed to the repo.
   - Valid: the turn carries a note "CEO-verified, card X".
   - Header present but bad, expired or replayed: the prompt is blocked and an alert is logged.
   - A prompt with no header is untouched.

**Delivery form:** (a). **Proof:** his Face ID signature. **Not** a hub-held key; §5 explains why.

**Zero-build interim (Contabo sessions only, usable today):** COO's message to the CEO carries the
deep link to the target session's Console chat page. He taps it and types; there is no hunting.
This does not help Mac or winbox sessions.

## 4. Why (a), and not (b) or (c)

| | (a) Type into the session | (b) Remote Control "as the user" | (c) Signed envelope on a cross-session message |
|---|---|---|---|
| Arrives as | a real user turn | a real user turn | a peer message (`<cross-session-message>`) |
| Classifier | treats it as his own words, the same path as his Console chat today | same as (a) | still a peer message. Signed or not, the harness tells the model a peer cannot grant escalation, so refusals continue. |
| Needs | an executor that owns the target pty. Contabo: yes, today. Mac: P2. winbox: P2, plus sessions run under the winbox Console (§10). | his claude.ai login on a server. We know of no documented "send as user" API [unverified]. | a hook in every session, plus a hub key |
| Blast radius | the Console on that host, which is already root and already types his chat | his whole claude.ai account if the box leaks | low, but it does not solve the problem |
| Verdict | **chosen** | rejected: maximum-blast secret, unsupported | rejected as a delivery path; its signature idea is kept as the proof inside (a) |

## 5. Unforgeable: where the key lives

**Why not a key on the hub.** On Contabo, every C-level session runs as **root**, and so does the
Console (`ps`, 2026-10-04). Any key the hub holds on that box is reachable by a root session.
Nothing technical stops it; only policy does. A hub-held signing key would therefore **not** be
"outside every session's reach".

**His passkey is.** A WebAuthn assertion is his device key signing
`authenticatorData ‖ sha256(clientDataJSON)`, and `clientDataJSON` carries a challenge we choose:

    challenge = sha256(canonical JSON {v:1, card, host, session, text_sha256, operator, expires_at, nonce})

The verifier needs only public inputs:
- his credential public key(s), committed as `config/ceo-passkeys.json` (public keys only; rotating
  a passkey means a PR),
- the rpId and the origin (`terminal.mooniex.com`).

**The hook checks all of the following:**
1. The signature is valid (ES256).
2. The user-verified flag is set.
3. The rpIdHash and the origin match.
4. challenge == sha256(the header fields).
5. sha256(the delivered text) == `text_sha256`.
6. `session` == this session's id.
7. Now is before `expires_at` (approval + 5 min).
8. The card id is not already in this session's consumed ledger. This ledger is the single-use
   guard. The counter cannot be: synced passkeys report counter 0.

**What this does not close.** A root process that types plain keystrokes into another pane, with no
header, looks like the CEO at the keyboard. That is true today without this feature:
`session-rename.sh` types into its own pane. The fixes are outside this design: non-root sessions
(as SomPong already runs) and per-user tmux sockets. This design makes **"CEO-approved"**
unforgeable; it does not make the keyboard unforgeable.

## 6. Addressing a session

- **The target is the 8-hex session id** (`#e106b78b`). Topics, Remote Control refs and tab names
  change; the id survives a launcher resume **only** when `--id <id>` is passed (a known trap in
  `spawn-cto.sh --resume`).
- **Where the id comes from.** The hub keeps a registry of live sessions, reported by each host's
  Console (`listSessions`). COO resolves "the Chatudo CTO" to an id from that registry. The card
  shows id, role and topic, and the CEO sees all three before he scans.
- **If the id is live on no host** at delivery, the card fails with `target_not_live`. It is never
  re-aimed at another session.

## 7. Delivery (executor kind `say`)

1. **Re-check** that the card is approved, not past the 5-min window, its sha256 matches, and the
   target is live.
2. **Check the pane is idle.** Read it with `capture-pane`; the input line must be empty.
   - If a draft is in the box, wait 30 s and retry, up to 10 times, then fail `draft_in_box`.
   - Never clear the line (`C-u`): it would erase his own draft.
   - Why: `session-rename.sh` typed onto drafts 3 times (`//rename`, `า/rename`, `หรื/rename`).
3. **Paste and submit.** `tmux load-buffer` + `paste-buffer -p` (bracketed paste, so newlines do not
   submit early), then Enter.
4. **Confirm.** `capture-pane` after 3 s. If text is still on the input line, send Enter once; if
   it is still there, fail `not_submitted`.
5. **A session mid-turn** queues the message as its next user turn. That is acceptable.

**Header**, one line before the text:

    [CEO·FaceID v=1 card=RUN-… proof=state/ceo-say/<card>.json sha=<sha256 of that file>]

The assertion bundle is ~1 KB [E]. The executor writes it to `state/ceo-say/<card>.json` on the
target host (0644; it holds no secret, only public signature data), and the hook reads it there.
This keeps the typed text short.

## 8. Audit

- **Hub:** a `run_say_log` row with card id, approver (operator + credential id), approved_at,
  target host + session, the text, its sha256, delivered_at and the result.
- **Target host:** the hook appends `{card, verified, reason, ts}` to `state/ceo-say-ledger.jsonl`.
  The same file is the replay ledger.
- **Org event log:** one line per delivery, so it shows in every C-level's "Recent org activity".

## 9. Blast radius

**What changes.** This changes how a CEO approval can enter **every session on every machine**.
After it lands, a session acts on a verified card as if he had typed it, including money, secret
and deploy words in the text.

**Limits:**
- One card = one target = one message.
- The text shown on the phone is the text delivered: its sha256 is checked at the phone, the hub
  and the hook.
- The card must be delivered within 5 min of approval, and it is single use.
- Every `say` card is red: a fresh Face ID each time, with no 15-min remember.

**How it fails:**
- **Console down:** the card stays pending and nothing is delivered.
- **Hook bug:** at worst it blocks prompts that carry the header; plain prompts are never touched.
  `ORG_CEO_SAY=off` turns the feature off (no delivery, no verification).
- **Passkey lost:** no new cards can be approved, and the old ones expire.

**Nothing silent:** it lands only after the CEO OKs this document, and each phase is announced to
every C-level.

## 10. Build plan and effort [E]

| Phase | What | Where | Who | Effort [E] |
|---|---|---|---|---|
| S1 | `say` card kind: create and validate (target, text ≤ 4,000 chars, the existing secret-shape check), the phone view, challenge = card hash, local-host paste executor, `run_say_log` | Console | codex/AGY worker + CTO review | ~1 day, 2 worker runs |
| S2 | Verify hook, public-key export, ledger, offline tests (ES256 with `cryptography`) | Agents-Core | codex worker | ~0.5 day, 1 run |
| S3 | Contabo live: deploy the Console, turn the hook on, drill (card to a scratch session; a forged header is refused; a replay is refused) | Contabo | CTO | ~2 h |
| S4 | Mac delivery | Console-Mac | after P2 (Run Inbox §P2); MAC CTO #e6754203 to say who builds it | +0.5 day after P2 |
| S5 | winbox delivery | winbox Console | after P2, **and** winbox C-level sessions must run under the winbox Console's pty (today the CEO launches them at the desk) | +1 day after P2 |

Contabo could use it about **2 days after the CEO's OK** [E], on AGY/codex workers, with no new
spend. Mac and winbox wait on P2, which nobody has scheduled yet.

## 11. Decisions for the CEO (recommended answer first)

1. Use (a): type into the session, with his Face ID signature as the proof. **Recommended: yes.**
2. Every "say to session" card is red: a fresh face scan for each card, with no 15-minute remember.
   **Recommended: yes.**
3. A card must be delivered within 5 minutes of the scan, or it dies. **Recommended: yes.**
4. COO and every C-level may create these cards; he always sees the full text before he scans.
   **Recommended: yes.**
5. Text delivered by a card counts as if he typed it himself, including money, secrets and deploy
   when the text says so explicitly. The money rule still needs the exact $ amount written in the
   text. **Recommended: yes.**
6. Order: Contabo first, then Mac and winbox after P2. **Recommended: yes.**
7. Start building S1–S3 (~2 days, AGY/codex workers, no extra spend). **Recommended: yes.**
