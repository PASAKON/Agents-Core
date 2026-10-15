"""tools/run_watch.py -- status / tail / follow, plan tests B1 and B7."""
from __future__ import annotations

import io
import json
import sqlite3
from datetime import datetime, timezone

import pytest

from lib import db, run_liveness as rl
from tools import run_watch as rw

NOW = 1_800_000_000.0


def iso(offset_s: float) -> str:
    return datetime.fromtimestamp(NOW - offset_s, timezone.utc).isoformat(timespec="seconds")


def row(tid="task-aaaa1111", **kw) -> dict:
    base = {
        "id": tid, "status": "in_progress", "role": "developer",
        "title": "fixture title", "runner": "claude", "runner_model": "claude-sonnet-5-5",
        "owner_cto": "7cf528f0", "pid": 4242, "tmux_session": None, "worktree": None,
        "spawned_at": iso(3600), "created_at": iso(3700), "updated_at": iso(3000),
    }
    base.update(kw)
    return base


def stubs(alive=(), logs=None):
    """Probe stubs: `alive` is the set of task ids whose pid answers."""
    logs = logs or {}
    return dict(
        is_local=lambda t: t.get("host") in (None, "contabo"),
        pid_alive_fn=lambda t: t["id"] in alive,
        tmux_alive_fn=lambda t: False,
        newest_log_fn=lambda t: (f"/log/{t['id']}", logs[t["id"]]) if t["id"] in logs else (None, None),
    )


def five_states():
    """One fixture row per state, with its probe answers."""
    tasks = [
        row("task-run00001"),                                          # alive, fresh log
        row("task-quiet001"),                                          # alive, old log
        row("task-done0001", status="review", updated_at=iso(300)),
        row("task-fail0001", status="failed", updated_at=iso(300)),
        row("task-dead0001"),                                          # nothing answers
    ]
    probes = stubs(alive={"task-run00001", "task-quiet001"},
                   logs={"task-run00001": NOW - 5, "task-quiet001": NOW - 2000,
                         "task-dead0001": NOW - 2000})
    return tasks, probes


@pytest.fixture(autouse=True)
def _defaults(monkeypatch, tmp_path):
    for name in ("RUN_WATCH_QUIET_S", "RUN_WATCH_BATCH_S", "RUN_WATCH_ENDED_S",
                 "RUN_WATCH_SPAWN_GRACE_S", "RUN_WATCH_REPORT_GRACE_S", "RUN_WATCH_POLL_S"):
        monkeypatch.delenv(name, raising=False)
    # `status` records acks; keep them out of the checkout's state/.
    monkeypatch.setattr(rw, "STATE_ROOT", tmp_path / "run-watch")


# --- B1: all five states, through the whole status path --------------------

def test_status_reports_all_five_states():
    tasks, probes = five_states()
    runs = rw.collect_runs(tasks, now=NOW, **probes)
    assert {r["task"]: r["state"] for r in runs} == {
        "task-run00001": "running", "task-quiet001": "quiet", "task-done0001": "done",
        "task-fail0001": "failed", "task-dead0001": "dead"}
    assert set(rl.STATES) == {r["state"] for r in runs}


def test_worst_state_is_listed_first():
    tasks, probes = five_states()
    order = [r["state"] for r in rw.collect_runs(tasks, now=NOW, **probes)]
    assert order == ["dead", "failed", "quiet", "running", "done"]


def test_other_hosts_and_long_ended_runs_are_not_shown():
    tasks, probes = five_states()
    tasks.append(row("task-elsewhere", host="winbox"))
    tasks.append(row("task-old00001", status="review", updated_at=iso(1801)))
    tasks.append(row("task-edge00001", status="review", updated_at=iso(1700)))
    ids = {r["task"] for r in rw.collect_runs(tasks, now=NOW, **probes)}
    assert "task-elsewhere" not in ids
    assert "task-old00001" not in ids
    assert "task-edge00001" in ids


def test_ended_window_comes_from_env(monkeypatch):
    monkeypatch.setenv("RUN_WATCH_ENDED_S", "60")
    tasks, probes = five_states()
    ids = {r["task"] for r in rw.collect_runs(tasks, now=NOW, **probes)}
    assert "task-done0001" not in ids and "task-fail0001" not in ids


# --- status text and --json ------------------------------------------------

def test_status_text_is_a_header_plus_one_row_per_run():
    tasks, probes = five_states()
    runs = rw.collect_runs(tasks, now=NOW, **probes)[:4]
    text = rw.render_status(runs)
    lines = text.splitlines()
    assert len(lines) == 5                      # <= 5 lines for 4 runs
    assert lines[0].split()[:2] == ["task", "runner/model"]
    assert lines[1].split()[0] == "task-dead0001"
    assert lines[1].rstrip().endswith("dead")
    assert "claude/sonnet-5-5" in lines[1]


