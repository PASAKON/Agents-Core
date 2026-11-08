"""One timer tick for the host's Run Watch session. Never creates a tmux server.

The host has ONE Watch session, always up and never killed when idle (CEO 3 Nov: he
pins it in the Claude app). Its Claude conversation is one uuid kept in driver.json:
the first start gives it `--session-id`, every later start resumes it with `-r`. The
driver kills it only for low MemAvailable; the next tick resumes the same uuid.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import rename_service, run_watch as watch, run_watcher as watcher  # noqa: E402
from lib.run_liveness import _env_int  # noqa: E402
from lib import ph_state

WORDS = dict(start="เริ่ม", done="เสร็จ", failed="พัง", dead="ตาย",
             quiet="เงียบ", resumed="กลับมา")
FOLLOW_FIELDS = ("prev", "seeded", "pending", "window_start")
PROJECTS = Path.home() / ".claude" / "projects"      # where claude keeps conversations
COMPACT_TOKENS_DEFAULT = 60000
# A transcript line is JSON around the text, so bytes/4 over-counts tokens:
# the compaction comes early rather than late.
BYTES_PER_TOKEN = 4
KILL_AVAIL_MB_DEFAULT = 350   # below the 700 MB a start needs: killing must not flap with starting


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
    raise ValueError("no MemAvailable")


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


def transcript_path(session_id: str) -> Path | None:
    """The stored conversation `claude -r <id>` opens from ROOT, else None. It is not
    written until the first message, so a first launch that died early has none."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))     # as tools/memory_sync.py names it
    path = PROJECTS / slug / f"{session_id}.jsonl"
    return path if path.is_file() else None


def transcript_bytes(session_id: str | None) -> int:
    path = transcript_path(session_id) if session_id else None
    try:
        return path.stat().st_size if path else 0
    except OSError:
        return 0


def ready(pane: str) -> bool:
    return rename_service._blocked(pane) is None and rename_service._blocked(pane) is None


def ph_snapshot(host, now, *, dry_run=False):
    """All hosts read one hub; only local native panes and PIDs are inspected."""
    try:
        rows = watch.fetch_phs()
        tasks = watch._query("SELECT owner_cto,status FROM tasks WHERE owner_cto IS NOT NULL", ())
        if not dry_run:
            sessions = watch._query("SELECT * FROM c_level_sessions WHERE status='open' AND host=?", (host,))
            for session in sessions:
                sid = session['session_id']
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', sid):
                    continue
                project = rename_service._read(f'project_head-{sid}.project')
                if session['role'] != 'project_head' and not project:
                    continue
                session['project'] = project or session.get('charter') or sid
                shell_marker = rename_service.LOCKS_DIR / f'project_head-{sid}.shell'
                owner = rename_service._read(f'project_head-{sid}.spawned_by').split(':')
                if len(owner) == 3:
                    session.update(lane=owner[1], owner=f'{owner[1]}-{owner[2]}')
                if any(r['session_id'] == session['session_id'] and r['host'] == host
                       and r['brain'] != 'claude-native' for r in rows):
                    continue
                if shell_marker.is_file():
                    continue  # A shell is never a native PH brain.
                try:
                    capture = rename_service.tmux('capture-pane', '-p', '-e', '-t',
                                                  '=' + session['role'] + '-' + sid + ':0.0')
                    if capture.returncode == 0:
                        ph_state.observe_native(session, capture.stdout, now=now)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            rows = ph_state.observe(watch.fetch_phs(), now=now, local_host=host, tasks=tasks)
            rows = [row for row in watch.fetch_phs()
                    if not (row['host'] == host and row['brain'] == 'claude-native'
                            and (rename_service.LOCKS_DIR /
                                 f"project_head-{row['session_id']}.shell").is_file())]
            rows += ph_state.missing_brains(
                sessions, rows, now=now, locks_dir=rename_service.LOCKS_DIR,
                brains_dir=ROOT / 'state' / 'ph-brains')
        return {'at': now, 'rows': rows}
    except Exception:
        # Never leak a hub DSN; do not turn unreadable data into false red PHs.
        return {'at': now, 'rows': [], 'error': True}


def ph_display_alive(session):
    try:
        proc = subprocess.run(['tmux', '-N', 'list-panes', '-t', '=' + session + ':0',
                               '-F', '#{pane_dead} #{pane_start_command}'],
                              capture_output=True, text=True, timeout=10)
        return proc.returncode == 0 and any(
            line.startswith('0 ') and 'tools/run_watch.py' in line and 'ph-display' in line
            for line in proc.stdout.splitlines())
    except (OSError, subprocess.TimeoutExpired):
        return False


