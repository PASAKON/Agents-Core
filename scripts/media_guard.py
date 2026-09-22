import argparse
import fnmatch
import sys
import subprocess
from pathlib import Path
import yaml

def get_staged_files(repo_path: Path):
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AM", "-M", "-z"],
        cwd=repo_path,
        capture_output=True,
        check=True
    )
    if not result.stdout:
        return []

    files = result.stdout.split(b'\x00')
    return [f.decode('utf-8') for f in files if f]

def get_staged_size(repo_path: Path, filepath: str) -> int:
    result = subprocess.run(
        ["git", "cat-file", "-s", f":{filepath}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True
    )
    return int(result.stdout.strip())

def main():
    parser = argparse.ArgumentParser(description="Guard to prevent large media files from being committed.")

    default_policy_path = Path(__file__).resolve().parent.parent / "config" / "storage-policy.yaml"
    parser.add_argument("--policy", type=Path, default=default_policy_path, help="Path to storage policy YAML")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Path to git repository")

    args = parser.parse_args()

    with open(args.policy, "r", encoding="utf-8") as f:
        policy = yaml.safe_load(f)

    media_guard = policy.get("media_guard", {})
    max_bytes = media_guard.get("max_bytes", 1048576)
    extensions = {ext.lower() for ext in media_guard.get("extensions", [])}
    allow_globs = media_guard.get("allow", [])

    max_mb = max_bytes / (1024 * 1024)

    staged_files = get_staged_files(args.repo)

    violations = False

    for filepath in staged_files:
        ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ""
        if ext not in extensions:
            continue

        size = get_staged_size(args.repo, filepath)

        if size > max_bytes:
            is_allowed = False
            for glob in allow_globs:
                if fnmatch.fnmatch(filepath, glob):
                    is_allowed = True
                    break

            if not is_allowed:
                size_mb = size / (1024 * 1024)
                print(f"media_guard: {filepath} {size_mb:.1f} MB > {max_mb:.1f} MB — keep media out of git (ADR 0030); put it in the task's out/ folder or Drive")
                violations = True

    if violations:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
