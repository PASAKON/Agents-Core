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
                           --scope user (Windows only, option B): save under
                           %LOCALAPPDATA%\\MoonieX\\Infisical, ACL'd to this user, for a node where
                           nothing runs elevated; read_cred falls back to it.
    plan                   Show what `apply` would create or change. Read-only.
    apply [--mint HOST]    Create what is missing: the projects, their environments, the Org-Infra
                           folders, the machine identities with read-only project memberships and
                           the CEO as admin of every project. --mint also creates a client secret
                           for HOST and saves it here as /etc/infisical/HOST.env. Safe to re-run.
    status                 Print what exists now.
    retire-setup           Delete the temporary `setup` identity and its file (end of migration).
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
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("INFISICAL_API_URL", "https://app.infisical.com")
_DEFAULT_CRED_DIR = (os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "Infisical")
                     if os.name == "nt" else "/etc/infisical")   # PLAN §5: root-only, one file per host
CRED_DIR = os.environ.get("INFISICAL_CRED_DIR", _DEFAULT_CRED_DIR)  # override only in tests
# Option B (CEO 2026-10-02): on winbox nothing runs elevated (UAC on: Claude, the Run executor, every
# scheduled task), so an Administrators-only file is unreadable by every consumer. `save --scope user`
# keeps the file under the user's profile instead, ACL'd to that user + SYSTEM + Administrators, and
# read_cred falls back to it when the machine file is missing or unreadable. Windows only; off when
# INFISICAL_CRED_DIR points somewhere else (tests).
_DEFAULT_USER_CRED_DIR = (os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local"),
                                       "MoonieX", "Infisical")
                          if os.name == "nt" and "INFISICAL_CRED_DIR" not in os.environ else None)
USER_CRED_DIR = os.environ.get("INFISICAL_USER_CRED_DIR", _DEFAULT_USER_CRED_DIR)
SETUP = "setup"
SETUP_MAX_DAYS = 14  # the admin identity lives only for the migration (PLAN §6)

# W4.6c F2: the one project a node's token comes from. `contabo` is a viewer HERE (the hub reads it
# to serve the token, tools/node_token_api.py) and no node is a member: nodes have no identity
# (CEO 2026-10-03). Its content is exactly NODE_SECRET_NAMES; the CEO enters the value (gate G3) and
# no code here writes it. On Free a viewer sees every environment and there are no folder
# permissions, so the project holds these names and nothing else (`put` and `import-env` refuse more).
NODE_PROJECT = "Org-Node"
NODE_SECRET_NAMES = ("CLAUDE_CODE_OAUTH_TOKEN",)
# Infisical Free: 5 identities, and the org's USER accounts count against the same 5 (found by
# drill run 5, 2026-10-03: the CEO's account is the fifth with contabo, mac, winbox and setup).
IDENTITY_CAP = 5

