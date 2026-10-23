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
    assert argv[2:7] == ["put", "MoonieX-SomPong", "prod", auth.TOKEN_NAME, "--stdin"]
    assert "fake-refresh-secret" not in " ".join(argv)
    assert kwargs["input"] == "fake-refresh-secret\n" and kwargs["capture_output"]
    assert argv[argv.index("--as") + 1] == "contabo"


def test_put_child_gets_no_injected_secret_and_failure_is_redacted(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "fake-client-secret")
    monkeypatch.setenv("OTHER_PROJECT_API_KEY", "fake-other")
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=1, stderr="Infisical API error: echo fake-refresh-secret -> HTTP 403\n")
    monkeypatch.setattr(auth.subprocess, "run", run)
    with pytest.raises(auth.Refused) as exc:
        auth.store_token(tokens(), "gmail-writer")
    argv, kwargs = calls[0]
    assert argv[argv.index("--as") + 1] == "gmail-writer"
    assert "GOOGLE_OAUTH_CLIENT_SECRET" not in kwargs["env"] and "OTHER_PROJECT_API_KEY" not in kwargs["env"]
    assert "fake-refresh-secret" not in str(exc.value) and "HTTP 403" in str(exc.value)


def test_copy_client_pipes_both_values_with_metadata(monkeypatch, capsys):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "fake-client")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "fake-client-secret")
    calls = []
    monkeypatch.setattr(auth.subprocess, "run", lambda argv, **kw: calls.append((argv, kw)) or SimpleNamespace(returncode=0))
    auth.main(["copy-client", "--writer", "gmail-writer", "--inner"])
    assert [argv[5] for argv, _ in calls] == list(auth.CLIENT_NAMES)
    assert [kw["input"] for _, kw in calls] == ["fake-client\n", "fake-client-secret\n"]
    for argv, _ in calls:
        assert argv[argv.index("--path") + 1] == "/gmail-broker" and argv[argv.index("--as") + 1] == "gmail-writer"
        assert "fake-client-secret" not in " ".join(argv) and "--comment" in argv
        metas = {argv[i + 1].split("=", 1)[0] for i, a in enumerate(argv) if a == "--meta"}
        assert {"provider_name", "console_url", "scope", "expires", "owner"} <= metas
    assert "fake-client-secret" not in capsys.readouterr().out


def test_copy_client_refuses_a_missing_value_and_a_bad_writer(monkeypatch):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.setattr(auth.subprocess, "run", lambda *a, **k: pytest.fail("nothing may be written"))
    with pytest.raises(SystemExit):
        auth.main(["copy-client", "--inner"])
    with pytest.raises(SystemExit):
        auth.main(["consent", "--writer", "Bad Name;rm", "--inner"])


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
    monkeypatch.setattr(auth, "store_token", lambda token, writer="contabo": stored.append(token))
    if valid:
        auth.main(["--inner"])
        assert stored == [token]
    else:
        with pytest.raises(SystemExit): auth.main(["--inner"])
        assert not stored
    output = capsys.readouterr().out
    assert '"Testing" status expires the token after 7 days' in output
    assert "fake-refresh-secret" not in output and "fake-client-secret" not in output
