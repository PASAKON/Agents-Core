"""Tests for 100% Winbox Outbound (`winbox_only`), `tools/care_outbox.py`, and `tools/care_runner.py`."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.care.browser_sender import (  # noqa: E402
    BrowserSender,
    FixtureBrowserDriver,
    JitterPacer,
    SENDER_ENABLED_FLAG,
)
from lib.care.outbox import Outbox  # noqa: E402
from tools import care_inbox, care_outbox, care_runner  # noqa: E402

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "care_dom"
NOW = datetime(2026, 11, 28, 8, 0, tzinfo=timezone.utc)


def test_winbox_only_never_uses_line_api_and_defers_on_logout():
    ob = Outbox(sqlite3.connect(":memory:"), clock=lambda: NOW)
    ob.init_schema()

    # Even with a valid reply_token attached, winbox_only=True must NEVER call HTTP!
    rid, _ = ob.enqueue(
        idempotency_key="wb-only-1",
        recipient_id="U_SYNTHETIC_001",
        recipient_display_name="SyntheticUser_01",
        message_kind="care_reply",
        payload=[{"type": "text", "text": "ข้อความทดสอบ 0 โควต้า"}],
        reply_token="VALID-REPLY-TOKEN-MUST-NOT-BE-USED",
        reply_token_expires_at=NOW + timedelta(minutes=5),
    )

    api_calls = []

    def forbidden_http(method, url, headers, body):
        api_calls.append((method, url))
        return 200, {}

    logout_driver = FixtureBrowserDriver((FIXTURE_DIR / "logout.html").read_text(encoding="utf-8"))
    bs_logout = BrowserSender(
        ob,
        logout_driver,
        http=forbidden_http,
        token="DUMMY-TOKEN",
        clock=lambda: NOW,
        winbox_only=True,
    )
    out = bs_logout.process(rid)
    assert out == "kill_switch_logout"
    assert api_calls == []
    assert ob.get_flag(SENDER_ENABLED_FLAG) == "false"
    # Row stays in `deferred` (awaiting winbox relogin), NOT `fallback` (api_reply)!
    assert ob.get(rid)["state"] == "deferred"

    # While disabled, subsequent rows also defer cleanly with 0 API calls
    rid2, _ = ob.enqueue(
        idempotency_key="wb-only-2",
        recipient_id="U_SYNTHETIC_001",
        recipient_display_name="SyntheticUser_01",
        message_kind="care_reply",
        payload=[{"type": "text", "text": "รอล็อกอินใหม่"}],
        reply_token="VALID-REPLY-TOKEN-2",
        reply_token_expires_at=NOW + timedelta(minutes=5),
    )
    assert bs_logout.process(rid2) == "defer_winbox_only"
    assert api_calls == []
    assert ob.get(rid2)["state"] == "deferred"


def test_multi_item_text_and_slip_payload_via_send_items(tmp_path):
    ob = Outbox(sqlite3.connect(":memory:"), clock=lambda: NOW)
    ob.init_schema()
    slip = tmp_path / "slip.png"
    slip.write_bytes(b"\x89PNG\r\n\x1a\n")

    rid, _ = ob.enqueue(
        idempotency_key="wb-slip-1",
        recipient_id="U_SYNTHETIC_001",
        recipient_display_name="SyntheticUser_01",
        message_kind="care_reply",
        payload=[
            {"type": "image", "file_path": str(slip)},
            {"type": "text", "text": "โอนยอดคืนเรียบร้อยครับ"},
            {"type": "text", "text": "ต้องขออภัยที่ดำเนินการล่าช้าด้วยนะครับ"},
        ],
    )

    normal_html = (FIXTURE_DIR / "normal_chat.html").read_text(encoding="utf-8")

    class FakeMultiDriver(FixtureBrowserDriver):
        def __init__(self):
            super().__init__(normal_html)
            self.sent_items = []

        def send_items(self, items, pacer):
            assert ob.get(rid)["state"] == "sending"
            assert ob.get(rid)["delivery_via"] == "oa_browser"
            self.sent_items = list(items)
            return True, self.get_page(), "ok"

    drv = FakeMultiDriver()
    bs = BrowserSender(ob, drv, pacer=JitterPacer(), clock=lambda: NOW, winbox_only=True)
    assert bs.process(rid) == "sent_browser"
    assert ob.get(rid)["state"] == "sent"
    assert len(drv.sent_items) == 3
    assert drv.sent_items[0]["type"] == "image"


def test_care_runner_idle_spends_zero_tokens_and_processes_ready_rows(tmp_path, monkeypatch):
    db_file = tmp_path / "care_runtime.db"
    model_invocations = []

    # 1. Idle: 0 ready rows -> 0 model invocations
    idle_res = care_runner.run_hourly_batch(
        db_path=db_file,
        live_send=False,
        force_outside_hours=True,
        fetch_ready_fn=lambda **_kw: {"ok": True, "rows": []},
        turn_fn=lambda **kw: model_invocations.append(kw) or {"action": "skip", "bubbles": []},
    )
    assert idle_res["status"] == "idle_zero_tokens"
    assert model_invocations == []

    # 2. Ready rows: groups burst, runs turn_fn, validates via CareGate, marks done, queues in care_outbox
    marked_done = []
    monkeypatch.setattr(care_inbox, "_load_claudeflow_supabase_creds", lambda *_a, **_kw: (None, None))
    monkeypatch.setattr(care_inbox, "_load_line_access_token", lambda **_kw: None)

    ready_rows = [
        {
            "id": 101,
            "sender_id": "U_TEST_CARE_RUNNER_01",
            "message_type": "text",
            "status": "ready",
            "payload": {"text": "สวัสดีครับ รีเบตยังไม่เข้าครับ"},
            "created_at": "2026-11-28T09:00:00Z",
        },
        {
            "id": 102,
            "sender_id": "U_TEST_CARE_RUNNER_01",
            "message_type": "text",
            "status": "ready",
            "payload": {"text": "เทรดทองเมื่อวานครับ"},
            "created_at": "2026-11-28T09:00:05Z",
        },
    ]

    proc_res = care_runner.run_hourly_batch(
        db_path=db_file,
        live_send=False,
        force_outside_hours=True,
        fetch_ready_fn=lambda **_kw: {"ok": True, "rows": ready_rows},
        turn_fn=lambda **kw: (
            model_invocations.append(kw)
            or {
                "action": "reply",
                "bubbles": ["สวัสดีครับ รบกวนขอเลขบัญชี MT4/MT5 และวันที่เริ่มไม่เข้าด้วยนะครับ"],
                "_model_used": "gemini-4-argon-high",
            }
        ),
        mark_done_fn=lambda ids: marked_done.extend(ids),
        drain_fn=lambda **_kw: {"ok": True, "live": False, "pending_count": 1},
    )
    assert proc_res["status"] == "processed"
    assert len(model_invocations) == 1  # 2 burst rows grouped into 1 single turn!
    assert marked_done == [101, 102]
    assert proc_res["threads"][0]["action"] == "reply"

    conn, outbox, _ = care_outbox.open_runtime(db_file)
    try:
        pending = outbox.pending()
        assert len(pending) == 1
        row = outbox.get(pending[0])
        assert json.loads(row["payload_json"]) == [
            {"type": "text", "text": "สวัสดีครับ รบกวนขอเลขบัญชี MT4/MT5 และวันที่เริ่มไม่เข้าด้วยนะครับ"}
        ]
    finally:
        conn.close()
