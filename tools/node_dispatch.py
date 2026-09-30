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
import base64
import ctypes
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config, db, mailbox, proc  # noqa: E402

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


# Credentials a failing child can print (git echoes a remote URL with its
# token, an HTTP client its Authorization header). Every error string passes
# through here before it reaches the reply, the audit row or letters.last_error.
_SECRET_PATTERNS = (
    (re.compile(r"([A-Za-z][A-Za-z0-9+.-]*://)[^/\s@]+@"), r"\1***@"),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"), "***"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "***"),
    (re.compile(r"(?i)\b(bearer|token|basic)\s+[A-Za-z0-9._~+/=-]{16,}"), r"\1 ***"),
)


def _redact(text: str) -> str:
    for pattern, repl in _SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def _self_host() -> str:
    return config.self_host()


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _os_name() -> str:
    if _is_windows():
        return "windows"
    return "darwin" if sys.platform == "darwin" else "linux"


def _caller() -> str | None:
    """Caller address from sshd's SSH_CLIENT ("<ip> <port> <server port>")."""
    parts = os.environ.get("SSH_CLIENT", "").split()
    ip = parts[0] if parts else ""
    return ip if _CALLER_RE.fullmatch(ip) else None


def _pid_is_alive(pid: object) -> bool:
    """lib.proc.pid_alive (W3.1): the one liveness probe on every OS. On
    Windows `os.kill(pid, 0)` sends Ctrl-C instead of probing, so nothing in
    this file signals a pid. Access denied means the process exists, so alive.

    worker_reap._pid_alive reads PermissionError as dead; that is right for a
    reaper that must never signal a stranger and wrong for a liveness answer.
    """
    return proc.pid_alive(pid)  # a non-int, a bool and pid <= 0 are False there


def _task_on_this_host(task_id: str) -> dict:
    """The row, if the hub assigned it to this host. A NULL host is refused
    like any other host: every real spawn names its host first
    (delegate.mesh_spawn_worker), so a NULL row is one the hub never routed
    here (W2.7 F2, task-42fdcda7)."""
    task = db.get_task(task_id)
    if not task:
        raise Refusal(f"no such task {task_id}")
    here = _self_host()
    task_host = task.get("host")
    if task_host != here:
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

