import base64
import email
import io
import json
from pathlib import Path
import socket
import subprocess
import urllib.error

import pytest

from runners import gmail_broker as b


def encoded(value):
    return base64.urlsafe_b64encode(value.encode()).decode()


def message(text="Hello", subject="Synthetic note", sender="sender@example.test", attachment=False):
    result = {"id": "m1", "threadId": "t1", "labelIds": ["INBOX"], "snippet": text[:100],
        "payload": {"mimeType": "multipart/mixed", "headers": [
            {"name": k, "value": v} for k, v in {
                "From": sender, "To": "reader@example.test", "Subject": subject,
                "Message-ID": "<synthetic@example.test>", "Date": "Thu, 1 Jan 2026 00:00:00 +0000"}.items()],
            "parts": [{"mimeType": "text/plain", "body": {"data": encoded(text)}}]}}
    if attachment:
        result["payload"]["parts"].append({"filename": "../.hidden\\safe\x00.txt", "mimeType": "text/plain",
            "body": {"attachmentId": "a1", "size": 3}})
    return result


class FakeClient:
    def __init__(self, msg=None):
        self.msg = msg or message()
        self.calls = []
        self.attachment = {"data": encoded("abc"), "size": 3}

    def call(self, method, path, query=None, data=None):
        self.calls.append((method, path, query, data))
        if path.endswith("/attachments/a1"):
            return self.attachment
        if method == "GET":
            if path == "/messages":
                return {"messages": [{"id": "m1"}], "nextPageToken": "next"}
            if path == "/drafts":
                return {"drafts": [{"id": "d1"}]}
            if path == "/drafts/d1":
                return {"id": "d1", "message": self.msg}
            if path == "/labels":
                return {"labels": [{"id": "Label_1", "name": "Work", "type": "user"}]}
            return self.msg
        if path.startswith("/drafts"):
            return {"id": "d1", "message": {"id": "m2", "threadId": "t1"}}
        return {"id": "m1", "labelIds": ["TRASH"] if path.endswith("/trash") else ["Label_1"]}


@pytest.fixture
def cfg(tmp_path):
    return b.BrokerConfig(frozenset({1234}), tmp_path / "gmail.sock", tmp_path)


def request(cfg, client, op, **args):
    return b.handle_request(json.dumps({"op": op, "args": args}).encode(), cfg, client, 1234)


def test_wire_list_read_and_pagination(cfg):
    client = FakeClient()
    result = request(cfg, client, "list", query="is:unread", page_token="previous")["result"]
    assert result["untrusted"] and result["next_page_token"] == "next"
    assert client.calls[0][2] == {"q": "is:unread", "maxResults": 20, "pageToken": "previous"}
    assert set(result["messages"][0]) == {"id", "thread_id", "from", "to", "subject", "date", "snippet", "labels", "security_withheld", "untrusted"}
    read = request(cfg, client, "read", id="m1")["result"]
    assert read["body_text"] == "Hello" and read["untrusted"]
    assert read["message_id_header"] == "<synthetic@example.test>"


@pytest.mark.parametrize("op", ["list", "draft_list"])
@pytest.mark.parametrize("value", [0, -1, 51, True, "20", None])
def test_limits(cfg, op, value):
    client = FakeClient()
    assert request(cfg, client, op, limit=value)["error"] == "invalid_args"
    assert not client.calls


