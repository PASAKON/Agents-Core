import random
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib.care.browser_sender import (
    KILL_ALERT_FLAG,
    KILL_REASON_FLAG,
    SENDER_ENABLED_FLAG,
    BrowserSender,
    BrowserSenderConfig,
    FixtureBrowserDriver,
    JitterPacer,
    PacingConfig,
    decide_browser_throttle,
    inspect_oa_dom,
    load_care_config,
    manual_reenable_sender,
)
from lib.care.outbox import Outbox
from lib.care.quota import QuotaConfig
from lib.care.sender import CareSender

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "care_dom"
TOKEN = "DUMMY-TOKEN-NOT-REAL"
NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
SYNTHETIC_USER_ID = "U_SYNTHETIC_001"
SYNTHETIC_USER_NAME = "SyntheticUser_01"
SYNTHETIC_TEXT = "[SYNTHETIC_CARE_REPLY_01]"


class Clock:
    def __init__(self, initial: datetime = NOW):
        self.now = initial

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> datetime:
        self.now = self.now + timedelta(**kwargs)
        return self.now


class FakeHttp:
    def __init__(self, usage: int = 0, reply: int = 200, push: int = 200):
        self.usage = usage
        self.reply = reply
        self.push = push
        self.calls: list[tuple[str, str, dict, dict]] = []

    def __call__(self, method: str, url: str, headers: dict, body: dict):
        self.calls.append((method, url, dict(headers), body))
        if url.endswith("/quota/consumption"):
            return 200, {"totalUsage": self.usage}
        if url.endswith("/reply"):
            return self.reply, {}
        return self.push, {}


@pytest.fixture
def clock():
    return Clock(NOW)


@pytest.fixture
def ob(clock):
    outbox = Outbox(sqlite3.connect(":memory:"), clock=clock)
    outbox.init_schema()
    return outbox


def load_fixture_html(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def enqueue_row(
    ob: Outbox,
    key: str = "k1",
    recipient_id: str = SYNTHETIC_USER_ID,
    recipient_display_name: str = SYNTHETIC_USER_NAME,
    text: str = SYNTHETIC_TEXT,
    kind: str = "care_reply",
    token: str | None = None,
    exp: datetime | None = None,
    channel_basic_id: str = "@587kfqpt",
) -> int:
    rid, _ = ob.enqueue(
        idempotency_key=key,
        recipient_id=recipient_id,
        recipient_display_name=recipient_display_name,
        message_kind=kind,
        payload=[{"type": "text", "text": text}],
        reply_token=token,
        reply_token_expires_at=exp,
        channel_basic_id=channel_basic_id,
    )
    return rid


def test_config_placeholders_remain_null():
    raw_cfg = load_care_config()
    cfg = BrowserSenderConfig.from_dict(raw_cfg)
    assert cfg.channel_basic_id == "@587kfqpt"
    assert cfg.channel_display_name == "MoonieX Officials"
    assert cfg.channel_name == "@mooniex"
    assert cfg.hourly_ceiling is None
    assert cfg.daily_ceiling is None
    assert cfg.cdp_port is None

    dec = decide_browser_throttle(cfg, hourly_used=50, daily_used=200)
    assert dec.allowed is True
    assert dec.reason == "ok_ceilings_unset"


def test_sanitized_dom_fixtures_classification_and_hygiene():
    expected = {
        "normal_chat.html": "normal_chat",
        "captcha.html": "captcha",
        "warning.html": "warning",
        "logout.html": "logout",
    }
    for fname, expected_state in expected.items():
        raw = load_fixture_html(fname)
        insp = inspect_oa_dom(raw)
        assert insp.page_state == expected_state, f"{fname} classified as {insp.page_state}"
        # Zero tokens or real PII in fixture files
        assert TOKEN not in raw
        assert "Bearer " not in raw
        assert not re.search(r"\b0[689]\d{8}\b", raw)  # no Thai mobile numbers
        assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw)

    normal = inspect_oa_dom(load_fixture_html("normal_chat.html"))
    assert normal.channel_basic_id == "@587kfqpt"
    assert normal.channel_display_name == "MoonieX Officials"
    assert normal.channel_account_name == "@mooniex"
    assert normal.recipient_id == SYNTHETIC_USER_ID
    assert normal.recipient_display_name == SYNTHETIC_USER_NAME
    assert normal.has_oa_header and normal.has_chat_header
    assert normal.has_composer_input and normal.has_send_button


