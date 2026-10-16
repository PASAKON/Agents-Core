"""Spend-cap contract for the tools that sit behind a spend-labelled Run card (task-407a64ce).

The rule (Console docs/run.md §Spend label): a command on a spend-labelled card carries
`--max-usd N` or `--max-credits N`; the tool stops before any call that would take its running
total past N, prints `spend cap reached: spent X of N <unit>` and exits 3; every ArgumentParser in
the file sets allow_abbrev=False, or `--max 100` is silently expanded to the cap flag.

Two halves:
  A. all 8 files: an abbreviation of a real flag is rejected. Each case first proves the
     abbreviation WOULD parse with abbreviations switched back on, so it cannot pass vacuously.
  B. the tools that click a paid button (flow_shoot, gen_loop, credit_fire, champa_fire and, since
     iteration 2, topview_wan3 and flow_music): with --max-credits N the tool makes no call that
     would pass N, nothing after it, and exits 3; without the flag nothing changes.
     bl_realfootage and ilag_round make no paid call, so they are in half A only.

Iteration 2 (CTO feedback) is the last section: topview_wan3's cap is a run total, flow_music gets a
run-total --max-credits, flow_shoot accepts --max-credits without --credit-cap, and the hub's own
cap_flag_check accepts the command each of them will carry.

HARD: no network and no spend. Every provider key is stripped from the environment, sockets and
urlopen refuse, and the paid click is a stub in every test. Nothing here runs a tool for real.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import socket
import sys
import types
import urllib.request
from pathlib import Path

import pytest

from scripts.champa import champa_fire
from scripts.higgsfield import credit_fire, gen_loop
from tools import ask_run, bl_realfootage, flow_ledger, flow_music, flow_shoot, topview_wan3

REPO = Path(__file__).resolve().parent.parent
_CAP_ARGS = (flow_shoot.spend_cap_arg, gen_loop.spend_cap_arg, credit_fire.spend_cap_arg,
             champa_fire.spend_cap_arg, topview_wan3.spend_cap_arg, flow_music.spend_cap_arg)
FIXTURE_SHEET = REPO / "docs" / "scripts" / "banchi-ACT2.md"

# Exact names the eight files (and tools.decide, which two of them import) read, plus the prefixes a
# provider key could hide under. WORK_* changes flow_shoot's --dest rule, so it goes too.
_PROVIDER_NAMES = (
    "FAL_KEY", "OPENROUTER_API_KEY", "DECIDE_PROVIDER", "DECIDE_BUDGET_USD", "DECIDE_JEV_MODEL",
    "JEV_API_KEY", "JEV_API_URL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DRIVE_VIDEO_PARENT_FOLDER_ID",
    "WORKER_CTO_ID", "ORG_DB_URL", "FLOW_CDP", "FLOW_COMPLETION_TIMEOUT_S", "FLOW_CARD_OPEN_WAIT_S",
)
_PROVIDER_PREFIXES = ("HIGGSFIELD_", "TOPVIEW_", "CHAMPA_", "GOOGLE_OAUTH_", "FAL_", "OPENROUTER_",
                      "WORK_", "ILAG_", "KLING_", "ELEVENLABS_")


def _refuse_network(*_a, **_k):
    raise AssertionError("network call attempted in a spend-cap test")


@pytest.fixture(autouse=True)
def _no_keys_no_network(monkeypatch):
    for name in list(os.environ):
        if name in _PROVIDER_NAMES or name.startswith(_PROVIDER_PREFIXES):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(socket.socket, "connect", _refuse_network)
    monkeypatch.setattr(urllib.request, "urlopen", _refuse_network)
    monkeypatch.setattr(sys, "path", list(sys.path))  # importing ilag_round inserts into it


def test_provider_keys_are_stripped():
    leftovers = [n for n in os.environ if n in _PROVIDER_NAMES or n.startswith(_PROVIDER_PREFIXES)]
    assert leftovers == []


# ── half A: allow_abbrev=False on every parser ───────────────────────────────────────────

class _Captured(Exception):
    pass


def capture_parser(run) -> argparse.ArgumentParser:
    """The parser a main() builds, taken at its first parse_args() call. Nothing after that line
    of main() runs, so no tool code executes beyond building the parser."""
    holder = {}

    def spy(self, args=None, namespace=None):
        holder["parser"] = self
        raise _Captured

    with pytest.MonkeyPatch.context() as m:
        m.setattr(argparse.ArgumentParser, "parse_args", spy)
        with pytest.raises(_Captured):
            run()
    return holder["parser"]


def parser_tree(parser):
    yield parser
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                yield from parser_tree(sub)


def parses(parser, argv, errors=(SystemExit,)) -> bool:
    try:
        parser.parse_args(argv)
        return True
    except errors as e:
        if isinstance(e, SystemExit):
            assert e.code == 2
        return False


def assert_abbrev_rejected(parser, ok_argv, abbrev_argv, errors=(SystemExit,)):
    assert parses(parser, ok_argv, errors), "the full spelling must parse, or the case proves nothing"
    tree = list(parser_tree(parser))
    shipped = [p.allow_abbrev for p in tree]
    for p in tree:
        p.allow_abbrev = True
    try:
        assert parses(parser, abbrev_argv, errors), "control: with abbreviations on, this must parse"
    finally:
        for p, was in zip(tree, shipped):
            p.allow_abbrev = was
    assert not parses(parser, abbrev_argv, errors), f"{abbrev_argv} was accepted as an abbreviation"


def test_flow_music_abbrev_rejected():
    parser = capture_parser(lambda: flow_music.main(["x"]))
    base = ["p.json", "--out", "o", "--max-credits", "20"]
    # `--max` / `--max-c` are ambiguous between --max-credits and --max-credits-per-track (argparse refuses
    # them even with abbreviations on), so the proof uses the longer abbreviation that WOULD expand
    assert_abbrev_rejected(parser, base + ["--max-credits-per-track", "5"], base + ["--max-credits-per", "5"])


def test_topview_wan3_abbrev_rejected():
    parser = capture_parser(lambda: topview_wan3.main(["x"]))
    base = ["--out", "o"]
    assert_abbrev_rejected(parser, base + ["--max-credits", "3"], base + ["--max", "3"])
    assert_abbrev_rejected(parser, base + ["--max-credits", "3"], base + ["--max-c", "3"])


def test_flow_shoot_abbrev_rejected_on_every_subcommand():
    parser = flow_shoot.build_parser()
    run = ["run", "--sheet", "s", "--ledger", "l", "--dest", "d", "--credit-cap", "100"]
    assert_abbrev_rejected(parser, run + ["--max-credits", "100"], run + ["--max", "100"])
    assert_abbrev_rejected(parser, run + ["--max-credits", "100"], run + ["--max-c", "100"])
    pull = ["pull", "--sheet", "s", "--ledger", "l", "--dest", "d"]
    assert_abbrev_rejected(parser, pull + ["--only", "5"], pull + ["--on", "5"])
    status = ["status"]
    assert_abbrev_rejected(parser, status + ["--ledger", "l"], status + ["--led", "l"])


def test_gen_loop_abbrev_rejected(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["gen_loop.py"])
    parser = capture_parser(gen_loop.main)
    assert_abbrev_rejected(parser, ["--csv", "c", "--max-credits", "5"], ["--csv", "c", "--max", "5"])


def test_credit_fire_abbrev_rejected(tmp_path):
    parser = credit_fire.build_parser()
    errors = (credit_fire.ArgumentParsingError,)
    base = ["--prompts", "p.csv"]
    assert_abbrev_rejected(parser, base + ["--max-credits", "5"], base + ["--max-c", "5"], errors)
    assert_abbrev_rejected(parser, base + ["--budget", "5"], base + ["--bud", "5"], errors)
    # main() turns the same parser error into exit code 2 before it touches the page
    assert credit_fire.main(base + ["--max-c", "5"]) == 2


def test_champa_fire_abbrev_rejected():
    parser = champa_fire.build_parser()
    errors = (champa_fire.ArgumentParsingError,)
    base = ["--prompts", "p.csv"]
    assert_abbrev_rejected(parser, base + ["--max-credits", "5"], base + ["--max-c", "5"], errors)
    assert_abbrev_rejected(parser, base + ["--max-jobs", "2"], base + ["--max-j", "2"], errors)
    assert champa_fire.main(base + ["--max-c", "5"]) == 2


def test_bl_realfootage_abbrev_rejected():
    parser = bl_realfootage.build_arg_parser()
    base = ["run", "--shots", "s.yaml", "--episode", "bl1"]
    assert_abbrev_rejected(parser, base + ["--dry-run"], base + ["--dry"])
    assert_abbrev_rejected(parser, base + ["--episode", "bl2"], ["run", "--shots", "s.yaml", "--epis", "bl2"])


def test_ilag_round_abbrev_rejected(monkeypatch):
    # tools/ilag_round.py imports the Drive bridge at module level; a stub keeps that import inert.
    monkeypatch.setitem(sys.modules, "ilag_rest", types.ModuleType("ilag_rest"))
    try:
        ilag_round = importlib.import_module("tools.ilag_round")
        monkeypatch.setattr(sys, "argv", ["ilag_round.py"])
        parser = capture_parser(ilag_round.main)
    finally:
        sys.modules.pop("tools.ilag_round", None)
    base = ["--round", "1", "--item", "a=b"]
    assert_abbrev_rejected(parser, base + ["--no-drive"], base + ["--no-dr"])


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf", "-1", "abc", ""])
def test_cap_value_that_would_never_trip_is_refused(bad):
    """spent + cost > nan is always False: a NaN cap would let every call through."""
    for fn in _CAP_ARGS:
        with pytest.raises((argparse.ArgumentTypeError, ValueError)):
            fn(bad)


@pytest.mark.parametrize("good, value", [("0", 0.0), ("5", 5.0), ("2.5", 2.5)])
def test_plain_cap_numbers_are_accepted(good, value):
    for fn in _CAP_ARGS:
        assert fn(good) == value


# ── half B: flow_shoot (credits; the cost is the panel's estimate, read before every Submit) ──

class _FlowStub:
    """A FlowBrowser whose Submit is a counter. poll_result says 'timeout' so each shot ends after
    exactly one Submit (a refusal would trigger the runner's one re-fire)."""

    def __init__(self, estimate: int):
        self.estimate = estimate
        self.submits = 0
        self.dry_run = False
        self._chips = 0
        self._pasted = ""

    def attach(self): pass
    def mute_all_media(self): pass
    def close(self): pass
    def reset_composer(self): self._chips = 0

    def set_settings(self, dur_s, resolution="720p"):
        return {"model_omni": True, "mode_ingredients": True, "aspect_9_16": True,
                "qty_x1": True, "resolution": True, "duration": True}

    def attach_chip(self, _handle): self._chips += 1; return True
    def chip_count(self): return self._chips
    def paste_prompt(self, text): self._pasted = text
    def read_prompt_text(self): return self._pasted
    def read_credit_estimate(self): return self.estimate
    def submit(self, expected_chip_count=None): self.submits += 1
    def poll_result(self, timeout_s=0): return {"status": "timeout", "text": ""}
    def download(self): raise AssertionError("download() is never reached: every shot times out")


def _flow_run(tmp_path, estimate, *flags, credit_cap="9999"):
    cap_flags = ["--credit-cap", credit_cap] if credit_cap is not None else []
    args = flow_shoot.build_parser().parse_args([
        "run", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / "l.tsv"),
        "--dest", str(tmp_path / "dest"), *cap_flags, "--only", "35-37", *flags])
    stub = _FlowStub(estimate)
    return flow_shoot.cmd_run(args, browser_factory=lambda: stub), stub


