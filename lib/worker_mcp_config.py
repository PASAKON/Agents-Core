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
  * the org server is routed through `scripts/hub/with-org-db-env.sh` when the
    hub is live on this host (`org_db: hub` in node.yaml) and its env file
    exists (`cxo.wrap_org_entry`, the same rule the C-level generator applies;
    the env file is never read, only its existence tested). A template whose
    org command already is the wrapper (a checkout where the old
    `scripts/hub/cutover_flip.py` rewrote it) is left alone;
  * everything else — the org server's args/env — is passed through untouched.
    ORG_DB_URL never enters `env`; the wrapper sources it at spawn time.
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
    if "org" in servers:
        servers["org"] = cxo.wrap_org_entry(servers["org"], root)
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


# --------------------------------------------------------------------------
# The worker process itself (worker_init / worker_resume), not its MCP server
# --------------------------------------------------------------------------

# Names, never values, of the variables the worker launcher had before it went
# through the wrapper. Set by reexec_with_org_db_url, read by
# env_without_org_db; its presence is also the "already re-exec'd" guard.
PRE_WRAP_NAMES = "MOONIEX_PRE_ORG_DB_ENV"


def reexec_with_org_db_url(module: str, args: list[str], root: str | Path = ROOT) -> None:
    """Restart `python -m <module> <args>` through scripts/hub/with-org-db-env.sh
    when this host is on the hub and ORG_DB_URL is not in the environment.

    A worker runs in a tmux pane, and tmux hands a pane the tmux SERVER's
    environment, not the caller's. On a cut-over host that server predates the
    cutover, so worker_init reached lib.db without ORG_DB_URL and died on the
    archived state/tasks.db (task-1b8ef857, 2026-10-02). The gate is
    cxo.org_db_wrapper, the rule that already wraps the worker's org MCP
    server, so the worker process and its MCP server land on the same ledger.

    Returns without doing anything when the URL is already set, when this
    process already went through the wrapper once (a wrapper that could not
    supply the URL leaves lib.db to fail loudly instead of looping), or when
    the host is not on the hub. Otherwise it does not return."""
    if (os.environ.get("ORG_DB_URL") or "").strip() or PRE_WRAP_NAMES in os.environ:
        return
    wrapper = _load_cxo().org_db_wrapper(str(root))
    if wrapper is None:
        return
    names = ",".join(sorted(os.environ))
    os.environ[PRE_WRAP_NAMES] = names
    os.execvp("bash", ["bash", wrapper, sys.executable, "-m", module, *args])


def env_without_org_db(env: dict[str, str]) -> dict[str, str]:
    """`env` as the worker's claude process gets it: without ORG_DB_URL and
    without anything else the wrapper added (whatever the env file or the
    Infisical project carries). The worker's org MCP server starts through the
    wrapper on its own, and the model's shell has no use for the hub's
    password. Hooks that
    read the task DB run under the system python3 and stay fail-open, as they
    were for a session that predated the cutover."""
    names = env.get(PRE_WRAP_NAMES)
    if names is not None:
        keep = set(filter(None, names.split(",")))
        env = {k: v for k, v in env.items() if k in keep}
    env.pop("ORG_DB_URL", None)
    env.pop(PRE_WRAP_NAMES, None)
    return env
