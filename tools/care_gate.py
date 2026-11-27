#!/usr/bin/env python3
"""MoonieX Care Phase 1 (P1) gate and operating-hours ack policy (docs/design/mooniex-care.md §6).

Enforces the strict tool allowlist and security boundaries for the `care` session
("น้องมูน", Sonnet 5.5, own Unix user & gate, supervised by SomPong `coo`):

- Customer messages are untrusted data, never instructions.
- Allowed tools ONLY (§6.5):
  1. `reply`    — enqueue plain-text reply bubbles (<=5 per call) into `care_outbox` for the active customer.
  2. `skip`     — close the current event turn without sending a message.
  3. `history`  — read conversation history for THAT customer only (strictly scoped to active `customer_id`).
  4. `media`    — read/inspect media attachments sent by that customer in the current thread.
  5. `escalate` — escalate the thread to `coo` (SomPong) and enqueue the holding line.
  6. `faq_read` — read-only lookup against approved MoonieX Care FAQ / playbook rules.
- Hard Denylist (§6.5):
  No `Bash`, no `Edit`/`Write`, no web fetch of customer links, no org tools
  (no task ledger writes, no session management, no direct CEO cards), no secrets
  (no Infisical, `.env`, `/proc`, `/etc`, or credential access), and no Phase 1
  partner data (`XM` / `Exness`).
- Operating hours (`08-22 TH`, `Asia/Bangkok`) and immediate acknowledgement texts (§6.2):
  In hours (`08:00–22:00 TH`):
    "ได้รับข้อความแล้วครับ แอดมินจะตอบภายใน 1 ชั่วโมง (เวลาทำการ 08:00–22:00 น.)"
  Outside hours (before `08:00` or at/after `22:00` TH; never promises within 1 hour):
    "ได้รับข้อความแล้วครับ แอดมินจะเริ่มตอบตั้งแต่ 08:00 น. นะครับ"

Offline, stdlib-first module: makes no live LINE or winbox calls and holds no secrets.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "config" / "care_p1.yaml"

TH_TZ = timezone(timedelta(hours=7), name="Asia/Bangkok")

DEFAULT_BASIC_ID = "@587kfqpt"
DEFAULT_CHANNEL_NAME = "@mooniex"
DEFAULT_DISPLAY_NAME = "MoonieX Officials"

DAY_ACK_TEXT = "ได้รับข้อความแล้วครับ แอดมินจะตอบภายใน 1 ชั่วโมง (เวลาทำการ 08:00–22:00 น.)"
NIGHT_ACK_TEXT = "ได้รับข้อความแล้วครับ แอดมินจะเริ่มตอบตั้งแต่ 08:00 น. นะครับ"
HOLDING_TEXT = "ขอเช็คให้ก่อนนะครับ"

ALLOWED_TOOLS: tuple[str, ...] = (
    "reply",
    "skip",
    "history",
    "media",
    "escalate",
    "faq_read",
)

FORBIDDEN_CATEGORIES: tuple[str, ...] = (
    "bash",
    "edit",
    "web_fetch",
    "org_tools",
    "secrets",
    "partner_data",
)

MAX_BUBBLES_PER_REPLY = 5
ACTIVE_ENV = "MOONIEX_CARE_SESSION"

# Canonical mapping from tool names (bare or MCP-prefixed) to the 6 allowlisted actions.
_CANONICAL_ALLOWED_MAP: dict[str, str] = {
    "reply": "reply",
    "care_reply": "reply",
    "mcp__care__reply": "reply",
    "mcp__sompong__reply": "reply",
    "skip": "skip",
    "care_skip": "skip",
    "mcp__care__skip": "skip",
    "mcp__sompong__skip": "skip",
    "history": "history",
    "care_history": "history",
    "mcp__care__history": "history",
    "mcp__sompong__history": "history",
    "media": "media",
    "care_media": "media",
    "mcp__care__media": "media",
    "mcp__sompong__media": "media",
    "escalate": "escalate",
    "care_escalate": "escalate",
    "mcp__care__escalate": "escalate",
    "mcp__sompong__escalate": "escalate",
    "faq_read": "faq_read",
    "care_faq_read": "faq_read",
    "faq_lookup": "faq_read",
    "faq_search": "faq_read",
    "faq_get": "faq_read",
    "mcp__care__faq_read": "faq_read",
    "mcp__care__faq_lookup": "faq_read",
    "mcp__care__faq_search": "faq_read",
    "mcp__care__faq_get": "faq_read",
}

_BASH_TOOLS = frozenset({
    "bash",
    "sh",
    "zsh",
    "shell",
    "exec",
    "execute",
    "run_command",
    "run_terminal_cmd",
    "terminal",
    "cmd",
    "powershell",
    "subprocess",
})

_EDIT_TOOLS = frozenset({
    "edit",
    "write",
    "multiedit",
    "notebookedit",
    "write_file",
    "edit_file",
    "create_file",
    "delete_file",
    "remove_file",
    "apply_patch",
    "patch",
    "faq_write",
    "faq_update",
    "faq_delete",
    "mcp__care__faq_write",
    "mcp__care__faq_update",
    "mcp__care__faq_delete",
})

_WEB_FETCH_TOOLS = frozenset({
    "webfetch",
    "websearch",
    "web_fetch",
    "web_search",
    "fetch",
    "fetch_url",
    "read_url",
    "http_get",
    "http_post",
    "curl",
    "browser",
    "browse",
})

_ORG_TOOLS = frozenset({
    "create_task",
    "delegate_task",
    "delegate",
    "merge_task",
    "close_task",
    "get_task",
    "list_tasks",
    "wait_task",
    "send_to_cxo",
    "send_to_cto",
    "send_to_worker",
    "send_to_agy",
    "ask_ceo",
    "ask_run",
    "ask_run_wait",
    "respawn_clevel",
    "respawn_status",
    "portfolio",
    "order_take",
    "order_close",
    "session_open",
    "session_close",
    "session_save",
    "session_restart",
    "session_merge",
    "spawn_ph",
    "spawn_coo",
    "agent",
    "skill",
    "croncreate",
    "cronelete",
    "mcp__sompong__ask_ceo",
    "mcp__sompong__send",
    "mcp__sompong__drive_share",
})

_SECRET_TOOLS = frozenset({
    "infisical",
    "get_secret",
    "read_secret",
    "list_secrets",
    "set_secret",
    "secret_fetch",
    "secret_card",
    "secret_inventory",
    "copy_secret",
    "printenv",
    "env",
})

_PARTNER_TOOLS = frozenset({
    "partner_lookup",
    "partner_accounts",
    "partner_volume",
    "partner_summary",
    "partner_check",
    "xm_lookup",
    "xm_partner",
    "exness_lookup",
    "exness_partner",
})

SENSITIVE_PATH_PREFIXES: tuple[str, ...] = (
    "/etc/sompong",
    "/etc/mooniex",
    "/etc/infisical",
    "/etc/shadow",
    "/etc/passwd",
    "/root/.claude",
    "/root/.ssh",
    "/root/.config",
    "/proc",
    "/sys",
    "/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow",
    os.path.expanduser("~/.claude"),
    os.path.expanduser("~/.ssh"),
    os.path.expanduser("~/.config/mooniex"),
    os.path.expanduser("~/.config/infisical"),
    str(ROOT / "state"),
)

SENSITIVE_FILENAME_RE = re.compile(
    r"(^|/)(\.env($|\.[^/]*)|\.netrc|id_rsa|id_ed25519|\.git-credentials|"
    r"credentials[^/]*|.*secret[^/]*|.*\.token|.*\.pem|.*\.key|inbox\.db|tasks\.db)$",
    re.IGNORECASE,
)

SECRET_VALUE_RE = re.compile(
    r"(Bearer\s+[A-Za-z0-9._\-+/=]{12,}|"
    r"\bghp_[A-Za-z0-9]{20,}\b|"
    r"\bglpat-[A-Za-z0-9\-_]{16,}\b|"
    r"\bsk-[A-Za-z0-9\-_]{20,}\b|"
    r"\bpostgres(?:ql)?://[^\s\"']+|"
    r"\bINFISICAL_TOKEN\b|"
    r"\bLINE_CHANNEL_ACCESS_TOKEN\b|"
    r"\bSOMPONG_EA_WAKE_KEY\b|"
    r"\bORG_DB_URL\b)",
    re.IGNORECASE,
)

# Content prohibitions in customer replies (design §6.5):
# - Never quote amounts owed
# - Never make rebate or payout promises
# - Never give investment advice
# - Never speak in the CEO's name beyond the approved FAQ
_PROHIBITED_REPLY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "prohibited_amount_owed",
        re.compile(
            r"(ยอดเงินค้างชำระ|ค้างจ่ายคุณอยู่|ติดหนี้คุณ|ยอดรีเบตค้างจ่าย\s*\d[\d,.]*\s*(บาท|ดอลลาร์|USD|\$)|"
            r"owe\s+you\s+\$?\d[\d,.]*)",
            re.IGNORECASE,
        ),
    ),
    (
        "prohibited_rebate_promise",
        re.compile(
            r"(สัญญาว่ารีเบตจะเข้า|รับรองว่าได้รีเบตแน่นอน|การันตีจ่ายรีเบต|ยืนยันว่าจะโอนเงินคืนให้ทันที|"
            r"guarantee\s+(?:your\s+)?(?:rebate|payout))",
            re.IGNORECASE,
        ),
    ),
    (
        "prohibited_investment_advice",
        re.compile(
            r"(แนะนำให้ซื้อขาย|แนะนำให้เปิดออเดอร์|ควรเข้า\s*(?:buy|sell)\s*ตอนนี้|การันตีกำไร|"
            r"guaranteed\s+profit|financial\s+advice:\s*(?:buy|sell))",
            re.IGNORECASE,
        ),
    ),
    (
        "prohibited_ceo_impersonation",
        re.compile(
            r"(ในนาม\s*CEO\s*ขอสั่ง|ผมคือ\s*CEO|CEO\s*ฝากมาบอกเป็นการส่วนตัวว่าอนุมัติ|"
            r"speaking\s+personally\s+as\s+the\s+CEO)",
            re.IGNORECASE,
        ),
    ),
)

CHANNEL_TAG_RE = re.compile(
    r"""^<channel\s+source=["'](?P<source>care|sompong)["'](?P<attrs>[^>]*)>(?P<body>[\s\S]*?)</channel>$""",
    re.MULTILINE,
)
ATTR_RE = re.compile(r"""\b([A-Za-z_][A-Za-z0-9_]*)=["']([^"']*)["']""")
CUSTOMER_ID_RE = re.compile(r"^[A-Za-z0-9_.:@\-]{1,128}$")


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Stdlib YAML subset loader preserving null/None, booleans, ints, strings, and inline JSON lists."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        stripped_comment = raw_line.strip()
        if not stripped_comment or stripped_comment.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, sep, rest = raw_line.strip().partition(":")
        if not sep:
            continue
        val_str = rest.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if val_str == "":
            child: dict[str, Any] = {}
            parent[key.strip()] = child
            stack.append((indent, child))
        else:
            parent[key.strip()] = _parse_yaml_scalar(val_str)
    return root


