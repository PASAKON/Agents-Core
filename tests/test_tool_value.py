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
    for name in ("fetch_hub", "read_events", "write_event", "_gh", "send_to_coo", "_self_host",
                 "fetch_runner_fit", "fetch_context_deltas", "_git", "fetch_agy_browse_hub",
                 "fetch_router_off"):
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
        "REPORT_DIR": "reports", "CODEX_SESSIONS": "codex", "AGENT_CALLS": "agent-calls.jsonl",
    }
    for name, relative in paths.items():
        monkeypatch.setattr(tv, name, root / relative)
    monkeypatch.setattr(tv, "agy_browse_paths", lambda: [root / "agy-browse.jsonl", root / "worktree_state/agy-browse.jsonl"])
    monkeypatch.setattr(tv, "_load_yaml", lambda path: {})
    monkeypatch.setattr(tv, "jules_repos", lambda: ["o/A"])
    hub = json.loads((root / "hub.json").read_text())
    monkeypatch.setattr(tv, "fetch_hub", lambda win: (hub["tasks"], hub["events"]))
    monkeypatch.setattr(tv, "_gh", fake_gh)
    monkeypatch.setattr(tv, "fetch_runner_fit", lambda until: json.loads((root / "runner_fit.json").read_text()))
    monkeypatch.setattr(tv, "fetch_context_deltas", lambda win: json.loads((root / "context_deltas.json").read_text()))
    monkeypatch.setattr(tv, "_git", lambda args: "")
    monkeypatch.setattr(tv, "fetch_agy_browse_hub", lambda win: {"calls": 0, "keys": []})
    monkeypatch.setattr(tv, "fetch_router_off", lambda win: {"tasks": 0, "pinned": 0, "reasons": {}, "runners": {},
                                                            "first_ts": None})
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
    expected = dict(used_pct=60.0, at_cap_hours=3.0,
                    cap_starts=["2026-10-06T01:00:00+00:00"], errors=1, samples=8,
                    resets_seen=["2026-10-06", "2026-10-13"])
    assert {k: result["claude"][k] for k in expected} == expected
    assert result["codex"]["used_pct"] == 20.0
    assert result["codex"]["resets_seen"] == ["2026-10-10", "2026-10-17"]
    assert result["agy-gemini"]["used_pct"] == 2.0
    assert result["claude"]["resets"] == [{
        "at": "2026-10-06T10:00:00+00:00", "claude_used_pct": 100.0,
        "full_since": "2026-10-06T01:00:00+00:00", "others": {
            "codex": {"used_pct": 10.0, "sample_ts": "2026-10-06T00:00:00+00:00"},
            "agy-gemini": {"used_pct": 0.0, "sample_ts": "2026-10-06T00:00:00+00:00"}}}]
    assert tv.quota_usage(F / "quota-history.jsonl", tv.Window(W.start, tv.parse_ts("2026-10-06T09:00:00Z")))["claude"]["resets"] == []
    with pytest.raises(tv.SourceMissing):
        tv.quota_usage(F / "quota-history.jsonl", tv.Window(tv.bkk_midnight(date(2026, 1, 1)), tv.bkk_midnight(date(2026, 1, 8))))


