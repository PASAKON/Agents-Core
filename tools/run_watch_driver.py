"""One timer tick for the host's Run Watch session. Never creates a tmux server."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import rename_service, run_watch as watch, run_watcher as watcher  # noqa: E402
from lib.run_liveness import _env_int  # noqa: E402

WORDS = dict(start="เริ่ม", done="เสร็จ", failed="พัง", dead="ตาย",
             quiet="เงียบ", resumed="กลับมา")
FOLLOW_FIELDS = ("prev", "seeded", "pending", "window_start")


def tmux(*args: str) -> bool:
    try:
        # -N forbids starting a server, including if it disappears after our probe.
        return subprocess.run(["tmux", "-N", *args], capture_output=True,
                              timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def available_mb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024
    return 0


def save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False) as out:
            name = out.name
            json.dump(state, out, ensure_ascii=False, sort_keys=True)
            out.write("\n")
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def event_line(events: list[str]) -> str:
    short = []
    for event in events:
        _, kind, task, *_ = event.split()
        tid = "".join(c for c in task.removeprefix("task-") if c.isalnum())[:8]
        short.append(f"{tid} {WORDS[kind]}")
    for count in range(len(short), -1, -1):
        suffix = f" +{len(short) - count} more" if count < len(short) else ""
        line = "runs: " + "; ".join(short[:count]) + suffix
        if len(line) <= 100:
            return line
    raise ValueError("event count too large")


def claude_bin() -> str:
    """Absolute path: the tmux server's PATH and the unit's PATH lack ~/.local/bin."""
    return (os.environ.get("RUN_WATCH_CLAUDE_BIN")
            or shutil.which("claude", path=os.pathsep.join(
                [os.environ.get("PATH", ""), str(Path.home() / ".local/bin")]))
            or "claude")


def ready(pane: str) -> bool:
    return rename_service._blocked(pane) is None and rename_service._blocked(pane) is None


def tick(*, dry_run: bool = False) -> int:
    now = time.time()
    host = watch.this_host()
    try:
        tasks = watch.fetch_tasks()
        runs = watch.collect_runs(tasks, now=now)
    except watch.HubUnreachable:
        print("hub unreachable")
        return 0
    path = watch.state_file(host).with_name("driver.json")
    state = json.loads(path.read_text()) if path.exists() else {}
    n, light = watch.compute_light(runs, host=host, tasks=tasks, persist=not dry_run)
    count = state.get("start_count", 0)
    if n:
        state["last_end_at"] = None
    elif state.get("prev_n_active", 0) > 0:
        state["last_end_at"] = now
    ended = state.get("last_end_at")
    session = watcher.tmux_session_name(host)
    # An untouched idle host needs no tmux calls.
    alive = tmux("has-session", "-t", "=" + session) if n or count or state.get("sid") else False
    decision = watcher.decide_lifecycle(n, alive, count,
        None if ended is None else max(0, now - ended), now=now,
        host=host, record=not dry_run)
    typed, result, reason = "", "", ""
    follower = watch.Follower()
    for field in FOLLOW_FIELDS:
        if field in state.get("follower", {}):
            setattr(follower, field, state["follower"][field])
    pending = state.setdefault("pending_out", [])
    if alive:
        pending.extend(follower.step(runs, now))
        if n == 0:
            pending.extend(follower.pending)
            follower.pending = []
            follower.window_start = None
    applied = decision
    if decision in ("start", "restart"):
        if not tmux("list-sessions"):
            reason = "no tmux server"
        else:
            try:
                if available_mb() < _env_int("RUN_WATCH_MIN_AVAIL_MB", 700):
                    reason = "low MemAvailable"
            except (OSError, ValueError):
                reason = "MemAvailable unreadable"
        if not reason:
            sid = secrets.token_hex(4)
            env = {k: v for k, v in os.environ.items() if k.startswith("RUN_WATCH_")}
            env["RUN_WATCH_SID"] = sid
            argv = watcher.build_launch_argv(host, sid=sid, n_active=n, light=light,
                                             cwd=ROOT, env=env, claude_bin=claude_bin())
            if dry_run or tmux(*argv[1:]):
                state.update(sid=sid, last_name=watch.format_watch_name(n, light, sid=sid, host=host))
                follower = watch.Follower()
                follower.step(runs, now)
                alive = True
            else:
                reason = "launch failed"
        if reason:
            applied = "none"
    elif decision == "stop":
        if (pending or follower.pending) and state.get("flush_ticks", 0) < 3:
            state["flush_ticks"] = state.get("flush_ticks", 0) + 1
            applied, reason = "none", "flush"
        elif dry_run or tmux("kill-session", "-t", "=" + session):
            alive = False
            state["flush_ticks"] = 0
        else:
            applied, reason = "none", "stop failed"
    if alive:
        name = watch.format_watch_name(n, light, sid=state.get("sid", "000"), host=host)
        if name != state.get("last_name") and ready(session):
            typed = f"/rename {name}"
            result = "would type" if dry_run else rename_service.type_rename(session, typed)
            if result == "renamed":
                state["last_name"] = name
        if pending and not typed and ready(session):
            typed = event_line(pending)
            result = "would type" if dry_run else rename_service.type_rename(session, typed)
            if result == "renamed":
                pending.clear()
    state.update(start_count=watcher.next_start_count(n, alive, count, applied),
                 prev_n_active=n, follower={key: getattr(follower, key) for key in FOLLOW_FIELDS})
    if not dry_run:
        save(path, state)
    print(f"{'dry-run ' if dry_run else ''}{decision} n_active={n} light={light} "
          f"typed={json.dumps(typed, ensure_ascii=False)} result={result or '-'} reason={reason or '-'}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["tick"])
    parser.add_argument("--dry-run", action="store_true")
    return tick(dry_run=parser.parse_args(argv).dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
