"""MoonieX Care S2 CDP Browser Driver (`chat.line.biz` over local tunnel `127.0.0.1:19285`).

Implements the S2 `BrowserDriver` protocol defined in `lib/care/browser_sender.py` using
Playwright `connect_over_cdp` against `http://127.0.0.1:19285` (a PH tunnel to `winbox:9285`).

Composer & DOM facts (verified by CTO on live `chat.line.biz`):
- The message composer `textarea` sits inside a SHADOW ROOT: `document.querySelectorAll`
  cannot find it, whereas a Playwright `page.locator("textarea")` pierces the shadow root
  and locates it.
- The active chat thread in the left chat list is `.list-group-item.active`.

Safety invariants:
- DRY-RUN DEFAULT: `live=False` by default; `click_send()` and `send()` are no-ops unless `live=True`.
- Loopback tunnel only: refuses non-loopback CDP URLs (never makes direct network calls to `winbox`).
- No login, no secrets: attaches only to an already-open `chat.line.biz` tab; never touches unrelated
  tabs, never enters credentials, and trips the kill switch on `logout`, `captcha`, `warning`, or
  missing UI selectors.
- Pre-send gates: mandatory channel check (`header name == expected`, `@587kfqpt`, `@mooniex`) and
  recipient readback (`header name == expected`, `recipient_id`, and `.list-group-item.active` agreement)
  before send.
- Pre-click outbox commit: marks the outbox row `sending` (`delivery_via='oa_browser'`) BEFORE clicking Send.
- Post-send verification: re-reads the DOM after clicking Send and asserts the LAST outbound bubble
  (`outbound_bubbles[-1]`) equals our staged message text.
- Halts immediately (`halted = True`) on any mismatch.
"""
from __future__ import annotations

import html as html_lib
from html.parser import HTMLParser
from typing import Any, Callable, Iterable, Optional
from urllib.parse import urlparse

from .browser_sender import (
    DEFAULT_ACCOUNT_NAME,
    DEFAULT_DISPLAY_NAME,
    KILL_ALERT_FLAG,
    KILL_REASON_FLAG,
    KILL_TRIGGERS,
    SENDER_ENABLED_FLAG,
    BrowserSenderConfig,
    DomInspection,
    PageSnapshot,
    _extract_texts_from_payload,
    inspect_oa_dom,
    verify_channel,
)
from .outbox import DEFAULT_BASIC_ID, Outbox

DEFAULT_CDP_HOST = "127.0.0.1"
DEFAULT_CDP_PORT = 19285
DEFAULT_CDP_URL = f"http://{DEFAULT_CDP_HOST}:{DEFAULT_CDP_PORT}"

ALLOWED_CDP_HOSTS = ("127.0.0.1", "localhost", "::1")
CHAT_LINE_BIZ_HOST = "chat.line.biz"
LOGIN_LINE_BIZ_HOST = "account.line.biz"

OA_HEADER_SELECTOR = "[data-oa-header], .oa-account-header"
CHAT_HEADER_SELECTOR = "[data-chat-header], .chat-thread-header"
ACTIVE_CHAT_SELECTOR = ".list-group-item.active"
CHAT_LIST_ITEM_SELECTOR = ".list-group-item"
# Composer textarea sits inside a shadow root: Playwright locator("textarea") pierces it,
# whereas document.querySelectorAll("textarea") cannot find it.
COMPOSER_TEXTAREA_LOCATOR = "textarea"
COMPOSER_INPUT_SELECTOR = "textarea"
SEND_BUTTON_SELECTOR = "[data-send-button], button.chat-send-btn"
OUTBOUND_BUBBLE_SELECTOR = "[data-outbound-bubble], .chat-bubble-outbound"


class CareDriverError(RuntimeError):
    """Base error for MoonieX Care CDP driver failures and safety stops."""


class LoginForbiddenError(CareDriverError):
    """Raised when login is attempted or required (hard rule: never log in)."""


class KillSwitchError(CareDriverError):
    """Raised when captcha, warning, logout, or missing UI selector trips the kill switch."""


class ChannelCheckMismatchError(CareDriverError):
    """Raised when active OA header display name or ID does not match expected."""


class RecipientReadbackMismatchError(CareDriverError):
    """Raised when active chat thread recipient readback does not match expected."""


class PreSendStateError(CareDriverError):
    """Raised when outbox row cannot be marked `sending` before clicking Send."""


