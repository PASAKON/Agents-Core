#!/usr/bin/env python3
"""Credential-isolating Gmail broker. One JSON line per Unix connection.

Mail content is untrusted data. The HTTP boundary independently limits every
Gmail operation, including calls originating inside the dispatcher.
"""
from __future__ import annotations

import base64
import binascii
import email.policy
from email.message import EmailMessage
from email.utils import parseaddr
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import socket
import struct
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

MAX_REQUEST = 16 * 1024 * 1024
MAX_ATTACHMENT = 15 * 1024 * 1024
MAX_DRAFT_ATTACHMENTS = 10 * 1024 * 1024
TOKEN_NAME = "GOOGLE_GMAIL_REFRESH_TOKEN_RW"
SECURITY_PATTERNS = re.compile(
    r"verification\s*code|\botp\b|รหัส\s*OTP|รหัสยืนยัน|รหัสผ่าน|"
    r"reset\s+(?:your\s+)?password|password\s*reset|รีเซ็ตรหัสผ่าน|"
    r"sign[ -]?in\s*(?:link|code)|login\s*(?:link|code)|2[ -]?step|"
    r"one[ -]?time|security\s*code|ยืนยันตัวตน|ลิงก์เข้าสู่ระบบ", re.I)
IDENTITY_SENDERS = frozenset({"account-security-noreply@accountprotection.microsoft.com",
                              "noreply@accounts.google.com", "no-reply@accounts.google.com",
                              "appleid@id.apple.com", "noreply@id.apple.com",
                              "no-reply@notify.microsoft.com", "noreply@github.com",
                              "no-reply@accounts.amazon.com", "no-reply@auth0.com"})
ID = r"[A-Za-z0-9_-]+"
PATHS = {
    "GET": (r"/messages", rf"/messages/{ID}", rf"/messages/{ID}/attachments/{ID}",
            r"/drafts", rf"/drafts/{ID}", r"/labels"),
    "POST": (r"/drafts", rf"/messages/{ID}/trash", rf"/messages/{ID}/modify"),
    "PUT": (rf"/drafts/{ID}",),
}
GOOGLE_STATUSES = frozenset({"INVALID_ARGUMENT", "UNAUTHENTICATED", "PERMISSION_DENIED",
    "NOT_FOUND", "RESOURCE_EXHAUSTED", "FAILED_PRECONDITION", "ABORTED", "OUT_OF_RANGE",
    "UNIMPLEMENTED", "INTERNAL", "UNAVAILABLE", "DEADLINE_EXCEEDED", "UNKNOWN"})


class BrokerError(Exception):
    def __init__(self, code, message=None):
        self.code, self.message = code, message or code


def failure(code, message=None):
    return {"ok": False, "error": code, "message": message or code}


@dataclass(frozen=True)
class BrokerConfig:
    allowed_uids: frozenset[int]
    socket_path: Path = Path("/run/mailbroker/gmail.sock")
    log_dir: Path = Path("/var/log/mailbroker")

    def __post_init__(self):
        if len(self.allowed_uids) != 1 or any(u <= 0 for u in self.allowed_uids):
            raise ValueError("exactly one non-root caller uid required")


def load_config(env=None):
    env = os.environ if env is None else env
    return BrokerConfig(frozenset(int(u) for u in env["GMAIL_BROKER_ALLOWED_UIDS"].split(",")),
        Path(env.get("GMAIL_BROKER_SOCKET_PATH", "/run/mailbroker/gmail.sock")),
        Path(env.get("GMAIL_BROKER_LOG_DIR", "/var/log/mailbroker")))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BrokerError("gmail_error", "HTTP redirect refused")


