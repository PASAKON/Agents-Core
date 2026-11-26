"""Socket-free coverage of job replacement and real CLI refusal exit status."""
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from test_ask_run_questions import QID, CREATED, ROOT, _argv, _mcp_args
from tools import ask_run


def payload(job=None):
    args = _mcp_args()
    if job is not None:
        args["job"] = job
    return ask_run.prepare_question(ask_run._mcp_question_namespace(args), {})


def card(job="release", **changes):
    return {"id": QID, "status": "pending", "requester": {"session": "cto-t"},
            "why": f"job: {job}\nContext", "created_at": datetime.now(timezone.utc).isoformat(),
            **changes}


def transport(monkeypatch, rows, cancel="cancelled"):
    calls = []

    def call(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if method == "GET":
            return {"questions": rows}
        if path.endswith("/cancel"):
            return {"id": path.split("/")[-2], "status": cancel}
        return CREATED

    monkeypatch.setattr(ask_run, "_call", call)
    return calls


def test_job_cancels_all_matching_pending_cards_and_trims(monkeypatch):
    second = QID[:-4] + "abcd"
    calls = transport(monkeypatch, [card(), card(id=second), card(job="other"),
                                   card(requester={"session": "cto-other"}), card(status="answered")])
    body = payload("release")
    body["why"] = "\n".join(["x" * 90] * 4)
    result = ask_run.submit_question(body)
    assert result["id"] == QID
    assert [c[1] for c in calls[1:-1]] == [f"{ask_run.QUESTIONS_PATH}/{q}/cancel" for q in (QID, second)]
    sent = calls[-1][2]["body"]
    assert sent["why"].startswith(f"แทน {QID} (ยกเลิกแล้ว)")
    assert "job: release" in sent["why"].splitlines()
    assert len(sent["why"].splitlines()) <= 4
    assert all(len(line) <= 90 for line in sent["why"].splitlines())
    assert "job" not in sent  # persisted in the existing why column


def test_cancellation_failure_stops_creation(monkeypatch):
    calls = transport(monkeypatch, [card()], cancel="answered")
    with pytest.raises(ask_run.HubError, match="cancellation was not confirmed"):
        ask_run.submit_question(payload("release"))
    assert len(calls) == 2


def test_without_job_warns_only_recent_own_pending(monkeypatch, capsys):
    old = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
    calls = transport(monkeypatch, [card(), card(id=QID[:-4] + "abcd", created_at=old),
                                   card(id=QID[:-4] + "aaaa", requester={"session": "other"})])
    assert ask_run.submit_question(payload())["id"] == QID
    err = capsys.readouterr().err
    assert QID in err and "abcd" not in err and "aaaa" not in err
    assert len(calls) == 2


def test_job_flows_through_cli_and_mcp(monkeypatch, capsys):
    calls = transport(monkeypatch, [])
    assert ask_run.main(_argv(dry=False) + ["--job", "release"]) == 0
    assert QID in capsys.readouterr().out
    assert "job: release" in calls[-1][2]["body"]["why"]
    result = ask_run.mcp_ask_ceo({**_mcp_args(), "job": "release", "dry_run": False}, {})
    assert result["id"] == QID
    assert "job: release" in calls[-1][2]["body"]["why"]


def test_warning_is_successful_cli_submission(monkeypatch, capsys):
    transport(monkeypatch, [card()])
    assert ask_run.main(_argv(dry=False)) == 0
    out, err = capsys.readouterr()
    assert QID in out and "warning:" in err and QID in err


def test_failed_submission_exits_nonzero_with_reason(monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise ask_run.HubError("submission failed")
    monkeypatch.setattr(ask_run, "submit_question", fail)
    assert ask_run.main(_argv(dry=False)) == ask_run.EXIT_HUB
    out, err = capsys.readouterr()
    assert not out and "submission failed" in err


def test_dry_run_never_cancels_or_lists(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("dry run made a network call")
    monkeypatch.setattr(ask_run, "_call", forbidden)
    assert ask_run.main(_argv() + ["--job", "release"]) == 0


def test_missing_live_media_result_is_failure(monkeypatch, capsys):
    body = payload()
    body["media"] = [{"id": "test"}]
    monkeypatch.setattr(ask_run, "prepare_question", lambda *a, **kw: body)
    monkeypatch.setattr(ask_run, "send_media_question", lambda *a, **kw: (body, None, []))
    assert ask_run.main(_argv(dry=False) + ["--media", "one.png"]) == ask_run.EXIT_HUB
    out, err = capsys.readouterr()
    assert not out and "returned no result" in err
    with pytest.raises(ask_run.HubError, match="returned no result"):
        ask_run.mcp_ask_ceo({**_mcp_args(), "media": [{"path": "one.png"}], "dry_run": False}, {})


@pytest.mark.parametrize("job", ["", "bad\nkey", "x" * 65, 42])
def test_invalid_job_refused(job):
    ns = ask_run._mcp_question_namespace(_mcp_args())
    ns.job = job
    with pytest.raises(ask_run.Refused, match="invalid_job"):
        ask_run.prepare_question(ns, {})


def test_pick_many_one_media_process_exits_nonzero(tmp_path):
    media = tmp_path / "one.png"
    media.write_bytes(b"\x89PNG\r\n\x1a\n")
    argv = _argv({"options": []}, dry=False) + ["--pick", "many", "--media", str(media)]
    result = subprocess.run([sys.executable, str(ROOT / "tools/ask_run.py"), *argv],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == ask_run.EXIT_REFUSED
    assert "invalid_pick: one item" in result.stderr
    assert not result.stdout.strip()