def test_flow_shoot_stops_before_the_submit_that_would_pass_the_cap(tmp_path, capsys):
    rc, stub = _flow_run(tmp_path, 40, "--max-credits", "100")
    assert rc == 3
    assert stub.submits == 2                       # 40 + 40 = 80 <= 100; the third would make 120
    assert "spend cap reached: spent 80 of 100 credits" in capsys.readouterr().out
    rows = flow_ledger.load_ledger(tmp_path / "l.tsv")
    assert rows[37]["status"] == "todo"            # shot 37 was never submitted


def test_flow_shoot_total_equal_to_the_cap_is_allowed(tmp_path, capsys):
    rc, stub = _flow_run(tmp_path, 40, "--max-credits", "120")
    assert stub.submits == 3                       # 120 is not past 120
    assert "spend cap reached" not in capsys.readouterr().out
    assert rc == 1                                 # unchanged: the stub's shots ended in 'timeout'


def test_flow_shoot_without_the_flag_is_unchanged(tmp_path, capsys):
    rc, stub = _flow_run(tmp_path, 40)
    assert stub.submits == 3 and rc == 1
    assert "spend cap reached" not in capsys.readouterr().out


def test_flow_shoot_spend_cap_wins_when_the_legacy_cap_trips_too(tmp_path, capsys):
    rc, stub = _flow_run(tmp_path, 40, "--max-credits", "30", credit_cap="30")
    assert stub.submits == 0 and rc == 3           # the legacy --credit-cap alone would exit 0
    assert "spend cap reached: spent 0 of 30 credits" in capsys.readouterr().out


