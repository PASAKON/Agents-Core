from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.check_repo_boundaries import load_manifest, validate


def _manifest(**policy):
    return {
        "zones": {
            "source": {"lifecycle": "keep", "paths": ["src", "README.md"]},
            "legacy": {"lifecycle": "migrate", "paths": ["old.tsv"]},
        },
        "policy": {"new_root_file_patterns": ["*.tsv"], **policy},
    }


def test_current_repository_has_complete_unique_classification():
    manifest = load_manifest(Path("config/repository-boundaries.yaml"))
    tracked = {
        line.strip().replace("\\", "/").split("/", 1)[0]
        for line in subprocess.check_output(
            ["git", "ls-files", "--cached"], text=True
        ).splitlines()
        if line.strip()
    }
    # New files in the working tree are not in HEAD yet, so include the files
    # introduced by this boundary change explicitly during its first test run.
    tracked.update({"STRUCTURE.md"})
    report = validate(manifest, tracked)
    assert report["unclassified"] == []
    assert report["duplicates"] == []
    assert report["prohibited_new"] == []


def test_unclassified_top_level_path_is_reported():
    report = validate(_manifest(), {"src", "README.md", "surprise"})
    assert report["unclassified"] == ["surprise"]


def test_duplicate_classification_is_reported():
    manifest = _manifest()
    manifest["zones"]["docs"] = {"lifecycle": "keep", "paths": ["README.md"]}
    report = validate(manifest, {"src", "README.md", "old.tsv"})
    assert report["duplicates"] == ["README.md"]


def test_new_root_data_file_is_rejected_but_declared_legacy_is_allowed():
    report = validate(_manifest(), {"src", "README.md", "old.tsv", "new.tsv"})
    assert report["prohibited_new"] == ["new.tsv"]
    assert report["migration_backlog"] == ["old.tsv"]