class _MemoryStatusEx(ctypes.Structure):
    """MEMORYSTATUSEX for GlobalMemoryStatusEx (64 bytes). Defined on every OS
    so a test can pin its layout without Windows."""
    _fields_ = [
        ("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32),
        ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


def _win_avail_phys_bytes() -> int | None:
    """Free physical RAM on Windows, or None when the call is not there
    (`ctypes.windll` is missing on every other OS)."""
    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return int(status.ullAvailPhys)


def _ram_free_gb() -> float | None:
    try:
        if _is_windows():
            avail = _win_avail_phys_bytes()
            return None if avail is None else round(avail / 1024 ** 3, 1)
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


# W4.4 (task-49f70bc6): `provides` measured on the node, never read from
# hosts.yaml. Each detector answers one capability with a bool. Bounded: every
# child has an argv list, no shell, no stdin and PROBE_CHILD_TIMEOUT_S, and a
# detector that raises (or whose child hangs) is left out of the list and named
# once in `probe_errors`; nothing here can fail the probe.
#
# A signed-in runner is read off the credential file's existence and size from
# os.stat. The file is never opened, read, hashed or printed
# (tests/test_w44_probe_provides.py pins that with an open() that explodes).
PROBE_CHILD_TIMEOUT_S = 5
_NODE_MIN_MAJOR = 20
_NODE_VERSION_RE = re.compile(r"v(\d{1,4})\.")


def _is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _file_has_content(path: Path) -> bool:
    """Exists, is a regular file, size > 0. os.stat only: never opens `path`."""
    try:
        st = path.stat()
    except OSError:
        return False
    return stat.S_ISREG(st.st_mode) and st.st_size > 0


def _windows_env_dirs(*names: str) -> list[Path]:
    """Each named env var that is set and non-empty, as a Path. An unset one is
    skipped: Path('') / 'x' would be a relative path under the working dir."""
    return [Path(v) for v in (os.environ.get(n) for n in names) if v]


def _chrome_candidates() -> list[Path]:
    home = Path.home()
    if _is_windows():
        tails = (Path("Google/Chrome/Application/chrome.exe"),
                 Path("Chromium/Application/chrome.exe"))
        return [d / t for d in _windows_env_dirs("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")
                for t in tails]
    if _os_name() == "darwin":
        apps = (Path("Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("Chromium.app/Contents/MacOS/Chromium"))
        return [root / a for root in (Path("/Applications"), home / "Applications") for a in apps]
    named = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")
    found = [Path(p) for p in (shutil.which(n) for n in named) if p]
    return found + [Path("/opt/google/chrome/chrome"), Path("/snap/bin/chromium")]


def _has_chrome() -> bool:
    return any(_is_file(p) for p in _chrome_candidates())


def _child_exit(argv: list[str], want_stdout: bool = False) -> tuple[int, str]:
    """(exit code, stdout) of a bounded child. stderr and stdin are /dev/null; with
    `want_stdout` False stdout is too, so no pipe stays open if a grandchild
    outlives the timeout."""
    r = subprocess.run(
        argv, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE if want_stdout else subprocess.DEVNULL,
        text=True, timeout=PROBE_CHILD_TIMEOUT_S,
    )
    return r.returncode, (r.stdout or "") if want_stdout else ""


def _has_ffmpeg() -> bool:
    exe = shutil.which("ffmpeg")
    return bool(exe) and _child_exit([exe, "-version"])[0] == 0


def _has_gpu() -> bool:
    """An NVIDIA GPU: nvidia-smi exits 0 and lists one. A driver with no device is
    not a GPU. macOS Metal is not reported (the task says only nvidia)."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return False
    code, out = _child_exit([exe, "-L"], want_stdout=True)
    return code == 0 and any(ln.startswith("GPU ") for ln in out.splitlines())


def _has_node20() -> bool:
    exe = shutil.which("node")
    if not exe:
        return False
    code, out = _child_exit([exe, "--version"], want_stdout=True)
    m = _NODE_VERSION_RE.match(out.strip()) if code == 0 else None
    return bool(m) and int(m.group(1)) >= _NODE_MIN_MAJOR


def _playwright_browsers_dir() -> Path | None:
    override = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if override:
        # "0" makes Playwright keep browsers inside node_modules: no fixed folder.
        return None if override == "0" else Path(override)
    if _is_windows():
        base = _windows_env_dirs("LOCALAPPDATA")
        return base[0] / "ms-playwright" if base else None
    if _os_name() == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def _has_playwright_chromium() -> bool:
    """The browsers folder holds a chromium build (`chromium-<n>`). A folder with
    only firefox/webkit in it does not provide playwright_chromium."""
    folder = _playwright_browsers_dir()
    try:
        return folder is not None and any(folder.glob("chromium*"))
    except OSError:
        return False


def _claude_credentials() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / ".credentials.json"


# macOS keeps the Claude Code login in the Keychain, not in .credentials.json.
# Signed in is read without the secret, two ways, in this order:
#   1. `claude auth status --json`: the `loggedIn` boolean only. Its output also
#      carries an email and an org name, so it is parsed in place and only the
#      boolean leaves this function; nothing is logged or returned from it.
#   2. the Keychain item's presence: `security find-generic-password -s <service>`
#      with no -w and no -g (either would print the secret). Attributes only;
#      the exit code is the whole answer, stdout and stderr go to /dev/null.
# tests/test_mesh_followups.py fails if a -w or -g ever reaches an argv here.
_SECURITY_BIN = "/usr/bin/security"
_CLAUDE_KEYCHAIN_SERVICE = "Claude Code-credentials"


def _claude_logged_in_per_cli() -> bool | None:
    """`loggedIn` from `claude auth status --json`; None when the CLI cannot
    answer (not on PATH, hung, failed to start, output that is not that JSON)."""
    exe = shutil.which("claude")
    if not exe:
        return None
    try:
        _, out = _child_exit([exe, "auth", "status", "--json"], want_stdout=True)
        logged_in = json.loads(out).get("loggedIn")
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return None
    return logged_in if isinstance(logged_in, bool) else None


def _claude_signed_in() -> bool:
    if _os_name() != "darwin":
        return _file_has_content(_claude_credentials())
    per_cli = _claude_logged_in_per_cli()
    if per_cli is not None:
        return per_cli
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        # A custom config dir may keep its login under another Keychain item;
        # the default service could then answer for a different login.
        return _file_has_content(_claude_credentials())
    return _child_exit([_SECURITY_BIN, "find-generic-password", "-s", _CLAUDE_KEYCHAIN_SERVICE])[0] == 0


def _codex_credentials() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "auth.json"


def _agy_credentials() -> Path:
    return Path.home() / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"


# In the order the probe reports them. `os` is handled apart (it always answers).
_PROVIDES_DETECTORS = (
    ("chrome", _has_chrome),
    ("ffmpeg", _has_ffmpeg),
    ("gpu", _has_gpu),
    ("node20", _has_node20),
    ("playwright_chromium", _has_playwright_chromium),
    ("runner_claude", _claude_signed_in),
    ("runner_codex", lambda: _file_has_content(_codex_credentials())),
    ("runner_agy", lambda: _file_has_content(_agy_credentials())),
)


def _measure_provides() -> tuple[list[str], list[str]]:
    """(provides_measured, probe_errors). The OS family is always first:
    `macos`, `linux` or `windows`. An error entry is `<name>: <ExceptionType>`
    and nothing else, so a path or a message cannot leak through it."""
    os_family = {"darwin": "macos"}.get(_os_name(), _os_name())
    measured, errors = [os_family], []
    for name, detect in _PROVIDES_DETECTORS:
        try:
            if detect():
                measured.append(name)
        except Exception as e:  # incl. subprocess.TimeoutExpired: absent, not a failed probe
            errors.append(f"{name}: {type(e).__name__}")
    return measured, errors


def verb_probe() -> dict:
    host = _self_host()
    cpus, load_per_core = _cpu_facts()
    provides_measured, probe_errors = _measure_provides()
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
        # W4.4: measured here, not from hosts.yaml. Reported only; it is not
        # written to the `hosts` row (the router's merge is a separate change).
        "provides_measured": provides_measured,
        "probe_errors": probe_errors,
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
    task = _task_on_this_host(task_id)
    pid = task.get("pid")
    return {"task_id": task_id, "pid": pid, "alive": _pid_is_alive(pid)}


def _json_list(value: object) -> list:
    try:
        out = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return out if isinstance(out, list) else []


def _windows_spawn_gate(task: dict) -> None:
    """The checks delegate_task runs before a spawn, read-only, for the win32
    path that does not call delegate_task (W2.7, task-42fdcda7). The hub's
    delegate_task ran them and took the path locks before it dispatched, so on
    the normal path they pass. They stop a caller holding the org_dispatch key
    from starting a pending row the hub never gated: one with an unfinished
    dependency, whose touches overlap a task already in flight, or on a box
    below the disk floor (F3b). Locks stay the hub's to take; nothing here
    writes. The row's host is checked before this, by _task_on_this_host."""
    tid = task["id"]
    deps =[d for d in _json_list(task.get("depends_on")) if isinstance(d, str)]
    unmet = db.unmet_dependencies(deps) if deps else []
    if unmet:
        raise Refusal(f"task {tid} has unfinished dependencies: "
                      + ", ".join(f"{u['id']}({u['status']})" for u in unmet[:5]))
    touches = [p for p in _json_list(task.get("touches")) if isinstance(p, str)]
    conflicts = db.find_conflicts(task["project"], touches, exclude_task=tid) if touches else []
    if conflicts:
        raise Refusal(f"task {tid} overlaps tasks in flight: "
                      + ", ".join(str(c.get("task_id")) for c in conflicts[:5]))
    _windows_disk_floor_gate(task)


def _nearest_existing(path: Path) -> Path:
    """`path`, or its closest ancestor that exists: the worktrees root is made by
    the launcher, so on a first spawn it is not there yet and disk_usage raises.
    The ancestor is on the same drive."""
    for candidate in (path, *path.parents):
        if candidate.exists():
            return candidate
    return path


def _windows_disk_floor_gate(task: dict) -> None:
    """W2.7 F3b: the disk floor delegate_task applies before a spawn, re-checked
    here because the win32 path never calls delegate_task. Same reading seam
    (delegate._free_gb), same floor (delegate._disk_orange_floor_gb, the
    `gauge.orange` key of config/storage-policy.yaml), same strict `<`, same
    scope rule (delegate._scope_applies "disk_floor"). Measured on the drive
    that will hold the worktree. A refusal leaves the row pending: delegate's
    queue-for-disk is the hub's to do. The browser cap stays the hub's too.
    A free-space read that fails is a refusal, not a pass: this is a guard."""
    from tools import delegate
    if not delegate._scope_applies("disk_floor", task.get("owner_cto")):
        return
    where = _nearest_existing(_worktrees_root())
    floor_gb = delegate._disk_orange_floor_gb()
    try:
        free_gb = delegate._free_gb(str(where))
    except OSError as e:
        raise Refusal(f"spawn_worker: cannot read free disk on {_show(where)}: {type(e).__name__}")
    if free_gb < floor_gb:
        raise Refusal(f"disk red on {_self_host()}: {free_gb:.1f} GB free < {floor_gb:.1f} GB "
                      f"floor (storage-policy gauge.orange), spawn refused")


def verb_spawn_worker(task_id: str) -> dict:
    task = _task_on_this_host(task_id)
    if task["status"] != "pending":
        raise Refusal(f"task {task_id} is {task['status']}, spawn_worker needs pending")
    if _is_windows():
        _windows_spawn_gate(task)
        _spawn_worker_windows(task)
    else:
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
           f"exec bash {shlex.quote(str(launcher))} --role {shlex.quote(role)}{claude_args}")
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


# Everything that is formatted into a PowerShell string below is checked against
# this first. It is deliberately narrow: no quote, backtick, dollar sign,
# semicolon, ampersand, parenthesis or control character, so a value cannot end
# the single-quoted literal it sits in. A repo path outside it is refused, not
# escaped.
_PS_SAFE_RE = re.compile(r"[A-Za-z0-9_.:\\/ -]{1,300}")
# The same set plus the double quote that wraps the launcher path in the
# scheduled task's argument string.
_PS_ARGUMENT_RE = re.compile(r'[A-Za-z0-9_.:\\/ "-]{1,600}')
_SCHTASK_START_WAIT_S = 20
_SCHTASK_TIMEOUT_S = 90


def _ps_safe(label: str, value: object) -> str:
    if not isinstance(value, str) or not _PS_SAFE_RE.fullmatch(value):
        raise Refusal(f"{label} {_show(value)} is not safe to hand to PowerShell")
    return value


def _run_powershell(script: str, timeout: float = _SCHTASK_TIMEOUT_S) -> subprocess.CompletedProcess:
    """One powershell.exe call, argv list. The script travels as -EncodedCommand
    (base64 of UTF-16LE), so no shell or command line ever re-parses it."""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-EncodedCommand", encoded],
        capture_output=True, text=True, timeout=timeout,
        stdin=subprocess.DEVNULL,
    )


def _one_shot_task_script(task_name: str, argument: str) -> str:
    """PowerShell for the pattern windows/spawn-worker.ps1 uses: an interactive
    one-shot scheduled task, so the process lands on the logged-in desktop
    (session 1) and not in the session 0 sshd gives us. Register, run, wait
    until it is Running, unregister (the running process is kept, as for
    spawn-worker's codex/agy launch). Both values are validated here again,
    whatever the caller did."""
    _ps_safe("task name", task_name)
    if not _PS_ARGUMENT_RE.fullmatch(argument):
        raise Refusal("task argument has a character PowerShell could act on")
    name = f"'{task_name}'"
    return (
        "$ErrorActionPreference = 'Stop'; "
        "$me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name; "
        f"$act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '{argument}'; "
        "$pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited; "
        "$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Seconds 0); "
        f"Register-ScheduledTask -TaskName {name} -Action $act -Principal $pri "
        "-Settings $set -Force | Out-Null; "
        # try/finally (W2.7): with 'Stop', a Start-ScheduledTask that throws
        # would otherwise leave the task registered for anyone to re-run.
        f"try {{ Start-ScheduledTask -TaskName {name}; "
        f"$deadline = (Get-Date).AddSeconds({_SCHTASK_START_WAIT_S}); "
        f"while ((Get-Date) -lt $deadline -and (Get-ScheduledTask -TaskName {name}).State "
        "-ne 'Running') { Start-Sleep -Milliseconds 500 }; "
        f"$state = [string](Get-ScheduledTask -TaskName {name}).State }} "
        f"finally {{ Unregister-ScheduledTask -TaskName {name} -Confirm:$false "
        "-ErrorAction SilentlyContinue }; "
        "if ($state -ne 'Running') { throw \"task state is $state, not Running\" }; "
        "Write-Output \"STARTED $state\""
    )


def _start_clevel_schtask(role: str, resume_sid: str | None) -> dict:
    """Windows: windows/cxo-claude.ps1 (W3.2) from a one-shot interactive
    scheduled task. Same result shape as _start_clevel_tmux.

    The id is passed as `-Session <sid>` because that is the only way the
    launcher takes one, and it is how the caller learns which session it started.
    That is the launcher's ephemeral shape: it does not write the
    `<role>-active` pointer, so a letter to this session names it by
    `to_session`; a role-only letter finds nothing until the pointer exists."""
    from tools import session_status
    launcher = ROOT / "windows" / "cxo-claude.ps1"
    if not launcher.exists():
        raise Failure(f"missing {launcher.name}")
    if role not in config.live_c_level_roles():
        raise Refusal(f"start_clevel: unknown role {_show(role)}")
    resume_args = ""
    if resume_sid:
        # Same rule as the tmux path: a short id must never reach `claude`.
        if not SESSION_ID_RE.fullmatch(resume_sid):
            raise Refusal(f"start_clevel: malformed session id {_show(resume_sid)}")
        target = (session_status.resume_target(role, resume_sid) or "").strip()
        if not session_status.UUID_RE.fullmatch(target):
            raise Refusal(f"no resumable UUID for {role}-{resume_sid}")
        # `--resume`, not `-r`: PowerShell would bind `-r` as an abbreviation of
        # -Role / -RemainingArgs. cxo-claude.ps1 adds --fork-session for it.
        resume_args = f" --resume {target}"
    sid = uuid.uuid4().hex[:8]
    task_name = f"mooniex-cxo-{role}-{sid}"
    argument = (f'-NoProfile -ExecutionPolicy Bypass -File "{_ps_safe("launcher path", str(launcher))}" '
                f"-Role {role} -Session {sid}{resume_args}")
    script = _one_shot_task_script(task_name, argument)
    try:
        r = _run_powershell(script)
    except (OSError, subprocess.SubprocessError) as e:
        raise Failure(f"scheduled task launch failed: {e}")
    if r.returncode != 0 or "STARTED" not in (r.stdout or ""):
        raise Failure(f"scheduled task exit {r.returncode}: "
                      f"{(r.stderr or r.stdout).strip()[:200]}")
    return {"role": role, "via": "schtask", "session_id": sid, "task_name": task_name,
            "resumed_from": resume_sid}


# ---------------------------------------------------------------------------
# spawn_worker on Windows
# ---------------------------------------------------------------------------
#
# delegate.delegate_task cannot start a worker on Windows: _spawn_local needs
# tmux and fails the row, and the launcher transport is linux-only. The hub has
# already done delegate_task's gating (dependencies, path locks, browser cap,
# disk floor) before it sent this verb, so what is left here is what
# delegate._spawn_remote does for a Windows host: render the launch arguments,
# run windows/spawn-worker.ps1, read its output, write the row. That script makes
# the one-shot interactive scheduled task itself (session 1), so nothing here
# starts claude directly.
#
# Every value below reaches PowerShell as a single-quoted literal, and a
# single-quoted literal is only ever ended by a quote. Each value is still held
# to its own allow-list first (the same rule as _ps_safe): a refusal, never an
# escape.
_PS_TOKEN_RE = re.compile(r"[A-Za-z0-9_.-]{1,64}")
_PS_REF_RE = re.compile(r"[A-Za-z0-9._/-]{1,100}")
_PS_REPO_URL_RE = re.compile(r"git@[A-Za-z0-9.-]{1,64}:[A-Za-z0-9._-]{1,64}/[A-Za-z0-9._-]{1,100}")
_PS_CLAUDE_ARGS_RE = re.compile(r"[A-Za-z0-9_.,: -]{0,600}")
_PS_SESSION_NAME_RE = re.compile(r"[A-Za-z0-9_.#() -]{1,120}")
_PS_MODEL_RE = re.compile(r"[A-Za-z0-9_.:/-]{1,100}")
_WORKER_RUNNERS = ("claude", "codex", "agy")
_SPAWN_WORKER_TIMEOUT_S = 300  # delegate.REMOTE_LAUNCH_TIMEOUT_S: a clone can be slow

# spawn-worker.ps1 parameter -> the pattern its value must fullmatch, in the
# order they are passed. RunnerModel is added only when there is one.
_SPAWN_PARAMS = (
    ("Task", TASK_ID_RE), ("Project", _PS_TOKEN_RE), ("Role", _PS_TOKEN_RE),
    ("Branch", BRANCH_RE), ("Base", _PS_REF_RE), ("RepoUrl", _PS_REPO_URL_RE),
    ("RepoPath", _PS_SAFE_RE), ("WorktreeRoot", _PS_SAFE_RE),
    ("ClaudeArgs", _PS_CLAUDE_ARGS_RE), ("Model", _PS_TOKEN_RE),
    ("Effort", _PS_TOKEN_RE), ("SessionName", _PS_SESSION_NAME_RE),
    ("TaskFile", _PS_SAFE_RE), ("Runner", _PS_TOKEN_RE),
    ("RunnerModel", _PS_MODEL_RE), ("AgentsRoot", _PS_SAFE_RE),
)


def _spawn_worker_script(launcher: str, values: dict) -> str:
    """The PowerShell that runs spawn-worker.ps1 with `values`. Refuses, before
    it returns any text, a value that is not a string or is outside its pattern.
    `exit $LASTEXITCODE` hands the launcher's own exit code to the caller."""
    if not _PS_SAFE_RE.fullmatch(launcher):
        raise Refusal(f"launcher path {_show(launcher)} is not safe to hand to PowerShell")
    if values.get("Runner") not in _WORKER_RUNNERS:
        raise Refusal(f"runner {_show(values.get('Runner'))} is not one of {list(_WORKER_RUNNERS)}")
    parts = [f"& '{launcher}'"]
    for name, pattern in _SPAWN_PARAMS:
        if name == "RunnerModel" and not values.get(name):
            continue
        value = values.get(name)
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise Refusal(f"{name} {_show(value)} is not safe to hand to PowerShell")
        parts.append(f"-{name} '{value}'")
    return " ".join(parts) + "; exit $LASTEXITCODE"


def _spawn_worker_values(task: dict) -> dict:
    """What spawn-worker.ps1 needs for `task` on this Windows host, from the same
    delegate helpers _spawn_remote uses (no second copy of the branch, argument
    and URL rules). Nothing is run; a config problem is a refusal."""
    from tools import delegate
    host = _self_host()
    role, project_key = task["role"], task["project"]
    try:
        host_cfg = config.host(host)
        if host_cfg.get("os") != "windows":
            raise ValueError(f"host {host!r} is os={host_cfg.get('os')!r}, not windows")
        runner = (task.get("runner") or "claude").strip().lower()
        delegate._validate_runner(runner, host)
        proj = config.get_project(project_key)
        role_cfg = config.role(role)
        repo_url = delegate._ssh_remote_url(proj.get("remote") or "")
        repo_path = config.project_path_for_host(project_key, host)
        claude_args = delegate._render_remote_runner_args(role, host, runner)
        branch = delegate._runner_branch_name(runner, role, task["id"])
        worktree_root = host_cfg["worktrees"]
    except (ValueError, KeyError) as e:
        raise Refusal(f"spawn_worker: {e}")
    # The title is free text a person typed. Keep the readable part and cut the
    # rest; worker_session_name would only add "..." past 40 characters.
    title = re.sub(r"[^A-Za-z0-9 ._-]", "", task.get("title") or "")[:40].strip()
    return {
        "Task": task["id"], "Project": project_key, "Role": role, "Branch": branch,
        "Base": proj.get("default_branch"), "RepoUrl": repo_url, "RepoPath": repo_path,
        "WorktreeRoot": worktree_root,
        "ClaudeArgs": claude_args,
        "Model": role_cfg.get("model") or "claude-sonnet-5-5",
        "Effort": role_cfg.get("effort") or "high",
        "SessionName": config.worker_session_name(host, role, task["id"], title),
        "Runner": runner,
        "RunnerModel": str(task.get("runner_model") or ""),
        "AgentsRoot": str(ROOT),
        "_project": proj,
    }


def _spawn_worker_windows(task: dict) -> None:
    """Start `task`'s worker on this Windows host and write the row the way
    delegate._spawn_remote writes it: in_progress with the pid, blocked_host
    when the launcher says GitHub is unreachable, conflict when it refuses,
    failed for anything else. The caller reads the row back."""
    from runners.worker_init import _build_prompt
    task_id = task["id"]
    launcher = ROOT / "windows" / "spawn-worker.ps1"
    if not launcher.exists():
        raise Failure(f"missing {launcher.name}")
    values = _spawn_worker_values(task)
    proj = values.pop("_project")
    worktree = f"{values['WorktreeRoot']}\\{values['Project']}__{values['Role']}__{task_id}"
    task_file = ROOT / "state" / f".remote-task-{task_id}.md"
    values["TaskFile"] = str(task_file)
    # Built, and so validated, before the brief is written or anything runs.
    script = _spawn_worker_script(str(launcher), values)
    prompt = _build_prompt({**task, "branch": values["Branch"]}, proj, worktree)
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(prompt, encoding="utf-8")
    db.set_fields(task_id, spawned_at=db.now_iso(), host=_self_host(), actor=ACTOR)
    try:
        r = _run_powershell(script, timeout=_SPAWN_WORKER_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as e:
        db.update_status(task_id, "failed", delegate_log=f"spawn failed: {e}", actor=ACTOR)
        return
    finally:
        task_file.unlink(missing_ok=True)
    lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
    route = next((ln for ln in lines if ln.startswith("GITHUB_SSH_ROUTE=unreachable")), None)
    if route is not None:
        # The launcher can print a pid even with a dead route: it must not stay.
        note = ""
        if lines and lines[-1].isdigit():
            try:
                k = subprocess.run(["taskkill", "/PID", lines[-1], "/T", "/F"],
                                   capture_output=True, text=True, timeout=30,
                                   stdin=subprocess.DEVNULL)
                note = f"; killed leaked pid {lines[-1]} (exit {k.returncode})"
            except (OSError, subprocess.SubprocessError) as e:
                note = f"; could not kill leaked pid {lines[-1]}: {str(e)[:100]}"
        db.update_status(task_id, "blocked_host", actor=ACTOR,
                         delegate_log=f"{route} -- git route from {_self_host()} dead{note}")
        return
    refused = next((ln for ln in lines if ln.startswith("SPAWN_REFUSED=")), None)
    if refused is not None:
        db.update_status(task_id, "conflict", actor=ACTOR,
                         delegate_log=f"spawn refused ({_self_host()}): "
                                      f"{refused[len('SPAWN_REFUSED='):]}")
        return
    if r.returncode != 0 or not lines:
        detail = _redact((r.stderr or r.stdout or "").strip())[:1000]
        db.update_status(task_id, "failed", actor=ACTOR,
                         delegate_log=f"spawn ({_self_host()}) failed: {detail}")
        return
    if not lines[-1].isdigit():
        db.update_status(task_id, "failed", actor=ACTOR,
                         delegate_log=f"spawn ({_self_host()}): unparseable pid line {lines[-1][:100]!r}")
        return
    db.update_status(
        task_id, "in_progress", pid=int(lines[-1]), host=_self_host(), worktree=worktree,
        branch=values["Branch"], assigned_agent=values["Role"], runner=values["Runner"],
        actor=ACTOR,
    )


# W2.7 F10 (task-42fdcda7, CTO decision): each session is a paid Claude
# session, so a looping or prompt-injected caller must not be able to start
# them without end. At most this many live sessions of one role per host; the
# next start_clevel is refused (exit 2). A session counts while
# state/locks/<role>-<sid>.lock holds a live pid (every launcher writes it:
# cxo-claude.sh, spawn-cto.sh, cxo-claude.ps1). The start itself holds a
# `locks` row for the role, so two calls cannot both count 2 and both launch.
# The launcher writes its lock file a few seconds after start_clevel returns
# (iTerm tab, tmux session, scheduled task), so a start that succeeds keeps the
# row for CLEVEL_LAUNCH_GRACE_S: a burst of starts cannot each count before the
# last one's lock exists. A refused or failed start frees the row at once.
MAX_LIVE_CLEVEL_PER_ROLE = 3
CLEVEL_START_CLAIM_TTL_S = 300  # above the slowest launch (script 120 s + prompt delay)
CLEVEL_LAUNCH_GRACE_S = 60


def _live_clevel_count(role: str) -> int:
    from tools import send_to_cxo
    prefix = f"{role}-"
    try:
        locks = [p for p in Path(send_to_cxo.LOCKS_DIR).glob("*.lock")
                 if p.stem.startswith(prefix) and SESSION_ID_RE.fullmatch(p.stem[len(prefix):])]
    except OSError:
        return 0
    live = 0
    for lock in locks:
        try:
            pid = int(lock.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if _pid_is_alive(pid):
            live += 1
    return live


def verb_start_clevel(role: str, resume_sid: str | None) -> dict:
    host = _self_host()
    key = f"clevel:{host}:{role}:start"
    token = _claim(key, CLEVEL_START_CLAIM_TTL_S)
    if token is None:
        raise Refusal(f"start_clevel: another {role} start is in progress on {host} "
                      f"(one start per role per {CLEVEL_LAUNCH_GRACE_S} s); try again shortly")
    try:
        live = _live_clevel_count(role)
        if live >= MAX_LIVE_CLEVEL_PER_ROLE:
            raise Refusal(f"start_clevel: {live} {role} sessions are already live on {host} "
                          f"(limit {MAX_LIVE_CLEVEL_PER_ROLE}); close one first")
        if _is_windows():
            result = _start_clevel_schtask(role, resume_sid)
        elif _os_name() == "darwin":
            result = _start_clevel_iterm(role, resume_sid)
        else:
            result = _start_clevel_tmux(role, resume_sid)
    except BaseException:
        _release(key, token)
        raise
    _hold(key, token, CLEVEL_LAUNCH_GRACE_S)
    return result


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


def _clevel_session_live(role: str, sid: str) -> bool:
    """Is `<role>-<sid>` running here? tmux answers on POSIX. Windows has no
    tmux: windows/cxo-claude.ps1 writes state\\locks\\<role>-<sid>.lock holding
    the pid of the PowerShell that runs claude, so that pid is the answer."""
    from tools import send_to_cxo, session_name
    if not _is_windows():
        return _session_live(session_name.lock_basename(role, sid))
    try:
        pid = int((Path(send_to_cxo.LOCKS_DIR) / f"{role}-{sid}.lock").read_text().strip())
    except (OSError, ValueError):
        return False
    return _pid_is_alive(pid)


def _letter_sender(letter: dict) -> tuple[str, str]:
    from_role = letter.get("from_role") or "hub"
    from_sid = letter.get("from_session") or "node-dispatch"
    for label, value in (("from_role", from_role), ("from_session", from_sid)):
        if not _SAFE_TOKEN_RE.fullmatch(str(value)):
            raise ValueError(f"unsafe {label} {_show(value)}")
    return from_role, from_sid


WIN_WAKE_FLAG = "ORG_WIN_WAKE"


def _windows_wake(role: str, sid: str, from_role: str) -> dict:
    """W3.5 wiring, OFF unless ORG_WIN_WAKE is exactly "1" (CEO has not decided
    whether a wake may raise a window on his desktop and press Enter). Off: the
    W3.3 answer, `woke: False`, and agent_transport.wake_windows_tab is never
    called. On: its `woke` and `why`. The letter is already on disk, so a wake
    that fails or raises is `woke: False`, never a failed delivery. C-level
    letters only: a worker reads MAILBOX.md before every tool call."""
    if os.environ.get(WIN_WAKE_FLAG) != "1":
        return {"woke": False}
    from tools import agent_transport
    try:
        r = agent_transport.wake_windows_tab(f"{role}-{sid}", from_role.upper())
        return {"woke": r.get("woke") is True,
                "why": _redact(str(r.get("why", "")))[:MAX_ERROR_CHARS]}
    except Exception as e:
        return {"woke": False, "why": f"wake raised {type(e).__name__}"}


def _write_clevel_letter(letter: dict, role: str) -> dict:
    from tools import send_to_cxo
    sid = letter.get("to_session") or send_to_cxo._active_session_id(role)
    if not sid:
        raise ValueError(f"no active {role} session on this host")
    if not _SAFE_TOKEN_RE.fullmatch(str(sid)):
        raise ValueError(f"unsafe to_session {_show(sid)}")
    from_role, from_sid = _letter_sender(letter)
    # A letter in a box nobody reads is lost while the hub says delivered.
    # runners/mac_agent.do_relay refuses the same way.
    if not _clevel_session_live(role, sid):
        raise ValueError(f"no live session {role}-{sid} on this host")
    path = mailbox.send(role, sid, letter["body"], from_role, from_sid)
    if not path.is_file():
        raise ValueError(f"letter not on disk after write: {path}")
    if _is_windows():
        return {"to": f"{role}-{sid}", **_windows_wake(role, sid, from_role)}
    try:  # best effort, never changes the outcome (same rule as send_to_cxo)
        send_to_cxo.attempt_wake(role, sid, from_role.upper())
    except Exception:
        pass
    return {"to": f"{role}-{sid}"}


def _append_worker_mailbox(task: dict, body: str, from_role: str, from_sid: str) -> dict:
    """Windows worker: one line appended to `<worktree>\\MAILBOX.md`, the file
    a remote worker reads before every tool call. Same contract as
    tools.send_to_worker._send_remote (append-only, UTF-8, line
    `<ISO-8601 UTC> | <from_role>-<from_sid> | <message on one line>`), verified
    by reading the last line back. Written here, on the box, not over ssh."""
    tid = task["id"]
    if not task.get("worktree"):
        raise ValueError(f"task {tid} has no worktree yet")
    worktree = Path(task["worktree"]).resolve()
    if _worktrees_root().resolve() not in worktree.parents:
        raise ValueError(f"worktree {_show(worktree)} is outside the worktrees root")
    if not worktree.is_dir():
        raise ValueError(f"worktree {_show(worktree)} does not exist")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{stamp} | {from_role}-{from_sid} | {' '.join(body.splitlines())}"
    path = worktree / "MAILBOX.md"
    # The worker owns its worktree, so it can plant MAILBOX.md as a symlink or
    # a hard link to any file its user can write, and the append would land
    # there. Refuse a link before opening, and check the opened file is the
    # plain file named MAILBOX.md in this worktree before writing to it.
    if path.is_symlink() or (path.exists() and path.resolve().parent != worktree):
        raise ValueError(f"MAILBOX.md for {tid} is a link, refusing to write through it")
    with open(path, "ab") as f:  # bytes: CRLF like Add-Content, no newline translation
        st = os.fstat(f.fileno())
        if (path.is_symlink() or st.st_nlink != 1
                or not os.path.samestat(st, os.lstat(path))):
            raise ValueError(f"MAILBOX.md for {tid} is a link, refusing to write through it")
        f.write((line + "\r\n").encode("utf-8"))
    lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
             if ln.strip()]
    if not lines or lines[-1].strip() != line.strip():
        raise ValueError(f"MAILBOX.md write for {tid} could not be verified")
    return {"to": f"{task['role']}-{tid}", "woke": False}


def _write_worker_letter(letter: dict, role: object) -> dict:
    """A letter for a worker on this host. `to_session` is its task id and the
    task row must say this role and this host: the row is the proof that a
    live worker owns the inbox, so a caller cannot aim a letter at an arbitrary
    mailbox path."""
    from tools import agent_transport
    tid = letter.get("to_session")
    if (not isinstance(role, str) or not _SAFE_TOKEN_RE.fullmatch(role)
            or not isinstance(tid, str) or not TASK_ID_RE.fullmatch(tid)):
        raise ValueError(f"to_role {role!r} is not a C-level role, "
                         f"and to_session {_show(tid)} is not a task id")
    task = db.get_task(tid)
    if not task:
        raise ValueError(f"no such task {tid}")
    if task.get("role") != role:
        raise ValueError(f"task {tid} has role {task.get('role')!r}, the letter is for {role!r}")
    here = _self_host()
    if task.get("host") != here:
        raise ValueError(f"task {tid} is on host {task.get('host')!r}, this host is {here!r}")
    from_role, from_sid = _letter_sender(letter)
    if _is_windows():
        return _append_worker_mailbox(task, letter["body"], from_role, from_sid)
    tmux_name = task.get("tmux_session")
    if not tmux_name or not _SAFE_TOKEN_RE.fullmatch(tmux_name) or not _session_live(tmux_name):
        raise ValueError(f"no live tmux session for task {tid} on this host")
    path = mailbox.send(role, tid, letter["body"], from_role, from_sid)
    if not path.is_file():
        raise ValueError(f"letter not on disk after write: {path}")
    try:  # best effort, never changes the outcome
        agent_transport.attempt_wake(tmux_name, from_role.upper(), "node_dispatch")
    except Exception:
        pass
    return {"to": f"{role}-{tid}"}


def _write_letter(letter: dict) -> dict:
    role = letter.get("to_role")
    if role in config.live_c_level_roles():
        return _write_clevel_letter(letter, role)
    return _write_worker_letter(letter, role)


# One delivery slot per letter (W2.7, task-42fdcda7). Two overlapping
# deliver_letter calls for one id both passed the "not delivered" read and both
# wrote the letter: 20 of 20 measured, with a window of at least 0.7 s (the
# wake's own sleeps) on every delivery. Overlap is ordinary: send_to_cxo's first
# dial and the watchdog's retry, or a retry after lib.mesh gave up at 30 s while
# the far side was still writing. The slot is one row in the existing `locks`
# table, taken by an INSERT the primary key lets exactly one caller win (SQLite
# and Postgres alike). A slot older than the TTL belongs to a call that died.
LETTER_CLAIM_TTL_S = 120


def _claim(key: str, ttl_s: int) -> str | None:
    """One `locks` row as a slot: the slot's token, or None when another call
    holds it live. A single INSERT ... ON CONFLICT DO NOTHING RETURNING on the
    primary key, so two callers cannot both win (SQLite and Postgres)."""
    token = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(seconds=ttl_s)).isoformat(timespec="seconds")
    with db.get_conn() as conn:
        conn.execute("DELETE FROM locks WHERE key=? AND expires_at<=?",
                     (key, now.isoformat(timespec="seconds")))
        row = conn.execute(
            "INSERT INTO locks (key, owner, expires_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO NOTHING RETURNING owner",
            (key, token, expires),
        ).fetchone()
    return token if row is not None else None


def _release(key: str, token: str) -> None:
    try:  # a slot that cannot be freed now frees itself at the TTL
        db.release_lock(key, token)
    except Exception as e:
        print(f"node_dispatch: release of {key} failed: {e}", file=sys.stderr)


def _hold(key: str, token: str, seconds: int) -> None:
    """Keep a slot this call owns for `seconds` from now instead of freeing it."""
    expires = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="seconds")
    try:  # on failure the row keeps its claim TTL, which is longer
        with db.get_conn() as conn:
            conn.execute("UPDATE locks SET expires_at=? WHERE key=? AND owner=?",
                         (expires, key, token))
    except Exception as e:
        print(f"node_dispatch: hold of {key} failed: {e}", file=sys.stderr)


def _letter_claim_key(lid: int) -> str:
    return f"letter:{lid}:delivery"


def _claim_letter(lid: int) -> str | None:
    """The slot's token, or None when another call holds a live slot."""
    return _claim(_letter_claim_key(lid), LETTER_CLAIM_TTL_S)


def _release_letter(lid: int, token: str) -> None:
    _release(_letter_claim_key(lid), token)


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
    token = _claim_letter(lid)
    if token is None:
        raise Refusal(f"letter {lid} is being delivered by another call")
    try:
        # Read again under the slot: a call that finished between the first
        # read and the claim has already written this letter.
        if (db.get_letter(lid) or {}).get("status") == "delivered":
            return {"letter_id": lid, "already_delivered": True}
        try:
            where = _write_letter(letter)
            if not db.mark_letter_delivered(lid):
                return {"letter_id": lid, "already_delivered": True}
        except Exception as e:
            db.record_letter_attempt(lid, _redact(f"{type(e).__name__}: {e}")[:MAX_ERROR_CHARS])
            raise Failure(f"letter {lid} not delivered: {e}")
    finally:
        _release_letter(lid, token)
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
        "error": _redact(error)[:MAX_ERROR_CHARS] if error else None,
    }
    if raw is not None:
        payload["raw"] = _redact(raw[:MAX_COMMAND_CHARS])
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
    if out.get("error"):
        out["error"] = _redact(out["error"])
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
