#!/usr/bin/env python3
"""Weekly "are our tools worth it" report (tool-value plan §2-§3, task T1).

Plan: docs/plans/tool-value-weekly-and-enforcement-2026-10-13.md (CEO order 13 Oct 2026, via SomPong).

    bash scripts/hub/org-python.sh tools/tool_value.py collect [--week D] [--as-of T] [--dry-run]
    bash scripts/hub/org-python.sh tools/tool_value.py report  [--week D] [--as-of T] [--dry-run] [--no-send]
    bash scripts/hub/org-python.sh tools/tool_value.py context-delta --what TEXT --before N --after N --method TEXT --evidence TEXT --by TEXT

collect  reads every source of plan §2.0 that exists on this host, read-only, and writes ONE hub event per
         window: events(task_id NULL, actor=<host>, kind='tool_usage_week', payload=<json>). It writes the
         current window, and the previous one too when this host has no row for it yet (the back-fill).
report   builds the previous-vs-current table from the latest row per host and window. A window with no row
         from this host is computed live from local sources; a missing Mac or winbox row prints
         "ไม่มีข้อมูล (<host> ไม่ส่ง)", never a zero. Writes state/reports/tool-value/<week>.md + .json
         (gitignored: Agents-Core is public) and sends the Thai summary + table to SomPong (coo) once per week.

Labels: every cell carries one of วัดจริง (MEASURED), ประมาณการ (ESTIMATE), ขั้นต่ำ (lower bound) or
ไม่มีข้อมูล (no source). A source that cannot be read goes in `missing`; it is never counted as 0.
No model call and no paid call. This module reads no key: the OpenRouter numbers come from the rows
`tools/jev_lab.py balance` already wrote.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import traceback
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Runtime data (state/, ledgers, prototypes/) lives in the hub checkout. ORG_ROOT wins when set, as in
# lib/mailbox.py, so the code can run from a worktree against the real ledgers (read-only).
DATA_ROOT = Path(os.environ.get("ORG_ROOT") or ROOT)

BKK = ZoneInfo("Asia/Bangkok")
EVENT_KIND = "tool_usage_week"
SCHEMA = 1
ORG_HOST = "contabo"            # the host whose collect also reads the org-wide sources (quota, hub, GitHub)
HOSTS = ("contabo", "mac", "winbox")
HOST_TH = {"contabo": "Contabo", "mac": "Mac", "winbox": "winbox"}

QUOTA_HISTORY = DATA_ROOT / "state" / "reports" / "quota-history.jsonl"
DECISIONS_DIR = DATA_ROOT / "state" / "decisions"
SITES_DIR = ROOT / "config" / "decisions"
CREDIT_LEDGER = DATA_ROOT / "docs" / "ops" / "credit-ledger.jsonl"
OPENROUTER_BALANCE = DATA_ROOT / "docs" / "ops" / "jev-lab-2026-09-23" / "balance.jsonl"
PROTOTYPES_DIR = DATA_ROOT / "prototypes"
REPORT_DIR = DATA_ROOT / "state" / "reports" / "tool-value"
JULES_CONFIG = ROOT / "config" / "jules.yaml"
PLANS_CONFIG = ROOT / "config" / "plans.yaml"
TRANSCRIPT_HOMES = (
    Path("/root/.claude/projects"),
    Path("/home/sompong/.claude/projects"),
    Path("/home/secretary/.claude/projects"),
)
CODEX_SESSIONS = Path("/root/.codex/sessions")
# Plan §1: the 7 allowlisted repos + Console + Option were read for the Jules lower bound.
JULES_EXTRA_REPOS = ("PASAKON/MoonieX-Console", "PASAKON/MoonieX-Option")
JULES_BRANCH = re.compile(r"-\d{15,}$")      # Jules opens `<slug>-<sessionId>` branches
TASK_ID = re.compile(r"task-[0-9a-f]{8}")
OVERRIDE_LINE = re.compile(r"^[ \t]*override:[ \t]*(\S.*)$", re.IGNORECASE | re.MULTILINE)
HAIKU_55 = "claude-haiku-5-5"   # the model the CEO asks about ("Haiku ช่วยเราได้มากขึ้นแค่ไหน")
CAP_EPS = 0.005                # weekly_remaining at or under this = at the cap
RESET_JUMP = 0.2
RUNNER_SKILLS = {"codex": "CTO_Knowledge_Codex", "agy-gemini": "CTO_Knowledge_AGY",
                 "agy-claude": "CTO_Knowledge_AGY", "jules": "CTO_Knowledge_Jules",
                 "jev": "ALL_Knowledge_Jev", "claude-haiku": "CTO_Knowledge_Haiku"}
# COO's draft gate (CEO roadmap 14 Oct, phase 1 → 2); COO_Procedure_ToolValueWeekly owns final numbers.
PHASE_FIRST_PASS = 80
PHASE_MIN_JOBS = 10
PHASE_STABLE_DAYS = 14
RULE_COMMIT = re.compile(r"^skill\(([^)]*)\):\s*(rule|flip)\b")
ANTHROPIC_PRICE_CONFIRMED = datetime(2026, 10, 14, tzinfo=BKK)
MAX_GAP = timedelta(hours=2)   # a longer gap between quota samples is not counted as time at the cap
OUTSIDE_RUNNERS = ("codex", "agy")
# Proposed floors (plan §4.3 M3); the CEO sets the real ones (§7 Q1). Shown as "เกณฑ์ที่เสนอ".
FLOORS = {"bucket_used_pct": 50.0, "jules_sessions": 10, "jev_calls_per_site": 1}
JULES_CAPACITY_WEEK = 300 * 7  # CTO_Knowledge_Jules "Jules in Ultra": 300 sessions/day (BOUND, §7 Q2)
FIRST_REPORT_DAY = date(2026, 10, 19)
TH_MONTHS = ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")
LABEL_TH = {"measured": "วัดจริง", "estimate": "ประมาณการ", "lower": "ขั้นต่ำ", "bound": "เพดาน", "none": "ไม่มีข้อมูล"}
FIRST_REPORT_QUESTIONS = (
    "1. เกณฑ์ขั้นต่ำ: AGY/Codex ≥50% ของโควตาสัปดาห์ · Jules ≥10 session/สัปดาห์ · JEV ≥1 ครั้งต่อ site ใช้ได้ไหม",
    "2. แพ็กเกจ Google ที่จ่ายจริงคืออะไร ($100 ใน plans.yaml หรือ AI Ultra ตาม skill Jules) — CFO ยืนยัน",
    "3. เครดิต OpenRouter: JEV และ Haiku fallback หยุดเมื่อเครดิตหมด การเติมเงินเป็นการตัดสินใจของ CEO",
    "4. กฎ 'ใช้ runner นอกก่อน' (IRON §59 ข้อ 7) และการเปิดโหมดบล็อกของ hook Agent รอ CEO ดูตัวเลขสัปดาห์นี้ก่อน",
)


class SourceMissing(Exception):
    """A source this host cannot read. The reason is printed as ไม่มีข้อมูล, never as a zero."""


# ---------------------------------------------------------------------------------------------- windows

@dataclass(frozen=True)
class Window:
    start: datetime   # aware, UTC
    end: datetime     # aware, UTC, exclusive

    @property
    def key(self) -> str:
        return self.start.astimezone(BKK).date().isoformat()

    @property
    def days(self) -> float:
        return max((self.end - self.start).total_seconds() / 86400.0, 1e-9)

    def contains(self, ts: datetime | None) -> bool:
        return ts is not None and self.start <= ts < self.end

    def label(self) -> str:
        """Thai label, e.g. "6–12 ต.ค." or "13–19 ต.ค. (ถึง 07:00)"."""
        a = self.start.astimezone(BKK)
        b_excl = self.end.astimezone(BKK)
        b = b_excl - timedelta(seconds=1)
        if a.month == b.month:
            s = f"{a.day}–{b.day} {TH_MONTHS[b.month - 1]}"
        else:
            s = f"{a.day} {TH_MONTHS[a.month - 1]}–{b.day} {TH_MONTHS[b.month - 1]}"
        if b_excl.time() != time(0, 0):
            s += f" (ถึง {b_excl:%H:%M})"
        return s

    def as_json(self) -> dict:
        return {"start": iso(self.start), "end": iso(self.end), "key": self.key, "label": self.label()}


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def bkk_midnight(d: date) -> datetime:
    return datetime.combine(d, time(0, 0), tzinfo=BKK).astimezone(timezone.utc)


def parse_ts(val) -> datetime | None:
    """ISO-8601 (Z, +00:00, +0200 or naive = UTC) or epoch seconds to an aware UTC datetime; None if unreadable."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    s = str(val).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    m = re.match(r"^(.*[T ]\d\d:\d\d(?::\d\d(?:\.\d+)?)?)([+-]\d\d)(\d\d)$", s)
    if m:  # +0200 -> +02:00 (jev_lab writes time.strftime('%z'))
        s = f"{m.group(1)}{m.group(2)}:{m.group(3)}"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def windows(as_of: datetime, week: date | None = None) -> tuple[Window, Window]:
    """(previous, current). The current window never runs past `as_of`.

    --week D:   current = 7 days from D 00:00 BKK, previous = the 7 days before.
    first run:  on Mon 19 Oct 2026 the CEO's ranges (plan §3.1): Tue 6 -> Mon 12 Oct, Tue 13 -> Mon 19 07:00.
    otherwise:  current = the Mon-Sun BKK week that ended at the last Monday 00:00, previous = the one before.
    """
    now_bkk = as_of.astimezone(BKK)
    if week is not None:
        cur = Window(bkk_midnight(week), bkk_midnight(week + timedelta(days=7)))
        prev = Window(bkk_midnight(week - timedelta(days=7)), cur.start)
    elif now_bkk.date() == FIRST_REPORT_DAY:
        prev = Window(bkk_midnight(date(2026, 10, 6)), bkk_midnight(date(2026, 10, 13)))
        cur = Window(prev.end, datetime(2026, 10, 19, 7, 0, tzinfo=BKK).astimezone(timezone.utc))
    else:
        monday = now_bkk.date() - timedelta(days=now_bkk.weekday())
        cur = Window(bkk_midnight(monday - timedelta(days=7)), bkk_midnight(monday))
        prev = Window(bkk_midnight(monday - timedelta(days=14)), cur.start)
    as_of_utc = as_of.astimezone(timezone.utc)
    if cur.end > as_of_utc:
        cur = Window(cur.start, max(as_of_utc, cur.start))
    return prev, cur


