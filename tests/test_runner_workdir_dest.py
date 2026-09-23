"""Tests for task-2b587031: WORK_DIR-pilot --dest defaulting, forbidden-path
refusal and free-space guard in tools/flow_shoot.py and
scripts/higgsfield/gen_loop.py — IRON §55 / Work/RULES.md rules 2 and 9.

No network, no browser: every test monkeypatches $WORK_DIR (and, where the
forbidden-path check is exercised, Path.home()) and injects a free-space
function rather than touching the real disk. Every "unchanged when WORK_DIR
is unset" test asserts a behaviour that WOULD flip if the `if not wd:
return`/`if not work_dir_set` guard were ever removed from the source — see
each test's docstring for exactly what breaks.

Run via:  pytest tests/test_runner_workdir_dest.py
(not in pytest.ini's default `testpaths` — run explicitly, same convention
as tests/test_flow_shoot.py.)
"""
from __future__ import annotations

import types
from pathlib import Path

import pytest

from tools import flow_ledger, flow_shoot
from scripts.higgsfield import gen_loop


@pytest.fixture(autouse=True)
def _clean_work_dir_env(monkeypatch):
    # Never let a real ambient $WORK_DIR (e.g. this task's own pilot export)
    # leak into a test that expects it unset.
    monkeypatch.delenv("WORK_DIR", raising=False)


# ── tools/flow_shoot.py: resolve_dest ───────────────────────────────────────

def test_resolve_dest_defaults_to_work_dir_out_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    assert flow_shoot.resolve_dest(None) == tmp_path / "out"


def test_resolve_dest_explicit_value_still_wins_over_default(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    custom = tmp_path / "custom-dest"
    assert flow_shoot.resolve_dest(str(custom)) == custom


def test_resolve_dest_raises_when_omitted_and_work_dir_unset():
    # WORK_DIR unset (autouse fixture above) + no --dest value: this is the
    # exact case build_parser's own required=True already refuses at the
    # CLI layer (see the next test) — resolve_dest backstops it the same way
    # if ever called directly.
    with pytest.raises(RuntimeError):
        flow_shoot.resolve_dest(None)


def test_resolve_dest_desktop_allowed_when_work_dir_unset(tmp_path):
    # Today's behaviour, byte-for-byte: no forbidden-path check runs at all
    # when WORK_DIR is unset — other sessions mid-shoot with
    # --dest ~/Desktop/... must not be touched by this task.
    # TEETH: if `if wd:` were removed from resolve_dest (i.e. the forbidden
    # check ran unconditionally), this raises DestForbidden and fails.
    desktop_dest = str(tmp_path / "Desktop" / "banchi-ACT2")
    assert flow_shoot.resolve_dest(desktop_dest) == Path(desktop_dest).expanduser()


def test_resolve_dest_refuses_desktop_dest_when_work_dir_set(monkeypatch, tmp_path):
    monkeypatch.setattr(flow_shoot.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "work"))
    desktop_dest = str(tmp_path / "Desktop" / "banchi-ACT2")
    with pytest.raises(flow_shoot.DestForbidden, match="IRON §55 rule 2"):
        flow_shoot.resolve_dest(desktop_dest)


def test_resolve_dest_refuses_downloads_and_movies_too(monkeypatch, tmp_path):
    monkeypatch.setattr(flow_shoot.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "work"))
    for sub in ("Downloads", "Movies"):
        with pytest.raises(flow_shoot.DestForbidden):
            flow_shoot.resolve_dest(str(tmp_path / sub / "clips"))


def test_resolve_dest_allows_a_non_forbidden_dest_when_work_dir_set(monkeypatch, tmp_path):
    monkeypatch.setattr(flow_shoot.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "work"))
    ok_dest = tmp_path / "work" / "out"
    assert flow_shoot.resolve_dest(str(ok_dest)) == ok_dest


# ── tools/flow_shoot.py: build_parser's --dest required=... ────────────────

def test_build_parser_dest_required_when_work_dir_unset():
    # Byte-for-byte the "required" argparse error runners had before this
    # task. TEETH: if build_parser stopped reading $WORK_DIR (dest_required
    # hardcoded True or the env check removed), this test still passes —
    # but the paired test right below it would then fail because --dest
    # would ALSO be required with WORK_DIR set, proving the check is real.
    ap = flow_shoot.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args(["run", "--sheet", "s.md", "--ledger", "l.tsv", "--credit-cap", "10"])
    with pytest.raises(SystemExit):
        ap.parse_args(["pull", "--sheet", "s.md", "--ledger", "l.tsv"])