def test_flow_shoot_backstop_blocks_submit_even_if_the_pre_check_is_skipped():
    stub = _FlowStub(40)
    with pytest.raises(flow_shoot.SpendCapReached):
        flow_shoot._submit_or_raise(stub, 80, 40, 9999, 3, max_credits=100)
    assert stub.submits == 0
    flow_shoot._submit_or_raise(stub, 80, 40, 9999, 3, max_credits=120)
    assert stub.submits == 1


# ── half B: gen_loop (credits; the cost is the number on the Generate button) ──────────────

class _GenPage:
    """Just enough of a Playwright page for gen_loop.main(): the Generate button shows `label`,
    every click on it is counted, and evaluate() says whether generation started."""

    def __init__(self, label, started=(True,)):
        self.label = label
        self.url = "https://higgsfield.ai/ai/video"
        self.clicks = 0
        self._started = list(started)
        self.keyboard = types.SimpleNamespace(press=lambda *_a, **_k: None)

    def bring_to_front(self): pass
    def wait_for_timeout(self, _ms): pass

    def query_selector(self, sel):
        if sel == "button[type=submit]":
            return types.SimpleNamespace(inner_text=lambda: self.label)
        return None

    def locator(self, sel):
        page = self

        class _Loc:
            first = None

            def click(self, *_a, **_k):
                if sel == "button[type=submit]":
                    page.clicks += 1

        loc = _Loc()
        loc.first = loc
        return loc

    def evaluate(self, script):
        if "generating" in script:
            return self._started.pop(0) if len(self._started) > 1 else self._started[0]
        return None


def _gen_run(monkeypatch, tmp_path, page, *flags, clips=3):
    csv_path = tmp_path / "clips.csv"
    csv_path.write_text("clip_id,prompt,category,subcategory,palette,duration\n" + "".join(
        f"c{i},prompt {i},trading,sub,pal,8\n" for i in range(1, clips + 1)), encoding="utf-8")

    class _PW:
        chromium = None

        def __init__(self):
            self.chromium = self

        def connect_over_cdp(self, _url):
            return types.SimpleNamespace(contexts=[types.SimpleNamespace(pages=[page])])

        def __enter__(self): return self
        def __exit__(self, *_a): return False

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = _PW
    pkg = types.ModuleType("playwright")
    pkg.sync_api = sync_api
    monkeypatch.setitem(sys.modules, "playwright", pkg)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)

    monkeypatch.setattr(gen_loop, "resolve_local_root", lambda: tmp_path / "out")
    monkeypatch.setattr(gen_loop, "done_ids", lambda: set())
    monkeypatch.setattr(gen_loop, "load_env", lambda: {"DRIVE_VIDEO_PARENT_FOLDER_ID": "x"})
    monkeypatch.setattr(gen_loop, "drive_token", lambda _env: "token")
    monkeypatch.setattr(gen_loop, "drive_folder", lambda *_a, **_k: "folder")
    monkeypatch.setattr(gen_loop, "DRIVE_CACHE", tmp_path / "drive_cache.json")
    monkeypatch.setattr(gen_loop, "ensure_config", lambda _page: True)
    monkeypatch.setattr(gen_loop, "type_prompt", lambda *_a, **_k: None)
    monkeypatch.setattr(gen_loop, "check_free_space", lambda **_k: None)
    monkeypatch.setattr(gen_loop, "_hf_urls", lambda _page: [])
    monkeypatch.setattr(gen_loop, "poll_for_result",
                        lambda *_a, **_k: {"status": "refusal", "text": "stub"})
    monkeypatch.setattr(gen_loop.time, "sleep", lambda _s: None)
    monkeypatch.setattr(sys, "argv", ["gen_loop.py", "--csv", str(csv_path), *flags])
    try:
        gen_loop.main()
    except SystemExit as e:
        return e.code
    return None