def _parse_yaml_scalar(val_str: str) -> Any:
    if not (val_str.startswith('"') or val_str.startswith("'")):
        val_str = val_str.split("#", 1)[0].strip()
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


def load_care_p1_config(path: Optional[Path] = None) -> dict[str, Any]:
    """Load config/care_p1.yaml preserving null (None) placeholders."""
    cfg_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    text = cfg_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass
    return _parse_simple_yaml(text)


@dataclass(frozen=True)
class CareP1Config:
    role: str = "care"
    persona: str = "น้องมูน"
    persona_en: str = "Moon"
    model: str = "claude-sonnet-5-5"
    supervisor_role: str = "coo"
    channel_basic_id: str = DEFAULT_BASIC_ID
    channel_name: str = DEFAULT_CHANNEL_NAME
    channel_display_name: str = DEFAULT_DISPLAY_NAME
    timezone: str = "Asia/Bangkok"
    hours_window: str = "08-22 TH"
    start_hour_th: int = 8
    end_hour_th: int = 22
    day_ack_text: str = DAY_ACK_TEXT
    night_ack_text: str = NIGHT_ACK_TEXT
    holding_text: str = HOLDING_TEXT
    quiet_hours_window: Optional[int] = None
    max_bubbles_per_reply: int = MAX_BUBBLES_PER_REPLY
    allowed_tools: tuple[str, ...] = ALLOWED_TOOLS
    forbidden_categories: tuple[str, ...] = FORBIDDEN_CATEGORIES
    ceo_card_ranked_choices: int = 3
    digest_hour_th: int = 21
    lunar_cutover_only_after_care_live: bool = True
    active_case_live_turn_minutes: Optional[int] = None
    push_quota_counting_mode: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "CareP1Config":
        hours = d.get("hours") if isinstance(d.get("hours"), Mapping) else {}
        ack = d.get("ack") if isinstance(d.get("ack"), Mapping) else {}
        esc = d.get("escalation") if isinstance(d.get("escalation"), Mapping) else {}
        digest = d.get("digest") if isinstance(d.get("digest"), Mapping) else {}
        gate = d.get("gate") if isinstance(d.get("gate"), Mapping) else {}

        day_text = str(
            ack.get("day_text")
            or ack.get("in_hours_text")
            or d.get("day_ack_text")
            or DAY_ACK_TEXT
        )
        night_text = str(
            ack.get("night_text")
            or ack.get("outside_hours_text")
            or d.get("night_ack_text")
            or NIGHT_ACK_TEXT
        )
        holding = str(
            esc.get("holding_text")
            or ack.get("holding_text")
            or d.get("holding_text")
            or HOLDING_TEXT
        )
        quiet_win = ack.get("quiet_hours_window")
        live_min = d.get("active_case_live_turn_minutes")
        allowed_raw = gate.get("allowed_tools")
        forbidden_raw = gate.get("forbidden_categories")

        return cls(
            role=str(d.get("role") or "care"),
            persona=str(d.get("persona") or "น้องมูน"),
            persona_en=str(d.get("persona_en") or "Moon"),
            model=str(d.get("model") or "claude-sonnet-5-5"),
            supervisor_role=str(d.get("supervisor_role") or esc.get("target_role") or "coo"),
            channel_basic_id=str(d.get("channel_basic_id") or DEFAULT_BASIC_ID),
            channel_name=str(d.get("channel_name") or DEFAULT_CHANNEL_NAME),
            channel_display_name=str(d.get("channel_display_name") or DEFAULT_DISPLAY_NAME),
            timezone=str(hours.get("timezone") or d.get("timezone") or "Asia/Bangkok"),
            hours_window=str(hours.get("window") or d.get("hours_window") or "08-22 TH"),
            start_hour_th=int(hours.get("start_hour", d.get("start_hour_th", 8))),
            end_hour_th=int(hours.get("end_hour", d.get("end_hour_th", 22))),
            day_ack_text=day_text,
            night_ack_text=night_text,
            holding_text=holding,
            quiet_hours_window=int(quiet_win) if quiet_win is not None else None,
            max_bubbles_per_reply=int(
                gate.get("max_bubbles_per_reply", d.get("max_bubbles_per_call", MAX_BUBBLES_PER_REPLY))
            ),
            allowed_tools=tuple(str(x) for x in allowed_raw) if isinstance(allowed_raw, (list, tuple)) else ALLOWED_TOOLS,
            forbidden_categories=(
                tuple(str(x) for x in forbidden_raw)
                if isinstance(forbidden_raw, (list, tuple))
                else FORBIDDEN_CATEGORIES
            ),
            ceo_card_ranked_choices=int(esc.get("ceo_card_ranked_choices", 3)),
            digest_hour_th=int(digest.get("hour_th", 21)),
            lunar_cutover_only_after_care_live=bool(
                d.get("lunar_cutover_only_after_care_live", True)
            ),
            active_case_live_turn_minutes=int(live_min) if live_min is not None else None,
            push_quota_counting_mode=(
                str(d["push_quota_counting_mode"])
                if d.get("push_quota_counting_mode") is not None
                else None
            ),
        )

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "CareP1Config":
        return cls.from_dict(load_care_p1_config(path))


