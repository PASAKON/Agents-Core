"""The one command an `org_dispatch` ssh key may run on a host (Org Mesh W2.2).

docs/design/org-mesh.md, W2: `authorized_keys` pins the key to
`python -m tools.node_dispatch` (see docs/ops/node-dispatch.md for the exact
line per OS; installed in W2.8). sshd hands the caller's text to this process
as SSH_ORIGINAL_COMMAND and never to a shell. A caller can NAME a row in the
hub (a task id, a letter id); it can never SEND a shell.

The model is runners/mac_agent.py's fixed dispatch table: an enumerated verb
list, every argument checked against an exact pattern, an unknown verb is a
refusal and never a fallback execution. Nothing here passes a caller string to
a shell -- every subprocess call is an argv list. Every value that reaches
tools.tmux_session.create()'s shell string (start_clevel on non-darwin) is an
allow-list member, a regex match, or generated here.

Input   SSH_ORIGINAL_COMMAND when set, else sys.argv[1:] (local use, tests).
Output  exactly one JSON line on stdout:
          {"ok": true,  "verb": ..., "result": ...}
          {"ok": false, "verb": ..., "error": ...}
Exit    0 ok, 2 refusal (nothing ran), 1 a verb that ran and failed.
Audit   every call, refusals included, writes one `events` row (actor
        node_dispatch, kind dispatch) through lib.db.log_event.

In-process API for W2.3: `dispatch(verb, args) -> dict`. It is synchronous and
some verbs call asyncio.run(), so call it from async code through
asyncio.to_thread().

Run:  python -m tools.node_dispatch probe
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, db, mailbox  # noqa: E402

ACTOR = "node_dispatch"
MAX_COMMAND_CHARS = 256
MAX_LOG_ARGS = 8
MAX_ERROR_CHARS = 500

# fullmatch only, explicit [0-9a-f] classes: `\d` would accept unicode digits
# and `$` would accept a trailing newline.
TASK_ID_RE = re.compile(r"task-[0-9a-f]{8}")
SESSION_ID_RE = re.compile(r"[0-9a-f]{8}")
LETTER_ID_RE = re.compile(r"[0-9]{1,12}")
BRANCH_RE = re.compile(r"agent/[a-z_]+-task-[0-9a-f]{8}")
# A role or session name that becomes part of a mailbox path. No dot, no slash.
_SAFE_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
_CALLER_RE = re.compile(r"[0-9A-Fa-f:.]{1,45}")

# Same wait relay_mcp_server.spawn_c_level uses before dismissing Claude
# Code's "new MCP servers found" screen in a pane nobody is watching.
SPAWN_PROMPT_DELAY_S = float(os.environ.get("NODE_DISPATCH_SPAWN_PROMPT_DELAY_S", "12"))
SPAWN_SCRIPT_TIMEOUT_S = 120
GIT_PUSH_TIMEOUT_S = 120


class Refusal(Exception):
    """A precondition or argument check failed. Nothing ran. Exit 2."""


class Failure(Exception):
    """The verb ran and did not succeed. Exit 1."""


def _show(value: object) -> str:
    return repr(str(value)[:64])


def _self_host() -> str:
    return config.self_host()


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _os_name() -> str:
    if sys.platform == "darwin":
        return "darwin"
    return "windows" if _is_windows() else "linux"


def _caller() -> str | None:
    """Caller address from sshd's SSH_CLIENT ("<ip> <port> <server port>")."""
    parts = os.environ.get("SSH_CLIENT", "").split()
    ip = parts[0] if parts else ""
    return ip if _CALLER_RE.fullmatch(ip) else None


def _pid_is_alive(pid: object) -> bool:
    """kill(pid, 0). PermissionError means the process exists, so alive.

    worker_reap._pid_alive reads PermissionError as dead; that is right for a
    reaper that must never signal a stranger and wrong for a liveness answer.
    """
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _task_on_this_host(task_id: str, *, allow_null_host: bool = False) -> dict:
    task = db.get_task(task_id)
    if not task:
        raise Refusal(f"no such task {task_id}")
    here = _self_host()
    task_host = task.get("host")
    if task_host != here and not (allow_null_host and task_host is None):
        raise Refusal(f"task {task_id} is on host {task_host!r}, this host is {here!r}")
    return task


def _slim_task(task_id: str) -> dict:
    row = db.get_task(task_id) or {}
    return {k: row.get(k) for k in ("id", "status", "pid", "branch")}


