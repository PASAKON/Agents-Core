"""tools/rename_to_rule.py (M10b): the sanctioned rename of this host's org sessions.
tmux is a fake; the session records and lock files live in tmp_path."""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from lib import config
from tools import live_sessions as ls
from tools import rename_to_rule as rr

CONTABO = "\U0001F310"
U_CTO = "00000000-0000-0000-0000-0000c34459eb"
U_PH = "00000000-0000-0000-0000-00007cf528f0"
U_COO = "00000000-0000-0000-0000-0000fde4c4ca"
U_WD = "00000000-0000-0000-0000-0000afe57b21"


class FakeTmux:
    def __init__(self, sessions, panes):
        self.sessions, self.panes, self.sent = sessions, panes, []

    def __call__(self, *args):
        if args[0] == "list-sessions":
            out = "\n".join(self.sessions) + "\n"
        elif args[0] == "capture-pane":
            out = self.panes.get(args[args.index("-t") + 1], "")
        elif args[0] == "send-keys":
            self.sent.append((args[args.index("-t") + 1], args[-1]))
            out = ""
        else:
            raise AssertionError(args)
        return subprocess.CompletedProcess(["tmux", *args], 0, out, "")


@pytest.fixture
def box(tmp_path, monkeypatch):
    sessions_dir, locks = tmp_path / "sessions", tmp_path / "locks"
    sessions_dir.mkdir()
    locks.mkdir()
    monkeypatch.setattr(ls, "session_dirs", lambda host: [sessions_dir])
    monkeypatch.setattr(rr, "LOCKS_DIR", locks)
    monkeypatch.setattr(ls, "LOCKS_DIR", locks)
    monkeypatch.setattr(config, "self_host", lambda: "contabo")
    n = [100]

    def record(uuid, name, tmux):
        n[0] += 1
        (sessions_dir / f"{n[0]}.json").write_text(json.dumps(
            {"pid": os.getpid(), "sessionId": uuid, "name": name, "tmux": tmux}))

    record(U_CTO, "CTO (Kavin) — CTO Main", "cto-c34459eb:@1.%1")
    record(U_PH, "CONTABO Project Head (CTO) #7cf528f0 (OrgRestructure)", "project_head-7cf528f0:@2.%2")
    record(U_WD, "CTO (Kavin)", "wd-afe57b21:@3.%3")
    record(U_COO, "COO (SomPong)", "sompong:@4.%4")
    (locks / "project_head-7cf528f0.project").write_text("OrgRestructure\n")
    (locks / "project_head-7cf528f0.spawned_by").write_text("cxo:cto:c34459eb\n")
    empty = "  some output\n❯ \n  ? for shortcuts\n"
    fake = FakeTmux(["cto-c34459eb", "project_head-7cf528f0", "wd-afe57b21", "sompong", "scratch"],
                    {"cto-c34459eb": empty, "project_head-7cf528f0": empty, "sompong": empty})
    monkeypatch.setattr(rr, "tmux", fake)
    return fake, locks


def test_the_dry_run_plans_rule_names_and_types_nothing(box, capsys):
    fake, _ = box
    assert rr.main([]) == 1          # sompong: no launcher uuid file -> skipped
    out = capsys.readouterr().out.splitlines()
    assert out == [
        f'rename   cto-c34459eb "CTO (Kavin) — CTO Main" -> "{CONTABO} CTO (Kavin) — CTO Main" (no host emoji)',
        f'rename   project_head-7cf528f0 "CONTABO Project Head (CTO) #7cf528f0 (OrgRestructure)" -> '
        f'"{CONTABO} PH#7cf (CTO) - OrgRestructure" (no host emoji)',
        "skip     sompong (not the launcher's COO session)",
    ]
    assert fake.sent == []           # workers ("wd-…") and other tmux are never listed


def test_apply_types_rename_only_into_an_empty_prompt(box, capsys):
    fake, locks = box
    (locks / "coo-fde4c4ca.uuid").write_text(U_COO + "\n")
    fake.panes["project_head-7cf528f0"] = "❯ half-typed CEO draft\n"
    assert rr.main(["--apply"]) == 1
    out = capsys.readouterr().out
    assert fake.sent == [("cto-c34459eb", f"/rename {CONTABO} CTO (Kavin) — CTO Main"),
                         ("cto-c34459eb", "Enter"),
                         ("sompong", f"/rename {CONTABO} COO (SomPong)"), ("sompong", "Enter")]
    [ph] = [l for l in out.splitlines() if "project_head-7cf528f0" in l]
    assert ph.startswith("skip     project_head-7cf528f0") and "prompt line not empty" in ph


def test_a_name_already_on_the_rule_is_left_alone(box, capsys):
    fake, _ = box
    assert rr.main(["--apply", "--session", "cto-c34459eb"]) == 0
    fake.sent.clear()
    for f in ls.session_dirs("contabo")[0].iterdir():
        d = json.loads(f.read_text())
        if d["sessionId"] == U_CTO:
            d["name"] = f"⏸ {CONTABO} CTO (Kavin) — CTO Main"
            f.write_text(json.dumps(d))
    capsys.readouterr()
    assert rr.main(["--apply", "--session", "cto-c34459eb"]) == 0
    assert fake.sent == [] and capsys.readouterr().out.startswith("ok       cto-c34459eb")


def test_a_ph_with_no_project_record_is_skipped_not_guessed(box, capsys):
    fake, locks = box
    (locks / "project_head-7cf528f0.spawned_by").unlink()
    rr.main(["--apply", "--session", "project_head-7cf528f0"])
    assert fake.sent == []
    assert "no .project/.spawned_by record" in capsys.readouterr().out


@pytest.mark.parametrize("name,topic", [
    ("CTO (Kavin) — CTO Main", "CTO Main"), ("CONTABO CMO #ef04792e (CMO Main)", "CMO Main"),
    ("PH#36c (CMO) - MimiPage — MimiPage", "MimiPage"), ("CTO (Kavin)", ""),
])
def test_the_topic_carried_over(name, topic):
    assert rr.topic_of(name) == topic


def test_a_ph_topic_equal_to_its_project_is_dropped(box):
    _, locks = box
    (locks / "project_head-36c49776.project").write_text("MimiPage")
    (locks / "project_head-36c49776.spawned_by").write_text("cxo:cmo:ef04792e")
    assert rr.rule_name("project_head", "36c49776", "contabo",
                        "PH#36c (CMO) - MimiPage — MimiPage") == (f"{CONTABO} PH#36c (CMO) - MimiPage", "")
