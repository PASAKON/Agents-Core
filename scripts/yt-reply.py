#!/usr/bin/env python3
"""Post YouTube comment replies from a replies JSON, no browser, no model.

One-time auth (the CEO runs these, each as a plain `!` command):
    python3 scripts/yt-reply.py auth-url
        -> open the printed URL, pick the account that owns the channel, allow.
           The browser then fails to load a localhost page. That is expected:
           copy the WHOLE address from the address bar.
    python3 scripts/yt-reply.py auth-finish '<the address you copied>'

Posting:
    python3 scripts/yt-reply.py post docs/promo/replies/<file>.json [--dry-run]
Resumable: every reply that went out is recorded in <file>.sent.json and is
never posted twice.
"""
import base64, hashlib, json, os, random, secrets, sys, time
import urllib.error, urllib.parse, urllib.request
from pathlib import Path

CLIENT_ENV = Path("/root/projects/mooniex-claudeflow/.env")
STORE = Path("/root/.config/mooniex/youtube")
TOKEN, PENDING = STORE / "token.json", STORE / "pending.json"
SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
REDIRECT = "http://localhost:8765/"
API = "https://www.googleapis.com/youtube/v3"


def client():
    env = {}
    for ln in CLIENT_ENV.read_text().splitlines():
        if ln.startswith("GOOGLE_OAUTH_CLIENT_") and "=" in ln:
            k, v = ln.split("=", 1)
            env[k] = v.strip().strip('"')
    return env["GOOGLE_OAUTH_CLIENT_ID"], env["GOOGLE_OAUTH_CLIENT_SECRET"]


def post_form(url, fields):
    data = urllib.parse.urlencode(fields).encode()
    return json.load(urllib.request.urlopen(url, data, timeout=30))


def auth_url():
    cid, _ = client()
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(16)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    STORE.mkdir(parents=True, exist_ok=True)
    PENDING.write_text(json.dumps({"verifier": verifier, "state": state}))
    os.chmod(PENDING, 0o600)
    print("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": REDIRECT, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"}))


def auth_finish(pasted):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(pasted.strip()).query)
    pend = json.loads(PENDING.read_text())
    if q.get("state", [""])[0] != pend["state"]:
        sys.exit("state does not match the last auth-url; run auth-url again and use that link")
    if "code" not in q:
        sys.exit("no code in that address: " + ", ".join(f"{k}={v[0]}" for k, v in q.items()))
    cid, csec = client()
    tok = post_form("https://oauth2.googleapis.com/token", {
        "client_id": cid, "client_secret": csec, "code": q["code"][0],
        "code_verifier": pend["verifier"], "redirect_uri": REDIRECT, "grant_type": "authorization_code"})
    if "refresh_token" not in tok:
        sys.exit("Google returned no refresh token; run auth-url again (it forces the consent screen)")
    TOKEN.write_text(json.dumps({"refresh_token": tok["refresh_token"], "scope": tok.get("scope")}))
    os.chmod(TOKEN, 0o600)
    PENDING.unlink()
    ch = api("GET", "channels?part=snippet&mine=true")
    names = [i["snippet"]["title"] for i in ch.get("items", [])]
    print("authorised as channel:", names or "NO CHANNEL on this account - pick the channel's account")


def access_token():
    cid, csec = client()
    rt = json.loads(TOKEN.read_text())["refresh_token"]
    return post_form("https://oauth2.googleapis.com/token", {
        "client_id": cid, "client_secret": csec, "refresh_token": rt, "grant_type": "refresh_token"})["access_token"]


def api(method, path, body=None):
    req = urllib.request.Request(f"{API}/{path}", method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + access_token(),
                                          "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        err = json.loads(e.read() or b"{}").get("error", {})
        sys.exit(f"YouTube API {e.code}: {[x.get('reason') for x in err.get('errors', [])]} {err.get('message', '')}")


def post(path, dry):
    plan = json.loads(Path(path).read_text())
    ledger_p = Path(path).with_suffix(".sent.json")
    ledger = json.loads(ledger_p.read_text()) if ledger_p.exists() else {}
    todo = [r for r in plan["replies"] if r["ref"] not in ledger]
    print(f"{len(todo)} to post, {len(ledger)} already sent")
    for i, r in enumerate(todo):
        parent = r["comment_id"].split(".")[0]
        text = r["text"] if "." not in r["comment_id"] else f"{r['author']} {r['text']}"
        print(f"[{r['ref']}] -> {r['author']}: {text}")
        if dry:
            continue
        res = api("POST", "comments?part=snippet",
                  {"snippet": {"parentId": parent, "textOriginal": text}})
        ledger[r["ref"]] = {"reply_id": res["id"], "text": text,
                            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        ledger_p.write_text(json.dumps(ledger, ensure_ascii=False, indent=1))
        if i < len(todo) - 1:
            time.sleep(random.uniform(25, 60))
    print(f"done: {len(ledger)} of {len(plan['replies'])} sent, ledger {ledger_p}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "auth-url":
        auth_url()
    elif cmd == "auth-finish" and len(sys.argv) > 2:
        auth_finish(sys.argv[2])
    elif cmd == "post" and len(sys.argv) > 2:
        post(sys.argv[2], "--dry-run" in sys.argv)
    else:
        sys.exit(__doc__)