def test_gen_loop_stops_before_the_click_that_would_pass_the_cap(monkeypatch, tmp_path, capsys):
    page = _GenPage("Generate 80 60")
    code = _gen_run(monkeypatch, tmp_path, page, "--max-credits", "100")
    assert code == 3
    assert page.clicks == 1                        # 60 <= 100; the second would make 120
    assert "spend cap reached: spent 60 of 100 credits" in capsys.readouterr().out


def test_gen_loop_total_equal_to_the_cap_is_allowed(monkeypatch, tmp_path, capsys):
    page = _GenPage("Generate 80 60")
    code = _gen_run(monkeypatch, tmp_path, page, "--max-credits", "120")
    assert code == 3 and page.clicks == 2          # clip 3 would make 180
    assert "spend cap reached: spent 120 of 120 credits" in capsys.readouterr().out


def test_gen_loop_without_the_flag_is_unchanged(monkeypatch, tmp_path, capsys):
    page = _GenPage("Generate 80 60")
    assert _gen_run(monkeypatch, tmp_path, page) is None
    assert page.clicks == 3
    assert "spend cap reached" not in capsys.readouterr().out


def test_gen_loop_unlimited_label_costs_nothing_even_under_cap_zero(monkeypatch, tmp_path):
    page = _GenPage("UNLIMITED · 140 0")
    assert _gen_run(monkeypatch, tmp_path, page, "--max-credits", "0") is None
    assert page.clicks == 3


def test_gen_loop_unreadable_label_is_priced_at_the_largest_known_cost(monkeypatch, tmp_path, capsys):
    page = _GenPage("Buy credits")                 # parse_price -> None: the price is unknown
    code = _gen_run(monkeypatch, tmp_path, page, "--max-credits", "100")
    assert code == 3 and page.clicks == 0          # 140 > 100: no click at all
    assert "spend cap reached: spent 0 of 100 credits" in capsys.readouterr().out
    assert gen_loop.UNKNOWN_CLICK_CREDITS == 140


def test_gen_loop_retry_click_is_a_second_paid_call_and_is_capped(monkeypatch, tmp_path, capsys):
    page = _GenPage("Generate 80 60", started=(False,))   # generation never starts -> retry click
    code = _gen_run(monkeypatch, tmp_path, page, "--max-credits", "100")
    assert code == 3 and page.clicks == 1          # the retry would make 120
    assert "spend cap reached: spent 60 of 100 credits" in capsys.readouterr().out


# ── half B: credit_fire (credits; the cost is the number on the submit button) ─────────────

class _HiggsAdapter:
    def __init__(self, label="Generate 80 60"):
        self.label = label
        self.typed = []
        self.clicks = 0

    def read_label(self): return self.label if self.typed else "Generate"
    def read_settings(self): return {"duration": "5s", "ratio": "16:9", "resolution": "1080p"}
    def apply_settings(self, **_k): pass
    def has_textbox(self): return True
    def type_prompt(self, text): self.typed.append(text)
    def click_submit(self): self.clicks += 1
    def newest_ts(self): return "20260101_000000"

    def poll(self, _t0, timeout_s=900):
        return {"status": "download", "url": "https://stub.invalid/hf_20260101_000001_a.mp4"}

    def download(self, _url, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"x")
        return 1

    def close(self): pass


def _fire(tmp_path, *flags, label="Generate 80 60", budget="1000"):
    prompts = tmp_path / "p.csv"
    prompts.write_text("clip_id,prompt\nc1,one\nc2,two\nc3,three\n", encoding="utf-8")
    adapter = _HiggsAdapter(label)
    rc = credit_fire.main(["--prompts", str(prompts), "--out", str(tmp_path / "out"), "--fire",
                           "--max-per-clip", "60", "--budget", budget, *flags], adapter=adapter)
    return rc, adapter


@pytest.fixture
def _fast_price_wait(monkeypatch):
    monkeypatch.setattr(credit_fire, "WAIT_PRICE_TIMEOUT_S", 0.05)
    monkeypatch.setattr(credit_fire, "WAIT_PRICE_POLL_S", 0.01)


def test_credit_fire_stops_before_the_click_that_would_pass_the_cap(tmp_path, capsys, _fast_price_wait):
    rc, adapter = _fire(tmp_path, "--max-credits", "100")
    assert rc == 3 and adapter.clicks == 1         # 60 <= 100; the second would make 120
    assert "spend cap reached: spent 60 of 100 credits" in capsys.readouterr().out


def test_credit_fire_total_equal_to_the_cap_is_allowed(tmp_path, capsys, _fast_price_wait):
    rc, adapter = _fire(tmp_path, "--max-credits", "120")
    assert rc == 3 and adapter.clicks == 2
    assert "spend cap reached: spent 120 of 120 credits" in capsys.readouterr().out


def test_credit_fire_without_the_flag_is_unchanged(tmp_path, capsys, _fast_price_wait):
    rc, adapter = _fire(tmp_path)
    assert rc == 0 and adapter.clicks == 3
    assert "spend cap reached" not in capsys.readouterr().out


