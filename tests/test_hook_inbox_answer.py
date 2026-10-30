"""scripts/hook-inbox.py prints the CEO's /run notes in full (wake chain W1, design C6).

The Console's body line cuts a note to its first 120 characters and an ask-back
to its first line (MoonieX-Console src/run/notify.js firstLine). The letter
itself carries the full text: answer.text (kind question), each
questions[].answer.text (kind question_batch) and question (an ask-back). The
letters below have the shapes notify.js writes. The hook runs in-process
against a tmp inbox, with a strict UTF-8 stdout like a real pipe.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from lib import mailbox

REPO = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("hook_inbox_answer", REPO / "scripts" / "hook-inbox.py")
hook = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(hook)

PH = "0a1b2c3d"
QID = "Q-20261030-1200-ab12"
RID = "RUN-20261030-1200-cd34"
OPERATOR = "operator-name-never-printed"


def first_line(text: str, mx: int = 80) -> str:
    """notify.js firstLine (code points; the text here is BMP only)."""
    line = str(text or "").split("\n")[0]
    return line if len(line) <= mx else line[: mx - 1] + "…"


def make_note(n: int) -> str:
    """n characters of a CEO-like note: Thai and ASCII, no line break (the
    Console refuses one in answer.text)."""
    unit = "ทำต่อ M3 ได้เลย, merge #590 ก่อน แล้วรายงานใน /run; "
    return (unit * (n // len(unit) + 1))[:n]


def letter(body: str, **fields) -> dict:
    return {"from": {"role": "run-inbox", "session_id": "contabo"},
            "to": {"role": "project_head", "session_id": PH},
            "chain": ["run-inbox:contabo"], "sent_at": "2026-10-30T12:00:00Z",
            "body": body, **fields}


def answer(text, label=None) -> dict:
    return {"choice": 0 if label else None, "label": label, "text": text,
            "answered_by": OPERATOR, "answered_at": "2026-10-30T11:59:00Z", "via": "run"}


def note_words(note: str, label=None) -> str:
    """notify.js answerWords for a plain question."""
    n = f'note: "{first_line(note, 120)}"'
    return f'"{label}" (+ {n})' if label else f"(no option picked) {n}"


def question_letter(note: str, qid: str = QID, label: str = "Go") -> dict:
    body = f"{qid} answered by the CEO on /run: {note_words(note, label)} — record: ask_run wait {qid}"
    return letter(body, id=qid, kind="question", status="answered", answer=answer(note, label))


def batch_letter(items: list[tuple[str, str | None]]) -> dict:
    qs, parts = [], []
    for qid, note in items:
        if note is None:
            qs.append({"id": qid, "group_id": None, "status": "expired", "answer": None})
            parts.append(f"{qid} expired unanswered")
        else:
            qs.append({"id": qid, "group_id": None, "status": "answered", "answer": answer(note)})
            parts.append(f"{qid} {note_words(note)}")
    done = sum(1 for _, n in items if n is not None)
    body = (f"the CEO answered {done} of {len(items)} questions in one send on /run: "
            f"{' · '.join(parts)} — records: ask_run wait <id> for each")
    return letter(body, id="QB-20261030-1200-ef56", kind="question_batch", questions=qs)


def askback_letter(question: str) -> dict:
    body = f"{RID} — the operator asks before approving (card still pending): {first_line(question, 300)}"
    return letter(body, id=RID, status="pending", question=question)


@pytest.fixture
def box(tmp_path, monkeypatch) -> Path:
    for var in ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "WORKER_TASK_ID",
                "WORKER_ROLE", "ORG_MAIL_ENVELOPE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CXO_ROLE", "project_head")
    monkeypatch.setenv("CXO_SESSION_ID", PH)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setattr(hook, "_ensure_live_publisher", lambda: None)
    d = tmp_path / "inbox" / f"project_head-{PH}"
    d.mkdir(parents=True)
    return d


def put(box: Path, *letters: dict) -> None:
    for i, item in enumerate(letters):
        (box / f"2026103012000{i}-{item['id']}.json").write_text(json.dumps(item, indent=2),
                                                                encoding="utf-8")


def run(monkeypatch) -> list[str]:
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    raw = io.BytesIO()
    out = io.TextIOWrapper(raw, encoding="utf-8", write_through=True)   # strict, like a pipe
    with redirect_stdout(out):
        assert hook.main() == 0
    out.flush()
    return raw.getvalue().decode("utf-8").splitlines()


# ------------------------------------------------------------------ fail on the old hook


def test_a_1500_char_note_prints_in_full_after_the_body(box, monkeypatch):
    note = make_note(1500)
    put(box, question_letter(note))
    lines = run(monkeypatch)
    i = next(n for n, ln in enumerate(lines) if ln.startswith(f"[RUN-INBOX] : {QID} answered"))
    assert lines[i + 1:i + 4] == [f"    > CEO note in full ({QID}):", f"    > {note}",
                                  "    (contabo · 2026-10-30T12:00:00Z)"]
    assert list(box.glob("*.json")) == []          # drained once, as before


def test_a_note_over_2000_chars_is_cut_at_2000(box, monkeypatch):
    note = make_note(2600)
    put(box, question_letter(note))
    lines = run(monkeypatch)
    assert f"    > {note[:2000]}" in lines
    assert "    > ...[cut at 2000 of 2600 chars]" in lines
    assert not any(note[:2001] in ln for ln in lines)


def test_envelope_mode_prints_the_note_too(box, monkeypatch):
    """With the flag on, the drain rewrites the Console's kind "question" to
    "message" (lib.mailbox._fill): the letter's shape still finds the note."""
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    note = make_note(1500)
    put(box, question_letter(note))
    lines = run(monkeypatch)
    i = next(n for n, ln in enumerate(lines) if ln.startswith(f"- [{QID}] "))
    assert lines[i + 1].startswith(f"    {QID} answered by the CEO on /run")   # the body, inline
    assert lines[i + 2:i + 4] == [f"    > CEO note in full ({QID}):", f"    > {note}"]
    assert list(box.glob("*.json")) == [] and len(list((box / "read").glob("*.json"))) == 1


