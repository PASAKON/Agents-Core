"""tools/org_mail_baseline.py: counts what the mail hooks put into context, read only.

Synthetic transcripts only: nothing here reads ~/.claude or any real session.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path

from tools import org_mail_baseline as omb

DAY = "2026-10-13"                      # Thai date under test
IN_DAY = "2026-10-13T03:00:00.000Z"     # 10:00 Thai
EARLY_THAI = "2026-10-12T17:30:00.000Z"  # 00:30 Thai on the 13th, still the 12th in UTC
BEFORE = "2026-10-08T03:00:00.000Z"     # outside a 4-day window ending on the 13th
SID = "aaaaaaaa-bbbb-cccc-dddd-00003c1f65ae"
WSID = "aaaaaaaa-bbbb-cccc-dddd-0000feedbeef"
HSID = "aaaaaaaa-bbbb-cccc-dddd-0000deadbeef"

INBOX_OUT = ("## Mailbox — 2 letter(s) delivered (drained; each arrives once)\n\n"
             "[CTO] : first\n    (x · t)\n\n[COO] : second\n    (y · t)\n\n")
LOG_OUT = ("## Recent DEV / org activity (since your previous reply)\n\n"
           "[2026-10-13T10:00:00] Developer task-abc123: done\n    body line\n")


def user(pid, text, ts=IN_DAY, sid=SID, kind=None, meta=False, compact=False, ep="cli"):
    r = {"type": "user", "promptId": pid, "sessionId": sid, "timestamp": ts, "entrypoint": ep,
         "message": {"role": "user", "content": text}}
    if kind:
        r["origin"] = {"kind": kind}
    if meta:
        r["isMeta"] = True
    if compact:
        r["isCompactSummary"] = True
    return r


def tool_result(pid, ts=IN_DAY, sid=SID):
    return {"type": "user", "promptId": pid, "sessionId": sid, "timestamp": ts,
            "message": {"role": "user", "content": [{"type": "tool_result", "content": "x"}]}}


def asst(mid, cr, cw=0, ts=IN_DAY, sid=SID, text="ok"):
    return {"type": "assistant", "sessionId": sid, "timestamp": ts,
            "message": {"id": mid, "content": [{"type": "text", "text": text}],
                        "usage": {"cache_read_input_tokens": cr, "cache_creation_input_tokens": cw}}}


def hook(script, out, ts=IN_DAY, sid=SID):
    return {"type": "attachment", "sessionId": sid, "timestamp": ts,
            "attachment": {"type": "hook_success", "hookEvent": "UserPromptSubmit",
                           "command": f'python3 "${{CLAUDE_PROJECT_DIR:-$PWD}}"/scripts/{script}',
                           "stdout": out, "content": out}}


def write(root: Path, project: str, sid: str, recs: list[dict]) -> Path:
    d = root / project
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{sid}.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")
    return p


def build(root: Path) -> None:
    write(root, "-opt-MoonieXHQ-Agents-Core", SID, [
        {"type": "custom-title", "customTitle": "CONTABO CTO #3c1f65ae (test)", "sessionId": SID},
        # outside the window: never counted
        user("p0", "old prompt", ts=BEFORE, kind="human"),
        asst("m0", 999, ts=BEFORE),
        hook("hook-inbox.py", INBOX_OUT, ts=BEFORE),
        # wake 1: typed in the pane; the mail hooks fire on it
        user("p1", "please do x", ts=EARLY_THAI, kind="human"),
        hook("hook-inbox.py", INBOX_OUT, ts=EARLY_THAI),
        hook("hook-log-prompt.py", LOG_OUT, ts=EARLY_THAI),
        hook("hook-memory-nudge.py", "[memory nudge] turn 50", ts=EARLY_THAI),
        asst("m1", 100, 10, ts=EARLY_THAI),
        asst("m1", 100, 10, ts=EARLY_THAI),        # same message, second content block
        tool_result("p1", ts=EARLY_THAI),
        asst("m2", 200, ts=EARLY_THAI,
             text="grep hook-inbox.py hook_success"),  # a mention is not a hook record
        # an auto-compaction resumes the turn in progress: not a wake
        user("p2", "This session is being continued from a previous conversation", compact=True),
        asst("m3", 50),
        # wake 2: a peer message
        user("p3", "Another Claude session sent a message:\nhello there", kind="peer", meta=True),
        asst("m4", 300, 5),
        # wake 3: the mailbox wake marker typed by tmux
        user("p4", "[New message from CTO]", kind="human"),
        hook("hook-inbox.py", INBOX_OUT),
        asst("m5", 400),
        # wake 4: a background task notice
        user("p5", "<task-notification>\n<task-id>b1</task-id>", kind="task-notification"),
        asst("m6", 500),
    ])
    write(root, "-opt-MoonieXHQ-Agents-Core-worktrees-mooniex-agents--developer--task-abcdef12", WSID, [
        user("w1", "# Task task-abcdef12\n\nProject: x", sid=WSID, kind="human"),
        asst("wm1", 1000, 7, sid=WSID),
    ])
    write(root, "-tmp", HSID, [
        user("h1", "Reply with the single word ok.", sid=HSID, ep="sdk-cli"),
        asst("hm1", 13, sid=HSID),
    ])


def collect(root: Path, days: int = 4):
    return omb.collect([root], days, dt.date(2026, 10, 13))


def by_session(rows, tail):
    return next(r for r in rows if r["session"] == tail)


def test_counts_mail_hook_chars_wakes_and_cache_reads(tmp_path):
    build(tmp_path)
    rows = omb.rows(collect(tmp_path))
    r = by_session(rows, "3c1f65ae")
    assert r["day"] == DAY and r["role"] == "CTO" and r["kind"] == "session"
    assert r["inbox_chars"] == 2 * len(INBOX_OUT) and r["inbox_fires"] == 2 and r["letters"] == 4
    assert r["ctolog_chars"] == len(LOG_OUT) and r["ctolog_fires"] == 1 and r["ctolog_lines"] == 2
    assert r["wakes"] == 4
    assert (r["wakes_human"], r["wakes_peer"], r["wakes_mailbox"], r["wakes_task"]) == (1, 1, 1, 1)
    assert r["peer_msg_chars"] == len("Another Claude session sent a message:\nhello there")
    # first calls: 100, 300, 400, 500; m1 counted once; m3, after the compaction, stays in wake 1
    assert r["cache_read_first_call_avg"] == round((100 + 300 + 400 + 500) / 4)
    assert r["cache_write_first_call_avg"] == round((10 + 5 + 0 + 0) / 4)
    assert r["cache_read_per_wake_avg"] == round((100 + 200 + 50 + 300 + 400 + 500) / 4)


def test_thai_day_boundary_and_window(tmp_path):
    build(tmp_path)
    data = collect(tmp_path)
    assert data["days"] == ["2026-10-10", "2026-10-11", "2026-10-12", "2026-10-13"]
    rows = omb.rows(data)
    assert {r["day"] for r in rows} == {DAY}         # 17:30Z on the 12th is the 13th in Thailand
    assert all(r["cache_read_first_call_avg"] != 999 for r in rows)   # the out-of-window turn


def test_worker_launch_and_headless(tmp_path):
    build(tmp_path)
    data = collect(tmp_path)
    w = by_session(omb.rows(data), "feedbeef")
    assert (w["kind"], w["role"], w["wakes_launch"], w["wakes_human"]) == ("worker", "developer", 1, 0)
    assert all(r["session"] != "deadbeef" for r in omb.rows(data))
    h = by_session(omb.rows(data, include_headless=True), "deadbeef")
    assert h["kind"] == "headless" and h["wakes_other"] == 1


def test_day_totals_weight_by_turn(tmp_path):
    build(tmp_path)
    data = collect(tmp_path)
    tot = {t["day"]: t for t in omb.day_totals(omb.rows(data), data["days"])}
    t = tot[DAY]
    assert t["sessions"] == 2 and t["wakes"] == 5 and t["letters"] == 4
    assert t["cache_read_first_call_avg"] == round((100 + 300 + 400 + 500 + 1000) / 5)
    assert tot["2026-10-10"]["wakes"] == 0 and tot["2026-10-10"]["cache_read_first_call_avg"] is None


def test_skips_files_last_written_before_the_window(tmp_path):
    build(tmp_path)
    p = next((tmp_path / "-opt-MoonieXHQ-Agents-Core").glob("*.jsonl"))
    old = time.mktime((2026, 10, 1, 0, 0, 0, 0, 0, -1))
    os.utime(p, (old, old))
    assert all(r["session"] != "3c1f65ae" for r in omb.rows(collect(tmp_path)))


def test_missing_root_is_reported_not_measured(tmp_path, capsys):
    build(tmp_path)
    missing = tmp_path / "nope"
    assert omb.main(["--root", str(tmp_path), "--root", str(missing), "--today", DAY]) == 0
    out = capsys.readouterr().out
    assert "MEASURED" in out and f"NOT MEASURED (missing_roots): {missing}" in out
    assert "left out: 1 headless" in out


def test_json_output_and_read_only(tmp_path, capsys):
    build(tmp_path)
    before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in tmp_path.rglob("*") if p.is_file()}
    assert omb.main(["--root", str(tmp_path), "--today", DAY, "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["measured"] is True and doc["days"][-1] == DAY
    assert {s["session"] for s in doc["sessions"]} == {"3c1f65ae", "feedbeef"}
    after = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before
