"""Store one Run form JSON line; values travel to the helper only on stdin."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


HELPER = Path(__file__).with_name("infisical_setup.py")


def metadata(item):
    key, sep, value = item.partition("=")
    if not sep or not re.fullmatch(r"[a-z_]+", key) or not value.strip():
        raise argparse.ArgumentTypeError("metadata must be key=value with a lowercase key")
    return item


def after_store(steps):
    """Extension point for ExpertAdvisor's MT5/Myfxbook steps after successful storage."""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("env")
    parser.add_argument("--meta", action="append", type=metadata, default=[])
    parser.add_argument("--comment", help="purpose required by the helper for new secrets")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(sys.stdin.readline())
        if not isinstance(payload, dict):
            raise ValueError
        steps = payload.get("_steps", {})
        if not isinstance(steps, dict) or any(
            not isinstance(v, bool) for v in steps.values()
        ):
            raise ValueError
        secrets = []
        for key, value in payload.items():
            if key == "_steps":
                continue
            if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", key):
                raise ValueError
            if value is None or value == "":
                continue
            if not isinstance(value, str) or value != value.strip() or any(
                ord(c) < 32 or ord(c) == 127 for c in value
            ):
                raise ValueError
            secrets.append((key, value))
    except (ValueError, TypeError):
        print("STEP store fail invalid input", flush=True)
        return 1

    failed = False
    for key, value in secrets:
        command = [sys.executable, str(HELPER), "put", args.project, args.env, key, "--stdin"]
        for item in args.meta:
            command.extend(["--meta", item])
        if args.comment is not None:
            command.extend(["--comment", args.comment])
        try:
            result = subprocess.run(command, input=value + "\n", text=True,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ok = result.returncode == 0
        except OSError:
            ok = False
        if ok:
            detail = "…" + value[-4:] if len(value) >= 20 else "set"
            print(f"STEP store ok {key} {detail}", flush=True)
        else:
            failed = True
            print(f"STEP store fail {key}", flush=True)
    if failed:
        return 1
    after_store(steps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
