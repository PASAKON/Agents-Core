"""Owner relay (W2 of the wake chain, design C2, CTO Main 30 Oct 2026).

A zero-model pass that turns task events into letters for the task's owner, so a PH
(or the C-level that owns a task directly) hears within one escalation-watch tick
(5 min) that a task failed, stalled, was blocked, conflicted, was cancelled by gc,
waits for review, has a dead worker, or waits in the budget or disk queue. Before it,
update_status only logged an event and nobody told the owner.

It runs inside tools/escalation_watch.py main() (escalation-watch.timer, every 5 min,
root, hub env): no new unit, no new timer, no model call. Token rules (CEO 30 Oct):
  * one letter per box per tick, up to MAX_LINES tasks, at most LETTER_MAX chars;
  * a fyi letter (a task entered a queue) never wakes; blocker and ask letters do;
  * a wake only into a live local session whose record is idle and whose screen is
    prompt_ready; never a parked PH, never the COO box;
  * at most DAY_WAKES system wakes per box per Thai day, then one per BATCH_S times
    the usage-budget factor (lib/wake_backoff.wake_interval; None = no more wakes);
  * a PH comes first: its C-level hears only when the PH is dead (lock, no session),
    or after the re-wake ladder (escalation_watch.rewake) held three times. Those
    ladder lines ride in the owner box's one letter of the tick (run(extra=...)).

Mode file state/owner_relay.mode: "dry" (the default when it is missing: print what
would be sent, write state, send nothing), "live" (send), "off" (nothing at all).
The re-wake ladder obeys the same mode. A dry state is never reused live: the first
live run starts again from the BOOTSTRAP_S window, so what dry mode only printed is
still delivered. A task whose status has moved on since its event gets no letter.
Change the mode only with --set-mode: it writes a fresh file and renames it into
place, so a link someone planted at that name is replaced, never followed. Never
write a file under state/ with a shell redirect (state/ is group-writable).

State file state/owner_relay.json (atomic write, never through a link). Letters
carry task ids, statuses, a short cleaned reason and the next step; the output
names boxes, task ids and kinds only, never a letter body.

    python tools/owner_relay.py --stats              # wakes per box per Thai day
    python tools/owner_relay.py --set-mode live      # or dry / off (run as root)
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import mailbox, wake_backoff  # noqa: E402
from lib.pane_screen import not_ready_reason  # noqa: E402
from tools import live_sessions as ls  # noqa: E402

STATE_PATH = ROOT / "state" / "owner_relay.json"
MODE_PATH = ROOT / "state" / "owner_relay.mode"
LOCKS_DIR = ROOT / "state" / "locks"
QUEUES = (("budget", ROOT / "state" / "budget_queue.jsonl"), ("disk", ROOT / "state" / "disk_queue.jsonl"))
MODES = ("dry", "live", "off")
DEFAULT_MODE = "dry"
HOST = "contabo"            # dead-worker probes are local: only this host's runs
BOOTSTRAP_S = 8 * 3600      # the first run looks back this far, no further
MAX_LETTERS = 10            # letters per run (the unit has 120 s; each wake costs seconds)
MAX_WAKES = 10              # wake attempts per run, owner letters and re-wake ladder together
MAX_LINES = 8               # tasks per letter
LETTER_MAX = 600            # chars per letter, all lines included
REASON_MAX = 160
DAY_WAKES = 12              # system wakes per box per Thai day, then hourly batches
BATCH_S = 3600
QUEUE_LATE_S = 12 * 3600
FETCH_MAX = 2000            # events per run; the cursor resumes from the last one read
STATE_READ_MAX = 1024 * 1024
MODE_READ_MAX = 64
QUEUE_READ_MAX = 1024 * 1024
HEAD_BYTES = mailbox.HEAD_BYTES
MAX_SEEN, MAX_QUEUE_SEEN, MAX_PENDING_BOXES, MAX_PENDING_LINES, WAKE_DAYS = 2000, 1000, 100, 50, 8
TH = timezone(timedelta(hours=7))
FROM = ("watch", "owner-relay")     # letters-meta: from watch-owner-relay
WAKE_LABEL = "OWNER-RELAY"

STATUS = {"status_failed": "failed", "status_stalled": "stalled", "status_blocked_human": "blocked_human",
          "status_blocked_host": "blocked_host", "status_conflict": "conflict",
          "status_cancelled": "cancelled", "status_review": "review"}
GC_ACTORS = ("gc_stale_tasks", "system", "watchdog")   # a cancel by anyone else was meant
NEXT = {
    "failed": "reopen or re-delegate it",
    "stalled": "check the worker, then reopen or re-delegate",
    "blocked_human": "clear it, or ask_ceo on /run yourself",
    "blocked_host": "pick another host or wait for one",
    "conflict": "rebase it, then review",
    "cancelled": "re-delegate it if still needed",
    "review": "review_diff, then merge",
    "dead": "worker pid and tmux gone: reopen or re-delegate",
    "suspect": "worker silent: read its log",
    "blocked": "answer the worker's blocker",
    "queued": "waits for a runner; no action yet",
    "queue_late": "ask the CEO on /run: switch runner or wait",
    # the re-wake ladder's owner lines (escalation_watch.rewake_scan); the task is the PH box
    "rewake": "look at its pane, clear what holds it, or take its work",
    "ph_dead": "resume it (scripts/spawn-ph.sh --resume {sid}) or take its work",
}
BLOCKER_KINDS = {"failed", "stalled", "blocked_human", "blocked_host", "conflict", "cancelled", "dead",
                 "suspect", "blocked", "rewake", "ph_dead"}
# A hold that is not a failed try: the session is mid-turn (record or screen), or a cap
# holds the wake (escalation_watch.rewake spends no ladder try on these).
NO_TRY = ("busy", "day cap", "woken this tick")
FYI_KINDS = {"queued"}          # never wakes (token rule 2)
_SID_RE = re.compile(r"[0-9a-f]{8}")
_CSID_RE = re.compile(r"[0-9a-f]{8}|fresh")
_ROLE_RE = re.compile(r"c[a-z]o")
_BOX_RE = re.compile(r"c[a-z]o-(?:[0-9a-f]{8}|fresh)|project_head-[0-9a-f]{8}")
_TASK_RE = re.compile(r"task-[0-9a-f]{8}")
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f  ​-‏‪-‮⁦-⁩]+")


class StateUnusable(Exception):
    """The state cannot be saved: a letter would repeat every run, so none is sent."""


# --- small safe reads ----------------------------------------------------------------

def _read_small(path: Path, limit: int) -> bytes | None:
    """A regular file of at most `limit` bytes, never through a link, owned by root or
    this user, not group/other writable, one link (escalation_watch._read_capped's
    rules: state/ is group-writable by the secretary account). Over the cap: None."""
    fd = ls._safe_open(path, os.O_RDONLY, create=False)
    if fd is None:
        return None
    try:
        st = os.fstat(fd)
        if (st.st_size > limit or st.st_uid not in (0, os.geteuid()) or st.st_mode & 0o022
                or st.st_nlink != 1):
            return None
        data = os.read(fd, limit + 1)
        return None if len(data) > limit else data
    except OSError:
        return None
    finally:
        os.close(fd)


def read_mode(path: Path | None = None) -> str:
    """dry (missing or unreadable file, or an unknown word), live or off."""
    raw = _read_small(path or MODE_PATH, MODE_READ_MAX)
    word = (raw or b"").decode("ascii", "replace").strip().lower()
    return word if word in MODES else DEFAULT_MODE


def _is_file(path: Path) -> bool:
    return _ours(path)


def thai_day(now: float) -> str:
    return datetime.fromtimestamp(now, TH).strftime("%Y-%m-%d")


def _epoch(ts) -> float | None:
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp()


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")


def clean(text, limit: int = REASON_MAX, *, tail: bool = False) -> str:
    """One line of plain text: control and direction characters gone, spaces folded."""
    s = " ".join(_CTRL_RE.sub(" ", str(text or "")).split())
    if len(s) <= limit:
        return s
    return "…" + s[-(limit - 1):] if tail else s[:limit - 1] + "…"


# --- boxes, locks and owners ---------------------------------------------------------

def has_lock(box: str) -> bool:
    return bool(_BOX_RE.fullmatch(box)) and _is_file(LOCKS_DIR / f"{box}.lock")


def parked(box: str) -> bool:
    """A PH saved on purpose: no .lock, and its lock files carry a .parked suffix."""
    if not _BOX_RE.fullmatch(box) or has_lock(box):
        return False
    try:
        return any(p.name.endswith(".parked") and p.name.startswith(box + ".") and _ours(p)
                   for p in LOCKS_DIR.iterdir())
    except OSError:
        return False


def active_box(role: str) -> str | None:
    """`<role>-<sid>` from the state/locks/<role>-active pointer (cxo-claude.sh writes it)."""
    if not _ROLE_RE.fullmatch(role):
        return None
    sid = ls.read_lock(LOCKS_DIR / f"{role}-active")
    return f"{role}-{sid}" if _ROLE_RE.fullmatch(role) and _CSID_RE.fullmatch(sid) else None


def live_c_box(box: str | None) -> str | None:
    """A C-level box that a live session drains: `box` when it has a lock, else the
    role's <role>-active box when that one has (design C4: .spawned_by and the task row
    can name a session that ended). Neither live: `box` itself, where the letter waits."""
    if not box or not _BOX_RE.fullmatch(box) or box.startswith("project_head-"):
        return None
    if has_lock(box):
        return box
    act = active_box(box.split("-", 1)[0])
    return act if act and has_lock(act) else box


def ph_owner(sid: str) -> str | None:
    """A PH's live owner C-level box: its .spawned_by ("cxo:<role>:<sid>"), else CTO Main."""
    if not _SID_RE.fullmatch(sid):
        return None
    parts = ls.read_lock(LOCKS_DIR / f"project_head-{sid}.spawned_by").split(":")
    box = None
    if len(parts) == 3 and _ROLE_RE.fullmatch(parts[1]) and _CSID_RE.fullmatch(parts[2]):
        box = f"{parts[1]}-{parts[2]}"
    return live_c_box(box) if box else live_c_box(active_box("cto"))


