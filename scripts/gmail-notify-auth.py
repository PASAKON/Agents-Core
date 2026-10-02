#!/usr/bin/env python3
"""One-time Google consent for the Run/Relay mail notifications (CEO 2026-10-02).

The Console's scripts/run-mail-sender.mjs puts one unread mail into the CEO's own Gmail for every
Run card and every relay login request ("ฉันลืมทุกครั้งเลย"). It needs a refresh token with scope
gmail.insert: that token can add mail to its owner's mailbox and nothing else (no reading, no
other recipient). This script mints it. Run it on Contabo from a Run card (--expects-input,
timeout 1800 s); the CEO does the Google part on his phone:

    cd /opt/MoonieXHQ/Agents/Core && python3 scripts/gmail-notify-auth.py

1. The OAuth client (GOOGLE_OAUTH_CLIENT_ID/SECRET, Google Cloud project moonez-project, the one
   scripts/yt-reply.py uses) goes into Infisical MoonieX-Console/prod if it is not there yet,
   moved 1:1 from ClaudeFlow's legacy .env by `infisical_setup.py import-env` (names printed,
   values never).
2. The script re-runs itself under `infisical_setup.py run MoonieX-Console prod`, prints the
   consent link, and reads the address the phone lands on with echo off.
3. It checks the state, the scope and the account (id_token email), inserts one test mail, and
   pipes the refresh token into `infisical_setup.py put … GMAIL_INSERT_REFRESH_TOKEN --stdin`.
Nothing it prints is a secret: the link carries only the public client id.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import getpass
import hashlib
import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETUP = ROOT / "tools" / "infisical_setup.py"
PROJECT, ENV = "MoonieX-Console", "prod"
LEGACY_CLIENT_ENV = Path("/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env")
CLIENT_NAMES = ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET")
TOKEN_NAME = "GMAIL_INSERT_REFRESH_TOKEN"
SCOPE = "https://www.googleapis.com/auth/gmail.insert openid email"
REDIRECT = "http://localhost:8765/"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
INSERT_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
OWNER = "cto-e106b78b"


def consent_url(client_id: str, account: str, state: str, verifier: str) -> str:
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "login_hint": account, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})


def code_from_redirect(pasted: str, state: str) -> str:
    """The `code` of the address the browser landed on, or SystemExit with a reason (never the value)."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(pasted.strip()).query)
    if "error" in q:
        sys.exit(f"Google answered {q['error'][0]!r}: nothing stored")
    if q.get("state", [""])[0] != state:
        sys.exit("that address is not from this link (state differs): run the card again")
    if not q.get("code", [""])[0]:
        sys.exit("no code in that address: copy the whole address bar after pressing Allow")
    return q["code"][0]


def email_of(id_token: str) -> str:
    """The email claim of an id_token received straight from Google's token endpoint over TLS."""
    try:
        part = id_token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    except (IndexError, ValueError):
        return ""
    return str(claims.get("email", "")) if claims.get("email_verified", True) else ""


def post(url: str, data: bytes, headers: dict) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e).get("error")
        except ValueError:
            err = None
        code = err.get("status") if isinstance(err, dict) else err
        sys.exit(f"{urllib.parse.urlparse(url).netloc} refused: HTTP {e.code} {code or ''}".rstrip())


def test_mail(access_token: str, account: str) -> None:
    subject = "=?UTF-8?B?" + base64.b64encode("[RUN] ทดสอบแจ้งเตือน — MoonieX".encode()).decode() + "?="
    body = ("ถ้ามือถือเด้งแจ้งเตือนฉบับนี้ แปลว่าใช้ได้แล้ว\n"
            "ต่อไปทุกคำขอ Run และ Relay จะมาเป็นอีเมลแบบนี้ (ยังไม่ได้อ่าน)\n"
            "https://terminal.mooniex.com/run\n")
    raw = (f"From: MoonieX Run <{account}>\r\nTo: <{account}>\r\nSubject: {subject}\r\n"
           "MIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\n"
           "Content-Transfer-Encoding: base64\r\n\r\n" + base64.b64encode(body.encode()).decode() + "\r\n")
    post(INSERT_URL, json.dumps({"raw": base64.urlsafe_b64encode(raw.encode()).decode(),
                                 "labelIds": ["INBOX", "UNREAD"]}).encode(),
         {"authorization": f"Bearer {access_token}", "content-type": "application/json"})


