#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BL TikTok CTA loop — the decision engine that turns a comment/DM into an
action (task-8df13432).

CEO's flow (verbatim, 2026-09-23): check whether we can Inbox a commenter
directly; if yes, send the Inbox and reply on the comment saying we sent it;
if no, reply on the comment inviting them to DM us; track who DM'd us from
which episode so an unprompted DM later gets the right deliverable, or falls
back to a general chat mode for senders we don't recognize.

Builds on tools/bl_tiktok_watch.py (task-c01b0b99): reads that tool's
events.jsonl (new comments/DMs) and reuses its VerificationWall/is_logged_in
conventions. Memory lives in a small SQLite ledger at state/bl-tiktok/cta.sqlite
(never committed — same convention as state/bl-tiktok/state.json).

Reply packs (written by task-6cc24a28, read-only here) live at
prototypes/bl-reply-packs/EP<n>.yaml — see load_pack() for the schema.

SHADOW MODE IS THE DEFAULT (HARD, per task brief). The engine always runs its
full decision logic — including the read-only `can_dm` check — but in shadow
mode never calls the two OUTWARD adapters (`send_dm`, `reply_comment`).
Instead every decision is written to the `planned_actions` table and to the
run's summary text: "would DM @handle: <text>", "would reply to comment X:
<text>". Only `--live` (never used by this task) calls the outward adapters,
and even then only up to `--cap` (default 10) per day, with a randomized
human-pace delay between actions.

Before ANY text is sent or planned, it is checked against the pack's
`never_say` list and against "no URL except the ones already present
somewhere in the pack" (safety_check()). A failed check blocks the action and
logs why — it never silently drops the check and sends anyway.

Adapters (`can_dm` / `send_dm` / `reply_comment`, see BLTikTokCTABrowser at
the bottom) are UNVERIFIED against the live TikTok DOM — same status as
tools/bl_tiktok_watch.py's BLTikTokBrowser, for the same reason (no logged-in
session reached yet). Everything above that class is pure and unit-tested
with fake adapters (tests/test_bl_tiktok_cta.py, fixtures under
tests/fixtures/bl_tiktok_cta/).

    python3 tools/bl_tiktok_cta.py run    [--live] [--cap N] [--cdp URL]
                                           [--db PATH] [--packs-dir DIR]
    python3 tools/bl_tiktok_cta.py status [--db PATH]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import yaml

from tools.bl_tiktok_watch import VerificationWall, BLTikTokBrowser

DB_PATH = Path("state/bl-tiktok/cta.sqlite")
PACKS_DIR = Path("prototypes/bl-reply-packs")
EVENTS_PATH = Path("state/bl-tiktok/events.jsonl")
CDP = "http://127.0.0.1:9224"
DEFAULT_DAILY_CAP = 10
DEFAULT_LIVE_DELAY_RANGE = (20.0, 90.0)  # seconds, randomized human pace


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _today(run_at: str | None = None) -> str:
    ts = run_at or _now_iso()
    return ts[:10]


# ── exceptions ───────────────────────────────────────────────────────────────

class PackNotFound(RuntimeError):
    """No reply pack file exists for the requested episode."""


class DailyCapReached(RuntimeError):
    """Live mode hit its per-day outward-action cap; caller must stop, not
    silently keep trying (that would look like the cap doesn't exist)."""


# ── keyword matching: tolerate Thai spelling drift ─────────────────────────
# Common final-consonant drift the CEO's audience actually types: ค/ก (เช็ค
# vs เช็ก, โบรค vs โบรก) collapse to one canonical form for MATCHING ONLY —
# never for the text we send back, which stays exactly as authored in the
# pack. This is a narrow fold (still requires the rest of the word to line
# up), not a fuzzy/edit-distance matcher.
_THAI_FOLD = str.maketrans({"ค": "ก", "ฆ": "ก", "ข": "ก", "ฃ": "ก"})

# Strip emoji / pictographs / dingbats / arrows before matching. Deliberately
# broad block ranges (same "false positive costs one skipped match, false
# negative costs a duplicate-looking miss" tradeoff as bl_tiktok_watch's
# verification-marker check).
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F000-\U0001F0FF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF"
    "]",
    flags=re.UNICODE,
)