# PLAN.md §3: project -> environments. Org-Infra has prod only (§3b).
PROJECTS: dict[str, list[str]] = {
    "Agents-Core": ["dev", "prod"],
    "Org-Infra": ["prod"],
    NODE_PROJECT: ["prod"],   # the token the hub hands to approved nodes (W4.6c F2), see NODE_PROJECT
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
# W4.6c F3: the hub's public join endpoint reads ONLY this folder of Agents-Core prod
# (ORG_JOIN_DB_URL, the DSN of the Postgres role `org_join`), never the whole project.
ORG_JOIN_FOLDER = "org-join"
# W4.2b: the hub's node-token service reads ONLY this folder of Agents-Core prod
# (ORG_NODE_TOKEN_DB_URL, the DSN of the Postgres role `org_node_token`).
NODE_TOKEN_FOLDER = "node-token"
# project -> folders `apply` creates in its prod environment (none of these hold a value yet)
PROJECT_FOLDERS: dict[str, list[str]] = {
    ORG_INFRA: ORG_INFRA_FOLDERS,
    "Agents-Core": [ORG_JOIN_FOLDER, NODE_TOKEN_FOLDER],
}

# PLAN.md §3: machine identity -> projects it may read (viewer). On Free a viewer sees every
# environment of the project, so MoonieX-WebApp is not given to the Mac until local dev needs it.
MACHINES: dict[str, list[str]] = {
    # NODE_PROJECT: the hub reads the node token there and hands it to approved nodes (CEO 2026-10-03).
    "contabo": ["Agents-Core", "MoonieX-ClaudeFlow", "MoonieX-Option", "MoonieX-AlphaTrader",
                "MoonieX-LineAutomation", "MoonieX-Console", "LungNote-MCP", NODE_PROJECT],
    "mac": ["Agents-Core", ORG_INFRA, "MoonieX-Console", "MoonieX-ComfyRunpod", "LungNote-MCP"],
    # Agents-Core back for W3.4 (CEO approval 2026-10-03): winbox reads ORG_DB_URL through
    # `run Agents-Core prod --as winbox`, never an org-db.env. Option = IQ demo trader (CEO 2026-10-01)
    "winbox": ["Agents-Core", "MoonieX-Console", "MoonieX-CookierunBot", "LungNote-MCP", "MoonieX-Option"],
}
TOKEN_TTL = 86_400            # an access token lives a day...
TOKEN_MAX_TTL = 7 * 86_400    # ...and cannot be renewed past a week
MACHINE_SECRET_TTL = 365 * 86_400  # the machine's client secret: rotate yearly (radar, phase 5)

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")


class ApiError(RuntimeError):
    pass


def _error_text(method: str, path: str, code: int, body: str) -> str:
    """The text of an ApiError. Infisical answers with JSON {reqId, statusCode, message, error};
    the text leads with that `message` and then the `reqId` (the number Infisical support asks
    for), then the request line. A body that is not such JSON stays as it was: the first 300
    characters, after the request line. Never longer than ~400 characters either way."""
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = None
    msg = parsed.get("message") if isinstance(parsed, dict) else None
    if msg is None or msg == "":
        return f"{method} {path} -> HTTP {code}: {body[:300]}"
    if not isinstance(msg, str):   # a validation error carries a list or an object
        msg = json.dumps(msg, ensure_ascii=False)
    rid = parsed.get("reqId")
    tail = f" (reqId {str(rid)[:64]})" if isinstance(rid, (str, int)) and rid != "" else ""
    return f"{msg[:300]}{tail}: {method} {path} -> HTTP {code}"


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
            raise ApiError(_error_text(method, path, exc.code,
                                       exc.read().decode(errors="replace"))) from None
    raise ApiError(f"{method} {path} -> still rate-limited after retries")


# --- credentials ----------------------------------------------------------------------------

def cred_path(name: str) -> str:
    return os.path.join(CRED_DIR, f"{name}.env")


def user_cred_path(name: str) -> str | None:
    """The user-scoped file of option B, or None where there is none: not Windows, or CRED_DIR
    moved away from the default (a test), so a test can never fall back to a real credential."""
    if not (_is_nt() and USER_CRED_DIR and CRED_DIR == _DEFAULT_CRED_DIR):
        return None
    return os.path.join(USER_CRED_DIR, f"{name}.env")


def read_cred(name: str) -> tuple[str, str]:
    values = {}
    try:
        fh = open(cred_path(name))
    except (FileNotFoundError, PermissionError):
        user = user_cred_path(name)
        if not user or not os.path.exists(user):
            raise
        fh = open(user)
    with fh:
        for line in fh:
            key, _, val = line.strip().partition("=")
            values[key] = val
    return (values["INFISICAL_UNIVERSAL_AUTH_CLIENT_ID"],
            values["INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET"])


class AclError(OSError):
    """icacls refused, or could not run: the credentials were not saved."""


def _is_nt() -> bool:
    return os.name == "nt"


def _run_icacls(argv: list) -> int:
    """Return code of an icacls run. argv is a list and there is no shell."""
    return subprocess.run(argv, capture_output=True, timeout=30, check=False).returncode


def current_user_sid(run=None) -> str:
    """SID of the account this process runs as (`whoami /user`), for option B's ACL.
    `run(argv) -> stdout` is injectable for tests."""
    def _whoami(argv: list) -> str:
        return subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False).stdout
    try:
        out = (run or _whoami)(["whoami", "/user", "/fo", "csv", "/nh"])
    except (OSError, subprocess.SubprocessError) as exc:
        raise AclError(f"whoami could not run ({type(exc).__name__})") from None
    sid = out.strip().rsplit(",", 1)[-1].strip().strip('"')
    if not re.fullmatch(r"S-1-[0-9-]+", sid):
        raise AclError("whoami did not return a SID")
    return sid


