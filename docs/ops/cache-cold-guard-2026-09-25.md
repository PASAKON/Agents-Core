# hook-cache-cold-warn.py

CEO ruling 2026-09-25 (task-a40d2d8e). Measured the same day in
`Wikis/research/2026-09-25-token-saving-techniques-caveman-survey.md`: 70
idle gaps >1h over 7 days produced 108 cache re-write spikes = 51M tokens,
~14% of the week's token bill. A C-level session idle past the 1-hour prompt
cache's TTL re-writes its whole context on the next turn as a fresh
cache-creation charge — roughly 2x a normal cache-read/base-input token.
This hook gives ONE blocking warning before that happens, so the human can
choose `/clear`, `/session-save`, or accept the cost and resend.

## hook-cache-cold-warn.py — UserPromptSubmit, no matcher (all prompts)

Reads the session's own transcript (`transcript_path` from stdin) for the
last assistant turn's `timestamp` and `message.usage` (`input_tokens +
cache_creation_input_tokens + cache_read_input_tokens` = context size).
Blocks (exit 2, warning on stderr) only when idle time AND context size both
clear their threshold AND no warning was already recorded for this session
within the grace window. Otherwise exit 0, silent.

**FAIL-OPEN**: any exception, missing file, bad JSON, or anything it cannot
cleanly determine → exit 0, print nothing. Reads only the transcript's tail
(8MB) so it stays comfortably under 3s even against a 50MB real transcript.

### Thresholds (env, all optional)

| Var | Default | Meaning |
|---|---|---|
| `ORG_COLD_IDLE_MIN` | `60` | minutes idle before a warning is eligible |
| `ORG_COLD_CTX_TOKENS` | `300000` | context size (tokens) before a warning is eligible |
| `ORG_COLD_GRACE_MIN` | `10` | minutes after a warning during which a resend passes untouched |
| `ORG_COLD_STATE_DIR` | `state/cache-cold` | where per-session warning state is written (tests point this at `tmp_path`) |

### Exemptions (exit 0, no state touched)

- `cwd` contains `/worktrees/` — a DEV/worker worktree, never a C-level
  session's cwd.
- `WORKER_TASK_ID` is set — the env marker `runners/worker_init.py` exports
  on every worker spawn (same marker `lib/notify.py` and
  `scripts/hook-inbox.py` use to recognize a worker).
- the prompt is a slash command (starts with `/`).
- the prompt is the org wake marker `tools/agent_transport.py`'s
  `attempt_wake()` types into a pane: literal `"[New message from {label}]"`.
  A blocked prompt is ERASED, and this is the one line the mailbox wake path
  actually submits as a real prompt.
- this session's own mailbox (`state/inbox/<role>-<session_id>/`) has
  letters waiting (checked non-destructively via `lib.mailbox.peek`).
  **Why beyond the literal wake-marker case**: verified against
  code.claude.com/docs/en/hooks (2026-09-25) that UserPromptSubmit hooks in
  the same settings array run in **parallel**, not sequentially — array
  order gives no protection. If this hook blocked an ordinary prompt while
  `scripts/hook-inbox.py` (also on UserPromptSubmit) happened to run in the
  same tick, `lib.mailbox.drain()` (destructive, exactly-once) would still
  empty the box, but its stdout is discarded along with the rest of the
  erased turn — the letter would be gone with nothing shown. Peeking first
  and standing down whenever mail is waiting removes that race for every
  prompt, not only the literal wake text.

### State

`state/cache-cold/<session_id>.json` (gitignored — `state/cache-cold/.gitignore`
contains `*`; the root `.gitignore` is untouched):

```json
{"last_warned_at": "2026-09-25T15:30:00+00:00", "idle_minutes": 125.3, "ctx_tokens": 605002, "model": "claude-opus-5-5"}
```

### Warning text

One line to stderr, Thai+English, e.g.:

```
idle 2h5m · context 605k tokens · เทิร์นนี้จะ re-write cache ทั้งหมดที่ราคา 2x
(API-equivalent ≈ $4.84 ที่ Opus 5.5 $8/MTok cache-write) · ตัวเลือก: /clear
(เริ่มใหม่), /session-save (พักไว้ก่อน resume แบบย่อ), หรือส่งข้อความเดิมซ้ำเพื่อไปต่อตามเดิม
```

Per-1M-cache-write-token price by session model (substring match on
`message.model`, org standard Opus 5.5 price used as fallback for an
unrecognized model): Fable 5.1 `$20`, Opus 5.5 `$8`, Sonnet 5 `$4`.

## Testing by hand

```bash
echo '{"session_id":"s1","transcript_path":"/path/to/real/transcript.jsonl","prompt":"status?","cwd":"/Users/gob/MoonieXHQ/Agents/Core"}' \
  | python3 scripts/hook-cache-cold-warn.py; echo "exit=$?"
```

Exit 0 + silent when the session isn't stale enough, or when a warning for
that session was already recorded within the grace window. Exit 2 + the
warning on stderr the first time a session clears both thresholds.

A real ~/.claude transcript is READ-ONLY here — the hook never writes to it,
only to its own state dir.

## Automated tests

```bash
.venv/bin/python -m pytest tests/test_hook_cache_cold_warn.py -q
```

## Rollback

Remove the `hook-cache-cold-warn.py` entry from `.claude/settings.json`'s
`UserPromptSubmit` array (added as the first hook in the array; every other
hook in that array — `hook-log-prompt.py`, `hook-recall.py`,
`hook-skill-suggest.py`, `hook-memory-nudge.py`, `hook-inbox.py` — is
untouched and keeps working with the entry gone). `state/cache-cold/` can be
deleted at any time; it is pure per-session cache, nothing depends on it
surviving.