def test_normal_chat_channel_check_readback_and_mark_sending_before_click(ob, clock):
    rid = enqueue_row(ob)
    state_at_click: dict = {}

    def capture_before_click():
        row_now = ob.get(rid)
        state_at_click["state"] = row_now["state"]
        state_at_click["delivery_via"] = row_now["delivery_via"]
        state_at_click["sending_started_at"] = row_now["sending_started_at"]
        state_at_click["sent_at"] = row_now["sent_at"]
        state_at_click["attempt_count"] = row_now["attempt_count"]

    driver = FixtureBrowserDriver(
        load_fixture_html("normal_chat.html"),
        on_before_click=capture_before_click,
    )
    pacer = JitterPacer(rng=random.Random(7))
    bs = BrowserSender(ob, driver, pacer=pacer, clock=clock)

    outcome = bs.process(rid)
    assert outcome == "sent_browser"

    # Proof that row was marked `sending` BEFORE click_send executed
    assert state_at_click == {
        "state": "sending",
        "delivery_via": "oa_browser",
        "sending_started_at": NOW.isoformat(),
        "sent_at": None,
        "attempt_count": 1,
    }

    final_row = ob.get(rid)
    assert final_row["state"] == "sent"
    assert final_row["delivery_via"] == "oa_browser"
    assert final_row["sent_at"] == NOW.isoformat()
    assert final_row["last_error"] is None
    assert driver.click_count == 1
    assert driver.selected_threads == [SYNTHETIC_USER_ID]
    assert [phase for phase, _ in pacer.history] == ["pre_open", "stage_typing", "cooldown"]


def test_channel_check_mismatch_aborts_before_sending_and_click(ob, clock):
    wrong_oa_html = (
        load_fixture_html("normal_chat.html")
        .replace("@587kfqpt", "@999wrong")
        .replace("MoonieX Officials", "Wrong OA Display")
    )
    driver = FixtureBrowserDriver(wrong_oa_html)
    alerts: list[str] = []
    rid = enqueue_row(ob)
    bs = BrowserSender(ob, driver, alert_coo=alerts.append, clock=clock)

    assert bs.process(rid) == "failed_channel_check"
    assert driver.click_count == 0
    row = ob.get(rid)
    assert row["state"] == "failed"
    assert row["sending_started_at"] is None
    assert row["sent_at"] is None
    assert row["last_error"] == "channel_check_mismatch"
    assert len(alerts) == 1
    assert SYNTHETIC_TEXT not in alerts[0]


def test_recipient_readback_mismatch_aborts_before_sending_and_click(ob, clock):
    driver = FixtureBrowserDriver(load_fixture_html("normal_chat.html"))
    alerts: list[str] = []
    bs = BrowserSender(ob, driver, alert_coo=alerts.append, clock=clock)

    # Mismatched recipient_id
    r_bad_id = enqueue_row(ob, key="bad_id", recipient_id="U_WRONG_999")
    assert bs.process(r_bad_id) == "failed_recipient_readback"
    assert driver.click_count == 0
    assert ob.get(r_bad_id)["state"] == "failed"
    assert ob.get(r_bad_id)["sending_started_at"] is None
    assert ob.get(r_bad_id)["last_error"] == "recipient_readback_mismatch"

    # Mismatched recipient_display_name
    r_bad_name = enqueue_row(ob, key="bad_name", recipient_display_name="WrongDisplayName")
    assert bs.process(r_bad_name) == "failed_recipient_readback"
    assert driver.click_count == 0
    assert ob.get(r_bad_name)["state"] == "failed"
    assert ob.get(r_bad_name)["sending_started_at"] is None
    assert ob.get(r_bad_name)["last_error"] == "recipient_readback_mismatch"


def test_missing_ui_selector_fails_closed_and_trips_kill_switch(ob, clock):
    broken_html = load_fixture_html("normal_chat.html").replace(
        '<button class="chat-send-btn" data-send-button="true" type="button">Send</button>',
        "",
    )
    driver = FixtureBrowserDriver(broken_html)
    alerts: list[str] = []
    rid = enqueue_row(ob)
    bs = BrowserSender(ob, driver, alert_coo=alerts.append, clock=clock)

    assert bs.process(rid) == "kill_switch_ui_selector_missing"
    assert driver.click_count == 0
    assert ob.get_flag(SENDER_ENABLED_FLAG) == "false"
    assert ob.get(rid)["state"] == "fallback"
    assert ob.get(rid)["sent_at"] is None
    assert len(alerts) == 1


