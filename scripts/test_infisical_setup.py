"""tools/infisical_setup.py against a fake Infisical API (in-process HTTP server, temp cred dir).

Proves: plan on an empty org lists the whole PLAN §3 layout, apply builds it, a second apply
changes nothing, the minted machine secret lands 0600 and logs in, save refuses bad logins,
and no secret value ever reaches stdout.
"""
from __future__ import annotations

import base64
import contextlib
import io
import itertools
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

ORG = "org-0000-1111"
SETUP_ID, SETUP_SECRET = "setup-client-id", "setup-SECRET-value-do-not-print"


class Fake:
    def __init__(self):
        self.ids = itertools.count(1)
        self.projects: dict[str, dict] = {}          # id -> {name, slug, envs{slug:id}, folders{env:set}, users set, idents{name:[roles]}}
        self.identities: dict[str, dict] = {"id-setup": {"name": "setup", "client": SETUP_ID}}
        self.secrets = {SETUP_ID: SETUP_SECRET}      # clientId -> clientSecret
        self.writes = 0

    def nid(self, p):
        return f"{p}-{next(self.ids)}"

    def jwt(self, identity_id):
        body = base64.urlsafe_b64encode(json.dumps(
            {"orgId": ORG, "identityId": identity_id}).encode()).decode().rstrip("=")
        return f"h.{body}.s"