def test_transcripts(local, tmp_path):
    result, missing = tv.transcript_usage([*homes(local), tmp_path / "nope"], W)
    families = result["families"]
    for family, messages, tokens in [("opus", 1, 150), ("sonnet", 4, 600), ("haiku", 2, 15)]:
        assert families[family]["messages"] == messages
        assert families[family]["output_tokens"] == tokens
    assert families["opus"]["cache_creation_tokens"] == 1000
    assert families["sonnet"]["sidechain_messages"] == 1
    assert families["sonnet"]["sidechain_output_tokens"] == 40
    assert result["models"]["claude-haiku-5-5"] == {"messages": 1, "output_tokens": 10}
    assert sum(m["messages"] for m in result["models"].values()) == 7
    assert result["by_kind"] == {
        "worker": dict(messages=2, output_tokens=500, input_tokens=50, cache_creation_tokens=120),
        "clevel": dict(messages=5, output_tokens=265, input_tokens=29, cache_creation_tokens=1000)}
    assert result["worker_task_ids"] == ["task-4a53167b"]
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
    expected = dict(tasks=4, status={"done": 2, "cancelled": 1, "review": 1}, override=2,
                    override_codes={"free-text": 1, "review": 1}, reopens=1, routed=1, seed_claude_pct_done=6.0,
                    done_clean=2, iter_sum=2, iter_n=2, router_skipped=1)
    assert {k: result["claude"][k] for k in expected} == expected
    assert result["codex"]["tasks"] == 2
    assert result["codex"]["routed"] == 1
    assert result["codex"]["seed_claude_pct_done"] == 3.0
    assert result["agy"]["tasks"] == 2
    assert result["agy"]["seed_claude_pct_done"] == 8.0
    assert result["unrouted"]["tasks"] == 1
    assert result["unrouted"]["roles"] == {"video_editor": 1}
    for runner, clean, iterations, codes in [("codex", 1, 3, {"ceo-order": 1}), ("agy", 1, 2, {"free-text": 1})]:
        assert {k: result[runner][k] for k in ("done_clean", "iter_sum", "iter_n", "router_skipped", "override_codes")} == dict(
            done_clean=clean, iter_sum=iterations, iter_n=2, router_skipped=0, override_codes=codes)
    assert result["codex"]["done_sizes"] == {"S": 2}
    assert result["agy"]["done_sizes"] == {"S": 1, "M": 1}


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
    assert "usd_per_pct_anthropic" not in cells
    for usd in (20, 200):
        assert "ไม่ได้บันทึก" in cells[f"usd_per_pct_anthropic_{usd}"]["note"]
        assert cells[f"usd_per_pct_anthropic_{usd}"]["value"] == round(usd * 12 / 52 / 60, 2)
    assert cells["worthwhile"]["value"] == "claude 2/2 · codex 1/2 · agy 1/2"
    assert cells["iterations"]["value"] == "claude 1.0 · codex 1.5 · agy 1.0"
    assert cells["router_skipped"]["value"] == "claude 1 · codex 0 · agy 0"
    assert cells["tokens_per_job_worker"]["value"] == 500
    assert cells["tokens_per_job_clevel"]["value"] == 29  # 265 / 9 tasks
    assert "ข้อความอิสระ 1" in cells["claude_pinned"]["note"]
    text = report["text"]
    assert "ณ เวลาที่ Claude รีเซ็ตโควตาสัปดาห์ (วัดจริง จาก quota-history):" in text
    assert "- 06/10 17:00: Claude ใช้ 100% (เต็มตั้งแต่ 06/10 08:00) · Codex 10% · AGY Gemini 0% · AGY Claude ไม่มีข้อมูล" in text
    assert "runner-fit (cell = runner × ประเภทงาน" in text
    assert "| cell | ประเภทงาน | งาน | ผ่าน/แก้ซ้ำ/ล้ม |" in text
    assert "เฟสองค์กร: 2 — cell ที่ผ่านเกณฑ์ 1/2" in text
    assert "ขนาดข้อความที่โหลดทุกครั้ง (วัดจริง: claude -p delta):" in text
    assert "- roles §32 Tab Title: 1,496 → 986 tokens (-510, -34%) · ทุก turn · CTO · fixture evidence" in text
    assert "รวม -510 tokens" in text
    assert report["claude_resets"] == payload["sources"]["quota"]["claude"]["resets"]
    assert report["org_phase"] == dict(used=2, passed=1, phase=2)


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
    assert set(result["sources"]) == {"transcripts", "codex_rollouts", "decisions", "agy_browse", "bl_jev",
                                      "agent_calls"}
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