# ---------------------------------------------------------------------------------------------- helpers

def _jsonl(path: Path) -> Iterable[dict]:
    """Rows of a JSONL file; a line that is not JSON is skipped. Raises SourceMissing when unreadable."""
    try:
        fh = path.open("rb")
    except FileNotFoundError:
        raise SourceMissing(f"{path} ไม่มีไฟล์")
    except PermissionError:
        raise SourceMissing(f"{path} อ่านไม่ได้ (permission)")
    with fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except ValueError:
                continue
            if isinstance(row, dict):
                yield row


def _family(model: str) -> str | None:
    m = (model or "").lower()
    if not m or m.startswith("<"):
        return None
    for fam in ("haiku", "sonnet", "opus", "fable"):
        if fam in m:
            return fam
    return "other"


def _load_yaml(path: Path) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# ---------------------------------------------------------------------------------------------- sources

def quota_usage(path: Path, win: Window) -> dict:
    """% of each weekly bucket used inside `win` = sum of drops between consecutive samples inside it
    (plan §3.1; handles mid-week resets), hours spent at the cap, and the reset dates seen."""
    by_bucket: dict[str, list[tuple[datetime, float, str | None]]] = {}
    history: dict[str, list[tuple[datetime, float, str | None]]] = {}
    errors: dict[str, int] = {}
    for row in _jsonl(path):
        ts = parse_ts(row.get("ts"))
        if ts is not None and ts < win.end and not row.get("error") and row.get("weekly_remaining") is not None:
            history.setdefault(row.get("provider") or "?", []).append(
                (ts, float(row["weekly_remaining"]), row.get("weekly_resets_at")))
        if not win.contains(ts):
            continue
        b = row.get("provider") or "?"
        wr = row.get("weekly_remaining")
        if row.get("error") or wr is None:
            errors[b] = errors.get(b, 0) + 1
            continue
        by_bucket.setdefault(b, []).append((ts, float(wr), row.get("weekly_resets_at")))
    if not by_bucket:
        raise SourceMissing(f"{path.name}: ไม่มี sample ในช่วง {win.label()}")
    out: dict[str, dict] = {}
    for b, rows in by_bucket.items():
        rows.sort(key=lambda r: r[0])
        used = 0.0
        cap_s = 0.0
        cap_starts: list[str] = []
        resets: list[str] = []
        for (t0, w0, _), (t1, w1, _) in zip(rows, rows[1:]):
            used += max(0.0, w0 - w1)
            if w0 <= CAP_EPS and w1 <= CAP_EPS and t1 - t0 <= MAX_GAP:
                cap_s += (t1 - t0).total_seconds()
        was_capped = False
        for t, w, r in rows:
            if w <= CAP_EPS and not was_capped:
                cap_starts.append(iso(t))
            was_capped = w <= CAP_EPS
            rd = parse_ts(r)
            if rd is not None:
                day = rd.astimezone(BKK).date().isoformat()
                if day not in resets:
                    resets.append(day)
        out[b] = {
            "used_pct": round(used * 100, 1),
            "at_cap_hours": round(cap_s / 3600, 1),
            "cap_starts": cap_starts,
            "samples": len(rows),
            "errors": errors.get(b, 0),
            "resets_seen": resets,
            "last_remaining_pct": round(rows[-1][1] * 100, 1),
        }
    if "claude" in out:
        for samples in history.values():
            samples.sort(key=lambda s: s[0])
        resets = []
        full_since = None
        rows = history["claude"]
        for (t0, w0, _), (t1, w1, _) in zip(rows, rows[1:]):
            full_since = (full_since or iso(t0)) if w0 <= CAP_EPS else None
            if win.contains(t1) and w1 - w0 >= RESET_JUMP:
                others = {}
                for bucket, samples in history.items():
                    eligible = [s for s in samples if s[0] <= t1]
                    if bucket != "claude" and eligible:
                        ts, w, _ = eligible[-1]
                        others[bucket] = {"used_pct": round((1 - w) * 100, 1), "sample_ts": iso(ts)}
                resets.append({"at": iso(t1), "claude_used_pct": round((1 - w0) * 100, 1),
                               "full_since": full_since, "others": others})
        out["claude"]["resets"] = resets
    return out


def _first_block_override(description: str | None) -> str | None:
    from lib.router import header
    m = OVERRIDE_LINE.search(header(description))
    return m.group(1).strip() if m else None


def _reason_code(reason: str) -> str:
    """First word of an override reason, lower-case, for grouping (gate v2 makes it a closed list)."""
    word = re.split(r"[\s:;,.()—–]+", reason.strip().lower(), maxsplit=1)[0]
    from tools.route import REASON_CODES
    return word if word in REASON_CODES else "free-text"


def hub_tasks_summary(tasks: list[dict], events: list[dict], win: Window) -> dict:
    """Worker tasks created in `win`, per runner: status counts, reopens, override reasons, the seed
    estimate of Claude quota the outside runners saved (plan §2.6 step 1)."""
    from tools import forecast

    seeds = forecast.SEED_COSTS["claude"]
    statuses: dict[str, list[str]] = {}
    for e in sorted(events, key=lambda e: (e.get("ts") or "", e.get("id") or 0)):
        k = e.get("kind") or ""
        if k.startswith("status_"):
            statuses.setdefault(e.get("task_id"), []).append(k[len("status_"):])
    out: dict[str, dict] = {}
    for t in tasks:
        if not win.contains(parse_ts(t.get("created_at"))):
            continue
        runner = (t.get("runner") or "").strip() or "unrouted"
        r = out.setdefault(runner, {"tasks": 0, "status": {}, "reopens": 0, "routed": 0,
                                    "override": 0, "override_codes": {}, "roles": {},
                                    "seed_claude_pct_done": 0.0, "done_sizes": {}, "done_clean": 0,
                                    "iter_sum": 0, "iter_n": 0, "router_skipped": 0})
        r["tasks"] += 1
        st = t.get("status") or "?"
        r["status"][st] = r["status"].get(st, 0) + 1
        role = t.get("role") or "?"
        r["roles"][role] = r["roles"].get(role, 0) + 1
        seq = statuses.get(t.get("id"), [])
        reopens = sum(1 for a, b in zip(seq, seq[1:]) if a == "review" and b in ("in_progress", "pending"))
        r["reopens"] += reopens
        if "router:" in (t.get("delegate_log") or ""):
            r["routed"] += 1
        reason = _first_block_override(t.get("description"))
        if runner != "unrouted" and "router:" not in (t.get("delegate_log") or "") and not reason:
            r["router_skipped"] += 1
        if reason:
            r["override"] += 1
            code = _reason_code(reason)
            r["override_codes"][code] = r["override_codes"].get(code, 0) + 1
        if st == "done":
            iteration = t.get("iteration") or 0
            r["iter_sum"] += iteration + 1
            r["iter_n"] += 1
            reopened = any(a in ("review", "done") and b in ("in_progress", "pending") for a, b in zip(seq, seq[1:]))
            clean = not reopened and iteration == 0
            r["done_clean"] += int(clean)
            touches = t.get("touches")
            if isinstance(touches, str):
                try:
                    touches = json.loads(touches)
                except ValueError:
                    touches = []
            size = forecast.infer_size(touches or [], t.get("description") or "")
            r["done_sizes"][size] = r["done_sizes"].get(size, 0) + 1
            if clean:
                r["seed_claude_pct_done"] += float(seeds[size])
    for r in out.values():
        r["seed_claude_pct_done"] = round(r["seed_claude_pct_done"], 1)
    return out


def fetch_hub(win: Window) -> tuple[list[dict], list[dict]]:
    """Tasks created in `win` (a day of slack each side, filtered exactly in Python) and their status events."""
    from lib import db
    lo = iso(win.start - timedelta(days=1))
    hi = iso(win.end + timedelta(days=1))
    with db.get_conn(readonly=True) as conn:
        tasks = [dict(r) for r in conn.execute(
            "SELECT id, role, runner, runner_model, model_hint, status, description, delegate_log, touches,"
            " host, created_at, iteration FROM tasks WHERE created_at >= ? AND created_at < ?", (lo, hi)).fetchall()]
        ids = [t["id"] for t in tasks]
        events: list[dict] = []
        for i in range(0, len(ids), 200):
            chunk = ids[i:i + 200]
            marks = ",".join("?" for _ in chunk)
            events += [dict(r) for r in conn.execute(
                f"SELECT id, task_id, kind, ts FROM events WHERE task_id IN ({marks}) AND kind LIKE 'status_%'",
                chunk).fetchall()]
    return tasks, events


