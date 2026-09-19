#!/usr/bin/env python3
"""Gate 8 of cto-merge-checklist, as a check instead of a glance.

    python3 tools/check_replay_script.py <path> [<path> ...]

A "replay script" is accepted only if it is a file that compiles as code:
.py via py_compile, .js/.mjs via `node --check`, .sh via `bash -n`. Anything
else — a .md, a .txt, a .js that is 128 lines of comments and no statements —
is refused, because that is exactly what was merged as a "script" on
2026-08-12 (task-cda4f469) and again on 2026-09-19 (cc16c251). Exit 0 = every
path is a real script; exit 1 = at least one is not, with the reason.
"""
import py_compile
import re
import subprocess
import sys
from pathlib import Path

COMMENT_ONLY = re.compile(r"^\s*(//.*|/\*.*|\*.*|\*/|#.*)?\s*$")


def has_code(p: Path) -> bool:
    return any(not COMMENT_ONLY.match(line) for line in p.read_text(encoding="utf-8", errors="ignore").splitlines())


def check(p: Path) -> str | None:
    if not p.exists():
        return "does not exist"
    if p.suffix == ".py":
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            return f"py_compile: {e.msg.splitlines()[0]}"
    elif p.suffix in (".js", ".mjs", ".cjs"):
        r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
        if r.returncode:
            return "node --check: " + (r.stderr.strip().splitlines() or ["?"])[0]
    elif p.suffix == ".sh":
        r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
        if r.returncode:
            return "bash -n: " + (r.stderr.strip().splitlines() or ["?"])[0]
    else:
        return f"{p.suffix or 'no extension'} is not a script type (md/txt/notes are prose, not a replay script)"
    if not has_code(p):
        return "compiles, but contains no statements — comments only. Prose is not a script."
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    bad = 0
    for a in sys.argv[1:]:
        why = check(Path(a))
        print(f"{'FAIL' if why else 'ok  '} {a}" + (f" — {why}" if why else ""))
        bad += bool(why)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