def lock_acl(path: str, run=None, user_sid: str | None = None) -> None:
    """Windows only (W4.6a F5): drop the ACL entries `path` inherits (ProgramData gives
    BUILTIN\\Users read and execute) and leave SYSTEM and Administrators, plus `user_sid` for
    option B's user-scoped file. os.chmod and the 0o600 of os.open set no ACL on nt. Fails
    closed: a non-zero exit, or icacls missing, raises AclError. `run(argv) -> returncode` is
    injectable for tests. A no-op elsewhere."""
    if not _is_nt():
        return
    argv = ["icacls", path, "/inheritance:r", "/grant:r", "SYSTEM:F", "Administrators:F"]
    if user_sid:
        argv.append(f"*{user_sid}:F")
    try:
        rc = (run or _run_icacls)(argv)
    except (OSError, subprocess.SubprocessError) as exc:
        raise AclError(f"icacls could not run on {path} ({type(exc).__name__})") from None
    if rc != 0:
        raise AclError(f"icacls exited {rc} on {path}")


def write_cred(name: str, client_id: str, client_secret: str, *, run=None,
               scope: str = "machine", user_sid: str | None = None) -> str:
    if scope == "user":
        path = user_cred_path(name)
        if not path:
            raise AclError("--scope user is for Windows nodes only (option B)")
        cdir = USER_CRED_DIR
        user_sid = user_sid or current_user_sid()
    else:
        require_root()
        cdir, path, user_sid = CRED_DIR, cred_path(name), None
    os.makedirs(cdir, mode=0o700, exist_ok=True)
    os.chmod(cdir, 0o700)
    lock_acl(cdir, run, user_sid)    # the directory first, before a secret exists anywhere in it
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(f"INFISICAL_API_URL={API}\n"
                 f"INFISICAL_UNIVERSAL_AUTH_CLIENT_ID={client_id}\n"
                 f"INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET={client_secret}\n")
    try:
        lock_acl(path + ".tmp", run, user_sid)
    except AclError:
        os.unlink(path + ".tmp")   # fail closed: no secret-bearing file is left behind
        raise
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