def test_credit_fire_spend_cap_speaks_when_the_budget_would_refuse_too(tmp_path, capsys, _fast_price_wait):
    rc, adapter = _fire(tmp_path, "--max-credits", "100", budget="100")
    out = capsys.readouterr()
    assert rc == 3 and adapter.clicks == 1
    assert "spend cap reached: spent 60 of 100 credits" in out.out
    assert "SpendRefused" not in out.err


# ── half B: champa_fire (credits; the cost is the label's last integer, 0 on the Unlimited lane) ──

class _ChampaAdapter:
    """labels[i] is what the submit button reads after the i-th prompt is filled."""

    def __init__(self, labels):
        self.labels = labels
        self.filled = 0
        self.clicks = 0

    def has_textbox(self): return True
    def fill_prompt(self, _text): self.filled += 1
    def clear_prompt(self): pass

    def read_label(self):
        return self.labels[min(self.filled, len(self.labels)) - 1] if self.filled else "ส่งเข้าคิว"

    def read_unlimited_switch(self): return "true"
    def read_balance(self): return "1,350"

    def read_settings(self):
        return {"model": "Seedance 2.0", "ratio": "16:9", "duration": "4s", "resolution": "720p"}

    def apply_settings(self, **_k): pass
    def click_submit(self): self.clicks += 1
    def close(self): pass


_FREE = "ส่งเข้าคิว Unlimited 0"


def _champa_fire(tmp_path, labels, *flags):
    prompts = tmp_path / "p.csv"
    prompts.write_text("clip_id,prompt\nc1,one\nc2,two\nc3,three\n", encoding="utf-8")
    adapter = _ChampaAdapter(labels)
    rc = champa_fire.main(["--prompts", str(prompts), "--out", str(tmp_path / "out"), "--fire",
                           "--max-jobs", "3", *flags], adapter=adapter)
    return rc, adapter


@pytest.fixture
def _fast_label_wait(monkeypatch):
    monkeypatch.setattr(champa_fire, "WAIT_LABEL_TIMEOUT_S", 0.05)
    monkeypatch.setattr(champa_fire, "WAIT_LABEL_POLL_S", 0.01)


def test_champa_label_price_is_its_last_integer():
    assert champa_fire.label_credits(_FREE) == 0
    assert champa_fire.label_credits("ส่งเข้าคิว 5") == 5
    assert champa_fire.label_credits("Generate 80 60") == 60
    assert champa_fire.label_credits(None) == 0


def test_champa_fire_stops_before_the_submit_that_would_pass_the_cap(tmp_path, capsys, _fast_label_wait):
    # clip 1 is free; clip 2's button shows a price of 5 > cap 3. Nothing is clicked for clip 2.
    rc, adapter = _champa_fire(tmp_path, [_FREE, "ส่งเข้าคิว 5"], "--max-credits", "3")
    assert rc == 3 and adapter.clicks == 1
    assert "spend cap reached: spent 0 of 3 credits" in capsys.readouterr().out


def test_champa_fire_free_lane_runs_to_the_end_under_cap_zero(tmp_path, capsys, _fast_label_wait):
    rc, adapter = _champa_fire(tmp_path, [_FREE], "--max-credits", "0")
    assert rc == 0 and adapter.clicks == 3
    assert "spend cap reached" not in capsys.readouterr().out


def test_champa_fire_without_the_flag_is_unchanged(tmp_path, capsys, _fast_label_wait):
    # a priced label is refused by the guard exactly as before: exit 3, its own message, no click
    rc, adapter = _champa_fire(tmp_path, ["ส่งเข้าคิว 5"])
    out = capsys.readouterr()
    assert rc == 3 and adapter.clicks == 0
    assert "Refused by guard" in out.err and "spend cap reached" not in out.out


# ═══ iteration 2 (CTO feedback) ═══════════════════════════════════════════════════════════

def printed_line(out: str, message: str) -> bool:
    """The message on a line of its own. The stop note embeds the same words, so a substring test cannot
    tell whether the dedicated `spend cap reached: ...` line was printed."""
    return any(line.strip() == message for line in out.splitlines())


# ── topview_wan3: --max-credits is a RUN total across every job file given ─────────────────

class _TVPage:
    url = "https://www.topview.ai/board/stub"

    def wait_for_timeout(self, _ms): pass
    def reload(self, **_k): pass


class _TVBrowser:
    """Reads like the live page: a Generate button priced `cost`, a big balance, a paid plan.
    click_generate is a counter and nothing else."""

    def __init__(self, cost: float):
        self.cost = cost
        self.clicks = 0
        self.page = _TVPage()

    def attach(self): pass
    def close(self, keep_tab=False): pass
    def log(self, *_a): pass
    def media_srcs(self): return []
    def drain_network(self, _seen): pass

    def state(self):
        return {"genText": f"Generate {self.cost:g}", "costAria": None, "balanceText": "1000",
                "genDisabled": False, "dialogs": [], "pricingModal": "", "plan": "Pro"}

    def click_generate(self, _cost): self.clicks += 1


def _tv_jobs(tmp_path, n):
    refs = tmp_path / "refs"
    refs.mkdir(exist_ok=True)
    (refs / "a.png").write_bytes(b"x")
    paths = []
    for i in range(1, n + 1):
        job = tmp_path / f"n{i:02d}.wan3.json"
        job.write_text(json.dumps({"key": f"n{i:02d}", "title": "t", "seconds": 2,
                                   "images": ["C/a.png"], "prompt": "@Image1 x"}))
        paths.append(str(job))
    return paths