def test_title_is_cut_to_40_characters():
    long = "x" * 80
    text = rw.render_status([rl.inspect_run(
        row(title=long), now=NOW, pid_alive_fn=lambda t: True,
        tmux_alive_fn=lambda t: False, newest_log_fn=lambda t: (None, None))])
    cell = [w for w in text.splitlines()[1].split() if w.startswith("xxx")][0]
    assert len(cell) == 40 and cell.endswith("…")


def test_no_runs_is_one_line():
    assert rw.render_status([]) == "no runs"


RUN_KEYS = {"task", "state", "status", "runner", "model", "owner", "title", "started",
            "elapsed_s", "ended", "last_log", "idle_s", "log", "pid", "pid_alive", "tmux_alive"}


def run_main(monkeypatch, capsys, argv, tasks, probes=None):
    probes = probes or {}
    monkeypatch.setattr(rw, "this_host", lambda: "contabo")
    monkeypatch.setattr(rw, "fetch_tasks", lambda: tasks)
    real = rw.collect_runs
    monkeypatch.setattr(rw, "collect_runs",
                        lambda ts, **kw: real(ts, now=NOW, **{**probes, **kw}))
    rc = rw.main(argv)
    return rc, capsys.readouterr().out


def test_status_json_schema(monkeypatch, capsys):
    tasks, probes = five_states()
    rc, out = run_main(monkeypatch, capsys, ["status", "--json"], tasks, probes)
    assert rc == 0
    doc = json.loads(out)
    assert set(doc) == {"host", "at", "runs"}
    assert doc["host"] == "contabo"
    assert len(doc["runs"]) == 5
    for r in doc["runs"]:
        assert set(r) == RUN_KEYS
        assert r["state"] in rl.STATES
        assert isinstance(r["pid_alive"], bool) and isinstance(r["tmux_alive"], bool)
    dead = next(r for r in doc["runs"] if r["state"] == "dead")
    assert dead["pid_alive"] is False and dead["tmux_alive"] is False


def test_bad_keeps_only_quiet_failed_dead(monkeypatch, capsys):
    tasks, probes = five_states()
    rc, out = run_main(monkeypatch, capsys, ["status", "--bad", "--json"], tasks, probes)
    assert {r["state"] for r in json.loads(out)["runs"]} == {"dead", "failed", "quiet"}


def test_bad_with_nothing_bad_says_so(monkeypatch, capsys):
    tasks = [row("task-run00001")]
    probes = stubs(alive={"task-run00001"}, logs={"task-run00001": NOW - 5})
    rc, out = run_main(monkeypatch, capsys, ["status", "--bad"], tasks, probes)
    assert (rc, out.strip()) == (0, "no bad runs")


# --- follow: change lines only, batched ------------------------------------

def snap(**states):
    """A collect_runs-shaped snapshot: {task: state}."""
    return [{"task": t, "state": s, "runner": "codex", "model": None, "owner": "7cf528f0",
             "title": f"job {t}", "idle_s": 1000 if s == "quiet" else 5}
            for t, s in states.items()]


def test_first_look_is_a_silent_baseline():
    f = rw.Follower(batch_s=120)
    assert f.step(snap(a="running", b="quiet"), 0) == []
    assert f.step(snap(a="running", b="quiet"), 500) == []


def test_events_inside_one_window_come_out_as_one_batch():
    f = rw.Follower(batch_s=120)
    f.step(snap(a="running"), 0)
    assert f.step(snap(a="running", b="running"), 10) == []          # b starts
    assert f.step(snap(a="quiet", b="running"), 40) == []            # a goes quiet
    assert f.step(snap(a="quiet", b="dead"), 100) == []              # b dies
    batch = f.step(snap(a="quiet", b="dead"), 130)                   # window (from t=10) closed
    assert len(batch) == 3
    assert [ln.split()[1] for ln in batch] == ["start", "quiet", "dead"]
    assert f.step(snap(a="quiet", b="dead"), 400) == []              # nothing left to say


def test_at_most_one_batch_per_window():
    f = rw.Follower(batch_s=120)
    f.step(snap(a="running"), 0)
    printed = []
    # the window opens at t=5 and closes at t=125
    for t, s in [(5, "quiet"), (60, "running"), (118, "quiet"), (124, "quiet"), (126, "quiet")]:
        batch = f.step(snap(a=s), t)
        if batch:
            printed.append((t, batch))
    assert [t for t, _ in printed] == [126]
    assert len(printed[0][1]) == 3


def test_second_burst_after_a_batch_opens_a_new_window():
    f = rw.Follower(batch_s=120)
    f.step(snap(a="running"), 0)
    f.step(snap(a="quiet"), 10)
    assert len(f.step(snap(a="quiet"), 131)) == 1
    f.step(snap(a="running"), 200)
    assert f.step(snap(a="running"), 250) == []
    assert len(f.step(snap(a="running"), 321)) == 1