def test_fit_cells():
    records = json.loads((F / "runner_fit.json").read_text())
    skills = {"skills": {s: {"exists": True, "commits": []} for s in set(tv.RUNNER_SKILLS.values())}}
    rows, org = tv.fit_cells(records, skills, W)
    assert org == dict(used=2, passed=1, phase=2)
    b, a = rows
    assert a == dict(cell="codex", job_type="code", jobs=5, **{"pass": 5}, redo=0, fail=0,
                     first_pass_pct=100, redo_pct=0, iter_avg=1.0, minutes_avg=10.0,
                     last10_n=10, last10_first_pass_pct=100, skill="CTO_Knowledge_Codex",
                     skill_exists=True, skill_edits=0, rule_change=False, phase=2, why="ผ่านเกณฑ์")
    assert b == dict(cell="agy-gemini", job_type="docs", jobs=3, **{"pass": 1}, redo=1, fail=1,
                     first_pass_pct=33, redo_pct=33, iter_avg=2.0, minutes_avg=20.0,
                     last10_n=3, last10_first_pass_pct=33, skill="CTO_Knowledge_AGY",
                     skill_exists=True, skill_edits=0, rule_change=False, phase=1, why="ยังไม่ถึง 10 งาน (3)")
    skills["skills"]["CTO_Knowledge_Codex"]["commits"] = [
        {"ts": tv.iso(W.end - timedelta(days=3)), "subject": "skill(CTO_Knowledge_Codex): rule — x"}]
    rows, org = tv.fit_cells(records, skills, W)
    assert rows[1]["why"] == "skill เปลี่ยน rule ใน 14 วัน"
    assert rows[1]["skill_edits"] == 1
    assert org == dict(used=2, passed=0, phase=1)
    rows, org = tv.fit_cells(records, None, W)
    assert rows[1]["why"] == "ไม่มีข้อมูล skill"
    assert rows[1]["rule_change"] is rows[1]["skill_exists"] is rows[1]["skill_edits"] is None
    assert org == dict(used=2, passed=0, phase=1)
    codex = [r for r in records if r["runner"] == "codex"]
    for r in codex:
        r["runner"] = "claude"
        r["model"] = "claude-opus-5-5"
    rows, org = tv.fit_cells(codex, None, W)
    assert rows[0]["cell"] == "claude-opus"
    assert rows[0]["phase"] == 2
    assert org == dict(used=1, passed=1, phase=3)
    for r in codex[:3]:
        r["first_pass"] = False
    rows, org = tv.fit_cells(codex, None, W)
    assert rows[0]["why"] == "first-pass 70% < 80%"
    assert org == dict(used=1, passed=0, phase=1)
    assert tv.fit_cells([], None, W) == ([], dict(used=0, passed=0, phase=1))


@pytest.mark.parametrize("subject, days, changed", [
    ("skill(CTO_Knowledge_Codex, CTO_Knowledge_AGY): flip x", 14, True),
    ("skill(CTO_Knowledge_Codex): rule x", 0, False),
    ("skill(CTO_Knowledge_Codex): rule x", 15, False),
    ("skill(CTO_Knowledge_AGY): rule x", 3, False),
    ("skill(CTO_Knowledge_Codex): docs x", 3, False),
])
def test_rule_changes(subject, days, changed):
    records = json.loads((F / "runner_fit.json").read_text())
    skills = {"skills": {"CTO_Knowledge_Codex": {"exists": False, "commits": [
        {"ts": tv.iso(W.end - timedelta(days=days)), "subject": subject}]}}}
    rows, _ = tv.fit_cells(records, skills, W)
    assert rows[1]["rule_change"] is changed
    assert rows[1]["phase"] == (1 if changed else 2)


def test_skill_commits():
    calls = []
    def run(args):
        calls.append(args)
        if args[0] == "cat-file":
            if "CTO_Knowledge_Jules" in args[-1]:
                raise tv.subprocess.CalledProcessError(1, args)
            return ""
        assert args[1:5] == ["origin/main", "--since=2026-09-28T17:00:00+00:00",
                             "--until=2026-10-12T17:00:00+00:00", "--format=%cI%x09%s"]
        return "2026-10-08T07:00:00+07:00\tskill(test): docs\n"
    result = tv.skill_commits(W, run=run)
    assert result["ref"] == "origin/main"
    assert len(calls) == 2 * len(set(tv.RUNNER_SKILLS.values()))
    for name, info in result["skills"].items():
        assert info == {"exists": name != "CTO_Knowledge_Jules", "commits": [
            {"ts": "2026-10-08T00:00:00+00:00", "subject": "skill(test): docs"}]}
    def fail(args):
        if args[0] == "log":
            raise tv.subprocess.CalledProcessError(1, args)
        return ""
    with pytest.raises(tv.SourceMissing, match="git log"):
        tv.skill_commits(W, run=fail)


