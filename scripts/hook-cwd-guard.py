#!/usr/bin/env python3
"""PreToolUse hook (Bash) — a command must not leave the session's home dir.

ADR 0028 §6 (session cto-0e8d80b8, 2026-09-22): the Bash tool's cwd persists
between calls. Measured FIVE times in one CTO session that day: a
`cd X && ...` inside a compound command left the session in X, so every later
relative path, `python3 -m tools.*`, `scripts/*.sh` ran against the wrong
repo. Memory `feedback_cd_in_compound_bash_moves_the_session_cwd.md` already
said so and it still happened — a doc does not stop it, a hook does.

Simulates where the command would leave the shell: walks the top-level
segments (split on `;`, `&&`, `||`, `|`, newlines), ignoring anything inside
quotes, `$( ... )` / `( ... )` subshells (a subshell never changes the
caller's cwd) and heredoc bodies (data, not shell). A segment whose first
word is `cd` or `pushd` moves the simulated cwd; `popd` and `cd -` go to the
previous one; a variable in the path (`cd "$W"`) makes the result UNKNOWN.

Home = $CLAUDE_PROJECT_DIR (hooks get it) -> fallback: the event's `cwd`.
Simulated end == home -> allow (exit 0, silent). Anywhere else, or UNKNOWN
-> block (exit 2) with a fix.

Escape hatch, for genuine repair only: CWD_GUARD=off.
"""
from __future__ import annotations

import json
import os
import posixpath
import sys

KEYWORDS = {"do", "then", "else", "elif", "time"}
CD_WORDS = {"cd", "pushd"}


# --------------------------------------------------------------------------
# Tokenizer: split a command into top-level segments, respecting quotes,
# ( ... ) / $( ... ) depth, and heredoc bodies.
# --------------------------------------------------------------------------

def _split_top_level_segments(command: str) -> list[str]:
    segments: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(command)
    quote: str | None = None
    depth = 0
    pending_heredocs: list[tuple[str, bool]] = []  # (delimiter, strip_tabs)

    def _flush() -> None:
        segments.append("".join(buf))
        buf.clear()

    while i < n:
        c = command[i]

        if quote == "'":
            buf.append(c)
            if c == "'":
                quote = None
            i += 1
            continue
        if quote == '"':
            if c == "\\" and i + 1 < n:
                buf.append(c)
                buf.append(command[i + 1])
                i += 2
                continue
            buf.append(c)
            if c == '"':
                quote = None
            i += 1
            continue

        if c in ("'", '"'):
            quote = c
            buf.append(c)
            i += 1
            continue
        if c == "\\" and i + 1 < n and depth == 0:
            buf.append(c)
            buf.append(command[i + 1])
            i += 2
            continue
        if c == "(":
            depth += 1
            buf.append(c)
            i += 1
            continue
        if c == ")":
            depth = max(0, depth - 1)
            buf.append(c)
            i += 1
            continue
        if depth > 0:
            buf.append(c)
            i += 1
            continue

        # depth 0, outside quotes — heredoc operator?
        if c == "<" and i + 1 < n and command[i + 1] == "<":
            j = i + 2
            dash = False
            if j < n and command[j] == "-":
                dash = True
                j += 1
            while j < n and command[j] in " \t":
                j += 1
            delim = ""
            if j < n and command[j] in ("'", '"'):
                qch = command[j]
                j += 1
                start = j
                while j < n and command[j] != qch:
                    j += 1
                delim = command[start:j]
                if j < n:
                    j += 1
            else:
                start = j
                while j < n and command[j] not in " \t\n;&|()<>":
                    j += 1
                delim = command[start:j]
            if delim:
                pending_heredocs.append((delim, dash))
                buf.append(command[i:j])
                i = j
                continue

        if c == ";":
            _flush()
            i += 1
            continue
        if c == "\n":
            _flush()
            i += 1
            if pending_heredocs:
                for delim, dash in pending_heredocs:
                    while i <= n:
                        nl = command.find("\n", i)
                        line = command[i:nl] if nl != -1 else command[i:n]
                        i = nl + 1 if nl != -1 else n
                        check_line = line.lstrip("\t") if dash else line
                        if check_line == delim:
                            break
                        if nl == -1:
                            break
                pending_heredocs = []
            continue
        if c == "&" and i + 1 < n and command[i + 1] == "&":
            _flush()
            i += 2
            continue
        if c == "|" and i + 1 < n and command[i + 1] == "|":
            _flush()
            i += 2
            continue
        if c == "|":
            _flush()
            i += 1
            continue

        buf.append(c)
        i += 1

    _flush()
    return segments


