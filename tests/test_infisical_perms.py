"""`perms`: read-only view of what this identity may do in a project (CTO #c34459eb, 2026-10-14)."""
from __future__ import annotations

from tools import infisical_setup


class _Org:
    identity = "contabo"

    def __init__(self, out):
        self.out, self.gets, self.sent = out, [], []

    def projects(self):
        return {"org-coo": {"id": "pid-123456789", "name": "Org-Coo", "slug": "org-coo"},
                "agents-core": {"id": "pid-2", "name": "Agents-Core", "slug": "agents-core"}}

    def get(self, route, **query):
        self.gets.append(route)
        return self.out

    def send(self, *a, **k):  # perms must never write
        self.sent.append(a)
        raise AssertionError("perms wrote to Infisical")


def test_perms_prints_role_and_rules_and_never_writes(capsys):
    org = _Org({"data": {"membership": {"roles": [{"role": "viewer"}]},
                         "permissions": [["read", "secret-folders"], ["read", "secrets"]]}})
    infisical_setup.cmd_perms(org, "Org-Coo")
    out = capsys.readouterr().out
    assert 'contabo sees 2 project(s): ["agents-core", "org-coo"]' in out
    assert '"Org-Coo" (slug "org-coo", id pid-1234): roles=["viewer"]' in out
    assert '  allow ["read", "secret-folders"]' in out
    assert org.gets == ["/api/v1/workspace/pid-123456789/permissions"]
    assert org.sent == []


def test_perms_custom_role_slug_wins_and_missing_membership_is_empty(capsys):
    infisical_setup.cmd_perms(_Org({"data": {"membership": {"roles": [{"role": "custom", "customRoleSlug": "gate-writer"}]}}}), "org-coo")
    assert 'roles=["gate-writer"]' in capsys.readouterr().out
    infisical_setup.cmd_perms(_Org({"data": {}}), "Org-Coo")
    assert "roles=[]" in capsys.readouterr().out


def test_perms_deny_flag_survives_truncation(capsys):
    long_cond = {"secretPath": {"$glob": "/" + "x" * 400}}
    infisical_setup.cmd_perms(_Org({"data": {"permissions": [["create", "secret-folders", long_cond, 1],
                                                             {"action": "read", "subject": "secrets", "inverted": True},
                                                             ["read", "secrets", 0, 0]]}}), "Org-Coo")
    lines = [l for l in capsys.readouterr().out.splitlines() if l.startswith("  ")]
    assert lines[0].startswith("  DENY  ") and len(lines[0]) <= 308
    assert lines[1].startswith("  DENY  ")
    assert lines[2].startswith("  allow ")


def test_perms_null_fields_do_not_crash(capsys):
    for out in ({"data": None}, {"data": {"membership": None, "permissions": None}},
                {"data": {"membership": {"roles": None}}}, None):
        infisical_setup.cmd_perms(_Org(out), "Org-Coo")
    assert capsys.readouterr().out.count("roles=[]") == 4


def test_perms_refuses_a_path_as_identity(monkeypatch):
    monkeypatch.setattr(infisical_setup, "Org", lambda identity: (_ for _ in ()).throw(AssertionError("opened a cred")))
    try:
        infisical_setup.main(["perms", "Org-Coo", "--as", "../etc/x"])
    except SystemExit as e:
        assert "bad identity name" in str(e)
    else:
        raise AssertionError("no refusal")


def test_perms_parser_defaults_to_this_machine(monkeypatch):
    seen = {}
    monkeypatch.setattr(infisical_setup, "self_host", lambda: "contabo")
    monkeypatch.setattr(infisical_setup, "Org", lambda identity: seen.setdefault("id", identity) or _Org({}))
    monkeypatch.setattr(infisical_setup, "cmd_perms", lambda org, project: seen.setdefault("project", project))
    infisical_setup.main(["perms", "Org-Coo"])
    assert seen == {"id": "contabo", "project": "Org-Coo"}