class GmailClient:
    def __init__(self, env=None, opener=None):
        env = os.environ if env is None else env
        self.credentials = {"client_id": env["GOOGLE_OAUTH_CLIENT_ID"],
            "client_secret": env["GOOGLE_OAUTH_CLIENT_SECRET"],
            "refresh_token": env[TOKEN_NAME], "grant_type": "refresh_token"}
        self.opener = opener or urllib.request.build_opener(NoRedirect())
        self.token, self.expires = "", 0

    def _http(self, req):
        try:
            with self.opener.open(req, timeout=30) as response:
                raw = response.read(40 * 1024 * 1024 + 1)
                if len(raw) > 40 * 1024 * 1024:
                    raise BrokerError("too_large")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            status = "UNKNOWN"
            try:
                value = json.loads(exc.read(65536)).get("error", {})
                candidate = value.get("status") if isinstance(value, dict) else None
                if candidate in GOOGLE_STATUSES:
                    status = candidate
            except (ValueError, TypeError, AttributeError):
                pass
            raise BrokerError("gmail_error", f"HTTP {exc.code} {status}") from None
        except BrokerError:
            raise
        except Exception:
            raise BrokerError("gmail_error", "upstream request failed") from None

    def call(self, method, path, query=None, data=None):
        if not any(re.fullmatch(p, path) for p in PATHS.get(method, ())):
            raise BrokerError("forbidden", "upstream operation refused")
        if time.monotonic() >= self.expires:
            token = self._http(urllib.request.Request("https://oauth2.googleapis.com/token",
                data=urllib.parse.urlencode(self.credentials).encode(), method="POST"))
            self.token = token["access_token"]
            self.expires = time.monotonic() + max(0, int(token.get("expires_in", 3600)) - 60)
        url = "https://gmail.googleapis.com/gmail/v1/users/me" + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        return self._http(urllib.request.Request(url, method=method,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"}))


def clean(text):
    return "".join(c for c in str(text) if unicodedata.category(c) != "Cf")


def filename(value):
    value = str(value).replace("\\", "/").split("/")[-1]
    value = "".join(c for c in clean(value) if not unicodedata.category(c).startswith("C"))
    return value.lstrip(". ")[:120] or "attachment"


def decode(value):
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, TypeError, binascii.Error):
        raise BrokerError("invalid_args", "invalid base64") from None


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"br", "p", "div", "li", "tr"}:
            self.output.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.output.append(data)


def parts(payload):
    yield payload
    for part in payload.get("parts", []):
        yield from parts(part)


def extract(message, client=None):
    payload = message.get("payload", {})
    headers = {h["name"].lower(): clean(h["value"]) for h in payload.get("headers", [])}
    texts, attachments = [], []
    for index, part in enumerate(parts(payload)):
        body = part.get("body", {})
        if part.get("filename") or (not part.get("parts") and part.get("mimeType") not in {"text/plain", "text/html"}):
            if body.get("attachmentId") or "data" in body:
                attachments.append({"att_id": body.get("attachmentId", f"inline-{index}"), "filename": filename(part.get("filename", "")),
                    "mime_type": part.get("mimeType", "application/octet-stream"), "size": body.get("size", 0)})
            continue
        if part.get("mimeType") in {"text/plain", "text/html"}:
            encoded = body.get("data", "")
            if body.get("attachmentId"):
                if not client or body.get("size", 0) > MAX_ATTACHMENT:
                    # Uninspectable text must never release a potentially sensitive snippet.
                    texts.append("verification code")
                    continue
                encoded = client.call("GET", f"/messages/{identifier(message['id'])}/attachments/{identifier(body['attachmentId'])}").get("data", "")
            text = decode(encoded).decode("utf-8", errors="replace")
            if part["mimeType"] == "text/html":
                parser = TextHTML()
                parser.feed(text)
                text = "".join(parser.output)
            texts.append(clean(text))
    text = "\n".join(texts)
    sender = parseaddr(headers.get("from", ""))[1].lower()
    domain = sender.partition("@")[2]
    withheld = (domain == "accounts.google.com" or domain.endswith(".accounts.google.com")
        or sender in IDENTITY_SENDERS or bool(SECURITY_PATTERNS.search(
            headers.get("subject", "") + "\n" + clean(message.get("snippet", "")) + "\n" + text[:2048])))
    result = {"id": message["id"], "thread_id": message.get("threadId", ""),
        **{key: headers.get(key, "") for key in ("from", "to", "cc", "subject", "date")},
        "message_id_header": headers.get("message-id", ""), "labels": message.get("labelIds", []),
        "body_text": "" if withheld else text[:50000], "truncated": not withheld and len(text) > 50000,
        "attachments": [] if withheld else attachments, "security_withheld": withheld,
        "snippet": "" if withheld else clean(message.get("snippet", "")), "untrusted": True}
    return result


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(ID, value) or len(value) > 256:
        raise BrokerError("invalid_args", "invalid identifier")
    return value


