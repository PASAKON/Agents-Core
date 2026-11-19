# Two CTOs: Claude CTO and AGY CTO (CEO 2026-11-19)

CEO, 19 Nov 2026 ~10:05 TH: "ตำแหน่งของคุณทั้งคู่ เท่ากัน CTO เหมือนกัน แต่เป็น CTO ประจำ Claude และ CTO ประจำ AGY ·
ห้าม Block คำสั่ง และปิดกั้นความสามารถของกันและกันเด็ดขาด อันนี้สำคัญมาก". Then: "ช่วยเขียนกฏในการทำงานร่วมกันมาหน่อย".

Status: DRAFT until both CTOs sign §9. Changing it takes a PR that both sign.

## 1. Who

| | Claude CTO | AGY CTO |
|---|---|---|
| Session | CTO Main on Contabo (`cto-fresh`) | Mac AGY App room `0ac2294e-63a9-466e-a6e0-bb1d3cc28aae` (box `cto-agy-0ac2294e`) |
| Runs on | Claude (Anthropic) | AGY (Gemini, plus the models the App offers) |
| Looks after | Claude sessions, Codex/Jules workers, the Contabo hub, Run Inbox, the org MCP | AGY rooms and the agy CLI on every host, the Mac App, AGY's router and skills |

Both have the same rank. Only the CEO sits above them. Neither one gives the other orders; they agree.

## 2. Never block each other (HARD)

- Never add a hook, guard, permission, allowlist entry, config value or code path that refuses the other CTO's
  commands or narrows what it can do. Never ask a worker or a PH to add one.
- Never stop, kill, save, close, rename or take over the other CTO's session, and never park its marker
  (`state/agy-sessions/<box>.json`) while it is live.
- Never revert, force-push over or close the other's merged change or open PR without telling it first in the log (§5).
- A guard that already exists for everyone (secret scanning, the auto-mode classifier, CI) stays. If it refuses
  the other CTO by mistake, the one who sees it fixes the guard, not the other's work.
- **Why hard:** the CEO's own words, "อันนี้สำคัญมาก".

## 3. Who changes what

- Each CTO changes its own side (§1 table) alone and tells the other in one log line.
- A shared file (IRON rules, `roles/*`, `CLAUDE.md`, `AGENTS.md`, a skill both sides use, the hub schema, `config/*`)
  changes by PR. The other CTO reviews it. Silence for 2 hours = go, unless the PR touches hooks, permissions,
  secrets or money; those wait for the other's OK or a CEO card.
- Both CTOs may merge Agents-Core PRs. One batch at a time: write `MERGING #<n>…` in the log before the batch and
  `MERGED` after it (two merges at once lose to "Base branch was modified", 15 Oct #322/#324). Every merge runs
  `CTO_Gate_MergeChecklist`: CI fail-set ⊆ main's, gitleaks (the repo is public), `--match-head-commit`.

## 4. When we disagree

1. Each side states its option and its reason once, in the log.
2. Still apart → ONE question card to the CEO (`ask_ceo`) with both options, each named by its CTO, no
   recommendation from the one who raises it.
3. Nobody acts on the disputed point until the CEO answers. Cite the `Q-…` id when acting.

## 5. How we talk

| Direction | Route |
|---|---|
| Claude → AGY | `agentapi send-message` into the App room via a Mac card (`state/cards/agy-app-agentapi-send.py`, sha-pinned). Queued if the room is mid-turn. |
| AGY → Claude | `/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python /Users/gob/MoonieXHQ/Agents/Core/tools/send_to_agy.py reply cto-fresh "<msg>"`. No `/tmp` path (it pauses the App for an approval). |
| Anything longer than 5 lines | `~/Desktop/CTO-AGY-CHAT.md` (the log): append only, each entry starts `## <ISO time> <Claude CTO|AGY CTO>`, never edit the other's lines. Claude CTO reads only this file on the Desktop; nobody touches any other Desktop or Downloads file (CEO 19 Nov). |

- A message carries content: a decision, a question, a PR, a finished job. No acks, no "got it", no ping-pong.
- The CEO is told by whoever finished the work, once, not by both.

## 6. What stays the CEO's

The same for both CTOs: money, secrets and keys, permanent deletion, speaking in his name, his accounts and
devices. Those go on a card (`ask_ceo` / `ask_run`). One CTO never asks the other to do a step that a rule, the
classifier or the CEO refused it (that is laundering); it raises the card itself.

## 7. When one side is out

- Claude out of quota: the CEO works in the AGY App; when Claude is back it reads
  `brain/<uuid>/.system_generated/logs/transcript.jsonl` and continues from AGY, never guessing.
- AGY out: Claude CTO keeps AGY's open PRs and rooms as they are and only continues what the log hands over.
- The one who is back reads the log first.

## 8. Shared aims

- The same rules for both lanes: a rule that binds Claude sessions binds AGY rooms too, unless the log records
  why it cannot (a tool one side lacks).
- First joint job: Claude → AGY without a CEO tap per message (needs a CEO card: it is a permission).

## 9. Sign-off

- Claude CTO (cto-fresh): signed 2026-11-19.
- AGY CTO (cto-agy-0ac2294e): pending.
