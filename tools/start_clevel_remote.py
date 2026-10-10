"""Start a C-level on another mesh host, with caller guards and a local budget."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
import time
from pathlib import Path

from lib import config, db, mesh, roles

STATE = Path(__file__).resolve().parent.parent / "state" / "start-clevel-remote.json"


def _reserve(host: str, role: str) -> str | None:
    """Reserve before dialing, including uncertain/failed starts in the budget.

    An exclusive lock file serializes readers across MCP processes on all hosts.
    Locks older than 60 seconds are reclaimed; the JSON is replaced atomically.
    """
    STATE.parent.mkdir(parents=True, exist_ok=True)
    lock = STATE.with_suffix(".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            if time.time() - lock.stat().st_mtime <= 60:
                return "rate limit state busy"
            lock.unlink()
        except FileNotFoundError:
            pass
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return "rate limit state busy"
    try:
        now = time.time()
        try:
            rows = json.loads(STATE.read_text())
            if not isinstance(rows, list) or not all(
                isinstance(r, dict) and isinstance(r.get("host"), str)
                and isinstance(r.get("role"), str)
                and isinstance(r.get("at"), (int, float))
                and math.isfinite(r["at"]) for r in rows
            ):
                rows = []
        except (OSError, ValueError):
            rows = []
        rows = [r for r in rows if now - r["at"] < 3600]
        if any(r["host"] == host and r["role"] == role and now - r["at"] < 600
               for r in rows):
            return "rate limit: one start per host/role per 10 minutes"
        if len(rows) >= 6:
            return "rate limit: six starts per hour"
        rows.append({"host": host, "role": role, "at": now})
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=STATE.parent, delete=False) as f:
                tmp = Path(f.name)
                json.dump(rows, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, STATE)
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)
    finally:
        os.close(fd)
        lock.unlink()
    return None


def start_clevel_remote(host: str, role: str, resume_session_id: str = "") -> str:
    caller = os.environ.get("CXO_ROLE", "")
    reply = {"ok": False, "error": "start refused"}
    outcome = "refused"
    try:
        why = None
        if caller not in roles.c_level_roles():
            why = "caller must be C-level"
        elif role not in config.live_c_level_roles():
            why = "role is not a live C-level"
        elif roles.singleton_refusal(role):
            why = roles.singleton_refusal(role)
        elif host not in config.hosts() or not config.hosts()[host].get("mesh_ssh"):
            why = "host has no mesh_ssh"
        elif host == config.self_host():
            why = "host must be remote"
        elif not isinstance(resume_session_id, str) or (
            resume_session_id and not re.fullmatch(r"[0-9a-f]{8}", resume_session_id)
        ):
            why = "resume_session_id must be eight lowercase hex characters"
        elif not mesh.enabled():
            why = "ORG_MESH_DISPATCH is disabled"
        else:
            why = _reserve(host, role)
        if why:
            reply = {"ok": False, "error": why}
        else:
            args = ("--resume", resume_session_id) if resume_session_id else ()
            reply = mesh.dispatch(host, "start_clevel", role, *args)
            outcome = "allowed" if reply.get("ok") is True else "dispatch_refused"
    except mesh.MeshUnreachable as e:
        outcome = type(e).__name__
        detail = str(e)
        try:
            from tools.node_dispatch import _redact
        except ImportError:
            pass
        else:
            detail = _redact(detail)
        reply = {"ok": False, "error": "unreachable", "detail": detail[:200]}
    except Exception as e:
        # Do not copy transport stderr or configuration values into the audit.
        outcome = type(e).__name__
        reply = {"ok": False, "error": outcome}
    finally:
        def safe(value):
            return value if isinstance(value, str) and re.fullmatch(r"[a-z0-9_-]{0,64}", value) else "invalid"

        payload = {
            "host": safe(host), "role": safe(role), "resumed_from": safe(resume_session_id),
            "caller_role": safe(caller),
            "caller_session": safe(os.environ.get("CXO_SESSION_ID") or
                                   os.environ.get("CTO_SESSION_ID", "")),
            "outcome": outcome, "ok": reply.get("ok") is True,
        }
        try:
            with db.get_conn() as conn:
                db.log_event(conn, None, "start_clevel_remote", "mesh_start", payload)
        except Exception:
            pass
    return json.dumps(reply, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("host")
    ap.add_argument("role")
    ap.add_argument("--resume", default="")
    args = ap.parse_args(argv)
    result = start_clevel_remote(args.host, args.role, args.resume)
    print(result)
    return 0 if json.loads(result).get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
