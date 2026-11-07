"""Zero-model idle session parking (CEO O-20261107-2250-c276)."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.pane_screen import prompt_ready
from tools import ask_run

DAY = 86400


def command(argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True, check=True, timeout=90).stdout
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{argv[0]} failed: {exc.stderr.strip()}") from exc


def read(path):
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return ""


def persist(path, state):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def sessions():
    rows = command(["tmux", "list-panes", "-a", "-F",
                    "#{session_name}\t#{pane_id}\t#{pane_current_path}"])
    result = {}
    for line in rows.splitlines():
        name, pane, cwd = line.split("\t", 2)
        result.setdefault(name, []).append((pane, cwd))
    return result


def ready(panes):
    return all(prompt_ready(command(["tmux", "capture-pane", "-e", "-p", "-t", pane]))
               for pane, _ in panes)


def activity(name, panes, root):
    """Latest real signal; absent metadata never becomes an ancient timestamp."""
    from lib.run_liveness import log_files, parse_ts
    files, times = [], []
    project = Path(panes[0][1]).name or "unknown"
    if name.startswith(("mooniex-task-", "wd-task-")):
        from tools import live_sessions
        tid = name.removeprefix("mooniex-").removeprefix("wd-")
        conn = live_sessions._open_hub()  # no stale SQLite fallback or DB creation
        try:
            row = conn.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
            task = dict(row) if row else None
        finally:
            conn.close()
        if task:
            project = task.get("project") or project
            files.extend(log_files(task))
            if task.get("worktree"):
                files.append(Path(task["worktree"]))
            stamp = parse_ts(task.get("updated_at"))
            if stamp is not None:
                times.append(stamp)
        files.extend(Path(cwd) for _, cwd in panes)
        files.extend((root / f".launch-{tid}" / f for f in
                      ("codex-events.jsonl", "agy-events.log")))
    else:
        uuid = read(root / "state/locks" / f"{name}.uuid")
        if re.fullmatch(r"[a-fA-F0-9-]+", uuid):
            files.extend((Path.home() / ".claude/projects").glob(f"*/{uuid}.jsonl"))
    for path in files:
        try:
            times.append(path.stat().st_mtime)
        except FileNotFoundError:
            pass
    return (max(times) if times else None), project


def question(qid):
    rec = ask_run._unwrap(ask_run._call("GET", ask_run._question_path(qid)))
    ask_run.verify_question_record(rec)
    return rec


def main_box(root):
    return read(root / "state/locks/cto-active") or "fresh"


def create_card(name, project, days, root):
    title = f"{name[:40]} · {project[:25]} · idle {days} วัน"[:90]
    raw = command([sys.executable, str(root / "tools/ask_run.py"), "ask",
                   "--role", "cto", "--session", f"cto-{main_box(root)}",
                   "--question", title, "--option", "ปิด (save ถาวร)",
                   "--option", "ทำต่อ 3 วัน", "--why", "เก็บงานบน disk ไว้ให้เจ้าของจัดการ",
                   "--no-free-text", "--expires-h", "168", "--json"])
    return json.loads(raw)["id"]


def save_session(name, status, note, root):
    if name.startswith(("mooniex-task-", "wd-task-")):
        # Same surface teardown as the remote launcher. No task-row mutation.
        command(["tmux", "kill-session", "-t", f"={name}"])
    else:
        command(["bash", str(root / "scripts/session-kill.sh"),
                 "--status", status, "--note", note, name])


def notify(name, days, owner, root):
    from lib import mailbox
    match = re.fullmatch(r"cxo:([^:]+):([^:]+)", owner)
    role, sid = match.groups() if match else ("cto", main_box(root))
    mailbox.send(role, sid,
                 f"saved {name} (idle {days} d); its worktree/Work stays, yours to clear",
                 "cto", main_box(root), kind="fyi")


def flush_notices(state, path, root):
    for name, entry in state.items():
        if entry.get("notice"):
            notice = entry["notice"]
            notify(name, notice["days"], notice["owner"], root)
            del entry["notice"]
            persist(path, state)


def sweep(root=ROOT, *, dry_run=False):
    state_dir = root / "state"
    if (state_dir / "idle_sweep.off").exists():
        print("idle sweep: off")
        return
    path = state_dir / "idle_sweep.json"
    state = json.loads(read(path) or "{}")  # corrupt state must not duplicate cards
    if not dry_run:
        # A saved last session may have stopped the tmux server altogether.
        # Retry its FYI before requiring a live inventory (or resetting a resumed name).
        flush_notices(state, path, root)
    now = time.time()
    current = command(["tmux", "display-message", "-p", "#S"]).strip() if os.environ.get("TMUX") else ""
    cards = saves = 0
    for name, panes in sessions().items():
        try:
            lock = read(state_dir / "locks" / f"{name}.lock")
            if (name == "sompong" or name.startswith("runwatch-") or name == current
                    or lock in {str(os.getpid()), str(os.getppid())}
                    or not re.fullmatch(r"[\w-]+", name) or not ready(panes)):
                print(f"skip {name}: protected or pane not prompt_ready")
                continue
            touched, project = activity(name, panes, root)
            if touched is None:
                print(f"skip {name}: no transcript or activity signal")
                continue
            days = int((now - touched) // DAY)
            entry = state.get(name, {})
            qid = entry.get("card_id")
            if entry.get("saved"):
                # Same named session resumed: start a new cycle only with fresh activity.
                if touched <= entry["saved"]:
                    continue
                entry = state[name] = {}
                qid = None
            status = None
            if qid:
                rec = question(qid)
                answer = rec.get("answer") or {}
                if rec.get("status") == "answered":
                    if answer.get("choice") == 1:
                        print(f"snooze {name}: 3 days")
                        state[name] = {"snooze_until": now + 3 * DAY}
                        if not dry_run:
                            persist(path, state)
                        continue
                    if answer.get("choice") == 0:
                        status = "saved"
                elif now - entry["raised_at"] >= 7 * DAY and rec.get("status") in ("pending", "expired", "cancelled"):
                    status = "force_saved"
                if status and saves < 3:
                    print(f"{status} {name}: idle {days} d; {qid}")
                    saves += 1
                    if dry_run:
                        continue
                    # Recheck after hub I/O, immediately before teardown.
                    if not ready(panes):
                        continue
                    if status == "force_saved" and rec.get("status") == "pending":
                        command([sys.executable, str(root / "tools/ask_run.py"), "cancel", qid])
                    note = f"idle sweep: CEO {qid}" if status == "saved" else f"idle sweep: no answer 7 d {qid}"
                    owner = read(state_dir / "locks" / f"{name}.spawned_by")
                    save_session(name, status, note, root)
                    entry["saved"] = now
                    entry["notice"] = {"days": days, "owner": owner}
                    persist(path, state)
                continue
            if days >= 3 and now >= entry.get("snooze_until", 0) and cards < 5:
                print(f"ask {name} · {project} · idle {days} วัน")
                cards += 1
                if not dry_run:
                    state[name] = {"card_id": create_card(name, project, days, root),
                                   "raised_at": now, "snooze_until": 0}
                    persist(path, state)
        except Exception as exc:
            print(f"skip {name}: {type(exc).__name__}: {exc}")
    if not dry_run:
        flush_notices(state, path, root)


def tick(root=ROOT, *, dry_run=False):
    """Serialize manual and watcher runs; reserve the hourly slot before I/O."""
    if dry_run:
        sweep(root, dry_run=True)
        return
    if (root / "state/idle_sweep.off").exists():
        return
    root.joinpath("state").mkdir(exist_ok=True)
    with (root / "state/idle_sweep.stamp").open("a+") as stamp:
        try:
            fcntl.flock(stamp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        stamp.seek(0)
        previous = stamp.read().strip()
        now = time.time()
        if previous and now - float(previous) < 3600:
            return
        stamp.seek(0)
        stamp.truncate()
        stamp.write(str(now))
        stamp.flush()
        sweep(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        tick(dry_run=args.dry_run)
    except Exception as exc:
        print(f"idle sweep skipped: {type(exc).__name__}: {exc}")
        sys.exit(1)