def normalize_for_match(text: str) -> str:
    """Fold spelling drift + strip emoji/whitespace, for MATCHING only."""
    if not text:
        return ""
    text = _EMOJI_RE.sub("", text)
    text = text.translate(_THAI_FOLD)
    text = re.sub(r"\s+", "", text)
    return text.lower()


def match_keyword(comment_text: str, pack: dict) -> Optional[str]:
    """Returns the ORIGINAL (un-normalized) keyword/variant string from the
    pack that matched, or None. Checks pack['cta']['keyword'] first, then
    every entry in pack['cta']['variants'], in order."""
    cta = pack.get("cta", {})
    candidates = [cta.get("keyword", "")] + list(cta.get("variants", []) or [])
    normalized_text = normalize_for_match(comment_text)
    if not normalized_text:
        return None
    for candidate in candidates:
        if not candidate:
            continue
        if normalize_for_match(candidate) in normalized_text:
            return candidate
    return None


# ── safety: never_say + URL allowlist ───────────────────────────────────────

_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def _extract_urls(text: str) -> set[str]:
    return {u.rstrip("\").,!?'\\") for u in _URL_RE.findall(text or "")}


def _pack_allowed_urls(pack: dict) -> set[str]:
    """Every URL that appears anywhere in the pack itself is allowed —
    the pack is the CEO's authored copy, so any link the copywriter put in
    it (a deliverable link, an official channel) is trusted by construction."""
    return _extract_urls(json.dumps(pack, ensure_ascii=False))


def safety_check(text: str, pack: dict) -> tuple[bool, Optional[str]]:
    """(ok, reason). reason is None iff ok is True."""
    lowered = (text or "").lower()
    for phrase in pack.get("never_say", []) or []:
        if phrase and phrase.lower() in lowered:
            return False, f"never_say match: {phrase!r}"
    allowed = _pack_allowed_urls(pack)
    for url in _extract_urls(text):
        if url not in allowed:
            return False, f"disallowed URL: {url!r}"
    return True, None


# ── reply-pack loading (read-only — task-6cc24a28 owns writing these) ──────

def load_pack(packs_dir: Path, episode: str) -> dict:
    path = Path(packs_dir) / f"{episode}.yaml"
    if not path.exists():
        raise PackNotFound(str(path))
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# ── SQLite memory ────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    handle TEXT PRIMARY KEY,
    first_seen TEXT NOT NULL,
    source_episode TEXT,
    source_comment_id TEXT,
    matched_keyword TEXT,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    comment_id TEXT PRIMARY KEY,
    handle TEXT NOT NULL,
    episode TEXT,
    text TEXT,
    seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    mode TEXT NOT NULL,
    action_type TEXT NOT NULL,
    handle TEXT,
    episode TEXT,
    comment_id TEXT,
    text TEXT,
    blocked INTEGER NOT NULL DEFAULT 0,
    block_reason TEXT
);