@pytest.mark.parametrize("text,subject,sender", [
    ("Hello", "Synthetic", "Security <no-reply@accounts.google.com>"),
    ("Hello", "Synthetic", "account-security-noreply@accountprotection.microsoft.com"),
    ("verification code 123456", "Synthetic", "sender@example.test"),
    ("รหัส OTP 123456", "Synthetic", "sender@example.test"),
    ("รหัสยืนยัน 123456", "Synthetic", "sender@example.test"),
    ("Hello", "reset your password", "sender@example.test"),
    ("รีเซ็ตรหัสผ่าน", "Synthetic", "sender@example.test"),
    ("Hello", "2-Step verification", "sender@example.test"),
    ("sign-in link", "Synthetic", "sender@example.test"),
    ("verifi\u200bcation code", "Synthetic", "sender@example.test"),
])
def test_security_withholding_every_read_surface(cfg, text, subject, sender):
    client = FakeClient(message(text, subject, sender, True))
    read = request(cfg, client, "read", id="m1")["result"]
    assert read["security_withheld"] and read["body_text"] == "" and read["attachments"] == []
    item = request(cfg, client, "list")["result"]["messages"][0]
    assert item["security_withheld"] and item["snippet"] == ""
    assert request(cfg, client, "attachment", id="m1", att_id="a1")["error"] == "security_withheld"
    assert request(cfg, client, "draft_list")["result"]["drafts"][0]["snippet"] == ""
    assert not any("/attachments/" in c[1] for c in client.calls)


def test_security_scan_beyond_snippet_and_html(cfg):
    msg = message("normal")
    msg["payload"]["parts"] = [{"mimeType": "text/html", "body": {"data": encoded("<p>verification <b>code</b> 123456</p>")}}]
    assert request(cfg, FakeClient(msg), "read", id="m1")["result"]["security_withheld"]


def test_html_unicode_and_truncation(cfg):
    msg = message()
    msg["payload"]["parts"] = [{"mimeType": "text/html", "body": {"data": encoded("<p>Hello &amp; <b>world</b>\u202e\u200b</p><script>bad()</script>" + "x" * 50010)}}]
    read = request(cfg, FakeClient(msg), "read", id="m1")["result"]
    assert read["body_text"].startswith("\nHello & world")
    assert "bad()" not in read["body_text"] and "\u202e" not in read["body_text"]
    assert "\u200b" not in read["body_text"] and len(read["body_text"]) == 50000 and read["truncated"]


@pytest.mark.parametrize("name", ["../../.secret", "a\\b\\.file", "\x00\n\t", "." * 200, "a" * 200, "a/\u202eb"])
def test_filename_sanitization(name):
    result = b.filename(name)
    assert 1 <= len(result) <= 120 and not result.startswith(".")
    assert all(c not in result for c in "/\\\x00\n\t\u202e")


def test_attachment_and_size_guards(cfg):
    client = FakeClient(message(attachment=True))
    result = request(cfg, client, "attachment", id="m1", att_id="a1")["result"]
    assert result == {"filename": "safe.txt", "mime_type": "text/plain", "size": 3, "data_b64": "YWJj"}
    assert request(cfg, client, "attachment", id="m1", att_id="unknown")["error"] == "not_found"
    client.msg["payload"]["parts"][1]["body"]["size"] = b.MAX_ATTACHMENT + 1
    before = len(client.calls)
    assert request(cfg, client, "attachment", id="m1", att_id="a1")["error"] == "too_large"
    assert len(client.calls) == before + 1
    client.msg["payload"]["parts"][1]["body"]["size"] = 3
    client.attachment = {"data": encoded("x" * (b.MAX_ATTACHMENT + 1))}
    assert request(cfg, client, "attachment", id="m1", att_id="a1")["error"] == "too_large"


def draft_mime(client):
    payload = client.calls[-1][3]["message"]
    return email.message_from_bytes(b.decode(payload["raw"]), policy=email.policy.default), payload


def test_reply_draft_and_update_preserve_thread(cfg):
    client = FakeClient()
    result = request(cfg, client, "draft_create", to=["reader@example.test"], body="Reply", reply_to_id="m1")
    assert result["result"] == {"draft_id": "d1", "message_id": "m2", "thread_id": "t1"}
    mime, payload = draft_mime(client)
    assert payload["threadId"] == "t1"
    assert mime["Subject"] == "Re: Synthetic note"
    assert mime["In-Reply-To"] == mime["References"] == "<synthetic@example.test>"
    client.msg["payload"]["headers"] += [{"name": "In-Reply-To", "value": "<original@example.test>"}, {"name": "References", "value": "<original@example.test>"}]
    assert request(cfg, client, "draft_update", draft_id="d1", body="Edited")["ok"]
    mime, payload = draft_mime(client)
    assert mime["Subject"] == "Synthetic note" and mime["To"] == "reader@example.test"
    assert mime["In-Reply-To"] == "<original@example.test>" and payload["threadId"] == "t1"
    assert mime.get_content().strip() == "Edited"


