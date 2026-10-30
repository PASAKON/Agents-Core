"""Escalation watch (M11, CEO order 2026-10-14 ~11:45 TH): flag sessions that stall.

CEO: "ทำไมเวลา PH ติดปัญหาถึงไม่มาถาม C level · และทำไม C level ถึงไม่มาถามที่ run
เป็นกฎหลัก · ตอนนี้งานไม่เดินแล้ว session หยุดและตายไปช้า". The IRON rule (CTO Main)
says what a session must do; this checks that it happened. Four findings:

  waiting   a C-level or PH whose pane shows a prompt waiting on a person (a
            permission prompt or an on-screen question: the app's ✋, which the
            session record still reports as "idle"). Contabo panes only (tmux).
  idle      a C-level or PH idle for IDLE_S (30 min) or more (local records).
  blocker   a PH's blocker letter its C-level has held BLOCKER_S (15 min) with no
            question card from that C-level since, and no letter back to the PH.
  host      a host whose live-sessions publisher went stale.

A finding is an EPISODE: it starts the first run it is seen and ends the first run
it is gone. Each episode gets one letter and at most one reminder (REMIND_S later),
then nothing until it ends (§2b review of #292, B-2):

  waiting   → the COO, and a PH's owner. Never the waiting session itself: it cannot
              read a letter while a prompt holds it, and a wake would press Enter on
              that prompt (B-1). Sent at once, kind blocker.
  blocker   → the C-level holding it and the COO, at once, only while the PH is live.
  idle      → the COO's digest only (kind fyi, one letter per DIGEST_S, no reminder).
  host      → the digest of the COO and every live C-level, once per stale period; a
              host stale longer than HOST_RETIRED_S is a note, not a finding.

A wake follows only a letter sent at once, and only when the recipient's own screen
is prompt_ready (empty input box, no turn running, no prompt waiting): the same test
the rename service uses before it types.

The timed parts (the idle threshold, the one reminder, the digest spacing) run on
lib/wake_backoff.wake_interval(base, tier=<the recipient's tier>): the base times the
usage-budget factor (x2 one provider over, x4 all over, stale or missing data x1) times
the tier factor (a critical or C-level recipient x1, normal x2 while over, low none: no
timed letter at all). A PH's tier is its projects row (ph_session); every C-level is
critical. A new at-once finding is never slowed (IRON-RULES section 64). Letters carry box ids, never a session's
display name or any text a session wrote (M-1). Dry run by default:

    python tools/escalation_watch.py            # print findings, send nothing
    python tools/escalation_watch.py --nudge    # also send the letters

Sources: the hub's live_sessions/live_hosts (tools/live_sessions), this host's
session records, tmux capture-pane, state/reports/letters-meta.jsonl (lib/mailbox
logs every letter's from/to/kind, never the body), and the Run Inbox question list
(tools/ask_run). A source that cannot be read is named in the output, never guessed.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import mailbox, portfolio, wake_backoff  # noqa: E402
from tools import live_sessions as ls  # noqa: E402
from tools.rename_service import pane_waiting, prompt_ready  # noqa: E402  (the rename service's screen tests)

IDLE_S = 30 * 60
BLOCKER_S = 15 * 60
REMIND_S = 60 * 60          # the one reminder of an at-once finding
DIGEST_S = 2 * 60 * 60      # fyi letters: one digest per recipient per 2 h (COO, 14 Oct)
HOST_RETIRED_S = 24 * 3600  # stale longer than this: a retired host, not a finding
LINE_MAX = 300
LOCKS_DIR = ROOT / "state" / "locks"
STATE_PATH = ROOT / "state" / "escalation_watch.json"
FROM = ("watchdog", "escalation")
# CTO Main's box is cto-fresh (state/locks/cto-active = fresh), so a C-level id is 8 hex
# or "fresh"; a PH's is always 8 hex. Always fullmatch.
_BOX_RE = re.compile(r"c[a-z]o-(?:[0-9a-f]{8}|fresh)|project_head-[0-9a-f]{8}")
# The re-wake ladder (W2, design C3): tries at these ages of the oldest unread
# non-quiet letter, each x lib/wake_backoff.wake_interval; then one letter to the
# PH's owner C-level. A bounded retry of a real letter's delivery (IRON-RULES §64).
REWAKE_LADDER = (5 * 60, 15 * 60, 45 * 60)
DEAD_PH_S = 15 * 60          # a dead PH's unread letter waits this long before its owner hears
OPEN_STATUSES = ("pending", "in_progress", "review", "blocked_human", "blocked_host", "stalled",
                 "failed", "conflict")
_HOST_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
# Root reads files under state/, which the secretary service can write (no sticky
# bit): no symlink, no FIFO, a size cap (§2b review of #283 v2, B-1, same class).
META_READ_MAX = 8 * 1024 * 1024
STATE_READ_MAX = 1024 * 1024
# The saved state is bounded (§2b review of #292 round 2, item 4): the newest of each
# are kept, and what is written is always small enough for load_state to read back.
MAX_EPISODES = 500
MAX_DIGESTS = 200
DIGEST_LINES = 50
AT_ONCE_SENDS = 2           # a letter and one reminder; an episode's `sent` never exceeds it


class StateUnusable(Exception):
    """The state file cannot be read or saved, so a letter could not be remembered and
    would repeat on every run: nothing is sent. `sent`: the letters that had already
    gone out when it was found (only a failed final save has any)."""

    def __init__(self, msg: str):
        super().__init__(msg)
        self.sent: list[str] = []


def _read_capped(path: Path, limit: int, *, whole: bool = False) -> bytes | None:
    """At most the last `limit` bytes of a regular file, never through a symlink, and
    only one that root (or this user) owns, nobody else can write and has one link:
    the secretary account can create files in state/ (§2b review of #292, M-2).
    `whole`: the file is parsed as one document, so one over `limit` is not read at all
    (StateUnusable); half a JSON file is never parsed."""
    fd = ls._safe_open(path, os.O_RDONLY, create=False)
    if fd is None:
        return None
    try:
        st = os.fstat(fd)
        if whole and st.st_size > limit:
            raise StateUnusable(f"{path.name} is {st.st_size} bytes, over the {limit} byte cap: not parsed")
        if st.st_uid not in (0, os.geteuid()) or st.st_mode & 0o022 or st.st_nlink != 1:
            return None
        size = st.st_size
        if size > limit and not whole:
            os.lseek(fd, size - limit, os.SEEK_SET)
        chunks, left = [], limit + 1 if whole else limit
        while left > 0:
            b = os.read(fd, min(left, 1 << 20))
            if not b:
                break
            chunks.append(b)
            left -= len(b)
        data = b"".join(chunks)
        if whole and len(data) > limit:                  # it grew while we read it
            raise StateUnusable(f"{path.name} grew past the {limit} byte cap while it was read")
        return data
    except OSError:
        return None
    finally:
        os.close(fd)


def _now() -> float:
    return time.time()


# --- sources -----------------------------------------------------------------------

def capture(tmux_target: str, *, escapes: bool = False) -> str | None:
    try:
        r = subprocess.run(["tmux", "capture-pane", "-p", *(["-e"] if escapes else []), "-t", f"={tmux_target}:"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def capture_e(tmux_target: str) -> str | None:
    """The W2 wake gate's capture (owner letters and the re-wake ladder): with -e, so
    lib/pane_screen reads Claude Code's dim ghost suggestion as an empty input box, as
    the rename service and agent_transport do (design C3 failure_handling). Without the
    escapes an idle session showing a suggestion looks like one holding a draft. find()
    and nudge() keep the plain capture."""
    return capture(tmux_target, escapes=True)


def _root_record(d, p: Path) -> bool:
    """A record W2 may act on: a regular file root (or this user) owns in a dir root
    owns, neither writable by group or other. sompong's registry dir is its own
    (config/hosts.yaml), so a record there can say nothing about a PH or a C-level
    that W2 wakes or routes letters by; SomPong's own (coo) box is never woken by W2."""
    try:
        ds, fs = os.stat(d), os.lstat(p)
    except OSError:
        return False
    ok = lambda st: st.st_uid in (0, os.geteuid()) and not st.st_mode & 0o022
    return ok(ds) and ok(fs) and stat.S_ISREG(fs.st_mode) and fs.st_nlink == 1


def local_sessions(host: str) -> list[dict]:
    """This host's live listed sessions from their records: box, status age, tmux, and
    `trusted` (_root_record: only those reach owner_tick)."""
    out = []
    for d in ls.session_dirs(host):
        try:
            files = [p for p in Path(d).iterdir() if ls._SESSION_FILE_RE.match(p.name)]
        except OSError:
            continue
        for p in files:
            raw = ls._read_session_file(p)
            try:
                data = json.loads(raw) if raw else None
                pid = int(data["pid"])
            except (ValueError, KeyError, TypeError):
                continue
            if not isinstance(data, dict) or not ls.is_alive(pid, ls._proc_start(data.get("procStart"))):
                continue
            uuid = str(data.get("sessionId") or "")
            role, sid, verified = ls._ids_from_record(data, str(data.get("name") or ""), uuid)
            if not verified or not ls.is_listed(role) or role == "ceo":
                continue
            since = data.get("statusUpdatedAt") or data.get("updatedAt")
            out.append({"box": f"{role}-{sid}", "role": role, "sid": sid, "name": data.get("name") or "",
                        "status": ls.map_status(data.get("status")),
                        "since": since / 1000 if isinstance(since, (int, float)) else None,
                        "tmux": str(data.get("tmux") or "").split(":", 1)[0] or None,
                        "trusted": _root_record(d, p)})
    return out


def read_meta(path: Path) -> list[dict]:
    raw = _read_capped(path, META_READ_MAX)
    if raw is None:
        return []
    lines = raw.decode("utf-8", "replace").splitlines()
    out = []
    for l in lines[-5000:]:
        try:
            d = json.loads(l)
            if not isinstance(d, dict) or not isinstance(d.get("from"), str) or not isinstance(d.get("to"), str):
                continue
            d["t"] = datetime.strptime(d["sent_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc).timestamp()
            out.append(d)
        except (ValueError, KeyError, TypeError, RecursionError):
            continue
    return out


def question_times() -> dict[str, list[float]] | None:
    """{requester session box: [created epoch, …]} from the Run Inbox, or None."""
    try:
        from tools import ask_run
        resp = ask_run._call("GET", ask_run.QUESTIONS_PATH, query={"limit": "200"})
    except Exception:   # no token, no route, an HTTP error: the source is unknown
        return None
    qs = resp.get("questions") if isinstance(resp, dict) else resp
    out: dict[str, list[float]] = {}
    for q in qs or []:
        if not isinstance(q, dict) or not isinstance(q.get("requester"), dict):
            continue
        try:
            t = datetime.fromisoformat(str(q.get("created_at")).replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
        out.setdefault(str(q["requester"].get("session") or ""), []).append(t)
    return out


def _has_lock(box: str) -> bool:
    try:
        return stat.S_ISREG(os.lstat(LOCKS_DIR / f"{box}.lock").st_mode)
    except OSError:
        return False


def live_box(box: str | None) -> str | None:
    """A C-level box a live session drains (design C4): `box` when it has a lock, else
    its role's state/locks/<role>-active box when that one has. .spawned_by and the
    letters log can name a C-level session that ended (cto-c34459eb, cmo-ef04792e), and
    nobody drains its box. Neither live: `box` itself. A PH box is returned as it is."""
    if not box or box.startswith("project_head-") or _has_lock(box):
        return box
    alt = f"{box.split('-', 1)[0]}-{ls.read_lock(LOCKS_DIR / (box.split('-', 1)[0] + '-active'))}"
    return alt if _BOX_RE.fullmatch(alt) and _has_lock(alt) else box


def live_c_levels() -> list[str]:
    """The live C-level boxes from the <role>-active pointers that have a lock (design
    C4): the session record's sid can be a different id from the box it drains."""
    from lib.roles import c_level_roles  # falls back to its static roster itself
    roles = c_level_roles()
    out = []
    for role in roles:
        box = f"{role}-{ls.read_lock(LOCKS_DIR / f'{role}-active')}"
        if _BOX_RE.fullmatch(box) and _has_lock(box):
            out.append(box)
    return sorted(out)


def owner_box(ph_sid: str) -> str | None:
    """A PH's C-level box from its .spawned_by ("cxo:<role>:<sid>"), moved to the role's
    live box when that session ended (C4)."""
    parts = ls.read_lock(LOCKS_DIR / f"project_head-{ph_sid}.spawned_by").split(":")
    box = f"{parts[1]}-{parts[2]}" if len(parts) == 3 and _BOX_RE.fullmatch(f"{parts[1]}-{parts[2]}") else None
    return live_box(box)


def open_work() -> set[str] | None:
    """Boxes that own an open task (hub), or None when the hub cannot be read."""
    try:
        from lib import db
        with db.get_conn(readonly=True) as conn:
            rows = conn.execute("SELECT DISTINCT owner_role, owner_cto FROM tasks WHERE status IN ("
                                + ",".join("?" * len(OPEN_STATUSES)) + ")", list(OPEN_STATUSES)).fetchall()
        return {f"{r['owner_role']}-{r['owner_cto']}" for r in rows if r["owner_role"] and r["owner_cto"]}
    except Exception:
        return None


def tier_of(box: str) -> str:
    """The tier that paces timed letters to `box`: a PH's projects row (normal when it has
    none or the hub is unreadable), critical for every C-level and the COO."""
    if not box.startswith("project_head-"):
        return "critical"
    return portfolio.tier_for({"owner_cto": box})


def coo_box() -> str | None:
    sid = ls.read_lock(LOCKS_DIR / "coo-active")
    return f"coo-{sid}" if re.fullmatch(r"[0-9a-f]{8}", sid) else None


# --- findings ----------------------------------------------------------------------

def find(sessions, meta, questions, hosts, now: float, *, panes=capture,
         live: set[str] | None = None, idle_s: float | None = IDLE_S) -> list[dict]:
    """Findings, each with a stable `subject` (its episode key). `live`: the boxes of
    live sessions; a blocker from a PH not in it is dropped (B-2). None = unknown, keep.
    `idle_s`: the idle threshold, already scaled for its recipient (None: no idle check)."""
    out = []
    for s in sessions:
        if not _BOX_RE.fullmatch(s["box"]):
            continue
        screen = panes(s["tmux"]) if s.get("tmux") else None
        if screen is not None and pane_waiting(screen):
            out.append({"kind": "waiting", "box": s["box"], "subject": f"waiting:{s['box']}",
                        "text": "a prompt is waiting on a person (permission or question)"})
        elif idle_s is not None and s["status"] == "idle" and s["since"] and now - s["since"] >= idle_s:
            out.append({"kind": "idle", "box": s["box"], "subject": f"idle:{s['box']}:{int(s['since'])}",
                        "text": f"idle {int((now - s['since']) // 60)} min"})
    for b in [m for m in meta if m.get("kind") == "blocker" and _BOX_RE.fullmatch(m["from"])
              and m["from"].startswith("project_head-")
              and _BOX_RE.fullmatch(m["to"]) and not m["to"].startswith("project_head-")]:
        if now - b["t"] < BLOCKER_S or (live is not None and b["from"] not in live):
            continue
        if any(m["from"] == b["to"] and m["to"] == b["from"] and m["t"] >= b["t"] for m in meta):
            continue
        if questions is None:
            card = "Run Inbox unreadable: card unknown"
        elif any(t >= b["t"] for t in questions.get(b["to"], [])):
            continue
        else:
            card = "no question card since"
        out.append({"kind": "blocker", "box": b["to"], "ph": b["from"],
                    "subject": f"blocker:{b['from']}:{b['to']}:{int(b['t'])}",
                    "text": f"holds {b['from']}'s blocker {int((now - b['t']) // 60)} min, "
                            f"no reply to it, {card}"})
    for host, info in hosts.items():
        if not _HOST_RE.fullmatch(str(host)) or not ls.DEFAULT_TTL_S < info["age"] <= HOST_RETIRED_S:
            continue
        out.append({"kind": "host", "box": None, "host": host, "subject": f"host:{host}",
                    "text": f"{host} stopped publishing {int(info['age'] // 60)} min ago: "
                            f"its sessions may be dead, nothing restarts them"})
    return out


AT_ONCE = ("waiting", "blocker")


def recipients(f: dict, live_c_levels: list[str]) -> list[str]:
    """Who hears about a finding; never the session the finding is about."""
    coo = coo_box()
    if f["kind"] == "host":
        to = list(live_c_levels) + [coo]
    elif f["kind"] == "idle":
        # An idle PH that owns open work: its lane C-level's digest too, not the COO's
        # alone (C4: nobody drains the COO box). Still fyi, so no clock wake.
        owner = owner_box(f["box"].split("-", 1)[1]) if f["box"].startswith("project_head-") and f.get("work") else None
        to = [owner, coo]
    elif f["kind"] == "waiting":
        owner = owner_box(f["box"].split("-", 1)[1]) if f["box"].startswith("project_head-") else None
        to = [owner, coo] if coo != f["box"] else list(live_c_levels)
    else:                                   # blocker: the C-level holding it, or its live successor
        to = [live_box(f["box"]), coo]
    about = None if f["kind"] == "blocker" else f.get("box")   # a blocker's box is its holder
    return sorted({b for b in to if b and _BOX_RE.fullmatch(b) and b != about})


def line(f: dict) -> str:
    return f"{f['kind']} {f.get('box') or f.get('host')}: {f['text']}"[:LINE_MAX]


_EMPTY_STATE = {"episodes": {}, "digest": {}}


def load_state(now: float) -> dict:
    """{"episodes": {subject: {"start", "sent", "last"}}, "digest": {box: {"last",
    "lines"}}}. A time after `now` means the clock stepped back (or a bad value): it is
    clamped to `now` and the counters stay, so a step back never resets a rate limit
    (round 2, item 3). A `sent` we could not have written is dropped with its episode.
    Raises StateUnusable for a file over STATE_READ_MAX."""
    raw = _read_capped(STATE_PATH, STATE_READ_MAX, whole=True)
    try:
        d = json.loads(raw) if raw else {}
    except (ValueError, RecursionError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    ok = lambda t: isinstance(t, (int, float)) and not isinstance(t, bool) and t >= 0
    count = lambda n: isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= AT_ONCE_SENDS
    eps = {k: {"start": min(v["start"], now), "sent": v["sent"], "last": min(v["last"], now)}
           for k, v in (d.get("episodes") or {}).items() if isinstance(k, str) and isinstance(v, dict)
           and ok(v.get("start")) and ok(v.get("last")) and count(v.get("sent"))}
    dig = {k: {"last": min(v["last"], now), "lines": [str(x)[:LINE_MAX] for x in v["lines"][:DIGEST_LINES]]}
           for k, v in (d.get("digest") or {}).items()
           if isinstance(k, str) and _BOX_RE.fullmatch(k) and isinstance(v, dict)
           and ok(v.get("last")) and isinstance(v.get("lines"), list)}
    return {"episodes": eps, "digest": dig}


def _bounded(state: dict) -> str:
    """The state as JSON text: the newest MAX_EPISODES episodes and MAX_DIGESTS digest
    boxes, and never more than STATE_READ_MAX (ASCII, so chars are bytes), the oldest
    digest box and then the oldest episode dropped first."""
    eps = dict(sorted(state["episodes"].items(), key=lambda kv: kv[1]["start"])[-MAX_EPISODES:])
    dig = {b: {"last": d["last"], "lines": d["lines"][:DIGEST_LINES]}
           for b, d in sorted(state["digest"].items(), key=lambda kv: kv[1]["last"])[-MAX_DIGESTS:]}
    blob = json.dumps({"episodes": eps, "digest": dig})
    while len(blob) > STATE_READ_MAX and (dig or eps):
        victim = dig or eps
        del victim[next(iter(victim))]                  # insertion order = oldest first
        blob = json.dumps({"episodes": eps, "digest": dig})
    return blob


def save_state(state: dict) -> None:
    """Write the state atomically. Raises StateUnusable when it cannot be written: a
    letter that cannot be remembered repeats on every run, so the caller must not send."""
    blob = _bounded(state)
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        # mkstemp: O_EXCL on a fresh random name, so no planted .tmp link is followed;
        # os.replace swaps the directory entry and never writes through a link.
        fd, tmp = tempfile.mkstemp(dir=STATE_PATH.parent, prefix=".escalation_watch.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(blob)
            os.replace(tmp, STATE_PATH)
        except OSError:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
    except OSError as e:
        raise StateUnusable(f"state file {STATE_PATH} cannot be saved ({type(e).__name__}: "
                            f"{e.strerror or e})") from e


RULE = ("Rule (CEO 2026-10-14): a PH sends its C-level a blocker at once; a C-level that "
        "cannot unblock it puts a question card on /run at once (ask_ceo), never a todo.")


def nudge(findings, live_c_levels, now: float, *, send=mailbox.send, wake=None,
          panes=capture, budget=None, tier_of=tier_of) -> list[str]:
    """Send what is due and return one line per letter. An at-once finding (waiting,
    blocker): a letter when its episode starts, one reminder REMIND_S later, then
    nothing. Others: one digest line per episode, flushed per recipient at most once
    per DIGEST_S. A wake only after an at-once letter, and only into a screen that is
    prompt_ready. `budget` (lib/wake_backoff.load_budget(); None = no slowdown) and
    `tier_of` pace the reminder and the digest per recipient: wake_interval(REMIND_S or
    DIGEST_S, tier=tier_of(recipient)); a recipient whose interval is None gets neither."""
    def interval(base, box):
        return wake_backoff.wake_interval(base, tier=tier_of(box), budget_json=budget, now=now)

    state, sent = load_state(now), []
    eps, dig = state["episodes"], state["digest"]
    current = {f["subject"] for f in findings}
    for k in [k for k in eps if k not in current]:      # the episode ended
        del eps[k]
    # Tracked episodes first: past MAX_EPISODES a new one waits, so the cap never drops an
    # episode that is still running (it would fire again on the next run).
    findings = sorted(findings, key=lambda f: f["subject"] not in eps)[:MAX_EPISODES]
    save_state(state)       # before any letter: a state that cannot be saved sends nothing
    for f in findings:
        ep = eps.setdefault(f["subject"], {"start": now, "sent": 0, "last": 0})
        to = recipients(f, live_c_levels)
        if f["kind"] in AT_ONCE:
            if ep["sent"] >= AT_ONCE_SENDS:
                continue
            if ep["sent"] == 1:         # the reminder is the one timed part: pace it per recipient
                to = [b for b in to if (iv := interval(REMIND_S, b)) is not None and now - ep["last"] >= iv]
                if not to:
                    continue
            again = " (reminder; the last one this episode)" if ep["sent"] else ""
            body = f"blocker · urgent · escalation watch{again}: {line(f)}. {RULE}"
            for box in to:
                role, sid = box.split("-", 1)
                send(role, sid, body, *FROM, kind="blocker",
                     subject=f"escalation: {f['kind']} {f.get('box') or ''}"[:80])
                woke = ""
                if wake:
                    screen = panes(box)
                    if screen is not None and prompt_ready(screen):
                        wake(role, sid)
                        woke = " +wake"
                sent.append(f"{box} <- {f['kind']} {f.get('box') or f.get('host')}{woke}")
        else:
            if ep["sent"]:
                continue
            for box in to:
                if interval(DIGEST_S, box) is not None:
                    dig.setdefault(box, {"last": 0, "lines": []})["lines"].append(line(f))
        ep["sent"], ep["last"] = ep["sent"] + 1, now
    for box, d in dig.items():
        iv = interval(DIGEST_S, box)
        if d["lines"] and iv is not None and now - d["last"] >= iv:
            role, sid = box.split("-", 1)
            body = ("fyi · normal · escalation watch digest (no wake; act only if one is yours):\n- "
                    + "\n- ".join(d["lines"][:50]))
            send(role, sid, body, *FROM, kind="fyi", subject="escalation watch digest")
            sent.append(f"{box} <- digest of {len(d['lines'])}")
            d["lines"], d["last"] = [], now
    state["digest"] = {b: d for b, d in dig.items()
                       if d["lines"] or now - d["last"] < (interval(DIGEST_S, b) or DIGEST_S)}
    try:
        save_state(state)
    except StateUnusable as e:
        e.sent = sent           # the letters are out; main prints them with the note
        raise
    return sent


def _wake(role: str, sid: str) -> None:
    try:
        from tools import send_to_cto
        send_to_cto._attempt_wake(role, sid, "Escalation watch")
    except Exception:
        pass


def _th_clock(t: float) -> str:
    return datetime.fromtimestamp(t, timezone(timedelta(hours=7))).strftime("%H:%M")


def _boxes(sessions) -> dict[str, dict]:
    return {s["box"]: s for s in sessions if _BOX_RE.fullmatch(s.get("box") or "")}


def rewake_scan(sessions, now: float, state: dict, *, budget=None, tier_of=tier_of,
                unread=None) -> tuple[list[dict], list[str]]:
    """Phase 1 of the re-wake ladder (W2, design C3), before owner_relay.run on the same
    tick. Zero model calls. Returns (owner lines, boxes due a try).

    Every live local C-level (not the COO: SomPong has no inbox hook, so a wake never
    drains its box) and PH whose box holds an unread letter that is not fyi or report
    (those wait for the next prompt, token rule 2) is due a try at 5, 15 and 45 min of
    the oldest such letter's age, each x wake_interval (None, a low tier: no re-wake),
    while its session record is idle (rewake makes the try). After the third try, a PH's
    owner C-level gets one line; a PH box with a lock and no live session holding such a
    letter DEAD_PH_S or longer gets one owner line per episode. A parked PH stays silent.
    The lines carry `to` (the owner's live box): owner_relay.run puts them in that box's
    one letter of the tick (token rule 3), inside MAX_LETTERS, and wakes the box at most
    once. `state` is owner_relay's."""
    from tools import owner_relay as orl
    unread = unread or orl.unread
    by_box = _boxes(sessions)
    lad, dead_eps = state.setdefault("rewake", {}), state.setdefault("dead_eps", {})
    lines: list[dict] = []
    due: list[str] = []

    def owner_line(ph: str, kind: str, reason: str, t: float) -> None:
        to = orl.ph_owner(ph.split("-", 1)[1])
        if to and not to.startswith("coo-"):
            lines.append({"task": ph, "kind": kind, "role": "project_head", "sid": ph.split("-", 1)[1],
                          "reason": reason, "actor": "", "t": t, "to": to})

    for box, s in sorted(by_box.items()):
        role = s.get("role") or box.split("-", 1)[0]
        if role == "coo" or orl.parked(box):
            lad.pop(box, None)
            continue
        waiting = sorted(m for m, k in unread(box) if k not in mailbox.QUIET_KINDS)
        if not waiting:
            lad.pop(box, None)          # the box emptied: the ladder resets
            continue
        oldest = waiting[0]
        ep = lad.get(box)
        if not isinstance(ep, dict) or ep.get("key") != oldest:
            ep = lad[box] = {"key": oldest, "tries": 0, "escalated": False, "why": ""}
        if ep["tries"] >= len(REWAKE_LADDER):
            if not ep["escalated"] and box.startswith("project_head-"):
                ep["escalated"] = True
                owner_line(box, "rewake", f"{len(waiting)} unread since {_th_clock(oldest)} TH; "
                                          f"{len(REWAKE_LADDER)} wakes did not land "
                                          f"({ep.get('why') or 'not read'})", oldest)
            continue
        iv = wake_backoff.wake_interval(REWAKE_LADDER[ep["tries"]], tier=tier_of(box), budget_json=budget, now=now)
        if iv is None or now - oldest < iv:
            continue
        if s.get("status") != "idle":
            continue                    # mid-turn: the first idle tick tries; no try spent
        due.append(box)
    for name in _ph_locks():
        box = name[:-len(".lock")]
        if box in by_box or not _BOX_RE.fullmatch(box):
            continue
        waiting = sorted(m for m, k in unread(box) if k not in mailbox.QUIET_KINDS)
        if not waiting or now - waiting[0] < DEAD_PH_S:
            dead_eps.pop(box, None)
            continue
        if dead_eps.get(box) == waiting[0]:
            continue                    # this episode was told
        dead_eps[box] = waiting[0]
        owner_line(box, "ph_dead", f"a lock but no live session; {len(waiting)} unread since "
                                   f"{_th_clock(waiting[0])} TH", waiting[0])
    locked = {n[:-len(".lock")] for n in _ph_locks()}
    for k in [k for k in lad if k not in by_box]:          # the session ended: its ladder too
        del lad[k]
    for k in [k for k in dead_eps if k not in locked]:     # lock gone (parked, closed): episode over
        del dead_eps[k]
    return lines, due


def rewake(sessions, now: float, state: dict, due, *, mode: str, panes=capture_e, wake=None,
           budget=None, tier_of=tier_of, woke: set | None = None) -> list[str]:
    """Phase 2 of the re-wake ladder, after owner_relay.run: one try per box rewake_scan
    found due. owner_relay.try_wake needs an idle record, a prompt_ready screen (captured
    with escapes), the day cap and the tick's caps. A hold that is a running turn (record
    or screen) or a cap (owner_relay.NO_TRY) spends no try: the first tick after the turn
    ends tries. Any other hold (a draft, a choice prompt, an unreadable screen, a wake
    that did not land) is a try. Mode dry prints and counts, live acts."""
    from tools import owner_relay as orl
    woke = set() if woke is None else woke
    if wake is None:
        from tools import mail_wake
        wake = mail_wake.wake
    by_box, lad, out = _boxes(sessions), state.setdefault("rewake", {}), []
    for box in due:
        ep = lad.get(box)
        if not isinstance(ep, dict):
            continue
        if mode != "live":
            ep["tries"] += 1
            out.append(f"would rewake {box} try {ep['tries']}")
            continue
        ok, why = orl.try_wake(box, state, now, sessions=by_box, panes=panes, wake=wake, budget=budget,
                               tier=tier_of(box), woke=woke)
        if not ok and why.startswith(orl.NO_TRY):
            out.append(f"rewake {box} waits: {why}")
            continue                    # not a failed try: a later tick or the hourly batch takes it
        ep["tries"] += 1
        ep["why"] = "" if ok else why
        out.append(f"rewake {box} try {ep['tries']}: " + ("woke" if ok else f"held: {why}"))
    return out


def relay_tick(sessions, now: float, state: dict, *, mode: str, hub, panes=capture_e, wake=None, send=None,
               budget=None, tier_of=tier_of, meta=(), queues=None, unread=None, host: str | None = None,
               woke: set | None = None) -> list[str]:
    """One W2 tick on a loaded owner_relay state (mode dry or live): rewake_scan, then
    owner_relay.run with the ladder's owner lines in it (at most one letter and one wake
    per box), then rewake's tries. `sessions` is with_lock_boxes' list."""
    from tools import owner_relay as orl
    woke = set() if woke is None else woke
    lines, due = rewake_scan(sessions, now, state, budget=budget, tier_of=tier_of, unread=unread)
    out = orl.run(now, state, mode=mode, hub=hub, sessions=_boxes(sessions), panes=panes, meta=meta,
                  budget=budget, tier_of=tier_of, woke=woke, wake=wake, send=send, queues=queues,
                  host=host or orl.HOST, extra=lines)
    out += rewake(sessions, now, state, due, mode=mode, panes=panes, wake=wake, budget=budget,
                  tier_of=tier_of, woke=woke)
    return out


def _ph_locks() -> list[str]:
    try:
        return sorted(p.name for p in LOCKS_DIR.iterdir()
                      if re.fullmatch(r"project_head-[0-9a-f]{8}\.lock", p.name) and _has_lock(p.name[:-5]))
    except OSError:
        return []


def with_lock_boxes(sessions) -> list[dict]:
    """`sessions` keyed by the box each pane drains, one entry per pane (one ladder, one
    day count). A live C-level box (a <role>-active pointer with a lock, C4) is drained by
    the session in the tmux session of that name, whose record can carry another id
    (CTO Main: record cto-<uuid tail>, tmux and box cto-fresh): that record becomes the
    box's entry with its own status, and a busy record wins over an idle one for the same
    box. A live C-level box with no record at all is added with status idle: its status
    is unknown, so its screen gates a wake (a running turn there is "busy" and spends no
    ladder try; prompt_ready refuses a choice prompt and a draft). Never the COO."""
    lock_boxes = [b for b in live_c_levels() if not b.startswith("coo-")]
    merged: dict[str, dict] = {}
    for s in sessions:
        t = s.get("tmux")
        if t in lock_boxes and s.get("box") != t:
            s = dict(s, box=t, role=t.split("-", 1)[0], sid=t.split("-", 1)[1])
        prev = merged.get(s.get("box"))
        if prev is None or (prev.get("status") == "idle" and s.get("status") != "idle"):
            merged[s.get("box")] = s
    extra = [{"box": b, "role": b.split("-", 1)[0], "sid": b.split("-", 1)[1], "status": "idle", "tmux": b,
              "since": None, "name": b} for b in lock_boxes if b not in merged]
    return list(merged.values()) + extra


def owner_tick(sessions, now: float, budget, *, hub=None, panes=capture_e, wake=None, send=None) -> list[str]:
    """W2: owner letters for task events (tools/owner_relay, C2) and the re-wake ladder
    (C3) on this tick (relay_tick), under one state file and one mode
    (state/owner_relay.mode). `sessions`: only records _root_record trusts (main()).
    Never raises: a failure is one note line and the escalation letters are untouched."""
    try:
        from tools import owner_relay as orl
        mode = orl.read_mode()
        if mode == "off":
            return ["owner-relay off (state/owner_relay.mode)"]
        st = orl.load_state(mode)
        from lib import config
        out = relay_tick(with_lock_boxes(sessions), now, st, mode=mode, hub=hub or orl.Hub(), panes=panes,
                         wake=wake, send=send, budget=budget, meta=read_meta(mailbox.meta_path()),
                         host=config.self_host())
        orl.save_state(st)
        return [f"[{mode}] {o}" for o in out]
    except Exception as e:      # the type only: a driver error can echo a connection string
        from tools import owner_relay as orl
        why = f": {e}" if isinstance(e, orl.StateUnusable) else ""
        return [f"note owner relay skipped ({type(e).__name__}{why})"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--nudge", action="store_true", help="send the letters (default: print only)")
    a = ap.parse_args(argv)
    from lib import config
    host = config.self_host()
    now = _now()
    notes = []
    try:
        conn = ls._open_hub()
        try:
            snap = ls._snapshot_from_hub(conn, ls.DEFAULT_TTL_S)
        finally:
            conn.close()
        hosts = snap["hosts"]
        live = {f"{r['role']}-{r['sid']}" for r in snap["rows"] if not r.get("stale")}
        live_c = sorted({f"{r['role']}-{r['sid']}" for r in snap["rows"]
                         if ls.is_c_level(r["role"]) and r["role"] != "ceo" and not r.get("stale")
                         and r["host"] == host})
    except Exception as e:
        hosts, live_c, live = {}, [], None
        notes.append(f"hub unreadable ({type(e).__name__}): host check skipped")
    sessions = local_sessions(host)
    if live is not None:
        live |= {s["box"] for s in sessions}
    live_c = live_c_levels() or live_c      # C4: the boxes the live sessions drain
    if not live_c:
        live_c = sorted({s["box"] for s in sessions if ls.is_c_level(s["role"])})
    questions = question_times()
    if questions is None:
        notes.append("Run Inbox unreadable: blocker findings cannot see question cards")
    budget = wake_backoff.load_budget()
    factor = wake_backoff.backoff_factor(budget, now)
    if factor > 1:
        notes.append(f"usage budget over: timed checks slowed x{factor} (new findings still go at once)")
    idle_s = wake_backoff.wake_interval(IDLE_S, tier=tier_of(coo_box() or ""), budget_json=budget, now=now)
    findings = find(sessions, read_meta(mailbox.meta_path()), questions, hosts, now, live=live, idle_s=idle_s)
    if any(f["kind"] == "idle" for f in findings):
        work = open_work()
        for f in findings:
            if f["kind"] == "idle":
                f["work"] = bool(work and f["box"] in work)
    for f in findings:
        print(f"{f['kind']:<8} {f.get('box') or f.get('host')}: {f['text']}")
    for h, info in hosts.items():
        if info["age"] > HOST_RETIRED_S:
            notes.append(f"host {h} stale {int(info['age'] // 3600)} h: retired? not a finding")
    for n in notes:
        print(f"note     {n}")
    if not findings:
        print("ok       nothing stalled")
    rc = 0
    if a.nudge:     # also on an empty scan: ended episodes are pruned, a due digest flushes
        try:
            sent = nudge(findings, live_c, now, wake=_wake, budget=budget)
        except StateUnusable as e:
            for out in e.sent:
                print(f"sent     {out}")
            print(f"note     {e}; no letter goes out until it is fixed")
            rc = 1
        else:
            for out in sent:
                print(f"sent     {out}")
        # W2: its own state and mode file; only records root wrote (_root_record)
        for out in owner_tick([s for s in sessions if s.get("trusted")], now, budget):
            print(f"relay    {out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
