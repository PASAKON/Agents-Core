#!/usr/bin/env python3
"""Unified 3-Tier Dual-Path CLI for MoonieX Customer Care (@mooniex / น้องมูน & COO SomPong).

Implements CEO ruling Q-20261128-0625-e55d (2026-11-28) + COO SomPong headless DB fallback:
  - Tier 1 (`auto` — Primary): reads `public.care_queue` from MoonieX-ClaudeFlow's
    Supabase PostgREST API (text + image + audio transcript + video frames/transcript).
  - Tier 2 (`oa` — Browser Fallback & Verifier): reads live LINE OA Manager
    (`MoonieX Officials`, `chat.line.biz/U1434fa89bc696a8ba3e84e6fd6f8e70b` on
    `winbox:9285`) in 100% read-only mode when `care_queue` is down or at quota limits.
  - Tier 3 (`db` — Headless DB + LINE Content API / Supabase Storage Fallback):
    automatically activates whenever `winbox:9285` OA Manager is signed out or
    unreachable (or via `--mode db`). Reads `claudeflow_conversations` +
    `claudeflow_contacts` (with LINE Profile API fallback for display names) and
    downloads every attachment via LINE Content API
    (`https://api-data.line.me/v2/bot/message/<id>/content`) and Supabase Storage
    (`claudeflow_user_images` `imgref_*`).
  - `reconcile`: compares `care_queue` (`auto`) against live OA Manager (`oa`) or `db`
    threads and flags `MISSING_IN_API`.
  - `stage-reply`: enforces `CARE_Rules_MoonieX` + `CARE_Protocol_Playbook` hard gates
    (<= 5 bubbles, blocks unapproved % or money amounts unless `--ceo-approved-amount`
    is set), writes a sha256-pinned send plan (`0600`, `O_NOFOLLOW`), and prints or
    raises the exact `ask_run` card.

Works identically from Contabo (local) or Mac (delegating Contabo/Winbox probes via
`ssh mooniex-vps` without ever printing credentials or storing customer PII in git).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OA_CHAT_URL = "https://chat.line.biz/U1434fa89bc696a8ba3e84e6fd6f8e70b"
OA_DISPLAY_NAME = "MoonieX Officials"
CLAUDEFLOW_ENV_CONTABO = Path("/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env")
WORK_CARE_CONTABO = Path("/opt/MoonieXHQ/Work/MoonieXCare")
STORAGE_BUCKET = "claudeflow_user_images"
WEBHOOK_CONTAINER = "mooniex-claudeflow-claudeflow-webhook-1"

MAX_BUBBLES = 5
# CARE_Rules_MoonieX §1: never quote rebate % or money/per-lot amounts without CEO approval.
_FORBIDDEN_PCT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|เปอร์เซ็นต์)")
_FORBIDDEN_MONEY_RE = re.compile(
    r"(?:\$\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*\$|\b\d[\d,]*(?:\.\d+)?\s*(?:บาท|ดอลลาร์|เหรียญ|usd|thb)\b|\b\d+(?:\.\d+)?\s*/\s*lot\b)",
    re.IGNORECASE,
)
_IMGREF_RE = re.compile(r"\[รูปภาพ:(imgref_[A-Za-z0-9_]+)\]")
_LINE_SENDER_RE = re.compile(r"^U[0-9a-f]{32}$", re.IGNORECASE)
_DOCKER_REQ_LINE_RE = re.compile(r"POST /line/@mooniex\b.*?\bbody=(\{.*)")
_DOCKER_IMG_LINE_RE = re.compile(
    r"\[line/mooniex\]\s+(?:Image|Video|Audio|File)\s+from\s+(U[0-9a-f]{32}):\s+messageId=(\d+)",
    re.IGNORECASE,
)

HttpJsonFn = Callable[[str, dict[str, str], int], Any]
HttpBytesFn = Callable[[str, dict[str, str], int], tuple[bytes, str]]


def is_contabo() -> bool:
    return CLAUDEFLOW_ENV_CONTABO.is_file() or Path("/opt/MoonieXHQ/Agents/Core").is_dir()


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9\u0e00-\u0e7f]+", "-", (name or "").strip()).strip("-").lower()
    return cleaned[:48] or "chat"


def _write_private_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` with `0600` permissions and `O_NOFOLLOW`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path), flags, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _ext_from_content_type(content_type: str) -> str:
    ct = (content_type or "").lower()
    if "png" in ct:
        return "png"
    if "webp" in ct:
        return "webp"
    if "gif" in ct:
        return "gif"
    if "mp4" in ct or "video" in ct:
        return "mp4"
    if "m4a" in ct or "mp4a" in ct or "aac" in ct:
        return "m4a"
    if "mpeg" in ct or "mp3" in ct:
        return "mp3"
    if "audio" in ct:
        return "m4a"
    return "jpg"


def validate_reply_bubbles(
    bubbles: list[str],
    *,
    ceo_approved_amount: bool = False,
) -> tuple[bool, list[str]]:
    """Enforce CARE_Rules_MoonieX §1 & CARE_Protocol_Playbook Step 3 before staging any customer reply."""
    clean = [b.strip() for b in bubbles if b and b.strip()]
    errors: list[str] = []
    if not clean:
        errors.append("empty_reply:ต้องมีข้อความอย่างน้อย 1 บับเบิล")
    if len(clean) > MAX_BUBBLES:
        errors.append(f"too_many_bubbles:ส่งได้ไม่เกิน {MAX_BUBBLES} บับเบิลต่อรอบ (พบ {len(clean)})")
    if not ceo_approved_amount:
        for idx, b in enumerate(clean, 1):
            if _FORBIDDEN_PCT_RE.search(b):
                errors.append(
                    f"forbidden_rebate_pct:บับเบิลที่ {idx} มีตัวเลข % (กฎ §1 ห้ามแจ้ง % รีเบตลูกค้า หาก CEO อนุมัติแล้วให้ใส่ --ceo-approved-amount)"
                )
            if _FORBIDDEN_MONEY_RE.search(b):
                errors.append(
                    f"forbidden_money_amount:บับเบิลที่ {idx} มีจำนวนเงิน/เรทต่อ lot (กฎ §1 ห้ามแจ้งยอดเงินก่อน CEO อนุมัติ หากอนุมัติแล้วให้ใส่ --ceo-approved-amount)"
                )
    return (len(errors) == 0, errors)


def reconcile_records(
    auto_rows: list[dict[str, Any]],
    oa_threads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare `care_queue` (`auto_rows`) against live OA Manager or DB (`oa_threads`)."""
    auto_texts: list[str] = []
    auto_senders: set[str] = set()
    for r in auto_rows:
        sid = str(r.get("sender_id") or r.get("customer_id") or "").strip()
        if sid:
            auto_senders.add(sid)
        payload = r.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except ValueError:
                payload = {"text": payload}
        txt = str(payload.get("text") or r.get("text") or r.get("transcript") or "").strip()
        if txt:
            auto_texts.append(" ".join(txt.split()).lower())

    matched: list[dict[str, Any]] = []
    missing_in_api: list[dict[str, Any]] = []

    for th in oa_threads:
        sid = str(th.get("sender_id") or "").strip()
        preview = " ".join(str(th.get("preview") or "").split()).lower()
        probe = preview[:24] if preview else ""
        is_hit = bool(
            (sid and sid in auto_senders)
            or (probe and any(probe in at or at in preview for at in auto_texts))
        )
        entry = {
            "name": th.get("name"),
            "sender_id": sid or None,
            "time": th.get("time"),
            "unread": th.get("unread", 0),
            "preview": th.get("preview", ""),
        }
        if is_hit:
            matched.append(entry)
        else:
            missing_in_api.append(entry)

    return {
        "auto_count": len(auto_rows),
        "oa_thread_count": len(oa_threads),
        "matched_count": len(matched),
        "missing_in_api_count": len(missing_in_api),
        "matched": matched,
        "missing_in_api": missing_in_api,
    }


