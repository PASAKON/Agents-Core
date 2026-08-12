"""Shared logic for `scripts/terminal-restart.sh` + `scripts/session-restart.sh`
(task-b0b3f602).

Both scripts replace a wedged/stale `claude` process without losing the
session's resume identity. All tmux/process/DB interaction lives here, behind
small mockable seams, so the bash wrappers stay thin orchestration and the
actual behavior is unit-testable without a real tmux server or a real claude
process (`scripts/test_terminal_restart.py`).

  terminal-restart.sh (common case)
      claude is stuck/stale/confused but tmux is fine. `tmux respawn-pane -k`
      replaces just the process, in place — same pane/window/session.

  session-restart.sh (last resort)
      tmux itself is wedged, so respawn-pane cannot even be delivered. Tear
      the stack down (`session-kill.sh --status saved`) and rebuild it
      (`spawn-cto.sh`/`spawn-cxo.sh --resume`) with the same id + uuid.

Shared hard gate: refuse to touch a session that owns live work (a task in
pending/in_progress/rate_limited/blocked_human) — killing its claude orphans
any DEV it is supervising, whose report would then land with nobody reading
it. `--force` overrides, loudly, naming what it overrode.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db  # noqa: E402
from tools import session_name  # noqa: E402

LOCKS_DIR = ROOT / "state" / "locks"

# Statuses meaning this session owns work nobody else is watching. Mirrors
# the set named in TASK.md's hard gate.
LIVE_STATUSES = ("pending", "in_progress", "rate_limited", "blocked_human")

# "~25s" per TASK.md's verify step — long enough for claude's CLI + MCP
# handshake to finish inside the freshly respawned pane.
VERIFY_DELAY_S = 25


# ---------------------------------------------------------------------------
# Resume identity (.uuid) + the run-file a launcher wrote at spawn time
# ---------------------------------------------------------------------------

def uuid_path(locks_dir: Path | str, name: str) -> Path:
    return Path(locks_dir) / f"{name}.uuid"


def read_uuid(locks_dir: Path | str, name: str) -> str | None:
    """The full Claude resume UUID for this session, or None if absent/empty.

    Never raises — a missing file is the case this whole module exists to
    refuse loudly on, not to crash over.
    """
    try:
        v = uuid_path(locks_dir, name).read_text().strip()
    except OSError:
        return None
    return v or None


def run_file_path(locks_dir: Path | str, name: str) -> Path:
    return Path(locks_dir) / f"{name}.run"


def read_run_file(locks_dir: Path | str, name: str) -> str | None:
    """The launcher's original run-file text, or None if it is gone."""
    try:
        return run_file_path(locks_dir, name).read_text()
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Hard gate — does this session own live work?
# ---------------------------------------------------------------------------

def owning_live_tasks(session_id: str) -> list[dict]:
    """Tasks this session owns that are still live (see LIVE_STATUSES)."""
    out: list[dict] = []
    for status in LIVE_STATUSES:
        out.extend(db.list_tasks(status=status, owner_cto=session_id, limit=1000))
    return out


def _tasks_summary(tasks: list[dict]) -> str:
    return ", ".join(f"{t['id']}({t['status']})" for t in tasks)


def evaluate(name: str, locks_dir: Path | str, *, force: bool = False) -> dict:
    """Whether a restart of `name` may proceed.

    Returns {"ok", "uuid", "reason", "overridden"}. The missing-.uuid refusal
    is never forceable — without it a restart is an amnesia event, not a
    restart (TASK.md deliverable 1, step 2). The owns-live-work refusal is
    the one `force=True` overrides, and `overridden` is set (not silently
    dropped) so the caller can say out loud what it just overrode.
    """
    uuid = read_uuid(locks_dir, name)
    if not uuid:
        return {
            "ok": False, "uuid": None, "overridden": None,
            "reason": (
                f"no resume UUID at {uuid_path(locks_dir, name)} — refusing: "
                f"without it a restart is an amnesia event, not a restart"
            ),
        }

    session_id = session_name.id_from_tmux_session(name)
    tasks = owning_live_tasks(session_id) if session_id else []
    if tasks:
        msg = (
            f"session '{name}' owns {len(tasks)} live task(s) — "
            f"{_tasks_summary(tasks)} — restarting would orphan them"
        )
        if force:
            return {"ok": True, "uuid": uuid, "reason": None, "overridden": msg}
        return {
            "ok": False, "uuid": uuid, "overridden": None,
            "reason": f"{msg} (pass --force to override)",
        }

    return {"ok": True, "uuid": uuid, "reason": None, "overridden": None}