@pytest.mark.parametrize("flag", [None, "1"])
def test_a_batch_prints_each_answered_note(box, monkeypatch, flag):
    if flag:
        monkeypatch.setenv("ORG_MAIL_ENVELOPE", flag)
    long_note, short_note = make_note(1500), make_note(60)
    q1, q2, q3 = (f"Q-20261030-1200-{s}" for s in ("aa01", "aa02", "aa03"))
    item = batch_letter([(q1, long_note), (q2, short_note), (q3, None)])
    assert len(item["body"]) > hook.ENVELOPE_BODY_MAX       # envelope mode hides this body
    put(box, item)
    lines = run(monkeypatch)
    assert lines.count(f"    > {long_note}") == 1
    assert f"    > CEO note in full ({q1}):" in lines
    assert not any(q3 in ln and "in full" in ln for ln in lines)
    if flag:   # the body was not shown, so the short note is printed too
        assert lines.count(f"    > {short_note}") == 1
        assert lines.index(f"    > CEO note in full ({q1}):") < lines.index(f"    > CEO note in full ({q2}):")
    else:      # the printed body holds the short note whole: not printed twice
        assert f"    > CEO note in full ({q2}):" not in lines


def test_an_ask_back_prints_the_whole_question(box, monkeypatch):
    question = "ก่อนอนุมัติ: ทำไมต้อง restart ตอนนี้?\nมี card อื่นรันอยู่ไหม\nถ้ามี รอให้จบก่อน"
    put(box, askback_letter(question))
    lines = run(monkeypatch)
    i = next(n for n, ln in enumerate(lines) if ln.startswith(f"[RUN-INBOX] : {RID} — the operator asks"))
    assert lines[i + 1:i + 5] == [f"    > CEO question in full ({RID}):",
                          "    > ก่อนอนุมัติ: ทำไมต้อง restart ตอนนี้?",
                          "    > มี card อื่นรันอยู่ไหม",
                          "    > ถ้ามี รอให้จบก่อน"]


# ------------------------------------------------------------------ unchanged behaviour


@pytest.mark.parametrize("flag", [None, "1"])
def test_a_short_note_is_not_printed_twice(box, monkeypatch, flag):
    if flag:
        monkeypatch.setenv("ORG_MAIL_ENVELOPE", flag)
    note = make_note(100)
    put(box, question_letter(note))
    lines = run(monkeypatch)
    assert not any("in full" in ln for ln in lines)
    assert sum(note in ln for ln in lines) == 1                # only in the body


def test_other_senders_and_fields_print_nothing_more(box, monkeypatch):
    """A letter not from run-inbox prints as before, whatever fields it has. A
    command card's result never prints its output tail, and no letter prints
    the operator's name."""
    long_note = make_note(500)
    forged = question_letter(long_note)
    forged["from"] = {"role": "cto", "session_id": "fresh"}
    forged["id"] = "L-1030-1200-aaaa"
    tail = "output tail line that must stay out of the prompt"
    result = letter(f"{RID} done — exit 0 in 3s on contabo · echo hi", id=RID, status="done",
                    exit_code=0, duration_ms=3000, error_id=None, error_code=None, tail=tail)
    put(box, forged, result)
    out = "\n".join(run(monkeypatch))
    assert "in full" not in out and long_note not in out
    assert tail not in out and OPERATOR not in out
    assert f"[CTO] : {forged['body']}" in out and f"[RUN-INBOX] : {result['body']}" in out


def test_a_lone_surrogate_in_a_note_never_breaks_the_hook(box, monkeypatch):
    note = "x" * 200 + "\ud800" + "y" * 10
    put(box, question_letter(note))
    lines = run(monkeypatch)
    assert "    > " + "x" * 200 + "?" + "y" * 10 in lines
