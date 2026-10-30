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
import os
import pathlib
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from lib import db as db_mod
from lib import mailbox
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
    """Every path opened for writing, by Path.open or by os.open (the hook's
    log append opens relative to a directory fd: the path is resolved
    through /proc/self/fd)."""
    seen: list[str] = []
    real_path_open = pathlib.Path.open
    real_os_open = os.open

    def path_open(self, mode="r", *a, **kw):
        if any(c in mode for c in "wax+"):
            seen.append(str(self))
        return real_path_open(self, mode, *a, **kw)

    def os_open(path, flags, mode=0o777, *, dir_fd=None):
        fd = real_os_open(path, flags, mode, dir_fd=dir_fd)
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND):
            base = os.readlink(f"/proc/self/fd/{dir_fd}") if dir_fd is not None else ""
            seen.append(os.path.join(base, os.fspath(path)))
        return fd
    monkeypatch.setattr(pathlib.Path, "open", path_open)
    monkeypatch.setattr(os, "open", os_open)
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


def run_dev(mod, monkeypatch, tp: Path, task_id: str, *, cto: str | None = CTO,
            owner_role: str | None = None) -> int:
    monkeypatch.setenv("WORKER_TASK_ID", task_id)
    monkeypatch.setenv("WORKER_ROLE", "developer")
    for key, value in (("WORKER_CTO_ID", cto), ("WORKER_CTO_ROLE", owner_role)):
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
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


def test_flag_off_root_is_the_scripts_own_checkout_too(monkeypatch):
    """Wake chain W1 (2026-10-30): the Mac literal is gone. With the flag off
    ROOT was /Users/gob/..., so on Contabo every worker report failed to import
    tools.send_to_cto and reached no owner."""
    monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)
    mod = load(DEV_HOOK, "devhook_off")
    assert mod.ENVELOPE is False and mod.ROOT == DEV_HOOK.resolve().parent.parent
    assert not hasattr(mod, "LEGACY_ROOT")
    assert mod._log_for(None).name == "cto.log" and mod._log_for(CTO).name == f"cto-{CTO}.log"
    assert mod._log_for(None).parent == mod._log_for(CTO).parent == mod.ROOT / "state" / "logs"


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
    assert row["session_id"] == "sess-0001"
    assert row["last_checkpoint"] is None        # the Stop hook leaves dev_message's column alone
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


def guarded_checkout(tmp_path: Path, name: str):
    """checkout() + the copy loaded. A copy whose ROOT is not its own checkout
    (the old flag-off Mac literal) fails here, before it can write anywhere."""
    root = checkout(tmp_path)
    mod = load(root / "scripts" / DEV_HOOK.name, name)
    assert mod.ROOT == root.resolve()
    return root, mod


def flag(monkeypatch, on) -> None:
    if on:
        monkeypatch.setenv("ORG_MAIL_ENVELOPE", "1")
    else:
        monkeypatch.delenv("ORG_MAIL_ENVELOPE", raising=False)


def api_limit(pid="p5"):
    """This turn's own API error record: the session hit its limit."""
    return [msg("user", "go on", pid),
            msg("assistant", [{"type": "text", "text": "You've hit your session limit"}],
                isApiErrorMessage=True, error="rate_limit")]


def prose_429(pid="p0"):
    """An earlier turn whose prose only mentions 429 (no API error record)."""
    return [msg("user", "go", pid),
            msg("assistant", [{"type": "text", "text": "Baseline: 1429 tests collected; "
                                                       "the API returns HTTP 429 on burst"}])]


def test_flag_off_a_progress_turn_sends_nothing(tmp_path, monkeypatch, ledger, relays, writes):
    """Wake chain W1 review: with ROOT fixed, the flag-off path relayed every
    Stop turn that had text, as a kind-less letter that woke the owner each
    time. Only an event turn (or a rate limit) is logged and relayed now."""
    flag(monkeypatch, False)
    root, mod = guarded_checkout(tmp_path, "devhook_off_quiet")
    tp = transcript(tmp_path, [report_turn(),
                               plain_turn(text="The full suite is running; I will report when it ends.")])
    writes.clear()
    assert run_dev(mod, monkeypatch, tp, ledger) == 0
    assert relays == [] and writes == []
    assert db_mod.get_task(ledger)["session_id"] == "sess-0001"