def _tv_main(monkeypatch, tmp_path, cost, n_jobs, *flags):
    browser = _TVBrowser(cost)
    monkeypatch.setattr(topview_wan3, "TopViewBrowser", lambda _url: browser)
    monkeypatch.setattr(topview_wan3, "prepare", lambda *_a, **_k: {
        "gen_text": "Generate 1", "balance_text": "1000", "model": "Wan 3.0", "aspect": "16:9",
        "seconds": "2s", "resolution": "SD 480p", "chips": ["@Image1"], "plan": "Pro"})
    monkeypatch.setattr(topview_wan3, "wait_for_clip",
                        lambda *_a, **_k: ("https://stub.invalid/v.mp4", b"x"))
    rc = topview_wan3.main([*_tv_jobs(tmp_path, n_jobs), "--out", str(tmp_path / "out"), *flags])
    return rc, browser


def test_topview_cap_is_a_run_total_across_jobs(monkeypatch, tmp_path, capsys):
    rc, b = _tv_main(monkeypatch, tmp_path, 1.5, 4, "--max-credits", "4")
    assert rc == 3
    assert b.clicks == 2                           # 1.5 + 1.5 = 3 <= 4; the third would make 4.5
    assert printed_line(capsys.readouterr().out, "spend cap reached: spent 3 of 4 credits")
    ledger = topview_wan3.load_ledger(tmp_path / "out" / "ledger.json")
    assert ledger["n03"]["status"] == "stopped" and ledger["n03"]["hazard_kind"] == "spend_cap"
    assert "n04" not in ledger                     # nothing after the stop was touched
    assert not (tmp_path / "out" / "n03.mp4").exists()


def test_topview_total_equal_to_the_cap_is_allowed(monkeypatch, tmp_path, capsys):
    rc, b = _tv_main(monkeypatch, tmp_path, 1.5, 3, "--max-credits", "4.5")
    assert rc == 0 and b.clicks == 3
    assert "spend cap reached" not in capsys.readouterr().out


def test_topview_one_job_dearer_than_the_cap_fires_nothing_and_exits_3(monkeypatch, tmp_path, capsys):
    rc, b = _tv_main(monkeypatch, tmp_path, 2, 2, "--max-credits", "1")
    assert rc == 3 and b.clicks == 0               # the old per-job stop was exit 1
    assert printed_line(capsys.readouterr().out, "spend cap reached: spent 0 of 1 credits")


def test_topview_float_noise_does_not_stop_a_run_at_exactly_the_cap(monkeypatch, tmp_path):
    assert 0.1 + 0.1 + 0.1 > 0.3                   # the trap: three 0.1s sum to 0.30000000000000004
    rc, b = _tv_main(monkeypatch, tmp_path, 0.1, 3, "--max-credits", "0.3")
    assert rc == 0 and b.clicks == 3


def test_topview_dry_run_fires_nothing_and_is_not_capped(monkeypatch, tmp_path, capsys):
    rc, b = _tv_main(monkeypatch, tmp_path, 1.5, 2, "--max-credits", "0", "--dry-run")
    assert rc == 0 and b.clicks == 0
    assert "spend cap reached" not in capsys.readouterr().out


def test_topview_a_job_already_fired_costs_nothing_this_run(monkeypatch, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "ledger.json").write_text(json.dumps({"n01": {"key": "n01", "status": "done"}}))
    rc, b = _tv_main(monkeypatch, tmp_path, 1.5, 2, "--max-credits", "1.5")
    assert rc == 0 and b.clicks == 1               # n01 is read back as done; only n02 is clicked


def test_topview_max_credits_is_still_required(tmp_path):
    with pytest.raises(SystemExit) as e:
        topview_wan3.main([*_tv_jobs(tmp_path, 1), "--out", str(tmp_path / "out")])
    assert e.value.code == 2


# ── flow_music: --max-credits is a RUN total, checked before each click against the worst track ──

class _FMPage:
    url = "https://www.flowmusic.app/session/00000000-0000-0000-0000-000000000000"

    def wait_for_timeout(self, _ms): pass
    def evaluate(self, _script): return 1          # the song card is on the session page


class _FMBrowser:
    """A Flow Music whose Generate click takes `charge` off the balance. The price is not shown
    before the click, as on the live page (measured 2026-09-26)."""

    def __init__(self, charge: float, balance: float = 1000.0, blind_after_click: bool = False):
        self.charge, self.balance, self.clicks = charge, balance, 0
        self.blind_after_click, self.reads = blind_after_click, 0
        self.page = _FMPage()
        self.debug_net = False
        self.api_credits = None

    def attach(self): pass
    def close(self, keep_tab=False): pass
    def log(self, *_a): pass
    def library_clips(self): return []
    def drain(self): return []
    def read_balance(self):
        self.reads += 1
        if self.blind_after_click and self.reads % 2 == 0:   # run_item reads before (odd) and after (even)
            return None, "unreadable"
        return self.balance, f"{self.balance:g} credits"

    def state(self):
        return {"genCount": 1, "genText": "Generate", "genDisabled": False, "dialogs": [],
                "url": self.page.url}

    def click_generate(self):
        self.clicks += 1
        self.balance -= self.charge


def _fm_prompts(tmp_path, n):
    f = tmp_path / "prompts.json"
    f.write_text(json.dumps([{"id": f"A{i}", "title": f"t{i}", "prompt": f"piano {i}"}
                             for i in range(1, n + 1)]))
    return str(f)