def route(owner_role, owner_cto, live: set[str]) -> tuple[str | None, str]:
    """(box, why) for a task's letter. A live PH gets its own; a PH with a lock but no
    session (dead), or none at all (closed, remote), goes to its owner C-level; a parked
    PH and the COO get nothing (None)."""
    role, sid = str(owner_role or "cto"), str(owner_cto or "")
    if role == "project_head":
        if not _SID_RE.fullmatch(sid):
            return None, "bad owner"
        ph = f"project_head-{sid}"
        if parked(ph):
            return None, "parked"
        if ph in live:
            return ph, ""
        to = ph_owner(sid)
        why = "dead" if has_lock(ph) else "gone"
        return (to, f"PH {ph} {why}") if to and not to.startswith("coo-") else (None, f"PH {why}, no owner")
    if not (_ROLE_RE.fullmatch(role) and _CSID_RE.fullmatch(sid)):
        return None, "bad owner"
    if role == "coo":
        return None, "coo"
    to = live_c_box(f"{role}-{sid}")
    return (to, "") if to and not to.startswith("coo-") else (None, "coo")


# --- state ---------------------------------------------------------------------------

def _fresh(mode: str, keep: dict | None = None) -> dict:
    keep = keep or {}
    live_cursor = keep.get("live_cursor")
    return {"mode": mode, "cursor": live_cursor if mode == "live" else None, "live_cursor": live_cursor,
            "seen": {}, "queue_seen": {}, "pending": {},
            "wakes": keep.get("wakes", {}), "last_wake": keep.get("last_wake", {}),
            "rewake": {}, "dead_eps": {}}


