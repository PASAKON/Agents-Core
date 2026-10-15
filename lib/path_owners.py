"""Who owns a path in Agents-Core (config/path-owners.yaml).

CEO 2026-10-14: each Project Head merges its own project's paths, and CTO Main steps in only on a
conflict. A PH needs to know, before it merges, whether the PR touches a path another PH owns.

    owners_for(paths)            -> {path: project name | "shared" | None}
    foreign_paths(project, paths) -> [(path, owner)]    # only paths ANOTHER project owns

The table is a list of fnmatch globs per project plus the reserved key `shared`. `*` crosses `/`, so
`dir/**` and `dir/*` both cover everything under `dir`. The longest matching glob wins; two equal-length
globs that both match go to the one listed first in the file. A path that matches no glob is None
(unowned). `shared` paths are never "foreign": they belong to no PH, so a PR touching one is reported
separately (tools/pr_owner_check.py) and the PH tells CTO Main.

The file is read on every call: it is a few dozen lines, and the org MCP server is long-lived, so a
cached copy would go stale after a live sync.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parent.parent
OWNERS_CONFIG = ROOT / "config" / "path-owners.yaml"
SHARED = "shared"

Table = list[tuple[str, str]]   # (glob, owner) in file order; owner is a project name or SHARED


def _norm(path: str) -> str:
    """Repo-relative, forward slashes, no leading ./ or /."""
    p = str(path).strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def load_table(path: Path | str | None = None) -> Table:
    """Read the owners file into [(glob, owner)]. Raises ValueError on a malformed file and
    OSError / yaml.YAMLError when it cannot be read: callers decide whether to fail open."""
    src = Path(path) if path else OWNERS_CONFIG
    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{src}: top level must be a mapping of project name -> list of globs")
    table: Table = []
    for owner, globs in data.items():
        if not isinstance(owner, str) or not isinstance(globs, list) \
                or not all(isinstance(g, str) and g.strip() for g in globs):
            raise ValueError(f"{src}: {owner!r} must map to a list of non-empty glob strings")
        table.extend((_norm(g), owner) for g in globs)
    return table


def projects(table: Table | None = None) -> list[str]:
    """Project names that own at least one glob (not `shared`), in file order."""
    seen: list[str] = []
    for _, owner in (load_table() if table is None else table):
        if owner != SHARED and owner not in seen:
            seen.append(owner)
    return seen


def _owner_of(norm_path: str, table: Table) -> str | None:
    best_len, best_owner = -1, None
    for glob, owner in table:
        if len(glob) > best_len and fnmatch.fnmatchcase(norm_path, glob):
            best_len, best_owner = len(glob), owner
    return best_owner


def owners_for(paths: Iterable[str], table: Table | None = None) -> dict[str, str | None]:
    """{path: owner} for every path given, keyed by the string as given.
    owner is a project name, "shared", or None when no glob matches."""
    tbl = load_table() if table is None else table
    return {p: _owner_of(_norm(p), tbl) for p in paths}


def foreign_paths(project: str, paths: Iterable[str],
                  table: Table | None = None) -> list[tuple[str, str]]:
    """[(path, owner)] for the paths another project owns, in the order given, each path once.
    Shared and unowned paths are not foreign; neither are the project's own (compared ignoring case).
    A project that owns nothing in the table sees every owned path as foreign."""
    me = (project or "").strip().casefold()
    out: list[tuple[str, str]] = []
    for path, owner in owners_for(paths, table).items():
        if owner not in (None, SHARED) and owner.casefold() != me:
            out.append((path, owner))
    return out
