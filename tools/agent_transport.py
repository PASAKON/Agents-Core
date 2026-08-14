"""Direction-agnostic transport primitives shared by tools/send_to_worker.py,
tools/send_to_cto.py, and tools/send_to_cxo.py.

Task task-eb0d9863 (CEO asked why the 3 send_to_*.py files aren't one file).
Real answer: they already shared code, but wrongly -- send_to_worker.py and
send_to_cto.py both imported underscore-prefixed private names
(`current_identity`, `_resolve_sender_role`, `_active_session_id`,
`_wake_tmux_send`, `_WAKE_MARKER_TEMPLATE`) straight out of send_to_cxo.py,
which only became "the shared library" by being written first -- its own
module docstring/purpose (C-level peer-to-peer send + `--spawn`
ephemeral-tab cold-start) has nothing to do with being a dependency of the
other two. A full merge into one file/one CLI was explicitly out of scope
(19 files reference the 3 modules by name; renaming call sites for a
cosmetic win isn't worth the risk). This module holds only the genuinely
shared, direction-agnostic pieces; each send_to_*.py file keeps its own
logic for RESOLVING which session name/id to act on -- see each file's own
`attempt_wake`/`_attempt_wake` wrapper.

No external caller's import path changes: `tools.send_to_worker` /
`tools.send_to_cto` / `tools.send_to_cxo` still expose every name they did
before this task, either by defining it locally (unchanged) or re-exporting
it from here.
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from lib import notify
from lib.config import display_for, is_c_level
from tools import tmux_session

ROOT = Path(__file__).resolve().parent.parent
LOCKS_DIR = ROOT / "state" / "locks"


def _active_session_id(role: str, locks_dir: Path | None = None) -> str | None:
    """Return the most-recent C-level session id for `role`, or None.

    Looks first at the `<role>-active` pointer that cxo-claude.sh writes
    on boot. Falls back to the newest matching `.winid` file so we still
    work for sessions started before this helper existed.

    `locks_dir` defaults to this module's own `LOCKS_DIR`. `send_to_cxo.py`
    passes its own `LOCKS_DIR` explicitly instead (its own thin wrapper of
    this function) so tests that isolate `tools.send_to_cxo.LOCKS_DIR`
    (several do -- e.g. `runners/mac_agent.py`'s relay tests) keep working
    unchanged: a bare-name global lookup only sees a monkeypatch on the
    module it's actually looked up in.
    """
    base = locks_dir if locks_dir is not None else LOCKS_DIR
    pointer = base / f"{role}-active"
    if pointer.exists():
        sid = pointer.read_text().strip()
        if sid:
            return sid
    candidates = sorted(
        base.glob(f"{role}-*.winid"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in candidates:
        sid = p.stem.split("-", 1)[1]
        if sid != "active":
            return sid
    return None


def _resolve_sender_role() -> str:
    """Best-effort sender label. CEO when no C-level env is set."""
    r = os.environ.get("CXO_ROLE")
    if r and is_c_level(r):
        return display_for(r)
    if os.environ.get("CTO_SESSION_ID"):
        return display_for("cto")
    return "CEO"


@dataclass(frozen=True)
class Identity:
    """A node in the ownership graph: a C-level session or a DEV task."""

    kind: str  # "cxo" | "dev" | "ceo" | "secretary"
    role: str  # cto/cmo/cgo/cfo for "cxo"; the DEV role key for "dev"
    session_id: str | None  # session id ("cxo") or task_id ("dev"); None for "ceo"

    def label(self) -> str:
        if self.kind == "ceo":
            return "CEO"
        disp = display_for(self.role) if self.kind == "cxo" else self.role
        return f"{disp}#{self.session_id}" if self.session_id else disp


CEO_IDENTITY = Identity("ceo", "CEO", None)


def current_identity() -> Identity:
    """Who is calling send_to_cxo/send_to_worker/send_to_cto right now,
    resolved from process env -- never from anything the caller passes in."""
    r = os.environ.get("CXO_ROLE")
    if r and is_c_level(r):
        sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
        if sid:
            return Identity("cxo", r, sid)
    task_id = os.environ.get("WORKER_TASK_ID")
    if task_id:
        return Identity("dev", os.environ.get("WORKER_ROLE", "dev"), task_id)
    cto_sid = os.environ.get("CTO_SESSION_ID")
    if cto_sid:
        return Identity("cxo", "cto", cto_sid)
    return CEO_IDENTITY


# ---------------------------------------------------------------------------
# Wake nudge -- the org's ONE low-level tmux-send-keys primitive
# (`_wake_tmux_send`) plus the ONE generic wrap/log/never-raise wrapper
# (`attempt_wake`), replacing the 3 near-identical copy-pasted versions that
# used to live one in each of send_to_cxo.py, send_to_worker.py, send_to_cto.py.
# Each direction file keeps its OWN logic for resolving which session name
# to wake -- it just passes the resolved name in here.
# ---------------------------------------------------------------------------

_WAKE_MARKER_TEMPLATE = "[New message from {label}]"


def _wake_tmux_send(session: str, text: str) -> None:
    """Type `text` into tmux `session` and submit it with a settle-delay +
    rescue Enter -- NOT via `tools.tmux_session.send_keys()`.

    GH #70: `send_keys()` sends typed text then `C-m` back-to-back with
    zero settle delay, suspected of hitting the same bracketed-paste
    Enter-swallow `lib.iterm_type` already documents and fixed for iTerm --
    found live when a message typed via that exact function sat unsubmitted
    in a CMO composer, and a later bare `Enter` (tmux keyname, not `C-m`),
    sent as its own separate command after the composer had settled,
    worked. This is that settle-delay+rescue sequence, mirroring
    `lib.iterm_type.type_submit_fragment`'s pattern (type, delay 0.4, key,
    delay 0.3, key again as rescue) rather than the unproven zero-delay path
    GH #70 flagged. `tools.tmux_session.send_keys()` is untouched -- fixing
    it is GH #70's job, out of scope here.
    """
    tmux = tmux_session.tmux_bin()
    subprocess.run(
        [tmux, "send-keys", "-t", session, "-l", text],
        capture_output=True, text=True, check=True, timeout=5,
    )
    time.sleep(0.4)
    subprocess.run(
        [tmux, "send-keys", "-t", session, "Enter"],
        capture_output=True, text=True, check=True, timeout=5,
    )
    time.sleep(0.3)
    subprocess.run(
        [tmux, "send-keys", "-t", session, "Enter"],
        capture_output=True, text=True, check=True, timeout=5,
    )


def attempt_wake(session: str | None, label: str, log_prefix: str, *,
                  send_fn=_wake_tmux_send) -> None:
    """Best-effort attention nudge for a just-delivered letter's recipient.
    The one hard rule (task-cf325742): NOTHING from this step may
    propagate or change the caller's notion of success -- no tmux session,
    a tmux error, a timeout, anything. The mailbox write already succeeded
    before this is ever called; this is strictly on top of it.

    `session` is already resolved by the caller -- each send_to_*.py file
    has its own logic for that (task row lookup for DEVs,
    `tools.session_name.lock_basename()` for C-level sessions). Does
    nothing (silently) if `session` is falsy or not live -- the letter is
    already queued; there's just no live process to poke right now.

    `log_prefix` names the caller in `state/logs/*.log` lines (e.g.
    "send_to_cxo") so a human watching the log can still tell which
    direction a wake came from.

    `send_fn` defaults to this module's own `_wake_tmux_send`, but every
    current caller passes its OWN imported reference explicitly
    (`send_fn=_wake_tmux_send`, resolved in the CALLER's own module
    globals) -- Python resolves a bare name via the *defining* module's
    globals, never the caller's, so without this indirection a test that
    monkeypatches e.g. `tools.send_to_worker._wake_tmux_send` would silently
    have no effect on what actually runs.
    """
    if not session:
        return
    try:
        if not tmux_session.has_session(session):
            try:
                notify.info(f"[{log_prefix}] wake skipped (no live session): {session}")
            except Exception:
                pass
            return
        try:
            notify.info(f"[{log_prefix}] wake attempted: {session}")
        except Exception:
            pass
        marker = _WAKE_MARKER_TEMPLATE.format(label=label)
        send_fn(session, marker)
        try:
            notify.info(f"[{log_prefix}] wake succeeded: {session}")
        except Exception:
            pass
    except Exception as e:
        try:
            notify.info(f"[{log_prefix}] wake failed: {session}: {e}")
        except Exception:
            pass
