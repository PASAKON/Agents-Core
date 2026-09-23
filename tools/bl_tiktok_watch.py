#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BL TikTok watch — read-only, zero-model CTA-loop monitor (task-c01b0b99).

STANDALONE — no Claude in the loop, zero token cost at runtime — same pattern
as tools/flow_shoot.py and scripts/higgsfield/gen_loop.py: Playwright over CDP,
a dedicated Chrome profile (scripts/bl-tiktok/launch-chrome-debug.sh, port
9224), a resumable ledger under state/bl-tiktok/. This tool NEVER writes to
the account: no reply, like, follow, or message. It only reads.

    python3 tools/bl_tiktok_watch.py login-qr [--out PATH] [--cdp URL]
    python3 tools/bl_tiktok_watch.py run      [--cdp URL] [--state PATH] [--events PATH]
    python3 tools/bl_tiktok_watch.py status   [--state PATH]

Every function that touches the browser lives on BLTikTokBrowser, at the
bottom of this file, and is UNVERIFIED against the live TikTok Studio DOM/API
— written from general knowledge of TikTok's public API field naming, not a
logged-in session (this task never reached one: Step 1 QR login blocks on the
CEO scanning it, see the task report). Same convention as tools/flow_shoot.py's
FlowBrowser: "the first live check is a human-run --dry-run after the CEO logs
in." Everything ABOVE BLTikTokBrowser — the raw-JSON adapters, the diff/delta
logic, the ledger I/O, the summary formatting — is pure and unit-tested
against saved fixtures (tests/test_bl_tiktok_watch.py) and does not change
just because a selector or a field name turns out to be wrong; only the
adapters (`extract_*_from_raw`) will need correcting once real captured JSON
is available.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

CDP = "http://127.0.0.1:9224"
STATE_PATH = Path("state/bl-tiktok/state.json")
EVENTS_PATH = Path("state/bl-tiktok/events.jsonl")
LOGIN_URL = "https://www.tiktok.com/login"
DEFAULT_QR_OUT = Path.home() / "MoonieXHQ/Work/task-c01b0b99/out/bl-tiktok-login-qr.png"

