"""Tests for tools/org_inspector.py (task-05ae76f3).

No real tmux, no real ssh, no real home directory: tmp_path + monkeypatch
throughout. The security tests are the point — history_read is the one
function that returns file content, so a refusal is proven by asserting the
file was never OPENED, not merely that the return value looked bad.
"""
from __future__ import annotations

import builtins
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.org_inspector as oi  # noqa: E402
from scripts.session_list import parse_title  # noqa: E402

ROW_KEYS = {
    "host", "role", "id", "tmux_name", "live", "attached", "glyph", "state",
    "summary", "goal", "done", "total", "percent", "blocker", "created",
    "last_active", "idle_seconds",
}


class FakeRun:
    """Records subprocess.run argv, returns a canned CompletedProcess."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.calls = []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __call__(self, argv, *a, **kw):
        self.calls.append(list(argv))
        return subprocess.CompletedProcess(
            argv, self.returncode, self.stdout, self.stderr)


@pytest.fixture
def layout(tmp_path, monkeypatch):
    """Synthetic repo state: tab-titles/, logs/, session-data/ under tmp_path,
    with org_inspector's module constants AND its history allowlist repointed
    there (ALLOWED_HISTORY_ROOTS is computed at import, so it needs its own
    patch)."""
    tabs = tmp_path / "tab-titles"
    logs = tmp_path / "logs"
    saves = tmp_path / "session-data"
    for d in (tabs, logs, saves):
        d.mkdir()
    monkeypatch.setattr(oi, "TAB_DIR", tabs)
    monkeypatch.setattr(oi, "LOG_DIR", logs)
    monkeypatch.setattr(oi, "SAVE_DIR", saves)
    monkeypatch.setattr(oi, "ALLOWED_HISTORY_ROOTS", (logs, tabs, saves))
    monkeypatch.setattr(oi, "_tmux_ls", lambda: {})
    return {"tabs": tabs, "logs": logs, "saves": saves, "tmp": tmp_path}


def spy_open(monkeypatch):
    """Wrap builtins.open and record every path opened during the test."""
    opened = []
    real_open = builtins.open

    def recorder(file, *a, **kw):
        opened.append(str(file))
        return real_open(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", recorder)
    return opened


def write_title(layout, stem, content):
    (layout["tabs"] / f"{stem}.title").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# parse_title — the shared tab-title grammar (lives in scripts/session_list.py)
# ---------------------------------------------------------------------------

def test_parse_title_closed_glyph_wins_over_stray_active_glyph():
    glyph, state, summary, blocker = parse_title("CTO #0a1b2c 🏁 งานจบ-ปิด ✅ แถว")
    assert glyph == "🏁"
    assert state == "closed"
    assert blocker is None, "closed means no live blocker"


def test_parse_title_blocked_glyph_summary_is_the_blocker():
    glyph, state, summary, blocker = parse_title("CTO #0a1b2c 🔴 รอ CEO approve key")
    assert glyph == "🔴" and state == "blocked"
    assert blocker == "รอ CEO approve key"


def test_parse_title_waits_fragment_inside_any_summary_is_the_blocker():
    glyph, state, summary, blocker = parse_title("CTO #624111c5 ✅ ครบแล้ว รอ CEO สั่งต่อ")
    assert glyph == "✅" and state == "pending"
    assert blocker == "รอ CEO สั่งต่อ"


def test_parse_title_no_glyph_returns_raw_content():
    glyph, state, summary, blocker = parse_title("plain text no glyph")
    assert glyph == "" and state == "?"
    assert summary == "plain text no glyph"
    assert blocker is None


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------

def test_full_row_shape_live_session(layout, monkeypatch):
    write_title(layout, "cto-624111c5", "CTO #624111c5 ✅ SomPong stack ครบ รอ CEO สั่ง")
    (layout["tabs"] / "cto-624111c5.main.json").write_text(
        '{"started": "2026-08-03T14:41:31+00:00", "goal": "SomPong secretary + relay",'
        ' "done": 6, "total": 7}', encoding="utf-8")
    (layout["logs"] / "cto-624111c5.log").write_text("a\nb\n", encoding="utf-8")
    monkeypatch.setattr(oi, "_tmux_ls", lambda: {
        "cto-624111c5": {"activity": time.time() - 120, "attached": True}})

    rows = oi.list_sessions()

    assert len(rows) == 1
    r = rows[0]
    assert set(r) == ROW_KEYS, "row keys are a stable contract for the MCP task"
    assert r["host"] in ("mac", "contabo")  # detected, never guessed
    assert (r["role"], r["id"]) == ("cto", "624111c5")
    assert r["tmux_name"] == "cto-624111c5"
    assert r["live"] is True and r["attached"] is True
    assert r["glyph"] == "✅" and r["state"] == "pending"
    assert r["goal"] == "SomPong secretary + relay"
    assert (r["done"], r["total"]) == (6, 7)
    assert r["percent"] == 86
    assert r["blocker"] == "รอ CEO สั่ง"
    assert r["created"] is not None and r["last_active"] > 0
    assert 0 <= r["idle_seconds"] <= 600


def test_percent_is_none_not_zero_without_main_json(layout):
    write_title(layout, "cmo-04ff8c79", "CMO #04ff8c79 ⏳ รันแคมเปญ")
    rows = oi.list_sessions()
    assert rows[0]["percent"] is None, "unknown progress must not masquerade as 0%"
    assert rows[0]["done"] is None and rows[0]["total"] is None
    assert rows[0]["goal"] is None


def test_percent_none_when_total_zero(layout):
    write_title(layout, "cmo-04ff8c79", "CMO #04ff8c79 ⏳ รันแคมเปญ")
    (layout["tabs"] / "cmo-04ff8c79.main.json").write_text(
        '{"started": "2026-08-03T14:41:31+00:00", "goal": "g", "done": 0, "total": 0}',
        encoding="utf-8")
    assert oi.list_sessions()[0]["percent"] is None


def test_live_tmux_session_without_title_file_still_appears(layout, monkeypatch):
    monkeypatch.setattr(oi, "_tmux_ls", lambda: {
        "cfo-15a1ce76": {"activity": time.time(), "attached": False}})
    rows = oi.list_sessions()
    assert len(rows) == 1
    r = rows[0]
    assert r["live"] is True and r["attached"] is False
    assert r["glyph"] is None and r["state"] is None and r["summary"] is None
    assert r["percent"] is None and r["created"] is None


def test_title_file_without_live_tmux_appears_not_live(layout):
    write_title(layout, "cgo-aa11bb22", "CGO #aa11bb22 💤 พักไว้")
    rows = oi.list_sessions()
    assert len(rows) == 1
    assert rows[0]["live"] is False and rows[0]["attached"] is False
    assert rows[0]["tmux_name"] is None
    assert rows[0]["state"] == "idle/parked"


def test_closed_sessions_hidden_unless_include_closed_or_live(layout, monkeypatch):
    write_title(layout, "cto-0a11b2c3", "CTO #0a11b2c3 🏁 งานจบ")
    write_title(layout, "cto-0d44e5f6", "CTO #0d44e5f6 🔗 merged away")
    write_title(layout, "cto-0e77a8b9", "CTO #0e77a8b9 ⏳ กำลังทำ")

    default = oi.list_sessions()
    assert [r["id"] for r in default] == ["0e77a8b9"], "🏁/🔗 and not live are hidden"

    everything = oi.list_sessions(include_closed=True)
    assert len(everything) == 3

    # a closed session that is STILL live is happening now — always shown
    monkeypatch.setattr(oi, "_tmux_ls", lambda: {
        "cto-0a11b2c3": {"activity": time.time(), "attached": True}})
    default = oi.list_sessions()
    assert {r["id"] for r in default} == {"0a11b2c3", "0e77a8b9"}


def test_rows_sorted_newest_activity_first(layout):
    now = time.time()
    write_title(layout, "cto-0a11b2c3", "CTO #0a11b2c3 ⏳ เก่า")
    write_title(layout, "cto-0e77a8b9", "CTO #0e77a8b9 ⏳ ใหม่")
    os.utime(layout["tabs"] / "cto-0a11b2c3.title", (now - 5000, now - 5000))
    os.utime(layout["tabs"] / "cto-0e77a8b9.title", (now, now))

    assert [r["id"] for r in oi.list_sessions()] == ["0e77a8b9", "0a11b2c3"]


def test_host_env_override_stamps_every_row(layout, monkeypatch):
    monkeypatch.setenv("ORG_INSPECTOR_HOST", "contabo")
    write_title(layout, "cto-0a11b2c3", "CTO #0a11b2c3 ⏳ งาน")
    assert oi.list_sessions()[0]["host"] == "contabo"


def test_tmux_ls_parses_output_and_degrades_quietly(monkeypatch):
    fake = FakeRun(stdout="cto-abc12345 1755100000 1\nnot a session line\n")
    monkeypatch.setattr(oi.subprocess, "run", fake)
    assert oi._tmux_ls() == {"cto-abc12345": {"activity": 1755100000.0, "attached": True}}

    monkeypatch.setattr(oi.subprocess, "run", FakeRun(returncode=1))
    assert oi._tmux_ls() == {}, "no tmux server just means nothing is live"

    def boom(argv, *a, **kw):
        raise OSError("no tmux binary")
    monkeypatch.setattr(oi.subprocess, "run", boom)
    assert oi._tmux_ls() == {}


def test_uppercase_tmux_name_merges_with_lowercase_title(layout, monkeypatch):
    monkeypatch.setattr(oi, "_tmux_ls", lambda: {
        "CTO-624111C5": {"activity": time.time(), "attached": True}})
    write_title(layout, "cto-624111c5", "CTO #624111c5 ⏳ งาน")
    rows = oi.list_sessions()
    assert len(rows) == 1, "case mismatch must not fork one session into two rows"
    assert rows[0]["live"] is True


# ---------------------------------------------------------------------------
# history_index — sizes and counts only
# ---------------------------------------------------------------------------

def test_history_index_filters_by_session_id(layout):
    (layout["logs"] / "cfo-1611052f.log").write_text("one\ntwo\nthree\n", encoding="utf-8")
    (layout["saves"] / "2026-08-03-1611052f-session.tmp").write_text("save", encoding="utf-8")
    (layout["saves"] / "2026-07-16-548f2aad-session.tmp").write_text("other", encoding="utf-8")

    out = oi.history_index("1611052f")

    assert out["session_id"] == "1611052f"
    assert out["counts"] == {"event_logs": 1, "session_saves": 1}
    log = out["event_logs"][0]
    assert log["role"] == "cfo"
    assert log["lines"] == 3
    assert log["bytes"] == 14
    assert out["session_saves"][0]["path"].endswith("1611052f-session.tmp")


def test_history_index_without_session_id_counts_everything(layout):
    for i in range(3):
        (layout["saves"] / f"2026-08-0{i+1}-0a1b2c{i}-session.tmp").write_text(
            "x", encoding="utf-8")
    out = oi.history_index()
    assert out["session_id"] is None
    assert out["counts"]["session_saves"] == 3
    assert out["counts"]["event_logs"] == 0


def test_history_index_bad_session_id_matches_nothing_and_never_crashes(layout):
    out = oi.history_index("../../etc")
    assert out["counts"] == {"event_logs": 0, "session_saves": 0}


def test_history_index_returns_no_file_content(layout):
    (layout["saves"] / "2026-08-03-1611052f-session.tmp").write_text(
        "SECRET SUMMARY TEXT", encoding="utf-8")
    blob = str(oi.history_index("1611052f"))
    assert "SECRET" not in blob, "index is sizes and counts only, never content"


# ---------------------------------------------------------------------------
# history_read — the security boundary
# ---------------------------------------------------------------------------

def test_read_rejects_dotdot_traversal_and_never_opens(layout, monkeypatch):
    opened = spy_open(monkeypatch)
    out = oi.history_read("../../etc/passwd")
    assert out["status"] == "rejected"
    assert not any("passwd" in p for p in opened), "file must never be opened"


def test_read_rejects_absolute_path_outside_roots(layout, monkeypatch):
    opened = spy_open(monkeypatch)
    out = oi.history_read("/etc/passwd")
    assert out["status"] == "rejected"
    assert not any("passwd" in p for p in opened)


def test_read_rejects_symlink_inside_root_pointing_outside(layout, monkeypatch):
    secret = layout["tmp"] / "secret-target.log"
    secret.write_text("TOP SECRET", encoding="utf-8")
    link = layout["logs"] / "evil.log"
    os.symlink(secret, link)

    opened = spy_open(monkeypatch)
    out = oi.history_read(str(link))

    assert out["status"] == "rejected", "resolved-path check must see through the symlink"
    assert not any("secret-target" in p for p in opened), "target must never be opened"


def test_read_refuses_transcripts_even_at_exact_absolute_path(tmp_path, monkeypatch):
    """~/.claude/projects/**/*.jsonl holds full verbatim conversations — a
    pasted Cloudflare token lives in one forever. It must not be readable
    through this module even by exact path."""
    home = tmp_path / "home"
    projects = home / ".claude" / "projects" / "-Users-x-Proj"
    projects.mkdir(parents=True)
    transcript = projects / "abc12345-def0.jsonl"
    transcript.write_text('{"pasted": "CF_API_TOKEN"}', encoding="utf-8")

    saves = tmp_path / "session-data"
    saves.mkdir()
    monkeypatch.setattr(oi, "SAVE_DIR", saves)
    monkeypatch.setattr(oi, "ALLOWED_HISTORY_ROOTS", (saves,))

    out = oi.history_read(str(transcript))
    assert out["status"] == "rejected"

    # and the containment wall holds on its own: even an allowlisted
    # extension under ~/.claude/projects is refused (in case a future edit
    # ever widens the extension list)
    sibling = projects / "note.json"
    sibling.write_text("{}", encoding="utf-8")
    assert oi.history_read(str(sibling))["status"] == "rejected"


@pytest.mark.parametrize("name", ["secret.env", "server.pem", "id_rsa"])
def test_read_extension_allowlist_refuses_dangerous_types(layout, monkeypatch, name):
    target = layout["logs"] / name
    target.write_text("PRIVATE KEY MATERIAL", encoding="utf-8")

    opened = spy_open(monkeypatch)
    out = oi.history_read(str(target))

    assert out["status"] == "rejected"
    assert "allowlist" in out["reason"]
    assert not any(name in p for p in opened)


def test_read_returns_requested_tail(layout):
    log = layout["logs"] / "cto-abc12345.log"
    log.write_text("\n".join(f"event-{i}" for i in range(1, 6)) + "\n", encoding="utf-8")

    out = oi.history_read(str(log), tail_lines=2)

    assert out["status"] == "ok"
    assert out["lines_returned"] == 2
    assert out["lines_total"] == 5
    assert out["text"] == "event-4\nevent-5"
    assert out["truncated_bytes"] == 0


def test_read_clamps_tail_lines_to_module_cap(layout):
    log = layout["logs"] / "cto-abc12345.log"
    log.write_text("\n".join(f"l{i}" for i in range(300)) + "\n", encoding="utf-8")

    out = oi.history_read(str(log), tail_lines=99_999)

    assert out["status"] == "ok"
    assert out["lines_returned"] == oi.MAX_TAIL_LINES
    assert out["text"].splitlines()[0] == f"l{300 - oi.MAX_TAIL_LINES}"


def test_read_caps_bytes_so_one_call_cannot_pull_a_giant_file(layout):
    log = layout["logs"] / "cto-abc12345.log"
    line = "x" * 1000
    log.write_text("\n".join([line] * 400) + "\n", encoding="utf-8")  # ~400 KB

    out = oi.history_read(str(log), tail_lines=oi.MAX_TAIL_LINES)

    assert out["status"] == "ok"
    assert out["bytes_read"] <= oi.MAX_READ_BYTES
    assert out["truncated_bytes"] > 0
    assert all(len(l) <= 1000 for l in out["text"].splitlines()), \
        "the partial first line after the byte seek must have been dropped"


def test_read_missing_file_inside_a_root_is_rejected_not_raised(layout):
    out = oi.history_read(str(layout["logs"] / "nope.log"))
    assert out["status"] == "rejected"


def test_read_non_string_path_is_rejected():
    assert oi.history_read(None)["status"] == "rejected"
    assert oi.history_read(123)["status"] == "rejected"
