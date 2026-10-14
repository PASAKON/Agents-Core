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

Each finding nudges the session's C-level (a PH's owner, from .spawned_by; a
C-level itself) and the COO with one letter, then again at most every RENUDGE_S.
Host findings go to the COO and every live C-level. Dry run by default:

    python tools/escalation_watch.py            # print findings, send nothing
    python tools/escalation_watch.py --nudge    # also send the letters

Sources: the hub's live_sessions/live_hosts (tools/live_sessions), this host's
session records, tmux capture-pane, state/reports/letters-meta.jsonl (lib/mailbox
logs every letter's from/to/kind, never the body), and the Run Inbox question list
(tools/ask_run). A source that cannot be read is named in the output, never guessed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import mailbox  # noqa: E402
from tools import live_sessions as ls  # noqa: E402

IDLE_S = 30 * 60
BLOCKER_S = 15 * 60
RENUDGE_S = 30 * 60
LOCKS_DIR = ROOT / "state" / "locks"
STATE_PATH = ROOT / "state" / "escalation_watch.json"
FROM = ("watchdog", "escalation")
_BOX_RE = re.compile(r"^(c[a-z]o|project_head)-([0-9a-f]{8})$")
# A numbered choice with the cursor on it, plus the footer of a choice prompt.
_CHOICE_RE = re.compile(r"^[\s│┃|]*❯\s*\d+\.\s")   # it may sit inside a │ box
_CHOICE_HINTS = ("Do you want", "Esc to cancel", "to navigate", "Enter to select", "Would you like")


def _now() -> float:
    return time.time()


# --- sources -----------------------------------------------------------------------

def pane_waiting(text: str) -> bool:
    """True when a pane's last screen holds a choice prompt waiting on a person."""
    tail = text.splitlines()[-30:]
    return any(_CHOICE_RE.match(l) for l in tail) and any(h in l for l in tail for h in _CHOICE_HINTS)


def capture(tmux_target: str) -> str | None:
    try:
        r = subprocess.run(["tmux", "capture-pane", "-p", "-t", tmux_target],
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
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    out = []
    for l in lines[-5000:]:
        try:
            d = json.loads(l)
            d["t"] = datetime.strptime(d["sent_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc).timestamp()
            out.append(d)
        except (ValueError, KeyError, TypeError):
            continue
    return out


def question_times() -> dict[str, list[float]] | None:
    """{requester session box: [created epoch, …]} from the Run Inbox, or None."""
    try:
        from tools import ask_run
        resp = ask_run._call("GET", ask_run.QUESTIONS_PATH, query={"limit": "200"})
    except BaseException:   # no token, no route, an HTTP error: the source is unknown
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
    try:
        parts = (LOCKS_DIR / f"project_head-{ph_sid}.spawned_by").read_text().strip().split(":")
    except OSError:
        return None
    return f"{parts[1]}-{parts[2]}" if len(parts) == 3 and _BOX_RE.match(f"{parts[1]}-{parts[2]}") else None


def coo_box() -> str | None:
    try:
        sid = (LOCKS_DIR / "coo-active").read_text().strip()
    except OSError:
        return None
    return f"coo-{sid}" if re.fullmatch(r"[0-9a-f]{8}", sid) else None


# --- findings ----------------------------------------------------------------------

def find(sessions, meta, questions, hosts, now: float, *, panes=capture) -> list[dict]:
    out = []
    for s in sessions:
        screen = panes(s["tmux"]) if s.get("tmux") else None
        if screen is not None and pane_waiting(screen):
            out.append({"kind": "waiting", "box": s["box"], "name": s["name"],
                        "text": "a prompt is waiting on a person (permission or question)"})
        elif s["status"] == "idle" and s["since"] and now - s["since"] >= IDLE_S:
            out.append({"kind": "idle", "box": s["box"], "name": s["name"],
                        "text": f"idle {int((now - s['since']) // 60)} min"})
    for b in [m for m in meta if m.get("kind") == "blocker" and m["from"].startswith("project_head-")
              and _BOX_RE.match(m["to"]) and not m["to"].startswith("project_head-")]:
        if now - b["t"] < BLOCKER_S:
            continue
        answered = any(m["from"] == b["to"] and m["to"] == b["from"] and m["t"] >= b["t"] for m in meta)
        if answered:
            continue
        if questions is None:
            card = "Run Inbox unreadable: card unknown"
        elif any(t >= b["t"] for t in questions.get(b["to"], [])):
            continue
        else:
            card = "no question card since"
        out.append({"kind": "blocker", "box": b["to"], "ph": b["from"], "since": b["t"],
                    "text": f"holds {b['from']}'s blocker {int((now - b['t']) // 60)} min, "
                            f"no reply to it, {card}"})
    for host, info in hosts.items():
        if info["age"] > ls.DEFAULT_TTL_S:
            out.append({"kind": "host", "box": None, "host": host,
                        "text": f"{host} stopped publishing {int(info['age'] // 60)} min ago: "
                                f"its sessions may be dead, nothing restarts them"})
    return out


def recipients(f: dict, live_c_levels: list[str]) -> list[str]:
    coo = coo_box()
    if f["kind"] == "host":
        to = live_c_levels
    elif f["box"].startswith("project_head-"):
        to = [owner_box(f["box"].split("-", 1)[1])]
    else:
        to = [f["box"]]
    return sorted({b for b in to + [coo] if b})


def key(f: dict) -> str:
    return f"{f['kind']}:{f.get('box') or f.get('host')}:{int(f.get('since') or 0)}"


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, ValueError):
        return {}


def nudge(findings, live_c_levels, now: float, *, send=mailbox.send, wake=None) -> list[str]:
    state, sent = load_state(), []
    for f in findings:
        k = key(f)
        if now - state.get(k, 0) < RENUDGE_S:
            continue
        who = f.get("name") or f.get("box") or f.get("host")
        body = (f"blocker · urgent · escalation watch: {who} {f['text']}. "
                "Rule (CEO 2026-10-14): a PH sends its C-level a blocker at once; a C-level that "
                "cannot unblock it puts a question card on /run at once (ask_ceo), never a todo.")
        for box in recipients(f, live_c_levels):
            role, sid = box.split("-", 1)
            send(role, sid, body, *FROM)
            if wake:
                wake(role, sid)
            sent.append(f"{box} <- {f['kind']} {who}")
        state[k] = now
    state = {k: t for k, t in state.items() if now - t < 2 * 86400}
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        os.replace(tmp, STATE_PATH)
    except OSError:
        pass
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
        live_c = sorted({f"{r['role']}-{r['sid']}" for r in snap["rows"]
                         if ls.is_c_level(r["role"]) and r["role"] != "ceo" and not r.get("stale")
                         and r["host"] == host})
    except Exception as e:
        hosts, live_c = {}, []
        notes.append(f"hub unreadable ({type(e).__name__}): host check skipped")
    sessions = local_sessions(host)
    if not live_c:
        live_c = sorted({s["box"] for s in sessions if ls.is_c_level(s["role"])})
    questions = question_times()
    if questions is None:
        notes.append("Run Inbox unreadable: blocker findings cannot see question cards")
    findings = find(sessions, read_meta(mailbox.meta_path()), questions, hosts, now)
    for f in findings:
        print(f"{f['kind']:<8} {f.get('name') or f.get('box') or f.get('host')}: {f['text']}")
    for n in notes:
        print(f"note     {n}")
    if not findings:
        print("ok       nothing stalled")
    if a.nudge and findings:
        for line in nudge(findings, live_c, now, wake=_wake):
            print(f"sent     {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