def to_thai_time(dt: datetime) -> datetime:
    """Convert a datetime to Thailand local time (Asia/Bangkok, UTC+7). Naive datetimes are assumed TH."""
    if not isinstance(dt, datetime):
        raise TypeError("dt must be a datetime instance")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TH_TZ)
    return dt.astimezone(TH_TZ)


def is_operating_hours(dt: datetime, cfg: Optional[CareP1Config] = None) -> bool:
    """Return True during 08:00–22:00 TH (`start_hour_th <= hour < end_hour_th`), False outside hours."""
    c = cfg or CareP1Config()
    th = to_thai_time(dt)
    return c.start_hour_th <= th.hour < c.end_hour_th


def is_hourly_round_hour(hour_th: int, cfg: Optional[CareP1Config] = None) -> bool:
    """Hourly batch rounds fire on the hour from 08:00 through 22:00 TH inclusive (§6.2.3)."""
    c = cfg or CareP1Config()
    return c.start_hour_th <= int(hour_th) <= c.end_hour_th


def select_ack_text(dt: datetime, cfg: Optional[CareP1Config] = None) -> str:
    """Select the immediate webhook replyToken ack text for timestamp `dt` (design §6.2.2).

    - In hours (`08:00–22:00 TH`): promises a response within 1 hour during 08:00–22:00.
    - Outside hours (before `08:00` or at/after `22:00` TH): never promises "within 1 hour";
      uses the CEO-selected night text stating responses start at 08:00.
    """
    c = cfg or CareP1Config()
    if is_operating_hours(dt, c):
        return c.day_ack_text
    return c.night_ack_text