def test_draft_attachments_preserved_and_replaced(cfg):
    client = FakeClient(message(attachment=True))
    assert request(cfg, client, "draft_update", draft_id="d1", subject="Edited")["ok"]
    mime, _ = draft_mime(client)
    assert list(mime.iter_attachments())[0].get_payload(decode=True) == b"abc"
    assert request(cfg, client, "draft_update", draft_id="d1", attachments=[])["ok"]
    assert not list(draft_mime(client)[0].iter_attachments())
    atts = [{"filename": "../.x", "mime_type": "text/plain", "data_b64": encoded("x" * (6 * 1024 * 1024))}] * 2
    assert request(cfg, client, "draft_create", to=[], body="", attachments=atts)["error"] == "too_large"


def test_draft_attachment_total_guard_direct():
    # The encoded wire cap is independent of the decoded aggregate cap.
    atts = [{"filename": "x", "mime_type": "text/plain", "data_b64": encoded("x" * (5 * 1024 * 1024 + 1))}] * 2
    with pytest.raises(b.BrokerError) as exc:
        b.make_draft({"to": [], "body": "", "attachments": atts}, FakeClient())
    assert exc.value.code == "too_large"


@pytest.mark.parametrize("changes", [{"to": "bad"}, {"subject": "x\r\nBcc: other@example.test"}, {"body": 1}, {"attachments": [{"filename": "x", "mime_type": "text/plain", "data_b64": "???"}]}])
def test_invalid_draft_inputs(cfg, changes):
    args = {"to": [], "body": ""}
    args.update(changes)
    assert request(cfg, FakeClient(), "draft_create", **args)["error"] == "invalid_args"


@pytest.mark.parametrize("label", ["DRAFT", "SENT", "TRASH", "Unknown"])
def test_label_refusals(cfg, label):
    client = FakeClient()
    assert request(cfg, client, "label", id="m1", add=[label])["error"] == "invalid_args"
    assert all(c[0] == "GET" for c in client.calls)


def test_label_trash_and_audit(cfg):
    client = FakeClient()
    assert request(cfg, client, "label", id="m1", add=["Work", "STARRED", "INBOX", "IMPORTANT", "SPAM"], remove=["UNREAD"])["ok"]
    assert client.calls[-1][3] == {"addLabelIds": ["Label_1", "STARRED", "INBOX", "IMPORTANT", "SPAM"], "removeLabelIds": ["UNREAD"]}
    assert request(cfg, client, "trash", id="m1")["result"]["labels"] == ["TRASH"]
    assert request(cfg, client, "draft_create", to=["reader@example.test"], subject="Private subject", body="Private body")["ok"]
    assert request(cfg, client, "draft_update", draft_id="d1", body="Private body")["ok"]
    assert not request(cfg, client, "label", id="m1", add=["SENT"])["ok"]
    raw = (cfg.log_dir / "audit.jsonl").read_text()
    rows = [json.loads(line) for line in raw.splitlines()]
    assert len(rows) == 5 and rows[-1]["ok"] is False
    assert {r["op"] for r in rows} == b.MUTATIONS
    assert all(set(r) == {"ts", "op", "id", "caller_uid", "ok"} and r["caller_uid"] == 1234 for r in rows)
    assert all(s not in raw for s in ("Private", "example.test", "Hello"))


def test_audit_unavailable_blocks_mutation(tmp_path):
    cfg = b.BrokerConfig(frozenset({1234}), log_dir=tmp_path / "missing")
    client = FakeClient()
    assert request(cfg, client, "trash", id="m1")["error"] == "audit_error"
    assert not client.calls