def _worktrees_root() -> Path:
    return Path(config.host(_self_host()).get("worktrees") or ROOT / "worktrees")


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

def _ram_free_gb() -> float | None:
    try:
        if sys.platform.startswith("linux"):
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemAvailable:"):
                    return round(int(line.split()[1]) / 1024 / 1024, 1)  # kB
        elif sys.platform == "darwin":
            out = subprocess.run(["vm_stat"], capture_output=True, text=True,
                                 timeout=10).stdout
            page = int(re.search(r"page size of (\d+) bytes", out).group(1))
            pages = sum(int(re.search(rf"Pages {name}:\s+(\d+)\.", out).group(1))
                        for name in ("free", "inactive", "speculative"))
            return round(pages * page / 1024 ** 3, 1)
    except Exception:
        return None
    return None


def _git_version() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return (r.stdout.strip() or None) if r.returncode == 0 else None


def _running_workers(host: str) -> int:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT pid FROM tasks WHERE host=? AND status='in_progress'", (host,)
        ).fetchall()
    if _is_windows():  # no liveness check until W3.3
        return len(rows)
    return sum(1 for r in rows if _pid_is_alive(r["pid"]))


def _cpu_facts() -> tuple[int | None, float | None]:
    """(cpus, load_per_core) for the router (PLAN-auto-dispatch H1).

    load_per_core is the 1-minute loadavg over the core count, 2 places. None
    on Windows (no loadavg) or on any error; a probe never fails over a load
    reading. Load per core, not raw load, so a 4-core and a 16-core box rank
    on the same scale.
    """
    try:
        cpus = os.cpu_count()
    except Exception:
        return None, None
    if not cpus or _is_windows():
        return cpus or None, None
    try:
        return cpus, round(os.getloadavg()[0] / cpus, 2)
    except Exception:
        return cpus, None


def _installed_runners() -> list[str]:
    return sorted(n for n in ("claude", "codex", "agy") if shutil.which(n))


def verb_probe() -> dict:
    host = _self_host()
    cpus, load_per_core = _cpu_facts()
    facts = {
        "host": host,
        "os": _os_name(),
        "agents_root": str(ROOT),
        "free_gb": round(shutil.disk_usage(ROOT).free / 1024 ** 3, 1),
        "ram_free_gb": _ram_free_gb(),
        "running": _running_workers(host),
        "version": _git_version(),
        "cpus": cpus,
        "load_per_core": load_per_core,
        "runners": _installed_runners(),
    }
    # Probe fields only. `status` is left alone on purpose: it is the join
    # state machine's (pending_identity -> online), not a measurement.
    db.upsert_host(
        host, probed_at=db.now_iso(), free_gb=facts["free_gb"],
        ram_free_gb=facts["ram_free_gb"], running=facts["running"],
        version=facts["version"], cpus=facts["cpus"],
        load_per_core=facts["load_per_core"], runners=facts["runners"],
    )
    return facts


# ---------------------------------------------------------------------------
# workers
# ---------------------------------------------------------------------------

def verb_pid_alive(task_id: str) -> dict:
    if _is_windows():
        raise Refusal("pid_alive is not supported on windows until W3.3")
    task = _task_on_this_host(task_id)
    pid = task.get("pid")
    return {"task_id": task_id, "pid": pid, "alive": _pid_is_alive(pid)}


def verb_spawn_worker(task_id: str) -> dict:
    task = _task_on_this_host(task_id, allow_null_host=True)
    if task["status"] != "pending":
        raise Refusal(f"task {task_id} is {task['status']}, spawn_worker needs pending")
    from tools import delegate
    asyncio.run(delegate.delegate_task(task_id, host=_self_host()))
    row = _slim_task(task_id)
    # delegate_task returns normally for a spawn it queued or blocked
    # (disk floor, blocked_host, conflict); only in_progress means a worker.
    if row["status"] != "in_progress":
        raise Failure(f"task {task_id} is {row['status']} after spawn, not in_progress")
    return row


def verb_kill_worker(task_id: str) -> dict:
    _task_on_this_host(task_id)
    from tools import worker_reap
    result = worker_reap.close_dev(
        task_id, reason=f"node_dispatch kill_worker from {_caller() or 'local'}"
    )
    if result.get("refused"):
        raise Refusal(f"close_dev refused: {result['refused']}")
    return result


