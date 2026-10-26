---
name: ALL_Protocol_EmailCEO
kind: protocol
owner: CTO
description: "PROTOCOL — Email the CEO (pass.gob1@gmail.com) through the org MCP tool `email_ceo` / tools/email_ceo.py, the only sanctioned way. Four kinds only: ACTION (a decision only he can make, blocking work; buzzes), ALERT (money, a customer or security is being hurt now; buzzes), DONE (an order he gave is finished, link to the result; silent), DEADLINE (one of his to-dos is due within 24 h; no mail, the 08:00 digest carries it). Trigger on /ALL_Protocol_EmailCEO, when you are blocked on his decision and he is not in this chat, when something is breaking money/customers/security, when you finish an order he gave and he is away, or the moment you think 'I should tell the CEO by email'. Do NOT fire for progress, FYI, anything he can read in this chat now, or a Run card / relay request (those email him by themselves). C-level sessions only; a worker reports to its C-level."
created_by: agent
author: {role: cto, date: "2026-10-02"}
audience: [cxo]
---

# Email the CEO — four kinds, one format, hard caps

> CEO 2026-10-02: "สร้าง Skill ในการส่ง Email หา CEO … การเรียกใช้ได้ด้วยเหตุผลไหน และ Pattern + หน้าตาการส่ง"
> — and he chose: ACTION + ALERT buzz · an 08:00 digest · no quiet hours · C-level senders only.

The CEO reads email on his phone. Each mail that is not worth his time trains him to ignore the
next one, and then the ACTION that mattered is missed. So the channel is narrow on purpose, and the
**caps are enforced by the hub**, not by your judgement (Console `src/notify/ceo.js`).

## Rule 1 — which kind (if none fits, do not send)

| kind | send when | he must | phone |
|---|---|---|---|
| `action` | You need a decision **only he** can make, it **blocks** work, and he is not in this chat. Example: approve spend, pick A/B, a ruling. | do one thing | buzzes |
| `alert` | Something is breaking **money, a customer or security** right now (leak, outage, a charge, a refund storm). | know now | buzzes, any hour |
| `done` | An order **he gave** is finished and there is a result to open (merged, posted, deployed, file on Drive). | open it later | silent |
| `deadline` | One of **his** to-dos falls due within 24 h. Usually sent by the timer, not by you. | see it at 08:00 | no mail (digest) |

For `done`, the 07:50 feed sends the daily merged-PR line (ref `merge-digest-<date>`), so a merger sends no merge mail.

**Never send:**
- progress or "still working"
- FYI or background
- a question you could decide yourself (code decisions are yours, see ALL_Rules_Approvals)
- anything he can read in this chat right now
- a Run card or relay request, which already mail him (ALL_Protocol_RunInbox, relay-login)
- a secret value, which the tool refuses

## Rule 2 — the format (fixed; the hub builds it from your fields)

**≤5 lines, enforced (CEO 2026-10-14: ≤5 lines total, alert only, plain words, detail in a linked
file).** `title` + `need` + `why` + `if_not` + `link` + `due` together are at most 5 lines of at most
90 chars; the title is line 1, an empty line counts, a lone link may run to 200. `ref` and the hub's
`จาก:` line do not count. The tool refuses more (exit 2) and no flag skips it (`lib/ceo_text.py`).

Subject: `[KIND][ROLE] <title> — N-xxxx`. From: `MoonieX <ROLE>`. Body: one labelled fact per line.

```
[ACTION][CTO] อนุมัติเครดิต Flow 300 สำหรับ EP3 — N-1a2b

ต้องการจากคุณ: ตอบ "อนุมัติ/ไม่" ในแชท CTO
ทำไม: script EP3 ผ่าน lint แล้ว พร้อมยิง
ถ้าไม่ทำ: EP3 ไม่ทันโพสต์ เสาร์ 19:30
เปิด: https://terminal.mooniex.com/…        ← lands on the thing itself
เรื่อง: ep3-credits
จาก: CTO · cto-e106b78b · contabo
```

