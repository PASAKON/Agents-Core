"""Org Mesh W4.2b: the Run cards in deploy/node-token/README.md.

Nothing in the README was run while it was written, so these tests read it the way the CTO will use
it: every `ask_run.py create` block must parse with ask_run's own parser, pass its secret-shape
lint, name files and verbs that exist, and come in the order the deploy needs (apply before the
DSN is put, the DSN before the unit starts). A dry run builds each card body through the same
`prepare_ask` the real call uses and sends nothing.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w42b_node_token_cards.py
"""
from __future__ import annotations

import io
import json
import re
import shlex
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import ask_run  # noqa: E402
from tools import infisical_setup  # noqa: E402

README = ROOT / "deploy" / "node-token" / "README.md"
UNIT = ROOT / "deploy" / "node-token" / "org-node-token.service"
SUBSTITUTE = {"<sha>": "0123abc", "<worktree>": "/opt/MoonieXHQ/Agents/Core/worktrees/w42b",
              "<YYYY-MM-DD>": "2027-01-01"}


def _cards() -> list[list[str]]:
    """Each ```bash block that starts `python3 tools/ask_run.py create`, as an argv for ask_run.main."""
    text = README.read_text(encoding="utf-8")
    out = []
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        if not block.lstrip().startswith("python3 tools/ask_run.py create"):
            continue
        for old, new in SUBSTITUTE.items():
            block = block.replace(old, new)
        argv = shlex.split(block.replace("\\\n", " "))
        assert argv[:2] == ["python3", "tools/ask_run.py"], argv[:3]
        out.append(argv[2:])
    return out


CARDS = _cards()


def _flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def _as_the_cto(monkeypatch):
    """Dry runs only: ask_run refuses --command from a worker, and a worker may not claim a role.
    The environment of a C-level session is what the CTO has when typing these."""
    for var in ("WORKER_TASK_ID", "WORKER_ROLE", "CTO_SESSION_ID", "ORG_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", "cto-00000000")


def _dry_run(argv: list[str]) -> dict:
    cut = argv.index("--") if "--" in argv else len(argv)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = ask_run.main([*argv[:cut], "--dry-run", *argv[cut:]])
    assert rc == 0, err.getvalue()
    return json.loads(out.getvalue())


def test_the_readme_has_the_cards_the_design_names():
    assert len(CARDS) == 5, [c[:4] for c in CARDS]
    for argv in CARDS:
        assert argv[0] == "create" and _flag(argv, "--host") == "contabo"
        assert "--why" in argv and "--expected" in argv


def test_the_cards_come_in_the_order_the_deploy_needs():
    plan, apply_, role, unit, health = (" ".join(c) for c in CARDS)
    assert plan.endswith("-- plan") and "infisical_setup.py" in plan
    assert apply_.endswith("-- apply") and "infisical_setup.py" in apply_
    # the role and the DSN put are one line: the URL holds the password and never rests on a file
    assert "org_node_token_role.py |" in role
    assert "put Agents-Core prod ORG_NODE_TOKEN_DB_URL --path /node-token --stdin" in role
    assert "systemctl enable --now org-node-token" in unit and "cp deploy/node-token/org-node-token.service" in unit
    assert "8792/health" in health
    text = README.read_text(encoding="utf-8")
    assert text.index("-- plan") < text.index("-- apply") < text.index("org_node_token_role.py |") \
        < text.index("systemctl enable --now") < text.index("8792/health")


def test_the_ceo_enters_the_token_himself_between_apply_and_the_unit():
    text = README.read_text(encoding="utf-8")
    step = text[text.index("3. **The CEO's own step"):text.index("4. **Role and DSN")]
    assert "CLAUDE_CODE_OAUTH_TOKEN" in step and "Org-Node" in step and "not a card" in step
    assert "ask_run.py" not in step                      # no card, no command, carries that value


@pytest.mark.parametrize("argv", CARDS, ids=lambda a: _flag(a, "--why")[:40])
def test_each_card_parses_with_ask_runs_own_parser_and_carries_no_secret_shape(argv):
    args, rest = ask_run._parser().parse_known_args(argv)
    assert args.verb == "create" and args.host == "contabo"
    body = [args.why, args.expected or "", getattr(args, "command", None) or "", *rest]
    assert ask_run.find_secret_shapes(body) == []
    assert "<" not in " ".join(body)                     # every placeholder was substituted: none is left


