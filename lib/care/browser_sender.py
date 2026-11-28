"""MoonieX Care S2: Offline LINE OA Manager browser sender (docs/design/mooniex-care.md §4).

Strictly offline implementation:
- No live browser, no CDP socket, no winbox SSH, no relay-inventory call, no login.
- Channel check (`MoonieX Officials` / `@mooniex` / `@587kfqpt`) and recipient readback before send.
- Marks outbox row `sending` (`delivery_via='oa_browser'`) BEFORE clicking Send.
- Per-hour and per-day rolling throttle ceilings from config (`null` placeholders stay `None`).
- Human-like jittered pacing across pre-open, proportional typing/staging, and post-send cooldown.
- Kill switch on `captcha`, `warning`, or `logout` (and broken UI selectors): halts immediately,
  flips `care_sender_enabled` to `"false"`, alerts COO once, never auto re-enables.
- Fallback to webhook reply-token path (`api_reply` / `state='fallback'`) when sender is off.
- Never logs or persists tokens or customer PII/text in error strings or alerts.
"""
from __future__ import annotations

import html
import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Optional, Protocol

from .outbox import DEFAULT_BASIC_ID, Outbox
from .quota import Http
from .sender import ReplyBackend

DEFAULT_DISPLAY_NAME = "MoonieX Officials"
DEFAULT_ACCOUNT_NAME = "@mooniex"

SENDER_ENABLED_FLAG = "care_sender_enabled"
KILL_REASON_FLAG = "care_sender_kill_reason"
KILL_ALERT_FLAG = "care_sender_kill_alerted"

KILL_TRIGGERS = ("captcha", "warning", "logout", "ui_selector_missing")


@dataclass(frozen=True)
class PacingConfig:
    pre_open_seconds: tuple[float, float] = (0.25, 0.75)
    per_char_seconds: tuple[float, float] = (0.018, 0.045)
    min_stage_seconds: tuple[float, float] = (0.30, 0.90)
    cooldown_seconds: tuple[float, float] = (1.20, 2.80)

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "PacingConfig":
        if not d:
            return cls()

        def _pair(key: str, default: tuple[float, float]) -> tuple[float, float]:
            val = d.get(key)
            if isinstance(val, (list, tuple)) and len(val) == 2:
                lo, hi = float(val[0]), float(val[1])
                if 0.0 <= lo <= hi:
                    return (lo, hi)
            return default

        return cls(
            pre_open_seconds=_pair("pre_open_seconds", cls.pre_open_seconds),
            per_char_seconds=_pair("per_char_seconds", cls.per_char_seconds),
            min_stage_seconds=_pair("min_stage_seconds", cls.min_stage_seconds),
            cooldown_seconds=_pair("cooldown_seconds", cls.cooldown_seconds),
        )


@dataclass(frozen=True)
class BrowserSenderConfig:
    channel_basic_id: str = DEFAULT_BASIC_ID
    channel_display_name: str = DEFAULT_DISPLAY_NAME
    channel_name: str = DEFAULT_ACCOUNT_NAME
    enabled: bool = True
    cdp_port: Optional[int] = None        # TBD: must stay None in offline S2
    hourly_ceiling: Optional[int] = None  # TBD: null placeholder in config/care.yaml
    daily_ceiling: Optional[int] = None   # TBD: null placeholder in config/care.yaml
    pacing: PacingConfig = field(default_factory=PacingConfig)

    @classmethod
    def from_dict(cls, d: dict) -> "BrowserSenderConfig":
        bs = d.get("browser_sender") or {}
        top_basic = d.get("channel_basic_id", DEFAULT_BASIC_ID)
        hourly = bs.get("hourly_ceiling")
        daily = bs.get("daily_ceiling")
        cdp = bs.get("cdp_port")
        return cls(
            channel_basic_id=bs.get("channel_basic_id") or top_basic,
            channel_display_name=bs.get("channel_display_name", DEFAULT_DISPLAY_NAME),
            channel_name=bs.get("channel_name", DEFAULT_ACCOUNT_NAME),
            enabled=bool(bs.get("enabled", True)),
            cdp_port=int(cdp) if cdp is not None else None,
            hourly_ceiling=int(hourly) if hourly is not None else None,
            daily_ceiling=int(daily) if daily is not None else None,
            pacing=PacingConfig.from_dict(bs.get("pacing")),
        )


def load_care_config(path: Optional[Path] = None) -> dict:
    """Load config/care.yaml preserving null (None) placeholders."""
    cfg_path = path or Path(__file__).resolve().parents[2] / "config" / "care.yaml"
    text = cfg_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, rest = line.strip().partition(":")
        val_str = rest.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if val_str == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_yaml_scalar(val_str)
    return root


def _parse_yaml_scalar(val_str: str):
    if val_str in ("null", "Null", "NULL", "~"):
        return None
    if val_str in ("true", "True"):
        return True
    if val_str in ("false", "False"):
        return False
    if val_str.startswith("[") and val_str.endswith("]"):
        return json.loads(val_str)
    if (val_str.startswith('"') and val_str.endswith('"')) or (
        val_str.startswith("'") and val_str.endswith("'")
    ):
        return val_str[1:-1]
    try:
        return int(val_str)
    except ValueError:
        try:
            return float(val_str)
        except ValueError:
            return val_str


