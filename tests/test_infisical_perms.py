"""`perms`: read-only view of what this identity may do in a project (CTO #c34459eb, 2026-10-14)."""
from __future__ import annotations

from tools import infisical_setup


class _Org:
    identity = "contabo"
    setup_identity = "ident-abcdef12"

    def __init__(self, out, routes=None):
        self.out, self.gets, self.sent, self.routes = out, [], [], routes or {}

    def projects(self):
        return {"org-coo": {"id": "pid-123456789", "name": "Org-Coo", "slug": "org-coo"},
                "agents-core": {"id": "pid-2", "name": "Agents-Core", "slug": "agents-core"}}

    def get(self, route, **query):
        self.gets.append(route)
        hit = next((v for k, v in self.routes.items() if route.startswith(k)), None)
        if isinstance(hit, Exception):
            raise hit
        return hit if hit is not None else self.out

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
    assert org.gets == ["/api/v1/projects/pid-123456789/permissions"]
    assert org.sent == []


def test_perms_custom_role_slug_wins_and_missing_membership_is_empty(capsys):
    infisical_setup.cmd_perms(_Org({"data": {"membership": {"roles": [{"role": "custom", "customRoleSlug": "gate-writer"}]}}}), "org-coo")
    assert 'roles=["gate-writer"]' in capsys.readouterr().out
    infisical_setup.cmd_perms(_Org({"data": {}}, {"/api/v1/projects/pid-123456789/identity-memberships/": {}}), "Org-Coo")
    assert "roles=[]" in capsys.readouterr().out


def _404(route):
    return infisical_setup.ApiError(f"Route GET:{route} not found: GET {route} -> HTTP 404")


def test_perms_falls_through_a_404_route_and_reads_the_membership_row(capsys):
    org = _Org({}, {"/api/v1/projects/pid-123456789/permissions": _404("/api/v1/projects/x/permissions"),
                    "/api/v1/workspace/pid-123456789/permissions": _404("/api/v1/workspace/x/permissions"),
                    "/api/v1/projects/pid-123456789/identity-memberships/ident-abcdef12":
                        {"identityMembership": {"roles": [{"role": "developer"}]}}})
    infisical_setup.cmd_perms(org, "Org-Coo")
    out = capsys.readouterr().out
    assert 'roles=["developer"]' in out
    assert "no permissions route answered" in out
    assert org.gets[-1] == "/api/v1/projects/pid-123456789/identity-memberships/ident-abcdef12"


def test_perms_second_route_answers_after_a_404(capsys):
    org = _Org({}, {"/api/v1/projects/pid-123456789/permissions": _404("/api/v1/projects/x/permissions"),
                    "/api/v1/workspace/pid-123456789/permissions":
                        {"data": {"membership": {"roles": [{"role": "admin"}]}, "permissions": [["create", "secret-folders"]]}}})
    infisical_setup.cmd_perms(org, "Org-Coo")
    out = capsys.readouterr().out
    assert 'roles=["admin"]' in out and '  allow ["create", "secret-folders"]' in out
    assert "no permissions route" not in out


def test_perms_an_error_other_than_404_or_403_still_raises():
    org = _Org({}, {"/api/v1/projects/pid-123456789/permissions":
                    infisical_setup.ApiError("GET /x -> HTTP 500: boom")})
    try:
        infisical_setup.cmd_perms(org, "Org-Coo")
    except infisical_setup.ApiError as exc:
        assert "500" in str(exc)
    else:
        raise AssertionError("500 swallowed")


def test_perms_a_403_falls_through_to_the_membership_row(capsys):
    # card 86de (2026-10-14): Infisical answered 403 on the caller's own permissions route
    deny = infisical_setup.ApiError("You are not allowed to access this resource: GET /x -> HTTP 403")
    org = _Org({}, {"/api/v1/projects/pid-123456789/permissions": deny,
                    "/api/v1/workspace/pid-123456789/permissions": deny,
                    "/api/v1/projects/pid-123456789/identity-memberships/":
                        {"identityMembership": {"roles": [{"role": "member"}]}}})
    infisical_setup.cmd_perms(org, "Org-Coo")
    out = capsys.readouterr().out
    assert "(403 on /api/v1/projects/<id>/permissions)" in out
    assert 'roles=["member"]' in out
    assert "roles above come from the membership row" in out
    assert org.sent == []


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