@dataclass(frozen=True)
class CareTurnContext:
    """Authenticated turn scope for a single active customer thread."""

    customer_id: str
    event_id: Optional[str] = None
    allowed_media_ids: Optional[frozenset[str]] = None
    allowed_faq_paths: tuple[str, ...] = ()
    max_bubbles_per_reply: int = MAX_BUBBLES_PER_REPLY

    @classmethod
    def from_turn_dict(cls, turn: Optional[Mapping[str, Any]]) -> Optional["CareTurnContext"]:
        if not isinstance(turn, Mapping):
            return None
        if turn.get("unreadable") or turn.get("forged"):
            return None

        customer_id = str(turn.get("customer_id") or turn.get("active_customer_id") or "").strip()
        event_id = str(turn.get("event_id") or "").strip() or None
        media_ids: set[str] = set()
        has_explicit_media_scope = False

        if "allowed_media_ids" in turn and turn["allowed_media_ids"] is not None:
            has_explicit_media_scope = True
            for mid in turn["allowed_media_ids"]:
                if isinstance(mid, str) and mid.strip():
                    media_ids.add(mid.strip())

        events = turn.get("events")
        if isinstance(events, Sequence) and not isinstance(events, (str, bytes)):
            event_customers: set[str] = set()
            for ev in events:
                if not isinstance(ev, Mapping):
                    return None
                cid = str(ev.get("customer_id") or ev.get("sender_id") or ev.get("target") or "").strip()
                if not cid:
                    return None
                event_customers.add(cid)
                if not event_id and ev.get("event_id"):
                    event_id = str(ev["event_id"]).strip()
                if "media" in ev and isinstance(ev["media"], Sequence):
                    has_explicit_media_scope = True
                    for item in ev["media"]:
                        if isinstance(item, Mapping):
                            mid = str(item.get("message_id") or item.get("media_id") or "").strip()
                            if mid:
                                media_ids.add(mid)
                        elif isinstance(item, str) and item.strip():
                            media_ids.add(item.strip())
            if not customer_id:
                if len(event_customers) == 1:
                    customer_id = next(iter(event_customers))
                else:
                    # Ambiguous multi-customer turn without explicit active_customer_id fails closed
                    return None
            elif event_customers and customer_id not in event_customers:
                return None

        if not customer_id or not CUSTOMER_ID_RE.match(customer_id):
            return None

        faq_paths_raw = turn.get("allowed_faq_paths") or ()
        faq_paths = (
            tuple(str(p) for p in faq_paths_raw if isinstance(p, (str, Path)) and str(p).strip())
            if isinstance(faq_paths_raw, (list, tuple, set, frozenset))
            else ()
        )
        max_bubbles = int(turn.get("max_bubbles_per_reply") or MAX_BUBBLES_PER_REPLY)

        return cls(
            customer_id=customer_id,
            event_id=event_id,
            allowed_media_ids=frozenset(media_ids) if has_explicit_media_scope else None,
            allowed_faq_paths=faq_paths,
            max_bubbles_per_reply=max_bubbles,
        )


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    decision: str  # "allow" | "deny"
    reason: str
    tool: str = ""
    category: str = ""

    def to_hook_output(self) -> dict[str, Any]:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow" if self.allowed else "deny",
                "permissionDecisionReason": self.reason,
            }
        }


