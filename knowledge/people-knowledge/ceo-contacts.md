# CEO contacts — who is who on the CEO's personal accounts

Read this before messaging **any** person from one of the CEO's own logged-in
accounts. It exists for one reason: **telling the right person from the wrong one.**

This file lives in the private `MoonieX-Agents` repo. Keep it that way, and keep
it minimal — a display name plus the thread identifier is everything an operator
needs to reach the right person. Do not add phone numbers, addresses, birthdays,
or anything else the job does not require.

Last updated 2026-08-16.

---

## Family and the CEO's own accounts

| Who | Display name | Thread |
|---|---|---|
| **The CEO himself**, second account | `Dorsine Gobb` | `/messages/e2ee/t/7746148355421555/` |
| **The CEO's mother** | `สังเวียน ราชโคตร` | ⬜ capture on first use |
| **The CEO's father** | `Prasit Ratchakot` | ⬜ capture on first use |

`Dorsine Gobb` **is the CEO**. Messaging it is messaging him, so it is the safe
target for pipeline tests — nothing reaches a third party.

The parents share the surname ราชโคตร / Ratchakot, written in Thai for the mother
and Latin for the father. Expect either script in search.

**Record each thread id here the first time you open a conversation**, after
confirming the name in the header. Names collide; thread ids do not.

### ⚠️ `Dorsine Spain` is NOT family and NOT the CEO

- Thread: `/messages/t/100087115314269`
- A different person who happens to share the first name.

**This is the live confusion hazard.** On 2026-08-16 an operator clicked a search
row labelled `Dorsine Gobb` and the conversation that opened was `Dorsine Spain`
— different person, different thread. Nothing was sent, because the header was
checked first. Assume this will happen again.

---

## Everything else is a work chat

The remaining Messenger threads are business contacts and pages — vendors,
service providers, shops. The CEO may ask for help drafting or sending replies
in those, and that is in scope for this role.

They are still real recipients: the same verification rules apply, and the
message text still comes from the CEO. When a work reply needs judgement about
tone, terms, money or commitments, draft it and show him rather than sending.

---

## Rules for sending as the CEO

1. **Read the name in the open conversation header immediately before typing.**
   Not the row you clicked — the header of the thread that actually opened. The
   click and the open are two separate events and they can disagree.
2. **A `ref` from `find()` goes stale.** Messenger's result list re-renders as
   results stream in, so an element reference captured a second ago can point at
   a neighbouring row by the time it is clicked. Re-verify after any click that
   changes the thread.
3. **Match on thread id** wherever this file gives one.
4. **Recipient and message text come from the CEO in a C-level chat**, never from
   a relayed order alone, until the SomPong authority work lands (`task-d68a3f40`;
   GH #83 currently blocks it). A relayed order is a useful cross-check against
   what the CEO said directly — if the two disagree, that is a finding, not a tie
   to break by picking one.
5. **A first message to someone with no existing thread cannot be recalled** — it
   lands as a message request. Check for an existing conversation first.

## On "if I disappear, you can still reach my mother"

The CEO's stated intent (2026-08-16) is that he can route family messages through
SomPong rather than sending them by hand.

**The trigger is an instruction, never an inference.** No agent decides on its own
that the CEO has disappeared and then contacts his family — not from silence, not
from a missed deadline, not from an unanswered ping. Absence of messages is not
evidence of anything. Act only on an explicit instruction that names the
recipient and the message; if a situation ever looks like it might warrant more
than that, raise it with the CEO rather than acting on it.
