#!/usr/bin/env python3
"""Create or refresh the hub role `org_node_token` and print its URL on stdout (Org Mesh W4.2b).

    infisical_setup.py run Agents-Core prod --as <id> -- .venv/bin/python deploy/node-token/org_node_token_role.py \\
      | infisical_setup.py put Agents-Core prod ORG_NODE_TOKEN_DB_URL --path /node-token --stdin ...

deploy/node-token/README.md, card 4 (role and DSN put are one line), has the whole line. Same recipe as
deploy/join/org_join_role.py, for the role that may only read four columns of `hosts`:

1. Reads the hub URL of the connecting role (`ORG_DB_URL`, put in the environment by
   `infisical_setup.py run`), and makes a fresh password in memory.
2. Computes the SCRAM-SHA-256 verifier of that password here (scram_verifier) and runs
   `org_node_token_role.sql` with psql, handing it the VERIFIER (ORG_NODE_TOKEN_VERIFIER), never the
   password. `CREATE ROLE ... PASSWORD '<password>'` is a statement the server may log (log_statement,
   an error message, pg_stat_statements); `PASSWORD 'SCRAM-SHA-256$...'` is a one-way hash that
   Postgres stores as given. The connection comes from PG* variables, so nothing secret is on a
   command line (`ps` shows argv).
3. Only when psql succeeded, prints ONE line on stdout: the URL of `org_node_token` (same host,
   port, database and query as the connecting URL; this is the only place the password appears).
   Everything else, psql's output included, goes to stderr, with the password and the verifier
   replaced by `***` in case a server message echoed a statement.

When anything fails, stdout stays empty, so `put` refuses the empty value and nothing is stored.
Running it again rotates the password and re-applies the grants. stdlib only.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

SQL = Path(__file__).resolve().with_name("org_node_token_role.sql")
ROLE = "org_node_token"
PSQL_ENV = "ORG_NODE_TOKEN_PSQL"   # tests only: the psql executable
VERIFIER_ENV = "ORG_NODE_TOKEN_VERIFIER"
SCRAM_ITERATIONS = 4096            # Postgres's own default for scram_iterations
SCRAM_SALT_BYTES = 16


def _fail(message: str, code: int = 2) -> int:
    print(f"org_node_token_role: {message}", file=sys.stderr)
    return code


def scram_verifier(password: str, *, salt: bytes | None = None, iterations: int = SCRAM_ITERATIONS) -> str:
    """The SCRAM-SHA-256 verifier Postgres stores in pg_authid.rolpassword (RFC 5802 / 7677):

        SCRAM-SHA-256$<iterations>:<salt, base64>$<StoredKey, base64>:<ServerKey, base64>

    Given a string in this form as a role's PASSWORD, Postgres keeps it as it is; a client then logs
    in with the plain password. No SASLprep step: the password this script makes is [A-Za-z0-9_-],
    on which SASLprep is the identity."""
    salt = secrets.token_bytes(SCRAM_SALT_BYTES) if salt is None else salt
    salted = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    b64 = lambda raw: base64.b64encode(raw).decode("ascii")  # noqa: E731
    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored_key)}:{b64(server_key)}"


def role_url(parts, password: str) -> str:
    """The URL of ROLE: `parts` (urlsplit of the connecting URL) with the user and password swapped."""
    host = parts.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port else ""
    query = f"?{parts.query}" if parts.query else ""
    return f"{parts.scheme}://{ROLE}:{password}@{host}{port}{parts.path}{query}"


def main(argv: list[str] | None = None, environ=None) -> int:
    env = dict(os.environ if environ is None else environ)
    if argv:
        return _fail("takes no arguments (the connecting URL is ORG_DB_URL in the environment)")
    url = (env.get("ORG_DB_URL") or "").strip()
    if not url:
        return _fail("ORG_DB_URL is not set: run this under `infisical_setup.py run Agents-Core prod`")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return _fail("ORG_DB_URL is not a URL")
    if parts.scheme not in ("postgresql", "postgres") or not parts.hostname or not parts.username \
            or not parts.path.strip("/"):
        return _fail("ORG_DB_URL must look like postgresql://user:password@host:port/database")
    psql = shutil.which(env.get(PSQL_ENV) or "psql")
    if psql is None:
        return _fail("psql is not installed on this machine (command -v psql)")

    password = secrets.token_urlsafe(32)   # 43 characters of [A-Za-z0-9_-]: URL-safe, no quoting
    verifier = scram_verifier(password)
    # no inherited PG* setting, and no plain password variable that a caller's shell may have left
    child = {k: v for k, v in env.items()
             if not k.startswith("PG") and k not in ("ORG_DB_URL", "ORG_NODE_TOKEN_PASSWORD")}
    child.update(PGHOST=parts.hostname, PGUSER=unquote(parts.username),
                 PGDATABASE=unquote(parts.path.lstrip("/")), PGCONNECT_TIMEOUT="10",
                 **{VERIFIER_ENV: verifier})
    if port:
        child["PGPORT"] = str(port)
    if parts.password:
        child["PGPASSWORD"] = unquote(parts.password)
    sslmode = parse_qs(parts.query).get("sslmode")
    if sslmode:
        child["PGSSLMODE"] = sslmode[-1]

    done = subprocess.run([psql, "-X", "-v", "ON_ERROR_STOP=1", "-f", str(SQL)], env=child,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
    for line in (done.stdout + done.stderr).splitlines():
        print(line.replace(password, "***").replace(verifier, "***"), file=sys.stderr)
    if done.returncode != 0:
        return _fail(f"psql exited {done.returncode}: the role was not (fully) set up; "
                     "nothing is printed and nothing should be stored", 1)
    print(role_url(parts, password))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
