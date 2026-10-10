#!/usr/bin/env python3
"""Run a command with the Claude token in its environment, on a joined node (Org Mesh W4.2b).

    python3 -I tools/node_token.py run [--name NAME] [--config PATH] -- <command> [args...]

A node has no Infisical identity (CEO 2026-10-03). The hub (tools/node_token_api.py) hands the
token to a node it approved, sealed to the age recipient this node registered. This program:

  1. reads host, token_url and age_identity from node.yaml (default ~/.config/mooniex/node.yaml;
     the identity falls back to ~/.config/mooniex/age-identity.txt, where join.sh puts it),
  2. GETs <token_url>?host=<host>&nonce=<16 random bytes, hex>, which answers an armored age
     ciphertext,
  3. opens it with `age -d -i <identity>` through pipes and refuses it unless it carries that
     nonce and an issued_at within 300 s of this machine's clock (an old answer played back to
     this node opens with its key too: the nonce and the age are what reject it),
  4. puts the value in the child's environment under NAME (default CLAUDE_CODE_OAUTH_TOKEN),
  5. replaces itself with the command.

The value is held in this process's memory between 3 and 5 and nowhere else. It is never written
to a file, never printed, never on a command line. Errors say the HTTP status and the hub's short
code (or the exception class), never a body, a path's contents or a value. This is the one
exception to "a service reads its secrets through `infisical run`" and it is for nodes only.

Standard library only and no import from this repo: join.sh and the drill start it as
`python3 -I`, which puts neither the current directory nor this file's directory on sys.path, and
a root process must not import files a user can write.

Exit: 2 = bad usage or node.yaml; 3 = the hub refused (403: the node is not approved, or left);
4 = the hub or the network failed; 5 = the answer could not be opened, or was stale or for another
request; 6 = caller node does not match host; 7 = hub identity lookup unavailable; 127 = the command could not
start; otherwise the command's own (on Windows) or none (the command replaces this process).
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_NAME = "CLAUDE_CODE_OAUTH_TOKEN"
NONCE_BYTES = 16         # the request carries 16 random bytes as hex; the hub seals them into the answer
MAX_ANSWER_AGE_S = 300   # an opened answer whose issued_at is further than this from now is refused
ISSUED_AT_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\+00:00")
NAME_RE = re.compile(r"[A-Z][A-Z0-9_]{2,63}")
HOST_RE = re.compile(r"[a-z][a-z0-9-]{1,29}[a-z0-9]")
# The hub's token service answers on the hub's TAILNET address and nowhere else, so that is the only
# URL a node accepts: http://<IPv4 in 100.64.0.0/10>:<port>/v1/token. No host name (a DNS answer or a
# hosts-file line could move it), no https (nothing on the tailnet holds a certificate for an address),
# no other path, no user, query or fragment. tools/hq_join.py checks the same string with
# tailnet_token_url() before it puts it in a node's bundle.
TOKEN_NET = ipaddress.ip_network("100.64.0.0/10")
URL_RE = re.compile(r"http://([0-9]{1,3}(?:\.[0-9]{1,3}){3}):([1-9][0-9]{0,4})/v1/token")
CODE_RE = re.compile(r"[a-z_]{1,32}")
YAML_LINE_RE = re.compile(r"^([a-z_]+):[ \t]*(.*?)[ \t]*$")

CONF_DIR = Path.home() / ".config" / "mooniex"
NODE_YAML = CONF_DIR / "node.yaml"
AGE_IDENTITY_DEFAULT = CONF_DIR / "age-identity.txt"
AGE_TIMEOUT_S = 30
HTTP_TIMEOUT_S = 15
ATTEMPTS = 3             # the tailnet may need a moment right after `tailscale up`
RETRY_WAIT_S = 3.0
MAX_ANSWER = 64 * 1024
_EXTRA_BIN_DIRS = ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin")


class TokenError(Exception):
    """A failure to report in one line. `code` is the exit status. Never carries a value."""

    def __init__(self, msg: str, code: int = 1):
        super().__init__(msg)
        self.code = code


def read_node_yaml(path: Path) -> dict:
    """The flat `key: value` lines of node.yaml, quotes cut. join.sh writes a flat file and this
    reads only that: no nesting, no lists, no PyYAML (it is not in the system python)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        raise TokenError(f"cannot read {path} (this machine has not joined: run join.sh)", 2) from None
    out = {}
    for line in text.splitlines():
        m = YAML_LINE_RE.match(line)
        if not m:
            continue
        val = m.group(2)
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1].replace("''", "'") if val[0] == "'" else val[1:-1]
        out[m.group(1)] = val
    return out


