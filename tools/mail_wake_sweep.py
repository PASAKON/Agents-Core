"""Fire the wakes envelope mail deferred (org restructure P1).

With `ORG_MAIL_ENVELOPE=1`, a normal-priority letter to a C-level does not wake
its pane at once: `lib.mailbox.wake_due()` holds the wake until 3 letters wait
or the oldest has waited `ORG_WAKE_DEBOUNCE_S` (600 s). Something has to fire
that late wake when no further letter arrives; this is it. One pass over this
host's C-level boxes, run every 60 s by a timer
(`scripts/install-mail-wake-sweep.sh`).

Each pass touches the sweeper heartbeat (`state/inbox/.wake-sweep`). A sender
debounces only while that heartbeat is fresh (`lib.mailbox.sweeper_alive`), so
on a host with no sweeper, or one whose timer stopped, every letter wakes at
once exactly as before: nothing waits on a sweep that will never come.

Each pass also prunes every box's read letters past 7 days (`mailbox.prune`).
A drain prunes only the box it drains, so without this a dead session's or a
finished worker's `read/` would keep its letters for good.

Flag off in this process's env: does nothing, not even the heartbeat. Worker
boxes get no wake: a worker's wake is never debounced. Unread letters are never
touched: it does not drain, move or delete one; it writes only the heartbeat,
each woken box's `.last_wake`, and the prune.

Usage:
    python -m tools.mail_wake_sweep            # one pass, one JSON line per wake
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import mailbox  # noqa: E402
from lib.roles import c_level_roles  # noqa: E402


def _newest_sender(box: Path) -> str:
    """Upper-case role of the newest unread letter's sender, for the wake
    marker. Read no-follow (`mailbox._read_regular`: this runs as root over
    the COO's writable box) and cut to a plain token, because the label is
    typed into the session's pane."""
    for p in sorted(box.glob("*.json"), reverse=True):
        try:
            frm = json.loads(mailbox._read_regular(p) or "").get("from") or {}
        except Exception:
            continue
        label = re.sub(r"[^A-Z0-9_-]", "", str(frm.get("role") or "").upper())[:24]
        return label or "MAIL"
    return "MAIL"


def sweep(*, root: Path | None = None, now: float | None = None) -> list[dict]:
    """One pass. Returns one {"box", "woke"} per box it woke."""
    if not mailbox.envelope_on():
        return []
    base = root if root is not None else mailbox.INBOX_ROOT
    t = now if now is not None else time.time()
    mailbox.note_sweep(root=base)
    roles = set(c_level_roles())
    out = []
    try:
        boxes = sorted(p for p in base.iterdir() if p.is_dir() and not p.is_symlink())
    except OSError:
        return out
    from tools import send_to_cxo   # lazy: a flag-off run never imports it
    for box in boxes:
        mailbox.prune(box, now=t)
        role, _, sid = box.name.partition("-")
        if role not in roles or not sid:
            continue
        try:
            if not mailbox.wake_due(role, sid, "normal", root=base, now=t, sweeping=True):
                continue
            woke = send_to_cxo._attempt_wake(role, sid, _newest_sender(box))
        except Exception as e:  # one bad box never stops the pass
            out.append({"box": box.name, "woke": False, "error": f"{type(e).__name__}: {e}"})
            continue
        mailbox.note_wake(role, sid, root=base, now=t)
        out.append({"box": box.name, "woke": bool(woke)})
    return out


def main() -> int:
    for row in sweep():
        print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
