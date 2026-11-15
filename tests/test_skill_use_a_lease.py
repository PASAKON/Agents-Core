"""Check the lease procedure against local sources without opening a database."""
import argparse
from pathlib import Path
import re
import shlex

import pytest
import yaml

from tools import lease as cli


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude/skills/ALL_Procedure_UseALease/SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")


@pytest.fixture
def parser(monkeypatch):
    class Captured(Exception):
        pass

    captured = []

    def capture(self, *args, **kwargs):
        captured.append(self)
        raise Captured

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", capture)
    monkeypatch.setattr(cli.api, "default_service", lambda: pytest.fail("hub access"))
    with pytest.raises(Captured):
        cli.main([])
    return captured[0]


def command_parsers(parser):
    return next(a.choices for a in parser._actions
                if isinstance(a, argparse._SubParsersAction))


def validate_commands(text, parser):
    commands = command_parsers(parser)
    mentions = re.findall(r"tools/lease\.py\s+([^\n`]+)", text)
    assert mentions, "no CLI examples found"
    for mention in mentions:
        tokens = shlex.split(mention)
        assert tokens[0] in commands, f"unknown subcommand: {tokens[0]}"
        allowed = commands[tokens[0]]._option_string_actions
        for token in tokens[1:]:
            if token.startswith("--"):
                assert token.split("=", 1)[0] in allowed, token
    all_flags = set(parser._option_string_actions)
    for subparser in commands.values():
        all_flags.update(subparser._option_string_actions)
    for flag in re.findall(r"--[a-z][a-z0-9-]*", text):
        assert flag in all_flags, f"unknown documented flag: {flag}"


def repo_paths(text):
    # File-shaped references anywhere, including fenced code and Markdown links.
    # HTTP endpoints and slash skill triggers deliberately have no file suffix.
    return set(re.findall(
        r"(?<![\w/])(?:\.?[A-Za-z_][\w.-]*/)+[\w.-]+\.(?:py|md|yaml|yml|sh|ps1|json)\b",
        text,
    ))


def test_frontmatter_and_procedure_template():
    _, frontmatter, body = TEXT.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    assert meta["name"] == SKILL.parent.name
    assert meta["kind"] == "procedure"
    assert meta["owner"] == "CTO"
    assert meta["audience"] == ["all"]
    assert meta["created_by"] == "agent"
    assert {"author", "improved_by", "aka"} <= meta.keys()
    assert meta["description"].startswith("PROCEDURE — ")
    assert f"Trigger on /{meta['name']}" in meta["description"]
    assert len(meta["description"]) <= 350
    for heading in ("## Steps (numbered; each with the stop condition)",
                    '## Verify (the command, and what "done" looks like)',
                    "## Failure modes seen (dated)", "## Field notes"):
        assert body.count(heading) == 1
    assert not body.split("## Field notes", 1)[1].strip()


def test_documented_commands_and_flags(parser):
    validate_commands(TEXT, parser)


@pytest.mark.parametrize("example", [
    "tools/lease.py force-release REQUEST_ID",
    "tools/lease.py status REQUEST_ID --token 1",
    "tools/lease.py acquire host:contabo:workers --invented value",
])
def test_command_checker_rejects_drift(parser, example):
    with pytest.raises(AssertionError):
        validate_commands(example, parser)


def test_all_documented_repo_paths_exist():
    paths = repo_paths(TEXT)
    assert {"tools/lease.py", "lib/lease.py", "config/resources.yaml",
            "tests/test_skill_use_a_lease.py"} <= paths
    for path in paths:
        assert (ROOT / path).exists(), f"missing repository path: {path}"


def test_path_extraction_includes_code_links_and_hidden_directories():
    assert repo_paths('`lib/missing.py` [x](docs/missing.md)\n'
                      '.claude/skills/Missing/SKILL.md\n/api/leases/status') == {
        "lib/missing.py", "docs/missing.md", ".claude/skills/Missing/SKILL.md"}


def test_worked_rows_are_literal_registry_rows():
    registry = (ROOT / "config/resources.yaml").read_text()
    blocks = re.findall(r"```yaml\n(.*?)```", TEXT, re.S)
    assert len(blocks) == 1
    rows = yaml.safe_load(blocks[0])
    assert {row["kind"] for row in rows} == {"mutex", "pool", "rate"}
    for line in blocks[0].splitlines():
        if line.strip():
            assert line.strip() in registry