def transcript_usage(homes: Iterable[Path], win: Window) -> tuple[dict, list[dict]]:
    """Assistant messages and tokens per model family in Claude Code transcripts, deduped by message.id
    (Claude Code rewrites one message several times; a plain sum double-counts about 2x). Streams line
    by line; keeps one small record per message id. Returns (summary, missing)."""
    seen: dict[str, list] = {}   # id -> [model, out, in, cache_create, cache_read, sidechain, home, kind, task]
    missing: list[dict] = []
    files = 0
    homes_read: list[str] = []
    floor = win.start.timestamp()
    for home in homes:
        if not home.exists():
            missing.append({"source": f"transcripts:{home}", "reason": "ไม่มีโฟลเดอร์"})
            continue
        try:
            paths = [p for p in home.rglob("*.jsonl") if p.stat().st_mtime >= floor]
        except PermissionError:
            missing.append({"source": f"transcripts:{home}", "reason": "อ่านไม่ได้ (permission)"})
            continue
        homes_read.append(str(home))
        for p in paths:
            task = TASK_ID.search(str(p.relative_to(home)))
            kind = "worker" if task else "clevel"
            files += 1
            try:
                fh = p.open("rb")
            except OSError as e:
                missing.append({"source": f"transcripts:{p}", "reason": type(e).__name__})
                continue
            with fh:
                for raw in fh:
                    if b'"assistant"' not in raw:
                        continue
                    try:
                        row = json.loads(raw)
                    except ValueError:
                        continue
                    if not isinstance(row, dict) or row.get("type") != "assistant":
                        continue
                    if not win.contains(parse_ts(row.get("timestamp"))):
                        continue
                    msg = row.get("message") or {}
                    model = msg.get("model") or ""
                    mid = msg.get("id")
                    if _family(model) is None or not mid:
                        continue
                    u = msg.get("usage") or {}
                    vals = [int(u.get(k) or 0) for k in
                            ("output_tokens", "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")]
                    cur = seen.get(mid)
                    if cur is None:
                        seen[mid] = [model, *vals, bool(row.get("isSidechain")), str(home), kind,
                                     task.group() if task else None]
                    else:
                        for i, v in enumerate(vals, start=1):
                            cur[i] = max(cur[i], v)
    if not homes_read:
        raise SourceMissing("ไม่มี transcript home ที่อ่านได้")
    fams: dict[str, dict] = {}
    models: dict[str, dict] = {}
    per_home: dict[str, int] = {}
    by_kind = {k: dict(messages=0, output_tokens=0, input_tokens=0, cache_creation_tokens=0)
               for k in ("worker", "clevel")}
    task_ids = set()
    for model, out_t, in_t, cc, cr, side, home, kind, task in seen.values():
        for key, value in zip(by_kind[kind], (1, out_t, in_t, cc)):
            by_kind[kind][key] += value
        if task:
            task_ids.add(task)
        m = models.setdefault(model, {"messages": 0, "output_tokens": 0})
        m["messages"] += 1
        m["output_tokens"] += out_t
        f = fams.setdefault(_family(model), {"messages": 0, "output_tokens": 0, "input_tokens": 0, "cache_creation_tokens": 0,
                                  "cache_read_tokens": 0, "sidechain_messages": 0, "sidechain_output_tokens": 0})
        f["messages"] += 1
        f["output_tokens"] += out_t
        f["input_tokens"] += in_t
        f["cache_creation_tokens"] += cc
        f["cache_read_tokens"] += cr
        if side:
            f["sidechain_messages"] += 1
            f["sidechain_output_tokens"] += out_t
        per_home[home] = per_home.get(home, 0) + 1
    return {"families": fams, "models": models, "files_scanned": files, "homes_read": homes_read,
            "messages_per_home": per_home, "by_kind": by_kind, "worker_task_ids": sorted(task_ids)}, missing


def codex_usage(root: Path, win: Window) -> dict:
    """Codex CLI sessions started in `win` (session_meta timestamp) and their final cumulative tokens."""
    if not root.exists():
        raise SourceMissing(f"{root} ไม่มีโฟลเดอร์")
    sessions = 0
    with_task = 0
    per_day: dict[str, int] = {}
    tok = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0}
    max_used = None
    d = (win.start - timedelta(days=1)).date()
    last = (win.end + timedelta(days=1)).date()
    while d <= last:
        for p in sorted((root / f"{d:%Y}" / f"{d:%m}" / f"{d:%d}").glob("rollout-*.jsonl")):
            start = None
            cwd = ""
            last_tc = None
            with p.open("rb") as fh:
                for i, raw in enumerate(fh):
                    if i == 0:
                        try:
                            meta = json.loads(raw)
                            start = parse_ts((meta.get("payload") or {}).get("timestamp") or meta.get("timestamp"))
                            cwd = str((meta.get("payload") or {}).get("cwd") or "")
                        except ValueError:
                            pass
                    elif b'"token_count"' in raw:
                        last_tc = raw
            if not win.contains(start):
                continue
            sessions += 1
            day = start.astimezone(BKK).date().isoformat()
            per_day[day] = per_day.get(day, 0) + 1
            if TASK_ID.search(cwd):
                with_task += 1
            if last_tc:
                try:
                    pl = json.loads(last_tc).get("payload") or {}
                except ValueError:
                    pl = {}
                total = ((pl.get("info") or {}).get("total_token_usage") or {})
                for k in tok:
                    tok[k] += int(total.get(k) or 0)
                used = ((pl.get("rate_limits") or {}).get("primary") or {}).get("used_percent")
                if used is not None:
                    max_used = max(float(used), max_used or 0.0)
        d += timedelta(days=1)
    return {"sessions": sessions, "sessions_with_task": with_task, "sessions_per_day": per_day,
            "tokens": tok, "max_used_percent_seen": max_used}


def decision_usage(ledger_dir: Path, sites_dir: Path, win: Window) -> dict:
    """decide() calls in `win` per site and provider, $ spent and $ counterfactual (lib/decision_ledger.py)."""
    if not ledger_dir.exists():
        raise SourceMissing(f"{ledger_dir} ไม่มีโฟลเดอร์")
    wired = sorted(p.stem for p in sites_dir.glob("*.yaml") if not p.name.startswith("_")) if sites_dir.exists() else []
    months = sorted({(win.start + timedelta(days=i)).strftime("%Y-%m") for i in range(int(win.days) + 2)})
    sites: dict[str, dict] = {}
    providers: dict[str, int] = {}
    cost = 0.0
    counterfactual = 0.0
    calls = 0
    for m in months:
        path = ledger_dir / f"{m}.jsonl"
        if not path.exists():
            continue
        for row in _jsonl(path):
            if not win.contains(parse_ts(row.get("ts"))):
                continue
            calls += 1
            site = row.get("site") or "?"
            prov = row.get("provider") or "?"
            s = sites.setdefault(site, {"calls": 0, "providers": {}})
            s["calls"] += 1
            s["providers"][prov] = s["providers"].get(prov, 0) + 1
            providers[prov] = providers.get(prov, 0) + 1
            cost += float(row.get("cost_usd") or 0.0)
            counterfactual += float(row.get("counterfactual_usd") or 0.0)
    return {"calls": calls, "providers": providers, "sites": sites, "wired_sites": wired,
            "wired_sites_called": sorted(s for s in sites if s in wired),
            "cost_usd": round(cost, 6), "counterfactual_usd": round(counterfactual, 6),
            "saved_usd": round(counterfactual - cost, 6)}


def agy_browse_usage(paths: Iterable[Path], win: Window) -> dict:
    """agy_browse calls in `win` from the main log and every worktree copy still on disk. Each call keeps
    its timestamp as a key so the report can union hosts and hub events without double counting."""
    keys: set[str] = set()
    failed: set[str] = set()
    verbs: dict[str, int] = {}
    read = []
    for p in paths:
        if not p.exists():
            continue
        read.append(str(p))
        for row in _jsonl(p):
            ts = parse_ts(row.get("ts"))
            if not win.contains(ts):
                continue
            key = f"{row.get('ts')}|{row.get('verb')}|{row.get('port')}"
            if key in keys:
                continue
            keys.add(key)
            verbs[row.get("verb") or "?"] = verbs.get(row.get("verb") or "?", 0) + 1
            if row.get("exit") not in (0, None):
                failed.add(key)
    if not read:
        raise SourceMissing("ไม่มีไฟล์ agy-browse.jsonl")
    return {"calls": len(keys), "failed": len(failed), "verbs": verbs, "files": read, "keys": sorted(keys)[:2000]}


def agy_browse_paths(root: Path = DATA_ROOT) -> list[Path]:
    paths = [root / "state" / "agy-browse.jsonl"]
    wt = root / "worktrees"
    if wt.exists():
        paths += sorted(wt.glob("*/state/agy-browse.jsonl"))
    return paths


def credit_usage(path: Path, win: Window) -> dict:
    """Generation credits logged by tools/credit_ledger.py in `win` (context for the Google plan only)."""
    engines: dict[str, dict] = {}
    rows = 0
    for row in _jsonl(path):
        if not win.contains(parse_ts(row.get("ts"))):
            continue
        rows += 1
        key = f"{row.get('engine') or '?'}:{row.get('unit') or '?'}"
        e = engines.setdefault(key, {"rows": 0, "amount": 0.0})
        e["rows"] += 1
        e["amount"] += float(row.get("amount") or 0.0)
    return {"rows": rows, "engines": engines}


def openrouter_balance(path: Path, win: Window) -> dict:
    """The latest OpenRouter balance read at or before the window's end, and the account usage between the
    first and last reads inside the window (both MEASURED at their read times; the key is shared)."""
    before = []
    for row in _jsonl(path):
        at = parse_ts(row.get("at"))
        if at is not None and at < win.end:
            before.append((at, row))
    if not before:
        raise SourceMissing(f"{path.name}: ยังไม่มีการอ่านยอดก่อน {win.label()}")
    before.sort(key=lambda r: r[0])
    at, last = before[-1]
    inside = [r for t, r in before if t >= win.start]
    credits, usage = last.get("account_total_credits"), last.get("account_total_usage")
    out = {"read_at": iso(at), "read_inside_window": bool(inside),
           "account_credits_usd": credits, "account_usage_usd": usage,
           "account_remaining_usd": round(credits - usage, 2) if credits is not None and usage is not None else None,
           "key_usage_weekly_usd": last.get("key_usage_weekly"), "usage_between_reads_usd": None, "reads_in_window": len(inside)}
    if len(inside) >= 2:
        a, b = inside[0].get("account_total_usage"), inside[-1].get("account_total_usage")
        if a is not None and b is not None:
            out["usage_between_reads_usd"] = round(b - a, 2)
    return out


