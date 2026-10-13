"""tools/thai_inventory.py — kind split, load tiers, and the public/private output split."""
from __future__ import annotations

import json

from tools import thai_inventory as ti


def kinds(repo, rel, text):
    return ti.classify(repo, rel, text).kinds


def test_python_comment_docstring_and_string_are_told_apart():
    src = (
        '"""โมดูลนี้ทำอะไร"""\n'          # docstring → comment (translate)
        "# อธิบายโค้ด\n"                   # comment → translate
        "MSG = 'ข้อความถึงลูกค้า'\n"        # string literal → runtime_string (keep)
    )
    k = kinds("Agents-Core", "tools/x.py", src)
    assert k["comment"] == ti.thai("โมดูลนี้ทำอะไร") + ti.thai("อธิบายโค้ด")
    assert k["runtime_string"] == ti.thai("ข้อความถึงลูกค้า")


def test_js_line_and_block_comments_vs_strings():
    src = "// คอมเมนต์\nconst a = \"สวัสดี\"; /* บล็อก */\n"
    k = kinds("MoonieX-Console", "src/a.js", src)
    assert k["comment"] == ti.thai("คอมเมนต์บล็อก")
    assert k["runtime_string"] == ti.thai("สวัสดี")


def test_markdown_quote_wrapping_a_line_in_a_ceo_paragraph_is_a_ceo_quote():
    src = ('**Why.** CEO 2026-09-29: "ทดสอบด้วยการใช้ worker จาก เจ้าอื่น ... เพื่อประหยัด\n'
           'token ของ Claude". Every plan is paid monthly.\n\n'
           "ย่อหน้านี้เป็นคำอธิบายภายใน\n")
    k = kinds("Agents-Core", "docs/x.md", src)
    assert k["ceo_quote"] == ti.thai("ทดสอบด้วยการใช้ worker จาก เจ้าอื่น ... เพื่อประหยัดtoken ของ")
    assert k["doc"] == ti.thai("ย่อหน้านี้เป็นคำอธิบายภายใน")


def test_blockquote_under_a_ceo_heading_is_the_ceos_words():
    src = "## Rule (CEO 2026-09-18)\n\n> \"ส่วน Worker ให้เรียนรู้ไป\"\n"
    assert kinds("Agents-Core", "roles/tester.md", src) == {"ceo_quote": ti.thai("ส่วนให้เรียนรู้ไป")}


def test_skill_description_keeps_trigger_phrases_and_flags_plain_thai():
    src = ("---\nname: X\ndescription: \"Do X. Trigger on \\\"ตรวจคลิป\\\", 'ซับขึ้น' "
           "and อธิบาย\"\n---\n\n# Body\n\nเนื้อหา skill\n")
    row = ti.classify("Agents-Core", ".claude/skills/X/SKILL.md", src)
    assert row.kinds["trigger_phrase"] == ti.thai("ตรวจคลิปซับขึ้น")
    assert row.kinds["always_loaded"] == ti.thai("อธิบาย")
    assert row.kinds["skill_body"] == ti.thai("เนื้อหา skill")
    assert row.desc_thai == ti.thai("ตรวจคลิปซับขึ้นอธิบาย")


def test_tiers_follow_what_the_launchers_inject():
    assert ti.tier_of("Agents-Core", "roles/cto.md") == "T0_session"
    assert ti.tier_of("Agents-Core", "roles/developer.md") == "T0_worker"
    assert ti.tier_of("Agents-Rules", "roles/cfo.md") == "T3_demand"  # not injected
    assert ti.tier_of("MoonieX-ClaudeFlow", "CLAUDE.md") == "T0_session"
    assert ti.tier_of("Agents-Memory", "MEMORY.md") == "T0_session"
    assert ti.tier_of("Agents-Rules", "IRON-RULES.md") == "T1_start"
    assert ti.tier_of("Agents-Core", ".claude/skills/X/SKILL.md") == "T2_trigger"
    assert ti.tier_of("Agents-Core", "docs/plans/x.md") == "T3_demand"


def test_test_files_and_user_facing_paths_are_kept():
    assert kinds("Agents-Core", "tests/test_x.py", "# ไทย\nx = 'ไทย'\n") == {"test_fixture": 6}
    k = kinds("Agents-Core", "docs/promo/caption.md", "แคปชั่นโพสต์\n")
    assert set(k) == {"user_facing"}


def test_totals_add_up_for_every_file():
    for rel, src in [("a.md", "ไทย \"คำพูด\" «ชื่อ»\n"), ("b.py", "x = 1  # ไทย\n"),
                     ("c.sh", "echo 'ไทย' # คอมเมนต์\n"), ("d.json", '{"k": "ไทย"}')]:
        row = ti.classify("Agents-Core", rel, src)
        assert sum(row.kinds.values()) == row.thai
        assert row.translate + row.keep == row.thai


def test_main_writes_public_rows_and_keeps_private_paths_out(tmp_path):
    pub = tmp_path / "Agents-Core"
    priv = tmp_path / "Secret-Repo"
    for d in (pub, priv):
        (d / "docs").mkdir(parents=True)
    (pub / "docs" / "a.md").write_text("เอกสารภายใน\n", encoding="utf-8")
    (priv / "docs" / "hidden-name.md").write_text("เอกสารลับ\n", encoding="utf-8")
    out, detail = tmp_path / "out", tmp_path / "detail"
    rc = ti.main(["--root", str(pub), "--root", str(priv), "--public", "Agents-Core",
                  "--out", str(out), "--detail-out", str(detail)])
    assert rc == 0
    rows = [json.loads(line) for line in (out / "rows.jsonl").read_text().splitlines()]
    assert [r["path"] for r in rows] == ["docs/a.md"]
    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert "hidden-name" not in summary and "Secret-Repo" in summary
    private = (detail / "rows-private.jsonl").read_text(encoding="utf-8")
    assert "hidden-name.md" in private