def test_flag_off_a_report_turn_names_its_kind(tmp_path, monkeypatch, ledger, relays):
    flag(monkeypatch, False)
    root, mod = guarded_checkout(tmp_path, "devhook_off_report")
    tp = transcript(tmp_path, [report_turn()])
    assert run_dev(mod, monkeypatch, tp, ledger) == 0
    assert len(relays) == 1
    _, body, kw = relays[0]
    assert body == "report · urgent · [submit_report] Done: 3 files, 12 tests pass."
    assert kw == {"role": "developer", "cto_id": CTO, "owner_role": "cto",
                  "kind": "report", "prio": "urgent"}
    # no envelope fields with the flag off: the body's first word carries the kind
    assert mailbox.letter_kind(None, body) == "report"


@pytest.mark.parametrize("owner_role,woken", [("cto", False), ("project_head", True)])
def test_flag_off_a_report_wakes_a_ph_box_never_a_c_level_box(
        tmp_path, monkeypatch, ledger, owner_role, woken):
    """Token rule 2 through the real send_to_cto: a report waits in a C-level
    box for its next prompt; a Project Head box is woken (it must review)."""
    flag(monkeypatch, False)
    root, mod = guarded_checkout(tmp_path, f"devhook_off_wake_{owner_role}")
    letters, wakes = [], []
    monkeypatch.setattr(send_to_cto_mod.mailbox, "send", lambda *a, **kw: letters.append((a, kw)))
    monkeypatch.setattr(send_to_cto_mod, "_attempt_wake", lambda *a: wakes.append(a))
    tp = transcript(tmp_path, [report_turn()])
    assert run_dev(mod, monkeypatch, tp, ledger, owner_role=owner_role) == 0
    assert len(letters) == 1 and letters[0][0][:2] == (owner_role, CTO)
    assert letters[0][1] == {}                  # flag off: the letter has no envelope fields
    assert bool(wakes) is woken


def test_flag_off_the_letter_is_at_most_600_chars(tmp_path, monkeypatch, ledger, relays):
    flag(monkeypatch, False)
    root, mod = guarded_checkout(tmp_path, "devhook_off_cap")
    turn = report_turn()
    turn[-1] = msg("assistant", [{"type": "text", "text": "x" * 3000}])
    assert run_dev(mod, monkeypatch, transcript(tmp_path, [turn]), ledger) == 0
    body = relays[0][1]
    assert len(body) == mod.RELAY_MAX_CHARS == 600 and body.endswith("...[truncated]")


@pytest.mark.parametrize("on", [False, True])
def test_old_429_prose_then_a_report_keeps_review(tmp_path, monkeypatch, ledger, relays, on):
    """Wake chain W1 review (blocker): the flag-off scan matched "429" in any
    earlier assistant prose, so the Stop after submit_report set a task in
    review to rate_limited (merge_task then refuses it, nothing reaps it)."""
    flag(monkeypatch, on)
    root, mod = guarded_checkout(tmp_path, f"devhook_429_{on}")
    db_mod.update_status(ledger, "review")
    tp = transcript(tmp_path, [prose_429(), report_turn()])
    assert run_dev(mod, monkeypatch, tp, ledger) == 0
    row = db_mod.get_task(ledger)
    assert row["status"] == "review" and row["retry_after_ts"] is None
    assert len(relays) == 1
    assert "rate limit" not in relays[0][1] and "auto-resume" not in relays[0][1]


@pytest.mark.parametrize("on", [False, True])
@pytest.mark.parametrize("status,after", [("in_progress", "rate_limited"), ("review", "review"),
                                          ("done", "done"), ("cancelled", "cancelled")])
def test_a_real_rate_limit_moves_only_a_task_at_work(
        tmp_path, monkeypatch, ledger, relays, on, status, after):
    flag(monkeypatch, on)
    root, mod = guarded_checkout(tmp_path, f"devhook_rl_{on}_{status}")
    db_mod.update_status(ledger, status)
    assert run_dev(mod, monkeypatch, transcript(tmp_path, [api_limit()]), ledger) == 0
    row = db_mod.get_task(ledger)
    assert row["status"] == after
    assert bool(row["retry_after_ts"]) is (after == "rate_limited")
    assert len(relays) == 1 and "rate limit hit this turn" in relays[0][1]
    assert relays[0][2]["kind"] == "fyi"        # no event: a fyi, which never wakes a C-level box


