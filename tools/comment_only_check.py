"""Verify that a diff changes only comments and docstrings, never code or runtime strings."""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import tokenize
from pathlib import Path

PY_EXTS = {".py"}
CLIKE_EXTS = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go"}
YAML_EXTS = {".yaml", ".yml"}
SHELL_EXTS = {".sh", ".bash", ".toml"}
HASH_EXTS = YAML_EXTS | SHELL_EXTS

_CODE_TOKEN_RE = re.compile(r"[$_\w]+|[^\s$_\w]")
_SH_WORD_BREAK = " \t\n;|&()<>"

_PY_SKIP = frozenset({
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.ENCODING,
})


def _tokens_python(text: str) -> list[tuple[int, str]] | None:
    try:
        raw = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    sig = [t for t in raw if t.type not in _PY_SKIP]
    out: list[tuple[int, str]] = []
    expect_doc = True
    in_header = False
    paren_depth = 0
    i = 0
    n = len(sig)
    while i < n:
        t = sig[i]
        if expect_doc:
            if t.type in (tokenize.NEWLINE, tokenize.INDENT):
                out.append((t.type, "" if t.type == tokenize.NEWLINE else t.string))
                i += 1
                continue
            if t.type == tokenize.STRING and not t.string.lstrip("rRfFuU").startswith(("b", "B")):
                j = i
                while j < n and sig[j].type == tokenize.STRING:
                    j += 1
                nxt_type = sig[j].type if j < n else tokenize.ENDMARKER
                nxt_str = sig[j].string if j < n else ""
                at_line_start = i == 0 or sig[i - 1].type in (tokenize.NEWLINE, tokenize.INDENT)
                if nxt_type == tokenize.NEWLINE:
                    expect_doc = False
                    i = j + 1 if at_line_start else j
                    continue
                if nxt_type == tokenize.OP and nxt_str == ";":
                    j += 1
                    if at_line_start and j < n and sig[j].type == tokenize.NEWLINE:
                        j += 1
                    expect_doc = False
                    i = j
                    continue
                if nxt_type in (tokenize.DEDENT, tokenize.ENDMARKER):
                    expect_doc = False
                    i = j
                    continue
            expect_doc = False

        if t.type == tokenize.NAME and t.string in ("def", "class") and paren_depth == 0:
            in_header = True
        elif t.type == tokenize.OP:
            if t.string in "([{":
                paren_depth += 1
            elif t.string in ")]}" and paren_depth > 0:
                paren_depth -= 1
            elif t.string == ":" and in_header and paren_depth == 0:
                in_header = False
                expect_doc = True

        if t.type != tokenize.ENDMARKER:
            out.append((t.type, "" if t.type in (tokenize.NEWLINE, tokenize.DEDENT) else t.string))
        i += 1
    return out