def verb_publish_branch(task_id: str) -> dict:
    task = _task_on_this_host(task_id)
    if task["status"] != "review":
        raise Refusal(f"task {task_id} is {task['status']}, publish_branch needs review")
    branch = task.get("branch") or ""
    if not BRANCH_RE.fullmatch(branch) or not branch.endswith(f"-{task_id}"):
        raise Refusal(f"task branch {_show(branch)} is not this task's agent branch")
    if not task.get("worktree"):
        raise Refusal(f"task {task_id} has no worktree")
    worktree = Path(task["worktree"]).resolve()
    if _worktrees_root().resolve() not in worktree.parents:
        raise Refusal(f"worktree {_show(worktree)} is outside the worktrees root")
    if not worktree.is_dir():
        raise Refusal(f"worktree {_show(worktree)} does not exist")
    # Never the base branch (BRANCH_RE forces agent/...), never --force.
    r = subprocess.run(
        ["git", "push", "origin", branch], cwd=str(worktree),
        capture_output=True, text=True, timeout=GIT_PUSH_TIMEOUT_S,
        stdin=subprocess.DEVNULL, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if r.returncode != 0:
        raise Failure(f"git push exit {r.returncode}: "
                      f"{(r.stderr or r.stdout).strip()[-300:]}")
    return {"task_id": task_id, "branch": branch, "pushed": True}


# ---------------------------------------------------------------------------
# C-level sessions
# ---------------------------------------------------------------------------

def _start_clevel_iterm(role: str, resume_sid: str | None) -> dict:
    """Mac: the launcher runners/mac_agent.do_spawn already uses, plus --resume
    (both scripts translate it to `claude -r <uuid>` or refuse)."""
    script = ROOT / "scripts" / ("spawn-cto.sh" if role == "cto" else "spawn-cxo.sh")
    if not script.exists():
        raise Failure(f"missing {script.name}")
    cmd = ["bash", str(script)] + ([] if role == "cto" else ["--role", role])
    if resume_sid:
        cmd += ["--resume", resume_sid]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=SPAWN_SCRIPT_TIMEOUT_S, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        raise Failure(f"spawn failed: {e}")
    if r.returncode != 0:
        raise Failure(f"spawn exit {r.returncode}: "
                      f"{(r.stderr or r.stdout).strip()[:200]}")
    m = re.search(r"id=([0-9a-f]{8})", r.stdout)
    return {"role": role, "via": script.name,
            "session_id": m.group(1) if m else None, "resumed_from": resume_sid}


def _start_clevel_tmux(role: str, resume_sid: str | None) -> dict:
    """Linux: spawn-cxo.sh ends in osascript, so it cannot run here. Same
    command runners/relay_mcp_server.spawn_c_level runs on Contabo, in tmux."""
    from tools import session_status, tmux_session
    launcher = ROOT / "scripts" / "cxo-claude.sh"
    if not launcher.exists():
        raise Failure(f"missing {launcher.name}")
    claude_args = ""
    if resume_sid:
        # A short id must never reach `claude -r`: it opens a fresh session
        # and reports success (task-a98788d7).
        target = (session_status.resume_target(role, resume_sid) or "").strip()
        if not session_status.UUID_RE.fullmatch(target):
            raise Refusal(f"no resumable UUID for {role}-{resume_sid}")
        claude_args = f" -r {target}"
    sid = uuid.uuid4().hex[:8]
    name = f"{role}-{sid}"
    cmd = (f"export CXO_SESSION_ID={sid} && "
           f"exec bash {shlex.quote(str(launcher))} --role {role}{claude_args}")
    try:
        tmux_session.create(name, ROOT, cmd)
    except Exception as e:
        raise Failure(f"tmux spawn failed: {e}")
    dismissed = True
    try:
        time.sleep(SPAWN_PROMPT_DELAY_S)
        subprocess.run([tmux_session.tmux_bin(), "send-keys", "-t", name, "Escape"],
                       capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        dismissed = False
    return {"role": role, "via": "tmux", "session_id": sid, "tmux_session": name,
            "resumed_from": resume_sid, "prompt_dismissed": dismissed}


def verb_start_clevel(role: str, resume_sid: str | None) -> dict:
    if _is_windows():
        raise Refusal("start_clevel is not supported on windows until W3")
    if _os_name() == "darwin":
        return _start_clevel_iterm(role, resume_sid)
    return _start_clevel_tmux(role, resume_sid)


def _parse_start_clevel(args: list[str]) -> tuple[str, str | None]:
    if len(args) not in (1, 3):
        raise Refusal("start_clevel takes <role> [--resume <sid>]")
    if args[0] not in config.live_c_level_roles():
        raise Refusal(f"start_clevel: unknown role {_show(args[0])}")
    if len(args) == 1:
        return args[0], None
    if args[1] != "--resume":
        raise Refusal(f"start_clevel: unexpected argument {_show(args[1])}")
    if not SESSION_ID_RE.fullmatch(args[2]):
        raise Refusal(f"start_clevel: malformed session id {_show(args[2])}")
    return args[0], args[2]


# ---------------------------------------------------------------------------
# letters
# ---------------------------------------------------------------------------

def _session_live(name: str) -> bool:
    from tools import tmux_session
    try:
        return tmux_session.has_session(name)
    except OSError:  # no tmux on this box
        return False


def _write_letter(letter: dict) -> dict:
    from tools import send_to_cxo, session_name
    role = letter.get("to_role")
    if role not in config.live_c_level_roles():
        raise ValueError(f"to_role {role!r} is not a C-level role")
    sid = letter.get("to_session") or send_to_cxo._active_session_id(role)
    if not sid:
        raise ValueError(f"no active {role} session on this host")
    from_role = letter.get("from_role") or "hub"
    from_sid = letter.get("from_session") or "node-dispatch"
    for label, value in (("to_session", sid), ("from_role", from_role),
                         ("from_session", from_sid)):
        if not _SAFE_TOKEN_RE.fullmatch(str(value)):
            raise ValueError(f"unsafe {label} {_show(value)}")
    # A letter in a box nobody reads is lost while the hub says delivered.
    # runners/mac_agent.do_relay refuses the same way.
    if not _session_live(session_name.lock_basename(role, sid)):
        raise ValueError(f"no live session {role}-{sid} on this host")
    path = mailbox.send(role, sid, letter["body"], from_role, from_sid)
    if not path.is_file():
        raise ValueError(f"letter not on disk after write: {path}")
    try:  # best effort, never changes the outcome (same rule as send_to_cxo)
        send_to_cxo.attempt_wake(role, sid, from_role.upper())
    except Exception:
        pass
    return {"to": f"{role}-{sid}"}


def verb_deliver_letter(letter_id: str) -> dict:
    lid = int(letter_id)
    letter = db.get_letter(lid)
    if not letter:
        raise Refusal(f"no such letter {lid}")
    here = _self_host()
    if letter["to_host"] != here:
        raise Refusal(f"letter {lid} is for host {letter['to_host']!r}, this host is {here!r}")
    if letter["status"] == "delivered":
        return {"letter_id": lid, "already_delivered": True}
    try:
        where = _write_letter(letter)
        if not db.mark_letter_delivered(lid):  # a concurrent call won
            return {"letter_id": lid, "already_delivered": True}
    except Exception as e:
        db.record_letter_attempt(lid, f"{type(e).__name__}: {e}"[:MAX_ERROR_CHARS])
        raise Failure(f"letter {lid} not delivered: {e}")
    return {"letter_id": lid, "delivered": True, **where}


# ---------------------------------------------------------------------------
# Dispatch table -- the security core. An unknown verb is a refusal.
# ---------------------------------------------------------------------------

HANDLERS = {
    "probe": verb_probe,
    "pid_alive": verb_pid_alive,
    "spawn_worker": verb_spawn_worker,
    "kill_worker": verb_kill_worker,
    "start_clevel": verb_start_clevel,
    "deliver_letter": verb_deliver_letter,
    "publish_branch": verb_publish_branch,
}

# Exact argument patterns, in order. start_clevel has its own parser above.
_ARGSPEC = {
    "probe": (),
    "pid_alive": (TASK_ID_RE,),
    "spawn_worker": (TASK_ID_RE,),
    "kill_worker": (TASK_ID_RE,),
    "deliver_letter": (LETTER_ID_RE,),
    "publish_branch": (TASK_ID_RE,),
}
_TASK_VERBS = frozenset({"pid_alive", "spawn_worker", "kill_worker", "publish_branch"})


def _check_args(verb: str, args: list[str]) -> tuple:
    if verb == "start_clevel":
        return _parse_start_clevel(args)
    spec = _ARGSPEC[verb]
    if len(args) != len(spec):
        raise Refusal(f"{verb} takes {len(spec)} argument(s), got {len(args)}")
    for arg, pattern in zip(args, spec):
        if not pattern.fullmatch(arg):
            raise Refusal(f"{verb}: malformed argument {_show(arg)}")
    return tuple(args)


def _audit(verb, args: list, ok: bool, error: str | None, *,
           task_id: str | None = None, raw: str | None = None) -> None:
    payload = {
        "verb": verb,
        "args": [str(a)[:MAX_COMMAND_CHARS] for a in args[:MAX_LOG_ARGS]],
        "caller": _caller(),
        "ok": ok,
        "error": error[:MAX_ERROR_CHARS] if error else None,
    }
    if raw is not None:
        payload["raw"] = raw[:MAX_COMMAND_CHARS]
    try:
        with db.get_conn() as conn:
            db.log_event(conn, task_id, ACTOR, "dispatch", payload)
    except Exception as e:  # a lost audit row must not turn a spawn into a retry
        print(f"node_dispatch: audit write failed: {e}", file=sys.stderr)


def _run(verb: object, args: object) -> tuple[dict, int]:
    shown = verb[:64] if isinstance(verb, str) else None
    log_args = list(args) if isinstance(args, (list, tuple)) else []
    task_id = None
    try:
        if not isinstance(verb, str):
            raise Refusal("verb must be a string")
        if not isinstance(args, (list, tuple)) or not all(isinstance(a, str) for a in args):
            raise Refusal("args must be a list of strings")
        args = list(args)
        if verb not in HANDLERS:
            raise Refusal(f"unknown verb {_show(verb)}. Known: {', '.join(HANDLERS)}")
        parsed = _check_args(verb, args)
        if verb in _TASK_VERBS:
            task_id = args[0]
        out = {"ok": True, "verb": shown, "result": HANDLERS[verb](*parsed)}
        code = 0
    except Refusal as e:
        out, code = {"ok": False, "verb": shown, "error": str(e)}, 2
    except Failure as e:
        out, code = {"ok": False, "verb": shown, "error": str(e)}, 1
    except Exception as e:  # a backend that raised ran and failed
        out, code = {"ok": False, "verb": shown, "error": f"{type(e).__name__}: {e}"}, 1
    _audit(shown, log_args, out["ok"], out.get("error"), task_id=task_id)
    return out, code


def dispatch(verb: str, args: list[str]) -> dict:
    """In-process entry for W2.3: same dict the CLI prints as its JSON line."""
    return _run(verb, args)[0]


def parse_command(raw: str) -> list[str]:
    """SSH_ORIGINAL_COMMAND -> [verb, *args], or Refusal."""
    if not isinstance(raw, str) or not raw.strip():
        raise Refusal("empty command")
    if len(raw) > MAX_COMMAND_CHARS:
        raise Refusal(f"command longer than {MAX_COMMAND_CHARS} chars")
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):
        raise Refusal("control character (NUL, newline, tab, ...) in command")
    try:
        parts = shlex.split(raw)
    except ValueError as e:
        raise Refusal(f"cannot parse command: {e}")
    if not parts:
        raise Refusal("empty command")
    return parts


def run_command(raw: str) -> tuple[dict, int]:
    try:
        parts = parse_command(raw)
    except Refusal as e:
        _audit(None, [], False, str(e),
               raw=raw if isinstance(raw, str) else repr(raw))
        return {"ok": False, "verb": None, "error": str(e)}, 2
    return _run(parts[0], parts[1:])


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    raw = os.environ.get("SSH_ORIGINAL_COMMAND")
    if raw is None:
        raw = shlex.join(argv)
    # Exactly one JSON line on stdout: while a verb runs, fd 1 points at
    # stderr so nothing a backend or child prints can share the channel.
    sys.stdout.flush()
    saved_out, saved_in = os.dup(1), os.dup(0)
    devnull = os.open(os.devnull, os.O_RDONLY)
    try:
        os.dup2(2, 1)
        os.dup2(devnull, 0)
        out, code = run_command(raw)
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_out, 1)
        os.dup2(saved_in, 0)
        for fd in (saved_out, saved_in, devnull):
            os.close(fd)
    sys.stdout.write(json.dumps(out, ensure_ascii=True, default=str) + "\n")
    sys.stdout.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())
