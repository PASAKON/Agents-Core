"""scripts/gmail-notify-auth.py — the one-time Gmail consent for the Run/Relay mail notifications.

CEO 2026-10-02: every Run card and relay login request mails him. The token this script mints must
carry gmail.insert only (own mailbox, no reading, no other recipient), must belong to his account,
and must reach Infisical only on `put --stdin`. Nothing here talks to Google or Infisical: post(),
getpass and subprocess.run are replaced.

Run: .venv/bin/python -m pytest tests/test_gmail_notify_auth.py
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import urllib.parse
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("gmail_notify_auth", ROOT / "scripts" / "gmail-notify-auth.py")
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)

ACCOUNT = "ceo@example.com"
FAKE = {"GOOGLE_OAUTH_CLIENT_ID": "cid-public-1", "GOOGLE_OAUTH_CLIENT_SECRET": "csec-not-real-2"}
REFRESH = "refresh-not-real-3"


def id_token(email: str) -> str:
    claims = base64.urlsafe_b64encode(json.dumps({"email": email, "email_verified": True}).encode()).decode().rstrip("=")
    return f"h.{claims}.s"


def test_consent_url_asks_for_insert_only_with_pkce():
    url = auth.consent_url("cid", ACCOUNT, "st", "ver")
    q = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(url).query).items()}
    assert q["scope"].split() == ["https://www.googleapis.com/auth/gmail.insert", "openid", "email"]
    assert q["code_challenge_method"] == "S256"
    want = base64.urlsafe_b64encode(hashlib.sha256(b"ver").digest()).rstrip(b"=").decode()
    assert q["code_challenge"] == want
    assert q["access_type"] == "offline" and q["prompt"] == "consent" and q["login_hint"] == ACCOUNT
    assert q["redirect_uri"] == "http://localhost:8765/" and q["state"] == "st"


@pytest.mark.parametrize("pasted, why", [
    ("http://localhost:8765/?state=other&code=c", "state differs"),
    ("http://localhost:8765/?error=access_denied&state=st", "access_denied"),
    ("http://localhost:8765/?state=st", "no code"),
])
def test_a_bad_address_is_refused_with_a_reason(pasted, why):
    with pytest.raises(SystemExit) as e:
        auth.code_from_redirect(pasted, "st")
    assert why in str(e.value)


def test_the_code_comes_back_from_a_good_address():
    assert auth.code_from_redirect(" http://localhost:8765/?state=st&code=4%2Fabc&scope=x \n", "st") == "4/abc"


def test_email_of_reads_the_claim_and_survives_junk():
    assert auth.email_of(id_token(ACCOUNT)) == ACCOUNT
    assert auth.email_of("garbage") == ""


@pytest.fixture
def wired(monkeypatch):
    """consent() with Google, getpass and Infisical replaced; returns what each received."""
    seen = {"posts": [], "runs": []}
    for k, v in FAKE.items():
        monkeypatch.setenv(k, v)
    token = {"access_token": "access-not-real-4", "refresh_token": REFRESH,
             "scope": "https://www.googleapis.com/auth/gmail.insert openid email", "id_token": id_token(ACCOUNT)}
    seen["token"] = token

    def post(url, data, headers):
        seen["posts"].append(url)
        return token if url == auth.TOKEN_URL else {"id": "m1"}

    class Done:
        returncode = 0

    def run(cmd, **kw):
        seen["runs"].append((cmd, kw.get("input")))
        return Done()

    monkeypatch.setattr(auth, "post", post)
    monkeypatch.setattr(auth.subprocess, "run", run)
    monkeypatch.setattr(auth.secrets, "token_urlsafe", lambda n=16: "st")
    monkeypatch.setattr(auth.getpass, "getpass", lambda prompt="": "http://localhost:8765/?state=st&code=c")
    return seen


def test_consent_stores_the_token_on_stdin_only_and_prints_no_secret(wired, capsys):
    auth.consent(ACCOUNT)
    out = capsys.readouterr().out
    assert wired["posts"] == [auth.TOKEN_URL, auth.INSERT_URL]  # exchange, then the test mail
    (cmd, stdin), = wired["runs"]
    assert cmd[2:7] == ["put", "MoonieX-Console", "prod", "GMAIL_INSERT_REFRESH_TOKEN", "--stdin"]
    assert stdin == REFRESH + "\n"
    assert REFRESH not in " ".join(cmd)
    for value in (REFRESH, FAKE["GOOGLE_OAUTH_CLIENT_SECRET"], "access-not-real-4"):
        assert value not in out
    assert "cid-public-1" in out  # the link carries the public client id, nothing else


def test_a_consent_without_gmail_insert_stores_nothing(wired):
    wired["token"]["scope"] = "openid email"
    with pytest.raises(SystemExit, match="gmail.insert"):
        auth.consent(ACCOUNT)
    assert wired["runs"] == []


def test_a_consent_for_another_account_stores_nothing(wired):
    wired["token"]["id_token"] = id_token("someone@example.com")
    with pytest.raises(SystemExit, match="someone@example.com"):
        auth.consent(ACCOUNT)
    assert wired["runs"] == [] and wired["posts"] == [auth.TOKEN_URL]  # no test mail either


def test_a_testing_mode_client_is_called_out(wired, capsys):
    wired["token"]["refresh_token_expires_in"] = 604799
    auth.consent(ACCOUNT)
    assert "Testing" in capsys.readouterr().out
    (cmd, _), = wired["runs"]
    assert any(a.startswith("expires=20") for a in cmd)  # a real date, 6 days out
