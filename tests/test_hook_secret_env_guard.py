"""scripts/hook-secret-env-guard.py -- PreToolUse guard for running services' secrets.

Chatudo O7b design §7 "Insider on the box": no agent reads a chatudo container's
environment, /proc/*/environ, `ps e` output or the Infisical /chatudo folder.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("hooksecretenv", ROOT / "scripts" / "hook-secret-env-guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def _bash(cmd, env=None):
    return guard.decide({"tool_name": "Bash", "tool_input": {"command": cmd}}, env=env or {})


BLOCKED = [
    "docker inspect chatudo-webhook",
    "docker container inspect chatudo-cron | jq .",
    "docker exec -it chatudo-webhook env",
    "docker exec chatudo-webhook printenv CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET",
    "docker compose -f docker-compose.chatudo.yml exec webhook sh",
    "docker-compose -f /opt/x/docker-compose.chatudo.yml exec webhook env",
    "docker cp chatudo-webhook:/proc/1/environ /tmp/e",
    "docker compose -f docker-compose.chatudo.yml config",
    "docker compose -f docker-compose.chatudo.yml run --rm webhook env",
    "docker inspect $(docker ps -q)",
    "docker ps -q | xargs docker inspect",
    "cat /proc/1234/environ",
    "tr '\\0' '\\n' < /proc/self/environ",
    "strings /proc/42/task/43/environ",
    "ps eww",
    "ps auxe | grep node",
    "sleep 1; ps -o pid eww 1",
    "python3 scripts/infisical_setup.py last4 --path /chatudo CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET",
    "infisical export --env prod --path /chatudo",
    "infisical secrets get X --path=/chatudo",
]

ALLOWED = [
    "docker ps",
    "docker ps --filter name=chatudo",
    "docker logs --tail 50 chatudo-webhook",
    "docker inspect mooniex-line-queue --format '{{.State.Status}}'",
    "docker exec mooniex-webhook node -v",
    "ps -ef | grep node",
    "ps aux",
    "ps -o pid,cmd -p 1",
    "ps -o pid,etime,cmd -p 1",
    "sudo ps -ef",
    "cat /proc/meminfo",
    "ls /proc/1/",
    "git -C /opt/x log --oneline -3",
    "grep -rn chatudo docs/",
    "python3 scripts/infisical_setup.py run --path /chatudo -- node src/webhook/server.js",
]


def test_blocked_commands():
    for cmd in BLOCKED:
        assert _bash(cmd), f"should block: {cmd}"


def test_allowed_commands():
    for cmd in ALLOWED:
        assert _bash(cmd) is None, f"should allow: {cmd} -> {_bash(cmd)}"


def test_read_and_grep_on_proc_environ():
    assert guard.decide({"tool_name": "Read", "tool_input": {"file_path": "/proc/1/environ"}}, env={})
    assert guard.decide({"tool_name": "Grep", "tool_input": {"path": "/proc/7/environ", "pattern": "KEY"}}, env={})
    assert guard.decide({"tool_name": "Read", "tool_input": {"file_path": "/proc/cpuinfo"}}, env={}) is None


def test_reason_never_echoes_the_command():
    cmd = "docker exec chatudo-webhook printenv CLAUDEFLOW_CREDENTIAL_ENCRYPTION_SECRET"
    reason = _bash(cmd)
    assert "CLAUDEFLOW" not in reason and "printenv" not in reason


def test_escape_hatch_and_other_tools():
    assert _bash("cat /proc/1/environ", env={"SECRET_ENV_GUARD": "off"}) is None
    assert guard.decide({"tool_name": "Edit", "tool_input": {"file_path": "/proc/1/environ"}}, env={}) is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