def _tokens_clike(text: str, ext: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        two = text[i : i + 2]
        if two == "//":
            j = text.find("\n", i + 2)
            i = n if j < 0 else j
        elif two == "/*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c in "'\"`":
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == "\\" and (c != "`" or ext != ".go") and j + 1 < n:
                    j += 2
                    continue
                if c != "`" and text[j] == "\n":
                    break
                j += 1
            end = min(j + 1, n)
            out.append(("STR", text[i:end]))
            i = end
        else:
            j = i
            while j < n and text[j] not in "'\"`/":
                j += 1
            if j == i:
                j = i + 1
            for tok in _CODE_TOKEN_RE.findall(text[i:j]):
                out.append(("CODE", tok))
            i = j
    return out


def _tokens_yaml(text: str) -> list[tuple[str, list[tuple[str, str]]]]:
    out: list[tuple[str, list[tuple[str, str]]]] = []
    for line_idx, line in enumerate(text.splitlines()):
        if line_idx == 0 and line.startswith("#!"):
            out.append(("", [("SHEBANG", line.strip())]))
            continue
        stripped = line.lstrip(" \t")
        indent = line[: len(line) - len(stripped)]
        line_toks: list[tuple[str, str]] = []
        i, n = 0, len(stripped)
        while i < n:
            c = stripped[i]
            if c in "'\"":
                j = i + 1
                while j < n:
                    if c == '"' and stripped[j] == "\\" and j + 1 < n:
                        j += 2
                        continue
                    if c == "'" and stripped[j : j + 2] == "''":
                        j += 2
                        continue
                    if stripped[j] == c:
                        break
                    j += 1
                end = min(j + 1, n)
                line_toks.append(("STR", stripped[i:end]))
                i = end
            elif c == "\\" and i + 1 < n:
                line_toks.append(("CODE", stripped[i : i + 2]))
                i += 2
            elif c == "#" and (i == 0 or stripped[i - 1] in " \t"):
                # YAML: `#` opens a comment only at line start or after whitespace; `a: x#1` is a value.
                break
            else:
                j = i
                while j < n and stripped[j] not in "'\"\\#":
                    j += 1
                if j == i:
                    j = i + 1
                for tok in _CODE_TOKEN_RE.findall(stripped[i:j]):
                    line_toks.append(("CODE", tok))
                i = j
        if line_toks:
            out.append((indent, line_toks))
    return out


def _tokens_hash(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    i, n = 0, len(text)
    if text.startswith("#!"):
        j = text.find("\n")
        end = n if j < 0 else j
        out.append(("SHEBANG", text[:end].strip()))
        out.append(("EOL", "\n"))
        i = end + 1 if j >= 0 else n

    line_has_tok = False
    pending_ws = False

    def emit(kind: str, val: str) -> None:
        nonlocal line_has_tok, pending_ws
        if line_has_tok and pending_ws:
            out.append(("WS", " "))
        out.append((kind, val))
        line_has_tok = True
        pending_ws = False

    while i < n:
        c = text[i]
        three = text[i : i + 3]
        if c == "\n":
            if line_has_tok:
                out.append(("EOL", "\n"))
            line_has_tok = False
            pending_ws = False
            i += 1
        elif c in " \t\r":
            if c in " \t" and line_has_tok:
                pending_ws = True
            i += 1
        elif three in ('"""', "'''"):
            j = text.find(three, i + 3)
            end = n if j < 0 else j + 3
            emit("STR", text[i:end])
            i = end
        elif c in "'\"":
            j = i + 1
            while j < n and text[j] != c:
                if c == '"' and text[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if text[j] == "\n":
                    break
                j += 1
            end = min(j + 1, n)
            emit("STR", text[i:end])
            i = end
        elif c == "\\" and i + 1 < n:
            if text[i + 1] == "\n":
                i += 2
            else:
                emit("CODE", text[i : i + 2])
                i += 2
        elif c == "#" and (i == 0 or text[i - 1] in _SH_WORD_BREAK):
            # Shell: `#` opens a comment only where a word starts (`a#b`, `$#`, `${#x}` are code).
            j = text.find("\n", i + 1)
            i = n if j < 0 else j
        else:
            j = i
            while j < n and text[j] not in " \t\r\n'\"\\#":
                j += 1
            if j == i:
                j = i + 1
            for tok in _CODE_TOKEN_RE.findall(text[i:j]):
                emit("CODE", tok)
            i = j

    if line_has_tok:
        out.append(("EOL", "\n"))
    return out


def code_changed(old_text: str, new_text: str, path: str) -> bool:
    """Return True when anything other than comments or docstrings differs."""
    ext = Path(path).suffix.lower()
    if ext in PY_EXTS:
        old_toks = _tokens_python(old_text)
        new_toks = _tokens_python(new_text)
        if old_toks is None or new_toks is None:
            return old_text != new_text
        return old_toks != new_toks
    if ext in CLIKE_EXTS:
        return _tokens_clike(old_text, ext) != _tokens_clike(new_text, ext)
    if ext in YAML_EXTS:
        return _tokens_yaml(old_text) != _tokens_yaml(new_text)
    if ext in SHELL_EXTS:
        return _tokens_hash(old_text) != _tokens_hash(new_text)
    raise ValueError(f"Unsupported file extension for {path!r}: {ext or '<none>'}")


def _git_show(rev: str, path: str) -> str | None:
    res = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        return None
    return res.stdout


def _read_working(path: str) -> str | None:
    p = Path(path)
    try:
        if p.is_symlink() or not p.is_file():
            return None
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True, help="Base git revision")
    ap.add_argument("--head", default=None, help="Head git revision (working tree if omitted)")
    ap.add_argument("paths", nargs="*", help="Optional file paths to check")
    args = ap.parse_args(argv)

    diff_cmd = ["git", "diff", "--name-only", args.base]
    if args.head is not None:
        diff_cmd.append(args.head)
    if args.paths:
        diff_cmd.extend(["--", *args.paths])

    res = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)
    files = [line for line in res.stdout.splitlines() if line]
    if args.paths:
        norm = [p.rstrip("/") for p in args.paths]
        files = [f for f in files if any(f == p or f.startswith(p + "/") for p in norm)]

    all_ok = True
    for path in files:
        old_text = _git_show(args.base, path)
        new_text = _git_show(args.head, path) if args.head is not None else _read_working(path)
        if old_text is None or new_text is None:
            status = "CODE"
        else:
            try:
                status = "CODE" if code_changed(old_text, new_text, path) else "OK"
            except ValueError:
                status = "UNSUPPORTED"
        print(f"{status} {path}")
        if status != "OK":
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
