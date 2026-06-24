#!/usr/bin/env python3
"""
Claude usage monitor (VPS, always-on).

Reads the VPS's OWN Claude Code OAuth credentials — a dedicated `claude auth
login` session, independent of the Mac so neither logs the other out — then:

  1. self-refreshes the access token (the rotating refresh token is written
     back to the same credentials file, so the chain never breaks),
  2. polls the Anthropic OAuth usage endpoint (5-hour + weekly utilization),
  3. caches the result to usage.json (for the iPhone widget to fetch later),
  4. evaluates "warm-up" reminders and emails the CEO so the subscription
     gets used to the fullest before each window/weekly budget resets.

Run by a systemd timer every few minutes. Idempotent; safe to run by hand.

Modes:
  monitor.py              poll, cache, evaluate reminders, send any that are due
  monitor.py --dry-run    poll + print what it WOULD email; no send, no state write
  monitor.py --status     print current usage JSON and exit
  monitor.py --test-email send a test email and exit

Why a separate VPS login (not the Mac's token): the OAuth refresh token rotates
on every refresh. Two independent clients sharing one chain rotate each other
out -> repeated logouts. A dedicated VPS login has its own chain. The usage
endpoint is account-level, so the VPS still reports the same numbers.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- paths / constants -----------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CRED_PATH   = os.environ.get("CLAUDE_CRED", "/root/.claude/.credentials.json")
STATE_PATH  = os.environ.get("MON_STATE", os.path.join(BASE_DIR, "state.json"))
CACHE_PATH  = os.environ.get("MON_CACHE", os.path.join(BASE_DIR, "usage.json"))
# Reuse claudeflow's existing Gmail OAuth2 creds (single source of truth).
CF_ENV_PATH = os.environ.get("CF_ENV", "/root/projects/mooniex-claudeflow/.env")

CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"   # public/static Claude Code client
UA        = "claude-code/2.1.187 (external, cli)"     # required or the endpoint rate-limits
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
EMAIL_TO  = os.environ.get("MON_EMAIL_TO", "pass.gob1@gmail.com")

REFRESH_SKEW_MS = 5 * 60 * 1000   # refresh when <5 min to expiry (matches Claude Code)

# --- reminder thresholds (tune here) ---------------------------------------
# 5h-window reset: fire only when you had been using it meaningfully and it just
# rolled over, AND the weekly budget still has room (else a fresh 5h is useless).
FIVE_H_NOTIFY_AFTER = 50   # prev 5h utilization was >= this %
FIVE_H_RESET_BELOW  = 15   # ...and it has now dropped below this %
WEEKLY_ROOM_MIN     = 10   # weekly must have >= this % remaining for a 5h email to matter

# Weekly reset: the big budget refresh.
WEEKLY_RESET_FROM   = 20   # only announce if prev weekly utilization was >= this %
WEEKLY_RESET_BELOW  = 10   # ...and it has now dropped below this %

# "Use it or lose it": weekly budget about to reset with a lot still unused.
USE_IT_WINDOW_H     = 24   # fire when weekly resets within this many hours
USE_IT_UNUSED_MIN   = 30   # ...and >= this % of the weekly budget is still unused


# --- small helpers ---------------------------------------------------------
def now_ms() -> int:
    return int(time.time() * 1000)


def log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} claude-usage-monitor: {msg}",
          flush=True)


def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)   # atomic, same dir


def http(method: str, url: str, headers=None, body=None, form=False, timeout=25):
    """Return (status, parsed_json_or_text). Never raises on HTTP error codes."""
    data = None
    headers = dict(headers or {})
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            data = json.dumps(body).encode()
            headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        status = e.code
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, str(e)
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def parse_iso(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


# --- credentials / token ---------------------------------------------------
def load_cred():
    """Return (full_blob, oauth_dict). oauth_dict is the mutable inner object."""
    blob = load_json(CRED_PATH, None)
    if not blob:
        raise SystemExit(f"no credentials at {CRED_PATH} — run `claude auth login` on the VPS first")
    oauth = blob.get("claudeAiOauth", blob)   # tolerate either shape
    return blob, oauth


def save_cred(blob) -> None:
    tmp = f"{CRED_PATH}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(blob, f)
    os.replace(tmp, CRED_PATH)
    os.chmod(CRED_PATH, 0o600)


def refresh_token(blob, oauth) -> str:
    """POST the rotating refresh token, persist the new pair, return new access token."""
    rt = oauth.get("refreshToken")
    if not rt:
        raise SystemExit("credentials have no refreshToken")
    status, resp = http("POST", TOKEN_URL, body={
        "grant_type": "refresh_token",
        "refresh_token": rt,
        "client_id": CLIENT_ID,
    })
    if status != 200 or not isinstance(resp, dict) or "access_token" not in resp:
        raise SystemExit(f"token refresh failed (http {status}): {str(resp)[:200]}")
    oauth["accessToken"] = resp["access_token"]
    if resp.get("refresh_token"):
        oauth["refreshToken"] = resp["refresh_token"]   # rotated — MUST persist
    if resp.get("expires_in"):
        oauth["expiresAt"] = now_ms() + int(resp["expires_in"]) * 1000
    save_cred(blob)
    log("refreshed access token (rotated refresh token persisted)")
    return oauth["accessToken"]


def ensure_token():
    blob, oauth = load_cred()
    exp = oauth.get("expiresAt", 0)
    if exp - now_ms() < REFRESH_SKEW_MS:
        return refresh_token(blob, oauth), blob, oauth
    return oauth["accessToken"], blob, oauth


# --- usage -----------------------------------------------------------------
def get_usage():
    access, blob, oauth = ensure_token()
    headers = {
        "Authorization": f"Bearer {access}",
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": UA,
        "Content-Type": "application/json",
    }
    status, resp = http("GET", USAGE_URL, headers=headers)
    if status == 401:   # token died early — refresh once and retry
        access = refresh_token(blob, oauth)
        headers["Authorization"] = f"Bearer {access}"
        status, resp = http("GET", USAGE_URL, headers=headers)
    if status != 200 or not isinstance(resp, dict):
        raise SystemExit(f"usage fetch failed (http {status}): {str(resp)[:200]}")
    return resp


def util(block) -> float:
    if not isinstance(block, dict):
        return 0.0
    v = block.get("utilization")
    return float(v) if v is not None else 0.0


# --- email (Gmail API, reusing claudeflow OAuth2 creds) --------------------
def read_env_file(path: str) -> dict:
    out = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return out


def gmail_access_token():
    env = read_env_file(CF_ENV_PATH)
    cid, sec, rt = env.get("GMAIL_CLIENT_ID"), env.get("GMAIL_CLIENT_SECRET"), env.get("GMAIL_REFRESH_TOKEN")
    if not (cid and sec and rt):
        raise SystemExit(f"Gmail creds (GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN) not in {CF_ENV_PATH}")
    status, resp = http("POST", "https://oauth2.googleapis.com/token", body={
        "client_id": cid, "client_secret": sec,
        "refresh_token": rt, "grant_type": "refresh_token",
    }, form=True)
    if status != 200 or "access_token" not in resp:
        raise SystemExit(f"Gmail token refresh failed (http {status}): {str(resp)[:200]}")
    return resp["access_token"]


def send_email(subject: str, body: str) -> None:
    token = gmail_access_token()
    # sender = the authenticated Gmail account
    s, prof = http("GET", "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                   headers={"Authorization": f"Bearer {token}"})
    sender = prof.get("emailAddress", EMAIL_TO) if isinstance(prof, dict) else EMAIL_TO

    msg = EmailMessage()
    msg["To"] = EMAIL_TO
    msg["From"] = sender
    msg["Subject"] = subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    status, resp = http("POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                        headers={"Authorization": f"Bearer {token}"}, body={"raw": raw})
    if status not in (200, 201):
        raise SystemExit(f"Gmail send failed (http {status}): {str(resp)[:200]}")
    log(f"emailed CEO: {subject!r}")


# --- reminder evaluation ---------------------------------------------------
def fmt_reset(ts) -> str:
    d = parse_iso(ts)
    if not d:
        return "ไม่ทราบเวลา"
    try:
        ict = d.astimezone(timezone(timedelta(hours=7)))
        return ict.strftime("%-d %b %H:%M") + " (ICT)"
    except Exception:
        return ts


def hours_until(ts):
    d = parse_iso(ts)
    if not d:
        return None
    return (d - datetime.now(timezone.utc)).total_seconds() / 3600.0


def evaluate(usage, state, dry=False):
    """Return list of (subject, body) emails that are due; mutate `state`."""
    fh, sd = usage.get("five_hour") or {}, usage.get("seven_day") or {}
    fh_u, sd_u = util(fh), util(sd)
    fh_reset, sd_reset = fh.get("resets_at"), sd.get("resets_at")
    weekly_left = round(100 - sd_u, 1)

    first_run = "prev_5h_util" not in state
    prev_fh = state.get("prev_5h_util", fh_u)
    prev_sd = state.get("prev_7d_util", sd_u)

    emails = []

    if not first_run:
        # 1) 5h window reset — you were using it, now it's fresh again
        if prev_fh >= FIVE_H_NOTIFY_AFTER and fh_u < FIVE_H_RESET_BELOW:
            if weekly_left >= WEEKLY_ROOM_MIN:
                emails.append((
                    "🔥 Claude 5-ชม.รีเซ็ตแล้ว — มาใช้ต่อ",
                    f"5-hour window รีเซ็ตแล้ว (เพิ่งใช้ไป {prev_fh:.0f}% → ตอนนี้ {fh_u:.0f}%).\n"
                    f"Weekly ยังเหลือ {weekly_left:.0f}% — มาลุยต่อให้คุ้ม.\n"
                    f"5h reset ครั้งถัดไป: {fmt_reset(fh_reset)}",
                ))
            else:
                log(f"5h reset but weekly nearly out ({weekly_left:.0f}% left) — staying silent")

        # 2) weekly reset — full budget back
        if prev_sd >= WEEKLY_RESET_FROM and sd_u < WEEKLY_RESET_BELOW:
            emails.append((
                "🎉 Claude Weekly รีเซ็ตแล้ว — budget ก้อนใหม่เต็ม",
                f"Weekly budget รีเซ็ตแล้ว ({prev_sd:.0f}% → {sd_u:.0f}%). เริ่มสัปดาห์ใหม่ ใช้ให้คุ้ม.\n"
                f"Weekly reset ครั้งถัดไป: {fmt_reset(sd_reset)}",
            ))

    # 3) use-it-or-lose-it — weekly resets soon and budget still unused (dedupe per cycle)
    h = hours_until(sd_reset)
    if h is not None and 0 < h <= USE_IT_WINDOW_H and weekly_left >= USE_IT_UNUSED_MIN:
        if state.get("notified_useit_for") != sd_reset:
            emails.append((
                f"⏰ Claude Weekly เหลือ {weekly_left:.0f}% จะหมดใน {h:.0f} ชม.",
                f"Weekly budget จะรีเซ็ตใน {h:.0f} ชม. ({fmt_reset(sd_reset)}) "
                f"แต่ยังเหลือ {weekly_left:.0f}% ไม่ได้ใช้ — ใช้ไม่งั้นหายเปล่า (ไม่ roll over).",
            ))
            if not dry:
                state["notified_useit_for"] = sd_reset

    if not dry:
        state["prev_5h_util"] = fh_u
        state["prev_7d_util"] = sd_u
    return emails


# --- main ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="poll + print would-be emails; no send/state")
    ap.add_argument("--status", action="store_true", help="print current usage JSON and exit")
    ap.add_argument("--test-email", action="store_true", help="send a test email and exit")
    args = ap.parse_args()

    if args.test_email:
        send_email("✅ Claude usage monitor — test",
                   "ทดสอบ: ระบบเตือน Claude usage บน VPS ส่งอีเมลได้แล้ว.")
        return

    usage = get_usage()

    # cache for the iPhone widget (Phase B)
    cache = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    for k in ("five_hour", "seven_day", "seven_day_opus", "seven_day_sonnet", "extra_usage"):
        cache[k] = usage.get(k)
    if not args.dry_run:
        save_json(CACHE_PATH, cache)

    if args.status:
        print(json.dumps(cache, indent=2, ensure_ascii=False))
        return

    state = load_json(STATE_PATH, {})
    emails = evaluate(usage, state, dry=args.dry_run)

    if args.dry_run:
        log(f"DRY-RUN 5h={util(usage.get('five_hour')):.0f}% 7d={util(usage.get('seven_day')):.0f}% "
            f"-> {len(emails)} email(s) would send:")
        for subj, body in emails:
            print(f"\n--- {subj} ---\n{body}")
        return

    for subj, body in emails:
        send_email(subj, body)
    save_json(STATE_PATH, state)
    log(f"ok 5h={util(usage.get('five_hour')):.0f}% 7d={util(usage.get('seven_day')):.0f}% "
        f"sent={len(emails)}")


if __name__ == "__main__":
    main()
