#!/usr/bin/env python3
"""
scripts/update_sources.py — Free weekly check of cinematic prompt sources for updates.

Usage:
  update_sources.py [--state <path>] [--sources <path>] [--dry-run] [--with-data]
"""
import argparse
import datetime
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_SOURCES_PATH = (
    Path(__file__).resolve().parent.parent / "references" / "sources.json"
)
DEFAULT_STATE_PATH = Path("/opt/MoonieXHQ/Work/cineprompt/updates/state.json")


def fetch_url(url, timeout=30):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MoonieX-CinePrompt/1.0 (internal research tool)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def process_git_source(content_bytes, prev_state):
    try:
        commits = json.loads(content_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid JSON from git pull_url: {e}")

    if not isinstance(commits, list) or len(commits) == 0:
        newest_sha = None
        all_shas = []
    else:
        newest_sha = commits[0].get("sha")
        all_shas = [c.get("sha") for c in commits if isinstance(c, dict) and "sha" in c]

    prev_marker = prev_state.get("marker") if prev_state else None

    if prev_marker is None:
        # First seen
        detail = "(new commits)"
        return "changed", detail, {"marker": newest_sha, "all_shas": all_shas}

    if prev_marker == newest_sha:
        return "unchanged", "", prev_state

    # Changed
    if prev_marker in all_shas:
        n_new = all_shas.index(prev_marker)
        detail = f"(+{n_new} new commits)"
    else:
        detail = "(new commits)"
    return "changed", detail, {"marker": newest_sha, "all_shas": all_shas}


def process_hf_source(content_bytes, prev_state):
    try:
        data = json.loads(content_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid JSON from hf pull_url: {e}")

    if isinstance(data, dict):
        last_modified = data.get("lastModified")
    else:
        last_modified = None

    prev_marker = prev_state.get("marker") if prev_state else None

    if prev_marker is None:
        detail = f"(lastModified: {last_modified})" if last_modified else "(new lastModified)"
        return "changed", detail, {"marker": last_modified}

    if prev_marker == last_modified:
        return "unchanged", "", prev_state

    detail = f"(lastModified: {last_modified})" if last_modified else "(new lastModified)"
    return "changed", detail, {"marker": last_modified}


def process_json_source(content_bytes, prev_state):
    body_sha256 = hashlib.sha256(content_bytes).hexdigest()
    try:
        data = json.loads(content_bytes.decode("utf-8"))
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next((v for v in data.values() if isinstance(v, list)), [])
        else:
            items = []
    except Exception:
        items = []

    seen_ids = [str(item["id"]) for item in items if isinstance(item, dict) and "id" in item]
    prev_marker = prev_state.get("marker") if prev_state else None
    prev_ids = set(prev_state.get("ids", [])) if prev_state else set()

    if prev_marker is None:
        if seen_ids:
            detail = f"(+{len(seen_ids)} new ids)"
        else:
            detail = f"(sha256: {body_sha256[:8]})"
        return "changed", detail, {"marker": body_sha256, "ids": seen_ids}

    if prev_marker == body_sha256:
        return "unchanged", "", prev_state

    # Marker changed
    new_ids = set(seen_ids) - prev_ids
    if new_ids:
        detail = f"(+{len(new_ids)} new ids)"
    elif seen_ids:
        detail = f"(+{len(seen_ids)} new ids)"
    else:
        detail = f"(sha256: {body_sha256[:8]})"
    return "changed", detail, {"marker": body_sha256, "ids": seen_ids}


def main():
    parser = argparse.ArgumentParser(description="Weekly check of cinematic prompt sources")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES_PATH, help="Path to sources.json")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH, help="Path to state.json")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without network requests")
    parser.add_argument("--with-data", action="store_true", help="Download dataset files if data_url is set")
    args = parser.parse_args()

    if not args.sources.exists():
        print(f"Error: sources file not found: {args.sources}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.sources, "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:
        print(f"Error reading sources file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(sources, list):
        print("Error: sources.json must contain a JSON array", file=sys.stderr)
        sys.exit(1)

    state_path = args.state
    state_dir = state_path.parent

    if args.dry_run:
        print("DRY-RUN: Source check plan")
        print(f"State file: {state_path}")
        print(f"Sources to check ({len(sources)}):")
        for s in sources:
            name = s.get("name", "unnamed")
            pull_kind = s.get("pull_kind", "unknown")
            pull_url = s.get("pull_url", "no-url")
            has_data = "yes" if s.get("data_url") and args.with_data else "no"
            print(f"  - {name} [{pull_kind}] -> {pull_url} (download data: {has_data})")
        sys.exit(0)

    # Load existing state
    state = {}
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception as e:
            print(f"Warning: could not read existing state file ({e}), starting fresh", file=sys.stderr)
            state = {}

    failed_count = 0
    changed_sources = []
    new_state = dict(state)

    for s in sources:
        name = s.get("name", "unnamed")
        pull_kind = s.get("pull_kind", "")
        pull_url = s.get("pull_url", "")
        prev_s_state = state.get(name)

        if not pull_url:
            failed_count += 1
            print(f"{name}: error missing pull_url")
            continue

        try:
            content_bytes = fetch_url(pull_url, timeout=30)
            if pull_kind == "git":
                status, detail, s_state = process_git_source(content_bytes, prev_s_state)
            elif pull_kind == "hf":
                status, detail, s_state = process_hf_source(content_bytes, prev_s_state)
            elif pull_kind == "json":
                status, detail, s_state = process_json_source(content_bytes, prev_s_state)
            else:
                raise ValueError(f"Unknown pull_kind '{pull_kind}'")

            # Check data_url if --with-data
            if args.with_data and s.get("data_url"):
                try:
                    fetch_url(s["data_url"], timeout=30)
                except Exception as de:
                    print(f"Warning: failed downloading data_url for {name}: {de}", file=sys.stderr)

            new_state[name] = s_state
            if status == "changed":
                changed_sources.append(s)
                print(f"{name}: changed {detail}".rstrip())
            else:
                print(f"{name}: unchanged")

        except Exception as e:
            failed_count += 1
            print(f"{name}: error {e}")

    # Write state file if at least one source succeeded or changed
    if failed_count < len(sources):
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(new_state, f, indent=2)
        except Exception as e:
            print(f"Error saving state file: {e}", file=sys.stderr)

    # Write review list if any sources changed
    if changed_sources:
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            review_file = state_dir / f"review-{today_str}.md"
            lines = [
                f"# Prompt Source Updates for Review — {today_str}",
                "",
                "The following sources have new updates available for review:",
                "",
            ]
            for cs in changed_sources:
                cname = cs.get("name", "unnamed")
                license_val = cs.get("license", "unknown")
                copy_ok_val = cs.get("copy_ok", "unknown")
                lines.append(f"## {cname}")
                lines.append(f"- License: {license_val}")
                lines.append(f"- Copy OK: {copy_ok_val}")
                lines.append("- ideas_only: rewrite in our words, never paste")
                lines.append("")

            review_file.write_text("\n".join(lines), encoding="utf-8")
        except Exception as e:
            print(f"Error writing review file: {e}", file=sys.stderr)

    if sources and failed_count == len(sources):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
