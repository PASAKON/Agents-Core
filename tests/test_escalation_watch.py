"""tools/escalation_watch.py (M11): stalled sessions, held blockers, stale hosts."""
from __future__ import annotations

import json

import pytest

from tools import escalation_watch as ew

NOW = 1_800_000_000.0
PERMISSION = """\
 Bash command
   systemctl restart foo
 Do you want to proceed?
 ❯ 1. Yes
   2. Yes, and don't ask again for systemctl commands
   3. No, and tell Claude what to do differently (esc)
"""
BOXED = "│ Do you want to make this edit to x.py?\n│ ❯ 1. Yes\n│   2. No\n"
QUESTION = "Which one?\n❯ 1. A\n  2. B\nEnter to select · ↑/↓ to navigate · Esc to cancel\n"
INPUT = "some output\n❯ \n  ? for shortcuts\n"
DRAFT = "❯ 1. step one of my plan\n"


@pytest.mark.parametrize("screen,waiting", [(PERMISSION, True), (BOXED, True), (QUESTION, True),
                                            (INPUT, False), (DRAFT, False), ("", False)])
def test_a_prompt_waiting_on_a_person_is_read_off_the_screen(screen, waiting):
    assert ew.pane_waiting(screen) is waiting


def _s(box, status="idle", since=NOW - 60, tmux="t"):
    return {"box": box, "role": box.split("-")[0], "sid": box.split("-")[1], "name": box,
            "status": status, "since": since, "tmux": tmux}


def _m(frm, to, kind, ago):
    return {"from": frm, "to": to, "kind": kind, "t": NOW - ago}


def test_waiting_and_idle_findings():
    sessions = [_s("cmo-ef04792e"), _s("project_head-13db8720", since=NOW - 31 * 60),
                _s("cto-c34459eb", status="running", since=NOW - 99 * 60),
                _s("project_head-36c49776", since=NOW - 29 * 60)]
    screens = {"cmo-ef04792e": PERMISSION}
    for s in sessions:
        s["tmux"] = s["box"]
    out = ew.find(sessions, [], {}, {}, NOW, panes=lambda t: screens.get(t, INPUT))
    assert [(f["kind"], f["box"]) for f in out] == [("waiting", "cmo-ef04792e"),
                                                    ("idle", "project_head-13db8720")]


def test_a_held_blocker_is_flagged_until_a_card_or_a_reply():
    blk = _m("project_head-13db8720", "cmo-ef04792e", "blocker", 16 * 60)
    out = ew.find([], [blk], {}, {}, NOW)
    assert out[0]["kind"] == "blocker" and "no question card since" in out[0]["text"]
    assert ew.find([], [blk], {"cmo-ef04792e": [NOW - 60]}, {}, NOW) == []          # card after it
    assert ew.find([], [blk], {"cmo-ef04792e": [NOW - 20 * 60]}, {}, NOW) != []     # card before it
    reply = _m("cmo-ef04792e", "project_head-13db8720", "answer", 60)
    assert ew.find([], [blk, reply], {}, {}, NOW) == []
    assert ew.find([], [_m("project_head-13db8720", "cmo-ef04792e", "blocker", 14 * 60)], {}, {}, NOW) == []
    assert "card unknown" in ew.find([], [blk], None, {}, NOW)[0]["text"]
    # not a PH's blocker to a C-level: not this rule
    assert ew.find([], [_m("cto-c34459eb", "cmo-ef04792e", "blocker", 3600)], {}, {}, NOW) == []


def test_a_stale_host_is_a_finding():
    out = ew.find([], [], {}, {"mac": {"age": 3600.0}, "contabo": {"age": 4.0}}, NOW)
    assert [(f["kind"], f["host"]) for f in out] == [("host", "mac")]