def test_event_words():
    f = rw.Follower(batch_s=1)
    f.step(snap(a="running", b="running", c="running", d="quiet"), 0)
    f.step(snap(a="done", b="failed", c="dead", d="running", e="running", g="done"), 1)
    batch = f.step(snap(a="done", b="failed", c="dead", d="running", e="running", g="done"), 3)
    words = {ln.split()[2]: ln.split()[1] for ln in batch}
    assert words == {"a": "done", "b": "failed", "c": "dead", "d": "resumed",
                     "e": "start", "g": "done"}


def test_quiet_and_dead_lines_carry_the_reason():
    f = rw.Follower(batch_s=1)
    f.step(snap(a="running", b="running"), 0)
    f.step(snap(a="quiet", b="dead"), 1)
    lines = f.step(snap(a="quiet", b="dead"), 3)
    assert any("idle 16m" in ln for ln in lines)
    assert any("pid and tmux gone" in ln for ln in lines)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_run_follow_prints_only_changes_and_only_once_per_batch(monkeypatch):
    clock = Clock()
    states = iter([
        snap(a="running"),                      # t=0   baseline
        snap(a="running"),                      # t=10
        snap(a="quiet"),                        # t=20  change -> window opens
        snap(a="quiet", b="running"),           # t=30  change, same window
        *[snap(a="quiet", b="running")] * 20,   # t=40.. no change
    ])
    monkeypatch.setattr(rw, "collect_runs", lambda tasks, **kw: next(states))
    out = io.StringIO()
    rc = rw.run_follow(fetch=lambda: [], clock=clock, sleep=clock.sleep, out=out,
                       poll_s=10, max_polls=24)
    assert rc == 0
    lines = out.getvalue().splitlines()
    assert [ln.split()[1] for ln in lines] == ["quiet", "start"]      # one batch, 2 lines
    assert not any("running" in ln.split()[1:2] for ln in lines)       # no status chatter


def test_follow_batch_size_comes_from_env(monkeypatch):
    monkeypatch.setenv("RUN_WATCH_BATCH_S", "30")
    assert rw.Follower().batch_s == 30


# --- B7: the hub is down ----------------------------------------------------

def _snapshot_with_a_false_dead(tmp_path):
    """A hub snapshot a careless reader would trust: an in_progress row whose
    pid is long gone (the run finished after the 15-minute export)."""
    path = tmp_path / "tasks.snapshot.db"
    conn = sqlite3.connect(path)
    conn.executescript(db.SCHEMA)
    have = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
    for col, typ in db._MIGRATION_COLUMNS:
        if col not in have:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {typ}")
    db.init_snapshot_meta(conn)
    db.write_snapshot_meta(conn, "2026-10-14T00:00:00+00:00")
    conn.execute(
        "INSERT INTO tasks (id, project, role, status, title, description, pid, host, "
        "created_at, updated_at) VALUES ('task-stale001', 'p', 'developer', 'in_progress', "
        "'finished since the export', 'd', 999999, 'contabo', '2026-10-14T00:00:00+00:00', "
        "'2026-10-14T00:00:00+00:00')")
    conn.commit()
    conn.close()
    return path


def test_hub_unreachable_is_one_line_and_never_a_false_dead(monkeypatch, capsys, tmp_path):
    snapshot = _snapshot_with_a_false_dead(tmp_path)
    monkeypatch.setattr(db, "SNAPSHOT_PATH", snapshot)
    monkeypatch.setattr(db, "_SNAPSHOT_FALLBACK_WARNED", set())
    bad_url = "postgresql://org:s3cretpw@127.0.0.1:1/nohub"
    monkeypatch.setenv("ORG_DB_URL", bad_url)
    monkeypatch.setattr(rw, "this_host", lambda: "contabo")
    # the trap is real: lib.db would quietly hand back the stale row ...
    assert [t["id"] for t in db.list_tasks()] == ["task-stale001"]
    capsys.readouterr()

    for argv in (["status"], ["status", "--json"], ["status", "--bad"], ["tail", "stale001"]):
        rc = rw.main(argv)
        out, err = capsys.readouterr()
        assert rc != 0
        assert out == "hub unreachable\n"          # exactly one line, nothing else
        assert "dead" not in out and "task-stale001" not in out
        assert "s3cretpw" not in out + err and "127.0.0.1" not in out + err


def test_hub_unreachable_in_follow(monkeypatch, capsys):
    monkeypatch.setenv("ORG_DB_URL", "postgresql://org:pw@127.0.0.1:1/nohub")
    monkeypatch.setattr(rw, "this_host", lambda: "contabo")
    assert rw.main(["follow"]) == rw.EXIT_HUB
    assert capsys.readouterr().out == "hub unreachable\n"


