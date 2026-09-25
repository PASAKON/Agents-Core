"""tools/ask_run.py and the ask_run / ask_run_wait tools in
claude-home/mcp/mooniex-coord/index.mjs (Run Inbox P1b,
docs/design/run-inbox/DESIGN.md §6 + §13, brief run-inbox-p1b-core.md).

Every networked test talks to a FAKE hub: a ThreadingHTTPServer on
127.0.0.1 with an OS-assigned port. Nothing here can reach
terminal.mooniex.com: an autouse fixture points RUN_INBOX_URL at the
loopback discard port and clears the token env, so a test that forgets its
hub fails with "unreachable" instead of going live.

Token-shaped fixtures are ASSEMBLED AT RUNTIME (_val / _shape): CI runs
gitleaks over the full history, and a literal token-shaped string in this
file would fail that job for good.

The MCP half runs the real index.mjs under node (skipped when no node >= 18
is found) and feeds one table of cases through both implementations, so a
refusal cannot hold on one side and not the other.

Run: .venv/bin/python -m pytest tests/test_ask_run.py -q
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.ask_run as ask_run  # noqa: E402

INDEX_MJS = ROOT / "claude-home" / "mcp" / "mooniex-coord" / "index.mjs"
BLUEPRINT = ROOT / "scripts" / "contabo_blueprint.sh"
ASK_ID = "RUN-20260925-1612-ab12"
SCRIPT_SPEC = "Agents-Core@9df4e185:scripts/contabo_blueprint.sh"
CREATED = {"id": ASK_ID, "status": "pending", "risk": "amber", "expires_at": "2026-09-25T16:42:00Z"}


def _val(n: int = 24) -> str:
    """A literal-looking secret value, built at runtime."""
    return ("q7" * n)[:n]


def _shape(prefix_parts: tuple[str, ...], body: str) -> str:
    return "".join(prefix_parts) + body


# ------------------------------------------------------------------ fake hub
class FakeHub:
    """Routes are (METHOD, path) -> responses; each call takes the next one
    and the last one repeats. A response is (status, json), (status, bytes,
    content_type) or ("redirect", location)."""

    def __init__(self) -> None:
        self.token = "tok-" + "fake-hub"
        self.accepted = {self.token}
        self.requests: list[dict] = []
        self.routes: dict[tuple[str, str], list] = {}
        self.url = ""

    def on(self, method: str, path: str, *responses) -> None:
        self.routes[(method, path)] = list(responses)

    def answer(self, method: str, path: str):
        seq = self.routes.get((method, path))
        if not seq:
            return (404, {"error": "not_found"})
        return seq.pop(0) if len(seq) > 1 else seq[0]

    def paths(self) -> list[str]:
        return [r["path"] for r in self.requests]


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # keep pytest output clean
        pass

    def _reply(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, body) -> None:
        hub: FakeHub = self.server.hub  # type: ignore[attr-defined]
        u = urlsplit(self.path)
        auth = self.headers.get("Authorization")
        hub.requests.append({"method": self.command, "path": u.path, "query": parse_qs(u.query),
                             "auth": auth, "body": body})
        if auth not in {f"Bearer {t}" for t in hub.accepted}:
            self._reply(401, b'{"error":"unauthorized"}', "application/json")
            return
        resp = hub.answer(self.command, u.path)
        if resp[0] == "redirect":
            self._reply(302, b"", "text/plain", {"Location": resp[1]})
        elif len(resp) == 3:
            self._reply(resp[0], resp[1], resp[2])
        else:
            self._reply(resp[0], json.dumps(resp[1]).encode(), "application/json")

    def do_GET(self) -> None:  # noqa: N802
        self._handle(None)

    def do_POST(self) -> None:  # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        self._handle(json.loads(raw) if raw else None)


@pytest.fixture(autouse=True)
def _sealed(monkeypatch, tmp_path):
    """No test can reach the real hub or read the real token file."""
    for var in ("RUN_INBOX_TOKEN", "ORG_SESSION_ID", "WORKER_TASK_ID", "WORKER_ROLE",
                "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("RUN_INBOX_URL", "http://127.0.0.1:9")  # discard port: refused, never live
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(ask_run, "MIN_INTERVAL_S", 0.0)


@pytest.fixture
def hub(monkeypatch):
    fake = FakeHub()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.hub = fake  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    fake.url = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setenv("RUN_INBOX_URL", fake.url)
    monkeypatch.setenv("RUN_INBOX_TOKEN", fake.token)
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _create(*extra: str, script_args: tuple[str, ...] = ()) -> list[str]:
    argv = ["create", "--host", "contabo", "--script", SCRIPT_SPEC, "--why", "weekly capture",
            "--session", "cto-test", "--role", "cto", *extra]
    return argv + (["--", *script_args] if script_args else [])


def _token_file(mode: int, value: str) -> Path:
    path = ask_run.token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n", encoding="utf-8")
    path.chmod(mode)
    return path


# ------------------------------------------------------------------- create
def test_dry_run_prints_the_contract_body_and_calls_nothing(hub, monkeypatch, capsys):
    def _no_network(*a, **k):
        raise AssertionError("--dry-run opened a connection")
    monkeypatch.setattr(ask_run._OPENER, "open", _no_network)
    rc = ask_run.main(_create("--dry-run", script_args=("--quick", "two words")))
    out, err = capsys.readouterr()
    assert rc == 0
    body = json.loads(out)
    assert body == {
        "host": "contabo", "kind": "script",
        "script": {"repo": "Agents-Core", "sha": "9df4e185", "path": "scripts/contabo_blueprint.sh",
                   "args": ["--quick", "two words"]},
        "why": "weekly capture", "risk": "amber", "timeout_s": 300, "expects_input": False,
        "requester": {"session": "cto-test", "role": "cto"},
    }
    assert list(body) == ["host", "kind", "script", "why", "risk", "timeout_s", "expects_input", "requester"]
    assert "nothing sent" in err
    assert hub.requests == []


def test_dry_run_needs_no_token():
    assert ask_run.main(_create("--dry-run")) == 0


def test_create_posts_the_body_and_prints_id_and_phone_url(hub, capsys):
    hub.on("POST", "/api/run/asks", (201, CREATED))
    rc = ask_run.main(_create(script_args=("--quick",)))
    out, err = capsys.readouterr()
    assert rc == 0
    assert out.splitlines() == [ASK_ID, f"{hub.url}/run#{ASK_ID}"]
    assert "risk amber" in err and "wait " + ASK_ID in err
    (req,) = hub.requests
    assert (req["method"], req["path"], req["auth"]) == ("POST", "/api/run/asks", f"Bearer {hub.token}")
    assert req["body"]["script"]["args"] == ["--quick"]
    assert hub.token not in out + err


def test_create_sends_every_optional_field_in_contract_order(hub, capsys):
    hub.on("POST", "/api/run/asks", (201, {**CREATED, "risk": "red"}))
    rc = ask_run.main(["create", "--host", "Contabo", "--command", "systemctl restart mooniex-console ",
                       "--why", "pick up the new key", "--expected", "active (running)",
                       "--risk", "red", "--timeout", "60", "--expects-input", "--shell", "bash",
                       "--cwd", "/opt/MoonieXHQ/Agents/Core", "--env-key", "GITHUB_TOKEN",
                       "--env-key", "GITHUB_TOKEN", "--task", "task-8669cf28",
                       "--session", "cto-6ebacd0e", "--role", "CTO"])
    assert rc == 0
    body = hub.requests[0]["body"]
    assert list(body) == ["host", "kind", "command", "shell", "cwd", "env_keys", "why", "expected",
                          "risk", "timeout_s", "expects_input", "requester"]
    assert body["host"] == "contabo"
    assert body["command"] == "systemctl restart mooniex-console "  # byte-for-byte, trailing space kept
    assert body["env_keys"] == ["GITHUB_TOKEN"]
    assert (body["risk"], body["timeout_s"], body["expects_input"]) == ("red", 60, True)
    assert body["requester"] == {"session": "cto-6ebacd0e", "role": "cto", "task": "task-8669cf28"}
    assert "risk red" in capsys.readouterr().err


# ---------------------------------------------------------------- role gate
@pytest.mark.parametrize("role", ["cto", "cfo", "cxo", "ceo"])
def test_command_allowed_for_c_level(role, capsys):
    assert ask_run.main(["create", "--dry-run", "--host", "contabo", "--command", "uptime",
                         "--why", "load", "--session", f"{role}-x", "--role", role]) == 0


@pytest.mark.parametrize("role", ["dev", "designer", "cmo", "browser_operator"])
def test_command_refused_for_other_roles_before_any_call(hub, role, capsys):
    rc = ask_run.main(["create", "--host", "contabo", "--command", "uptime", "--why", "load",
                       "--session", f"{role}-x", "--role", role])
    assert rc == 2
    assert "freeform_needs_c_level" in capsys.readouterr().err
    assert hub.requests == []


def test_worker_process_cannot_claim_a_c_level_role(hub, monkeypatch, capsys):
    monkeypatch.setenv("WORKER_TASK_ID", "task-8669cf28")
    rc = ask_run.main(["create", "--host", "contabo", "--command", "uptime", "--why", "load", "--role", "cto"])
    assert rc == 2
    assert "a worker cannot claim role 'cto'" in capsys.readouterr().err
    assert hub.requests == []


def test_worker_env_script_ask_goes_to_the_workers_own_mailbox(hub, monkeypatch):
    monkeypatch.setenv("WORKER_TASK_ID", "task-8669cf28")
    monkeypatch.setenv("WORKER_ROLE", "developer")
    hub.on("POST", "/api/run/asks", (201, CREATED))
    assert ask_run.main(["create", "--host", "contabo", "--script", SCRIPT_SPEC, "--why", "capture"]) == 0
    assert hub.requests[0]["body"]["requester"] == {
        "session": "developer-task-8669cf28", "role": "developer", "task": "task-8669cf28"}


@pytest.mark.parametrize("env, expected", [
    ({"CXO_ROLE": "cto", "CTO_SESSION_ID": "6ebacd0e"}, {"session": "cto-6ebacd0e", "role": "cto"}),
    ({"CXO_ROLE": "cfo", "CXO_SESSION_ID": "ab12cd34", "CTO_SESSION_ID": "ab12cd34"},
     {"session": "cfo-ab12cd34", "role": "cfo"}),
    ({"CTO_SESSION_ID": "6ebacd0e"}, {"session": "cto-6ebacd0e", "role": "cto"}),
    ({"WORKER_TASK_ID": "task-1", "WORKER_ROLE": "dev"}, {"session": "dev-task-1", "role": "dev", "task": "task-1"}),
    ({"CXO_ROLE": "cto", "CTO_SESSION_ID": "6ebacd0e", "ORG_SESSION_ID": "cto-override"},
     {"session": "cto-override", "role": "cto"}),
    ({"CXO_ROLE": "cto", "ORG_SESSION_ID": "77aa88bb"}, {"session": "cto-77aa88bb", "role": "cto"}),
])
def test_requester_session_is_the_mailbox_box_name(env, expected):
    """hook-inbox.py drains state/inbox/<role>-<id>/, so that is what the hub must be told."""
    assert ask_run.resolve_requester(None, None, None, env) == expected


def test_requester_needs_a_role_and_a_mailbox():
    with pytest.raises(ask_run.Refused, match="role"):
        ask_run.resolve_requester(None, None, None, {})
    with pytest.raises(ask_run.Refused, match="mailbox"):
        ask_run.resolve_requester(None, "cto", None, {})
    with pytest.raises(ask_run.Refused, match="mailbox name"):
        ask_run.resolve_requester("../../etc", "cto", None, {})


# ------------------------------------------------------------ secret shapes
# Each case: the MCP-style arguments of one ask. _argv() turns it into CLI argv.
SECRET_CASES = [
    ("assign at line start", lambda: {"command": f"FOO_TOKEN={_val()} ./deploy.sh"}),
    ("assign mid-command", lambda: {"command": f"export GITHUB_TOKEN={_val()} && ./x.sh"}),
    ("flag assignment", lambda: {"command": f"./x.sh --password={_val()}"}),
    ("token in a URL query", lambda: {"command": f"curl -fsS https://api.example.com/cb?access_token={_val()}"}),
    ("quoted JSON key", lambda: {"command": "curl -d '{\"api_key\": \"" + _val() + "\"}' https://x"}),
    ("YAML line in why", lambda: {"why": f"client_secret: {_val()}"}),
    ("expected", lambda: {"expected": f"SECRET_KEY={_val()}"}),
    ("script arg", lambda: {"args": [f"--api-key={_val()}"]}),
    ("cwd", lambda: {"cwd": f"PASSWORD={_val()}"}),
    ("private key block", lambda: {"command": "printf '%s' '-----" + "BEGIN OPENSSH " + "PRIVATE KEY-----' > k"}),
    ("GitHub token", lambda: {"command": "git remote set-url origin https://" + _shape(("gh", "p_"), _val(36))
                              + "@github.com/o/r.git"}),
    ("sk key", lambda: {"command": "echo " + _shape(("s", "k-", "an", "t-"), _val(40))}),
    ("AWS key id", lambda: {"command": "aws configure set id " + _shape(("AK", "IA"), "Q" * 16)}),
    ("Slack token", lambda: {"why": "post with " + _shape(("xo", "xb-"), _val(20))}),
    ("Google key", lambda: {"command": "curl https://x?k=" + _shape(("AI", "za"), _val(35))}),
    ("JWT", lambda: {"command": "echo " + ".".join("ey" + "J" + _val(12) for _ in range(2)) + "." + _val(12)}),
    ("Bearer literal", lambda: {"command": "curl -H 'Authorization: " + "Bearer " + _val(32) + "' https://x"}),
]

CLEAN_CASES = [
    ("env reference", lambda: {"command": 'GITHUB_TOKEN="$GITHUB_TOKEN" ./deploy.sh'}),
    ("braced env reference", lambda: {"command": "./x.sh --token=${RUN_TOKEN}"}),
    ("Bearer from env", lambda: {"command": 'curl -H "Authorization: Bearer $RUN_INBOX_TOKEN" https://x'}),
    ("Windows env reference", lambda: {"command": "set GH_TOKEN=%GITHUB_TOKEN%", "shell": "cmd"}),
    ("PowerShell env reference", lambda: {"command": "$t = $env:GITHUB_TOKEN; ./x.ps1 -Token:$env:GITHUB_TOKEN"}),
    ("prose why", lambda: {"why": "rotate the token: it expired yesterday"}),
    # Thai prose, as card lines usually are: "check token: expired"
    ("Thai prose why", lambda: {"why": "ตรวจ token: หมดอายุ"}),
    ("empty value", lambda: {"command": "echo '{\"password\": \"\"}'"}),
    ("secretary service name", lambda: {"command": "systemctl restart mooniex-secretary"}),
    ("token file by path, space-separated", lambda: {"command": "python3 tools/x.py --token-file ~/.config/x.token"}),
    ("grep for a key name", lambda: {"command": 'grep -rn "api_key" config/'}),
    ("env key names", lambda: {"env_keys": ["GITHUB_TOKEN", "OPENROUTER_API_KEY"]}),
    ("script named secrets", lambda: {"script": "Agents-Core@9df4e185:scripts/rotate_secrets.sh", "args": ["--dry-run"]}),
]


def _argv(case: dict) -> list[str]:
    argv = ["create", "--dry-run", "--host", "contabo", "--role", "cto", "--session", "cto-t",
            "--why", case.get("why", "a reason")]
    if "expected" in case:
        argv += ["--expected", case["expected"]]
    if "command" in case:
        argv += ["--command", case["command"]]
    else:
        argv += ["--script", case.get("script", "Agents-Core@9df4e185:scripts/x.sh")]
    if "shell" in case:
        argv += ["--shell", case["shell"]]
    if "cwd" in case:
        argv += ["--cwd", case["cwd"]]
    for key in case.get("env_keys", []):
        argv += ["--env-key", key]
    if "args" in case:
        argv += ["--", *case["args"]]
    return argv


def _mcp_args(case: dict) -> dict:
    args = {"host": "contabo", "role": "cto", "session": "cto-t", "why": case.get("why", "a reason"),
            "dry_run": True}
    for key in ("expected", "command", "shell", "cwd", "env_keys", "args"):
        if key in case:
            args[key] = case[key]
    if "command" not in case:
        args["script"] = case.get("script", "Agents-Core@9df4e185:scripts/x.sh")
    return args


def _hits(stderr_text: str) -> list[str]:
    return [line.strip() for line in stderr_text.splitlines() if line.startswith("  ")]


@pytest.mark.parametrize("label, build", SECRET_CASES, ids=[c[0] for c in SECRET_CASES])
def test_secret_shape_refused_before_any_call(hub, capsys, label, build):
    case = build()
    argv = [a for a in _argv(case) if a != "--dry-run"]  # a live create: must still send nothing
    rc = ask_run.main(argv)
    out, err = capsys.readouterr()
    assert rc == 2, err
    assert "secret_shaped_value" in err
    assert hub.requests == []
    assert _val(12) not in out + err and "Q" * 16 not in out + err  # the value is never echoed


@pytest.mark.parametrize("label, build", CLEAN_CASES, ids=[c[0] for c in CLEAN_CASES])
def test_clean_values_pass(label, build, capsys):
    rc = ask_run.main(_argv(build()))
    assert rc == 0, capsys.readouterr().err


def test_secret_family_is_the_blueprints():
    """Put the rule in one family: the CLI, the MCP tool and the blueprint's
    final pass must carry the same key alternation and key-material marker."""
    blueprint = BLUEPRINT.read_text(encoding="utf-8")
    index = INDEX_MJS.read_text(encoding="utf-8")
    assert ask_run.SECRET_KEY_WORDS in blueprint
    assert ask_run.PRIVATE_KEY_MARKER in blueprint
    assert ask_run.SECRET_KEY_WORDS in index
    assert ask_run.PRIVATE_KEY_MARKER in index


# --------------------------------------------------------------------- token
def test_token_env_wins_over_file_then_file_is_used(hub, monkeypatch, capsys):
    file_token = "file-" + "token-value"
    hub.accepted.add(file_token)
    _token_file(0o600, file_token)
    hub.on("POST", "/api/run/asks", (201, CREATED))
    assert ask_run.main(_create()) == 0
    assert hub.requests[-1]["auth"] == f"Bearer {hub.token}"
    monkeypatch.delenv("RUN_INBOX_TOKEN")
    assert ask_run.main(_create()) == 0
    assert hub.requests[-1]["auth"] == f"Bearer {file_token}"
    out, err = capsys.readouterr()
    assert file_token not in out + err and hub.token not in out + err


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_token_file_readable_by_others_is_refused(hub, monkeypatch, capsys):
    monkeypatch.delenv("RUN_INBOX_TOKEN")
    secret = "loose-" + "token-value"
    _token_file(0o644, secret)
    rc = ask_run.main(_create())
    out, err = capsys.readouterr()
    assert rc == 3
    assert "chmod 600" in err and secret not in out + err
    assert hub.requests == []


def test_no_token_fails_before_any_call(hub, monkeypatch, capsys):
    monkeypatch.delenv("RUN_INBOX_TOKEN")
    rc = ask_run.main(_create())
    assert rc == 3
    assert "no token" in capsys.readouterr().err
    assert hub.requests == []


def test_default_hub_url_without_calling_it(monkeypatch):
    monkeypatch.delenv("RUN_INBOX_URL")
    assert ask_run.base_url() == ask_run.DEFAULT_URL == "https://terminal.mooniex.com"
    assert ask_run.card_url(ASK_ID) == f"https://terminal.mooniex.com/run#{ASK_ID}"


def test_redirect_is_refused_so_the_token_goes_nowhere_else(hub, capsys):
    hub.on("POST", "/api/run/asks", ("redirect", "/steal"))
    hub.on("GET", "/steal", (200, {}))
    rc = ask_run.main(_create())
    assert rc == 3
    assert "not followed" in capsys.readouterr().err
    assert hub.paths() == ["/api/run/asks"]


def test_gitignore_keeps_token_files_out():
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "*.token" in lines


# ---------------------------------------------------------------------- wait
def _card(status: str, **extra) -> tuple[int, dict]:
    return (200, {"id": ASK_ID, "host": "contabo", "status": status, **extra})


def test_wait_polls_until_done_and_prints_the_tail(hub, capsys):
    tail = "\n".join(f"line {i}" for i in range(1, 51))
    hub.on("GET", f"/api/run/asks/{ASK_ID}", _card("pending"), _card("approved"), _card("running"),
           _card("done", exit_code=0, duration_ms=12300, output_tail=tail))
    rc = ask_run.main(["wait", ASK_ID, "--interval", "0.01"])
    out, err = capsys.readouterr()
    assert rc == 0
    assert out.splitlines()[0] == f"{ASK_ID}  done  exit 0  12.3s  host contabo"
    assert "output tail (40 of 50 lines)" in out and "line 50" in out and "line 10\n" not in out
    assert [p for p in hub.paths()] == [f"/api/run/asks/{ASK_ID}"] * 4
    for status in ("pending", "approved", "running", "done"):
        assert status in err


@pytest.mark.parametrize("status", ["failed", "denied", "expired", "cancelled"])
def test_wait_exits_1_when_the_ask_ends_without_success(hub, capsys, status):
    extra = {"error_id": ASK_ID, "exit_code": 2} if status == "failed" else {}
    if status == "denied":
        extra["deny_reason"] = "not today"
    hub.on("GET", f"/api/run/asks/{ASK_ID}", _card(status, **extra))
    assert ask_run.main(["wait", ASK_ID]) == 1
    out = capsys.readouterr().out
    assert status in out
    if status == "failed":
        assert f"Error ID {ASK_ID}" in out
    if status == "denied":
        assert "not today" in out


def test_wait_gives_up_after_max_wait(hub, capsys):
    hub.on("GET", f"/api/run/asks/{ASK_ID}", _card("pending"))
    assert ask_run.main(["wait", ASK_ID, "--interval", "0.01", "--max-wait", "0.05"]) == 4
    assert "still pending" in capsys.readouterr().err


def test_wait_rides_out_a_transient_5xx(hub):
    hub.on("GET", f"/api/run/asks/{ASK_ID}", (503, {"error": "busy"}), _card("done", exit_code=0))
    assert ask_run.main(["wait", ASK_ID, "--interval", "0.01"]) == 0


def test_wait_stops_on_a_4xx(hub, capsys):
    hub.on("GET", f"/api/run/asks/{ASK_ID}", (404, {"error": "not_found"}))
    assert ask_run.main(["wait", ASK_ID]) == 3
    assert "not yours" in capsys.readouterr().err
    assert len(hub.requests) == 1


def test_wait_accepts_the_phone_url_and_rejects_junk(hub, capsys):
    hub.on("GET", f"/api/run/asks/{ASK_ID}", _card("done", exit_code=0))
    assert ask_run.main(["wait", f"https://terminal.mooniex.com/run#{ASK_ID}"]) == 0
    assert ask_run.main(["wait", "../../etc/passwd"]) == 2
    assert hub.paths() == [f"/api/run/asks/{ASK_ID}"]


# ---------------------------------------------------------- list / cancel
def test_list_passes_the_filter_and_prints_rows(hub, capsys):
    hub.on("GET", "/api/run/asks", (200, {"asks": [
        {"id": ASK_ID, "status": "pending", "host": "contabo", "risk": "amber",
         "command": "bash scripts/contabo_blueprint.sh", "expires_at": "2026-09-25T16:42:00Z"},
        {"id": "RUN-20260925-0912-4f2a", "status": "done", "host": "contabo", "risk": "green",
         "script": {"repo": "Agents-Core", "sha": "9df4e185aa", "path": "scripts/x.sh", "args": ["-q"]}},
    ]}))
    assert ask_run.main(["list", "--status", "pending", "--limit", "5"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert hub.requests[0]["query"] == {"status": ["pending"], "limit": ["5"]}
    assert out[0].startswith(ASK_ID) and "bash scripts/contabo_blueprint.sh" in out[0] and "expires" in out[0]
    assert "Agents-Core@9df4e185:scripts/x.sh -q" in out[1]


def test_cancel_posts_to_the_asks_cancel_route(hub, capsys):
    hub.on("POST", f"/api/run/asks/{ASK_ID}/cancel", (200, {"id": ASK_ID, "status": "cancelled"}))
    assert ask_run.main(["cancel", ASK_ID]) == 0
    assert capsys.readouterr().out.strip() == f"{ASK_ID} cancelled"
    assert hub.requests[0]["method"] == "POST"


def test_cancel_of_a_running_ask_reports_the_hubs_409(hub, capsys):
    hub.on("POST", f"/api/run/asks/{ASK_ID}/cancel", (409, {"error": "not_pending"}))
    assert ask_run.main(["cancel", ASK_ID]) == 3
    assert "409" in capsys.readouterr().err


@pytest.mark.parametrize("status, code", [
    (403, "freeform_needs_c_level"), (501, "peer_exec_not_yet"), (400, "secret_shaped_value")])
def test_hub_refusals_are_reported_with_their_code(hub, capsys, status, code):
    hub.on("POST", "/api/run/asks", (status, {"error": code}))
    assert ask_run.main(_create()) == 3
    assert code in capsys.readouterr().err


# ---------------------------------------------------------------------- tail
def _sse(*events: tuple[str, str]) -> bytes:
    chunks = [": connected\n\n"]
    for name, data in events:
        chunks.append(f"event: {name}\n" + "".join(f"data: {d}\n" for d in data.split("\n")) + "\n")
    return "".join(chunks).encode()


def test_tail_streams_output_and_exits_by_the_end_event(hub, capsys):
    hub.on("GET", f"/api/run/asks/{ASK_ID}/events", (200, _sse(
        ("state", '{"status": "running"}'),
        ("output", json.dumps("hello\n")),
        ("output", '{"chunk": "world\\n"}'),
        ("output", "raw line one\nraw line two"),
        ("end", '{"exit_code": 0, "duration_ms": 1500}'),
    ), "text/event-stream"))
    assert ask_run.main(["tail", ASK_ID]) == 0
    out, err = capsys.readouterr()
    assert out == "hello\nworld\nraw line one\nraw line two\n"
    assert "[state] running" in err and "[end] exit 0 in 1.5s" in err


def test_tail_nonzero_exit_and_denied(hub):
    path = f"/api/run/asks/{ASK_ID}/events"
    hub.on("GET", path, (200, _sse(("end", '{"exit_code": 3}')), "text/event-stream"))
    assert ask_run.main(["tail", ASK_ID]) == 1
    hub.on("GET", path, (200, _sse(("state", '{"status": "denied"}')), "text/event-stream"))
    assert ask_run.main(["tail", ASK_ID]) == 1
    hub.on("GET", path, (200, _sse(("state", '{"status": "running"}')), "text/event-stream"))
    assert ask_run.main(["tail", ASK_ID]) == 3  # closed with no end event


# ----------------------------------------------------------- argument checks
@pytest.mark.parametrize("spec", [
    "Agents-Core:scripts/x.sh", "Agents-Core@main:scripts/x.sh", "Agents-Core@9df4e185:/etc/passwd",
    "Agents-Core@9df4e185:../x.sh", "Agents-Core@9df4e185:a/../../x.sh", "Agents-Core@9df4e185:",
    "@9df4e185:x.sh", "Agents-Core@9df4e185:scripts\\x.ps1", "Agents-Core@9df4:x.sh",
])
def test_bad_script_specs_are_refused(spec):
    with pytest.raises(ask_run.Refused):
        ask_run.parse_script_spec(spec)


def test_script_spec_lowercases_the_sha():
    assert ask_run.parse_script_spec("Agents-Core@9DF4E185:windows/x.ps1") == ("Agents-Core", "9df4e185", "windows/x.ps1")


@pytest.mark.parametrize("argv", [
    ["create", "--dry-run", "--host", "contabo", "--command", "uptime", "--why", "x", "--role", "cto",
     "--session", "cto-t", "--", "extra"],
    ["create", "--dry-run", "--host", "contabo", "--command", "uptime", "--why", "two\nlines", "--role", "cto",
     "--session", "cto-t"],
    ["create", "--dry-run", "--host", "contabo", "--script", SCRIPT_SPEC, "--why", "x", "--role", "cto",
     "--session", "cto-t", "--env-key", "A=b"],
    ["create", "--dry-run", "--host", "Not A Host", "--script", SCRIPT_SPEC, "--why", "x", "--role", "cto",
     "--session", "cto-t"],
    ["create", "--dry-run", "--host", "contabo", "--script", SCRIPT_SPEC, "--why", "x", "--role", "cto",
     "--session", "cto-t", "--timeout", "0"],
])
def test_bad_arguments_are_refused(argv, capsys):
    assert ask_run.main(argv) == 2


# ======================================================== the MCP tools (node)
def _node() -> str | None:
    for cand in ("/opt/node-v22/bin/node", shutil.which("node")):
        if not cand or not Path(cand).exists():
            continue
        try:
            ver = subprocess.run([cand, "--version"], capture_output=True, text=True, timeout=10).stdout
            if int(ver.strip().lstrip("v").split(".")[0]) >= 18:  # global fetch
                return cand
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
    return None


class McpClient:
    """The real index.mjs over stdio, one JSON-RPC request at a time (stdin
    stays open: the server exits on stdin close, before async tools finish)."""

    def __init__(self, node: str, env: dict, workdir: Path) -> None:
        self._stderr = open(workdir / "mcp-stderr.log", "w", encoding="utf-8")
        self.proc = subprocess.Popen([node, str(INDEX_MJS)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self._stderr, env=env, cwd=str(workdir), text=True,
                                     encoding="utf-8")
        self.lines: queue.Queue = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()
        self.next_id = 0

    def _pump(self) -> None:
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def request(self, method: str, params: dict | None = None, timeout: float = 30.0) -> dict:
        self.next_id += 1
        rid = self.next_id
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid, "method": method,
                                          "params": params or {}}) + "\n")
        self.proc.stdin.flush()
        deadline = time.monotonic() + timeout
        while True:
            line = self.lines.get(timeout=max(0.1, deadline - time.monotonic()))
            if line is None:
                raise AssertionError("mcp server exited early")
            msg = json.loads(line)
            if msg.get("id") == rid:
                return msg

    def tool(self, name: str, arguments: dict) -> tuple[dict, str]:
        result = self.request("tools/call", {"name": name, "arguments": arguments})["result"]
        return result, result["content"][0]["text"]

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            self.proc.kill()
        self._stderr.close()


@pytest.fixture
def mcp(tmp_path):
    node = _node()
    if not node:
        pytest.skip("node >= 18 not found")
    clients: list[McpClient] = []

    def start(**env_extra: str) -> McpClient:
        home = tmp_path / "mcp-home"
        home.mkdir(exist_ok=True)
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "RUN_INBOX_URL": "http://127.0.0.1:9",
               **env_extra}
        client = McpClient(node, env, tmp_path)
        clients.append(client)
        client.request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                      "clientInfo": {"name": "pytest", "version": "0"}})
        return client

    yield start
    for c in clients:
        c.close()


def test_mcp_lists_both_tools_with_the_one_rule(mcp):
    tools = {t["name"]: t for t in mcp().request("tools/list")["result"]["tools"]}
    for name in ("ask_run", "ask_run_wait"):
        assert "the ceo's tap is the only authority; the tool never approves" in tools[name]["description"].lower()
    assert tools["ask_run"]["inputSchema"]["required"] == ["host", "why"]
    assert tools["ask_run_wait"]["inputSchema"]["required"] == ["id"]


def test_mcp_dry_run_body_equals_the_cli_body(mcp, capsys):
    case = {"script": SCRIPT_SPEC, "args": ["--quick", "two words"], "expected": "a dir path",
            "cwd": "/opt/MoonieXHQ/Agents/Core", "env_keys": ["GITHUB_TOKEN"], "shell": "bash"}
    assert ask_run.main(_argv(case)) == 0
    cli_body = json.loads(capsys.readouterr().out)
    result, text = mcp().tool("ask_run", _mcp_args(case))
    assert not result.get("isError"), text
    assert json.loads(text)["payload"] == cli_body


def test_mcp_refusals_match_the_cli_case_for_case(mcp, capsys):
    client = mcp()
    for label, build in SECRET_CASES + CLEAN_CASES:
        case = build()
        rc = ask_run.main(_argv(case))
        cli_hits = _hits(capsys.readouterr().err)
        result, text = client.tool("ask_run", _mcp_args(case))
        assert bool(result.get("isError")) == (rc == 2), label
        if rc == 2:
            assert _hits(text) == cli_hits and cli_hits, label


def test_mcp_role_gate_and_worker_guard(mcp):
    _, text = mcp().tool("ask_run", {"host": "contabo", "command": "uptime", "why": "x", "role": "dev",
                                     "session": "dev-x", "dry_run": True})
    assert "freeform_needs_c_level" in text
    _, text = mcp(WORKER_TASK_ID="task-1").tool("ask_run", {"host": "contabo", "command": "uptime", "why": "x",
                                                            "role": "cto", "dry_run": True})
    assert "a worker cannot claim role 'cto'" in text


def test_mcp_ask_run_posts_and_returns_id_url_risk_expiry(mcp, hub, capsys):
    hub.on("POST", "/api/run/asks", (201, CREATED))
    result, text = mcp(RUN_INBOX_URL=hub.url, RUN_INBOX_TOKEN=hub.token).tool(
        "ask_run", {**_mcp_args({"script": SCRIPT_SPEC}), "dry_run": False})
    assert not result.get("isError"), text
    assert json.loads(text) == {"id": ASK_ID, "url": f"{hub.url}/run#{ASK_ID}", "risk": "amber",
                                "expires_at": "2026-09-25T16:42:00Z"}
    assert hub.requests[0]["auth"] == f"Bearer {hub.token}"
    assert ask_run.main(_argv({"script": SCRIPT_SPEC})) == 0
    assert hub.requests[0]["body"] == json.loads(capsys.readouterr().out)
    assert hub.token not in text


def test_mcp_reads_the_token_file_and_refuses_a_loose_one(mcp, hub, tmp_path):
    token_file = tmp_path / "mcp-home" / ".config" / "mooniex" / "run-inbox.token"
    token_file.parent.mkdir(parents=True)
    file_token = "mcp-file-" + "token"
    hub.accepted = {file_token}
    token_file.write_text(file_token + "\n", encoding="utf-8")
    token_file.chmod(0o600)
    hub.on("POST", "/api/run/asks", (201, CREATED))
    client = mcp(RUN_INBOX_URL=hub.url)
    args = {**_mcp_args({"script": SCRIPT_SPEC}), "dry_run": False}
    result, text = client.tool("ask_run", args)
    assert not result.get("isError"), text
    assert hub.requests[-1]["auth"] == f"Bearer {file_token}"
    if os.name == "posix":
        token_file.chmod(0o644)
        result, text = client.tool("ask_run", args)
        assert result.get("isError") and "chmod 600" in text and file_token not in text
        assert len(hub.requests) == 1


def test_mcp_ask_run_wait_returns_the_terminal_record(mcp, hub):
    tail = "\n".join(f"line {i}" for i in range(1, 51))
    hub.on("GET", f"/api/run/asks/{ASK_ID}", _card("running"),
           _card("done", exit_code=0, output_tail=tail))
    client = mcp(RUN_INBOX_URL=hub.url, RUN_INBOX_TOKEN=hub.token)
    result, text = client.tool("ask_run_wait", {"id": f"{hub.url}/run#{ASK_ID}", "interval_s": 1})
    assert not result.get("isError"), text
    rec = json.loads(text)
    assert (rec["terminal"], rec["status"], rec["exit_code"]) == (True, "done", 0)
    assert rec["output_tail"].splitlines()[0] == "line 11" and rec["output_tail_shown"] == "last 40 of 50 lines"
    hub.on("GET", f"/api/run/asks/{ASK_ID}", _card("pending"))
    _, text = client.tool("ask_run_wait", {"id": ASK_ID, "interval_s": 1, "max_wait_s": 1})
    assert json.loads(text)["terminal"] is False
    hub.on("GET", f"/api/run/asks/{ASK_ID}", (404, {"error": "not_found"}))
    result, text = client.tool("ask_run_wait", {"id": ASK_ID})
    assert result.get("isError") and "404" in text
