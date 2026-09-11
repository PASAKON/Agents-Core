# Task briefs to winbox lose every non-ASCII character

Found 2026-09-12 03:00 by the CTO, surfaced by a worker that correctly refused to act.

## What happens

A task description containing Thai text and emoji arrived on winbox with every
non-ASCII character replaced by `?`. Measured on task-9e45edb2:

| | |
|---|---|
| description stored in `state/tasks.db` | **2,058 chars, complete and correct** |
| `TASK.md` written into the worker's worktree | Thai replaced by `?`, `⚠️` became `??` |

Line 17 of that TASK.md reads, verbatim:

```
the CEO replying "???????? ??? AI ?????????????????"
```

The whole MESSAGE body of that task was Thai, so it arrived as a wall of question
marks. The worker read that as "no message text was included" and stopped — which
was the right call, and the only reason this was caught instead of a mangled
message reaching a real person.

## Why it matters beyond cosmetics

It is **not truncation**. The text is there; the characters are destroyed. A brief
can therefore look complete and be silently wrong — every Thai proper noun, quoted
line of dialogue, character name or file name in it becomes `?`. On this project
that includes dialogue, the CEO's own instructions and most prompt-sheet content.

## What to do

1. **Write winbox task descriptions in ASCII only.**
2. **Any non-ASCII content travels as a file**, copied with `scp`, which preserves
   bytes exactly. Verify with md5 on both sides — it costs one command:

```bash
scp -q msg.txt winbox:'C:/mooniex/line/msg.txt'
md5sum msg.txt
ssh -n winbox 'powershell -NoProfile -Command "(Get-FileHash C:\mooniex\line\msg.txt -Algorithm MD5).Hash.ToLower()"'
```

   Verified working: md5 matched on both sides and the Thai read back correctly
   on winbox with `Get-Content -Encoding UTF8`.
3. Tell the worker in the brief which file to read and with what encoding.

## Not fixed here

The real fix is in whatever writes `TASK.md` on the remote spawn path
(`tools/delegate.py` → `windows/spawn-worker.ps1`) — it needs to write UTF-8
instead of the console codepage. Left for whoever owns the dispatch work; the CEO
parked that topic and this is a workaround, not a repair.
