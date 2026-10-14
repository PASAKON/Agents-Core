"""`mkdir`: one folder, idempotent, and a FAIL-CLOSED write probe before the COO gate rotation
(deploy/coo-gate/README.md step 2; PH CooGate #adb2edb0, 2026-10-14). Every run writes: a nested
probe folder is created and deleted even when the target already exists."""
from __future__ import annotations

import pytest

from tools import infisical_setup

DENY = "You are not allowed to create on folders: POST /api/v2/folders -> HTTP 403"


class _Org:
    def __init__(self, have=(), deny=False, deny_delete=False):
        self.have, self.deny, self.deny_delete, self.sent = set(have), deny, deny_delete, []

    def projects(self):
        return {"org-coo": {"id": "pid", "name": "Org-Coo", "slug": "org-coo"}}

    def environments(self, project_id):
        return {"prod": "e1"}

    def folders(self, project_id, env):
        return set(self.have)

    def send(self, method, route, body=None, **query):
        if self.deny or (method == "DELETE" and self.deny_delete):
            raise infisical_setup.ApiError(DENY)
        self.sent.append((method, route, body))
        return {"folder": {"id": f"fid-{len(self.sent)}", "name": (body or {}).get("name")}}


def _posts(org):
    return [b for m, r, b in org.sent if m == "POST"]


def test_creates_a_missing_folder_then_probes_inside_it(capsys):
    org = _Org()
    infisical_setup.cmd_mkdir(org, "Org-Coo", "prod", "/gate")
    posts = _posts(org)
    assert posts[0] == {"projectId": "pid", "environment": "prod", "name": "gate", "path": "/"}
    assert posts[1]["path"] == "/gate" and posts[1]["name"].startswith("probe-")
    assert org.sent[-1] == ("DELETE", "/api/v2/folders/fid-2",
                            {"projectId": "pid", "environment": "prod", "path": "/gate"})
    out = capsys.readouterr().out
    assert "folder /gate created" in out and "write proven" in out and "removed" in out


def test_existing_folder_still_proves_write(capsys):
    org = _Org(have={"gate"})
    infisical_setup.cmd_mkdir(org, "Org-Coo", "prod", "gate")
    posts = _posts(org)
    assert len(posts) == 1 and posts[0]["path"] == "/gate" and posts[0]["name"].startswith("probe-")
    assert org.sent[-1][0] == "DELETE"
    assert "exists" in capsys.readouterr().out


def test_folder_exists_and_no_write_role_raises():
    # The hole the probe must not have: /gate already there, contabo has no write -> stop the card.
    with pytest.raises(infisical_setup.ApiError):
        infisical_setup.cmd_mkdir(_Org(have={"gate"}, deny=True), "Org-Coo", "prod", "gate")


def test_missing_folder_and_no_write_role_raises():
    with pytest.raises(infisical_setup.ApiError):
        infisical_setup.cmd_mkdir(_Org(deny=True), "Org-Coo", "prod", "gate")


def test_probe_names_differ_between_runs():
    a, b = _Org(have={"gate"}), _Org(have={"gate"})
    infisical_setup.cmd_mkdir(a, "Org-Coo", "prod", "gate")
    infisical_setup.cmd_mkdir(b, "Org-Coo", "prod", "gate")
    assert _posts(a)[0]["name"] != _posts(b)[0]["name"]


def test_refused_delete_still_succeeds_but_says_so(capsys):
    infisical_setup.cmd_mkdir(_Org(have={"gate"}, deny_delete=True), "Org-Coo", "prod", "gate")
    assert "left in place" in capsys.readouterr().err


@pytest.mark.parametrize("bad", ["a/b", "", "../x", "g ate"])
def test_refuses_nested_or_odd_names(bad):
    with pytest.raises(SystemExit):
        infisical_setup.cmd_mkdir(_Org(), "Org-Coo", "prod", bad)


def test_refuses_org_infra():
    with pytest.raises(SystemExit):
        infisical_setup.cmd_mkdir(_Org(), "Org-Infra", "prod", "x")


def test_cli_exits_nonzero_on_403_even_when_the_folder_exists(monkeypatch):
    monkeypatch.setattr(infisical_setup, "Org", lambda identity=None: _Org(have={"gate"}, deny=True))
    with pytest.raises(SystemExit) as e:
        infisical_setup.main(["mkdir", "Org-Coo", "prod", "gate", "--as", "contabo"])
    assert "HTTP 403" in str(e.value.code)
