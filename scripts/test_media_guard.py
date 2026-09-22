import subprocess
import os
from pathlib import Path
import yaml
import pytest

def run_guard(tmp_path, policy_path):
    # Determine path to the script
    script_path = Path(__file__).resolve().parent / "media_guard.py"

    result = subprocess.run(
        ["python", str(script_path), "--policy", str(policy_path), "--repo", str(tmp_path)],
        capture_output=True,
        text=True
    )
    return result

def test_media_guard(tmp_path):
    # Initialize a throwaway repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)

    # Make initial commit so we have a HEAD, this avoids issues with some git commands
    (tmp_path / "README.md").write_text("Init")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True, capture_output=True)

    # Create policy
    policy = {
        "media_guard": {
            "max_bytes": 1048576, # 1 MiB
            "extensions": ["mp4", "png", "txt"], # txt included to test extension ignore properly later
            "allow": ["docs/**"]
        }
    }
    policy_path = tmp_path / "policy.yaml"
    with open(policy_path, "w") as f:
        yaml.dump(policy, f)

    # Test: small png passes
    small_png = tmp_path / "small.png"
    small_png.write_bytes(b"0" * 1024)
    subprocess.run(["git", "add", "small.png"], cwd=tmp_path, check=True, capture_output=True)

    res = run_guard(tmp_path, policy_path)
    assert res.returncode == 0
    assert not res.stdout.strip()

    # 2 MiB mp4 fails with exit 1 and the message
    large_mp4 = tmp_path / "large.mp4"
    large_mp4.write_bytes(b"0" * (2 * 1024 * 1024))
    subprocess.run(["git", "add", "large.mp4"], cwd=tmp_path, check=True, capture_output=True)

    res = run_guard(tmp_path, policy_path)
    assert res.returncode == 1
    assert "media_guard: large.mp4 2.0 MB > 1.0 MB — keep media out of git (ADR 0030); put it in the task's out/ folder or Drive" in res.stdout

    # Unstage large_mp4 for next test
    subprocess.run(["git", "restore", "--staged", "large.mp4"], cwd=tmp_path, check=True, capture_output=True)

    # 2 MiB .MP4 upper-case fails
    upper_mp4 = tmp_path / "upper.MP4"
    upper_mp4.write_bytes(b"0" * (2 * 1024 * 1024))
    subprocess.run(["git", "add", "upper.MP4"], cwd=tmp_path, check=True, capture_output=True)

    res = run_guard(tmp_path, policy_path)
    assert res.returncode == 1
    assert "media_guard: upper.MP4 2.0 MB > 1.0 MB" in res.stdout

    subprocess.run(["git", "restore", "--staged", "upper.MP4"], cwd=tmp_path, check=True, capture_output=True)

    # 2 MiB mp4 under an allowed glob passes
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    allowed_mp4 = docs_dir / "allowed.mp4"
    allowed_mp4.write_bytes(b"0" * (2 * 1024 * 1024))
    subprocess.run(["git", "add", "docs/allowed.mp4"], cwd=tmp_path, check=True, capture_output=True)

    res = run_guard(tmp_path, policy_path)
    assert res.returncode == 0

    subprocess.run(["git", "restore", "--staged", "docs/allowed.mp4"], cwd=tmp_path, check=True, capture_output=True)

    # Modify policy to make txt not an extension
    policy["media_guard"]["extensions"] = ["mp4", "png"]
    with open(policy_path, "w") as f:
        yaml.dump(policy, f)

    # 2 MiB .txt passes (not media)
    large_txt = tmp_path / "large.txt"
    large_txt.write_bytes(b"0" * (2 * 1024 * 1024))
    subprocess.run(["git", "add", "large.txt"], cwd=tmp_path, check=True, capture_output=True)

    res = run_guard(tmp_path, policy_path)
    assert res.returncode == 0

    subprocess.run(["git", "restore", "--staged", "large.txt"], cwd=tmp_path, check=True, capture_output=True)

    # Thai filename with a space fails correctly
    thai_mp4 = tmp_path / "ทดสอบ space.mp4"
    thai_mp4.write_bytes(b"0" * (2 * 1024 * 1024))
    subprocess.run(["git", "add", "ทดสอบ space.mp4"], cwd=tmp_path, check=True, capture_output=True)

    res = run_guard(tmp_path, policy_path)
    assert res.returncode == 1
    assert "media_guard: ทดสอบ space.mp4 2.0 MB > 1.0 MB" in res.stdout

    subprocess.run(["git", "restore", "--staged", "ทดสอบ space.mp4"], cwd=tmp_path, check=True, capture_output=True)

    # Deleted media file is not a violation
    # Commit the large_mp4 first by bypassing the check
    subprocess.run(["git", "add", "large.mp4"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add large mp4"], cwd=tmp_path, check=True, capture_output=True)

    subprocess.run(["git", "rm", "large.mp4"], cwd=tmp_path, check=True, capture_output=True)
    # The file is staged for deletion
    res = run_guard(tmp_path, policy_path)
    assert res.returncode == 0

    subprocess.run(["git", "commit", "-m", "Remove large mp4"], cwd=tmp_path, check=True, capture_output=True)

    # Pure `git mv` of an already-committed large media file is not a violation
    subprocess.run(["git", "checkout", "HEAD^"], cwd=tmp_path, check=True, capture_output=True) # Go back to commit where large.mp4 exists
    subprocess.run(["git", "mv", "large.mp4", "large_renamed.mp4"], cwd=tmp_path, check=True, capture_output=True)

    res = run_guard(tmp_path, policy_path)
    assert res.returncode == 0