def tick(*, dry_run: bool = False) -> int:
    now = time.time()
    host = watch.this_host()
    snapshot = ph_snapshot(host, now, dry_run=dry_run)
    if not dry_run:
        save(watch.state_file(host).with_name('ph.json'), snapshot)
    try:
        tasks = watch.fetch_tasks()
        runs = watch.collect_runs(tasks, now=now)
    except watch.HubUnreachable:
        print("hub unreachable")
        return 0
    path = watch.state_file(host).with_name("driver.json")
    state = json.loads(path.read_text()) if path.exists() else {}
    n, light = watch.compute_light(runs, host=host, tasks=tasks, persist=not dry_run)
    session = watcher.tmux_session_name(host)
    alive = tmux("has-session", "-t", "=" + session)
    if alive:
        state.setdefault("started_at", now)     # a session from before the pin: adopt it
    count = watcher.forget_deaths(
        state.get("start_count", 0), alive=alive, started_at=state.get("started_at"),
        gave_up_at=state.get("gave_up_at"), now=now)
    decision = watcher.decide_lifecycle(n, alive, count, now, host=host, record=not dry_run)
    typed, result, reason = "", "", ""
    follower = watch.Follower()
    for field in FOLLOW_FIELDS:
        if field in state.get("follower", {}):
            setattr(follower, field, state["follower"][field])
    pending = state.setdefault("pending_out", [])
    if alive:
        pending.extend(follower.step(runs, now))
        if n == 0 or any(ln.split()[1] in watch.FAIL_STATES for ln in follower.pending):
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
            session_id = state.get("uuid") or str(uuid.uuid4())
            env = {k: v for k, v in os.environ.items() if k.startswith("RUN_WATCH_")}
            argv = watcher.build_launch_argv(
                host, session_id=session_id, resume=transcript_path(session_id) is not None,
                n_active=n, light=light, cwd=ROOT, env=env, claude_bin=claude_bin())
            if dry_run or tmux(*argv[1:]):
                if session_id != state.get("uuid"):
                    state["compact_base"] = 0       # a new conversation: nothing compacted yet
                state.update(uuid=session_id, started_at=now,
                             ph_pane=False,
                             last_name=watch.format_watch_name(n, light, host=host))
                follower = watch.Follower()
                follower.step(runs, now)
                alive = True
            else:
                reason = "launch failed"
        if reason:
            applied = "none"
    elif decision == "give_up":
        state["gave_up_at"] = now
    elif alive:
        # Never stopped for being idle, only for memory. Killed below what a start needs,
        # so the next tick's resume cannot be killed again at once.
        try:
            low = available_mb() < _env_int("RUN_WATCH_KILL_AVAIL_MB", KILL_AVAIL_MB_DEFAULT)
        except (OSError, ValueError):
            low = False
        if low:
            if dry_run or tmux("kill-session", "-t", "=" + session):
                alive, applied, reason = False, "stop", "low MemAvailable: killed"
            else:
                reason = "kill failed"
    if alive:
        # Keep a dedicated zero-model pane inside Watch. Its own clock can warn
        # after this driver stops, unlike a one-shot ! print into Claude.
        if not dry_run and not snapshot.get('error') and (
                not state.get('ph_pane') or not ph_display_alive(session)):
            command = shlex.join([sys.executable, str(ROOT / 'tools/run_watch.py'),
                                  'ph-display', '--host', host])
            if tmux('split-window', '-d', '-v', '-l', '8', '-t', '=' + session + ':0.0', command):
                state['ph_pane'] = True
        name = watch.format_watch_name(n, light, host=host)
        if not snapshot.get('error'):
            name += ph_state.suffix(snapshot['rows'])
        if name != state.get("last_name") and ready(session):
            typed = f"/rename {name}"
            result = "would type" if dry_run else rename_service.type_rename(session, typed)
            if result == "renamed":
                state["last_name"] = name
        ph_changed = ph_state.signature(snapshot) != state.get('ph_signature')
        if (not snapshot.get('error') and ph_changed and not typed
                and now - state.get('ph_printed_at', 0) >= 60 and ready(session)):
            # Claude's ! command runs local Bash directly, without a Haiku turn.
            # No model-authored report and no prompt content from PH telemetry.
            typed = '! ' + shlex.join(['bash', 'scripts/hub/org-python.sh',
                                      'tools/run_watch.py', 'ph-display', '--once', '--host', host])
            result = 'would type' if dry_run else rename_service.type_rename(session, typed)
            if result == 'renamed':
                state.update(ph_signature=ph_state.signature(snapshot), ph_printed_at=now)
        if pending and not typed and ready(session):
            session_id = state.get("uuid")
            grown = max(0, transcript_bytes(session_id) - state.get("compact_base", 0))
            compact = grown // BYTES_PER_TOKEN >= _env_int(
                "RUN_WATCH_COMPACT_TOKENS", COMPACT_TOKENS_DEFAULT)
            typed = "/compact" if compact else event_line(pending)
            result = "would type" if dry_run else rename_service.type_rename(session, typed)
            if result == "renamed":
                if compact:     # the event line goes in on a later tick, once it is done
                    state["compact_base"] = transcript_bytes(session_id)
                else:
                    pending.clear()
    state.update(start_count=watcher.next_start_count(count, applied),
                 follower={key: getattr(follower, key) for key in FOLLOW_FIELDS})
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
