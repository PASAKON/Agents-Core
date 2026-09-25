#!/usr/bin/env python3
"""UserPromptSubmit hook: warn once when a stale C-level session is about to
re-write its whole 1-hour prompt cache at 2x input price.

CEO ruling 2026-09-25 (task-a40d2d8e). Measured 2026-09-25 in
Wikis/research/2026-09-25-token-saving-techniques-caveman-survey.md: 70 idle
gaps >1h over 7 days produced 108 cache re-write spikes = 51M tokens, ~14% of
the week's token bill. The 1-hour prompt cache is dead once a session sits
idle past its TTL -- the next turn re-writes the entire context as a fresh
cache-creation charge, which is priced roughly 2x a cache-read/base-input
token. This hook fires on UserPromptSubmit, checks the session's own
transcript for idle time + context size, and -- once per stale window, never
twice in a row -- blocks the prompt (exit 2) with a warning so the human can
choose `/clear`, `/session-save`, or just resend to accept the cost.

FAIL-OPEN CONTRACT: any exception, missing file, bad JSON, or anything this
hook cannot cleanly determine -> exit 0, print nothing. This hook must never
be the reason a real prompt gets stuck, and must finish in well under the
UserPromptSubmit budget (checked empirically: comfortably <3s even against a
50MB real transcript, since only the tail is read -- see
`_find_last_assistant_usage`).

Hook stdin contract (code.claude.com/docs/en/hooks, confirmed against a real
transcript in ~/.claude/projects/-Users-gob-MoonieXHQ-Agents-Core/*.jsonl):
`session_id`, `transcript_path`, `prompt`, `cwd`. Exit 2 blocks + erases the
prompt and shows stderr to the human; exit 0 lets it through (stdout would
become context, but this hook never prints on the non-blocking path -- it
fires on every single prompt of every C-level session and silence must cost
nothing, same rule `hook-inbox.py` documents for itself).

Exemptions (exit 0, no state touched):
  - `cwd` contains "/worktrees/" -- DEV/worker worktrees, never a C-level
    session's cwd (a C-level session always runs with cwd = repo root).
  - `WORKER_TASK_ID` is set in the environment -- the marker
    `runners/worker_init.py` exports on every worker spawn (also read by
    `lib/notify.py` and `scripts/hook-inbox.py` for the same purpose).
  - the prompt is a slash command (starts with "/").
  - the prompt is the org wake marker typed into a pane by
    `tools/agent_transport.py`'s `attempt_wake()` -- literal template
    `"[New message from {label}]"`. A blocked prompt is ERASED, and this is
    the one line the mailbox wake path actually submits as a real prompt
    (the letter body itself arrives separately, printed as context by
    `scripts/hook-inbox.py` on whatever prompt follows) -- blocking it would
    silently drop the wake and the letter would just sit undelivered-looking
    until the next unrelated human prompt happens to drain it.
  - this session's own mailbox (`state/inbox/<role>-<session_id>/`, drained
    by `scripts/hook-inbox.py` on every prompt) has letters waiting -- see
    `_has_pending_mail()`. Verified against code.claude.com/docs/en/hooks
    2026-09-25: UserPromptSubmit hooks in the same settings array run in
    PARALLEL, not sequentially, so array order gives no protection -- if
    this hook blocks a prompt, `hook-inbox.py` can still fire in the same
    tick, `lib.mailbox.drain()` it (destructive, exactly-once) and have its
    stdout discarded along with the rest of the erased turn. Peeking
    (non-destructive) and standing down whenever mail is waiting removes
    that race for every prompt, not just the literal wake-marker text.

Grace window: once a warning fires for a session, a resend within
ORG_COLD_GRACE_MIN minutes passes through untouched (state file's
`last_warned_at` is checked before idle/ctx thresholds) -- otherwise the
CEO's own instructed recovery move ("send the same message again") would
just get blocked again forever.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# runners/worker_init.py exports this on every worker spawn (env["WORKER_TASK_ID"]
# = task_id); lib/notify.py and scripts/hook-inbox.py key off the same var to
# tell a worker process apart from a C-level session.
WORKER_ENV_MARKER = "WORKER_TASK_ID"

# tools/agent_transport.py: _WAKE_MARKER_TEMPLATE = "[New message from {label}]"
WAKE_MARKER_PREFIX = "[New message from"

# Only the tail of the transcript is ever read -- the last assistant turn is
# always within a few hundred KB of EOF in practice, and this keeps the hook
# fast against a real multi-hour transcript that can run past 50MB.
TAIL_BYTES = 8_000_000

MODEL_PRICE_PER_MTOK = (
    ("fable", 20.0),
    ("opus", 8.0),
    ("sonnet", 4.0),
)
MODEL_LABELS = (
    ("fable", "Fable 5.1"),
    ("opus", "Opus 5.5"),
    ("sonnet", "Sonnet 5"),
)
DEFAULT_PRICE = 8.0  # org standard model (Opus 5.5) when the model string is unrecognized


def _state_dir() -> Path:
    override = os.environ.get("ORG_COLD_STATE_DIR")
    if override:
        return Path(override)
    return ROOT / "state" / "cache-cold"


def _tail_bytes(path: Path, max_bytes: int) -> bytes:
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > max_bytes:
            f.seek(size - max_bytes)
        return f.read()


def _find_last_assistant_usage(transcript_path: Path):
    """(timestamp_str, model, usage_dict) for the last assistant turn found
    in the transcript's tail, or None if none is found there."""
    data = _tail_bytes(transcript_path, TAIL_BYTES)
    text = data.decode("utf-8", errors="replace")
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") != "assistant":
            continue
        ts = obj.get("timestamp")
        msg = obj.get("message") or {}
        usage = msg.get("usage")
        if not ts or not usage:
            continue
        return ts, msg.get("model"), usage
    return None


