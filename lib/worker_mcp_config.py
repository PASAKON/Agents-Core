"""Per-spawn worker MCP config (Org Mesh W0.3, task-6f6e5179).

`config/worker.mcp.json` is a git-tracked TEMPLATE written for the Mac: every
path in it is `/Users/gob/MoonieXHQ/...`. A worker on Contabo (or winbox later)
cannot use it as is. `write_for_worktree` renders the template against THIS
host and writes the result inside the worktree as an ignored file; the worker
launcher passes that path to `claude --mcp-config`.

What is rewritten, and what is deliberately not:
  * the Mac Agents root, in every string of the template, becomes this host's root;
  * the Mac venv interpreter becomes `_venv_python(root)` (bin/python or
    Scripts\\python.exe), reusing scripts/lib/cxo_mcp_config.py;
  * the LungNote index.js becomes the first candidate that exists on this box
    (`LUNGNOTE_MCP_JS`, then the Mac / Contabo / winbox locations); with no
    candidate the server is dropped and one line is logged;
  * everything else — the org server's command/args/env — is passed through
    untouched. `scripts/hub/cutover_flip.py` rewrites the org `command` to
    `scripts/hub/with-org-db-env.sh` and puts ORG_DB_URL into `env`; a
    generator that rebuilt those would undo the cutover.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "config" / "worker.mcp.json"
GENERATED_NAME = ".org-worker.mcp.json"

# What the tracked template was written against (the Mac).
TEMPLATE_ROOT = "/Users/gob/MoonieXHQ/Agents/Core"
TEMPLATE_PYTHON = f"{TEMPLATE_ROOT}/.venv/bin/python"
TEMPLATE_LUNGNOTE_JS = "/Users/gob/MoonieXHQ/Projects/LungNote/Mcp/index.js"


def _load_cxo():
    """scripts/lib/cxo_mcp_config.py is a launcher helper, not a package
    (scripts/lib has no __init__), so load it by path and reuse its logic
    instead of copying it."""
    src = ROOT / "scripts" / "lib" / "cxo_mcp_config.py"
    spec = importlib.util.spec_from_file_location("cxo_mcp_config", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _is_file(path: str) -> bool:
    return Path(path).is_file()


def _retarget(value, root: str):
    """Replace the Mac root in every string of a JSON value."""
    if isinstance(value, str):
        return value.replace(TEMPLATE_ROOT, root)
    if isinstance(value, list):
        return [_retarget(v, root) for v in value]
    if isinstance(value, dict):
        return {k: _retarget(v, root) for k, v in value.items()}
    return value


def generate(
    root: str | Path = ROOT,
    *,
    template: Path = TEMPLATE,
    venv_python: str | Path | None = None,
    lungnote_js: str | None = None,
    lungnote_node: str | None = None,
) -> dict:
    """Render the template for the host whose Agents checkout is `root`.

    The keyword arguments exist so a test can pin the host-dependent inputs;
    production passes none of them."""
    root = str(root)
    cxo = _load_cxo()
    python = str(venv_python) if venv_python is not None else str(cxo._venv_python(root))
    js = lungnote_js if lungnote_js is not None else cxo.LUNGNOTE_MCP_JS
    node = lungnote_node if lungnote_node is not None else cxo.LUNGNOTE_MCP_NODE

    cfg = _retarget(json.loads(Path(template).read_text(encoding="utf-8")), root)
    servers = cfg.get("mcpServers") or {}

    for name, srv in list(servers.items()):
        if srv.get("command") == _retarget(TEMPLATE_PYTHON, root):
            srv["command"] = python
        if name == "lungnote":
            if not _is_file(js):
                del servers[name]
                print(
                    f"worker_mcp_config: no LungNote MCP index.js on this host "
                    f"(tried {js}) — worker starts without the lungnote server",
                    file=sys.stderr,
                )
                continue
            srv["args"] = [js if a == TEMPLATE_LUNGNOTE_JS else a for a in srv.get("args", [])]
            if srv.get("command") == "node":
                srv["command"] = node
    return cfg


def write_for_worktree(worktree: str | Path, root: str | Path = ROOT) -> Path:
    """Write the rendered config into `worktree` (mode 600, git-excluded) and
    return its path, ready for `--mcp-config`."""
    # Lazy: tools.worktree imports lib.config, so a top-level import here would
    # make lib depend on tools at import time.
    from tools.worktree import _exclude_in_worktree

    worktree = Path(worktree)
    out = worktree / GENERATED_NAME
    payload = json.dumps(generate(root), indent=2) + "\n"
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(payload)
    os.chmod(out, 0o600)
    _exclude_in_worktree(worktree, (GENERATED_NAME,))
    return out