def bl_jev_usage(prototypes: Path, win: Window) -> dict:
    """BL JevEditor episodes whose decisions.jsonl changed in `win` (file mtime: the rows carry no time)
    and scoreboard rows scored in `win`. Main checkout only; worktree copies are not episodes."""
    if not prototypes.exists():
        raise SourceMissing(f"{prototypes} ไม่มีโฟลเดอร์")
    eps = set()
    for p in list(prototypes.glob("bl-*/decisions.jsonl")) + list(prototypes.glob("bl-*/*/decisions.jsonl")):
        if win.contains(datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)):
            eps.add(p.relative_to(prototypes).parts[0])
    scored = []
    sb = prototypes / "bl-jev-scoreboard" / "scoreboard.jsonl"
    if sb.exists():
        for row in _jsonl(sb):
            if win.contains(parse_ts(row.get("scored_at") or row.get("ts"))):
                scored.append({"episode": row.get("episode"), "net_saved_usd": row.get("net_saved_usd")})
    return {"episodes_with_decisions": sorted(eps), "scoreboard_rows": scored}


def _gh(args: list[str]) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip().splitlines()[-1:] or ["gh failed"])
    return r.stdout


def jules_repos() -> list[str]:
    cfg = _load_yaml(JULES_CONFIG)
    repos = [r["repo"] for r in cfg.get("repos") or [] if r.get("repo")]
    return repos + [r for r in JULES_EXTRA_REPOS if r not in repos]


def jules_github(repos: Iterable[str], win: Window, run: Callable[[list[str]], str] = _gh) -> dict:
    """PRs from a Jules session branch (`<slug>-<sessionId>`), created or merged in `win`. A lower bound on
    Jules use: a session that opened no PR is invisible here (the session count needs the Mac, T5)."""
    since = (win.start - timedelta(days=1)).date().isoformat()
    created = merged = 0
    per_repo: dict[str, int] = {}
    failed: list[dict] = []
    ok = 0
    for repo in repos:
        try:
            out = run(["pr", "list", "--repo", repo, "--state", "all", "--limit", "200",
                       "--search", f"updated:>={since}", "--json", "headRefName,createdAt,mergedAt,state,number"])
            prs = json.loads(out or "[]")
        except Exception as e:  # noqa: BLE001 — one unreadable repo must not hide the others
            failed.append({"repo": repo, "reason": str(e)[:200]})
            continue
        ok += 1
        for pr in prs:
            if not JULES_BRANCH.search(pr.get("headRefName") or ""):
                continue
            if win.contains(parse_ts(pr.get("createdAt"))):
                created += 1
                per_repo[repo] = per_repo.get(repo, 0) + 1
            if win.contains(parse_ts(pr.get("mergedAt"))):
                merged += 1
    if ok == 0:
        raise SourceMissing("gh อ่าน repo ไม่ได้เลย: " + "; ".join(f["reason"] for f in failed[:2]))
    return {"prs_created": created, "prs_merged": merged, "per_repo": per_repo,
            "repos_read": ok, "repos_failed": failed}


def _git(args: list[str]) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, timeout=30,
                          capture_output=True, text=True).stdout


def skill_commits(win: Window, run: Callable[[list[str]], str] = _git) -> dict:
    """Skill presence and commits on the published main branch."""
    skills = {}
    since = iso(min(win.start, win.end - timedelta(days=PHASE_STABLE_DAYS)))
    for skill in sorted(set(RUNNER_SKILLS.values())):
        path = f".claude/skills/{skill}/SKILL.md"
        exists = True
        try:
            run(["cat-file", "-e", f"origin/main:{path}"])
        except subprocess.CalledProcessError:
            exists = False
        try:
            log = run(["log", "origin/main", f"--since={since}", f"--until={iso(win.end)}",
                       "--format=%cI%x09%s", "--", path])
        except (subprocess.SubprocessError, OSError) as e:
            raise SourceMissing(f"git log {skill}: {e}") from e
        commits = []
        for line in log.splitlines():
            ts, sep, subject = line.partition("\t")
            if sep and parse_ts(ts) is not None:
                commits.append({"ts": iso(parse_ts(ts)), "subject": subject})
        skills[skill] = {"exists": exists, "commits": commits}
    return {"ref": "origin/main", "skills": skills}


def _event_payload(value) -> dict | None:
    try:
        p = json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return None
    return p if isinstance(p, dict) and p.get("schema") == SCHEMA else None


def fetch_runner_fit(until: datetime) -> list[dict]:
    """Recent finished jobs, including history needed by the phase gate."""
    from lib import db
    with db.get_conn(readonly=True) as conn:
        rows = conn.execute("SELECT ts, task_id, payload FROM events WHERE kind=? AND ts < ? ORDER BY ts, id",
                            ("runner_fit", iso(until))).fetchall()
    records = []
    keys = ("runner", "model", "bucket", "job_type", "result", "fail_reason", "first_pass",
            "reviewer_fix", "iteration", "minutes")
    for row in rows:
        p = _event_payload(row["payload"])
        ts = parse_ts(row["ts"])
        if p is not None and ts is not None and ts < until:
            records.append(dict(ts=iso(ts), task_id=row["task_id"], **{k: p.get(k) for k in keys}))
    return sorted(records, key=lambda r: r["ts"])[-2000:]


def fetch_context_deltas(win: Window) -> list[dict]:
    """Measurements are selected by measurement time, not event creation time."""
    from lib import db
    with db.get_conn(readonly=True) as conn:
        rows = conn.execute("SELECT payload FROM events WHERE kind=? ORDER BY ts, id",
                            ("context_delta",)).fetchall()
    records = []
    for row in rows:
        p = _event_payload(row["payload"])
        if p is not None and win.contains(parse_ts(p.get("at"))):
            records.append(p)
    return sorted(records, key=lambda p: parse_ts(p["at"]))


def cell_key(rec: dict) -> str:
    if rec["runner"] == "claude":
        family = _family(rec.get("model"))
        return "claude-" + family if family else "claude"
    return rec.get("bucket") or rec["runner"]


def fit_cells(records: list[dict], skills_src: dict | None, win: Window) -> tuple[list[dict], dict]:
    """Window outcomes and the draft phase gate per runner and job type."""
    groups = {}
    for rec in records:
        ts = parse_ts(rec.get("ts"))
        if ts is not None and ts < win.end:
            groups.setdefault((cell_key(rec), rec["job_type"]), []).append(rec)
    rows = []
    for (cell, job), history in sorted(groups.items()):
        history.sort(key=lambda r: parse_ts(r["ts"]))
        current = [r for r in history if win.contains(parse_ts(r["ts"]))]
        if not current:
            continue
        last = history[-PHASE_MIN_JOBS:]
        pct = lambda rs: int(round(100 * sum(bool(r.get("first_pass")) for r in rs) / len(rs)))
        skill = RUNNER_SKILLS.get(cell)
        info = (skills_src.get("skills", {}).get(skill) if skills_src is not None else None)
        commits = info.get("commits", []) if info else []
        stable = Window(win.end - timedelta(days=PHASE_STABLE_DAYS), win.end)
        change = None if skills_src is None else any(
            stable.contains(parse_ts(c["ts"])) and (m := RULE_COMMIT.match(c["subject"]))
            and skill in [s.strip() for s in m.group(1).split(",")] for c in commits)
        if len(last) < PHASE_MIN_JOBS:
            why = f"ยังไม่ถึง 10 งาน ({len(last)})"
        elif pct(last) < PHASE_FIRST_PASS:
            why = f"first-pass {pct(last)}% < 80%"
        elif skill and change:
            why = "skill เปลี่ยน rule ใน 14 วัน"
        elif skill and change is None:
            why = "ไม่มีข้อมูล skill"
        else:
            why = "ผ่านเกณฑ์"
        minutes = [r["minutes"] for r in current if r.get("minutes") is not None]
        rows.append(dict(cell=cell, job_type=job, jobs=len(current),
                         **{k: sum(r["result"] == k for r in current) for k in ("pass", "redo", "fail")},
                         first_pass_pct=pct(current),
                         redo_pct=int(round(100 * sum(r["result"] == "redo" for r in current) / len(current))),
                         iter_avg=round(statistics.mean((r.get("iteration") or 0) + 1 for r in current), 1),
                         minutes_avg=round(statistics.mean(minutes), 1) if minutes else None,
                         last10_n=len(last), last10_first_pass_pct=pct(last), skill=skill,
                         skill_exists=info.get("exists") if info else None,
                         skill_edits=sum(win.contains(parse_ts(c["ts"])) for c in commits) if skills_src is not None else None,
                         rule_change=change, phase=2 if why == "ผ่านเกณฑ์" else 1, why=why))
    passed = sum(r["phase"] == 2 for r in rows)
    return rows, {"used": len(rows), "passed": passed,
                  "phase": 3 if rows and passed == len(rows) else 2 if passed else 1}


# ---------------------------------------------------------------------------------------------- collect

def collect(win: Window, host: str, *, org: bool, now: datetime | None = None,
            homes: Iterable[Path] = TRANSCRIPT_HOMES) -> dict:
    """One host's payload for one window. Every source is tried; a failure lands in `missing`."""
    sources: dict[str, dict] = {}
    missing: list[dict] = []

    def run(name: str, fn: Callable[[], dict]) -> None:
        try:
            sources[name] = fn()
        except SourceMissing as e:
            missing.append({"source": name, "reason": str(e)})
        except Exception as e:  # noqa: BLE001 — a broken reader must not sink the week
            traceback.print_exc(file=sys.stderr)
            missing.append({"source": name, "reason": f"{type(e).__name__}: {e}"[:300]})

    def transcripts() -> dict:
        summary, miss = transcript_usage(homes, win)
        missing.extend(miss)
        return summary

    if org:
        run("runner_fit", lambda: {"records": fetch_runner_fit(win.end)})
        run("skill_commits", lambda: skill_commits(win, run=_git))
        run("context_deltas", lambda: {"records": fetch_context_deltas(win)})
        run("quota", lambda: quota_usage(QUOTA_HISTORY, win))
        run("hub_tasks", lambda: hub_tasks_summary(*fetch_hub(win), win))
        run("jules_github", lambda: jules_github(jules_repos(), win, run=_gh))
        run("openrouter", lambda: openrouter_balance(OPENROUTER_BALANCE, win))
    run("transcripts", transcripts)
    run("codex_rollouts", lambda: codex_usage(CODEX_SESSIONS, win))
    run("decisions", lambda: decision_usage(DECISIONS_DIR, SITES_DIR, win))
    run("agy_browse", lambda: agy_browse_usage(agy_browse_paths(), win))
    run("credit_ledger", lambda: credit_usage(CREDIT_LEDGER, win))
    run("bl_jev", lambda: bl_jev_usage(PROTOTYPES_DIR, win))
    return {"schema": SCHEMA, "host": host, "org": org, "window": win.as_json(),
            "collected_at": iso(now or datetime.now(timezone.utc)), "sources": sources, "missing": missing}