| field | rule |
|---|---|
| `title` | One line, ≤ 90 chars. Start with the verb of what he must do or what happened: "อนุมัติ…", "เลือก…", "โพสต์ EP2 แล้ว". |
| `need` | **The ONE action**, phrased so he can do it from the phone. Required for `action`. |
| `why` | ≤ 90 chars a line, plain Thai, no jargon he must look up. For `done` this is the result. |
| `if_not` | What happens if he does nothing, with a time. Strongly advised for `action`. |
| `link` | One URL that opens the thing itself: the card, the PR, the Drive file, the session. Never a home page. Required except for `deadline`. |
| `ref` | Task id, issue or slug. The same kind + ref within 6 h is a duplicate. |
| `due` | `deadline` only. |

Write it in the CEO's language: Thai, short. No emoji, no secrets, no "please". He reads it on a
lock screen.

## Rule 3 — the caps (hub-enforced; a refusal is an answer, not an error to retry)

- **3 mails per session per Thai day.** An `alert` is exempt. If you hit the cap, fold the rest
  into one mail, or let the 08:00 digest carry `done` items. Never open a new session to dodge it.
- **20 mails per day for the whole org.** Past that, everything waits for the digest.
- **Duplicates.** The same kind + ref within 6 h → 409 `duplicate`, naming the first mail. Do not
  change the ref to resend; the first one is in his inbox.
- **30 deadlines a day.**

## Rule 4 — how to send

```
mcp__org__email_ceo(kind="action", title="…", need="…", why="…", if_not="…", link="https://…", ref="task-1234")
```
CLI on any box with the Run token:
`python3 tools/email_ceo.py send --kind action --title … --need … --why … --link … [--if-not …] [--ref …]`.
Add `dry_run=True` / `--dry-run` to see the exact subject and body without sending. Role and
session come from the session env.

**Returns:** `{id, mailed, buzz, quota:{session_left, day_left}}`. Say in **one chat line** what you
sent (id + kind + title). A refusal (`invalid_*`, `missing_field`, `secret_shape`, `*_cap`,
`duplicate`) names its reason: fix the field or stop. Never retry a cap.

## The 08:00 digest (automatic; you do nothing)

Console `scripts/ceo-digest.mjs` runs at 08:00 Asia/Bangkok (`ceo-digest.timer`) and sends one
buzzing mail. It covers everything since the last digest, in this order:

1. what is waiting for him right now (open relay requests, pending cards)
2. cards that expired unseen
3. the ACTION and ALERT mails
4. deadlines
5. DONE mails

Empty = no mail. At 07:50 Asia/Bangkok, `ceo-deadline-feed.timer` (Agents-Core
`deploy/ceo-deadline-feed.*`) turns his LungNote to-dos due in the next 24 h into `deadline` rows.

## Where things live

| what | where |
|---|---|
| API, caps, format | MoonieX-Console `src/notify/ceo.js`, docs `docs/run.md` §CEO mail |
| Digest | Console `src/notify/digest.js`, `scripts/ceo-digest.mjs` |
| Delivery | Console `scripts/run-mail-sender.mjs`. Gmail `users.messages.insert`, own inbox only; UNREAD = buzz. |
| Requester + deadline feeder | Agents-Core `tools/email_ceo.py`, MCP tool `email_ceo` |
| Ledger of every mail | Console `data/ceo-mail-ledger.jsonl` (Contabo) |

## Field notes

- 2026-10-13 [MISSING] Rule 1 + Rule 3 — a reminder sent by a timer: `deadline` is never mailed (digest only, and a row written after 08:00 waits a whole day), so a reminder he must act on is `action`. Give the timer its own session name, because the 3-a-day cap counts by session string (`cto-contabo-invoice`, as `cto-deadline-feed` does). Use one ref per occurrence (`contabo-invoice-<YYYY-MM>-d<N>`), so two reminders are never duplicates. Fire early in the Thai day (08:30), because the org's 20-mail cap counts every mailing kind, `alert` included · evidence: session cto-b203a039, tools/contabo_invoice_reminder.py 36788b36, test mail N-7aa3 · status: pending
