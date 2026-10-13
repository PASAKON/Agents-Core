"""Fixture-only coverage for the weekly tool-value report; no live services."""
import copy
import json
import os
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools
import tools.tool_value as tv


F = Path(__file__).resolve().parent / "fixtures" / "tool_value"
W = tv.Window(tv.bkk_midnight(date(2026, 10, 6)), tv.bkk_midnight(date(2026, 10, 13)))


def forbidden(*args, **kwargs):
    pytest.fail("A live integration was called")


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    for name in ("fetch_hub", "read_events", "write_event", "_gh", "send_to_coo", "_self_host"):
        monkeypatch.setattr(tv, name, forbidden)
    # Also catch any captured subprocess default without executing a command.
    monkeypatch.setattr(tv.subprocess, "run", forbidden)


def stamp(path, ts):
    seconds = tv.parse_ts(ts).timestamp()
    os.utime(path, (seconds, seconds))


@pytest.fixture
def local(tmp_path, monkeypatch):
    root = tmp_path / "fixtures"
    shutil.copytree(F, root)
    for p in (root / "transcripts").rglob("*.jsonl"):
        stamp(p, "2026-10-08T00:00:00Z")
    stamp(root / "prototypes/bl-ep99/decisions.jsonl", "2026-10-08T00:00:00Z")
    stamp(root / "prototypes/bl-ep98/armA/decisions.jsonl", "2026-09-01T00:00:00Z")
    paths = {
        "QUOTA_HISTORY": "quota-history.jsonl", "DECISIONS_DIR": "decisions",
        "SITES_DIR": "sites", "CREDIT_LEDGER": "credit-ledger.jsonl",
        "OPENROUTER_BALANCE": "balance.jsonl", "PROTOTYPES_DIR": "prototypes",
        "REPORT_DIR": "reports", "CODEX_SESSIONS": "codex",
    }
    for name, relative in paths.items():
        monkeypatch.setattr(tv, name, root / relative)
    monkeypatch.setattr(tv, "agy_browse_paths", lambda: [root / "agy-browse.jsonl", root / "worktree_state/agy-browse.jsonl"])
    monkeypatch.setattr(tv, "_load_yaml", lambda path: {})
    monkeypatch.setattr(tv, "jules_repos", lambda: ["o/A"])
    hub = json.loads((root / "hub.json").read_text())
    monkeypatch.setattr(tv, "fetch_hub", lambda win: (hub["tasks"], hub["events"]))
    monkeypatch.setattr(tv, "_gh", fake_gh)
    return root


def fake_gh(args):
    if "o/A" in args:
        return (F / "gh_prs.json").read_text()
    raise RuntimeError("fixture repo unavailable")


def homes(root):
    return [root / "transcripts/home1", root / "transcripts/home2"]


@pytest.fixture
def payload(local):
    return tv.collect(W, "contabo", org=True, homes=homes(local))


def test_windows():
    prev, cur = tv.windows(datetime(2026, 10, 19, 8, tzinfo=tv.BKK))
    assert prev == W
    assert cur.start == datetime(2026, 10, 12, 17, tzinfo=timezone.utc)
    assert cur.end == datetime(2026, 10, 19, tzinfo=timezone.utc)
    assert prev.label() == "6–12 ต.ค."
    assert cur.label() == "13–19 ต.ค. (ถึง 07:00)"
    prev, cur = tv.windows(datetime(2026, 10, 26, 8, tzinfo=tv.BKK))
    assert cur == tv.Window(tv.bkk_midnight(date(2026, 10, 19)), tv.bkk_midnight(date(2026, 10, 26)))
    assert prev == tv.Window(cur.start - timedelta(days=7), cur.start)
    now = datetime(2026, 10, 21, 12, tzinfo=tv.BKK)
    _, cur = tv.windows(now, date(2026, 10, 20))
    assert cur.start == tv.bkk_midnight(date(2026, 10, 20))
    assert cur.end == now
    assert tv.Window(tv.bkk_midnight(date(2026, 9, 29)), W.start).label() == "29 ก.ย.–5 ต.ค."
    assert W.key == "2026-10-06"
    assert W.days == 7.0