# --------------------------------------------------------------------------
# cd / pushd / popd simulation
# --------------------------------------------------------------------------

def _strip_quotes(tok: str) -> str:
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
        return tok[1:-1]
    return tok


def _strip_leading_keywords(seg: str) -> str:
    seg = seg.strip()
    while True:
        parts = seg.split(None, 1)
        if len(parts) == 2 and parts[0] in KEYWORDS:
            seg = parts[1]
            continue
        return seg


class _State:
    __slots__ = ("current", "previous", "unknown_reason")

    def __init__(self, home: str) -> None:
        self.current = home
        self.previous = home
        self.unknown_reason: str | None = None


def _apply_cd(state: _State, raw_arg: str) -> None:
    arg = raw_arg.strip()
    tok = arg.split(None, 1)[0] if arg else ""
    old_current = state.current

    if not tok or tok == "~":
        shell_home = os.environ.get("HOME")
        state.previous = old_current
        if shell_home:
            state.current = shell_home
        else:
            state.current = "UNKNOWN"
            state.unknown_reason = "no $HOME set to resolve bare `cd`"
        return

    if "$" in tok:
        state.previous = old_current
        state.current = "UNKNOWN"
        state.unknown_reason = "a variable in the cd path"
        return

    if tok == "-":
        state.current = state.previous
        state.previous = old_current
        return

    stripped = _strip_quotes(tok)
    if "$" in stripped:
        state.previous = old_current
        state.current = "UNKNOWN"
        state.unknown_reason = "a variable in the cd path"
        return

    if stripped.startswith("~/"):
        shell_home = os.environ.get("HOME")
        state.previous = old_current
        if shell_home:
            state.current = posixpath.normpath(posixpath.join(shell_home, stripped[2:]))
        else:
            state.current = "UNKNOWN"
            state.unknown_reason = "no $HOME set to resolve `cd ~/...`"
        return

    state.previous = old_current
    if stripped.startswith("/"):
        state.current = posixpath.normpath(stripped)
    elif state.current == "UNKNOWN":
        state.current = "UNKNOWN"
    else:
        state.current = posixpath.normpath(posixpath.join(state.current, stripped))


def _apply_popd(state: _State) -> None:
    old_current = state.current
    state.current = state.previous
    state.previous = old_current


def simulate_final_cwd(command: str, home: str) -> tuple[str, str | None]:
    """Returns (final_cwd_or_'UNKNOWN', unknown_reason_or_None)."""
    state = _State(home)
    for raw_seg in _split_top_level_segments(command):
        seg = _strip_leading_keywords(raw_seg)
        parts = seg.split(None, 1)
        if not parts:
            continue
        first = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        if first in CD_WORDS:
            _apply_cd(state, rest)
        elif first == "popd":
            _apply_popd(state)
    return state.current, state.unknown_reason


# --------------------------------------------------------------------------
# hook entrypoint
# --------------------------------------------------------------------------

def main() -> int:
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    if os.environ.get("CWD_GUARD", "").strip().lower() == "off":
        return 0

    command = str((ev.get("tool_input") or {}).get("command") or "").strip()
    if not command:
        return 0

    home = os.environ.get("CLAUDE_PROJECT_DIR") or str(ev.get("cwd") or "")
    if not home:
        return 0
    home = posixpath.normpath(home)

    final, unknown_reason = simulate_final_cwd(command, home)
    if final == home:
        return 0

    where = f"an unresolved location ({unknown_reason})" if final == "UNKNOWN" else final
    sys.stderr.write(
        f"BLOCKED — this command would leave the session in {where} (home is {home}).\n"
        "Every later call in this session runs there, not in the repo you expect "
        "(measured 5x on 2026-09-22).\n"
        "Use `git -C <path> ...`, absolute paths, a subshell `(cd X && ...)`, "
        f"or end the command with `&& cd {home}`.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