class Opener:
    def __init__(self, error=False):
        self.requests, self.error = [], error

    def open(self, req, timeout):
        self.requests.append(req)
        if self.error:
            body = {"error": {"status": "UNAUTHENTICATED", "message": "fake-refresh-secret fake-access-secret Authorization: Bearer fake-access-secret"}}
            raise urllib.error.HTTPError(req.full_url, 401, "secret", {}, io.BytesIO(json.dumps(body).encode()))
        if "oauth2" in req.full_url:
            return io.BytesIO(b'{"access_token":"fake-access-secret","expires_in":3600}')
        return io.BytesIO(json.dumps(message()).encode())


def http_client(opener):
    return b.GmailClient({"GOOGLE_OAUTH_CLIENT_ID": "fake-client", "GOOGLE_OAUTH_CLIENT_SECRET": "fake-client-secret", b.TOKEN_NAME: "fake-refresh-secret"}, opener)


def test_http_refresh_and_fixed_origin(cfg):
    opener = Opener()
    assert request(cfg, http_client(opener), "read", id="m1")["ok"]
    assert len(opener.requests) == 2
    assert opener.requests[1].full_url == "https://gmail.googleapis.com/gmail/v1/users/me/messages/m1?format=full"
    assert opener.requests[1].get_header("Authorization") == "Bearer fake-access-secret"


def test_http_error_never_echoes_credentials(cfg):
    client = http_client(Opener(error=True))
    result = request(cfg, client, "read", id="m1")
    assert result == {"ok": False, "error": "gmail_error", "message": "HTTP 401 UNAUTHENTICATED"}
    assert "secret" not in json.dumps(result) and "Authorization" not in json.dumps(result)


@pytest.mark.parametrize("method,path", [
    ("POST", "/messages/send"), ("POST", "/drafts/d1/send"), ("POST", "/drafts/send"),
    ("DELETE", "/messages/m1"), ("POST", "/messages/batchDelete"), ("DELETE", "/threads/t1"),
    ("DELETE", "/drafts/d1"), ("GET", "/settings/filters"), ("POST", "/settings/forwardingAddresses"),
    ("GET", "/settings/sendAs"), ("GET", "/settings/delegates"), ("POST", "/messages/import"),
    ("POST", "/messages"), ("GET", "https://evil.test/messages"), ("POST", "/labels"),
    ("GET", "/messages/../settings"), ("GET", "/messages/m1?alt=media"),
])
def test_http_allowlist_denies_before_any_network(method, path):
    opener = Opener()
    with pytest.raises(b.BrokerError) as exc:
        http_client(opener).call(method, path)
    assert exc.value.code == "forbidden" and not opener.requests


def test_module_has_no_forbidden_endpoint_text():
    text = Path(b.__file__).read_text()
    for forbidden in ("messages.send", "drafts.send", "/send", "messages.delete", "batchDelete", "threads.delete", "drafts.delete", "sendAs", "forwarding", "delegates"):
        assert forbidden not in text


@pytest.mark.parametrize("op", ["send", "delete", "settings", "import", "insert", "batchDelete"])
def test_no_other_operation(cfg, op):
    client = FakeClient()
    assert request(cfg, client, op)["error"] == "unsupported_op" and not client.calls


@pytest.mark.parametrize("uids", [frozenset(), frozenset({0}), frozenset({-1}), frozenset({1, 2})])
def test_config_rejects_root_or_multiple_callers(uids):
    with pytest.raises(ValueError):
        b.BrokerConfig(uids)


def test_request_cap_and_malformed(cfg):
    client = FakeClient()
    assert b.handle_request(b"x" * (b.MAX_REQUEST + 1), cfg, client, 1234)["error"] == "too_large"
    for raw in (b"[]", b"{", b'{"op": [], "args": {}}', b'{"op":"read","args":[]}'):
        assert not b.handle_request(raw, cfg, client, 1234)["ok"]
    assert b.handle_request(b"{}", cfg, client, 0)["error"] == "unauthorized"
    assert not client.calls


