"""tests/test_machine_doctor.py — registry vs disk (tools/machine_doctor.py,
ADR 0031, IRON §58, docs/ops/briefs/machine-contract-phase1.md).

Every test builds its own tiny registry dict and points snapshot/check/report
at tmp_path via the `registry=`/`home=`/`claude_config_dir=`/`opt_dir=`/
`docker_volumes_dir=`/`state_dir=` keyword overrides — never the real
config/machine-contract.yaml, and never the real disk.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.machine_doctor as md  # noqa: E402

MACHINE = "testbox"


def _registry(entries: list[dict], **machine_overrides) -> dict:
    m = {"os": "linux", "home": "/unused", "claude_config_dir": "/unused/.claude",
         "hq": "/unused/hq", "scheduler": "cron", "capture": "x", "restore": "x", "run_by": "t"}
    m.update(machine_overrides)
    return {
        "version": 0,
        "unknown_growth": {"min_mb": 500, "classify_within_days": 14, "report": "weekly"},
        "machines": {MACHINE: m},
        "entries": entries,
    }


def _row(path: str, cls: str, **kw) -> dict:
    row = {"machine": MACHINE, "path": path, "class": cls, "owner": "t",
           "review": "2026-12-23", "discovered": False, "restore": "reinstall"}
    row.update(kw)
    return row


def _make_sparse(path: Path, size_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.truncate(size_bytes)


# --------------------------------------------------------------- load/detect

def test_load_registry_reads_yaml(tmp_path):
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(_registry([])), encoding="utf-8")
    reg = md.load_registry(p)
    assert reg["machines"][MACHINE]["os"] == "linux"


def test_detect_machine_by_hostname_substring():
    reg = {"machines": {"myhost": {"os": "made-up-os"}}}
    assert md.detect_machine(reg, hostname="myhost-01.local") == "myhost"


def test_detect_machine_by_unique_os_when_hostname_does_not_match():
    reg = {"machines": {"linuxbox": {"os": "linux"}, "macbox": {"os": "macos"}}}
    # This suite runs on Linux (Contabo, per the brief) — os-fallback picks it.
    assert md.detect_machine(reg, hostname="unrelated-name") == "linuxbox"


def test_detect_machine_raises_when_ambiguous():
    reg = {"machines": {"linuxbox1": {"os": "linux"}, "linuxbox2": {"os": "linux"}}}
    with pytest.raises(SystemExit):
        md.detect_machine(reg, hostname="totally-unrelated-hostname")


# ------------------------------------------------------------- placeholders

def test_substitute_all_three_named_placeholders():
    ctx = {"HOME": "/h", "CLAUDE_CONFIG_DIR": "/h/.claude", "hq": "/hq", "_os": "linux"}
    assert md._substitute("$CLAUDE_CONFIG_DIR/x $HOME/y <hq>/z", ctx) == "/h/.claude/x /h/y /hq/z"


def test_substitute_angle_placeholder_becomes_wildcard():
    ctx = {"HOME": "/h", "CLAUDE_CONFIG_DIR": "/h/.claude", "hq": "/hq", "_os": "linux"}
    assert md._substitute("<hq>/Work/<task-id>/**", ctx) == "/hq/Work/*/**"


def test_substitute_windows_placeholder_skipped_on_non_windows():
    ctx = {"HOME": "/h", "CLAUDE_CONFIG_DIR": "/h/.claude", "hq": "/hq", "_os": "linux"}
    assert md._substitute("%USERPROFILE%/Documents/x", ctx) is None


def test_substitute_windows_placeholder_kept_on_windows():
    ctx = {"HOME": "/h", "CLAUDE_CONFIG_DIR": "/h/.claude", "hq": "/hq", "_os": "windows"}
    assert md._substitute("%USERPROFILE%/Documents/x", ctx) == "%USERPROFILE%/Documents/x"


def test_expand_braces_mid_path():
    assert md._expand_braces("/a/{x,y}/b") == ["/a/x/b", "/a/y/b"]


def test_expand_braces_whole_string_group():
    assert md._expand_braces("{/a,/b,/c}") == ["/a", "/b", "/c"]


def test_expand_braces_noop_without_group():
    assert md._expand_braces("/plain/path") == ["/plain/path"]


# ------------------------------------------------------------------ resolve

def test_resolve_rows_marks_windows_row_inapplicable_on_linux(tmp_path):
    reg = _registry([_row("%USERPROFILE%/x/**", "CONFIG")])
    ctx = md.build_context(reg, MACHINE, home=tmp_path, claude_config_dir=tmp_path / ".claude")
    rows = md.resolve_rows(reg, MACHINE, ctx)
    assert rows[0]["applicable"] is False
    assert rows[0]["exists"] is False


def test_resolve_rows_reports_exists_and_bytes(tmp_path):
    home = tmp_path / "home"
    (home / "keep").mkdir(parents=True)
    (home / "keep" / "a.bin").write_bytes(b"x" * 100)
    reg = _registry([_row("$HOME/keep/**", "REBUILD")])
    ctx = md.build_context(reg, MACHINE, home=home, claude_config_dir=home / ".claude")
    rows = md.resolve_rows(reg, MACHINE, ctx)
    assert rows[0]["exists"] is True
    assert rows[0]["bytes"] == 100


def test_resolve_rows_missing_path_does_not_exist(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    reg = _registry([_row("$HOME/nope/**", "REBUILD")])
    ctx = md.build_context(reg, MACHINE, home=home, claude_config_dir=home / ".claude")
    rows = md.resolve_rows(reg, MACHINE, ctx)
    assert rows[0]["exists"] is False
    assert rows[0]["bytes"] == 0


# ----------------------------------------------------------------- snapshot

def test_snapshot_writes_json_with_exists_and_bytes(tmp_path):
    home = tmp_path / "home"
    (home / "keep").mkdir(parents=True)
    (home / "keep" / "a.bin").write_bytes(b"x" * 250)
    reg = _registry([_row("$HOME/keep/**", "REBUILD"), _row("$HOME/absent/**", "DISPOSABLE")])
    state_dir = tmp_path / "state"

    data = md.snapshot(MACHINE, registry=reg, state_dir=state_dir, home=home,
                        claude_config_dir=home / ".claude")

    out_file = state_dir / f"machine-snapshot-{MACHINE}.json"
    assert out_file.exists()
    on_disk = json.loads(out_file.read_text())
    assert on_disk["machine"] == MACHINE
    by_path = {e["path"]: e for e in on_disk["entries"]}
    assert by_path["$HOME/keep/**"]["exists"] is True
    assert by_path["$HOME/keep/**"]["bytes"] == 250
    assert by_path["$HOME/absent/**"]["exists"] is False
    assert data == on_disk


# -------------------------------------------------------------------- check

def test_check_flags_irreplaceable_existing_with_no_restore(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / "secret.env").write_text("x")
    reg = _registry([_row("$HOME/secret.env", "IRREPLACEABLE", restore="")])
    result = md.check(MACHINE, registry=reg, state_dir=tmp_path / "state",
                       home=home, claude_config_dir=home / ".claude",
                       opt_dir=tmp_path / "no-opt", docker_volumes_dir=tmp_path / "no-docker")
    assert any(p["kind"] == "MISSING_RESTORE" for p in result["problems"])


def test_check_does_not_flag_missing_restore_when_path_absent(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    reg = _registry([_row("$HOME/secret.env", "IRREPLACEABLE", restore="")])
    result = md.check(MACHINE, registry=reg, state_dir=tmp_path / "state",
                       home=home, claude_config_dir=home / ".claude",
                       opt_dir=tmp_path / "no-opt", docker_volumes_dir=tmp_path / "no-docker")
    assert result["problems"] == []


def test_check_flags_unclassified_registry_row_regardless_of_existence(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    reg = _registry([_row("/root/restore/**", "UNCLASSIFIED", restore=None, owner=None,
                           review=None, discovered=True)])
    result = md.check(MACHINE, registry=reg, state_dir=tmp_path / "state",
                       home=home, claude_config_dir=home / ".claude",
                       opt_dir=tmp_path / "no-opt", docker_volumes_dir=tmp_path / "no-docker")
    assert any(p["kind"] == "UNCLASSIFIED" and p["path"] == "/root/restore/**"
               for p in result["problems"])


def test_check_discovers_oversized_uncovered_directory(tmp_path):
    home = tmp_path / "home"
    _make_sparse(home / "bigstuff" / "data.bin", 600 * 1024 * 1024)
    reg = _registry([])  # nothing covers home/bigstuff

    result = md.check(MACHINE, registry=reg, state_dir=tmp_path / "state",
                       home=home, claude_config_dir=home / ".claude",
                       opt_dir=tmp_path / "no-opt", docker_volumes_dir=tmp_path / "no-docker")

    discovered = [p for p in result["problems"] if p["kind"] == "DISCOVERED"]
    assert len(discovered) == 1
    assert discovered[0]["path"] == str(home / "bigstuff")

    log_path = tmp_path / "state" / f"machine-discovered-{MACHINE}.yaml"
    assert log_path.exists()
    logged = yaml.safe_load(log_path.read_text())["entries"]
    assert logged[0]["path"] == str(home / "bigstuff")
    assert logged[0]["class"] == "UNCLASSIFIED"
    assert logged[0]["discovered"] is True


def test_check_does_not_discover_a_path_the_registry_already_covers(tmp_path):
    home = tmp_path / "home"
    _make_sparse(home / "bigstuff" / "data.bin", 600 * 1024 * 1024)
    reg = _registry([_row("$HOME/bigstuff/**", "REBUILD")])  # covers it

    result = md.check(MACHINE, registry=reg, state_dir=tmp_path / "state",
                       home=home, claude_config_dir=home / ".claude",
                       opt_dir=tmp_path / "no-opt", docker_volumes_dir=tmp_path / "no-docker")

    assert [p for p in result["problems"] if p["kind"] in ("DISCOVERED", "CANDIDATE")] == []
    assert not (tmp_path / "state" / f"machine-discovered-{MACHINE}.yaml").exists()


def test_check_second_run_after_removal_reports_clean(tmp_path):
    home = tmp_path / "home"
    big_dir = home / "bigstuff"
    _make_sparse(big_dir / "data.bin", 600 * 1024 * 1024)
    reg = _registry([])
    kwargs = dict(registry=reg, state_dir=tmp_path / "state", home=home,
                  claude_config_dir=home / ".claude", opt_dir=tmp_path / "no-opt",
                  docker_volumes_dir=tmp_path / "no-docker")

    first = md.check(MACHINE, **kwargs)
    assert any(p["kind"] == "DISCOVERED" for p in first["problems"])

    shutil.rmtree(big_dir)

    second = md.check(MACHINE, **kwargs)
    assert second["problems"] == []  # gone -> not re-reported this run


def test_check_escalates_to_candidate_after_classify_within_days(tmp_path):
    home = tmp_path / "home"
    _make_sparse(home / "bigstuff" / "data.bin", 600 * 1024 * 1024)
    reg = _registry([])
    kwargs = dict(registry=reg, state_dir=tmp_path / "state", home=home,
                  claude_config_dir=home / ".claude", opt_dir=tmp_path / "no-opt",
                  docker_volumes_dir=tmp_path / "no-docker")

    day0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = md.check(MACHINE, now=day0, **kwargs)
    assert [p["kind"] for p in first["problems"]] == ["DISCOVERED"]

    later = day0 + timedelta(days=15)
    second = md.check(MACHINE, now=later, **kwargs)
    assert [p["kind"] for p in second["problems"]] == ["CANDIDATE"]
    assert second["problems"][0]["age_days"] == 15


def test_check_creates_state_dir_when_missing(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    state_dir = tmp_path / "nested" / "state"
    reg = _registry([])
    md.check(MACHINE, registry=reg, state_dir=state_dir, home=home,
             claude_config_dir=home / ".claude", opt_dir=tmp_path / "no-opt",
             docker_volumes_dir=tmp_path / "no-docker")
    assert state_dir.is_dir()


# -------------------------------------------------------------------- report

def test_report_sums_bytes_by_class(tmp_path):
    home = tmp_path / "home"
    (home / "a").mkdir(parents=True)
    (home / "a" / "f.bin").write_bytes(b"x" * 1024)
    (home / "b").mkdir(parents=True)
    (home / "b" / "g.bin").write_bytes(b"y" * 2048)
    reg = _registry([
        _row("$HOME/a/**", "REBUILD"),
        _row("$HOME/b/**", "CONFIG"),
        _row("$HOME/missing/**", "DISPOSABLE"),
    ])
    rows = md.report(MACHINE, registry=reg, home=home, claude_config_dir=home / ".claude")
    by_class = dict(rows)
    assert by_class["REBUILD"] == pytest.approx(1024 / 1024 ** 3)
    assert by_class["CONFIG"] == pytest.approx(2048 / 1024 ** 3)
    assert by_class["DISPOSABLE"] == 0


# ---------------------------------------------------------- version-change

def test_on_version_change_detects_bump_then_settles(tmp_path):
    home = tmp_path / "home"
    ccd = home / ".claude"
    ccd.mkdir(parents=True)
    (ccd / ".last-update-result.json").write_text(json.dumps({"version_to": "9.9.9"}))
    reg = _registry([])
    state_dir = tmp_path / "state"
    kwargs = dict(registry=reg, state_dir=state_dir, home=home, claude_config_dir=ccd)

    first = md.check_on_version_change(MACHINE, **kwargs)
    assert first["changed"] is True
    assert first["current_version"] == "9.9.9"
    assert (state_dir / f"machine-snapshot-{MACHINE}.json").exists()

    second = md.check_on_version_change(MACHINE, **kwargs)
    assert second["changed"] is False


def test_on_version_change_prints_marker_via_cli(tmp_path, capsys):
    home = tmp_path / "home"
    ccd = home / ".claude"
    ccd.mkdir(parents=True)
    (ccd / ".last-update-result.json").write_text(json.dumps({"version_to": "1.2.3"}))
    reg_path = tmp_path / "reg.yaml"
    reg_path.write_text(yaml.safe_dump(_registry([])), encoding="utf-8")
    state_dir = tmp_path / "state"

    rc = md._cli(["--machine", MACHINE, "--registry", str(reg_path), "--state-dir", str(state_dir),
                  "--home", str(home), "--claude-config-dir", str(ccd),
                  "--opt-dir", str(tmp_path / "no-opt"), "--docker-volumes-dir", str(tmp_path / "no-docker"),
                  "--on-version-change"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "CLAUDE_VERSION_CHANGED" in out


# ----------------------------------------------------------------------- CLI

def test_cli_snapshot_check_report_roundtrip(tmp_path, capsys):
    home = tmp_path / "home"
    (home / "a").mkdir(parents=True)
    (home / "a" / "f.bin").write_bytes(b"x" * 10)
    reg_path = tmp_path / "reg.yaml"
    reg_path.write_text(yaml.safe_dump(_registry([_row("$HOME/a/**", "REBUILD")])), encoding="utf-8")
    state_dir = tmp_path / "state"
    common = ["--machine", MACHINE, "--registry", str(reg_path), "--state-dir", str(state_dir),
              "--home", str(home), "--claude-config-dir", str(home / ".claude"),
              "--opt-dir", str(tmp_path / "no-opt"), "--docker-volumes-dir", str(tmp_path / "no-docker")]

    assert md._cli(common + ["snapshot"]) == 0
    assert (state_dir / f"machine-snapshot-{MACHINE}.json").exists()

    assert md._cli(common + ["check"]) == 0  # nothing IRREPLACEABLE/UNCLASSIFIED/oversized here

    assert md._cli(common + ["report"]) == 0
    out = capsys.readouterr().out
    assert "REBUILD" in out


def test_cli_check_exits_1_on_a_problem(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / "secret.env").write_text("x")
    reg_path = tmp_path / "reg.yaml"
    reg_path.write_text(
        yaml.safe_dump(_registry([_row("$HOME/secret.env", "IRREPLACEABLE", restore="")])),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    rc = md._cli(["--machine", MACHINE, "--registry", str(reg_path), "--state-dir", str(state_dir),
                  "--home", str(home), "--claude-config-dir", str(home / ".claude"),
                  "--opt-dir", str(tmp_path / "no-opt"), "--docker-volumes-dir", str(tmp_path / "no-docker"),
                  "check"])
    assert rc == 1


# ---- Windows rows (first winbox run 2026-09-24): %VAR% expansion, separators, junction-safe walk


def test_windows_vars_expand_on_windows_only():
    env = {"USERPROFILE": "C:\\Users\\passg", "LocalAppData": "C:\\Users\\passg\\AppData\\Local"}
    ctx = {"HOME": "C:\\Users\\passg", "CLAUDE_CONFIG_DIR": "C:\\Users\\passg\\.claude", "hq": "",
           "_os": "windows", "_env": env}
    assert md._substitute("%USERPROFILE%/cookierun-bot/**", ctx) == "C:\\Users\\passg/cookierun-bot/**"
    # case-insensitive lookup, like cmd.exe
    assert md._substitute("%LOCALAPPDATA%/Google/**", ctx) == "C:\\Users\\passg\\AppData\\Local/Google/**"
    # an unset name stays literal so the row never matches, instead of matching everything
    assert md._substitute("%NOPE%/x", ctx) == "%NOPE%/x"
    # the same row on a non-Windows machine is "not applicable"
    assert md._substitute("%USERPROFILE%/cookierun-bot/**", dict(ctx, _os="linux")) is None


def test_segments_are_normcased(monkeypatch):
    # normcase is a no-op on POSIX; emulate Windows' folding to prove _covered uses it
    monkeypatch.setattr(md.os.path, "normcase", lambda s: s.replace("\\", "/").lower())
    assert md._covered(Path("C:/Users/PASSG/cookierun-bot"),
                       ["C:/Users/passg/cookierun-bot/**"])


def test_is_link_skips_symlinks_and_walk_prunes_them(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "f.bin").write_bytes(b"x" * 1000)
    link = tmp_path / "loop"
    link.symlink_to(real, target_is_directory=True)
    assert md._is_link(link) is True
    assert md._is_link(real) is False
    # the link contributes nothing, and a walk from tmp_path counts the real bytes once
    assert md._path_bytes(link) == 0
    assert md._path_bytes(tmp_path) == 1000