# Same wording family as tools/flow_shoot.py's is_refusal_text / decide layer,
# kept as a plain keyword check here — this tool is explicitly zero-model, so
# it never calls tools/decide.py. Deliberately broad and Thai+English: a false
# "yes, this is a wall" costs one stopped run; a false "no" risks the account
# getting flagged for scripted captcha-solving, which this must never attempt.
_VERIFICATION_MARKERS = (
    "verify to continue", "captcha", "ยืนยันตัวตน", "security check",
    "slide to verify", "เลื่อนเพื่อยืนยัน", "unusual activity",
    "confirm it's you", "confirm you're not a robot",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ── exceptions ───────────────────────────────────────────────────────────────

class VerificationWall(RuntimeError):
    """A captcha/verification wall was shown. STOP — never try to solve it
    (task brief, Step 3 rule: "If TikTok shows a captcha or a verification
    wall, stop and report it. Never try to solve it.")."""


class NotLoggedIn(RuntimeError):
    """The automation Chrome's TikTok session is not signed in."""


class UnrecognizedResponseShape(RuntimeError):
    """A raw JSON blob captured from the page didn't match ANY of the field
    names this adapter knows how to read. Deliberately its own type, not a
    silent zero — an unreadable stat is not a zero stat, same principle as
    tools/flow_shoot.py's EstimateUnreadable. This is also the signal that
    the adapter needs correcting against the real live shape once one is
    captured (see this file's module docstring)."""


# ── pure adapters: raw (unverified-shape) JSON -> normalized dicts ─────────
# Each adapter tries several candidate key names per field, because the exact
# TikTok Studio / creator-center internal JSON shape has never been captured
# live in this task (Step 1 blocked on CEO QR login before Step 3 could run
# against the real account). Candidates are chosen from TikTok's own PUBLIC
# API field naming (Content Posting API / Display API: view_count, like_count,
# comment_count, share_count) plus the common alternate camelCase form
# (playCount/diggCount) seen in TikTok's public web JSON elsewhere, since the
# internal Studio API is unknown. CORRECT THESE CANDIDATE LISTS the first time
# real captured JSON is available — do not trust this guess in production
# without that check.

_VIDEO_ID_KEYS = ("id", "video_id", "item_id", "aweme_id")
_METRIC_CANDIDATES = {
    "views": ("views", "view_count", "play_count", "playCount"),
    "likes": ("likes", "like_count", "digg_count", "diggCount"),
    "comments": ("comments", "comment_count", "commentCount"),
    "shares": ("shares", "share_count", "shareCount"),
    "saves": ("saves", "save_count", "collect_count", "collectCount"),
}


def _first_present(d: dict, keys: tuple[str, ...]):
    for k in keys:
        if k in d:
            return d[k]
    return None


def extract_video_stats_from_raw(raw: dict) -> list[dict]:
    """raw is the parsed JSON body of one intercepted TikTok Studio content/
    analytics response. Returns a list of normalized dicts:
    {id, views, likes, comments, shares, saves}. Looks for a list under a few
    candidate container keys (list/items/videos/data), since the response
    envelope shape is equally unverified."""
    items = None
    if isinstance(raw, list):
        items = raw
    else:
        for key in ("items", "list", "videos", "data", "aweme_list"):
            v = raw.get(key) if isinstance(raw, dict) else None
            if isinstance(v, list):
                items = v
                break
    if items is None:
        raise UnrecognizedResponseShape(
            f"no item list found under any known container key; top-level keys={list(raw)[:20] if isinstance(raw, dict) else type(raw)!r}")

    out = []
    for item in items:
        vid = _first_present(item, _VIDEO_ID_KEYS)
        if vid is None:
            raise UnrecognizedResponseShape(f"no video id found in item keys={list(item)[:20]}")
        stats_src = item.get("stats", item) if isinstance(item, dict) else item
        row = {"id": str(vid)}
        for field, candidates in _METRIC_CANDIDATES.items():
            val = _first_present(stats_src, candidates)
            if val is None:
                val = _first_present(item, candidates)
            row[field] = int(val) if val is not None else 0
        out.append(row)
    return out


def extract_comments_from_raw(raw: dict, video_id: str) -> list[dict]:
    """Normalized: {id, video_id, handle, text, posted_at}."""
    items = None
    if isinstance(raw, list):
        items = raw
    else:
        for key in ("comments", "items", "list", "data"):
            v = raw.get(key) if isinstance(raw, dict) else None
            if isinstance(v, list):
                items = v
                break
    if items is None:
        raise UnrecognizedResponseShape(
            f"no comment list found; top-level keys={list(raw)[:20] if isinstance(raw, dict) else type(raw)!r}")

    out = []
    for c in items:
        cid = _first_present(c, ("id", "cid", "comment_id"))
        if cid is None:
            raise UnrecognizedResponseShape(f"no comment id in keys={list(c)[:20]}")
        user = c.get("user", {}) if isinstance(c.get("user"), dict) else {}
        handle = _first_present(c, ("handle", "unique_id", "username")) or user.get("unique_id") or user.get("handle")
        text = _first_present(c, ("text", "comment_text", "content"))
        posted_at = _first_present(c, ("create_time", "posted_at", "time", "timestamp"))
        out.append({
            "id": str(cid),
            "video_id": video_id,
            "handle": handle or "",
            "text": text or "",
            "posted_at": posted_at,
        })
    return out


def extract_inbox_messages_from_raw(raw: dict) -> list[dict]:
    """Normalized: {id, handle, text, sent_at}."""
    items = None
    if isinstance(raw, list):
        items = raw
    else:
        for key in ("messages", "items", "list", "data"):
            v = raw.get(key) if isinstance(raw, dict) else None
            if isinstance(v, list):
                items = v
                break
    if items is None:
        raise UnrecognizedResponseShape(
            f"no message list found; top-level keys={list(raw)[:20] if isinstance(raw, dict) else type(raw)!r}")

    out = []
    for m in items:
        mid = _first_present(m, ("id", "message_id", "mid"))
        if mid is None:
            raise UnrecognizedResponseShape(f"no message id in keys={list(m)[:20]}")
        sender = m.get("sender", {}) if isinstance(m.get("sender"), dict) else {}
        handle = _first_present(m, ("handle", "from", "sender_handle")) or sender.get("unique_id") or sender.get("handle")
        text = _first_present(m, ("text", "content", "message"))
        sent_at = _first_present(m, ("create_time", "sent_at", "time", "timestamp"))
        out.append({
            "id": str(mid),
            "handle": handle or "",
            "text": text or "",
            "sent_at": sent_at,
        })
    return out


# ── pure diff / delta logic (unit-tested against fixtures) ─────────────────

def new_items_since(seen_ids: set, items: list[dict], id_key: str = "id") -> list[dict]:
    """Items whose id is not already in seen_ids, in the order given."""
    return [it for it in items if str(it[id_key]) not in seen_ids]


def video_deltas(prev_videos: dict, curr_videos: list[dict]) -> dict:
    """video_id -> {views, likes, comments, shares, saves} deltas
    (curr - prev; prev defaults to 0 for a video never seen before, so its
    first-ever delta equals its raw stat, not a spurious huge jump)."""
    out = {}
    for row in curr_videos:
        vid = row["id"]
        prev = prev_videos.get(vid, {})
        out[vid] = {
            field: row[field] - prev.get(field, 0)
            for field in ("views", "likes", "comments", "shares", "saves")
        }
    return out


def format_summary(run_at: str, deltas: dict, new_comments: list[dict], new_dms: list[dict]) -> str:
    lines = [f"BL TikTok watch — {run_at}"]
    lines.append(f"Videos tracked: {len(deltas)}")
    for vid in sorted(deltas):
        d = deltas[vid]
        lines.append(
            f"  {vid}  views {d['views']:+d}  likes {d['likes']:+d}  "
            f"comments {d['comments']:+d}  shares {d['shares']:+d}  saves {d['saves']:+d}")
    lines.append(f"New comments: {len(new_comments)}")
    for c in new_comments:
        lines.append(f"  [{c['video_id']}] @{c['handle']}: {c['text'][:120]!r}")
    lines.append(f"New DMs: {len(new_dms)}")
    for m in new_dms:
        lines.append(f"  @{m['handle']}: {m['text'][:120]!r}")
    return "\n".join(lines)


# ── ledger I/O (state/bl-tiktok/) ───────────────────────────────────────────

def load_state(path: Path) -> dict:
    if not path.exists():
        return {"videos": {}, "seen_comment_ids": [], "seen_dm_ids": [], "last_run_at": None}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    """Write temp, then rename — a crash between two writes loses nothing.
    Same convention as tools/flow_ledger.py's save_ledger()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append_events(path: Path, events: list[dict]) -> None:
    if not events:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


# ── the pure orchestration step run() delegates to — this is what the unit
# tests exercise directly with fixture JSON, no browser involved ───────────

def process_run(raw_videos: list[dict], raw_comments_by_video: dict, raw_inbox: list[dict],
                 state: dict, run_at: str | None = None) -> tuple[dict, str, list[dict]]:
    """(new_state, summary_text, new_events). Pure — no I/O, no browser.

    raw_videos: list of ALREADY-NORMALIZED video stat dicts (the output of
    extract_video_stats_from_raw), one per video this run saw.
    raw_comments_by_video: {video_id: [normalized comment dicts]}.
    raw_inbox: normalized inbox message dicts.
    """
    run_at = run_at or _now_iso()
    prev_videos = state.get("videos", {})
    seen_comment_ids = set(state.get("seen_comment_ids", []))
    seen_dm_ids = set(state.get("seen_dm_ids", []))

    deltas = video_deltas(prev_videos, raw_videos)

    all_comments = [c for vid_comments in raw_comments_by_video.values() for c in vid_comments]
    new_comments = new_items_since(seen_comment_ids, all_comments)
    new_dms = new_items_since(seen_dm_ids, raw_inbox)

    new_state = {
        "videos": {
            row["id"]: {**{k: row[k] for k in ("views", "likes", "comments", "shares", "saves")},
                        "updated_at": run_at}
            for row in raw_videos
        },
        "seen_comment_ids": sorted(seen_comment_ids | {c["id"] for c in all_comments}),
        "seen_dm_ids": sorted(seen_dm_ids | {m["id"] for m in raw_inbox}),
        "last_run_at": run_at,
    }

    events = (
        [{"type": "comment", "seen_at": run_at, **c} for c in new_comments]
        + [{"type": "dm", "seen_at": run_at, **m} for m in new_dms]
    )

    summary = format_summary(run_at, deltas, new_comments, new_dms)
    return new_state, summary, events


def status_summary(path: Path) -> str:
    state = load_state(path)
    videos = state.get("videos", {})
    if not videos:
        return f"ledger empty or not found: {path}"
    lines = [f"ledger: {path}  ({len(videos)} videos tracked)",
             f"last run: {state.get('last_run_at') or 'never'}",
             f"comments seen: {len(state.get('seen_comment_ids', []))}",
             f"dms seen: {len(state.get('seen_dm_ids', []))}"]
    return "\n".join(lines)


# ── browser layer — UNVERIFIED against the live DOM/API, see module docstring ─

class BLTikTokBrowser:
    """Playwright-over-CDP adapter for the dedicated BL TikTok Chrome profile
    (scripts/bl-tiktok/launch-chrome-debug.sh, port 9224). Every method here
    is read-only by construction: there is no method that clicks reply, like,
    follow, or send — that capability simply does not exist in this class, so
    a future caller cannot accidentally wire it in by passing a new flag."""

    def __init__(self, cdp_url: str = CDP):
        self.cdp_url = cdp_url
        self._pw = None
        self._browser = None
        self.page = None

    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        ctx = self._browser.contexts[0]
        page = next((pg for pg in ctx.pages if "tiktok.com" in pg.url), None)
        if page is None:
            page = ctx.new_page()
            page.goto("https://www.tiktok.com/tiktokstudio/content",
                      wait_until="domcontentloaded", timeout=30_000)
        try:
            page.bring_to_front()
        except Exception:
            pass
        self.page = page
        return page

    def close(self) -> None:
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    def is_verification_wall(self) -> bool:
        try:
            body = (self.page.evaluate("() => document.body.innerText") or "").lower()
        except Exception:
            return False
        return any(m.lower() in body for m in _VERIFICATION_MARKERS)

    def is_logged_in(self) -> bool:
        """Best-effort: an unauthenticated tiktok.com page redirects to /login
        for any account-scoped route (tiktokstudio, /messages), and the
        homepage shows a login CTA rather than an avatar menu. UNVERIFIED —
        confirm against the live DOM the first time this account is signed
        in (see module docstring)."""
        try:
            if "/login" in self.page.url:
                return False
            return self.page.locator('div[data-e2e="channel-item"]').count() == 0
        except Exception:
            return False

    # -- Step 1: QR login (never types a password or code) ------------------

    def fetch_login_qr(self, out_path: Path) -> Path:
        """Confirmed live 2026-09-23 (this task, read-only probe, no account
        signed in): https://www.tiktok.com/login lists 7
        `div[data-e2e="channel-item"]` options; the QR one's visible text is
        "ใช้รหัส QR" (Thai locale). Clicking it navigates to
        https://www.tiktok.com/login/qrcode, which renders the QR as a single
        bare `<canvas>` (170x170 CSS px, no img/src). The code expires in
        ~1-2 minutes; always take a fresh capture."""
        page = self.page
        if "tiktok.com/login" not in page.url:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(2000)
        if self.is_verification_wall():
            raise VerificationWall("verification wall shown at /login")
        if "/login" not in page.url:
            raise RuntimeError(f"page is not on a /login route ({page.url}) — already signed in?")
        if "qrcode" not in page.url:
            items = page.locator('div[data-e2e="channel-item"]')
            qr_item = items.filter(has_text="QR").first
            qr_item.click(timeout=5000)
            page.wait_for_timeout(2000)
        if self.is_verification_wall():
            raise VerificationWall("verification wall shown after selecting QR login")
        canvas = page.locator("canvas").first
        canvas.wait_for(state="visible", timeout=10_000)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.screenshot(path=str(out_path))
        return out_path

    # -- Step 3: read-only collection — UNVERIFIED selectors/endpoints -------
    # No live logged-in session was available this task (Step 1 blocks on the
    # CEO's QR scan). These methods intercept the page's own XHR/JSON
    # (preferred over parsing pixels, per the task brief) by watching
    # `response` events for a URL matching a guessed TikTok Studio endpoint
    # pattern. THE PATTERNS BELOW ARE UNVERIFIED — the first live run must
    # open the real TikTok Studio content/comments/inbox pages with devtools
    # network capture, confirm the actual endpoint path(s), and correct
    # `_collect_json_from`'s callers below.

    def _collect_json_from(self, nav_url: str, url_pattern) -> list[dict]:
        import re
        pattern = url_pattern if isinstance(url_pattern, re.Pattern) else re.compile(url_pattern)
        captured: list[dict] = []

        def on_response(resp):
            if pattern.search(resp.url):
                try:
                    captured.append(resp.json())
                except Exception:
                    pass

        page = self.page
        page.on("response", on_response)
        try:
            page.goto(nav_url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(4000)
            if self.is_verification_wall():
                raise VerificationWall(f"verification wall shown at {nav_url}")
            if not self.is_logged_in():
                raise NotLoggedIn(f"not logged in at {nav_url}")
        finally:
            page.remove_listener("response", on_response)
        return captured

    def collect_video_stats_raw(self) -> list[dict]:
        """Raw JSON blobs from the TikTok Studio content/analytics list —
        pass each to extract_video_stats_from_raw(). Endpoint pattern
        UNVERIFIED (see method group docstring above)."""
        return self._collect_json_from(
            "https://www.tiktok.com/tiktokstudio/content",
            r"/tiktok/(studio|v1)/(content|item)(_list)?/")

    def collect_inbox_raw(self) -> list[dict]:
        """Raw JSON blobs from the inbox/messages view. Endpoint pattern
        UNVERIFIED (see method group docstring above)."""
        return self._collect_json_from(
            "https://www.tiktok.com/messages",
            r"/tiktok/(im|message)/(list|history)/")


# ── CLI ──────────────────────────────────────────────────────────────────────

def cmd_login_qr(args) -> int:
    browser = BLTikTokBrowser(args.cdp)
    try:
        browser.attach()
        path = browser.fetch_login_qr(args.out)
    except VerificationWall as e:
        print(f"VERIFICATION_WALL: {e} — STOP, do not attempt to solve this")
        return 2
    except RuntimeError as e:
        print(f"ALREADY_LOGGED_IN_OR_ERROR: {e}")
        return 0
    finally:
        browser.close()
    print(f"QR saved: {path}")
    print("Scan with the TikTok app on the black_liquidity account within ~1-2 minutes "
          "(TikTok expires the code) — re-run this command for a fresh one if it lapses.")
    return 0


def cmd_run(args) -> int:
    state = load_state(args.state)
    browser = BLTikTokBrowser(args.cdp)
    try:
        browser.attach()
        if browser.is_verification_wall():
            print("VERIFICATION_WALL — stopping, not attempting to solve it")
            return 2
        if not browser.is_logged_in():
            print("NOT_LOGGED_IN — run `login-qr` and have the CEO scan it first")
            return 1

        raw_video_blobs = browser.collect_video_stats_raw()
        raw_videos: list[dict] = []
        for blob in raw_video_blobs:
            raw_videos.extend(extract_video_stats_from_raw(blob))

        raw_comments_by_video: dict[str, list[dict]] = {}
        for row in raw_videos:
            vid = row["id"]
            comment_blobs = browser._collect_json_from(
                f"https://www.tiktok.com/tiktokstudio/content/{vid}/comments",
                r"/tiktok/(studio|v1)/comment(_list)?/")
            comments: list[dict] = []
            for blob in comment_blobs:
                comments.extend(extract_comments_from_raw(blob, vid))
            raw_comments_by_video[vid] = comments

        raw_inbox: list[dict] = []
        for blob in browser.collect_inbox_raw():
            raw_inbox.extend(extract_inbox_messages_from_raw(blob))
    except (VerificationWall, NotLoggedIn) as e:
        print(f"STOP: {e}")
        return 2
    finally:
        browser.close()

    new_state, summary, events = process_run(raw_videos, raw_comments_by_video, raw_inbox, state)
    save_state(args.state, new_state)
    append_events(args.events, events)
    print(summary)
    return 0


def cmd_status(args) -> int:
    print(status_summary(args.state))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_qr = sub.add_parser("login-qr", help="capture a fresh TikTok QR login code (never types a password)")
    p_qr.add_argument("--out", type=Path, default=DEFAULT_QR_OUT)
    p_qr.add_argument("--cdp", default=CDP)
    p_qr.set_defaults(func=cmd_login_qr)

    p_run = sub.add_parser("run", help="one read-only pass: stats + new comments + new DMs")
    p_run.add_argument("--cdp", default=CDP)
    p_run.add_argument("--state", type=Path, default=STATE_PATH)
    p_run.add_argument("--events", type=Path, default=EVENTS_PATH)
    p_run.set_defaults(func=cmd_run)

    p_status = sub.add_parser("status", help="one-screen ledger summary")
    p_status.add_argument("--state", type=Path, default=STATE_PATH)
    p_status.set_defaults(func=cmd_status)

    return ap


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
