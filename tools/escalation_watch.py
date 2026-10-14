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
the rename service uses before it types. Letters carry box ids, never a session's
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
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import mailbox  # noqa: E402
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
_BOX_RE = re.compile(r"(c[a-z]o|project_head)-([0-9a-f]{8})")   # always fullmatch
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

def capture(tmux_target: str) -> str | None:
    try:
        r = subprocess.run(["tmux", "capture-pane", "-p", "-t", f"={tmux_target}:"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def local_sessions(host: str) -> list[dict]:
    """This host's live listed sessions from their records: box, status age, tmux."""
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
                        "tmux": str(data.get("tmux") or "").split(":", 1)[0] or None})
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


def owner_box(ph_sid: str) -> str | None:
    """A PH's C-level box from its .spawned_by ("cxo:<role>:<sid>")."""
    parts = ls.read_lock(LOCKS_DIR / f"project_head-{ph_sid}.spawned_by").split(":")
    return f"{parts[1]}-{parts[2]}" if len(parts) == 3 and _BOX_RE.fullmatch(f"{parts[1]}-{parts[2]}") else None


def coo_box() -> str | None:
    sid = ls.read_lock(LOCKS_DIR / "coo-active")
    return f"coo-{sid}" if re.fullmatch(r"[0-9a-f]{8}", sid) else None


# --- findings ----------------------------------------------------------------------

def find(sessions, meta, questions, hosts, now: float, *, panes=capture,
         live: set[str] | None = None) -> list[dict]:
    """Findings, each with a stable `subject` (its episode key). `live`: the boxes of
    live sessions; a blocker from a PH not in it is dropped (B-2). None = unknown, keep."""
    out = []
    for s in sessions:
        if not _BOX_RE.fullmatch(s["box"]):
            continue
        screen = panes(s["tmux"]) if s.get("tmux") else None
        if screen is not None and pane_waiting(screen):
            out.append({"kind": "waiting", "box": s["box"], "subject": f"waiting:{s['box']}",
                        "text": "a prompt is waiting on a person (permission or question)"})
        elif s["status"] == "idle" and s["since"] and now - s["since"] >= IDLE_S:
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
        to = [coo]
    elif f["kind"] == "waiting":
        owner = owner_box(f["box"].split("-", 1)[1]) if f["box"].startswith("project_head-") else None
        to = [owner, coo] if coo != f["box"] else list(live_c_levels)
    else:                                   # blocker: the C-level holding it
        to = [f["box"], coo]
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
          panes=capture) -> list[str]:
    """Send what is due and return one line per letter. An at-once finding (waiting,
    blocker): a letter when its episode starts, one reminder REMIND_S later, then
    nothing. Others: one digest line per episode, flushed per recipient at most once
    per DIGEST_S. A wake only after an at-once letter, and only into a screen that is
    prompt_ready."""
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
            if ep["sent"] >= AT_ONCE_SENDS or (ep["sent"] == 1 and now - ep["last"] < REMIND_S):
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
                dig.setdefault(box, {"last": 0, "lines": []})["lines"].append(line(f))
        ep["sent"], ep["last"] = ep["sent"] + 1, now
    for box, d in dig.items():
        if d["lines"] and now - d["last"] >= DIGEST_S:
            role, sid = box.split("-", 1)
            body = ("fyi · normal · escalation watch digest (no wake; act only if one is yours):\n- "
                    + "\n- ".join(d["lines"][:50]))
            send(role, sid, body, *FROM, kind="fyi", subject="escalation watch digest")
            sent.append(f"{box} <- digest of {len(d['lines'])}")
            d["lines"], d["last"] = [], now
    state["digest"] = {b: d for b, d in dig.items() if d["lines"] or now - d["last"] < DIGEST_S}
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
    if not live_c:
        live_c = sorted({s["box"] for s in sessions if ls.is_c_level(s["role"])})
    questions = question_times()
    if questions is None:
        notes.append("Run Inbox unreadable: blocker findings cannot see question cards")
    findings = find(sessions, read_meta(mailbox.meta_path()), questions, hosts, now, live=live)
    for f in findings:
        print(f"{f['kind']:<8} {f.get('box') or f.get('host')}: {f['text']}")
    for h, info in hosts.items():
        if info["age"] > HOST_RETIRED_S:
            notes.append(f"host {h} stale {int(info['age'] // 3600)} h: retired? not a finding")
    for n in notes:
        print(f"note     {n}")
    if not findings:
        print("ok       nothing stalled")
    if a.nudge:     # also on an empty scan: ended episodes are pruned, a due digest flushes
        try:
            sent = nudge(findings, live_c, now, wake=_wake)
        except StateUnusable as e:
            for out in e.sent:
                print(f"sent     {out}")
            print(f"note     {e}; no letter goes out until it is fixed")
            return 1
        for out in sent:
            print(f"sent     {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