@pytest.mark.parametrize("value, expected", [
    ("2026-10-01T13:57:18+0200", datetime(2026, 10, 1, 11, 57, 18, tzinfo=timezone.utc)),
    ("2026-10-07T01:00:00.000Z", datetime(2026, 10, 7, 1, tzinfo=timezone.utc)),
    ("2026-10-07T01:00:00", datetime(2026, 10, 7, 1, tzinfo=timezone.utc)),
    (0, datetime(1970, 1, 1, tzinfo=timezone.utc)),
    ("garbage", None), ("", None), (None, None),
])
def test_parse_ts(value, expected):
    assert tv.parse_ts(value) == expected


def test_quota():
    result = tv.quota_usage(F / "quota-history.jsonl", W)
    expected = dict(used_pct=60.0, at_cap_hours=2.0,
                    cap_starts=["2026-10-06T01:00:00+00:00"], errors=1, samples=7,
                    resets_seen=["2026-10-06", "2026-10-13"])
    assert {k: result["claude"][k] for k in expected} == expected
    assert result["codex"]["used_pct"] == 20.0
    assert result["codex"]["resets_seen"] == ["2026-10-10", "2026-10-17"]
    assert result["agy-gemini"]["used_pct"] == 2.0
    with pytest.raises(tv.SourceMissing):
        tv.quota_usage(F / "quota-history.jsonl", tv.Window(tv.bkk_midnight(date(2026, 1, 1)), tv.bkk_midnight(date(2026, 1, 8))))


def test_transcripts(local, tmp_path):
    result, missing = tv.transcript_usage([*homes(local), tmp_path / "nope"], W)
    families = result["families"]
    for family, messages, tokens in [("opus", 1, 150), ("sonnet", 2, 100), ("haiku", 2, 15)]:
        assert families[family]["messages"] == messages
        assert families[family]["output_tokens"] == tokens
    assert families["opus"]["cache_creation_tokens"] == 1000
    assert families["sonnet"]["sidechain_messages"] == 1
    assert families["sonnet"]["sidechain_output_tokens"] == 40
    assert result["models"]["claude-haiku-5-5"] == {"messages": 1, "output_tokens": 10}
    assert sum(m["messages"] for m in result["models"].values()) == 5
    assert "<synthetic>" not in result["models"]
    assert missing == [{"source": f"transcripts:{tmp_path / 'nope'}", "reason": "ไม่มีโฟลเดอร์"}]
    stamp(local / "transcripts/home2/proj/other.jsonl", "2026-09-01T00:00:00Z")
    after, _ = tv.transcript_usage(homes(local), W)
    assert after["files_scanned"] == result["files_scanned"] - 1
    with pytest.raises(tv.SourceMissing):
        tv.transcript_usage([tmp_path / "nope"], W)


def test_codex(tmp_path):
    assert tv.codex_usage(F / "codex", W) == {
        "sessions": 2, "sessions_with_task": 1, "sessions_per_day": {"2026-10-07": 2},
        "tokens": {"input_tokens": 3000, "cached_input_tokens": 1500, "output_tokens": 300, "reasoning_output_tokens": 30},
        "max_used_percent_seen": 35.0,
    }
    with pytest.raises(tv.SourceMissing):
        tv.codex_usage(tmp_path / "nope", W)


def test_decisions():
    result = tv.decision_usage(F / "decisions", F / "sites", W)
    assert result["calls"] == 3
    assert result["providers"] == {"jev": 1, "rules": 2}
    assert result["wired_sites"] == ["bl.beat", "skill.route", "sompong.route"]
    assert result["wired_sites_called"] == ["bl.beat", "sompong.route"]
    for key, value in [("cost_usd", 0.0001), ("counterfactual_usd", 0.06), ("saved_usd", 0.0599)]:
        assert result[key] == pytest.approx(value)