def _parse_claudeflow_env(env_path: Path = CLAUDEFLOW_ENV_CONTABO) -> dict[str, str]:
    """Parse select keys from ClaudeFlow .env safely (skipping malformed lines, never printing values)."""
    allowed_keys = {
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_KEY",
        "LINE_CHANNEL_ACCESS_TOKEN",
        "CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET",
    }
    parsed: dict[str, str] = {}
    if not env_path.is_file():
        return parsed
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k in allowed_keys:
            v_clean = v.strip().strip("'").strip('"')
            if v_clean:
                parsed[k] = v_clean
    return parsed


def _load_claudeflow_supabase_creds(env_path: Path = CLAUDEFLOW_ENV_CONTABO) -> tuple[str | None, str | None]:
    """Read SUPABASE_URL and SUPABASE_SERVICE_KEY from env or ClaudeFlow .env without printing them."""
    url = os.environ.get("CLAUDEFLOW_SUPABASE_URL")
    key = os.environ.get("CLAUDEFLOW_SUPABASE_SERVICE_KEY")
    if url and key:
        return url, key
    parsed = _parse_claudeflow_env(env_path)
    return parsed.get("SUPABASE_URL"), (parsed.get("SUPABASE_SERVICE_KEY") or parsed.get("SUPABASE_KEY"))


def _default_http_json(url: str, headers: dict[str, str], timeout: int = 12) -> Any:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _default_http_bytes(url: str, headers: dict[str, str], timeout: int = 20) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type") or "application/octet-stream"
        return resp.read(), ctype


def _decrypt_claudeflow_enc_v1(
    ciphertext: str,
    *,
    tenant_slug: str,
    platform: str,
    account_slug: str,
    field: str,
    keyring_raw: str | None,
) -> str | None:
    """Decrypt `enc:v1:<kid>:<iv_b64url>:<ct_tag_b64url>` when `CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET` is available."""
    if not keyring_raw or not ciphertext.startswith("enc:v1:"):
        return None
    parts = ciphertext.split(":")
    if len(parts) != 5:
        return None
    _, _, kid, iv_b64, ct_tag_b64 = parts
    ring: dict[str, bytes] = {}
    import base64

    for entry in keyring_raw.split(","):
        entry = entry.strip()
        if "=" not in entry:
            continue
        k, _, b64val = entry.partition("=")
        try:
            raw_key = base64.b64decode(b64val.strip())
            if len(raw_key) == 32:
                ring[k.strip()] = raw_key
        except Exception:  # noqa: BLE001
            continue
    key = ring.get(kid)
    if not key:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        pad = lambda s: s + "=" * ((4 - len(s) % 4) % 4)
        iv = base64.urlsafe_b64decode(pad(iv_b64))
        ct_tag = base64.urlsafe_b64decode(pad(ct_tag_b64))
        aad = f"claudeflow:v1:{tenant_slug}:{platform}:{account_slug}:{field}".encode("utf-8")
        plain = AESGCM(key).decrypt(iv, ct_tag, aad)
        return plain.decode("utf-8").strip()
    except Exception:  # noqa: BLE001
        return None


