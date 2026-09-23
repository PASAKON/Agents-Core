"""Config loader for projects.yaml and agents.yaml.

Project dict optional fields (beyond the required key/name/path/remote/default_branch):
  auto_deploy (dict | None):
    enabled (bool)           – must be True to trigger deploy; default False
    requires_ceo_ack (bool)  – if True, deploy is deferred (awaiting_ceo_ack); no command runs
    command (str)            – shell command executed via subprocess (shell=True)
    timeout_seconds (int)    – subprocess timeout; default 60
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROJECTS_CONFIG = ROOT / "config" / "projects.yaml"
AGENTS_CONFIG = ROOT / "policies" / "agents.yaml"
WIKIS_CONFIG = ROOT / "config" / "wikis.yaml"
HOSTS_CONFIG = ROOT / "config" / "hosts.yaml"


@lru_cache(maxsize=1)
def _wiki_registry() -> dict:
    return yaml.safe_load(WIKIS_CONFIG.read_text())


def _wiki_root_path(ns: str) -> str | None:
    for w in _wiki_registry().get("wikis", []):
        if w.get("ns") == ns:
            return w.get("path")
    return None


@lru_cache(maxsize=1)
def projects() -> dict[str, dict]:
    data = yaml.safe_load(PROJECTS_CONFIG.read_text())
    out = {p["key"]: p for p in data["projects"]}
    # The `LLMs` project's path is not duplicated in projects.yaml — it's
    # derived from config/wikis.yaml, the single source of truth for wiki
    # roots (ADR 0013).
    if "LLMs" in out and out["LLMs"].get("path") is None:
        out["LLMs"]["path"] = _wiki_root_path("mooniex")
    return out


@lru_cache(maxsize=1)
def agents() -> dict:
    return yaml.safe_load(AGENTS_CONFIG.read_text())


def role(name: str) -> dict:
    r = agents()["roles"].get(name)
    if not r:
        raise ValueError(f"unknown role: {name}")
    return r


def is_c_level(role_name: str) -> bool:
    return role_name in agents()["c_level"]


def live_c_level_roles() -> tuple[str, ...]:
    """C-level roles that can own a real agent session, in config order.

    `agents()["c_level"]` includes ``ceo`` because the CEO *is* C-level for
    authority purposes (`is_c_level` must keep saying yes). But the CEO is a
    human at a terminal, never a spawned session with a lock, a tmux pane, or
    a mailbox -- so anything that iterates *sessions* (broadcast delivery,
    GC, session listing) wants this list, not the raw config key. Iterating
    the raw key would try to deliver to a "ceo" session that cannot exist,
    and would create an empty `state/inbox/ceo-*` box as a side effect.

    Exists so the roster stops being copy-pasted. Three hardcoded tuples had
    already drifted: `tools/session_name.py` (deliberately wider -- it also
    carries the generic `cxo` prefix and is NOT a C-level roster), and
    `runners/relay_mcp_server.py` / `runners/mac_agent.py` (same members,
    different order). Adding a C-level should be one `policies/agents.yaml`
    edit, not a hunt for tuples (CEO 2026-08-14).
    """
    return tuple(r for r in agents()["c_level"] if r != "ceo")


# Host key (config/hosts.yaml) -> the machine label the CEO sees first in a
# worker's session name (ADDENDUM 1, CTO 2026-09-07): every session is now
# addressed from the Claude app, on any device, never from a terminal on a
# specific box — the machine has to be in the name itself. Falls back to
# the host key upper-cased for a host not listed here (hosts.yaml can grow
# without this map growing in lockstep).
_HOST_MACHINE_LABEL = {"mac": "MAC", "winbox": "WINDOWS", "contabo": "CONTABO"}


def worker_session_name(host_name: str, role_name: str, task_id: str,
                        title: str) -> str:
    """`<MACHINE> <ROLE> #<task-id-8> (<title, truncated ~40>)`.

    e.g. `WINDOWS Browser Operator #4a59a1a4 (SHOOT the teaser)`. Single
    source of truth for this shape — the Windows launcher (spawn-worker.ps1)
    receives the fully-rendered string from tools/delegate.py rather than
    recomputing the truncation/label logic itself, and a follow-up task can
    switch runners/worker_init.py's Mac-side `-n` to call this too.
    """
    machine = _HOST_MACHINE_LABEL.get(host_name, host_name.upper())
    short_id = task_id[len("task-"):] if task_id.startswith("task-") else task_id
    short_id = short_id[:8]
    display = display_for(role_name)
    trimmed = (title or "").strip()
    if len(trimmed) > 40:
        trimmed = trimmed[:40].rstrip() + "…"
    suffix = f" ({trimmed})" if trimmed else ""
    return f"{machine} {display} #{short_id}{suffix}"


def display_for(role_name: str) -> str:
    """Pretty role label used in tab titles, chat prefixes, and logs.

    Falls back to the raw role key if no display name is configured —
    keeps things working for ad-hoc roles in roles/ without a matching
    policies/agents.yaml entry.
    """
    try:
        r = role(role_name)
    except ValueError:
        return role_name
    return r.get("display") or role_name


def get_project(key: str) -> dict:
    p = projects().get(key)
    if not p:
        raise ValueError(f"unknown project: {key}. Known: {list(projects())}")
    return p


def _read_dotenv_var(name: str) -> str | None:
    """Read a single KEY=value from the gitignored repo-root .env.

    Tiny parser so we don't pull in python-dotenv just for one secret.
    Returns None if the file or key is absent.
    """
    env_file = ROOT / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == name:
            v = v.strip()
            # Strip a trailing inline comment (`value   # note`) — only
            # outside quotes, so quoted values may contain literal '#'.
            if v and v[0] not in "\"'":
                hash_idx = v.find(" #")
                if hash_idx != -1:
                    v = v[:hash_idx].strip()
            return v.strip('"').strip("'")
    return None



@lru_cache(maxsize=1)
def hosts() -> dict[str, dict]:
    """Host registry (config/hosts.yaml, ADR-shaped like projects/agents).

    Phase 1 (docs/design/multi-host-workers.md): declares what each host
    provides and how to reach it (ssh alias, native paths). Nothing here
    reads `provides` for routing yet — that's Phase 3.
    """
    data = yaml.safe_load(HOSTS_CONFIG.read_text())
    return data["hosts"]


def host(name: str) -> dict:
    h = hosts().get(name)
    if not h:
        raise ValueError(f"unknown host: {name}. Known: {list(hosts())}")
    return h


def project_path_for_host(project_key: str, host_name: str) -> str:
    """Repo-checkout path for `project_key` on `host_name`.

    `mac` falls back to the project's top-level `path:` (backward
    compatible with every project that predates the `paths:` map). Every
    other host reads `paths.<host_name>` only. A project with no path
    configured for a host is not routable there — raise a clear error
    rather than guessing or falling back to the Mac path, which would
    silently point a remote spawn at a directory that doesn't exist on
    that box.
    """
    proj = get_project(project_key)
    if host_name == "mac":
        p = (proj.get("paths") or {}).get("mac") or proj.get("path")
    else:
        p = (proj.get("paths") or {}).get(host_name)
    if not p:
        raise ValueError(
            f"project {project_key!r} has no path configured for host "
            f"{host_name!r} — not routable there. Add it under "
            f"paths.{host_name} in config/projects.yaml."
        )
    return p


def _read_dotenv_var(name: str) -> str | None:
    """Read a single KEY=value from the gitignored repo-root .env.

    Tiny parser so we don't pull in python-dotenv just for one secret.
    Returns None if the file or key is absent.
    """
    env_file = ROOT / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == name:
            v = v.strip()
            # Strip a trailing inline comment (`value   # note`) — only
            # outside quotes, so quoted values may contain literal '#'.
            if v and v[0] not in "\"'":
                hash_idx = v.find(" #")
                if hash_idx != -1:
                    v = v[:hash_idx].strip()
            return v.strip('"').strip("'")
    return None



