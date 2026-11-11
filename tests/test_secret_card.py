"""Only synthetic values and a local fake helper; no credential/service access."""
import io
import json
from pathlib import Path
import sys

import pytest

from tools import secret_card as tool


@pytest.fixture
def fake(monkeypatch, tmp_path):
    helper = tmp_path / "fake_helper.py"
    log = tmp_path / "calls.jsonl"
    helper.write_text(
        "import json, sys\n"
        f"with open({str(log)!r}, 'a') as f:\n"
        "    f.write(json.dumps([sys.argv[1:], sys.stdin.read()]) + '\\n')\n"
        "print('fake-helper-private-output')\n"
        "print('fake-helper-private-error', file=sys.stderr)\n"
        "sys.exit(1 if 'FAIL_PASSWORD' in sys.argv else 0)\n"
    )
    monkeypatch.setattr(tool, "HELPER", helper)
    return log


def invoke(monkeypatch, payload, extra=()):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload) + '\nignored next line\n'))
    return tool.main(["Demo", "dev", *extra])


def calls(log):
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_default_helper_is_sibling():
    assert tool.HELPER == Path(tool.__file__).with_name("infisical_setup.py")


def test_path_cannot_override_helper(fake, monkeypatch, tmp_path, capsys):
    planted = tmp_path / "infisical_setup.py"
    planted.write_text("raise RuntimeError('planted helper ran')\n")
    planted.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert invoke(monkeypatch, {"TEST_PASSWORD": "fakepass"}) == 0
    assert calls(fake) == [[["put", "Demo", "dev", "TEST_PASSWORD", "--stdin"], "fakepass\n"]]
    assert capsys.readouterr().out == "STEP store ok TEST_PASSWORD set\n"


@pytest.mark.parametrize("length", [1, 4, 8, 19, 20, 30])
def test_suffix_threshold(fake, monkeypatch, capsys, length):
    value = "x" * length
    assert invoke(monkeypatch, {"TEST_API_KEY": value}) == 0
    output = capsys.readouterr()
    expected = "…xxxx" if length >= 20 else "set"
    assert output.out == f"STEP store ok TEST_API_KEY {expected}\n"
    assert output.err == ""


def test_metadata_passed_to_every_put(fake, monkeypatch):
    metas = ["provider_name=fake", "console_url=https://example.test/?a=b",
             "scope=read", "expires=never", "owner=test"]
    extra = [arg for item in metas for arg in ("--meta", item)]
    extra += ["--comment", "synthetic test"]
    assert invoke(monkeypatch, {"ONE_PASSWORD": "fakeone", "TWO_PASSWORD": "faketwo"}, extra) == 0
    for argv, value in calls(fake):
        assert argv[5:] == extra
        assert value.strip() not in argv


@pytest.mark.parametrize("item", ["owner", "Owner=x", "owner1=x", "=x", "own-er=x", "owner=", "owner= "])
def test_invalid_metadata(fake, monkeypatch, item):
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, {"TEST_PASSWORD": "fakepass"}, ["--meta", item])
    assert error.value.code == 2
    assert not fake.exists()


def test_failure_continues_and_does_not_run_hook(fake, monkeypatch, capsys):
    monkeypatch.setattr(tool, "after_store", lambda steps: pytest.fail("hook ran"))
    assert invoke(monkeypatch, {"FAIL_PASSWORD": "fakefail", "OK_PASSWORD": "fakegood"}) == 1
    assert len(calls(fake)) == 2
    assert capsys.readouterr().out == "STEP store fail FAIL_PASSWORD\nSTEP store ok OK_PASSWORD set\n"


def test_skips_and_hook(fake, monkeypatch):
    seen = []
    monkeypatch.setattr(tool, "after_store", seen.append)
    assert invoke(monkeypatch, {"NO_PASSWORD": None, "EMPTY_PASSWORD": "", "_steps": {"mt5": True}}) == 0
    assert not fake.exists()
    assert seen == [{"mt5": True}]


@pytest.mark.parametrize("payload", [[], {"bad key": "fake"}, {"TEST_PASSWORD": 123},
    {"TEST_PASSWORD": "fake\nline"}, {"TEST_PASSWORD": " fake"}, {"_steps": []},
    {"_steps": {"mt5": "yes"}}])
def test_invalid_input_before_any_put(fake, monkeypatch, capsys, payload):
    assert invoke(monkeypatch, payload) == 1
    assert not fake.exists()
    assert capsys.readouterr().out == "STEP store fail invalid input\n"


def test_malformed_json(fake, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"fake-private-input"'))
    assert tool.main(["Demo", "dev"]) == 1
    assert not fake.exists()
    assert capsys.readouterr().out == "STEP store fail invalid input\n"


def test_spawn_failure(fake, monkeypatch, capsys):
    def unavailable(*args, **kwargs):
        raise OSError("fake-private-error")
    monkeypatch.setattr(tool.subprocess, "run", unavailable)
    assert invoke(monkeypatch, {"TEST_PASSWORD": "fakepass"}) == 1
    assert capsys.readouterr().out == "STEP store fail TEST_PASSWORD\n"
