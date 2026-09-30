"""W1.9 follow-up (task-a23e8873): scripts/hub/contabo-cutover-remote.sh after the rehearsal
findings of task-a49a3f35 (docs/reports/task-a49a3f35/REPORT.md), so the real W1.10 cutover
cannot hit them.

  F2  the drop-in `install` loop and `systemctl daemon-reload` moved from step 4 to step 8,
      right before the restarts: a unit systemd restarts earlier must come back on its OLD
      unit file, never on a half-migrated hub.
  F3  step 5 refuses while state/tasks.db holds a pending / in_progress / queued_remote task,
      then stops the watchdog, the secretary and its waker before the import; a failure after
      the stop prints how to start them again.
  F4  MOONIEX_NODE_YAML is exported from NODE_YAML (cutover_flip.py reads only the former),
      and the rollback line it prints carries it.
  F7  the rollback text removes the three now-empty <unit>.service.d directories.
  F5/F6 are runbook lines in docs/design/org-mesh-w18-contabo-consumers.md.

Same throwaway root as tests/test_w18_contabo_consumers.py (imported: its `box` fixture and
its fake python3 / systemctl / .venv tools, which log to one file in call order). The fakes
record how many drop-ins existed under SYSTEMD_DIR at the moment of each call, so "install
after migrate, before restart" is read off the log, not assumed. Nothing here reaches a real
unit, node file, database or the network.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# tests/ has no __init__.py: pytest puts this directory on sys.path, so the W1.8 module imports by name.
from test_w18_contabo_consumers import (  # noqa: F401  (box is a fixture, used by name)
    CUTOVER, DESIGN, REMOTE, ROOT, UNITS, _make_tasks_db, _no_dropins_installed, _read_log,
    _run_remote, box,
)

LIVE_STATUSES = ("pending", "in_progress", "queued_remote")
ROLLBACK_HEAD = "Rollback (Contabo half"


def _labels(box) -> list[str]:
    """One label per call that matters, in the order the script made them."""
    out = []
    for c in _read_log(box.log):
        a = c["argv"]
        if c["tool"] == "systemctl" and a[:1] in (["stop"], ["restart"]):
            out.append(f"{a[0]}:" + a[1].removesuffix(".service"))
        elif c["tool"] == "systemctl" and a[:1] == ["daemon-reload"]:
            out.append("daemon-reload")
        elif c["tool"] == "systemctl" and a[:1] == ["start"]:
            out.append("start")
        elif c["tool"] == "venv-python" and a and a[0].endswith("migrate_tasks_db.py"):
            out.append("migrate")
        elif c["tool"] == "venv-python" and a and a[0].endswith("verify_migration_counts.py"):
            out.append("verify-counts")
        elif c["tool"] == "venv-python" and a == ["-"]:
            out.append("read-back")
    return out


def _code(path: Path) -> str:
    return "\n".join(ln for ln in path.read_text().splitlines() if not ln.lstrip().startswith("#"))


def _step(code: str, n: str, nxt: str | None) -> str:
    body = code.split(f'echo "== step {n}:')[1]
    return body.split(f'echo "== step {nxt}:')[0] if nxt else body


# --------------------------------------------------------------------------- F2

def test_f2_dropins_appear_after_the_migration_and_right_before_the_restarts(box):
    _make_tasks_db(box.work)

    r = _run_remote(box)
    assert r.returncode == 0, r.stdout + r.stderr

    log = _read_log(box.log)
    at_reload = next(i for i, c in enumerate(log)
                     if c["tool"] == "systemctl" and c["argv"][:1] == ["daemon-reload"])
    first_restart = next(i for i, c in enumerate(log)
                         if c["tool"] == "systemctl" and c["argv"][:1] == ["restart"])
    assert first_restart == at_reload + 1, "the reload must be the call right before the first restart"
    # every tool call before the reload -- the stops, the migration, the verify, the read-back,
    # step 4's `systemctl cat` -- ran with NO drop-in installed on the box
    before = [c for c in log[:at_reload] if "dropins" in c]
    assert len(before) >= 8 and all(c["dropins"] == 0 for c in before), \
        [(c["tool"], c["argv"][:2], c["dropins"]) for c in before if c["dropins"]]
    assert log[at_reload]["dropins"] == len(UNITS)
    assert all(c["dropins"] == len(UNITS) for c in log[first_restart:] if "dropins" in c)
    labels = _labels(box)
    assert labels.index("migrate") < labels.index("verify-counts") < labels.index("read-back") \
        < labels.index("daemon-reload")


def test_f2_step4_and_step5_install_and_reload_nothing_when_step5_refuses(box):
    _make_tasks_db(box.work, "in_progress")

    r = _run_remote(box)

    assert r.returncode != 0 and "REFUSING:" in r.stdout
    assert _no_dropins_installed(box)
    assert "daemon-reload" not in _labels(box)


def test_f2_step_text_step4_has_no_install_or_reload_and_step8_has_both_before_the_restart():
    code = _code(REMOTE)
    step4, step8 = _step(code, "4", "5"), _step(code, "8", None)
    assert not re.search(r"\binstall\s+-[dm]\b", step4) and "daemon-reload" not in step4
    at = [step8.index(x) for x in ("install -m 644", "daemon-reload", "systemctl restart")]
    assert at == sorted(at)
    assert not re.search(r"\binstall\s+-[dm]\b|daemon-reload", _step(code, "5", "5b"))


def test_f2_a_dropin_that_cannot_be_installed_refuses_before_any_restart(box):
    _make_tasks_db(box.work)
    blocker = box.tmp / "a-file"
    blocker.write_text("not a directory\n")

    r = _run_remote(box, SYSTEMD_DIR=str(blocker / "systemd"))     # install -d under a file cannot work

    assert r.returncode != 0
    assert "REFUSING: could not install the drop-in for mooniex-watchdog. No unit was restarted." in r.stdout
    assert "daemon-reload" not in _labels(box) and not any(x.startswith("restart:") for x in _labels(box))
    assert r.stdout.count(ROLLBACK_HEAD) == 1


def test_f2_a_failed_daemon_reload_refuses_before_any_restart(box):
    _make_tasks_db(box.work)

    r = _run_remote(box, FAKE_RELOAD_FAIL="1")

    assert r.returncode != 0
    assert "systemctl daemon-reload failed. No unit was restarted." in r.stdout
    assert not any(x.startswith("restart:") for x in _labels(box))
    assert r.stdout.count(ROLLBACK_HEAD) == 1
    assert len(list(box.systemd.glob("*/org-db.conf"))) == len(UNITS), "the reload comes after the install"


# --------------------------------------------------------------------------- F3

@pytest.mark.parametrize("status", LIVE_STATUSES)
def test_f3_a_live_task_refuses_before_anything_is_stopped_or_written(box, status):
    _make_tasks_db(box.work, "done", status)

    r = _run_remote(box)

    assert r.returncode != 0
    assert "REFUSING: 1 task(s) in state/tasks.db are pending, in_progress or queued_remote." in r.stdout
    assert _labels(box) == []                                    # not stopped, not migrated, not reloaded
    assert (box.work / "state" / "tasks.db").is_file()
    assert _no_dropins_installed(box)
    assert box.node.read_bytes() == b"host: contabo\n"
    assert ROLLBACK_HEAD not in r.stdout, "refused before the stop: nothing to roll back"


def test_f3_every_live_task_is_counted(box):
    _make_tasks_db(box.work, "pending", "in_progress", "queued_remote", "done")

    r = _run_remote(box)

    assert r.returncode != 0 and "REFUSING: 3 task(s) in state/tasks.db" in r.stdout


def test_f3_finished_tasks_do_not_block_the_cutover(box):
    _make_tasks_db(box.work, "done", "failed", "cancelled", "stalled")

    r = _run_remote(box)

    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("how", ["no status column", "not a database"])
def test_f3_a_count_that_cannot_be_read_is_a_refusal_too(box, how):
    db = box.work / "state" / "tasks.db"
    db.parent.mkdir(exist_ok=True)
    if how == "no status column":
        subprocess.run(["sqlite3", str(db), "CREATE TABLE tasks (id INTEGER); INSERT INTO tasks VALUES (1);"],
                       check=True, capture_output=True)
    else:
        db.write_text("this is not a sqlite file\n" * 20)

    r = _run_remote(box)

    assert r.returncode != 0
    assert "REFUSING: could not count the live tasks in state/tasks.db" in r.stdout
    assert _labels(box) == [] and db.is_file() and _no_dropins_installed(box)


def test_f3_the_three_units_are_stopped_before_the_import_and_only_step8_starts_them(box):
    _make_tasks_db(box.work)

    r = _run_remote(box)
    assert r.returncode == 0, r.stdout + r.stderr

    labels = _labels(box)
    assert labels == [*[f"stop:{u}" for u in UNITS], "migrate", "verify-counts", "read-back",
                      "daemon-reload", *[f"restart:{u}" for u in UNITS]]
    log = _read_log(box.log)
    stops = [c for c in log if c["tool"] == "systemctl" and c["argv"][:1] == ["stop"]]
    assert [c["argv"] for c in stops] == [["stop", f"{u}.service"] for u in UNITS]
    assert all(c["tombstone"] is False and c["node_hub"] is False and c["dropins"] == 0 for c in stops)
    assert "start" not in labels, "step 8's restart is what brings the units back"
    assert ROLLBACK_HEAD not in r.stdout and "FAILED (exit" not in r.stdout


def test_f3_without_a_ledger_nothing_is_stopped(box):
    r = _run_remote(box)                                          # no state/tasks.db in the throwaway root

    assert r.returncode == 0, r.stdout + r.stderr
    assert "no state/tasks.db here" in r.stdout
    assert _labels(box) == ["read-back", "daemon-reload", *[f"restart:{u}" for u in UNITS]]


def test_f3_a_unit_that_will_not_stop_refuses_before_the_import(box):
    _make_tasks_db(box.work)

    r = _run_remote(box, FAKE_STOP_FAIL_UNIT="mooniex-secretary")

    assert r.returncode != 0
    assert "REFUSING: could not stop mooniex-secretary. Nothing was imported." in r.stdout
    labels = _labels(box)
    assert "migrate" not in labels and not any(x.startswith("restart:") for x in labels)
    assert (box.work / "state" / "tasks.db").is_file() and _no_dropins_installed(box)
    assert r.stdout.count(ROLLBACK_HEAD) == 1
    assert f"systemctl start {' '.join(UNITS)}" in r.stdout


def test_f3_a_failure_after_the_stop_says_how_to_start_the_units_on_the_old_unit_files(box):
    _make_tasks_db(box.work)

    r = _run_remote(box, FAKE_MIGRATE_FAIL="1")

    assert r.returncode != 0
    assert r.stdout.count(ROLLBACK_HEAD) == 1
    assert "FAILED (exit 1) after step 5 stopped the three units." in r.stdout
    tail = r.stdout[r.stdout.index(ROLLBACK_HEAD):]
    assert f"systemctl start {' '.join(UNITS)}" in tail
    assert "OLD unit files" in tail and "tasks.db half" in tail
    # ... and the claim is true at that moment: no drop-in was installed, the node file is untouched
    assert _no_dropins_installed(box) and box.node.read_bytes() == b"host: contabo\n"
    assert not any(x.startswith("restart:") for x in _labels(box))
    assert (box.work / "state" / "tasks.db").is_file(), "no tombstone before a successful migration"


def test_f3_a_step8_failure_prints_the_rollback_once_not_twice(box):
    _make_tasks_db(box.work)

    r = _run_remote(box, FAKE_INACTIVE_UNIT="mooniex-secretary")

    assert r.returncode != 0
    assert r.stdout.count(ROLLBACK_HEAD) == 1
    assert "FAILED (exit" not in r.stdout                        # step 8 said it itself; the trap stays quiet
    assert f"systemctl start {' '.join(UNITS)}" in r.stdout


def test_f3_a_refusal_before_the_stop_prints_no_rollback(box):
    r = _run_remote(box, FAKE_MISSING_UNIT="mooniex-secretary")   # step 4 refuses

    assert r.returncode != 0 and "REFUSING:" in r.stdout
    assert ROLLBACK_HEAD not in r.stdout and "FAILED (exit" not in r.stdout


def test_f3_step5_text_counts_first_then_stops_and_names_the_three_statuses():
    step5 = _step(_code(REMOTE), "5", "5b")
    assert "'pending','in_progress','queued_remote'" in step5
    assert step5.index("select count(*) from tasks") < step5.index("systemctl stop") \
        < step5.index("migrate_tasks_db.py")


# --------------------------------------------------------------------------- F4

@pytest.mark.parametrize("outer", ["decoy", "unset"])
def test_f4_moonix_node_yaml_follows_node_yaml_in_every_child(box, outer):
    _make_tasks_db(box.work)
    decoy = box.tmp / "live-looking" / "node.yaml"
    env = box.env(**({"MOONIEX_NODE_YAML": str(decoy)} if outer == "decoy" else {}))
    if outer == "unset":
        env.pop("MOONIEX_NODE_YAML")

    r = subprocess.run(["bash", str(REMOTE)], env=env, capture_output=True, text=True, timeout=60)

    assert r.returncode == 0, r.stdout + r.stderr
    seen = {c["node_env"] for c in _read_log(box.log) if c["tool"] == "systemctl"}
    assert seen == {str(box.node)}
    assert not decoy.exists() and box.node.read_text() == "host: contabo\norg_db: hub\n"


def test_f4_the_printed_rollback_line_names_the_node_file_and_reaches_only_that_one(box):
    _make_tasks_db(box.work)
    r = _run_remote(box, FAKE_INACTIVE_UNIT="mooniex-secretary")   # step 8 fails after the node write
    assert r.returncode != 0 and box.node.read_text() == "host: contabo\norg_db: hub\n"

    m = re.search(r"\((MOONIEX_NODE_YAML=\S+ python3 scripts/hub/cutover_flip\.py --rollback --apply)\)", r.stdout)
    assert m, r.stdout
    line = m.group(1)
    assert line == f"MOONIEX_NODE_YAML={box.node} python3 scripts/hub/cutover_flip.py --rollback --apply"
    # run exactly what was printed, with a HOME whose default node file must stay untouched
    home = box.tmp / "rollback-home"
    live = home / ".config" / "mooniex" / "node.yaml"
    live.parent.mkdir(parents=True)
    live.write_text("host: contabo\norg_db: hub\n")

    rb = subprocess.run(["bash", "-c", line], cwd=box.work, capture_output=True, text=True, timeout=30,
                        env={"PATH": os.environ["PATH"], "HOME": str(home)})

    assert rb.returncode == 0, rb.stdout + rb.stderr
    assert box.node.read_bytes() == b"host: contabo\n"
    assert live.read_text() == "host: contabo\norg_db: hub\n"


def test_f4_the_script_exports_the_variable_next_to_the_other_defaults():
    code = _code(REMOTE)
    assert 'export MOONIEX_NODE_YAML="$NODE_YAML"' in code
    assert code.index('NODE_YAML="${NODE_YAML:-') < code.index('export MOONIEX_NODE_YAML="$NODE_YAML"') \
        < code.index("cd \"$ROOT\"")
    assert "MOONIEX_NODE_YAML=/root/.config/mooniex/node.yaml python3 scripts/hub/cutover_flip.py" \
        in CUTOVER.read_text()


# --------------------------------------------------------------------------- F7

@pytest.mark.skipif(sys.platform == "darwin", reason="GNU rmdir flag; the script runs on Contabo")
def test_f7_the_printed_rollback_leaves_no_empty_unit_dirs_and_keeps_a_foreign_file(box):
    _make_tasks_db(box.work)
    r = _run_remote(box, FAKE_INACTIVE_UNIT="mooniex-secretary")   # drop-ins installed, then a unit failed
    assert r.returncode != 0
    m = re.search(r"rmdir --ignore-fail-on-non-empty (\S+)/<unit>\.service\.d", r.stdout)
    assert m, r.stdout
    assert m.group(1) == str(box.systemd)
    (box.systemd / "mooniex-secretary.service.d" / "keep-me.conf").write_text("someone else's drop-in\n")

    for u in UNITS:                                               # step 1 of the printed rollback, for each unit
        d = box.systemd / f"{u}.service.d"
        (d / "org-db.conf").unlink()
        rm = subprocess.run(["rmdir", "--ignore-fail-on-non-empty", str(d)], capture_output=True, text=True)
        assert rm.returncode == 0, rm.stderr

    assert sorted(p.name for p in box.systemd.iterdir()) == ["mooniex-secretary.service.d"]
    assert [p.name for p in (box.systemd / "mooniex-secretary.service.d").iterdir()] == ["keep-me.conf"]


def test_f7_both_rollback_texts_name_the_rmdir():
    assert "rmdir --ignore-fail-on-non-empty" in REMOTE.read_text()
    header = CUTOVER.read_text().split("set -euo pipefail")[0]
    assert "rmdir --ignore-fail-on-non-empty /etc/systemd/system/$u.service.d" in header


# ---------------------------------------------------------------- F5 / F6 (runbook)

def test_f5_f6_runbook_lines_are_in_the_design_doc():
    text = (ROOT / DESIGN).read_text()
    section = " ".join(text.split("## Runbook lines for the W1.10 window")[1].split("\n## ")[0].split())
    assert "Mac cutover first, or Contabo first: either order is safe" in section
    assert "0 key overlap" in section
    assert "stale Console tasks" in section and "src/orgdb.js" in section
    assert "frozen at the cutover moment" in section


def test_the_headers_describe_the_new_step_order():
    header = CUTOVER.read_text().split("set -euo pipefail")[0]
    h4 = header.split("#   4.")[1].split("#   5.")[0]
    h5 = header.split("#   5.")[1].split("#   6.")[0]
    h8 = header.split("#   8.")[1].split("# Rollback:")[0]
    assert "copy the three drop-ins" not in h4 and "daemon-reload" not in h4
    assert "pending / in_progress / queued_remote" in h5 and "systemctl stop" in h5
    assert "copy the three drop-ins" in h8 and "daemon-reload" in h8
