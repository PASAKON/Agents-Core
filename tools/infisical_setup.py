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
    node-secrets           List the client secrets under the shared `org-node` identity (description,
                           id, created, live/revoked). Never a value. Minting and revoking them is
                           done by tools/hq_join through ensure_node_identity / mint_node_secret /
                           revoke_node_secret below (Org Mesh W4.2), not by a verb.
    put <project> <env> <NAME> --stdin [--as ID] [--comment ..] [--meta k=v ..] [--multiline]
                           Create or update ONE secret whose value arrives on stdin (phase 2,
                           skill CTO_Procedure_KeyFetch). Lints NAME against PLAN §4b, requires
                           the §4c metadata on create, prints only name · last4 · expires.
    last4 <project> <env> <NAME> [--as ID]
                           Print the last 4 characters of a stored value, to compare with what
                           the provider's page shows. Never the value.
    import-env <project> <env> <path> [--only A,B] [--legacy] [--comment ..] [--meta k=v ..]
                           Phase 2 cutover: move a whole .env into Infisical 1:1 (names printed,
                           values never). Names that fail §4b are skipped unless --legacy, which
                           imports them with metadata naming=legacy for the phase-6 rename.
    run <project> <env> [--as HOST] -- <command...>
                           PLAN §5: exec the command with the project's secrets in its
                           environment, read with this machine's identity; nothing touches disk.
                           This is how a service or a launcher starts once its .env is gone.

