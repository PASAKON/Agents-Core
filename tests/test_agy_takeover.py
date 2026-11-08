"""Unit tests for Cross-Host Claude Code -> AGY Takeover (`tools/agy_takeover.py`)."""
from __future__ import annotations

from pathlib import Path

from tools import agy_takeover


def test_format_handoff_markdown_includes_brief_mailbox_turns_and_skills(tmp_path):
    sample = {
        "host": "contabo",
        "uuid": "88d0d421-625d-4075-ab2b-fdc03511068d",
        "short_id": "3511068d",
        "kind": "project_head",
        "role_label": "project_head-3511068d",
        "project": "CnDrama",
        "owner": "cxo:cmo:fresh",
        "cwd": "/opt/MoonieXHQ/Agents/Core",
        "git_branch": "main",
        "quota_stopped": True,
        "last_ts": "2026-11-01T13:22:27Z",
        "brief": "# PH brief: CnDrama\nWrite EP02 script.",
        "drained_mailbox": ["[RUN-INBOX] : RUN-20261101-1157-77ce FAILED E_EXIT_NONZERO"],
        "recent_turns": [
            {"role": "user", "text": "Start EP02", "ts": "2026-11-01T13:00:00Z"},
            {"role": "assistant", "text": "You've hit your weekly limit", "ts": "2026-11-01T13:22:27Z"},
        ],
        "resolved_skills": [
            {"name": "CMO_Procedure_Colab_DirectRender", "path": "/opt/MoonieXHQ/Agents/Core/.claude/skills/CMO_Procedure_Colab_DirectRender/SKILL.md"}
        ],
    }
    saved = agy_takeover.save_handoff_bundle(sample, takeover_dir=tmp_path)
    text = saved.read_text(encoding="utf-8")
    assert "# Emergency AGY Takeover Brief: CnDrama" in text
    assert "CMO_Procedure_Colab_DirectRender" in text
    assert "RUN-20261101-1157-77ce FAILED" in text
    assert "Write EP02 script." in text
    assert (tmp_path / "latest-handoff.md").read_text(encoding="utf-8") == text


def test_resolve_local_skill_paths_finds_real_claude_skills():
    resolved = agy_takeover.resolve_local_skill_paths(["session-open", "NON_EXISTENT_SKILL_XYZ"])
    names = [r["name"] for r in resolved]
    assert "session-open" in names
    assert "NON_EXISTENT_SKILL_XYZ" not in names
    assert Path(resolved[0]["path"]).is_file()