# ---------------------------------------------------------------------------
# Deliverable 1 — terminal-restart: build a resume run-file, respawn in place
# ---------------------------------------------------------------------------

def build_resume_run_file_text(original_text: str, uuid: str) -> str:
    """`original_text` with `-r <uuid>` appended to its launcher line.

    Everything else — the env exports, the launcher script path, any
    existing args — is left untouched, so the relaunch "re-exports the same
    env" by construction rather than by us re-deriving which vars mattered.
    `-r` is enough: cto-claude.sh / cxo-claude.sh already turn a `-r`/`-c` in
    their own args into `--fork-session` (see FORK_ARGS in both) when
    `--session-id` is also passed, which they always pass. Adding
    `--fork-session` here too would be a second, possibly-diverging
    invocation of the same rule.
    """
    lines = original_text.splitlines()
    out: list[str] = []
    inserted = False
    for line in lines:
        if not inserted and "exec bash" in line:
            out.append(f"{line.rstrip()} -r {shlex.quote(uuid)}")
            inserted = True
        else:
            out.append(line)
    if not inserted:
        raise ValueError("original run-file has no 'exec bash ...' launcher line")
    return "\n".join(out) + "\n"


def write_resume_run_file(locks_dir: Path | str, name: str, uuid: str) -> Path:
    """Rewrite `<name>.run` in place to resume into `uuid`. Returns its path.

    Same path the original launcher wrote (`<locks_dir>/<name>.run`) — that
    launcher's own EXIT trap removes exactly that path on exit, and
    `respawn-pane` needs a real file to hand to the fresh `bash` it starts.
    """
    original = read_run_file(locks_dir, name)
    if original is None:
        raise FileNotFoundError(
            f"no run-file at {run_file_path(locks_dir, name)} to base the resume on"
        )
    path = run_file_path(locks_dir, name)
    path.write_text(build_resume_run_file_text(original, uuid))
    path.chmod(0o755)
    return path


def respawn_pane(name: str, run_file: Path | str) -> subprocess.CompletedProcess:
    """`tmux respawn-pane -k` — same pane/window/session, only the process
    inside is replaced. Deliberately never `kill-session`: tmux itself must
    stay up, which is the entire reason this is preferred over a rebuild.
    """
    return subprocess.run(
        ["tmux", "respawn-pane", "-k", "-t", name, f"bash {run_file}"],
        capture_output=True, text=True,
    )


# ---------------------------------------------------------------------------
# Verify a claude process actually came back
# ---------------------------------------------------------------------------

