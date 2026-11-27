"""Mocked CDP unit tests for `lib/care/browser_driver.py`.

Strictly offline:
- No network calls to `winbox` or localhost sockets (socket connect is blocked by an autouse fixture).
- No real Playwright browser launched; `connect_over_cdp` is tested with mocked CDP objects.
- Verifies CTO-confirmed composer facts: message `textarea` sits in a SHADOW ROOT where
  `document.querySelectorAll` cannot find it, whereas Playwright `page.locator("textarea")` does,
  and the active chat in the sidebar is `.list-group-item.active`.
- No login, no secrets, no customer PII.
"""
from __future__ import annotations

import html
import socket
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Optional

import pytest

from lib.care.browser_driver import (
    ACTIVE_CHAT_SELECTOR,
    COMPOSER_INPUT_SELECTOR,
    COMPOSER_TEXTAREA_LOCATOR,
    DEFAULT_CDP_PORT,
    DEFAULT_CDP_URL,
    SEND_BUTTON_SELECTOR,
    CareDriverError,
    CdpBrowserDriver,
    ChannelCheckMismatchError,
    KillSwitchError,
    LastBubbleMismatchError,
    LoginForbiddenError,
    PreSendStateError,
    RecipientReadbackMismatchError,
    connect_over_cdp,
    validate_cdp_url,
)
from lib.care.browser_sender import (
    KILL_ALERT_FLAG,
    KILL_REASON_FLAG,
    SENDER_ENABLED_FLAG,
    BrowserSender,
)
from lib.care.outbox import Outbox

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "care_dom"
NOW = datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc)
SYNTHETIC_USER_ID = "U_SYNTHETIC_001"
SYNTHETIC_USER_NAME = "SyntheticUser_01"
SYNTHETIC_TEXT = "[SYNTHETIC_CARE_REPLY_01]"


