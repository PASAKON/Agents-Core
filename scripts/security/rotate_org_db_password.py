#!/usr/bin/env python3
"""Apply the new password of the hub role `org` that the CEO put in Infisical (order
O-20261027-1347-4e62, CEO Q-20261026-1057-1569: the hub URL leaked into a transcript on 26 Oct).

The CEO sets the new URL in Infisical Agents-Core/prod `ORG_DB_URL`, then taps one Run card on
Contabo that runs scripts/security/rotate-org-db-password.sh, which runs this file under
`infisical_setup.py run Agents-Core prod --as contabo`, so the new URL exists only in this
process's environment:

    check   steps 1-2, read-only (the rehearsal card)
    apply   steps 1-6

1. Parse ORG_DB_URL. Refuse unless the user is `org` and host, port and database are the hub's:
   the host is Contabo's tailnet address from config/hosts.yaml (hosts.contabo.mesh_ssh), the
   port and database the ones scripts/hub/contabo-postgres-up.sh publishes.
2. Connect with that URL. If it already logs in, Infisical still holds a working password (or the
   rotation already ran): refuse, exit 3, nothing changed. Anything but a password failure (hub
   down, timeout) refuses too, exit 4: then nothing proves the old password is gone.
3. Compute the SCRAM-SHA-256 verifier of the new password here (RFC 5802 / 7677), so the plain
   password never reaches the server, its logs or psql.
4. `docker exec -i -e NEWVERIFIER org-postgres psql -U org -d org` over the container's local
   socket (superuser `org`, no `postgres` role: config/machine-contract.yaml, scripts/contabo_restore.sh).
   The verifier passes by NAME on the command line and by value only in docker's environment;
   the SQL on stdin turns statement and error logging off for the session, reads it with \\getenv
   and runs ALTER ROLE org PASSWORD :'v'.
5. Log in with the new URL and SELECT 1. Then drop the stale secret lines (POSTGRES_PASSWORD,
   ORG_DB_URL, ORG_TEST_DB_URL) from the hub env file (MOONIEX_ORG_DB_ENV, default
   ~/.config/mooniex/org-db.env), atomically and 0600; the new password is never written to it.
6. Print, by name only, the services and sessions that still hold the old URL.

The password, the verifier and the URL never reach stdout, stderr, argv, a file or an exception
message: every failure prints its exception CLASS only, and psql's output is filtered.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
HOSTS_YAML = ROOT / "config" / "hosts.yaml"
ROLE = "org"
SCRAM_ITERATIONS = 4096            # Postgres's own default for scram_iterations
SCRAM_SALT_BYTES = 16
MIN_PASSWORD_LEN = 16
CONNECT_TIMEOUT = 3
VERIFIER_ENV = "NEWVERIFIER"
ENV_FILE_DEFAULT = Path.home() / ".config" / "mooniex" / "org-db.env"
STALE_KEYS = ("POSTGRES_PASSWORD", "ORG_DB_URL", "ORG_TEST_DB_URL")
UNIT_DIR = Path("/etc/systemd/system")
UNIT_PATTERNS = ("infisical_setup.py run Agents-Core prod", "with-org-db-env.sh", "org-python.sh")
# password failure: SQLSTATE 28P01 invalid_password / 28000 invalid_authorization_specification
AUTH_SQLSTATES = ("28P01", "28000")

# Stdin of psql in the container. -X skips psqlrc. The SETs keep the statement (it carries the
# verifier once psql substitutes :'v') out of the server log, an error's STATEMENT line and
# pg_stat_statements; `org` is a superuser, so it may set all four. VERBOSITY terse and
# SHOW_CONTEXT never keep psql from echoing the statement text back with an error.
APPLY_SQL = f"""\\set ON_ERROR_STOP on
\\set VERBOSITY terse
\\set SHOW_CONTEXT never
SET log_statement = 'none';
SET log_min_error_statement = 'panic';
SET log_min_duration_statement = -1;
SET pg_stat_statements.track_utility = off;
\\getenv v {VERIFIER_ENV}
ALTER ROLE {ROLE} PASSWORD :'v';
"""

VERIFIER_RE = re.compile(r"^SCRAM-SHA-256\$4096:[A-Za-z0-9+/]{22}==\$[A-Za-z0-9+/]{43}=:[A-Za-z0-9+/]{43}=$")


class Refused(Exception):
    """A refusal whose message is written here and never carries a secret."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