def _pane_pid(name: str) -> int | None:
    r = subprocess.run(
        ["tmux", "list-panes", "-t", name, "-F", "#{pane_pid}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    try:
        return int(lines[0]) if lines else None
    except ValueError:
        return None


def _descendant_pids(root_pid: int, max_depth: int = 5) -> list[int]:
    """BFS down the process tree from `root_pid` via `pgrep -P`.

    Needed because the launcher scripts run `claude` as a plain child, not
    an exec'd replacement (so their own EXIT trap still fires — see
    cto-claude.sh) — the tmux pane's immediate process is the launcher
    shell, not claude itself. Observed directly on a live, healthy session
    (`pane_current_command` read "bash", the real claude pid was two levels
    down): trusting tmux's own idea of the foreground command would have
    reported a healthy session as dead.
    """
    found: list[int] = []
    frontier = [root_pid]
    depth = 0
    while frontier and depth < max_depth:
        r = subprocess.run(
            ["pgrep", "-P", ",".join(str(p) for p in frontier)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            break
        children = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
        if not children:
            break
        found.extend(children)
        frontier = children
        depth += 1
    return found


def _is_claude_process(pid: int) -> bool:
    r = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return False
    first_word = r.stdout.strip().split()[0]
    return first_word.rsplit("/", 1)[-1] == "claude"


def find_claude_pid(name: str) -> int | None:
    """The pid of a live `claude` process inside session `name`'s pane, or
    None. Checks the pane's own pid plus its process descendants (see
    `_descendant_pids`)."""
    pane_pid = _pane_pid(name)
    if pane_pid is None:
        return None
    for pid in [pane_pid, *_descendant_pids(pane_pid)]:
        if _is_claude_process(pid):
            return pid
    return None


def verify_restart(name: str, *, delay: float = VERIFY_DELAY_S,
                   sleep_fn=time.sleep) -> dict:
    """Wait `delay`s then confirm a live claude is back in `name`'s pane.

    On failure the caller (the CLI, or the deferred bash block) is
    responsible for shouting loudly and printing the resume UUID — this
    function only reports, it never itself decides where that goes, since
    the self-restart path has no terminal left to print to by the time this
    runs (TASK.md step 5).
    """
    if delay:
        sleep_fn(delay)
    pid = find_claude_pid(name)
    if pid is None:
        return {
            "ok": False, "pid": None, "name": name,
            "message": (
                f"no live claude process found in session '{name}' after "
                f"restart — a human must resume by hand"
            ),
        }
    return {
        "ok": True, "pid": pid, "name": name,
        "message": f"claude pid={pid} alive in session '{name}'",
    }


# ---------------------------------------------------------------------------
# Deliverable 2 — session-restart: capture id+uuid before the kill
# ---------------------------------------------------------------------------

def capture_identity(locks_dir: Path | str, name: str, dest: Path | str) -> Path:
    """Copy `name`'s role/session_id/uuid to `dest`, OUTSIDE `locks_dir`,
    before a kill that reaps the lock family.

    `session-kill.sh::reap_locks` deletes everything in
    `session_name.LOCK_SUFFIXES` but deliberately preserves `.uuid`
    (`session_name.KEEP_SUFFIXES`) precisely so a resume stays possible —
    this capture is the belt-and-suspenders copy TASK.md deliverable 2 asks
    for, so session-restart.sh still has the id even if `.uuid` were ever
    hand-deleted between the capture and the rebuild.
    """
    uuid = read_uuid(locks_dir, name)
    if not uuid:
        raise FileNotFoundError(
            f"no .uuid for '{name}' at {locks_dir} — cannot capture, nothing to resume"
        )
    role = session_name.parse_role(name)
    session_id = session_name.id_from_tmux_session(name)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({
        "name": name, "role": role, "session_id": session_id, "uuid": uuid,
    }) + "\n")
    return dest


def read_captured_identity(path: Path | str) -> dict:
    return json.loads(Path(path).read_text())


# ---------------------------------------------------------------------------
# CLI — thin dispatch so the bash scripts stay orchestration-only
# ---------------------------------------------------------------------------

def _cmd_check(args: argparse.Namespace) -> int:
    result = evaluate(args.name, args.locks_dir, force=args.force)
    if result["overridden"]:
        print(f"--force overriding: {result['overridden']}")
    if not result["ok"]:
        print(result["reason"])
        return 1
    return 0


def _cmd_build_run_file(args: argparse.Namespace) -> int:
    uuid = read_uuid(args.locks_dir, args.name)
    if not uuid:
        print(f"no resume UUID for '{args.name}' at {args.locks_dir}", file=sys.stderr)
        return 1
    try:
        path = write_resume_run_file(args.locks_dir, args.name, uuid)
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    print(str(path))
    return 0


def _cmd_respawn(args: argparse.Namespace) -> int:
    r = respawn_pane(args.name, args.run_file)
    if r.stdout:
        print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="", file=sys.stderr)
    return r.returncode


def _cmd_verify(args: argparse.Namespace) -> int:
    result = verify_restart(args.name, delay=args.delay)
    print(result["message"])
    if result["ok"]:
        print(f"pid={result['pid']}")
    return 0 if result["ok"] else 1


def _cmd_capture(args: argparse.Namespace) -> int:
    try:
        capture_identity(args.locks_dir, args.name, args.dest)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(str(args.dest))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="tools.terminal_restart",
        description="Shared logic for terminal-restart.sh / session-restart.sh",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    def _common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--name", required=True, help="<role>-<id> session name")
        p.add_argument("--locks-dir", type=Path, default=LOCKS_DIR)

    c = sub.add_parser("check", help="refuse or allow a restart of --name")
    _common(c)
    c.add_argument("--force", action="store_true",
                   help="override the owns-live-work refusal (never the missing-uuid one)")

    b = sub.add_parser("build-run-file", help="write the resume run-file, print its path")
    _common(b)

    r = sub.add_parser("respawn", help="tmux respawn-pane -k --name with --run-file")
    _common(r)
    r.add_argument("--run-file", required=True, type=Path)

    v = sub.add_parser("verify", help="wait then confirm claude is alive in --name")
    _common(v)
    v.add_argument("--delay", type=float, default=VERIFY_DELAY_S)

    cap = sub.add_parser("capture", help="copy id+uuid for --name to --dest before a kill")
    _common(cap)
    cap.add_argument("--dest", required=True, type=Path)

    args = ap.parse_args(argv)
    db.init()

    return {
        "check": _cmd_check,
        "build-run-file": _cmd_build_run_file,
        "respawn": _cmd_respawn,
        "verify": _cmd_verify,
        "capture": _cmd_capture,
    }[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
