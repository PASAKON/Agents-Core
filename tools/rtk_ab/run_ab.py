#!/usr/bin/env python3
"""Drive the RTK A/B: run the same read-only Bash-heavy job in arm A (no RTK)
and arm B (RTK PreToolUse hook wired) via headless `claude -p`, save each
run's JSON result + stdout under tools/rtk_ab/results/.

Usage:
  python3 tools/rtk_ab/run_ab.py --smoke        # 1 run each, A then B
  python3 tools/rtk_ab/run_ab.py --measured     # 3 runs each, alternating order
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ARMS = {'A': HERE / 'arms' / 'A', 'B': HERE / 'arms' / 'B'}
RESULTS = HERE / 'results'
PROMPT_TEXT = (HERE / 'PROMPT.md').read_text()
CLAUDE_BIN = 'claude'
MODEL = 'claude-sonnet-5'
TIMEOUT_S = 20 * 60
RTK_BIN_DIR = str(HERE / 'bin')  # rtk's own rewrite hardcodes bare "rtk" -> must be on PATH


def run_one(arm, index):
    cwd = ARMS[arm]
    cmd = [CLAUDE_BIN, '-p', PROMPT_TEXT, '--model', MODEL,
           '--output-format', 'json', '--permission-mode', 'bypassPermissions']
    env = dict(os.environ)
    env['PATH'] = RTK_BIN_DIR + os.pathsep + env.get('PATH', '')
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=TIMEOUT_S, env=env)
        wall = time.time() - t0
        timed_out = False
    except subprocess.TimeoutExpired as e:
        wall = time.time() - t0
        proc = None
        timed_out = True
        stdout, stderr = (e.stdout or ''), (e.stderr or '')

    out = {
        'arm': arm, 'run_index': index, 'wall_seconds': round(wall, 1),
        'timed_out': timed_out,
        'returncode': proc.returncode if proc else None,
        'stdout_raw': proc.stdout if proc else stdout,
        'stderr_raw': (proc.stderr if proc else stderr)[-4000:],
    }
    if proc and proc.stdout:
        try:
            out['claude_result'] = json.loads(proc.stdout)
        except json.JSONDecodeError:
            out['claude_result'] = None
    RESULTS.mkdir(exist_ok=True)
    dest = RESULTS / f'{arm}-{index}.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f'[{arm}-{index}] wall={wall:.0f}s rc={out["returncode"]} timed_out={timed_out} -> {dest}')
    return out


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--smoke', action='store_true', help='1 run each: A then B')
    g.add_argument('--measured', action='store_true', help='3 runs each, alternating order per the design')
    a = ap.parse_args()

    if a.smoke:
        run_one('A', 0)
        run_one('B', 0)
        return

    for i in range(1, 4):
        order = ('A', 'B') if i % 2 else ('B', 'A')
        for arm in order:
            run_one(arm, i)


if __name__ == '__main__':
    main()
