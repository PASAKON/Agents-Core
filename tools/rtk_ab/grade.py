#!/usr/bin/env python3
"""Score a run's transcript output against tools/rtk_ab/ANSWER_KEY.json, out of 10.

Usage: python3 tools/rtk_ab/grade.py <path-to-file-with-agent-stdout>
Finds the last line in the file that parses as a JSON object and compares its
10 fields against the answer key. q3 (5 largest files) is graded as a set of
(path, bytes) pairs — order doesn't matter, but all 5 must match exactly.
Prints "N/10" plus a per-question breakdown; exits 1 if no JSON line found.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = json.load(open(os.path.join(HERE, 'ANSWER_KEY.json')))['answers']


def find_last_json_object(text):
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith('{') or not line.endswith('}'):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def grade(got):
    score = 0
    rows = []

    q1_ok = all(got.get(k) == KEY[k] for k in
                ('q1_pytest_passed', 'q1_pytest_failed', 'q1_pytest_skipped'))
    score += q1_ok
    rows.append(('q1_pytest', q1_ok,
                 {k: KEY[k] for k in ('q1_pytest_passed', 'q1_pytest_failed', 'q1_pytest_skipped')},
                 {k: got.get(k) for k in ('q1_pytest_passed', 'q1_pytest_failed', 'q1_pytest_skipped')}))

    simple_keys = [
        'q2_skill_commits', 'q4_scripts_py_count', 'q5_lib_py_count',
        'q6_tools_def_main_count', 'q7_scripts_lsR_dir_count',
        'q9_token_profile_lines', 'q10_tools_import_argparse_count',
    ]
    for k in simple_keys:
        ok = got.get(k) == KEY[k]
        score += ok
        rows.append((k, ok, KEY[k], got.get(k)))

    q3_ok = False
    try:
        got_set = {(p, b) for p, b in got.get('q3_largest_tools_files', [])}
        key_set = {(p, b) for p, b in KEY['q3_largest_tools_files']}
        q3_ok = got_set == key_set
    except (TypeError, ValueError):
        pass
    score += q3_ok
    rows.append(('q3_largest_tools_files', q3_ok, KEY['q3_largest_tools_files'], got.get('q3_largest_tools_files')))

    q8_ok = got.get('q8_head_stat') == KEY['q8_head_stat']
    score += q8_ok
    rows.append(('q8_head_stat', q8_ok, KEY['q8_head_stat'], got.get('q8_head_stat')))

    return score, rows


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    text = open(sys.argv[1], errors='ignore').read()
    got = find_last_json_object(text)
    if got is None:
        print('NO JSON OBJECT FOUND in', sys.argv[1])
        sys.exit(1)
    score, rows = grade(got)
    for k, ok, want, have in rows:
        mark = 'OK ' if ok else 'FAIL'
        print(f'{mark} {k}: want={want!r} got={have!r}')
    print(f'\nSCORE: {score}/10')


if __name__ == '__main__':
    main()
