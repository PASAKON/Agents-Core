"""Org Mesh W4.6c F2 (reshaped by W4.2b): the Org-Node project holds the one node secret, nothing else.

Review task-79219f24 F2: every node must read one project and no other. Since W4.2b (CEO
2026-10-03) a node has no Infisical identity at all: `contabo` is a viewer on Org-Node, the hub
reads the token there and hands it to an approved node (tools/node_token_api.py). Nothing here
contacts Infisical and no test writes a secret value.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w46c_node_project.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools import hq_join, infisical_setup

ROOT = Path(__file__).resolve().parent.parent
JOIN_SH = ROOT / "deploy" / "join" / "join.sh"
JOIN_PS1 = ROOT / "deploy" / "join" / "join.ps1"


@pytest.fixture(autouse=True)
def _no_admin_files(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "CRED_DIR", str(tmp_path / "no-creds"))


class _NoCallOrg:
    """An org that records every call: the guards under test must make none."""
    def __init__(self):
        self.calls = []

    def get(self, *a, **k):
        self.calls.append(("GET", a))
        raise AssertionError("the org was asked")

    send = get


# ------------------------------------------------------------ the plan

def test_org_node_is_a_prod_only_project_in_the_plan():
    assert infisical_setup.NODE_PROJECT == "Org-Node"
    assert infisical_setup.PROJECTS["Org-Node"] == ["prod"]
    assert infisical_setup.NODE_SECRET_NAMES == ("CLAUDE_CODE_OAUTH_TOKEN",)


def test_only_contabo_reads_org_node_and_no_node_identity_is_planned():
    """The hub (contabo) reads the token and serves it; no other machine and no node is a member."""
    readers = [m for m, allowed in infisical_setup.MACHINES.items() if "Org-Node" in allowed]
    assert readers == ["contabo"]
    assert "org-node" not in infisical_setup.MACHINES
    assert infisical_setup.NODE_IDENTITY == "org-node"      # kept only as a name no host may take


def test_the_join_and_node_token_folders_are_planned_in_agents_core_prod_only():
    assert infisical_setup.PROJECT_FOLDERS["Agents-Core"] == ["org-join", "node-token"]
    assert "Org-Node" not in infisical_setup.PROJECT_FOLDERS          # one secret at /, no folders
    assert infisical_setup.PROJECT_FOLDERS["Org-Infra"] == infisical_setup.ORG_INFRA_FOLDERS


# ------------------------------------------------------------ names only, one secret

def test_the_rotate_scope_is_the_one_node_secret_and_needs_no_infisical_call():
    """What a leaving node's rotation list names comes from NODE_SECRET_NAMES, not from a lookup."""
    assert hq_join.rotate_scope() == {"Org-Node/prod": ["CLAUDE_CODE_OAUTH_TOKEN"]}


@pytest.mark.parametrize("project,name,path,refused", [
    ("Org-Node", "CLAUDE_CODE_OAUTH_TOKEN", "/", False),
    ("org-node", "CLAUDE_CODE_OAUTH_TOKEN", "/", False),
    ("Org-Node", "ORG_DB_URL", "/", True),                          # a second secret on every node
    ("Org-Node", "CLAUDE_CODE_OAUTH_TOKEN", "/org-join", True),     # a folder is a second place
    ("Org-Node", None, "/", True),                                  # a bulk import
    ("Agents-Core", "ORG_DB_URL", "/", False),                      # every other project is untouched
    ("Agents-Core", None, "/org-join", False),
])
def test_org_node_accepts_exactly_the_one_secret_name(project, name, path, refused):
    if refused:
        with pytest.raises(SystemExit, match="Org-Node holds only CLAUDE_CODE_OAUTH_TOKEN"):
            infisical_setup._node_project_guard(project, name, path)
    else:
        infisical_setup._node_project_guard(project, name, path)


def test_put_and_import_refuse_before_reading_a_value(monkeypatch):
    """The guard runs ahead of the stdin read and the API: a refused put consumes nothing."""
    org = _NoCallOrg()
    monkeypatch.setattr(infisical_setup, "read_stdin_value",
                        lambda *a, **k: pytest.fail("the value was read"))
    with pytest.raises(SystemExit, match="Org-Node holds only"):
        infisical_setup.cmd_put(org, "Org-Node", "prod", "ORG_DB_URL", "c", [], False)
    with pytest.raises(SystemExit, match="Org-Node holds only"):
        infisical_setup.cmd_import_env(org, "Org-Node", "prod", "/nonexistent.env", [], None, [], False)
    assert org.calls == []


# ------------------------------------------------------------ what a node is told to run

def test_join_scripts_send_the_node_to_org_node_prod():
    for path in (JOIN_SH, JOIN_PS1):
        text = path.read_text(encoding="utf-8")
        assert "run Org-Node prod --as" in text, path.name
        assert "run Agents-Core prod" not in text, path.name


def test_no_doc_tells_a_node_to_run_under_agents_core_prod():
    # a node's `infisical_setup.py run <project> prod --as <host>` is Org-Node now; the secretary
    # units on Contabo (machine identity contabo) are a different thing and keep Agents-Core
    text = (ROOT / "docs" / "ops" / "hq-join.md").read_text(encoding="utf-8")
    bad = [ln for ln in text.splitlines() if re.search(r"run Agents-Core prod --as <?(host|node)", ln)]
    assert bad == []
