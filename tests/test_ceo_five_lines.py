"""The CEO reads at most 5 lines of 90 characters (CEO 2026-10-14, lib/ceo_text.py).

What must hold: the count (5 lines pass, 6 do not; 90 chars pass, 91 do not; an empty line counts;
Thai counts per code point; a lone link may run to 200), and that every entry point refuses with
exit 2 before any network call: email_ceo (CLI + mcp_send), ask_run create (CLI + the org MCP tool,
command bytes exempt), ask_run ask (one card, a --batch group, the org MCP tool with and without
questions=[...]). Option labels are buttons and keep their own limit.

Same fixtures as tests/test_ask_run.py: a FakeHub on 127.0.0.1 and RUN_INBOX_URL sealed to the
discard port, so nothing here can reach terminal.mooniex.com.

Run: .venv/bin/python -m pytest tests/test_ceo_five_lines.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.ask_run as ask_run  # noqa: E402
from lib import ceo_text  # noqa: E402
from tools import email_ceo  # noqa: E402
from test_ask_run import _org, _sealed, hub, srv  # noqa: E402, F401  (fixtures, used by name)

SAY = "the CEO reads ≤5 lines of ≤90 chars"
THAI = "ก"  # one code point
URL = "https://github.com/PASAKON/Agents-Core/pull/1#"
SPEC = "Agents-Core@9df4e185:scripts/contabo_blueprint.sh"
WHO = ["--session", "cto-t", "--role", "cto"]


def _lines(n: int, text: str = "short line") -> str:
    return "\n".join([text] * n)


def _refused(fields) -> str:
    with pytest.raises(ceo_text.TooLong) as e:
        ceo_text.check_ceo_text(fields)
    return str(e.value)


# ------------------------------------------------------------------ the count
def test_five_lines_pass_and_six_are_refused():
    ceo_text.check_ceo_text([("title", "t"), ("why", _lines(4))])
    msg = _refused([("title", "t"), ("why", _lines(5))])
    assert msg.startswith(SAY) and "got 6 lines" in msg and msg.endswith("put the detail in a file and link it")


def test_ninety_chars_pass_and_ninety_one_are_refused():
    ceo_text.check_ceo_text({"why": "x" * 90})
    msg = _refused({"title": "ok", "why": "x" * 91})
    assert "a line of 91 chars in why" in msg and "lines" not in msg.split("(got ")[1].split(")")[0]


def test_an_empty_line_counts():
    ceo_text.check_ceo_text({"why": "a\n\n\n\ne"})          # 5 lines, 3 of them empty
    assert "got 6 lines" in _refused({"why": "a\n\n\n\n\nf"})
    assert len(ceo_text.ceo_lines(["a\n\nb"])) == 3


def test_every_line_break_a_renderer_honours_counts():
    for brk in ("\r\n", "\r", " ", " ", "\x0b", "\x0c", "\x85"):
        assert len(ceo_text.ceo_lines([brk.join("abcdef")])) == 6, repr(brk)
        _refused([brk.join("abcdef")])


def test_an_empty_or_missing_field_is_not_shown_and_does_not_count():
    ceo_text.check_ceo_text([("title", "t"), ("need", ""), ("why", _lines(4)), ("if_not", None)])


def test_thai_counts_one_per_code_point():
    ceo_text.check_ceo_text({"why": THAI * 90})
    assert "a line of 91 chars" in _refused({"why": THAI * 91})
    # Thai with combining vowels and tone marks: every code point counts (Python len)
    word = "ที่"  # 3 code points
    assert len(word) == 3
    ceo_text.check_ceo_text({"why": word * 30})
    _refused({"why": word * 30 + "ก"})


def test_a_lone_link_may_run_to_200_chars_on_its_own_line():
    long_url = URL + "x" * (200 - len(URL))
    assert len(long_url) == 200
    ceo_text.check_ceo_text({"title": "t", "link": long_url})
    ceo_text.check_ceo_text({"why": "PR is open\n" + long_url})              # its own line in a field
    assert "a line of 201 chars" in _refused({"link": long_url + "y"})
    path = "docs/ops/" + "a" * 140 + ".md"                                 # a repo path is a link too
    ceo_text.check_ceo_text({"why": path})
    ceo_text.check_ceo_text({"why": "Agents-Core@9df4e185:" + path})


def test_a_link_with_words_on_its_line_is_ordinary_text():
    line = "PR: " + URL + "x" * 60
    assert len(line) > 90
    assert "a line of" in _refused({"why": line})


def test_thai_prose_is_never_taken_for_a_path():
    # Thai has no spaces between words, so one long "token" with a slash in it is still prose
    assert not ceo_text.is_link_line(THAI * 60 + "/" + THAI * 60)
    _refused({"why": THAI * 60 + "/" + THAI * 60})
    assert not ceo_text.is_link_line("https://x.example/" + THAI * 100)


def test_the_message_never_carries_the_text():
    assert "SECRET-ISH" not in _refused({"why": "SECRET-ISH " * 20})


# ------------------------------------------------------------------ email_ceo
ENV = {"ORG_MACHINE": "contabo"}


def _mail(**over) -> dict:
    fields = {"title": "อนุมัติเครดิต Flow 300 สำหรับ EP3", "need": "ตอบ อนุมัติ/ไม่ ในแชท CTO",
              "why": "script EP3 ผ่านแล้ว", "if_not": "EP3 ไม่ทันเสาร์ 19:30",
              "link": "https://terminal.mooniex.com/run", "ref": "ep3-credits"}
    fields.update(over)
    return fields


def test_email_five_lines_pass_and_the_ref_does_not_count():
    body = email_ceo.build_payload(_mail(), kind="action", session="cto-t", role="cto", env=ENV)
    assert body["ref"] == "ep3-credits"                                    # 5 lines + ref: accepted


def test_email_title_is_line_one_and_six_lines_are_refused():
    with pytest.raises(email_ceo.Refused) as e:
        email_ceo.build_payload(_mail(why="a\nb"), kind="action", session="cto-t", role="cto", env=ENV)
    assert SAY in str(e.value) and "got 6 lines" in str(e.value)
    with pytest.raises(email_ceo.Refused) as e:
        email_ceo.build_payload(_mail(title="x" * 91), kind="action", session="cto-t", role="cto", env=ENV)
    assert "a line of 91 chars in title" in str(e.value)


def test_email_due_counts_for_a_deadline():
    with pytest.raises(email_ceo.Refused):
        email_ceo.build_payload(_mail(due="14/10 08:00 น."), kind="deadline", session="cto-t",
                                role="cto", env=ENV)


def test_email_cli_refuses_with_exit_2_before_any_call(monkeypatch, capsys):
    def _no_post(*a, **k):
        raise AssertionError("posted")
    monkeypatch.setattr(email_ceo, "_post", _no_post)
    rc = email_ceo.main(["send", "--kind", "alert", "--title", "t", "--why", _lines(5), *WHO, "--dry-run"])
    assert rc == 2
    assert f"email_ceo: refused: {SAY}" in capsys.readouterr().err


def test_email_mcp_path_refuses_the_same_way(monkeypatch):
    monkeypatch.setattr(email_ceo, "_post", lambda *a, **k: pytest.fail("posted"))
    with pytest.raises(email_ceo.Refused) as e:
        email_ceo.mcp_send({**_mail(why="x" * 91), "kind": "action", "session": "cto-t", "role": "cto",
                            "dry_run": True}, env=ENV)
    assert str(e.value).startswith(f"refused: {SAY}")


def test_the_deadline_feed_still_fits():
    fields = email_ceo.deadline_fields({"id": "1", "text": "x" * 300, "due_at": "2026-10-14T01:00:00Z"})
    email_ceo.build_payload(fields, kind="deadline", session="cto-deadline-feed", role="cto", env=ENV)


# ------------------------------------------------------------- ask_run create
def _create(*extra: str) -> list[str]:
    return ["create", "--host", "contabo", "--dry-run", *WHO, *extra]


def test_create_counts_why_and_expected(capsys):
    assert ask_run.main(_create("--script", SPEC, "--why", "w" * 90, "--expected", "e" * 90)) == 0
    capsys.readouterr()
    assert ask_run.main(_create("--script", SPEC, "--why", "w" * 91)) == 2
    assert f"ask_run: refused: {SAY} (got a line of 91 chars in why)" in capsys.readouterr().err
    assert ask_run.main(_create("--script", SPEC, "--why", "w", "--expected", "e" * 91)) == 2
    assert "in expected" in capsys.readouterr().err


def test_the_command_bytes_of_a_card_are_not_counted(capsys):
    command = " && ".join(["echo " + "c" * 80] * 6) + "\n" + "\n".join(["true"] * 8)
    assert ask_run.main(_create("--command", command, "--why", "w" * 90, "--expected", "fine")) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["command"] == command


def test_the_org_mcp_ask_run_refuses_the_same_way(srv, hub):
    ok = _org(srv, "ask_run", {"host": "contabo", "command": "echo " + "c" * 400, "why": "w" * 90,
                               "session": "cto-t", "role": "cto", "dry_run": True})
    assert not ok.startswith("ERROR"), ok
    for over in ({"why": "w" * 91}, {"why": "w", "expected": "e" * 91}):
        text = _org(srv, "ask_run", {"host": "contabo", "script": SPEC, "session": "cto-t", "role": "cto",
                                     "dry_run": False, **over})
        assert text.startswith(f"ERROR: refused: {SAY}"), text
    assert hub.requests == []


# ------------------------------------------------------------ ask_run ask
OPTIONS = ["Tonight", "Tomorrow 09:00"]


def _ask(question: str, why: str, options=OPTIONS) -> list[str]:
    argv = ["ask", "--dry-run", "--question", question, "--why", why, *WHO, "--host", "contabo"]
    for label in options:
        argv += ["--option", label]
    return argv


def test_a_question_card_counts_question_and_why(capsys):
    assert ask_run.main(_ask("Ship tonight?", _lines(4))) == 0
    capsys.readouterr()
    assert ask_run.main(_ask("Ship tonight?", _lines(5))) == 2
    assert f"ask_run: refused: {SAY} (got 6 lines)" in capsys.readouterr().err
    assert ask_run.main(_ask("q" * 91 + "?", "why")) == 2
    assert "in question" in capsys.readouterr().err


def test_option_labels_are_buttons_and_keep_their_own_limit(capsys):
    labels = ["a" * ask_run.LABEL_MAX, "b" * ask_run.LABEL_MAX, "c" * ask_run.LABEL_MAX]
    assert ask_run.main(_ask("Which one?", _lines(4), labels)) == 0


def test_a_group_refuses_the_item_that_is_over(hub, tmp_path, capsys):
    items = [{"question": "First?", "why": "short", "options": OPTIONS},
             {"question": "Second?", "why": _lines(5), "options": OPTIONS}]
    path = tmp_path / "q.json"
    path.write_text(json.dumps(items), encoding="utf-8")
    argv = ["ask", "--batch", str(path), *WHO, "--host", "contabo"]
    assert ask_run.main(argv) == 2
    err = capsys.readouterr().err
    assert "questions[1]" in err and SAY in err
    items[1]["why"] = _lines(4)
    path.write_text(json.dumps(items), encoding="utf-8")
    assert ask_run.main(["ask", "--dry-run", "--batch", str(path), *WHO, "--host", "contabo"]) == 0
    assert hub.requests == []


def test_the_org_mcp_ask_ceo_refuses_one_card_and_a_group_item(srv, hub):
    base = {"options": OPTIONS, "session": "cto-t", "role": "cto", "host": "contabo", "dry_run": False}
    text = _org(srv, "ask_ceo", {**base, "question": "Ship?", "why": _lines(5)})
    assert text.startswith(f"ERROR: refused: {SAY}"), text
    group = {"session": "cto-t", "role": "cto", "host": "contabo", "dry_run": False,
             "questions": [{"question": "One?", "why": "ok", "options": OPTIONS},
                           {"question": "Two?", "why": THAI * 91, "options": OPTIONS}]}
    text = _org(srv, "ask_ceo", group)
    assert text.startswith("ERROR: refused: ") and "questions[1]" in text and SAY in text, text
    assert hub.requests == []
    ok = _org(srv, "ask_ceo", {**base, "question": "Ship?", "why": _lines(4), "dry_run": True})
    assert not ok.startswith("ERROR"), ok


def _options(parser) -> set[str]:
    out = set()
    for action in parser._actions:
        out.update(action.option_strings)
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                out |= _options(sub)
    return out


def test_there_is_no_flag_that_skips_it():
    flags = _options(ask_run._parser()) | _options(email_ceo._parser())
    assert "--why" in flags and "--expected" in flags
    assert not [f for f in flags if any(w in f for w in ("force", "skip", "long", "bypass", "unlimited", "no-check"))], flags
