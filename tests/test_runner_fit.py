from contextlib import contextmanager
from itertools import product
import json
from types import SimpleNamespace

import pytest

from tools import runner_fit as fit


@pytest.mark.parametrize("result,iteration,fix", product(fit.RESULTS, (0, 1), (False, True)))
def test_first_pass(result, iteration, fix):
    p = fit.build(runner="CODEX", job_type="code", result=result,
                  fail_reason="limit", iteration=iteration, reviewer_fix=fix, note="kept")
    assert p["first_pass"] == (result == "pass" and iteration == 0 and not fix)
    assert p["runner"] == "codex" and p["note"] == "kept"
    assert p["fail_reason"] == ("limit" if result == "fail" else None)


@pytest.mark.parametrize("fields", [dict(result="bad"), dict(job_type="bad"),
    dict(pct_done=-1), dict(pct_done=101), dict(pct_done=1.5), dict(pct_done=True),
    dict(result="fail"), dict(first_pass=True)])
def test_invalid(fields):
    with pytest.raises(ValueError):
        fit.build(**(dict(runner="codex", job_type="code", result="pass") | fields))


@pytest.mark.parametrize("runner,model,bucket", [("agy", "gemini-3.8-flash-high", "agy-gemini"),
    ("codex", None, "codex"), ("claude", "claude-haiku-5-5", "claude")])
def test_bucket(runner, model, bucket):
    assert fit.bucket_for(runner, model, fit.load_plans()) == bucket


def test_from_task():
    events = [dict(kind="status_in_progress", ts="2026-10-13T12:00:00Z"),
              dict(kind="status_review", ts="2026-10-13T12:02:36Z")]
    p = fit.from_task(dict(touches='["a"]', description="fix", iteration=1), events,
                      job_type="fix", result="pass")
    assert p["minutes"] == 2.6 and p["size"] == "S"
    assert p["runner"] == "claude" and p["source"] == "delegate"
    assert not p["first_pass"]
    assert fit.from_task({}, [], job_type="code", result="redo")["minutes"] is None


@pytest.fixture
def hub(monkeypatch):
    writes = []
    conn = SimpleNamespace(execute=lambda *a: SimpleNamespace(fetchall=lambda: []))
    @contextmanager
    def get_conn():
        yield conn
    monkeypatch.setattr(fit.db, "get_conn", get_conn)
    monkeypatch.setattr(fit.db, "get_task", lambda _: dict(runner="codex"))
    monkeypatch.setattr(fit.db, "log_event", lambda *args: writes.append(args))
    return writes, conn


def test_cli(hub, capsys, monkeypatch):
    writes, conn = hub
    assert fit.main(["task", "task-12345678", "--job", "tests", "--result", "pass"]) == 0
    assert len(writes) == 1 and writes[0][3] == "runner_fit"
    assert json.loads(capsys.readouterr().out)["first_pass"]
    assert fit.main(["manual", "--runner", "agy", "--job", "code", "--result", "pass", "--dry-run"]) == 0
    assert len(writes) == 1
    capsys.readouterr()
    assert fit.main(["manual", "--runner", "agy", "--job", "bad", "--result", "pass"]) == 2
    assert "job_type" in capsys.readouterr().err
    def unavailable(*a, **kw):
        raise fit.db.HubUnavailable("offline")
    monkeypatch.setattr(fit.db, "get_task", unavailable)
    assert fit.main(["task", "t", "--job", "code", "--result", "pass"]) == 3
    assert "offline" in capsys.readouterr().err


def test_list(hub, capsys):
    _, conn = hub
    calls = []
    def execute(sql, params):
        calls.append((sql, params))
        return SimpleNamespace(fetchall=lambda: [dict(payload='{"runner":"codex"}')])
    conn.execute = execute
    assert fit.main(["list", "--since", "2026-10-13"]) == 0
    assert json.loads(capsys.readouterr().out) == dict(runner="codex")
    assert "ORDER BY ts, id" in calls[0][0]
    assert calls[0][1] == ("runner_fit", "2026-10-13")