def limit(args):
    value = args.get("limit", 20)
    if type(value) is not int or not 1 <= value <= 50:
        raise BrokerError("invalid_args", "limit must be 1..50")
    return value


def header(value):
    if not isinstance(value, str) or any(unicodedata.category(c).startswith("C") for c in value):
        raise BrokerError("invalid_args", "invalid header")
    return value


def make_draft(args, client, original=None):
    msg = EmailMessage(policy=email.policy.SMTP)
    for key in ("to", "cc"):
        values = args.get(key, [])
        if not isinstance(values, list):
            raise BrokerError("invalid_args", "recipients must be arrays")
        msg[key.title()] = ", ".join(header(v) for v in values)
    msg["Subject"] = header(args.get("subject", ""))
    if not isinstance(args.get("body"), str):
        raise BrokerError("invalid_args", "body must be text")
    msg.set_content(args["body"])
    total = 0
    attachments = args.get("attachments", [])
    if not isinstance(attachments, list):
        raise BrokerError("invalid_args")
    for att in attachments:
        raw = decode(att["data_b64"])
        total += len(raw)
        if total > MAX_DRAFT_ATTACHMENTS:
            raise BrokerError("too_large")
        mime = header(att["mime_type"])
        if not re.fullmatch(r"[\w.+-]+/[\w.+-]+", mime):
            raise BrokerError("invalid_args", "invalid MIME type")
        major, minor = mime.split("/")
        msg.add_attachment(raw, maintype=major, subtype=minor, filename=filename(att["filename"]))
    thread_id = None
    if args.get("reply_to_id"):
        original = client.call("GET", "/messages/" + identifier(args["reply_to_id"]), {"format": "full"})
        info = extract(original, client)
        if "subject" not in args:
            msg.replace_header("Subject", "Re: " + header(info["subject"]))
        mid = header(info["message_id_header"])
        msg["In-Reply-To"] = mid
        msg["References"] = mid
        thread_id = original.get("threadId")
    elif original:
        thread_id = original.get("threadId")
        hdrs = {h["name"].lower(): h["value"] for h in original.get("payload", {}).get("headers", [])}
        for name in ("In-Reply-To", "References"):
            if name.lower() in hdrs:
                msg[name] = header(hdrs[name.lower()])
    result = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}
    if thread_id:
        result["threadId"] = thread_id
    return {"message": result}