@pytest.mark.parametrize(
    "trigger,fixture_name",
    [
        ("captcha", "captcha.html"),
        ("warning", "warning.html"),
        ("logout", "logout.html"),
    ],
)
def test_kill_switch_on_captcha_warning_logout_alerts_once_and_no_auto_reenable(
    ob, clock, trigger, fixture_name
):
    hazard_driver = FixtureBrowserDriver(load_fixture_html(fixture_name))
    alerts: list[str] = []
    r1 = enqueue_row(ob, key=f"k1_{trigger}")
    bs = BrowserSender(ob, hazard_driver, alert_coo=alerts.append, clock=clock)

    assert bs.process(r1) == f"kill_switch_{trigger}"
    assert hazard_driver.click_count == 0
    assert hazard_driver.login_attempts == 0
    assert ob.get_flag(SENDER_ENABLED_FLAG) == "false"
    assert ob.get_flag(KILL_REASON_FLAG) == trigger
    assert ob.get_flag(KILL_ALERT_FLAG) == trigger
    assert len(alerts) == 1
    assert trigger in alerts[0]

    row1 = ob.get(r1)
    assert row1["state"] == "fallback"
    assert row1["sending_started_at"] is None
    assert row1["sent_at"] is None
    assert row1["last_error"] == f"kill_switch_{trigger}"

    # Swap to a healthy normal_chat driver: sender MUST NOT auto re-enable or re-alert COO
    healthy_driver = FixtureBrowserDriver(load_fixture_html("normal_chat.html"))
    bs_after = BrowserSender(ob, healthy_driver, alert_coo=alerts.append, clock=clock)
    r2 = enqueue_row(ob, key=f"k2_{trigger}")

    assert bs_after.process(r2) == "fallback_reply_token"
    assert healthy_driver.events == []
    assert healthy_driver.click_count == 0
    assert ob.get_flag(SENDER_ENABLED_FLAG) == "false"
    assert len(alerts) == 1  # COO alerted only once
    assert ob.get(r2)["state"] == "fallback"

    # Manual operator re-enable is required to restore browser sending
    with pytest.raises(ValueError):
        manual_reenable_sender(ob, operator_id="   ")

    manual_reenable_sender(ob, operator_id="coo_sompong")
    assert ob.get_flag(SENDER_ENABLED_FLAG) == "true"

    r3 = enqueue_row(ob, key=f"k3_{trigger}")
    assert bs_after.process(r3) == "sent_browser"
    assert ob.get(r3)["state"] == "sent"


def test_fallback_to_reply_token_path_when_sender_is_off(ob, clock):
    http = FakeHttp()
    alerts: list[str] = []

    # 1. Trip kill switch on logout fixture for a row whose reply token has expired
    logout_driver = FixtureBrowserDriver(load_fixture_html("logout.html"))
    bs_logout = BrowserSender(
        ob, logout_driver, alert_coo=alerts.append, http=http, token=TOKEN, clock=clock
    )
    r_expired = enqueue_row(
        ob, key="expired_tok", token="old_rt", exp=NOW - timedelta(seconds=5)
    )
    assert bs_logout.process(r_expired) == "kill_switch_logout"
    assert ob.get_flag(SENDER_ENABLED_FLAG) == "false"
    assert ob.get(r_expired)["state"] == "fallback"
    assert http.calls == []

    # 2. While sender is off, a row with a valid reply_token falls back immediately to api_reply
    normal_driver = FixtureBrowserDriver(load_fixture_html("normal_chat.html"))
    bs_off = BrowserSender(
        ob, normal_driver, alert_coo=alerts.append, http=http, token=TOKEN, clock=clock
    )
    r_valid = enqueue_row(
        ob, key="valid_tok", token="fresh_rt_1", exp=NOW + timedelta(seconds=30)
    )
    assert bs_off.process(r_valid) == "sent_fallback_reply"
    assert normal_driver.events == []
    assert len(http.calls) == 1
    assert http.calls[0][1].endswith("/reply")
    assert ob.get(r_valid)["state"] == "sent"
    assert ob.get(r_valid)["delivery_via"] == "api_reply"

    # 3. When a fresh webhook reply_token arrives for the earlier `fallback` row,
    # CareSender (and BrowserSender) delivers it via the webhook reply-token path.
    assert ob.attach_reply_token(r_expired, "fresh_rt_2", NOW + timedelta(seconds=30)) is True
    care_sender = CareSender(
        ob,
        http,
        TOKEN,
        QuotaConfig(),
        alert_coo=alerts.append,
        dry_run=False,
        clock=clock,
        browser_sender=bs_off,
    )
    assert care_sender.process(r_expired) == "sent_reply"
    assert len(http.calls) == 2
    assert http.calls[1][1].endswith("/reply")
    assert ob.get(r_expired)["state"] == "sent"
    assert ob.get(r_expired)["delivery_via"] == "api_reply"


