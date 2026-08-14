"""DEV -> owning C-level mailbox: queue a message into the owner's inbox,
then attempt a best-effort wake. Mirror of `tools/send_to_dev.py`, opposite
direction.

Task task-2f04a8ca (CEO directive 2026-08-14, same migration as
`send_to_dev.py` -- see that file's docstring for the full CEO quote and
the day's history it traces to). Used by the DEV's Stop hook
(`scripts/hook-log-dev-reply.py`) so every DEV reply reaches the owning
C-level's mailbox instead of being typed into that C-level's iTerm tab.

Routing (issue #15, preserved as-is -- this task only swaps the transport):
  * `cto_id` + `owner_role` identify the owning C-level session
    (`tasks.owner_cto` / `tasks.owner_role`). The letter is queued ONLY
    into that one session's box -- never broadcast.
  * `cto_id=None` (ownerless task) does not broadcast either. By default
    the message is dropped to `state/orphan-dev-replies-unowned.log` and
    `False` is returned -- unchanged from before this task, per the brief
    ("that safety net is unrelated to the transport"). Single-CTO setups
    that want the legacy broadcast still opt in via
    `SEND_TO_CTO_BROADCAST=1`; the broadcast itself now queues+wakes every
    live C-level session's mailbox instead of typing into every "CTO Chat"
    tab -- same opt-in gate, same log-file safety net, new transport
    underneath, per the same "delete the typing path, don't keep it as a
    fallback" rule this whole migration follows (GH #69's lesson).

What changed vs. the old `send()`: it used to resolve `<owner_role>-<cto_id>
.winid` and type into that iTerm window via AppleScript, logging to
`state/orphan-dev-replies-<cto_id>.log` and returning `False` whenever the
winid file was missing or the window couldn't be found -- "delivered" was
defined as "a window matched". `lib.mailbox` redefines delivery as "the
letter exists in the recipient's box", which has no dependency on any
window/winid existing at all, so that whole reachability check (and its
`_read_winid` legacy-fallback-filename logic) is gone: a known owner
(`cto_id` given) now always succeeds -- the write either lands or raises,
matching every other file in this migration's "queued or raised, never
probably" contract. The only remaining case that can return `False`
without raising is the ownerless-task safety net above, which this task
was told to leave alone.

The message is prefixed via the wake marker's `label` (e.g. "Developer
task-2f04a8ca") so a human glancing at the owner's pane, and the letter's
`from` field itself, both show who's talking -- never a typed
`[<Role> <id>]:` string in a terminal composer.

Usage:
    python -m tools.send_to_cto <from_id> "<message>" [role] [cto_id] [owner_role]
    python -m tools.send_to_cto task-161dbcf7 "patch ready, please review"
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import mailbox  # noqa: E402
from lib.config import display_for, live_c_level_roles  # noqa: E402
from tools import agent_transport, session_name  # noqa: E402
from tools.agent_transport import _wake_tmux_send  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"


def _log_orphan(cto_id: str, from_id: str, role: str | None,
                message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    snippet = repr(message[:80])
    log_path = STATE_DIR / f"orphan-dev-replies-{cto_id}.log"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] from={from_id} role={role or 'unknown'} msg={snippet}\n")


def _attempt_wake(role: str, session_id: str, label: str) -> None:
    """Best-effort attention nudge for the just-delivered letter's C-level
    recipient. Same isolation guarantee as `send_to_cxo._attempt_wake()`:
    nothing here may raise or change `send()`'s return value.

    Unlike `send_to_dev.py`'s DEV-side wake, the target here is always a
    C-level session -- `cto-claude.sh` / `cxo-claude.sh` always launch
    inside `tmux new-session -A -s <role>-<id>`, so
    `session_name.lock_basename(role, session_id)` reliably names a live
    tmux session whenever that C-level's tab is actually open. This is the
    direction the wake mechanism was originally proven for.

    Delegates the actual wrap/log/never-raise nudge to
    `tools.agent_transport.attempt_wake()` (task task-eb0d9863) --
    `send_fn=_wake_tmux_send` is this module's own imported reference,
    resolved in THIS module's globals, so a test that monkeypatches
    `tools.send_to_cto._wake_tmux_send` is still honored.
    """
    session = session_name.lock_basename(role, session_id)
    agent_transport.attempt_wake(session, label, "send_to_cto", send_fn=_wake_tmux_send)


def send(from_id: str, message: str, role: str | None = None,
         cto_id: str | None = None, owner_role: str = "cto") -> bool:
    """Queue `message` into the owning C-level's mailbox, then attempt a
    wake. Returns `True` once the letter is queued.

    `role` is the DEV's role key (e.g. `web_designer`); its display label
    (e.g. `Web Designer`) names the sender in the wake marker. Falls back
    to `Dev` when role is missing or unknown.

    `cto_id` + `owner_role`: the owning session identifies the mailbox box
    directly (`(owner_role, cto_id)`) -- no window/winid lookup, so a known
    owner always succeeds; this call either returns `True` or raises
    whatever `lib.mailbox.send()` raises (disk full, permission denied --
    no silent partial failure).

    `cto_id=None` (ownerless task): unchanged from before this task -- the
    message is dropped to `state/orphan-dev-replies-unowned.log` and
    `False` is returned, no broadcast, unless `SEND_TO_CTO_BROADCAST=1` is
    set, in which case it queues+wakes every live C-level session instead
    of the old broadcast-by-typing.
    """
    label = display_for(role) if role else "Dev"
    from_role = role or "dev"
    wake_label = f"{label} {from_id}"

    if cto_id:
        mailbox.send(owner_role, cto_id, message, from_role, from_id)
        _attempt_wake(owner_role, cto_id, wake_label)
        return True

    if os.environ.get("SEND_TO_CTO_BROADCAST") != "1":
        _log_orphan("unowned", from_id, role, message)
        sys.stderr.write(
            f"[send_to_cto] ownerless message from {from_id} dropped to "
            f"state/orphan-dev-replies-unowned.log "
            f"(set SEND_TO_CTO_BROADCAST=1 to broadcast to all live C-level sessions)\n"
        )
        return False

    delivered_any = False
    for r in live_c_level_roles():
        sid = agent_transport._active_session_id(r)
        if not sid:
            continue
        mailbox.send(r, sid, message, from_role, from_id)
        _attempt_wake(r, sid, wake_label)
        delivered_any = True
    return delivered_any


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: python -m tools.send_to_cto <from_id> "<message>" '
              '[role] [cto_id] [owner_role]', file=sys.stderr)
        return 1
    role = sys.argv[3] if len(sys.argv) > 3 else None
    cto_id = sys.argv[4] if len(sys.argv) > 4 else None
    owner_role = sys.argv[5] if len(sys.argv) > 5 else "cto"
    ok = send(sys.argv[1], sys.argv[2], role=role, cto_id=cto_id,
              owner_role=owner_role)
    print("queued" if ok else "orphaned (see state/orphan-dev-replies-*.log)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