def test_the_script_cards_dry_run_to_a_body_the_hub_would_accept(monkeypatch):
    _as_the_cto(monkeypatch)
    verbs = []
    for argv in CARDS:
        if "--script" not in argv:
            continue
        body = _dry_run(argv)
        assert body["kind"] == "script" and body["host"] == "contabo"
        assert body["script"]["repo"] == "Agents-Core" and body["script"]["sha"] == "0123abc"
        assert (ROOT / body["script"]["path"]).is_file()
        verbs.append(body["script"]["args"])
    assert verbs == [["plan"], ["apply"]]


def test_the_command_cards_dry_run_for_a_c_level_session(monkeypatch):
    _as_the_cto(monkeypatch)
    for argv in CARDS:
        if "--command" not in argv:
            continue
        body = _dry_run(argv)
        assert body["kind"] == "command" and body["host"] == "contabo"
        assert ask_run.find_secret_shapes(body) == []


def test_the_role_and_put_card_names_files_flags_and_metadata_that_exist():
    role = next(" ".join(c) for c in CARDS if "org_node_token_role.py" in " ".join(c))
    assert (ROOT / "deploy" / "node-token" / "org_node_token_role.py").is_file()
    for name in infisical_setup.REQUIRED_META:           # `put` refuses a create without these
        assert f"--meta {name}=" in role, name
    assert "--path /node-token" in role and infisical_setup.NODE_TOKEN_FOLDER == "node-token"
    assert "run Agents-Core prod --as contabo" in role   # the connecting URL comes from the hub's own project
    assert "ORG_NODE_TOKEN_DB_URL" in role


def test_the_readme_says_how_to_start_a_unit_that_the_start_limit_stopped():
    text = README.read_text(encoding="utf-8")
    assert "systemctl reset-failed org-node-token" in text and "StartLimitBurst" in text
    assert "RestartPreventExitStatus=2" in text and "MemoryMax=256M" in text and "TasksMax=64" in text


def test_the_unit_card_creates_the_user_the_unit_drops_to_and_installs_the_file_it_has():
    unit_card = next(" ".join(c) for c in CARDS if "systemctl enable" in " ".join(c))
    unit = UNIT.read_text(encoding="utf-8")
    assert "--reuid=org-node-token" in unit and "useradd" in unit_card and "org-node-token" in unit_card
    assert "[Install]" in unit and "WantedBy=multi-user.target" in unit    # enable --now has something to enable
    # the checkout path the card tests is the one the unit starts from
    assert "WorkingDirectory=/opt/MoonieXHQ/Agents/Core" in unit
    assert "/opt/MoonieXHQ/Agents/Core/tools/node_token_api.py" in unit_card
    assert (ROOT / "tools" / "node_token_api.py").is_file()


def test_the_health_card_reads_the_tailnet_address_on_contabo_and_not_on_the_typists_machine():
    health = next(c for c in CARDS if "8792/health" in " ".join(c))
    assert "$(tailscale ip -4" in _flag(health, "--command")
    line = next(ln for ln in README.read_text(encoding="utf-8").splitlines() if "8792/health" in ln and "--command" in ln)
    assert "--command '" in line                         # a double-quoted $( ) would run on the Mac


def test_the_readme_says_the_acl_rule_and_that_it_is_not_applied():
    text = README.read_text(encoding="utf-8")
    assert "tag:org-node" in text and "8792" in text and "not** allow-all" in text
    assert "Nothing\nhere applies that rule" in text
    assert "ORG_NODE_TOKEN_URL" in text and "ORG_W42_PROVISION=1" in text


def test_the_readme_holds_no_token_shaped_value_or_key_material():
    # Not find_secret_shapes over the whole page: its `NAME=value` rule flags the documentation of
    # ORG_NODE_TOKEN_URL and the bundle's "token_url" field, which are addresses. The cards above
    # went through the whole lint; here only the shapes of real credentials are searched for.
    text = README.read_text(encoding="utf-8")
    for label, rx in ask_run._TOKEN_SHAPES:
        assert not rx.search(text), label
    assert not ask_run._KEYMAT.search(text) and "AGE-SECRET-KEY-" not in text
