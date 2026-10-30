"""scripts/hook-log-dev-reply.py: ROOT is the script's own checkout, flag on or off
(wake chain W1, design C1, 2026-10-30).

With ORG_MAIL_ENVELOPE off (the default, and the live state on Contabo) ROOT used
to be the Mac literal. On Contabo that tree holds no lib/ or tools/, so the
hub write and the relay to the owning Project Head or C-level failed inside
`except: pass`: no Claude worker's report reached its owner.

The end-to-end test runs the real script in a fresh interpreter from a tmp
checkout whose lib/ and tools/ are recording stubs: no hub, no mailbox, no
tmux. Before it spawns anything it loads the copy in-process and checks ROOT,
so a run against the old script fails there and never writes a log line
outside tmp_path.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DEV_HOOK = REPO / "scripts" / "hook-log-dev-reply.py"
TASK = "task-0a1b2c3d"
OWNER = "9f8e7d6c"

# lib.db: the UPDATEs, lib.config: the label, tools.send_to_cto: the relay. Each
# records its call as one JSON line in $STUB_RECORD.
_STUBS = {
    "lib/__init__.py": "",
    "lib/db.py": '''\
import json, os
from contextlib import contextmanager


class _Conn:
    def execute(self, sql, params=()):
        with open(os.environ["STUB_RECORD"], "a", encoding="utf-8") as f:
            f.write(json.dumps({"db": " ".join(sql.split()[:3]), "params": list(params)}) + "\\n")


@contextmanager
def get_conn(**kw):
    yield _Conn()
''',
    "lib/config.py": '''\
def display_for(role):
    return "Developer"
''',
    "tools/__init__.py": "",
    "tools/send_to_cto.py": '''\
import json, os


def send(from_id, message, **kw):
    with open(os.environ["STUB_RECORD"], "a", encoding="utf-8") as f:
        f.write(json.dumps({"send": [from_id, message], "kw": kw}) + "\\n")
    return True
''',
}

_ENV_STRIP = ("ORG_MAIL_ENVELOPE", "ORG_ROOT", "PYTHONPATH", "PYTHONHOME",
              "WORKER_TASK_ID", "WORKER_ROLE", "WORKER_CTO_ID", "WORKER_CTO_ROLE",
              "CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _checkout(tmp_path: Path, stubs: bool = True) -> Path:
    """<tmp>/Core/scripts/hook-log-dev-reply.py (+ stub lib/ and tools/)."""
    root = tmp_path / "Core"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(DEV_HOOK, root / "scripts" / DEV_HOOK.name)
    if stubs:
        for rel, text in _STUBS.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
    return root


def _report_transcript(tmp_path: Path) -> Path:
    recs = [
        {"type": "user", "promptId": "p1", "message": {"role": "user", "content": "do it"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "x", "name": "mcp__org__submit_report", "input": {}}]}},
        {"type": "user", "promptId": "p1", "message": {"role": "user", "content": [
            {"type": "tool_result", "content": "OK"}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Done: PR ready for review, 4 tests pass."}]}},
    ]
    p = tmp_path / "sess-w1root.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    return p


@pytest.mark.parametrize("flag", [None, "1"])
def test_root_is_the_scripts_own_checkout_with_the_flag_on_or_off(tmp_path, monkeypatch, flag):
    if flag is None:
        monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    else:
        monkeypatch.setenv("ORG_MAIL_ENVELOPE", flag)
    root = _checkout(tmp_path, stubs=False)
    mod = _load(root / "scripts" / DEV_HOOK.name, f"devhook_root_{flag}")
    assert mod.ROOT == root.resolve()
    assert mod._log_for(None) == root.resolve() / "state" / "logs" / "cto.log"
    assert mod._log_for(OWNER) == root.resolve() / "state" / "logs" / f"cto-{OWNER}.log"
    assert not hasattr(mod, "LEGACY_ROOT")


def test_a_link_to_the_checkout_resolves_to_the_checkout(tmp_path, monkeypatch):
    """/opt/mooniex-agents is a compat link to the Contabo checkout."""
    monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    root = _checkout(tmp_path, stubs=False)
    link = tmp_path / "compat-link"
    link.symlink_to(root, target_is_directory=True)
    mod = _load(link / "scripts" / DEV_HOOK.name, "devhook_link")
    assert mod.ROOT == root.resolve()


def test_flag_off_a_worker_report_reaches_its_project_head(tmp_path, monkeypatch):
    """The live Contabo case: flag off, a PH-owned task, the worker's report turn.
    The hub write, the relay and both log lines all go through the checkout
    the script runs from."""
    monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    root = _checkout(tmp_path)
    # the guard: an old copy fails here, before anything runs
    assert _load(root / "scripts" / DEV_HOOK.name, "devhook_guard").ROOT == root.resolve()

    record = tmp_path / "calls.jsonl"
    env = {k: v for k, v in os.environ.items() if k not in _ENV_STRIP}
    env.update({"WORKER_TASK_ID": TASK, "WORKER_ROLE": "developer",
                "WORKER_CTO_ID": OWNER, "WORKER_CTO_ROLE": "project_head",
                "STUB_RECORD": str(record)})
    tp = _report_transcript(tmp_path)
    res = subprocess.run([sys.executable, "-I", str(root / "scripts" / DEV_HOOK.name)],
                         input=json.dumps({"transcript_path": str(tp)}), cwd=str(tmp_path),
                         capture_output=True, text=True, env=env, timeout=30)
    assert res.returncode == 0, res.stderr

    calls = [json.loads(line) for line in record.read_text(encoding="utf-8").splitlines()]
    db_calls = [c for c in calls if "db" in c]
    sends = [c for c in calls if "send" in c]
    assert [c["db"] for c in db_calls] == ["UPDATE tasks SET"]
    assert db_calls[0]["params"][0] == "sess-w1root" and db_calls[0]["params"][-1] == TASK
    assert sends == [{"send": [TASK, "Done: PR ready for review, 4 tests pass."],
                      "kw": {"role": "developer", "cto_id": OWNER, "owner_role": "project_head"}}]

    logs = root / "state" / "logs"
    assert sorted(p.name for p in logs.iterdir()) == ["cto-9f8e7d6c.log", "cto.log"]
    for name in ("cto.log", f"cto-{OWNER}.log"):
        assert f"Developer {TASK}: Done: PR ready for review" in (logs / name).read_text(encoding="utf-8")