def _allow(tool: str, reason: str, category: str = "allowlist") -> GateDecision:
    return GateDecision(allowed=True, decision="allow", reason=reason, tool=tool, category=category)


def _deny(tool: str, reason: str, category: str) -> GateDecision:
    return GateDecision(allowed=False, decision="deny", reason=reason, tool=tool, category=category)


def _norm_path(path: str, cwd: str = "") -> str:
    expanded = os.path.expanduser(path.strip())
    if not os.path.isabs(expanded):
        base = cwd.strip() if cwd and cwd.strip() else str(ROOT)
        expanded = os.path.join(base, expanded)
    return os.path.realpath(expanded)


def is_sensitive_path(path: str, cwd: str = "") -> bool:
    """Return True if `path` points to or traverses into any secret, credential, or state path."""
    if not path or not path.strip():
        return True
    raw = path.strip()
    if SENSITIVE_FILENAME_RE.search(raw):
        return True
    resolved = _norm_path(raw, cwd)
    if SENSITIVE_FILENAME_RE.search(resolved):
        return True
    for prefix in SENSITIVE_PATH_PREFIXES:
        base = os.path.realpath(prefix)
        if resolved == base or resolved.startswith(base + os.sep):
            return True
    return False


def _is_within_allowed_faq(path: str, allowed_faq_paths: Sequence[str], cwd: str = "") -> bool:
    if not path or not path.strip() or not allowed_faq_paths:
        return False
    if is_sensitive_path(path, cwd):
        return False
    resolved = _norm_path(path, cwd)
    for allowed in allowed_faq_paths:
        base = _norm_path(str(allowed), cwd)
        if is_sensitive_path(base, cwd):
            continue
        if resolved == base or resolved.startswith(base + os.sep):
            return True
    return False


def _input_contains_secret_reference(tool_input: Mapping[str, Any], cwd: str = "") -> Optional[str]:
    """Inspect tool arguments for secret paths, environment variable dumps, or raw tokens."""
    for key, val in tool_input.items():
        k_low = str(key).lower()
        if k_low in ("secret", "secret_key", "infisical_token", "api_key", "access_token", "channel_token"):
            return f"secret_argument_forbidden:{k_low}"
        if isinstance(val, str):
            if SECRET_VALUE_RE.search(val):
                return "secret_value_detected"
            if k_low in ("path", "file_path", "filepath", "file", "dir", "directory", "target_path"):
                if is_sensitive_path(val, cwd):
                    return "sensitive_path_forbidden"
            elif any(
                tok in val
                for tok in (
                    "/etc/infisical",
                    "/etc/sompong",
                    "/etc/mooniex",
                    "/proc/",
                    ".env",
                    "state/inbox.db",
                    "state/tasks.db",
                )
            ):
                return "sensitive_path_reference_forbidden"
    return None


def classify_forbidden_tool(tool_name: str) -> Optional[str]:
    """Return the forbidden category name if `tool_name` is on the hard denylist, else None."""
    name = (tool_name or "").strip()
    low = name.lower()
    bare = low.rsplit("__", 1)[-1] if "__" in low else low

    if low in _BASH_TOOLS or bare in _BASH_TOOLS or "bash" in bare or "shell" in bare:
        return "bash"
    if low in _EDIT_TOOLS or bare in _EDIT_TOOLS or bare.startswith(("edit_", "write_", "delete_")):
        return "edit"
    if low in _WEB_FETCH_TOOLS or bare in _WEB_FETCH_TOOLS or bare.startswith(("web_", "http_", "fetch_")):
        return "web_fetch"
    if (
        low.startswith("mcp__infisical__")
        or low in _SECRET_TOOLS
        or bare in _SECRET_TOOLS
        or "infisical" in low
        or "secret" in bare
    ):
        return "secrets"
    if (
        low.startswith("mcp__sompong__partner_")
        or low.startswith("mcp__care__partner_")
        or low in _PARTNER_TOOLS
        or bare in _PARTNER_TOOLS
        or bare.startswith(("partner_", "xm_", "exness_"))
    ):
        return "partner_data"
    if (
        low.startswith("mcp__org__")
        or low.startswith("mcp__gmail__")
        or low.startswith("mcp__lungnote__")
        or re.match(r"^mcp__[a-z0-9_-]+__(mail|draft)_", low)
        or low in _ORG_TOOLS
        or bare in _ORG_TOOLS
    ):
        return "org_tools"
    return None