def make_handler(fake: Fake):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, obj):
            raw = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def route(self, method):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            p = u.path
            b = self.body() if method in ("POST", "PATCH") else {}
            if method != "GET" and p != "/api/v1/auth/universal-auth/login":
                fake.writes += 1
            if method == "POST" and p == "/api/v1/auth/universal-auth/login":
                if fake.secrets.get(b.get("clientId")) != b.get("clientSecret"):
                    return self.reply(401, {"message": "Invalid credentials"})
                iid = next(i for i, x in fake.identities.items() if x.get("client") == b["clientId"])
                return self.reply(200, {"accessToken": fake.jwt(iid), "expiresIn": 86400})
            if not self.headers.get("Authorization", "").startswith("Bearer h."):
                return self.reply(401, {"message": "no token"})
            if method == "GET" and p == f"/api/v2/organizations/{ORG}/workspaces":
                return self.reply(200, {"workspaces": [
                    {"id": i, "slug": x["slug"], "name": x["name"],
                     "environments": [{"slug": s, "name": s} for s in x["envs"]]}
                    for i, x in fake.projects.items()]})
            if method == "POST" and p == "/api/v2/workspace":
                i = fake.nid("proj")
                defaults = () if b.get("shouldCreateDefaultEnvs") is False else ("dev", "staging", "prod")
                fake.projects[i] = {"name": b["projectName"], "slug": b["slug"],
                                    "envs": {e: fake.nid("env") for e in defaults},
                                    "folders": {}, "users": set(), "idents": {"setup": ["admin"]}}
                return self.reply(200, {"project": {"id": i, "slug": b["slug"]}})
            m = re.fullmatch(r"/api/v1/projects/([^/]+)", p)
            if method == "GET" and m:
                x = fake.projects[m[1]]
                return self.reply(200, {"project": {"id": m[1], "environments": [
                    {"slug": s, "name": s, "id": e} for s, e in x["envs"].items()]}})
            m = re.fullmatch(r"/api/v1/projects/([^/]+)/environments/([^/]+)", p)
            if method == "DELETE" and m:
                # the real API answered 500 to every delete on 2026-09-26; the tool must never call it
                return self.reply(500, {"message": "Something went wrong"})
                envs = fake.projects[m[1]]["envs"]  # unreachable, kept for the record
                slug = next(s for s, e in envs.items() if e == m[2])
                del envs[slug]
                return self.reply(200, {"message": "ok"})
            m = re.fullmatch(r"/api/v1/projects/([^/]+)/environments", p)
            if method == "POST" and m:
                envs = fake.projects[m[1]]["envs"]
                if len(envs) >= 3:
                    return self.reply(400, {"message": "environment limit reached"})
                envs[b["slug"]] = fake.nid("env")
                return self.reply(200, {"message": "ok"})
            if p == "/api/v2/folders":
                if method == "GET":
                    names = fake.projects[q["projectId"]]["folders"].get(q["environment"], set())
                    return self.reply(200, {"folders": [{"name": n} for n in sorted(names)]})
                fake.projects[b["projectId"]]["folders"].setdefault(b["environment"], set()).add(b["name"])
                return self.reply(200, {"folder": {"id": fake.nid("fld")}})
            if method == "GET" and p == f"/api/v2/organizations/{ORG}/memberships":
                return self.reply(200, {"users": [{"role": "admin", "isActive": True,
                                                   "user": {"username": "ceo@example.com"}}]})
            m = re.fullmatch(r"/api/v1/workspace/([^/]+)/memberships", p)
            if method == "GET" and m:
                return self.reply(200, {"memberships": [
                    {"user": {"username": u}} for u in fake.projects[m[1]]["users"]]})
            m = re.fullmatch(r"/api/v2/workspace/([^/]+)/memberships", p)
            if method == "POST" and m:
                fake.projects[m[1]]["users"].update(b["usernames"])
                return self.reply(200, {"memberships": []})
            if p == "/api/v1/identities":
                if method == "GET":
                    return self.reply(200, {"identities": [
                        {"identity": {"id": i, "name": x["name"]}} for i, x in fake.identities.items()]})
                i = fake.nid("ident")
                fake.identities[i] = {"name": b["name"]}
                return self.reply(200, {"identity": {"id": i}})
            m = re.fullmatch(r"/api/v1/identities/([^/]+)", p)
            if method == "DELETE" and m:
                fake.identities.pop(m[1])
                return self.reply(200, {"identity": {"id": m[1]}})
            m = re.fullmatch(r"/api/v1/auth/universal-auth/identities/([^/]+)", p)
            if m:
                x = fake.identities[m[1]]
                if method == "POST":
                    x["client"] = fake.nid("client")
                return self.reply(200, {"identityUniversalAuth": {"clientId": x["client"]}})
            m = re.fullmatch(r"/api/v1/auth/universal-auth/identities/([^/]+)/client-secrets", p)
            if method == "POST" and m:
                secret = f"minted-SECRET-{next(fake.ids)}"
                fake.secrets[fake.identities[m[1]]["client"]] = secret
                return self.reply(200, {"clientSecret": secret, "clientSecretData": {}})
            m = re.fullmatch(r"/api/v1/projects/([^/]+)/identity-memberships", p)
            if method == "GET" and m:
                return self.reply(200, {"identityMemberships": [
                    {"identity": {"name": n}, "roles": [{"role": r} for r in roles]}
                    for n, roles in fake.projects[m[1]]["idents"].items()]})
            m = re.fullmatch(r"/api/v1/projects/([^/]+)/identity-memberships/([^/]+)", p)
            if method == "POST" and m:
                fake.projects[m[1]]["idents"][fake.identities[m[2]]["name"]] = [b["role"]]
                return self.reply(200, {"identityMembership": {}})
            return self.reply(404, {"message": f"fake: no route {method} {p}"})

        def do_GET(self):
            self.route("GET")

        def do_POST(self):
            self.route("POST")

        def do_DELETE(self):
            self.route("DELETE")

        def do_PATCH(self):
            self.route("PATCH")
    return H


