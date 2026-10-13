#!/usr/bin/env python3
"""UserPromptSubmit hook: every N turns, ask whether the session name still
matches the current job (CEO order 2026-10-13, relayed by SomPong).

CEO: "การคุยมีการเปลี่ยนแปลงไปเรื่อยๆ ตามงานที่ทำ การ rename นั้นสำคัญจะได้กลับมาดูได้ง่าย".
The rule itself is event-based and lives in session-open §3 and session-save:
rename whenever the main job changes, and at /session-save. This hook is only
the safety net for a job that drifted without anyone noticing. It prints ONE
line every N turns and nothing otherwise. It never renames (an agent typing
into its own pane is refused by the auto-mode classifier as Self-Modification,
session-open field note 2026-09-30) and never blocks a prompt.

Shape deliberately matches scripts/hook-memory-nudge.py: event JSON on stdin,
one line on stdout, fail silent with return 0 on any error.

Who gets it: interactive C-level sessions (CXO_SESSION=1 or CTO_SESSION=1, set
by cto-claude.sh / cxo-claude.sh). Silent for:
  - SomPong (CXO_ROLE=coo): its name is fixed;
  - workers: WORKER_TASK_ID set (runners/worker_init.py) or cwd under /worktrees/;
  - headless runs: Claude Code sets CLAUDE_CODE_ENTRYPOINT=cli only for an
    interactive session (sdk-cli for `claude -p`, sdk-ts/sdk-py for the SDKs).

Cadence: RENAME_NUDGE_N (default 20). Counter: state/rename-nudge-counters.json
keyed by Claude session id, entries untouched for 30 days are dropped. A runtime
artifact (gitignored), like state/session-nudge-counters.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_N = 20
PRUNE_AFTER_S = 30 * 86400


def _state_dir() -> Path:
    # Tests point this at tmp_path; a test that wrote real state broke ~/.claude
    # links once (docs/ops/cache-cold-guard-2026-09-25.md).
    return Path(os.environ.get("RENAME_NUDGE_STATE_DIR") or ROOT / "state")


def _exempt(payload: dict) -> bool:
    env = os.environ
    if env.get("CXO_SESSION") != "1" and env.get("CTO_SESSION") != "1":
        return True
    if env.get("CXO_ROLE") == "coo":
        return True
    if env.get("WORKER_TASK_ID") or "/worktrees/" in str(payload.get("cwd") or ""):
        return True
    return env.get("CLAUDE_CODE_ENTRYPOINT", "cli") != "cli"


def _bump(counter_path: Path, session_id: str) -> int:
    try:
        counters = json.loads(counter_path.read_text(encoding="utf-8"))
        if not isinstance(counters, dict):
            counters = {}
    except Exception:
        counters = {}
    now = int(time.time())
    entry = counters.get(session_id)
    turn = (int(entry.get("n", 0)) if isinstance(entry, dict) else 0) + 1
    counters = {
        k: v for k, v in counters.items()
        if isinstance(v, dict) and now - int(v.get("t", 0)) < PRUNE_AFTER_S
    }
    counters[session_id] = {"n": turn, "t": now}
    counter_path.parent.mkdir(parents=True, exist_ok=True)
    # Per-process tmp name: two sessions submitting at the same instant must not
    # write into one shared tmp file.
    tmp = counter_path.with_name(f"{counter_path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(counters), encoding="utf-8")
    os.replace(tmp, counter_path)
    return turn


def _recorded_name(state_dir: Path) -> str:
    # The topic scripts/session-rename.sh last sent. It may not have landed
    # (session-open §3), so it is shown as "last set", never as the name.
    role = os.environ.get("CXO_ROLE") or "cto"
    sid = os.environ.get("CTO_SESSION_ID") or os.environ.get("CXO_SESSION_ID") or ""
    if not sid:
        return ""
    try:
        return (state_dir / "locks" / f"{role}-{sid}.topic").read_text(
            encoding="utf-8").strip()[:60]
    except Exception:
        return ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict) or _exempt(payload):
        return 0
    session_id = payload.get("session_id") or payload.get("sessionId") or ""
    if not session_id:
        return 0

    n = DEFAULT_N
    try:
        n = int(os.environ.get("RENAME_NUDGE_N", DEFAULT_N))
    except ValueError:
        pass
    if n < 1:
        n = DEFAULT_N

    state_dir = _state_dir()
    try:
        turn = _bump(state_dir / "rename-nudge-counters.json", session_id)
    except Exception:
        # A miscounted nudge is harmless; a blocked prompt is not.
        return 0
    if turn % n != 0:
        return 0

    name = _recorded_name(state_dir)
    last = f' (last set: "{name}")' if name else ""
    # One line, paid for only on the turn it fires (ADR 0016).
    print(
        f"[rename nudge] turn {turn}{last} — does the session name still match "
        f"the current job? If not, rename (session-open §3)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
