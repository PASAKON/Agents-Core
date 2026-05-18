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


def get_project(key: str) -> dict:
    p = projects().get(key)
    if not p:
        raise ValueError(f"unknown project: {key}. Known: {list(projects())}")
    return p
