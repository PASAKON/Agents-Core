"""What a Claude Code pane's screen shows, read from a `tmux capture-pane -p` capture.

Pure predicates, stdlib only, no tmux call of their own: the caller captures the
screen and passes the text in. Moved here unchanged from tools/rename_service.py
(Agents-Core #272/#283, review round 4) so the org's wake (tools/agent_transport.py
`_wake_tmux_send`) asks the same questions the rename service does before it types
into a pane: is a choice prompt (permission / question) up, does the input box hold a
draft, is a turn running. tools/rename_service.py re-exports every name.
"""
from __future__ import annotations

import re

_PROMPT = "❯"


# A numbered choice with the cursor on it (maybe inside a │ box), plus a choice footer:
# a permission prompt or an on-screen question, the app's ✋ "waiting for you".
_CHOICE_RE = re.compile(r"^[\s\u2502\u2503|]*\u276f\s*\d+\.\s")
_CHOICE_HINTS = ("Do you want", "Esc to cancel", "to navigate", "Enter to select", "Would you like")


def pane_waiting(text: str) -> bool:
    """True when a pane's screen holds a choice prompt waiting on a person."""
    tail = text.splitlines()[-30:]
    return any(_CHOICE_RE.match(l) for l in tail) and any(h in l for l in tail for h in _CHOICE_HINTS)


def prompt_line(screen: str) -> str | None:
    """The text on the last ❯ line, or None when there is none."""
    lines = [l for l in screen.splitlines() if _PROMPT in l]
    if not lines:
        return None
    return lines[-1].split(_PROMPT, 1)[1].replace("\xa0", " ").strip().strip("".join(_BOX_CHARS)).strip()


# Box-drawing (─ │ ╭ ╮ …) and block characters a TUI draws around its input box.
_BOX_CHARS = {chr(c) for c in range(0x2500, 0x25A0)}


def _box_rows(screen: str) -> list[str] | None:
    """The input box's rows: the text after the last ❯ plus the rows it wrapped onto,
    up to the box's bottom rule, box characters removed. None with no ❯ line."""
    lines = screen.splitlines()
    idx = [i for i, l in enumerate(lines) if _PROMPT in l]
    if not idx:
        return None
    rows = [lines[idx[-1]].split(_PROMPT, 1)[1]]
    for l in lines[idx[-1] + 1:]:
        if l.strip() and all(c in _BOX_CHARS or c.isspace() for c in l):
            break                                   # the rule under the input box
        rows.append(l)
    return ["".join(c for c in r if c not in _BOX_CHARS).strip() for r in rows]


def typed_text(screen: str) -> str | None:
    """What sits in the input box with every space and box character removed (a long
    name wraps at the pane width). None when there is no ❯ line."""
    rows = _box_rows(screen)
    return None if rows is None else _squash("".join(rows))


def _box_len(screen: str | None) -> int:
    """At least the number of characters in the input box: its rows plus one space
    per wrap, which a capture drops."""
    rows = _box_rows(screen) if screen is not None else None
    rows = [r for r in rows or [] if r]
    return sum(len(r) for r in rows) + len(rows)


def _squash(text: str) -> str:
    return "".join(c for c in text if not c.isspace() and c not in _BOX_CHARS)


# An empty box in a fresh session shows a dim hint (`Try "fix lint errors"`), which a
# plain capture cannot tell from typed text (seen on a real pane 14 Oct).
_PLACEHOLDER_RE = re.compile(r'Try"[^"]{1,80}"')
# A turn is running: the footer says so, or the spinner line "✽ Computing… (11s · …)".
_BUSY_RE = re.compile(r"esc to interrupt|…\s*\(\d+[sm]\b")


def box_empty(screen: str) -> bool:
    """The WHOLE input box is empty, not only its ❯ row: a draft can start with an
    empty first row (Shift+Enter) and hold text below it (review round 4, M-1)."""
    text = typed_text(screen)
    return text is not None and (text == "" or bool(_PLACEHOLDER_RE.fullmatch(text)))


def pane_busy(screen: str) -> bool:
    """A turn is running: Enter could land on a dialog that opens a moment later."""
    return bool(_BUSY_RE.search(screen))


def prompt_ready(screen: str) -> bool:
    """The whole input box is empty, no turn is running and no choice prompt
    (permission / question) is up."""
    return not pane_waiting(screen) and not pane_busy(screen) and box_empty(screen)