The layout below is PLAN.md §3 / §3b as the CEO approved it on 2026-09-25; changing it is a plan
change. Rules this tool enforces itself:
  - it never prints a secret value; identity secrets are written only to /etc/infisical/*.env
    (0600) and a project secret reaches Infisical only through `put --stdin` (never an argument,
    never a file a model reads);
  - Org-Infra values are the CEO's to enter by hand (PLAN §3b write rule 1): `put` refuses them.
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
_DEFAULT_CRED_DIR = (os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "Infisical")
                     if os.name == "nt" else "/etc/infisical")   # PLAN §5: root-only, one file per host
CRED_DIR = os.environ.get("INFISICAL_CRED_DIR", _DEFAULT_CRED_DIR)  # override only in tests
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
    require_root()
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
    if os.name != "nt" and os.geteuid() != 0:
        sys.exit(f"run as root: the credentials file lives in {CRED_DIR} (0700)")


def self_host() -> str:
    """The machine identity this box should use (PLAN §3): winbox / mac / contabo."""
    if os.name == "nt":
        return "winbox"
    return "mac" if sys.platform == "darwin" else "contabo"


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
    def __init__(self, identity: str = SETUP) -> None:
        self.identity = identity
        self.token, claims, _ = login(*read_cred(identity))
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
            iid = act(f"+ identity {host} (no org role, Universal Auth, token {TOKEN_TTL} s)",
                      lambda h=host: _create_identity(org, h))
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


# --- org-node: one shared identity, one client secret per joining node (Org Mesh W4.2) ------------
# Infisical Free allows IDENTITY_CAP identities and mac, contabo, winbox (plus `setup` until
# retire-setup) already hold slots. A joining node therefore gets its own Universal Auth CLIENT
# SECRET under this one identity, never an identity of its own; `hq_join leave` revokes that one
# secret. These are functions, not CLI verbs: a value exists only in mint_node_secret's return.

NODE_IDENTITY = "org-node"
NODE_PROJECT = "Agents-Core"   # viewer membership; on Free a viewer sees dev and prod alike
IDENTITY_CAP = 5
# The host-name rule, 3-31 chars: a copy of lib.config.HOST_NAME_RE (tools/hq_join.HOST_RE is that
# same object). Not imported: this file stays stdlib-only, a Run Inbox card copies it alone.
# tests/test_w44c_join_followups.py asserts the two patterns are the same string.
NODE_HOST_RE = re.compile(r"[a-z][a-z0-9-]{1,29}[a-z0-9]")
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")   # ids go into URL paths


class IdentityCapError(ApiError):
    """Creating org-node would be the identity that goes over the Free plan's cap."""


def _create_identity(org: Org, name: str) -> str:
    """A machine identity with no org role and Universal Auth; returns its id."""
    made = org.send("POST", "/api/v1/identities",
                    {"name": name, "organizationId": org.org_id, "role": "no-access"})
    new_id = made["identity"]["id"]
    org.send("POST", f"/api/v1/auth/universal-auth/identities/{new_id}",
             {"accessTokenTTL": TOKEN_TTL, "accessTokenMaxTTL": TOKEN_MAX_TTL})
    return new_id


def ensure_node_identity(org: Org) -> str:
    """Id of the `org-node` identity, created when missing (and repaired when half-made):
    Universal Auth attached, viewer on Agents-Core and nothing else. Safe to re-run.
    Never creates an identity past IDENTITY_CAP: raises IdentityCapError naming the ones in use."""
    idents = org.identities()
    iid = idents.get(NODE_IDENTITY)
    if iid is None:
        if len(idents) >= IDENTITY_CAP:
            raise IdentityCapError(
                f"not creating {NODE_IDENTITY}: the org already has {len(idents)} identities "
                f"({', '.join(sorted(idents))}) and Free allows {IDENTITY_CAP}")
        iid = _create_identity(org, NODE_IDENTITY)
    else:
        try:
            org.get(f"/api/v1/auth/universal-auth/identities/{iid}")
        except ApiError as exc:
            if "HTTP 404" not in str(exc):
                raise
            org.send("POST", f"/api/v1/auth/universal-auth/identities/{iid}",
                     {"accessTokenTTL": TOKEN_TTL, "accessTokenMaxTTL": TOKEN_MAX_TTL})
    project = org.projects().get(NODE_PROJECT.lower())
    if project is None:
        raise ApiError(f"project {NODE_PROJECT} does not exist: run `apply` first")
    roles = org.identity_members(project["id"]).get(NODE_IDENTITY)
    if roles is None:
        org.send("POST", f"/api/v1/projects/{project['id']}/identity-memberships/{iid}",
                 {"role": "viewer"})
    elif roles != ["viewer"]:   # its secret goes to every node: never widen, refuse when wider
        raise ApiError(f"{NODE_IDENTITY} has roles {roles} on {NODE_PROJECT}, expected viewer only")
    return iid


def _client_secrets(org: Org, identity_id: str) -> list[dict]:
    out = org.get(f"/api/v1/auth/universal-auth/identities/{identity_id}/client-secrets")
    return [{"description": s.get("description") or "", "id": s.get("id"),
             "created": s.get("createdAt"), "revoked": bool(s.get("isClientSecretRevoked"))}
            for s in out.get("clientSecretData", [])]


def list_node_secrets(org: Org) -> list[dict]:
    """description · id · created · revoked of every client secret under org-node. Never a value."""
    iid = org.identities().get(NODE_IDENTITY)
    return [] if iid is None else _client_secrets(org, iid)


def mint_node_secret(org: Org, host: str) -> dict:
    """A new client secret for `host` under org-node (no ttl, unlimited uses), as
    {client_id, client_secret, client_secret_id}. The value is in this return only: nothing is
    printed or logged, and no error message here carries it. Refuses when a live secret
    described `org-node:<host>` already exists, so a repeat never leaves one nobody can find."""
    if not isinstance(host, str) or not NODE_HOST_RE.fullmatch(host):
        raise ApiError("bad host name for a node secret")
    iid = ensure_node_identity(org)
    desc = f"{NODE_IDENTITY}:{host}"
    live = [s for s in _client_secrets(org, iid) if s["description"] == desc and not s["revoked"]]
    if live:
        raise ApiError(f"a live client secret described {desc!r} already exists "
                       f"(id {live[0]['id']}): revoke it first")
    client_id = org.get(f"/api/v1/auth/universal-auth/identities/{iid}")[
        "identityUniversalAuth"]["clientId"]
    out = org.send("POST", f"/api/v1/auth/universal-auth/identities/{iid}/client-secrets",
                   {"description": desc, "ttl": 0, "numUsesLimit": 0})
    secret = out.get("clientSecret") if isinstance(out, dict) else None
    data = out.get("clientSecretData") if isinstance(out, dict) else None
    sid = data.get("id") if isinstance(data, dict) else None
    if not (isinstance(secret, str) and secret and isinstance(sid, str) and _UUID_RE.fullmatch(sid)):
        # Names only, never the body: it holds the value. A secret may exist now.
        raise ApiError(f"client-secret response had an unexpected shape; check "
                       f"`node-secrets` for a live {desc!r}")
    return {"client_id": client_id, "client_secret": secret, "client_secret_id": sid}


def revoke_node_secret(org: Org, client_secret_id: str) -> None:
    """Revoke ONE client secret of org-node by id. Already revoked or gone counts as done."""
    if not isinstance(client_secret_id, str) or not _UUID_RE.fullmatch(client_secret_id):
        raise ApiError("bad client secret id")
    iid = org.identities().get(NODE_IDENTITY)
    if iid is None:   # no identity, no live secret
        return
    try:
        org.send("POST", f"/api/v1/auth/universal-auth/identities/{iid}"
                         f"/client-secrets/{client_secret_id}/revoke", {})
    except ApiError as exc:
        text = str(exc)
        if "HTTP 404" in text or ("HTTP 400" in text and "revoked" in text.lower()):
            return
        raise


def cmd_node_secrets(org: Org) -> None:
    rows = list_node_secrets(org)
    if not rows:
        print(f"no client secrets under {NODE_IDENTITY}")
    for s in rows:
        print(f"{s['description']} · {s['id']} · created {s['created']} · "
              f"{'REVOKED' if s['revoked'] else 'live'}")


# --- put / last4: one secret in, from stdin only (phase 2, skill CTO_Procedure_KeyFetch) ---------

KINDS = ("API_KEY", "TOKEN", "BOT_TOKEN", "SECRET", "CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN",
         "PASSWORD", "PRIVATE_KEY", "WEBHOOK_SECRET", "URL", "ID")  # PLAN §4b closed list
ACCESS = ("RO", "RW", "ADMIN")
PUBLIC_UNSAFE = ("API_KEY", "TOKEN", "BOT_TOKEN", "SECRET", "CLIENT_SECRET", "REFRESH_TOKEN",
                 "PASSWORD", "PRIVATE_KEY", "WEBHOOK_SECRET")
REQUIRED_META = ("provider_name", "console_url", "scope", "expires", "owner")  # PLAN §4c


def lint_name(name: str) -> str | None:
    """PLAN §4b: <PROVIDER>_[<WHICH>_]<KIND>[_<ACCESS>]. Return the problem, or None when fine."""
    if not re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+", name):
        return "must be UPPER_SNAKE_CASE with at least two parts"
    body = name
    for access in ACCESS:
        if body.endswith("_" + access):
            body = body[: -len(access) - 1]
            break
    kind = next((k for k in sorted(KINDS, key=len, reverse=True)
                 if body.endswith("_" + k) and len(body) > len(k) + 1), None)
    if kind is None:
        return "must end with a KIND (" + " ".join(KINDS) + "), then an optional _RO/_RW/_ADMIN"
    if name.startswith("NEXT_PUBLIC_") and kind in PUBLIC_UNSAFE:
        return "NEXT_PUBLIC_ is shipped to the browser; a secret KIND there is refused"
    return None


def read_stdin_value(multiline: bool) -> str:
    if sys.stdin.isatty():
        sys.exit("pipe the value on stdin (never as an argument, never in a file a model reads)")
    data = sys.stdin.read()
    if multiline:
        data = data.strip("\r\n")
        if not data.strip():
            sys.exit("empty value on stdin")
        return data + "\n"
    data = data.rstrip("\r\n")
    if not data or "\n" in data or "\r" in data or data != data.strip():
        sys.exit("the value must be exactly one non-empty line with no surrounding spaces")
    return data


def _project(org: Org, name: str) -> dict:
    projects = org.projects()
    p = projects.get(name.lower()) or projects.get(name)
    if not p:
        sys.exit(f"no project {name!r}; have: {', '.join(sorted(projects))}")
    return p


def _get_secret(org: Org, project_id: str, env: str, name: str, path: str = "/") -> dict | None:
    try:
        return org.get(f"/api/v3/secrets/raw/{name}", workspaceId=project_id, environment=env,
                       secretPath=path)["secret"]
    except ApiError as exc:
        if "HTTP 404" in str(exc) or "not found" in str(exc).lower():
            return None
        raise


def parse_meta(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        key, sep, val = item.partition("=")
        if not sep or not key.strip() or not val.strip():
            sys.exit(f"bad --meta {item!r}: use key=value")
        out[key.strip()] = val.strip()
    return out


def _target(org: Org, project: str, env: str) -> dict:
    if project.lower() == ORG_INFRA.lower():
        sys.exit("refused: Org-Infra values are entered by the CEO in the web UI (PLAN §3b rule 1)")
    p = _project(org, project)
    if env not in org.environments(p["id"]):
        sys.exit(f"project {p['name']} has no environment {env!r}")
    return p


def _check_name(name: str, legacy: bool) -> bool:
    """Return True when the name is a §4b name, False when it is a tolerated legacy name."""
    problem = lint_name(name)
    if problem and not legacy:
        sys.exit(f"refused: {name}: {problem} (PLAN §4b; --legacy imports an old name 1:1)")
    return problem is None


def _require_meta_for_new(existing: dict | None, comment: str | None, metadata: dict) -> None:
    if existing is None:
        missing = [k for k in REQUIRED_META if k not in metadata]
        if missing or not comment:
            sys.exit("refused: a new secret needs --comment <purpose> and --meta "
                     + " ".join(f"{k}=…" for k in missing) + " (PLAN §4c)")


def _write_secret(org: Org, p: dict, env: str, name: str, value: str, comment: str | None,
                  metadata: dict, existing: dict | None, multiline: bool = False,
                  path: str = "/") -> str:
    """POST or PATCH one secret; the value never leaves this process except in the request."""
    metadata = dict(metadata)
    if existing is not None:
        old = {m["key"]: m["value"] for m in existing.get("secretMetadata") or [] if m.get("key")}
        metadata = {**old, **metadata}
        comment = comment or existing.get("secretComment") or ""
    who = os.environ.get("CTO_SESSION_ID") or os.environ.get("CXO_SESSION_ID") or "cli"
    stamp = f"{dt.date.today().isoformat()} {who}"
    metadata.setdefault("created", stamp)
    metadata["updated"] = stamp
    metadata.setdefault("status", "active")
    body = {"workspaceId": p["id"], "environment": env, "secretPath": path, "secretValue": value,
            "secretComment": comment or "", "skipMultilineEncoding": multiline,
            "secretMetadata": [{"key": k, "value": v} for k, v in metadata.items()]}
    org.send("PATCH" if existing else "POST", f"/api/v3/secrets/raw/{name}", body)
    where = f"{p['name']}/{env}" + ("" if path == "/" else path.rstrip("/"))
    return (f"{'updated' if existing else 'created'} {where} {name}"
            f" · last4={value.strip()[-4:]} · expires={metadata.get('expires', '?')}"
            f" · owner={metadata.get('owner', '?')}")


def cmd_put(org: Org, project: str, env: str, name: str, comment: str | None,
            meta: list[str], multiline: bool, legacy: bool = False, path: str = "/") -> None:
    clean = _check_name(name, legacy)
    p = _target(org, project, env)
    metadata = parse_meta(meta)
    if not clean:
        metadata["naming"] = "legacy"
    existing = _get_secret(org, p["id"], env, name, path)
    _require_meta_for_new(existing, comment, metadata)
    value = read_stdin_value(multiline)   # read last: every refusal above happens before it exists
    print(_write_secret(org, p, env, name, value, comment, metadata, existing, multiline, path))


def parse_env_file(path: str) -> dict[str, str]:
    """KEY=value lines of a .env file (quotes stripped, `export` tolerated). Values stay in memory."""
    values: dict[str, str] = {}
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            if key:
                values[key] = val
    return values


def cmd_import_env(org: Org, project: str, env: str, file: str, only: list[str],
                   comment: str | None, meta: list[str], legacy: bool, path: str = "/") -> None:
    """Phase 2: move a whole .env into Infisical 1:1 — names are printed, values never."""
    values = parse_env_file(file)
    names = [n for n in values if not only or n in only]
    absent = [n for n in only if n not in values]
    if absent:
        sys.exit(f"{file} has no {', '.join(absent)}")
    if not names:
        sys.exit(f"{file}: no KEY=value lines to import")
    p = _target(org, project, env)
    metadata = parse_meta(meta)
    for name in names:
        problem = lint_name(name)
        if problem and not legacy:
            print(f"skip    {name}: {problem} (use --legacy to import it 1:1)")
            continue
        md = dict(metadata)
        if problem:
            md["naming"] = "legacy"
        existing = _get_secret(org, p["id"], env, name, path)
        _require_meta_for_new(existing, comment, md)
        print(_write_secret(org, p, env, name, values[name], comment, md, existing, path=path))


def cmd_last4(org: Org, project: str, env: str, name: str, path: str = "/") -> None:
    p = _project(org, project)
    s = _get_secret(org, p["id"], env, name, path)
    if s is None:
        sys.exit(f"{p['name']}/{env}{'' if path == '/' else path} has no secret {name}")
    print(f"{p['name']}/{env}{'' if path == '/' else path.rstrip('/')} {name}"
          f" · last4={(s.get('secretValue') or '').strip()[-4:]}")


def cmd_run(identity: str, project: str, env: str, argv: list[str], path: str = "/") -> None:
    """Exec a command with the project's secrets in its environment (PLAN §5), nothing on disk.

    `--path /<instance>` picks a folder: two prod instances of one repo (MoonieX and Chatudo both
    run MoonieX-ClaudeFlow) keep different values under the same names, one folder each
    (ruling 2026-09-28, PLAN §3)."""
    if not argv:
        sys.exit("run: give the command after `--`")
    org = Org(identity)
    p = _project(org, project)
    out = org.get("/api/v3/secrets/raw", workspaceId=p["id"], environment=env, secretPath=path)
    secrets = {s["secretKey"]: s["secretValue"] for s in out.get("secrets", []) if s.get("secretKey")}
    where = f"{p['name']}/{env}" + ("" if path == "/" else path.rstrip("/"))
    if not secrets:
        sys.exit(f"{where} holds no secrets — refusing to start {argv[0]} without them")
    print(f"[infisical run] {where} as {identity}: {', '.join(sorted(secrets))} -> {argv[0]}",
          file=sys.stderr)
    os.execvpe(argv[0], argv, {**os.environ, **secrets})


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    command: list[str] = []
    if "--" in argv:                       # `run ... -- <command>`: everything after -- is the command
        cut = argv.index("--")
        argv, command = argv[:cut], argv[cut + 1:]
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
    sub.add_parser("node-secrets")
    for cmd in ("put", "last4", "import-env", "run"):
        c = sub.add_parser(cmd)
        c.add_argument("project")
        c.add_argument("env")
        if cmd in ("put", "last4"):
            c.add_argument("name")
        if cmd == "import-env":
            c.add_argument("file", help=".env file to move 1:1 (names printed, values never)")
            c.add_argument("--only", default="", metavar="A,B", help="import only these names")
        if cmd == "run":
            c.usage = "%(prog)s project env [--as HOST] [--path /folder] -- <command> [args...]"
        c.add_argument("--as", dest="identity", default=self_host() if cmd == "run" else SETUP,
                       help=f"identity whose file under {CRED_DIR} logs in "
                            f"(default: {'this machine' if cmd == 'run' else SETUP})")
        c.add_argument("--path", default="/", metavar="/folder",
                       help="folder inside the environment; one per instance when two prod "
                            "instances of one repo need different values (PLAN §3, 2026-09-28)")
        if cmd in ("put", "import-env"):
            c.add_argument("--comment", help="purpose (PLAN §4c); required when creating")
            c.add_argument("--meta", action="append", default=[], metavar="k=v",
                           help="provider_name, console_url, scope, expires, owner, spend_cap, ...")
            c.add_argument("--legacy", action="store_true",
                           help="import an existing name that fails §4b, 1:1 (renamed in phase 6)")
        if cmd == "put":
            c.add_argument("--stdin", action="store_true", required=True,
                           help="the value comes on stdin — the only way in")
            c.add_argument("--multiline", action="store_true", help="PEM / JSON spanning lines")
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
        elif args.cmd == "node-secrets":
            cmd_node_secrets(Org())
        elif args.cmd == "put":
            cmd_put(Org(args.identity), args.project, args.env, args.name, args.comment,
                    args.meta, args.multiline, legacy=args.legacy, path=args.path)
        elif args.cmd == "import-env":
            only = [n for n in args.only.split(",") if n]
            cmd_import_env(Org(args.identity), args.project, args.env, args.file, only,
                           args.comment, args.meta, args.legacy, path=args.path)
        elif args.cmd == "last4":
            cmd_last4(Org(args.identity), args.project, args.env, args.name, path=args.path)
        elif args.cmd == "run":
            cmd_run(args.identity, args.project, args.env, command, path=args.path)
    except ApiError as exc:
        sys.exit(f"Infisical API error: {exc}")
    except FileNotFoundError as exc:
        sys.exit(f"missing credentials: {exc.filename} (run `save {SETUP}` first)")


if __name__ == "__main__":
    main()
