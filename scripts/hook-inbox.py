#!/usr/bin/env python3
"""UserPromptSubmit hook: drain this session's mailbox and print it.

Task task-de2cdc15 (CEO directive 2026-08-14, option A). Read-side
counterpart to `lib/mailbox.py` -- modelled on `scripts/hook-recall.py`'s
shape: read the event JSON on stdin, print to stdout, fail silent with
`return 0` always. A hook that raises must never block a prompt.

Drains the CURRENT session's own box and prints the letters as context.
The box is resolved from env only -- `CXO_ROLE` + `CXO_SESSION_ID`
(`CTO_SESSION_ID` for a plain `cto-claude.sh` launch, which exports that
instead) for a C-level session, or `WORKER_TASK_ID`/`WORKER_ROLE` for a DEV
worktree -- the same resolution `tools/send_to_cxo.py`'s
`current_identity()` uses. Never from anything a caller passes: a prompt
cannot ask this hook to open somebody else's box.

Draining is exactly-once (`lib.mailbox.drain`), so the same letter is
never printed twice. Prints nothing when the box is empty -- this runs on
every prompt of every session, so silence (the common case) must cost
nothing.

Also, for a C-level session only, makes sure the host's live-sessions
publisher is running (`tools.live_sessions.ensure_publisher`, task-9c563bea).
A hook SCRIPT is read from disk on every prompt, unlike the hook CONFIG, which
Claude Code snapshots at startup -- so a `git pull` is the whole rollout: the
next prompt on that host starts the publisher. One open + flock when it is
already alive; nothing printed, nothing raised.

Envelope mode (`ORG_MAIL_ENVELOPE=1`, default off; org restructure P1): one
envelope line per letter (id, kind/prio, sender, time, subject), with the body
inline only when it is ENVELOPE_BODY_MAX characters or fewer; a longer one is
read with `read_letter("<id>")` (org MCP) or `python -m tools.letters read <id>`.
`lib.mailbox.drain` then marks the letters read instead of deleting them.
Off, the output is exactly as before.

CEO notes in full (wake chain W1, design C6, 2026-10-30), both modes: the
Console's body line cuts what the CEO typed on /run (notify.js firstLine: a
note to its first 120 characters, an "ask back" to its first line). The letter
carries the full text, so after the body of a letter from run-inbox the hook
prints each note in full, up to NOTE_MAX characters, as a quoted block:
answer.text of a question letter, each answer.text of a question batch, and
the question of an ask-back. A note the printed body already holds whole is
not printed twice. No other field is printed: not a result's output tail, not
the operator's name.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ENVELOPE_BODY_MAX = 400
NOTE_MAX = 2000          # the Console's own cap on a note (src/run/questions.js MAX_NOTE)
NOTE_SENDER = "run-inbox"


def _envelope_on() -> bool:
    return os.environ.get("ORG_MAIL_ENVELOPE", "").strip().lower() in ("1", "true", "yes", "on")


def _one_line(value, cap: int) -> str:
    """A field a sender wrote, as one bounded line: a newline in a subject or a
    sender name must not print a second envelope line."""
    return " ".join(str(value if value is not None else "").split())[:cap]


def _answer_text(record) -> str | None:
    answer = record.get("answer") if isinstance(record, dict) else None
    text = answer.get("text") if isinstance(answer, dict) else None
    return text if isinstance(text, str) else None


def _ceo_notes(letter: dict) -> list[tuple[str, str, str]]:
    """(what, card id, text) for each note the CEO typed on /run that a
    run-inbox letter carries: the answer note of a question letter, of each
    question in a batch, and the question of an ask-back on a pending command
    card. Nothing for any other sender or field.

    The letter's shape decides, not its kind: with the envelope flag on,
    lib.mailbox._fill rewrites a kind it does not know ("question",
    "question_batch") to "message" before this hook sees the letter."""
    frm = letter.get("from")
    if not isinstance(frm, dict) or frm.get("role") != NOTE_SENDER:
        return []
    found: list[tuple[str, object, str | None]] = []
    if isinstance(letter.get("answer"), dict):          # one question (Console kind "question")
        found.append(("note", letter.get("id"), _answer_text(letter)))
    questions = letter.get("questions")
    for q in questions if isinstance(questions, list) else []:   # "question_batch"
        found.append(("note", q.get("id") if isinstance(q, dict) else None, _answer_text(q)))
    if isinstance(letter.get("question"), str):         # an ask-back, the card still pending
        found.append(("question", letter.get("id"), letter.get("question")))
    return [(what, _one_line(card or "?", 96), text) for what, card, text in found
            if text and text.strip()]


def _note_lines(letter: dict, shown: str) -> list[str]:
    """The quoted block printed after a letter's body (see the module
    docstring). `shown` is the body text already printed in full, "" when it
    was not printed. Never raises: a malformed letter gives no lines."""
    try:
        out: list[str] = []
        for what, card, text in _ceo_notes(letter):
            if text in shown:
                continue                    # the body already holds it whole
            # a lone surrogate (a \ud800 escape in the JSON) would make print() raise
            # after the letter was drained: it becomes "?"
            full = text[:NOTE_MAX].encode("utf-8", "replace").decode("utf-8")
            out.append(f"    > CEO {what} in full ({card}):")
            out.extend(f"    > {ln}" for ln in full.splitlines())
            if len(text) > NOTE_MAX:
                out.append(f"    > ...[cut at {NOTE_MAX} of {len(text)} chars]")
        return out
    except Exception:
        return []


def _print_envelopes(letters: list[dict]) -> None:
    print(f"## Mailbox — {len(letters)} letter(s), marked read "
          f"(a body over {ENVELOPE_BODY_MAX} chars: read_letter(\"<id>\") "
          f"or `python -m tools.letters read <id>`)")
    print()
    for letter in letters:
        frm = letter.get("from") if isinstance(letter.get("from"), dict) else {}
        who = (f"{_one_line(frm.get('role') or '?', 24).upper()} "
               f"{_one_line(frm.get('session_id', '?'), 40)}")
        kind = _one_line(letter.get("kind") or "message", 16)
        prio = _one_line(letter.get("prio") or "normal", 16)
        tag = (kind if prio == "normal" else f"{kind}/{prio}").upper()
        lid = _one_line(letter.get("id") or "?", 96)
        body = str(letter.get("body") or "")
        subject = _one_line(letter.get("subject") or body, 80)
        print(f"- [{lid}] {tag} from {who} · {_one_line(letter.get('sent_at', ''), 32)} · {subject}")
        shown = ""
        if len(body) <= ENVELOPE_BODY_MAX:
            for ln in body.splitlines() or [""]:
                print(f"    {ln}")
            shown = body
        else:
            print(f"    ({len(body)} chars, not shown: read_letter(\"{lid}\"))")
        for ln in _note_lines(letter, shown):
            print(ln)
    print()


def _current_box() -> tuple[str, str] | None:
    """(role, session_id) for the box THIS session drains, or None if this
    session (e.g. a bare CEO shell) has no box of its own."""
    role = os.environ.get("CXO_ROLE")
    if role:
        sid = os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
        return (role, sid) if sid else None
    task_id = os.environ.get("WORKER_TASK_ID")
    if task_id:
        return os.environ.get("WORKER_ROLE", "dev"), task_id
    return None


def _ensure_live_publisher() -> None:
    """C-level sessions only (CXO_ROLE set, no WORKER_TASK_ID). Ignores the
    result and every error: this must never cost a prompt anything."""
    try:
        if not os.environ.get("CXO_ROLE") or os.environ.get("WORKER_TASK_ID"):
            return
        # scripts/test_mailbox.py drives main() with CXO_ROLE set; a test run
        # must not start a publisher against the real hub
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        # a hook's stdout becomes the model's context on EVERY prompt: whatever the
        # call writes, it never reaches it
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            from tools import live_sessions
            live_sessions.ensure_publisher()
    except Exception:
        pass


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    _ensure_live_publisher()    # before the drain: an empty box still runs it
    box = _current_box()
    if box is None:
        return 0
    role, session_id = box

    try:
        from lib import mailbox
        letters = mailbox.drain(role, session_id)
    except Exception:
        return 0
    if not letters:
        return 0

    if _envelope_on():
        _print_envelopes(letters)
        return 0

    print(f"## Mailbox — {len(letters)} letter(s) delivered (drained; each arrives once)")
    print()
    for letter in letters:
        frm = letter.get("from") or {}
        role_label = str(frm.get("role") or "?").upper()
        body = letter.get("body", "")
        print(f"[{role_label}] : {body}")
        for ln in _note_lines(letter, str(body)):
            print(ln)
        print(f"    ({frm.get('session_id', '?')} · {letter.get('sent_at', '')})")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
