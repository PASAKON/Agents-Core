"""Envelope mail (ORG_MAIL_ENVELOPE, org restructure P1): the worker Stop hook and
the C-level prompt hook.

T16: with the flag on, the worker hook writes nothing outside its own checkout
(no /Users/gob tree on a box that is not the Mac) and records tasks.session_id.
Before it, ROOT was the Mac literal, so on Contabo the DB write could not import
lib.db and five tasks of 2026-10-13 kept session_id NULL.

Every hook here runs in-process against a tmp ledger and a tmp checkout; the
relay is replaced by a recorder, so no mailbox is written and no pane is woken.
"""
from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from lib import db as db_mod
import tools.send_to_cto as send_to_cto_mod

REPO = Path(__file__).resolve().parent.parent
DEV_HOOK = REPO / "scripts" / "hook-log-dev-reply.py"
PROMPT_HOOK = REPO / "scripts" / "hook-log-prompt.py"
CTO = "abcd1234"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ledger(monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    for k in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    return db_mod.create_task("projA", "developer", "t", "d", owner_cto=CTO, owner_role="cto")


@pytest.fixture
def relays(monkeypatch):
    sent = []
    monkeypatch.setattr(send_to_cto_mod, "send",
                        lambda task_id, msg, **kw: sent.append((task_id, msg, kw)) or True)
    return sent


@pytest.fixture
def writes(monkeypatch):
    """Every path opened for writing, by Path.open or open()."""
    seen: list[str] = []
    real_path_open = pathlib.Path.open

    def path_open(self, mode="r", *a, **kw):
        if any(c in mode for c in "wax+"):
            seen.append(str(self))
        return real_path_open(self, mode, *a, **kw)
    monkeypatch.setattr(pathlib.Path, "open", path_open)
    return seen


def checkout(tmp_path: Path) -> Path:
    """A copy of the hook in a tmp checkout: its own location is its ROOT."""
    root = tmp_path / "Core"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(DEV_HOOK, root / "scripts" / DEV_HOOK.name)
    return root


def msg(role, content, pid=None, **extra):
    r = {"type": role, "message": {"role": role, "content": content}, **extra}
    if pid:
        r["promptId"] = pid
    return r


def tool(name):
    return [{"type": "tool_use", "id": "x", "name": f"mcp__org__{name}", "input": {}}]


def transcript(tmp_path: Path, turns: list[list[dict]]) -> Path:
    p = tmp_path / "sess-0001.jsonl"
    p.write_text("\n".join(json.dumps(r) for t in turns for r in t) + "\n", encoding="utf-8")
    return p


def run_dev(mod, monkeypatch, tp: Path, task_id: str) -> int:
    monkeypatch.setenv("WORKER_TASK_ID", task_id)
    monkeypatch.setenv("WORKER_ROLE", "developer")
    monkeypatch.setenv("WORKER_CTO_ID", CTO)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"transcript_path": str(tp)})))
    return mod.main()


def report_turn():
    return [msg("user", "do it", "p1"),
            msg("assistant", tool("submit_report")),
            msg("user", [{"type": "tool_result", "content": "OK"}], "p1"),
            msg("assistant", [{"type": "text", "text": "Done: 3 files, 12 tests pass."}])]


def plain_turn(pid="p2", text="still working"):
    return [msg("user", "next", pid), msg("assistant", [{"type": "text", "text": text}])]


# ---------------------------------------------------------------- dev hook


def test_flag_off_keeps_the_legacy_root(monkeypatch):
    monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    mod = load(DEV_HOOK, "devhook_off")
    assert mod.ENVELOPE is False and mod.ROOT == mod.LEGACY_ROOT
    assert mod._log_for(None).name == "cto.log" and mod._log_for(CTO).name == f"cto-{CTO}.log"


def test_flag_on_root_is_the_scripts_own_checkout(monkeypatch):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    mod = load(DEV_HOOK, "devhook_on")
    assert mod.ROOT == DEV_HOOK.resolve().parent.parent
    assert mod._log_for(None).parent == mod._log_for(CTO).parent == mod.ROOT / "state" / "logs"


