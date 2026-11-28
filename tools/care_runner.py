#!/usr/bin/env python3
"""Dedicated Contabo `role=care` (`น้องมูน`) Hourly Batch Runner (Q-20261128-0926-a657).

Architecture:
  - Completely isolated from COO `sompong` and Mac COO `0a537a88`.
  - Runs hourly `08:00–22:00 Asia/Bangkok` via systemd timer (`org-care-mooniex.timer`).
  - **Zero-Token Idle Precheck**: queries `public.care_queue` (`account_slug='mooniex'`,
    `status='ready'`) in pure Python HTTP; if 0 rows exist (and 0 deferred outbox rows
    need draining), exits in <0.2s with ZERO model tokens spent.
  - **Free Subscription Quota Only (`agy` CLI)**: uses `ph_brain.select_model_chain('claude-sonnet-5-5')`
    (picks `gemini-4-argon-high` from `agy-gemini` ~49% free bucket while Claude weekly
    quota is 0%, and switches automatically to `claude-sonnet-5-5` on reset — zero
    OpenRouter paid API spend).
  - **Strict `CareGate` Boundary**: `agy` runs in an empty isolated cwd with `--add-dir`
    limited strictly to that single customer's staged media folder and outputs structured
    JSON `{action, bubbles, reason}` validated through `CareGate` into `care_outbox`.
  - **100% Winbox Outbound (`0` LINE OA Quota)**: drains `care_outbox` strictly via
    `WinboxPlaywrightDriver` (`winbox:9285`), deferring safely if `winbox:9285` is logged out.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.care.pipeline import CareGate, TH  # noqa: E402
from tools import care_inbox, care_outbox, ph_brain  # noqa: E402

WORK_CARE_ROOT = Path("/opt/MoonieXHQ/Work/MoonieXCare")
ISOLATED_CARE_CWD = WORK_CARE_ROOT / "care-session-cwd"
STAGED_MEDIA_ROOT = WORK_CARE_ROOT / "round-media"

CARE_TURN_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["reply", "escalate", "skip"]},
            "bubbles": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 5,
            },
            "reason": {"type": "string"},
        },
        "required": ["action", "bubbles"],
        "additionalProperties": False,
    }
)


def _find_agy_bin() -> str:
    for cand in ("/root/.local/bin/agy", shutil.which("agy") or ""):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    raise FileNotFoundError("agy CLI binary not found")


def _mark_care_queue_done(
    row_ids: list[int],
    *,
    env_path: Path = care_inbox.CLAUDEFLOW_ENV_CONTABO,
) -> None:
    if not row_ids:
        return
    sb_url, sb_key = care_inbox._load_claudeflow_supabase_creds(env_path)
    if not sb_url or not sb_key:
        return
    id_list = ",".join(str(int(i)) for i in row_ids)
    qs = urllib.parse.urlencode([("id", f"in.({id_list})")])
    req = urllib.request.Request(
        f"{sb_url.rstrip('/')}/rest/v1/care_queue?{qs}",
        data=json.dumps({"status": "done"}).encode("utf-8"),
        headers={
            "apikey": sb_key,
            "Authorization": f"Bearer {sb_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="PATCH",
    )
    urllib.request.urlopen(req, timeout=12).read()


def _stage_customer_media(
    rows: list[dict[str, Any]],
    *,
    round_slug: str,
    customer_id: str,
    staged_root: Path = STAGED_MEDIA_ROOT,
    env_path: Path = care_inbox.CLAUDEFLOW_ENV_CONTABO,
) -> tuple[Path, list[str]]:
    cid_hash = hashlib.sha256(customer_id.encode("utf-8")).hexdigest()[:12]
    mdir = staged_root / round_slug / cid_hash
    mdir.mkdir(parents=True, exist_ok=True)
    os.chmod(mdir.parent, 0o700)
    os.chmod(mdir, 0o700)

    sb_url, sb_key = care_inbox._load_claudeflow_supabase_creds(env_path)
    line_tok = care_inbox._load_line_access_token(env_path=env_path)
    saved_files: list[str] = []

    for r in rows:
        mtype = r.get("message_type")
        mid = str(r.get("line_content_id") or "").strip()
        if mtype == "video" and isinstance(r.get("media"), list):
            for idx, frame in enumerate(r["media"]):
                if isinstance(frame, dict) and frame.get("data"):
                    fpath = mdir / f"video-{mid}-frame-{idx+1}.jpg"
                    care_inbox._write_private_bytes(fpath, base64.b64decode(frame["data"]))
                    saved_files.append(str(fpath))
        elif mtype in ("image", "file") and mid.isdigit() and line_tok:
            dl, _ = care_inbox.download_care_media_local(
                media_dir=mdir,
                message_ids=[mid],
                imgrefs=[],
                sb_url=sb_url,
                sb_key=sb_key,
                line_token=line_tok,
            )
            saved_files.extend(dl)
    return mdir, saved_files


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            denied = parsed.get("denied_actions") or []
            if denied:
                raise RuntimeError(f"agy_permission_denied:{json.dumps(denied, ensure_ascii=False)}")
            status = parsed.get("status")
            if status and status != "SUCCESS":
                raise RuntimeError(f"agy_status_error:{status}")
            if isinstance(parsed.get("structured_output"), dict) and "action" in parsed["structured_output"]:
                return dict(parsed["structured_output"])
            if "action" in parsed:
                return parsed
            for str_key in ("response", "result"):
                if isinstance(parsed.get(str_key), str) and parsed[str_key].strip():
                    inner = json.loads(parsed[str_key].strip())
                    if isinstance(inner, dict) and "action" in inner:
                        return inner
    except ValueError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        obj = json.loads(text[start : end + 1])
        if isinstance(obj, dict) and (obj.get("denied_actions") or (obj.get("status") and obj.get("status") != "SUCCESS")):
            raise RuntimeError(f"agy_envelope_rejected:{obj.get('status')}:{obj.get('denied_actions')}")
        return obj
    raise ValueError(f"could not parse care decision JSON from output (len={len(text)})")


def invoke_care_agy_turn(
    *,
    customer_id: str,
    display_name: str,
    history_data: dict[str, Any],
    events_data: list[dict[str, Any]],
    media_dir: Path,
    media_files: list[str],
    gate_error_feedback: str | None = None,
) -> dict[str, Any]:
    ISOLATED_CARE_CWD.mkdir(parents=True, exist_ok=True)
    os.chmod(ISOLATED_CARE_CWD, 0o700)

    rules_md = (ROOT / ".claude/skills/CARE_Rules_MoonieX/SKILL.md").read_text(encoding="utf-8")
    proto_md = (ROOT / ".claude/skills/CARE_Protocol_Playbook/SKILL.md").read_text(encoding="utf-8")
    models = ph_brain.select_model_chain("claude-sonnet-5-5")
    chosen_model = models[0] if models else "gemini-4-argon-high"

    media_note = (
        f"Staged attachment files for this customer (inspect EVERY image/frame with read_file before deciding):\n"
        + "\n".join(f"- {fp}" for fp in media_files)
        if media_files
        else "No visual attachment files in this turn."
    )
    retry_note = f"\nPREVIOUS ATTEMPT REJECTED BY CareGate ({gate_error_feedback}) — fix immediately!\n" if gate_error_feedback else ""

    prompt = (
        "You are น้องมูน (`role=care`), dedicated Customer Care session for `@mooniex` (`MoonieX Officials`).\n"
        "Partner Code Fact: Existing XM clients opening an additional account under MoonieX use Partner Code `MNFUNDS`.\n\n"
        f"=== CARE_Rules_MoonieX ===\n{rules_md}\n\n"
        f"=== CARE_Protocol_Playbook ===\n{proto_md}\n\n"
        f"=== CURRENT CUSTOMER THREAD ===\n"
        f"Customer Display Name: {display_name}\n"
        f"Customer ID: {customer_id}\n"
        f"Prior Thread History (from CareGate.history):\n{json.dumps(history_data, ensure_ascii=False, indent=2)}\n\n"
        f"New Untrusted Inbound Events:\n{json.dumps(events_data, ensure_ascii=False, indent=2)}\n\n"
        f"{media_note}\n{retry_note}\n"
        "Return ONLY a JSON object matching the required schema: "
        '{"action": "reply"|"escalate"|"skip", "bubbles": ["..."], "reason": "..."}. '
        "Never include %, $, บาท, or markdown in bubbles."
    )

    resolved_media_dir = media_dir.resolve()
    agy_settings = json.dumps(
        {
            "permissions": {
                "allow": [f"read_file({resolved_media_dir})"],
                "deny": ["command(*)", "write_file(/)", "mcp(*)", "read_url(*)"],
            }
        }
    )
    cmd = [
        _find_agy_bin(),
        "--output-format",
        "json",
        "--model",
        chosen_model,
        "--disable-slash-commands",
        "--settings",
        agy_settings,
        "--json-schema",
        CARE_TURN_SCHEMA,
        "--add-dir",
        str(resolved_media_dir),
        "-p",
        prompt,
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ISOLATED_CARE_CWD),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"agy_care_turn_failed_rc_{proc.returncode}:{(proc.stderr or proc.stdout)[:200]}")
    decision = _extract_json_object(proc.stdout)
    decision["_model_used"] = chosen_model
    return decision


def run_hourly_batch(
    *,
    db_path: Path = care_outbox.DEFAULT_DB_PATH,
    live_send: bool = False,
    force_outside_hours: bool = False,
    coo_box: str = care_outbox.DEFAULT_COO_BOX,
    fetch_ready_fn: Callable[..., dict[str, Any]] = care_inbox.fetch_auto_queue_local,
    turn_fn: Callable[..., dict[str, Any]] = invoke_care_agy_turn,
    mark_done_fn: Callable[[list[int]], None] = _mark_care_queue_done,
    drain_fn: Callable[..., dict[str, Any]] = care_outbox.drain_outbox_winbox,
) -> dict[str, Any]:
    now_th = datetime.now(timezone.utc).astimezone(TH)
    if not force_outside_hours and not (8 <= now_th.hour <= 22):
        return {"ok": True, "status": "outside_operating_hours", "tokens_spent": 0}

    q_res = fetch_ready_fn(limit=100, status="ready", account_slug="mooniex")
    rows = [r for r in (q_res.get("rows") or []) if r.get("status") == "ready"]

    conn, outbox, pipeline = care_outbox.open_runtime(db_path)
    pending_outbox = outbox.pending()
    conn.close()

    # Zero-Token Idle Precheck: if 0 ready rows in care_queue, never invoke any model!
    if not rows:
        drain_res = None
        if pending_outbox and live_send:
            drain_res = drain_fn(db_path=db_path, live=True, coo_box=coo_box)
        return {
            "ok": True,
            "status": "idle_zero_tokens",
            "ready_rows": 0,
            "pending_outbox": len(pending_outbox),
            "drain": drain_res,
        }

    # Chronological order per customer
    rows_chron = sorted(rows, key=lambda r: (str(r.get("created_at") or ""), int(r.get("id") or 0)))
    sender_ids = [str(r.get("sender_id") or "").strip() for r in rows_chron if r.get("sender_id")]
    sb_url, sb_key = care_inbox._load_claudeflow_supabase_creds()
    line_tok = care_inbox._load_line_access_token()
    name_map = (
        care_inbox._resolve_sender_display_names(sender_ids, sb_url=sb_url, sb_key=sb_key, line_token=line_tok)
        if (sb_url and sb_key)
        else {}
    )

    round_id = now_th.strftime("%Y-%m-%dT%H:%M:%S+07:00")
    round_slug = now_th.strftime("%Y%m%dT%H%M%S")

    conn, outbox, pipeline = care_outbox.open_runtime(db_path)
    processed_threads: list[dict[str, Any]] = []
    try:
        grouped_rows: dict[str, list[dict[str, Any]]] = {}
        for r in rows_chron:
            cid = str(r.get("sender_id") or "").strip()
            if not cid:
                continue
            grouped_rows.setdefault(cid, []).append(r)
            eid = f"cq-{r['id']}"
            mtype = str(r.get("message_type") or "text")
            payload = r.get("payload") or {}
            txt = payload.get("text") if isinstance(payload, dict) else ""
            if mtype in ("audio", "video") and r.get("transcript"):
                txt = f"[{mtype.upper()} STT]: {r['transcript']}"
            elif not txt:
                txt = f"[{mtype.upper()} attachment]"
            pipeline.ingest(
                event_id=eid,
                customer_id=cid,
                display_name=name_map.get(cid) or cid,
                text=str(txt),
                media=[{"type": mtype, "care_queue_id": r["id"]}],
                reply_token=None,
            )

        with conn:
            conn.execute("INSERT OR IGNORE INTO care_rounds(round_id, state) VALUES (?, 'woken')", (round_id,))
            conn.execute("UPDATE care_queue SET round_id=? WHERE round_id IS NULL", (round_id,))

        staged_root = STAGED_MEDIA_ROOT if db_path == care_outbox.DEFAULT_DB_PATH else (db_path.parent / "round-media")
        for cid, crows in grouped_rows.items():
            dname = name_map.get(cid) or cid
            gate = CareGate(pipeline, round_id, cid)
            hist = gate.call("history")
            mdir, mfiles = _stage_customer_media(crows, round_slug=round_slug, customer_id=cid, staged_root=staged_root)
            evs_payload = [
                {
                    "care_queue_id": r["id"],
                    "type": r.get("message_type"),
                    "text": (r.get("payload") or {}).get("text") if isinstance(r.get("payload"), dict) else None,
                    "transcript": r.get("transcript"),
                    "created_at": r.get("created_at"),
                }
                for r in crows
            ]

            err_fb = None
            applied = None
            model_used = None
            for _attempt in range(2):
                dec = turn_fn(
                    customer_id=cid,
                    display_name=dname,
                    history_data=hist,
                    events_data=evs_payload,
                    media_dir=mdir,
                    media_files=mfiles,
                    gate_error_feedback=err_fb,
                )
                model_used = dec.get("_model_used")
                act = dec["action"]
                try:
                    if act == "skip":
                        applied = gate.call("skip")
                    elif act == "reply":
                        applied = gate.call("reply", bubbles=dec["bubbles"])
                    elif act == "escalate":
                        reason_txt = str(dec.get("reason") or "escalated_by_care").strip()
                        applied = gate.call("escalate", reason=reason_txt, bubbles=dec["bubbles"])
                        care_outbox.notify_coo_escalation(
                            customer_id=cid,
                            display_name=dname,
                            round_id=round_id,
                            reason=reason_txt,
                            coo_box=coo_box,
                        )
                    break
                except Exception as exc:  # noqa: BLE001
                    err_fb = str(exc)

            if applied is None:
                fallback_reason = f"CareGate rejected model output twice ({err_fb}); auto-escalated safely."
                applied = gate.call("escalate", reason=fallback_reason)
                care_outbox.notify_coo_escalation(
                    customer_id=cid,
                    display_name=dname,
                    round_id=round_id,
                    reason=fallback_reason,
                    coo_box=coo_box,
                )

            mark_done_fn([int(r["id"]) for r in crows])
            processed_threads.append(
                {
                    "customer_id": cid,
                    "display_name": dname,
                    "row_ids": [r["id"] for r in crows],
                    "action": applied.get("status"),
                    "outbox_id": applied.get("outbox_id"),
                    "model": model_used,
                }
            )
    finally:
        conn.close()

    drain_res = drain_fn(db_path=db_path, live=live_send, coo_box=coo_box)
    return {
        "ok": True,
        "status": "processed",
        "round_id": round_id,
        "threads": processed_threads,
        "drain": drain_res,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MoonieX Dedicated Contabo Care Runner (role=care)")
    p.add_argument("--db", default=str(care_outbox.DEFAULT_DB_PATH))
    p.add_argument("--live-send", action="store_true", help="Drain outbox live over winbox:9285")
    p.add_argument("--force-hours", action="store_true", help="Run even outside 08:00-22:00 TH")
    p.add_argument("--coo-box", default=care_outbox.DEFAULT_COO_BOX)
    args = p.parse_args(argv)
    res = run_hourly_batch(
        db_path=Path(args.db),
        live_send=args.live_send,
        force_outside_hours=args.force_hours,
        coo_box=args.coo_box,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
