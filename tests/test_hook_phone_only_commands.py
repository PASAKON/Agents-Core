"""scripts/hook-phone-only-commands.py -- Stop hook for the phone-only rule.

CEO ruling 2026-09-26: commands reach the CEO on the phone only (Run Inbox), so a
reply that hands him a `!` command is blocked and rewritten. CEO ruling 2026-10-30:
a C-level or Project Head that asks him something in chat, with no question card in
the turn, is blocked too (`question_offenders`). Every case writes its own
transcript under tmp_path, and none reads a real session transcript.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.roles import c_level_roles  # noqa: E402

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


# --------------------------------------------------- question check (CEO 2026-10-30)
CARD = "Q-20261030-0412-abcd"
ASKS = [
    "If this is the right account, just reply with this message, edited if you want:",
    "จะให้ผม merge เลยไหมครับ",
    "เลือกแบบไหนดีครับ?",
    "ตอบ 1, 2 หรือ 3 ได้เลยครับ",
    "Should I post it now?",
    "ยืนยันไหมครับ",
]
CTO = {"CXO_ROLE": "cto"}


def _assistant_tools(text, *tool_uses):
    blocks = ([{"type": "text", "text": text}] if text else []) + [
        {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}
        for i, (name, inp) in enumerate(tool_uses)]
    return {"type": "assistant", "message": {"role": "assistant", "content": blocks}}


def test_question_roles_match_the_c_level_roster():
    assert hookphone.QUESTION_ROLES == (set(c_level_roles()) - {"coo"}) | {"project_head"}


@pytest.mark.parametrize("ask", ASKS)
def test_ask_in_chat_with_no_card_blocks(tmp_path, ask):
    out = _run(tmp_path, [_user("q"), _assistant(ask)], env=CTO)
    assert out and out["decision"] == "block"
    assert repr(ask.strip()) in out["reason"]


@pytest.mark.parametrize("role", sorted(hookphone.QUESTION_ROLES))
def test_every_question_role_is_checked(tmp_path, role):
    out = _run(tmp_path, [_user("q"), _assistant("Should I post it now?")], env={"CXO_ROLE": role})
    assert out and out["decision"] == "block"


def test_reason_is_the_ruling_verbatim(tmp_path):
    out = _run(tmp_path, [_user("q"), _assistant("Should I post it now?")], env=CTO)
    assert out["reason"] == (
        "Run-card rule (CEO 30 Oct 2026, every C-level and PH): your reply asks the CEO something "
        "in chat: 'Should I post it now?'. If it is his to decide (money, secrets, permanent "
        "deletion, speaking in his name, his accounts or devices, or a choice he asked to make), "
        "raise a question card now (mcp__org__ask_ceo, or tools/ask_run.py ask; on winbox or the "
        "Mac send one blocker letter to your Contabo C-level) and end with the card id. If it is "
        "yours to decide, decide and say what you chose. If the line is not a question to the "
        "CEO, end without changing anything.")


def test_ask_in_a_tool_turn_still_blocks_when_the_tool_is_not_a_card(tmp_path):
    recs = [_user("q"), _assistant_tools("Should I post it now?", ("Bash", {"command": "ls"})),
            _tool_result(), _assistant("done")]
    assert _run(tmp_path, recs, env=CTO)["decision"] == "block"


def test_both_checks_hit_gives_one_block_with_both_reasons(tmp_path):
    out = _run(tmp_path, [_user("q"), _assistant("Should I post it now?\n```\n! ls\n```")], env=CTO)
    assert out["reason"].count("Phone-only rule") == 1
    assert out["reason"].count("Run-card rule") == 1


def test_bang_check_still_runs_for_a_role_the_question_check_skips(tmp_path):
    recs = [_user("q"), _assistant("```\n! ls\n```")]
    out = _run(tmp_path, recs, env={"CXO_ROLE": "coo"})
    assert out and "Phone-only rule" in out["reason"] and "Run-card rule" not in out["reason"]


@pytest.mark.parametrize("ask", ASKS)
def test_ask_with_a_card_id_in_the_text_passes(tmp_path, ask):
    assert _run(tmp_path, [_user("q"), _assistant(f"{ask}\nการ์ด {CARD}")], env=CTO) is None


@pytest.mark.parametrize("card_id", ["QG-20261030-0412-abcd", "RUN-20261030-0412-abcd", "rq-0123abcd"])
def test_every_card_and_request_id_shape_passes(tmp_path, card_id):
    assert _run(tmp_path, [_user("q"), _assistant(f"Should I post it now? {card_id}")], env=CTO) is None


@pytest.mark.parametrize("tool", ["mcp__org__ask_ceo", "mcp__org__ask_run", "mcp__sompong__ask_ceo"])
def test_ask_tool_use_in_the_turn_passes(tmp_path, tool):
    recs = [_user("q"), _assistant_tools("Should I post it now?", (tool, {"question": "post?"}))]
    assert _run(tmp_path, recs, env=CTO) is None


@pytest.mark.parametrize("command", [
    "python3 tools/ask_run.py ask --question x --option a --option b --why y",
    "bash scripts/hub/org-python.sh tools/ask_run.py create --command 'ls' --host contabo --why y",
    "node scripts/relay-request.mjs open --host winbox",
])
def test_card_command_in_the_turn_passes(tmp_path, command):
    recs = [_user("q"), _assistant_tools("Should I post it now?", ("Bash", {"command": command}))]
    assert _run(tmp_path, recs, env=CTO) is None


@pytest.mark.parametrize("command", [
    "python3 tools/ask_run.py wait Q-20261030-0412-abcd --max-wait 60",
    "python3 tools/ask_run.py list",
    "grep -rn ask_run tools",
])
def test_a_command_that_raises_no_card_does_not_exempt(tmp_path, command):
    recs = [_user("q"), _assistant_tools("Should I post it now?", ("Bash", {"command": command}))]
    assert _run(tmp_path, recs, env=CTO)["decision"] == "block"


@pytest.mark.parametrize("tool", ["SendMessage", "mcp__org__send_to_cxo"])
def test_blocker_letter_in_the_turn_passes(tmp_path, tool):
    recs = [_user("q"), _assistant_tools("Should I post it now?", (tool, {"message": "blocker · urgent · x"}))]
    assert _run(tmp_path, recs, env={"CXO_ROLE": "project_head"}) is None


def test_letter_without_blocker_does_not_exempt(tmp_path):
    recs = [_user("q"), _assistant_tools("Should I post it now?", ("SendMessage", {"message": "fyi · done"}))]
    assert _run(tmp_path, recs, env=CTO)["decision"] == "block"


def test_card_tool_before_the_last_real_user_message_does_not_exempt(tmp_path):
    recs = [_user("q1"), _assistant_tools("", ("mcp__org__ask_ceo", {"question": "x"})), _user("q2"),
            _assistant("Should I post it now?")]
    assert _run(tmp_path, recs, env=CTO)["decision"] == "block"


@pytest.mark.parametrize("env", [{}, {"CXO_ROLE": "coo"}, {"CXO_ROLE": "developer"},
                                 {"CXO_ROLE": "cto", "CARD_GUARD": "off"}])
def test_out_of_scope_session_or_switch_off_passes(tmp_path, env):
    assert _run(tmp_path, [_user("q"), _assistant("Should I post it now?")], env=env) is None


def test_stop_hook_active_never_blocks_a_question_twice(tmp_path):
    assert _run(tmp_path, [_user("q"), _assistant("Should I post it now?")], env=CTO,
                stop_hook_active=True) is None


def test_phone_only_guard_off_still_switches_the_whole_hook_off(tmp_path):
    env = {"CXO_ROLE": "cto", "PHONE_ONLY_GUARD": "off"}
    assert _run(tmp_path, [_user("q"), _assistant("Should I post it now?")], env=env) is None


@pytest.mark.parametrize("text", [
    'CEO ถามว่า "ทำไมไม่ส่งมาใน RUN"',
    "CEO asked \u201cshould I post it now?\u201d and I did",
    "```\nShould I post it now?\nจะให้ผม merge เลยไหมครับ\n```",
    "> Should I post it now?",
    "ห้ามเขียนว่า `จะให้ผม merge เลยไหมครับ` ในแชท",
    "PH ตอบมาว่า merge แล้ว",
    "ยังไม่ได้เช็คว่า Chat เปิดได้ไหม",
    "ทำไมยังเกิดปัญหานี้ได้อีก",
    "PH ยืนยันด้วย log ว่าผ่าน",
    "Posted. The PR is #578 and CI is green.",
])
def test_text_that_is_not_a_question_to_the_ceo_passes(tmp_path, text):
    assert _run(tmp_path, [_user("q"), _assistant(text)], env=CTO) is None


@pytest.mark.parametrize("text", [
    "Do you want the long version?",
    "ผมโพสต์เลย แล้วคุณโอเคไหม?",
    "ขอให้คุณเลือก Option A หรือ B?",
    "รอคำตอบจากคุณ",
    "Please confirm the account.",
    "Let me know which one.",
    "Which account should it use?",
    "Is it OK to delete the branch?",
])
def test_other_asks_in_either_language_block(tmp_path, text):
    assert _run(tmp_path, [_user("q"), _assistant(text)], env=CTO)["decision"] == "block"


def test_ask_before_the_last_real_user_message_is_ignored(tmp_path):
    recs = [_user("q1"), _assistant("Should I post it now?"), _user("q2"), _assistant("Posted.")]
    assert _run(tmp_path, recs, env=CTO) is None


def test_ask_before_a_tool_result_in_the_same_turn_still_blocks(tmp_path):
    recs = [_user("q"), _assistant("Should I post it now?"), _tool_result(), _assistant("done")]
    assert _run(tmp_path, recs, env=CTO)["decision"] == "block"


# ------------------------------------------- CTO review fixes (false positives on real turns)
@pytest.mark.parametrize("text", [
    "| clip.mp4 | น้ำไหล ลุยได้ไหม? | 56 s |",                    # a table row holding a clip title
    "  | clip.mp4 | Should I post it now? | 56 s |",
    "ระหว่างนี้พี่ไม่ต้องทำอะไรครับ",                              # a statement, not a question
    "ไม่มีอะไรค้างครับ",
    "I've recorded your approval: up to 1,600 credits",
])
def test_review_false_positives_pass(tmp_path, text):
    assert _run(tmp_path, [_user("q"), _assistant(text)], env=CTO) is None


@pytest.mark.parametrize("text", [
    "จะเอาแบบไหนครับ",
    "พี่จะเอาอันไหน?",
    "this needs your approval",
    "This needs your go-ahead.",
    "| a | b |\nShould I post it now?",                           # only the table row is skipped
])
def test_review_asks_still_block(tmp_path, text):
    assert _run(tmp_path, [_user("q"), _assistant(text)], env=CTO)["decision"] == "block"