def _load_line_access_token(
    *,
    account_slug: str = "mooniex",
    env_path: Path = CLAUDEFLOW_ENV_CONTABO,
    http_json: HttpJsonFn = _default_http_json,
) -> str | None:
    """Resolve @mooniex LINE channel access token (env override -> claudeflow_webhook_accounts -> ClaudeFlow .env).

    Never logs or returns secret values in error messages.
    """
    override = os.environ.get("MOONIEX_LINE_CHANNEL_ACCESS_TOKEN")
    if override and override.strip():
        return override.strip()

    parsed_env = _parse_claudeflow_env(env_path)
    keyring_raw = os.environ.get("CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET") or parsed_env.get(
        "CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET"
    )

    sb_url, sb_key = _load_claudeflow_supabase_creds(env_path)
    if sb_url and sb_key:
        qs = urllib.parse.urlencode(
            [
                ("platform", "eq.line"),
                ("account_slug", f"eq.{account_slug}"),
                ("select", "platform,account_slug,tenant_slug,credentials"),
                ("limit", "1"),
            ]
        )
        headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}", "Accept": "application/json"}
        for table in ("claudeflow_webhook_accounts", "claudeflow_accounts"):
            try:
                rows = http_json(f"{sb_url.rstrip('/')}/rest/v1/{table}?{qs}", headers, 8)
                if isinstance(rows, list) and rows:
                    row = rows[0]
                    creds = row.get("credentials") or {}
                    tslug = str(row.get("tenant_slug") or account_slug)
                    if isinstance(creds, dict):
                        for field in ("channel_access_token", "access_token", "token"):
                            tok = creds.get(field)
                            if not isinstance(tok, str) or not tok:
                                continue
                            if not tok.startswith("enc:"):
                                return tok.strip()
                            dec = _decrypt_claudeflow_enc_v1(
                                tok,
                                tenant_slug=tslug,
                                platform="line",
                                account_slug=account_slug,
                                field=field,
                                keyring_raw=keyring_raw,
                            )
                            if dec:
                                return dec
            except Exception:  # noqa: BLE001
                continue

    tok = parsed_env.get("LINE_CHANNEL_ACCESS_TOKEN")
    if tok and " " not in tok and len(tok) >= 20:
        return tok
    return None


def fetch_auto_queue_local(
    *,
    limit: int = 25,
    status: str | None = None,
    account_slug: str = "mooniex",
    env_path: Path = CLAUDEFLOW_ENV_CONTABO,
    http_json: HttpJsonFn = _default_http_json,
) -> dict[str, Any]:
    """Query `public.care_queue` directly on Contabo via Supabase PostgREST."""
    sb_url, sb_key = _load_claudeflow_supabase_creds(env_path)
    if not sb_url or not sb_key:
        return {"ok": False, "error": "missing_supabase_env", "rows": []}

    params = [
        ("account_slug", f"eq.{account_slug}"),
        ("order", "created_at.desc"),
        ("limit", str(max(1, min(limit, 200)))),
    ]
    if status:
        params.append(("status", f"eq.{status}"))
    qs = urllib.parse.urlencode(params)
    endpoint = f"{sb_url.rstrip('/')}/rest/v1/care_queue?{qs}"
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Accept": "application/json",
    }
    try:
        rows = http_json(endpoint, headers, 12)
        return {"ok": True, "source": "auto:care_queue", "rows": rows if isinstance(rows, list) else []}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")[:300]
        if exc.code == 404 or "PGRST205" in body or "care_queue" in body:
            return {"ok": False, "error": "care_queue_table_not_created", "detail": body, "rows": []}
        return {"ok": False, "error": f"http_{exc.code}", "detail": body, "rows": []}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "rows": []}


def _resolve_sender_display_names(
    sender_ids: list[str],
    *,
    sb_url: str,
    sb_key: str,
    line_token: str | None,
    http_json: HttpJsonFn = _default_http_json,
) -> dict[str, str]:
    """Map LINE `sender_id` -> `display_name` via `claudeflow_contacts` + LINE Profile API fallback."""
    unique_ids = [s for s in dict.fromkeys(sender_ids) if s]
    if not unique_ids:
        return {}
    names: dict[str, str] = {}
    sb_headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Accept": "application/json",
    }
    in_list = ",".join(unique_ids[:100])
    qs = urllib.parse.urlencode(
        [
            ("platform", "eq.line"),
            ("sender_id", f"in.({in_list})"),
            ("select", "sender_id,display_name,username"),
        ]
    )
    try:
        rows = http_json(f"{sb_url.rstrip('/')}/rest/v1/claudeflow_contacts?{qs}", sb_headers, 10)
        if isinstance(rows, list):
            for r in rows:
                sid = str(r.get("sender_id") or "").strip()
                dname = str(r.get("display_name") or r.get("username") or "").strip()
                if sid and dname:
                    names[sid] = dname
    except Exception:  # noqa: BLE001
        pass

    if line_token:
        line_headers = {"Authorization": f"Bearer {line_token}", "Accept": "application/json"}
        for sid in unique_ids[:40]:
            if sid in names or not _LINE_SENDER_RE.match(sid):
                continue
            try:
                prof = http_json(f"https://api.line.me/v2/bot/profile/{sid}", line_headers, 6)
                if isinstance(prof, dict) and prof.get("displayName"):
                    names[sid] = str(prof["displayName"]).strip()
            except Exception:  # noqa: BLE001
                continue
    return names


def fetch_db_threads_local(
    *,
    limit: int = 20,
    account_slug: str = "mooniex",
    env_path: Path = CLAUDEFLOW_ENV_CONTABO,
    http_json: HttpJsonFn = _default_http_json,
) -> dict[str, Any]:
    """Tier 3 headless fallback: group recent `@mooniex` threads from `claudeflow_conversations`."""
    sb_url, sb_key = _load_claudeflow_supabase_creds(env_path)
    if not sb_url or not sb_key:
        return {"ok": False, "error": "missing_supabase_env", "threads": []}

    sb_headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Accept": "application/json",
    }
    row_limit = max(100, min(limit * 20, 600))
    qs = urllib.parse.urlencode(
        [
            ("platform", "eq.line"),
            ("tenant_slug", f"eq.{account_slug}"),
            ("or", f"(page_id.eq.{account_slug},page_id.is.null)"),
            ("select", "id,sender_id,role,message,created_at,page_id"),
            ("order", "created_at.desc"),
            ("limit", str(row_limit)),
        ]
    )
    try:
        rows = http_json(f"{sb_url.rstrip('/')}/rest/v1/claudeflow_conversations?{qs}", sb_headers, 12)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"conversations_query_failed:{str(exc)[:160]}", "threads": []}

    if not isinstance(rows, list):
        rows = []

    grouped: dict[str, dict[str, Any]] = {}
    for r in rows:
        sid = str(r.get("sender_id") or "").strip()
        if not sid:
            continue
        msg = str(r.get("message") or "").strip()
        role = str(r.get("role") or "user").strip()
        ts = str(r.get("created_at") or "")
        imgrefs = _IMGREF_RE.findall(msg)
        if sid not in grouped:
            grouped[sid] = {
                "sender_id": sid,
                "time": ts,
                "latest_role": role,
                "preview": msg,
                "unread": 1 if role == "user" else 0,
                "message_count": 1,
                "imgrefs": list(imgrefs),
            }
        else:
            g = grouped[sid]
            g["message_count"] += 1
            for ref in imgrefs:
                if ref not in g["imgrefs"]:
                    g["imgrefs"].append(ref)

    selected_sids = list(grouped.keys())[: max(1, limit)]
    line_tok = _load_line_access_token(account_slug=account_slug, env_path=env_path, http_json=http_json)
    name_map = _resolve_sender_display_names(
        selected_sids,
        sb_url=sb_url,
        sb_key=sb_key,
        line_token=line_tok,
        http_json=http_json,
    )

    threads: list[dict[str, Any]] = []
    for idx, sid in enumerate(selected_sids):
        g = grouped[sid]
        threads.append(
            {
                "index": idx,
                "name": name_map.get(sid) or sid,
                "sender_id": sid,
                "time": g["time"],
                "preview": g["preview"],
                "unread": g["unread"],
                "latest_role": g["latest_role"],
                "message_count": g["message_count"],
                "imgref_count": len(g["imgrefs"]),
            }
        )
    return {
        "ok": True,
        "source": "db:claudeflow_conversations+line_api",
        "threads": threads,
    }