@dataclass(frozen=True)
class ThrottleDecision:
    allowed: bool
    reason: str
    hourly_used: int = 0
    daily_used: int = 0


def decide_browser_throttle(
    cfg: BrowserSenderConfig,
    hourly_used: int,
    daily_used: int,
    batch: int = 1,
) -> ThrottleDecision:
    """Evaluate rolling per-hour and per-day ceilings (TBD null -> unset/allowed)."""
    if cfg.hourly_ceiling is not None and hourly_used + batch > cfg.hourly_ceiling:
        return ThrottleDecision(False, "hourly_ceiling", hourly_used, daily_used)
    if cfg.daily_ceiling is not None and daily_used + batch > cfg.daily_ceiling:
        return ThrottleDecision(False, "daily_ceiling", hourly_used, daily_used)
    unset = cfg.hourly_ceiling is None or cfg.daily_ceiling is None
    return ThrottleDecision(
        True,
        "ok_ceilings_unset" if unset else "ok",
        hourly_used,
        daily_used,
    )


class JitterPacer:
    """Human-like non-uniform pacing generator with injectable RNG and sleep."""

    def __init__(
        self,
        cfg: PacingConfig = PacingConfig(),
        rng: Optional[random.Random] = None,
        sleep: Callable[[float], None] = lambda _s: None,
    ):
        self.cfg = cfg
        self.rng = rng if rng is not None else random.Random()
        self.sleep = sleep
        self.history: list[tuple[str, float]] = []

    def _sample(self, bounds: tuple[float, float]) -> float:
        lo, hi = bounds
        if hi <= lo:
            return max(0.0, lo)
        return self.rng.uniform(lo, hi)

    def pause_pre_open(self) -> float:
        delay = round(self._sample(self.cfg.pre_open_seconds), 4)
        self.history.append(("pre_open", delay))
        self.sleep(delay)
        return delay

    def pause_stage_typing(self, char_count: int) -> float:
        base = self._sample(self.cfg.min_stage_seconds)
        per_char = self._sample(self.cfg.per_char_seconds)
        delay = round(base + max(1, int(char_count)) * per_char, 4)
        self.history.append(("stage_typing", delay))
        self.sleep(delay)
        return delay

    def pause_cooldown(self) -> float:
        delay = round(self._sample(self.cfg.cooldown_seconds), 4)
        self.history.append(("cooldown", delay))
        self.sleep(delay)
        return delay


@dataclass(frozen=True)
class DomInspection:
    page_state: str  # "normal_chat" | "captcha" | "warning" | "logout" | "ui_selector_missing"
    url: str = ""
    channel_basic_id: Optional[str] = None
    channel_display_name: Optional[str] = None
    channel_account_name: Optional[str] = None
    recipient_id: Optional[str] = None
    recipient_display_name: Optional[str] = None
    has_oa_header: bool = False
    has_chat_header: bool = False
    has_composer_input: bool = False
    has_send_button: bool = False
    outbound_bubbles: tuple[str, ...] = ()
    hazard_detail: Optional[str] = None


