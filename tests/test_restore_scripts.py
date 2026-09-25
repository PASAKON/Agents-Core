"""tests/test_restore_scripts.py — structural tests for scripts/contabo_restore.sh and
scripts/mac_restore.sh (ADR 0031, IRON §58, docs/ops/briefs/machine-contract-phase3-restore.md).

Every test that runs a script uses --dry-run only (this suite never runs a real restore —
see the brief's "Not in scope"). Path-carrying env vars (HQ_ROOT/CORE for contabo,
HOME_HQ/CORE for mac) are pointed at tmp_path so a run here can never read or write the
real box; the "never writes" tests confirm --dry-run truly executes nothing that changes
state, not just that it prints something plausible.
"""
from __future__ import annotations

import os
import platform
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CONTABO_SCRIPT = ROOT / "scripts" / "contabo_restore.sh"
MAC_SCRIPT = ROOT / "scripts" / "mac_restore.sh"

CONTABO_TOTAL = 9
MAC_TOTAL = 8

# Steps the brief calls out as needing a human hand (tailscale login, cross-machine
# rsync, EnvironmentFile from the secrets bundle, crontab confirmation, Drive volume
# tars, claude login + re-trust, secrets fetch) — see each script's hdr() names.
CONTABO_HUMAN_STEPS = {1, 2, 4, 5, 6, 7, 8}
CONTABO_NON_HUMAN_STEPS = {3, 9}
# step 2 became HUMAN on 2026-09-25: a fresh Mac has no SSH key until step 7, so cloning the
# private repos needs `gh auth login` (HTTPS) first.
MAC_HUMAN_STEPS = {2, 4, 5, 6, 7}
MAC_NON_HUMAN_STEPS = {1, 3, 8}


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        args, capture_output=True, text=True, cwd=ROOT, env=full_env, timeout=90,
    )


def _step_chunks(output: str) -> dict[int, str]:
    """{step_number: <output from its header up to the next header>}."""
    markers = list(re.finditer(r"^\[(\d+)/(\d+)\] .*$", output, re.MULTILINE))
    chunks: dict[int, str] = {}
    for i, m in enumerate(markers):
        n = int(m.group(1))
        start = m.start()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(output)
        chunks[n] = output[start:end]
    return chunks


def _step_numbers(output: str, total: int) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(r"\[(\d+)/%d\]" % total, output)]


# ============================================================== bash -n syntax

def test_contabo_restore_bash_syntax_ok():
    r = _run(["bash", "-n", str(CONTABO_SCRIPT)])
    assert r.returncode == 0, r.stderr


def test_mac_restore_bash_syntax_ok():
    r = _run(["bash", "-n", str(MAC_SCRIPT)])
    assert r.returncode == 0, r.stderr


def test_both_scripts_are_shebanged_bash():
    for script in (CONTABO_SCRIPT, MAC_SCRIPT):
        first_line = script.read_text(encoding="utf-8").splitlines()[0]
        assert first_line == "#!/usr/bin/env bash", f"{script}: {first_line!r}"


# =================================================== contabo_restore.sh --dry-run

@pytest.fixture
def contabo_env(tmp_path):
    hq = tmp_path / "hq"
    return {"HQ_ROOT": str(hq), "CORE": str(hq / "Agents" / "Core")}


def test_contabo_dry_run_exits_zero(contabo_env):
    r = _run(["bash", str(CONTABO_SCRIPT), "--dry-run"], env=contabo_env)
    assert r.returncode == 0, r.stdout + r.stderr


def test_contabo_dry_run_prints_every_step_header_in_order(contabo_env):
    r = _run(["bash", str(CONTABO_SCRIPT), "--dry-run"], env=contabo_env)
    assert _step_numbers(r.stdout, CONTABO_TOTAL) == list(range(1, CONTABO_TOTAL + 1)), r.stdout


def test_contabo_dry_run_human_steps_carry_the_marker(contabo_env):
    r = _run(["bash", str(CONTABO_SCRIPT), "--dry-run"], env=contabo_env)
    chunks = _step_chunks(r.stdout)
    assert set(chunks) == set(range(1, CONTABO_TOTAL + 1)), chunks.keys()
    for n in CONTABO_HUMAN_STEPS:
        assert "HUMAN" in chunks[n], f"step {n} is missing its HUMAN marker:\n{chunks[n]}"


def test_contabo_dry_run_non_human_steps_stay_unmarked(contabo_env):
    # Not a brief requirement, but pins down that HUMAN is meaningful (not stamped on
    # every step) so the "must carry the marker" test above can't pass vacuously.
    r = _run(["bash", str(CONTABO_SCRIPT), "--dry-run"], env=contabo_env)
    chunks = _step_chunks(r.stdout)
    for n in CONTABO_NON_HUMAN_STEPS:
        assert "HUMAN" not in chunks[n], f"step {n} unexpectedly carries HUMAN:\n{chunks[n]}"


def test_contabo_dry_run_never_writes_under_hq_root(contabo_env):
    hq = Path(contabo_env["HQ_ROOT"])
    r = _run(["bash", str(CONTABO_SCRIPT), "--dry-run"], env=contabo_env)
    assert r.returncode == 0
    assert not hq.exists(), "--dry-run must not create anything under HQ_ROOT/CORE"


def test_contabo_dry_run_prints_a_pass_fail_summary_line(contabo_env):
    r = _run(["bash", str(CONTABO_SCRIPT), "--dry-run"], env=contabo_env)
    assert re.search(r"^\[SUMMARY\] (PASS|FAIL)", r.stdout, re.MULTILINE), r.stdout


