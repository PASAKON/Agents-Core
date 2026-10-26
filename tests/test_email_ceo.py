"""Offline regression coverage for the shared LungNote transport."""
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit
from types import SimpleNamespace
import io
import json
import os
import pwd
import subprocess
import urllib.error

import pytest

from tools import email_ceo
from lib.ceo_text import check_ceo_text, ceo_lines

ENV = dict(SUPABASE_URL="https://example.invalid", SUPABASE_SECRET_KEY="synthetic-secret",
           LUNGNOTE_USER_ID="synthetic-user")


def test_due_todos_keeps_deadline_window():
    requests = []
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
    assert email_ceo.due_todos(now, ENV, lambda req: requests.append(req) or []) == []
    query = parse_qs(urlsplit(requests[0].full_url).query)
    assert query["due_at"] == ["gte.2026-10-23T00:00:00+00:00", "lte.2026-10-24T00:00:00+00:00"]
    assert query["done"] == ["eq.false"]
    assert query["user_id"] == ["eq.synthetic-user"]
    assert query["limit"] == [str(email_ceo.FEED_MAX)]
    assert requests[0].get_method() == "GET"


def test_patch_transport():
    requests = []
    email_ceo.lungnote_request([("id", "eq.synthetic-todo")], ENV,
        lambda req: requests.append(req) or [], body={"due_at": "2026-11-01T09:00:00+07:00"})
    assert requests[0].get_method() == "PATCH"
    assert requests[0].get_header("Authorization") == "Bearer synthetic-secret"


NOW = datetime(2026, 10, 25, 18, tzinfo=timezone.utc)


def pr(repo="Agents-Core", number=447):
    return {"repository": {"nameWithOwner": f"PASAKON/{repo}"}, "number": number}


def runner_for(prs):
    def run(cmd, **kwargs):
        assert cmd == ["gh", "search", "prs", "--owner", "PASAKON", "--merged",
                       "--merged-at", "2026-10-24T18:00:00+00:00..2026-10-25T18:00:00+00:00",
                       "--limit", "1000", "--json", "number,repository"]
        assert kwargs["timeout"] == 60
        assert kwargs["check"] is True
        assert kwargs["env"]["HOME"] == pwd.getpwuid(os.getuid()).pw_dir
        return SimpleNamespace(stdout=json.dumps(prs))
    return run


def test_merged_grouping_and_ref(monkeypatch):
    posted = []
    monkeypatch.setattr(email_ceo, "_post", lambda body, **kw: posted.append(body) or {})
    result = email_ceo.feed_merged(now=NOW, env={}, runner=runner_for([
        pr(number=450), pr("Console", 7), pr(number=447), pr(number=448)]))
    assert result["sent"] == 1
    assert len(posted) == 1
    body = posted[0]
    assert body["kind"] == "done"
    assert body["ref"] == "merge-digest-2026-10-26"
    assert body["why"] == "Agents-Core 3: #447 #448 #450\nConsole 1: #7"
    assert body["title"] == "merge แล้ว 24 ชม.: 4 PR"
    assert urlsplit(body["link"]).netloc == "github.com"


@pytest.mark.parametrize("count", [0, 1, 3, 12])
def test_merged_limits(count, monkeypatch):
    posted = []
    monkeypatch.setattr(email_ceo, "_post", lambda body, **kw: posted.append(body) or {})
    prs = [pr("repository-" + str(i) + "x" * 80, n) for i in range(count) for n in range(1, 60)]
    result = email_ceo.feed_merged(now=NOW, env={}, runner=runner_for(prs))
    assert result["sent"] == bool(count)
    assert len(posted) == bool(count)
    if count:
        fields = [(k, posted[0].get(k)) for k in email_ceo.CEO_READS]
        check_ceo_text(fields)
        assert len(ceo_lines(fields)) <= 5
        assert all(len(line) <= 90 for key, line in ceo_lines(fields) if key != "link")
    if count == 12:
        assert posted[0]["why"].splitlines()[-1] == "+10 repo …"


def test_merged_duplicate_409(monkeypatch):
    class Opener:
        def open(self, req, **kwargs):
            raise urllib.error.HTTPError(req.full_url, 409, "Conflict", {},
                                         io.BytesIO(b'{"error":"duplicate"}'))
    monkeypatch.setattr(email_ceo.ask_run, "_OPENER", Opener())
    monkeypatch.setattr(email_ceo.ask_run, "load_token", lambda: "fake-token")
    monkeypatch.setattr(email_ceo.ask_run, "base_url", lambda: "https://example.invalid")
    assert email_ceo.feed_merged(now=NOW, env={}, runner=runner_for([pr()])) == {
        "sent": 1, "status": "already sent"}


@pytest.mark.parametrize("failure", [FileNotFoundError(), subprocess.CalledProcessError(1, "gh"),
                                      subprocess.TimeoutExpired("gh", 60), "bad json", "{}", "[{}]"])
@pytest.mark.parametrize("deadline_exit", [0, 2, 3])
def test_gh_failure_preserves_deadlines(monkeypatch, capsys, failure, deadline_exit):
    posted = []
    def run(*a, **kw):
        if isinstance(failure, Exception):
            raise failure
        return SimpleNamespace(stdout=failure)
    monkeypatch.setattr(email_ceo.subprocess, "run", run)
    monkeypatch.setattr(email_ceo, "due_todos", lambda *a: [{"id": "one", "text": "due", "due_at": ""}])
    def post(body, **kw):
        posted.append(body)
        if deadline_exit == 3:
            raise email_ceo.HubError("offline")
    monkeypatch.setattr(email_ceo, "_post", post)
    if deadline_exit == 2:
        monkeypatch.setattr(email_ceo, "deadline_fields", lambda todo: {"title": "x" * 91})
    assert email_ceo.main(["deadlines"]) == deadline_exit
    assert len(posted) == (deadline_exit != 2)
    assert all(body["kind"] == "deadline" for body in posted)
    assert capsys.readouterr().err.count("merged-digest unavailable; skipped") == 1


def test_no_merged(monkeypatch):
    monkeypatch.setattr(email_ceo, "feed_deadlines", lambda **kw: {"queued": 1})
    monkeypatch.setattr(email_ceo, "feed_merged", lambda **kw: pytest.fail("must skip gh"))
    assert email_ceo.main(["deadlines", "--no-merged"]) == 0


def test_dry_run_never_posts(monkeypatch, capsys):
    monkeypatch.setattr(email_ceo, "due_todos", lambda *a: [{"id": "one", "text": "due", "due_at": ""}])
    monkeypatch.setattr(email_ceo.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=json.dumps([pr()])))
    hub_dry_runs = []
    def post(body, *, dry_run=False):
        if not dry_run:
            pytest.fail("dry-run posted")
        hub_dry_runs.append(body["kind"])
        return {"ok": True}
    monkeypatch.setattr(email_ceo, "_post", post)
    assert email_ceo.main(["deadlines", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert hub_dry_runs == ["deadline"]
    assert 'merged-digest dry-run: {"kind": "done"' in output
    assert "Agents-Core 1: #447" in output