def test_nudges_go_to_the_owner_and_the_coo_once_per_window(tmp_path, monkeypatch):
    monkeypatch.setattr(ew, "LOCKS_DIR", tmp_path)
    monkeypatch.setattr(ew, "STATE_PATH", tmp_path / "state.json")
    (tmp_path / "coo-active").write_text("fde4c4ca\n")
    (tmp_path / "project_head-13db8720.spawned_by").write_text("cxo:cmo:ef04792e\n")
    sent, woke = [], []
    send = lambda role, sid, body, fr, fs: sent.append((f"{role}-{sid}", body, fr))
    f = [{"kind": "idle", "box": "project_head-13db8720", "name": "PH#13d", "text": "idle 31 min"},
         {"kind": "host", "box": None, "host": "mac", "text": "mac stopped"}]
    ew.nudge(f, ["cmo-ef04792e", "cto-c34459eb"], NOW, send=send, wake=lambda r, s: woke.append(r))
    assert sorted(b for b, _, _ in sent) == ["cmo-ef04792e", "cmo-ef04792e", "coo-fde4c4ca",
                                            "coo-fde4c4ca", "cto-c34459eb"]
    assert all(body.startswith("blocker · urgent · escalation watch: ") and fr == "watchdog"
               for _, body, fr in sent)
    sent.clear()
    ew.nudge(f, ["cmo-ef04792e"], NOW + 60, send=send)
    assert sent == []                                            # inside RENUDGE_S
    ew.nudge(f, ["cmo-ef04792e"], NOW + ew.RENUDGE_S + 1, send=send)
    assert len(sent) == 4
    assert json.loads((tmp_path / "state.json").read_text())


def test_read_meta_skips_bad_lines(tmp_path):
    p = tmp_path / "m.jsonl"
    p.write_text('{"sent_at": "2026-10-14T05:00:00Z", "from": "a-1", "to": "b-2", "kind": "blocker"}\n'
                 "not json\n{}\n")
    [m] = ew.read_meta(p)
    assert m["kind"] == "blocker" and m["t"] > 0


# --- root reads files under state/, which the secretary service can write -----------
# (same class as §2b review of #283 v2, B-1)

@pytest.mark.parametrize("kind", ["dev-zero", "fifo", "big"])
def test_planted_lock_files_are_not_followed(tmp_path, monkeypatch, kind):
    import os
    monkeypatch.setattr(ew, "LOCKS_DIR", tmp_path)
    for name in ("project_head-36c49776.spawned_by", "coo-active"):
        p = tmp_path / name
        if kind == "dev-zero":
            p.symlink_to("/dev/zero")
        elif kind == "fifo":
            os.mkfifo(p)
        else:
            p.write_text("cxo:cmo:ef04792e" + " " * 300)
    assert ew.owner_box("36c49776") is None and ew.coo_box() is None


def test_lock_files_are_read(tmp_path, monkeypatch):
    monkeypatch.setattr(ew, "LOCKS_DIR", tmp_path)
    (tmp_path / "project_head-36c49776.spawned_by").write_text("cxo:cmo:ef04792e\n")
    (tmp_path / "coo-active").write_text("fde4c4ca")
    assert ew.owner_box("36c49776") == "cmo-ef04792e" and ew.coo_box() == "coo-fde4c4ca"


def test_a_symlinked_or_fifo_meta_log_reads_as_empty(tmp_path):
    import os
    link = tmp_path / "meta.jsonl"
    link.symlink_to("/dev/zero")
    assert ew.read_meta(link) == []
    fifo = tmp_path / "fifo.jsonl"
    os.mkfifo(fifo)
    assert ew.read_meta(fifo) == []


def test_a_big_meta_log_is_read_from_its_tail_only(tmp_path, monkeypatch):
    monkeypatch.setattr(ew, "META_READ_MAX", 4096)
    line = json.dumps({"from": "a", "to": "b", "kind": "fyi", "sent_at": "2026-10-14T07:00:00Z"})
    p = tmp_path / "m.jsonl"
    p.write_text("x" * 100_000 + "\n" + (line + "\n") * 3)
    assert len(ew.read_meta(p)) == 3


def test_the_state_file_never_writes_through_a_planted_link(tmp_path, monkeypatch):
    target = tmp_path / "victim"
    target.write_text("keep")
    st = tmp_path / "state" / "escalation_watch.json"
    st.parent.mkdir()
    st.with_suffix(".tmp").symlink_to(target)
    monkeypatch.setattr(ew, "STATE_PATH", st)
    monkeypatch.setattr(ew, "coo_box", lambda: None)
    f = {"kind": "idle", "box": "cto-c34459eb", "name": "x", "text": "idle 31 min"}
    assert ew.nudge([f], [], NOW, send=lambda *a: None) == ["cto-c34459eb <- idle x"]
    assert target.read_text() == "keep" and json.loads(st.read_text())
    assert not [p for p in st.parent.iterdir() if p.name.startswith(".escalation_watch.")]