def write_event(payload: dict, *, kind: str = EVENT_KIND) -> None:
    from lib import db
    with db.get_conn() as conn:
        db.log_event(conn, None, payload["by"] if kind == "context_delta" else payload["host"], kind, payload)


def read_events(since: datetime) -> list[dict]:
    from lib import db
    with db.get_conn(readonly=True) as conn:
        rows = conn.execute("SELECT actor, payload, ts FROM events WHERE kind=? AND ts >= ? ORDER BY id",
                            (EVENT_KIND, iso(since))).fetchall()
    out = []
    for r in rows:
        try:
            p = json.loads(r["payload"])
        except (TypeError, ValueError):
            continue
        if isinstance(p, dict) and p.get("schema") == SCHEMA:
            out.append(p)
    return out


def latest_rows(events: list[dict], win: Window) -> dict[str, dict]:
    """The newest payload per host whose window is exactly `win` (later rows win)."""
    out: dict[str, dict] = {}
    for p in events:
        w = p.get("window") or {}
        if w.get("start") == iso(win.start) and w.get("end") == iso(win.end):
            out[p.get("host")] = p
    return out


# ---------------------------------------------------------------------------------------------- report

def _cell(value, label: str, note: str = "") -> dict:
    return {"value": value, "label": label, "note": note}


def _none(reason: str) -> dict:
    return _cell(None, "none", reason)


def _src(rows: dict[str, dict], host: str, name: str):
    p = rows.get(host)
    if not p:
        return None
    return (p.get("sources") or {}).get(name)


def _org_src(rows: dict[str, dict], name: str):
    for p in rows.values():
        if p.get("org") and name in (p.get("sources") or {}):
            return p["sources"][name]
    return None


def _org_missing(rows: dict[str, dict], name: str) -> str:
    for p in rows.values():
        if p.get("org"):
            for m in p.get("missing") or []:
                if m.get("source") == name:
                    return f"ไม่มีข้อมูล ({m.get('reason')})"
            return "ไม่มีข้อมูล"
    return f"ไม่มีข้อมูล ({HOST_TH[ORG_HOST]} ไม่ส่ง)"


def _host_sum(rows: dict[str, dict], name: str, fn: Callable[[dict], float | int | None],
              hosts: Iterable[str]) -> tuple[float | int | None, list[str], list[str]]:
    """Sum fn(source) over the hosts that sent it. Returns (total or None, hosts counted, hosts missing)."""
    total = None
    got, gone = [], []
    for h in hosts:
        s = _src(rows, h, name)
        v = fn(s) if s is not None else None
        if v is None:
            gone.append(h)
            continue
        got.append(h)
        total = v if total is None else total + v
    return total, got, gone


def _scope(got: list[str], gone: list[str]) -> str:
    parts = []
    if got:
        parts.append("+".join(HOST_TH[h] for h in got))
    if gone:
        parts.append("ไม่มีข้อมูล (" + ", ".join(HOST_TH[h] for h in gone) + ")")
    return " · ".join(parts)


def _plan_usd_week(provider: str, at: datetime, plans: dict) -> float | None:
    prov = (plans.get("providers") or {}).get(provider) or {}
    usd = None
    for p in prov.get("plans") or []:
        frm = parse_ts(str(p.get("from")))
        if frm is not None and frm <= at:
            usd = float(p.get("usd"))
    return usd * 12 / 52 if usd is not None else None