class _OADomParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_url: str = ""
        self.explicit_states: list[str] = []
        self.captcha_signals: list[str] = []
        self.warning_signals: list[str] = []
        self.logout_signals: list[str] = []

        self.oa_header_count: int = 0
        self.chat_header_count: int = 0
        self.composer_count: int = 0
        self.send_button_count: int = 0

        self.channel_basic_id: Optional[str] = None
        self.channel_display_name: Optional[str] = None
        self.channel_account_name: Optional[str] = None
        self.recipient_id: Optional[str] = None
        self.recipient_display_name: Optional[str] = None
        self.outbound_bubbles: list[str] = []

        self._text_stack: list[tuple[str, list[str]]] = []
        self._all_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        ad = {k.lower(): (v or "") for k, v in attrs}
        cls = ad.get("class", "")
        cls_tokens = set(cls.lower().split())
        el_id = ad.get("id", "").lower()

        if tag == "meta" and ad.get("name", "").lower() == "page-url":
            self.meta_url = ad.get("content", "").strip()

        page_state = ad.get("data-page-state", "").strip().lower()
        if page_state in ("captcha", "warning", "logout"):
            self.explicit_states.append(page_state)

        # Hazard attribute/class signals
        if (
            "data-captcha" in ad
            or "captcha" in el_id
            or any(c in cls_tokens for c in ("captcha", "captcha-modal", "g-recaptcha", "h-captcha", "cf-turnstile"))
        ):
            self.captcha_signals.append("selector_captcha")

        if (
            "data-oa-warning" in ad
            or "warning" in el_id
            or any(
                c in cls_tokens
                for c in ("oa-warning", "oa-warning-banner", "oa-policy-warning-modal", "rate-warning", "policy-warning")
            )
        ):
            self.warning_signals.append("selector_warning")

        if (
            "data-login-form" in ad
            or "login" in el_id
            or any(c in cls_tokens for c in ("line-login-form", "session-expired", "login-redirect"))
            or (tag == "form" and "account.line.biz" in ad.get("action", "").lower())
        ):
            self.logout_signals.append("selector_logout")

        # OA header selectors
        if "data-oa-header" in ad or "oa-account-header" in cls_tokens:
            self.oa_header_count += 1
            if ad.get("data-basic-id"):
                self.channel_basic_id = ad["data-basic-id"].strip()
            if ad.get("data-display-name"):
                self.channel_display_name = ad["data-display-name"].strip()
            if ad.get("data-account-name"):
                self.channel_account_name = ad["data-account-name"].strip()

        if "oa-display-name" in cls_tokens or "data-oa-display-name" in ad:
            if ad.get("data-oa-display-name"):
                self.channel_display_name = ad["data-oa-display-name"].strip()
            self._text_stack.append(("oa_display_name", []))
            return
        if "oa-basic-id" in cls_tokens or "data-oa-basic-id" in ad:
            if ad.get("data-oa-basic-id"):
                self.channel_basic_id = ad["data-oa-basic-id"].strip()
            self._text_stack.append(("oa_basic_id", []))
            return
        if "oa-account-name" in cls_tokens or "data-oa-account-name" in ad:
            if ad.get("data-oa-account-name"):
                self.channel_account_name = ad["data-oa-account-name"].strip()
            self._text_stack.append(("oa_account_name", []))
            return

        # Recipient chat header selectors
        if "data-chat-header" in ad or "chat-thread-header" in cls_tokens:
            self.chat_header_count += 1
            if ad.get("data-recipient-id"):
                self.recipient_id = ad["data-recipient-id"].strip()
            if ad.get("data-recipient-display-name"):
                self.recipient_display_name = ad["data-recipient-display-name"].strip()

        if "chat-recipient-name" in cls_tokens or "data-recipient-display-name" in ad:
            if ad.get("data-recipient-display-name"):
                self.recipient_display_name = ad["data-recipient-display-name"].strip()
            if ad.get("data-recipient-id") and not self.recipient_id:
                self.recipient_id = ad["data-recipient-id"].strip()
            self._text_stack.append(("recipient_display_name", []))
            return

        if "chat-recipient-id" in cls_tokens:
            self._text_stack.append(("recipient_id", []))
            return

        # Composer & Send button selectors
        if "data-composer-input" in ad or (tag == "textarea" and "chat-composer-input" in cls_tokens):
            if "disabled" not in ad:
                self.composer_count += 1

        if "data-send-button" in ad or (tag == "button" and "chat-send-btn" in cls_tokens):
            if "disabled" not in ad:
                self.send_button_count += 1

        # Outbound bubble in chat transcript
        if "data-outbound-bubble" in ad or "chat-bubble-outbound" in cls_tokens:
            self._text_stack.append(("outbound_bubble", []))
            return

        self._text_stack.append(("", []))

    def handle_endtag(self, tag: str) -> None:
        if not self._text_stack:
            return
        role, chunks = self._text_stack.pop()
        text = "".join(chunks).strip()
        if not text:
            return
        if role == "oa_display_name" and not self.channel_display_name:
            self.channel_display_name = text
        elif role == "oa_basic_id" and not self.channel_basic_id:
            self.channel_basic_id = text
        elif role == "oa_account_name" and not self.channel_account_name:
            self.channel_account_name = text
        elif role == "recipient_display_name" and not self.recipient_display_name:
            self.recipient_display_name = text
        elif role == "recipient_id" and not self.recipient_id:
            self.recipient_id = text
        elif role == "outbound_bubble":
            self.outbound_bubbles.append(text)

    def handle_data(self, data: str) -> None:
        if self._text_stack:
            self._text_stack[-1][1].append(data)
        stripped = data.strip()
        if stripped:
            self._all_text.append(stripped)


def inspect_oa_dom(raw_html: str, url: str = "") -> DomInspection:
    """Inspect an offline HTML snapshot of chat.line.biz and classify its state."""
    parser = _OADomParser()
    parser.feed(raw_html or "")
    parser.close()

    effective_url = (url or parser.meta_url or "").strip()
    url_lower = effective_url.lower()
    full_text_lower = " ".join(parser._all_text).lower()

    # 1. Check captcha
    if (
        "captcha" in parser.explicit_states
        or parser.captcha_signals
        or "/captcha" in url_lower
        or any(
            phrase in full_text_lower
            for phrase in (
                "captcha challenge",
                "verify you are human",
                "security verification",
                "complete the verification challenge",
            )
        )
    ):
        return DomInspection(
            page_state="captcha",
            url=effective_url,
            hazard_detail="captcha_detected",
        )

    # 2. Check warning
    if (
        "warning" in parser.explicit_states
        or parser.warning_signals
        or any(
            phrase in full_text_lower
            for phrase in (
                "automated activity warning",
                "unusual message sending rate",
                "policy warning",
                "account restriction warning",
                "rate limit warning",
            )
        )
    ):
        return DomInspection(
            page_state="warning",
            url=effective_url,
            hazard_detail="warning_detected",
        )

    # 3. Check logout / session expiry
    if (
        "logout" in parser.explicit_states
        or parser.logout_signals
        or "account.line.biz" in url_lower
        or "/login" in url_lower
        or any(
            phrase in full_text_lower
            for phrase in (
                "log in with line",
                "session expired",
                "please log in to continue",
                "sign in to line official account",
            )
        )
    ):
        return DomInspection(
            page_state="logout",
            url=effective_url,
            hazard_detail="logout_detected",
        )

    has_oa = parser.oa_header_count == 1
    has_chat = parser.chat_header_count == 1
    has_composer = parser.composer_count == 1
    has_send = parser.send_button_count == 1

    if not (has_oa and has_chat and has_composer and has_send):
        return DomInspection(
            page_state="ui_selector_missing",
            url=effective_url,
            channel_basic_id=parser.channel_basic_id,
            channel_display_name=parser.channel_display_name,
            channel_account_name=parser.channel_account_name,
            recipient_id=parser.recipient_id,
            recipient_display_name=parser.recipient_display_name,
            has_oa_header=has_oa,
            has_chat_header=has_chat,
            has_composer_input=has_composer,
            has_send_button=has_send,
            outbound_bubbles=tuple(parser.outbound_bubbles),
            hazard_detail="required_selector_missing_or_ambiguous",
        )

    return DomInspection(
        page_state="normal_chat",
        url=effective_url,
        channel_basic_id=parser.channel_basic_id,
        channel_display_name=parser.channel_display_name,
        channel_account_name=parser.channel_account_name,
        recipient_id=parser.recipient_id,
        recipient_display_name=parser.recipient_display_name,
        has_oa_header=True,
        has_chat_header=True,
        has_composer_input=True,
        has_send_button=True,
        outbound_bubbles=tuple(parser.outbound_bubbles),
    )


