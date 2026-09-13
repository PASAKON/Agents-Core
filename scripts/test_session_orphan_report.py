"""Tests for scripts/session_orphan_report.py.

Tests:
  1. Process whose task id has a local row -> known, never orphan.
  2. Process whose task id has no local row -> orphan.
  3. Process with no task id -> not_ours, and appears in neither other
     bucket.
  4. Unreachable host -> reported unreachable (never "no workers"), and the
     overall exit code does not claim "no orphans".
  5. A fake `subprocess.run` that raises UnicodeDecodeError (simulating a
     worker's non-UTF-8 CommandLine hitting strict decoding) -> the tool
     still classifies without crashing.

Run via: .venv/bin/python scripts/test_session_orphan_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.session_orphan_report as sor

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _check_known_process_never_orphan() -> None:
    procs = [{"pid": "100", "task": "task-11111111", "started": "now"}]
    local_tasks = {"task-11111111": "in_progress"}
    result = sor.classify(procs, local_tasks)
    _mark(len(result["known"]) == 1 and result["known"][0]["status"] == "in_progress",
          "[1a] task id with a local row -> known, carries its status")
    _mark(len(result["orphan"]) == 0,
          "[1b] known process does not also land in orphan")


def _check_unknown_task_id_is_orphan() -> None:
    procs = [{"pid": "200", "task": "task-22222222", "started": "now"}]
    local_tasks = {"task-11111111": "in_progress"}  # different id
    result = sor.classify(procs, local_tasks)
    _mark(len(result["orphan"]) == 1 and result["orphan"][0]["pid"] == "200",
          "[2] task id with no local row -> orphan")
    _mark(len(result["known"]) == 0,
          "[2b] orphan process does not also land in known")


def _check_no_task_id_is_not_ours() -> None:
    procs = [
        {"pid": "300", "task": "<none>", "started": "now"},
        {"pid": "301", "task": "task-11111111", "started": "now"},
    ]
    local_tasks = {"task-11111111": "in_progress"}
    result = sor.classify(procs, local_tasks)
    not_ours_pids = {p["pid"] for p in result["not_ours"]}
    known_pids = {p["pid"] for p in result["known"]}
    orphan_pids = {p["pid"] for p in result["orphan"]}
    _mark("300" in not_ours_pids, "[3a] no task id in argv -> not_ours")
    _mark("300" not in known_pids and "300" not in orphan_pids,
          "[3b] not-ours process appears in neither known nor orphan")
    _mark("301" in known_pids, "[3c] the other process with a real id still classifies known")


def _check_unreachable_host_is_reported_and_blocks_clean_exit() -> None:
    def fake_run_ssh(alias, remote_cmd, timeout=sor.SSH_TIMEOUT_S):
        return None  # simulates ssh timing out / connection refused

    report = sor.build_report(host_filter="winbox", run_ssh=fake_run_ssh)
    h = report["hosts"][0]
    _mark(h["reachable"] is False, "[4a] unreachable host reported as reachable=False")
    _mark("known" not in h and "orphan" not in h,
          "[4b] unreachable host is not silently reported as 'no workers'")
    code = sor.compute_exit_code(report)
    _mark(code != 0,
          f"[4c] exit code does not claim 'no orphans' when a host is unreachable (got {code})")


def _check_unicode_decode_error_does_not_crash() -> None:
    def fake_subprocess_run(*args, **kwargs):
        raise UnicodeDecodeError("utf-8", b"\xae", 0, 1, "invalid start byte")

    original = sor.subprocess.run
    sor.subprocess.run = fake_subprocess_run
    try:
        r = sor._run_ssh("winbox", ["ps", "-eo", "pid=,lstart=,args="])
        _mark(r is None,
              "[5a] _run_ssh swallows UnicodeDecodeError from subprocess.run, returns None")

        procs, reachable = sor.fetch_windows_workers("winbox")
        _mark(reachable is False and procs == [],
              "[5b] fetch_windows_workers survives the decode error (unreachable, no crash)")

        report = sor.build_report(host_filter="winbox")
        _mark(report["hosts"][0]["reachable"] is False,
              "[5c] build_report end-to-end survives the decode error without raising")
    finally:
        sor.subprocess.run = original


def _check_win_and_linux_parsers() -> None:
    win_out = "100\ttask-11111111\t9/11/2026 8:31:00 AM\n200\t<none>\t9/11/2026 8:31:01 AM\n"
    win_procs = sor._parse_win_output(win_out)
    _mark(len(win_procs) == 2 and win_procs[0]["task"] == "task-11111111",
          "[6a] windows tab-separated output parses pid/task/started")
    _mark(win_procs[1]["task"] == "<none>", "[6b] '<none>' passes through untouched")

    linux_out = (
        "  123 Thu Sep 11 08:31:00 2026 /usr/bin/claude --resume task-33333333 foo\n"
        "  456 Thu Sep 11 08:31:01 2026 /usr/sbin/sshd -D\n"
    )
    linux_procs = sor._parse_linux_ps(linux_out)
    _mark(len(linux_procs) == 1 and linux_procs[0]["task"] == "task-33333333",
          "[6c] linux ps output filters to claude processes and extracts the task id")


def main() -> int:
    _check_known_process_never_orphan()
    _check_unknown_task_id_is_orphan()
    _check_no_task_id_is_not_ours()
    _check_unreachable_host_is_reported_and_blocks_clean_exit()
    _check_unicode_decode_error_does_not_crash()
    _check_win_and_linux_parsers()

    print(f"\n{'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
