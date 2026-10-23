#!/usr/bin/env python3
"""One-time consent from a Run card with --expects-input (timeout 1800s)."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
SETUP = ROOT / "tools/infisical_setup.py"
PROJECT = "Agents-Core"
SECRET_PATH = "/gmail-broker"
TOKEN_NAME = "GOOGLE_GMAIL_CONTABO_REFRESH_TOKEN_RW"
ACCOUNT = "pass.gob1@gmail.com"
SCOPE = "https://www.googleapis.com/auth/gmail.modify openid email"
REDIRECT = "http://localhost:8765/"
CLIENT_NAMES = ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET")


def consent_url(client_id, state, verifier, nonce):
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "login_hint": ACCOUNT,
        "state": state, "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256",
        "include_granted_scopes": "false"})


def code_from_redirect(pasted, state):
    url = urllib.parse.urlsplit(pasted.strip())
    query = urllib.parse.parse_qs(url.query)
    if (url.scheme, url.netloc, url.path) != ("http", "localhost:8765", "/"):
        raise ValueError("unexpected redirect")
    if "error" in query or query.get("state") != [state] or len(query.get("code", [])) != 1:
        raise ValueError("consent failed or state differs")
    return query["code"][0]


def validate_tokens(token, client_id, nonce):
    # Google may spell the email scope using its canonical userinfo URI.
    # This is the same permission, not an additional accepted permission.
    scopes = set(token.get("scope", "").split())
    if "https://www.googleapis.com/auth/userinfo.email" in scopes:
        scopes.remove("https://www.googleapis.com/auth/userinfo.email")
        scopes.add("email")
    if scopes != set(SCOPE.split()):
        raise ValueError("granted scopes differ; nothing stored")
    try:
        part = token["id_token"].split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        valid = (claims.get("email", "").lower() == ACCOUNT and claims.get("email_verified") is True
            and claims.get("aud") == client_id and claims.get("nonce") == nonce
            and claims.get("iss") in {"accounts.google.com", "https://accounts.google.com"}
            and float(claims.get("exp", 0)) > time.time())
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        valid = False
    # The ID token is accepted only directly from Google's TLS token response,
    # never from the caller or the pasted redirect.
    if not valid or not isinstance(token.get("refresh_token"), str) or not token["refresh_token"]:
        raise ValueError("identity or refresh token rejected; nothing stored")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("redirect refused")


def exchange(client_id, client_secret, code, verifier):
    request = urllib.request.Request("https://oauth2.googleapis.com/token", method="POST",
        data=urllib.parse.urlencode({"client_id": client_id, "client_secret": client_secret,
            "code": code, "code_verifier": verifier, "redirect_uri": REDIRECT,
            "grant_type": "authorization_code"}).encode())
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            return json.load(response)
    except Exception:
        raise ValueError("Google token exchange failed; nothing stored") from None


def store_token(token):
    today = dt.date.today()
    result = subprocess.run([sys.executable, str(SETUP), "put", PROJECT, "prod", TOKEN_NAME, "--stdin", "--path", SECRET_PATH,
        "--comment", "Gmail broker runtime credential; agent access constrained by Unix broker",
        "--meta", "provider_name=google-gmail-broker-contabo",
        "--meta", "console_url=https://myaccount.google.com/connections",
        "--meta", "scope=" + SCOPE, "--meta", "owner=CEO", "--meta", "created=" + today.isoformat(),
        "--meta", "expires=" + (today + dt.timedelta(days=6 if "refresh_token_expires_in" in token else 365)).isoformat(),
        "--meta", "used_by=contabo runners/gmail_broker.py",
        "--meta", "blast_radius=mailbox read/write including sending if broker credential is stolen",
        "--meta", "revoke_url=https://myaccount.google.com/connections"],
        input=token["refresh_token"] + "\n", text=True, capture_output=True)
    if result.returncode:
        raise ValueError("Infisical write failed; no credential printed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.inner:
        os.execv(sys.executable, [sys.executable, str(SETUP), "run", PROJECT, "prod", "--as", "contabo", "--path", SECRET_PATH,
            "--", sys.executable, str(Path(__file__).resolve()), "--inner"])
    try:
        client_id, client_secret = (os.environ[n] for n in CLIENT_NAMES)
        state, verifier, nonce = (secrets.token_urlsafe(32) for _ in range(3))
        print('A consent screen in "Testing" status expires the token after 7 days.')
        print("Open this link on your phone, approve, then paste the full localhost address into the Run card:")
        print(consent_url(client_id, state, verifier, nonce), flush=True)
        if sys.stdin.isatty():
            pasted = getpass.getpass("Redirect address (hidden): ")
        else:
            # Run cards provide a pipe; do not use getpass's echoing fallback.
            pasted = sys.stdin.readline(16384)
        code = code_from_redirect(pasted, state)
        token = exchange(client_id, client_secret, code, verifier)
        validate_tokens(token, client_id, nonce)
        store_token(token)
        print(f"Stored {TOKEN_NAME} in {PROJECT}/prod{SECRET_PATH}.")
    except Exception:
        sys.exit("Consent or storage failed; no credential printed. Check client provisioning, identity and exact scopes.")


if __name__ == "__main__":
    main()
