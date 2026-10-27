#!/usr/bin/env python3
"""Portfolio watch (ProjectTrack P3, CEO order 2026-10-27): chase late work with letters.

Zero model, zero spend. It reads the flags the Project Monitor already computes
(lib/portfolio.py monitor_payload(version=2): late, waiting_ceo, no_plan, unlinked_order)
and turns each into an EPISODE, the escalation watch's pattern (tools/escalation_watch.py):
an episode starts the first run its finding is seen and ends the first run it is gone;
its state lives in state/portfolio_watch.json. The ladder, one letter per step per episode:

  late, no_plan      first seen   -> the project's PH (kind blocker): finish, replan or block.
                                     A project with no PH: the owner C-level instead.
                     +4 h         -> the owner C-level (kind blocker): cut scope, move the
                                     date, change the PH or park.
  unlinked_order     30 min old   -> the C-level that took it (orders.taken_by).
  waiting_ceo        never a letter: the CEO already sees that band on the monitor.
  any episode        +24 h        -> `red: true` in the state file, no letter.
  episode gone                    -> removed from the state, no letter.

Never a letter for a parked or closed project, never to the CEO. Dry run by default:

    python tools/portfolio_watch.py            # print findings and the letters it would send
    python tools/portfolio_watch.py --nudge    # send them and save the state

The live-sessions publisher on the hub host runs `--nudge` every 5 minutes
(tools/live_sessions.py PortfolioWatch). ORG_DB_URL is the hub it reads.

Exit: 0 done. 1 a letter or the state file could not be written (no letter goes out when
the state cannot be saved: it would repeat every run). 3 the hub could not be read, or only
its read-only snapshot answered: stale data is never acted on.
One line on stderr per run, starting `portfolio_watch: `.
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

from lib import mailbox  # noqa: E402

PREFIX = "portfolio_watch: "
FROM = ("system", "portfolio-watch")
STATE_PATH = ROOT / "state" / "portfolio_watch.json"
STATE_READ_MAX = 1024 * 1024
MAX_EPISODES = 500
ORDER_AFTER = timedelta(minutes=30)     # an unlinked order this old gets its letter
OWNER_AFTER = timedelta(hours=4)        # a late project still here this long reaches its C-level
RED_AFTER = timedelta(hours=24)         # an episode this old is marked red
LIVE_STAGES = ("active", "review")      # a parked or closed project is never chased
SUBJECT_MAX = 80
CAP = 500                               # items asked of the monitor (its wire cap is 10); hitting this = incomplete
_ROLE_RE = re.compile(r"[a-z][a-z_]{0,31}")
_SID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}")
_WHEN = "%Y-%m-%dT%H:%M:%SZ"

LABEL = {"late": "late", "no_plan": "no plan", "waiting_ceo": "waiting on CEO",
         "unlinked_order": "unlinked order"}
SAY = {"late": "is late", "no_plan": "has no plan"}      # the verb phrase in a letter about a project
CLI = "bash scripts/hub/org-python.sh tools/portfolio.py"


class StateUnusable(Exception):
    """The state file cannot be saved: a letter could not be remembered and would repeat.
    `sent`: the letters that had already gone out when it was found."""
    sent: list = ()


class StaleHub(Exception):
    """Only the hub's read-only snapshot answered."""


class Found(list):
    """The findings. `complete` is False when the monitor's attention list hit its cap, so
    a finding that is not in it may only be hidden: its episode must not be ended."""
    complete = True


# --- time ----------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(_WHEN)


def _at(text, default: datetime) -> datetime:
    try:
        return datetime.strptime(str(text), _WHEN).replace(tzinfo=timezone.utc)
    except ValueError:
        return default