def verify_channel(
    inspection: DomInspection,
    cfg: BrowserSenderConfig,
    row_basic_id: Optional[str] = None,
) -> tuple[bool, str]:
    """Verify active OA matches MoonieX Officials / @mooniex / @587kfqpt (design §4.6)."""
    expected_basic = (row_basic_id or cfg.channel_basic_id or DEFAULT_BASIC_ID).strip().lower()
    cfg_basic = (cfg.channel_basic_id or DEFAULT_BASIC_ID).strip().lower()
    if expected_basic != cfg_basic:
        return False, "channel_basic_id_config_mismatch"

    actual_basic = (inspection.channel_basic_id or "").strip().lower()
    if not actual_basic or actual_basic != expected_basic:
        return False, "channel_basic_id_mismatch"

    expected_display = (cfg.channel_display_name or DEFAULT_DISPLAY_NAME).strip()
    actual_display = (inspection.channel_display_name or "").strip()
    if not actual_display or actual_display != expected_display:
        return False, "channel_display_name_mismatch"

    if inspection.channel_account_name is not None:
        expected_account = (cfg.channel_name or DEFAULT_ACCOUNT_NAME).strip().lower()
        actual_account = inspection.channel_account_name.strip().lower()
        if actual_account != expected_account:
            return False, "channel_account_name_mismatch"

    return True, "ok"


def verify_recipient(inspection: DomInspection, row: dict) -> tuple[bool, str]:
    """Verify active chat header matches care_outbox recipient_id and recipient_display_name."""
    expected_id = str(row.get("recipient_id") or "").strip()
    expected_name = str(row.get("recipient_display_name") or "").strip()
    actual_id = (inspection.recipient_id or "").strip()
    actual_name = (inspection.recipient_display_name or "").strip()

    if not expected_id or not actual_id or actual_id != expected_id:
        return False, "recipient_id_mismatch"
    if not expected_name or not actual_name or actual_name != expected_name:
        return False, "recipient_display_name_mismatch"
    return True, "ok"


@dataclass(frozen=True)
class PageSnapshot:
    html: str
    url: str = "https://chat.line.biz/"


class BrowserDriver(Protocol):
    def get_page(self) -> PageSnapshot: ...
    def select_thread(self, recipient_id: str) -> PageSnapshot: ...
    def stage_text(self, text: str) -> PageSnapshot: ...
    def click_send(self) -> PageSnapshot: ...


class FixtureBrowserDriver:
    """Offline DOM fixture driver for S2 tests (no live browser, no network, no login)."""

    def __init__(
        self,
        initial_html: str,
        url: str = "https://chat.line.biz/",
        on_before_click: Optional[Callable[[], None]] = None,
        post_click_html: Optional[str] = None,
        render_bubble_on_click: bool = True,
    ):
        self._html = initial_html
        self._url = url
        self._on_before_click = on_before_click
        self._post_click_html = post_click_html
        self._render_bubble_on_click = render_bubble_on_click
        self.staged_texts: list[str] = []
        self.selected_threads: list[str] = []
        self.click_count: int = 0
        self.login_attempts: int = 0
        self.events: list[str] = []

    @classmethod
    def from_fixture_path(cls, path: Path, **kwargs) -> "FixtureBrowserDriver":
        return cls(path.read_text(encoding="utf-8"), **kwargs)

    def get_page(self) -> PageSnapshot:
        self.events.append("get_page")
        return PageSnapshot(html=self._html, url=self._url)

    def select_thread(self, recipient_id: str) -> PageSnapshot:
        self.events.append(f"select_thread:{recipient_id}")
        self.selected_threads.append(recipient_id)
        return PageSnapshot(html=self._html, url=self._url)

    def stage_text(self, text: str) -> PageSnapshot:
        self.events.append("stage_text")
        self.staged_texts.append(text)
        return PageSnapshot(html=self._html, url=self._url)

    def click_send(self) -> PageSnapshot:
        if self._on_before_click is not None:
            self._on_before_click()
        self.events.append("click_send")
        self.click_count += 1
        if self._post_click_html is not None:
            self._html = self._post_click_html
            return PageSnapshot(html=self._html, url=self._url)
        if self._render_bubble_on_click and self.staged_texts:
            escaped = html.escape(self.staged_texts[-1])
            bubble_html = f'<div class="chat-bubble-outbound" data-outbound-bubble="true">{escaped}</div>'
            if "</div><!--chat-transcript-end-->" in self._html:
                self._html = self._html.replace(
                    "</div><!--chat-transcript-end-->",
                    f"{bubble_html}</div><!--chat-transcript-end-->",
                )
            elif "</body>" in self._html:
                self._html = self._html.replace("</body>", f"{bubble_html}</body>")
            else:
                self._html = self._html + bubble_html
        return PageSnapshot(html=self._html, url=self._url)

    def attempt_login(self, *_args, **_kwargs) -> None:
        """Hard rule (design §4.2, §4.6): sender must NEVER attempt login."""
        self.login_attempts += 1
        raise RuntimeError("login_forbidden")