def validate_reply_bubbles(
    bubbles_or_text: Any,
    max_bubbles: int = MAX_BUBBLES_PER_REPLY,
) -> tuple[bool, str, list[str]]:
    """Validate outbound `reply` bubbles (1..5 plain-text items, no secrets, no prohibited promises)."""
    texts: list[str] = []
    if isinstance(bubbles_or_text, str):
        texts = [bubbles_or_text]
    elif isinstance(bubbles_or_text, Sequence) and not isinstance(bubbles_or_text, (bytes, bytearray)):
        for item in bubbles_or_text:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, Mapping):
                if item.get("type", "text") != "text":
                    return False, "reply_only_plain_text_allowed", []
                txt = item.get("text")
                if not isinstance(txt, str):
                    return False, "reply_bubble_missing_text", []
                texts.append(txt)
            else:
                return False, "reply_invalid_bubble_type", []
    else:
        return False, "reply_missing_content", []

    if not texts:
        return False, "reply_empty_bubbles", []
    if len(texts) > max_bubbles:
        return False, f"reply_exceeds_max_bubbles_{max_bubbles}", []

    cleaned: list[str] = []
    for txt in texts:
        stripped = txt.strip()
        if not stripped:
            return False, "reply_empty_bubble_text", []
        if SECRET_VALUE_RE.search(stripped):
            return False, "reply_contains_secret_or_token", []
        for reason_code, pattern in _PROHIBITED_REPLY_PATTERNS:
            if pattern.search(stripped):
                return False, f"reply_{reason_code}_must_escalate", []
        cleaned.append(stripped)

    return True, "ok", cleaned