def test_contabo_dry_run_prints_a_drill_jsonl_template(contabo_env):
    r = _run(["bash", str(CONTABO_SCRIPT), "--dry-run"], env=contabo_env)
    assert "re-os-drills.jsonl" in r.stdout
    assert '"machine": "contabo"' in r.stdout
    assert '"minutes_to_remote_access"' in r.stdout


def test_contabo_restore_script_has_at_least_5_human_lines():
    # Mirrors the brief's own verification: grep -c HUMAN scripts/contabo_restore.sh
    text = CONTABO_SCRIPT.read_text(encoding="utf-8")
    assert len(re.findall(r"HUMAN", text)) >= 5


def test_contabo_restore_never_touches_drive_docker_up_or_secrets_paths():
    text = CONTABO_SCRIPT.read_text(encoding="utf-8")
    # "rclone"/"Drive" may appear in HUMAN prose (pointing at where a human fetches
    # something from) but must never be the target of a cmd/cmd_sh invocation.
    for line in text.splitlines():
        stripped = line.strip()
        if re.search(r"rclone|drive", stripped, re.IGNORECASE) and (
            stripped.startswith("cmd ") or stripped.startswith("cmd_sh ")
        ):
            pytest.fail(f"contabo_restore.sh must not invoke Drive/rclone directly: {line!r}")
    assert not re.search(r"docker(\s+compose)?\s+up\b", text), "must never run docker ... up"
    assert "cat /root/.ssh" not in text and "cat $HOME/.ssh" not in text


# ======================================================= mac_restore.sh --dry-run

@pytest.fixture
def mac_env(tmp_path):
    home_hq = tmp_path / "homehq"
    # HOME and CLAUDE_CONFIG_DIR too: on the Mac itself a real (non --dry-run) run is NOT
    # refused, and the script's `ln -sfn … "$HOME/.claude/…"` repointed the REAL
    # ~/.claude/{CLAUDE.md,commands,hooks,settings.json,tools} into this tmp dir
    # (2026-09-25 03:02, every Mac session lost its settings, hooks and /spawn-cto).
    fake_home = tmp_path / "home"
    return {"HOME_HQ": str(home_hq), "CORE": str(home_hq / "Agents" / "Core"),
            "HOME": str(fake_home), "CLAUDE_CONFIG_DIR": str(fake_home / ".claude")}


def test_mac_dry_run_exits_zero(mac_env):
    r = _run(["bash", str(MAC_SCRIPT), "--dry-run"], env=mac_env)
    assert r.returncode == 0, r.stdout + r.stderr


def test_mac_dry_run_prints_every_step_header_in_order(mac_env):
    r = _run(["bash", str(MAC_SCRIPT), "--dry-run"], env=mac_env)
    assert _step_numbers(r.stdout, MAC_TOTAL) == list(range(1, MAC_TOTAL + 1)), r.stdout


def test_mac_dry_run_human_steps_carry_the_marker(mac_env):
    r = _run(["bash", str(MAC_SCRIPT), "--dry-run"], env=mac_env)
    chunks = _step_chunks(r.stdout)
    assert set(chunks) == set(range(1, MAC_TOTAL + 1)), chunks.keys()
    for n in MAC_HUMAN_STEPS:
        assert "HUMAN" in chunks[n], f"step {n} is missing its HUMAN marker:\n{chunks[n]}"


def test_mac_dry_run_non_human_steps_stay_unmarked(mac_env):
    r = _run(["bash", str(MAC_SCRIPT), "--dry-run"], env=mac_env)
    chunks = _step_chunks(r.stdout)
    for n in MAC_NON_HUMAN_STEPS:
        assert "HUMAN" not in chunks[n], f"step {n} unexpectedly carries HUMAN:\n{chunks[n]}"


def test_mac_dry_run_never_writes_under_home_hq(mac_env):
    home_hq = Path(mac_env["HOME_HQ"])
    r = _run(["bash", str(MAC_SCRIPT), "--dry-run"], env=mac_env)
    assert r.returncode == 0
    assert not home_hq.exists(), "--dry-run must not create anything under HOME_HQ/CORE"


def test_mac_dry_run_allowed_on_this_non_darwin_box(mac_env):
    # The whole point of --dry-run existing here (brief: "no macOS on this box").
    r = _run(["bash", str(MAC_SCRIPT), "--dry-run"], env=mac_env)
    assert r.returncode == 0
    assert "refusing" not in r.stderr.lower()


@pytest.mark.skipif(platform.system() == "Darwin",
                    reason="on macOS a real run is not refused: it would execute the restore "
                           "(brew, launchctl, tailscale, ~/.claude links). This test only proves "
                           "the non-Darwin refusal.")
def test_mac_restore_refuses_a_real_run_on_non_darwin(mac_env):
    # Safe to invoke without --dry-run: the Darwin check runs before any command that
    # could change state (see the script — the guard is the first thing after arg
    # parsing), and this test box is Linux, so it always exits at that check.
    r = _run(["bash", str(MAC_SCRIPT)], env=mac_env)
    assert r.returncode != 0
    assert "refusing" in r.stderr and "not macOS" in r.stderr, r.stderr
    home_hq = Path(mac_env["HOME_HQ"])
    assert not home_hq.exists(), "the refusal path must not create anything either"


def test_mac_restore_script_matches_the_established_darwin_guard_idiom():
    # scripts/mac_blueprint.sh already carries this exact guard; keep the two scripts
    # consistent rather than inventing a second way to say the same thing.
    contract = MAC_SCRIPT.read_text(encoding="utf-8")
    blueprint = (ROOT / "scripts" / "mac_blueprint.sh").read_text(encoding="utf-8")
    guard = 'uname -s)" != "Darwin"'
    assert guard in contract
    assert guard in blueprint