def cmd_save(name: str, from_stdin: bool = False, scope: str = "machine") -> None:
    if not NAME_RE.match(name):
        sys.exit(f"bad identity name: {name!r}")
    if scope == "user" and not user_cred_path(name):
        sys.exit("--scope user is for Windows nodes only (option B); nothing saved")
    if scope != "user":
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
    try:
        path = write_cred(name, client_id, client_secret, scope=scope)
    except AclError as exc:
        sys.exit(f"{exc}; nothing saved")
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

    def org_users(self) -> list[str]:
        """Every user that holds a seat: active members by username, invited ones by the address
        they were invited at. Sorted. Infisical Free counts them with the identities (IDENTITY_CAP)."""
        out = self.get(f"/api/v2/organizations/{self.org_id}/memberships")
        names = {(u.get("user") or {}).get("username") or u.get("inviteEmail")
                 for u in out.get("users", [])}
        return sorted(n for n in names if n)

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

    for project_name, wanted in PROJECT_FOLDERS.items():
        if project_name not in project_ids:
            continue
        pid = project_ids[project_name]
        have = org.folders(pid, "prod")
        for folder in wanted:
            if folder not in have:
                act(f"+ {project_name}: folder /{folder}", lambda f=folder, p=pid: org.send(
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
            refused = None
            if dry:   # a live run raises inside _create_identity; a dry one says so and goes on
                try:
                    check_identity_room(org, idents)
                except IdentityCapError as exc:
                    refused = exc
            if refused:
                log.append(f"! would refuse identity {host}: {refused}")
                print(log[-1])
            else:
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


# --- nodes: no identity of their own (CEO ruling 2026-10-03, Org Mesh W4.2b) ------------------------
# Infisical Free allows IDENTITY_CAP identities and the CEO's own user account counts as one of them.
# With contabo, mac, winbox and setup the org is full, so a node cannot have an identity, and there
# is no shared `org-node` identity either (drill run 5: POST /api/v1/identities -> HTTP 400). The hub
# reads NODE_PROJECT through `contabo` and hands the token to a node it has approved
# (tools/node_token_api.py); a node never logs in to Infisical. Nothing here mints or revokes a
# node credential. NODE_PROJECT is declared above, next to PROJECTS.

# The host-name rule, 3-31 chars: a copy of lib.config.HOST_NAME_RE (tools/hq_join.HOST_RE is that
# same object). Not imported: this file stays stdlib-only, a Run Inbox card copies it alone.
# tests/test_w44c_join_followups.py asserts the two patterns are the same string.
NODE_HOST_RE = re.compile(r"[a-z][a-z0-9-]{1,29}[a-z0-9]")
# "org-node" stays a name no host may take (tools/hq_join.reserved_hosts). No identity of that
# name exists or is created any more; it was the name of the shared one, and a join must not land
# on a name an operator may still know it by.
NODE_IDENTITY = "org-node"


class IdentityCapError(ApiError):
    """Creating another identity would go over the Free plan's seat cap."""


def seat_holders(org: Org, idents: dict[str, str] | None = None) -> tuple[list[str], list[str]]:
    """(identity names, user names) that hold the org's seats, each sorted. Infisical Free counts
    both against the same cap. A user that was invited and has not accepted yet is listed by the
    address it was invited at: refusing early costs a look, creating one too many costs a 400."""
    idents = org.identities() if idents is None else idents
    return sorted(idents), org.org_users()


def check_identity_room(org: Org, idents: dict[str, str] | None = None) -> None:
    """Raise IdentityCapError, naming every identity and user, when one more identity would not
    fit. Reads only; called BEFORE the POST that would create it, so the refusal is ours and says
    who holds the seats, not Infisical's bare HTTP 400."""
    names, users = seat_holders(org, idents)
    if len(names) + len(users) >= IDENTITY_CAP:
        raise IdentityCapError(
            f"not creating an identity: the org already holds {len(names) + len(users)} of "
            f"{IDENTITY_CAP} seats on Free (identities: {', '.join(names) or 'none'}; "
            f"users: {', '.join(users) or 'none'})")


def _create_identity(org: Org, name: str) -> str:
    """A machine identity with no org role and Universal Auth; returns its id. Refuses first,
    with IdentityCapError, when the org has no seat left."""
    check_identity_room(org)
    made = org.send("POST", "/api/v1/identities",
                    {"name": name, "organizationId": org.org_id, "role": "no-access"})
    new_id = made["identity"]["id"]
    org.send("POST", f"/api/v1/auth/universal-auth/identities/{new_id}",
             {"accessTokenTTL": TOKEN_TTL, "accessTokenMaxTTL": TOKEN_MAX_TTL})
    return new_id


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


def _node_project_guard(project: str, name: str | None, path: str) -> None:
    """Org-Node holds NODE_SECRET_NAMES at `/` and nothing else (W4.6c F2): every joined node
    reads the whole project, so a second name is a second secret on every node. `name` None is
    a bulk import, always refused."""
    if project.lower() != NODE_PROJECT.lower():
        return
    if name not in NODE_SECRET_NAMES or path != "/":
        sys.exit(f"refused: {NODE_PROJECT} holds only {', '.join(NODE_SECRET_NAMES)} at / "
                 f"(every joined node reads all of it); nothing else goes there")


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
    _node_project_guard(project, name, path)
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
    _node_project_guard(project, None, path)      # first: a refused import opens no file
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


EXIT_NO_SECRETS = 2


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
        # Exit 2, not sys.exit(message)'s 1: an empty folder is a standing condition, not a blip, and a
        # unit that lists 2 in RestartPreventExitStatus= (org-node-token.service) must not retry it.
        print(f"{where} holds no secrets — refusing to start {argv[0]} without them", file=sys.stderr)
        sys.exit(EXIT_NO_SECRETS)
    print(f"[infisical run] {where} as {identity}: {', '.join(sorted(secrets))} -> {argv[0]}",
          file=sys.stderr)
    child_env = {**os.environ, **secrets}
    if _is_nt():
        # os.exec* on Windows starts a NEW process and ends this one at once (CRT _execvpe), so a
        # supervisor (winbox-trader.ps1's wait, -Loop, taskkill /T) would lose the real program.
        # Wait for it as a child instead and hand back its exit code.
        exe = shutil.which(argv[0], path=child_env.get("PATH")) or argv[0]
        try:
            rc = subprocess.call([exe, *argv[1:]], env=child_env)
        except KeyboardInterrupt:
            rc = 130
        sys.exit(rc)
    os.execvpe(argv[0], argv, child_env)


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
    s.add_argument("--scope", choices=("machine", "user"), default="machine",
                   help="user: Windows only, the file goes under %%LOCALAPPDATA%%\\MoonieX\\Infisical "
                        "for nodes where nothing runs elevated (option B, CEO 2026-10-02)")
    sub.add_parser("plan")
    a = sub.add_parser("apply")
    a.add_argument("--mint", metavar="HOST")
    sub.add_parser("status")
    sub.add_parser("retire-setup")
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
            cmd_save(args.identity, from_stdin=args.stdin, scope=args.scope)
        elif args.cmd == "plan":
            reconcile(Org(), dry=True, mint=None)
        elif args.cmd == "apply":
            reconcile(Org(), dry=False, mint=args.mint)
        elif args.cmd == "status":
            cmd_status(Org())
        elif args.cmd == "retire-setup":
            cmd_retire_setup(Org())
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
