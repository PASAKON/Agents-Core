"""lib.mailbox's letter log (M11): from, to, kind and time of every letter, never the body."""
from __future__ import annotations

import json

import pytest

from lib import mailbox


@pytest.mark.parametrize("body,kind", [
    ("blocker · urgent · key missing", "blocker"),
    ("[Project Head (CTO) #7cf528f0] : blocker · urgent · x", "blocker"),
    ("report · normal · M9 done", "report"),
    ("[Project Head (CTO) #7cf528f0] : fyi · normal · x", "fyi"),
    ("[a\nb] : blocker · urgent · x", None),
    ("blocked on the key", None),
    ("[x] : nonsense · y", None),
])
def test_the_kind_is_read_off_the_body_while_the_envelope_is_off(body, kind):
    assert mailbox.body_kind(body) == kind


def test_send_logs_one_line_without_the_body(tmp_path, monkeypatch):
    log = tmp_path / "letters-meta.jsonl"
    monkeypatch.setenv("ORG_LETTERS_META", str(log))
    mailbox.send("cto", "c34459eb", "blocker · urgent · SECRET-ish text", "project_head", "7cf528f0",
                 root=tmp_path / "inbox")
    mailbox.send("project_head", "7cf528f0", "answer", "cto", "c34459eb", root=tmp_path / "inbox",
                 kind="answer")
    lines = [json.loads(l) for l in log.read_text().splitlines()]
    assert [(l["from"], l["to"], l["kind"]) for l in lines] == [
        ("project_head-7cf528f0", "cto-c34459eb", "blocker"),
        ("cto-c34459eb", "project_head-7cf528f0", "answer")]
    assert "SECRET" not in log.read_text() and all(l["sent_at"].endswith("Z") for l in lines)


def test_a_log_that_cannot_be_written_never_fails_the_letter(tmp_path, monkeypatch):
    (tmp_path / "blocked").write_text("a file, not a dir")
    monkeypatch.setenv("ORG_LETTERS_META", str(tmp_path / "blocked" / "x.jsonl"))
    p = mailbox.send("cto", "c34459eb", "hi", "cmo", "ef04792e", root=tmp_path / "inbox")
    assert p.exists()
