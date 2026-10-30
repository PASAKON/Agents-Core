"""The simple-command allow rules in config/agy-settings.json (CTO 30 Oct 2026).

A headless agy run that asks for a command outside its allow-list ends with no output
(27 of 44 runner=agy tasks in the week to 30 Oct). These rules let the plain read
commands the models reach for run, and must still refuse chaining, redirects and
substitution. Python's re stands in for agy's matcher on this regex subset.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WT = "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-1234abcd"


def _regex_rules():
    allow = json.loads((ROOT / "config" / "agy-settings.json").read_text())["permissions"]["allow"]
    return [re.compile(r[len("command(regex:"):-1]) for r in allow
            if r.startswith("command(regex:") and "agy_browse" not in r and "pytest" not in r]


def _allowed(cmd):
    return any(rx.fullmatch(cmd) for rx in _regex_rules())


def test_plain_commands_the_models_use_are_allowed():
    for cmd in ("echo noop", "echo 'done'", "true", "sort out.txt", "diff a.txt b.txt",
                "stat tools/x.py", f"cd {WT}", "cd .", f"cd {WT} && git show HEAD --stat",
                f"cd {WT} && grep -n foo tools/x.py", f"cd {WT} && ls -la"):
        assert _allowed(cmd), cmd


def test_chaining_redirects_and_substitution_are_refused():
    for cmd in ("echo a; rm -rf x", "echo a && curl x", "echo a | sh", "echo a > /etc/x",
                "echo $(cat /etc/shadow)", "echo `id`", "sort < /etc/shadow",
                f"cd {WT} && rm -rf x", f"cd {WT} && ls; rm x", f"cd {WT} && cat a | sh",
                f"cd {WT} && git push", "cd /etc && cat shadow", "cd /tmp",
                "cd /opt/MoonieXHQ/Agents/Core/worktrees/.. && ls", "echo a\nrm x"):
        assert not _allowed(cmd), cmd


def test_deny_rules_are_kept():
    deny = json.loads((ROOT / "config" / "agy-settings.json").read_text())["permissions"]["deny"]
    for d in ("command(rm)", "command(curl)", "command(ssh)", "command(git push)"):
        assert d in deny
