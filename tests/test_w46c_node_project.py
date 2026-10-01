"""Org Mesh W4.6c F2: a node reads its own Infisical project (Org-Node), nothing else.

Review task-79219f24 F2: org-node was a viewer on Agents-Core, so one compromised node read every
Agents-Core secret. Now org-node is a viewer on Org-Node (prod only, one secret) and on no other
project. Nothing here contacts Infisical: the org is the FakeOrg of test_w42_provision (two
projects, proj-1 = Org-Node and proj-2 = Agents-Core) and no test writes a secret value.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w46c_node_project.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools import hq_join, infisical_setup
from tools.infisical_setup import ApiError

from test_w42_provision import FakeOrg

ROOT = Path(__file__).resolve().parent.parent
JOIN_SH = ROOT / "deploy" / "join" / "join.sh"
JOIN_PS1 = ROOT / "deploy" / "join" / "join.ps1"


@pytest.fixture(autouse=True)
def _no_admin_files(monkeypatch, tmp_path):
    monkeypatch.setattr(infisical_setup, "CRED_DIR", str(tmp_path / "no-creds"))


def _posts(org):
    return [c for c in org.calls if c[0] == "POST"]


# ------------------------------------------------------------ the plan

def test_org_node_is_a_prod_only_project_in_the_plan():
    assert infisical_setup.NODE_PROJECT == "Org-Node"
    assert infisical_setup.PROJECTS["Org-Node"] == ["prod"]
    assert infisical_setup.NODE_SECRET_NAMES == ("CLAUDE_CODE_OAUTH_TOKEN",)


def test_no_machine_identity_is_planned_onto_org_node():
    # nodes reach Org-Node through org-node alone; a machine identity there would be a second door
    assert all("Org-Node" not in allowed for allowed in infisical_setup.MACHINES.values())


def test_the_join_folder_is_planned_in_agents_core_prod_only():
    assert infisical_setup.PROJECT_FOLDERS["Agents-Core"] == ["org-join"]
    assert "Org-Node" not in infisical_setup.PROJECT_FOLDERS          # one secret at /, no folders
    assert infisical_setup.PROJECT_FOLDERS["Org-Infra"] == infisical_setup.ORG_INFRA_FOLDERS


# ------------------------------------------------------------ membership

def test_org_node_gets_viewer_on_org_node_and_is_not_added_anywhere_else():
    org = FakeOrg()
    infisical_setup.ensure_node_identity(org)
    member_posts = [r for _, r, _ in _posts(org) if "identity-memberships" in r]
    assert member_posts == ["/api/v1/projects/proj-1/identity-memberships/id-org-node"]   # proj-1 = Org-Node
    assert org.members == {"org-node": ["viewer"]}
    assert "org-node" not in org.core_members


def test_ensure_refuses_when_org_node_is_still_a_member_of_agents_core():
    org = FakeOrg(idents=("mac", "contabo", "winbox", "org-node"))
    org.core_members["org-node"] = ["viewer"]       # the state today, before the move
    with pytest.raises(ApiError) as ei:
        infisical_setup.ensure_node_identity(org)
    msg = str(ei.value)
    assert "org-node" in msg and "Agents-Core" in msg and "Org-Node" in msg and "Remove it" in msg
    assert _posts(org) == []                        # nothing was created, repaired or granted


def test_the_refusal_comes_before_any_repair_of_a_half_made_org_node():
    org = FakeOrg(idents=("mac", "contabo", "winbox", "org-node"))
    del org.ua["id-org-node"]                       # Universal Auth missing
    org.members.pop("org-node")                     # no membership on Org-Node
    org.core_members["org-node"] = ["viewer"]
    with pytest.raises(ApiError, match="Agents-Core"):
        infisical_setup.ensure_node_identity(org)
    assert _posts(org) == [] and "id-org-node" not in org.ua


def test_a_third_project_is_named_too(monkeypatch):
    org = FakeOrg(idents=("mac", "org-node"))
    real = org.get

    def get(route, **q):
        if route == "/api/v2/organizations/org-1/workspaces":
            out = real(route, **q)
            out["workspaces"].append({"slug": "org-infra", "name": "Org-Infra", "id": "proj-3"})
            return out
        if route == "/api/v1/projects/proj-3/identity-memberships":
            org.calls.append(("GET", route, None))
            return {"identityMemberships": [{"identity": {"name": "org-node"}, "roles": [{"role": "viewer"}]}]}
        return real(route, **q)

    monkeypatch.setattr(org, "get", get)
    with pytest.raises(ApiError) as ei:
        infisical_setup.ensure_node_identity(org)
    assert "Org-Infra" in str(ei.value) and "Agents-Core" not in str(ei.value)
    assert _posts(org) == []


def test_ensure_says_apply_first_when_org_node_does_not_exist_yet(monkeypatch):
    org = FakeOrg()
    real = org.get

    def get(route, **q):
        out = real(route, **q)
        if route == "/api/v2/organizations/org-1/workspaces":
            out["workspaces"] = [w for w in out["workspaces"] if w["slug"] != "org-node"]
        return out

    monkeypatch.setattr(org, "get", get)
    with pytest.raises(ApiError, match="Org-Node does not exist: run `apply` first"):
        infisical_setup.ensure_node_identity(org)
    assert _posts(org) == []


def test_ensure_is_idempotent_on_the_clean_layout():
    org = FakeOrg(idents=("mac", "contabo", "winbox", "org-node"))
    assert infisical_setup.ensure_node_identity(org) == "id-org-node"
    assert _posts(org) == []


# ------------------------------------------------------------ names only, one secret

def test_node_readable_secret_names_reads_org_node_and_only_org_node():
    class Org(FakeOrg):
        def get(self, route, **q):
            if route == "/api/v1/projects/proj-1":
                self.calls.append(("GET", route, None))
                return {"project": {"environments": [{"slug": "prod", "id": "e"}]}}
            if route == "/api/v3/secrets/raw":
                self.calls.append(("GET", route, None))
                assert q["workspaceId"] == "proj-1" and q["environment"] == "prod"     # Org-Node
                return {"secrets": [{"secretKey": "CLAUDE_CODE_OAUTH_TOKEN", "secretValue": "LEAKME-v"}]}
            return super().get(route, **q)

    out = infisical_setup.node_readable_secret_names(Org())
    assert out == {"Org-Node/prod": ["CLAUDE_CODE_OAUTH_TOKEN"]}
    assert "LEAKME" not in repr(out)


def test_the_documented_fallback_set_is_the_one_node_secret():
    assert len(hq_join.DOCUMENTED_READABLE) == 1
    assert hq_join.DOCUMENTED_READABLE[0].startswith("CLAUDE_CODE_OAUTH_TOKEN")
    scope = hq_join.rotate_scope(None)
    assert list(scope["names"]) == ["Org-Node (documented set)"]


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
    org = FakeOrg()
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
