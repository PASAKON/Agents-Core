"""All inputs are synthetic; never invoke the real Infisical helper."""

import io
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools import secret_card


@pytest.fixture
def fake_helper(tmp_path, monkeypatch):
    helper = tmp_path / "infisical_setup.py"
    helper.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "value = sys.stdin.read()\n"
        "with open(os.environ['FAKE_CALLS'], 'a') as out:\n"
        "    out.write(json.dumps([sys.argv[1:], value]) + '\\n')\n"
        "print(value)\n"
        "print(value, file=sys.stderr)\n"
        "sys.exit(7 if sys.argv[4] == 'FAIL_KEY' else 0)\n"
    )
    helper.chmod(0o755)
    calls = tmp_path / "calls.jsonl"
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("FAKE_CALLS", str(calls))
    return calls


def invoke(payload):
    return subprocess.run(
        [sys.executable, str(Path(secret_card.__file__)), "Fake-Project", "dev"],
        input=payload, text=True, capture_output=True,
    )


def test_storage_stdin_and_one_line(fake_helper):
    result = invoke(json.dumps({"API_KEY": "fake-only-1234", "LOGIN_ID": 123456,
                                "EMPTY_KEY": "", "SKIP_KEY": None,
                                "_steps": {"mt5": False}}) + '\nnot-json\n')
    assert result.returncode == 0
    calls = [json.loads(line) for line in fake_helper.read_text().splitlines()]
    assert calls == [
        [["put", "Fake-Project", "dev", "API_KEY", "--stdin"], "fake-only-1234"],
        [["put", "Fake-Project", "dev", "LOGIN_ID", "--stdin"], "123456"],
    ]
    assert result.stdout == "STEP store ok API_KEY …1234\nSTEP store ok LOGIN_ID …3456\n"
    assert result.stderr == ""


def test_failure_continues_without_leaking(fake_helper):
    result = invoke(json.dumps({"FAIL_KEY": "fake-failure-value", "NEXT_KEY": "abc"}))
    assert result.returncode != 0
    assert result.stdout == "STEP store fail FAIL_KEY put failed\nSTEP store ok NEXT_KEY …••••\n"
    assert result.stderr == ""
    assert len(fake_helper.read_text().splitlines()) == 2


@pytest.mark.parametrize("payload", [
    "", "not json", "[]", '{"AA":"x","AA":"y"}',
    '{"AA":"valid-fake","bad":"fake"}', '{"AA":true}',
    '{"AA":{}}', '{"AA":NaN}', '{"AA":"fake\\nvalue"}',
    '{"AA":" padded "}', '{"_steps":[]}', '{"_steps":{"mt5":"yes"}}',
    json.dumps({f"KEY_{i}": "fake" for i in range(17)}),
])
def test_invalid_form_has_no_writes(fake_helper, payload):
    result = invoke(payload)
    assert result.returncode == 1
    assert result.stdout == "STEP store fail invalid form\n"
    assert result.stderr == ""
    assert not fake_helper.exists()


def test_hook_receives_only_destination_and_steps(fake_helper, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"AA":"fake-value","_steps":{"mt5":true}}'))
    seen = []
    monkeypatch.setattr(secret_card, "run_later_steps", lambda *args: seen.append(args) or 3)
    assert secret_card.main(["Fake-Project", "dev"]) == 3
    assert seen == [("Fake-Project", "dev", {"mt5": True})]


def test_failure_does_not_run_hook(fake_helper, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"FAIL_KEY":"fake-value"}'))
    monkeypatch.setattr(secret_card, "run_later_steps", lambda *args: pytest.fail("hook ran"))
    assert secret_card.main(["Fake-Project", "dev"]) == 1


def test_launch_error_is_safe(fake_helper, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"AA":"fake-value"}'))
    def unavailable(*args, **kwargs):
        raise OSError("fake-value")
    monkeypatch.setattr(subprocess, "run", unavailable)
    assert secret_card.main(["Fake-Project", "dev"]) == 1
    assert capsys.readouterr().out == "STEP store fail AA put failed\n"