def build_rows(rows: dict[str, dict], win: Window, hosts: Iterable[str], plans: dict) -> dict[str, dict]:
    """Every metric of the table for one window, as labelled cells."""
    hosts = tuple(hosts)
    c: dict[str, dict] = {}
    q = _org_src(rows, "quota")
    for b, name in (("claude", "claude"), ("codex", "codex"), ("agy-gemini", "agy_gemini"), ("agy-claude", "agy_claude")):
        if q and b in q:
            note = f"รีเซ็ต {', '.join(q[b]['resets_seen'])}" if b == "codex" and q[b]["resets_seen"] else ""
            c[f"{name}_used_pct"] = _cell(q[b]["used_pct"], "measured", note)
        else:
            c[f"{name}_used_pct"] = _none(_org_missing(rows, "quota"))
    if q and "claude" in q:
        starts = q["claude"].get("cap_starts") or []
        note = ("เริ่ม " + ", ".join(f"{parse_ts(x).astimezone(BKK):%d/%m %H:%M}" for x in starts)) if starts else ""
        c["claude_cap_hours"] = _cell(q["claude"]["at_cap_hours"], "measured", note)
    else:
        c["claude_cap_hours"] = _none(_org_missing(rows, "quota"))

    ht = _org_src(rows, "hub_tasks")
    for runner in ("claude", "codex", "agy", "unrouted"):
        if ht is None:
            c[f"tasks_{runner}"] = _none(_org_missing(rows, "hub_tasks"))
            continue
        r = ht.get(runner) or {"tasks": 0, "status": {}}
        done = r["status"].get("done", 0)
        c[f"tasks_{runner}"] = _cell(r["tasks"], "measured", f"เสร็จ {done}")
    if ht is not None:
        cl = ht.get("claude") or {}
        codes = cl.get("override_codes") or {}
        top = ", ".join(f"{'ข้อความอิสระ' if k == 'free-text' else k} {v}"
                        for k, v in sorted(codes.items(), key=lambda kv: -kv[1]))
        c["claude_pinned"] = _cell(cl.get("override", 0), "measured", top)
        redo = []
        for runner in ("claude", "codex", "agy"):
            r = ht.get(runner) or {"status": {}, "reopens": 0}
            bad = sum(r["status"].get(s, 0) for s in ("cancelled", "failed", "stalled"))
            redo.append(f"{runner} {bad}/{r['reopens']}")
        c["redo"] = _cell(" · ".join(redo), "measured", "ยกเลิก+ล้ม+ค้าง / reopen")
        seed = sum((ht.get(r) or {}).get("seed_claude_pct_done", 0.0) for r in OUTSIDE_RUNNERS)
        own = (ht.get("claude") or {}).get("seed_claude_pct_done", 0.0)
        c["claude_saved_seed"] = _cell(round(seed, 1), "estimate",
                                       f"seed S3/M8/L20 ต่องาน สูงเกินจริง (งาน Claude เองคิดได้ {own:.0f}%)")
    else:
        for k in ("claude_pinned", "redo", "claude_saved_seed"):
            c[k] = _none(_org_missing(rows, "hub_tasks"))

    for key, label, note in (
        ("worthwhile", "measured", "เสร็จโดยไม่ reopen และ iteration 0 / เสร็จทั้งหมด"),
        ("iterations", "measured", "เฉลี่ย (iteration+1) ของงานที่เสร็จ"),
        ("router_skipped", "estimate", "runner ตั้งเอง ไม่มีบรรทัด router: และไม่มี override · นับเกิน: log ถูกเขียนทับตอน retry"),
    ):
        parts = []
        available = ht is not None
        for runner in ("claude", "codex", "agy"):
            r = (ht or {}).get(runner, {})
            required = {"worthwhile": "done_clean", "iterations": "iter_n", "router_skipped": "router_skipped"}[key]
            if r and required not in r:
                available = False
            if key == "worthwhile":
                value = f"{r.get('done_clean', 0)}/{r.get('status', {}).get('done', 0)}"
            elif key == "iterations":
                value = f"{r['iter_sum'] / r['iter_n']:.1f}" if r.get("iter_n") else "—"
            else:
                value = str(r.get("router_skipped", 0))
            parts.append(f"{runner} {value}")
        c[key] = _cell(" · ".join(parts), label, note) if available else _none(_org_missing(rows, "hub_tasks"))

    for kind in ("worker", "clevel"):
        v, got, gone = _host_sum(rows, "transcripts",
                                lambda s: s.get("by_kind", {}).get(kind, {}).get("output_tokens"), hosts)
        if kind == "worker":
            ids = set().union(*[set((_src(rows, h, "transcripts") or {}).get("worker_task_ids", [])) for h in got])
            n = len(ids)
            note = f"{n} งานที่มี transcript · " + _scope(got, gone)
        else:
            n = sum(r["tasks"] for r in ht.values()) if ht is not None else 0
            note = f"แบ่งเท่ากันทุกงาน ไม่ได้แยกตามงานจริง · {n} งาน · " + _scope(got, gone)
        c[f"tokens_per_job_{kind}"] = _cell(int(round(v / n)), "measured" if kind == "worker" else "estimate", note) \
            if v is not None and n else _none("ไม่มีข้อมูล · " + _scope(got, gone))

    def fam(f: str, key: str):
        return lambda s: ((s.get("families") or {}).get(f) or {}).get(key, 0)

    def model(m: str, key: str):
        return lambda s: ((s.get("models") or {}).get(m) or {}).get(key, 0)

    def measured(v, got, gone, note: str = "") -> dict:
        scope = _scope(got, gone)
        return _cell(v, "measured", f"{note} · {scope}" if note else scope) if v is not None else _none(scope)

    for f in ("opus", "sonnet"):
        c[f"{f}_out_tokens"] = measured(*_host_sum(rows, "transcripts", fam(f, "output_tokens"), hosts))
    v, got, gone = _host_sum(rows, "transcripts", model(HAIKU_55, "messages"), hosts)
    other, _, _ = _host_sum(rows, "transcripts", fam("haiku", "messages"), hosts)
    c["haiku_messages"] = measured(v, got, gone, f"Haiku รุ่นอื่น {(other or 0) - (v or 0)}" if v is not None else "")
    hk, _, _ = _host_sum(rows, "transcripts", model(HAIKU_55, "output_tokens"), hosts)
    tot, got, gone = _host_sum(rows, "transcripts",
                               lambda s: sum(x.get("output_tokens", 0) for x in (s.get("families") or {}).values()), hosts)
    c["haiku_share"] = measured(round(100.0 * (hk or 0) / tot, 2) if tot else None, got, gone)
    c["sidechain_out"] = measured(*_host_sum(
        rows, "transcripts",
        lambda s: sum(x.get("sidechain_output_tokens", 0) for x in (s.get("families") or {}).values()), hosts))

    v, got, gone = _host_sum(rows, "codex_rollouts", lambda s: s.get("sessions"), hosts)
    c["codex_sessions"] = _cell(v, "measured", _scope(got, gone)) if v is not None else _none(_scope(got, gone))
    v, got, gone = _host_sum(rows, "codex_rollouts", lambda s: (s.get("tokens") or {}).get("output_tokens"), hosts)
    c["codex_out_tokens"] = _cell(v, "measured", _scope(got, gone)) if v is not None else _none(_scope(got, gone))

    keys: set[str] = set()
    got, gone = [], []
    for h in hosts:
        s = _src(rows, h, "agy_browse")
        if s is None:
            gone.append(h)
        else:
            got.append(h)
            keys.update(s.get("keys") or [])
    hub_ab = _org_src(rows, "agy_browse_hub")
    if hub_ab is not None:
        keys.update(hub_ab.get("keys") or [])
    c["agy_browse_calls"] = _cell(len(keys), "measured", _scope(got, gone)) if got or hub_ab else _none(_scope(got, gone))

    jg = _org_src(rows, "jules_github")
    if jg is not None:
        c["jules_prs"] = _cell(jg["prs_created"], "lower", f"merge {jg['prs_merged']} · อ่าน {jg['repos_read']} repo")
    else:
        c["jules_prs"] = _none(_org_missing(rows, "jules_github"))
    v, got, gone = _host_sum(rows, "jules_sessions", lambda s: s.get("sessions"), ("mac",))
    if v is not None:
        c["jules_sessions"] = _cell(v, "measured", f"จาก {JULES_CAPACITY_WEEK:,} ต่อสัปดาห์ (เพดาน)")
    else:
        c["jules_sessions"] = _none("ไม่มีข้อมูล (Mac)")

    v, got, gone = _host_sum(rows, "decisions", lambda s: s.get("calls"), hosts)
    c["jev_calls"] = _cell(v, "measured", _scope(got, gone)) if v is not None else _none(_scope(got, gone))
    v2, _, _ = _host_sum(rows, "decisions", lambda s: (s.get("providers") or {}).get("jev", 0), hosts)
    if v is not None:
        c["jev_calls"]["note"] = f"ถาม Jev จริง {v2 or 0} · " + c["jev_calls"]["note"]
    wired: set[str] = set()
    called: set[str] = set()
    for h in got:
        s = _src(rows, h, "decisions") or {}
        wired.update(s.get("wired_sites") or [])
        called.update(s.get("wired_sites_called") or [])
    c["jev_sites"] = _cell(f"{len(called)}/{len(wired)}", "measured", "site ที่ถูกเรียก / site ที่ต่อไว้") if got \
        else _none(_scope(got, gone))
    v, got, gone = _host_sum(rows, "decisions", lambda s: s.get("cost_usd"), hosts)
    c["jev_cost"] = _cell(round(v, 4), "measured", _scope(got, gone)) if v is not None else _none(_scope(got, gone))
    v, got, gone = _host_sum(rows, "decisions", lambda s: s.get("saved_usd"), hosts)
    c["jev_saved"] = _cell(round(v, 4), "estimate", "ราคา counterfactual จาก config/decisions") if v is not None \
        else _none(_scope(got, gone))
    v, got, gone = _host_sum(rows, "bl_jev", lambda s: len(s.get("episodes_with_decisions") or []), hosts)
    c["bl_episodes"] = _cell(v, "measured", "ตาม mtime ของ decisions.jsonl · " + _scope(got, gone)) if v is not None \
        else _none(_scope(got, gone))

    orb = _org_src(rows, "openrouter")
    if orb is not None and orb.get("account_remaining_usd") is not None:
        when = parse_ts(orb["read_at"]).astimezone(BKK)
        note = f"อ่านเมื่อ {when:%d/%m %H:%M}" + ("" if orb["read_inside_window"] else " (ก่อนช่วงนี้)")
        c["openrouter_left"] = _cell(orb["account_remaining_usd"], "measured", note)
    else:
        c["openrouter_left"] = _none(_org_missing(rows, "openrouter"))

    for usd in (20, 200):
        pct = c["claude_used_pct"]["value"]
        usd_win = usd * 12 / 52 * win.days / 7
        note = ("ราคาแพ็กเกจสัปดาห์นั้นไม่ได้บันทึก (CEO บอกว่าตอนนี้ $200)"
                if win.start < ANTHROPIC_PRICE_CONFIRMED else "CEO ยืนยัน $200 ตั้งแต่ 14 ต.ค.")
        c[f"usd_per_pct_anthropic_{usd}"] = _cell(round(usd_win / pct, 2) if pct > 0 else None, "estimate",
            f"${usd_win:.2f} ต่อช่วงนี้ ÷ {pct:.1f}% · " + note) if pct is not None else _none(_org_missing(rows, "quota"))
    for prov, buckets in (("openai", ("codex",)), ("google", ("agy_gemini", "agy_claude"))):
        usd = _plan_usd_week(prov, win.start, plans)
        used = [c[f"{b}_used_pct"]["value"] for b in buckets if c[f"{b}_used_pct"]["value"] is not None]
        if usd is None or not used:
            c[f"usd_per_pct_{prov}"] = _none("ไม่มีข้อมูล")
            continue
        pct = sum(used) / len(used)
        usd_win = usd * win.days / 7
        basis = "เฉลี่ย 2 bucket" if len(buckets) > 1 else ""
        c[f"usd_per_pct_{prov}"] = _cell(round(usd_win / pct, 2) if pct > 0 else None, "estimate",
                                         f"${usd_win:.2f} ต่อช่วงนี้ ÷ {pct:.1f}% {basis}".strip())
    return c


ROW_ORDER = (
    ("Claude", "โควตาสัปดาห์ที่ใช้ %", "claude_used_pct"),
    ("Claude", "ชั่วโมงที่ชนเพดาน", "claude_cap_hours"),
    ("Claude", "งาน worker (runner=claude)", "tasks_claude"),
    ("Claude", "งานที่ pin มือ (override:)", "claude_pinned"),
    ("Claude", "งาน role ที่ไม่ผ่าน router", "tasks_unrouted"),
    ("Claude", "output tokens Opus", "opus_out_tokens"),
    ("Claude", "output tokens Sonnet", "sonnet_out_tokens"),
    ("Claude", "output tokens ใน subagent (ทุกรุ่น)", "sidechain_out"),
    ("Haiku 5.5", "ข้อความ assistant", "haiku_messages"),
    ("Haiku 5.5", "สัดส่วน output tokens ของตระกูล Claude %", "haiku_share"),
    ("Codex/ChatGPT", "โควตาสัปดาห์ที่ใช้ %", "codex_used_pct"),
    ("Codex/ChatGPT", "งาน worker", "tasks_codex"),
    ("Codex/ChatGPT", "session Codex CLI", "codex_sessions"),
    ("Codex/ChatGPT", "output tokens", "codex_out_tokens"),
    ("AGY", "bucket Gemini ที่ใช้ %", "agy_gemini_used_pct"),
    ("AGY", "bucket Claude (Sonnet 4.6) ที่ใช้ %", "agy_claude_used_pct"),
    ("AGY", "งาน worker", "tasks_agy"),
    ("AGY", "agy_browse ครั้ง", "agy_browse_calls"),
    ("Jules", "PR จาก branch ของ Jules", "jules_prs"),
    ("Jules", "session", "jules_sessions"),
    ("JEV", "decide() ครั้ง", "jev_calls"),
    ("JEV", "site ที่ถูกใช้", "jev_sites"),
    ("JEV", "จ่ายจริง $", "jev_cost"),
    ("JEV", "ประหยัด $", "jev_saved"),
    ("JEV", "ตอน BL ที่ให้ Jev ช่วยตัด", "bl_episodes"),
    ("OpenRouter", "เครดิตคงเหลือ $", "openrouter_left"),
    ("ความคุ้ม", "โควตา Claude ที่ runner นอกประหยัด %", "claude_saved_seed"),
    ("ความคุ้ม", "งานที่คุ้มค่า", "worthwhile"),
    ("ความคุ้ม", "รอบเฉลี่ย", "iterations"),
    ("ความคุ้ม", "งานที่ข้าม router", "router_skipped"),
    ("ความคุ้ม", "output tokens / งาน worker", "tokens_per_job_worker"),
    ("ความคุ้ม", "output tokens C-level / งาน", "tokens_per_job_clevel"),
    ("ความคุ้ม", "$ ต่อ 1% (Anthropic $20)", "usd_per_pct_anthropic_20"),
    ("ความคุ้ม", "$ ต่อ 1% (Anthropic $200)", "usd_per_pct_anthropic_200"),
    ("ความคุ้ม", "$ ต่อ 1% (OpenAI)", "usd_per_pct_openai"),
    ("ความคุ้ม", "$ ต่อ 1% (Google)", "usd_per_pct_google"),
    ("ความคุ้ม", "งานพัง/แก้ซ้ำ ต่อ runner", "redo"),
)
COUNT_ROWS = {"tasks_claude", "claude_pinned", "tasks_unrouted", "haiku_messages", "tasks_codex", "codex_sessions",
              "tasks_agy", "agy_browse_calls", "jules_prs", "jules_sessions", "jev_calls", "bl_episodes"}


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.2f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:,.0f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def _cell_text(cell: dict, win: Window, key: str) -> str:
    if cell["label"] == "none":
        return cell["note"] or "ไม่มีข้อมูล"
    s = _fmt(cell["value"])
    if key in COUNT_ROWS and isinstance(cell["value"], (int, float)):
        s += f" ({cell['value'] / win.days:.1f}/วัน)"
    return s


