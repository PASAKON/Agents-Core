"""scripts/hook-rename-nudge.py -- every-N-turns "does the name still match the
job?" line for interactive C-level sessions (CEO order 2026-10-13).

Every case points RENAME_NUDGE_STATE_DIR at tmp_path, never the real state/.
"""
from __future__ import annotations

import importlib.util
import io
import json
import time
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "hookrename", ROOT / "scripts" / "hook-rename-nudge.py"
)
hookrename = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hookrename)

CLEAR = ("CXO_SESSION", "CTO_SESSION", "CXO_ROLE", "CXO_SESSION_ID",
         "CTO_SESSION_ID", "WORKER_TASK_ID", "CLAUDE_CODE_ENTRYPOINT",
         "RENAME_NUDGE_N")


def _env(monkeypatch, tmp_path, **env):
    for var in CLEAR:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("RENAME_NUDGE_STATE_DIR", str(tmp_path / "state"))
    base = {"CXO_SESSION": "1", "CXO_ROLE": "cto", "CTO_SESSION_ID": "abcd1234",
            "CLAUDE_CODE_ENTRYPOINT": "cli"}
    base.update(env)
    for k, v in base.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)


def _turn(monkeypatch, *, session_id="s1", cwd="/opt/MoonieXHQ/Agents/Core",
          raw=None) -> tuple[int, str]:
    text = raw if raw is not None else json.dumps(
        {"session_id": session_id, "cwd": cwd, "prompt": "hi"})
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    out = io.StringIO()
    with redirect_stdout(out):
        rc = hookrename.main()
    return rc, out.getvalue()


def test_nudges_every_20_turns_and_is_silent_otherwise(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    fired = []
    for i in range(1, 41):
        rc, out = _turn(monkeypatch)
        assert rc == 0
        if out:
            fired.append(i)
            assert out.count("\n") == 1
            assert "does the session name still match the current job" in out
    assert fired == [20, 40]


def test_interval_override(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, RENAME_NUDGE_N="3")
    outs = [_turn(monkeypatch)[1] for _ in range(6)]
    assert [bool(o) for o in outs] == [False, False, True, False, False, True]


def test_sessions_count_separately(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, RENAME_NUDGE_N="2")
    assert _turn(monkeypatch, session_id="a")[1] == ""
    assert _turn(monkeypatch, session_id="b")[1] == ""
    assert _turn(monkeypatch, session_id="a")[1] != ""


def test_shows_last_recorded_name(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, RENAME_NUDGE_N="1")
    locks = tmp_path / "state" / "locks"
    locks.mkdir(parents=True)
    (locks / "cto-abcd1234.topic").write_text("⏸ LAST BELL รอ CEO ตอบ 4 ข้อ")
    out = _turn(monkeypatch)[1]
    assert 'last set: "⏸ LAST BELL รอ CEO ตอบ 4 ข้อ"' in out


def test_no_recorded_name_still_nudges(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, RENAME_NUDGE_N="1", CTO_SESSION_ID=None)
    out = _turn(monkeypatch)[1]
    assert out.startswith("[rename nudge] turn 1 — does")


def _assert_exempt(monkeypatch, tmp_path, **kw):
    for _ in range(3):
        rc, out = _turn(monkeypatch, **kw)
        assert (rc, out) == (0, "")
    assert not (tmp_path / "state" / "rename-nudge-counters.json").exists()


def test_cto_session_alone_counts_as_c_level(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, CXO_SESSION=None, CTO_SESSION="1",
         RENAME_NUDGE_N="1")
    assert _turn(monkeypatch)[1] != ""


def test_plain_session_is_exempt(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, CXO_SESSION=None, RENAME_NUDGE_N="1")
    _assert_exempt(monkeypatch, tmp_path)


def test_sompong_is_exempt(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, CXO_ROLE="coo", RENAME_NUDGE_N="1")
    _assert_exempt(monkeypatch, tmp_path)


def test_worker_env_is_exempt(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, WORKER_TASK_ID="task-1", RENAME_NUDGE_N="1")
    _assert_exempt(monkeypatch, tmp_path)


def test_worker_worktree_cwd_is_exempt(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, RENAME_NUDGE_N="1")
    _assert_exempt(monkeypatch, tmp_path,
                   cwd="/opt/MoonieXHQ/Agents/Core/worktrees/x__dev__task-1")


def test_headless_is_exempt(monkeypatch, tmp_path):
    for entry in ("sdk-cli", "sdk-py", "mcp"):
        _env(monkeypatch, tmp_path, CLAUDE_CODE_ENTRYPOINT=entry,
             RENAME_NUDGE_N="1")
        _assert_exempt(monkeypatch, tmp_path)


def test_bad_input_is_silent(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, RENAME_NUDGE_N="1")
    for raw in ("", "not json", "[]", json.dumps({"cwd": "/x"})):
        assert _turn(monkeypatch, raw=raw) == (0, "")


def test_unwritable_state_is_silent(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, RENAME_NUDGE_N="1")
    blocker = tmp_path / "state"
    blocker.write_text("a file where the state dir should be")
    assert _turn(monkeypatch) == (0, "")


def test_stale_sessions_are_pruned(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    path = tmp_path / "state" / "rename-nudge-counters.json"
    path.parent.mkdir(parents=True)
    old = int(time.time()) - 31 * 86400
    path.write_text(json.dumps({"old": {"n": 5, "t": old},
                                "junk": 7,
                                "fresh": {"n": 2, "t": int(time.time())}}))
    _turn(monkeypatch, session_id="s1")
    kept = json.loads(path.read_text())
    assert set(kept) == {"fresh", "s1"}
    assert kept["s1"]["n"] == 1
    assert not list(path.parent.glob("*.tmp"))