def _fm_main(monkeypatch, tmp_path, charge, n, *flags, blind_after_click=False):
    browser = _FMBrowser(charge, blind_after_click=blind_after_click)
    monkeypatch.setattr(flow_music, "FlowMusicBrowser", lambda _url, debug_net=False: browser)
    monkeypatch.setattr(flow_music, "prepare", lambda *_a, **_k: {
        "compose_url": "u", "instrumental": True, "length": "1:00", "bpm": "Auto", "model": "Lyria 3.5",
        "title_set": None, "gen_text": "Generate", "gen_count": 1, "gen_disabled": False, "dialogs": [],
        "prompt_chars": 7})
    monkeypatch.setattr(flow_music, "wait_for_songs", lambda *_a, **_k: [{"id": "c1"}])
    monkeypatch.setattr(flow_music, "collect", lambda *_a, **_k: [{"file": "stub.wav"}])
    rc = flow_music.main([_fm_prompts(tmp_path, n), "--out", str(tmp_path / "out"), *flags])
    return rc, browser


def test_flow_music_worst_track_figure_is_the_one_the_file_and_its_ledgers_state():
    assert flow_music.WORST_TRACK_CREDITS == 5.0
    ledger = json.loads((REPO / "docs/promo/topview-trailer/MUSIC-LEDGER.json").read_text())
    rows = ledger.values() if isinstance(ledger, dict) else ledger
    charges = [r["charged"] for r in rows if isinstance(r, dict) and r.get("charged") is not None]
    assert charges and max(charges) <= flow_music.WORST_TRACK_CREDITS   # no recorded track cost more


def test_flow_music_stops_before_the_click_that_could_pass_the_cap(monkeypatch, tmp_path, capsys):
    rc, b = _fm_main(monkeypatch, tmp_path, 5, 3, "--max-credits", "12")
    assert rc == 3
    assert b.clicks == 2                           # 5 + 5 = 10 spent; a third track may charge 5 -> 15 > 12
    assert printed_line(capsys.readouterr().out, "spend cap reached: spent 10 of 12 credits")
    ledger = flow_music.load_ledger(tmp_path / "out" / "ledger.json")
    assert ledger["A3"]["status"] == "stopped" and ledger["A3"]["hazard_kind"] == "spend_cap"


def test_flow_music_total_equal_to_the_cap_is_allowed(monkeypatch, tmp_path, capsys):
    rc, b = _fm_main(monkeypatch, tmp_path, 5, 3, "--max-credits", "15")
    assert rc == 0 and b.clicks == 3
    assert "spend cap reached" not in capsys.readouterr().out


def test_flow_music_counts_the_measured_charge_not_the_worst_case(monkeypatch, tmp_path, capsys):
    # tracks charge 2: after each, the total is the actual 2, not the 5 reserved at the click
    rc, b = _fm_main(monkeypatch, tmp_path, 2, 6, "--max-credits", "12")
    assert rc == 3 and b.clicks == 4               # 2, 4, 6, 8 spent; the fifth could reach 13 > 12
    assert printed_line(capsys.readouterr().out, "spend cap reached: spent 8 of 12 credits")


def test_flow_music_an_unreadable_balance_after_a_track_keeps_the_worst_case_reservation(monkeypatch, tmp_path, capsys):
    # the charge cannot be measured, so each track stays counted at WORST_TRACK_CREDITS (5): 5, 10, then stop
    rc, b = _fm_main(monkeypatch, tmp_path, 5, 3, "--max-credits", "12", blind_after_click=True)
    assert rc == 3 and b.clicks == 2
    assert printed_line(capsys.readouterr().out, "spend cap reached: spent 10 of 12 credits")


def test_flow_music_a_cap_below_one_track_fires_nothing(monkeypatch, tmp_path, capsys):
    rc, b = _fm_main(monkeypatch, tmp_path, 5, 2, "--max-credits", "4")
    assert rc == 3 and b.clicks == 0
    assert printed_line(capsys.readouterr().out, "spend cap reached: spent 0 of 4 credits")


def test_flow_music_track_dearer_than_assumed_ends_the_run_even_with_max_credits_alone(monkeypatch, tmp_path, capsys):
    # --max-credits-per-track was not given: it defaults to WORST_TRACK_CREDITS, so a track that charged 9
    # is the old per-track stop (exit 1) while the run total (9 <= 20) is still inside the cap
    rc, b = _fm_main(monkeypatch, tmp_path, 9, 3, "--max-credits", "20")
    out = capsys.readouterr().out
    assert rc == 1 and b.clicks == 1
    assert "STOP after A1: charged 9.0 > --max-credits-per-track 5.0" in out
    assert "spend cap reached" not in out


def test_flow_music_track_that_takes_the_run_past_the_cap_exits_3(monkeypatch, tmp_path, capsys):
    rc, b = _fm_main(monkeypatch, tmp_path, 9, 3, "--max-credits", "8")
    assert rc == 3 and b.clicks == 1
    assert printed_line(capsys.readouterr().out, "spend cap reached: spent 9 of 8 credits")


def test_flow_music_per_track_flag_alone_behaves_as_before(monkeypatch, tmp_path, capsys):
    rc, b = _fm_main(monkeypatch, tmp_path, 5, 3, "--max-credits-per-track", "20")
    assert rc == 0 and b.clicks == 3
    assert "spend cap reached" not in capsys.readouterr().out


def test_flow_music_per_track_flag_still_stops_the_run_after_a_dearer_track(monkeypatch, tmp_path, capsys):
    rc, b = _fm_main(monkeypatch, tmp_path, 5, 3, "--max-credits-per-track", "4")
    out = capsys.readouterr().out
    assert rc == 1 and b.clicks == 1
    assert "STOP after A1: charged 5.0 > --max-credits-per-track 4.0" in out and "spend cap reached" not in out


