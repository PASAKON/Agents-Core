"""Wiki tools. Read = all roles. Write = C-level only. Auto-commits on write.

Multi-root support (ADR 0013 — wiki scope boundary). The wiki is split
across namespaces, each backed by its own git repo, declared in
config/wikis.yaml:

    default: mooniex          # namespace used when a path carries no prefix
    wikis:
      - ns: org
        path: /abs/path/to/Agents-Wikis
      - ns: mooniex
        path: /abs/path/to/MoonieX-Wikis

Path addressing:
  - "org:playbooks/x.md"  -> resolves under the `org` root.
  - "IRON-RULES.md"       -> no recognized "ns:" prefix, resolves against
                             the DEFAULT namespace. Every pre-multiroot
                             caller passes paths this way and keeps working
                             unchanged.
  - A prefix before the first ":" only counts as a namespace if it matches
    a registered `ns`; anything else is treated as a literal unprefixed
    path against the default namespace.

Root-path precedence, per namespace (highest wins):
  1. WIKI_ROOT_<NS>  e.g. WIKI_ROOT_ORG. Any namespace. config/wikis.yaml
                     carries Mac absolute paths, so this is how a non-Mac box
                     (Contabo) points a root at its own checkout.
  2. WIKI_ROOT       legacy var, DEFAULT namespace only — kept so existing
                     deploys and the systemd unit keep working unchanged.
  3. config/wikis.yaml `path:` entry for that ns

Missing roots (Contabo has none by design; `Agents-Wikis` doesn't exist
until Phase 2 of the split) are not fatal by themselves:
  - wiki_list() / wiki_search() silently skip a missing root. If EVERY
    registered root is missing, they raise the same generic WikiError the
    single-root version always raised ("wiki not available in this
    environment") rather than returning an empty result.
  - wiki_read() / wiki_write() against a missing root raise WikiError
    naming the namespace, e.g. "wiki 'org' not available in this
    environment".
"""
from __future__ import annotations

import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import yaml

from lib.config import is_c_level

ROOT = Path(__file__).resolve().parent.parent
WIKIS_CONFIG = ROOT / "config" / "wikis.yaml"


class WikiError(Exception):
    pass


@lru_cache(maxsize=1)
def _registry() -> dict:
    return yaml.safe_load(WIKIS_CONFIG.read_text(encoding="utf-8"))


def _default_ns() -> str:
    return _registry()["default"]


def _env_root_var(ns: str) -> str:
    """Per-namespace override var name: `org` -> WIKI_ROOT_ORG."""
    return "WIKI_ROOT_" + re.sub(r"[^A-Za-z0-9]", "_", ns).upper()


@lru_cache(maxsize=1)
def _roots() -> dict[str, Path]:
    """ns -> resolved root Path.

    Precedence per namespace (highest first):
      1. WIKI_ROOT_<NS>   e.g. WIKI_ROOT_ORG. Works for ANY namespace, which is
                          what lets a non-Mac box (Contabo) point a root at its
                          own checkout path — config/wikis.yaml carries Mac
                          absolute paths.
      2. WIKI_ROOT        legacy var, DEFAULT namespace only. Kept so existing
                          deploys and the systemd unit keep working unchanged.
      3. config/wikis.yaml `path:`
    """
    reg = _registry()
    default_ns = reg["default"]
    legacy = os.environ.get("WIKI_ROOT")
    out: dict[str, Path] = {}
    for w in reg["wikis"]:
        ns = w["ns"]
        per_ns = os.environ.get(_env_root_var(ns))
        if per_ns:
            out[ns] = Path(per_ns).resolve()
        elif ns == default_ns and legacy:
            out[ns] = Path(legacy).resolve()
        else:
            out[ns] = Path(w["path"]).resolve()
    return out


def _split_ns(path: str) -> tuple[str, str]:
    """Split "ns:relpath" into (ns, relpath); unprefixed -> (default_ns, path)."""
    ns_prefix, sep, rest = path.partition(":")
    if sep and ns_prefix in _roots():
        return ns_prefix, rest
    return _default_ns(), path


def _root_for(ns: str) -> Path:
    roots = _roots()
    if ns not in roots:
        raise WikiError(f"unknown wiki namespace: {ns}")
    return roots[ns]


