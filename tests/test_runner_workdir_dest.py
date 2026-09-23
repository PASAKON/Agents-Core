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
import yaml

from tools import flow_ledger, flow_shoot
from scripts.higgsfield import gen_loop


@pytest.fixture(autouse=True)
def _clean_work_dir_env(monkeypatch):
    # Never let a real ambient $WORK_DIR (e.g. this task's own pilot export)
    # leak into a test that expects it unset.
    monkeypatch.delenv("WORK_DIR", raising=False)


def _write_policy(tmp_path: Path, *, scope_space_check, space_check_overrides=None) -> Path:
    """A minimal storage_policy.load()-valid policy yaml with a custom
    scope.space_check / space_check block (task-9586db0c) — for tests that
    need a scope or estimate value the real config/storage-policy.yaml
    (scope.space_check: all, default_estimate_gb: 1, min_free_after_gb: 5)
    can't give them without editing that file, which this task leaves alone
    (CTO note: C7 owns config/storage-policy.yaml this task)."""
    space_check = {"min_free_after_gb": 5, "default_estimate_gb": 1, "estimates_gb": {}}
    if space_check_overrides:
        space_check.update(space_check_overrides)
    policy = {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {"HOT": [], "REBUILD": [], "COLD": [], "NEVER": []},
        "scope": {"space_check": scope_space_check},
        "space_check": space_check,
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(policy))
    return path


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


# ── tools/flow_shoot.py: check_free_space (task-9586db0c, CEO 2026-09-23) ──
# Not a fixed floor: refuse iff free_gb - expected_gb < min_free_after_gb.
# Whether the check runs at all is scope.space_check ("all" = always, a list
# = $WORKER_CTO_ID membership, off = complete no-op) — no longer gated by
# $WORK_DIR. The real config/storage-policy.yaml ships scope.space_check:
# all, min_free_after_gb: 5, default_estimate_gb: 1 — used directly below
# where those exact numbers matter; a private tmp policy (_write_policy)
# wherever a specific scope or estimate value must be pinned instead.

def test_flow_shoot_free_space_off_scope_is_a_complete_noop(tmp_path):
    # TEETH: 0 bytes free, no estimate given — if _space_check_scope_applies
    # were removed (or defaulted True), this raises and fails.
    policy_path = _write_policy(tmp_path, scope_space_check=[])
    flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 0)


def test_flow_shoot_free_space_list_scope_is_worker_cto_id_membership(monkeypatch, tmp_path):
    policy_path = _write_policy(tmp_path, scope_space_check=["cto-a"])
    monkeypatch.delenv("WORKER_CTO_ID", raising=False)
    flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 0)  # not a member
    monkeypatch.setenv("WORKER_CTO_ID", "cto-a")
    with pytest.raises(flow_shoot.InsufficientFreeSpace):
        flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 0)


def test_flow_shoot_free_space_all_scope_applies_regardless_of_worker_cto_id(monkeypatch, tmp_path):
    # "all" means always (task spec point 2) — no $WORKER_CTO_ID needed.
    policy_path = _write_policy(tmp_path, scope_space_check="all")
    monkeypatch.delenv("WORKER_CTO_ID", raising=False)
    with pytest.raises(flow_shoot.InsufficientFreeSpace):
        flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 0)


def test_flow_shoot_free_space_exactly_at_threshold_passes(tmp_path):
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"min_free_after_gb": 5,
                                                         "default_estimate_gb": 2})
    # 7 GB free - 2 GB estimate = 5 GB left == min_free_after_gb -> passes.
    flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 7 * 1024 ** 3)


def test_flow_shoot_free_space_just_below_threshold_refuses(tmp_path):
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"min_free_after_gb": 5,
                                                         "default_estimate_gb": 2})
    with pytest.raises(flow_shoot.InsufficientFreeSpace):
        flow_shoot.check_free_space(policy_path=policy_path,
                                     free_bytes_fn=lambda: 7 * 1024 ** 3 - 1)


def test_flow_shoot_free_space_expect_gb_param_wins_over_env_and_project(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_EXPECT_GB", "0.1")
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"estimates_gb": {"proj": 0.1}})
    # explicit expect_gb=10 on 10 GB free -> 0 left < 5 -> refuses, proving
    # it (not the tiny env/project values) was used.
    with pytest.raises(flow_shoot.InsufficientFreeSpace):
        flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 10 * 1024 ** 3,
                                     expect_gb=10.0, project="proj")