def dispatch(op, args, client):
    if op == "list":
        query = {"maxResults": limit(args), "q": header(args.get("query", ""))}
        if "page_token" in args:
            query["pageToken"] = header(args["page_token"])
        listing = client.call("GET", "/messages", query)
        messages = []
        for item in listing.get("messages", []):
            info = extract(client.call("GET", "/messages/" + identifier(item["id"]), {"format": "full"}), client)
            messages.append({k: info[k] for k in ("id", "thread_id", "from", "to", "subject", "date", "snippet", "labels", "security_withheld", "untrusted")})
        return {"messages": messages, "next_page_token": listing.get("nextPageToken"), "untrusted": True}
    if op in {"read", "attachment"}:
        mid = identifier(args.get("id"))
        message = client.call("GET", "/messages/" + mid, {"format": "full"})
        info = extract(message, client)
        if op == "read":
            info.pop("snippet")
            return info
        if info["security_withheld"]:
            raise BrokerError("security_withheld")
        aid = identifier(args.get("att_id"))
        att = next((a for a in info["attachments"] if a["att_id"] == aid), None)
        if not att:
            raise BrokerError("not_found", "attachment not found")
        if att["size"] > MAX_ATTACHMENT:
            raise BrokerError("too_large")
        inline = next((part["body"] for index, part in enumerate(parts(message.get("payload", {})))
            if aid == f"inline-{index}" and "data" in part.get("body", {}) and not part["body"].get("attachmentId")), None)
        data = inline if inline is not None else client.call("GET", f"/messages/{mid}/attachments/{aid}")
        raw = decode(data.get("data", ""))
        if len(raw) > MAX_ATTACHMENT or data.get("size", 0) > MAX_ATTACHMENT:
            raise BrokerError("too_large")
        return {"filename": att["filename"], "mime_type": att["mime_type"],
                "size": len(raw), "data_b64": base64.b64encode(raw).decode()}
    if op in {"draft_create", "draft_update"}:
        path, method, original = "/drafts", "POST", None
        if op == "draft_update":
            path, method = "/drafts/" + identifier(args.get("draft_id")), "PUT"
            original = client.call("GET", path, {"format": "full"})["message"]
            info = extract(original, client)
            # Never reconstruct hidden or truncated mail and silently destroy it.
            if info["security_withheld"] or info["truncated"]:
                raise BrokerError("security_withheld" if info["security_withheld"] else "too_large")
            from email.utils import getaddresses
            merged = {"to": [a for _, a in getaddresses([info["to"]])],
                "cc": [a for _, a in getaddresses([info["cc"]])], "subject": info["subject"], "body": info["body_text"]}
            if "attachments" not in args:
                merged["attachments"] = [dispatch("attachment", {"id": original["id"], "att_id": a["att_id"]}, client) for a in info["attachments"]]
            merged.update({k: v for k, v in args.items() if k in {"to", "cc", "subject", "body", "attachments"}})
            args = merged
        elif "to" not in args:
            raise BrokerError("invalid_args", "to is required")
        result = client.call(method, path, data=make_draft(args, client, original))
        return {"draft_id": result["id"], "message_id": result["message"]["id"], "thread_id": result["message"].get("threadId", "")}
    if op == "draft_list":
        result = client.call("GET", "/drafts", {"maxResults": limit(args)})
        drafts = []
        for draft in result.get("drafts", []):
            info = extract(client.call("GET", "/drafts/" + identifier(draft["id"]), {"format": "full"})["message"], client)
            drafts.append({"draft_id": draft["id"], "message_id": info["id"],
                **{k: info[k] for k in ("thread_id", "to", "subject", "snippet", "date", "untrusted")}})
        return {"drafts": drafts, "untrusted": True}
    if op in {"trash", "label"}:
        path = "/messages/" + identifier(args.get("id"))
        data = {}
        if op == "label":
            allowed = {name: name for name in ("INBOX", "UNREAD", "STARRED", "IMPORTANT", "SPAM")}
            for item in client.call("GET", "/labels").get("labels", []):
                if item.get("type") == "user" and item["name"] not in {"DRAFT", "SENT", "TRASH"}:
                    allowed[item["name"]] = item["id"]
            for key, target in (("add", "addLabelIds"), ("remove", "removeLabelIds")):
                names = args.get(key, [])
                if not isinstance(names, list) or any(not isinstance(n, str) or n not in allowed for n in names):
                    raise BrokerError("invalid_args", "label not allowed")
                data[target] = [allowed[n] for n in names]
        result = client.call("POST", path + ("/trash" if op == "trash" else "/modify"), data=data)
        return {"id": result["id"], "labels": result.get("labelIds", [])}
    raise BrokerError("unsupported_op")