def evaluate_tool(
    tool_name: str,
    tool_input: Optional[Mapping[str, Any]] = None,
    context: Optional[CareTurnContext] = None,
    cwd: str = "",
) -> GateDecision:
    """Evaluate a single tool call against the MoonieX Care P1 gate allowlist (§6.5)."""
    name = (tool_name or "").strip()
    if not name:
        return _deny("", "care gate: missing tool_name", "invalid_tool")

    args: Mapping[str, Any] = tool_input if isinstance(tool_input, Mapping) else {}

    # 1. Check hard denylist categories first (Bash, Edit/Write, web fetch, org tools, secrets, partner data).
    forbidden_cat = classify_forbidden_tool(name)
    if forbidden_cat is not None:
        return _deny(
            name,
            f"care gate: forbidden_{forbidden_cat} ({name} is not permitted in care session)",
            f"forbidden_{forbidden_cat}",
        )

    # 2. Check arguments for any secret path or secret value leak across all tools.
    secret_hit = _input_contains_secret_reference(args, cwd)
    if secret_hit is not None:
        return _deny(
            name,
            f"care gate: forbidden_secrets ({secret_hit})",
            "forbidden_secrets",
        )

    # 3. Special case for Claude Code `Read`: denied unless reading an explicitly allowlisted FAQ path.
    if name in ("Read", "read_file"):
        file_path = str(args.get("file_path") or args.get("path") or "").strip()
        if not file_path or is_sensitive_path(file_path, cwd):
            return _deny(
                name,
                "care gate: forbidden_secrets (cannot read sensitive or arbitrary files)",
                "forbidden_secrets",
            )
        if context is not None and _is_within_allowed_faq(file_path, context.allowed_faq_paths, cwd):
            return _allow("faq_read", "care gate: read-only FAQ file allowed", "faq_read")
        return _deny(
            name,
            "care gate: arbitrary file Read is denied; only faq_read on approved FAQ is allowed",
            "tool_not_in_allowlist",
        )

    if name in ("Grep", "Glob"):
        return _deny(
            name,
            f"care gate: {name} is denied in care session; use faq_read",
            "tool_not_in_allowlist",
        )

    # 4. Resolve tool against the 6-tool allowlist.
    canonical = _CANONICAL_ALLOWED_MAP.get(name.lower())
    if canonical is None:
        return _deny(
            name,
            f"care gate: tool '{name}' is not in the care allowlist ({', '.join(ALLOWED_TOOLS)})",
            "tool_not_in_allowlist",
        )

    # 5. Fail closed if turn context (customer_id) is missing or invalid.
    if context is None or not context.customer_id or not CUSTOMER_ID_RE.match(context.customer_id):
        return _deny(
            canonical,
            "care gate: missing or unverified customer turn context (fail closed)",
            "missing_turn_context",
        )

    active_cid = context.customer_id

    # --- Tool 1: reply ---
    if canonical == "reply":
        target_cid = str(
            args.get("customer_id") or args.get("recipient_id") or args.get("target") or active_cid
        ).strip()
        if target_cid != active_cid:
            return _deny(
                "reply",
                f"care gate: cross_customer_reply_denied (active={active_cid}, requested={target_cid})",
                "cross_customer_denied",
            )
        if context.event_id and args.get("event_id") is not None:
            if str(args.get("event_id")).strip() != context.event_id:
                return _deny(
                    "reply",
                    "care gate: reply event_id does not match active turn event_id",
                    "cross_event_denied",
                )
        raw_content = (
            args.get("bubbles")
            if "bubbles" in args
            else (args.get("messages") if "messages" in args else args.get("text"))
        )
        ok, reason, _ = validate_reply_bubbles(raw_content, max_bubbles=context.max_bubbles_per_reply)
        if not ok:
            return _deny("reply", f"care gate: {reason}", reason)
        return _allow("reply", f"care gate: reply allowed for customer {active_cid}", "reply")

    # --- Tool 2: skip ---
    if canonical == "skip":
        target_cid = str(args.get("customer_id") or args.get("target") or active_cid).strip()
        if target_cid != active_cid:
            return _deny(
                "skip",
                f"care gate: cross_customer_skip_denied (active={active_cid}, requested={target_cid})",
                "cross_customer_denied",
            )
        if context.event_id and args.get("event_id") is not None:
            if str(args.get("event_id")).strip() != context.event_id:
                return _deny(
                    "skip",
                    "care gate: skip event_id does not match active turn event_id",
                    "cross_event_denied",
                )
        return _allow("skip", f"care gate: skip allowed for customer {active_cid}", "skip")

    # --- Tool 3: history (strictly for THAT customer only) ---
    if canonical == "history":
        req_cid = str(
            args.get("customer_id") or args.get("target") or args.get("recipient_id") or ""
        ).strip()
        if not req_cid:
            return _deny(
                "history",
                "care gate: history requires explicit customer_id matching the active customer",
                "missing_customer_id",
            )
        if req_cid in ("*", "all", "ANY") or req_cid != active_cid:
            return _deny(
                "history",
                f"care gate: cross_customer_history_denied (active={active_cid}, requested={req_cid})",
                "cross_customer_denied",
            )
        return _allow("history", f"care gate: history allowed for active customer {active_cid}", "history")

    # --- Tool 4: media (attachments sent by that customer in the current thread) ---
    if canonical == "media":
        req_cid = str(args.get("customer_id") or args.get("target") or active_cid).strip()
        if req_cid != active_cid:
            return _deny(
                "media",
                f"care gate: cross_customer_media_denied (active={active_cid}, requested={req_cid})",
                "cross_customer_denied",
            )
        media_id = str(args.get("message_id") or args.get("media_id") or "").strip()
        if not media_id:
            return _deny("media", "care gate: media requires message_id or media_id", "missing_media_id")
        if "/" in media_id or ".." in media_id or "\\" in media_id:
            return _deny("media", "care gate: invalid media_id path traversal", "invalid_media_id")
        if context.allowed_media_ids is not None and media_id not in context.allowed_media_ids:
            return _deny(
                "media",
                f"care gate: media_id '{media_id}' does not belong to active customer thread",
                "cross_customer_media_denied",
            )
        return _allow("media", f"care gate: media allowed for customer {active_cid}", "media")

    # --- Tool 5: escalate (to coo SomPong + holding line) ---
    if canonical == "escalate":
        req_cid = str(args.get("customer_id") or args.get("target") or active_cid).strip()
        if req_cid != active_cid:
            return _deny(
                "escalate",
                f"care gate: cross_customer_escalate_denied (active={active_cid}, requested={req_cid})",
                "cross_customer_denied",
            )
        to_role = str(args.get("to") or args.get("target_role") or "coo").strip().lower()
        if to_role != "coo":
            return _deny(
                "escalate",
                f"care gate: care may escalate only to 'coo' (SomPong), never directly to '{to_role}'",
                "invalid_escalation_target",
            )
        return _allow("escalate", f"care gate: escalate to coo allowed for customer {active_cid}", "escalate")

    # --- Tool 6: faq_read (read-only lookup against approved FAQ / playbook rules) ---
    if canonical == "faq_read":
        for write_key in ("write", "update", "delete", "content", "new_rule", "overwrite"):
            if write_key in args and args[write_key] not in (None, False, ""):
                return _deny(
                    "faq_read",
                    "care gate: faq_read is strictly read-only; FAQ mutations are denied",
                    "forbidden_edit",
                )
        faq_path = str(args.get("path") or args.get("file_path") or "").strip()
        if faq_path:
            if ".." in Path(faq_path).parts or is_sensitive_path(faq_path, cwd):
                return _deny(
                    "faq_read",
                    "care gate: faq_read path traversal or sensitive path denied",
                    "forbidden_secrets",
                )
            if context.allowed_faq_paths and not _is_within_allowed_faq(
                faq_path, context.allowed_faq_paths, cwd
            ):
                return _deny(
                    "faq_read",
                    "care gate: faq_read path is outside approved FAQ locations",
                    "faq_path_outside_allowlist",
                )
        return _allow("faq_read", "care gate: read-only FAQ lookup allowed", "faq_read")

    return _deny(name, "care gate: tool not in allowlist", "tool_not_in_allowlist")


