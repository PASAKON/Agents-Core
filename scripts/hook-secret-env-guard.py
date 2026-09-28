#!/usr/bin/env python3
"""PreToolUse hook (Bash|Read|Grep): an agent never reads a running service's secrets.

Chatudo O7b design §7 (security_engineer, task-f50d0c4c), the row "Insider on
the box": every agent session on Contabo runs as root, and the Chatudo
containers get their secrets through `infisical run` as process environment.
Anything that prints that environment puts shop tokens and the credential
encryption key into a transcript. The design recommends this hook before the
Chatudo instance is brought up (O4, 13 Oct 2026). Residual, for the CEO to
accept: root can still read process memory by other means.

Blocked (exit 2, one line on stderr naming the rule, never the command):
  - docker inspect / exec / cp / run / config (also `docker container …` and
    `docker compose … exec|run|config`; `config` prints interpolated values)
    when the command names a chatudo container or compose file. `inspect`
    with a dynamic target list ($( ), backticks, xargs) is blocked for any
    container, because `docker inspect $(docker ps -q)` includes chatudo too;
  - any path under /proc/<pid>/environ, in Bash or through Read/Grep;
  - `ps` with a BSD-style option cluster holding `e` (`ps eww`, `ps auxe`),
    which prints each process's environment (`ps -ef` stays allowed);
  - `infisical` commands that export or print secrets from the /chatudo folder.

Everything else passes silently (exit 0). Escape hatch, for repair only and
set in the environment Claude Code runs in, never inside a command:
SECRET_ENV_GUARD=off.
"""
from __future__ import annotations

import json
import os
import re
import sys

PROC_ENVIRON_RE = re.compile(r"/proc/[^\s/]+/(?:task/[^\s/]+/)?environ\b")
DOCKER_RE = re.compile(r"\bdocker(?:-compose)?\b")
DOCKER_READ_VERB_RE = re.compile(r"\b(?:inspect|exec|cp|run|config)\b")
DYNAMIC_TARGET_RE = re.compile(r"\$\(|`|\bxargs\b")
INFISICAL_RE = re.compile(r"\binfisical(?:_setup\.py)?\b")
INFISICAL_READ_RE = re.compile(r"\b(?:export|secrets|get|last4)\b")


def check_bash(command: str) -> str | None:
    if PROC_ENVIRON_RE.search(command):
        return "reading /proc/*/environ prints a process's secrets"
    lowered = command.lower()
    if DOCKER_RE.search(lowered) and DOCKER_READ_VERB_RE.search(lowered):
        if "chatudo" in lowered:
            return "docker inspect/exec/cp/run/config on chatudo exposes its environment"
        if re.search(r"\binspect\b", lowered) and DYNAMIC_TARGET_RE.search(command):
            return "docker inspect over a dynamic container list can include chatudo"
    for segment in re.split(r"[;&|\n()]+", command):
        if _ps_shows_env(segment.split()):
            return "ps with the e option prints every process's environment"
    if INFISICAL_RE.search(lowered) and "/chatudo" in lowered and INFISICAL_READ_RE.search(lowered):
        return "printing secrets from the Infisical /chatudo folder"
    return None


PS_ARG_OPTS = {"-o", "-O", "-p", "-q", "-u", "-U", "-g", "-G", "-C", "-t", "-k",
               "--format", "--sort", "--pid", "--ppid", "--user", "--cols", "--rows"}


def _ps_shows_env(words: list[str]) -> bool:
    """True when a `ps` call carries a BSD-style option cluster with `e`
    (`ps eww`, `ps auxe`, `ps -o pid eww 1`). An argument that belongs to an
    option (`-o pid,etime`) and dashed SysV options (`ps -ef`) do not count."""
    while words and words[0] in ("sudo", "env", "nice", "timeout"):
        words = words[1:]
        while words and words[0].startswith("-"):
            words = words[1:]
    if not words or words[0] != "ps":
        return False
    skip = False
    for arg in words[1:]:
        if skip:
            skip = False
            continue
        if arg in PS_ARG_OPTS:
            skip = True
            continue
        if arg.startswith("-"):
            continue
        if re.fullmatch(r"[a-zA-Z]+", arg) and "e" in arg:
            return True
    return False


def check_path(path: str) -> str | None:
    if path and PROC_ENVIRON_RE.search(path):
        return "reading /proc/*/environ prints a process's secrets"
    return None


def decide(event: dict, env: dict | None = None) -> str | None:
    env = os.environ if env is None else env
    if env.get("SECRET_ENV_GUARD", "").lower() == "off":
        return None
    tool = event.get("tool_name") or ""
    tin = event.get("tool_input") or {}
    if tool == "Bash":
        return check_bash(str(tin.get("command") or ""))
    if tool == "Read":
        return check_path(str(tin.get("file_path") or ""))
    if tool == "Grep":
        return check_path(str(tin.get("path") or ""))
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    reason = decide(event)
    if reason:
        print(f"BLOCKED by secret-env guard: {reason}. "
              "Chatudo O7b design §7: an agent session never reads a service's secrets. "
              "Ask the CEO if you believe this is a false positive.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
