"""What a Claude Code pane's screen shows, read from a `tmux capture-pane -p [-e]` capture.

Pure predicates, stdlib only, no tmux call of their own: the caller captures the
screen and passes the text in. A capture made with `-e` carries the screen's colours
and attributes as escape sequences; every predicate here accepts one (and a plain
capture, which has none) and reads the ghost prompt suggestion in the input box as
EMPTY: Claude Code draws that suggestion dim (SGR 2) after the ❯, and only the
attributes tell it from a draft somebody typed (Contabo, 15 Oct 2026: four idle
sessions waited 20+ minutes on a suggestion). Moved here unchanged from tools/rename_service.py
(Agents-Core #272/#283, review round 4) so the org's wake (tools/agent_transport.py
`_wake_tmux_send`) asks the same questions the rename service does before it types
into a pane: is a choice prompt (permission / question) up, does the input box hold a
draft, is a turn running. tools/rename_service.py re-exports every name.
"""
from __future__ import annotations

import re

_PROMPT = "❯"

# --- colours and attributes (`capture-pane -e`) -----------------------------------------
# An SGR sequence (group 1 = its parameters), any other CSI sequence, an OSC string
# (tmux emits the app's hyperlinks: ESC ] 8 ; id=… ; url ST) and a two-character escape.
_ESC_RE = re.compile(
    r"\x1b\[([0-9;:]*)m|\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")


def _sgr_dim(params: str, dim: bool) -> bool:
    """The dim state after an SGR sequence: 0 (or no parameter) and 22 end it, 2 starts
    it. The arguments of a 38/48/58 colour (`38;5;246`, `38;2;r;g;b`) are skipped: that
    2 is a colour selector, not "dim". A group with a ":" (`4:3`, `38:2::r:g:b`) is one
    self-contained setting and changes nothing here."""
    groups = params.split(";")
    i = 0
    while i < len(groups):
        g = groups[i] or "0"
        i += 1
        if not g.isdigit():
            continue
        n = int(g)
        if n in (0, 22):
            dim = False
        elif n == 2:
            dim = True
        elif n in (38, 48, 58):
            kind = groups[i] if i < len(groups) else ""
            i += 2 if kind == "5" else 4 if kind == "2" else 0
    return dim


def strip_ansi(screen: str) -> str:
    """The capture with every escape sequence removed: the text a plain capture shows."""
    return _ESC_RE.sub("", screen) if "\x1b" in screen else screen


def drop_ghost(screen: str) -> str:
    """The capture with escapes removed AND every dim character dropped, except the ❯
    pointer, box-drawing characters and line ends: the input box without Claude Code's
    ghost prompt suggestion (SGR 2). Dim state is per line (tmux ends every row with a
    reset and re-sets the attributes on the next), so a stray sequence cannot carry over.
    A capture with no escape sequence comes back unchanged."""
    if "\x1b" not in screen:
        return screen
    out = []
    for line in screen.split("\n"):
        dim, pos, kept = False, 0, []
        for m in _ESC_RE.finditer(line):
            kept.append(line[pos:m.start()] if not dim else _undimmed_keep(line[pos:m.start()]))
            if m.group(1) is not None:
                dim = _sgr_dim(m.group(1), dim)
            pos = m.end()
        kept.append(line[pos:] if not dim else _undimmed_keep(line[pos:]))
        out.append("".join(kept))
    return "\n".join(out)


def _undimmed_keep(text: str) -> str:
    """What survives inside a dim span: the ❯ pointer and box-drawing characters."""
    return "".join(c for c in text if c == _PROMPT or c in _BOX_CHARS)


# A numbered choice with the cursor on it (maybe inside a │ box), plus a choice footer:
# a permission prompt or an on-screen question, the app's ✋ "waiting for you".
_CHOICE_RE = re.compile(r"^[\s\u2502\u2503|]*\u276f\s*\d+\.\s")
_CHOICE_HINTS = ("Do you want", "Esc to cancel", "to navigate", "Enter to select", "Would you like")


def pane_waiting(text: str) -> bool:
    """True when a pane's screen holds a choice prompt waiting on a person."""
    tail = strip_ansi(text).splitlines()[-30:]
    return any(_CHOICE_RE.match(l) for l in tail) and any(h in l for l in tail for h in _CHOICE_HINTS)


def prompt_line(screen: str) -> str | None:
    """The text on the last ❯ line, or None when there is none."""
    lines = [l for l in drop_ghost(screen).splitlines() if _PROMPT in l]
    if not lines:
        return None
    return lines[-1].split(_PROMPT, 1)[1].replace("\xa0", " ").strip().strip("".join(_BOX_CHARS)).strip()


# Box-drawing (─ │ ╭ ╮ …) and block characters a TUI draws around its input box.
_BOX_CHARS = {chr(c) for c in range(0x2500, 0x25A0)}


def _box_rows(screen: str) -> list[str] | None:
    """The input box's rows: the text after the last ❯ plus the rows it wrapped onto,
    up to the box's bottom rule, box characters removed. None with no ❯ line."""
    lines = drop_ghost(screen).splitlines()
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
    return bool(_BUSY_RE.search(strip_ansi(screen)))


def not_ready_reason(screen: str) -> str | None:
    """None when a prompt is ready; else the first thing in the way, in the words the
    rename service logs: a choice prompt is up, a turn is running (Claude Code greys the
    ❯ and shows "esc to interrupt" then), or the box holds a draft / no input box shows."""
    if pane_waiting(screen):
        return "choice prompt up"
    if pane_busy(screen):
        return "turn running"
    if not box_empty(screen):
        return "prompt not empty"
    return None


def prompt_ready(screen: str) -> bool:
    """The whole input box is empty (a dim ghost suggestion counts as empty), no turn is
    running and no choice prompt (permission / question) is up."""
    return not_ready_reason(screen) is None

