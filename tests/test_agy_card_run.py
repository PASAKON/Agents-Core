"""Tests for AGY CardRun (`tools/agy_card_run.py`) and AGY session wake in `tools/mail_wake.py`."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import claude_quota, mailbox, org_flags, ph_state  # noqa: E402
from tools import agy_card_run, ask_run, mail_wake, ph_brain, send_to_cxo  # noqa: E402

CONV_UUID = "aced3034-2643-403e-ac26-42f1884593d6"
OLDER_UUID = "11111111-2222-3333-4444-555555555555"


def test_detect_conversation_id_from_flag_env_and_brain_dir(tmp_path):
    brain = tmp_path / "brain"
    d1 = brain / OLDER_UUID
    d2 = brain / CONV_UUID
    not_uuid = brain / "not-a-uuid"
    d1.mkdir(parents=True)
    time.sleep(0.01)
    d2.mkdir(parents=True)
    not_uuid.mkdir(parents=True)

    # 1. Explicit flag wins
    assert (
        agy_card_run.detect_conversation_id(
            "explicit-conv-id",
            env={"AGY_CONVERSATION_ID": OLDER_UUID},
            brain_dir=brain,
        )
        == "explicit-conv-id"
    )
    # 2. Env var wins over brain dir
    assert (
        agy_card_run.detect_conversation_id(
            None,
            env={"AGY_CONVERSATION_ID": OLDER_UUID},
            brain_dir=brain,
        )
        == OLDER_UUID
    )
    # 3. Newest UUID directory in brain_dir
    assert agy_card_run.detect_conversation_id(None, env={}, brain_dir=brain) == CONV_UUID


def test_resolve_identity_defaults_and_overrides(tmp_path):
    box, role, sid, conv = agy_card_run.resolve_identity(
        env={"AGY_CONVERSATION_ID": CONV_UUID},
        brain_dir=tmp_path,
    )
    assert box == "cto-agy-aced3034"
    assert role == "cto"
    assert sid == "agy-aced3034"
    assert conv == CONV_UUID

    # Explicit takeover session
    box2, role2, sid2, conv2 = agy_card_run.resolve_identity(
        session="cmo-e785343f",
        conversation_id=CONV_UUID,
        env={},
        brain_dir=tmp_path,
    )
    assert (box2, role2, sid2, conv2) == ("cmo-e785343f", "cmo", "e785343f", CONV_UUID)


def test_register_and_load_session_refuses_symlinks(tmp_path):
    sdir = tmp_path / "agy-sessions"
    rec = agy_card_run.register_session(
        box="cto-agy-aced3034",
        role="cto",
        conversation_id=CONV_UUID,
        card_id="RUN-20261108-1200-abcd",
        sessions_dir=sdir,
        env={"ORG_HOST": "contabo"},
    )
    assert rec["box"] == "cto-agy-aced3034"
    assert rec["conversation_id"] == CONV_UUID
    assert rec["cards"] == ["RUN-20261108-1200-abcd"]

    loaded = agy_card_run.load_session("cto-agy-aced3034", sessions_dir=sdir)
    assert loaded is not None and loaded["conversation_id"] == CONV_UUID

    # Symlinked session file is refused
    evil = sdir / "cto-evil.json"
    evil.symlink_to(sdir / "cto-agy-aced3034.json")
    assert agy_card_run.load_session("cto-evil", sessions_dir=sdir) is None


def test_ask_run_env_box_supports_agy_conversation_id():
    req = ask_run.resolve_requester(
        None,
        None,
        None,
        env={"AGY_CONVERSATION_ID": CONV_UUID, "AGY_ROLE": "cmo"},
    )
    assert req == {"session": "cmo-agy-aced3034", "role": "cmo"}


def test_passthrough_create_injects_identity_registers_session_and_spawns_watcher(tmp_path, monkeypatch):
    sdir = tmp_path / "agy-sessions"
    seen_argv = []
    watched = []

    def fake_ask_run_main(argv):
        seen_argv.append(argv)
        print("RUN-20261108-1500-beef")
        print("https://terminal.mooniex.com/run#RUN-20261108-1500-beef")
        return 0

    monkeypatch.setattr(ask_run, "main", fake_ask_run_main)
    monkeypatch.setattr(
        agy_card_run,
        "spawn_card_watcher",
        lambda cid, box, **kw: watched.append((cid, box)) or 4242,
    )

    rc = agy_card_run.run_passthrough(
        "create",
        [
            "--host",
            "contabo",
            "--command",
            "systemctl status mooniex-console",
            "--why",
            "org-rule: check status",
            "--conversation",
            CONV_UUID,
        ],
        sessions_dir=sdir,
        env={"ORG_HOST": "mac"},
    )
    assert rc == 0
    assert seen_argv == [
        [
            "create",
            "--host",
            "contabo",
            "--command",
            "systemctl status mooniex-console",
            "--why",
            "org-rule: check status",
            "--role",
            "cto",
            "--session",
            "cto-agy-aced3034",
        ]
    ]
    # On Mac (peer host), watcher is spawned automatically
    assert watched == [("RUN-20261108-1500-beef", "cto-agy-aced3034")]
    saved = agy_card_run.load_session("cto-agy-aced3034", sessions_dir=sdir)
    assert saved is not None
    assert saved["cards"] == ["RUN-20261108-1500-beef"]


def test_wake_session_drains_letters_formats_notes_and_tail_and_falls_back_on_quota(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    sdir = tmp_path / "agy-sessions"
    monkeypatch.setattr(mailbox, "INBOX_ROOT", inbox)
    monkeypatch.setattr(ph_brain, "QUOTA_SNAPSHOT", tmp_path / "no-snapshot.json")

    box = "cto-agy-aced3034"
    agy_card_run.register_session(
        box=box,
        role="cto",
        conversation_id=CONV_UUID,
        sessions_dir=sdir,
        env={"ORG_HOST": "contabo"},
    )

    # Deliver a RUN result letter with output tail and a Q answer letter with full CEO note
    p1 = mailbox.send("cto", "agy-aced3034", "RUN-20261108-1500-beef done (exit 0)", "run-inbox", "hub", root=inbox)
    d1 = json.loads(p1.read_text())
    d1["tail"] = "active (running) since Sun 2026-11-08\nMemory: 42.1M"
    p1.write_text(json.dumps(d1))

    p2 = mailbox.send("cto", "agy-aced3034", "Q-20261108-1501-cafe answered: Tonight", "run-inbox", "hub", root=inbox)
    d2 = json.loads(p2.read_text())
    d2["answer"] = {"choice": 0, "label": "Tonight", "text": "Deploy after 22:30 TH and ping me on LINE"}
    p2.write_text(json.dumps(d2))

    calls = []

    def fake_call_agy(prompt, *, conversation_id, model, **kw):
        calls.append((model, conversation_id, prompt))
        if model == ph_brain.PRIMARY_MODEL:
            return {
                "ok": False,
                "returncode": 1,
                "model": model,
                "conversation_id": conversation_id,
                "response": "You have exhausted your quota on this model",
                "limit_hit": "you have exhausted your quota on this model",
            }
        return {
            "ok": True,
            "returncode": 0,
            "model": model,
            "conversation_id": conversation_id,
            "response": "Proceeding with tonight's deploy.",
            "limit_hit": None,
        }

    monkeypatch.setattr(agy_card_run, "_call_agy_cli", fake_call_agy)

    res = agy_card_run.wake_session(box, sessions_dir=sdir, inbox_root=inbox)
    assert res["ok"] is True
    assert res["woke"] is True
    assert res["model"] == ph_brain.FALLBACK_MODEL
    assert [m for m, _, _ in calls] == [ph_brain.PRIMARY_MODEL, ph_brain.FALLBACK_MODEL]

    prompt_sent = calls[-1][2]
    assert "active (running) since Sun 2026-11-08" in prompt_sent
    assert "Deploy after 22:30 TH and ping me on LINE" in prompt_sent
    # Inbox is drained and archived in read/
    assert list((inbox / box).glob("*.json")) == []
    assert len(list((inbox / box / "read").glob("*.json"))) == 2


def test_mail_wake_triggers_registered_agy_session(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    sdir = tmp_path / "agy-sessions"
    monkeypatch.setattr(mailbox, "INBOX_ROOT", inbox)
    monkeypatch.setattr(mail_wake, "AGY_SESSIONS_DIR", sdir)
    monkeypatch.setattr(claude_quota, "HISTORY", tmp_path / "no-quota.jsonl")

    box = "cto-agy-aced3034"
    agy_card_run.register_session(
        box=box,
        role="cto",
        conversation_id=CONV_UUID,
        sessions_dir=sdir,
        env={"ORG_HOST": "contabo"},
    )
    mailbox.send("cto", "agy-aced3034", "RUN-20261108-1500-beef done", "run-inbox", "hub", root=inbox)

    spawned = []
    monkeypatch.setattr(mail_wake, "_spawn_agy_runner", lambda b: spawned.append(b))
    monkeypatch.setattr(send_to_cxo, "attempt_wake", lambda *a: pytest.fail("should wake AGY directly"))

    out = mail_wake.wake(box)
    assert out == {"box": box, "woke": True, "reason": "woke AGY session"}
    assert spawned == [box]


def test_mail_wake_plan_commands_allows_ask_run_for_ph_and_records_wait(tmp_path, monkeypatch):
    sid = "b2ff34d1"
    rec = {"project": "KhaoHom", "lane": "cmo", "owner": "cmo-e785343f"}
    reply = (
        "Raise a Run card:\n"
        "```bash\n"
        'python3 tools/ask_run.py create --host contabo --command "systemctl status mooniex-console" '
        '--why "org-rule: check status"\n'
        "tools/ask_run.py cancel RUN-20261108-1200-abcd\n"
        "tools/ask_run.py create --host contabo --command x --why y --session cto-evil\n"
        "```\n"
    )
    run, skipped = mail_wake.plan_commands(reply, sid, rec)
    assert len(skipped) == 1 and "--session is not this PH" in skipped[0]
    assert run == [
        [
            "tools/ask_run.py",
            "create",
            "--host",
            "contabo",
            "--command",
            "systemctl status mooniex-console",
            "--why",
            "org-rule: check status",
            "--role",
            "project_head",
            "--session",
            f"project_head-{sid}",
        ],
        ["tools/ask_run.py", "cancel", "RUN-20261108-1200-abcd"],
    ]

    # Verify _run_plan records ph_state.wait when ask_run.py create returns a card ID
    waits = []
    monkeypatch.setattr(ph_state, "wait", lambda s, cid: waits.append((s, cid)))
    monkeypatch.setattr(
        mail_wake,
        "_run_cmd",
        lambda argv, **kw: (0, "RUN-20261108-1600-f00d\nhttps://terminal.mooniex.com/run#RUN-20261108-1600-f00d\n"),
    )
    mail_wake._run_plan(sid, rec, reply.splitlines()[2])
    assert waits == [(sid, "RUN-20261108-1600-f00d")]


def test_watch_card_writes_letter_and_wakes_local_agy_session(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    sdir = tmp_path / "agy-sessions"
    box = "cto-agy-aced3034"
    agy_card_run.register_session(
        box=box,
        role="cto",
        conversation_id=CONV_UUID,
        sessions_dir=sdir,
        env={"ORG_HOST": "mac"},
    )

    monkeypatch.setattr(
        ask_run,
        "wait_result",
        lambda cid, **kw: {
            "terminal": True,
            "id": cid,
            "status": "answered",
            "question": "Ship tonight?",
            "answer": {"choice": 0, "label": "Tonight", "text": "Go ahead now"},
        },
    )
    woke_calls = []
    monkeypatch.setattr(
        agy_card_run,
        "_call_agy_cli",
        lambda prompt, **kw: woke_calls.append(prompt)
        or {
            "ok": True,
            "returncode": 0,
            "model": kw["model"],
            "conversation_id": kw["conversation_id"],
            "response": "Shipped!",
            "limit_hit": None,
        },
    )

    res = agy_card_run.watch_card(
        "Q-20261108-1630-1234",
        box,
        interval_s=0.1,
        max_wait_s=5.0,
        sessions_dir=sdir,
        inbox_root=inbox,
    )
    assert res["ok"] is True
    assert res["status"] == "answered"
    assert len(woke_calls) == 1
    assert "Q-20261108-1630-1234 answered: Tonight" in woke_calls[0]
    assert "Go ahead now" in woke_calls[0]


def test_delegated_agy_worker_worktree_cannot_claim_c_level(tmp_path):
    wt = tmp_path / "worktrees" / "Agents-Core__developer__task-8669cf28" / "src"
    wt.mkdir(parents=True)

    # Even with ANTIGRAVITY_CONVERSATION_ID present, a process inside a worker worktree
    # resolves as the worker (developer-task-8669cf28) and is refused C-level/PH roles.
    req = ask_run.resolve_requester(
        None,
        None,
        None,
        env={"ANTIGRAVITY_CONVERSATION_ID": CONV_UUID},
        cwd=wt,
    )
    assert req == {
        "session": "developer-task-8669cf28",
        "role": "developer",
        "task": "task-8669cf28",
    }

    with pytest.raises(ask_run.Refused, match="a worker cannot claim role 'cto'"):
        ask_run.resolve_requester(
            None,
            "cto",
            None,
            env={"ANTIGRAVITY_CONVERSATION_ID": CONV_UUID},
            cwd=wt,
        )


def test_ask_run_auto_binds_agy_session_from_antigravity_conversation_id(tmp_path, monkeypatch):
    sdir = tmp_path / "agy-sessions"
    monkeypatch.setattr(agy_card_run, "AGY_SESSIONS_DIR", sdir)
    watched = []
    monkeypatch.setattr(
        agy_card_run,
        "spawn_card_watcher",
        lambda cid, box, **kw: watched.append((cid, box)) or 9999,
    )

    env = {"ANTIGRAVITY_CONVERSATION_ID": CONV_UUID, "ORG_HOST": "mac"}
    req = ask_run.resolve_requester(None, None, None, env=env)
    assert req == {"session": "cto-agy-aced3034", "role": "cto"}

    ask_run._auto_bind_agy_session({"requester": req}, "RUN-20261108-1700-cafe", env=env)
    saved = agy_card_run.load_session("cto-agy-aced3034", sessions_dir=sdir)
    assert saved is not None
    assert saved["conversation_id"] == CONV_UUID
    assert saved["cards"] == ["RUN-20261108-1700-cafe"]
    assert watched == [("RUN-20261108-1700-cafe", "cto-agy-aced3034")]


def test_detect_conversation_id_from_source_metadata_and_cli_pb_files(tmp_path):
    meta_env = {
        "ANTIGRAVITY_SOURCE_METADATA": '{"tool":{"conversationId":"aced3034-2643-403e-ac26-42f1884593d6"}}'
    }
    assert agy_card_run.detect_conversation_id(env=meta_env, brain_dir=tmp_path) == CONV_UUID
    assert ask_run._agy_env_conv(meta_env) == CONV_UUID

    # Also supports antigravity-cli/conversations/<uuid>.pb files (Contabo / CLI layout)
    conv_dir = tmp_path / "conversations"
    conv_dir.mkdir()
    pb_file = conv_dir / f"{CONV_UUID}.pb"
    pb_file.write_bytes(b"proto")
    assert agy_card_run.detect_conversation_id(env={}, brain_dir=conv_dir) == CONV_UUID

    # ORG_ROLE=project_head + ORG_SESSION_NAME=project_head-3511068d resolves cleanly on AGY
    ph_env = {
        "ORG_ROLE": "project_head",
        "ORG_SESSION_NAME": "project_head-3511068d",
        "ANTIGRAVITY_CONVERSATION_ID": CONV_UUID,
    }
    assert ask_run.resolve_requester(None, None, None, env=ph_env) == {
        "session": "project_head-3511068d",
        "role": "project_head",
    }
    box, role, sid, cid = agy_card_run.resolve_identity(env=ph_env)
    assert (box, role, sid, cid) == ("project_head-3511068d", "project_head", "3511068d", CONV_UUID)


def test_wake_session_uses_agentapi_for_desktop_app_and_falls_back_to_cli(tmp_path, monkeypatch):
    sdir = tmp_path / "agy-sessions"
    inbox = tmp_path / "inbox"
    fake_ls = tmp_path / "language_server"
    fake_ls.write_text("#!/bin/sh\nexit 0\n")
    fake_ls.chmod(0o755)

    desktop_env = {
        "ANTIGRAVITY_CONVERSATION_ID": CONV_UUID,
        "ANTIGRAVITY_LS_ADDRESS": "localhost:63985",
        "ANTIGRAVITY_CSRF_TOKEN": "csrf-secret-123",
        "ANTIGRAVITY_AGENTAPI_EXE": str(fake_ls),
        "ANTIGRAVITY_PROJECT_ID": "default-cli-project",
        "ORG_HOST": "mac",
    }
    rec = agy_card_run.register_session(sessions_dir=sdir, env=desktop_env)
    assert rec["ls_address"] == "localhost:63985"
    assert rec["csrf_token"] == "csrf-secret-123"
    assert rec["agentapi_exe"] == str(fake_ls)

    mailbox.send("cto", "agy-aced3034", "Q-20261108-1649-a4dd answered: ทดสอบผ่าน!", "run-inbox", "hub", root=inbox)
    res = agy_card_run.wake_session("cto-agy-aced3034", sessions_dir=sdir, inbox_root=inbox)
    assert res["ok"] is True
    assert res["woke"] is True
    assert res["method"] == "agentapi"
    assert agy_card_run.load_session("cto-agy-aced3034", sessions_dir=sdir)["last_wake_method"] == "agentapi"

    # If the Desktop App language server returns non-zero (e.g. closed), wake_session falls back to _call_agy_cli
    fake_ls.write_text("#!/bin/sh\nexit 1\n")
    mailbox.send("cto", "agy-aced3034", "RUN-20261108-1705-abcd done (exit 0)", "run-inbox", "hub", root=inbox)
    cli_called = []
    monkeypatch.setattr(
        agy_card_run,
        "_call_agy_cli",
        lambda prompt, **kw: cli_called.append(prompt) or {
            "ok": True,
            "returncode": 0,
            "model": "claude-opus-5-5-high",
            "conversation_id": CONV_UUID,
            "response": "woke via cli fallback",
            "limit_hit": None,
        },
    )
    res2 = agy_card_run.wake_session("cto-agy-aced3034", sessions_dir=sdir, inbox_root=inbox)
    assert res2["ok"] is True
    assert res2["woke"] is True
    assert len(cli_called) == 1


