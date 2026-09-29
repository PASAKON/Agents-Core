"""Mark a directory as trusted in Claude Code's global config (GH #161).

A worker's `claude` starts inside a fresh worktree. When nothing has trusted
that path, claude stops at "Quick safety check: Is this a project you created
or one you trust?" with **No, exit** highlighted, and the kickoff/wake Enter
confirms it: the worker quits with no transcript. Trust on the parent repo
does not cover `worktrees/<...>` (measured 2026-09-23: Core trusted, 0 entries
under Core/worktrees), and a repo the HQ migration moved is not trusted at its
new path either.

The worktree is one this org just created for its own task, so the spawn path
records the trust itself before claude starts. The write inserts only the new
key's bytes, the same way scripts/hq_migrate_step4b.py does for Core, so every
other project's entry stays byte-identical.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

TRUST_KEY = "hasTrustDialogAccepted"


def claude_json_path() -> Path:
    """Where Claude Code keeps its global config: `$CLAUDE_CONFIG_DIR/.claude.json`
    when that is set, else `~/.claude.json`. `ORG_CLAUDE_JSON` overrides both;
    the test suite points it at a scratch path so no test edits the real one."""
    override = os.environ.get("ORG_CLAUDE_JSON")
    if override:
        return Path(override).expanduser()
    cfg_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if cfg_dir:
        return Path(cfg_dir).expanduser() / ".claude.json"
    return Path.home() / ".claude.json"


def _keys_for(path: str | Path) -> list[str]:
    """The path as given, plus its resolved form when a symlink makes them
    differ. claude keys a project by the cwd it sees, which is the literal
    path on one launcher and the resolved one on another."""
    literal = os.path.abspath(os.path.expanduser(str(path)))
    keys = [literal]
    try:
        real = os.path.realpath(literal)
    except OSError:
        real = literal
    if real != literal:
        keys.append(real)
    return keys


def _atomic_write(target: Path, text: str) -> None:
    """Write next to the real file, then rename over it. A symlinked
    ~/.claude.json keeps its link: the rename lands on the link's target."""
    real = Path(os.path.realpath(target))
    mode = real.stat().st_mode & 0o777 if real.exists() else 0o600
    fd, tmp = tempfile.mkstemp(prefix=".claude.json.", dir=str(real.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, real)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def trust_path(path: str | Path, *, claude_json: Path | None = None) -> str:
    """Record `path` as trusted. Returns "ok", "already", or "skipped:<why>".

    Never raises: a spawn must not fail because this best-effort write did
    not happen. The caller logs the result; the kickoff guard
    (`tools.tmux_session.shows_trust_dialog`) is the second line of defence.
    """
    cfg = claude_json or claude_json_path()
    try:
        if not cfg.exists():
            return f"skipped:{cfg} not found"
        text = cfg.read_text(encoding="utf-8")
        data = json.loads(text)
        projects = data.get("projects")
        if not isinstance(projects, dict):
            return 'skipped:no top-level "projects" object'

        missing = [k for k in _keys_for(path)
                   if not (projects.get(k) or {}).get(TRUST_KEY)]
        if not missing:
            return "already"

        new_text = text
        rewrite = False
        for key in missing:
            if key in projects:
                # An existing row that is not trusted: set the flag on it.
                # Rare (claude writes the row with the flag when a person
                # accepts), so a full re-serialize is acceptable here.
                rewrite = True
                continue
            marker = '"projects": {'
            idx = new_text.find(marker)
            if idx == -1:
                return 'skipped:no "projects": { marker to insert after'
            insert_at = idx + len(marker)
            sep = "" if new_text[insert_at:].lstrip().startswith("}") else ","
            insertion = f"\n    {json.dumps(key)}: {json.dumps({TRUST_KEY: True})}{sep}"
            new_text = new_text[:insert_at] + insertion + new_text[insert_at:]

        if rewrite:
            data = json.loads(new_text)
            for key in missing:
                row = data["projects"].setdefault(key, {})
                row[TRUST_KEY] = True
            new_text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

        reparsed = json.loads(new_text)  # must still parse
        if not all(reparsed["projects"][k].get(TRUST_KEY) for k in missing):
            return "skipped:trust flag did not round-trip"
        _atomic_write(cfg, new_text)
        return "ok"
    except Exception as e:  # best-effort by contract
        return f"skipped:{type(e).__name__}: {e}"