CONTEXT_ARGS = ["context-delta", "--what", "roles §32 Tab Title", "--before", "1496", "--after", "986",
                "--method", "claude -p input-total delta", "--evidence", "fixture evidence", "--by", "CTO",
                "--per", "ทุก turn", "--at", "2026-10-08T00:00:00Z"]


@pytest.mark.parametrize("flag,value", [("--before", "-1"), ("--after", "-2"), ("--before", "1.5"),
                                       ("--after", "bad"), ("--at", "bad")])
def test_context_bad_arguments(flag, value, capsys):
    args = CONTEXT_ARGS.copy()
    args[args.index(flag) + 1] = value
    assert tv.main(args) == 2
    captured = capsys.readouterr()
    assert len(captured.err.splitlines()) == 1
    assert captured.out == ""


@pytest.mark.parametrize("dry", [True, False])
def test_context_payload(monkeypatch, capsys, dry):
    writes = []
    monkeypatch.setattr(tv, "write_event", lambda p, **kw: writes.append((p, kw)))
    assert tv.main(CONTEXT_ARGS + (["--dry-run"] if dry else [])) == 0
    expected = json.loads((F / "context_deltas.json").read_text())[0]
    if dry:
        assert writes == []
        assert json.loads(capsys.readouterr().out) == expected
    else:
        assert writes == [(expected, {"kind": "context_delta"})]


def test_context_defaults(monkeypatch):
    writes = []
    monkeypatch.setattr(tv, "write_event", lambda p, **kw: writes.append(p))
    args = CONTEXT_ARGS[:CONTEXT_ARGS.index("--per")]
    args[args.index("--before") + 1] = "0"
    before = datetime.now(timezone.utc).replace(microsecond=0)
    assert tv.main(args) == 0
    assert before <= tv.parse_ts(writes[0]["at"]) <= datetime.now(timezone.utc)
    assert writes[0]["before"] == 0
    assert writes[0]["per"] == ""


FETCH_FIT = tv.fetch_runner_fit
FETCH_CONTEXT = tv.fetch_context_deltas
WRITE_EVENT = tv.write_event


def fake_db(monkeypatch, records):
    class Conn:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def execute(self, sql, args):
            self.sql, self.args = sql, args
            return self
        def fetchall(self):
            return records
    from lib import db
    conn = Conn()
    monkeypatch.setattr(db, "get_conn", lambda **kw: conn)
    return conn


def test_fetch_sources(monkeypatch):
    p = json.loads((F / "runner_fit.json").read_text())[0]
    rows = [{"ts": "2026-10-08T00:00:00Z", "task_id": str(i),
             "payload": dict(p, schema=1, extra="ignored")} for i in range(2002)]
    rows[-1]["payload"] = json.dumps(rows[-1]["payload"])
    rows.append(dict(ts=tv.iso(W.end), task_id="future", payload=dict(p, schema=1)))
    rows.append(dict(ts=tv.iso(W.start), task_id="bad", payload="bad"))
    conn = fake_db(monkeypatch, rows)
    result = FETCH_FIT(W.end)
    assert conn.args == ("runner_fit", tv.iso(W.end))
    assert len(result) == 2000
    assert result[0]["task_id"] == "2"
    assert result[-1]["task_id"] == "2001"
    assert set(result[0]) == {"ts", "task_id", "runner", "model", "bucket", "job_type", "result",
                              "fail_reason", "first_pass", "reviewer_fix", "iteration", "minutes"}
    measurement = json.loads((F / "context_deltas.json").read_text())[0]
    fake_db(monkeypatch, [{"payload": json.dumps(measurement)},
                         {"payload": dict(measurement, at=tv.iso(W.end))}, {"payload": "bad"}])
    assert FETCH_CONTEXT(W) == [measurement]


def test_context_event_envelope(monkeypatch):
    from lib import db
    conn = fake_db(monkeypatch, [])
    calls = []
    monkeypatch.setattr(db, "log_event", lambda *args: calls.append(args))
    payload = json.loads((F / "context_deltas.json").read_text())[0]
    WRITE_EVENT(payload, kind="context_delta")
    assert calls == [(conn, None, "CTO", "context_delta", payload)]