def ensure_client() -> None:
    """Step 1: the OAuth client into MoonieX-Console/prod, once."""
    have = subprocess.run([sys.executable, str(SETUP), "last4", PROJECT, ENV, CLIENT_NAMES[1]],
                          capture_output=True, text=True)
    if have.returncode == 0:
        print(f"OAuth client: already in {PROJECT}/{ENV}")
        return
    if not LEGACY_CLIENT_ENV.is_file():
        sys.exit(f"OAuth client not in {PROJECT}/{ENV} and {LEGACY_CLIENT_ENV} is missing")
    print(f"OAuth client: moving {', '.join(CLIENT_NAMES)} into {PROJECT}/{ENV} (names only)")
    today = dt.date.today().isoformat()
    r = subprocess.run([
        sys.executable, str(SETUP), "import-env", PROJECT, ENV, str(LEGACY_CLIENT_ENV),
        "--only", ",".join(CLIENT_NAMES),
        "--comment", "Google OAuth client (project moonez-project, consent app 'make.com') for the "
                     "Run/Relay mail sender; copy of ClaudeFlow .env, rotate both together",
        "--meta", "provider_name=google-cloud-moonez-project-oauth-client",
        "--meta", "console_url=https://console.cloud.google.com/apis/credentials?project=moonez-project",
        "--meta", "scope=OAuth client; grants nothing alone",
        "--meta", "expires=never", "--meta", f"owner={OWNER}", "--meta", f"created={today}",
    ])
    if r.returncode != 0:
        sys.exit("import-env failed: nothing else done")


def consent(account: str) -> None:
    """Steps 2-3, inside `infisical_setup.py run MoonieX-Console prod`."""
    cid, csec = (os.environ.get(n, "") for n in CLIENT_NAMES)
    if not cid or not csec:
        sys.exit(f"{' / '.join(CLIENT_NAMES)} not in the environment: is {PROJECT}/{ENV} readable?")
    state, verifier = secrets.token_urlsafe(16), secrets.token_urlsafe(64)
    print("\n1) เปิดลิงก์นี้บนมือถือ (กดค้างแล้วคัดลอกไปเปิดก็ได้):\n")
    print(consent_url(cid, account, state, verifier))
    print(f"\n2) เลือก {account} แล้วกด อนุญาต / Allow"
          "\n   (ถ้า Google เตือนว่าแอปยังไม่ได้ยืนยัน: ขั้นสูง → ไปต่อ)"
          "\n3) หน้าจะขึ้นว่าโหลดไม่ได้ (localhost) = ปกติ: คัดลอกที่อยู่ทั้งบรรทัดจากแถบที่อยู่"
          "\n4) วางในช่องของการ์ดนี้แล้วกดส่ง (ตัวอักษรจะไม่แสดง)\n", flush=True)
    code = code_from_redirect(getpass.getpass("ที่อยู่: "), state)
    tok = post(TOKEN_URL, urllib.parse.urlencode({
        "client_id": cid, "client_secret": csec, "code": code, "code_verifier": verifier,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code"}).encode(),
        {"content-type": "application/x-www-form-urlencoded"})
    if "gmail.insert" not in tok.get("scope", ""):
        sys.exit("Google did not grant gmail.insert (the box was unticked?): nothing stored, run again")
    got = email_of(tok.get("id_token", ""))
    if got.lower() != account.lower():
        sys.exit(f"that consent is for {got or 'an unknown account'}, not {account}: nothing stored")
    if not tok.get("refresh_token"):
        sys.exit("Google returned no refresh token: remove the app at myaccount.google.com/connections, run again")
    testing = "refresh_token_expires_in" in tok
    expires = (dt.date.today() + dt.timedelta(days=6)).isoformat() if testing else "on-revoke"
    test_mail(tok["access_token"], account)
    print(f"ทดสอบ: ใส่อีเมลทดสอบเข้า inbox ของ {account} แล้ว (ยังไม่ได้อ่าน)")
    r = subprocess.run([
        sys.executable, str(SETUP), "put", PROJECT, ENV, TOKEN_NAME, "--stdin",
        "--comment", "Gmail refresh token, scope gmail.insert: the Run/Relay mail sender puts unread "
                     "notifications into the CEO's own inbox (Console scripts/run-mail-sender.mjs)",
        "--meta", "provider_name=google-oauth-moonez-project-gmail-insert",
        "--meta", "console_url=https://myaccount.google.com/connections",
        "--meta", "scope=gmail.insert + openid email; own mailbox only, cannot read or send",
        "--meta", f"expires={expires}", "--meta", f"owner={OWNER}",
        "--meta", f"created={dt.date.today().isoformat()}",
    ], input=tok["refresh_token"] + "\n", text=True)
    if r.returncode != 0:
        sys.exit("storing the token failed: the test mail went out but nothing is saved, run again")
    if testing:
        print("คำเตือน: แอป make.com ใน Google Cloud ยังอยู่โหมด Testing → กุญแจนี้หมดอายุใน 7 วัน"
              " ต้องกด Publish app ที่ OAuth consent screen ก่อน แล้วรันการ์ดนี้ใหม่")
    print("เสร็จ: ทุกคำขอ Run/Relay ใหม่จะส่งอีเมลแจ้งเตือน")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--account", default=os.environ.get("RUN_INBOX_MAIL_TO") or "pass.gob1@gmail.com")
    ap.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.inner:
        consent(args.account)
        return
    ensure_client()
    os.execv(sys.executable, [sys.executable, str(SETUP), "run", PROJECT, ENV, "--as", "contabo", "--",
                              sys.executable, str(Path(__file__).resolve()), "--inner",
                              "--account", args.account])


if __name__ == "__main__":
    main()
