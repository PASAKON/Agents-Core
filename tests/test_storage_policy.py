import pytest
import yaml
from pathlib import Path
import tools.storage_policy as sp

def test_load_valid_policy(tmp_path):
    policy_path = Path(__file__).resolve().parent.parent / "config" / "storage-policy.yaml"
    data = sp.load(policy_path)
    assert isinstance(data, dict)
    assert "gauge" in data
    assert "tiers" in data

def test_load_invalid_yaml(tmp_path):
    p = tmp_path / "broken.yaml"
    p.write_text("a: b\n- c")
    with pytest.raises(sp.PolicyError, match="Failed to load yaml"):
        sp.load(p)

def test_load_root_not_mapping(tmp_path):
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b")
    with pytest.raises(sp.PolicyError, match="Root must be a mapping"):
        sp.load(p)

def test_load_missing_gauge(tmp_path):
    p = tmp_path / "missing_gauge.yaml"
    p.write_text("tiers: {}")
    with pytest.raises(sp.PolicyError, match="Missing key: gauge"):
        sp.load(p)

def test_load_gauge_invalid_order(tmp_path):
    p = tmp_path / "invalid_gauge.yaml"
    data = {
        "gauge": {"green": 10, "yellow": 20, "orange": 5, "red": 0},
        "tiers": {"HOT": [], "REBUILD": [], "COLD": [], "NEVER": []}
    }
    p.write_text(yaml.dump(data))
    with pytest.raises(sp.PolicyError, match="gauge must have green > yellow > orange > red"):
        sp.load(p)

