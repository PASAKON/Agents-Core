"""Driver integration with fake hub, tmux, clock, memory and pane."""
import json

import pytest

from tools import run_watch_driver as d


@pytest.fixture
def rig(monkeypatch, tmp_path):
    for key in list(d.os.environ):
        if key.startswith("RUN_WATCH_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("RUN_WATCH_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("RUN_WATCH_STEWARD_DIR", str(tmp_path / "steward"))
    monkeypatch.setenv("RUN_WATCH_CLOSE_AFTER_S", "60")
    monkeypatch.setenv("RUN_WATCH_BATCH_S", "60")
    r = dict(now=1000, runs=[], alive=False, server=True, mb=1000,
             busy=False, calls=[], typed=[], result="renamed")
    monkeypatch.setattr(d.watch, "this_host", lambda: "contabo")
    monkeypatch.setattr(d.watch, "fetch_tasks", lambda: [])
    monkeypatch.setattr(d.watch, "collect_runs", lambda *a, **k: r["runs"])
    monkeypatch.setattr(d.time, "time", lambda: r["now"])
    monkeypatch.setattr(d, "available_mb", lambda: r["mb"])
    monkeypatch.setattr(d.rename_service, "_blocked", lambda p: "busy" if r["busy"] else None)
    def type_line(p, line):
        assert p == "runwatch-contabo"
        r["typed"].append(line)
        return r["result"]
    monkeypatch.setattr(d.rename_service, "type_rename", type_line)
    def tmux(*args):
        r["calls"].append(args)
        if args[0] == "has-session":
            assert args[-1] == "=runwatch-contabo"
            return r["alive"]
        if args[0] == "list-sessions":
            return r["server"]
        if args[0] == "new-session":
            r["alive"] = True
        elif args[0] == "kill-session":
            assert args[-1] == "=runwatch-contabo"
            r["alive"] = False
        else:
            pytest.fail(str(args))
        return True
    monkeypatch.setattr(d, "tmux", tmux)
    r["path"] = tmp_path / "contabo" / "driver.json"
    r["state"] = lambda: json.loads(r["path"].read_text())
    return r


def run(state="running", tid="task-12345678"):
    return dict(task=tid, state=state, runner="claude", model=None, owner=None,
                title="fixture", idle_s=999, started="", status="in_progress")


def test_idle_start_and_stop(rig):
    r = rig
    d.tick()
    assert not r["calls"]
    r["runs"] = [run()]
    d.tick()
    launch = next(c for c in r["calls"] if c[0] == "new-session")
    assert launch[launch.index("-c") + 1] == str(d.ROOT)
    env = [launch[i+1] for i, x in enumerate(launch) if x == "-e"]
    assert "RUN_WATCH_CLOSE_AFTER_S=60" in env
    assert "RUN_WATCH_STATE_DIR=" + str(r["path"].parent.parent) in env
    assert "RUN_WATCH_SID=" + r["state"]()["sid"] in env
    assert len(r["state"]()["sid"]) == 8
    r["runs"] = [run("done")]
    d.tick()
    assert r["state"]()["last_end_at"] == 1000
    r["now"] += 59
    d.tick()
    assert r["alive"]
    r["now"] += 1
    d.tick()
    assert not r["alive"]
    assert r["state"]()["start_count"] == 0


@pytest.mark.parametrize("field,value", [("server", False), ("mb", 699)])
def test_refusal_retries(rig, field, value):
    rig["runs"] = [run()]
    rig[field] = value
    d.tick()
    assert rig["state"]()["start_count"] == 0
    assert not any(c[0] == "new-session" for c in rig["calls"])
    rig.update(server=True, mb=1000)
    d.tick()
    assert rig["state"]()["start_count"] == 1


def test_restart_give_up(rig):
    rig["runs"] = [run()]
    d.tick()
    sid = rig["state"]()["sid"]
    rig["alive"] = False
    d.tick()
    assert rig["state"]()["sid"] != sid
    rig["alive"] = False
    d.tick()
    d.tick()
    assert sum(c[0] == "new-session" for c in rig["calls"]) == 2
    notice = rig["path"].parent.parent / "steward/contabo/open.md"
    assert len(notice.read_text().splitlines()) == 1


def test_hub_failure_untouched(rig, monkeypatch, capsys):
    d.tick()
    before = rig["path"].read_bytes()
    def fail():
        raise d.watch.HubUnreachable("secret DSN")
    monkeypatch.setattr(d.watch, "fetch_tasks", fail)
    capsys.readouterr()
    assert d.tick() == 0
    assert capsys.readouterr().out == "hub unreachable\n"
    assert rig["path"].read_bytes() == before
    assert not rig["calls"]


def test_batch_busy_rename_priority_and_retry(rig):
    r = rig
    r["runs"] = [run()]
    d.tick()
    d.tick()
    assert not r["typed"]
    r["runs"] = [run("quiet")]
    r["busy"] = True
    d.tick()
    r["now"] += 60
    d.tick()
    assert r["state"]()["pending_out"]
    r["busy"] = False
    d.tick()
    assert len(r["typed"]) == 1 and r["typed"][0].startswith("/rename ")
    assert r["state"]()["pending_out"]
    r["result"] = "held"
    d.tick()
    assert r["state"]()["pending_out"]
    r["result"] = "renamed"
    d.tick()
    assert r["typed"][-1] == "runs: 12345678 เงียบ"
    assert not r["state"]()["pending_out"]
    total = len(r["typed"])
    d.tick()
    assert len(r["typed"]) == total


def test_summary_limit_and_words():
    for event, word in d.WORDS.items():
        assert d.event_line([f"00:00Z {event} task-12345678 extra"]) == f"runs: 12345678 {word}"
    line = d.event_line(["00:00Z start task-12345678 extra"] * 20)
    assert len(line) <= 100 and line.endswith(" more")


def test_final_events_flush_before_stop(rig, monkeypatch, capsys):
    r = rig
    monkeypatch.setenv("RUN_WATCH_BATCH_S", "120")
    r.update(now=3 * 3600 + 31 * 60,
             runs=[run(tid="task-11111111"), run(tid="task-22222222")])
    d.tick()
    r.update(now=3 * 3600 + 32 * 60,
             runs=[run("done", "task-11111111"), run(tid="task-22222222")])
    d.tick()
    assert r["state"]()["follower"]["pending"]
    r.update(now=3 * 3600 + 34 * 60,
             runs=[run("done", "task-11111111"), run("dead", "task-22222222")])
    before = len(r["typed"])
    d.tick()
    assert len(r["typed"]) == before + 1
    assert r["typed"][-1].startswith("/rename ")
    assert len(r["state"]()["pending_out"]) == 2
    assert not r["state"]()["follower"]["pending"]
    assert r["state"]()["follower"]["window_start"] is None
    r["now"] += 60  # 03:35: close deadline, but final events still need typing.
    d.tick()
    assert r["alive"]
    assert r["typed"][-1] == "runs: 11111111 เสร็จ; 22222222 ตาย"
    assert not r["state"]()["pending_out"]
    assert "reason=flush" in capsys.readouterr().out
    r["now"] += 60
    d.tick()
    assert not r["alive"]
    assert r["state"]()["flush_ticks"] == 0


@pytest.mark.parametrize("blocked", ["busy", "held"])
def test_stop_flush_capped_at_three_ticks(rig, blocked):
    r = rig
    r["runs"] = [run()]
    d.tick()
    r.update(runs=[run("done")], busy=blocked == "busy",
             result="held" if blocked == "held" else "renamed")
    d.tick()
    # End-of-cycle release bypasses even an unexpired batch window.
    assert r["state"]()["pending_out"]
    assert not r["state"]()["follower"]["pending"]
    for count in range(1, 4):
        r["now"] += 60
        d.tick()
        assert r["alive"]
        assert r["state"]()["flush_ticks"] == count
    r["now"] += 60
    d.tick()
    assert not r["alive"]
    assert r["state"]()["flush_ticks"] == 0


def test_multiple_events_accumulate_between_ticks(rig):
    rig["runs"] = [run()]
    d.tick()
    rig["runs"] = [run("done"), run(tid="task-aaaaaaaa")]
    d.tick()
    assert not rig["typed"]
    rig["now"] += 30
    rig["runs"] = [run("done"), run("done", "task-aaaaaaaa"),
                   run(tid="task-bbbbbbbb")]
    d.tick()
    assert not rig["typed"]
    rig["now"] += 30
    d.tick()
    assert len(rig["typed"]) == 1
    assert rig["typed"][0] == (
        "runs: 12345678 เสร็จ; aaaaaaaa เริ่ม; aaaaaaaa เสร็จ; bbbbbbbb เริ่ม")
    assert not rig["state"]()["pending_out"]


def test_dry_run_no_writes_including_ack_and_give_up(rig, capsys):
    rig["runs"] = [run()]
    d.main(["tick", "--dry-run"])
    assert not rig["path"].exists()
    assert not any(c[0] == "new-session" for c in rig["calls"])
    d.tick()
    rig["alive"] = False
    d.tick()
    rig["alive"] = False
    rig["runs"].append(run("failed", "task-ffffffff"))
    before = rig["path"].read_bytes()
    d.tick(dry_run=True)
    assert rig["path"].read_bytes() == before
    assert not rig["path"].with_name("ack.json").exists()
    assert not (rig["path"].parent.parent / "steward").exists()
    assert "give_up" in capsys.readouterr().out


def test_second_read_blocks_typing(rig, monkeypatch):
    rig["runs"] = [run()]
    d.tick()
    rig["runs"] = [run("quiet")]
    answers = iter([None, "draft"])
    monkeypatch.setattr(d.rename_service, "_blocked", lambda p: next(answers))
    d.tick()
    assert not rig["typed"]


def test_dry_run_rename_and_stop(rig, capsys):
    rig["runs"] = [run()]
    d.tick()
    before = rig["path"].read_bytes()
    rig["runs"] = [run("quiet")]
    d.tick(dry_run=True)
    assert "/rename " in capsys.readouterr().out
    assert not rig["typed"]
    assert rig["path"].read_bytes() == before
    rig["runs"] = []
    d.tick()
    before = rig["path"].read_bytes()
    rig["now"] += 60
    d.tick(dry_run=True)
    assert rig["alive"]
    assert rig["path"].read_bytes() == before
    assert not any(c[0] == "kill-session" for c in rig["calls"])


def test_tmux_never_starts_server(monkeypatch):
    calls = []
    from types import SimpleNamespace
    monkeypatch.setattr(d.subprocess, "run", lambda argv, **kw:
                        calls.append(argv) or SimpleNamespace(returncode=1))
    assert not d.tmux("new-session", "-s", "runwatch-contabo")
    assert calls == [["tmux", "-N", "new-session", "-s", "runwatch-contabo"]]