def test_flow_shoot_free_space_env_expect_gb_wins_when_no_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_EXPECT_GB", "10")
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"estimates_gb": {"proj": 0.1}})
    with pytest.raises(flow_shoot.InsufficientFreeSpace):
        flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 10 * 1024 ** 3,
                                     project="proj")


def test_flow_shoot_free_space_project_estimate_wins_when_no_flag_or_env(monkeypatch, tmp_path):
    monkeypatch.delenv("WORK_EXPECT_GB", raising=False)
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"estimates_gb": {"proj": 10},
                                                         "default_estimate_gb": 0.1})
    # default (0.1) would pass; the project estimate (10) must win instead.
    with pytest.raises(flow_shoot.InsufficientFreeSpace):
        flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 10 * 1024 ** 3,
                                     project="proj")


def test_flow_shoot_free_space_project_via_env_work_project(monkeypatch, tmp_path):
    monkeypatch.delenv("WORK_EXPECT_GB", raising=False)
    monkeypatch.setenv("WORK_PROJECT", "proj")
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"estimates_gb": {"proj": 10},
                                                         "default_estimate_gb": 0.1})
    with pytest.raises(flow_shoot.InsufficientFreeSpace):
        flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 10 * 1024 ** 3)


def test_flow_shoot_free_space_default_estimate_logs_one_line(monkeypatch, tmp_path):
    monkeypatch.delenv("WORK_EXPECT_GB", raising=False)
    monkeypatch.delenv("WORK_PROJECT", raising=False)
    monkeypatch.setattr(flow_shoot, "LOG_PATH", tmp_path / "flow_shoot.log")
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"default_estimate_gb": 3})
    flow_shoot.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 100 * 1024 ** 3)
    log_text = flow_shoot.LOG_PATH.read_text()
    assert "no size estimate given" in log_text
    assert "assumed 3 GB" in log_text


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
    # real config: default_estimate_gb 1, min_free_after_gb 5 -> 1 GB free
    # leaves 0 GB, well under the floor.
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


def test_cmd_run_reaches_submit_regardless_of_work_dir_when_disk_is_fine(monkeypatch, tmp_path):
    # WORK_DIR unset (autouse fixture) — real config scope.space_check: all
    # (task-9586db0c) means the check now runs regardless of $WORK_DIR;
    # with ample free space it still doesn't block submit().
    monkeypatch.setattr(flow_shoot.shutil, "disk_usage",
                         lambda path: types.SimpleNamespace(free=100 * 1024 ** 3))
    ap = flow_shoot.build_parser()
    args = ap.parse_args([
        "run", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / "no_workdir.tsv"),
        "--dest", str(tmp_path / "dest"), "--credit-cap", "999", "--only", "35",
    ])
    stub = _SpaceGateStubBrowser(allow_generation=True)
    flow_shoot.cmd_run(args, browser_factory=lambda: stub)
    assert stub.submit_called is True


def test_cmd_run_low_disk_blocks_submit_even_without_work_dir(monkeypatch, tmp_path):
    # TEETH: proves scope.space_check "all" really means always (task spec
    # point 2), not "only when $WORK_DIR is set" — same low-disk refusal as
    # test_cmd_run_low_disk_blocks_submit_before_any_credit_spend above, but
    # with $WORK_DIR left unset. If check_free_space() were still gated on
    # `if not _work_dir(): return`, this reaches submit() and fails.
    monkeypatch.setattr(flow_shoot.shutil, "disk_usage",
                         lambda path: types.SimpleNamespace(free=1 * 1024 ** 3))
    ap = flow_shoot.build_parser()
    args = ap.parse_args([
        "run", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / "space_no_wd.tsv"),
        "--dest", str(tmp_path / "dest"), "--credit-cap", "999", "--only", "35",
    ])
    stub = _SpaceGateStubBrowser()
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)
    assert stub.submit_called is False
    assert stub.download_called is False
    rows = flow_ledger.load_ledger(tmp_path / "space_no_wd.tsv")
    assert rows[35]["status"] == "failed"
    assert "space" in rows[35]["note"]
    assert rc == 1


