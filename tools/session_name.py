"""One name for one session.

Two independent things answer "which C-level sessions are running", and they
must agree or a session goes invisible:

  - the lock files in ``state/locks/<role>-<id>.{lock,run,tty,uuid,winid}``
    → read by ``tools/session_cap.live_sessions()`` → drives the spawn cap.
  - ``tmux ls`` → read by MoonieX Console → what the CEO sees on the phone.

Both names are ``<role>-<id>``. Measured 2026-08-10 they disagreed in BOTH
directions for the same failed spawn: a lock ``cto-4020c182`` (uuid hex this
module's callers generate) sat next to a tmux session ``cto-session-mslldjt6``
(the console's slugify fallback for an empty name, ``session-<base36>``). The
lock ate a cap slot the console could not see; the tmux session showed on the
phone but counted for nothing. Nine hours later a ``claude -n`` was still
burning quota, reachable by nobody.

The fix is structural: the lock basename and the tmux session name must be the
SAME string. This module is the single derivation of that rule, so the two
launchers (which name tmux), the GC tool (which classifies the halves), and the
tests cannot drift to three different answers. ``tools/session_cap`` keeps its
own narrower ROLES (it deliberately does not count ``cgo``); the wider set here
covers every role the spawn machinery can produce, so a ``cgo`` orphan is still
detectable by the GC even though it is invisible to the cap.
"""
from __future__ import annotations

import re

# Every role scripts/spawn-cxo.sh + scripts/cxo-claude.sh can launch. Wider
# than session_cap.ROLES on purpose: the cap counts cto/cmo/cfo/cxo only, but
# the GC must still reconcile a cgo session whose halves have drifted.
ROLES = ("cto", "cmo", "cgo", "cfo", "cxo")

ROLE_RE = re.compile(rf"^({'|'.join(ROLES)})-(.+)$")

# The full sibling family a launcher + spawn file drop for one session.
# Mirrored by scripts/session-kill.sh and the --reap path in tools/session_gc
# so a new extension lands everywhere at once instead of becoming a 4th list
# to forget.
LOCK_SUFFIXES = (
    ".lock", ".run", ".tty", ".winid", ".watcher-pid", ".topic",
)

# NOT reapable, and deliberately absent from LOCK_SUFFIXES above.
#
# `.uuid` holds the full Claude session UUID (e.g. 7ad3ec9f-…-c3560e9d1eaa);
# the org's short id is only its last 8 hex. `spawn-cto.sh --resume <id>` reads
# this file to recover the real UUID, because `claude -r` needs an exact match
# and drops into picker mode without one. It is the resume KEY, not runtime
# state — deleting it on close means that session can never be resumed again,
# which is the opposite of what closing should mean. Removed only by hand.
KEEP_SUFFIXES = (".uuid",)


def lock_basename(role: str, session_id: str) -> str:
    """``<role>-<session_id>`` — the lock file stem AND the tmux session name.

    This is the single value both halves derive from; callers that need a
    concrete path build ``f"{locks_dir}/{lock_basename(role, id)}.<ext>"``.
    """
    return f"{role}-{session_id}"


def id_from_tmux_session(tmux_name: str, role: str | None = None) -> str | None:
    """Recover the session id from a tmux session name, or ``None``.

    A console-spawned session may carry a fallback slug — the console's
    slugify produces ``session-<base36>`` for an empty name — rather than a
    uuid hex. Either way the id is everything after the ``<role>-`` prefix,
    so the lock basename reconstructed from it equals the tmux session name
    exactly. That is what makes the two halves one value.

    Returns ``None`` when the name is not ``<role>-<id>`` shaped, or when
    ``role`` is given and the prefix belongs to a different role: a caller
    then falls back to a fresh uuid instead of adopting a name that would
    collide with another role's lock.
    """
    m = ROLE_RE.match(tmux_name)
    if not m:
        return None
    if role is not None and m.group(1) != role:
        return None
    return m.group(2)


def parse_role(tmux_name: str) -> str | None:
    """The role prefix of a session name, or ``None`` if it is not C-level."""
    m = ROLE_RE.match(tmux_name)
    return m.group(1) if m else None