def test_agy_browse(tmp_path):
    result = tv.agy_browse_usage([F / "agy-browse.jsonl", F / "worktree_state/agy-browse.jsonl"], W)
    assert result["calls"] == 3
    assert result["failed"] == 1
    assert result["verbs"] == {"text": 1, "?": 1, "shot": 1}
    with pytest.raises(tv.SourceMissing):
        tv.agy_browse_usage([tmp_path / "nope"], W)
    paths = [tmp_path / "state/agy-browse.jsonl", tmp_path / "worktrees/x/state/agy-browse.jsonl"]
    for path in paths:
        path.parent.mkdir(parents=True)
        shutil.copyfile(F / "agy-browse.jsonl", path)
    assert tv.agy_browse_paths(tmp_path) == paths


def test_credits():
    assert tv.credit_usage(F / "credit-ledger.jsonl", W) == {
        "rows": 3, "engines": {"flow:credits": {"rows": 2, "amount": 35.0}, "higgsfield:credits": {"rows": 1, "amount": 4.0}},
    }


def test_openrouter():
    result = tv.openrouter_balance(F / "balance.jsonl", W)
    expected = dict(read_at="2026-10-09T08:00:00+00:00", account_remaining_usd=33.5,
                    reads_in_window=2, usage_between_reads_usd=1.5, read_inside_window=True, key_usage_weekly_usd=2.5)
    assert {k: result[k] for k in expected} == expected
    with pytest.raises(tv.SourceMissing):
        tv.openrouter_balance(F / "balance.jsonl", tv.Window(tv.bkk_midnight(date(2026, 9, 1)), tv.bkk_midnight(date(2026, 9, 8))))


def test_bl_jev(local):
    assert tv.bl_jev_usage(local / "prototypes", W) == {
        "episodes_with_decisions": ["bl-ep99"], "scoreboard_rows": [{"episode": "EP99", "net_saved_usd": 0.42}],
    }


def test_jules():
    result = tv.jules_github(["o/A", "o/B"], W, run=fake_gh)
    assert result["prs_created"] == 1
    assert result["prs_merged"] == 2
    assert result["per_repo"] == {"o/A": 1}
    assert result["repos_read"] == 1
    assert result["repos_failed"] == [{"repo": "o/B", "reason": "fixture repo unavailable"}]
    with pytest.raises(tv.SourceMissing):
        tv.jules_github(["o/B"], W, run=fake_gh)


def test_hub_tasks():
    hub = json.loads((F / "hub.json").read_text())
    result = tv.hub_tasks_summary(hub["tasks"], hub["events"], W)
    expected = dict(tasks=3, status={"done": 1, "cancelled": 1, "review": 1}, override=2,
                    override_codes={"in-session": 1, "review": 1}, reopens=1, routed=1, seed_claude_pct_done=3.0)
    assert {k: result["claude"][k] for k in expected} == expected
    assert result["codex"]["tasks"] == result["codex"]["routed"] == 1
    assert result["codex"]["seed_claude_pct_done"] == 3.0
    assert result["agy"]["tasks"] == 1
    assert result["agy"]["seed_claude_pct_done"] == 8.0
    assert result["unrouted"]["tasks"] == 1
    assert result["unrouted"]["roles"] == {"video_editor": 1}


def test_missing_rows():
    cells = tv.build_rows({}, W, tv.HOSTS, {})
    assert set(cells) == {key for _, _, key in tv.ROW_ORDER}
    assert all(c["label"] == "none" and c["value"] is None for c in cells.values())


@pytest.mark.parametrize("first", [True, False])
def test_build_report(payload, first):
    assert payload["sources"]["jules_github"]["prs_created"] == 1
    rows = {"contabo": payload}
    report = tv.build_report(rows, rows, W, W, plans={}, first=first)
    cells = report["current"]["cells"]
    assert cells["claude_used_pct"]["value"] == 60.0
    assert cells["claude_used_pct"]["label"] == "measured"
    assert cells["jules_sessions"]["label"] == "none"
    assert "ไม่มีข้อมูล (Mac)" in report["text"]
    assert "Mac ไม่ส่ง" in report["text"]
    assert all(metric in report["text"] for _, metric, _ in tv.ROW_ORDER)
    assert ("คำถามถึง CEO" in report["text"]) is first


