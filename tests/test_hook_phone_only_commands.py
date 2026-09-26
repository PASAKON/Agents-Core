"""scripts/hook-phone-only-commands.py -- Stop hook for the phone-only rule.

CEO ruling 2026-09-26: commands reach the CEO on the phone only (Run Inbox), so a
reply that hands him a `!` command is blocked and rewritten. Every case writes
its own transcript under tmp_path.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "hookphone", ROOT / "scripts" / "hook-phone-only-commands.py"
)
hookphone = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hookphone)


def _user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def _tool_result():
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}}


def _assistant(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": text}]}}


def _run(tmp_path, records, env=None, **payload):
    tp = tmp_path / "t.jsonl"
    tp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
                  encoding="utf-8")
    return hookphone.decide({"transcript_path": str(tp), **payload}, env=env or {})


def test_fenced_bang_command_blocks(tmp_path):
    out = _run(tmp_path, [_user("ลบให้หน่อย"), _assistant("รันเอง:\n```\n! python3 x.py --go\n```")])
    assert out and out["decision"] == "block"
    assert "! python3 x.py --go" in out["reason"]


def test_inline_bang_command_blocks(tmp_path):
    out = _run(tmp_path, [_user("q"), _assistant("พิมพ์ `! bash scripts/login.sh` ในแชท")])
    assert out and out["decision"] == "block"


def test_plain_line_bang_command_blocks(tmp_path):
    out = _run(tmp_path, [_user("q"), _assistant("ทำตามนี้\n! gh auth login\nแล้วบอกผม")])
    assert out and out["decision"] == "block"


def test_bang_before_a_tool_result_in_the_same_turn_still_blocks(tmp_path):
    out = _run(tmp_path, [_user("q"), _assistant("```\n! ls\n```"), _tool_result(),
                          _assistant("done")])
    assert out and out["decision"] == "block"


def test_bang_in_an_earlier_turn_is_ignored(tmp_path):
    out = _run(tmp_path, [_user("q1"), _assistant("```\n! ls\n```"), _user("q2"),
                          _assistant("ส่งการ์ด RUN-20260926-1900-abcd แล้ว")])
    assert out is None


def test_markdown_image_and_bare_mention_do_not_block(tmp_path):
    text = "![cover](a.png)\nห้ามยื่น `!` ในแชท\n```\n!= not a command\n![x](y)\n```"
    assert _run(tmp_path, [_user("q"), _assistant(text)]) is None


def test_stop_hook_active_never_blocks_twice(tmp_path):
    recs = [_user("q"), _assistant("```\n! ls\n```")]
    assert _run(tmp_path, recs, stop_hook_active=True) is None


def test_env_off_disables(tmp_path):
    recs = [_user("q"), _assistant("```\n! ls\n```")]
    assert _run(tmp_path, recs, env={"PHONE_ONLY_GUARD": "off"}) is None


def test_missing_transcript_fails_open():
    assert hookphone.decide({"transcript_path": "/nonexistent/t.jsonl"}, env={}) is None
