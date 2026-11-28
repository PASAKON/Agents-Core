"""Tests for MoonieX Care Unified 3-Tier CLI (`tools/care_inbox.py`) and `role=care` tools."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.config import role as get_role  # noqa: E402
from tools import care_inbox  # noqa: E402


def test_care_role_allows_media_tool():
    care_cfg = get_role("care")
    assert care_cfg["allowed_tools"] == ["reply", "skip", "history", "escalate", "media"]


def test_validate_reply_bubbles_enforces_care_playbook_gates():
    ok, errs = care_inbox.validate_reply_bubbles(["สวัสดีครับ", "แอดมินตรวจสอบให้นะครับ"])
    assert ok is True
    assert errs == []

    # > 5 bubbles refused
    ok_many, errs_many = care_inbox.validate_reply_bubbles(["1", "2", "3", "4", "5", "6"])
    assert ok_many is False
    assert any("too_many_bubbles" in e for e in errs_many)

    # Rebate % refused without --ceo-approved-amount
    ok_pct, errs_pct = care_inbox.validate_reply_bubbles(["พอร์ตนี้ได้รีเบต 50% ครับ"])
    assert ok_pct is False
    assert any("forbidden_rebate_pct" in e for e in errs_pct)

    # Money / per-lot amount refused without --ceo-approved-amount
    ok_amt, errs_amt = care_inbox.validate_reply_bubbles(["ยอดคืน $42.50 ครับ"])
    assert ok_amt is False
    assert any("forbidden_money_amount" in e for e in errs_amt)

    # Allowed when CEO explicitly approved the amount
    ok_app, errs_app = care_inbox.validate_reply_bubbles(
        ["ยอดคืน $42.50 ครับ"], ceo_approved_amount=True
    )
    assert ok_app is True
    assert errs_app == []


def test_reconcile_records_matches_by_sender_or_preview_and_flags_missing():
    auto_rows = [
        {
            "id": 10,
            "sender_id": "U11111111111111111111111111111111",
            "message_type": "text",
            "payload": {"text": "ส่งเลขพอร์ต 362371027 มาให้เช็ครีเบตครับ"},
        }
    ]
    oa_threads = [
        {
            "name": "Customer A",
            "sender_id": "U11111111111111111111111111111111",
            "time": "12:10",
            "unread": 0,
            "preview": "ข้อความล่าสุดต่างกันแต่ sender ตรง",
        },
        {
            "name": "Customer B",
            "time": "13:05",
            "unread": 1,
            "preview": "ส่งรูปประวัติเทรดมาแล้วค่ะ",
        },
    ]
    rec = care_inbox.reconcile_records(auto_rows, oa_threads)
    assert rec["matched_count"] == 1
    assert rec["missing_in_api_count"] == 1
    assert rec["missing_in_api"][0]["name"] == "Customer B"


def test_list_and_read_cascade_fall_back_to_db_when_oa_signed_out(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SUPABASE_URL=https://fixture.supabase.co\n"
        "SUPABASE_SERVICE_KEY=fixture-service-key-not-real\n"
        "# malformed env line without valid LINE_CHANNEL_ACCESS_TOKEN -> must read claudeflow_webhook_accounts\n"
        "LINE_CHANNEL_ACCESS_TOKEN=broken token with spaces\n",
        encoding="utf-8",
    )

    sid_a = "Uaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    sid_b = "Ubbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

    def fake_http_json(url: str, headers: dict[str, str], timeout: int = 10):
        if "/rest/v1/claudeflow_webhook_accounts" in url:
            return [
                {
                    "platform": "line",
                    "account_slug": "mooniex",
                    "tenant_slug": "mooniex",
                    "credentials": {"channel_access_token": "fixture-webhook-account-token-not-real"},
                }
            ]
        if "/rest/v1/claudeflow_accounts" in url:
            return []
        if "/rest/v1/claudeflow_conversations" in url:
            if f"sender_id=eq.{sid_a}" in url:
                return [
                    {
                        "id": 2,
                        "sender_id": sid_a,
                        "role": "user",
                        "message": "[รูปภาพ:imgref_100_abcd] ส่ง QR ค่ะ",
                        "created_at": "2026-11-28T06:10:00Z",
                    },
                    {
                        "id": 1,
                        "sender_id": sid_a,
                        "role": "assistant",
                        "message": "ส่ง QR ได้เลยครับ",
                        "created_at": "2026-11-28T06:00:00Z",
                    },
                ]
            return [
                {
                    "id": 2,
                    "sender_id": sid_a,
                    "role": "user",
                    "message": "[รูปภาพ:imgref_100_abcd] ส่ง QR ค่ะ",
                    "created_at": "2026-11-28T06:10:00Z",
                },
                {
                    "id": 3,
                    "sender_id": sid_b,
                    "role": "user",
                    "message": "เช็คพอร์ตให้หน่อยครับ",
                    "created_at": "2026-11-28T05:55:00Z",
                },
            ]
        if "/rest/v1/claudeflow_contacts" in url:
            return [{"sender_id": sid_a, "display_name": "Synthetic Trader A", "username": None}]
        if f"api.line.me/v2/bot/profile/{sid_b}" in url:
            assert headers["Authorization"] == "Bearer fixture-webhook-account-token-not-real"
            return {"displayName": "Synthetic Trader B"}
        raise AssertionError(f"unexpected URL: {url}")

    def fake_http_bytes(url: str, headers: dict[str, str], timeout: int = 20):
        if "api-data.line.me/v2/bot/message/9988776655/content" in url:
            assert headers["Authorization"] == "Bearer fixture-webhook-account-token-not-real"
            return b"\x89PNG\r\n\x1a\npngbytes", "image/png"
        if "/storage/v1/object/claudeflow_user_images/imgref_100_abcd.jpg" in url:
            return b"\xff\xd8\xffjpegbytes", "image/jpeg"
        raise AssertionError(f"unexpected media URL: {url}")

    # 1. Cascade list: auto fails -> oa signed out -> db fallback succeeds
    list_res = care_inbox.run_list_cascade(
        mode="both",
        limit=10,
        auto_fn=lambda **kw: {"ok": False, "error": "care_queue_table_not_created", "rows": []},
        oa_fn=lambda **kw: {"ok": False, "error": "oa_not_signed_in_or_wrong_channel", "threads": []},
        db_fn=lambda **kw: care_inbox.fetch_db_threads_local(
            limit=kw["limit"], env_path=env_file, http_json=fake_http_json
        ),
    )
    assert list_res["active_path"] == "db_fallback"
    threads = list_res["db"]["threads"]
    assert [t["name"] for t in threads] == ["Synthetic Trader A", "Synthetic Trader B"]
    assert threads[0]["imgref_count"] == 1

    # 2. Cascade read + media download: OA signed out -> DB + LINE Content API + Storage succeeds
    fake_logs = [
        f'[req] POST /line/@mooniex ct=application/json body={json.dumps({"events": [{"type": "message", "source": {"userId": sid_a}, "message": {"type": "image", "id": "9988776655"}}]})}'
    ]
    out_media = tmp_path / "media_out"
    read_res = care_inbox.run_read_cascade(
        "Synthetic Trader A",
        mode="oa",
        download_media=True,
        out_dir=str(out_media),
        oa_read_fn=lambda *a, **kw: {"ok": False, "error": "oa_not_signed_in_or_wrong_channel"},
        db_read_fn=lambda chat, **kw: care_inbox.read_db_chat_local(
            chat,
            env_path=env_file,
            http_json=fake_http_json,
            http_bytes=fake_http_bytes,
            webhook_log_lines=fake_logs,
            **kw,
        ),
    )
    assert read_res["ok"] is True
    assert read_res["oa_fallback_reason"] == "oa_not_signed_in_or_wrong_channel"
    assert read_res["sender_id"] == sid_a
    assert len(read_res["media_files"]) == 2
    assert (out_media / "line-9988776655.png").read_bytes().startswith(b"\x89PNG")
    assert (out_media / "imgref_100_abcd.jpg").read_bytes().startswith(b"\xff\xd8\xff")