class InfisicalSetupTest(unittest.TestCase):
    def setUp(self):
        self.fake = Fake()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.fake))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.tmp = tempfile.TemporaryDirectory()
        self.cred_dir = os.path.join(self.tmp.name, "infisical")
        env = {"INFISICAL_API_URL": f"http://127.0.0.1:{self.srv.server_port}",
               "INFISICAL_CRED_DIR": self.cred_dir}
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        sys.modules.pop("infisical_setup", None)
        import infisical_setup
        self.mod = infisical_setup
        self.root = mock.patch.object(os, "geteuid", return_value=0)
        self.root.start()

    def tearDown(self):
        self.root.stop()
        self.env.stop()
        self.srv.shutdown()
        self.tmp.cleanup()

    def run_cli(self, *argv, stdin=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            if stdin is not None:
                with mock.patch("builtins.input", return_value=stdin[0]), \
                        mock.patch("getpass.getpass", return_value=stdin[1]):
                    self.mod.main(list(argv))
            else:
                self.mod.main(list(argv))
        text = out.getvalue()
        self.assertNotIn("SECRET", text, "a secret value reached stdout")
        return text

    def save_setup(self):
        return self.run_cli("save", "setup", stdin=(SETUP_ID, SETUP_SECRET))

    def test_save_writes_0600_and_hides_the_secret(self):
        text = self.save_setup()
        path = os.path.join(self.cred_dir, "setup.env")
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(self.cred_dir).st_mode & 0o777, 0o700)
        self.assertIn("login OK", text)
        self.assertIn(SETUP_SECRET, Path(path).read_text())

    def test_save_from_stdin_pipe(self):
        with mock.patch("sys.stdin", io.StringIO(f"{SETUP_ID}\n{SETUP_SECRET}\n")):
            text = self.run_cli("save", "setup", "--stdin")
        self.assertIn("login OK", text)
        self.assertEqual(os.stat(os.path.join(self.cred_dir, "setup.env")).st_mode & 0o777, 0o600)

    def test_save_refuses_a_wrong_secret_and_writes_nothing(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_cli("save", "setup", stdin=(SETUP_ID, "wrong"))
        self.assertIn("login failed", str(cm.exception))
        self.assertFalse(os.path.exists(os.path.join(self.cred_dir, "setup.env")))

    def test_plan_is_read_only_and_lists_the_layout(self):
        self.save_setup()
        text = self.run_cli("plan")
        self.assertEqual(self.fake.writes, 0)
        self.assertEqual(text.count("would + project "), len(self.mod.PROJECTS))
        self.assertIn("would + identity contabo", text)

    def test_apply_builds_plan_section_3_then_is_a_no_op(self):
        self.save_setup()
        self.run_cli("apply", "--mint", "contabo")
        projects = {x["name"]: x for x in self.fake.projects.values()}
        self.assertEqual(set(projects), set(self.mod.PROJECTS))
        for name, envs in self.mod.PROJECTS.items():
            self.assertEqual(sorted(projects[name]["envs"]), sorted(envs), name)
            self.assertIn("ceo@example.com", projects[name]["users"], name)
        self.assertEqual(projects["Org-Infra"]["envs"].keys(), {"prod"})
        self.assertEqual(projects["Org-Infra"]["folders"]["prod"], set(self.mod.ORG_INFRA_FOLDERS))
        for host, allowed in self.mod.MACHINES.items():
            for name, x in projects.items():
                self.assertEqual(x["idents"].get(host) == ["viewer"], name in allowed, (host, name))
        self.assertNotIn("contabo", projects["Org-Infra"]["idents"])
        self.assertNotIn("winbox", projects["Org-Infra"]["idents"])
        minted = os.path.join(self.cred_dir, "contabo.env")
        self.assertEqual(os.stat(minted).st_mode & 0o777, 0o600)
        self.assertFalse(os.path.exists(os.path.join(self.cred_dir, "mac.env")))

        before = self.fake.writes
        again = self.run_cli("apply")
        self.assertEqual(self.fake.writes, before, again)
        self.assertNotIn("+ ", again)

    def test_retire_setup_removes_identity_and_file(self):
        self.save_setup()
        self.run_cli("retire-setup")
        self.assertNotIn("setup", [x["name"] for x in self.fake.identities.values()])
        self.assertFalse(os.path.exists(os.path.join(self.cred_dir, "setup.env")))


if __name__ == "__main__":
    unittest.main()
