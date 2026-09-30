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
import platform
import re
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
    return yaml.safe_load(WIKIS_CONFIG.read_text(encoding="utf-8"))


def _wiki_root_path(ns: str) -> str | None:
    for w in _wiki_registry().get("wikis", []):
        if w.get("ns") == ns:
            return w.get("path")
    return None


@lru_cache(maxsize=1)
def projects() -> dict[str, dict]:
    data = yaml.safe_load(PROJECTS_CONFIG.read_text(encoding="utf-8"))
    out = {p["key"]: p for p in data["projects"]}
    # The `LLMs` project's path is not duplicated in projects.yaml — it's
    # derived from config/wikis.yaml, the single source of truth for wiki
    # roots (ADR 0013).
    if "LLMs" in out and out["LLMs"].get("path") is None:
        out["LLMs"]["path"] = _wiki_root_path("mooniex")
    return out


@lru_cache(maxsize=1)
def agents() -> dict:
    return yaml.safe_load(AGENTS_CONFIG.read_text(encoding="utf-8"))


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
    for line in env_file.read_text(encoding="utf-8").splitlines():
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

    A joined node (tools/hq_join) is in the hub's `hosts` table and in its
    own node.yaml, never in this repo's hosts.yaml: when node.yaml carries a
    well-formed host + os + hq_root for a name hosts.yaml does not declare,
    that entry is added here. hosts.yaml wins for every name it declares.
    A bad node.yaml adds nothing and never raises from here: self_host() is
    where it is reported. Cached per process, like hosts.yaml: a node.yaml
    written after the first call is seen by the next process.
    """
    data = yaml.safe_load(HOSTS_CONFIG.read_text(encoding="utf-8"))
    registry = data["hosts"]
    node = _node_yaml_entry()
    if node and node[0] not in registry:
        registry = {**registry, node[0]: node[1]}
    return registry


def host(name: str) -> dict:
    h = hosts().get(name)
    if not h:
        raise ValueError(f"unknown host: {name}. Known: {list(hosts())}")
    return h


# node.yaml is the C1 host-identity file (docs/design/org-mesh.md): a new
# machine writes its own host key here once, so a session on it never has to
# guess from a path or hostname. Absent = this source has nothing to say,
# not an error.
NODE_CONFIG_PATH = Path.home() / ".config" / "mooniex" / "node.yaml"

_PLATFORM_TO_OS = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}

# The one rule for a host name: tools/hq_join mints it, node.yaml carries it and
# `infisical_setup.py save` takes it as an identity name (NAME_RE there: 2-31
# chars). 3-31 chars, so every name hq_join accepts is a name `save` accepts.
HOST_NAME_RE = re.compile(r"[a-z][a-z0-9-]{1,29}[a-z0-9]")


def _load_node_yaml() -> dict | None:
    """node.yaml as a dict; None when the file is absent. Unparseable YAML, or a
    document that is not a mapping, raises."""
    if not NODE_CONFIG_PATH.exists():
        return None
    data = yaml.safe_load(NODE_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{NODE_CONFIG_PATH}: expected a mapping, got {type(data).__name__}")
    return data


def _node_hq_root(os_name: str, raw: object) -> str | None:
    """`raw` as tools/hq_join._check_hq_root accepts it (absolute for `os_name`,
    no control characters, no '..', not a filesystem root), trailing separators
    cut; None when it does not."""
    if not isinstance(raw, str) or not raw or len(raw) > 240:
        return None
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):
        return None
    if os_name == "windows":
        absolute = re.fullmatch(r"[A-Za-z]:[\\/].*", raw) is not None
    else:
        absolute = raw.startswith("/")
    if not absolute or ".." in re.split(r"[\\/]", raw):
        return None
    cleaned = raw.rstrip("\\/")
    if not cleaned or re.fullmatch(r"[A-Za-z]:", cleaned):
        return None
    return cleaned


def _node_entry(data: dict) -> tuple[str, dict] | None:
    """(host, hosts.yaml-shaped entry) for a parsed node.yaml that carries host,
    os and hq_root, all three well-formed; None otherwise. Never raises.

    The entry has the keys tools/hq_join.accept gives a joined node (os,
    hq_root, agents_root, worktrees, provides, max_workers, runners) with the
    same layout and the same conservative defaults: nothing is claimed that the
    probe has not measured. `ssh` is None, as for `mac` on the Mac: a node never
    dials out to reach itself, and an alias here would make tools/worker_reap
    treat this box as a remote one."""
    raw, os_name = data.get("host"), data.get("os")
    if not isinstance(raw, str) or os_name not in _PLATFORM_TO_OS.values():
        return None
    host = raw.strip().lower()
    root = _node_hq_root(os_name, data.get("hq_root"))
    if root is None or not HOST_NAME_RE.fullmatch(host):
        return None
    sep = "\\" if os_name == "windows" else "/"
    agents_root = f"{root}{sep}Agents{sep}Core"
    return host, {
        "os": os_name, "hq_root": root, "ssh": None,
        "agents_root": agents_root, "worktrees": f"{agents_root}{sep}worktrees",
        "provides": [], "max_workers": 1, "runners": [],
    }


def _node_yaml_entry() -> tuple[str, dict] | None:
    """_node_entry() of this machine's node.yaml; None when it is absent or bad.
    Never raises, so hosts() cannot fail because of it."""
    try:
        data = _load_node_yaml()
    except (OSError, ValueError, yaml.YAMLError):
        return None
    return _node_entry(data) if data else None


def _env_host() -> str | None:
    raw = os.environ.get("ORG_HOST")
    if raw is None or not raw.strip():
        return None
    key = raw.strip().lower()
    # hosts() includes a joined node's own node.yaml entry, so ORG_HOST naming it
    # resolves (deploy/join/join.sh runs the probe with ORG_HOST set). Any other
    # unknown name still raises.
    if key not in hosts():
        raise ValueError(
            f"ORG_HOST={raw!r} is not a known host (config/hosts.yaml, or a "
            f"well-formed host + os + hq_root in {NODE_CONFIG_PATH}). "
            f"Known: {sorted(hosts())}"
        )
    return key


def _node_yaml_host() -> str | None:
    data = _load_node_yaml()
    if data is None:
        return None
    raw = data.get("host")
    if raw is None or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    # hosts() holds hosts.yaml's names plus this node.yaml's own entry when it has
    # host + os + hq_root, all well-formed; anything else is unknown.
    if key not in hosts():
        raise ValueError(
            f"{NODE_CONFIG_PATH}: host: {raw!r} is not a known host "
            f"(config/hosts.yaml) and node.yaml has no well-formed os + hq_root "
            f"to make it one. Known: {sorted(hosts())}"
        )
    return key


def _root_match_host() -> str | None:
    """ROOT matched against each host's `agents_root`.

    Compares resolved real paths so a compat symlink (Contabo's, and any
    the Mac path is reached through) can't defeat the match. A worktree
    under `<agents_root>/worktrees/...` counts as that host too — this is
    how a DEV worker resolves its own host, not just a C-level session at
    the repo root.
    """
    root_real = ROOT.resolve()
    for name, h in hosts().items():
        agents_root = h.get("agents_root")
        if not agents_root:
            continue
        try:
            host_root = Path(agents_root).resolve()
        except OSError:
            continue
        if root_real == host_root:
            return name
        try:
            root_real.relative_to(host_root / "worktrees")
            return name
        except ValueError:
            pass
    return None


def _platform_host() -> str | None:
    os_key = _PLATFORM_TO_OS.get(platform.system())
    if os_key is None:
        return None
    matches = [name for name, h in hosts().items() if h.get("os") == os_key]
    return matches[0] if len(matches) == 1 else None


# Resolution order for self_host() (docs/design/org-mesh.md C1): the first
# source that gives a key wins. Shared with self_host_sources() so the two
# can never drift apart.
_SELF_HOST_SOURCES = (
    ("env", _env_host),
    ("node_yaml", _node_yaml_host),
    ("root", _root_match_host),
    ("platform", _platform_host),
)


@lru_cache(maxsize=1)
def self_host() -> str:
    """This process's config/hosts.yaml key. Cached per process.

    Never guesses: a host that resolves to nothing through any of the four
    sources below raises RuntimeError instead of silently defaulting to
    'mac' — that default is what sent Contabo/winbox local spawns and
    reconciliation to act on the wrong host (docs/design/org-mesh.md §2.2).
    A bad ORG_HOST or an unknown node.yaml host: key also raises, rather
    than falling through to a weaker source. "Unknown" means absent from
    hosts.yaml AND not a joined node's own node.yaml (host + os + hq_root).
    """
    sources: dict[str, str | None] = {}
    for name, fn in _SELF_HOST_SOURCES:
        sources[name] = fn()
        if sources[name]:
            return sources[name]
    raise RuntimeError(
        "cannot resolve self_host: "
        + ", ".join(f"{k}={v!r}" for k, v in sources.items())
    )


def self_host_sources() -> dict[str, str | None]:
    """What each self_host() source says, on its own, right now.

    Never raises (a source that would raise in self_host() — bad ORG_HOST,
    bad node.yaml key — reports its error message as the value instead) and
    never caches, so a health check (tools/mesh_check.py L0) always sees the
    current state. No network, no filesystem writes.
    """
    out: dict[str, str | None] = {}
    for name, fn in _SELF_HOST_SOURCES:
        try:
            out[name] = fn()
        except Exception as exc:
            out[name] = f"error: {exc}"
    return out


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
    for line in env_file.read_text(encoding="utf-8").splitlines():
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