def test_missing_transcripts_report(payload):
    payload = copy.deepcopy(payload)
    del payload["sources"]["transcripts"]
    payload["missing"].append({"source": "transcripts", "reason": "fixture unavailable"})
    rows = {"contabo": payload}
    report = tv.build_report(rows, rows, W, W, plans={})
    cell = report["current"]["cells"]["haiku_messages"]
    assert cell["label"] == "none"
    assert cell["value"] is None
    line = next(line for line in report["text"].splitlines() if line.startswith("| Haiku 5.5 | ข้อความ assistant |"))
    for value in line.split("|")[3:5]:
        assert "ไม่มีข้อมูล" in value
        assert "0" not in value


def test_idle(payload):
    cells = tv.build_rows({"contabo": payload}, W, tv.HOSTS, {})
    idle = {item["tool"]: item for item in tv.idle_list(cells, W)}
    assert "2.0%" in idle["AGY Gemini"]["value"]
    assert "20.0%" in idle["Codex"]["value"]
    assert "Claude" not in idle
    half = tv.Window(W.start, W.start + timedelta(days=3.5))
    cells["codex_used_pct"]["value"] = 30.0
    assert "Codex" not in {item["tool"] for item in tv.idle_list(cells, half)}


def test_latest_rows():
    old = dict(host="contabo", window=W.as_json(), sources={"version": 1})
    new = dict(host="contabo", window=W.as_json(), sources={"version": 2})
    other = dict(host="contabo", window=tv.Window(W.end, W.end + timedelta(days=7)).as_json())
    assert tv.latest_rows([old, new, other], W) == {"contabo": new}
    assert tv.latest_rows([new, old], W) == {"contabo": old}


def test_collect_local_failure(local, monkeypatch):
    for name in ("quota_usage", "fetch_hub", "jules_github", "openrouter_balance"):
        monkeypatch.setattr(tv, name, forbidden)
    def broken(*args):
        raise ValueError("fixture failure")
    monkeypatch.setattr(tv, "credit_usage", broken)
    result = tv.collect(W, "contabo", org=False, homes=homes(local))
    assert not {"quota", "hub_tasks", "jules_github", "openrouter"} & result["sources"].keys()
    assert set(result["sources"]) == {"transcripts", "codex_rollouts", "decisions", "agy_browse", "bl_jev"}
    assert result["missing"] == [{"source": "credit_ledger", "reason": "ValueError: fixture failure"}]


def stub_collect(win, host, **kwargs):
    return dict(host=host, org=True, window=win.as_json(), sources={}, missing=[])


@pytest.mark.parametrize("mode, code, count", [("empty", 0, 2), ("previous", 0, 1), ("error", 3, 0), ("dry", 0, 0)])
def test_main_collect(local, monkeypatch, mode, code, count):
    writes = []
    prev = tv.Window(W.start - timedelta(days=7), W.start)
    def read(since):
        if mode == "error":
            raise RuntimeError("offline")
        return [stub_collect(prev, "contabo")] if mode == "previous" else []
    monkeypatch.setattr(tv, "read_events", read)
    monkeypatch.setattr(tv, "write_event", writes.append)
    monkeypatch.setattr(tv, "collect", stub_collect)
    args = ["collect", "--week", "2026-10-06", "--host", "contabo"]
    assert tv.main(args + (["--dry-run"] if mode == "dry" else [])) == code
    assert len(writes) == count
    if writes:
        assert writes[0]["window"] == W.as_json()
    if count == 2:
        assert writes[1]["window"] == prev.as_json()