def load_state(mode: str, path: Path | None = None) -> dict:
    """The saved state for `mode`. A dry state is not reused live (it only printed): the
    first live run starts from the last live cursor, or the BOOTSTRAP_S window when it
    never ran live. The wake counters carry over. Existing unusable state raises
    StateUnusable."""
    path = path or STATE_PATH
    existed = os.path.lexists(path)
    raw = _read_small(path, STATE_READ_MAX)
    if raw is None:
        if existed or os.path.lexists(path):
            raise StateUnusable(f"{path.name} cannot be read")
        return _fresh(mode)
    try:
        d = json.loads(raw)
    except (ValueError, RecursionError) as e:
        raise StateUnusable(f"{path.name} cannot be parsed") from e
    if not isinstance(d, dict):
        raise StateUnusable(f"{path.name} must contain an object")
    st = _fresh(mode)
    for k, typ in (("wakes", dict), ("last_wake", dict), ("seen", dict), ("queue_seen", dict),
                   ("pending", dict), ("rewake", dict), ("dead_eps", dict)):
        if isinstance(d.get(k), typ):
            st[k] = d[k]
    ok = lambda c: isinstance(c, int) and not isinstance(c, bool) and c >= 0
    st["cursor"] = d["cursor"] if ok(d.get("cursor")) else None
    st["live_cursor"] = d["live_cursor"] if ok(d.get("live_cursor")) else None
    if d.get("mode") != mode:
        st = _fresh(mode, st)
    return st


def _trim(d: dict, n: int) -> dict:
    return dict(list(d.items())[-n:]) if n > 0 else {}