def test_cmd_run_expect_gb_flag_reaches_check_free_space(monkeypatch, tmp_path):
    # --expect-gb threads cmd_run -> _submit_or_raise -> check_free_space:
    # 10 GB free - 8 GB explicit estimate = 2 GB left < 5 -> refuses, proving
    # the CLI flag (not the real config's default_estimate_gb: 1) was used.
    monkeypatch.setenv("WORK_DIR", str(tmp_path))
    monkeypatch.setattr(flow_shoot.shutil, "disk_usage",
                         lambda path: types.SimpleNamespace(free=10 * 1024 ** 3))
    ap = flow_shoot.build_parser()
    args = ap.parse_args([
        "run", "--sheet", str(FIXTURE_SHEET), "--ledger", str(tmp_path / "expectgb.tsv"),
        "--credit-cap", "999", "--only", "35", "--expect-gb", "8",
    ])
    stub = _SpaceGateStubBrowser()
    rc = flow_shoot.cmd_run(args, browser_factory=lambda: stub)
    assert stub.submit_called is False
    assert rc == 1


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


# ── scripts/higgsfield/gen_loop.py: check_free_space (task-9586db0c) ───────
# Same replacement, same estimate order and scope rules — duplicated in
# gen_loop.py rather than imported (see that file's own comment); tested
# independently here to catch a copy-paste divergence between the two.

def test_gen_loop_free_space_off_scope_is_a_complete_noop(tmp_path):
    policy_path = _write_policy(tmp_path, scope_space_check=[])
    gen_loop.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 0)


def test_gen_loop_free_space_all_scope_refuses_below_threshold(tmp_path):
    policy_path = _write_policy(tmp_path, scope_space_check="all")
    with pytest.raises(gen_loop.InsufficientFreeSpace, match="space_check"):
        gen_loop.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 0)


def test_gen_loop_free_space_ok_above_threshold(tmp_path):
    policy_path = _write_policy(tmp_path, scope_space_check="all")
    gen_loop.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 100 * 1024 ** 3)


def test_gen_loop_free_space_exactly_at_threshold_passes(tmp_path):
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"min_free_after_gb": 5,
                                                         "default_estimate_gb": 2})
    gen_loop.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 7 * 1024 ** 3)


def test_gen_loop_free_space_just_below_threshold_refuses(tmp_path):
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"min_free_after_gb": 5,
                                                         "default_estimate_gb": 2})
    with pytest.raises(gen_loop.InsufficientFreeSpace):
        gen_loop.check_free_space(policy_path=policy_path,
                                   free_bytes_fn=lambda: 7 * 1024 ** 3 - 1)


def test_gen_loop_free_space_expect_gb_param_wins_over_env_and_project(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_EXPECT_GB", "0.1")
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"estimates_gb": {"proj": 0.1}})
    with pytest.raises(gen_loop.InsufficientFreeSpace):
        gen_loop.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 10 * 1024 ** 3,
                                   expect_gb=10.0, project="proj")


def test_gen_loop_free_space_env_expect_gb_wins_when_no_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("WORK_EXPECT_GB", "10")
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"estimates_gb": {"proj": 0.1}})
    with pytest.raises(gen_loop.InsufficientFreeSpace):
        gen_loop.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 10 * 1024 ** 3,
                                   project="proj")


def test_gen_loop_free_space_project_estimate_wins_when_no_flag_or_env(monkeypatch, tmp_path):
    monkeypatch.delenv("WORK_EXPECT_GB", raising=False)
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"estimates_gb": {"proj": 10},
                                                         "default_estimate_gb": 0.1})
    with pytest.raises(gen_loop.InsufficientFreeSpace):
        gen_loop.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 10 * 1024 ** 3,
                                   project="proj")


def test_gen_loop_free_space_default_estimate_logs_one_line(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("WORK_EXPECT_GB", raising=False)
    monkeypatch.delenv("WORK_PROJECT", raising=False)
    policy_path = _write_policy(tmp_path, scope_space_check="all",
                                 space_check_overrides={"default_estimate_gb": 3})
    gen_loop.check_free_space(policy_path=policy_path, free_bytes_fn=lambda: 100 * 1024 ** 3)
    out = capsys.readouterr().out
    assert "no size estimate given" in out
    assert "assumed 3 GB" in out