def test_build_parser_dest_optional_when_work_dir_set(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    ap = flow_shoot.build_parser()
    args = ap.parse_args(["run", "--sheet", "s.md", "--ledger", "l.tsv", "--credit-cap", "10"])
    assert args.dest is None
    args = ap.parse_args(["pull", "--sheet", "s.md", "--ledger", "l.tsv"])
    assert args.dest is None


# ── tools/flow_shoot.py: check_free_space ───────────────────────────────────

def test_flow_shoot_free_space_noop_when_work_dir_unset():
    # TEETH: free_bytes_fn reports 0 bytes free — if the `if not wd: return`
    # guard were removed, this would raise InsufficientFreeSpace and fail.
    flow_shoot.check_free_space(free_bytes_fn=lambda: 0)


def test_flow_shoot_free_space_refuses_below_keep_free_floor_unknown_size(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    # config/storage-policy.yaml work_dir.keep_free_gb == 10
    with pytest.raises(flow_shoot.InsufficientFreeSpace, match="Work/RULES.md rule 9"):
        flow_shoot.check_free_space(free_bytes_fn=lambda: 5 * 1024 ** 3)


def test_flow_shoot_free_space_ok_above_keep_free_floor_unknown_size(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    flow_shoot.check_free_space(free_bytes_fn=lambda: 100 * 1024 ** 3)


def test_flow_shoot_free_space_refuses_big_download_that_would_cross_floor(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    # expected 2 GB (> big_download_gb=1), 11 GB free -> 11-2=9 < keep_free_gb=10
    with pytest.raises(flow_shoot.InsufficientFreeSpace):
        flow_shoot.check_free_space(
            expected_bytes=2 * 1024 ** 3, free_bytes_fn=lambda: 11 * 1024 ** 3)


def test_flow_shoot_free_space_allows_big_download_with_enough_headroom(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    flow_shoot.check_free_space(
        expected_bytes=2 * 1024 ** 3, free_bytes_fn=lambda: 20 * 1024 ** 3)


def test_flow_shoot_free_space_small_known_download_skips_the_floor_check(monkeypatch, tmp_path):
    # Spec: the size-known branch only refuses when the known size is ITSELF
    # bigger than big_download_gb (1 GB). A known-small download (500 MB)
    # never enters either branch, even with almost no free space — this is
    # the literal rule 9 wording ("before a download > 1 GB").
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    flow_shoot.check_free_space(
        expected_bytes=int(0.5 * 1024 ** 3), free_bytes_fn=lambda: 1)


# ── cmd_run / cmd_pull wiring: a forbidden --dest is refused before any
#    browser attach, and never partially runs ──────────────────────────────

FIXTURE_SHEET = Path(__file__).resolve().parent.parent / "docs" / "scripts" / "banchi-ACT2.md"


@pytest.fixture(autouse=True)
def _redirect_flow_shoot_log(tmp_path, monkeypatch):
    monkeypatch.setattr(flow_shoot, "LOG_PATH", tmp_path / "flow_shoot.log")


def test_cmd_run_refuses_forbidden_dest_before_touching_the_browser(monkeypatch, tmp_path):
    monkeypatch.setattr(flow_shoot.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "work"))
    ap = flow_shoot.build_parser()
    args = ap.parse_args([
        "run", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / "l.tsv"),
        "--dest", str(tmp_path / "Desktop" / "banchi"), "--credit-cap", "10",
    ])

    def _boom():
        raise AssertionError("browser_factory must never be called — refused before attach")

    rc = flow_shoot.cmd_run(args, browser_factory=_boom)
    assert rc == 1


def test_cmd_pull_refuses_forbidden_dest_before_touching_the_browser(monkeypatch, tmp_path):
    monkeypatch.setattr(flow_shoot.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "work"))
    ap = flow_shoot.build_parser()
    args = ap.parse_args([
        "pull", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / "l.tsv"),
        "--dest", str(tmp_path / "Downloads" / "banchi"),
    ])
    rc = flow_shoot.cmd_pull(args)
    assert rc == 1


# ── cmd_run money-guard ordering (task-2b587031 iteration 1, CTO review):
#    the free-space check must gate browser.submit() (the paid generation),
#    not merely browser.download() — a disk-space refusal that only fires
#    after submit() has already spent credits on a generation nobody can
#    save is exactly the "money defect" this iteration exists to fix. This
#    mirrors tests/test_flow_shoot.py's own money-guard stubs (e.g.
#    _GateStubBrowser), including its reset_composer() no-op — cmd_run now
#    calls it at every shot boundary. ──────────────────────────────────────

class _SpaceGateStubBrowser:
    """poll_result()/download() both raise AssertionError unless
    allow_generation=True: the negative control (low disk) must never
    reach either — proving the refusal happens strictly before submit(),
    not merely before download(). The positive control (plenty of disk)
    sets allow_generation=True and gets a scripted refusal card, so
    download() still isn't exercised — same shape as test_flow_shoot.py's
    own test_chip_count_match_reaches_submit."""

    def __init__(self, allow_generation: bool = False):
        self._allow_generation = allow_generation
        self._chip_count = 0  # rises by one per attach_chip() call, like the real gate expects
        self.dry_run = False
        self.submit_called = False
        self.download_called = False
        self._pasted = ""

    def attach(self) -> None:
        pass

    def mute_all_media(self) -> None:
        pass

    def reset_composer(self) -> None:
        pass

    def close(self) -> None:
        pass

    def set_settings(self, dur_s, resolution="720p") -> dict:
        return {"model_omni": True, "mode_ingredients": True, "aspect_9_16": True,
                "qty_x1": True, "resolution": True, "duration": True}

    def chip_count(self) -> int:
        return self._chip_count

    def attach_chip(self, _handle: str) -> bool:
        self._chip_count += 1
        return True

    def paste_prompt(self, text: str) -> None:
        self._pasted = text

    def read_prompt_text(self) -> str:
        return self._pasted

    def read_credit_estimate(self) -> int:
        return 4

    def submit(self, expected_chip_count: int | None = None) -> None:
        self.submit_called = True

    def poll_result(self, timeout_s: int = 0) -> dict:
        if not self._allow_generation:
            raise AssertionError(
                "poll_result() must never be reached — the space refusal must "
                "happen before submit(), which is before this is ever called")
        return {"status": "refusal", "text": "ล้มเหลว (stub, positive-control test)"}

    def download(self):
        self.download_called = True
        raise AssertionError("download() must never be reached by either control")


def _space_run_args(tmp_path: Path, ledger_name: str) -> object:
    ap = flow_shoot.build_parser()
    return ap.parse_args([
        "run", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / ledger_name),
        "--credit-cap", "999", "--only", "35",
    ])  # --dest omitted: $WORK_DIR is set in every test below, so it defaults to $WORK_DIR/out