def _write_atomic(path: Path, text: str, perm: int) -> None:
    """A fresh random temp name (O_EXCL, so no planted link is followed) renamed over
    `path`: a link at `path` is replaced, never written through. Raises OSError."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".owner_relay.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            os.fchmod(fh.fileno(), perm)
            fh.write(text)
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def save_state(state: dict, path: Path | None = None) -> None:
    """Atomic (_write_atomic). Raises StateUnusable when it cannot be written."""
    path = path or STATE_PATH
    st = dict(state)
    st["seen"] = _trim(st.get("seen", {}), MAX_SEEN)
    st["queue_seen"] = _trim(st.get("queue_seen", {}), MAX_QUEUE_SEEN)
    st["pending"] = {b: v[-MAX_PENDING_LINES:] for b, v in _trim(st.get("pending", {}), MAX_PENDING_BOXES).items()}
    st["wakes"] = {b: dict(sorted(v.items())[-WAKE_DAYS:]) for b, v in st.get("wakes", {}).items()}
    blob = json.dumps(st, ensure_ascii=True)
    while len(blob) > STATE_READ_MAX:
        populated = [k for k, v in st.items() if isinstance(v, dict) and v]
        if not populated:
            raise StateUnusable(f"{path.name} exceeds state size limit")
        for k in populated:
            st[k] = _trim(st[k], len(st[k]) // 2)
        blob = json.dumps(st, ensure_ascii=True)
    try:
        _write_atomic(path, blob, 0o600)
    except OSError as e:
        raise StateUnusable(f"{path.name} cannot be saved ({type(e).__name__})") from e


def _ours(path: Path) -> bool:
    """A regular file root (or this user) owns, nobody else can write, one link."""
    try:
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            st = os.stat(path.name, dir_fd=dfd, follow_symlinks=False)
        finally:
            os.close(dfd)
    except OSError:
        return False
    return (stat.S_ISREG(st.st_mode) and st.st_uid in (0, os.geteuid()) and not st.st_mode & 0o022
            and st.st_nlink == 1)


def set_mode(mode: str, *, path: Path | None = None, state_path: Path | None = None) -> None:
    """The one way to change the mode (--set-mode): the state file first, when it is
    missing or not ours (so its name is root's regular file before another account can
    plant a directory there), then the mode file; both by _write_atomic, never through a
    link. Raises StateUnusable when either cannot be written, ValueError on a bad mode."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    path, state_path = path or MODE_PATH, state_path or STATE_PATH
    if not _ours(state_path):
        save_state(load_state(mode, state_path), state_path)
    try:
        _write_atomic(path, mode + "\n", 0o644)
    except OSError as e:
        raise StateUnusable(f"{path.name} cannot be written ({type(e).__name__})") from e


# --- wakes: one rule for owner letters and the re-wake ladder ------------------------

def screen_ready(box: str, sessions: dict, panes) -> tuple[bool, str]:
    """A wake goes only into a live local session that is idle with an empty prompt.
    `panes` must capture with escapes (escalation_watch.capture_e): only the dim
    attribute tells Claude Code's ghost suggestion from a draft (lib/pane_screen).
    A running turn, by the record or on screen, is "busy…" (no ladder try spent)."""
    s = sessions.get(box)
    if not s:
        return False, "no live session"
    if s.get("status") != "idle":
        return False, "busy"
    screen = panes(s["tmux"]) if s.get("tmux") else None
    if screen is None:
        return False, "screen unreadable"
    why = not_ready_reason(screen)
    if why == "turn running":
        return False, "busy: turn running on screen"
    if why:
        return False, f"screen not ready: {why}"
    return True, ""


def may_wake(state: dict, box: str, now: float, *, tier: str, budget) -> tuple[bool, str]:
    """DAY_WAKES per box per Thai day; past that one per BATCH_S x the budget factor."""
    n = state["wakes"].get(box, {}).get(thai_day(now), 0)
    if n < DAY_WAKES:
        return True, ""
    iv = wake_backoff.wake_interval(BATCH_S, tier=tier, budget_json=budget, now=now)
    if iv is None:
        return False, f"day cap {DAY_WAKES}, tier {tier}: no batch"
    left = iv - (now - state["last_wake"].get(box, 0))
    return (True, "hourly batch") if left <= 0 else (False, f"day cap {DAY_WAKES}: batch in {int(left // 60) + 1} min")


def note_wake(state: dict, box: str, now: float) -> None:
    day = thai_day(now)
    w = state["wakes"].setdefault(box, {})
    w[day] = w.get(day, 0) + 1
    state["last_wake"][box] = now