def test_new_sources_missing_and_empty(payload):
    rows = {"contabo": copy.deepcopy(payload)}
    for name in ("quota", "runner_fit", "context_deltas"):
        del rows["contabo"]["sources"][name]
        rows["contabo"]["missing"].append(dict(source=name, reason=name + " unavailable"))
    report = tv.build_report(rows, rows, W, W, plans={})
    for name in ("quota", "runner_fit", "context_deltas"):
        assert f"ไม่มีข้อมูล ({name} unavailable)" in report["text"]
    assert report["fit_cells"] is report["org_phase"] is None
    rows["contabo"]["sources"].update(runner_fit={"records": []}, context_deltas={"records": []})
    report = tv.build_report(rows, rows, W, W, plans={})
    assert "ยังไม่มีบันทึก runner_fit ในช่วงนี้ (เริ่มบันทึก 13 ต.ค.)" in report["text"]
    assert "- ไม่มีบันทึกในช่วงนี้" in report["text"]


def test_quota_reset_boundaries(tmp_path):
    path = tmp_path / "quota.jsonl"
    samples = [
        dict(provider="codex", ts=tv.iso(W.start - timedelta(hours=4)), weekly_remaining=0.7),
        dict(provider="claude", ts=tv.iso(W.start - timedelta(hours=3)), weekly_remaining=0),
        dict(provider="claude", ts=tv.iso(W.start - timedelta(hours=2)), weekly_remaining=0),
        dict(provider="claude", ts=tv.iso(W.start), weekly_remaining=0.2),
        dict(provider="claude", ts=tv.iso(W.start + timedelta(hours=1)), weekly_remaining=0.5),
        dict(provider="claude", ts=tv.iso(W.end), weekly_remaining=1),
    ]
    path.write_text("\n".join(json.dumps(s) for s in reversed(samples)))
    resets = tv.quota_usage(path, W)["claude"]["resets"]
    assert resets == [
        dict(at=tv.iso(W.start), claude_used_pct=100.0, full_since=tv.iso(W.start - timedelta(hours=3)),
             others={"codex": dict(used_pct=30.0, sample_ts=tv.iso(W.start - timedelta(hours=4)))}),
        dict(at=tv.iso(W.start + timedelta(hours=1)), claude_used_pct=80.0, full_since=None,
             others={"codex": dict(used_pct=30.0, sample_ts=tv.iso(W.start - timedelta(hours=4)))})]


def test_tokens_across_hosts(payload):
    rows = {"contabo": payload, "mac": copy.deepcopy(payload)}
    rows["mac"]["org"] = False
    cells = tv.build_rows(rows, W, tv.HOSTS, {})
    assert cells["tokens_per_job_worker"]["value"] == 1000  # shared task id counted once
    assert cells["tokens_per_job_clevel"]["value"] == 59
    assert "1 งานที่มี transcript" in cells["tokens_per_job_worker"]["note"]
    assert "ไม่มีข้อมูล (winbox)" in cells["tokens_per_job_worker"]["note"]
    del rows["contabo"]["sources"]["hub_tasks"]
    cells = tv.build_rows(rows, W, tv.HOSTS, {})
    assert cells["tokens_per_job_clevel"]["label"] == "none"
    assert cells["tokens_per_job_worker"]["value"] == 1000


def test_collect_new_source_failures(local, monkeypatch):
    def missing(*args, **kwargs):
        raise tv.SourceMissing("fixture offline")
    for name in ("fetch_runner_fit", "fetch_context_deltas", "_git"):
        monkeypatch.setattr(tv, name, missing)
    result = tv.collect(W, "contabo", org=True, homes=homes(local))
    assert {m["source"]: m["reason"] for m in result["missing"]} == {
        "runner_fit": "fixture offline", "context_deltas": "fixture offline", "skill_commits": "fixture offline"}
    assert not {"runner_fit", "context_deltas", "skill_commits"} & result["sources"].keys()