def tailnet_token_url(url) -> bool:
    """True only for http://<IPv4 inside TOKEN_NET>:<port 1-65535>/v1/token, written the plain way
    (no leading zeros: some resolvers read 0100 as octal)."""
    m = URL_RE.fullmatch(url) if isinstance(url, str) else None
    if m is None:
        return False
    addr, port = m.groups()
    if any(len(o) > 1 and o[0] == "0" for o in addr.split(".")) or int(port) > 65535:
        return False
    try:
        return ipaddress.IPv4Address(addr) in TOKEN_NET
    except ValueError:
        return False


def settings(config: Path) -> tuple[str, str, Path]:
    """(host, token_url, age identity path) from node.yaml, or TokenError naming the missing key."""
    conf = read_node_yaml(config)
    host, url = conf.get("host", ""), conf.get("token_url", "")
    if not HOST_RE.fullmatch(host):
        raise TokenError(f"{config} has no valid 'host'", 2)
    if not url:
        raise TokenError(f"{config} has no 'token_url' (this node joined before the hub served the "
                         f"token; run join.sh again)", 2)
    if not tailnet_token_url(url):
        raise TokenError(f"{config}: 'token_url' must be http://<hub tailnet address, 100.64.0.0/10>:"
                         f"<port>/v1/token", 2)
    return host, url, Path(conf.get("age_identity") or AGE_IDENTITY_DEFAULT)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _opener() -> urllib.request.OpenerDirector:
    """No proxy (an environment variable must not route this), no redirect, http(s) only."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def _hub_code(err: urllib.error.HTTPError) -> str:
    """The hub's short error code from a refusal body, or '' when it is not one."""
    try:
        code = json.loads(err.read(1024).decode("utf-8", "replace")).get("error")
    except Exception:
        return ""
    return code if isinstance(code, str) and CODE_RE.fullmatch(code) else ""


def fetch_ciphertext(url: str, host: str, name: str, nonce: str, *, opener=None) -> str:
    """The armored ciphertext the hub sealed for `host`. TokenError with the status and code.
    `nonce` is sent with the request and comes back sealed inside the answer (open_token checks it),
    so an answer recorded earlier cannot be played back to this node."""
    query = {"host": host}
    if name != DEFAULT_NAME:
        query["name"] = name
    query["nonce"] = nonce
    full = url + "?" + urllib.parse.urlencode(query)
    opener = opener or _opener()
    last = "hub not reachable"
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_WAIT_S)
        try:
            with opener.open(urllib.request.Request(full, method="GET"), timeout=HTTP_TIMEOUT_S) as r:
                data = r.read(MAX_ANSWER + 1)
            if len(data) > MAX_ANSWER:
                raise TokenError("the hub's answer is too long", 4)
            cipher = json.loads(data.decode("utf-8")).get("ciphertext")
            if not isinstance(cipher, str) or "BEGIN AGE ENCRYPTED FILE" not in cipher:
                raise TokenError("the hub's answer holds no ciphertext", 4)
            return cipher
        except urllib.error.HTTPError as e:
            code = _hub_code(e)
            detail = f"hub answered HTTP {e.code}" + (f" ({code})" if code else "")
            if e.code == 403:
                raise TokenError(detail, {"node_mismatch": 6, "whois_unavailable": 7}.get(code, 3)) from None
            if e.code < 500 and e.code != 429:
                raise TokenError(detail, 4) from None
            last = detail
        except TokenError:
            raise
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            last = f"hub not reachable ({type(e).__name__})"
        except (ValueError, UnicodeDecodeError, AttributeError):
            raise TokenError("the hub's answer is not the expected JSON", 4) from None
    raise TokenError(last, 4)


def find_age() -> str:
    found = shutil.which("age")
    if found is None:
        for d in _EXTRA_BIN_DIRS:
            if os.access(os.path.join(d, "age"), os.X_OK):
                return os.path.join(d, "age")
        raise TokenError("age is not installed (join.sh step 2 installs it)", 5)
    return found