def _scan_webhook_logs_for_sender(
    sender_id: str,
    *,
    since: str = "72h",
    log_lines: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Extract raw inbound `@mooniex` webhook events + LINE `messageId`s for `sender_id`."""
    if log_lines is None:
        try:
            proc = subprocess.run(
                ["docker", "logs", "--since", since, WEBHOOK_CONTAINER],
                capture_output=True,
                text=True,
                errors="ignore",
                timeout=12,
            )
            combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
            log_lines = combined.splitlines()
        except Exception:  # noqa: BLE001
            return []

    events_by_mid: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    for line in log_lines:
        if sender_id not in line:
            continue
        m_req = _DOCKER_REQ_LINE_RE.search(line)
        if m_req:
            raw_json = m_req.group(1).strip()
            try:
                body = json.loads(raw_json)
            except ValueError:
                body = None
            if isinstance(body, dict):
                for ev in body.get("events") or []:
                    src = ev.get("source") or {}
                    if src.get("userId") != sender_id:
                        continue
                    msg = ev.get("message") or {}
                    mid = str(msg.get("id") or "").strip()
                    mtype = str(msg.get("type") or ev.get("type") or "unknown")
                    rec = {
                        "message_id": mid or None,
                        "type": mtype,
                        "text": msg.get("text"),
                        "timestamp": ev.get("timestamp"),
                    }
                    if mid:
                        if mid not in events_by_mid:
                            events_by_mid[mid] = rec
                            ordered.append(rec)
                    else:
                        ordered.append(rec)
                continue

        m_img = _DOCKER_IMG_LINE_RE.search(line)
        if m_img and m_img.group(1) == sender_id:
            mid = m_img.group(2)
            if mid not in events_by_mid:
                rec = {"message_id": mid, "type": "media", "text": None, "timestamp": None}
                events_by_mid[mid] = rec
                ordered.append(rec)
    return ordered


def download_care_media_local(
    *,
    media_dir: Path,
    message_ids: list[str],
    imgrefs: list[str],
    sb_url: str | None,
    sb_key: str | None,
    line_token: str | None,
    http_bytes: HttpBytesFn = _default_http_bytes,
) -> tuple[list[str], list[str]]:
    """Download customer media via LINE Content API and Supabase Storage `claudeflow_user_images`."""
    saved: list[str] = []
    errors: list[str] = []

    # 1. LINE Content API (`https://api-data.line.me/v2/bot/message/<id>/content`)
    if message_ids:
        if not line_token:
            errors.append("missing_line_channel_access_token_for_message_ids")
        else:
            headers = {"Authorization": f"Bearer {line_token}"}
            for mid in dict.fromkeys(m for m in message_ids if m and str(m).isdigit()):
                url = f"https://api-data.line.me/v2/bot/message/{mid}/content"
                try:
                    data, ctype = http_bytes(url, headers, 25)
                    ext = _ext_from_content_type(ctype)
                    fpath = media_dir / f"line-{mid}.{ext}"
                    _write_private_bytes(fpath, data)
                    saved.append(str(fpath))
                except urllib.error.HTTPError as exc:
                    errors.append(f"line_content_{mid}:http_{exc.code}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"line_content_{mid}:{str(exc)[:80]}")

    # 2. Supabase Storage (`claudeflow_user_images` for `[รูปภาพ:imgref_xxx]`)
    if imgrefs and sb_url and sb_key:
        sb_headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
        for ref in dict.fromkeys(r for r in imgrefs if r):
            found_for_ref = False
            for ext in ("jpg", "png", "webp", "gif"):
                obj_name = f"{ref}.{ext}"
                url = f"{sb_url.rstrip('/')}/storage/v1/object/{STORAGE_BUCKET}/{obj_name}"
                try:
                    data, _ = http_bytes(url, sb_headers, 15)
                    fpath = media_dir / obj_name
                    _write_private_bytes(fpath, data)
                    saved.append(str(fpath))
                    found_for_ref = True
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code in (400, 404):
                        continue
                    errors.append(f"storage_{ref}:http_{exc.code}")
                    break
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"storage_{ref}:{str(exc)[:80]}")
                    break
            if not found_for_ref:
                errors.append(f"storage_{ref}:not_found")

    return saved, errors


def read_db_chat_local(
    chat_or_sender: str,
    *,
    download_media: bool = False,
    out_dir: str | None = None,
    limit: int = 120,
    extra_message_ids: list[str] | None = None,
    account_slug: str = "mooniex",
    env_path: Path = CLAUDEFLOW_ENV_CONTABO,
    http_json: HttpJsonFn = _default_http_json,
    http_bytes: HttpBytesFn = _default_http_bytes,
    webhook_log_lines: list[str] | None = None,
) -> dict[str, Any]:
    """Tier 3 headless full-thread read + LINE Content API / Storage media download."""
    sb_url, sb_key = _load_claudeflow_supabase_creds(env_path)
    if not sb_url or not sb_key:
        return {"ok": False, "error": "missing_supabase_env"}

    target = chat_or_sender.strip()
    line_tok = _load_line_access_token(account_slug=account_slug, env_path=env_path, http_json=http_json)
    sender_id: str | None = None
    display_name = target

    if _LINE_SENDER_RE.match(target):
        sender_id = target
        nmap = _resolve_sender_display_names(
            [sender_id], sb_url=sb_url, sb_key=sb_key, line_token=line_tok, http_json=http_json
        )
        display_name = nmap.get(sender_id) or sender_id
    else:
        # Resolve display name against recent threads (contacts + LINE Profile API)
        th_res = fetch_db_threads_local(
            limit=40, account_slug=account_slug, env_path=env_path, http_json=http_json
        )
        target_lower = target.lower()
        exact_hit = None
        partial_hit = None
        for th in th_res.get("threads") or []:
            nm = str(th.get("name") or "").strip()
            if nm == target or nm.lower() == target_lower:
                exact_hit = th
                break
            if target_lower in nm.lower() and partial_hit is None:
                partial_hit = th
        chosen = exact_hit or partial_hit
        if not chosen:
            return {
                "ok": False,
                "error": f"sender_not_found_in_db:{target}",
            }
        sender_id = str(chosen["sender_id"])
        display_name = str(chosen.get("name") or sender_id)

    sb_headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Accept": "application/json",
    }
    qs = urllib.parse.urlencode(
        [
            ("platform", "eq.line"),
            ("sender_id", f"eq.{sender_id}"),
            ("tenant_slug", f"eq.{account_slug}"),
            ("or", f"(page_id.eq.{account_slug},page_id.is.null)"),
            ("select", "id,role,message,created_at"),
            ("order", "created_at.desc"),
            ("limit", str(max(1, min(limit, 500)))),
        ]
    )
    try:
        rows = http_json(f"{sb_url.rstrip('/')}/rest/v1/claudeflow_conversations?{qs}", sb_headers, 12)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"conversations_read_failed:{str(exc)[:160]}"}

    chron_rows = list(reversed(rows)) if isinstance(rows, list) else []
    imgrefs: list[str] = []
    formatted_lines: list[str] = []
    for r in chron_rows:
        msg = str(r.get("message") or "").strip()
        role = "CUSTOMER" if r.get("role") == "user" else "ADMIN/BOT"
        ts = str(r.get("created_at") or "")
        for ref in _IMGREF_RE.findall(msg):
            if ref not in imgrefs:
                imgrefs.append(ref)
        formatted_lines.append(f"[{ts}] {role}: {msg}")

    webhook_events = _scan_webhook_logs_for_sender(sender_id, log_lines=webhook_log_lines)
    discovered_mids = [
        str(ev["message_id"])
        for ev in webhook_events
        if ev.get("message_id") and ev.get("type") in ("image", "video", "audio", "file", "media")
    ]
    for extra in extra_message_ids or []:
        if extra and extra not in discovered_mids:
            discovered_mids.append(extra)

    if webhook_events:
        formatted_lines.append(f"\n--- Raw Webhook Events ({len(webhook_events)} event(s) in last 72h) ---")
        for ev in webhook_events:
            txt_part = f": {ev['text']}" if ev.get("text") else ""
            formatted_lines.append(f"  - type={ev.get('type')} message_id={ev.get('message_id')}{txt_part}")

    saved_media: list[str] = []
    media_errors: list[str] = []
    if download_media:
        slug = _slugify(display_name)
        media_dir = Path(out_dir) if out_dir else (WORK_CARE_CONTABO / "media" / slug)
        saved_media, media_errors = download_care_media_local(
            media_dir=media_dir,
            message_ids=discovered_mids,
            imgrefs=imgrefs,
            sb_url=sb_url,
            sb_key=sb_key,
            line_token=line_tok,
            http_bytes=http_bytes,
        )

    return {
        "ok": True,
        "source": "db:claudeflow_conversations+line_content_api",
        "chat": display_name,
        "sender_id": sender_id,
        "message_count": len(chron_rows),
        "webhook_event_count": len(webhook_events),
        "imgrefs": imgrefs,
        "media_message_ids": discovered_mids,
        "media_files": saved_media,
        "media_errors": media_errors,
        "text": "\n".join(formatted_lines),
    }


def _ensure_oa_tunnel_local(local_port: int = 19285, remote_port: int = 9285) -> bool:
    """Ensure SSH port-forward `127.0.0.1:19285 -> winbox:9285` is open on Contabo."""
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{local_port}/json/version", timeout=2).read()
        return True
    except Exception:  # noqa: BLE001
        pass
    subprocess.run(
        [
            "ssh",
            "-n",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            "-o",
            "ExitOnForwardFailure=yes",
            "-f",
            "-N",
            "-L",
            f"127.0.0.1:{local_port}:127.0.0.1:{remote_port}",
            "winbox",
        ],
        capture_output=True,
        text=True,
    )
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{local_port}/json/version", timeout=3).read()
        return True
    except Exception:  # noqa: BLE001
        return False


def fetch_oa_list_local(*, limit: int = 20, cdp_port: int = 19285) -> dict[str, Any]:
    """Read-only list of recent threads from LINE OA Manager (`winbox:9285` via tunnel)."""
    if not _ensure_oa_tunnel_local(cdp_port, 9285):
        return {"ok": False, "error": "oa_browser_home_unreachable_winbox_9285", "threads": []}

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
        page = browser.contexts[0].new_page()
        try:
            page.goto(OA_CHAT_URL, timeout=45000)
            page.wait_for_timeout(5500)
            body_txt = page.locator("body").inner_text()
            if OA_DISPLAY_NAME not in body_txt:
                return {"ok": False, "error": "oa_not_signed_in_or_wrong_channel", "threads": []}

            threads = page.evaluate(
                """(maxItems) => {
                  const items = [...document.querySelectorAll('.list-group-item')].slice(0, maxItems);
                  return items.map((el, idx) => {
                    const lines = (el.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean);
                    const badge = el.querySelector('.badge, [class*="badge"]');
                    const unread = badge ? parseInt(badge.innerText.trim(), 10) || 0 : 0;
                    return {
                      index: idx,
                      name: lines[0] || '',
                      time: lines.length > 2 ? lines[lines.length - 1] : (lines[1] || ''),
                      preview: lines.length > 2 ? lines.slice(1, -1).join(' ') : (lines[1] || ''),
                      unread: unread
                    };
                  });
                }""",
                limit,
            )
            return {"ok": True, "source": "oa:line-oa-win:9285", "threads": threads}
        finally:
            page.close()


def read_oa_chat_local(
    chat_name: str,
    *,
    download_media: bool = False,
    out_dir: str | None = None,
    cdp_port: int = 19285,
) -> dict[str, Any]:
    """Read-only full chat read + optional media screenshot capture for one customer thread."""
    if not _ensure_oa_tunnel_local(cdp_port, 9285):
        return {"ok": False, "error": "oa_browser_home_unreachable_winbox_9285"}

    from playwright.sync_api import sync_playwright

    slug = _slugify(chat_name)
    media_dir = Path(out_dir) if out_dir else (WORK_CARE_CONTABO / "media" / slug)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
        page = browser.contexts[0].new_page()
        try:
            page.goto(OA_CHAT_URL, timeout=45000)
            page.wait_for_timeout(5500)
            body_txt = page.locator("body").inner_text()
            if OA_DISPLAY_NAME not in body_txt:
                return {"ok": False, "error": "oa_not_signed_in_or_wrong_channel"}

            page.get_by_text(chat_name, exact=True).first.click(timeout=8000)
            page.wait_for_timeout(3500)
            active_name = page.evaluate(
                "(() => { const a = document.querySelector('.list-group-item.active'); return a ? a.innerText.split('\\n')[0].trim() : ''; })()"
            )
            if active_name != chat_name.strip():
                return {
                    "ok": False,
                    "error": f"header_mismatch: expected {chat_name!r}, got {active_name!r}",
                }

            pane_text = page.evaluate(
                """() => {
                  const main = document.querySelector('main, .chat-body, [class*="chat-content"]') || document.body;
                  return main.innerText;
                }"""
            )
            saved_media: list[str] = []
            if download_media:
                media_dir.mkdir(parents=True, exist_ok=True)
                os.chmod(media_dir, 0o700)
                els = page.locator("img, video")
                count = els.count()
                idx_saved = 0
                for i in range(count):
                    el = els.nth(i)
                    box = el.bounding_box()
                    if not box or box["width"] < 110 or box["height"] < 110:
                        continue
                    idx_saved += 1
                    fpath = media_dir / f"media-{idx_saved:02d}.png"
                    el.screenshot(path=str(fpath))
                    os.chmod(fpath, 0o600)
                    saved_media.append(str(fpath))

            return {
                "ok": True,
                "source": "oa:line-oa-win:9285",
                "chat": active_name,
                "text": pane_text,
                "media_files": saved_media,
            }
        finally:
            page.close()


def _delegate_to_contabo(argv: list[str]) -> int:
    """When invoked on Mac, forward execution to Contabo's Agents-Core venv seamlessly."""
    quoted = " ".join(subprocess.list2cmdline([a]) if " " in a else repr(a) for a in argv)
    remote_cmd = f"cd /opt/MoonieXHQ/Agents/Core && .venv/bin/python tools/care_inbox.py {quoted}"
    proc = subprocess.run(["ssh", "-o", "ConnectTimeout=6", "mooniex-vps", remote_cmd])
    return proc.returncode


def run_list_cascade(
    *,
    mode: str,
    limit: int,
    status: str | None = None,
    include_oa_always: bool = False,
    include_db_always: bool = False,
    auto_fn: Callable[..., dict[str, Any]] = fetch_auto_queue_local,
    oa_fn: Callable[..., dict[str, Any]] = fetch_oa_list_local,
    db_fn: Callable[..., dict[str, Any]] = fetch_db_threads_local,
) -> dict[str, Any]:
    """Execute 3-tier list cascade (`auto` -> `oa` -> `db`) according to `mode`."""
    result: dict[str, Any] = {
        "mode_requested": mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if mode == "auto":
        auto_res = auto_fn(limit=limit, status=status)
        result["auto"] = auto_res
        result["active_path"] = "auto"
        return result

    if mode == "db":
        db_res = db_fn(limit=limit)
        result["db"] = db_res
        result["active_path"] = "db"
        return result

    if mode == "oa":
        oa_res = oa_fn(limit=limit)
        result["oa"] = oa_res
        if not oa_res.get("ok"):
            db_res = db_fn(limit=limit)
            result["db"] = db_res
            result["active_path"] = "db_fallback" if db_res.get("ok") else "oa"
        else:
            result["active_path"] = "oa"
        return result

    # mode == "both": Tier 1 (`auto`) -> Tier 2 (`oa`) -> Tier 3 (`db`)
    auto_res = auto_fn(limit=limit, status=status)
    result["auto"] = auto_res
    need_fallback = not auto_res.get("ok") or not (auto_res.get("rows") or [])
    if need_fallback or include_oa_always:
        oa_res = oa_fn(limit=limit)
        result["oa"] = oa_res
        if not oa_res.get("ok") or include_db_always:
            db_res = db_fn(limit=limit)
            result["db"] = db_res
            if not auto_res.get("ok") and not oa_res.get("ok"):
                result["active_path"] = "db_fallback"
            elif oa_res.get("ok"):
                result["active_path"] = "oa_fallback" if not auto_res.get("ok") else "both"
            else:
                result["active_path"] = "auto"
        else:
            result["active_path"] = "oa_fallback" if not auto_res.get("ok") else "both"
    else:
        if include_db_always:
            result["db"] = db_fn(limit=limit)
        result["active_path"] = "auto"
    return result


def run_read_cascade(
    chat: str,
    *,
    mode: str,
    download_media: bool = False,
    out_dir: str | None = None,
    extra_message_ids: list[str] | None = None,
    oa_read_fn: Callable[..., dict[str, Any]] = read_oa_chat_local,
    db_read_fn: Callable[..., dict[str, Any]] = read_db_chat_local,
) -> dict[str, Any]:
    """Execute read with automatic fallback from `oa` (`winbox:9285`) to `db` (`claudeflow_conversations` + LINE Content API)."""
    if mode == "db" or _LINE_SENDER_RE.match(chat.strip()):
        return db_read_fn(
            chat,
            download_media=download_media,
            out_dir=out_dir,
            extra_message_ids=extra_message_ids,
        )

    oa_res = oa_read_fn(chat, download_media=download_media, out_dir=out_dir)
    if oa_res.get("ok") or mode == "oa_strict":
        return oa_res

    db_res = db_read_fn(
        chat,
        download_media=download_media,
        out_dir=out_dir,
        extra_message_ids=extra_message_ids,
    )
    if db_res.get("ok"):
        db_res["oa_fallback_reason"] = oa_res.get("error")
        return db_res
    return oa_res


def cmd_list(args: argparse.Namespace) -> int:
    if not is_contabo():
        fwd = ["list", "--mode", args.mode, "--limit", str(args.limit)]
        if args.status:
            fwd.extend(["--status", args.status])
        if args.include_oa_always:
            fwd.append("--include-oa-always")
        if args.include_db_always:
            fwd.append("--include-db-always")
        if args.json:
            fwd.append("--json")
        return _delegate_to_contabo(fwd)

    result = run_list_cascade(
        mode=args.mode,
        limit=args.limit,
        status=args.status,
        include_oa_always=args.include_oa_always,
        include_db_always=args.include_db_always,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_format_list_human(result))
    if args.mode == "auto":
        return 0 if (result.get("auto") or {}).get("ok") else 1
    if args.mode == "db":
        return 0 if (result.get("db") or {}).get("ok") else 1
    return 0


def _format_list_human(result: dict[str, Any]) -> str:
    lines = [f"=== MoonieX Care Inbox (active_path={result.get('active_path', result.get('mode_requested'))}) ==="]
    auto = result.get("auto")
    if auto:
        if auto.get("ok"):
            rows = auto.get("rows") or []
            lines.append(f"[TIER 1 · AUTO care_queue] {len(rows)} row(s)")
            for r in rows:
                payload = r.get("payload") or {}
                txt = payload.get("text") if isinstance(payload, dict) else str(payload)
                preview = (txt or r.get("transcript") or f"<{r.get('message_type')}>")[:80]
                lines.append(
                    f"  - id={r.get('id')} [{r.get('status')}] type={r.get('message_type')} sender={str(r.get('sender_id'))[:10]}.. at={r.get('created_at')}: {preview}"
                )
        else:
            lines.append(f"[TIER 1 · AUTO care_queue] unavailable ({auto.get('error')})")
    oa = result.get("oa")
    if oa:
        if oa.get("ok"):
            threads = oa.get("threads") or []
            lines.append(f"[TIER 2 · OA Manager winbox:9285] {len(threads)} thread(s)")
            for th in threads:
                ub = f" [UNREAD:{th['unread']}]" if th.get("unread") else ""
                lines.append(f"  - {th.get('name')}{ub} ({th.get('time')}): {str(th.get('preview'))[:80]}")
        else:
            lines.append(f"[TIER 2 · OA Manager winbox:9285] unavailable ({oa.get('error')})")
    db = result.get("db")
    if db:
        if db.get("ok"):
            threads = db.get("threads") or []
            lines.append(f"[TIER 3 · DB claudeflow_conversations + LINE API] {len(threads)} thread(s)")
            for th in threads:
                ub = " [NEEDS_REPLY]" if th.get("unread") else ""
                imgs = f" [{th['imgref_count']} img]" if th.get("imgref_count") else ""
                lines.append(
                    f"  - {th.get('name')} ({str(th.get('sender_id'))[:10]}..){ub}{imgs} ({th.get('time')}): {str(th.get('preview'))[:80]}"
                )
        else:
            lines.append(f"[TIER 3 · DB claudeflow_conversations] unavailable ({db.get('error')})")
    return "\n".join(lines)


def cmd_read(args: argparse.Namespace) -> int:
    if not is_contabo():
        fwd = ["read", "--chat", args.chat, "--mode", args.mode]
        if args.download_media:
            fwd.append("--download-media")
        if args.out_dir:
            fwd.extend(["--out-dir", args.out_dir])
        for mid in args.message_id or []:
            fwd.extend(["--message-id", mid])
        if args.json:
            fwd.append("--json")
        return _delegate_to_contabo(fwd)

    res = run_read_cascade(
        args.chat,
        mode=args.mode,
        download_media=args.download_media,
        out_dir=args.out_dir,
        extra_message_ids=args.message_id,
    )
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        if not res.get("ok"):
            print(f"ERROR: {res.get('error')}", file=sys.stderr)
            return 1
        fb_note = f" [fallback from OA: {res['oa_fallback_reason']}]" if res.get("oa_fallback_reason") else ""
        print(f"=== Chat: {res['chat']} ({res['source']}){fb_note} ===")
        if res.get("sender_id"):
            print(f"Sender ID: {res['sender_id']}")
        if res.get("media_files"):
            print(f"Saved {len(res['media_files'])} media file(s): {', '.join(res['media_files'])}")
        if res.get("media_errors"):
            print(f"Media warnings: {', '.join(res['media_errors'])}")
        print(res.get("text", ""))
    return 0 if res.get("ok") else 1


def cmd_reconcile(args: argparse.Namespace) -> int:
    if not is_contabo():
        return _delegate_to_contabo(["reconcile", "--limit", str(args.limit)] + (["--json"] if args.json else []))

    auto_res = fetch_auto_queue_local(limit=max(args.limit * 4, 50))
    oa_res = fetch_oa_list_local(limit=args.limit)
    verifier_source = "oa"
    threads = oa_res.get("threads") or []
    db_res: dict[str, Any] | None = None
    if not oa_res.get("ok"):
        db_res = fetch_db_threads_local(limit=args.limit)
        if db_res.get("ok"):
            verifier_source = "db_fallback"
            threads = db_res.get("threads") or []

    rec = reconcile_records(auto_res.get("rows") or [], threads)
    payload = {
        "auto_ok": auto_res.get("ok"),
        "auto_error": auto_res.get("error"),
        "oa_ok": oa_res.get("ok"),
        "oa_error": oa_res.get("error"),
        "verifier_source": verifier_source,
        "db_ok": db_res.get("ok") if db_res else None,
        "reconcile": rec,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"=== Dual-Path Reconcile (verifier={verifier_source}) ===\n"
            f"auto_ok={payload['auto_ok']} ({rec['auto_count']} rows) | "
            f"oa_ok={payload['oa_ok']} | threads_checked={rec['oa_thread_count']}\n"
            f"matched={rec['matched_count']} | missing_in_api={rec['missing_in_api_count']}"
        )
        for m in rec["missing_in_api"]:
            print(f"  [MISSING_IN_API] {m['name']} ({m['time']}): {m['preview'][:80]}")
    return 0


def cmd_stage_reply(args: argparse.Namespace) -> int:
    ok, errs = validate_reply_bubbles(args.text, ceo_approved_amount=args.ceo_approved_amount)
    if not ok:
        for e in errs:
            print(f"GATE REFUSED: {e}", file=sys.stderr)
        return 2

    if not is_contabo():
        fwd = ["stage-reply", "--chat", args.chat]
        for t in args.text:
            fwd.extend(["--text", t])
        if args.ceo_approved_amount:
            fwd.append("--ceo-approved-amount")
        if args.raise_card:
            fwd.append("--raise-card")
        return _delegate_to_contabo(fwd)

    staged_dir = WORK_CARE_CONTABO / "staged"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(args.chat)
    plan = [{"name": args.chat.strip(), "lines": [t.strip() for t in args.text if t.strip()]}]
    raw_bytes = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    plan_path = staged_dir / f"reply-{ts}-{slug}.json"
    _write_private_bytes(plan_path, raw_bytes)

    sender_script = "/opt/MoonieXHQ/Work/MoonieXCare/pending-2026-11-27/tools/oa_send_final.py"
    pinned_cmd = (
        f"echo '{digest}  {plan_path}' | sha256sum -c - && "
        f"/opt/MoonieXHQ/Agents/Core/.venv/bin/python {sender_script} {plan_path}"
    )
    out = {
        "ok": True,
        "chat": args.chat.strip(),
        "bubbles": len(plan[0]["lines"]),
        "plan_path": str(plan_path),
        "sha256": digest,
        "command": pinned_cmd,
    }
    if args.raise_card:
        card_proc = subprocess.run(
            [
                "/opt/MoonieXHQ/Agents/Core/.venv/bin/python",
                "/opt/MoonieXHQ/Agents/Core/tools/ask_run.py",
                "create",
                "--host",
                "contabo",
                "--project",
                "MoonieXCare",
                "--lane",
                "coo",
                "--what",
                f"ส่งตอบแชท LINE OA: {args.chat.strip()[:20]}",
                "--does",
                f"ส่งข้อความ {len(plan[0]['lines'])} บับเบิลหา {args.chat.strip()[:28]}",
                "--impact",
                "ส่งข้อความถึงลูกค้าจริงบน LINE OA @mooniex (sha256-pinned)",
                "--command",
                pinned_cmd,
                "--why",
                "ผ่าน care gate และล็อก sha256 ของข้อความแล้ว",
                "--expected",
                f"{args.chat.strip()[:30]} SENT",
                "--risk",
                "amber",
            ],
            capture_output=True,
            text=True,
        )
        out["card_stdout"] = card_proc.stdout.strip()
        out["card_rc"] = card_proc.returncode

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MoonieX Care Unified 3-Tier CLI (auto care_queue + OA Manager + DB/LINE Content API)"
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    p_list = sub.add_parser("list", help="List recent customer chats/items (auto, oa, db, or automatic cascade)")
    p_list.add_argument("--mode", choices=("both", "auto", "oa", "db"), default="both")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--status", default=None)
    p_list.add_argument("--include-oa-always", action="store_true")
    p_list.add_argument("--include-db-always", action="store_true")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_read = sub.add_parser("read", help="Read full chat thread + optionally save customer images/videos")
    p_read.add_argument("--chat", required=True, help="Customer display name or LINE userId (U...)")
    p_read.add_argument("--mode", choices=("oa", "db", "auto", "oa_strict"), default="oa")
    p_read.add_argument("--download-media", action="store_true")
    p_read.add_argument("--out-dir", default=None)
    p_read.add_argument(
        "--message-id",
        action="append",
        default=[],
        help="Optional explicit LINE messageId(s) to fetch via LINE Content API",
    )
    p_read.add_argument("--json", action="store_true")
    p_read.set_defaults(func=cmd_read)

    p_rec = sub.add_parser("reconcile", help="Compare care_queue (API Auto) vs live LINE OA Manager / DB")
    p_rec.add_argument("--limit", type=int, default=20)
    p_rec.add_argument("--json", action="store_true")
    p_rec.set_defaults(func=cmd_reconcile)

    p_rep = sub.add_parser("stage-reply", help="Validate reply against CARE gate and stage sha256-pinned card")
    p_rep.add_argument("--chat", required=True)
    p_rep.add_argument("--text", action="append", required=True, help="One flag per bubble (max 5)")
    p_rep.add_argument("--ceo-approved-amount", action="store_true")
    p_rep.add_argument("--raise-card", action="store_true")
    p_rep.set_defaults(func=cmd_stage_reply)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
