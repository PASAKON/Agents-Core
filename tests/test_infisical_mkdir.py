"""`mkdir`: one folder, idempotent, and the write probe before the COO gate rotation
(deploy/coo-gate/README.md step 2; PH CooGate #adb2edb0, 2026-10-14)."""
from __future__ import annotations

import pytest

from tools import infisical_setup


class _Org:
    def __init__(self, have=(), deny=False):
        self.have, self.deny, self.sent = set(have), deny, []

    def projects(self):
        return {"org-coo": {"id": "pid", "name": "Org-Coo", "slug": "org-coo"}}

    def environments(self, project_id):
        return {"prod": "e1"}

    def folders(self, project_id, env):
        return set(self.have)

    def send(self, method, route, body=None, **query):
        if self.deny:
            raise infisical_setup.ApiError("You are not allowed to create on folders: POST /api/v2/folders -> HTTP 403")
        self.sent.append((method, route, body))
        return {}


def test_creates_a_missing_folder(capsys):
    org = _Org()
    infisical_setup.cmd_mkdir(org, "Org-Coo", "prod", "/gate")
    assert org.sent == [("POST", "/api/v2/folders",
                         {"projectId": "pid", "environment": "prod", "name": "gate", "path": "/"})]
    assert "folder /gate created" in capsys.readouterr().out


def test_existing_folder_is_left_alone(capsys):
    org = _Org(have={"gate"})
    infisical_setup.cmd_mkdir(org, "Org-Coo", "prod", "gate")
    assert org.sent == [] and "exists" in capsys.readouterr().out


def test_no_write_role_raises_so_the_card_stops():
    with pytest.raises(infisical_setup.ApiError):
        infisical_setup.cmd_mkdir(_Org(deny=True), "Org-Coo", "prod", "gate")


@pytest.mark.parametrize("bad", ["a/b", "", "../x", "g ate"])
def test_refuses_nested_or_odd_names(bad):
    with pytest.raises(SystemExit):
        infisical_setup.cmd_mkdir(_Org(), "Org-Coo", "prod", bad)


def test_refuses_org_infra():
    with pytest.raises(SystemExit):
        infisical_setup.cmd_mkdir(_Org(), "Org-Infra", "prod", "x")


def test_cli_exits_nonzero_on_403(monkeypatch):
    monkeypatch.setattr(infisical_setup, "Org", lambda identity=None: _Org(deny=True))
    with pytest.raises(SystemExit) as e:
        infisical_setup.main(["mkdir", "Org-Coo", "prod", "gate", "--as", "contabo"])
    assert "HTTP 403" in str(e.value.code)
