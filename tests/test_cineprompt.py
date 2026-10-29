"""
tests/test_cineprompt.py — Tests for cinematic prompt library tools:
- scripts/pick.py (list, find, show, lint on real library, error detection on temp copies)
- scripts/update_sources.py (urllib monkeypatched, state transitions, review file generation)
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "CMO_Knowledge_CinematicPrompts"
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
PROMPTS_DIR = REFERENCES_DIR / "prompts"
SOURCES_JSON = REFERENCES_DIR / "sources.json"
SOURCES_MD = REFERENCES_DIR / "SOURCES.md"
PICK_PY = SCRIPTS_DIR / "pick.py"
UPDATE_SOURCES_PY = SCRIPTS_DIR / "update_sources.py"


# ---------------------------------------------------------------------------
# Tests for SKILL.md and sources.json
# ---------------------------------------------------------------------------


def test_skill_md_frontmatter_and_body():
    assert SKILL_MD.exists(), "SKILL.md must exist"
    content = SKILL_MD.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Frontmatter parsing
    assert content.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    parts = content.split("---", 2)
    assert len(parts) >= 3, "Frontmatter must be enclosed by ---"
    fm = yaml.safe_load(parts[1])

    assert fm.get("name") == "CMO_Knowledge_CinematicPrompts"
    assert fm.get("kind") == "knowledge"
    assert fm.get("owner") == "CMO"
    assert fm.get("verified") == "2026-10-29"
    assert fm.get("refresh_after") == "2026-11-29"

    desc = fm.get("description", "")
    assert desc.startswith("KNOWLEDGE — ")
    assert len(desc) <= 350, f"Description too long ({len(desc)} > 350)"

    # Trigger words
    for kw in ["cinematic prompt", "B-roll prompt", "prompt library", "หา prompt", "prompt หนังสั้น", "ILAG prompt"]:
        assert kw in desc, f"Missing trigger keyword: {kw}"

    # Body lines <= 150
    body = parts[2].strip()
    body_lines = body.splitlines()
    assert len(body_lines) <= 150, f"Body has {len(body_lines)} lines (> 150)"

    # Mandatory body elements
    assert "66" in body
    assert "pick.py list" in body
    assert "pick.py find" in body
    assert "pick.py show" in body
    assert "pick.py lint" in body
    assert "CMO_Standard_Film_PromptFormat" in body
    assert "CMO_Knowledge_Seedance2.5_Higgsfield" in body
    assert "CMO_Knowledge_Wan3.0_TopView" in body
    assert "CMO_Knowledge_Flow_Omni1.1" in body
    assert "CMO_Gate_Flow_Omni1.1_FilmQC" in body
    assert "update_sources.py" in body
    assert "## Field notes" in body


def test_sources_json_contract():
    assert SOURCES_JSON.exists(), "sources.json must exist"
    with open(SOURCES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 4
    names = [s["name"] for s in data]
    assert "jnMetaCode/ai-shortfilm-prompts" in names
    assert "GokuScraper/seedance-2-prompts-datasets" in names
    assert "imagineVid/Awesome-wan-3-0-prompts-and-skills" in names
    assert "Rapidata/awesome-text2video-prompts" in names


def test_sources_md_exists():
    assert SOURCES_MD.exists(), "SOURCES.md must exist"
    text = SOURCES_MD.read_text(encoding="utf-8")
    assert "Idea Sources and Licensing Record" in text


# ---------------------------------------------------------------------------
# Tests for pick.py
# ---------------------------------------------------------------------------


def test_pick_list_real_library():
    result = subprocess.run(
        [sys.executable, str(PICK_PY), "list", "--dir", str(PROMPTS_DIR)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"pick.py list failed: {result.stderr}"
    output = result.stdout
    assert "Total entries: 66" in output
    assert "broll: 24" in output
    assert "movie: 22" in output
    assert "shortfilm: 20" in output
    assert "seedance-2.5:" in output
    assert "wan-3.0:" in output
    assert "flow-omni-1.1:" in output
    assert "any:" in output


def test_pick_find_real_library():
    # 1. Basic find by job
    result = subprocess.run(
        [sys.executable, str(PICK_PY), "find", "--job", "broll", "--dir", str(PROMPTS_DIR)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    lines = [ln for ln in result.stdout.strip().split("\n") if ln]
    assert len(lines) == 24
    assert any("broll-product-01" in ln for ln in lines)

    # 2. Find with model filter: model "any" in library matches specific model query
    result_seedance = subprocess.run(
        [
            sys.executable,
            str(PICK_PY),
            "find",
            "--job",
            "broll",
            "--model",
            "seedance-2.5",
            "--dir",
            str(PROMPTS_DIR),
        ],
        capture_output=True,
        text=True,
    )
    assert result_seedance.returncode == 0
    sd_lines = [ln for ln in result_seedance.stdout.strip().split("\n") if ln]
    # broll-product-01 is seedance-2.5, broll-product-04 is 'any'
    assert any("broll-product-01" in ln for ln in sd_lines)
    assert any("broll-product-04" in ln for ln in sd_lines)

    # 3. Find with style, aspect, max-seconds, and text
    result_filter = subprocess.run(
        [
            sys.executable,
            str(PICK_PY),
            "find",
            "--job",
            "movie",
            "--style",
            "thriller",
            "--aspect",
            "16:9",
            "--max-seconds",
            "8",
            "--text",
            "mirror",
            "--dir",
            str(PROMPTS_DIR),
        ],
        capture_output=True,
        text=True,
    )
    assert result_filter.returncode == 0
    assert "movie-thriller-03" in result_filter.stdout


def test_pick_show_real_library():
    # Real entry
    result = subprocess.run(
        [sys.executable, str(PICK_PY), "show", "broll-product-01", "--dir", str(PROMPTS_DIR)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    out = result.stdout
    assert "6s · 1080p · 9:16 · ONE CONTINUOUS TAKE" in out
    assert "Negatives: distorted glass, wobbling bottle" in out
    assert "Use when: Hero luxury skincare product showcase for vertical social reels." in out
    assert "Source: rapidata-text2video" in out
    assert "License: Apache-2.0" in out

    # Non-existent entry
    result_bad = subprocess.run(
        [sys.executable, str(PICK_PY), "show", "non-existent-id-999", "--dir", str(PROMPTS_DIR)],
        capture_output=True,
        text=True,
    )
    assert result_bad.returncode == 1
    assert "not found" in result_bad.stderr.lower()


def test_pick_lint_real_library():
    result = subprocess.run(
        [sys.executable, str(PICK_PY), "lint", str(PROMPTS_DIR)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Lint failed on real library:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    assert "Lint PASSED: 66 entries checked, 0 errors." in result.stdout


def test_pick_lint_planted_banned_word(tmp_path):
    # Copy broll.json and plant banned words
    with open(PROMPTS_DIR / "broll.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Plant banned words: "blush" and "หน้าแดง"
    data[0]["prompt"] += " She had a slight blush on her cheeks."
    data[1]["title"] += " หน้าแดง"

    tmp_file = tmp_path / "broll.json"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    result = subprocess.run(
        [sys.executable, str(PICK_PY), "lint", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Lint FAILED" in result.stderr
    assert "blush" in result.stderr
    assert "หน้าแดง" in result.stderr


def test_pick_lint_duplicate_id(tmp_path):
    with open(PROMPTS_DIR / "broll.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Make second item duplicate the first id
    data[1]["id"] = data[0]["id"]

    tmp_file = tmp_path / "broll.json"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    result = subprocess.run(
        [sys.executable, str(PICK_PY), "lint", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Lint FAILED" in result.stderr
    assert "duplicate id" in result.stderr


def test_pick_lint_invalid_seconds_and_aspect(tmp_path):
    with open(PROMPTS_DIR / "broll.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Invalid seconds (out of 4-15 range)
    data[0]["seconds"] = 25
    # 2. Missing aspect in first line of prompt
    data[1]["prompt"] = "First line without any aspect ratio\nSecond line 16:9"

    tmp_file = tmp_path / "broll.json"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    result = subprocess.run(
        [sys.executable, str(PICK_PY), "lint", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "seconds must be between 4 and 15" in result.stderr
    assert "prompt first line does not contain aspect" in result.stderr


# ---------------------------------------------------------------------------
# Tests for update_sources.py
# ---------------------------------------------------------------------------


def make_mock_response(content_bytes):
    mock = MagicMock()
    mock.read.return_value = content_bytes
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = None
    return mock


def test_update_sources_dry_run(tmp_path):
    state_file = tmp_path / "state.json"
    result = subprocess.run(
        [
            sys.executable,
            str(UPDATE_SOURCES_PY),
            "--sources",
            str(SOURCES_JSON),
            "--state",
            str(state_file),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "DRY-RUN: Source check plan" in result.stdout
    assert "jnMetaCode/ai-shortfilm-prompts" in result.stdout
    assert not state_file.exists()


def test_update_sources_runs(tmp_path, monkeypatch):
    state_file = tmp_path / "updates" / "state.json"

    # Sample mock responses for the 4 sources in sources.json
    git_commits = json.dumps([{"sha": "c0ffee1234567890", "commit": {"message": "Update"}}]).encode("utf-8")
    hf_dataset_1 = json.dumps({"id": "GokuScraper/seedance-2-prompts-datasets", "lastModified": "2026-10-29T10:00:00.000Z"}).encode("utf-8")
    json_prompts = json.dumps([{"id": "p1", "prompt": "test 1"}, {"id": "p2", "prompt": "test 2"}]).encode("utf-8")
    hf_dataset_2 = json.dumps({"id": "Rapidata/awesome-text2video-prompts", "lastModified": "2026-10-29T11:00:00.000Z"}).encode("utf-8")

    def mock_urlopen(req, timeout=30):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.github.com" in url:
            return make_mock_response(git_commits)
        elif "GokuScraper" in url:
            return make_mock_response(hf_dataset_1)
        elif "imagineVid" in url:
            return make_mock_response(json_prompts)
        elif "Rapidata" in url:
            return make_mock_response(hf_dataset_2)
        raise urllib.error.URLError(f"Unexpected URL: {url}")

    # Patch urllib in the update_sources module when running in-process or via import
    sys.path.insert(0, str(SCRIPTS_DIR))
    import update_sources

    # RUN 1: First run on clean state -> all sources are 'changed'
    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "update_sources.py",
                "--sources",
                str(SOURCES_JSON),
                "--state",
                str(state_file),
            ],
        )
        # Capture stdout
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            with pytest.raises(SystemExit) as exc_info:
                update_sources.main()
            assert exc_info.value.code == 0

        out1 = stdout_buf.getvalue()
        assert "jnMetaCode/ai-shortfilm-prompts: changed" in out1
        assert "GokuScraper/seedance-2-prompts-datasets: changed" in out1
        assert "imagineVid/Awesome-wan-3-0-prompts-and-skills: changed" in out1
        assert "Rapidata/awesome-text2video-prompts: changed" in out1

        # Check state file created
        assert state_file.exists()
        with open(state_file, "r", encoding="utf-8") as sf:
            state_data = json.load(sf)
        assert "jnMetaCode/ai-shortfilm-prompts" in state_data
        assert state_data["jnMetaCode/ai-shortfilm-prompts"]["marker"] == "c0ffee1234567890"

        # Check review file created
        review_files = list(state_file.parent.glob("review-*.md"))
        assert len(review_files) == 1
        review_content = review_files[0].read_text(encoding="utf-8")
        assert "jnMetaCode/ai-shortfilm-prompts" in review_content
        assert "ideas_only: rewrite in our words, never paste" in review_content

    # RUN 2: Second run with identical data -> all sources are 'unchanged'
    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "update_sources.py",
                "--sources",
                str(SOURCES_JSON),
                "--state",
                str(state_file),
            ],
        )
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            with pytest.raises(SystemExit) as exc_info:
                update_sources.main()
            assert exc_info.value.code == 0

        out2 = stdout_buf.getvalue()
        assert "jnMetaCode/ai-shortfilm-prompts: unchanged" in out2
        assert "GokuScraper/seedance-2-prompts-datasets: unchanged" in out2
        assert "imagineVid/Awesome-wan-3-0-prompts-and-skills: unchanged" in out2
        assert "Rapidata/awesome-text2video-prompts: unchanged" in out2

    # RUN 3: One source raises an error -> error line printed, rest still processed
    def mock_urlopen_one_fail(req, timeout=30):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.github.com" in url:
            raise urllib.error.URLError("GitHub API rate limit exceeded")
        return mock_urlopen(req, timeout=timeout)

    with patch("urllib.request.urlopen", side_effect=mock_urlopen_one_fail):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "update_sources.py",
                "--sources",
                str(SOURCES_JSON),
                "--state",
                str(state_file),
            ],
        )
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            with pytest.raises(SystemExit) as exc_info:
                update_sources.main()
            # Still exits 0 because not all sources failed
            assert exc_info.value.code == 0

        out3 = stdout_buf.getvalue()
        assert "jnMetaCode/ai-shortfilm-prompts: error" in out3
        assert "GokuScraper/seedance-2-prompts-datasets: unchanged" in out3
        assert "imagineVid/Awesome-wan-3-0-prompts-and-skills: unchanged" in out3
        assert "Rapidata/awesome-text2video-prompts: unchanged" in out3

    # RUN 4: All sources fail -> exits with 1
    def mock_urlopen_all_fail(req, timeout=30):
        raise urllib.error.URLError("Network unreachable")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen_all_fail):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "update_sources.py",
                "--sources",
                str(SOURCES_JSON),
                "--state",
                str(state_file),
            ],
        )
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            with pytest.raises(SystemExit) as exc_info:
                update_sources.main()
            assert exc_info.value.code == 1