def try_wake(box: str, state: dict, now: float, *, sessions: dict, panes, wake, budget, tier: str,
             woke: set) -> tuple[bool, str]:
    """(woke, why not). Never the COO, one attempt per box per tick and MAX_WAKES per
    tick in all (`woke` is shared by the owner letters and the re-wake ladder: each wake
    costs seconds of the unit's 120 s), never a busy screen."""
    if box.startswith("coo-"):
        return False, "coo box"
    if box in woke or f"tried:{box}" in woke:
        return False, "woken this tick"
    ok, why = screen_ready(box, sessions, panes)
    if not ok:
        return False, why
    ok, why = may_wake(state, box, now, tier=tier, budget=budget)
    if not ok:
        return False, why
    if sum(1 for x in woke if x.startswith("tried:")) >= MAX_WAKES:
        return False, "woken this tick: run cap"
    woke.add(f"tried:{box}")
    try:
        res = wake(box, WAKE_LABEL)
    except Exception as e:             # best effort, like mail_wake itself
        return False, f"wake error {type(e).__name__}"
    if isinstance(res, dict) and res.get("woke"):
        note_wake(state, box, now)
        woke.add(box)
        return True, ""
    return False, clean((res or {}).get("reason") if isinstance(res, dict) else "no result", 60)


def unread(box: str) -> list[tuple[float, str | None]]:
    """(mtime, kind) of each unread *.json letter in state/inbox/<box>/, read no-follow
    relative to the box (root reads boxes other accounts can write)."""
    if not _BOX_RE.fullmatch(box):
        return []
    dfd = mailbox._open_dir(mailbox.INBOX_ROOT / box) if mailbox._DIRFD_OK else None
    if dfd is None:
        return []
    out = []
    try:
        for name in sorted(n for n in os.listdir(dfd) if n.endswith(".json")):
            try:
                st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
                if not stat.S_ISREG(st.st_mode):
                    continue
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
                try:
                    head = os.read(fd, HEAD_BYTES).decode("utf-8", "replace")
                finally:
                    os.close(fd)
            except OSError:
                continue
            out.append((st.st_mtime, mailbox._head_kind(head)))
    except OSError:
        return out
    finally:
        os.close(dfd)
    return out


# --- the hub (production); tests pass a fake with the same three methods ------------

class Hub:
    COLS = ("id, status, owner_cto, owner_role, host, delegate_log, last_checkpoint, review, pid, "
            "tmux_session, runner, worktree, spawned_at, created_at, updated_at, role, title")

    @staticmethod
    def _rows(cur) -> list[dict]:
        out = []
        for r in cur.fetchall():
            out.append({k: r[k] for k in r.keys()} if hasattr(r, "keys") else dict(r))
        return out

    def events(self, cursor: int | None, since_iso: str) -> list[dict]:
        from lib import db
        where, args = ("id > ?", [cursor]) if cursor is not None else ("ts >= ?", [since_iso])
        with db.get_conn(readonly=True) as conn:
            return self._rows(conn.execute(
                f"SELECT id, task_id, actor, kind, payload, ts FROM events WHERE {where} "
                "AND (kind LIKE 'status_%' OR kind = 'fields_set') ORDER BY id LIMIT ?", args + [FETCH_MAX]))

    def tasks(self, ids) -> dict[str, dict]:
        from lib import db
        ids = sorted({i for i in ids if isinstance(i, str) and _TASK_RE.fullmatch(i)})
        if not ids:
            return {}
        with db.get_conn(readonly=True) as conn:
            rows = self._rows(conn.execute(
                f"SELECT {self.COLS} FROM tasks WHERE id IN ({','.join('?' * len(ids))})", ids))
        return {r["id"]: r for r in rows}

    def running(self, host: str) -> list[dict]:
        from lib import db
        with db.get_conn(readonly=True) as conn:
            rows = self._rows(conn.execute(
                f"SELECT {self.COLS} FROM tasks WHERE status = 'in_progress' AND host = ?", [host]))
        return [r for r in rows if _TASK_RE.fullmatch(str(r.get("id") or ""))]


def inspect_state(task: dict) -> str | None:
    from lib import run_liveness
    r = run_liveness.inspect_run(task)
    return r.get("state") if isinstance(r, dict) else None


def read_queue(path: Path) -> list[dict]:
    raw = _read_small(path, QUEUE_READ_MAX)
    out = []
    for l in (raw or b"").decode("utf-8", "replace").splitlines():
        try:
            d = json.loads(l)
        except (ValueError, RecursionError):
            continue
        if isinstance(d, dict) and isinstance(d.get("task_id"), str) and _TASK_RE.fullmatch(d["task_id"]):
            out.append(d)
    return out


# --- collecting lines ----------------------------------------------------------------

