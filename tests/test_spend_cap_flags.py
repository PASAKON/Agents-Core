"""Spend-cap contract for the tools that sit behind a spend-labelled Run card (task-407a64ce).

The rule (Console docs/run.md §Spend label): a command on a spend-labelled card carries
`--max-usd N` or `--max-credits N`; the tool stops before any call that would take its running
total past N, prints `spend cap reached: spent X of N <unit>` and exits 3; every ArgumentParser in
the file sets allow_abbrev=False, or `--max 100` is silently expanded to the cap flag.

Two halves:
  A. all 8 files: an abbreviation of a real flag is rejected. Each case first proves the
     abbreviation WOULD parse with abbreviations switched back on, so it cannot pass vacuously.
  B. the 4 tools that click a paid button (flow_shoot, gen_loop, credit_fire, champa_fire): with
     --max-credits N the tool makes no call that would pass N, nothing after it, and exits 3;
     without the flag nothing changes. bl_realfootage and ilag_round make no paid call, so they
     are in half A only.

HARD: no network and no spend. Every provider key is stripped from the environment, sockets and
urlopen refuse, and the paid click is a stub in every test. Nothing here runs a tool for real.
"""
from __future__ import annotations

import argparse
import importlib
import os
import socket
import sys
import types
import urllib.request
from pathlib import Path

import pytest

from scripts.champa import champa_fire
from scripts.higgsfield import credit_fire, gen_loop
from tools import bl_realfootage, flow_ledger, flow_music, flow_shoot, topview_wan3

REPO = Path(__file__).resolve().parent.parent
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
    base = ["p.json", "--out", "o"]
    assert_abbrev_rejected(parser, base + ["--max-credits-per-track", "5"], base + ["--max", "5"])


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
    for fn in (flow_shoot.spend_cap_arg, gen_loop.spend_cap_arg,
               credit_fire.spend_cap_arg, champa_fire.spend_cap_arg):
        with pytest.raises((argparse.ArgumentTypeError, ValueError)):
            fn(bad)


@pytest.mark.parametrize("good, value", [("0", 0.0), ("5", 5.0), ("2.5", 2.5)])
def test_plain_cap_numbers_are_accepted(good, value):
    for fn in (flow_shoot.spend_cap_arg, gen_loop.spend_cap_arg,
               credit_fire.spend_cap_arg, champa_fire.spend_cap_arg):
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
    args = flow_shoot.build_parser().parse_args([
        "run", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / "l.tsv"),
        "--dest", str(tmp_path / "dest"), "--credit-cap", credit_cap, "--only", "35-37", *flags])
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
