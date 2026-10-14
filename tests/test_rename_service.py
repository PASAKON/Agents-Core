"""tools/rename_service.py (M10b, Agents-Core #272): a session's rename request is
typed as exactly one "/rename <rule name>" line, only into that session's empty
prompt. tmux is a fake that records every call."""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from lib import config
from tools import live_sessions as ls
from tools import rename_service as rs

CONTABO = "\U0001F310"
U_CTO = "00000000-0000-0000-0000-0000c34459eb"
U_PH = "00000000-0000-0000-0000-000036c49776"
U_COO = "00000000-0000-0000-0000-0000fde4c4ca"
EMPTY = "out\n❯ \n  ? for shortcuts\n"
DRAFT = "out\n❯ half a sentence the CEO is typing\n"
PERMISSION = " Do you want to proceed?\n ❯ 1. Yes\n   2. No\n❯ \n"


class FakeTmux:
    def __init__(self):
        self.screens, self.calls, self.sent = {}, [], []

    def __call__(self, *args):
        self.calls.append(args)
        out = ""
        if args[0] == "capture-pane":
            out = self.screens.get(args[args.index("-t") + 1], EMPTY)
        elif args[0] == "send-keys":
            self.sent.append((args[args.index("-t") + 1], args[-1]))
        else:
            raise AssertionError(f"tmux {args[0]} is never used: {args}")
        return subprocess.CompletedProcess(["tmux", *args], 0, out, "")


@pytest.fixture
def box(tmp_path, monkeypatch):
    sessions, locks, reqs = tmp_path / "s", tmp_path / "locks", tmp_path / "req"
    for d in (sessions, locks, reqs):
        d.mkdir()
    monkeypatch.setattr(ls, "session_dirs", lambda host: [sessions])
    for mod in (rs, ls):
        monkeypatch.setattr(mod, "LOCKS_DIR", locks)
    monkeypatch.setattr(rs, "REQUESTS_DIR", reqs)
    fake = FakeTmux()
    monkeypatch.setattr(rs, "tmux", fake)
    n = [0]

    def record(uuid, name, tmux):
        n[0] += 1
        (sessions / f"{n[0]}.json").write_text(json.dumps(
            {"pid": os.getpid(), "sessionId": uuid, "name": name, "tmux": tmux}))

    def request(box_name, topic, prefix=""):
        (reqs / f"{box_name}.json").write_text(json.dumps({"topic": topic, "prefix": prefix}))

    record(U_CTO, "CTO (Kavin)", "cto-c34459eb:@1.%1")
    record(U_PH, "PH#36c (CMO) - MimiPage — MimiPage", "project_head-36c49776:@2.%2")
    record(U_COO, "COO (SomPong)", "sompong:@3.%3")
    (locks / "project_head-36c49776.project").write_text("MimiPage")
    (locks / "project_head-36c49776.spawned_by").write_text("cxo:cmo:ef04792e")
    fake.record, fake.request, fake.reqs, fake.locks, fake.sessions = record, request, reqs, locks, sessions
    return fake


@pytest.mark.parametrize("topic", [
    "ok\n/permissions",                      # a newline would be Enter, then a new command
    "\n/exit",
    "x\r/exit",
    "\x1b[201~\x1b[200~/exit\x1b",           # bracketed-paste / ESC sequences
    "/model opus",                           # a leading slash
    "a /exit b\u0085c",           # unicode line separators
    "‮ evil ​ zero width",        # bidi / format characters
    "\t/exit",
    "x" * 500,
    "$(touch /tmp/pwned) `id` ; | > <",      # shell / tmux key names stay literal text
])
def test_no_payload_in_a_topic_reaches_the_pane_beyond_one_rename_line(box, topic):
    box.request("cto-c34459eb", topic)
    rs.once("contabo", now=1000.0)
    typed = [t for _, t in box.sent if t != "Enter"]
    assert len(typed) == 1 and [t for _, t in box.sent].count("Enter") == 1
    line = typed[0]
    assert line.startswith(f"/rename {CONTABO} CTO (Kavin)")
    assert line.count("/") == 1 + line[len("/rename "):].count("/")    # only the command's own slash leads
    assert not any(ord(c) < 32 or 0x7f <= ord(c) < 0xa0 or c in "  ‮​\u0085" for c in line)
    assert len(line) <= len("/rename ") + rs.NAME_MAX
    topic_part = line.split(" — ", 1)[1] if " — " in line else ""
    assert not topic_part.startswith("/") and len(topic_part) <= rs.TOPIC_MAX + 1
    assert all(c[0] in ("capture-pane", "send-keys") for c in box.calls)