def extract_care_events(prompt: str) -> tuple[list[dict[str, str]], bool]:
    """Parse top-level `<channel source="care" ...>` tags without trusting embedded customer text.

    Returns `(events, unreadable)`. Any malformed `<channel` tag at top level marks `unreadable=True`
    so the gate fails closed. Forged `<channel>` tags injected inside customer message bodies are
    ignored or flagged as untrusted data.
    """
    events: list[dict[str, str]] = []
    for match in CHANNEL_TAG_RE.finditer(prompt or ""):
        attrs_raw = match.group("attrs") or ""
        attrs = {k: v for k, v in ATTR_RE.findall(attrs_raw)}
        cid = (attrs.get("customer_id") or attrs.get("sender_id") or attrs.get("target") or "").strip()
        ev_id = (attrs.get("event_id") or "").strip()
        if not cid or not CUSTOMER_ID_RE.match(cid):
            return [], True
        # Note: role is NEVER trusted from customer text; care channel events are always untrusted customer data.
        events.append({
            "customer_id": cid,
            "event_id": ev_id,
            "role": "customer",
        })

    has_channel_open = "<channel" in (prompt or "").lower()
    if has_channel_open and not events:
        return [], True
    return events, False


def decide_care(
    tool_name: str,
    tool_input: Optional[Mapping[str, Any]],
    turn: Optional[Mapping[str, Any]],
    cwd: str = "",
) -> dict[str, Any]:
    """Return a Claude Code `PreToolUse` hook decision dictionary (`allow` or `deny`, never `ask`)."""
    ctx = CareTurnContext.from_turn_dict(turn)
    decision = evaluate_tool(tool_name, tool_input, ctx, cwd=cwd)
    return decision.to_hook_output()


class CareGate:
    """High-level MoonieX Care P1 gate binding `config/care_p1.yaml` and turn evaluation."""

    def __init__(self, cfg: Optional[CareP1Config] = None, config_path: Optional[Path] = None):
        self.cfg = cfg if cfg is not None else CareP1Config.load(config_path)

    def is_operating_hours(self, dt: datetime) -> bool:
        return is_operating_hours(dt, self.cfg)

    def select_ack_text(self, dt: datetime) -> str:
        return select_ack_text(dt, self.cfg)

    def evaluate(
        self,
        tool_name: str,
        tool_input: Optional[Mapping[str, Any]] = None,
        *,
        customer_id: Optional[str] = None,
        context: Optional[CareTurnContext] = None,
        cwd: str = "",
    ) -> GateDecision:
        ctx = context
        if ctx is None and customer_id:
            ctx = CareTurnContext(
                customer_id=customer_id,
                max_bubbles_per_reply=self.cfg.max_bubbles_per_reply,
            )
        return evaluate_tool(tool_name, tool_input, ctx, cwd=cwd)

    def build_escalation_action(self, customer_id: str, reason: str, event_id: Optional[str] = None) -> dict[str, Any]:
        """Build the P1 escalation payload to `coo` (SomPong) with the customer holding reply (§6.3)."""
        if not customer_id or not CUSTOMER_ID_RE.match(customer_id):
            raise ValueError("valid customer_id required for escalation")
        return {
            "customer_id": customer_id,
            "event_id": event_id,
            "target_role": self.cfg.supervisor_role,
            "holding_text": self.cfg.holding_text,
            "ceo_card_ranked_choices": self.cfg.ceo_card_ranked_choices,
            "reason": reason.strip(),
        }


def run_pretool(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Process a Claude Code `PreToolUse` JSON payload and return the hook output dict."""
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), Mapping) else {}
    cwd = str(payload.get("cwd") or "")
    turn = payload.get("turn") if isinstance(payload.get("turn"), Mapping) else None
    if turn is None and payload.get("customer_id"):
        turn = {
            "customer_id": payload.get("customer_id"),
            "event_id": payload.get("event_id"),
            "allowed_media_ids": payload.get("allowed_media_ids"),
            "allowed_faq_paths": payload.get("allowed_faq_paths"),
        }
    return decide_care(tool_name, tool_input, turn, cwd=cwd)


def main(argv: Sequence[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "pretool"
    if mode == "ack":
        ts_arg = argv[2] if len(argv) > 2 else datetime.now(TH_TZ).isoformat()
        dt = datetime.fromisoformat(ts_arg)
        cfg = CareP1Config.load()
        print(select_ack_text(dt, cfg))
        return 0
    if mode == "pretool":
        if os.environ.get(ACTIVE_ENV, "1") != "1":
            return 0
        try:
            raw = sys.stdin.read() or "{}"
            payload = json.loads(raw)
        except ValueError:
            payload = {}
        if not isinstance(payload, Mapping):
            payload = {}
        out = run_pretool(payload)
        print(json.dumps(out, ensure_ascii=False))
        return 0
    print("usage: care_gate.py pretool|ack [ISO_TIMESTAMP]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
