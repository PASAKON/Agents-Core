#!/usr/bin/env python3
"""Set up the MoonieX Infisical org: phase 1 of docs/design/secrets-infisical/PLAN.md.

Stdlib only: a Run Inbox card copies this one file out of the repo and runs it with python3, so
it cannot import anything else from Agents-Core.

    save <identity>        Ask for a Universal Auth Client ID and Client Secret on this terminal
                           (the CEO types them into a Run Inbox card or a real terminal, never
                           into chat), check that they log in, and save them to
                           /etc/infisical/<identity>.env (root, 0600).
                           --stdin reads the two values as two lines from a pipe instead, for a
                           script that captures them from the web page so no model sees them.
    plan                   Show what `apply` would create or change. Read-only.
    apply [--mint HOST]    Create what is missing: the projects, their environments, the Org-Infra
                           folders, the machine identities with read-only project memberships and
                           the CEO as admin of every project. --mint also creates a client secret
                           for HOST and saves it here as /etc/infisical/HOST.env. Safe to re-run.
    status                 Print what exists now.
    retire-setup           Delete the temporary `setup` identity and its file (end of migration).

The layout below is PLAN.md §3 / §3b as the CEO approved it on 2026-09-25; changing it is a plan
change. Rules this tool enforces itself:
  - it never prints a secret value; secrets are written only to /etc/infisical/*.env (0600);
  - it writes no secret values anywhere in Infisical (phase 1 is structure only), and Org-Infra
    values are the CEO's to enter by hand (PLAN §3b write rule 1).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import getpass
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("INFISICAL_API_URL", "https://app.infisical.com")
CRED_DIR = os.environ.get("INFISICAL_CRED_DIR", "/etc/infisical")  # override only in tests
SETUP = "setup"
SETUP_MAX_DAYS = 14  # the admin identity lives only for the migration (PLAN §6)

# PLAN.md §3: project -> environments. Org-Infra has prod only (§3b).
PROJECTS: dict[str, list[str]] = {
    "Agents-Core": ["dev", "prod"],
    "Org-Infra": ["prod"],
    "MoonieX-ClaudeFlow": ["dev", "prod"],
    "MoonieX-Option": ["dev", "prod"],
    "MoonieX-AlphaTrader": ["dev", "prod"],
    "MoonieX-LineAutomation": ["dev", "prod"],
    "MoonieX-Console": ["dev", "prod"],
    "MoonieX-ComfyRunpod": ["dev", "prod"],
    "MoonieX-CookierunBot": ["dev", "prod"],
    "MoonieX-WebApp": ["dev", "prod"],
    "LungNote-MCP": ["dev", "prod"],
    "LungNote-Webapp": ["dev", "prod"],
    "WarpClip-Webapp": ["dev", "prod"],
    "LinkReed-Webapp": ["dev", "prod"],
}
ORG_INFRA = "Org-Infra"
ORG_INFRA_FOLDERS = ["dns", "deploy", "repo", "net", "db", "vault"]  # §3b closed list

# PLAN.md §3: machine identity -> projects it may read (viewer). On Free a viewer sees every
# environment of the project, so MoonieX-WebApp is not given to the Mac until local dev needs it.
MACHINES: dict[str, list[str]] = {
    "contabo": ["Agents-Core", "MoonieX-ClaudeFlow", "MoonieX-Option", "MoonieX-AlphaTrader",
                "MoonieX-LineAutomation", "MoonieX-Console", "LungNote-MCP"],
    "mac": ["Agents-Core", ORG_INFRA, "MoonieX-Console", "MoonieX-ComfyRunpod", "LungNote-MCP"],
    "winbox": ["Agents-Core", "MoonieX-Console", "MoonieX-CookierunBot"],
}
TOKEN_TTL = 86_400            # an access token lives a day...
TOKEN_MAX_TTL = 7 * 86_400    # ...and cannot be renewed past a week
MACHINE_SECRET_TTL = 365 * 86_400  # the machine's client secret: rotate yearly (radar, phase 5)

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")


class ApiError(RuntimeError):
    pass


def call(method: str, path: str, token: str | None = None, body: dict | None = None,
         query: dict | None = None) -> dict:
    url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "User-Agent": "mooniex-infisical-setup/1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(6):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 5:
                time.sleep(2 ** attempt)
                continue
            detail = exc.read().decode(errors="replace")[:300]
            raise ApiError(f"{method} {path} -> HTTP {exc.code}: {detail}") from None
    raise ApiError(f"{method} {path} -> still rate-limited after retries")


# --- credentials ----------------------------------------------------------------------------

def cred_path(name: str) -> str:
    return os.path.join(CRED_DIR, f"{name}.env")


def read_cred(name: str) -> tuple[str, str]:
    values = {}
    with open(cred_path(name)) as fh:
        for line in fh:
            key, _, val = line.strip().partition("=")
            values[key] = val
    return (values["INFISICAL_UNIVERSAL_AUTH_CLIENT_ID"],
            values["INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET"])


def write_cred(name: str, client_id: str, client_secret: str) -> str:
    os.makedirs(CRED_DIR, mode=0o700, exist_ok=True)
    os.chmod(CRED_DIR, 0o700)
    path = cred_path(name)
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(f"INFISICAL_API_URL={API}\n"
                 f"INFISICAL_UNIVERSAL_AUTH_CLIENT_ID={client_id}\n"
                 f"INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET={client_secret}\n")
    os.replace(path + ".tmp", path)
    return path


def login(client_id: str, client_secret: str) -> tuple[str, dict, int]:
    out = call("POST", "/api/v1/auth/universal-auth/login",
               body={"clientId": client_id, "clientSecret": client_secret})
    token = out["accessToken"]
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    return token, claims, int(out.get("expiresIn", 0))


def require_root() -> None:
    if os.geteuid() != 0:
        sys.exit("run as root: the credentials file lives in /etc/infisical (0700)")


# --- save -----------------------------------------------------------------------------------

def cmd_save(name: str, from_stdin: bool = False) -> None:
    if not NAME_RE.match(name):
        sys.exit(f"bad identity name: {name!r}")
    require_root()
    if from_stdin:
        client_id = sys.stdin.readline().strip()
        client_secret = sys.stdin.readline().strip()
    else:
        client_id = input("Client ID: ").strip()
        client_secret = getpass.getpass("Client Secret: ").strip()
    if not client_id or not client_secret:
        sys.exit("empty input, nothing saved")
    try:
        _, claims, ttl = login(client_id, client_secret)
    except ApiError as exc:
        sys.exit(f"login failed, nothing saved ({exc})")
    path = write_cred(name, client_id, client_secret)
    print(f"saved {path} (0600) · login OK · token lasts {ttl} s · "
          f"identity {str(claims.get('identityId', '?'))[:8]} · org {str(claims.get('orgId', '?'))[:8]}")
    if name == SETUP:
        until = dt.date.today() + dt.timedelta(days=SETUP_MAX_DAYS)
        print(f"reminder: `setup` is an org admin; retire it by {until} (retire-setup)")


# --- state ----------------------------------------------------------------------------------

class Org:
    def __init__(self) -> None:
        require_root()
        self.token, claims, _ = login(*read_cred(SETUP))
        self.org_id = claims["orgId"]
        self.setup_identity = claims.get("identityId")

    def get(self, route, **query):
        return call("GET", route, self.token, query=query or None)

    def send(self, method, route, body=None, **query):
        return call(method, route, self.token, body=body, query=query or None)

    def projects(self) -> dict[str, dict]:
        out = self.get(f"/api/v2/organizations/{self.org_id}/workspaces")
        return {p["slug"]: p for p in out.get("workspaces", [])}

    def environments(self, project_id: str) -> dict[str, str]:
        proj = self.get(f"/api/v1/projects/{project_id}")["project"]
        return {e["slug"]: e["id"] for e in proj.get("environments", [])}

    def folders(self, project_id: str, env: str) -> set[str]:
        out = self.get("/api/v2/folders", projectId=project_id, environment=env, path="/")
        return {f["name"] for f in out.get("folders", [])}

    def identities(self) -> dict[str, str]:
        out = self.get("/api/v1/identities", orgId=self.org_id)
        return {m["identity"]["name"]: m["identity"]["id"] for m in out.get("identities", [])}

    def identity_members(self, project_id: str) -> dict[str, list[str]]:
        out = self.get(f"/api/v1/projects/{project_id}/identity-memberships", limit=100)
        return {m["identity"]["name"]: [r.get("role") for r in m.get("roles", [])]
                for m in out.get("identityMemberships", [])}

    def org_admin_users(self) -> list[str]:
        out = self.get(f"/api/v2/organizations/{self.org_id}/memberships")
        return [u["user"]["username"] for u in out.get("users", [])
                if u.get("role") == "admin" and u.get("isActive", True) and u.get("user")]

    def user_members(self, project_id: str) -> set[str]:
        out = self.get(f"/api/v1/workspace/{project_id}/memberships")
        return {m["user"]["username"] for m in out.get("memberships", []) if m.get("user")}


# --- plan / apply ---------------------------------------------------------------------------

def reconcile(org: Org, dry: bool, mint: str | None) -> list[str]:
    log: list[str] = []

    def act(line: str, fn=None):
        log.append(("would " if dry else "") + line)
        print(log[-1], flush=True)
        if not dry and fn:
            return fn()
        return None

    existing = org.projects()
    project_ids: dict[str, str] = {}
    for name, envs in PROJECTS.items():
        slug = name.lower()
        if slug in existing:
            project_ids[name] = existing[slug]["id"]
        else:
            created = act(f"+ project {name}", lambda n=name, s=slug: org.send(
                "POST", "/api/v2/workspace",
                {"projectName": n, "slug": s, "type": "secret-manager",
                 "shouldCreateDefaultEnvs": False}))
            if created:
                project_ids[name] = created["project"]["id"]
            else:
                continue  # dry run: nothing more to inspect for a project that does not exist
        pid = project_ids[name]
        have = org.environments(pid)
        for env_slug in have:
            if env_slug not in envs:
                # Never deleted: on 2026-09-26 every DELETE by the setup identity (environment,
                # hard or soft, even an empty project) answered HTTP 500 on Infisical Cloud.
                # Projects are created without default environments instead; an extra one
                # (Agents-Core's `staging`, from the first run) is the CEO's one click in the UI.
                log.append(f"! {name}: environment {env_slug} is not in the plan, left in place")
                print(log[-1])
        for env_slug in envs:
            if env_slug not in have:
                act(f"+ {name}: environment {env_slug}", lambda p=pid, e=env_slug: org.send(
                    "POST", f"/api/v1/projects/{p}/environments", {"name": e, "slug": e}))

    if ORG_INFRA in project_ids:
        pid = project_ids[ORG_INFRA]
        have = org.folders(pid, "prod")
        for folder in ORG_INFRA_FOLDERS:
            if folder not in have:
                act(f"+ {ORG_INFRA}: folder /{folder}", lambda f=folder, p=pid: org.send(
                    "POST", "/api/v2/folders",
                    {"projectId": p, "environment": "prod", "name": f, "path": "/"}))

    admins = org.org_admin_users()
    for name, pid in project_ids.items():
        members = org.user_members(pid)
        missing = [u for u in admins if u not in members]
        if missing:
            act(f"+ {name}: CEO ({len(missing)} admin user) as project admin",
                lambda p=pid, m=missing: org.send(
                    "POST", f"/api/v2/workspace/{p}/memberships",
                    {"usernames": m, "roleSlugs": ["admin"]}))

    idents = org.identities()
    members = {name: org.identity_members(pid) for name, pid in project_ids.items()}
    for host, allowed in MACHINES.items():
        iid = idents.get(host)
        if not iid:
            def create(h=host):
                made = org.send("POST", "/api/v1/identities",
                                {"name": h, "organizationId": org.org_id, "role": "no-access"})
                new_id = made["identity"]["id"]
                org.send("POST", f"/api/v1/auth/universal-auth/identities/{new_id}",
                         {"accessTokenTTL": TOKEN_TTL, "accessTokenMaxTTL": TOKEN_MAX_TTL})
                return new_id
            iid = act(f"+ identity {host} (no org role, Universal Auth, token {TOKEN_TTL} s)", create)
            if iid:
                idents[host] = iid
        for name in allowed:
            roles = members.get(name, {}).get(host)
            if roles is None:
                pid = project_ids.get(name)
                act(f"+ {name}: {host} as viewer",
                    (lambda p=pid, i=iid: org.send(
                        "POST", f"/api/v1/projects/{p}/identity-memberships/{i}", {"role": "viewer"}))
                    if pid and iid else None)
            elif roles != ["viewer"]:
                log.append(f"! {name}: {host} has roles {roles}, expected viewer (not changed)")
                print(log[-1])
        for name in project_ids:
            if name not in allowed and host in members.get(name, {}):
                log.append(f"! {name}: {host} is a member but the plan says it should not be")
                print(log[-1])

    if mint:
        if mint not in MACHINES:
            sys.exit(f"--mint: unknown machine {mint!r}")
        if os.path.exists(cred_path(mint)):
            print(f"= {cred_path(mint)} already exists, not minting a second secret")
        elif mint in idents:
            def do_mint(h=mint):
                iid = idents[h]
                ua = org.get(f"/api/v1/auth/universal-auth/identities/{iid}")
                out = org.send("POST", f"/api/v1/auth/universal-auth/identities/{iid}/client-secrets",
                               {"description": f"{h}-{dt.date.today()}", "ttl": MACHINE_SECRET_TTL})
                write_cred(h, ua["identityUniversalAuth"]["clientId"], out["clientSecret"])
                login(*read_cred(h))  # prove it works before anyone relies on it
                return True
            act(f"+ client secret for {mint} -> {cred_path(mint)} (0600, expires in 365 days)", do_mint)
    return log


def cmd_status(org: Org) -> None:
    existing = org.projects()
    idents = org.identities()
    print(f"org {org.org_id[:8]} · {len(existing)} projects · identities: {', '.join(sorted(idents))}")
    for name in PROJECTS:
        p = existing.get(name.lower())
        if not p:
            print(f"  {name:24} missing")
            continue
        envs = ",".join(sorted(org.environments(p["id"])))
        members = org.identity_members(p["id"])
        who = " ".join(f"{h}:{'/'.join(r)}" for h, r in sorted(members.items()))
        print(f"  {name:24} envs={envs:9} {who}")


def cmd_retire_setup(org: Org) -> None:
    if not org.setup_identity:
        sys.exit("cannot tell which identity `setup` is")
    org.send("DELETE", f"/api/v1/identities/{org.setup_identity}")
    os.remove(cred_path(SETUP))
    print(f"deleted identity setup and {cred_path(SETUP)}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save")
    s.add_argument("identity")
    s.add_argument("--stdin", action="store_true", help="read id and secret as two lines from stdin")
    sub.add_parser("plan")
    a = sub.add_parser("apply")
    a.add_argument("--mint", metavar="HOST")
    sub.add_parser("status")
    sub.add_parser("retire-setup")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "save":
            cmd_save(args.identity, from_stdin=args.stdin)
        elif args.cmd == "plan":
            reconcile(Org(), dry=True, mint=None)
        elif args.cmd == "apply":
            reconcile(Org(), dry=False, mint=args.mint)
        elif args.cmd == "status":
            cmd_status(Org())
        elif args.cmd == "retire-setup":
            cmd_retire_setup(Org())
    except ApiError as exc:
        sys.exit(f"Infisical API error: {exc}")
    except FileNotFoundError as exc:
        sys.exit(f"missing credentials: {exc.filename} (run `save {SETUP}` first)")


if __name__ == "__main__":
    main()
