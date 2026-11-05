"""Driver integration with fake hub, tmux, clock, memory and pane."""
import json
import re

import pytest

from tools import run_watch_driver as d


@pytest.fixture
def rig(monkeypatch, tmp_path):
    for key in list(d.os.environ):
        if key.startswith("RUN_WATCH_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("RUN_WATCH_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("RUN_WATCH_STEWARD_DIR", str(tmp_path / "steward"))
    monkeypatch.setenv("RUN_WATCH_BATCH_S", "60")
    r = dict(now=1000, runs=[], alive=False, server=True, mb=1000,
             busy=False, calls=[], typed=[], result="renamed")
    monkeypatch.setattr(d.watch, "this_host", lambda: "contabo")
    monkeypatch.setattr(d.watch, "fetch_tasks", lambda: [])
    monkeypatch.setattr(d.watch, "collect_runs", lambda *a, **k: r["runs"])
    monkeypatch.setattr(d.time, "time", lambda: r["now"])
    monkeypatch.setattr(d, "available_mb", lambda: r["mb"])
    monkeypatch.setattr(d, "PROJECTS", tmp_path / "projects")
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

    def write_transcript(size):
        """The conversation claude keeps for the driver's uuid, `size` bytes long."""
        file = d.PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", str(d.ROOT)) / (r["state"]()["uuid"] + ".jsonl")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"x" * size)
    r["write_transcript"] = write_transcript
    return r


def run(state="running", tid="task-12345678"):
    return dict(task=tid, state=state, runner="claude", model=None, owner=None,
                title="fixture", idle_s=999, started="", status="in_progress")


def launches(r):
    """The claude flags of every `tmux new-session` so far, from --model on."""
    return [list(c[c.index("--model"):]) for c in r["calls"] if c[0] == "new-session"]


def remote_control_name(flags):
    return flags[flags.index("--remote-control") + 1]


def test_idle_host_starts_one_session_and_never_stops_it(rig):
    r = rig
    d.tick()                                    # no runs and no session: started anyway
    launch = next(c for c in r["calls"] if c[0] == "new-session")
    assert launch[launch.index("-c") + 1] == str(d.ROOT)
    env = [launch[i+1] for i, x in enumerate(launch) if x == "-e"]
    assert "RUN_WATCH_BATCH_S=60" in env
    assert "RUN_WATCH_STATE_DIR=" + str(r["path"].parent.parent) in env
    assert not any(e.startswith("RUN_WATCH_SID=") for e in env)
    assert len(r["state"]()["uuid"]) == 36
    assert remote_control_name(launches(r)[0]) == "\U0001F310 Watch Runs: 0⚪"
    r["runs"] = [run()]
    d.tick()
    r["runs"] = [run("done")]
    d.tick()
    for _ in range(4):                          # hours with no run: still no kill
        r["now"] += 3600
        d.tick()
    assert r["alive"]
    assert not any(c[0] == "kill-session" for c in r["calls"])
    assert len(launches(r)) == 1
    assert r["state"]()["start_count"] == 0     # up for hours: earlier starts are forgotten


def test_first_start_creates_the_conversation_and_every_later_start_resumes_it(rig):
    r = rig
    d.tick()
    uuid = r["state"]()["uuid"]
    first = launches(r)[0]
    assert first[-2:] == ["--session-id", uuid] and "-r" not in first
    r["write_transcript"](10)                   # claude wrote the conversation
    r["alive"] = False                          # and the session died
    d.tick()
    second = launches(r)[1]
    assert second[-2:] == ["-r", uuid] and "--session-id" not in second
    assert r["state"]()["uuid"] == uuid
    assert remote_control_name(second) == remote_control_name(first)
    assert second[second.index("-n") + 1] == remote_control_name(second)


def test_a_start_with_no_stored_conversation_creates_it_again(rig):
    r = rig
    d.tick()
    uuid = r["state"]()["uuid"]
    r["alive"] = False                          # died before claude wrote anything: -r would fail
    d.tick()
    assert [f[-2:] for f in launches(r)] == [["--session-id", uuid]] * 2


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
    uuid = rig["state"]()["uuid"]
    rig["alive"] = False
    d.tick()
    assert rig["state"]()["uuid"] == uuid       # a restart keeps the conversation
    rig["alive"] = False
    d.tick()
    d.tick()
    assert sum(c[0] == "new-session" for c in rig["calls"]) == 2
    notice = rig["path"].parent.parent / "steward/contabo/open.md"
    assert len(notice.read_text().splitlines()) == 1
    rig["now"] += 3599                          # gave up: no start before RUN_WATCH_RETRY_S
    d.tick()
    assert sum(c[0] == "new-session" for c in rig["calls"]) == 2
    rig["now"] += 1
    d.tick()
    assert sum(c[0] == "new-session" for c in rig["calls"]) == 3
    assert rig["state"]()["start_count"] == 1


def test_hub_failure_untouched(rig, monkeypatch, capsys):
    d.tick()
    rig["calls"].clear()
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


def test_final_events_are_typed_and_the_session_stays_up(rig, monkeypatch):
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
    r["now"] += 60  # no run is left, so the final events are typed at once
    d.tick()
    assert r["typed"][-1] == "runs: 11111111 เสร็จ; 22222222 ตาย"
    assert not r["state"]()["pending_out"]
    r["now"] += 3600
    d.tick()
    assert r["alive"]
    assert not any(c[0] == "kill-session" for c in r["calls"])


@pytest.mark.parametrize("blocked", ["busy", "held"])
def test_events_wait_for_a_ready_prompt_however_long(rig, blocked):
    r = rig
    r["runs"] = [run()]
    d.tick()
    r.update(runs=[run("done")], busy=blocked == "busy",
             result="held" if blocked == "held" else "renamed")
    d.tick()
    assert r["state"]()["pending_out"]
    for _ in range(6):                          # no flush cap: the session is not closing
        r["now"] += 60
        d.tick()
        assert r["alive"]
    assert r["state"]()["pending_out"]
    r.update(busy=False, result="renamed")
    d.tick()                                    # the rename first
    d.tick()
    assert r["typed"][-1] == "runs: 12345678 เสร็จ"
    assert not r["state"]()["pending_out"]


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


def test_dry_run_rename_and_no_stop(rig, capsys):
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


def test_dead_and_failed_release_without_waiting_for_batch_window(rig, monkeypatch):
    r = rig
    monkeypatch.setenv("RUN_WATCH_BATCH_S", "120")
    r["runs"] = [run(tid="task-11111111"), run(tid="task-22222222")]
    d.tick()
    assert not r["typed"]

    # Plain start/quiet events wait for the 120 s batch window while runs are active.
    r["now"] += 10
    r["runs"] = [run("quiet", "task-11111111"), run(tid="task-22222222"),
                 run(tid="task-33333333")]
    d.tick()
    assert len(r["typed"]) == 1 and r["typed"][-1].startswith("/rename ")
    assert not r["state"]()["pending_out"]
    assert len(r["state"]()["follower"]["pending"]) == 2

    r["now"] += 10
    d.tick()
    assert len(r["typed"]) == 1
    assert not r["state"]()["pending_out"]

    # A dead event releases the whole pending batch into pending_out immediately;
    # rename runs first on this tick, and the summary is typed on the next ready tick.
    r["now"] += 10
    r["runs"] = [run("quiet", "task-11111111"), run("dead", "task-22222222"),
                 run(tid="task-33333333")]
    d.tick()
    assert len(r["typed"]) == 2 and r["typed"][-1].startswith("/rename ")
    assert len(r["state"]()["pending_out"]) == 3
    assert not r["state"]()["follower"]["pending"]
    assert r["state"]()["follower"]["window_start"] is None

    r["now"] += 10
    d.tick()
    assert r["typed"][-1] == "runs: 11111111 เงียบ; 33333333 เริ่ม; 22222222 ตาย"
    assert not r["state"]()["pending_out"]

    # A failed event also releases without waiting 120 s.
    r["now"] += 10
    r["runs"] = [run("quiet", "task-11111111"), run("dead", "task-22222222"),
                 run("failed", "task-33333333")]
    d.tick()
    assert r["typed"][-1].startswith("/rename ")   # the count changed: rename first
    assert len(r["state"]()["pending_out"]) == 1   # released at once, not held 120 s
    r["now"] += 10
    d.tick()
    assert r["typed"][-1] == "runs: 33333333 พัง"
    assert not r["state"]()["pending_out"]


def test_low_memory_kills_the_session_and_the_next_tick_resumes_the_same_conversation(rig):
    r = rig
    d.tick()
    uuid = r["state"]()["uuid"]
    r["write_transcript"](10)
    r["mb"] = 349                               # below RUN_WATCH_KILL_AVAIL_MB (350)
    d.tick()
    assert not r["alive"]
    assert [c for c in r["calls"] if c[0] == "kill-session"]
    assert r["state"]()["uuid"] == uuid
    assert r["state"]()["start_count"] == 0     # our own kill is not a death
    d.tick()                                    # still too little memory for a start (700)
    assert len(launches(r)) == 1
    r["mb"] = 1000
    d.tick()
    resumed = launches(r)[1]
    assert resumed[-2:] == ["-r", uuid]
    assert remote_control_name(resumed) == remote_control_name(launches(r)[0])
    assert r["state"]()["uuid"] == uuid and r["state"]()["start_count"] == 1


def test_memory_between_the_kill_and_the_start_limits_changes_nothing(rig):
    r = rig
    d.tick()
    r["mb"] = 500                               # under the 700 a start needs, over the 350 a kill needs
    d.tick()
    assert r["alive"] and not any(c[0] == "kill-session" for c in r["calls"])
    r["alive"] = False
    d.tick()
    assert len(launches(r)) == 1                # and it does not start either


def test_dry_run_never_kills(rig):
    r = rig
    d.tick()
    before = r["path"].read_bytes()
    r["mb"] = 100
    d.tick(dry_run=True)
    assert r["alive"] and not any(c[0] == "kill-session" for c in r["calls"])
    assert r["path"].read_bytes() == before


def test_compact_is_typed_only_past_the_threshold_and_before_the_next_event_line(rig, monkeypatch):
    r = rig
    monkeypatch.setenv("RUN_WATCH_COMPACT_TOKENS", "100")      # 400 bytes of transcript
    r["runs"] = [run()]
    d.tick()
    dead = [run("dead", f"task-{c * 8}") for c in "abcdef"]    # each new dead run is typed at once
    r["runs"] = [dead[0]]
    d.tick()
    assert r["typed"][-1].startswith("/rename ")               # the count changed: the rename goes first

    r["write_transcript"](399)                                 # 99 tokens: under
    r["runs"] = dead[:2]
    d.tick()
    assert r["typed"][-1] == "runs: aaaaaaaa ตาย; bbbbbbbb ตาย"
    assert "/compact" not in r["typed"]

    r["write_transcript"](400)                                 # 100 tokens: over, and nothing to say yet
    d.tick()
    assert "/compact" not in r["typed"]
    r["runs"] = dead[:3]
    d.tick()
    assert r["typed"][-1] == "/compact"                        # before the event line
    assert r["state"]()["compact_base"] == 400
    assert r["state"]()["pending_out"]
    d.tick()
    assert r["typed"][-1] == "runs: cccccccc ตาย"              # then the event, with no second compact
    assert r["typed"].count("/compact") == 1

    r["write_transcript"](400 + 399)                           # grown 399 bytes since the compaction
    r["runs"] = dead[:4]
    d.tick()
    assert r["typed"][-1] == "runs: dddddddd ตาย"
    r["write_transcript"](400 + 399 + 1)
    r["runs"] = dead[:5]
    d.tick()
    assert r["typed"][-1] == "/compact" and r["state"]()["compact_base"] == 800


def test_compact_waits_for_a_ready_prompt(rig, monkeypatch):
    r = rig
    monkeypatch.setenv("RUN_WATCH_COMPACT_TOKENS", "100")
    r["runs"] = [run()]
    d.tick()
    r["runs"] = [run("dead")]
    d.tick()                                                   # the rename
    r["write_transcript"](4000)
    r["busy"] = True
    typed = len(r["typed"])
    d.tick()
    assert len(r["typed"]) == typed
    r["busy"] = False
    d.tick()
    assert r["typed"][-1] == "/compact"
