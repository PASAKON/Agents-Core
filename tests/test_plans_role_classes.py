"""config/plans.yaml role_classes may only name real worker roles (policies/agents.yaml).

A key that is not a role routes nothing and fails silently: `devops` sat there for weeks while the role
is `devops_engineer` (COO investigation, CEO 2026-10-04).
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_role_classes_keys_are_real_roles():
    plans = yaml.safe_load((ROOT / "config" / "plans.yaml").read_text(encoding="utf-8"))
    agents = yaml.safe_load((ROOT / "policies" / "agents.yaml").read_text(encoding="utf-8"))
    roles = set(agents["roles"])
    unknown = sorted(set(plans["role_classes"]) - roles)
    assert unknown == [], f"role_classes names roles that do not exist: {unknown}"


def test_role_classes_point_at_declared_classes():
    plans = yaml.safe_load((ROOT / "config" / "plans.yaml").read_text(encoding="utf-8"))
    classes = set(plans["roles"])
    assert sorted(set(plans["role_classes"].values()) - classes) == []
