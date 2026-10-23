import base64
import importlib.util
import io
import json
from pathlib import Path
import time
from types import SimpleNamespace
import urllib.parse

import pytest

spec = importlib.util.spec_from_file_location("gmail_broker_auth", Path(__file__).resolve().parents[1] / "scripts/gmail-broker-auth.py")
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)


def tokens(**claims):
    payload = {"email": auth.ACCOUNT, "email_verified": True, "aud": "fake-client", "nonce": "nonce",
        "iss": "https://accounts.google.com", "exp": time.time() + 1000}
    payload.update(claims)
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return {"scope": auth.SCOPE, "id_token": "synthetic." + encoded + ".synthetic", "refresh_token": "fake-refresh-secret"}


def test_consent_pkce_state_and_exact_scopes():
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(auth.consent_url("fake-client", "state", "verifier", "nonce")).query)
    assert query["scope"] == [auth.SCOPE]
    assert query["code_challenge_method"] == ["S256"] and query["state"] == ["state"]
    assert query["nonce"] == ["nonce"] and query["include_granted_scopes"] == ["false"]
    assert "verifier" not in json.dumps(query)
    assert auth.code_from_redirect("http://localhost:8765/?code=fake&state=state", "state") == "fake"


@pytest.mark.parametrize("url", ["http://localhost:8765/?code=fake&state=bad", "http://evil.test/?code=fake&state=state", "http://localhost:8765/?error=secret&state=state", "http://localhost:8765/?code=a&code=b&state=state"])
def test_bad_redirect(url):
    with pytest.raises(ValueError): auth.code_from_redirect(url, "state")


def test_token_validation_and_canonical_email_scope():
    token = tokens()
    auth.validate_tokens(token, "fake-client", "nonce")
    token["scope"] = token["scope"].replace(" email", " https://www.googleapis.com/auth/userinfo.email")
    auth.validate_tokens(token, "fake-client", "nonce")


@pytest.mark.parametrize("scope", ["", "https://mail.google.com/ openid email", auth.SCOPE + " https://mail.google.com/", auth.SCOPE + " https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.modify"])
def test_wrong_scopes_refused(scope):
    token = tokens()
    token["scope"] = scope
    with pytest.raises(ValueError): auth.validate_tokens(token, "fake-client", "nonce")


@pytest.mark.parametrize("claims", [{"email": "other@example.test"}, {"email_verified": False}, {"email_verified": None}, {"aud": "other"}, {"nonce": "other"}, {"iss": "https://evil.test"}, {"exp": 1}])
def test_wrong_identity_refused(claims):
    with pytest.raises(ValueError): auth.validate_tokens(tokens(**claims), "fake-client", "nonce")


def test_missing_refresh_token():
    token = tokens()
    del token["refresh_token"]
    with pytest.raises(ValueError): auth.validate_tokens(token, "fake-client", "nonce")


def test_pipe_only_storage(monkeypatch):
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(auth.subprocess, "run", run)
    auth.store_token(tokens())
    argv, kwargs = calls[0]
    assert argv[2:7] == ["put", "Agents-Core", "prod", auth.TOKEN_NAME, "--stdin"]
    assert "fake-refresh-secret" not in " ".join(argv)
    assert kwargs["input"] == "fake-refresh-secret\n" and kwargs["capture_output"]


def test_exchange_mocked_http(monkeypatch):
    class Opener:
        def open(self, req, timeout):
            assert req.full_url == "https://oauth2.googleapis.com/token"
            assert b"code_verifier=verifier" in req.data
            return io.BytesIO(json.dumps(tokens()).encode())
    monkeypatch.setattr(auth.urllib.request, "build_opener", lambda *args: Opener())
    assert auth.exchange("fake-client", "fake-secret", "fake-code", "verifier")["refresh_token"] == "fake-refresh-secret"


def test_exchange_errors_are_generic(monkeypatch):
    class Opener:
        def open(self, *args, **kwargs): raise RuntimeError("fake-secret")
    monkeypatch.setattr(auth.urllib.request, "build_opener", lambda *args: Opener())
    with pytest.raises(ValueError) as exc:
        auth.exchange("fake-client", "fake-secret", "fake-code", "verifier")
    assert "fake-secret" not in str(exc.value)


@pytest.mark.parametrize("valid", [True, False])
def test_full_consent_stores_only_valid_grant(monkeypatch, capsys, valid):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "fake-client")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "fake-client-secret")
    monkeypatch.setattr(auth.secrets, "token_urlsafe", lambda count: "nonce")
    monkeypatch.setattr(auth.sys, "stdin", io.StringIO("http://localhost:8765/?code=fake&state=nonce\n"))
    token = tokens() if valid else tokens(email="wrong@example.test")
    monkeypatch.setattr(auth, "exchange", lambda *args: token)
    stored = []
    monkeypatch.setattr(auth, "store_token", stored.append)
    if valid:
        auth.main(["--inner"])
        assert stored == [token]
    else:
        with pytest.raises(SystemExit): auth.main(["--inner"])
        assert not stored
    output = capsys.readouterr().out
    assert '"Testing" status expires the token after 7 days' in output
    assert "fake-refresh-secret" not in output and "fake-client-secret" not in output
