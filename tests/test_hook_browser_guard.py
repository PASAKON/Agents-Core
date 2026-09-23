import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_SCRIPT = Path("scripts/hook-browser-guard.py").resolve()

def run_hook(event, env_updates=None):
    env = os.environ.copy()
    if env_updates:
        env.update(env_updates)
    
    p = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(event).encode("utf-8"),
        env=env,
        capture_output=True,
    )
    return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8")


def test_dev_session_counts_and_warns(tmp_path):
    env = {
        "WORKER_ROLE": "1",
        "BROWSER_GUARD_STATE_DIR": str(tmp_path),
    }

    session_id = "dev_session_1"
    
    # 60 calls, 15 screenshots (all within caps)
    for i in range(60):
        # Every 4th call is a screenshot
        action = "screenshot" if i < 15 else "click"
        event = {
            "session_id": session_id,
            "tool_name": "mcp__claude-in-chrome__computer",
            "tool_input": {"action": action},
        }
        ret, stdout, stderr = run_hook(event, env)
        assert ret == 0, f"Failed at call {i+1} with return code {ret}"
        assert stderr == "", f"Unexpected stderr at call {i+1}: {stderr}"
        
    # At 61 calls, 16 screenshots, should warn but allow (exit 0)
    event = {
        "session_id": session_id,
        "tool_name": "mcp__claude-in-chrome__computer",
        "tool_input": {"action": "screenshot"},
    }
    ret, stdout, stderr = run_hook(event, env)
    assert ret == 0
    assert "WARNING" in stderr
    assert "BLOCKED by IRON-RULES" in stderr
    assert "screenshot" in stderr


def test_clevel_session_caps_and_blocks(tmp_path):
    # No WORKER_ROLE
    env = {
        "BROWSER_GUARD_STATE_DIR": str(tmp_path),
    }
    # Important: remove WORKER_ROLE if it is in the environment
    if "WORKER_ROLE" in env:
        del env["WORKER_ROLE"]

    session_id = "clevel_session_1"
    
    # 12 calls, 5 screenshots (within caps)
    for i in range(12):
        action = "screenshot" if i < 5 else "click"
        event = {
            "session_id": session_id,
            "tool_name": "mcp__claude-in-chrome__computer",
            "tool_input": {"action": action},
        }
        
        # Need to explicitly pop WORKER_ROLE since run_hook uses os.environ.copy()
        run_env = os.environ.copy()
        run_env.pop("WORKER_ROLE", None)
        run_env.update(env)
        
        p = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT)],
            input=json.dumps(event).encode("utf-8"),
            env=run_env,
            capture_output=True,
        )
        ret, stderr = p.returncode, p.stderr.decode("utf-8")

        assert ret == 0, f"Failed at call {i+1} with return code {ret}"
        assert stderr == "", f"Unexpected stderr at call {i+1}: {stderr}"
        
    # At 13 calls, 6 screenshots, should block (exit 2) and no warning prefix
    event = {
        "session_id": session_id,
        "tool_name": "mcp__claude-in-chrome__computer",
        "tool_input": {"action": "screenshot"},
    }
    
    run_env = os.environ.copy()
    run_env.pop("WORKER_ROLE", None)
    run_env.update(env)
    
    p = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(event).encode("utf-8"),
        env=run_env,
        capture_output=True,
    )
    ret, stderr = p.returncode, p.stderr.decode("utf-8")

    assert ret == 2
    assert "WARNING" not in stderr
    assert "BLOCKED by IRON-RULES" in stderr
