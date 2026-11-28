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



def test_invoke_care_agy_turn_flag_order_settings_and_denied_actions(tmp_path, monkeypatch):
    import subprocess as sp
    import pytest

    media_dir = tmp_path / "round-media" / "cid1"
    media_dir.mkdir(parents=True)
    img_file = media_dir / "qr.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr(care_runner, "ISOLATED_CARE_CWD", tmp_path / "cwd")
    monkeypatch.setattr(care_runner, "_find_agy_bin", lambda: "/usr/bin/false-agy")
    monkeypatch.setattr(care_runner.ph_brain, "select_model_chain", lambda _m: ["gemini-4-argon-high"])

    seen_cmds = []

    def fake_run_ok(cmd, **kwargs):
        seen_cmds.append(cmd)
        out = json.dumps(
            {
                "status": "SUCCESS",
                "structured_output": {
                    "action": "escalate",
                    "bubbles": ["รับทราบข้อมูลบัญชีแล้วครับ"],
                    "reason": "KBANK 741-2-99881-5",
                },
            },
            ensure_ascii=False,
        )
        return sp.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(care_runner.subprocess, "run", fake_run_ok)
    dec = care_runner.invoke_care_agy_turn(
        customer_id="U_SYNTH_QR",
        display_name="SynthQR",
        history_data={},
        events_data=[{"care_queue_id": 1, "type": "image"}],
        media_dir=media_dir,
        media_files=[str(img_file)],
    )
    assert dec["action"] == "escalate"
    assert "KBANK" in dec["reason"]
    cmd = seen_cmds[0]
    # Prompt MUST immediately follow -p at the end of argv
    assert cmd[-2] == "-p"
    assert "SynthQR" in cmd[-1]
    # --settings MUST scope read_file strictly to media_dir and deny command(*)
    settings_idx = cmd.index("--settings")
    settings_obj = json.loads(cmd[settings_idx + 1])
    assert settings_obj["permissions"]["allow"] == [f"read_file({media_dir.resolve()})"]
    assert "command(*)" in settings_obj["permissions"]["deny"]

    # If agy auto-denies read_file, _extract_json_object MUST raise RuntimeError
    def fake_run_denied(cmd, **kwargs):
        out = json.dumps(
            {
                "status": "SUCCESS",
                "denied_actions": [{"action": "read_file"}],
                "structured_output": {"action": "reply", "bubbles": ["ตอบมั่วโดยไม่อ่านรูป"]},
            }
        )
        return sp.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(care_runner.subprocess, "run", fake_run_denied)
    with pytest.raises(RuntimeError, match="agy_permission_denied"):
        care_runner.invoke_care_agy_turn(
            customer_id="U_SYNTH_QR",
            display_name="SynthQR",
            history_data={},
            events_data=[{"care_queue_id": 1, "type": "image"}],
            media_dir=media_dir,
            media_files=[str(img_file)],
        )


def test_winbox_playwright_driver_send_items_streams_buffer_and_clicks_modal(tmp_path):
    from lib.care.browser_sender import WinboxPlaywrightDriver

    slip = tmp_path / "slip_payout.png"
    raw_bytes = b"\x89PNG\r\n\x1a\nSLIPDATA"
    slip.write_bytes(raw_bytes)

    uploaded_payloads = []
    modal_clicks = []

    class FakeLocator:
        def __init__(self, kind, count_val=1):
            self.kind = kind
            self._count = count_val
            self.first = self

        def count(self):
            return self._count

        def set_input_files(self, payload):
            uploaded_payloads.append(payload)

        def click(self, timeout=None):
            modal_clicks.append(self.kind)

        def inner_text(self, timeout=None):
            return "MoonieX Officials"

    class FakePage:
        url = "https://chat.line.biz/U1434/chat/U9999"

        def locator(self, sel):
            if "type='file'" in sel:
                return FakeLocator("file_input")
            if ".modal.d-block" in sel:
                return FakeLocator("modal_confirm")
            return FakeLocator(sel)

        def wait_for_timeout(self, _ms):
            pass

        def evaluate(self, _js):
            return "SynthUser"

    drv = WinboxPlaywrightDriver()
    drv._page = FakePage()
    drv.bind_expected_recipient("U_SYNTH_01", "SynthUser")
    ok, _snap, reason = drv.send_items([{"type": "image", "file_path": str(slip)}], JitterPacer())
    assert ok is True
    assert reason == "ok"
    assert len(uploaded_payloads) == 1
    assert isinstance(uploaded_payloads[0], dict)
    assert uploaded_payloads[0]["name"] == "slip_payout.png"
    assert uploaded_payloads[0]["mimeType"] == "image/png"
    assert uploaded_payloads[0]["buffer"] == raw_bytes
    assert modal_clicks == ["modal_confirm"]