def test_context_zero_baseline_and_confirmed_price(payload):
    payload["sources"]["context_deltas"]["records"][0].update(before=0, after=10)
    later = tv.Window(tv.bkk_midnight(date(2026, 10, 14)), tv.bkk_midnight(date(2026, 10, 21)))
    rows = {"contabo": payload}
    report = tv.build_report(rows, rows, later, later, plans={})
    assert "tokens (+10, ไม่มีข้อมูล)" in report["text"]
    assert "รวม +10 tokens" in report["text"]
    for usd in (20, 200):
        assert "CEO ยืนยัน $200 ตั้งแต่ 14 ต.ค." in report["current"]["cells"][f"usd_per_pct_anthropic_{usd}"]["note"]


PLANS_WITH_TARGETS = {
    "providers": {"anthropic": {"plans": [{"usd": 20, "from": "2026-09-29T10:00:00Z"}, {"usd": 200, "from": "2026-10-10"}]},
                  "google": {"plans": [{"usd": 100, "from": "2026-09-01"}]},
                  "openai": {"plans": [{"usd": 20, "from": "2026-09-01"}]}},
    "targets": {"anthropic": {"usd": 20, "from": "2026-10-10"}, "google": {"usd": 100, "from": "2026-10-10"},
                "openai": {"usd": 20, "from": "2026-10-10"}},
}


def test_subscription_lines_now_vs_target():
    cur = {"claude_used_pct": tv._cell(104.0, "measured"), "claude_cap_hours": tv._cell(22.9, "measured")}
    sources = {"contabo": {"org": True, "sources": {"hub_tasks": {
        "claude": {"tasks": 33}, "codex": {"tasks": 17}, "agy": {"tasks": 5}, "unrouted": {"tasks": 5}}}}}
    lines = tv.subscription_lines(cur, sources, PLANS_WITH_TARGETS, W)
    assert lines[:8] == [
        "", "ค่าแพ็กเกจต่อเดือน เทียบเป้าของ CEO (14 ต.ค.):",
        "| บริการ | ตอนนี้ $ | เป้า $ | ห่าง $ |", "|---|---|---|---|",
        "| Claude | 200 | 20 | 180 |", "| Google AI Ultra | 100 | 100 | 0 |", "| ChatGPT | 20 | 20 | 0 |",
        "| รวม | 320 | 140 | 180 |"]
    assert lines[8] == "- งาน worker ที่ไม่ได้ใช้ Claude: 22/60 (37%) · วัดจริง (codex + agy ÷ ทุกงานใน hub)"
    # Max 20x -> Pro = 5% of today's weekly quota; 104% used -> about 21x too much (estimate, labelled).
    assert lines[9].startswith("- Claude ที่ $20 ใช้ได้ราว 5% ของโควตาสัปดาห์ของแพ็กเกจ $200 · ช่วงนี้ใช้ 104% → ต้องลดราว 21 เท่า"
                               " · ชนเพดาน 22.9 ชม. (วัดจริง) · ประมาณการ")
    assert lines[10] == "- ส่วนของ Ultra ที่ CEO บอกว่าใช้น้อย: Jules (ดูแถว Jules ในตาราง)"
    assert [x.strip("- ").split(":")[0] for x in lines[11:]] == ["Google Flow Music", "เครดิต Google Cloud รายเดือนที่มากับแพ็กเกจ ($40–100 ตามแหล่งข่าว ยังไม่ยืนยัน)"]


def test_subscription_lines_missing_sources_and_no_targets():
    assert tv.subscription_lines({}, {}, {"providers": PLANS_WITH_TARGETS["providers"]}, W) == []
    late = {**PLANS_WITH_TARGETS, "targets": {"anthropic": {"usd": 20, "from": "2027-01-01"}}}
    assert "| Claude | 200 | 20 | 180 |" in tv.subscription_lines({}, {}, late, W)  # a goal shows before its date
    plans = {"providers": {"google": {"plans": [{"usd": 100, "from": "2026-09-01"}]}},
             "targets": PLANS_WITH_TARGETS["targets"]}
    lines = tv.subscription_lines({"claude_used_pct": tv._none("x")}, {}, plans, W)
    assert "| Claude | — | 20 | ไม่มีข้อมูล |" in lines
    assert not any(x.startswith("| รวม") for x in lines)  # no total while one price is unknown
    assert any(x.startswith("- งาน worker ที่ไม่ได้ใช้ Claude: ไม่มีข้อมูล") for x in lines)
    assert "- Claude เทียบเป้า: ไม่มีข้อมูล (ไม่รู้ราคาแพ็กเกจหรือโควตาที่ใช้ในช่วงนี้)" in lines