@pytest.mark.parametrize("mode", ["send", "dry", "no-send"])
def test_main_report(local, monkeypatch, mode):
    sends = []
    monkeypatch.setattr(tv, "read_events", lambda since: [])
    monkeypatch.setattr(tv, "collect", stub_collect)
    def send(text):
        sends.append(text)
        return "ok: fixture"
    monkeypatch.setattr(tv, "send_to_coo", send)
    args = ["report", "--week", "2026-10-06", "--host", "contabo"]
    if mode != "send":
        args.append("--dry-run" if mode == "dry" else "--no-send")
    assert tv.main(args) == 0
    if mode == "dry":
        assert not tv.REPORT_DIR.exists()
    else:
        expected = {"2026-10-06.md", "2026-10-06.json"}
        if mode == "send":
            expected.add("2026-10-06.sent")
        assert {p.name for p in tv.REPORT_DIR.iterdir()} == expected
        assert json.loads((tv.REPORT_DIR / "2026-10-06.json").read_text())["current"]["window"] == W.as_json()
    assert len(sends) == (1 if mode == "send" else 0)
    if mode == "send":
        assert tv.main(args) == 2
        assert len(sends) == 1


# Preserve the function under test before the autouse fixture replaces delivery.
SEND_TO_COO = tv.send_to_coo


def test_send_to_coo(monkeypatch):
    calls = []
    def send(recipient, text, **kwargs):
        calls.append((os.environ["CXO_ROLE"], os.environ["CXO_SESSION_ID"]))
        assert recipient == "coo"
        assert text == "fixture report"
        assert "WORKER_TASK_ID" not in os.environ
        return "ok"
    fake = SimpleNamespace(send=send)
    monkeypatch.setitem(sys.modules, "tools.send_to_cxo", fake)
    monkeypatch.setattr(tools, "send_to_cxo", fake, raising=False)
    monkeypatch.setattr(tv, "send_to_coo", SEND_TO_COO)
    monkeypatch.setenv("CXO_ROLE", "cfo")
    monkeypatch.setenv("CXO_SESSION_ID", "original-session")
    monkeypatch.setenv("WORKER_TASK_ID", "original-task")
    assert tv.send_to_coo("fixture report") == "ok"
    assert calls == [("cto", "tool-value")]
    assert os.environ["CXO_ROLE"] == "cfo"
    assert os.environ["CXO_SESSION_ID"] == "original-session"
    assert os.environ["WORKER_TASK_ID"] == "original-task"


def test_send_from_a_deploy_checkout_uses_the_live_cli(monkeypatch, tmp_path):
    """deploy/systemd/tool-value-*.service run a pinned worktree with ORG_ROOT = the live checkout:
    the letter must go through the live checkout's send_to_cxo, never this tree's."""
    live = tmp_path / "live"
    live.mkdir()
    monkeypatch.setattr(tv, "send_to_coo", SEND_TO_COO)
    monkeypatch.setattr(tv, "DATA_ROOT", live)
    monkeypatch.setenv("WORKER_TASK_ID", "task-00000000")
    seen = {}

    def run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return SimpleNamespace(returncode=0, stdout="queued to SomPong #x: [CTO tool-value] : r\n", stderr="")

    monkeypatch.setattr(tv.subprocess, "run", run)
    assert tv.send_to_coo("fixture report").startswith("queued to SomPong")
    assert seen["cmd"][1:] == ["-m", "tools.send_to_cxo", "--from", "CTO tool-value", "coo", "fixture report"]
    assert seen["cwd"] == str(live)
    env = seen["env"]
    assert (env["CXO_ROLE"], env["CXO_SESSION_ID"], env["ORG_ROOT"]) == ("cto", "tool-value", str(live))
    assert "WORKER_TASK_ID" not in env


def test_send_from_a_deploy_checkout_raises_on_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(tv, "send_to_coo", SEND_TO_COO)
    monkeypatch.setattr(tv, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(tv.subprocess, "run", lambda cmd, **kw: SimpleNamespace(
        returncode=2, stdout="", stderr="no active SomPong session found. Spawn one first"))
    with pytest.raises(RuntimeError, match="exit 2: no active SomPong"):
        tv.send_to_coo("fixture report")
