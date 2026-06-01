"""Smoke test for the auto_deploy branch inside merge_task (git_ops.py).

Tests the subprocess dispatch logic in isolation without needing a real repo,
task DB, or SSH access — covers all four cases from the acceptance criteria:
  1. No auto_deploy block → deployed=false, reason="no auto_deploy config"
  2. enabled=false → same as no block
  3. enabled=true, requires_ceo_ack=true → deployed=false, reason="awaiting_ceo_ack"
  4. enabled=true, requires_ceo_ack=false, command succeeds → deployed=true, rc=0
  5. enabled=true, requires_ceo_ack=false, command fails → deployed=false, rc!=0
  6. enabled=true, requires_ceo_ack=false, timeout → deployed=false, reason="timeout"

Run via:  python scripts/test_auto_deploy.py
"""
from __future__ import annotations

import subprocess
import sys

_failures = 0


def _check(label: str, cond: bool) -> None:
    global _failures
    status = "OK  " if cond else "FAIL"
    print(f"  [{status}] {label}")
    if not cond:
        _failures += 1


def _run_auto_deploy(auto: dict) -> dict:
    """Reproduce the auto_deploy branch from merge_task verbatim."""
    deploy_result: dict = {"deployed": False, "reason": "no auto_deploy config"}

    if auto.get("enabled"):
        if auto.get("requires_ceo_ack"):
            deploy_result = {"deployed": False, "reason": "awaiting_ceo_ack",
                             "command": auto.get("command", "")}
        else:
            cmd = auto.get("command", "")
            timeout = int(auto.get("timeout_seconds", 60))
            try:
                proc = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=timeout
                )
                deploy_result = {
                    "deployed": proc.returncode == 0,
                    "stdout": proc.stdout[-500:],
                    "stderr": proc.stderr[-500:],
                    "rc": proc.returncode,
                }
            except subprocess.TimeoutExpired:
                deploy_result = {"deployed": False, "reason": "timeout",
                                 "timeout_seconds": timeout}

    return deploy_result


print("=== auto_deploy smoke tests ===\n")

print("Case 1: no auto_deploy block")
r = _run_auto_deploy({})
_check("deployed=False", r["deployed"] is False)
_check("reason=no auto_deploy config", r.get("reason") == "no auto_deploy config")

print("\nCase 2: enabled=false")
r = _run_auto_deploy({"enabled": False, "command": "echo should_not_run"})
_check("deployed=False", r["deployed"] is False)
_check("reason=no auto_deploy config (not enabled)", r.get("reason") == "no auto_deploy config")

print("\nCase 3: enabled=true, requires_ceo_ack=true")
r = _run_auto_deploy({"enabled": True, "requires_ceo_ack": True,
                      "command": "echo deploy_cmd"})
_check("deployed=False", r["deployed"] is False)
_check("reason=awaiting_ceo_ack", r.get("reason") == "awaiting_ceo_ack")
_check("command preserved", "echo deploy_cmd" in r.get("command", ""))

print("\nCase 4: enabled=true, requires_ceo_ack=false, command succeeds")
r = _run_auto_deploy({"enabled": True, "requires_ceo_ack": False,
                      "command": "echo hello_deploy", "timeout_seconds": 10})
_check("deployed=True", r["deployed"] is True)
_check("rc=0", r.get("rc") == 0)
_check("stdout captured", "hello_deploy" in r.get("stdout", ""))

print("\nCase 5: enabled=true, requires_ceo_ack=false, command fails")
r = _run_auto_deploy({"enabled": True, "requires_ceo_ack": False,
                      "command": "exit 42", "timeout_seconds": 10})
_check("deployed=False", r["deployed"] is False)
_check("rc=42", r.get("rc") == 42)

print("\nCase 6: enabled=true, requires_ceo_ack=false, timeout")
r = _run_auto_deploy({"enabled": True, "requires_ceo_ack": False,
                      "command": "sleep 10", "timeout_seconds": 1})
_check("deployed=False", r["deployed"] is False)
_check("reason=timeout", r.get("reason") == "timeout")
_check("timeout_seconds preserved", r.get("timeout_seconds") == 1)

print(f"\n=== {'PASSED' if _failures == 0 else f'FAILED ({_failures} failures)'} ===")
sys.exit(0 if _failures == 0 else 1)