def test_t16_no_file_outside_the_checkout_and_session_id_recorded(
        tmp_path, monkeypatch, ledger, relays, writes):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    root = checkout(tmp_path)
    mod = load(root / "scripts" / DEV_HOOK.name, "devhook_t16")
    assert mod.ROOT == root.resolve()
    tp = transcript(tmp_path, [report_turn()])
    writes.clear()                      # only what the hook itself opens
    assert run_dev(mod, monkeypatch, tp, ledger) == 0

    row = db_mod.get_task(ledger)
    assert row["session_id"] == "sess-0001" and row["last_checkpoint"]
    assert writes, "the report turn writes the log"
    assert all(w.startswith(str(root.resolve())) for w in writes), writes
    assert not any(w.startswith("/Users/gob") for w in writes)
    logs = sorted(p.name for p in (root / "state" / "logs").iterdir())
    assert logs == ["cto-abcd1234.log", "cto.log"]
    assert "[submit_report] Done: 3 files, 12 tests pass." in (root / "state" / "logs" / "cto.log").read_text()
    assert len(relays) == 1 and relays[0][1].startswith("[submit_report] Done")
    assert relays[0][2]["cto_id"] == CTO


def test_a_turn_without_an_event_relays_nothing_but_records_the_session(
        tmp_path, monkeypatch, ledger, relays, writes):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    root = checkout(tmp_path)
    mod = load(root / "scripts" / DEV_HOOK.name, "devhook_quiet")
    # the report was an earlier turn; this turn only worked
    tp = transcript(tmp_path, [report_turn(), plain_turn()])
    writes.clear()
    assert run_dev(mod, monkeypatch, tp, ledger) == 0
    assert relays == [] and writes == []
    assert db_mod.get_task(ledger)["session_id"] == "sess-0001"


@pytest.mark.parametrize("name,kind,prio", [("dev_message", "message", "normal"),
                                            ("file_blocker_issue", "blocker", "urgent"),
                                            ("submit_report", "report", "urgent")])
def test_message_and_blocker_turns_relay(tmp_path, monkeypatch, ledger, relays, name, kind, prio):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    root = checkout(tmp_path)
    mod = load(root / "scripts" / DEV_HOOK.name, f"devhook_{name}")
    tp = transcript(tmp_path, [[msg("user", "go", "p9"), msg("assistant", tool(name))]])
    assert run_dev(mod, monkeypatch, tp, ledger) == 0
    assert len(relays) == 1 and relays[0][1].startswith(f"[{name}] (no closing text")
    kw = relays[0][2]
    assert (kw["kind"], kw["prio"]) == (kind, prio)
    assert kw["subject"].startswith(f"{kind} {ledger}: ") and len(kw["subject"]) <= 80


def test_human_handoff_turn_is_not_relayed_again(tmp_path, monkeypatch, ledger, relays):
    """request_human_handoff sends its own urgent letter (worker_mcp_server);
    the hook relaying the same turn too would be a second letter."""
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    root = checkout(tmp_path)
    mod = load(root / "scripts" / DEV_HOOK.name, "devhook_handoff")
    tp = transcript(tmp_path, [[msg("user", "go", "p9"),
                                msg("assistant", tool("request_human_handoff"))]])
    assert run_dev(mod, monkeypatch, tp, ledger) == 0
    assert relays == []


def test_hub_and_mailbox_down_fail_open(tmp_path, monkeypatch, ledger):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    root = checkout(tmp_path)
    mod = load(root / "scripts" / DEV_HOOK.name, "devhook_down")

    def down(*a, **kw):
        raise OSError("hub unreachable")
    monkeypatch.setattr(db_mod, "get_conn", down)
    monkeypatch.setattr(send_to_cto_mod, "send", down)
    tp = transcript(tmp_path, [report_turn()])
    assert run_dev(mod, monkeypatch, tp, ledger) == 0
    assert (root / "state" / "logs" / "cto.log").exists()   # the log still gets the line


def test_flag_off_still_relays_every_turn(tmp_path, monkeypatch, ledger, relays):
    monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    mod = load(DEV_HOOK, "devhook_legacy")
    monkeypatch.setattr(mod, "ROOT", tmp_path / "Core")     # keep the legacy write off the real tree
    tp = transcript(tmp_path, [report_turn(), plain_turn()])
    assert run_dev(mod, monkeypatch, tp, ledger) == 0
    assert [r[1] for r in relays] == ["still working"]
    assert "subject" not in relays[0][2] and "kind" not in relays[0][2]   # the old call