CREATE TABLE IF NOT EXISTS planned_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    action_type TEXT NOT NULL,
    handle TEXT,
    episode TEXT,
    comment_id TEXT,
    text TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def get_contact(conn: sqlite3.Connection, handle: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM contacts WHERE handle = ?", (handle,)).fetchone()


def upsert_contact(conn: sqlite3.Connection, handle: str, *, status: str,
                    source_episode: str | None, source_comment_id: str | None,
                    matched_keyword: str | None, now: str) -> None:
    existing = get_contact(conn, handle)
    if existing is None:
        conn.execute(
            "INSERT INTO contacts (handle, first_seen, source_episode, source_comment_id, "
            "matched_keyword, status, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (handle, now, source_episode, source_comment_id, matched_keyword, status, now),
        )
    else:
        conn.execute(
            "UPDATE contacts SET status = ?, updated_at = ? WHERE handle = ?",
            (status, now, handle),
        )
    conn.commit()


def record_question(conn: sqlite3.Connection, comment_id: str, handle: str,
                     episode: str | None, text: str, now: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO questions (comment_id, handle, episode, text, seen_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (comment_id, handle, episode, text, now),
    )
    conn.commit()


def log_action(conn: sqlite3.Connection, *, mode: str, action_type: str,
                handle: str | None, episode: str | None, comment_id: str | None,
                text: str | None, blocked: bool = False, block_reason: str | None = None,
                now: str) -> None:
    conn.execute(
        "INSERT INTO action_log (ts, mode, action_type, handle, episode, comment_id, "
        "text, blocked, block_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (now, mode, action_type, handle, episode, comment_id, text, int(blocked), block_reason),
    )
    conn.commit()


def record_planned(conn: sqlite3.Connection, *, action_type: str, handle: str | None,
                    episode: str | None, comment_id: str | None, text: str, now: str) -> None:
    conn.execute(
        "INSERT INTO planned_actions (ts, action_type, handle, episode, comment_id, text) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (now, action_type, handle, episode, comment_id, text),
    )
    conn.commit()


def count_live_actions_today(conn: sqlite3.Connection, today: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM action_log WHERE mode = 'live' AND blocked = 0 "
        "AND substr(ts, 1, 10) = ?",
        (today,),
    ).fetchone()
    return row["n"] if row else 0


# ── decision results (for tests + summary formatting) ───────────────────────

@dataclass
class Decision:
    kind: str  # dm_sent | dm_invited | question | duplicate | blocked | delivered | general
    handle: str | None = None
    episode: str | None = None
    comment_id: str | None = None
    detail: str = ""
    planned: list[dict] = field(default_factory=list)


# ── adapters interface ───────────────────────────────────────────────────────
# Fake adapters (tests) and the real UNVERIFIED browser adapter (bottom of
# this file) both implement this shape: can_dm(handle) -> bool,
# send_dm(handle, text) -> None, reply_comment(comment_id, text) -> None.


class Engine:
    """The full decision engine. Pure aside from the adapters/db/clock it is
    handed — every branch is reachable with a fake adapters object and an
    in-memory or tmp_path sqlite db, no browser required."""

    def __init__(self, conn: sqlite3.Connection, packs_dir: Path, adapters,
                 *, live: bool = False, daily_cap: int = DEFAULT_DAILY_CAP,
                 clock: Callable[[], str] = _now_iso,
                 sleep_fn: Callable[[float], None] = time.sleep,
                 delay_range: tuple[float, float] = DEFAULT_LIVE_DELAY_RANGE,
                 rng: random.Random | None = None):
        self.conn = conn
        self.packs_dir = Path(packs_dir)
        self.adapters = adapters
        self.live = live
        self.daily_cap = daily_cap
        self.clock = clock
        self.sleep_fn = sleep_fn
        self.delay_range = delay_range
        self.rng = rng or random.Random()
        self._pack_cache: dict[str, dict] = {}

    def _pack(self, episode: str) -> dict:
        if episode not in self._pack_cache:
            self._pack_cache[episode] = load_pack(self.packs_dir, episode)
        return self._pack_cache[episode]

    def _human_pace(self) -> None:
        if self.live:
            self.sleep_fn(self.rng.uniform(*self.delay_range))

    def _try_outward(self, *, action_type: str, handle: str | None, episode: str | None,
                      comment_id: str | None, text: str, now: str, call: Callable[[], None]) -> bool:
        """Runs one outward action under live mode's safety net. Returns True
        if it was (or, in shadow, would have been) performed. Always records
        planned_actions; in live mode also enforces the cap and calls `call`."""
        record_planned(self.conn, action_type=action_type, handle=handle, episode=episode,
                        comment_id=comment_id, text=text, now=now)
        if not self.live:
            log_action(self.conn, mode="shadow", action_type=action_type, handle=handle,
                       episode=episode, comment_id=comment_id, text=text, now=now)
            return True

        today = _today(now)
        if count_live_actions_today(self.conn, today) >= self.daily_cap:
            log_action(self.conn, mode="live", action_type=action_type, handle=handle,
                       episode=episode, comment_id=comment_id, text=text, now=now,
                       blocked=True, block_reason=f"daily cap {self.daily_cap} reached")
            raise DailyCapReached(f"{self.daily_cap} actions already sent today ({today})")

        self._human_pace()
        call()
        log_action(self.conn, mode="live", action_type=action_type, handle=handle,
                   episode=episode, comment_id=comment_id, text=text, now=now)
        return True

    # -- comment path ---------------------------------------------------------

    def process_comment(self, episode: str, comment: dict) -> Decision:
        """comment: {id, handle, text}."""
        handle = comment["handle"]
        comment_id = comment["id"]
        now = self.clock()

        existing = get_contact(self.conn, handle)
        if existing is not None:
            log_action(self.conn, mode="live" if self.live else "shadow",
                       action_type="duplicate_comment_skipped", handle=handle, episode=episode,
                       comment_id=comment_id, text=None, now=now)
            return Decision(kind="duplicate", handle=handle, episode=episode,
                             comment_id=comment_id, detail=f"already tracked as {existing['status']!r}")

        pack = self._pack(episode)
        matched = match_keyword(comment["text"], pack)
        if matched is None:
            record_question(self.conn, comment_id, handle, episode, comment["text"], now)
            return Decision(kind="question", handle=handle, episode=episode,
                             comment_id=comment_id, detail=comment["text"])

        upsert_contact(self.conn, handle, status="commented", source_episode=episode,
                       source_comment_id=comment_id, matched_keyword=matched, now=now)

        cta = pack.get("cta", {})
        can = self.adapters.can_dm(handle)
        planned = []

        if can:
            dm_text = cta.get("dm_message", "")
            ok, reason = safety_check(dm_text, pack)
            if not ok:
                log_action(self.conn, mode="live" if self.live else "shadow",
                           action_type="dm_send", handle=handle, episode=episode,
                           comment_id=comment_id, text=dm_text, now=now,
                           blocked=True, block_reason=reason)
                return Decision(kind="blocked", handle=handle, episode=episode,
                                 comment_id=comment_id, detail=reason)

            reply_text = cta.get("comment_reply_dm_sent", "")
            ok2, reason2 = safety_check(reply_text, pack)
            if not ok2:
                log_action(self.conn, mode="live" if self.live else "shadow",
                           action_type="comment_reply", handle=handle, episode=episode,
                           comment_id=comment_id, text=reply_text, now=now,
                           blocked=True, block_reason=reason2)
                return Decision(kind="blocked", handle=handle, episode=episode,
                                 comment_id=comment_id, detail=reason2)

            self._try_outward(action_type="dm_send", handle=handle, episode=episode,
                              comment_id=comment_id, text=dm_text, now=now,
                              call=lambda: self.adapters.send_dm(handle, dm_text))
            planned.append({"type": "dm_send", "handle": handle, "text": dm_text})
            self._try_outward(action_type="comment_reply", handle=handle, episode=episode,
                              comment_id=comment_id, text=reply_text, now=now,
                              call=lambda: self.adapters.reply_comment(comment_id, reply_text))
            planned.append({"type": "comment_reply", "comment_id": comment_id, "text": reply_text})

            upsert_contact(self.conn, handle, status="dm_sent", source_episode=episode,
                           source_comment_id=comment_id, matched_keyword=matched, now=now)
            return Decision(kind="dm_sent", handle=handle, episode=episode,
                             comment_id=comment_id, detail=matched, planned=planned)

        invite_text = cta.get("comment_reply_dm_invite", "")
        ok, reason = safety_check(invite_text, pack)
        if not ok:
            log_action(self.conn, mode="live" if self.live else "shadow",
                       action_type="comment_reply", handle=handle, episode=episode,
                       comment_id=comment_id, text=invite_text, now=now,
                       blocked=True, block_reason=reason)
            return Decision(kind="blocked", handle=handle, episode=episode,
                             comment_id=comment_id, detail=reason)

        self._try_outward(action_type="comment_reply", handle=handle, episode=episode,
                          comment_id=comment_id, text=invite_text, now=now,
                          call=lambda: self.adapters.reply_comment(comment_id, invite_text))
        planned.append({"type": "comment_reply", "comment_id": comment_id, "text": invite_text})

        upsert_contact(self.conn, handle, status="dm_invited", source_episode=episode,
                       source_comment_id=comment_id, matched_keyword=matched, now=now)
        return Decision(kind="dm_invited", handle=handle, episode=episode,
                         comment_id=comment_id, detail=matched, planned=planned)

    # -- inbox path -------------------------------------------------------------

    def process_inbox(self, message: dict) -> Decision:
        """message: {id, handle, text}. No episode is known up front — the
        episode comes from memory of that handle's source comment, per the
        CEO's flow ("ระบบตรวจว่าใคร Direct มาจาก EP ไหน")."""
        handle = message["handle"]
        now = self.clock()
        contact = get_contact(self.conn, handle)

        if contact is not None and contact["status"] in ("dm_invited", "commented"):
            episode = contact["source_episode"]
            pack = self._pack(episode)
            deliver_text = pack.get("cta", {}).get("dm_message", "")
            ok, reason = safety_check(deliver_text, pack)
            if not ok:
                log_action(self.conn, mode="live" if self.live else "shadow",
                           action_type="dm_deliver", handle=handle, episode=episode,
                           comment_id=message["id"], text=deliver_text, now=now,
                           blocked=True, block_reason=reason)
                return Decision(kind="blocked", handle=handle, episode=episode,
                                 comment_id=message["id"], detail=reason)

            self._try_outward(action_type="dm_deliver", handle=handle, episode=episode,
                              comment_id=message["id"], text=deliver_text, now=now,
                              call=lambda: self.adapters.send_dm(handle, deliver_text))
            upsert_contact(self.conn, handle, status="delivered", source_episode=episode,
                           source_comment_id=contact["source_comment_id"],
                           matched_keyword=contact["matched_keyword"], now=now)
            return Decision(kind="delivered", handle=handle, episode=episode,
                             comment_id=message["id"], detail=deliver_text,
                             planned=[{"type": "dm_deliver", "handle": handle, "text": deliver_text}])

        # Sender not in memory (or already dm_sent/delivered/general): route to
        # the auto-chat-mode STUB. Model/cost is a later CEO decision — this
        # never talks back, only logs + surfaces in the summary.
        upsert_contact(self.conn, handle, status="general", source_episode=None,
                       source_comment_id=None, matched_keyword=None, now=now)
        log_action(self.conn, mode="live" if self.live else "shadow",
                   action_type="route_auto_chat_stub", handle=handle, episode=None,
                   comment_id=message["id"], text=message.get("text", ""), now=now)
        return Decision(kind="general", handle=handle, comment_id=message["id"],
                         detail=message.get("text", ""))


# ── run orchestration + summary ─────────────────────────────────────────────

def run_batch(engine: Engine, comments_by_episode: dict[str, list[dict]],
              inbox_messages: list[dict]) -> tuple[list[Decision], list[Decision]]:
    """Pure-ish orchestration over already-fetched events (no I/O beyond the
    engine's own db/adapters) — this is what both the CLI and the tests call."""
    comment_decisions: list[Decision] = []
    for episode, comments in comments_by_episode.items():
        for comment in comments:
            comment_decisions.append(engine.process_comment(episode, comment))

    inbox_decisions: list[Decision] = []
    for message in inbox_messages:
        inbox_decisions.append(engine.process_inbox(message))

    return comment_decisions, inbox_decisions


def format_summary(run_at: str, comment_decisions: list[Decision],
                    inbox_decisions: list[Decision], *, live: bool) -> str:
    mode = "LIVE" if live else "SHADOW"
    lines = [f"BL TikTok CTA — {mode} — {run_at}"]

    dm_sent = [d for d in comment_decisions if d.kind == "dm_sent"]
    dm_invited = [d for d in comment_decisions if d.kind == "dm_invited"]
    questions = [d for d in comment_decisions if d.kind == "question"]
    duplicates = [d for d in comment_decisions if d.kind == "duplicate"]
    blocked = [d for d in comment_decisions if d.kind == "blocked"] + \
        [d for d in inbox_decisions if d.kind == "blocked"]
    delivered = [d for d in inbox_decisions if d.kind == "delivered"]
    general = [d for d in inbox_decisions if d.kind == "general"]

    verb = "DMed" if live else "would DM"
    lines.append(f"Comments matched → {verb}: {len(dm_sent)}")
    for d in dm_sent:
        for p in d.planned:
            if p["type"] == "dm_send":
                lines.append(f"  {verb} @{d.handle} ({d.episode}): {p['text'][:160]!r}")

    verb2 = "invited" if live else "would invite"
    lines.append(f"Comments matched → {verb2} to DM: {len(dm_invited)}")
    for d in dm_invited:
        for p in d.planned:
            lines.append(f"  {verb2} @{d.handle} ({d.episode}) on comment {p.get('comment_id')}: {p['text'][:160]!r}")

    lines.append(f"Unmatched comments (questions, not auto-answered): {len(questions)}")
    for d in questions:
        lines.append(f"  @{d.handle} ({d.episode}): {d.detail[:160]!r}")

    lines.append(f"Duplicate comments skipped (already tracked): {len(duplicates)}")

    verb3 = "delivered" if live else "would deliver"
    lines.append(f"Inbox from known contacts → {verb3}: {len(delivered)}")
    for d in delivered:
        lines.append(f"  {verb3} to @{d.handle} ({d.episode}): {d.detail[:160]!r}")

    lines.append(f"Inbox from unknown senders → routed to auto-chat-mode STUB "
                 f"(no model wired up yet, CEO decision pending): {len(general)}")
    for d in general:
        lines.append(f"  @{d.handle}: {d.detail[:160]!r}")

    if blocked:
        lines.append(f"BLOCKED by safety check (never_say/URL): {len(blocked)}")
        for d in blocked:
            lines.append(f"  @{d.handle} ({d.episode}): {d.detail}")

    return "\n".join(lines)


# ── live browser adapter — UNVERIFIED, same status as bl_tiktok_watch ───────

class BLTikTokCTABrowser(BLTikTokBrowser):
    """Adds the 3 write-capable methods the Engine calls. can_dm is a
    read-only in-UI check; send_dm and reply_comment are the only two
    methods in this whole tool that ever mutate the account, and the Engine
    only calls them under --live. Every selector below is UNVERIFIED against
    the live TikTok Studio/DOM (no logged-in session reached in this task —
    see tools/bl_tiktok_watch.py's module docstring for the same caveat and
    why). CONFIRM AND CORRECT against the real DOM before the first --live
    run; nothing here has been exercised against a real page."""

    def can_dm(self, handle: str) -> bool:
        """UNVERIFIED. Expected approach: open the commenter's profile
        (https://www.tiktok.com/@<handle>) and look for a "Message" button
        vs. it being absent/disabled. TikTok's Business Messaging rules
        (per prototypes/bl-reply-bot/RESEARCH.md) mean a commenter who never
        messaged first is very likely NOT DM-able — that research is the
        starting assumption, not a substitute for checking the real button."""
        page = self.page
        page.goto(f"https://www.tiktok.com/@{handle}", wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(1500)
        if self.is_verification_wall():
            raise VerificationWall(f"verification wall on @{handle}'s profile")
        return page.locator('button[data-e2e="message-button"]').count() > 0

    def send_dm(self, handle: str, text: str) -> None:
        """UNVERIFIED. Never called except under --live."""
        page = self.page
        page.goto(f"https://www.tiktok.com/@{handle}", wait_until="domcontentloaded", timeout=30_000)
        if self.is_verification_wall():
            raise VerificationWall(f"verification wall on @{handle}'s profile")
        page.locator('button[data-e2e="message-button"]').first.click(timeout=5000)
        page.locator('div[data-e2e="message-input-area"]').first.fill(text, timeout=5000)
        page.locator('[data-e2e="message-send-button"]').first.click(timeout=5000)

    def reply_comment(self, comment_id: str, text: str) -> None:
        """UNVERIFIED. Never called except under --live."""
        page = self.page
        page.locator(f'[data-comment-id="{comment_id}"] [data-e2e="comment-reply"]').first.click(timeout=5000)
        page.locator(f'[data-comment-id="{comment_id}"] [data-e2e="comment-reply-input"]').first.fill(text, timeout=5000)
        page.locator(f'[data-comment-id="{comment_id}"] [data-e2e="comment-reply-submit"]').first.click(timeout=5000)


# ── CLI ──────────────────────────────────────────────────────────────────────

def _load_new_events(events_path: Path, since_id: int) -> list[dict]:
    if not events_path.exists():
        return []
    out = []
    with open(events_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i <= since_id:
                continue
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def cmd_run(args) -> int:
    conn = connect(args.db)
    conn.execute("CREATE TABLE IF NOT EXISTS event_offset (id INTEGER PRIMARY KEY CHECK (id = 0), last_line INTEGER NOT NULL)")
    conn.commit()
    row = conn.execute("SELECT last_line FROM event_offset WHERE id = 0").fetchone()
    since = row["last_line"] if row else -1

    events = _load_new_events(args.events, since)
    comments_by_episode: dict[str, list[dict]] = {}
    inbox_messages: list[dict] = []
    for ev in events:
        if ev.get("type") == "comment":
            comments_by_episode.setdefault(ev.get("video_id", "unknown"), []).append(ev)
        elif ev.get("type") == "dm":
            inbox_messages.append(ev)

    browser = BLTikTokCTABrowser(args.cdp)
    try:
        browser.attach()
        if browser.is_verification_wall():
            print("VERIFICATION_WALL — stopping, not attempting to solve it")
            return 2
        if not browser.is_logged_in():
            print("NOT_LOGGED_IN — run bl_tiktok_watch.py login-qr first")
            return 1
        # Shadow mode still needs can_dm's real read-only signal; the Engine
        # gates the two OUTWARD methods (send_dm/reply_comment) on --live,
        # never on this attach step.
        engine = Engine(conn, args.packs_dir, browser, live=args.live, daily_cap=args.cap)
        comment_decisions, inbox_decisions = run_batch(engine, comments_by_episode, inbox_messages)
    except (VerificationWall, DailyCapReached) as e:
        print(f"STOP: {e}")
        return 2
    finally:
        browser.close()

    conn.execute(
        "INSERT INTO event_offset (id, last_line) VALUES (0, ?) "
        "ON CONFLICT(id) DO UPDATE SET last_line = excluded.last_line",
        (since + len(events),),
    )
    conn.commit()

    print(format_summary(_now_iso(), comment_decisions, inbox_decisions, live=args.live))
    return 0


def cmd_status(args) -> int:
    conn = connect(args.db)
    n_contacts = conn.execute("SELECT COUNT(*) AS n FROM contacts").fetchone()["n"]
    n_questions = conn.execute("SELECT COUNT(*) AS n FROM questions").fetchone()["n"]
    n_planned = conn.execute("SELECT COUNT(*) AS n FROM planned_actions").fetchone()["n"]
    print(f"ledger: {args.db}")
    print(f"contacts tracked: {n_contacts}")
    print(f"unanswered questions: {n_questions}")
    print(f"planned actions (all-time): {n_planned}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="process new comments/DMs from bl_tiktok_watch's events.jsonl")
    p_run.add_argument("--live", action="store_true", help="HARD: never pass this from this task")
    p_run.add_argument("--cap", type=int, default=DEFAULT_DAILY_CAP)
    p_run.add_argument("--cdp", default=CDP)
    p_run.add_argument("--db", type=Path, default=DB_PATH)
    p_run.add_argument("--packs-dir", type=Path, default=PACKS_DIR)
    p_run.add_argument("--events", type=Path, default=EVENTS_PATH)
    p_run.set_defaults(func=cmd_run)

    p_status = sub.add_parser("status", help="one-screen ledger summary")
    p_status.add_argument("--db", type=Path, default=DB_PATH)
    p_status.set_defaults(func=cmd_status)

    return ap


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