def _payload(ev) -> dict:
    p = ev.get("payload")
    if isinstance(p, str):
        try:
            p = json.loads(p)
        except (ValueError, RecursionError):
            p = None
    return p if isinstance(p, dict) else {}


def _self_actor(actor: str, role: str, sid: str) -> bool:
    if role == "project_head":
        return bool(sid) and sid in actor and actor.startswith("project_head")
    return actor == role or actor == f"{role}-{sid}"


def _reason(row: dict, ev: dict | None, kind: str) -> str:
    p = _payload(ev) if ev else {}
    bits = []
    if p.get("error_code"):
        bits.append(clean(p["error_code"], 40))
    if kind == "suspect":
        try:
            bits.append(f"silent {int(json.loads(row.get('review') or '{}').get('silent_seconds', 0)) // 60} min")
        except (ValueError, TypeError, AttributeError, RecursionError):
            pass
    elif kind == "blocked":
        bits.append(clean(row.get("last_checkpoint"), REASON_MAX))
    elif row.get("delegate_log"):
        bits.append(clean(row["delegate_log"], REASON_MAX, tail=True))
    return clean("; ".join(b for b in bits if b), REASON_MAX)


def _reviewed_by_worker(meta, task_id: str, box: str, t: float) -> bool:
    """The worker's own letter (from *<task_id>) reached the owner box after the event."""
    return any(str(m.get("from", "")).endswith(task_id) and m.get("to") == box and m.get("t", 0) >= t
               for m in meta)


def collect(now: float, state: dict, *, hub, live: set[str], meta, inspect, queues, notes: list,
            host: str = HOST) -> list[dict]:
    """New lines from the hub and the queue files; the cursor and `seen` move here."""
    lines = []
    since = _iso(now - BOOTSTRAP_S)
    try:
        events = hub.events(state["cursor"], since)
        runs = [r for r in hub.running(host) if _TASK_RE.fullmatch(str(r.get("id") or ""))]
    except Exception as e:
        notes.append(f"hub unreadable ({type(e).__name__}): no new task letters, cursor kept")
        return lines
    qents = [(q, e) for q, entries in queues for e in entries
             if _TASK_RE.fullmatch(str(e.get("task_id") or ""))]
    try:
        rows = hub.tasks([e.get("task_id") for e in events] + [e["task_id"] for _, e in qents])
    except Exception as e:
        notes.append(f"hub unreadable ({type(e).__name__}): no new task letters, cursor kept")
        return lines
    rows = {tid: r for tid, r in rows.items() if _TASK_RE.fullmatch(str(tid or ""))
            and _TASK_RE.fullmatch(str(r.get("id") or ""))}
    for r in runs:
        rows.setdefault(r.get("id"), r)
    if events:
        state["cursor"] = max(int(e["id"]) for e in events)
    seen = state["seen"]

    def add(row, kind, ev=None, t=None):
        lines.append({"task": row["id"], "kind": kind, "role": row.get("owner_role") or "cto",
                      "sid": str(row.get("owner_cto") or ""), "reason": _reason(row, ev, kind),
                      "actor": clean((ev or {}).get("actor"), 24), "t": t or now})

    latest: dict[tuple[str, str], dict] = {}
    for ev in events:
        tid, kind = ev.get("task_id"), ev.get("kind")
        row = rows.get(tid)
        if not row or not row.get("owner_cto"):
            continue
        role, sid, actor = row.get("owner_role") or "cto", str(row["owner_cto"]), str(ev.get("actor") or "")
        if _self_actor(actor, role, sid):
            continue
        if kind in STATUS:
            k = STATUS[kind]
            if row.get("status") != k or (k == "cancelled" and actor not in GC_ACTORS):
                continue        # moved on since, or a deliberate cancel
            latest[(tid, k)] = ev
        elif kind == "fields_set":
            p = _payload(ev)
            if "review" in p and "suspect" not in seen.get(tid, []):
                try:
                    if json.loads(p["review"] or "{}").get("watchdog") == "suspect" and row.get("status") == "in_progress":
                        latest[(tid, "suspect")] = ev
                except (ValueError, TypeError, AttributeError, RecursionError):
                    pass
            cp = p.get("last_checkpoint")
            if isinstance(cp, str) and cp.lstrip().upper().startswith("BLOCKED") and "blocked" not in seen.get(tid, []):
                latest[(tid, "blocked")] = ev
    for (tid, k), ev in latest.items():
        row, t = rows[tid], _epoch(ev.get("ts")) or now
        box, _ = route(row.get("owner_role"), row.get("owner_cto"), live)
        if k == "review" and box and _reviewed_by_worker(meta, tid, box, t):
            continue            # the fixed C1 hook already told the owner
        if k in ("suspect", "blocked"):
            seen.setdefault(tid, []).append(k)
        add(row, k, ev, t)
    for row in runs:
        tid = row.get("id")
        if not isinstance(tid, str) or not row.get("owner_cto"):
            continue
        key = f"dead:{row.get('spawned_at') or ''}"
        if key in seen.get(tid, []):
            continue
        try:
            st = inspect(row)
        except Exception:
            st = None
        if st == "dead":
            seen.setdefault(tid, []).append(key)
            add(row, "dead")
    qs = state["queue_seen"]
    for qname, e in qents:
        tid, qat = e["task_id"], str(e.get("queued_at") or "")
        row = rows.get(tid) or {"id": tid, "owner_cto": e.get("owner_cto"),
                                "owner_role": "project_head" if _is_ph_sid(e.get("owner_cto")) else "cto"}
        row = dict(row, delegate_log=f"{qname} queue: {','.join(map(str, e.get('buckets') or []))}"[:REASON_MAX])
        if not row.get("owner_cto"):
            continue
        key, t = f"{qname}:{tid}", _epoch(qat) or now
        rec = qs.get(key)
        if rec is None:
            qs[key] = {"first": qat, "last": qat, "late": False}
            add(row, "queued", t=t)
            continue
        requeued = qat != rec.get("last") and thai_day(t) != thai_day(_epoch(rec.get("last")) or t)
        rec["last"] = qat
        if not rec.get("late") and (requeued or now - (_epoch(rec.get("first")) or now) >= QUEUE_LATE_S):
            rec["late"] = True
            add(row, "queue_late", t=t)
    live_q = {f"{q}:{e['task_id']}" for q, e in qents}
    for k in [k for k in qs if k not in live_q]:      # left the queue: forget it
        del qs[k]
    return lines


