"""
Storage policy module.

Purpose: Parses, validates, and classifies paths based on the storage policy rules.
Precedence: NEVER > REBUILD > COLD > HOT.
CLI: Provides commands to check the policy and classify paths.
Ref: ADR 0030.
"""
import argparse
import sys
import yaml
import time
import os
from pathlib import Path
import fnmatch

class PolicyError(Exception):
    pass

def load(path):
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise PolicyError(f"Failed to load yaml: {e}")

    if not isinstance(data, dict):
        raise PolicyError("Root must be a mapping")

    # Validate gauge
    if "gauge" not in data:
        raise PolicyError("Missing key: gauge")

    gauge = data["gauge"]
    if not isinstance(gauge, dict):
        raise PolicyError("gauge must be a mapping")

    for color in ["green", "yellow", "orange", "red"]:
        if color not in gauge:
            raise PolicyError(f"gauge missing color: {color}")
        if not isinstance(gauge[color], (int, float)):
            raise PolicyError(f"gauge color {color} must be a number")
        if gauge[color] < 0:
            raise PolicyError(f"gauge color {color} must be >= 0")

    if not (gauge["green"] > gauge["yellow"] > gauge["orange"] > gauge["red"]):
        raise PolicyError("gauge must have green > yellow > orange > red")

    # Validate tiers
    if "tiers" not in data:
        raise PolicyError("Missing key: tiers")
    tiers = data["tiers"]
    if not isinstance(tiers, dict):
        raise PolicyError("tiers must be a mapping")

    expected_tiers = {"HOT", "REBUILD", "COLD", "NEVER"}
    if set(tiers.keys()) != expected_tiers:
        raise PolicyError(f"tiers must be exactly {expected_tiers}")

    if not isinstance(tiers["HOT"], list):
        raise PolicyError("tiers.HOT must be a list")
    for item in tiers["HOT"]:
        if not isinstance(item, str):
            raise PolicyError("HOT entries must be strings")

    if not isinstance(tiers["NEVER"], list):
        raise PolicyError("tiers.NEVER must be a list")
    for item in tiers["NEVER"]:
        if not isinstance(item, str):
            raise PolicyError("NEVER entries must be strings")

    if not isinstance(tiers["REBUILD"], list):
        raise PolicyError("tiers.REBUILD must be a list")
    for item in tiers["REBUILD"]:
        if not isinstance(item, dict):
            raise PolicyError("REBUILD entries must be mappings")
        if "glob" not in item:
            raise PolicyError("REBUILD entry missing glob")
        if "rebuild" not in item or not item["rebuild"]:
            raise PolicyError("REBUILD entry missing or empty rebuild")

    if not isinstance(tiers["COLD"], list):
        raise PolicyError("tiers.COLD must be a list")
    for item in tiers["COLD"]:
        if not isinstance(item, dict):
            raise PolicyError("COLD entries must be mappings")
        if "glob" not in item:
            raise PolicyError("COLD entry missing glob")
        if "dest" not in item:
            raise PolicyError("COLD entry missing dest")

    return data

def match_path(path, glob_pattern, home):
    if "<" in glob_pattern and ">" in glob_pattern:
        return False

    if glob_pattern.startswith("~/"):
        glob_pattern = str(home) + glob_pattern[1:]

    # "X/**" also covers X itself: a NEVER folder must be NEVER at its own
    # root, or a folder-level scan would see ~/Pictures as UNCLASSIFIED.
    if glob_pattern.endswith("/**") and fnmatch.fnmatch(path.rstrip("/"), glob_pattern[:-3]):
        return True

    if Path(path).match(glob_pattern):
        return True

    if glob_pattern.startswith("**/") and Path(path).match(glob_pattern[3:]):
        return True

    return fnmatch.fnmatch(path, glob_pattern)

def classify(path, policy, home=None, age_days=None):
    if home is None:
        home = Path.home()

    path_str = str(path)
    home_str = str(home)

    tiers = policy.get("tiers", {})

    # Precedence: NEVER > REBUILD > COLD > HOT

    # NEVER
    for pattern in tiers.get("NEVER", []):
        if match_path(path_str, pattern, home_str):
            return "NEVER"

    # REBUILD
    for entry in tiers.get("REBUILD", []):
        if match_path(path_str, entry["glob"], home_str):
            return "REBUILD"

    # COLD
    for entry in tiers.get("COLD", []):
        if "when" in entry:
            continue
        if match_path(path_str, entry["glob"], home_str):
            if "older_than_days" in entry:
                if age_days is not None and age_days > entry["older_than_days"]:
                    return "COLD"
            else:
                return "COLD"

    # HOT
    for pattern in tiers.get("HOT", []):
        if match_path(path_str, pattern, home_str):
            return "HOT"

    return None

def band(free_gb, policy):
    gauge = policy["gauge"]
    if free_gb >= gauge["green"]:
        return "green"
    elif free_gb >= gauge["yellow"]:
        return "yellow"
    elif free_gb >= gauge["orange"]:
        return "orange"
    return "red"

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--policy", default=str(Path(__file__).resolve().parent.parent / "config" / "storage-policy.yaml"))

    classify_parser = subparsers.add_parser("classify")
    classify_parser.add_argument("path")
    classify_parser.add_argument("--policy", default=str(Path(__file__).resolve().parent.parent / "config" / "storage-policy.yaml"))

    args = parser.parse_args()

    if args.command == "check":
        try:
            load(args.policy)
            print("ok")
            sys.exit(0)
        except PolicyError as e:
            print(f"PolicyError: {e}")
            sys.exit(1)

    elif args.command == "classify":
        try:
            policy = load(args.policy)
            age_days = None
            if os.path.exists(args.path):
                mtime = os.path.getmtime(args.path)
                age_days = (time.time() - mtime) / (24 * 3600)
            result = classify(args.path, policy, age_days=age_days)
            print(result if result else "UNCLASSIFIED")
        except PolicyError as e:
            print(f"PolicyError: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