class LastBubbleMismatchError(CareDriverError):
    """Raised when post-send DOM readback shows the last outbound bubble is not ours."""


class _ActiveChatHtmlParser(HTMLParser):
    """Extract `.list-group-item.active` recipient metadata from raw HTML when present."""

    def __init__(self) -> None:
        super().__init__()
        self.active_count: int = 0
        self.active_recipient_id: Optional[str] = None
        self.active_recipient_name: Optional[str] = None
        self._in_active_depth: int = 0
        self._active_text_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        ad = {k.lower(): (v or "") for k, v in attrs}
        cls_tokens = set(ad.get("class", "").lower().split())
        if self._in_active_depth > 0:
            self._in_active_depth += 1
            if not self.active_recipient_id:
                rid = ad.get("data-recipient-id") or ad.get("data-thread-id") or ad.get("data-chat-id")
                if rid:
                    self.active_recipient_id = rid.strip()
            if not self.active_recipient_name and ad.get("data-recipient-display-name"):
                self.active_recipient_name = ad["data-recipient-display-name"].strip()
            return

        if "list-group-item" in cls_tokens and "active" in cls_tokens:
            self.active_count += 1
            self._in_active_depth = 1
            self._active_text_chunks = []
            rid = ad.get("data-recipient-id") or ad.get("data-thread-id") or ad.get("data-chat-id")
            if rid:
                self.active_recipient_id = rid.strip()
            if ad.get("data-recipient-display-name"):
                self.active_recipient_name = ad["data-recipient-display-name"].strip()

    def handle_endtag(self, tag: str) -> None:
        if self._in_active_depth > 0:
            self._in_active_depth -= 1
            if self._in_active_depth == 0 and not self.active_recipient_name:
                text = " ".join("".join(self._active_text_chunks).split()).strip()
                if text:
                    self.active_recipient_name = text

    def handle_data(self, data: str) -> None:
        if self._in_active_depth > 0 and data.strip():
            self._active_text_chunks.append(data.strip())


def inspect_active_chat_item(raw_html: str) -> tuple[int, Optional[str], Optional[str]]:
    """Return `(active_count, recipient_id, recipient_display_name)` for `.list-group-item.active`."""
    parser = _ActiveChatHtmlParser()
    parser.feed(raw_html or "")
    parser.close()
    return parser.active_count, parser.active_recipient_id, parser.active_recipient_name


def validate_cdp_url(cdp_url: str) -> str:
    """Validate that the CDP endpoint targets the local loopback tunnel, never remote winbox."""
    raw = (cdp_url or "").strip()
    if not raw:
        raise CareDriverError("empty_cdp_url")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https", "ws", "wss"):
        raise CareDriverError("invalid_cdp_url_scheme")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_CDP_HOSTS:
        raise CareDriverError("cdp_url_must_use_local_tunnel")
    return raw


def _read_page_url(page: Any) -> str:
    url_attr = getattr(page, "url", "")
    if callable(url_attr):
        return str(url_attr() or "")
    return str(url_attr or "")


def _find_chat_page(browser: Any) -> Any:
    """Find an existing chat.line.biz tab without opening or touching unrelated tabs."""
    contexts = getattr(browser, "contexts", None) or ()
    pages: list[Any] = []
    for ctx in contexts:
        pages.extend(getattr(ctx, "pages", None) or ())
    if not pages and hasattr(browser, "pages"):
        pages = list(getattr(browser, "pages") or ())

    for page in pages:
        url = _read_page_url(page).lower()
        if CHAT_LINE_BIZ_HOST in url and LOGIN_LINE_BIZ_HOST not in url:
            return page

    for page in pages:
        url = _read_page_url(page).lower()
        if LOGIN_LINE_BIZ_HOST in url or CHAT_LINE_BIZ_HOST in url:
            return page

    raise CareDriverError("chat_line_biz_tab_not_found")


def connect_over_cdp(
    cdp_url: str = DEFAULT_CDP_URL,
    *,
    playwright: Any = None,
    timeout_ms: int = 5000,
) -> tuple[Any, Any, Any]:
    """Connect to the local CDP tunnel (`http://127.0.0.1:19285`) and locate the `chat.line.biz` tab.

    Returns `(playwright_instance, browser, page)`.
    """
    validated_url = validate_cdp_url(cdp_url)
    pw = playwright
    if pw is None:
        from playwright.sync_api import sync_playwright  # lazy import

        pw = sync_playwright().start()

    connect_fn = pw.chromium.connect_over_cdp
    try:
        browser = connect_fn(validated_url, timeout=timeout_ms)
    except TypeError:
        browser = connect_fn(validated_url)

    page = _find_chat_page(browser)
    return pw, browser, page