def test_it_types_only_into_an_empty_prompt_and_retries_later(box):
    box.request("cto-c34459eb", "next job")
    for screen in (DRAFT, PERMISSION):
        box.screens["cto-c34459eb"] = screen
        assert rs.once("contabo", now=1000.0) == ["wait     cto-c34459eb: prompt not empty"]
        assert box.sent == []
    box.screens["cto-c34459eb"] = EMPTY
    assert rs.once("contabo", now=1000.0) == [f"renamed  cto-c34459eb: {CONTABO} CTO (Kavin) — next job"]
    assert box.sent == [("cto-c34459eb", f"/rename {CONTABO} CTO (Kavin) — next job"),
                        ("cto-c34459eb", "Enter")]


def test_a_landed_rename_ends_the_request_and_one_that_did_not_is_sent_again(box):
    box.request("cto-c34459eb", "t")
    rs.once("contabo", now=1000.0)
    assert rs.once("contabo", now=1010.0) == ["sent     cto-c34459eb: waiting for it to land"]
    rs.once("contabo", now=1000.0 + rs.RETRY_S + 1)
    assert len([t for _, t in box.sent if t != "Enter"]) == 2
    for f in box.sessions.iterdir():                     # now it landed
        d = json.loads(f.read_text())
        if d["sessionId"] == U_CTO:
            d["name"] = f"{CONTABO} CTO (Kavin) — t"
            f.write_text(json.dumps(d))
    assert rs.once("contabo", now=5000.0) == [f"done     cto-c34459eb: {CONTABO} CTO (Kavin) — t"]
    assert not (box.reqs / "cto-c34459eb.json").exists()


def test_it_types_into_that_sessions_pane_only(box):
    box.request("project_head-36c49776", "MimiPage")
    rs.once("contabo", now=1.0)
    assert box.sent[0] == ("project_head-36c49776", f"/rename {CONTABO} PH#36c (CMO) - MimiPage")
    box.sent.clear()
    box.request("cto-aaaaaaaa", "x")                    # no session of that id: nothing typed anywhere
    assert "wait     cto-aaaaaaaa: no single live session in its tmux" in rs.once("contabo", now=1.0)
    assert box.sent == []


def test_the_coo_needs_its_launcher_uuid_file(box):
    box.request("coo-fde4c4ca", "x")
    assert rs.once("contabo", now=1.0)[0].startswith("wait     coo-fde4c4ca")
    (box.locks / "coo-fde4c4ca.uuid").write_text(U_COO)
    rs.once("contabo", now=1.0)
    assert box.sent[0] == ("sompong", f"/rename {CONTABO} COO (SomPong) — x")


@pytest.mark.parametrize("name,body", [
    ("developer-afe57b21", {"topic": "x"}),                      # workers have no requests
    ("cto-c34459eb", {"topic": "x", "prefix": "/exit"}),         # prefix outside the set
    ("../cto-c34459eb", {"topic": "x"}),
])
def test_requests_with_no_rule_name_are_dropped(box, name, body):
    path = box.reqs / f"{name.replace('/', '_')}.json"
    path.write_text(json.dumps(body))
    rs.once("contabo", now=1.0)
    assert box.sent == [] and not path.exists()


def test_a_symlinked_or_huge_request_is_never_read(box, tmp_path):
    (tmp_path / "elsewhere.json").write_text(json.dumps({"topic": "x"}))
    (box.reqs / "cto-c34459eb.json").symlink_to(tmp_path / "elsewhere.json")
    rs.once("contabo", now=1.0)
    assert box.sent == [] and not (box.reqs / "cto-c34459eb.json").is_symlink()   # dropped
    (box.reqs / "cto-c34459eb.json").write_text(json.dumps({"topic": "x" * 5000}))
    rs.once("contabo", now=1.0)
    assert box.sent == []


@pytest.mark.parametrize("raw,clean", [
    ("ดูแล org  ทั้งหมด", "ดูแล org ทั้งหมด"), ("a\nb", "a b"), ("//x", "x"), ("  ", ""),
    ("M10: names (ok) + #272", "M10: names (ok) + #272"), ("a\x1b[2Jb", "a 2Jb"),
])
def test_clean_topic(raw, clean):
    assert rs.clean_topic(raw) == clean


def test_preview_is_what_the_service_would_type(box, capsys):
    assert rs.main(["preview", "--role", "cto", "--sid", "c34459eb", "--topic", "x",
                    "--host", "contabo"]) == 0
    assert capsys.readouterr().out.strip() == f"{CONTABO} CTO (Kavin) — x"
    assert rs.main(["preview", "--role", "developer", "--sid", "afe57b21", "--host", "contabo"]) == 1