def _ago(delta: timedelta) -> str:
    minutes = max(0, int(delta.total_seconds() // 60))
    if minutes < 120:
        return f"{minutes} min"
    return f"{minutes // 60} h" if minutes < 48 * 60 else f"{minutes // 1440} d"


def _line(text, limit: int) -> str:
    """One printable line: whitespace and control characters collapsed, backticks dropped
    (a name is data, never a command), at most `limit` characters."""
    return " ".join(re.sub(r"[\x00-\x1f\x7f-\x9f`]", " ", str(text or "")).split())[:limit]


# --- findings ------------------------------------------------------------------------

def _box(role, sid) -> str | None:
    """`role-sid` for a letter box, or None: an unknown shape, or the CEO (never written to)."""
    role, sid = str(role or ""), str(sid or "")
    return f"{role}-{sid}" if _ROLE_RE.fullmatch(role) and _SID_RE.fullmatch(sid) and role != "ceo" else None


def _owner_box(lane, owner_session) -> str | None:
    """The owner C-level's box: role is the lane, the lane's own prefix comes off the session."""
    sid = str(owner_session or "").strip()
    return _box(lane, sid[len(lane) + 1:] if sid.startswith(f"{lane}-") else sid)


def _ph_box(ph_session) -> str | None:
    sid = str(ph_session or "").strip()
    return _box("project_head", sid[len("project_head-"):] if sid.startswith("project_head-") else sid)


def _taker_box(taken_by) -> str | None:
    role, _, sid = str(taken_by or "").strip().partition("-")
    return _box(role, sid)


def _rows(conn, sql):
    return [dict(r) for r in conn.execute(sql).fetchall()]


def findings(now: datetime, conn=None) -> Found:
    """One finding per (project, flag) or (order, 'unlinked_order'). The flags come from
    portfolio.monitor_payload(version=2); one read of the projects and open orders adds what
    the payload lacks: the PH and owner boxes, the stage and who took the order. Raises
    StaleHub when only the read-only snapshot answered."""
    if conn is None:
        from lib import db
        with db.get_conn() as c:
            if isinstance(c, db._SnapshotConnection):
                raise StaleHub("hub unreachable, read-only snapshot only")
            return findings(now, c)
    from lib import portfolio
    attention = portfolio.monitor_payload(now, conn=conn, version=2, attention_cap=CAP)["attention"]
    # The payload cuts ids to 40 characters (the wire contract), so match on that.
    projects, clash = {}, set()
    for r in _rows(conn, "SELECT id, name, lane, stage, owner_session, ph_session FROM projects"):
        key = str(r["id"])[:40]
        if key in projects:
            clash.add(key)                                  # two ids share a prefix: addressed to neither
        else:
            projects[key] = r
    orders = {str(r["id"]): r for r in _rows(
        conn, "SELECT id, words, taken_by FROM orders WHERE closed_at IS NULL AND project_id IS NULL")}
    out = Found()
    out.complete = len(attention) < CAP
    for a in attention:
        kind, since = a["kind"], _at(a.get("since"), now)
        if kind == "unlinked_order":
            o = orders.get(str(a["order_id"]))
            if o is None:
                continue                                    # linked or closed since the payload
            out.append({"key": f"{a['order_id']}:{kind}", "kind": kind, "id": a["order_id"],
                        "name": _line(o["words"], 50), "what": "taken, no project yet",
                        "since": since, "ph": None, "owner": _taker_box(o["taken_by"])})
            continue
        p = projects.get(str(a["project_id"]))
        if p is None or p["stage"] not in LIVE_STAGES or str(a["project_id"]) in clash:
            continue
        what = {"late": f"due {_iso(since)[:10]}", "no_plan": "no dated milestone",
                "waiting_ceo": "waiting on CEO"}[kind]
        out.append({"key": f"{a['project_id']}:{kind}", "kind": kind, "id": a["project_id"],
                    "name": _line(p["name"], 40), "what": what, "since": since,
                    "ph": _ph_box(p["ph_session"]), "owner": _owner_box(p["lane"], p["owner_session"])})
    return out


# --- state ---------------------------------------------------------------------------

def load_state(now: datetime) -> dict:
    """{"episodes": {key: {"start": iso, "sent": [step, …], "red": bool}}}. A file that is
    missing, corrupt or not a regular file reads as empty, a bad episode is dropped, and a
    start in the future (the clock stepped back) is clamped to now. Never through a symlink."""
    try:
        fd = os.open(STATE_PATH, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return {"episodes": {}}
    try:
        st = os.fstat(fd)
        raw = os.read(fd, STATE_READ_MAX + 1) if stat.S_ISREG(st.st_mode) and st.st_size <= STATE_READ_MAX else b""
    except OSError:
        raw = b""
    finally:
        os.close(fd)
    try:
        d = json.loads(raw) if raw else {}
    except (ValueError, RecursionError):
        d = {}
    eps = {}
    for k, v in (d.get("episodes") or {} if isinstance(d, dict) else {}).items():
        if isinstance(k, str) and isinstance(v, dict) and isinstance(v.get("sent"), list):
            start = min(_at(v.get("start"), now), now)
            eps[k] = {"start": _iso(start), "sent": [s for s in v["sent"] if s in ("first", "owner")],
                      "red": v.get("red") is True}
    return {"episodes": eps}


def save_state(state: dict) -> None:
    """Atomic: a temp file beside it, then os.replace. Raises StateUnusable."""
    eps = dict(sorted(state["episodes"].items(), key=lambda kv: kv[1]["start"])[-MAX_EPISODES:])
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=STATE_PATH.parent, prefix=".portfolio_watch.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump({"episodes": eps}, fh, indent=1, sort_keys=True)
            os.replace(tmp, STATE_PATH)
        except OSError:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
    except OSError as e:
        raise StateUnusable(f"state file {STATE_PATH} cannot be saved ({type(e).__name__}: "
                            f"{e.strerror or e})") from e


# --- the ladder ----------------------------------------------------------------------

def _letter(f: dict, step: str, box: str, now: datetime) -> dict:
    """The subject (at most 80 characters) and body of one letter. The body opens
    `blocker · urgent ·` so its kind reads the same with the mail envelope on or off."""
    label, ref = LABEL[f["kind"]], f"{f['name']} ({f['id']})"
    say = SAY.get(f["kind"], "is " + label)
    subject = (("still " if step == "owner" else "") + f"{label}: {f['name']} {f['what']}")[:SUBJECT_MAX]
    late = f"since {_iso(f['since'])[:16]}Z, {_ago(now - f['since'])} ago"
    if f["kind"] == "unlinked_order":
        text = (f"order {f['id']} (\"{f['name']}\") was taken {_ago(now - f['since'])} ago and is still "
                f"linked to no project. Link it (`{CLI} order link {f['id']} <project>`) or close it "
                f"(`{CLI} order close {f['id']} --outcome <text>`).")
    elif step == "owner":
        held = (f"its Project Head has had a letter for {_ago(OWNER_AFTER)} with no change" if f["ph"]
                else "it has no Project Head")
        text = (f"project {ref} {say} ({f['what']}; {late}) and {held}. Decide: cut scope, move the "
                f"date (`{CLI} replan {f['id']} <n> --due <ISO> --why <text>`), change the PH, or park it.")
    elif box.startswith("project_head-"):
        todo = ("add milestones (`milestone add`) and give each a date (`replan`), or" if f["kind"] == "no_plan"
                else "finish it, or")
        text = (f"project {ref} {say} ({f['what']}; {late}). Please {todo} move the date with "
                f"`{CLI} replan {f['id']} <n> --due <ISO> --why <text>`, or say what holds it with "
                f"`{CLI} block {f['id']} --on ceo|clevel|external|resource --what <text>`. "
                f"If it is still here in {_ago(OWNER_AFTER)} your C-level hears of it.")
    else:                                               # no PH: the C-level hears first
        text = (f"project {ref} {say} ({f['what']}; {late}) and has no Project Head. Decide: "
                f"assign one, move the date (`{CLI} replan {f['id']} <n> --due <ISO> --why <text>`), or park it.")
    return {"box": box, "subject": subject, "body": f"blocker · urgent · portfolio watch: {text}"}


def plan(found, state: dict, now: datetime) -> list[dict]:
    """Advance the episodes in `state` (start, prune, red) and return the letters now due,
    each with its episode `key` and `step`. Sends nothing; deliver() sends and records."""
    eps, due = state["episodes"], []
    keys = {f["key"] for f in found}
    if getattr(found, "complete", True):
        for k in [k for k in eps if k not in keys]:     # the episode ended
            del eps[k]
    for f in found:
        if len(eps) >= MAX_EPISODES and f["key"] not in eps:
            continue                                    # the cap never drops a running episode
        ep = eps.setdefault(f["key"], {"start": _iso(now), "sent": [], "red": False})
        age = now - _at(ep["start"], now)
        if age >= RED_AFTER:
            ep["red"] = True
        steps = []
        if f["kind"] == "unlinked_order":
            if now - f["since"] >= ORDER_AFTER:
                steps = [("first", f["owner"])]
        elif f["kind"] != "waiting_ceo":
            steps = [("first", f["ph"] or f["owner"])]
            if age >= OWNER_AFTER:
                steps.append(("owner", f["owner"]))
        for step, box in steps:
            if step not in ep["sent"] and box:
                due.append({"key": f["key"], "step": step, **_letter(f, step, box, now)})
    return due


def deliver(letters, state: dict, *, send=mailbox.send) -> tuple[list[dict], list[str]]:
    """Send each letter and record it in `state`, saving after every one: a process killed
    between a send and its save would otherwise repeat it. Returns (sent, errors). A letter
    that fails to send stays unrecorded and goes out on the next run."""
    sent, errors = [], []
    for letter in letters:
        role, sid = letter["box"].split("-", 1)
        try:
            send(role, sid, letter["body"], *FROM, kind="blocker", subject=letter["subject"])
        except Exception as e:
            errors.append(f"{letter['box']} <- {letter['subject']}: {type(e).__name__}")
            continue
        state["episodes"][letter["key"]]["sent"].append(letter["step"])
        sent.append(letter)
        try:
            save_state(state)
        except StateUnusable as e:
            e.sent = sent                               # the letters are out; run() still names them
            raise
    return sent, errors


# --- CLI -----------------------------------------------------------------------------

def run(now: datetime, *, nudge: bool, conn=None, send=mailbox.send, out=print) -> int:
    try:
        found = findings(now, conn)
    except Exception as e:      # a psycopg message can name the host: the class only
        out(f"note     hub unreadable ({type(e).__name__})")
        print(f"{PREFIX}no findings ({type(e).__name__}), nothing sent", file=sys.stderr)
        return 3
    state = load_state(now)
    letters = plan(found, state, now)
    for f in found:
        ep = state["episodes"].get(f["key"], {})
        out(f"{LABEL[f['kind']]:<15} {f['name']} ({f['id']}): {f['what']}" + ("  RED" if ep.get("red") else ""))
    if not found:
        out("ok       nothing late")
    if not found.complete:
        out(f"note     the monitor shows only {CAP} items: more may be hidden, no episode was ended")
    if not nudge:
        for letter in letters:
            out(f"would send  {letter['box']} <- {letter['subject']}")
        print(f"{PREFIX}dry run, {len(found)} findings, {len(letters)} letters due", file=sys.stderr)
        return 0
    try:
        save_state(state)       # before any letter: a state that cannot be saved sends nothing
        sent, errors = deliver(letters, state, send=send)
        save_state(state)       # also on an empty round: ended episodes and red marks
    except StateUnusable as e:
        for letter in e.sent:
            out(f"sent     {letter['box']} <- {letter['subject']}")
        out(f"note     {e}; no letter goes out until it is fixed")
        print(f"{PREFIX}state unusable, nothing sent", file=sys.stderr)
        return 1
    for letter in sent:
        out(f"sent     {letter['box']} <- {letter['subject']}")
    for err in errors:
        out(f"note     not sent: {err}")
    print(f"{PREFIX}{'failed' if errors else 'ok'}, {len(found)} findings, {len(sent)} letters sent"
          + (f", {len(errors)} not sent" if errors else ""), file=sys.stderr)
    return 1 if errors else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--nudge", action="store_true", help="send the letters and save the state (default: print only)")
    a = ap.parse_args(argv)
    return run(datetime.now(timezone.utc), nudge=a.nudge)


if __name__ == "__main__":
    sys.exit(main())