def _locator_count(loc: Any) -> int:
    if loc is None:
        return 0
    count_fn = getattr(loc, "count", None)
    if callable(count_fn):
        return int(count_fn())
    return 1


def _locator_first(loc: Any) -> Any:
    first = getattr(loc, "first", None)
    return first if first is not None else loc


def _locator_get_attr(loc: Any, name: str) -> Optional[str]:
    target = _locator_first(loc)
    fn = getattr(target, "get_attribute", None)
    if callable(fn):
        val = fn(name)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _locator_text(loc: Any) -> Optional[str]:
    target = _locator_first(loc)
    for attr_name in ("inner_text", "text_content"):
        fn = getattr(target, attr_name, None)
        if callable(fn):
            val = fn()
            if isinstance(val, str) and val.strip():
                return " ".join(val.split()).strip()
    return None


class CdpBrowserDriver:
    """Playwright CDP driver for `chat.line.biz` implementing `BrowserDriver`.

    DRY-RUN DEFAULT: `live=False` by default; `click_send()` and `send()` are no-ops
    unless `live=True`.

    Uses `page.locator("textarea")` to pierce the composer's shadow root (never
    `document.querySelectorAll`) and verifies the active chat `.list-group-item.active`.
    """

    def __init__(
        self,
        *,
        cdp_url: str = DEFAULT_CDP_URL,
        live: bool = False,
        page: Any = None,
        playwright: Any = None,
        connect_fn: Optional[Callable[..., tuple[Any, Any, Any]]] = None,
        cfg: BrowserSenderConfig = BrowserSenderConfig(),
        expected_channel_name: Optional[str] = None,
        expected_channel_basic_id: Optional[str] = None,
        expected_channel_account_name: Optional[str] = None,
        expected_recipient_id: Optional[str] = None,
        expected_recipient_display_name: Optional[str] = None,
        outbox: Optional[Outbox] = None,
        row_id: Optional[int] = None,
        on_before_click: Optional[Callable[[], None]] = None,
        alert_coo: Callable[[str], None] = lambda _msg: None,
    ) -> None:
        self.cdp_url = validate_cdp_url(cdp_url or DEFAULT_CDP_URL)
        self.live = bool(live)
        self._page = page
        self._playwright = playwright
        self._browser: Any = None
        self._owns_playwright = False
        self._connect_fn = connect_fn or connect_over_cdp

        self.cfg = cfg
        self.expected_channel_name = (
            expected_channel_name
            if expected_channel_name is not None
            else (cfg.channel_display_name or DEFAULT_DISPLAY_NAME)
        )
        self.expected_channel_basic_id = (
            expected_channel_basic_id
            if expected_channel_basic_id is not None
            else (cfg.channel_basic_id or DEFAULT_BASIC_ID)
        )
        self.expected_channel_account_name = (
            expected_channel_account_name
            if expected_channel_account_name is not None
            else (cfg.channel_name or DEFAULT_ACCOUNT_NAME)
        )
        self.expected_recipient_id = expected_recipient_id
        self.expected_recipient_display_name = expected_recipient_display_name

        self.outbox = outbox
        self.row_id = row_id
        self._on_before_click = on_before_click
        self.alert_coo = alert_coo

        self.events: list[str] = []
        self.selected_threads: list[str] = []
        self.staged_texts: list[str] = []
        self.click_count: int = 0
        self.noop_send_count: int = 0
        self.login_attempts: int = 0
        self.halted: bool = False
        self.halt_reason: Optional[str] = None

    @property
    def dry_run(self) -> bool:
        return not self.live

    def _stop(self, reason: str) -> None:
        self.halted = True
        if self.halt_reason is None:
            self.halt_reason = reason
        self.events.append(f"stopped:{reason}")

    def _check_not_halted(self) -> None:
        if self.halted:
            raise CareDriverError(f"driver_halted:{self.halt_reason}")

    def _ensure_page(self) -> Any:
        self._check_not_halted()
        if self._page is not None:
            return self._page
        had_pw = self._playwright is not None
        pw, browser, page = self._connect_fn(
            self.cdp_url,
            playwright=self._playwright,
        )
        self._playwright = pw
        self._browser = browser
        self._page = page
        self._owns_playwright = not had_pw
        return self._page

    def close(self) -> None:
        """Disconnect Playwright without closing the user's existing chat.line.biz tab."""
        if self._owns_playwright and self._playwright is not None:
            stop_fn = getattr(self._playwright, "stop", None)
            if callable(stop_fn):
                stop_fn()
        self._owns_playwright = False

    def attempt_login(self, *_args: Any, **_kwargs: Any) -> None:
        """Hard rule: driver must NEVER sign in or enter credentials."""
        self.login_attempts += 1
        self._stop("login_forbidden")
        raise LoginForbiddenError("login_forbidden")

    def expect_recipient(
        self,
        recipient_id: str,
        recipient_display_name: Optional[str] = None,
    ) -> None:
        """Bind expected recipient identity for pre-send readback verification."""
        self.expected_recipient_id = recipient_id
        if recipient_display_name is not None:
            self.expected_recipient_display_name = recipient_display_name

    def bind_outbox_row(self, outbox: Outbox, row_id: int) -> dict:
        """Bind an outbox row so pre-send checks and pre-click `sending` commit use it."""
        self.outbox = outbox
        self.row_id = row_id
        row = outbox.get(row_id)
        self.expected_recipient_id = row.get("recipient_id") or self.expected_recipient_id
        self.expected_recipient_display_name = (
            row.get("recipient_display_name") or self.expected_recipient_display_name
        )
        if row.get("channel_basic_id"):
            self.expected_channel_basic_id = row["channel_basic_id"]
        return row

    def _trip_kill_switch(self, trigger: str) -> None:
        if self.outbox is not None:
            self.outbox.set_flag(SENDER_ENABLED_FLAG, "false")
            self.outbox.set_flag(KILL_REASON_FLAG, trigger)
            if self.outbox.set_flag_once(KILL_ALERT_FLAG, trigger):
                self.alert_coo(f"care browser sender kill switch tripped: {trigger}")
        else:
            self.alert_coo(f"care browser sender kill switch tripped: {trigger}")

    def _effective_cfg(self) -> BrowserSenderConfig:
        return BrowserSenderConfig(
            channel_basic_id=self.expected_channel_basic_id or DEFAULT_BASIC_ID,
            channel_display_name=self.expected_channel_name or DEFAULT_DISPLAY_NAME,
            channel_name=self.expected_channel_account_name or DEFAULT_ACCOUNT_NAME,
            enabled=self.cfg.enabled,
            cdp_port=self.cfg.cdp_port,
            hourly_ceiling=self.cfg.hourly_ceiling,
            daily_ceiling=self.cfg.daily_ceiling,
            pacing=self.cfg.pacing,
        )

    def _composer_locator(self, page: Any) -> Any:
        """Return Playwright `page.locator('textarea')` which pierces the composer shadow root."""
        locator_fn = getattr(page, "locator", None)
        if callable(locator_fn):
            return locator_fn(COMPOSER_TEXTAREA_LOCATOR)
        return None

    def _has_shadow_composer(self, page: Any) -> Optional[bool]:
        """Check whether the shadow-root composer `textarea` exists via `page.locator('textarea')`."""
        loc = self._composer_locator(page)
        if loc is None:
            return None
        count = _locator_count(loc)
        if count != 1:
            return False
        disabled = _locator_get_attr(loc, "disabled")
        if disabled is not None:
            return False
        is_disabled_fn = getattr(_locator_first(loc), "is_disabled", None)
        if callable(is_disabled_fn) and bool(is_disabled_fn()):
            return False
        return True

    def _read_active_chat_item(self, page: Any, raw_html: str) -> tuple[int, Optional[str], Optional[str]]:
        """Read `.list-group-item.active` via Playwright locator first, falling back to HTML."""
        locator_fn = getattr(page, "locator", None)
        if callable(locator_fn):
            loc = locator_fn(ACTIVE_CHAT_SELECTOR)
            if loc is not None and callable(getattr(loc, "count", None)):
                cnt = _locator_count(loc)
                if cnt > 0:
                    rid = (
                        _locator_get_attr(loc, "data-recipient-id")
                        or _locator_get_attr(loc, "data-thread-id")
                        or _locator_get_attr(loc, "data-chat-id")
                    )
                    rname = (
                        _locator_get_attr(loc, "data-recipient-display-name")
                        or _locator_text(loc)
                    )
                    return cnt, rid, rname
        return inspect_active_chat_item(raw_html)

    def _synthesize_shadow_dom_into_html(self, page: Any, raw_html: str) -> str:
        """Ensure shadow-root `textarea` discovered via `page.locator('textarea')` is reflected in
        `PageSnapshot.html` so `BrowserSender`'s offline `inspect_oa_dom` sees the composer input.
        """
        shadow_ok = self._has_shadow_composer(page)
        if shadow_ok is not True:
            return raw_html
        # If light DOM lacks the shadow-root composer textarea, inject a synthetic marker for inspect_oa_dom
        if "data-composer-input" not in raw_html and "chat-composer-input" not in raw_html:
            synth_tag = (
                '<textarea class="chat-composer-input" data-composer-input="true" '
                'data-shadow-root-composer="true"></textarea>'
            )
            if "</form>" in raw_html:
                return raw_html.replace("</form>", f"{synth_tag}</form>", 1)
            if "</main>" in raw_html:
                return raw_html.replace("</main>", f"{synth_tag}</main>", 1)
            if "</body>" in raw_html:
                return raw_html.replace("</body>", f"{synth_tag}</body>", 1)
            return raw_html + synth_tag
        return raw_html

    def _verify_channel_header(
        self,
        insp: DomInspection,
        row_basic_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        expected_name = (self.expected_channel_name or DEFAULT_DISPLAY_NAME).strip()
        actual_name = (insp.channel_display_name or "").strip()
        if not actual_name or actual_name != expected_name:
            return False, "channel_display_name_mismatch"
        return verify_channel(insp, self._effective_cfg(), row_basic_id)

    def _verify_recipient_header(
        self,
        insp: DomInspection,
        raw_html: str,
        row: Optional[dict] = None,
    ) -> tuple[bool, str]:
        exp_id = (
            (row.get("recipient_id") if row else None)
            or self.expected_recipient_id
            or ""
        ).strip()
        exp_name = (
            (row.get("recipient_display_name") if row else None)
            or self.expected_recipient_display_name
            or ""
        ).strip()
        actual_id = (insp.recipient_id or "").strip()
        actual_name = (insp.recipient_display_name or "").strip()

        if not actual_id:
            return False, "recipient_id_missing"
        if exp_id and actual_id != exp_id:
            return False, "recipient_id_mismatch"
        if not actual_name:
            return False, "recipient_display_name_missing"
        if exp_name and actual_name != exp_name:
            return False, "recipient_display_name_mismatch"

        # Also verify `.list-group-item.active` when present on the page
        page = self._ensure_page()
        active_count, active_id, active_name = self._read_active_chat_item(page, raw_html)
        if active_count > 1:
            return False, "multiple_active_chats"
        if active_count == 1:
            if active_id and exp_id and active_id.strip() != exp_id:
                return False, "active_chat_item_id_mismatch"
            if active_id and actual_id and active_id.strip() != actual_id:
                return False, "active_chat_item_id_mismatch"
            if active_name and exp_name and active_name.strip() != exp_name:
                return False, "active_chat_item_name_mismatch"
            if active_name and actual_name and active_name.strip() != actual_name:
                return False, "active_chat_item_name_mismatch"

        return True, "ok"

    def _assert_pre_send_dom(
        self,
        snap: PageSnapshot,
        *,
        row: Optional[dict] = None,
        fail_outbox: bool = False,
    ) -> DomInspection:
        page = self._ensure_page()
        insp = inspect_oa_dom(snap.html, snap.url)

        # If page.locator("textarea") explicitly reports missing shadow-root composer, trip ui_selector_missing
        shadow_composer = self._has_shadow_composer(page)
        if insp.page_state == "normal_chat" and shadow_composer is False:
            insp = DomInspection(
                page_state="ui_selector_missing",
                url=insp.url,
                channel_basic_id=insp.channel_basic_id,
                channel_display_name=insp.channel_display_name,
                channel_account_name=insp.channel_account_name,
                recipient_id=insp.recipient_id,
                recipient_display_name=insp.recipient_display_name,
                has_oa_header=insp.has_oa_header,
                has_chat_header=insp.has_chat_header,
                has_composer_input=False,
                has_send_button=insp.has_send_button,
                outbound_bubbles=insp.outbound_bubbles,
                hazard_detail="shadow_root_composer_textarea_missing",
            )

        if insp.page_state in KILL_TRIGGERS:
            self._stop(insp.page_state)
            self._trip_kill_switch(insp.page_state)
            if fail_outbox and self.outbox is not None and self.row_id is not None:
                self.outbox.mark_fallback(self.row_id, f"kill_switch_{insp.page_state}")
            raise KillSwitchError(insp.page_state)

        row_basic_id = row.get("channel_basic_id") if row else self.expected_channel_basic_id
        ch_ok, ch_reason = self._verify_channel_header(insp, row_basic_id)
        if not ch_ok:
            self._stop("channel_check_mismatch")
            if fail_outbox and self.outbox is not None and self.row_id is not None:
                self.outbox.mark_failed(self.row_id, "channel_check_mismatch")
            self.alert_coo("care browser sender channel check mismatch")
            raise ChannelCheckMismatchError(ch_reason)

        rec_ok, rec_reason = self._verify_recipient_header(insp, snap.html, row)
        if not rec_ok:
            self._stop("recipient_readback_mismatch")
            if fail_outbox and self.outbox is not None and self.row_id is not None:
                self.outbox.mark_failed(self.row_id, "recipient_readback_mismatch")
            self.alert_coo("care browser sender recipient readback mismatch")
            raise RecipientReadbackMismatchError(rec_reason)

        return insp

    def get_page(self) -> PageSnapshot:
        """Read current HTML and URL from the connected `chat.line.biz` CDP page."""
        page = self._ensure_page()
        self.events.append("get_page")
        raw_html = (
            page.content()
            if callable(getattr(page, "content", None))
            else str(getattr(page, "html", ""))
        )
        raw_html = self._synthesize_shadow_dom_into_html(page, raw_html)
        url = _read_page_url(page) or "https://chat.line.biz/"
        return PageSnapshot(html=raw_html, url=url)

    def select_thread(self, recipient_id: str) -> PageSnapshot:
        """Select the conversation thread for `recipient_id` (`.list-group-item.active`) and return snapshot."""
        self._check_not_halted()
        rid = (recipient_id or "").strip()
        if not rid:
            self._stop("recipient_id_empty")
            raise RecipientReadbackMismatchError("recipient_id_empty")

        page = self._ensure_page()
        self.events.append(f"select_thread:{rid}")
        self.selected_threads.append(rid)
        self.expected_recipient_id = rid

        if self.live:
            thread_selector = (
                f'{CHAT_LIST_ITEM_SELECTOR}[data-recipient-id="{rid}"], '
                f'{CHAT_LIST_ITEM_SELECTOR}[data-thread-id="{rid}"], '
                f'[data-thread-id="{rid}"], [data-recipient-id="{rid}"]'
            )
            if callable(getattr(page, "select_thread", None)):
                page.select_thread(rid)
            elif callable(getattr(page, "locator", None)):
                # Check if `.list-group-item.active` is already on the target recipient
                active_loc = page.locator(ACTIVE_CHAT_SELECTOR)
                active_id = _locator_get_attr(active_loc, "data-recipient-id") or _locator_get_attr(
                    active_loc, "data-thread-id"
                )
                if active_id != rid:
                    item_loc = page.locator(thread_selector)
                    if _locator_count(item_loc) > 0 and callable(
                        getattr(_locator_first(item_loc), "click", None)
                    ):
                        _locator_first(item_loc).click()
                    elif callable(getattr(page, "click", None)):
                        try:
                            page.click(thread_selector)
                        except Exception:
                            pass
            elif callable(getattr(page, "click", None)):
                try:
                    page.click(thread_selector)
                except Exception:
                    pass

        return self.get_page()

    def stage_text(self, text: str) -> PageSnapshot:
        """Stage message text in the shadow-root composer via `page.locator('textarea')`
        (no-op on remote DOM when `live=False`).
        """
        self._check_not_halted()
        if not isinstance(text, str) or not text.strip():
            self._stop("invalid_stage_text")
            raise CareDriverError("invalid_stage_text")

        page = self._ensure_page()
        self.events.append("stage_text")
        self.staged_texts.append(text)

        if self.live:
            # Composer textarea sits inside a shadow root: always prefer Playwright locator("textarea")
            loc = self._composer_locator(page)
            if loc is not None:
                if _locator_count(loc) != 1:
                    self._stop("ui_selector_missing")
                    self._trip_kill_switch("ui_selector_missing")
                    if self.outbox is not None and self.row_id is not None:
                        self.outbox.mark_fallback(self.row_id, "kill_switch_ui_selector_missing")
                    raise KillSwitchError("ui_selector_missing")
                target = _locator_first(loc)
                fill_fn = getattr(target, "fill", None)
                if callable(fill_fn):
                    fill_fn(text)
                elif callable(getattr(page, "fill", None)):
                    page.fill(COMPOSER_TEXTAREA_LOCATOR, text)
            elif callable(getattr(page, "stage_text", None)):
                page.stage_text(text)
            elif callable(getattr(page, "fill", None)):
                page.fill(COMPOSER_TEXTAREA_LOCATOR, text)

        return self.get_page()

    def click_send(self) -> PageSnapshot:
        """Verify channel + recipient, mark `sending` before click, click Send (only if `live=True`),
        and re-read the DOM to assert the last outbound bubble is ours.
        """
        self._check_not_halted()
        row = (
            self.outbox.get(self.row_id)
            if (self.outbox is not None and self.row_id is not None)
            else None
        )

        # 1. Pre-send channel check (header name == expected) and recipient readback.
        pre_snap = self.get_page()
        self._assert_pre_send_dom(pre_snap, row=row, fail_outbox=self.live)

        # 2. DRY-RUN DEFAULT: send is a no-op unless live=True.
        if not self.live:
            self.events.append("click_send:dry_run_noop")
            self.noop_send_count += 1
            return pre_snap

        if not self.staged_texts:
            self._stop("no_staged_text")
            raise CareDriverError("no_staged_text")

        expected_bubble = self.staged_texts[-1].strip()

        # 3. Mark outbox row `sending` (`oa_browser`) BEFORE clicking Send.
        if self.outbox is not None and self.row_id is not None:
            current_row = self.outbox.get(self.row_id)
            if current_row["state"] in ("queued", "deferred"):
                if not self.outbox.claim_sending(self.row_id, "oa_browser"):
                    self._stop("claim_sending_failed")
                    raise PreSendStateError("claim_sending_failed")
            elif not (
                current_row["state"] == "sending"
                and current_row.get("delivery_via") == "oa_browser"
            ):
                self._stop(f"invalid_pre_click_state:{current_row['state']}")
                raise PreSendStateError(f"invalid_pre_click_state:{current_row['state']}")

        if self._on_before_click is not None:
            self._on_before_click()

        # 4. Click Send on the CDP page.
        page = self._ensure_page()
        self.events.append("click_send")
        self.click_count += 1
        if callable(getattr(page, "click_send", None)):
            page.click_send()
        elif callable(getattr(page, "click", None)):
            page.click(SEND_BUTTON_SELECTOR)
        elif callable(getattr(page, "locator", None)):
            send_loc = page.locator(SEND_BUTTON_SELECTOR)
            _locator_first(send_loc).click()
        else:
            self._stop("send_click_unsupported")
            raise CareDriverError("send_click_unsupported")

        # 5. Re-read DOM after send and assert the LAST outbound bubble is ours.
        post_snap = self.get_page()
        post_insp = inspect_oa_dom(post_snap.html, post_snap.url)
        if post_insp.page_state in KILL_TRIGGERS:
            self._stop(post_insp.page_state)
            self._trip_kill_switch(post_insp.page_state)
            if self.outbox is not None and self.row_id is not None:
                self.outbox.mark_failed(
                    self.row_id, f"post_click_kill_switch_{post_insp.page_state}"
                )
            raise KillSwitchError(post_insp.page_state)

        ch_ok, ch_reason = self._verify_channel_header(
            post_insp, row.get("channel_basic_id") if row else self.expected_channel_basic_id
        )
        if not ch_ok:
            self._stop("post_send_channel_mismatch")
            if self.outbox is not None and self.row_id is not None:
                self.outbox.mark_failed(self.row_id, "post_send_channel_mismatch")
            raise ChannelCheckMismatchError(ch_reason)

        rec_ok, rec_reason = self._verify_recipient_header(post_insp, post_snap.html, row)
        if not rec_ok:
            self._stop("post_send_recipient_mismatch")
            if self.outbox is not None and self.row_id is not None:
                self.outbox.mark_failed(self.row_id, "post_send_recipient_mismatch")
            raise RecipientReadbackMismatchError(rec_reason)

        if (
            not post_insp.outbound_bubbles
            or post_insp.outbound_bubbles[-1].strip() != expected_bubble
        ):
            self._stop("last_bubble_mismatch")
            if self.outbox is not None and self.row_id is not None:
                self.outbox.mark_failed(self.row_id, "last_bubble_mismatch")
            raise LastBubbleMismatchError("last_bubble_mismatch")

        return post_snap

    def send(
        self,
        text: Optional[str] = None,
        *,
        recipient_id: Optional[str] = None,
        recipient_display_name: Optional[str] = None,
        expected_channel_name: Optional[str] = None,
        outbox: Optional[Outbox] = None,
        row_id: Optional[int] = None,
    ) -> str:
        """Execute a complete checked send flow for a message or outbox row.

        Returns `"dry_run"` when `live=False` (default) or `"sent_browser"` when `live=True`.
        Stops (`self.halted = True`) and raises on any channel, recipient, or last-bubble mismatch.
        """
        self._check_not_halted()

        if outbox is not None:
            self.outbox = outbox
        if row_id is not None:
            self.row_id = row_id
        if expected_channel_name is not None:
            self.expected_channel_name = expected_channel_name

        row: Optional[dict] = None
        if self.outbox is not None and self.row_id is not None:
            row = self.bind_outbox_row(self.outbox, self.row_id)
            state = row["state"]
            if state == "sending":
                return "skip_sending"
            if state not in ("queued", "deferred"):
                return f"skip_{state}"
            if text is None:
                extracted = _extract_texts_from_payload(row["payload_json"])
                if not extracted:
                    if self.live:
                        self.outbox.mark_failed(self.row_id, "invalid_payload")
                    self._stop("invalid_payload")
                    raise CareDriverError("invalid_payload")
                text = "\n".join(extracted)

        target_id = (recipient_id or self.expected_recipient_id or "").strip()
        if recipient_display_name is not None:
            self.expected_recipient_display_name = recipient_display_name

        if not target_id:
            self._stop("recipient_id_empty")
            raise RecipientReadbackMismatchError("recipient_id_empty")
        if not isinstance(text, str) or not text.strip():
            self._stop("invalid_stage_text")
            raise CareDriverError("invalid_stage_text")

        # 1. Select thread and run pre-send channel check + recipient readback.
        snap = self.select_thread(target_id)
        self._assert_pre_send_dom(snap, row=row, fail_outbox=self.live)

        # 2. DRY-RUN DEFAULT: send is a no-op unless live=True.
        if not self.live:
            self.events.append("send:dry_run_noop")
            self.noop_send_count += 1
            return "dry_run"

        # 3. Stage text via shadow-root locator("textarea"), then click_send (which re-verifies
        #    channel+recipient, marks `sending` immediately before click, clicks Send, and
        #    asserts the last bubble is ours).
        self.stage_text(text)
        self.click_send()

        if self.outbox is not None and self.row_id is not None:
            self.outbox.mark_sent(self.row_id)

        return "sent_browser"

    def send_row(self, outbox: Outbox, row_id: int) -> str:
        """Send a single `care_outbox` row by ID."""
        return self.send(outbox=outbox, row_id=row_id)

    def send_batch(
        self,
        outbox: Outbox,
        row_ids: Iterable[int],
    ) -> list[tuple[int, str]]:
        """Process a sequence of outbox rows, stopping immediately on the first mismatch."""
        results: list[tuple[int, str]] = []
        for rid in row_ids:
            outcome = self.send_row(outbox, rid)
            results.append((rid, outcome))
        return results


CareBrowserDriver = CdpBrowserDriver
OABrowserDriver = CdpBrowserDriver

__all__ = [
    "ACTIVE_CHAT_SELECTOR",
    "ALLOWED_CDP_HOSTS",
    "CHAT_HEADER_SELECTOR",
    "CHAT_LINE_BIZ_HOST",
    "CHAT_LIST_ITEM_SELECTOR",
    "COMPOSER_INPUT_SELECTOR",
    "COMPOSER_TEXTAREA_LOCATOR",
    "CareBrowserDriver",
    "CareDriverError",
    "CdpBrowserDriver",
    "ChannelCheckMismatchError",
    "DEFAULT_CDP_HOST",
    "DEFAULT_CDP_PORT",
    "DEFAULT_CDP_URL",
    "KillSwitchError",
    "LOGIN_LINE_BIZ_HOST",
    "LastBubbleMismatchError",
    "LoginForbiddenError",
    "OABrowserDriver",
    "OA_HEADER_SELECTOR",
    "OUTBOUND_BUBBLE_SELECTOR",
    "PreSendStateError",
    "RecipientReadbackMismatchError",
    "SEND_BUTTON_SELECTOR",
    "connect_over_cdp",
    "inspect_active_chat_item",
    "validate_cdp_url",
]