def _extract_texts_from_payload(payload_json: str) -> Optional[list[str]]:
    try:
        data = json.loads(payload_json)
    except Exception:
        return None
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data or len(data) > 5:
        return None
    texts: list[str] = []
    for item in data:
        if not isinstance(item, dict) or item.get("type") != "text":
            return None
        txt = item.get("text")
        if not isinstance(txt, str) or not txt.strip():
            return None
        texts.append(txt)
    return texts


def _extract_outbox_items(payload_json: str) -> Optional[list[dict]]:
    """Extract 1..6 outbound items (`text` bubbles and optional `image` transfer slips)."""
    try:
        data = json.loads(payload_json)
    except Exception:
        return None
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data or len(data) > 6:
        return None
    items: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            return None
        kind = item.get("type")
        if kind == "text":
            txt = item.get("text")
            if not isinstance(txt, str) or not txt.strip():
                return None
            items.append({"type": "text", "text": txt.strip()})
        elif kind == "image":
            fp = item.get("file_path")
            if not isinstance(fp, str) or not fp.strip():
                return None
            items.append({"type": "image", "file_path": fp.strip()})
        else:
            return None
    return items


class WinboxPlaywrightDriver:
    """Live Playwright CDP driver for `winbox:9285` (`line-oa-win` via `127.0.0.1:19285`).

    Hard rules (CEO Q-20261128-0926-a657 & design §4):
    - Zero LINE OA API calls: 100% browser delivery on `chat.line.biz`.
    - Wraps session in `home_lock('home:winbox:9285')` when available.
    - Never attempts automated login, never solves or clicks CAPTCHAs, never touches `terminal64`.
    - Verifies `MoonieX Officials` header + exact active recipient display name before sending.
    """

    OA_CHAT_URL = "https://chat.line.biz/U1434fa89bc696a8ba3e84e6fd6f8e70b"

    def __init__(
        self,
        *,
        local_cdp_port: int = 19285,
        winbox_cdp_port: int = 9285,
        channel_basic_id: str = DEFAULT_BASIC_ID,
        channel_display_name: str = DEFAULT_DISPLAY_NAME,
        channel_account_name: str = DEFAULT_ACCOUNT_NAME,
    ):
        self.local_cdp_port = local_cdp_port
        self.winbox_cdp_port = winbox_cdp_port
        self.channel_basic_id = channel_basic_id
        self.channel_display_name = channel_display_name
        self.channel_account_name = channel_account_name
        self._pw = None
        self._browser = None
        self._page = None
        self._lock_cm = None
        self._expected_recipient_id: str = ""
        self._expected_recipient_name: str = ""
        self._confirmed_bubbles: list[str] = []

    def _ensure_tunnel(self) -> bool:
        import subprocess
        import urllib.request

        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.local_cdp_port}/json/version", timeout=2).read()
            return True
        except Exception:
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
                f"127.0.0.1:{self.local_cdp_port}:127.0.0.1:{self.winbox_cdp_port}",
                "winbox",
            ],
            capture_output=True,
            text=True,
        )
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.local_cdp_port}/json/version", timeout=3).read()
            return True
        except Exception:
            return False

    def open(self) -> "WinboxPlaywrightDriver":
        if not self._ensure_tunnel():
            raise RuntimeError("winbox_9285_tunnel_unreachable")
        try:
            from tools.home_lock import home_lock

            self._lock_cm = home_lock(
                f"home:winbox:{self.winbox_cdp_port}",
                purpose="mooniex_care_outbox",
                wait_s=120,
            )
            self._lock_cm.__enter__()
        except Exception:
            self._lock_cm = None

        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(f"http://127.0.0.1:{self.local_cdp_port}")
        ctx = self._browser.contexts[0]
        self._page = ctx.new_page()
        self._page.goto(self.OA_CHAT_URL, timeout=45000)
        self._page.wait_for_timeout(5500)
        return self

    def close(self) -> None:
        try:
            if self._page is not None:
                self._page.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass
        if self._lock_cm is not None:
            try:
                self._lock_cm.__exit__(None, None, None)
            except Exception:
                pass
            self._lock_cm = None

    def __enter__(self) -> "WinboxPlaywrightDriver":
        return self.open()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def bind_expected_recipient(self, recipient_id: str, recipient_display_name: str) -> None:
        self._expected_recipient_id = recipient_id.strip()
        self._expected_recipient_name = recipient_display_name.strip()
        self._confirmed_bubbles = []

    def _build_snapshot(self, *, require_thread: bool = False) -> PageSnapshot:
        pg = self._page
        if pg is None:
            return PageSnapshot(html='<div data-page-state="logout"></div>', url="https://account.line.biz/login")
        cur_url = pg.url or ""
        url_low = cur_url.lower()
        body_txt = ""
        try:
            body_txt = pg.locator("body").inner_text(timeout=5000)
        except Exception:
            body_txt = ""
        body_low = body_txt.lower()

        if pg.locator("iframe[src*='captcha'], iframe[src*='recaptcha'], iframe[src*='hcaptcha'], .g-recaptcha, .h-captcha").count() > 0 or "/captcha" in url_low:
            return PageSnapshot(html='<div data-page-state="captcha"></div>', url=cur_url)

        if "account.line.biz" in url_low or "/login" in url_low or "line business id" in body_low:
            return PageSnapshot(html='<div data-page-state="logout"></div>', url=cur_url)

        if any(w in body_low for w in ("automated activity warning", "policy warning", "account restriction warning")):
            return PageSnapshot(html='<div data-page-state="warning"></div>', url=cur_url)

        has_oa = self.channel_display_name in body_txt
        disp_attr = html.escape(self.channel_display_name if has_oa else "WRONG_OA")
        basic_attr = html.escape(self.channel_basic_id if has_oa else "")
        acct_attr = html.escape(self.channel_account_name if has_oa else "")

        if not require_thread:
            # Pre-navigation check before a specific customer thread is clicked
            rec_name = html.escape(self._expected_recipient_name or "IDLE")
            rec_id = html.escape(self._expected_recipient_id or "IDLE")
            synth = (
                f'<header data-oa-header="1" data-basic-id="{basic_attr}" '
                f'data-display-name="{disp_attr}" data-account-name="{acct_attr}"></header>'
                f'<div data-chat-header="1" data-recipient-id="{rec_id}" data-recipient-display-name="{rec_name}"></div>'
                '<textarea data-composer-input="1"></textarea>'
                '<button data-send-button="1">Send</button>'
            )
            return PageSnapshot(html=synth, url=cur_url)

        active_name = pg.evaluate(
            "(() => { const a = document.querySelector('.list-group-item.active'); return a ? a.innerText.split('\\n')[0].trim() : ''; })()"
        ) or ""
        ta_count = pg.locator("textarea:not([disabled])").count()
        send_count = pg.locator("input.btn-primary:not([disabled]), button[type='submit']:not([disabled])").count()
        rec_id_out = self._expected_recipient_id if active_name == self._expected_recipient_name else "MISMATCH"
        bubbles_html = "".join(
            f'<div class="chat-bubble-outbound" data-outbound-bubble="true">{html.escape(b)}</div>'
            for b in self._confirmed_bubbles
        )
        ta_html = '<textarea data-composer-input="1"></textarea>' if ta_count == 1 else ""
        btn_html = '<button data-send-button="1">Send</button>' if send_count >= 1 else ""
        synth = (
            f'<header data-oa-header="1" data-basic-id="{basic_attr}" '
            f'data-display-name="{disp_attr}" data-account-name="{acct_attr}"></header>'
            f'<div data-chat-header="1" data-recipient-id="{html.escape(rec_id_out)}" '
            f'data-recipient-display-name="{html.escape(active_name)}"></div>'
            f"{ta_html}{btn_html}{bubbles_html}"
        )
        return PageSnapshot(html=synth, url=cur_url)

    def get_page(self) -> PageSnapshot:
        return self._build_snapshot(require_thread=False)

    def select_thread(self, recipient_id: str) -> PageSnapshot:
        pg = self._page
        assert pg is not None
        target_name = self._expected_recipient_name or recipient_id
        pg.get_by_text(target_name, exact=True).first.click(timeout=10000)
        pg.wait_for_timeout(3500)
        return self._build_snapshot(require_thread=True)

    def stage_text(self, text: str) -> PageSnapshot:
        pg = self._page
        assert pg is not None
        pg.locator("textarea").first.fill(text)
        pg.wait_for_timeout(400)
        return self._build_snapshot(require_thread=True)

    def click_send(self) -> PageSnapshot:
        pg = self._page
        assert pg is not None
        staged = pg.locator("textarea").first.input_value()
        pg.locator("input.btn-primary, button[type='submit']").last.click(timeout=8000)
        pg.wait_for_timeout(3200)
        body_now = pg.locator("body").inner_text(timeout=5000)
        probe = staged.strip()[:24]
        if probe and probe in body_now and pg.locator("textarea").first.input_value() == "":
            self._confirmed_bubbles.append(staged.strip())
        return self._build_snapshot(require_thread=True)

    def send_items(self, items: list[dict], pacer: JitterPacer) -> tuple[bool, PageSnapshot, str]:
        """Send multi-bubble text items and optional slip images one by one with human jitter."""
        pg = self._page
        assert pg is not None
        for idx, item in enumerate(items):
            if item["type"] == "text":
                txt = item["text"]
                pacer.pause_stage_typing(len(txt))
                pg.locator("textarea").first.fill(txt)
                pg.wait_for_timeout(500)
                snap_mid = self._build_snapshot(require_thread=True)
                if inspect_oa_dom(snap_mid.html, snap_mid.url).page_state in KILL_TRIGGERS:
                    return False, snap_mid, "kill_switch_mid_send"
                pg.locator("input.btn-primary, button[type='submit']").last.click(timeout=8000)
                pg.wait_for_timeout(3200)
                pacer.pause_cooldown()
                body_now = pg.locator("body").inner_text(timeout=5000)
                probe = txt[:24]
                if not (probe in body_now and pg.locator("textarea").first.input_value() == ""):
                    return False, self._build_snapshot(require_thread=True), f"bubble_{idx+1}_unconfirmed"
                self._confirmed_bubbles.append(txt)
            elif item["type"] == "image":
                fpath = Path(item["file_path"])
                if not fpath.is_file():
                    return False, self._build_snapshot(require_thread=True), "slip_file_missing"
                file_inp = pg.locator("input[type='file']").first
                file_inp.set_input_files(str(fpath))
                pg.wait_for_timeout(4500)
                pacer.pause_cooldown()
        return True, self._build_snapshot(require_thread=True), "ok"


