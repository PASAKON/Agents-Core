#!/usr/bin/env python3
"""Store one Run form JSON line: secret_card.py <project> <env>.

Null and empty fields are skipped. _steps is reserved for boolean step toggles.
Values travel only through subprocess stdin; child diagnostics are discarded.
An executable infisical_setup.py on PATH overrides the sibling script.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def read_form(stream):
    """Validate the entire form before any write, consuming exactly one line."""
    form = json.loads(stream.readline(), object_pairs_hook=_unique_object)
    if not isinstance(form, dict):
        raise ValueError("expected object")
    steps = form.pop("_steps", {})
    if not isinstance(steps, dict) or any(
        not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", key)
        or not isinstance(value, bool) for key, value in steps.items()
    ):
        raise ValueError("invalid steps")
    if len(form) > 16:
        raise ValueError("too many fields")
    values = {}
    for key, value in form.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", key):
            raise ValueError("invalid key")
        if value is None or value == "":
            continue
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError("invalid value")
        value = str(value)
        if value in ("nan", "inf", "-inf") or value != value.strip() or any(
            ord(char) < 32 or ord(char) == 127 for char in value
        ):
            raise ValueError("invalid value")
        values[key] = value
    return values, steps


def run_later_steps(project, env, steps):
    """PH ExpertAdvisor extension point (task-48c0accb).

    Called only after successful storage, with destination and boolean toggles,
    never form values. Implementations should emit STEP lines and return an exit
    status. No MT5/Myfxbook work is performed here yet.
    """
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("env")
    args = parser.parse_args(argv)
    try:
        values, steps = read_form(sys.stdin)
    except (ValueError, UnicodeError, RecursionError):
        print("STEP store fail invalid form", flush=True)
        return 1

    executable = shutil.which("infisical_setup.py")
    command = [executable] if executable else [
        sys.executable, str(Path(__file__).with_name("infisical_setup.py"))
    ]
    failed = False
    for key, value in values.items():
        try:
            result = subprocess.run(
                command + ["put", args.project, args.env, key, "--stdin"],
                input=value.encode("utf-8"), stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, check=False,
            )
            success = result.returncode == 0
        except (OSError, UnicodeError):
            success = False
        if success:
            suffix = value[-4:] if len(value) > 4 else "••••"
            print(f"STEP store ok {key} …{suffix}", flush=True)
        else:
            print(f"STEP store fail {key} put failed", flush=True)
            failed = True
    if failed:
        return 1
    return run_later_steps(args.project, args.env, steps)


if __name__ == "__main__":
    sys.exit(main())