def say(line: str) -> None:
    print(line, flush=True)


def load_hub(hosts_yaml: Path = HOSTS_YAML) -> dict:
    """The hub's address: Contabo's tailnet address (hosts.contabo.mesh_ssh, `user@<address>`, the
    address org-postgres is published on) and the port, database, container and superuser that
    scripts/hub/contabo-postgres-up.sh creates."""
    import yaml

    data = yaml.safe_load(hosts_yaml.read_text(encoding="utf-8"))
    mesh = str(((data.get("hosts") or {}).get("contabo") or {}).get("mesh_ssh") or "")
    host = mesh.rpartition("@")[2].strip()
    if not host:
        raise Refused("config/hosts.yaml has no hosts.contabo.mesh_ssh: cannot tell the hub's address")
    return {"host": host, "port": 5432, "database": "org", "container": "org-postgres", "superuser": "org"}


def parse_url(url: str, hub: dict) -> dict:
    """Step 1. The parts of ORG_DB_URL, or Refused. Messages name fields, never values."""
    if not url:
        raise Refused("ORG_DB_URL is not set: run this through scripts/security/rotate-org-db-password.sh")
    try:
        parts = urlsplit(url)
        port = parts.port or 5432
        user = unquote(parts.username or "")
        password = unquote(parts.password or "")
        host = parts.hostname or ""
        database = unquote(parts.path.lstrip("/"))
    except Exception:  # noqa: BLE001 - a ValueError's text may quote the URL
        raise Refused("ORG_DB_URL is not a URL") from None
    if parts.scheme not in ("postgresql", "postgres"):
        raise Refused("ORG_DB_URL must start postgresql://")
    if user != ROLE:
        raise Refused(f"ORG_DB_URL's user is not `{ROLE}`: this card rotates only the hub role {ROLE}")
    if host != hub["host"] or port != hub["port"] or database != hub["database"]:
        raise Refused("ORG_DB_URL's host, port or database is not the hub's (config/hosts.yaml "
                      "hosts.contabo.mesh_ssh, port 5432, database org)")
    if len(password) < MIN_PASSWORD_LEN:
        raise Refused(f"the password in ORG_DB_URL is empty or shorter than {MIN_PASSWORD_LEN} characters")
    # Printable ASCII only: SASLprep (RFC 4013), which libpq applies at login, is the identity on
    # it, so the verifier computed here matches what the client proves.
    if any(not (0x20 <= ord(ch) <= 0x7E) for ch in password):
        raise Refused("the password in ORG_DB_URL has a character outside printable ASCII")
    return {"url": url, "user": user, "password": password, "host": host, "port": port,
            "database": database}


def _connect(url: str):
    import psycopg

    return psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT)


def is_auth_failure(exc: BaseException) -> bool:
    """True when the server answered and refused the password (read here, never printed)."""
    if getattr(exc, "sqlstate", None) in AUTH_SQLSTATES:
        return True
    try:
        text = str(exc)
    except Exception:  # noqa: BLE001
        return False
    return "password authentication failed" in text


def probe(url: str, connect=_connect, *, select: bool = False) -> str:
    """Steps 2 and 5: 'works', 'auth_failed' or 'error:<class>'. With select, 'works' also means
    SELECT 1 returned 1. Never raises, never returns text that came from an exception."""
    try:
        conn = connect(url)
    except Exception as exc:  # noqa: BLE001
        return "auth_failed" if is_auth_failure(exc) else f"error:{type(exc).__name__}"
    try:
        if select and conn.execute("SELECT 1").fetchone()[0] != 1:
            return "error:SelectMismatch"
    except Exception as exc:  # noqa: BLE001
        return f"error:{type(exc).__name__}"
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass
    return "works"


def scram_verifier(password: str, *, salt: bytes | None = None, iterations: int = SCRAM_ITERATIONS) -> str:
    """The SCRAM-SHA-256 verifier Postgres stores in pg_authid.rolpassword (RFC 5802 / 7677):

        SCRAM-SHA-256$<iterations>:<salt, base64>$<StoredKey, base64>:<ServerKey, base64>

    Postgres keeps a PASSWORD in this form as it is. Same recipe as
    deploy/coo-gate/org_coo_role.py, copied rather than imported."""
    salt = secrets.token_bytes(SCRAM_SALT_BYTES) if salt is None else salt
    salted = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    b64 = lambda raw: base64.b64encode(raw).decode("ascii")  # noqa: E731
    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored_key)}:{b64(server_key)}"