def test_scan_scopes_events_to_the_current_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    mod = load(DEV_HOOK, "devhook_scan")
    tp = transcript(tmp_path, [report_turn()])
    assert mod._scan_records(tp)[2] == ["submit_report"]
    tp = transcript(tmp_path, [report_turn(), plain_turn()])
    assert mod._scan_records(tp)[2] == []
    # a compaction inside the turn does not reset it
    tp = transcript(tmp_path, [[msg("user", "go", "p1"), msg("assistant", tool("dev_message")),
                                msg("user", "summary", "p1c", isCompactSummary=True),
                                msg("assistant", [{"type": "text", "text": "after"}])]])
    assert mod._scan_records(tp)[2] == ["dev_message"]


def test_rate_limit_comes_from_this_turns_api_error_only(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    mod = load(DEV_HOOK, "devhook_rl")
    prose = [msg("user", "go", "p1"),
             msg("assistant", [{"type": "text", "text": "the API returns 429 on burst; added a retry"}])]
    assert mod._scan_records(transcript(tmp_path, [prose]))[1] is False
    hit = [msg("user", "go", "p2"),
           msg("assistant", [{"type": "text", "text": "You've hit your session limit"}],
               isApiErrorMessage=True, error="rate_limit")]
    assert mod._scan_records(transcript(tmp_path, [prose, hit]))[1] is True
    assert mod._scan_records(transcript(tmp_path, [hit, plain_turn("p3")]))[1] is False
    monkeypatch.delenv("ORG_MAIL_ENVELOPE")
    legacy = load(DEV_HOOK, "devhook_rl_legacy")
    assert legacy._scan_records(transcript(tmp_path, [prose]))[1] is True   # the legacy over-match, kept when off

# ------------------------------------------------------------- prompt hook


def run_prompt(mod, log: Path) -> str:
    mod.LOG = log
    mod.STATE = log.parent / ".pos"
    mod.SID = ""
    mod.STATE.write_text("0")
    out = io.StringIO()
    stdin, sys.stdin = sys.stdin, io.StringIO(json.dumps({"prompt": "status?"}))
    try:
        with redirect_stdout(out):
            mod.main()
    finally:
        sys.stdin = stdin
    return out.getvalue()


def events(n: int, body: int = 0) -> str:
    out = []
    for i in range(n):
        out.append(f"[2026-10-13T10:{i:02d}:00] Developer task-abc{i:03d}: event {i}")
        out += [f"    body {i}.{j}" for j in range(body)]
    return "\n".join(out) + "\n"


def test_prompt_hook_envelope_one_line_per_event(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    monkeypatch.setenv("CTO_SESSION", "1")
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    mod = load(PROMPT_HOOK, "prompthook_env")
    log = tmp_path / "cto.log"
    log.write_text(events(3, body=4), encoding="utf-8")
    body = [l for l in run_prompt(mod, log).splitlines()[2:] if l.strip()]
    assert len(body) == 3
    assert all("[+4 lines in" in l for l in body) and not any("body 0.1" in l for l in body)


def test_prompt_hook_envelope_caps_at_ten_lines_newest_kept(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    monkeypatch.setenv("CTO_SESSION", "1")
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    mod = load(PROMPT_HOOK, "prompthook_cap")
    log = tmp_path / "cto.log"
    log.write_text(events(25), encoding="utf-8")
    body = [l for l in run_prompt(mod, log).splitlines()[2:] if l.strip()]
    assert len(body) == 10
    assert body[0].startswith("(+16 earlier events in") and body[-1].endswith("event 24")


def test_prompt_hook_flag_off_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    monkeypatch.setenv("CTO_SESSION", "1")
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    mod = load(PROMPT_HOOK, "prompthook_off")
    log = tmp_path / "cto.log"
    log.write_text(events(3, body=4), encoding="utf-8")
    out = run_prompt(mod, log)
    assert "body 0.1" in out and "[+4 lines in" not in out
