#!/usr/bin/env python3
"""Internal Outbox CLI & Gate API for MoonieX Care (@mooniex / น้องมูน).

Implements CEO ruling Q-20261128-0926-a657:
  - 100% Winbox OA Script outbound (`winbox_only=True` -> zero LINE OA API quota).
  - Isolates `role=care` (`น้องมูน`): she interacts strictly through `CareGate`
    (`history`, `media`, `reply`, `escalate`, `skip`) against `care_runtime.db`
    and never touches `winbox:9285` directly.
  - `drain`: backend worker drains queued/deferred `care_outbox` rows over
    `127.0.0.1:19285 -> winbox:9285` (`WinboxPlaywrightDriver` + `home_lock`),
    verifying `MoonieX Officials` (`@587kfqpt`) + exact recipient display name
    before sending, and halting via kill-switch (`care_sender_enabled='false'`)
    with an alert to COO if `winbox:9285` logs out or hits a captcha.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.care.browser_sender import (  # noqa: E402
     KILL_ALERT_FLAG,
    KILL_REASON_FLAG,
    SENDER_ENABLED_FLAG,
    BrowserSender,
    BrowserSenderConfig,
    WinboxPlaywrightDriver,
    load_care_config,
    manual_reenable_sender,
)
from lib.care.outbox import DEFAULT_BASIC_ID, Outbox, make_idempotency_key  # noqa: E402
from lib.care.pipeline import CareGate, CarePipeline, TH  # noqa: E402
from lib.care.quota import QuotaConfig  # noqa: E402
from lib.care.sender import CareSender  # noqa: E402

DEFAULT_DB_PATH = Path("/opt/MoonieXHQ/Work/MoonieXCare/state/care_runtime.db")
DEFAULT_COO_BOX = "project_head-fe7a78a0"


def _forbidden_api_http(method: str, url: str, headers: dict, body: Any):
    raise RuntimeError(f"LINE_API_FORBIDDEN_BY_Q_20261128_0926_A657:{method}:{url}")


def open_runtime(db_path: Path = DEFAULT_DB_PATH) -> tuple[sqlite3.Connection, Outbox, CarePipeline]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(db_path.parent, 0o700)
    conn = sqlite3.connect(str(db_path))
    if db_path.is_file():
        os.chmod(db_path, 0o600)
    now_fn = lambda: datetime.now(timezone.utc)
    outbox = Outbox(conn, clock=now_fn)
    sender = CareSender(outbox, _forbidden_api_http, "", QuotaConfig(), dry_run=True, clock=now_fn)
    pipeline = CarePipeline(outbox, sender, quiet_hours=4, clock=now_fn)
    pipeline.init_schema()
    return conn, outbox, pipeline


def notify_coo_escalation(*, customer_id: str, display_name: str, round_id: str, reason: str, coo_box: str = DEFAULT_COO_BOX) -> bool:
    """Deliver escalation letter from `role=care` directly to COO SomPong's mailbox."""
    try:
        from tools import send_to_agy

        msg = (
            f"[น้องมูน Care Escalation · {display_name} ({customer_id}) · round {round_id}]\n"
            f"{reason.strip()}"
        )
        res = send_to_agy.send(coo_box, msg, from_box="care-mooniex")
        return bool(res.get("ok"))
    except Exception:  # noqa: BLE001
        return False


def notify_coo_alert(message: str, *, coo_box: str = DEFAULT_COO_BOX) -> None:
    try:
        from tools import send_to_agy

        send_to_agy.send(coo_box, f"[CARE WINBOX SENDER ALERT] {message}", from_box="care-mooniex")
    except Exception:  # noqa: BLE001
        pass


