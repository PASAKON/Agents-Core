"""MoonieX Care P1: inbound `care_queue`, instant ack via free replyToken once per
thread per N quiet hours, hourly batch timer (08:00-22:00 TH) grouping one wake
event per customer thread, per-customer goal/step persistence, and 21:00 TH digest
(docs/design/mooniex-care.md §6, docs/plans/2026-11-19-mooniex-care-team.md §2-§4 P1).

All customer text is treated strictly as untrusted data: no LLM runs at webhook
ingestion, and any channel/system markup in customer text is neutralized before
building wake events or history.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional, Sequence
from zoneinfo import ZoneInfo

from .outbox import DEFAULT_BASIC_ID, Outbox, _iso, _now, make_idempotency_key
from .sender import CareSender

BANGKOK = ZoneInfo("Asia/Bangkok")

DAY_ACK_TEXT = "ได้รับข้อความแล้วครับ แอดมินจะตอบภายใน 1 ชั่วโมง (เวลาทำการ 08:00–22:00 น.)"
NIGHT_ACK_TEXT = "ได้รับข้อความแล้วครับ แอดมินจะเริ่มตอบตั้งแต่ 08:00 น. นะครับ"
HOLDING_TEXT = "ขอเช็คให้ก่อนนะครับ"

DEFAULT_ACK_QUIET_HOURS = 4.0
DEFAULT_BATCH_HOURS_TH = (8, 22)
DEFAULT_DIGEST_HOUR_TH = 21
MAX_BUBBLES_PER_CALL = 5

QUEUE_STATES = ("pending", "batched", "answered", "skipped", "escalated")
CASE_STATUSES = ("active", "completed", "escalated", "closed")

CARE_P1_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS care_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  channel_basic_id TEXT NOT NULL DEFAULT '@587kfqpt',
  customer_id TEXT NOT NULL,
  customer_display_name TEXT NOT NULL DEFAULT '',
  text TEXT NOT NULL DEFAULT '',
  media_json TEXT NOT NULL DEFAULT '[]',
  reply_token TEXT,
  reply_token_expires_at TEXT,
  received_at TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending'
    CHECK (state IN ('pending','batched','answered','skipped','escalated')),
  batch_id TEXT,
  ack_outbox_id INTEGER,
  note TEXT,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS care_queue_state_idx ON care_queue (state, id);
CREATE INDEX IF NOT EXISTS care_queue_customer_idx ON care_queue (customer_id, id);

CREATE TABLE IF NOT EXISTS care_cases (
  customer_id TEXT PRIMARY KEY,
  customer_display_name TEXT NOT NULL DEFAULT '',
  goal TEXT NOT NULL,
  current_step TEXT NOT NULL,
  step_index INTEGER NOT NULL DEFAULT 1,
  case_status TEXT NOT NULL DEFAULT 'active'
    CHECK (case_status IN ('active','completed','escalated','closed')),
  source_rule_or_card_id TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS care_escalations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  customer_display_name TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL,
  reason TEXT NOT NULL,
  customer_text_json TEXT NOT NULL DEFAULT '[]',
  holding_outbox_id INTEGER,
  ranked_answers_json TEXT,
  ceo_card_id TEXT,
  ceo_choice TEXT,
  resolved_goal TEXT,
  resolved_faq_id INTEGER,
  state TEXT NOT NULL DEFAULT 'pending_coo'
    CHECK (state IN ('pending_coo','awaiting_ceo','resolved')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS care_faq (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_key TEXT NOT NULL UNIQUE,
  topic TEXT NOT NULL,
  question_pattern TEXT NOT NULL,
  approved_answer TEXT NOT NULL,
  goal_template TEXT,
  first_step_template TEXT,
  source_card_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

# Seeded baseline FAQ rules from .claude/skills/COO_Rules_MoonieXCare/SKILL.md (CEO 26-27 Nov 2026).
SEED_FAQ_RULES: tuple[dict[str, Optional[str]], ...] = (
    {
        "rule_key": "rebate_general_policy",
        "topic": "rebate",
        "question_pattern": "รีเบต|rebate|เงินคืน",
        "approved_answer": "เรามีรีเบตคืนให้ครับ สำหรับลูกค้าที่ลงทะเบียนภายใต้เครือข่าย MoonieX ครับ",
        "goal_template": "customer registers or confirms account under MoonieX network so rebate starts",
        "first_step_template": "ask customer for MT4/MT5 account ID to check registration under MoonieX",
        "source_card_id": "CEO-2026-11-27-COO_Rules_MoonieXCare-s1",
    },
    {
        "rule_key": "deposit_withdrawal_xm_support",
        "topic": "deposit_withdrawal",
        "question_pattern": "ฝากถอน|ฝากเงิน|ถอนเงิน|deposit|withdraw",
        "approved_answer": "ถ้าเป็นเรื่องการฝากถอน อาจจะต้องให้แอดมินของ XM ช่วยดูให้ครับ (Line: @xmsupport)",
        "goal_template": None,
        "first_step_template": None,
        "source_card_id": "CEO-2026-11-27-COO_Rules_MoonieXCare-s5",
    },
    {
        "rule_key": "out_of_scope_general",
        "topic": "scope",
        "question_pattern": "เรื่องอื่น|ไม่เกี่ยวกับเทรด",
        "approved_answer": "ผมดูแลเรื่องบัญชีเทรดและรีเบตของ MoonieX เป็นหลักครับ มีอะไรให้ช่วยเรื่องเทรดไหมครับ",
        "goal_template": None,
        "first_step_template": None,
        "source_card_id": "CEO-2026-11-27-COO_Rules_MoonieXCare-s5",
    },
)

_FORGED_TAG_RE = re.compile(
    r"<(\s*/?\s*(?:channel|system|task-notification|prompt|instructions)\b)",
    re.IGNORECASE,
)
_CTRL_ATTR_RE = re.compile(r"[\x00-\x1f\x7f\u2028\u2029]")


def neutralize_customer_text(text: str) -> str:
    """Neutralize channel/system tags and control bytes so customer text stays pure data."""
    cleaned = (text or "").replace("\x00", "")
    return _FORGED_TAG_RE.sub("\uff1c\\1", cleaned)


def _clean_attr(value: object, limit: int = 80) -> str:
    text = _CTRL_ATTR_RE.sub(" ", str(value or ""))
    text = text.replace('"', "'").replace("<", "(").replace(">", ")")
    return " ".join(text.split())[:limit]


@dataclass(frozen=True)
class CareP1Config:
    channel_basic_id: str = DEFAULT_BASIC_ID
    ack_quiet_hours: Optional[float] = None  # TBD null in config/care.yaml
    default_quiet_hours: float = DEFAULT_ACK_QUIET_HOURS
    active_case_live_window_seconds: Optional[int] = None  # TBD null in config/care.yaml
    batch_hours_th: tuple[int, int] = DEFAULT_BATCH_HOURS_TH
    digest_hour_th: int = DEFAULT_DIGEST_HOUR_TH
    max_bubbles_per_reply: int = MAX_BUBBLES_PER_CALL
    day_ack_text: str = DAY_ACK_TEXT
    night_ack_text: str = NIGHT_ACK_TEXT
    holding_text: str = HOLDING_TEXT

    @property
    def effective_quiet_hours(self) -> float:
        if self.ack_quiet_hours is not None:
            return max(0.0, float(self.ack_quiet_hours))
        return max(0.0, float(self.default_quiet_hours))

    @classmethod
    def from_dict(cls, d: dict) -> "CareP1Config":
        p1 = d.get("care_p1") or {}
        top_basic = d.get("channel_basic_id", DEFAULT_BASIC_ID)
        raw_quiet = p1.get("ack_quiet_hours")
        raw_live = p1.get("active_case_live_window_seconds")
        raw_hours = p1.get("batch_hours_th")
        if isinstance(raw_hours, (list, tuple)) and len(raw_hours) == 2:
            hours_th = (int(raw_hours[0]), int(raw_hours[1]))
        else:
            hours_th = DEFAULT_BATCH_HOURS_TH
        return cls(
            channel_basic_id=p1.get("channel_basic_id") or top_basic,
            ack_quiet_hours=float(raw_quiet) if raw_quiet is not None else None,
            active_case_live_window_seconds=int(raw_live) if raw_live is not None else None,
            batch_hours_th=hours_th,
            digest_hour_th=int(p1.get("digest_hour_th", DEFAULT_DIGEST_HOUR_TH)),
            max_bubbles_per_reply=int(p1.get("max_bubbles_per_reply", MAX_BUBBLES_PER_CALL)),
            day_ack_text=str(p1.get("day_ack_text") or DAY_ACK_TEXT),
            night_ack_text=str(p1.get("night_ack_text") or NIGHT_ACK_TEXT),
            holding_text=str(p1.get("holding_text") or HOLDING_TEXT),
        )


def is_within_operating_hours(
    dt: datetime,
    batch_hours_th: tuple[int, int] = DEFAULT_BATCH_HOURS_TH,
) -> bool:
    """True when `dt` in Asia/Bangkok is within 08:00–22:00 TH (not before 08:00, not after 22:00)."""
    th = dt.astimezone(BANGKOK)
    start_h, end_h = batch_hours_th
    cur = (th.hour, th.minute, th.second, th.microsecond)
    return (start_h, 0, 0, 0) <= cur <= (end_h, 0, 0, 0)


def select_ack_text(dt: datetime, cfg: CareP1Config = CareP1Config()) -> str:
    """Select day ack (08:00-22:00 TH) vs night ack (before 08:00 or after 22:00 TH, CEO Q-20261126-1837-cdec)."""
    if is_within_operating_hours(dt, cfg.batch_hours_th):
        return cfg.day_ack_text
    return cfg.night_ack_text


@dataclass(frozen=True)
class IngestResult:
    row_id: int
    created: bool
    ack_queued: bool
    ack_outbox_id: Optional[int] = None
    ack_text: Optional[str] = None
    ack_send_outcome: Optional[str] = None
    fallback_attached_outbox_id: Optional[int] = None
    active_case: bool = False
    live_turn_woke: bool = False


@dataclass(frozen=True)
class CareThreadEvent:
    event_id: str
    customer_id: str
    customer_display_name: str
    channel_basic_id: str
    queue_row_ids: tuple[int, ...]
    messages: tuple[dict[str, Any], ...]
    combined_text: str
    media: tuple[dict[str, Any], ...] = ()
    reply_token: Optional[str] = None
    reply_token_expires_at: Optional[str] = None
    active_case: Optional[dict[str, Any]] = None
    round_ts: str = ""
    channel_tag: str = ""

    def to_meta_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "platform": "line",
            "chat_type": "dm",
            "target": self.customer_id,
            "customer_id": self.customer_id,
            "customer_display_name": self.customer_display_name,
            "role": "customer",
            "queue_row_ids": list(self.queue_row_ids),
            "messages": list(self.messages),
            "media": list(self.media),
            "active_case": self.active_case,
        }


def build_thread_channel_tag(
    *,
    event_id: str,
    customer_id: str,
    customer_display_name: str,
    messages: Sequence[dict[str, Any]],
    active_case: Optional[dict[str, Any]] = None,
) -> str:
    """Render one customer thread event as a <channel source="care"> tag with neutralized data."""
    safe_eid = _clean_attr(event_id, 128)
    safe_cid = _clean_attr(customer_id, 128)
    safe_name = _clean_attr(customer_display_name or customer_id, 40)
    goal_attr = ""
    if active_case and active_case.get("case_status") == "active":
        g = _clean_attr(active_case.get("goal", ""), 80)
        s = _clean_attr(active_case.get("current_step", ""), 80)
        idx = int(active_case.get("step_index", 1))
        goal_attr = f' case_goal="{g}" case_step="{s}" case_step_index="{idx}"'
    lines = []
    for m in messages:
        txt = neutralize_customer_text(str(m.get("text") or ""))
        lines.append(txt if txt else "(media attachment)")
    body = "\n".join(lines)
    return (
        f'<channel source="care" event_id="{safe_eid}" platform="line" chat_type="dm" '
        f'target="{safe_cid}" customer_id="{safe_cid}" sender_name="{safe_name}" '
        f'role="customer" msg_count="{len(messages)}"{goal_attr}>'
        f"{body}</channel>"
    )


@dataclass(frozen=True)
class BatchRoundResult:
    ran: bool
    reason: str
    woke: bool
    events: tuple[CareThreadEvent, ...] = field(default_factory=tuple)


class CareQueue:
    """Inbound `care_queue` + instant ack + hourly batch timer (08:00-22:00 TH) + goal state."""

    def __init__(
        self,
        conn,
        outbox: Optional[Outbox] = None,
        sender: Optional[CareSender] = None,
        cfg: CareP1Config = CareP1Config(),
        clock: Callable[[], datetime] = _now,
        quiet_hours: Optional[float] = None,
        live_wake_callback: Optional[Callable[[CareThreadEvent], None]] = None,
    ):
        self.conn = conn
        self.clock = clock
        self.outbox = outbox if outbox is not None else Outbox(conn, clock=clock)
        self.sender = sender
        if quiet_hours is not None:
            cfg = CareP1Config(
                channel_basic_id=cfg.channel_basic_id,
                ack_quiet_hours=float(quiet_hours),
                default_quiet_hours=cfg.default_quiet_hours,
                active_case_live_window_seconds=cfg.active_case_live_window_seconds,
                batch_hours_th=cfg.batch_hours_th,
                digest_hour_th=cfg.digest_hour_th,
                max_bubbles_per_reply=cfg.max_bubbles_per_reply,
                day_ack_text=cfg.day_ack_text,
                night_ack_text=cfg.night_ack_text,
                holding_text=cfg.holding_text,
            )
        self.cfg = cfg
        self.live_wake_callback = live_wake_callback

    def init_schema(self) -> None:
        self.outbox.init_schema()
        self.conn.executescript(CARE_P1_SQLITE_SCHEMA)
        ts = self._ts()
        for rule in SEED_FAQ_RULES:
            self.conn.execute(
                "INSERT OR IGNORE INTO care_faq (rule_key, topic, question_pattern, approved_answer,"
                " goal_template, first_step_template, source_card_id, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    rule["rule_key"],
                    rule["topic"],
                    rule["question_pattern"],
                    rule["approved_answer"],
                    rule["goal_template"],
                    rule["first_step_template"],
                    rule["source_card_id"],
                    ts,
                    ts,
                ),
            )
        self.conn.commit()

    def _ts(self) -> str:
        return _iso(self.clock()) or datetime.now(timezone.utc).isoformat()

    def _ack_flag_key(self, customer_id: str, channel_basic_id: str) -> str:
        return f"ack_last:{channel_basic_id}:{customer_id}"

    def _last_ack_at(self, customer_id: str, channel_basic_id: str) -> Optional[datetime]:
        val = self.outbox.get_flag(self._ack_flag_key(customer_id, channel_basic_id))
        if not val:
            return None
        dt = datetime.fromisoformat(val)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    def _last_thread_message_at(self, customer_id: str, exclude_row_id: int) -> Optional[datetime]:
        row = self.conn.execute(
            "SELECT received_at FROM care_queue WHERE customer_id=? AND id<>? ORDER BY id DESC LIMIT 1",
            (customer_id, exclude_row_id),
        ).fetchone()
        if not row or not row[0]:
            return None
        dt = datetime.fromisoformat(row[0])
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    def _should_send_instant_ack(
        self,
        *,
        customer_id: str,
        channel_basic_id: str,
        row_id: int,
        now: datetime,
        has_reply_token: bool,
    ) -> bool:
        """Rate-limited to once per thread per N quiet hours, never once per message."""
        if not has_reply_token:
            return False
        window = timedelta(hours=self.cfg.effective_quiet_hours)
        last_ack = self._last_ack_at(customer_id, channel_basic_id)
        if last_ack is not None and (now - last_ack) < window:
            return False
        last_msg = self._last_thread_message_at(customer_id, exclude_row_id=row_id)
        if last_msg is not None and (now - last_msg) < window:
            return False
        return True

    def _attach_to_pending_fallback_row(
        self,
        customer_id: str,
        reply_token: str,
        reply_token_expires_at: Optional[datetime],
    ) -> Optional[int]:
        row = self.conn.execute(
            "SELECT id FROM care_outbox WHERE recipient_id=? AND state='fallback' ORDER BY id ASC LIMIT 1",
            (customer_id,),
        ).fetchone()
        if row is None:
            return None
        fid = int(row[0])
        if self.outbox.attach_reply_token(fid, reply_token, reply_token_expires_at):
            return fid
        return None

    def ingest(
        self,
        *,
        event_id: str,
        customer_id: str,
        customer_display_name: str = "",
        text: str = "",
        media: Optional[Sequence[dict[str, Any]]] = None,
        reply_token: Optional[str] = None,
        reply_token_expires_at: Optional[datetime] = None,
        received_at: Optional[datetime] = None,
        channel_basic_id: Optional[str] = None,
    ) -> IngestResult:
        """Record one inbound webhook message in `care_queue` (no LLM runs at ingest)
        and fire the free replyToken instant ack at most once per thread per N quiet hours."""
        if not event_id or not str(event_id).strip():
            raise ValueError("event_id is required")
        if not customer_id or not str(customer_id).strip():
            raise ValueError("customer_id is required")

        now = received_at.astimezone(timezone.utc) if received_at else self.clock()
        ts = _iso(now) or now.isoformat()
        ch = (channel_basic_id or self.cfg.channel_basic_id or DEFAULT_BASIC_ID).strip()
        disp = (customer_display_name or customer_id).strip()
        safe_text = neutralize_customer_text(text)
        media_list = list(media or [])

        cur = self.conn.execute(
            "INSERT OR IGNORE INTO care_queue (event_id, channel_basic_id, customer_id,"
            " customer_display_name, text, media_json, reply_token, reply_token_expires_at,"
            " received_at, state, updated_at) VALUES (?,?,?,?,?,?,?,?,?, 'pending', ?)",
            (
                event_id.strip(),
                ch,
                customer_id.strip(),
                disp,
                safe_text,
                json.dumps(media_list, ensure_ascii=False),
                reply_token,
                _iso(reply_token_expires_at),
                ts,
                ts,
            ),
        )
        created = cur.rowcount == 1
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM care_queue WHERE event_id=?",
            (event_id.strip(),),
        ).fetchone()
        row_id = int(row[0])

        if not created:
            return IngestResult(
                row_id=row_id,
                created=False,
                ack_queued=False,
                ack_send_outcome="duplicate",
            )

        active_case_dict = self.get_case(customer_id.strip())
        has_active_case = bool(active_case_dict and active_case_dict.get("case_status") == "active")

        ack_queued = False
        ack_outbox_id: Optional[int] = None
        ack_text: Optional[str] = None
        ack_outcome: Optional[str] = None
        fallback_attached_id: Optional[int] = None

        if self._should_send_instant_ack(
            customer_id=customer_id.strip(),
            channel_basic_id=ch,
            row_id=row_id,
            now=now,
            has_reply_token=bool(reply_token),
        ):
            ack_text = select_ack_text(now, self.cfg)
            ikey = make_idempotency_key(ch, customer_id.strip(), event_id.strip(), "instant_ack")
            ack_outbox_id, _ = self.outbox.enqueue(
                idempotency_key=ikey,
                recipient_id=customer_id.strip(),
                recipient_display_name=disp,
                message_kind="care_reply",
                payload=[{"type": "text", "text": ack_text}],
                reply_token=reply_token,
                reply_token_expires_at=reply_token_expires_at,
                channel_basic_id=ch,
            )
            ack_queued = True
            self.outbox.set_flag(self._ack_flag_key(customer_id.strip(), ch), ts)
            # Single-use replyToken is dedicated to the instant ack; clear it from the queue row
            # so a later batch reply does not attempt to reuse a spent token.
            self.conn.execute(
                "UPDATE care_queue SET ack_outbox_id=?, reply_token=NULL, updated_at=? WHERE id=?",
                (ack_outbox_id, ts, row_id),
            )
            self.conn.commit()
            if self.sender is not None:
                ack_outcome = self.sender.process(ack_outbox_id)
        elif reply_token:
            # If no instant ack fired (e.g. follow-up within N hours) and there is a fallback
            # outbox row waiting for a fresh webhook replyToken, attach it now.
            fallback_attached_id = self._attach_to_pending_fallback_row(
                customer_id.strip(), reply_token, reply_token_expires_at
            )

        live_woke = False
        if has_active_case and self.live_wake_callback is not None:
            batch_res = self.run_customer_live_turn(
                customer_id.strip(),
                now=now,
                wake_session=self.live_wake_callback,
            )
            live_woke = batch_res is not None

        return IngestResult(
            row_id=row_id,
            created=True,
            ack_queued=ack_queued,
            ack_outbox_id=ack_outbox_id,
            ack_text=ack_text,
            ack_send_outcome=ack_outcome,
            fallback_attached_outbox_id=fallback_attached_id,
            active_case=has_active_case,
            live_turn_woke=live_woke,
        )

    def get_queue_row(self, row_id: int) -> dict[str, Any]:
        cur = self.conn.execute("SELECT * FROM care_queue WHERE id=?", (row_id,))
        cols = [c[0] for c in cur.description]
        r = cur.fetchone()
        if r is None:
            raise KeyError(row_id)
        d = dict(zip(cols, r))
        d["media"] = json.loads(d.get("media_json") or "[]")
        return d

    def pending_rows(self) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM care_queue WHERE state='pending' ORDER BY id ASC"
        )
        cols = [c[0] for c in cur.description]
        out = []
        for r in cur.fetchall():
            d = dict(zip(cols, r))
            d["media"] = json.loads(d.get("media_json") or "[]")
            out.append(d)
        return out

    def _select_valid_unused_token(
        self,
        rows: Sequence[dict[str, Any]],
        now: datetime,
    ) -> tuple[Optional[str], Optional[str]]:
        for r in reversed(rows):
            tok = r.get("reply_token")
            if not tok:
                continue
            exp_str = r.get("reply_token_expires_at")
            if exp_str is not None:
                exp_dt = datetime.fromisoformat(exp_str)
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                if now >= exp_dt:
                    continue
            return tok, exp_str
        return None, None

    def _build_thread_event(
        self,
        customer_id: str,
        rows: Sequence[dict[str, Any]],
        now: datetime,
        prefix: str = "batch",
    ) -> CareThreadEvent:
        th_stamp = now.astimezone(BANGKOK).strftime("%Y%m%dT%H%M")
        first_id = rows[0]["id"]
        event_id = f"care-{prefix}-{th_stamp}-{customer_id}-{first_id}"
        disp = rows[-1].get("customer_display_name") or customer_id
        ch = rows[-1].get("channel_basic_id") or self.cfg.channel_basic_id
        messages = tuple(
            {
                "id": r["id"],
                "event_id": r["event_id"],
                "text": neutralize_customer_text(r.get("text") or ""),
                "media": list(r.get("media") or []),
                "received_at": r["received_at"],
            }
            for r in rows
        )
        media_items = tuple(
            item
            for r in rows
            for item in (r.get("media") or [])
        )
        combined = "\n".join(m["text"] for m in messages if m["text"])
        tok, exp_str = self._select_valid_unused_token(rows, now)
        case = self.get_case(customer_id)
        active_case = case if (case and case.get("case_status") == "active") else None
        tag = build_thread_channel_tag(
            event_id=event_id,
            customer_id=customer_id,
            customer_display_name=disp,
            messages=messages,
            active_case=active_case,
        )
        return CareThreadEvent(
            event_id=event_id,
            customer_id=customer_id,
            customer_display_name=disp,
            channel_basic_id=ch,
            queue_row_ids=tuple(int(r["id"]) for r in rows),
            messages=messages,
            combined_text=combined,
            media=media_items,
            reply_token=tok,
            reply_token_expires_at=exp_str,
            active_case=active_case,
            round_ts=_iso(now) or now.isoformat(),
            channel_tag=tag,
        )

    def run_hourly_batch(
        self,
        *,
        now: Optional[datetime] = None,
        wake_session: Optional[Callable[[list[CareThreadEvent]], None]] = None,
        force: bool = False,
    ) -> BatchRoundResult:
        """Run one hourly batch round (08:00-22:00 TH): wake `care` once with one
        grouped event per customer thread."""
        ts_dt = now.astimezone(timezone.utc) if now else self.clock()
        if not force and not is_within_operating_hours(ts_dt, self.cfg.batch_hours_th):
            return BatchRoundResult(
                ran=False,
                reason="outside_operating_hours",
                woke=False,
                events=(),
            )

        pending = self.pending_rows()
        if not pending:
            return BatchRoundResult(
                ran=True,
                reason="queue_empty",
                woke=False,
                events=(),
            )

        grouped: dict[str, list[dict[str, Any]]] = {}
        for r in pending:
            grouped.setdefault(r["customer_id"], []).append(r)

        ts_str = _iso(ts_dt) or ts_dt.isoformat()
        events: list[CareThreadEvent] = []
        for cid, rows in grouped.items():
            ev = self._build_thread_event(cid, rows, ts_dt, prefix="batch")
            marks = ",".join("?" * len(ev.queue_row_ids))
            self.conn.execute(
                f"UPDATE care_queue SET state='batched', batch_id=?, updated_at=?"
                f" WHERE id IN ({marks}) AND state='pending'",
                (ev.event_id, ts_str, *ev.queue_row_ids),
            )
            events.append(ev)
        self.conn.commit()

        if wake_session is not None:
            wake_session(list(events))

        return BatchRoundResult(
            ran=True,
            reason="woke_care",
            woke=True,
            events=tuple(events),
        )

    def run_customer_live_turn(
        self,
        customer_id: str,
        *,
        now: Optional[datetime] = None,
        wake_session: Optional[Callable[[CareThreadEvent], None]] = None,
    ) -> Optional[CareThreadEvent]:
        """Wake `care` for an active-case customer's live turn (design §6.2.4)."""
        case = self.get_case(customer_id)
        if not case or case.get("case_status") != "active":
            return None
        ts_dt = now.astimezone(timezone.utc) if now else self.clock()
        cur = self.conn.execute(
            "SELECT * FROM care_queue WHERE customer_id=? AND state='pending' ORDER BY id ASC",
            (customer_id,),
        )
        cols = [c[0] for c in cur.description]
        rows = []
        for r in cur.fetchall():
            d = dict(zip(cols, r))
            d["media"] = json.loads(d.get("media_json") or "[]")
            rows.append(d)
        if not rows:
            return None
        ev = self._build_thread_event(customer_id, rows, ts_dt, prefix="live")
        ts_str = _iso(ts_dt) or ts_dt.isoformat()
        marks = ",".join("?" * len(ev.queue_row_ids))
        self.conn.execute(
            f"UPDATE care_queue SET state='batched', batch_id=?, updated_at=?"
            f" WHERE id IN ({marks}) AND state='pending'",
            (ev.event_id, ts_str, *ev.queue_row_ids),
        )
        self.conn.commit()
        if wake_session is not None:
            wake_session(ev)
        return ev

    # -- Per-customer goal & step state (design §6.4) -------------------------

    def set_case(
        self,
        customer_id: str,
        goal: str,
        current_step: str,
        *,
        customer_display_name: str = "",
        step_index: int = 1,
        case_status: str = "active",
        source_rule_or_card_id: Optional[str] = None,
    ) -> dict[str, Any]:
        if case_status not in CASE_STATUSES:
            raise ValueError(f"bad case_status: {case_status}")
        if not goal or not goal.strip():
            raise ValueError("goal is required")
        if not current_step or not current_step.strip():
            raise ValueError("current_step is required")
        ts = self._ts()
        self.conn.execute(
            "INSERT INTO care_cases (customer_id, customer_display_name, goal, current_step,"
            " step_index, case_status, source_rule_or_card_id, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(customer_id) DO UPDATE SET"
            " customer_display_name=excluded.customer_display_name,"
            " goal=excluded.goal,"
            " current_step=excluded.current_step,"
            " step_index=excluded.step_index,"
            " case_status=excluded.case_status,"
            " source_rule_or_card_id=excluded.source_rule_or_card_id,"
            " updated_at=excluded.updated_at",
            (
                customer_id.strip(),
                customer_display_name.strip(),
                goal.strip(),
                current_step.strip(),
                int(step_index),
                case_status,
                source_rule_or_card_id,
                ts,
            ),
        )
        self.conn.commit()
        return self.get_case(customer_id.strip()) or {}

    def get_case(self, customer_id: str) -> Optional[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM care_cases WHERE customer_id=?",
            (customer_id.strip(),),
        )
        cols = [c[0] for c in cur.description]
        r = cur.fetchone()
        return dict(zip(cols, r)) if r is not None else None

    def advance_case_step(
        self,
        customer_id: str,
        next_step: str,
        *,
        completed: bool = False,
    ) -> Optional[dict[str, Any]]:
        existing = self.get_case(customer_id)
        if existing is None:
            return None
        new_status = "completed" if completed else "active"
        new_index = int(existing["step_index"]) + (0 if completed else 1)
        return self.set_case(
            customer_id,
            existing["goal"],
            next_step.strip() if next_step.strip() else existing["current_step"],
            customer_display_name=existing.get("customer_display_name", ""),
            step_index=new_index,
            case_status=new_status,
            source_rule_or_card_id=existing.get("source_rule_or_card_id"),
        )

    # -- Daily digest at 21:00 TH (design §6.7) -------------------------------

    def build_daily_digest(self, now: Optional[datetime] = None) -> dict[str, Any]:
        """Build the 21:00 TH daily digest for SomPong (`coo`)."""
        ts_dt = now.astimezone(BANGKOK) if now else self.clock().astimezone(BANGKOK)
        day_prefix = ts_dt.strftime("%Y-%m-%d")

        rows = self.conn.execute(
            "SELECT customer_id, state, text, received_at FROM care_queue ORDER BY id ASC"
        ).fetchall()

        threads_by_state: dict[str, set[str]] = {
            "answered": set(),
            "escalated": set(),
            "open": set(),
            "skipped": set(),
        }
        all_threads: set[str] = set()
        total_messages = 0
        questions: list[str] = []

        for cid, state, text, rec_at in rows:
            rec_th = datetime.fromisoformat(rec_at).astimezone(BANGKOK).strftime("%Y-%m-%d")
            if rec_th != day_prefix:
                continue
            total_messages += 1
            all_threads.add(cid)
            if state == "answered":
                threads_by_state["answered"].add(cid)
            elif state == "escalated":
                threads_by_state["escalated"].add(cid)
            elif state in ("pending", "batched"):
                threads_by_state["open"].add(cid)
            elif state == "skipped":
                threads_by_state["skipped"].add(cid)
            if text and text.strip():
                questions.append(text.strip()[:120])

        esc_rows = self.conn.execute(
            "SELECT category, reason, state FROM care_escalations ORDER BY id ASC"
        ).fetchall()
        candidate_faqs = [
            {"category": cat, "reason": reason, "state": st}
            for cat, reason, st in esc_rows
        ]

        return {
            "date_th": day_prefix,
            "total_threads": len(all_threads),
            "total_messages": total_messages,
            "answered_threads": len(threads_by_state["answered"]),
            "escalated_threads": len(threads_by_state["escalated"]),
            "open_threads": len(threads_by_state["open"]),
            "skipped_threads": len(threads_by_state["skipped"]),
            "top_questions": questions[:10],
            "candidate_faq_updates": candidate_faqs,
        }
