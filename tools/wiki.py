"""Wiki tools. Read = all roles. Write = C-level only. Auto-commits on write."""
from __future__ import annotations

import subprocess
from pathlib import Path

from lib.config import is_c_level

WIKI_ROOT = Path("/Users/gob/Projects/LLMs").resolve()


class WikiError(Exception):
    pass


def _safe_path(rel: str) -> Path:
    rel = rel.lstrip("/")
    full = (WIKI_ROOT / rel).resolve()
    if not str(full).startswith(str(WIKI_ROOT)):
        raise WikiError(f"path outside wiki: {rel}")
    return full


def wiki_read(path: str) -> str:
    """Read a wiki page. All roles allowed."""
    full = _safe_path(path)
    if not full.exists():
        raise WikiError(f"wiki page not found: {path}")
    if full.is_dir():
        return "\n".join(sorted(p.name for p in full.iterdir()))
    return full.read_text(encoding="utf-8")


def wiki_list(prefix: str = "") -> list[str]:
    base = _safe_path(prefix) if prefix else WIKI_ROOT
    out = []
    for p in base.rglob("*.md"):
        out.append(str(p.relative_to(WIKI_ROOT)))
    return sorted(out)


def wiki_write(path: str, content: str, *, role: str, message: str | None = None) -> str:
    """Write a wiki page. C-level only. Auto-commits."""
    if not is_c_level(role):
        raise PermissionError(f"role '{role}' cannot write wiki. C-level only.")
    full = _safe_path(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")

    msg = message or f"[{role}] update {path}"
    _git(["add", str(full)])
    rc, out = _git(["commit", "-m", msg], allow_empty=True)
    return f"wrote {path} ({rc}: {out.strip()[:80]})"


def wiki_search(query: str, limit: int = 20) -> list[dict]:
    """Grep wiki for matches."""
    try:
        result = subprocess.run(
            ["grep", "-rn", "-i", "--include=*.md", query, str(WIKI_ROOT)],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    hits = []
    for line in result.stdout.splitlines()[:limit]:
        parts = line.split(":", 2)
        if len(parts) == 3:
            path, lineno, text = parts
            hits.append({
                "path": str(Path(path).relative_to(WIKI_ROOT)),
                "line": int(lineno),
                "text": text.strip(),
            })
    return hits


def _git(args: list[str], allow_empty: bool = False) -> tuple[int, str]:
    cmd = ["git", "-C", str(WIKI_ROOT)] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 and not allow_empty:
        raise WikiError(f"git failed: {' '.join(cmd)}\n{r.stderr}")
    return r.returncode, r.stdout + r.stderr