def docker_env(environ: dict, verifier: str) -> dict:
    """The docker CLI's environment: what docker needs, plus the verifier. No *_DB_URL, no PG*."""
    keep = ("PATH", "HOME", "DOCKER_HOST", "DOCKER_CONFIG", "DOCKER_CONTEXT", "DOCKER_CERT_PATH",
            "DOCKER_TLS_VERIFY", "LANG", "LC_ALL")
    child = {k: environ[k] for k in keep if k in environ}
    child.setdefault("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
    child[VERIFIER_ENV] = verifier
    return child


def apply_verifier(hub: dict, verifier: str, environ: dict, run=subprocess.run) -> tuple[int, list[str]]:
    """Step 4: ALTER ROLE through psql inside the hub container. Returns psql's exit code and its
    output lines with every SCRAM string dropped (the caller scrubs the password too)."""
    argv = ["docker", "exec", "-i", "-e", VERIFIER_ENV, hub["container"],
            "psql", "-X", "-q", "-U", hub["superuser"], "-d", hub["database"], "-v", "ON_ERROR_STOP=1"]
    try:
        done = run(argv, input=APPLY_SQL, env=docker_env(environ, verifier),
                   capture_output=True, text=True, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return 127, [f"docker exec did not run ({type(exc).__name__})"]
    lines = []
    for line in f"{done.stdout or ''}\n{done.stderr or ''}".splitlines():
        if not line.strip():
            continue
        lines.append("[a line naming a SCRAM string was dropped]" if ("SCRAM" in line or verifier in line)
                     else line)
    return done.returncode, lines


def scrub_env_file(path: Path) -> list[str]:
    """Drop every STALE_KEYS line from the hub env file, atomically, keeping it 0600. Returns the key
    names dropped. The new password is never written: the role's password lives only in Infisical
    (CLAUDE.md §Secrets: no .env is extended). A missing file drops nothing."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    dropped, kept = [], []
    for line in text.splitlines(keepends=True):
        key = line.strip()
        if key.startswith("export "):
            key = key[len("export "):].lstrip()
        key = key.partition("=")[0].strip()
        if "=" in line and key in STALE_KEYS:
            dropped.append(key)
            kept.append(f"# {key} removed 2026-10-27 by scripts/security/rotate_org_db_password.py: "
                        "the hub password lives only in Infisical Agents-Core/prod ORG_DB_URL\n")
        else:
            kept.append(line)
    if not dropped:
        return []
    tmp = path.with_name(f".{path.name}.rotate-{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("".join(kept))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.chmod(path, 0o600)
    return dropped


def env_file_keys(path: Path) -> list[str]:
    """The STALE_KEYS a file assigns, by name (for `check`)."""
    if not path.is_file():
        return []
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        key = line.strip()
        if key.startswith("export "):
            key = key[len("export "):].lstrip()
        key = key.partition("=")[0].strip()
        if "=" in line and key in STALE_KEYS and key not in found:
            found.append(key)
    return found


def stale_test_url(environ: dict, new: dict) -> bool:
    """True when ORG_TEST_DB_URL logs in as `org` with a different password than the new one
    (role passwords are per cluster, so it shares the role's password and breaks with it)."""
    raw = (environ.get("ORG_TEST_DB_URL") or "").strip()
    if not raw:
        return False
    try:
        parts = urlsplit(raw)
        return unquote(parts.username or "") == ROLE and unquote(parts.password or "") != new["password"]
    except Exception:  # noqa: BLE001
        return True


def holders(unit_dir: Path = UNIT_DIR) -> list[str]:
    """Step 6: units on this host that start with the hub URL in their environment (the unit
    file or a drop-in names one of UNIT_PATTERNS). Unit names only."""
    found = set()
    if not unit_dir.is_dir():
        return []
    for path in sorted(unit_dir.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if not (path.suffix in (".service", ".conf")):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(p in text for p in UNIT_PATTERNS):
            unit = path.name if path.suffix == ".service" else path.parent.name.removesuffix(".d")
            found.add(unit)
    return sorted(found)


def next_steps(unit_dir: Path) -> None:
    units = holders(unit_dir)
    say("NEXT (names only): these hold the OLD hub URL until they restart:")
    say(f"  services on this host ({len(units)}, from {unit_dir}): {', '.join(units) or 'none found'}")
    say("    timer-run oneshots pick the new URL up at their next run; the long-running ones need a restart")
    say("  every tmux session on this host whose org MCP server started before now (SafeRestart)")
    say("  winbox sessions (infisical run Agents-Core prod --as winbox): restart them")
    say("  Mac: ~/.config/mooniex/org-db.env carries ORG_DB_URL itself -> update it, then restart its sessions and launchd jobs")
    say("  open connections keep their old login until they close: restart is what ends them")


def run(argv: list[str], environ: dict | None = None, *, hub: dict | None = None, connect=_connect,
        runner=subprocess.run, env_file: Path | None = None, unit_dir: Path = UNIT_DIR) -> int:
    environ = dict(os.environ if environ is None else environ)
    if len(argv) != 1 or argv[0] not in ("check", "apply"):
        say("usage: rotate_org_db_password.py check|apply   (ORG_DB_URL from the environment)")
        return 2
    verb = argv[0]
    hub = hub or load_hub()
    env_file = env_file or Path(environ.get("MOONIEX_ORG_DB_ENV") or ENV_FILE_DEFAULT)

    new = parse_url((environ.get("ORG_DB_URL") or "").strip(), hub)
    say(f"step 1 OK: ORG_DB_URL is role {ROLE} on the hub ({hub['container']}, database {hub['database']})")

    state = probe(new["url"], connect)
    if state == "works":
        say("REFUSED: Infisical still holds a working password; set the new one first "
            "(or the rotation already ran). Nothing changed.")
        return 3
    if state != "auth_failed":
        say(f"REFUSED: the hub did not answer with a password failure ({state.partition(':')[2]}); "
            "cannot prove the old password is gone. Nothing changed.")
        return 4
    say("step 2 OK: the hub refuses the new password, so it is not applied yet")
    if stale_test_url(environ, new):
        say("WARN: ORG_TEST_DB_URL in Agents-Core/prod logs in as org with another password; "
            "it shares the role's password, so it stops working after apply: update it too")
    stale = env_file_keys(env_file)
    if stale:
        say(f"note: {env_file} assigns {', '.join(stale)}; apply removes those lines")

    if verb == "check":
        say("CHECK OK: ready to apply. Nothing changed.")
        return 0

    verifier = scram_verifier(new["password"])
    if not VERIFIER_RE.match(verifier):
        say("FAIL: the computed verifier is malformed. Nothing changed.")
        return 5
    code, lines = apply_verifier(hub, verifier, environ, runner)
    for line in lines:
        say(f"  psql: {line.replace(new['password'], '***')}")
    if code != 0:
        say(f"FAIL: psql exited {code}: the password was not changed")
        return 5
    say(f"step 4 OK: ALTER ROLE {ROLE} applied (verifier only; logging off for that session)")

    state = probe(new["url"], connect, select=True)
    if state != "works":
        say(f"FAIL: role {ROLE} does not accept the new password ({state.partition(':')[2] or 'auth failed'})")
        return 6
    say(f"OK: role {ROLE} accepts the new password")

    try:
        dropped = scrub_env_file(env_file)
    except Exception as exc:  # noqa: BLE001
        say(f"WARN: could not clean {env_file} ({type(exc).__name__}): remove its "
            f"{', '.join(STALE_KEYS)} lines by hand")
    else:
        say(f"step 5 OK: {env_file}: removed {', '.join(dropped)}" if dropped
            else f"step 5 OK: {env_file} holds none of {', '.join(STALE_KEYS)}")

    next_steps(unit_dir)
    return 0


def main(argv: list[str] | None = None, **kw) -> int:
    try:
        return run(list(sys.argv[1:] if argv is None else argv), **kw)
    except Refused as exc:
        say(f"REFUSED: {exc}. Nothing changed.")
        return exc.code
    except BaseException as exc:  # noqa: BLE001 - the text of any exception may carry the URL
        say(f"FAIL: {type(exc).__name__} (message withheld: it may carry the URL)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