def _idle_minutes(ts_str: str, now: datetime) -> float:
    s = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 60.0


def _ctx_tokens(usage: dict) -> int:
    return (
        int(usage.get("input_tokens") or 0)
        + int(usage.get("cache_creation_input_tokens") or 0)
        + int(usage.get("cache_read_input_tokens") or 0)
    )


def _lookup(model: str, table, default):
    model_l = (model or "").lower()
    for key, value in table:
        if key in model_l:
            return value
    return default


def _has_pending_mail() -> bool:
    """True if THIS session's own mailbox box has letters waiting (same
    (role, session_id) resolution `scripts/hook-inbox.py`'s `_current_box()`
    uses for a C-level session). Non-destructive (`lib.mailbox.peek`) --
    never drains anything itself."""
    role = os.environ.get("CXO_ROLE")
    if not role:
        return False
    sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
    if not sid:
        return False
    try:
        from lib import mailbox
        return bool(mailbox.peek(role, sid))
    except Exception:
        return False


def _read_last_warned(state_path: Path) -> datetime | None:
    try:
        data = json.loads(state_path.read_text())
        ts = data.get("last_warned_at")
        if not ts:
            return None
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _format_warning(idle_minutes: float, ctx_tokens: int, model: str) -> str:
    h = int(idle_minutes // 60)
    m = int(idle_minutes % 60)
    k_tokens = round(ctx_tokens / 1000)
    price = _lookup(model, MODEL_PRICE_PER_MTOK, DEFAULT_PRICE)
    label = _lookup(model, MODEL_LABELS, model or "unknown model")
    cost = ctx_tokens / 1_000_000 * price
    return (
        f"idle {h}h{m}m · context {k_tokens}k tokens · เทิร์นนี้จะ re-write cache "
        f"ทั้งหมดที่ราคา 2x (API-equivalent ≈ ${cost:.2f} ที่ {label} "
        f"${price:.0f}/MTok cache-write) · ตัวเลือก: /clear (เริ่มใหม่), "
        "/session-save (พักไว้ก่อน resume แบบย่อ), หรือส่งข้อความเดิมซ้ำเพื่อไปต่อตามเดิม"
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    try:
        prompt = str(payload.get("prompt") or "")
        cwd = str(payload.get("cwd") or "")
        session_id = str(payload.get("session_id") or "")
        transcript_path = payload.get("transcript_path")

        if "/worktrees/" in cwd:
            return 0
        if os.environ.get(WORKER_ENV_MARKER):
            return 0

        stripped = prompt.strip()
        if stripped.startswith("/"):
            return 0
        if stripped.startswith(WAKE_MARKER_PREFIX):
            return 0

        if not session_id or not transcript_path:
            return 0
        tp = Path(transcript_path)
        if not tp.exists():
            return 0

        found = _find_last_assistant_usage(tp)
        if not found:
            return 0
        ts, model, usage = found

        idle_threshold_min = int(os.environ.get("ORG_COLD_IDLE_MIN", "60"))
        ctx_threshold = int(os.environ.get("ORG_COLD_CTX_TOKENS", "300000"))
        grace_min = int(os.environ.get("ORG_COLD_GRACE_MIN", "10"))

        now = datetime.now(timezone.utc)
        idle_minutes = _idle_minutes(ts, now)
        ctx_tokens = _ctx_tokens(usage)

        if idle_minutes < idle_threshold_min or ctx_tokens < ctx_threshold:
            return 0

        if _has_pending_mail():
            return 0

        state_dir = _state_dir()
        state_path = state_dir / f"{session_id}.json"
        last_warned = _read_last_warned(state_path)
        if last_warned is not None:
            since_warn_min = (now - last_warned).total_seconds() / 60.0
            if since_warn_min < grace_min:
                return 0

        state_dir.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({
            "last_warned_at": now.isoformat(),
            "idle_minutes": round(idle_minutes, 1),
            "ctx_tokens": ctx_tokens,
            "model": model,
        }))

        print(_format_warning(idle_minutes, ctx_tokens, model), file=sys.stderr)
        return 2
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
