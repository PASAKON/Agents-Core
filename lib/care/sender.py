"""Sender abstraction: reply-token and push backends (S1; no browser sender).

The channel token is a PARAMETER (from the account store loader in prod, a
dummy in tests). It is placed only in the Authorization header handed to the
injected `http`; it is never logged, stored or put in an error string.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from .outbox import Outbox
from .quota import GateDecision, Http, QuotaConfig, decide_push, month_key, read_consumption

REPLY_URL = "https://api.line.me/v2/bot/message/reply"
PUSH_URL = "https://api.line.me/v2/bot/message/push"


class ReplyBackend:
    def __init__(self, http: Http, token: str):
        self._http, self._token = http, token

    def send(self, row: dict) -> tuple[int, dict]:
        body = {"replyToken": row["reply_token"], "messages": json.loads(row["payload_json"])}
        return self._http("POST", REPLY_URL, {"Authorization": f"Bearer {self._token}"}, body)


class PushBackend:
    def __init__(self, http: Http, token: str):
        self._http, self._token = http, token

    def send(self, row: dict) -> tuple[int, dict]:
        # Retry key lets LINE dedupe an ambiguous retry; stable per outbox row.
        retry_key = str(uuid.uuid5(uuid.NAMESPACE_URL, row["idempotency_key"]))
        headers = {"Authorization": f"Bearer {self._token}", "X-Line-Retry-Key": retry_key}
        body = {"to": row["recipient_id"], "messages": json.loads(row["payload_json"])}
        return self._http("POST", PUSH_URL, headers, body)


class CareSender:
    """Routes one outbox row: reply while token valid, push only for important
    announcements after expiry, else defer for the S2 browser sender."""

    def __init__(self, outbox: Outbox, http: Http, token: str, cfg: QuotaConfig,
                 alert_coo: Callable[[str], None] = lambda msg: None,
                 dry_run: bool = True, clock=lambda: datetime.now(timezone.utc),
                 browser_sender=None):
        self.outbox, self.http, self._token, self.cfg = outbox, http, token, cfg
        self.alert_coo, self.dry_run, self.clock = alert_coo, dry_run, clock
        self.browser_sender = browser_sender
        self.reply = ReplyBackend(http, token)
        self.push = PushBackend(http, token)

    def _token_valid(self, row: dict) -> bool:
        if not row["reply_token"]:
            return False
        exp = row["reply_token_expires_at"]
        if exp is None:  # lifetime TBD: try it, LINE rejects an expired token for free
            return True
        return self.clock() < datetime.fromisoformat(exp)

    def _halted_key(self) -> str:
        return f"push_halt:{self.cfg.channel_id}:{month_key(self.clock())}"

    def _browser_sender_killed(self) -> bool:
        return self.outbox.get_flag("care_sender_enabled") == "false"

    def process(self, row_id: int) -> str:
        """Returns the plan/outcome label. In dry_run nothing is claimed or sent."""
        row = self.outbox.get(row_id)
        if row["state"] == "fallback":
            if self._token_valid(row):
                return self._do_reply(row)
            return "skip_fallback"
        if row["state"] not in ("queued", "deferred"):
            return f"skip_{row['state']}"
        if self._token_valid(row):
            return self._do_reply(row)
        if row["message_kind"] != "important_announcement":
            if self.browser_sender is not None:
                return self.browser_sender.process(row_id)
            if self._browser_sender_killed():
                if not self.dry_run:
                    self.outbox.mark_fallback(row_id, "sender_disabled_fallback_reply_token")
                return "fallback_reply_token"
            if not self.dry_run:
                self.outbox.mark_deferred(row_id, "await_browser_sender")
            return "defer_browser"
        return self._do_push(row)

    def _do_reply(self, row: dict) -> str:
        if self.dry_run:
            return "would_reply"
        rid = row["id"]
        if not self.outbox.claim_sending(rid, "api_reply"):
            return "skip_claimed"
        try:
            status, _ = self.reply.send(row)
        except Exception:
            self.outbox.mark_failed(rid, "reply_network_unconfirmed")
            return "failed"
        if status == 200:
            self.outbox.mark_sent(rid)
            return "sent_reply"
        if status == 400:  # token expired/used: nothing was delivered, safe to re-route
            self.outbox.clear_reply_token(rid)
            self.outbox.mark_deferred(rid, "reply_token_rejected")
            return "reply_rejected"
        self.outbox.mark_failed(rid, f"reply_http_{status}")
        return "failed"

    def _do_push(self, row: dict) -> str:
        rid = row["id"]
        halted = self.outbox.get_flag(self._halted_key()) is not None
        if halted:
            dec = GateDecision(False, "monthly_halt")
        else:
            try:
                used = read_consumption(self.http, self._token)
            except Exception:
                if not self.dry_run:
                    self.outbox.mark_deferred(rid, "quota_read_failed")
                return "defer_quota_unreadable"
            dec = decide_push(self.cfg, used, 1, bool(row["critical"]))
            if dec.alert and self.outbox.set_flag_once(
                    f"alert240:{self.cfg.channel_id}:{month_key(self.clock())}", "1"):
                self.alert_coo(f"care push quota at {dec.used + 1}/{self.cfg.monthly_limit}")
        if not dec.allowed:
            if not self.dry_run:
                self.outbox.mark_deferred(rid, f"push_blocked_{dec.reason}")
            return f"blocked_{dec.reason}"
        if self.dry_run:
            return "would_push"
        if not self.outbox.claim_sending(rid, "api_push"):
            return "skip_claimed"
        try:
            status, _ = self.push.send(row)
        except Exception:
            self.outbox.mark_failed(rid, "push_network_unconfirmed")
            return "failed"
        if status == 200:
            self.outbox.mark_sent(rid)
            return "sent_push"
        if status == 429:
            self.outbox.set_flag(self._halted_key(), "1")
            self.outbox.mark_deferred(rid, "push_http_429")
            return "halted_429"
        self.outbox.mark_failed(rid, f"push_http_{status}")
        return "failed"