def test_build_report_carries_the_subscription_section(payload):
    rows = {"contabo": payload}
    text = tv.build_report(rows, rows, W, W, plans=PLANS_WITH_TARGETS)["text"]
    assert "ค่าแพ็กเกจต่อเดือน เทียบเป้าของ CEO (14 ต.ค.):" in text
    assert text.index("ค่าแพ็กเกจต่อเดือน") < text.index("ณ เวลาที่ Claude รีเซ็ต")
    assert "ค่าแพ็กเกจต่อเดือน" not in tv.build_report(rows, rows, W, W, plans={})["text"]


def test_live_plans_yaml_targets_total_140():
    plans = tv._load_yaml(tv.PLANS_CONFIG)
    assert sum(t["usd"] for t in plans["targets"].values()) == 140
    assert set(plans["targets"]) <= set(plans["providers"])


def test_subscription_lines_claude_already_at_target():
    plans = {**PLANS_WITH_TARGETS, "providers": {**PLANS_WITH_TARGETS["providers"],
                                                 "anthropic": {"plans": [{"usd": 20, "from": "2026-09-01"}]}}}
    lines = tv.subscription_lines({"claude_used_pct": tv._cell(50.0, "measured")}, {}, plans, W)
    assert "- Claude: แพ็กเกจ $20 ไม่เกินเป้า $20 แล้ว (ตาม plans.yaml ณ สิ้นช่วง)" in lines



REAL_FETCH_AGY_BROWSE_HUB = tv.fetch_agy_browse_hub  # bound at import, before `isolate` replaces it


def test_agy_browse_hub_keys_union_with_the_file(monkeypatch):
    rows = [{"payload": json.dumps({"ts": "2026-10-07T03:00:00.000001Z", "verb": "read", "port": 9280})},
            {"payload": {"ts": "2026-10-07T03:00:00.000001Z", "verb": "read", "port": 9280}},  # same call twice
            {"payload": json.dumps({"ts": "2026-10-14T03:00:00.000001Z", "verb": "read", "port": 9280})},  # outside W
            {"payload": "not json"}]
    seen = []

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, args):
            seen.append((sql, args))
            return type("R", (), {"fetchall": lambda self: rows})()

    import lib.db
    monkeypatch.setattr(lib.db, "get_conn", lambda **kw: Conn())
    assert REAL_FETCH_AGY_BROWSE_HUB(W) == {"calls": 1, "keys": ["2026-10-07T03:00:00.000001Z|read|9280"]}
    assert "kind=?" in seen[0][0] and seen[0][1][0] == "agy_browse"
    # build_rows unions file keys and hub keys: the same call counted once.
    payload = {"org": True, "sources": {"agy_browse": {"keys": ["2026-10-07T03:00:00.000001Z|read|9280", "x|tabs|9280"]},
                                        "agy_browse_hub": {"keys": ["2026-10-07T03:00:00.000001Z|read|9280"]}}}
    assert tv.build_rows({"contabo": payload}, W, ("contabo",), {})["agy_browse_calls"]["value"] == 2


def test_agent_calls_usage_counts_the_t4_spool():
    got = tv.agent_calls_usage(F / "agent-calls.jsonl", W)
    assert {k: got[k] for k in ("calls", "read_only", "routed", "override", "unrouted", "background", "sessions")} == \
        {"calls": 4, "read_only": 1, "routed": 1, "override": 1, "unrouted": 1, "background": 1, "sessions": 2}
    assert got["types"] == {"general-purpose": 3, "Explore": 1}
    assert got["first_ts"] == tv.iso(tv.parse_ts("2026-10-07T03:00:00Z"))   # the 14 Oct line is outside W
    with pytest.raises(tv.SourceMissing):
        tv.agent_calls_usage(F / "no-such-spool.jsonl", W)