def _delta(a: dict, b: dict) -> str:
    va, vb = a["value"], b["value"]
    if not isinstance(va, (int, float)) or not isinstance(vb, (int, float)) or a["label"] == "none" or b["label"] == "none":
        return "—"
    d = round(vb - va, 4)
    if d == 0:
        return "0"
    return ("+" if d > 0 else "") + _fmt(d)


def idle_list(cur: dict, win: Window) -> list[dict]:
    """Tools under the proposed floor in the current window (plan §4.3 M3). Owner + job + next-Monday deadline;
    the COO turns each into a dated LungNote to-do (skill COO_Procedure_ToolValueWeekly)."""
    out = []
    scale = 7 / win.days
    due = (win.end.astimezone(BKK).date() + timedelta(days=7 - win.end.astimezone(BKK).weekday())).isoformat()
    for key, tool, owner, job in (
        ("agy_gemini_used_pct", "AGY Gemini", "CTO", "งาน developer ที่ไม่มีเหตุผล §59 ปล่อย runner ว่างให้ router เลือก agy"),
        ("agy_claude_used_pct", "AGY Claude-bucket", "CTO", "งานเขียนที่ต้องคุณภาพ Claude แต่ไม่ต้องใช้ tool เฉพาะ Claude (หลัง A/B)"),
        ("codex_used_pct", "Codex", "CTO", "งานที่ต้องรัน shell (tests, psql, docker) ไป dev_shell"),
    ):
        cell = cur[key]
        if cell["label"] == "none":
            continue
        pace = cell["value"] * scale
        if pace < FLOORS["bucket_used_pct"]:
            out.append({"tool": tool, "value": f"{cell['value']}% (เทียบเต็มสัปดาห์ ~{pace:.0f}%)",
                        "floor": f"≥{FLOORS['bucket_used_pct']:.0f}%", "owner": owner, "job": job, "due": due})
    jp = cur["jules_prs"]
    js = cur["jules_sessions"]
    if js["label"] != "none":
        if js["value"] * scale < FLOORS["jules_sessions"]:
            out.append({"tool": "Jules", "value": f"{js['value']} session", "floor": f"≥{FLOORS['jules_sessions']}",
                        "owner": "CTO เวร Contabo", "job": "issue ขนาด S/M ใน repo allowlist (tests, lint, docs)", "due": due})
    elif jp["label"] != "none" and jp["value"] < FLOORS["jules_sessions"]:
        out.append({"tool": "Jules", "value": f"PR {jp['value']} (ขั้นต่ำ; session ไม่มีข้อมูล)",
                    "floor": f"≥{FLOORS['jules_sessions']} session", "owner": "CTO เวร Contabo",
                    "job": "issue ขนาด S/M ใน repo allowlist (tests, lint, docs)", "due": due})
    sites = cur["jev_sites"]
    if sites["label"] != "none":
        called, wired = (int(x) for x in str(sites["value"]).split("/"))
        if called < wired:
            out.append({"tool": "JEV", "value": f"{called}/{wired} site", "floor": "≥1 ครั้งต่อ site",
                        "owner": "CTO (+CMO สำหรับ BL)", "job": "ไล่ site ที่ DECIDE_PROVIDER ว่าง · BL ตอนถัดไปเปิด Jev", "due": due})
    return out


def summary_th(prev: dict, cur: dict, pw: Window, cw: Window, idle: list[dict]) -> list[str]:
    """The fixed 5-line Thai summary (plan §3.4). No model call."""
    def v(c: dict, key: str) -> str:
        return _cell_text(c[key], cw, key) if c[key]["label"] != "none" else c[key]["note"] or "ไม่มีข้อมูล"
    idle_tools = {i["tool"] for i in idle}
    agy_flag = " · ต่ำกว่าเกณฑ์ → CTO ย้ายงาน developer ไป agy" if idle_tools & {"AGY Gemini", "AGY Claude-bucket"} else ""
    return [
        f"1. Claude: ใช้ {v(cur, 'claude_used_pct')}% (ก่อนหน้า {v(prev, 'claude_used_pct')}%) · ชนเพดาน {v(cur, 'claude_cap_hours')} ชม.",
        f"2. AGY: Gemini {v(cur, 'agy_gemini_used_pct')}% / Claude-bucket {v(cur, 'agy_claude_used_pct')}%{agy_flag}",
        f"3. Jules: PR {v(cur, 'jules_prs')} (ก่อนหน้า {v(prev, 'jules_prs')}) · session: {v(cur, 'jules_sessions')}",
        f"4. Codex/ChatGPT: {v(cur, 'tasks_codex')} งาน · {v(cur, 'codex_used_pct')}% โควตา",
        f"5. JEV: {v(cur, 'jev_calls')} ครั้ง · ประหยัด ${v(cur, 'jev_saved')} (ประมาณการ) · Haiku: {v(cur, 'haiku_messages')} ข้อความ",
    ]