def manual_reenable_sender(outbox: Outbox, *, operator_id: str) -> None:
    """Explicit human operator re-enable of the browser sender kill switch (design §4.6).

    Automated routines must NEVER call this function.
    """
    if not isinstance(operator_id, str) or not operator_id.strip():
        raise ValueError("operator_id required for manual re-enable")
    outbox.set_flag(SENDER_ENABLED_FLAG, "true")
    outbox.set_flag(KILL_REASON_FLAG, f"reenabled_by:{operator_id.strip()}")
    outbox.conn.execute("DELETE FROM care_state WHERE key=?", (KILL_ALERT_FLAG,))
    outbox.conn.commit()


class BrowserSender:
    """S2 offline LINE OA Manager browser sender (`chat.line.biz`)."""

    def __init__(
        self,
        outbox: Outbox,
        driver: BrowserDriver,
        cfg: BrowserSenderConfig = BrowserSenderConfig(),
        alert_coo: Callable[[str], None] = lambda _msg: None,
        pacer: Optional[JitterPacer] = None,
        http: Optional[Http] = None,
        token: Optional[str] = None,
        dry_run: bool = False,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        winbox_only: bool = False,
    ):
        self.outbox = outbox
        self.driver = driver
        self.cfg = cfg
        self.alert_coo = alert_coo
        self.pacer = pacer if pacer is not None else JitterPacer(cfg.pacing)
        self.dry_run = dry_run
        self.clock = clock
        self.winbox_only = winbox_only
        # CEO Q-20261128-0926-a657: when winbox_only=True, zero LINE OA API calls are ever permitted.
        self._reply_backend = (
            None if winbox_only else (ReplyBackend(http, token) if (http is not None and token) else None)
        )

    def is_enabled(self) -> bool:
        flag = self.outbox.get_flag(SENDER_ENABLED_FLAG)
        if flag == "false":
            return False
        if flag == "true":
            return True
        return bool(self.cfg.enabled)

    def _token_valid(self, row: dict) -> bool:
        if not row.get("reply_token"):
            return False
        exp = row.get("reply_token_expires_at")
        if exp is None:
            return True
        return self.clock() < datetime.fromisoformat(exp)

    def _trip_kill_switch(self, trigger: str) -> None:
        self.outbox.set_flag(SENDER_ENABLED_FLAG, "false")
        self.outbox.set_flag(KILL_REASON_FLAG, trigger)
        if self.outbox.set_flag_once(KILL_ALERT_FLAG, trigger):
            self.alert_coo(f"care browser sender kill switch tripped: {trigger}")

    def _fallback_when_off(self, row: dict, reason: str) -> str:
        rid = row["id"]
        if self.winbox_only:
            if not self.dry_run:
                self.outbox.mark_deferred(rid, f"winbox_only_hold:{reason}")
            return "defer_winbox_only"
        if self._reply_backend is not None and self._token_valid(row):
            if self.dry_run:
                return "would_fallback_reply"
            if not self.outbox.claim_sending(rid, "api_reply"):
                return "skip_claimed"
            try:
                status, _ = self._reply_backend.send(row)
            except Exception:
                self.outbox.mark_failed(rid, "reply_network_unconfirmed")
                return "failed"
            if status == 200:
                self.outbox.mark_sent(rid)
                return "sent_fallback_reply"
            if status == 400:
                self.outbox.clear_reply_token(rid)
                self.outbox.mark_fallback(rid, "reply_token_rejected")
                return "fallback_reply_rejected"
            self.outbox.mark_failed(rid, f"reply_http_{status}")
            return "failed"

        if not self.dry_run:
            self.outbox.mark_fallback(rid, reason)
        return "fallback_reply_token"

    def _check_throttle(self) -> ThrottleDecision:
        now = self.clock()
        hourly_used = self.outbox.count_browser_sends_since(now - timedelta(hours=1))
        daily_used = self.outbox.count_browser_sends_since(now - timedelta(hours=24))
        return decide_browser_throttle(self.cfg, hourly_used, daily_used, batch=1)

    def process(self, row_id: int) -> str:
        row = self.outbox.get(row_id)
        state = row["state"]

        # Crash recovery guard (design §2.3.3): never auto-retry a row already in `sending`.
        if state == "sending":
            return "skip_sending"

        if state == "fallback":
            if self._reply_backend is not None and self._token_valid(row):
                return self._fallback_when_off(row, "sender_disabled_fallback_reply_token")
            return "skip_fallback"

        if state not in ("queued", "deferred"):
            return f"skip_{state}"

        # 1. If kill switch is active or sender is disabled in config, do not touch browser.
        if not self.is_enabled():
            return self._fallback_when_off(row, "sender_disabled_fallback_reply_token")

        # 2. Validate payload structure before touching browser or claiming sending.
        items = _extract_outbox_items(row["payload_json"])
        texts = _extract_texts_from_payload(row["payload_json"])
        use_multi_items = hasattr(self.driver, "send_items")
        if (not items) if use_multi_items else (not texts):
            if not self.dry_run:
                self.outbox.mark_failed(row_id, "invalid_payload")
            return "failed_invalid_payload"

        if hasattr(self.driver, "bind_expected_recipient"):
            self.driver.bind_expected_recipient(row["recipient_id"], row["recipient_display_name"])

        # 3. Check rolling per-hour and per-day throttle ceilings.
        throttle = self._check_throttle()
        if not throttle.allowed:
            if not self.dry_run:
                self.outbox.mark_deferred(row_id, f"throttle_{throttle.reason}")
            return f"deferred_{throttle.reason}"

        # 4. Pre-navigation page inspection for captcha / warning / logout.
        snap = self.driver.get_page()
        pre_insp = inspect_oa_dom(snap.html, snap.url)
        if pre_insp.page_state in KILL_TRIGGERS:
            self._trip_kill_switch(pre_insp.page_state)
            self._fallback_when_off(row, f"kill_switch_{pre_insp.page_state}")
            return f"kill_switch_{pre_insp.page_state}"

        # 5. Human-like jittered pause before selecting/opening thread.
        self.pacer.pause_pre_open()
        snap = self.driver.select_thread(row["recipient_id"])
        insp = inspect_oa_dom(snap.html, snap.url)
        if insp.page_state in KILL_TRIGGERS:
            self._trip_kill_switch(insp.page_state)
            self._fallback_when_off(row, f"kill_switch_{insp.page_state}")
            return f"kill_switch_{insp.page_state}"

        # 6. Mandatory Channel Check (MoonieX Officials / @mooniex / @587kfqpt).
        ch_ok, _ch_reason = verify_channel(insp, self.cfg, row.get("channel_basic_id"))
        if not ch_ok:
            if not self.dry_run:
                self.outbox.mark_failed(row_id, "channel_check_mismatch")
            self.alert_coo("care browser sender channel check mismatch")
            return "failed_channel_check"

        # 7. Mandatory Recipient Readback before marking sending.
        rec_ok, _rec_reason = verify_recipient(insp, row)
        if not rec_ok:
            if not self.dry_run:
                self.outbox.mark_failed(row_id, "recipient_readback_mismatch")
            self.alert_coo("care browser sender recipient readback mismatch")
            return "failed_recipient_readback"

        if self.dry_run:
            return "would_send_browser"

        if use_multi_items and items is not None:
            if not self.outbox.claim_sending(row_id, "oa_browser"):
                return "skip_claimed"
            try:
                ok_multi, post_snap, err_reason = self.driver.send_items(items, self.pacer)
            except Exception:
                self.outbox.mark_failed(row_id, "browser_click_exception")
                return "failed"
            post_insp = inspect_oa_dom(post_snap.html, post_snap.url)
            if post_insp.page_state in KILL_TRIGGERS:
                self._trip_kill_switch(post_insp.page_state)
                self.outbox.mark_failed(row_id, f"post_click_kill_switch_{post_insp.page_state}")
                return f"kill_switch_{post_insp.page_state}"
            if not ok_multi:
                self.outbox.mark_failed(row_id, err_reason)
                return "failed_unconfirmed"
            self.outbox.mark_sent(row_id)
            return "sent_browser"

        assert texts is not None
        # 8. Stage message text with human-like proportional typing jitter.
        combined_text = "\n".join(texts)
        self.pacer.pause_stage_typing(len(combined_text))
        snap = self.driver.stage_text(combined_text)
        staged_insp = inspect_oa_dom(snap.html, snap.url)
        if staged_insp.page_state in KILL_TRIGGERS:
            self._trip_kill_switch(staged_insp.page_state)
            self._fallback_when_off(row, f"kill_switch_{staged_insp.page_state}")
            return f"kill_switch_{staged_insp.page_state}"

        # 9. CRITICAL: Mark row `sending` (`oa_browser`) BEFORE clicking Send (design §2.3.2).
        if not self.outbox.claim_sending(row_id, "oa_browser"):
            return "skip_claimed"

        # 10. Click Send, then pause for human-like post-send cooldown.
        try:
            post_snap = self.driver.click_send()
        except Exception:
            self.outbox.mark_failed(row_id, "browser_click_exception")
            return "failed"

        self.pacer.pause_cooldown()

        # 11. Post-send inspection: check for kill-switch hazards and confirm rendered bubble.
        post_insp = inspect_oa_dom(post_snap.html, post_snap.url)
        if post_insp.page_state in KILL_TRIGGERS:
            self._trip_kill_switch(post_insp.page_state)
            self.outbox.mark_failed(row_id, f"post_click_kill_switch_{post_insp.page_state}")
            return f"kill_switch_{post_insp.page_state}"

        if combined_text.strip() not in post_insp.outbound_bubbles:
            self.outbox.mark_failed(row_id, "browser_bubble_unconfirmed")
            return "failed_unconfirmed"

        self.outbox.mark_sent(row_id)
        return "sent_browser"