@pytest.fixture(autouse=True)
def forbid_all_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee zero network calls to winbox or any TCP socket during tests."""

    def _blocked_connect(*args, **kwargs):
        pytest.fail(f"Network socket connect forbidden in offline CDP tests: {args!r}")

    monkeypatch.setattr(socket.socket, "connect", _blocked_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked_connect)
    monkeypatch.setattr(socket, "create_connection", _blocked_connect)


@pytest.fixture
def ob() -> Outbox:
    outbox = Outbox(sqlite3.connect(":memory:"), clock=lambda: NOW)
    outbox.init_schema()
    return outbox


def load_fixture_html(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def enqueue_row(
    ob: Outbox,
    *,
    key: str = "k1",
    recipient_id: str = SYNTHETIC_USER_ID,
    recipient_display_name: str = SYNTHETIC_USER_NAME,
    text: str = SYNTHETIC_TEXT,
    channel_basic_id: str = "@587kfqpt",
) -> int:
    rid, _ = ob.enqueue(
        idempotency_key=key,
        recipient_id=recipient_id,
        recipient_display_name=recipient_display_name,
        message_kind="care_reply",
        payload=[{"type": "text", "text": text}],
        channel_basic_id=channel_basic_id,
    )
    return rid


class MockPlaywrightLocator:
    """Mock Playwright `Locator` that pierces shadow roots (unlike `document.querySelectorAll`)."""

    def __init__(
        self,
        page: "MockCdpPage",
        selector: str,
        *,
        count_val: int = 1,
        attrs: Optional[dict[str, str]] = None,
        text: Optional[str] = None,
        disabled: bool = False,
        on_click: Optional[Callable[[], None]] = None,
    ) -> None:
        self._page = page
        self.selector = selector
        self._count_val = count_val
        self._attrs = dict(attrs or {})
        self._text = text
        self._disabled = disabled
        self._on_click = on_click

    @property
    def first(self) -> "MockPlaywrightLocator":
        return self

    def count(self) -> int:
        return self._count_val

    def is_disabled(self) -> bool:
        return self._disabled

    def get_attribute(self, name: str) -> Optional[str]:
        if name == "disabled" and self._disabled:
            return "disabled"
        return self._attrs.get(name)

    def inner_text(self) -> str:
        return self._text or ""

    def text_content(self) -> str:
        return self._text or ""

    def fill(self, value: str) -> None:
        if self._count_val <= 0:
            raise RuntimeError(f"Locator {self.selector!r} matched 0 elements")
        self._page.locator_fills.append((self.selector, value))
        self._page.fills.append((self.selector, value))

    def click(self) -> None:
        if self._count_val <= 0:
            raise RuntimeError(f"Locator {self.selector!r} matched 0 elements")
        self._page.locator_clicks.append(self.selector)
        if self._on_click is not None:
            self._on_click()
        else:
            self._page.click(self.selector)


class MockCdpPage:
    """Mock Playwright CDP Page modeling chat.line.biz without any browser or network.

    Models both light-DOM fixtures and CTO-verified shadow-root composer / `.list-group-item.active`
    behavior:
    - `query_selector_all("textarea")` checks ONLY light DOM (`self._html`), returning `[]` when
      the composer `textarea` is inside a shadow root (`shadow_root_textarea=True` and light-DOM
      `<textarea>` stripped).
    - `locator("textarea")` pierces the shadow root and finds the composer `textarea`.
    - `locator(".list-group-item.active")` returns the active chat list item.
    """

    def __init__(
        self,
        initial_html: str,
        url: str = "https://chat.line.biz/U_OA_SYNTHETIC/chat/U_SYNTHETIC_001",
        *,
        on_send_click: Optional[Callable[["MockCdpPage"], None]] = None,
        post_send_html: Optional[str] = None,
        append_bubbles_on_send: Optional[list[str]] = None,
        render_staged_bubble: bool = True,
        shadow_root_textarea: bool = True,
        active_chat_recipient_id: Optional[str] = SYNTHETIC_USER_ID,
        active_chat_recipient_name: Optional[str] = SYNTHETIC_USER_NAME,
        active_chat_count: int = 1,
    ) -> None:
        self._html = initial_html
        self.url = url
        self._on_send_click = on_send_click
        self._post_send_html = post_send_html
        self._append_bubbles_on_send = append_bubbles_on_send
        self._render_staged_bubble = render_staged_bubble
        self.shadow_root_textarea = shadow_root_textarea
        self.active_chat_recipient_id = active_chat_recipient_id
        self.active_chat_recipient_name = active_chat_recipient_name
        self.active_chat_count = active_chat_count

        self.fills: list[tuple[str, str]] = []
        self.locator_fills: list[tuple[str, str]] = []
        self.clicks: list[str] = []
        self.locator_clicks: list[str] = []
        self.locator_queries: list[str] = []
        self.query_selector_all_calls: list[str] = []
        self.send_clicks: int = 0
        self.closed: bool = False

    def content(self) -> str:
        return self._html

    def query_selector_all(self, selector: str) -> list[Any]:
        """Simulates `document.querySelectorAll`: cannot pierce shadow roots."""
        self.query_selector_all_calls.append(selector)
        if "textarea" in selector:
            # Only finds light-DOM <textarea>; returns [] when textarea is only in shadow root!
            if "<textarea" in self._html:
                return ["<light-dom-textarea>"]
            return []
        return []

    def locator(self, selector: str) -> MockPlaywrightLocator:
        """Simulates Playwright `page.locator(...)`, which pierces open shadow roots."""
        self.locator_queries.append(selector)
        if selector == COMPOSER_TEXTAREA_LOCATOR or "textarea" in selector:
            has_ta = self.shadow_root_textarea and (
                'data-page-state="captcha"' not in self._html
                and 'data-page-state="warning"' not in self._html
                and 'data-page-state="logout"' not in self._html
            )
            return MockPlaywrightLocator(
                self,
                selector,
                count_val=1 if has_ta else 0,
            )

        if selector == ACTIVE_CHAT_SELECTOR:
            attrs: dict[str, str] = {}
            if self.active_chat_recipient_id:
                attrs["data-recipient-id"] = self.active_chat_recipient_id
            if self.active_chat_recipient_name:
                attrs["data-recipient-display-name"] = self.active_chat_recipient_name
            return MockPlaywrightLocator(
                self,
                selector,
                count_val=self.active_chat_count,
                attrs=attrs,
                text=self.active_chat_recipient_name,
            )

        if ".list-group-item" in selector:
            def _activate_chat() -> None:
                self.clicks.append(selector)

            return MockPlaywrightLocator(
                self,
                selector,
                count_val=1,
                on_click=_activate_chat,
            )

        return MockPlaywrightLocator(self, selector, count_val=1)

    def fill(self, selector: str, value: str) -> None:
        self.fills.append((selector, value))

    def click(self, selector: str) -> None:
        self.clicks.append(selector)
        if selector == SEND_BUTTON_SELECTOR or "data-send-button" in selector:
            if self._on_send_click is not None:
                self._on_send_click(self)
            self.send_clicks += 1
            if self._post_send_html is not None:
                self._html = self._post_send_html
                return
            bubbles_to_add: list[str] = []
            if self._append_bubbles_on_send is not None:
                bubbles_to_add.extend(self._append_bubbles_on_send)
            elif self._render_staged_bubble and self.fills:
                bubbles_to_add.append(self.fills[-1][1])
            for b_text in bubbles_to_add:
                self.append_outbound_bubble(b_text)

    def append_outbound_bubble(self, text: str) -> None:
        escaped = html.escape(text)
        bubble_html = (
            f'<div class="chat-bubble-outbound" data-outbound-bubble="true">{escaped}</div>'
        )
        marker = "</div><!--chat-transcript-end-->"
        if marker in self._html:
            self._html = self._html.replace(marker, f"{bubble_html}{marker}")
        elif "</body>" in self._html:
            self._html = self._html.replace("</body>", f"{bubble_html}</body>")
        else:
            self._html += bubble_html

    def close(self) -> None:
        self.closed = True


def make_shadow_only_chat_html() -> str:
    """Build a realistic `chat.line.biz` light-DOM snapshot where:
    - The active chat in the sidebar is `.list-group-item.active`.
    - The composer `<textarea>` is inside a shadow root and therefore NOT present in
      `document.documentElement.outerHTML` or reachable by `document.querySelectorAll('textarea')`.
    """
    base = load_fixture_html("normal_chat.html")
    # Remove light-DOM <textarea ...></textarea> so only shadow-root locator("textarea") can find it
    without_light_textarea = base.replace(
        '<textarea class="chat-composer-input" data-composer-input="true" placeholder="Enter message"></textarea>',
        '<chat-composer-host data-shadow-host="true"></chat-composer-host>',
    )
    active_list_html = (
        '<aside class="chat-sidebar">'
        f'<div class="list-group-item active" data-recipient-id="{SYNTHETIC_USER_ID}" '
        f'data-recipient-display-name="{SYNTHETIC_USER_NAME}">{SYNTHETIC_USER_NAME}</div>'
        '<div class="list-group-item" data-recipient-id="U_OTHER_002" '
        'data-recipient-display-name="OtherSyntheticUser">OtherSyntheticUser</div>'
        "</aside>"
    )
    return without_light_textarea.replace('<main class="oa-chat-main">', f'{active_list_html}<main class="oa-chat-main">')


def make_mock_playwright(pages: list[MockCdpPage]):
    """Build a fake `sync_playwright` tree recording `connect_over_cdp` calls."""
    recorded_urls: list[tuple[str, Optional[int]]] = []
    stopped: list[bool] = []
    context = SimpleNamespace(pages=pages)
    browser = SimpleNamespace(contexts=[context])

    def _connect_over_cdp(url: str, timeout: Optional[int] = None):
        recorded_urls.append((url, timeout))
        return browser

    pw = SimpleNamespace(
        chromium=SimpleNamespace(connect_over_cdp=_connect_over_cdp),
        stop=lambda: stopped.append(True),
    )
    return pw, recorded_urls, stopped


def test_default_cdp_url_is_local_tunnel_19285_and_rejects_winbox_network(monkeypatch):
    assert DEFAULT_CDP_PORT == 19285
    assert DEFAULT_CDP_URL == "http://127.0.0.1:19285"
    assert validate_cdp_url(DEFAULT_CDP_URL) == "http://127.0.0.1:19285"
    assert validate_cdp_url("http://localhost:19285") == "http://localhost:19285"

    for forbidden_url in (
        "",
        "http://winbox:9285",
        "http://winbox.tailnet:19285",
        "http://100.64.0.10:9285",
        "http://192.168.1.50:9285",
        "ftp://127.0.0.1:19285",
    ):
        with pytest.raises(CareDriverError):
            validate_cdp_url(forbidden_url)
        with pytest.raises(CareDriverError):
            CdpBrowserDriver(cdp_url=forbidden_url)

    unrelated_tab = MockCdpPage("<html><body>Other</body></html>", url="https://example.com/")
    chat_tab = MockCdpPage(load_fixture_html("normal_chat.html"))
    pw, recorded_urls, stopped = make_mock_playwright([unrelated_tab, chat_tab])

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        SimpleNamespace(sync_playwright=lambda: SimpleNamespace(start=lambda: pw)),
    )

    driver = CdpBrowserDriver()
    snap = driver.get_page()
    driver.close()

    assert recorded_urls == [("http://127.0.0.1:19285", 5000)]
    assert "MoonieX Officials" in snap.html
    assert unrelated_tab.closed is False
    assert chat_tab.closed is False
    assert stopped == [True]


def test_missing_chat_tab_fails_without_touching_unrelated_tabs():
    unrelated_tab = MockCdpPage("<html><body>Unrelated</body></html>", url="https://example.com/")
    pw, _, _ = make_mock_playwright([unrelated_tab])

    with pytest.raises(CareDriverError, match="chat_line_biz_tab_not_found"):
        connect_over_cdp(playwright=pw)
    assert unrelated_tab.clicks == []
    assert unrelated_tab.fills == []
    assert unrelated_tab.closed is False


def test_dry_run_is_default_and_send_is_noop_unless_live_true(ob: Outbox):
    page = MockCdpPage(make_shadow_only_chat_html())
    pw, recorded_urls, _ = make_mock_playwright([page])
    rid = enqueue_row(ob)

    # Default live=False (dry-run default)
    driver = CdpBrowserDriver(playwright=pw)
    assert driver.live is False
    assert driver.dry_run is True

    outcome = driver.send_row(ob, rid)
    assert outcome == "dry_run"
    assert recorded_urls == [("http://127.0.0.1:19285", 5000)]
    assert driver.click_count == 0
    assert driver.noop_send_count == 1
    assert page.send_clicks == 0
    assert page.clicks == []
    assert page.fills == []
    assert page.locator_fills == []

    # Outbox row must remain untouched in `queued` (never marked `sending` or `sent` in dry-run)
    row = ob.get(rid)
    assert row["state"] == "queued"
    assert row["sending_started_at"] is None
    assert row["sent_at"] is None

    # Direct click_send() on default driver is also a no-op
    driver.stage_text("Dry run direct stage")
    snap = driver.click_send()
    assert driver.click_count == 0
    assert driver.noop_send_count == 2
    assert page.send_clicks == 0
    assert page.fills == []
    assert page.locator_fills == []
    assert "Dry run direct stage" not in snap.html


def test_shadow_root_textarea_locator_and_active_chat_list_group_item(ob: Outbox):
    """Verify CTO composer facts:
    1. `document.querySelectorAll('textarea')` cannot find the shadow-root composer textarea.
    2. Playwright `page.locator('textarea')` finds and fills it.
    3. Active chat is `.list-group-item.active` and is verified against the expected recipient.
    """
    shadow_html = make_shadow_only_chat_html()
    assert "<textarea" not in shadow_html

    page = MockCdpPage(shadow_html, shadow_root_textarea=True)
    # Proof that querySelectorAll cannot find the textarea in the light DOM
    assert page.query_selector_all("textarea") == []
    # Proof that Playwright locator("textarea") pierces the shadow root and finds it
    assert page.locator("textarea").count() == 1
    assert page.locator(ACTIVE_CHAT_SELECTOR).count() == 1

    pw, _, _ = make_mock_playwright([page])
    rid = enqueue_row(ob)
    driver = CdpBrowserDriver(playwright=pw, live=True)

    outcome = driver.send_row(ob, rid)
    assert outcome == "sent_browser"
    assert page.locator_fills == [(COMPOSER_TEXTAREA_LOCATOR, SYNTHETIC_TEXT)]
    assert ACTIVE_CHAT_SELECTOR in page.locator_queries
    assert COMPOSER_TEXTAREA_LOCATOR in page.locator_queries
    assert ob.get(rid)["state"] == "sent"


def test_missing_shadow_root_textarea_trips_kill_switch_ui_selector_missing(ob: Outbox):
    """If `page.locator('textarea')` finds 0 shadow-root textareas, fail closed before sending."""
    page = MockCdpPage(make_shadow_only_chat_html(), shadow_root_textarea=False)
    pw, _, _ = make_mock_playwright([page])
    alerts: list[str] = []
    rid = enqueue_row(ob)

    driver = CdpBrowserDriver(playwright=pw, live=True, alert_coo=alerts.append)
    with pytest.raises(KillSwitchError, match="ui_selector_missing"):
        driver.send_row(ob, rid)

    assert driver.halted is True
    assert driver.halt_reason == "ui_selector_missing"
    assert driver.click_count == 0
    assert page.send_clicks == 0
    assert ob.get_flag(SENDER_ENABLED_FLAG) == "false"
    assert ob.get(rid)["state"] == "fallback"
    assert len(alerts) == 1


def test_active_chat_list_group_item_mismatch_stops_before_sending_and_click(ob: Outbox):
    """If `.list-group-item.active` points to a different chat than expected, stop immediately."""
    page = MockCdpPage(
        make_shadow_only_chat_html(),
        active_chat_recipient_id="U_OTHER_ACTIVE_CHAT",
        active_chat_recipient_name="OtherActiveUser",
    )
    pw, _, _ = make_mock_playwright([page])
    alerts: list[str] = []
    rid = enqueue_row(ob)

    driver = CdpBrowserDriver(playwright=pw, live=True, alert_coo=alerts.append)
    with pytest.raises(RecipientReadbackMismatchError):
        driver.send_row(ob, rid)

    assert driver.halted is True
    assert driver.halt_reason == "recipient_readback_mismatch"
    assert driver.click_count == 0
    assert page.send_clicks == 0
    assert page.locator_fills == []
    assert ob.get(rid)["state"] == "failed"
    assert ob.get(rid)["sending_started_at"] is None
    assert len(alerts) == 1


def test_live_send_checks_channel_and_recipient_marks_sending_before_click_and_asserts_last_bubble(
    ob: Outbox,
):
    rid = enqueue_row(ob)
    state_during_click: dict = {}

    def _inspect_outbox_at_click(_page: MockCdpPage) -> None:
        row_now = ob.get(rid)
        state_during_click["state"] = row_now["state"]
        state_during_click["delivery_via"] = row_now["delivery_via"]
        state_during_click["sending_started_at"] = row_now["sending_started_at"]
        state_during_click["sent_at"] = row_now["sent_at"]
        state_during_click["attempt_count"] = row_now["attempt_count"]

    page = MockCdpPage(
        make_shadow_only_chat_html(),
        on_send_click=_inspect_outbox_at_click,
    )
    # Seed an older outbound bubble so we verify the new bubble becomes the LAST bubble
    page.append_outbound_bubble("Earlier outbound message")

    pw, recorded_urls, _ = make_mock_playwright([page])
    driver = CdpBrowserDriver(playwright=pw, live=True)

    outcome = driver.send_row(ob, rid)
    assert outcome == "sent_browser"
    assert recorded_urls == [("http://127.0.0.1:19285", 5000)]

    # Proof that outbox row was marked `sending` BEFORE the send click executed
    assert state_during_click == {
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
    assert page.send_clicks == 1
    assert page.locator_fills == [(COMPOSER_INPUT_SELECTOR, SYNTHETIC_TEXT)]
    assert driver.halted is False


def test_channel_check_header_mismatch_stops_before_sending_and_click(ob: Outbox):
    wrong_header_html = make_shadow_only_chat_html().replace(
        "MoonieX Officials", "Other Brand Official"
    )
    page = MockCdpPage(wrong_header_html)
    pw, _, _ = make_mock_playwright([page])
    alerts: list[str] = []
    rid = enqueue_row(ob)

    driver = CdpBrowserDriver(playwright=pw, live=True, alert_coo=alerts.append)
    with pytest.raises(ChannelCheckMismatchError):
        driver.send_row(ob, rid)

    assert driver.halted is True
    assert driver.halt_reason == "channel_check_mismatch"
    assert driver.click_count == 0
    assert page.send_clicks == 0
    assert page.fills == []

    row = ob.get(rid)
    assert row["state"] == "failed"
    assert row["sending_started_at"] is None
    assert row["sent_at"] is None
    assert row["last_error"] == "channel_check_mismatch"
    assert len(alerts) == 1

    # Subsequent operations on a stopped driver must refuse immediately
    rid2 = enqueue_row(ob, key="k2")
    with pytest.raises(CareDriverError, match="driver_halted:channel_check_mismatch"):
        driver.send_row(ob, rid2)
    assert ob.get(rid2)["state"] == "queued"


@pytest.mark.parametrize(
    "bad_id,bad_name",
    [
        ("U_WRONG_RECIPIENT", SYNTHETIC_USER_NAME),
        (SYNTHETIC_USER_ID, "WrongRecipientDisplayName"),
    ],
)
def test_recipient_readback_mismatch_stops_before_sending_and_click(
    ob: Outbox, bad_id: str, bad_name: str
):
    page = MockCdpPage(make_shadow_only_chat_html())
    pw, _, _ = make_mock_playwright([page])
    alerts: list[str] = []
    rid = enqueue_row(
        ob,
        key=f"rec_{bad_id}_{bad_name}",
        recipient_id=bad_id,
        recipient_display_name=bad_name,
    )

    driver = CdpBrowserDriver(playwright=pw, live=True, alert_coo=alerts.append)
    with pytest.raises(RecipientReadbackMismatchError):
        driver.send_row(ob, rid)

    assert driver.halted is True
    assert driver.halt_reason == "recipient_readback_mismatch"
    assert driver.click_count == 0
    assert page.send_clicks == 0
    assert page.fills == []

    row = ob.get(rid)
    assert row["state"] == "failed"
    assert row["sending_started_at"] is None
    assert row["sent_at"] is None
    assert row["last_error"] == "recipient_readback_mismatch"
    assert len(alerts) == 1


def test_post_send_last_bubble_missing_stops_and_marks_failed(ob: Outbox):
    # Send click occurs, but no outbound bubble is rendered in the DOM
    page = MockCdpPage(
        make_shadow_only_chat_html(),
        render_staged_bubble=False,
    )
    pw, _, _ = make_mock_playwright([page])
    rid = enqueue_row(ob)

    driver = CdpBrowserDriver(playwright=pw, live=True)
    with pytest.raises(LastBubbleMismatchError):
        driver.send_row(ob, rid)

    assert driver.click_count == 1
    assert driver.halted is True
    assert driver.halt_reason == "last_bubble_mismatch"

    row = ob.get(rid)
    assert row["state"] == "failed"
    assert row["sending_started_at"] == NOW.isoformat()
    assert row["sent_at"] is None
    assert row["last_error"] == "last_bubble_mismatch"


def test_post_send_asserts_last_bubble_is_ours_not_merely_any_earlier_bubble(ob: Outbox):
    # Crucial check: an EARLIER bubble in the chat matches SYNTHETIC_TEXT,
    # but after clicking Send the LAST bubble is a different message.
    page = MockCdpPage(
        make_shadow_only_chat_html(),
        append_bubbles_on_send=["[CONCURRENT_OTHER_ADMIN_BUBBLE]"],
    )
    page.append_outbound_bubble(SYNTHETIC_TEXT)
    pw, _, _ = make_mock_playwright([page])
    rid = enqueue_row(ob)

    driver = CdpBrowserDriver(playwright=pw, live=True)
    with pytest.raises(LastBubbleMismatchError):
        driver.send_row(ob, rid)

    assert driver.click_count == 1
    assert driver.halted is True
    assert driver.halt_reason == "last_bubble_mismatch"

    row = ob.get(rid)
    assert row["state"] == "failed"
    assert row["sent_at"] is None
    assert row["last_error"] == "last_bubble_mismatch"

    # Next row in a batch must NOT be attempted after the mismatch stopped the driver
    rid2 = enqueue_row(ob, key="after_last_bubble_mismatch")
    with pytest.raises(CareDriverError, match="driver_halted:last_bubble_mismatch"):
        driver.send_batch(ob, [rid2])
    assert ob.get(rid2)["state"] == "queued"
    assert driver.click_count == 1


@pytest.mark.parametrize(
    "trigger,fixture_name",
    [
        ("captcha", "captcha.html"),
        ("warning", "warning.html"),
        ("logout", "logout.html"),
    ],
)
def test_kill_switch_hazards_stop_driver_forbid_login_and_trip_outbox_flag(
    ob: Outbox, trigger: str, fixture_name: str
):
    page = MockCdpPage(
        load_fixture_html(fixture_name),
        url="https://account.line.biz/login" if trigger == "logout" else "https://chat.line.biz/",
    )
    pw, _, _ = make_mock_playwright([page])
    alerts: list[str] = []
    rid = enqueue_row(ob, key=f"hz_{trigger}")

    driver = CdpBrowserDriver(playwright=pw, live=True, alert_coo=alerts.append)
    with pytest.raises(KillSwitchError, match=trigger):
        driver.send_row(ob, rid)

    assert driver.halted is True
    assert driver.halt_reason == trigger
    assert driver.click_count == 0
    assert driver.login_attempts == 0
    assert ob.get_flag(SENDER_ENABLED_FLAG) == "false"
    assert ob.get_flag(KILL_REASON_FLAG) == trigger
    assert ob.get_flag(KILL_ALERT_FLAG) == trigger
    assert len(alerts) == 1


def test_attempt_login_is_always_forbidden():
    page = MockCdpPage(make_shadow_only_chat_html())
    pw, _, _ = make_mock_playwright([page])
    driver = CdpBrowserDriver(playwright=pw, live=True)

    with pytest.raises(LoginForbiddenError, match="login_forbidden"):
        driver.attempt_login("user", "secret")

    assert driver.login_attempts == 1
    assert driver.halted is True
    assert driver.halt_reason == "login_forbidden"


def test_pre_send_state_error_when_row_already_claimed_stops_before_click(ob: Outbox):
    page = MockCdpPage(make_shadow_only_chat_html())
    pw, _, _ = make_mock_playwright([page])
    rid = enqueue_row(ob)

    driver = CdpBrowserDriver(playwright=pw, live=True, outbox=ob, row_id=rid)
    driver.select_thread(SYNTHETIC_USER_ID)
    driver.stage_text(SYNTHETIC_TEXT)

    # Simulate another worker marking the row failed/dropped before click_send runs
    ob.mark_dropped(rid, "operator_cancelled")

    with pytest.raises(PreSendStateError):
        driver.click_send()

    assert driver.click_count == 0
    assert page.send_clicks == 0
    assert driver.halted is True


def test_integration_with_s2_browser_sender(ob: Outbox):
    rid = enqueue_row(ob, key="s2_integ")
    state_at_click: dict = {}

    def _on_click(_page: MockCdpPage) -> None:
        state_at_click["state"] = ob.get(rid)["state"]

    page = MockCdpPage(make_shadow_only_chat_html(), on_send_click=_on_click)
    pw, _, _ = make_mock_playwright([page])
    driver = CdpBrowserDriver(playwright=pw, live=True, outbox=ob, row_id=rid)
    sender = BrowserSender(ob, driver, clock=lambda: NOW)

    assert sender.process(rid) == "sent_browser"
    assert state_at_click["state"] == "sending"
    assert ob.get(rid)["state"] == "sent"
    assert driver.click_count == 1
    assert page.locator_fills == [(COMPOSER_TEXTAREA_LOCATOR, SYNTHETIC_TEXT)]
