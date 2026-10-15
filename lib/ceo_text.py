"""What the CEO reads: at most 5 lines of at most 90 characters (CEO 2026-10-14).

CEO order, 14 Oct 2026: every email to him and every Run card is 5 lines or fewer, topic, subject
and body together. Alert only, plain words, laid out so it reads at a glance. The detail goes in a
linked file, never in the mail or the card.

One check, called where each body is built, so the CLI and the MCP tool share it:
    tools/email_ceo.py  build_payload   title + need + why + if_not + link + due (title = line 1)
    tools/ask_run.py    prepare_ask     command card: why + expected (the command bytes are exempt:
                                        they are what he approves, and the Console folds them)
    tools/ask_run.py    prepare_question  question card, alone or one item of a group: question + why
                                        (option labels are buttons, with their own limit)

How it counts (CTO ruling 2026-10-14):
  - only the text he reads: the fields the caller passes, in order; a field that is None or empty
    is not shown and does not count;
  - every line counts, an empty one too ("a\\n\\nb" is 3 lines);
  - a line is at most 90 characters by Python len (Thai counts one per code point);
  - a line that is one link and nothing else (an http(s) URL or a repo path) may be up to 200
    characters, so a long link still fits on a line of its own.
There is no flag that skips it.

Stdlib only: tools/ask_run.py runs on any box's python3.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

MAX_LINES = 5
MAX_CHARS = 90
MAX_LINK_CHARS = 200

# Every break a renderer might honour, so a field cannot hide a line in   or a form feed.
_BREAK = re.compile("\r\n|[\n\r\x0b\x0c\x1c\x1d\x1e\x85  ]")
# A link line is ONE token: printable ASCII, no space. Thai prose has no spaces between words, so a
# looser token rule would let a long Thai sentence pass as a "path".
_URL = re.compile(r"https?://[!-~]+\Z")
_REPO_PATH = re.compile(r"[A-Za-z0-9._~@+:#=-]*/[A-Za-z0-9._~@+:#=/-]*\Z")


class TooLong(ValueError):
    """More text than the CEO reads."""


def is_link_line(line: str) -> bool:
    token = line.strip()
    return bool(token) and bool(_URL.match(token) or _REPO_PATH.match(token))


def _pairs(fields: Mapping[str, Any] | Iterable[Any]) -> list[tuple[str, str]]:
    items = fields.items() if isinstance(fields, Mapping) else fields
    out = []
    for i, item in enumerate(items):
        name, text = item if isinstance(item, tuple) else (f"text {i + 1}", item)
        if text is None or text == "":
            continue
        out.append((str(name), str(text)))
    return out


def ceo_lines(fields: Mapping[str, Any] | Iterable[Any]) -> list[tuple[str, str]]:
    """The lines he reads, as (field, line), in order. `fields` is {name: text}, or a list of
    (name, text) pairs or plain strings."""
    return [(name, line) for name, text in _pairs(fields) for line in _BREAK.split(text)]


def line_limit(line: str) -> int:
    return MAX_LINK_CHARS if is_link_line(line) else MAX_CHARS


def check_ceo_text(fields: Mapping[str, Any] | Iterable[Any]) -> None:
    """None when the text fits; TooLong naming what is over, otherwise. Never names the text."""
    lines = ceo_lines(fields)
    over = []
    if len(lines) > MAX_LINES:
        over.append(f"{len(lines)} lines")
    for name, line in lines:
        if len(line) > line_limit(line):
            over.append(f"a line of {len(line)} chars in {name}")
            break
    if over:
        raise TooLong(f"the CEO reads ≤{MAX_LINES} lines of ≤{MAX_CHARS} chars (got {' and '.join(over)}); "
                      "put the detail in a file and link it")
