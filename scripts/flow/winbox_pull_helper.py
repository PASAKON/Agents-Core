"""Remote-side helper for scripts/flow/winbox_pull.sh — runs ON winbox.

Stdlib only (no repo deps: this is scp'd over and run standalone with
whatever `python`/`py -3` winbox has). Walks the given directory and prints
one line per file: "<relpath>\t<size_bytes>\t<sha256hex>", relpath always
using "/" separators so the Mac side can join it onto a POSIX dest path.

    python winbox_pull_helper.py <dir>
"""
import hashlib
import os
import sys


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv):
    if len(argv) != 2:
        print("usage: winbox_pull_helper.py <dir>", file=sys.stderr)
        return 2
    root = argv[1]
    if not os.path.isdir(root):
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 1
    rows = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            size = os.path.getsize(path)
            rows.append((rel, size, sha256_of(path)))
    for rel, size, sha in sorted(rows):
        print(f"{rel}\t{size}\t{sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
