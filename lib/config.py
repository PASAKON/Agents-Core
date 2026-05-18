"""Config loader for projects.yaml and agents.yaml."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROJECTS_CONFIG = ROOT / "config" / "projects.yaml"
AGENTS_CONFIG = ROOT / "policies" / "agents.yaml"


@lru_cache(maxsize=1)
def projects() -> dict[str, dict]:
    data = yaml.safe_load(PROJECTS_CONFIG.read_text())
    return {p["key"]: p for p in data["projects"]}


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
