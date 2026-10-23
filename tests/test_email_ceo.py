"""Offline regression coverage for the shared LungNote transport."""
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from tools import email_ceo

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
