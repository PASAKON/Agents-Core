"""Pre-production verification for film 5 «ขายชื่อ» EP1.

Verifies:
1. docs/ops/briefs/ep5-plates-round1.json parses and contains all character faces, states, locations and props.
2. docs/scripts/ep5-ACT1.md, ep5-ACT2.md, ep5-ACT3.md pass tools/shotsheet_lint.py audit.
3. Dialogue diff between rendered shot sheets and docs/scripts/ep5-khaichue-EP1-SCRIPT-v1.md is empty.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from tools import build_shotsheet, shotsheet_lint


def _load_data(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ep5_plates_json_parses():
    plates_path = Path("docs/ops/briefs/ep5-plates-round1.json")
    assert plates_path.exists(), "plates json missing"
    plates = json.loads(plates_path.read_text(encoding="utf-8"))
    assert len(plates) >= 20
    for p in plates:
        assert "name" in p and "prompt" in p


def test_ep5_shotsheet_lint_passes_all_acts():
    acts = [
        ("1", Path("docs/scripts/ep5-ACT1.data.py"), Path("docs/scripts/ep5-ACT1.md")),
        ("2", Path("docs/scripts/ep5-ACT2.data.py"), Path("docs/scripts/ep5-ACT2.md")),
        ("3", Path("docs/scripts/ep5-ACT3.data.py"), Path("docs/scripts/ep5-ACT3.md")),
    ]

    for act_num, data_path, md_path in acts:
        assert data_path.exists(), f"{data_path} missing"
        d = _load_data(data_path)
        md_text = build_shotsheet.build(d, act_num)
        md_path.write_text(md_text, encoding="utf-8")
        assert shotsheet_lint.audit(md_path) == 0, f"Lint failed for {md_path}"


def test_ep5_dialogue_diff_against_script_is_empty():
    script_text = Path("docs/scripts/ep5-khaichue-EP1-SCRIPT-v1.md").read_text(encoding="utf-8")
    script_lines = {}
    cur = None
    for ln in script_text.splitlines():
        m = re.match(r"^### SHOT (\d+) ", ln)
        if m:
            cur = int(m.group(1))
            script_lines[cur] = []
            continue
        m = re.match(r'^\*\*บทพูด\*\* (\S+) `"(.+)"` — (.+)$', ln)
        if m and cur is not None:
            script_lines[cur].append((m.group(1), m.group(2)))

    all_sheet_lines = {}
    for act_num in ["1", "2", "3"]:
        md_path = Path(f"docs/scripts/ep5-ACT{act_num}.md")
        assert md_path.exists(), f"{md_path} missing"
        text = md_path.read_text(encoding="utf-8")
        cur = None
        for ln in text.splitlines():
            m = re.match(r"^### SHOT (\d+)\b", ln)
            if m:
                cur = int(m.group(1))
                all_sheet_lines[cur] = []
                continue
            m = re.match(r'^\*\*บทพูด\*\* (\S+) `"(.+)"` — (.+)$', ln)
            if m and cur is not None:
                all_sheet_lines[cur].append((m.group(1), m.group(2)))

    assert len(all_sheet_lines) == 68
    assert len(script_lines) == 68

    char_to_script = {
        "sri__face": "แม่ศรี",
        "ton__face": "ต้น",
        "boy__face": "บอย",
        "fon__face": "ฝน",
        "collector__face": "คนเก็บค่าแผง",
        "friend__face": "เพื่อนต้น",
    }

    for n in range(1, 69):
        s_lines = script_lines[n]
        a_lines = all_sheet_lines[n]
        assert len(s_lines) == len(a_lines), f"Shot {n} line count mismatch: {len(s_lines)} vs {len(a_lines)}"
        for (s_who, s_text), (a_who, a_text) in zip(s_lines, a_lines):
            assert s_text == a_text, f"Shot {n} dialogue mismatch: '{s_text}' != '{a_text}'"
            assert char_to_script[a_who] == s_who, f"Shot {n} speaker mismatch: {char_to_script[a_who]} != {s_who}"