def test_flow_music_both_flags_together_the_run_total_still_applies(monkeypatch, tmp_path):
    rc, b = _fm_main(monkeypatch, tmp_path, 5, 3, "--max-credits", "12", "--max-credits-per-track", "20")
    assert rc == 3 and b.clicks == 2


def test_flow_music_needs_one_of_the_two_flags(tmp_path):
    with pytest.raises(SystemExit) as e:
        flow_music.main([_fm_prompts(tmp_path, 1), "--out", str(tmp_path / "out")])
    assert e.value.code == 2


def test_flow_music_dry_run_fires_nothing_and_is_not_capped(monkeypatch, tmp_path, capsys):
    rc, b = _fm_main(monkeypatch, tmp_path, 5, 2, "--max-credits", "0", "--dry-run")
    assert rc == 0 and b.clicks == 0
    assert "spend cap reached" not in capsys.readouterr().out


# ── the cap flag on the command line itself refuses a number that would never trip ─────────

@pytest.mark.parametrize("bad", ["nan", "inf"])
def test_cap_flag_given_on_the_command_line_refuses_nan_and_inf(bad, tmp_path):
    runs = (
        lambda: topview_wan3.main(["a.wan3.json", "--out", "o", "--max-credits", bad]),
        lambda: flow_music.main([_fm_prompts(tmp_path, 1), "--out", "o", "--max-credits", bad]),
        lambda: flow_shoot.main(["run", "--sheet", "s", "--ledger", "l", "--dest", "d", "--max-credits", bad]),
    )
    for run in runs:
        with pytest.raises(SystemExit) as e:
            run()
        assert e.value.code == 2


# ── flow_shoot: --max-credits alone is enough; at least one of the two is required ─────────

def test_flow_shoot_run_parses_with_max_credits_alone():
    args = flow_shoot.build_parser().parse_args(
        ["run", "--sheet", "s", "--ledger", "l", "--dest", "d", "--max-credits", "100"])
    assert args.credit_cap is None and args.max_credits == 100.0


def test_flow_shoot_run_with_neither_cap_is_an_argparse_error():
    with pytest.raises(SystemExit) as e:
        flow_shoot.main(["run", "--sheet", "s", "--ledger", "l", "--dest", "d"])
    assert e.value.code == 2


def test_flow_shoot_pull_and_status_need_no_cap():
    parser = flow_shoot.build_parser()
    parser.parse_args(["pull", "--sheet", "s", "--ledger", "l", "--dest", "d"])
    parser.parse_args(["status", "--ledger", "l"])


@pytest.mark.parametrize("credit_cap, max_credits, want", [
    (None, 100.0, 100.0),      # --max-credits alone doubles as the credit cap
    (300, 100.0, 300),         # --credit-cap given: it stays what it was
    (0, 100.0, 0),             # 0 is a real cap ("never spend"), not "unset"
    (300, None, 300),
    (None, None, None),
])
def test_flow_shoot_effective_credit_cap(credit_cap, max_credits, want):
    assert flow_shoot.effective_credit_cap(credit_cap, max_credits) == want


def test_flow_shoot_max_credits_alone_runs_and_stops_at_n(tmp_path, capsys):
    rc, stub = _flow_run(tmp_path, 40, "--max-credits", "100", credit_cap=None)
    assert rc == 3 and stub.submits == 2
    assert printed_line(capsys.readouterr().out, "spend cap reached: spent 80 of 100 credits")


def test_flow_shoot_credit_cap_zero_is_not_replaced_by_max_credits(tmp_path, capsys):
    rc, stub = _flow_run(tmp_path, 40, "--max-credits", "100", credit_cap="0")
    assert stub.submits == 0                       # the legacy "never spend" cap still blocks the Submit
    assert "spend cap reached" not in capsys.readouterr().out


def test_flow_shoot_cmd_run_with_neither_cap_refuses_before_it_attaches(tmp_path):
    args = flow_shoot.build_parser().parse_args(
        ["run", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / "l.tsv"),
         "--dest", str(tmp_path / "dest"), "--credit-cap", "5", "--only", "35"])
    args.credit_cap = None                         # a caller that skipped main()'s argparse check

    def no_browser():
        raise AssertionError("a browser was built although no cap was given")

    assert flow_shoot.cmd_run(args, browser_factory=no_browser) == 2


# ── the hub's own validator accepts the command each of these tools will carry ─────────────

def test_hub_cap_flag_check_accepts_the_command_a_spend_labelled_card_carries():
    assert ask_run.cap_flag_check(
        "python3 tools/flow_music.py prompts.json --out out --max-credits 20", "credits", 20.0) is None
    assert ask_run.cap_flag_check(
        "python3 tools/flow_shoot.py run --sheet s.md --ledger l.tsv --dest d --max-credits 100",
        "credits", 100.0) is None
    assert ask_run.cap_flag_check(
        "python3 tools/topview_wan3.py a.wan3.json b.wan3.json --out out --max-credits 3",
        "credits", 3.0) is None


def test_hub_refuses_the_per_track_spelling_which_is_why_it_is_optional_next_to_max_credits():
    for cmd in ("python3 tools/flow_music.py prompts.json --out out --max-credits-per-track 20",
                "python3 tools/flow_music.py prompts.json --out out --max-credits 20 --max-credits-per-track 20"):
        assert ask_run.cap_flag_check(cmd, "credits", 20.0) == "spend_cap_flag_ambiguous"