def _is_ph_sid(sid) -> bool:
    s = str(sid or "")
    return bool(_SID_RE.fullmatch(s)) and (has_lock(f"project_head-{s}") or parked(f"project_head-{s}")
                                           or _is_file(LOCKS_DIR / f"project_head-{s}.spawned_by"))


# --- letters -------------------------------------------------------------------------

def _head(lines: list[dict]) -> tuple[str, str]:
    kinds = {l["kind"] for l in lines}
    if kinds & BLOCKER_KINDS:
        return "blocker · urgent · owner relay:", "blocker"
    if kinds <= FYI_KINDS:
        return "fyi · normal · owner relay (no wake):", "fyi"
    return "ask · normal · owner relay, review ready:", "ask"


def _next(l: dict) -> str:
    """The next step for a line; a ladder line names its PH's id (its task is the PH box)."""
    return NEXT[l["kind"]].format(sid=str(l["task"]).rsplit("-", 1)[-1])


def compose(box_lines: list[dict]) -> tuple[str, str, int]:
    """(body, kind, n) for one box: the first n (at most MAX_LINES) tasks that fit in
    LETTER_MAX chars, each with its reason cut to share the room left; the caller keeps
    the rest for the next tick."""
    parts = [(f"\n- {l['task']} {l['kind']}{' (' + l['actor'] + ')' if l.get('actor') else ''}"
              f"{' [' + l['via'] + ']' if l.get('via') else ''}: ", f" -> {_next(l)}", l)
             for l in box_lines[:MAX_LINES]]
    n = len(parts)
    while n > 1 and len(_head([p[2] for p in parts[:n]])[0]) + sum(len(a) + len(b) + 1 for a, b, _ in parts[:n]) > LETTER_MAX:
        n -= 1
    head, kind = _head([p[2] for p in parts[:n]])
    room = LETTER_MAX - len(head) - sum(len(a) + len(b) for a, b, _ in parts[:n])
    per = max(0, min(REASON_MAX, room // max(1, n)))
    body = head + "".join(a + (clean(l["reason"], per) if per >= 8 and l["reason"] else "-") + b
                          for a, b, l in parts[:n])
    return body[:LETTER_MAX], kind, n


def _addressed(l: dict) -> str | None:
    """The box of a line that names its own (`to`: a ladder line for a PH's owner), when it
    is a C-level box that is not the COO's; else None."""
    to = l.get("to")
    return to if isinstance(to, str) and _BOX_RE.fullmatch(to) and not to.startswith(("coo-", "project_head-")) \
        else None


def run(now: float, state: dict, *, mode: str, hub, sessions: dict, panes, meta=(), send=None, wake=None,
        inspect=inspect_state, queues=None, budget=None, tier_of=None, woke: set | None = None,
        save=save_state, host: str = HOST, extra=()) -> list[str]:
    """One tick of C2. Returns output lines (boxes, task ids, kinds: never a body).
    `host`: whose in_progress runs are probed for a dead worker (only local runs can be).
    `extra`: lines that carry their own `to` box (the re-wake ladder's owner lines,
    escalation_watch.rewake_scan): they join that box's one letter of this tick, count
    against MAX_LETTERS and wait in `pending` like any other line (token rule 3)."""
    if mode == "off":
        return ["owner-relay off (state/owner_relay.mode)"]
    send = send or mailbox.send
    tier_of = tier_of or (lambda box: "critical" if not box.startswith("project_head-") else "normal")
    woke = set() if woke is None else woke
    if wake is None:
        from tools import mail_wake
        wake = mail_wake.wake
    queues = [(q, read_queue(p)) for q, p in QUEUES] if queues is None else queues
    notes, out = [], []
    live = set(sessions)
    new = collect(now, state, hub=hub, live=live, meta=list(meta), inspect=inspect, queues=queues, notes=notes,
                  host=host)
    by_box: dict[str, list[dict]] = {}
    for l in [l for ls_ in state["pending"].values() for l in ls_] + new + list(extra):
        if "to" in l:
            box, why = _addressed(l), ""
        else:
            box, why = route(l["role"], l["sid"], live)
        if box is None:
            continue
        l = dict(l, via=why) if why else {k: v for k, v in l.items() if k != "via"}
        cur = by_box.setdefault(box, [])
        if not any(x["task"] == l["task"] and x["kind"] == l["kind"] for x in cur):
            cur.append(l)
    state["pending"] = {}
    letters = []
    for box, bl in sorted(by_box.items(), key=lambda kv: min(l["t"] for l in kv[1])):
        if len(letters) < MAX_LETTERS:
            letters.append((box, bl[:MAX_LINES]))
            rest = bl[MAX_LINES:]
        else:
            rest = bl
        if rest:
            state["pending"][box] = rest[:MAX_PENDING_LINES]
    composed = []
    for box, bl in letters:
        body, kind, n = compose(bl)
        if n < len(bl):         # did not fit in LETTER_MAX: the next tick
            state["pending"][box] = (bl[n:] + state["pending"].get(box, []))[:MAX_PENDING_LINES]
        composed.append((box, bl[:n], body, kind))
    if mode == "live":
        state["live_cursor"] = state["cursor"]
    save(state)             # before any letter: a state that cannot be saved sends nothing
    for box, bl, body, kind in composed:
        ids = ",".join(f"{l['task']}:{l['kind']}" for l in bl)
        if mode != "live":
            out.append(f"would send {box} <- {kind} {len(bl)}: {ids}")
            continue
        role, sid = box.split("-", 1)
        try:
            send(role, sid, body, *FROM)
        except Exception as e:
            state["pending"].setdefault(box, []).extend(bl)
            out.append(f"failed {box} <- {kind} ({type(e).__name__}): kept for the next tick")
            continue
        tail = ""
        if kind != "fyi":
            ok, why = try_wake(box, state, now, sessions=sessions, panes=panes, wake=wake, budget=budget,
                               tier=tier_of(box), woke=woke)
            tail = " +wake" if ok else f" (wake held: {why})"
        out.append(f"sent {box} <- {kind} {len(bl)}: {ids}{tail}")
    save(state)
    return [f"note {n}" for n in notes] + out


def stats(state: dict) -> list[str]:
    rows = [(day, box, n) for box, days in state.get("wakes", {}).items() for day, n in days.items()]
    return [f"{day} {box} {n} wakes" for day, box, n in sorted(rows)] or ["no wakes recorded"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--stats", action="store_true", help="print wakes per box per Thai day")
    ap.add_argument("--set-mode", choices=MODES,
                    help="write state/owner_relay.mode safely (never use a shell redirect under state/)")
    a = ap.parse_args(argv)
    if a.set_mode:
        try:
            set_mode(a.set_mode)
        except StateUnusable as e:
            print(f"mode not set: {e}; a name under state/ that is not a regular file of ours is "
                  "not removed here: look at it by hand", file=sys.stderr)
            return 1
        print(f"mode {a.set_mode} (state/owner_relay.mode); the next escalation-watch tick uses it")
        return 0
    st = load_state(read_mode())
    if a.stats:
        for l in stats(st):
            print(l)
        return 0
    print(f"mode {st['mode']}; cursor {st['cursor']}; pending boxes {len(st['pending'])}; "
          "it runs inside tools/escalation_watch.py --nudge")
    return 0


if __name__ == "__main__":
    sys.exit(main())
