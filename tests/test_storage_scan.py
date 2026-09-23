import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path
import pytest

import tools.storage_scan as ss

def test_scan_basic_tiers(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    # Policy mapping
    policy = {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {
            "HOT": ["~/Project/**"],
            "REBUILD": [{"glob": "**/node_modules", "rebuild": "npm ci"}],
            "COLD": [{"glob": "~/Downloads/old/**", "dest": "x"}],
            "NEVER": ["~/Pictures/**"]
        }
    }

    # Create structures
    project_dir = home / "Project"
    project_dir.mkdir(parents=True)

    # A HOT file
    (project_dir / "app.js").write_text("console.log('hi');" * 100)

    # A REBUILD dir inside HOT
    node_modules = project_dir / "node_modules"
    node_modules.mkdir()
    (node_modules / "lib.js").write_text("module.exports = {};" * 100)

    # A NEVER dir
    pictures = home / "Pictures"
    pictures.mkdir()
    (pictures / "vacation.jpg").write_text("fake image data" * 100)

    # A COLD dir
    old_downloads = home / "Downloads" / "old"
    old_downloads.mkdir(parents=True)
    (old_downloads / "archive.zip").write_text("zip data" * 100)

    # UNCLASSIFIED file
    (home / "random.txt").write_text("random" * 100)

    # Run scan without size_never
    res = ss.scan([str(home)], policy, home=home, size_never=False, now=time.time())

    assert res["tiers"]["NEVER"] is None
    assert res["tiers"]["HOT"] > 0
    assert res["tiers"]["REBUILD"] > 0
    assert res["tiers"]["COLD"] > 0
    assert res["tiers"]["UNCLASSIFIED"] > 0

    assert len(res["top"]["HOT"]) == 1
    assert res["top"]["HOT"][0]["path"] == str(project_dir)

    assert len(res["top"]["REBUILD"]) == 1
    assert res["top"]["REBUILD"][0]["path"] == str(node_modules)

    assert len(res["top"]["NEVER"]) == 1
    assert res["top"]["NEVER"][0]["path"] == str(pictures)
    assert res["top"]["NEVER"][0]["bytes"] is None

    # Run scan with size_never
    res2 = ss.scan([str(home)], policy, home=home, size_never=True, now=time.time())
    assert res2["tiers"]["NEVER"] is not None
    assert res2["tiers"]["NEVER"] > 0
    assert res2["top"]["NEVER"][0]["bytes"] is not None

def test_scan_symlinks(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    policy = {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {
            "HOT": ["~/Project/**"],
            "REBUILD": [],
            "COLD": [],
            "NEVER": []
        }
    }

    project_dir = home / "Project"
    project_dir.mkdir(parents=True)
    f = project_dir / "large.txt"
    f.write_text("large file data" * 1000)
    f_size = f.stat().st_blocks * 512

    # Create a symlink to Project
    link_dir = home / "ProjectLink"
    os.symlink(str(project_dir), str(link_dir))

    res = ss.scan([str(home)], policy, home=home, size_never=False, now=time.time())

    # Symlink shouldn't be descended into, so UNCLASSIFIED should just be the link itself
    link_st = os.lstat(str(link_dir))
    link_size = getattr(link_st, 'st_blocks', 0) * 512

    assert link_size <= res["tiers"]["UNCLASSIFIED"]
    assert home.stat().st_blocks * 512 <= res["tiers"]["UNCLASSIFIED"]
    assert res["tiers"]["HOT"] == f_size + (project_dir.stat().st_blocks * 512)

def test_scan_hardlinks(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    policy = {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {
            "HOT": ["~/**"],
            "REBUILD": [],
            "COLD": [],
            "NEVER": []
        }
    }

    f1 = home / "file1.txt"
    f1.write_text("same content" * 1000)

    f2 = home / "file2.txt"
    os.link(str(f1), str(f2))

    res = ss.scan([str(home)], policy, home=home, size_never=False, now=time.time())

    f_blocks = f1.stat().st_blocks * 512
    home_blocks = home.stat().st_blocks * 512

    # The file should only be counted once
    assert res["tiers"]["HOT"] == f_blocks + home_blocks

def test_scan_file_age(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    policy = {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {
            "HOT": ["~/transcripts/*.jsonl"],
            "COLD": [{"glob": "~/transcripts/*.jsonl", "older_than_days": 7, "dest": "x"}],
            "REBUILD": [],
            "NEVER": []
        }
    }

    transcripts = home / "transcripts"
    transcripts.mkdir()

    now = time.time()

    hot_file = transcripts / "recent.jsonl"
    hot_file.write_text("hot")
    os.utime(str(hot_file), (now - 3 * 24 * 3600, now - 3 * 24 * 3600))

    cold_file = transcripts / "old.jsonl"
    cold_file.write_text("cold")
    os.utime(str(cold_file), (now - 10 * 24 * 3600, now - 10 * 24 * 3600))

    res = ss.scan([str(home)], policy, home=home, size_never=False, now=now)

    assert res["tiers"]["HOT"] > 0
    assert res["tiers"]["COLD"] > 0

    cold_top = [x["path"] for x in res["top"]["COLD"]]
    assert str(cold_file) in cold_top

def test_scan_permission_error(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("Running as root, chmod 000 will not cause PermissionError")

    home = tmp_path / "home"
    home.mkdir()

    policy = {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {
            "HOT": ["~/**"],
            "REBUILD": [],
            "COLD": [],
            "NEVER": []
        }
    }

    unreadable = home / "unreadable"
    unreadable.mkdir()
    (unreadable / "secret.txt").write_text("secret")

    # Make it unreadable
    unreadable.chmod(0o000)

    try:
        res = ss.scan([str(home)], policy, home=home, size_never=False, now=time.time())
        assert res["errors"] > 0
    finally:
        unreadable.chmod(0o755)

def test_cli_subprocess(tmp_path):
    script = Path(__file__).resolve().parent.parent / "tools" / "storage_scan.py"

    cmd = [sys.executable, str(script), "--root", str(tmp_path), "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "tiers" in data
    assert "top" in data
    assert data["errors"] >= 0

    cmd = [sys.executable, str(script), "--root", str(tmp_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    assert result.returncode == 0
    assert "Scan complete" in result.stdout
    assert "HOT" in result.stdout