def test_follow_survives_nothing_it_cannot_read():
    out = io.StringIO()

    def down():
        raise rw.HubUnreachable("x")
    assert rw.run_follow(fetch=down, out=out, sleep=lambda s: None, poll_s=1) == rw.EXIT_HUB
    assert out.getvalue() == "hub unreachable\n"


def test_no_hub_url_is_also_unreachable_not_an_empty_list(monkeypatch, capsys):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(rw, "this_host", lambda: "contabo")
    assert rw.main(["status"]) == rw.EXIT_HUB
    assert capsys.readouterr().out == "hub unreachable\n"


def test_a_failed_query_is_unreachable_not_empty(monkeypatch):
    class Conn:
        closed = False

        def execute(self, sql, params=()):
            raise RuntimeError("relation does not exist")

        def close(self):
            self.closed = True
    conn = Conn()
    monkeypatch.setenv("ORG_DB_URL", "postgresql://u:p@h/db")
    monkeypatch.setattr(rw.db_pg, "connect", lambda url, timeout=None: conn)
    with pytest.raises(rw.HubUnreachable):
        rw.fetch_tasks()
    assert conn.closed


def test_host_that_cannot_be_identified_is_its_own_error(monkeypatch, capsys):
    def nohost():
        raise rw.HostUnknown("no source")
    monkeypatch.setattr(rw, "this_host", nohost)
    assert rw.main(["status"]) == rw.EXIT_HOST
    assert capsys.readouterr().out == "host unknown: no source\n"


# --- tail -------------------------------------------------------------------

def _tail_args(task="aaaa1111", n=15):
    return rw._parser().parse_args(["tail", task, "-n", str(n)])


def test_tail_renders_a_claude_transcript_and_masks_secrets(monkeypatch, tmp_path, capsys):
    transcript = tmp_path / "s.jsonl"
    entries = [{"type": "assistant", "timestamp": f"2026-10-15T00:0{i}:00.000Z",
                "message": {"content": [{"type": "text", "text": f"step {i}"}]}}
               for i in range(5)]
    entries.append({"type": "assistant", "timestamp": "2026-10-15T00:09:00.000Z",
                    "message": {"content": [{"type": "text", "text": "key sk-abcdefgh12345678 leaked"}]}})
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    monkeypatch.setattr(rw, "fetch_task", lambda n: row("task-aaaa1111"))
    monkeypatch.setattr("tools.worker_reap.is_local_row", lambda t: True)
    monkeypatch.setattr(rl, "newest_log", lambda t: (transcript, 1.0))
    assert rw.cmd_tail(_tail_args(n=3)) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert lines[0].endswith("step 3") and "sk-abcdefgh" not in lines[-1]
    assert "***" in lines[-1]


def test_tail_falls_back_to_plain_lines_for_a_cli_log(monkeypatch, tmp_path, capsys):
    log = tmp_path / "codex-events.jsonl"
    log.write_text('{"type":"item.completed","item":{"text":"hello"}}\n' * 4)
    monkeypatch.setattr(rw, "fetch_task", lambda n: row("task-aaaa1111"))
    monkeypatch.setattr("tools.worker_reap.is_local_row", lambda t: True)
    monkeypatch.setattr(rl, "newest_log", lambda t: (log, 1.0))
    assert rw.cmd_tail(_tail_args(n=2)) == 0
    assert capsys.readouterr().out.count("item.completed") == 2


def test_tail_exit_codes(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("tools.worker_reap.is_local_row", lambda t: True)
    monkeypatch.setattr(rw, "fetch_task", lambda n: None)
    assert rw.cmd_tail(_tail_args("nope")) == rw.EXIT_NO_TASK
    assert capsys.readouterr().out == "no task nope\n"

    monkeypatch.setattr(rw, "fetch_task", lambda n: row("task-aaaa1111"))
    monkeypatch.setattr(rl, "newest_log", lambda t: (None, None))
    assert rw.cmd_tail(_tail_args()) == rw.EXIT_NO_TASK
    assert "no log" in capsys.readouterr().out

    monkeypatch.setattr("tools.worker_reap.is_local_row", lambda t: False)
    assert rw.cmd_tail(_tail_args()) == rw.EXIT_NO_TASK
    assert "another host" in capsys.readouterr().out


def test_tail_reads_only_the_end_of_a_big_log(tmp_path):
    big = tmp_path / "agy-events.log"
    big.write_text("".join(f"line {i}\n" for i in range(200_000)))
    assert big.stat().st_size > rw.TAIL_BYTES
    assert rw.tail_lines(big, 2) == ["line 199998", "line 199999"]
