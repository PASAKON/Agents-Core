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


# --- DEV model provider override (flag-gated, reversible) -----------------
# When DEV_MODEL_PROVIDER is set, worker DEVs spawn against an alternative
# Anthropic-compatible endpoint instead of Claude, to offload grunt coding
# work to a cheaper model (BytePlus ModelArk -> GLM-5.1) while C-level
# orchestration stays on Claude. Flag unset -> 100% original behaviour.

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
            return v.strip().strip('"').strip("'")
    return None


# Anthropic-compatible coding endpoints per provider. IMPORTANT: the
# BytePlus base URL MUST be /api/coding — the /api/v3 base bypasses the
# Coding Plan quota and incurs separate postpaid charges (BytePlus docs).
_PROVIDER_ENDPOINTS = {
    "byteplus": "https://ark.ap-southeast.bytepluses.com/api/coding",
}
_PROVIDER_KEY_VAR = {
    "byteplus": "BYTEPLUS_API_KEY",
}
_PROVIDER_DEFAULT_MODEL = {
    "byteplus": "glm-5.1",
}


def _provider_overrides(
    role_name: str,
    *,
    flag_var: str,
    roles_var: str,
    default_roles: str,
    model_var: str,
) -> dict | None:
    """Shared spawn-override resolver for the cheaper Anthropic-compatible
    provider path (BytePlus ModelArk -> GLM-5.1).

    Returns {"model": str, "env": dict, "effort": str | None} or None to
    use the default Claude path. Fails safe to None (Claude) when the
    provider is unknown, the role is outside the pilot scope, or the API
    key is missing — never spawns against a broken/unauthed endpoint.
    """
    provider = (os.environ.get(flag_var)
                or _read_dotenv_var(flag_var) or "").strip().lower()
    if not provider or provider not in _PROVIDER_ENDPOINTS:
        return None
    # Pilot scope: only these roles offload; others stay on Claude.
    pilot = os.environ.get(roles_var, default_roles)
    allowed_roles = {r.strip() for r in pilot.split(",") if r.strip()}
    if role_name not in allowed_roles:
        return None
    key = (os.environ.get(_PROVIDER_KEY_VAR[provider])
           or _read_dotenv_var(_PROVIDER_KEY_VAR[provider]))
    if not key:
        return None  # no key -> fall back to Claude rather than spawn broken
    model = os.environ.get(model_var) or _PROVIDER_DEFAULT_MODEL[provider]
    return {
        "model": model,
        "env": {
            "ANTHROPIC_BASE_URL": _PROVIDER_ENDPOINTS[provider],
            "ANTHROPIC_AUTH_TOKEN": key,
            "ANTHROPIC_MODEL": model,
        },
        "effort": None,  # GLM/ModelArk endpoints don't accept Claude --effort
    }


def dev_provider_overrides(role_name: str) -> dict | None:
    """Spawn overrides for a worker DEV when DEV_MODEL_PROVIDER is set.

    Flag-gated + reversible: unset DEV_MODEL_PROVIDER -> original Claude path.
    """
    return _provider_overrides(
        role_name,
        flag_var="DEV_MODEL_PROVIDER",
        roles_var="DEV_PROVIDER_ROLES",
        default_roles="developer,tester",
        model_var="DEV_PROVIDER_MODEL",
    )


def cxo_provider_overrides(role_name: str) -> dict | None:
    """Spawn overrides for a C-level (cto/cmo/cgo/cfo) when CXO_MODEL_PROVIDER
    is set. Independent flag from worker DEVs so C-level orchestration can be
    offloaded to GLM (to dodge the Claude weekly cap) separately.

    Flag-gated + reversible: unset CXO_MODEL_PROVIDER -> original Claude path.
    Default pilot scope is "cto" only; widen via CXO_PROVIDER_ROLES.
    """
    return _provider_overrides(
        role_name,
        flag_var="CXO_MODEL_PROVIDER",
        roles_var="CXO_PROVIDER_ROLES",
        default_roles="cto",
        model_var="CXO_PROVIDER_MODEL",
    )