def render(prev: dict, cur: dict, pw: Window, cw: Window, idle: list[dict], *, first: bool,
           missing: list[str], sources: dict[str, dict] | None = None) -> str:
    lines = [f"รายงานความคุ้มค่าเครื่องมือ — สัปดาห์ {cw.label()} เทียบ {pw.label()}", ""]
    lines += summary_th(prev, cur, pw, cw, idle)
    lines += ["", f"| เครื่องมือ | ตัววัด | {pw.label()} | {cw.label()} | ต่าง | ป้าย |", "|---|---|---|---|---|---|"]
    for tool, metric, key in ROW_ORDER:
        a, b = prev[key], cur[key]
        label = LABEL_TH[b["label"] if b["label"] != "none" else a["label"]]
        note = b["note"] if b["label"] != "none" and b["note"] else ""
        lines.append(f"| {tool} | {metric} | {_cell_text(a, pw, key)} | {_cell_text(b, cw, key)}"
                     f"{' · ' + note if note else ''} | {_delta(a, b)} | {label} |")
    sources = sources or {}
    q = _org_src(sources, "quota")
    lines += ["", "ณ เวลาที่ Claude รีเซ็ตโควตาสัปดาห์ (วัดจริง จาก quota-history):"]
    resets = (q or {}).get("claude", {}).get("resets", [])
    def when(ts):
        return f"{parse_ts(ts).astimezone(BKK):%d/%m %H:%M}"
    if q is None or "resets" not in q.get("claude", {}):
        lines.append("- " + _org_missing(sources, "quota"))
    elif not resets:
        lines.append("- ไม่มีการรีเซ็ตในช่วงนี้")
    for reset in resets:
        full = "เต็มตั้งแต่ " + when(reset["full_since"]) if reset["full_since"] else "ไม่เต็ม"
        line = f"- {when(reset['at'])}: Claude ใช้ {_fmt(reset['claude_used_pct'])}% ({full})"
        for bucket, label in (("codex", "Codex"), ("agy-gemini", "AGY Gemini"), ("agy-claude", "AGY Claude")):
            sample = reset["others"].get(bucket)
            value = _fmt(sample["used_pct"]) + "%" if sample else "ไม่มีข้อมูล"
            line += f" · {label} {value}"
        lines.append(line)
    lines += ["", "runner-fit (cell = runner × ประเภทงาน · เกณฑ์ร่าง COO: first-pass ≥80% ใน 10 งานล่าสุด และ skill ไม่เปลี่ยน rule 14 วัน):"]
    fit = _org_src(sources, "runner_fit")
    cells, org = fit_cells(fit["records"] if fit is not None else [], _org_src(sources, "skill_commits"), cw)
    if fit is None:
        lines.append(_org_missing(sources, "runner_fit"))
    elif not cells:
        lines.append("ยังไม่มีบันทึก runner_fit ในช่วงนี้ (เริ่มบันทึก 13 ต.ค.)")
    else:
        lines += ["| cell | ประเภทงาน | งาน | ผ่าน/แก้ซ้ำ/ล้ม | first-pass % | แก้ซ้ำ % | รอบเฉลี่ย | นาทีเฉลี่ย | first-pass 10 งานล่าสุด | skill แก้ในสัปดาห์ | เฟส |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in cells:
            lines.append(f"| {r['cell']} | {r['job_type']} | {r['jobs']} | {r['pass']}/{r['redo']}/{r['fail']} | "
                         f"{r['first_pass_pct']} | {r['redo_pct']} | {r['iter_avg']:.1f} | {_fmt(r['minutes_avg'])} | "
                         f"{r['last10_first_pass_pct']}% ({r['last10_n']}) | {_fmt(r['skill_edits'])} | {r['phase']} ({r['why']}) |")
        lines.append(f"เฟสองค์กร: {org['phase']} — cell ที่ผ่านเกณฑ์ {org['passed']}/{org['used']}")
    lines += ["", "ขนาดข้อความที่โหลดทุกครั้ง (วัดจริง: claude -p delta):"]
    context = _org_src(sources, "context_deltas")
    if context is None:
        lines.append("- " + _org_missing(sources, "context_deltas"))
    elif not context["records"]:
        lines.append("- ไม่มีบันทึกในช่วงนี้")
    else:
        total = 0
        for r in context["records"]:
            delta = r["after"] - r["before"]
            total += delta
            pct = f"{100 * delta / r['before']:+.0f}%" if r["before"] else "ไม่มีข้อมูล"
            lines.append(f"- {r['what']}: {r['before']:,} → {r['after']:,} tokens ({delta:+,}, {pct}) · "
                         f"{r.get('per') or ''} · {r['by']} · {r['evidence']}")
        lines.append(f"รวม {total:+,} tokens")
    lines.append("")
    if idle:
        lines.append(f"ต่ำกว่าเกณฑ์ที่เสนอ (CEO ยังไม่ได้กำหนดเกณฑ์) → เจ้าของ + งานที่ต้องย้าย ภายใน {idle[0]['due']}:")
        lines += [f"- {i['tool']}: {i['value']} (เกณฑ์ {i['floor']}) → {i['owner']}: {i['job']}" for i in idle]
    else:
        lines.append("ไม่มีเครื่องมือที่ต่ำกว่าเกณฑ์ที่เสนอ")
    if missing:
        lines += ["", "แหล่งที่อ่านไม่ได้: " + " · ".join(missing)]
    lines += ["", "ป้าย: วัดจริง = อ่านจาก log/ledger/hub · ประมาณการ = คำนวณ บอกฐานไว้ · ขั้นต่ำ = ค่าจริงอย่างน้อยเท่านี้ · "
              "ไม่มีข้อมูล = ไม่มีแหล่ง หรืออยู่บนเครื่องที่ไม่ได้ส่งมา (ไม่ใช่ 0)",
              f"ช่วงเวลาเป็นเวลาไทย · ต่อวัน = หารด้วยจำนวนวันของช่วง ({pw.days:.2f} / {cw.days:.2f} วัน)"]
    if first:
        lines += ["", "คำถามถึง CEO (ถามครั้งเดียว ในรายงานนี้):", *FIRST_REPORT_QUESTIONS]
    return "\n".join(lines)


def _missing_lines(rows_by_win: Iterable[dict[str, dict]], hosts: Iterable[str]) -> list[str]:
    out: list[str] = []
    for rows in rows_by_win:
        for h in hosts:
            if h not in rows:
                s = f"{HOST_TH[h]} ไม่ส่ง"
            else:
                continue
            if s not in out:
                out.append(s)
        for p in rows.values():
            for m in p.get("missing") or []:
                s = f"{HOST_TH.get(p.get('host'), p.get('host'))}:{m.get('source')}"
                if s not in out:
                    out.append(s)
    return out


def build_report(prev_rows: dict[str, dict], cur_rows: dict[str, dict], pw: Window, cw: Window, *,
                 plans: dict, hosts: Iterable[str] = HOSTS, first: bool = False) -> dict:
    hosts = tuple(hosts)
    prev = build_rows(prev_rows, pw, hosts, plans)
    cur = build_rows(cur_rows, cw, hosts, plans)
    idle = idle_list(cur, cw)
    fit = _org_src(cur_rows, "runner_fit")
    cells, phase = fit_cells(fit["records"] if fit is not None else [], _org_src(cur_rows, "skill_commits"), cw)
    quota = _org_src(cur_rows, "quota")
    text = render(prev, cur, pw, cw, idle, first=first, missing=_missing_lines((prev_rows, cur_rows), hosts), sources=cur_rows)
    return {"previous": {"window": pw.as_json(), "cells": prev}, "current": {"window": cw.as_json(), "cells": cur},
            "idle": idle, "text": text, "claude_resets": (quota or {}).get("claude", {}).get("resets", []),
            "fit_cells": cells if fit is not None else None, "org_phase": phase if fit is not None else None}


# ---------------------------------------------------------------------------------------------- delivery

COO_SENDER = "CTO tool-value"


def send_to_coo(text: str) -> str:
    """One letter to SomPong as the timer's own identity (cto / tool-value), never as the CEO.

    Run from a deploy checkout (ORG_ROOT names another tree, deploy/systemd/tool-value-*.service),
    the letter goes through the live checkout's own CLI. tools/send_to_cxo.py finds SomPong's session
    under its own checkout's state/locks, which a deploy worktree does not have, and the live CLI
    writes the mailbox format the live inbox hook reads."""
    if DATA_ROOT.resolve() != ROOT.resolve():
        return _send_via_live_checkout(text)
    from tools import send_to_cxo
    saved = {k: os.environ.get(k) for k in ("CXO_ROLE", "CXO_SESSION_ID", "WORKER_TASK_ID")}
    os.environ["CXO_ROLE"] = "cto"
    os.environ["CXO_SESSION_ID"] = "tool-value"
    os.environ.pop("WORKER_TASK_ID", None)
    try:
        return send_to_cxo.send("coo", text, sender=COO_SENDER)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _send_via_live_checkout(text: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "WORKER_TASK_ID"}
    env.update(CXO_ROLE="cto", CXO_SESSION_ID="tool-value", ORG_ROOT=str(DATA_ROOT))
    # subprocess.run is looked up at call time, so the tests' guard on it applies.
    p = subprocess.run([sys.executable, "-m", "tools.send_to_cxo", "--from", COO_SENDER, "coo", text],
            cwd=str(DATA_ROOT), env=env, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f"send_to_cxo ({DATA_ROOT}) exit {p.returncode}: {(p.stderr or '').strip()[:300]}")
    return (p.stdout or "").strip()


def _self_host() -> str:
    from lib.config import self_host
    return self_host()


def _rows_for(win: Window, events: list[dict], host: str, *, live: bool) -> dict[str, dict]:
    rows = latest_rows(events, win)
    if host not in rows and live:
        rows[host] = collect(win, host, org=(host == ORG_HOST))
        rows[host]["live"] = True
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("context-delta")
    for name in ("what", "before", "after", "method", "evidence", "by"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--per", default="")
    p.add_argument("--at")
    p.add_argument("--dry-run", action="store_true")
    for name in ("collect", "report"):
        p = sub.add_parser(name)
        p.add_argument("--week", type=date.fromisoformat, help="current window starts this BKK date (7 days)")
        p.add_argument("--as-of", help="pretend the run is at this time (ISO, BKK if no offset); the window still"
                                       " stops at the real now")
        p.add_argument("--dry-run", action="store_true", help="print; write and send nothing")
        p.add_argument("--host", help="this host's config/hosts.yaml key (default: resolved)")
        if name == "report":
            p.add_argument("--no-send", action="store_true", help="write the files, do not send to SomPong")
            p.add_argument("--force-send", action="store_true", help="send even if this week was already sent")
    a = ap.parse_args(argv)

    if a.cmd == "context-delta":
        try:
            before, after = int(a.before), int(a.after)
            if before < 0 or after < 0:
                raise ValueError("before and after must be non-negative integers")
            at = parse_ts(a.at) if a.at else datetime.now(timezone.utc)
            if at is None:
                raise ValueError("at must be an ISO timestamp")
        except ValueError as e:
            print(str(e).replace("\n", " "), file=sys.stderr)
            return 2
        payload = dict(schema=SCHEMA, what=a.what, before=before, after=after, method=a.method,
                       evidence=a.evidence, by=a.by, per=a.per, at=iso(at))
        if a.dry_run:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            write_event(payload, kind="context_delta")
        return 0

    real_now = datetime.now(timezone.utc)
    as_of = real_now
    if a.as_of:
        t = datetime.fromisoformat(a.as_of)
        as_of = (t if t.tzinfo else t.replace(tzinfo=BKK)).astimezone(timezone.utc)
    pw, cw = windows(as_of, a.week)
    if cw.end > real_now:
        cw = Window(cw.start, max(real_now, cw.start))
    host = a.host or _self_host()
    first = a.week is None and as_of.astimezone(BKK).date() == FIRST_REPORT_DAY

    if a.cmd == "collect":
        try:
            have = latest_rows(read_events(pw.start - timedelta(days=1)), pw) if not a.dry_run else {}
        except Exception as e:  # noqa: BLE001
            print(f"[tool_value] hub ไม่ตอบ: {type(e).__name__}", file=sys.stderr)
            return 3
        todo = [cw] + ([pw] if host not in have else [])
        for w in todo:
            payload = collect(w, host, org=(host == ORG_HOST))
            if a.dry_run:
                print(json.dumps(payload, ensure_ascii=False, indent=1)[:20000])
            else:
                write_event(payload)
                print(f"[tool_value] {host} {w.label()}: {len(payload['sources'])} แหล่ง,"
                      f" ไม่มีข้อมูล {len(payload['missing'])}")
        return 0

    try:
        events = read_events(pw.start - timedelta(days=1))
    except Exception as e:  # noqa: BLE001
        if not a.dry_run:
            print(f"[tool_value] hub ไม่ตอบ: {type(e).__name__}", file=sys.stderr)
            return 3
        print(f"[tool_value] hub ไม่ตอบ ({type(e).__name__}); dry run อ่านแหล่งในเครื่องอย่างเดียว", file=sys.stderr)
        events = []
    prev_rows = _rows_for(pw, events, host, live=True)
    cur_rows = _rows_for(cw, events, host, live=True)
    plans = _load_yaml(PLANS_CONFIG)
    rep = build_report(prev_rows, cur_rows, pw, cw, plans=plans, first=first)
    if a.dry_run:
        print(rep["text"])
        return 0
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    base = REPORT_DIR / cw.key
    base.with_suffix(".md").write_text(rep["text"] + "\n", encoding="utf-8")
    base.with_suffix(".json").write_text(json.dumps({k: v for k, v in rep.items() if k != "text"},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[tool_value] wrote {base}.md / .json")
    sent = base.with_suffix(".sent")
    if a.no_send:
        return 0
    if sent.exists() and not a.force_send:
        print(f"[tool_value] ส่งไปแล้ว ({sent.read_text().strip()}); ใช้ --force-send ถ้าจะส่งซ้ำ")
        return 2
    result = send_to_coo(rep["text"])
    sent.write_text(f"{iso(real_now)} {result.split(':')[0]}\n", encoding="utf-8")
    print(f"[tool_value] {result.split(':')[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
