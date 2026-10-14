"""tools/ask_run.py spend label (Console docs/run.md §Spend label, CEO 2026-10-14).

What must hold: `create --spend-*` and the org MCP `spend={...}` put the same `spend` object on the
POST body; the command must carry --max-usd / --max-credits equal to the cap, before anything is
sent; estimate <= cap; balance_after defaults to the spend guard's newest openrouter/fal balance
minus the cap (only when that snapshot is under an hour old), and a cap above the balance is refused;
--no-spend needs a reason and excludes a label. Every case runs --dry-run / dry_run=True against
the loopback discard port: nothing here reaches the hub or spends anything.

Run: .venv/bin/python -m pytest tests/test_ask_run_spend.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.ask_run as ask_run  # noqa: E402

NOW = datetime(2026, 10, 14, 7, 0, tzinfo=timezone.utc)
RENDER = "python tools/bl_render.py --ep 62 --max-usd 1.50"


@pytest.fixture(autouse=True)
def _sealed(monkeypatch, tmp_path):
    for var in ("RUN_INBOX_TOKEN", "ORG_SESSION_ID", "WORKER_TASK_ID", "WORKER_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("RUN_INBOX_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "org"))  # no spend guard snapshot unless a test writes one


def _snapshot(tmp_path: Path, at: datetime, **providers) -> None:
    d = tmp_path / "org" / "state" / "spend_guard"
    d.mkdir(parents=True, exist_ok=True)
    rows = [{"at": (at - timedelta(minutes=15)).isoformat(), "fal": {"ok": True, "balance": 99.0}},
            {"at": at.isoformat(), **providers}]
    (d / "snapshots.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _cli(*extra: str, command: str = RENDER) -> list[str]:
    return ["create", "--dry-run", "--host", "contabo", "--role", "cto", "--session", "cto-t",
            "--why", "render", "--command", command, *extra]


def _body(capsys, argv: list[str]) -> dict:
    assert ask_run.main(argv) == 0, capsys.readouterr().err
    return json.loads(capsys.readouterr().out)


def _refused(capsys, argv: list[str]) -> str:
    assert ask_run.main(argv) == 2
    return capsys.readouterr().err


FAL = ("--spend-provider", "fal", "--spend-estimate", "0.9", "--spend-cap", "1.5",
       "--spend-how", "4 x 15 s x $0.015/s")


def test_cli_label_with_declared_balance(capsys):
    body = _body(capsys, _cli(*FAL, "--spend-balance-after", "41.1", "--spend-budget", "brief: <= $5"))
    assert body["spend"] == {"provider": "fal", "billing": "api", "unit": "usd", "estimate": 0.9, "cap": 1.5,
                             "how": "4 x 15 s x $0.015/s", "balance_after": 41.1,
                             "balance_source": "declared", "budget": "brief: <= $5"}
    assert "no_spend" not in body


def test_cli_balance_after_comes_from_the_spend_guard(capsys, tmp_path, monkeypatch):
    _snapshot(tmp_path, datetime.now(timezone.utc), fal={"ok": True, "balance": 42.6},
              openrouter={"ok": True, "balance": 6.7})
    body = _body(capsys, _cli(*FAL))
    assert body["spend"]["balance_after"] == 41.1
    assert body["spend"]["balance_source"] == "spend_guard"


def test_spend_guard_balance_ignores_stale_or_unread_snapshots(tmp_path):
    _snapshot(tmp_path, NOW, fal={"ok": True, "balance": 42.6}, openrouter={"ok": False})
    root = tmp_path / "org"
    assert ask_run.spend_guard_balance("fal", root=root, now=NOW + timedelta(minutes=30)) == 42.6
    assert ask_run.spend_guard_balance("fal", root=root, now=NOW + timedelta(hours=2)) is None
    assert ask_run.spend_guard_balance("openrouter", root=root, now=NOW) is None
    assert ask_run.spend_guard_balance("fal", root=tmp_path / "nowhere", now=NOW) is None


def test_credits_label_needs_max_credits_and_never_reads_the_guard(capsys, tmp_path):
    _snapshot(tmp_path, datetime.now(timezone.utc), fal={"ok": True, "balance": 42.6})
    args = ("--spend-provider", "higgsfield", "--spend-billing", "account", "--spend-unit", "credits",
            "--spend-estimate", "40", "--spend-cap", "60", "--spend-how", "10 cr/shot")
    body = _body(capsys, _cli(*args, command="node runners/champa_fire.mjs --shots 4 --max-credits 60"))
    assert body["spend"]["unit"] == "credits" and "balance_after" not in body["spend"]
    assert "spend_cap_flag_missing" in _refused(capsys, _cli(*args, command="node x.mjs --max-usd 60"))


@pytest.mark.parametrize("extra,command,want", [
    (FAL, "python tools/bl_render.py --ep 62", "spend_cap_flag_missing"),
    (FAL, "python tools/bl_render.py --max-usd 2", "spend_cap_flag_mismatch"),
    (FAL, "a --max-usd 1.5 --max-usd 9", "spend_cap_flag_mismatch"),
    (FAL, "a --max-usd 1.5 && b --max-usd 9", "spend_command_not_simple (an unquoted &)"),
    (FAL, "python fal_render.py --max-usd 1.5 --max 100", "spend_cap_flag_ambiguous"),
    (("--spend-provider", "fal", "--spend-estimate", "2", "--spend-cap", "1.5", "--spend-how", "x"), RENDER,
     "spend_estimate_over_cap"),
    (("--spend-provider", "fal", "--spend-cap", "1.5", "--spend-how", "x"), RENDER, "estimate and cap are required"),
    (("--spend-provider", "Fal AI", "--spend-estimate", "1", "--spend-cap", "1.5", "--spend-how", "x"), RENDER,
     "invalid_spend: provider"),
    ((*FAL, "--spend-balance-after", "-0.5"), RENDER, "spend_cap_over_balance"),
    ((*FAL, "--no-spend", "a read"), RENDER, "spend_label_conflict"),
    (("--no-spend", "  "), "curl openrouter.ai/api/v1/credits", "--no-spend is empty"),
])
def test_cli_refusals_send_nothing(capsys, extra, command, want):
    assert want in _refused(capsys, _cli(*extra, command=command))


def test_cap_over_the_guard_balance_is_refused(capsys, tmp_path):
    _snapshot(tmp_path, datetime.now(timezone.utc), fal={"ok": True, "balance": 1.0})
    assert "spend_cap_over_balance" in _refused(capsys, _cli(*FAL))


def test_no_spend_reason_travels(capsys):
    body = _body(capsys, _cli("--no-spend", "reads the balance only", command="curl -s openrouter.ai/api/v1/credits"))
    assert body["no_spend"] == "reads the balance only" and "spend" not in body


def test_a_script_ask_reads_the_cap_from_its_argv(capsys):
    """The hub renders a .sh ask as `bash x.sh ...` and reads the flags from [path, *args]; an arg
    with ; or $ in it is one argv word, not shell."""
    base = ["create", "--dry-run", "--host", "contabo", "--role", "cto", "--session", "cto-t", "--why", "w",
            "--script", "Agents-Core@9df4e185:scripts/x.sh", *FAL, "--", "--prompt", "a cat; it's $5"]
    assert _body(capsys, [*base, "--max-usd", "1.5"])["spend"]["cap"] == 1.5
    assert "spend_cap_flag_ambiguous" in _refused(capsys, [*base, "--max-usd", "1.5", "--max", "100"])
    assert "spend_cap_flag_missing" in _refused(capsys, base)


# One list of cases, judged the same way by the Console hub (src/run/spend.js capFlag, its
# test/run-spend-capflag.test.js reads a byte-for-byte copy). The sha256 is pinned on both sides.
FIXTURES = ROOT / "tests" / "fixtures" / "spend-cap-flag.json"
FIXTURES_SHA256 = "939024645bff59032a8087c411ad142bb246d13b8fb41336c108ad19fe3ad2cf"
CASES = json.loads(FIXTURES.read_text(encoding="utf-8"))["cases"]


def test_the_fixtures_file_is_the_pinned_copy():
    assert hashlib.sha256(FIXTURES.read_bytes()).hexdigest() == FIXTURES_SHA256


@pytest.mark.parametrize("case", CASES, ids=[repr(c["command"])[:60] for c in CASES])
def test_cap_flag_judged_like_the_hub(case):
    assert ask_run.cap_flag_check(case["command"], case["unit"], case["cap"]) == case["want"]


def test_amounts_take_at_most_four_decimal_places(capsys):
    args = ("--spend-provider", "fal", "--spend-estimate", "1", "--spend-cap", "1.23456", "--spend-how", "x")
    assert "at most 4 decimal places" in _refused(capsys, _cli(*args, command="python fal_r.py --max-usd 1.23456"))


# ------------------------------------------------------------------ the org MCP tool
@pytest.fixture
def srv():
    from runners import cto_mcp_server
    return cto_mcp_server


def _org(srv, arguments: dict) -> str:
    result = asyncio.run(srv.mcp.call_tool("ask_run", arguments))
    content = result[0] if isinstance(result, tuple) else result
    return content[0].text


MCP = {"host": "contabo", "role": "cto", "session": "cto-t", "why": "render", "command": RENDER, "dry_run": True}
LABEL = {"provider": "fal", "estimate": 0.9, "cap": 1.5, "how": "4 x 15 s x $0.015/s", "balance_after": 41.1}


def test_org_spend_body_equals_the_cli_body(srv, capsys):
    cli = _body(capsys, _cli(*FAL, "--spend-balance-after", "41.1"))
    text = _org(srv, {**MCP, "spend": LABEL})
    assert not text.startswith("ERROR"), text
    assert json.loads(text)["payload"] == cli


def test_org_no_spend_and_refusals(srv):
    text = _org(srv, {**MCP, "command": "curl -s openrouter.ai/api/v1/credits", "no_spend": "balance read"})
    assert json.loads(text)["payload"]["no_spend"] == "balance read"
    assert "spend_cap_flag_missing" in _org(srv, {**MCP, "command": "python r.py", "spend": LABEL})
    assert "unknown field 'price'" in _org(srv, {**MCP, "spend": {**LABEL, "price": 1}})
    assert "spend_label_conflict" in _org(srv, {**MCP, "spend": LABEL, "no_spend": "x"})


def test_org_schema_lists_spend_and_no_spend(srv):
    tools = {t.name: t for t in asyncio.run(srv.mcp.list_tools())}
    props = tools["ask_run"].inputSchema["properties"]
    assert "spend" in props and "no_spend" in props
    assert tools["ask_run"].inputSchema["required"] == ["host", "why"]
    assert "--max-usd" in tools["ask_run"].description