def test_peer_rejected_before_read(cfg, monkeypatch):
    class Connection:
        def settimeout(self, value): pass
        def recv(self, count): pytest.fail("must not read unauthorized request")
        def sendall(self, value): self.result = json.loads(value)
    conn = Connection()
    monkeypatch.setattr(b, "get_peer_uid", lambda conn: 0)
    b.handle_connection(conn, cfg, FakeClient())
    assert conn.result["error"] == "unauthorized"


def test_unix_socket_roundtrip(cfg, monkeypatch):
    with socket.socket(socket.AF_UNIX) as server:
        try:
            server.bind(str(cfg.socket_path))
        except PermissionError as exc:
            pytest.skip(f"sandbox refuses Unix socket binding: {exc}")
        server.listen(1)
        with socket.socket(socket.AF_UNIX) as client:
            client.connect(str(cfg.socket_path))
            conn, _ = server.accept()
            with conn:
                assert b.get_peer_uid(conn) >= 0
                monkeypatch.setattr(b, "get_peer_uid", lambda conn: 1234)
                client.sendall(b'{"op":"read","args":{"id":"m1"}}\n')
                b.handle_connection(conn, cfg, FakeClient())
                assert json.loads(client.recv(65536))["ok"]


def test_connection_size_cap_without_socket(cfg, monkeypatch):
    class Connection:
        def settimeout(self, value): pass
        def recv(self, count): return b"x" * count
        def sendall(self, value): self.result = json.loads(value)
    conn = Connection()
    monkeypatch.setattr(b, "get_peer_uid", lambda conn: 1234)
    b.handle_connection(conn, cfg, FakeClient())
    assert conn.result["error"] == "too_large"


def test_redirects_refused():
    with pytest.raises(b.BrokerError):
        b.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test/")


def test_unknown_upstream_status_cannot_echo_secret(cfg):
    class EchoOpener:
        def open(self, req, timeout):
            raise urllib.error.HTTPError(req.full_url, 401, "secret", {}, io.BytesIO(b'{"error":{"status":"fake-refresh-secret"}}'))
    assert request(cfg, http_client(EchoOpener()), "read", id="m1")["message"] == "HTTP 401 UNKNOWN"


def test_success_upstream_echo_redacted(cfg):
    class EchoOpener(Opener):
        def open(self, req, timeout):
            if "oauth2" in req.full_url:
                return super().open(req, timeout)
            return io.BytesIO(json.dumps(message("fake-refresh-secret fake-access-secret")).encode())
    assert "fake-refresh-secret" not in json.dumps(request(cfg, http_client(EchoOpener()), "read", id="m1"))


def test_inline_draft_attachment_preserved(cfg):
    msg = message(attachment=True)
    msg["payload"]["parts"][1]["body"] = {"data": encoded("abc"), "size": 3}
    client = FakeClient(msg)
    assert request(cfg, client, "draft_update", draft_id="d1", body="Updated")["ok"]
    assert list(draft_mime(client)[0].iter_attachments())[0].get_payload(decode=True) == b"abc"


def test_installer_dry_run_unit_and_root_refusal():
    script = Path(__file__).resolve().parents[1] / "scripts/install-gmail-broker.sh"
    syntax = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert syntax.returncode == 0
    # Use an existing synthetic caller mapping to make this portable off Contabo.
    import pwd
    caller = next((p.pw_name for p in pwd.getpwall() if p.pw_uid > 0 and p.pw_name != "mailbroker"), None)
    if caller is None:
        pytest.skip("no non-root local account available for installer dry-run")
    result = subprocess.run(["bash", str(script), "install", "--dry-run", "--caller-user", caller], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    text = result.stdout
    assert "ExecStartPre=+/usr/bin/install -d" in text and "ReadWritePaths=-/run/mailbroker" in text
    assert "--reuid=mailbroker --regid=mailbroker --clear-groups" in text
    assert "run MoonieX-SomPong prod --as contabo --path /gmail-broker" in text
    assert "EnvironmentFile=" not in text and "GMAIL_BROKER_ALLOWED_UIDS=0\n" not in text
    refused = subprocess.run(["bash", str(script), "install", "--dry-run", "--caller-user", "root"], capture_output=True, text=True)
    assert refused.returncode != 0