def test_cmd_run_low_disk_blocks_submit_before_any_credit_spend(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    # 1 GB free < config/storage-policy.yaml work_dir.keep_free_gb (10)
    monkeypatch.setattr(flow_shoot.shutil, "disk_usage",
                         lambda path: types.SimpleNamespace(free=1 * 1024 ** 3))
    args = _space_run_args(tmp_path, "space.tsv")
    stub = _SpaceGateStubBrowser()
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is False
    assert stub.download_called is False
    rows = flow_ledger.load_ledger(tmp_path / "space.tsv")
    assert rows[35]["status"] == "failed"
    assert "space" in rows[35]["note"]
    assert rc == 1


def test_cmd_run_plenty_of_disk_still_reaches_submit(monkeypatch, tmp_path):
    # Positive control: the new gate must not false-block a healthy run —
    # with ample free space, submit() is reached exactly as before.
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    monkeypatch.setattr(flow_shoot.shutil, "disk_usage",
                         lambda path: types.SimpleNamespace(free=100 * 1024 ** 3))
    args = _space_run_args(tmp_path, "space_ok.tsv")
    stub = _SpaceGateStubBrowser(allow_generation=True)
    flow_shoot.cmd_run(args, browser_factory=lambda: stub)

    assert stub.submit_called is True
    assert stub.download_called is False  # stub's poll_result() always refuses


def test_cmd_run_free_space_check_is_noop_when_work_dir_unset(tmp_path):
    # WORK_DIR unset (autouse fixture) — byte-for-byte unchanged: reaches
    # submit() regardless of disk state, since check_free_space() no-ops.
    ap = flow_shoot.build_parser()
    args = ap.parse_args([
        "run", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / "no_workdir.tsv"),
        "--dest", str(tmp_path / "dest"), "--credit-cap", "999", "--only", "35",
    ])
    stub = _SpaceGateStubBrowser(allow_generation=True)
    flow_shoot.cmd_run(args, browser_factory=lambda: stub)
    assert stub.submit_called is True


# ── scripts/higgsfield/gen_loop.py: resolve_local_root ──────────────────────

def test_gen_loop_local_root_unchanged_when_work_dir_unset():
    # TEETH: if the `if not wd: return LOCAL_ROOT` guard were removed,
    # this would instead try to build a path off an unset $WORK_DIR and
    # fail differently (or silently diverge from LOCAL_ROOT).
    assert gen_loop.resolve_local_root() == gen_loop.LOCAL_ROOT


def test_gen_loop_local_root_defaults_to_work_dir_out_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    assert gen_loop.resolve_local_root() == tmp_path / "out"


def test_gen_loop_local_root_refuses_a_desktop_work_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(gen_loop.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "Desktop" / "gen-out"))
    with pytest.raises(gen_loop.DestForbidden, match="IRON §55 rule 2"):
        gen_loop.resolve_local_root()


# ── scripts/higgsfield/gen_loop.py: check_free_space ────────────────────────

def test_gen_loop_free_space_noop_when_work_dir_unset():
    gen_loop.check_free_space(free_bytes_fn=lambda: 0)


def test_gen_loop_free_space_refuses_below_keep_free_floor(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    with pytest.raises(gen_loop.InsufficientFreeSpace, match="Work/RULES.md rule 9"):
        gen_loop.check_free_space(free_bytes_fn=lambda: 5 * 1024 ** 3)


def test_gen_loop_free_space_ok_above_keep_free_floor(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    gen_loop.check_free_space(free_bytes_fn=lambda: 100 * 1024 ** 3)
