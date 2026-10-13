from contextlib import contextmanager
import csv
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

from tools import quota_handoff as q

FIXTURES = Path(__file__).parent / "fixtures" / "quota_handoff"


@pytest.fixture
def fixture_dir(tmp_path):
    return Path(shutil.copytree(FIXTURES, tmp_path / "fixtures"))


def test_fixture_constant(fixture_dir):
    expected = {}
    with (fixture_dir / "limit_strings.tsv").open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            expected.setdefault(row["runner"], []).append(row["text"])
    assert q.LIMIT_STRINGS == {k: tuple(v) for k, v in expected.items()}
    assert "jules" not in q.LIMIT_STRINGS


def test_agy_strings(fixture_dir):
    with (fixture_dir / "limit_strings.tsv").open() as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["runner"] == "agy":
                (fixture_dir / "agy-events.log").write_text("starting\n" + row["text"].swapcase())
                assert q.detect("agy", fixture_dir) == row["text"]


@pytest.mark.parametrize("needle", q.LIMIT_STRINGS["codex"])
@pytest.mark.parametrize("kind", ["error", "turn.failed", "item.completed", "stderr", "final", "report"])
def test_codex_detection(tmp_path, needle, kind):
    report = ""
    if kind == "report":
        report = needle
    elif kind == "final":
        (tmp_path / "codex-final.txt").write_text(needle)
    else:
        line = needle if kind == "stderr" else json.dumps(dict(type=kind, item=dict(type="agent_message", text=needle)))
        (tmp_path / "codex-events.jsonl").write_text(line + "\n")
    assert q.detect("codex", tmp_path, report) == (None if kind == "item.completed" else needle)


@pytest.fixture
def mocked(monkeypatch, tmp_path):
    state = SimpleNamespace(task=dict(runner="codex", status="in_progress", branch="work",
        project="p", role="developer", title="Fix", description="original\nbrief", touches='["tools/a.py"]'),
        logs=[], updates=[], fields=[], creates=[], delegates=[], git=[], remote=True,
        create_result="task-abcdef12", report="")
    monkeypatch.setattr(q.db, "get_task", lambda _: state.task)
    @contextmanager
    def get_conn():
        yield SimpleNamespace(execute=lambda *a: SimpleNamespace(fetchall=lambda: []))
    monkeypatch.setattr(q.db, "get_conn", get_conn)
    monkeypatch.setattr(q.db, "log_event", lambda *a: state.logs.append(a))
    monkeypatch.setattr(q.db, "update_status", lambda *a, **kw: state.updates.append((a, kw)))
    monkeypatch.setattr(q.db, "set_fields", lambda *a, **kw: state.fields.append((a, kw)))
    def dispatch(name, **kw):
        state.creates.append((name, kw))
        return state.create_result
    monkeypatch.setattr(q.org_tools_registry, "dispatch_sync", dispatch)
    def git(args, **kw):
        state.git.append(args)
        return SimpleNamespace(returncode=0, stdout=state.report if args[1] == "show" else ("abc\trefs/heads/work\n" if state.remote else ""))
    monkeypatch.setattr(q.subprocess, "run", git)
    async def delegate(task_id):
        state.delegates.append(task_id)
    monkeypatch.setitem(sys.modules, "tools.delegate", SimpleNamespace(delegate_task=delegate))
    import tools
    monkeypatch.setattr(tools, "delegate", sys.modules["tools.delegate"], raising=False)
    launch = tmp_path / ".launch-task-12345678"
    launch.mkdir()
    (launch / "codex-events.jsonl").write_text(json.dumps(dict(type="error", message=q.LIMIT_STRINGS["codex"][0])))
    state.root = tmp_path
    return state


def test_happy(mocked):
    s = mocked
    result = q.handoff("task-12345678", pct_done=80, root=s.root)
    assert result == dict(old="task-12345678", new="task-abcdef12", matched=q.LIMIT_STRINGS["codex"][0], pct_done=80, branch="work")
    assert len(s.logs) == 1
    payload = s.logs[0][4]
    assert (payload["result"], payload["fail_reason"], payload["pct_done"]) == ("fail", "limit", 80)
    assert payload["why"] == "quota-handoff to task-abcdef12"
    assert s.updates[0][0] == ("task-12345678", "failed")
    assert "quota-handoff → task-abcdef12" in s.updates[0][1]["review"]
    create = s.creates[0][1]
    lines = create["description"].splitlines()
    assert lines[0].startswith("override: quota-handoff — codex")
    assert "80% done" in lines[0]
    assert lines[1] == "Start: git fetch origin work && git merge --no-edit origin/work. Keep the partial work; do not redo it."
    assert create["description"].endswith("\n\noriginal\nbrief")
    assert create["touches"] == '["tools/a.py"]' and create["depends_on"] == ""
    assert s.fields == [(("task-abcdef12",), dict(runner="claude", runner_model=None))]
    assert s.delegates == ["task-abcdef12"]


@pytest.mark.parametrize("case,reason", [("no_limit", "no limit text"), ("remote", "partial work is not on origin"),
    ("claude", "runner"), ("done", "done"), ("merged", "merged"), ("jules", "exact words from the Jules page")])
def test_refusals(mocked, case, reason):
    s = mocked
    if case == "no_limit":
        (s.root / ".launch-task-12345678/codex-events.jsonl").write_text("")
    elif case == "remote":
        s.remote = False
    elif case in ("claude", "jules"):
        s.task["runner"] = case
    else:
        s.task["status"] = case
    with pytest.raises(ValueError, match=reason):
        q.handoff("task-12345678", root=s.root)
    assert not (s.logs or s.updates or s.creates or s.fields or s.delegates)


def test_dry_run(mocked):
    s = mocked
    result = q.handoff("task-12345678", root=s.root, dry_run=True, pct_done=0)
    assert "0% done" in result["create"]["description"]
    assert result["runner_fit"]["fail_reason"] == "limit"
    assert not (s.logs or s.updates or s.creates or s.fields or s.delegates)


def test_registry_refusal(mocked):
    mocked.create_result = "ERROR: creation refused"
    with pytest.raises(ValueError, match="creation refused"):
        q.handoff("task-12345678", root=mocked.root)
    assert not (mocked.logs or mocked.updates or mocked.fields or mocked.delegates)


def test_jules_explicit_no_delegate(mocked):
    mocked.task["runner"] = "jules"
    q.handoff("task-12345678", root=mocked.root, limit_text="Exact page wording", delegate=False)
    assert mocked.logs[0][4]["matched"] == "Exact page wording"
    assert not mocked.delegates


def test_cli(monkeypatch, capsys):
    monkeypatch.setattr(q, "handoff", lambda **kw: dict(old=kw["task_id"]))
    assert q.main(["task-12345678", "--no-delegate"]) == 0
    assert json.loads(capsys.readouterr().out)["old"] == "task-12345678"
    for exc, code in [(ValueError("refused"), 2), (q.db.HubUnavailable("offline"), 3)]:
        def fail(**kw):
            raise exc
        monkeypatch.setattr(q, "handoff", fail)
        assert q.main(["task-12345678"]) == code
        assert str(exc) in capsys.readouterr().err