def test_load_tiers_missing(tmp_path):
    p = tmp_path / "missing_tiers.yaml"
    data = {"gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0}}
    p.write_text(yaml.dump(data))
    with pytest.raises(sp.PolicyError, match="Missing key: tiers"):
        sp.load(p)

def test_load_tiers_invalid_keys(tmp_path):
    p = tmp_path / "invalid_tiers.yaml"
    data = {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {"HOT": [], "REBUILD": [], "WARM": [], "NEVER": []}
    }
    p.write_text(yaml.dump(data))
    with pytest.raises(sp.PolicyError, match="tiers must be exactly"):
        sp.load(p)

def test_load_rebuild_missing_glob(tmp_path):
    p = tmp_path / "bad_rebuild.yaml"
    data = {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {
            "HOT": [],
            "REBUILD": [{"rebuild": "npm"}],
            "COLD": [],
            "NEVER": []
        }
    }
    p.write_text(yaml.dump(data))
    with pytest.raises(sp.PolicyError, match="REBUILD entry missing glob"):
        sp.load(p)

def test_load_cold_missing_dest(tmp_path):
    p = tmp_path / "bad_cold.yaml"
    data = {
        "gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0},
        "tiers": {
            "HOT": [],
            "REBUILD": [{"glob": "a", "rebuild": "b"}],
            "COLD": [{"glob": "a"}],
            "NEVER": []
        }
    }
    p.write_text(yaml.dump(data))
    with pytest.raises(sp.PolicyError, match="COLD entry missing dest"):
        sp.load(p)

def test_band():
    policy = {"gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0}}
    assert sp.band(25, policy) == "green"
    assert sp.band(20, policy) == "green"
    assert sp.band(15, policy) == "yellow"
    assert sp.band(10, policy) == "yellow"
    assert sp.band(7, policy) == "orange"
    assert sp.band(5, policy) == "orange"
    assert sp.band(2, policy) == "red"
    assert sp.band(0, policy) == "red"

def test_classify_precedence():
    policy = {
        "tiers": {
            "NEVER": ["~/Desktop/**"],
            "HOT": ["~/MoonieXHQ/**"],
            "COLD": [{"glob": "~/Downloads/old/**", "dest": "x"}],
            "REBUILD": [{"glob": "**/__pycache__", "rebuild": "x"}]
        }
    }
    home = Path("/Users/test")
    # NEVER beats REBUILD
    assert sp.classify("/Users/test/Desktop/x/__pycache__", policy, home) == "NEVER"
    # REBUILD works elsewhere
    assert sp.classify("/Users/test/other/__pycache__", policy, home) == "REBUILD"
    
def test_classify_deep_match():
    policy = {
        "tiers": {
            "NEVER": [], "HOT": [], "COLD": [],
            "REBUILD": [{"glob": "**/node_modules", "rebuild": "x"}]
        }
    }
    home = Path("/Users/test")
    assert sp.classify("/a/b/c/node_modules", policy, home) == "REBUILD"
    
def test_classify_placeholder_skipped():
    policy = {
        "tiers": {
            "NEVER": [], "HOT": [],
            "COLD": [{"glob": "<work_root>/<task-id>/in/**", "dest": "x"}],
            "REBUILD": []
        }
    }
    home = Path("/Users/test")
    assert sp.classify("/work/123/in/file", policy, home) is None


def test_classify_node_modules():
    policy = {
        "tiers": {
            "NEVER": [], "HOT": ["~/MoonieXHQ/**"], "COLD": [],
            "REBUILD": [{"glob": "**/node_modules", "rebuild": "x"}]
        }
    }
    home = Path("/Users/test")
    assert sp.classify("/Users/test/MoonieXHQ/Projects/LungNote/Web/node_modules", policy, home) == "REBUILD"

def test_classify_venv():
    policy = {
        "tiers": {
            "NEVER": [], "HOT": ["~/MoonieXHQ/**"], "COLD": [],
            "REBUILD": [{"glob": "**/.venv", "rebuild": "x"}]
        }
    }
    home = Path("/Users/test")
    assert sp.classify("/Users/test/MoonieXHQ/Projects/Test/.venv", policy, home) == "REBUILD"

def test_classify_desktop_pycache():
    policy = {
        "tiers": {
            "NEVER": ["~/Desktop/**"], "HOT": [], "COLD": [],
            "REBUILD": [{"glob": "**/__pycache__", "rebuild": "x"}]
        }
    }
    home = Path("/Users/test")
    assert sp.classify("/Users/test/Desktop/project/__pycache__", policy, home) == "NEVER"

def test_classify_transcript_age():
    policy = {
        "tiers": {
            "NEVER": [], "REBUILD": [],
            "COLD": [{"glob": "~/.claude/projects/*/*.jsonl", "older_than_days": 7, "dest": "x"}],
            "HOT": ["~/.claude/projects/*/*.jsonl"]
        }
    }
    home = Path("/Users/test")
    # Age 3 -> HOT
    assert sp.classify("/Users/test/.claude/projects/p1/abc.jsonl", policy, home, age_days=3) == "HOT"
    # Age 10 -> COLD
    assert sp.classify("/Users/test/.claude/projects/p1/abc.jsonl", policy, home, age_days=10) == "COLD"
    # Age None -> HOT
    assert sp.classify("/Users/test/.claude/projects/p1/abc.jsonl", policy, home, age_days=None) == "HOT"

def test_classify_cold_when():
    policy = {
        "tiers": {
            "NEVER": [], "HOT": [], "REBUILD": [],
            "COLD": [{"glob": "<work_root>/<task-id>/in/**", "when": "task closed", "dest": "x"}]
        }
    }
    home = Path("/Users/test")
    assert sp.classify("/work/123/in/file", policy, home) is None

def test_load_invalid_hot_entry(tmp_path):
    p = tmp_path / "bad_hot.yaml"
    data = {"gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0}, "tiers": {"HOT": [{"a": "b"}], "REBUILD": [], "COLD": [], "NEVER": []}}
    p.write_text(yaml.dump(data))
    with pytest.raises(sp.PolicyError, match="HOT entries must be strings"):
        sp.load(p)

def test_load_empty_rebuild(tmp_path):
    p = tmp_path / "bad_rebuild.yaml"
    data = {"gauge": {"green": 20, "yellow": 10, "orange": 5, "red": 0}, "tiers": {"HOT": [], "REBUILD": [{"glob": "x", "rebuild": ""}], "COLD": [], "NEVER": []}}
    p.write_text(yaml.dump(data))
    with pytest.raises(sp.PolicyError, match="REBUILD entry missing or empty rebuild"):
        sp.load(p)

def test_load_negative_gauge(tmp_path):
    p = tmp_path / "bad_gauge.yaml"
    data = {"gauge": {"green": 20, "yellow": 10, "orange": -5, "red": -10}, "tiers": {"HOT": [], "REBUILD": [], "COLD": [], "NEVER": []}}
    p.write_text(yaml.dump(data))
    with pytest.raises(sp.PolicyError, match="gauge color .* must be >= 0"):
        sp.load(p)