@pytest.mark.parametrize("on", [False, True])
def test_the_stop_hook_keeps_the_dev_message_text(tmp_path, monkeypatch, ledger, relays, on):
    """runners/worker_mcp_server.dev_message keeps the worker's full text in
    tasks.last_checkpoint (GH #54); the Stop right after wrote a timestamp over it."""
    flag(monkeypatch, on)
    root, mod = guarded_checkout(tmp_path, f"devhook_cp_{on}")
    db_mod.set_fields(ledger, last_checkpoint="BLOCKED: the staging key is missing")
    tp = transcript(tmp_path, [[msg("user", "go", "p9"), msg("assistant", tool("dev_message"))]])
    assert run_dev(mod, monkeypatch, tp, ledger) == 0
    row = db_mod.get_task(ledger)
    assert row["last_checkpoint"] == "BLOCKED: the staging key is missing"
    assert row["session_id"] == "sess-0001"


def test_an_ownerless_task_is_logged_not_relayed(tmp_path, monkeypatch, ledger, relays):
    flag(monkeypatch, False)
    root, mod = guarded_checkout(tmp_path, "devhook_ownerless")
    assert run_dev(mod, monkeypatch, transcript(tmp_path, [report_turn()]), ledger, cto=None) == 0
    assert relays == []
    logs = root / "state" / "logs"
    assert sorted(p.name for p in logs.iterdir()) == ["cto.log"]
    assert "[submit_report] Done: 3 files" in (logs / "cto.log").read_text(encoding="utf-8")


@pytest.mark.parametrize("on", [False, True])
def test_a_planted_link_in_state_logs_is_not_followed(tmp_path, monkeypatch, ledger, relays, on):
    """state/logs is writable by another account and the hook runs as root on
    Contabo: a log name planted as a symlink or as a second hard link is
    skipped, its target untouched. The relay still goes out."""
    flag(monkeypatch, on)
    root, mod = guarded_checkout(tmp_path, f"devhook_link_{on}")
    logs = root / "state" / "logs"
    logs.mkdir(parents=True)
    victim, other = tmp_path / "victim.txt", tmp_path / "other.txt"
    victim.write_text("keep\n", encoding="utf-8")
    other.write_text("keep\n", encoding="utf-8")
    (logs / "cto.log").symlink_to(victim)
    os.link(other, logs / f"cto-{CTO}.log")
    assert run_dev(mod, monkeypatch, transcript(tmp_path, [report_turn()]), ledger) == 0
    assert victim.read_text(encoding="utf-8") == "keep\n"
    assert other.read_text(encoding="utf-8") == "keep\n"
    assert (logs / "cto.log").is_symlink() and len(relays) == 1


def test_without_dir_fd_the_log_is_written_and_a_link_skipped(tmp_path, monkeypatch, ledger, relays):
    """A platform with no dir_fd (Windows, as in lib.mailbox) takes a plain
    append; it still refuses a log name that is a symlink."""
    flag(monkeypatch, False)
    root, mod = guarded_checkout(tmp_path, "devhook_nodirfd")
    monkeypatch.setattr(mod, "_DIRFD_OK", False)
    logs = root / "state" / "logs"
    logs.mkdir(parents=True)
    victim = tmp_path / "victim.txt"
    victim.write_text("keep\n", encoding="utf-8")
    (logs / "cto.log").symlink_to(victim)
    assert run_dev(mod, monkeypatch, transcript(tmp_path, [report_turn()]), ledger) == 0
    assert victim.read_text(encoding="utf-8") == "keep\n"
    assert "[submit_report] Done: 3 files" in (logs / f"cto-{CTO}.log").read_text(encoding="utf-8")


def test_a_planted_logs_directory_link_is_not_followed(tmp_path, monkeypatch, ledger, relays):
    flag(monkeypatch, False)
    root, mod = guarded_checkout(tmp_path, "devhook_dirlink")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / "state").mkdir()
    (root / "state" / "logs").symlink_to(elsewhere, target_is_directory=True)
    assert run_dev(mod, monkeypatch, transcript(tmp_path, [report_turn()]), ledger) == 0
    assert list(elsewhere.iterdir()) == [] and len(relays) == 1


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
    off = load(DEV_HOOK, "devhook_rl_off")
    # flag off reads the same records (wake chain W1 review): prose is not a limit
    assert off._scan_records(transcript(tmp_path, [prose]))[1] is False
    assert off._scan_records(transcript(tmp_path, [prose, hit]))[1] is True
    assert off._scan_records(transcript(tmp_path, [hit, plain_turn("p3")]))[1] is False

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