def _require_root(ns: str) -> Path:
    root = _root_for(ns)
    if not root.exists():
        raise WikiError(f"wiki '{ns}' not available in this environment")
    return root


def _available_roots() -> list[tuple[str, Path]]:
    """(ns, root) pairs for roots that currently exist on disk."""
    return [(ns, root) for ns, root in _roots().items() if root.exists()]


def _safe_path(root: Path, rel: str) -> Path:
    rel = rel.lstrip("/")
    full = (root / rel).resolve()
    if full != root and root not in full.parents:
        raise WikiError(f"path outside wiki: {rel}")
    return full


def wiki_read(path: str) -> str:
    """Read a wiki page. Namespaced ("org:x.md") or unprefixed (default ns).
    All roles allowed."""
    ns, rel = _split_ns(path)
    root = _require_root(ns)
    full = _safe_path(root, rel)
    if not full.exists():
        raise WikiError(f"wiki page not found: {path}")
    if full.is_dir():
        return "\n".join(sorted(p.name for p in full.iterdir()))
    return full.read_text(encoding="utf-8")


def wiki_list(prefix: str = "") -> list[str]:
    """List wiki pages, each entry "ns:relpath".

    No prefix -> every available root (missing roots skipped; WikiError if
    ALL roots are missing). "ns" or "ns:subpath" -> that root only. Any
    other non-empty prefix -> scoped within the default namespace, mirroring
    wiki_read's unprefixed fallback.
    """
    if not prefix:
        available = _available_roots()
        if not available:
            raise WikiError("wiki not available in this environment")
        out = []
        for ns, root in available:
            out.extend(f"{ns}:{p.relative_to(root)}" for p in root.rglob("*.md"))
        return sorted(out)

    # A bare namespace ("org") carries no ":", so _split_ns would fall through
    # to the default ns and quietly look for a directory named "org" inside it
    # — returning [] instead of that root's pages. Match it explicitly first.
    if prefix in _roots():
        ns, rel = prefix, ""
    else:
        ns, rel = _split_ns(prefix)
    root = _require_root(ns)
    base = _safe_path(root, rel) if rel else root
    return sorted(f"{ns}:{p.relative_to(root)}" for p in base.rglob("*.md"))


def wiki_write(path: str, content: str, *, role: str, message: str | None = None) -> str:
    """Write a wiki page. C-level only. Auto-commits into the resolved
    root's own git repo."""
    if not is_c_level(role):
        raise PermissionError(f"role '{role}' cannot write wiki. C-level only.")
    ns, rel = _split_ns(path)
    root = _require_root(ns)
    full = _safe_path(root, rel)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")

    msg = message or f"[{role}] update {path}"
    _git(root, ["add", str(full)])
    rc, out = _git(root, ["commit", "-m", msg], allow_empty=True)
    return f"wrote {path} ({rc}: {out.strip()[:80]})"


def wiki_search(query: str, limit: int = 20) -> list[dict]:
    """Grep every available wiki root for matches. Each hit's `path` is
    "ns:relpath" so it round-trips straight back into wiki_read(). Raises
    WikiError if ALL roots are missing, matching the single-root behavior."""
    available = _available_roots()
    if not available:
        raise WikiError("wiki not available in this environment")
    hits: list[dict] = []
    for ns, root in available:
        if len(hits) >= limit:
            break
        try:
            result = subprocess.run(
                ["grep", "-rn", "-i", "--include=*.md", query, str(root)],
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        for line in result.stdout.splitlines():
            if len(hits) >= limit:
                break
            parts = line.split(":", 2)
            if len(parts) == 3:
                p, lineno, text = parts
                hits.append({
                    "path": f"{ns}:{Path(p).relative_to(root)}",
                    "line": int(lineno),
                    "text": text.strip(),
                })
    return hits


def _git(root: Path, args: list[str], allow_empty: bool = False) -> tuple[int, str]:
    cmd = ["git", "-C", str(root)] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 and not allow_empty:
        raise WikiError(f"git failed: {' '.join(cmd)}\n{r.stderr}")
    return r.returncode, r.stdout + r.stderr