def cmd_gate(args: argparse.Namespace) -> int:
    conn, _outbox, pipeline = open_runtime(Path(args.db))
    try:
        gate = CareGate(pipeline, args.round_id, args.customer_id)
        if args.subcmd == "history":
            res = gate.call("history")
        elif args.subcmd == "media":
            res = gate.call("media", event_id=args.event_id)
        elif args.subcmd == "skip":
            res = gate.call("skip")
        elif args.subcmd == "reply":
            res = gate.call("reply", bubbles=args.text)
        elif args.subcmd == "escalate":
            kw: dict[str, Any] = {"reason": args.reason}
            if args.text:
                kw["bubbles"] = args.text
            res = gate.call("escalate", **kw)
            row = conn.execute(
                "SELECT display_name FROM care_queue WHERE round_id=? AND customer_id=? LIMIT 1",
                (args.round_id, args.customer_id),
            ).fetchone()
            dname = row[0] if row else args.customer_id
            res["coo_notified"] = notify_coo_escalation(
                customer_id=args.customer_id,
                display_name=dname,
                round_id=args.round_id,
                reason=args.reason,
                coo_box=args.coo_box,
            )
        else:
            raise ValueError(f"unknown gate subcmd {args.subcmd}")
        print(json.dumps({"ok": True, **res}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    finally:
        conn.close()


def cmd_enqueue_operator(args: argparse.Namespace) -> int:
    """Trusted COO/CTO operator enqueue (e.g. CEO-approved payout amount + slip image)."""
    from tools.care_inbox import validate_reply_bubbles

    ok, errs = validate_reply_bubbles(args.text or [], ceo_approved_amount=args.ceo_approved_amount)
    if not ok and not args.slip_image:
        print(json.dumps({"ok": False, "errors": errs}, ensure_ascii=False), file=sys.stderr)
        return 2
    if args.text and not ok:
        print(json.dumps({"ok": False, "errors": errs}, ensure_ascii=False), file=sys.stderr)
        return 2

    payload: list[dict[str, str]] = []
    if args.slip_image:
        p = Path(args.slip_image)
        if not p.is_file():
            print(json.dumps({"ok": False, "error": f"slip_image_not_found:{p}"}), file=sys.stderr)
            return 2
        payload.append({"type": "image", "file_path": str(p.resolve())})
    for t in args.text or []:
        if t.strip():
            payload.append({"type": "text", "text": t.strip()})
    if not payload:
        print(json.dumps({"ok": False, "error": "empty_payload"}), file=sys.stderr)
        return 2

    conn, outbox, _ = open_runtime(Path(args.db))
    try:
        idem = args.idempotency_key or make_idempotency_key(
            DEFAULT_BASIC_ID,
            args.customer_id,
            args.display_name,
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        )
        rid, created = outbox.enqueue(
            idempotency_key=idem,
            recipient_id=args.customer_id,
            recipient_display_name=args.display_name,
            message_kind="care_reply",
            payload=payload,
            reply_token=None,
        )
        print(json.dumps({"ok": True, "outbox_id": rid, "created": created, "items": len(payload)}, ensure_ascii=False, indent=2))
        return 0
    finally:
        conn.close()


def drain_outbox_winbox(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    live: bool = False,
    local_cdp_port: int = 19285,
    winbox_cdp_port: int = 9285,
    coo_box: str = DEFAULT_COO_BOX,
) -> dict[str, Any]:
    """Drain queued/deferred `care_outbox` rows strictly through Winbox OA Manager (0 LINE API quota)."""
    conn, outbox, _ = open_runtime(db_path)
    try:
        pending_ids = outbox.pending()
        enabled_flag = outbox.get_flag(SENDER_ENABLED_FLAG)
        if not pending_ids:
            return {"ok": True, "pending_count": 0, "outcomes": {}, "sender_enabled": enabled_flag != "false"}

        if enabled_flag == "false":
            return {
                "ok": False,
                "pending_count": len(pending_ids),
                "error": f"kill_switch_active:{outbox.get_flag(KILL_REASON_FLAG)}",
                "outcomes": {},
            }

        cfg = BrowserSenderConfig.from_dict(load_care_config())
        outcomes: dict[int, str] = {}
        with WinboxPlaywrightDriver(
            local_cdp_port=local_cdp_port,
            winbox_cdp_port=winbox_cdp_port,
            channel_basic_id=cfg.channel_basic_id,
            channel_display_name=cfg.channel_display_name,
            channel_account_name=cfg.channel_name,
        ) as driver:
            bs = BrowserSender(
                outbox,
                driver,
                cfg=cfg,
                alert_coo=lambda m: notify_coo_alert(m, coo_box=coo_box),
                http=None,
                token=None,
                dry_run=not live,
                winbox_only=True,
            )
            for rid in pending_ids:
                out = bs.process(rid)
                outcomes[rid] = out
                if out.startswith("kill_switch_"):
                    break

        return {
            "ok": all(v in ("sent_browser", "would_send_browser") for v in outcomes.values()),
            "live": live,
            "pending_count": len(pending_ids),
            "outcomes": outcomes,
            "kill_reason": outbox.get_flag(KILL_REASON_FLAG),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}
    finally:
        conn.close()


def cmd_drain(args: argparse.Namespace) -> int:
    res = drain_outbox_winbox(
        db_path=Path(args.db),
        live=args.live,
        local_cdp_port=args.cdp_port,
        coo_box=args.coo_box,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


def cmd_status(args: argparse.Namespace) -> int:
    conn, outbox, _ = open_runtime(Path(args.db))
    try:
        counts = dict(conn.execute("SELECT state, count(*) FROM care_outbox GROUP BY state").fetchall())
        esc_pending = conn.execute("SELECT count(*) FROM care_escalations WHERE state='pending'").fetchone()[0]
        info = {
            "db": str(args.db),
            "sender_enabled": outbox.get_flag(SENDER_ENABLED_FLAG) != "false",
            "kill_reason": outbox.get_flag(KILL_REASON_FLAG),
            "kill_alerted": outbox.get_flag(KILL_ALERT_FLAG),
            "outbox_counts": counts,
            "stuck_sending_ids": outbox.stuck_sending(),
            "pending_ids": outbox.pending(),
            "pending_escalations": esc_pending,
        }
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0
    finally:
        conn.close()


def cmd_reenable(args: argparse.Namespace) -> int:
    conn, outbox, _ = open_runtime(Path(args.db))
    try:
        manual_reenable_sender(outbox, operator_id=args.operator)
        print(json.dumps({"ok": True, "reenabled_by": args.operator}, ensure_ascii=False))
        return 0
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="MoonieX Care Outbox & CareGate CLI (100% Winbox Outbound, 0 LINE Quota)")
    p.add_argument("--db", default=str(DEFAULT_DB_PATH))
    p.add_argument("--coo-box", default=DEFAULT_COO_BOX)
    sub = p.add_subparsers(dest="subcmd", required=True)

    for gcmd in ("history", "skip"):
        sp = sub.add_parser(gcmd)
        sp.add_argument("--round-id", required=True)
        sp.add_argument("--customer-id", required=True)
        sp.set_defaults(func=cmd_gate)

    p_med = sub.add_parser("media")
    p_med.add_argument("--round-id", required=True)
    p_med.add_argument("--customer-id", required=True)
    p_med.add_argument("--event-id", required=True)
    p_med.set_defaults(func=cmd_gate)

    p_rep = sub.add_parser("reply")
    p_rep.add_argument("--round-id", required=True)
    p_rep.add_argument("--customer-id", required=True)
    p_rep.add_argument("--text", action="append", required=True)
    p_rep.set_defaults(func=cmd_gate)

    p_esc = sub.add_parser("escalate")
    p_esc.add_argument("--round-id", required=True)
    p_esc.add_argument("--customer-id", required=True)
    p_esc.add_argument("--reason", required=True)
    p_esc.add_argument("--text", action="append", default=[])
    p_esc.set_defaults(func=cmd_gate)

    p_op = sub.add_parser("enqueue-operator", help="COO/CTO enqueue (e.g. CEO-approved payout + slip image)")
    p_op.add_argument("--customer-id", required=True)
    p_op.add_argument("--display-name", required=True)
    p_op.add_argument("--text", action="append", default=[])
    p_op.add_argument("--slip-image", default=None)
    p_op.add_argument("--ceo-approved-amount", action="store_true")
    p_op.add_argument("--idempotency-key", default=None)
    p_op.set_defaults(func=cmd_enqueue_operator)

    p_dr = sub.add_parser("drain")
    p_dr.add_argument("--live", action="store_true", help="Send via winbox:9285 (default: dry-run check)")
    p_dr.add_argument("--cdp-port", type=int, default=19285)
    p_dr.set_defaults(func=cmd_drain)

    p_st = sub.add_parser("status")
    p_st.set_defaults(func=cmd_status)

    p_re = sub.add_parser("reenable")
    p_re.add_argument("--operator", required=True)
    p_re.set_defaults(func=cmd_reenable)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