def test_throttle_per_hour_and_per_day_ceilings(ob, clock):
    cfg = BrowserSenderConfig(hourly_ceiling=2, daily_ceiling=3)
    driver = FixtureBrowserDriver(load_fixture_html("normal_chat.html"))
    bs = BrowserSender(ob, driver, cfg=cfg, clock=clock)

    r1 = enqueue_row(ob, key="t1")
    r2 = enqueue_row(ob, key="t2")
    r3 = enqueue_row(ob, key="t3")
    r4 = enqueue_row(ob, key="t4")

    assert bs.process(r1) == "sent_browser"
    clock.advance(minutes=10)
    assert bs.process(r2) == "sent_browser"

    # 3rd message within the same hour hits hourly_ceiling=2 -> deferred
    clock.advance(minutes=10)
    assert bs.process(r3) == "deferred_hourly_ceiling"
    assert ob.get(r3)["state"] == "deferred"
    assert ob.get(r3)["last_error"] == "throttle_hourly_ceiling"
    assert driver.click_count == 2

    # Advance past 1-hour rolling window (now at t=+75m): hourly usage drops to 0, r3 succeeds
    clock.advance(minutes=55)
    assert bs.process(r3) == "sent_browser"
    assert ob.get(r3)["state"] == "sent"
    assert driver.click_count == 3

    # 4th message within 24 hours hits daily_ceiling=3 -> deferred
    clock.advance(minutes=5)
    assert bs.process(r4) == "deferred_daily_ceiling"
    assert ob.get(r4)["state"] == "deferred"
    assert ob.get(r4)["last_error"] == "throttle_daily_ceiling"
    assert driver.click_count == 3

    # Advance past 24-hour rolling window: daily usage drops to 0, r4 succeeds
    clock.advance(hours=24)
    assert bs.process(r4) == "sent_browser"
    assert ob.get(r4)["state"] == "sent"
    assert driver.click_count == 4


def test_human_like_jittered_pacing_non_uniform_and_proportional():
    cfg = PacingConfig(
        pre_open_seconds=(0.25, 0.75),
        per_char_seconds=(0.02, 0.04),
        min_stage_seconds=(0.30, 0.60),
        cooldown_seconds=(1.20, 2.80),
    )
    slept: list[float] = []
    pacer = JitterPacer(cfg=cfg, rng=random.Random(12345), sleep=slept.append)

    pre_delays = [pacer.pause_pre_open() for _ in range(5)]
    short_stage = pacer.pause_stage_typing(char_count=5)
    long_stage = pacer.pause_stage_typing(char_count=150)
    cooldown_delays = [pacer.pause_cooldown() for _ in range(5)]

    assert len(set(pre_delays)) > 1  # non-uniform jitter
    assert all(0.25 <= d <= 0.75 for d in pre_delays)
    assert len(set(cooldown_delays)) > 1  # non-uniform cooldown jitter
    assert all(1.20 <= d <= 2.80 for d in cooldown_delays)
    assert long_stage > short_stage  # proportional to character count
    assert len(slept) == 12


def test_crash_recovery_skips_stuck_sending_and_no_pii_or_token_in_db(ob, clock):
    rid = enqueue_row(ob, key="stuck")
    assert ob.claim_sending(rid, "oa_browser") is True

    driver = FixtureBrowserDriver(load_fixture_html("normal_chat.html"))
    bs = BrowserSender(ob, driver, clock=clock)
    assert bs.process(rid) == "skip_sending"
    assert driver.click_count == 0
    assert driver.events == []

    # Verify token and customer text never appear in last_error or care_state
    r_warn = enqueue_row(ob, key="warn_row", text="[PRIVATE_SYNTHETIC_BUBBLE]")
    warn_driver = FixtureBrowserDriver(load_fixture_html("warning.html"))
    alerts: list[str] = []
    BrowserSender(
        ob, warn_driver, alert_coo=alerts.append, http=FakeHttp(), token=TOKEN, clock=clock
    ).process(r_warn)

    dump = "\n".join(ob.conn.iterdump())
    assert TOKEN not in dump
    assert "[PRIVATE_SYNTHETIC_BUBBLE]" not in (ob.get(r_warn)["last_error"] or "")
    assert all(TOKEN not in a and "[PRIVATE_SYNTHETIC_BUBBLE]" not in a for a in alerts)