def _agent_rows(first_ts, **counts):
    src = {"calls": 4, "read_only": 1, "routed": 1, "override": 1, "unrouted": 1, "background": 1, "sessions": 2,
           "types": {}, "first_ts": first_ts, **counts}
    return {"contabo": {"host": "contabo", "org": True, "sources": {"agent_calls": src}, "missing": []}}


def test_agent_call_cells_started_mid_window():
    c = tv.build_rows(_agent_rows("2026-10-07T03:00:00Z"), W, ("contabo",), {})
    assert c["agent_calls"]["value"] == 4 and c["agent_calls"]["label"] == "measured"
    assert "อ่านอย่างเดียว 1" in c["agent_calls"]["note"] and "2 session" in c["agent_calls"]["note"]
    assert "เริ่มเก็บ 07/10 10:00" in c["agent_calls"]["note"]                # BKK, so a partial week shows
    assert c["agent_calls_unrouted"]["value"] == 1
    assert "มี route: 1 · มี override: 1" in c["agent_calls_unrouted"]["note"]


def test_agent_call_cells_before_the_hook_are_no_data_not_zero():
    for first in ("2026-10-14T01:00:00Z", None):                         # started after W, or an empty spool
        c = tv.build_rows(_agent_rows(first, calls=0, unrouted=0), W, ("contabo",), {})
        assert c["agent_calls"]["label"] == "none" and c["agent_calls"]["value"] is None
        assert c["agent_calls_unrouted"]["label"] == "none"
    c = tv.build_rows({"contabo": {"host": "contabo", "org": True, "sources": {}, "missing": []}}, W, ("contabo",), {})
    assert c["agent_calls"]["label"] == "none"                             # the host never sent the source


def test_router_off_summary_counts_tasks_once():
    ev = lambda ts, task, **p: {"ts": ts, "task_id": task, "payload": json.dumps(p)}
    rows = [ev("2026-10-01T00:00:00Z", "task-00000000", reason="", runner="claude"),               # before W: first_ts only
            ev("2026-10-07T00:00:00Z", "task-11111111", reason="security: creds", runner="claude", pinned=True),
            ev("2026-10-07T00:05:00Z", "task-11111111", reason="security: creds", runner="claude", pinned=True),  # retry
            ev("2026-10-08T00:00:00Z", "task-22222222", reason="", runner="agy"),
            ev("2026-10-09T00:00:00Z", None, reason="just because", runner="claude"),
            {"ts": "2026-10-10T00:00:00Z", "task_id": "task-33333333", "payload": "not json"}]
    got = tv.router_off_summary(rows, W)
    assert got["tasks"] == 4 and got["pinned"] == 1
    assert got["reasons"] == {"ไม่ระบุ": 2, "free-text": 1, "security": 1}
    assert got["runners"] == {"claude": 2, "?": 1, "agy": 1}
    assert got["first_ts"] == tv.iso(tv.parse_ts("2026-10-01T00:00:00Z"))


def test_router_off_cell_is_no_data_until_the_first_event():
    row = lambda src: {"contabo": {"host": "contabo", "org": True, "sources": {"router_off": src}, "missing": []}}
    base = {"tasks": 0, "pinned": 0, "reasons": {}, "runners": {}}
    for first in (None, "2026-10-14T00:00:00Z"):
        c = tv.build_rows(row({**base, "first_ts": first}), W, ("contabo",), {})
        assert c["router_off"]["label"] == "none" and "router_off" in c["router_off"]["note"]
    c = tv.build_rows(row({**base, "first_ts": "2026-10-01T00:00:00Z"}), W, ("contabo",), {})
    assert c["router_off"] == {"value": 0, "label": "measured", "note": "pin อยู่แล้ว 0"}  # a real zero once it exists
    c = tv.build_rows(row({**base, "tasks": 2, "pinned": 1, "reasons": {"security": 2},
                           "first_ts": "2026-10-07T03:00:00Z"}), W, ("contabo",), {})
    assert c["router_off"]["value"] == 2
    assert c["router_off"]["note"] == "pin อยู่แล้ว 1 · เหตุผล: security 2 · เริ่มเก็บ 07/10 10:00"