def _issued_at(text) -> "datetime | None":
    """The UTC time the hub wrote (`2026-10-04T00:50:12+00:00`), or None when it is anything else.
    Parsed by hand: datetime.fromisoformat does not exist before Python 3.7."""
    m = ISSUED_AT_RE.fullmatch(text) if isinstance(text, str) else None
    if m is None:
        return None
    try:
        return datetime(*[int(g) for g in m.groups()], tzinfo=timezone.utc)
    except ValueError:
        return None


def open_token(cipher: str, identity: Path, host: str, name: str, nonce: str, *,
               runner=None, now: "datetime | None" = None) -> str:
    """The token value from `cipher`. The plaintext crosses stdin/stdout only; age gets the
    identity PATH on argv, which is not secret.

    The opened answer must carry THIS request's `nonce` and an `issued_at` within MAX_ANSWER_AGE_S
    of `now` (this machine's clock): an old sealed answer, replayed by something standing in for
    the hub, opens fine with the node's key but fails both checks."""
    if not Path(identity).is_file():
        raise TokenError(f"the age identity {identity} does not exist", 5)
    argv = [find_age(), "-d", "-i", str(identity)]
    try:
        if runner is not None:
            rc, out = runner(argv, cipher.encode("ascii"))
        else:
            p = subprocess.run(argv, input=cipher.encode("ascii"), capture_output=True,
                               timeout=AGE_TIMEOUT_S, check=False)
            rc, out = p.returncode, p.stdout
    except (subprocess.TimeoutExpired, OSError, UnicodeEncodeError) as e:
        raise TokenError(f"age failed ({type(e).__name__})", 5) from None
    if rc != 0:
        raise TokenError("age could not open the answer (it was sealed to another key)", 5)
    try:
        d = json.loads(out.decode("utf-8"))
        ok = d["v"] == 1 and d["host"] == host and d["name"] == name
        value = d["value"]
        echoed, issued = d.get("nonce"), _issued_at(d.get("issued_at"))
    except Exception:
        raise TokenError("the opened answer is not the expected JSON", 5) from None
    if not ok:
        raise TokenError("the opened answer is for another host or secret", 5)
    if echoed != nonce:
        raise TokenError("the opened answer is for another request (an old answer was played back)", 5)
    when = now if now is not None else datetime.now(timezone.utc)
    if issued is None or abs((when - issued).total_seconds()) > MAX_ANSWER_AGE_S:
        raise TokenError(f"the opened answer was not issued within {MAX_ANSWER_AGE_S} s of this machine's "
                         f"clock (an old answer was played back, or this clock is wrong)", 5)
    if not isinstance(value, str) or not value:
        raise TokenError("the opened answer holds no value", 5)
    return value


def run(argv: list[str], *, config: Path = NODE_YAML, name: str = DEFAULT_NAME,
        opener=None, runner=None, launch=None) -> int:
    """Fetch, open and start `argv` with NAME set. `launch(argv, env)` replaces os.exec for tests."""
    if not argv:
        raise TokenError("no command after --", 2)
    if not NAME_RE.fullmatch(name):
        raise TokenError("--name must look like CLAUDE_CODE_OAUTH_TOKEN", 2)
    host, url, identity = settings(config)
    nonce = secrets.token_hex(NONCE_BYTES)   # new for every run: nothing recorded earlier can answer it
    value = open_token(fetch_ciphertext(url, host, name, nonce, opener=opener), identity, host, name, nonce,
                       runner=runner)
    env = dict(os.environ)
    env[name] = value
    del value
    if launch is not None:
        return launch(argv, env)
    if os.name == "nt":    # exec* on Windows starts a new process and exits: the caller would not wait
        return subprocess.call(argv, env=env)
    try:
        os.execvpe(argv[0], argv, env)
    except OSError as e:
        raise TokenError(f"cannot run {argv[0]!r} ({type(e).__name__})", 127) from None
    return 0


def main(args: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if args is None else args)
    usage = "usage: node_token.py run [--name NAME] [--config PATH] -- <command> [args...]"
    try:
        if "--" not in args or args[:1] != ["run"]:
            raise TokenError(usage, 2)
        cut = args.index("--")
        opts, command = args[1:cut], args[cut + 1:]
        name, config = DEFAULT_NAME, NODE_YAML
        while opts:
            flag = opts.pop(0)
            if flag in ("--name", "--config") and opts:
                value = opts.pop(0)
                if flag == "--name":
                    name = value
                else:
                    config = Path(value)
            else:
                raise TokenError(usage, 2)
        return run(command, config=config, name=name)
    except TokenError as e:
        print(f"node_token: {e}", file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
