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
    ):
        self.outbox = outbox
        self.driver = driver
        self.cfg = cfg
        self.alert_coo = alert_coo
        self.pacer = pacer if pacer is not None else JitterPacer(cfg.pacing)
        self.dry_run = dry_run
        self.clock = clock
        self._reply_backend = ReplyBackend(http, token) if (http is not None and token) else None

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
        texts = _extract_texts_from_payload(row["payload_json"])
        if not texts:
            if not self.dry_run:
                self.outbox.mark_failed(row_id, "invalid_payload")
            return "failed_invalid_payload"

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