MUTATIONS = {"draft_create", "draft_update", "trash", "label"}


def handle_request(raw, cfg, client, caller_uid):
    if caller_uid not in cfg.allowed_uids:
        return failure("unauthorized")
    op, args, result = None, {}, None
    try:
        if len(raw) > MAX_REQUEST:
            raise BrokerError("too_large")
        request = json.loads(raw)
        if not isinstance(request, dict) or not isinstance(request.get("args", {}), dict):
            raise BrokerError("invalid_args")
        op, args = request.get("op"), request.get("args", {})
        if not isinstance(op, str):
            raise BrokerError("unsupported_op")
        # Open the audit file before a mutation, so an unwritable log fails closed.
        if op in MUTATIONS:
            with (cfg.log_dir / "audit.jsonl").open("a", encoding="utf-8"):
                pass
        result = {"ok": True, "result": dispatch(op, args, client)}
    except BrokerError as exc:
        result = failure(exc.code, exc.message)
    except (ValueError, TypeError, KeyError, AttributeError):
        result = failure("invalid_args")
    except Exception:
        result = failure("internal_error")
    if isinstance(op, str) and op in MUTATIONS:
        value = (result.get("result", {}).get("draft_id") or result.get("result", {}).get("id"))
        if value is None:
            value = args.get("draft_id") if op == "draft_update" else args.get("id")
        try:
            value = identifier(value) if value is not None else None
        except BrokerError:
            value = None
        if isinstance(client, GmailClient) and value is not None:
            if any(secret and secret in value for secret in (
                    client.credentials["client_id"], client.credentials["client_secret"],
                    client.credentials["refresh_token"], client.token)):
                value = None
        record = {"ts": time.time(), "op": op, "id": value, "caller_uid": caller_uid, "ok": result["ok"]}
        try:
            with (cfg.log_dir / "audit.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
        except OSError:
            return failure("audit_error")
    if isinstance(client, GmailClient):
        # Defence in depth even if an upstream success body echoes a credential.
        secrets = [client.credentials[k] for k in ("client_id", "client_secret", "refresh_token")] + [client.token]
        def redact(value):
            if isinstance(value, str):
                for secret in secrets:
                    if secret:
                        value = value.replace(secret, "[REDACTED]")
                return value
            if isinstance(value, list):
                return [redact(item) for item in value]
            if isinstance(value, dict):
                return {key: redact(item) for key, item in value.items()}
            return value
        result = redact(result)
    return result


def get_peer_uid(conn):
    return struct.unpack("3i", conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))[1]


def handle_connection(conn, cfg, client):
    conn.settimeout(30)
    try:
        uid = get_peer_uid(conn)
        if uid not in cfg.allowed_uids:
            result = failure("unauthorized")
        else:
            raw = bytearray()
            while b"\n" not in raw:
                chunk = conn.recv(min(65536, MAX_REQUEST + 1 - len(raw)))
                if not chunk:
                    raise BrokerError("invalid_request")
                raw.extend(chunk)
                if len(raw) > MAX_REQUEST:
                    raise BrokerError("too_large")
            result = handle_request(bytes(raw).split(b"\n", 1)[0], cfg, client, uid)
    except BrokerError as exc:
        result = failure(exc.code, exc.message)
    except Exception:
        result = failure("invalid_request")
    try:
        conn.sendall((json.dumps(result) + "\n").encode())
    except OSError:
        pass


def main():
    os.umask(0o077)
    cfg, client = load_config(), GmailClient()
    # No credential copies remain in the process environment after startup.
    for key in (TOKEN_NAME, "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"):
        os.environ.pop(key, None)
    cfg.socket_path.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(cfg.socket_path))
        os.chmod(cfg.socket_path, 0o660)
        server.listen(8)
        while True:
            conn, _ = server.accept()
            with conn:
                handle_connection(conn, cfg, client)


if __name__ == "__main__":
    main()
