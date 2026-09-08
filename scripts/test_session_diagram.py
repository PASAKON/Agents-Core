"""Tests for tools/session_diagram.py — the picture at the end of /session-worktree.

The renderer turns a session-tree JSON into a diagram-design-styled HTML/SVG
(and the 🌳 text tree). These pin the contract the skill relies on:

  1. accessible-SVG contract (role=img, prefixed title/desc, title first, no script)
  2. diagram-design's own self_check.py accepts the output (skipped if the
     external clone is not installed)
  3. every <rect> sits on the 4px grid
  4. the four node states render with their treatment + the counts line
  5. untrusted text is escaped and over-long titles are truncated
  6. the text tree matches the skill's format (markers, HERE, blockers, 📊)
  7. bad input raises
  8. the PNG scale respects Telegram's sendPhoto size cap
  9. the CLI writes the HTML and prints the diagram path

PNG rendering spawns Chrome; it runs only with SESSION_DIAGRAM_CHROME_TEST=1.

Run via:  .venv/bin/python scripts/test_session_diagram.py   (or pytest)
"""
from __future__ import annotations

import copy
import inspect
import io
import json
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import session_diagram as sd  # noqa: E402


def _session(mutate=None) -> sd.Session:
    data = copy.deepcopy(sd.SAMPLE)
    if mutate:
        mutate(data)
    return sd.Session(data)


def test_accessible_svg_contract():
    page, h = sd.render_html(_session())
    assert 'role="img"' in page
    assert 'aria-labelledby="session-tree-title session-tree-desc"' in page
    svg_start = page.index("<svg")
    title_at = page.index('<title id="session-tree-title">', svg_start)
    desc_at = page.index('<desc id="session-tree-desc">', svg_start)
    defs_at = page.index("<defs>", svg_start)
    assert title_at < desc_at < defs_at
    assert "<script" not in page
    assert h % 4 == 0
    assert "fonts.googleapis.com/css2" in page and "Noto+Sans+Thai" in page


def test_upstream_self_check_passes(tmp_path):
    p = Path(tmp_path) / "d.html"
    p.write_text(sd.render_html(_session())[0], encoding="utf-8")
    ok, msg = sd.self_check(p)
    assert ok, msg


def test_rects_on_4px_grid():
    page, _ = sd.render_html(_session())
    seen = 0
    for m in re.finditer(r'<rect x="(-?\d+)" y="(-?\d+)" width="(\d+)" height="(\d+)"', page):
        seen += 1
        for v in m.groups():
            assert int(v) % 4 == 0, m.group(0)
    assert seen > 10


def test_states_render_with_treatment_and_counts():
    page, _ = sd.render_html(_session())
    assert ">BLOCKED<" in page and "BLOCKED · รอ Chrome บน Contabo ยังไม่มี" in page
    assert "◀ HERE" in page
    assert 'stroke-dasharray="4,4"' in page      # blocked card
    assert 'stroke-dasharray="4,3"' in page      # todo card
    assert "2/6 DONE · 1 DOING · 2 TODO · 1 BLOCKED" in page
    assert "pinned 2724fd2 · v2.6.17" in page    # evidence sublabel
    assert "DEFINITION OF DONE" in page


def test_escaping_and_truncation():
    def mutate(d):
        d["nodes"][0]["title"] = "<b>x</b> & " + "ก" * 300
        d["entry_problem"] = "ยาว " * 80
    page, _ = sd.render_html(_session(mutate))
    assert "<b>x</b>" not in page and "&lt;b&gt;x&lt;/b&gt; &amp;" in page
    assert "…" in page
    serif_lines = page.count("font-size=\"24\"")
    assert 1 <= serif_lines <= 3


def test_tree_text_format():
    txt = sd.render_tree_text(_session())
    lines = txt.splitlines()
    assert lines[0] == "🌳 SESSION WORKTREE — 2026-09-08"
    assert lines[1].startswith("🎯 main: ")
    assert any(l.startswith("├─ ✅ #1  ⚙️ SETUP") for l in lines)
    assert any("⬅️ อยู่ตรงนี้" in l and "#2 " in l for l in lines)
    assert any(l.startswith("│  ├─ ✅ #2.1") for l in lines)
    assert any(l.startswith("└─ ⬜ #4  🏁 CLOSE") for l in lines)
    assert "📊 ✅ 2/6   🔄 1   ⬜ 2   🔴 1" in txt
    assert "🔴 BLOCKERS (1)" in txt and "• #3 — รอ Chrome บน Contabo ยังไม่มี" in txt
    assert "GH#" not in txt                        # issue 0 → no issue link


def test_bad_input_raises():
    for mutate in (
        lambda d: d["nodes"][0].__setitem__("status", "meh"),
        lambda d: d.__setitem__("nodes", []),
        lambda d: d.__setitem__("entry_problem", ""),
    ):
        try:
            _session(mutate)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_photo_scale_respects_telegram_cap():
    assert sd.photo_scale(2, 400) == 2
    assert sd.photo_scale(2, 4200) == 1           # 2 × (880 + 4200) > 10000
    assert sd.photo_scale(1, 9000) == 1


def test_cli_writes_html_and_prints_path(tmp_path):
    src = Path(tmp_path) / "s.json"
    src.write_text(json.dumps(sd.SAMPLE, ensure_ascii=False), encoding="utf-8")
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = sd.main([str(src), "--out-dir", str(tmp_path), "--basename", "t", "--print-tree", "--check"])
    out = buf.getvalue()
    assert rc == 0, out
    assert (Path(tmp_path) / "t.html").is_file()
    assert out.startswith("🌳 SESSION WORKTREE") and "\n---\n" in out
    assert out.rstrip().endswith(f"diagram: {Path(tmp_path) / 't.html'}")


def test_png_render_optional(tmp_path):
    if os.environ.get("SESSION_DIAGRAM_CHROME_TEST") != "1":
        return
    chrome = sd.find_chrome()
    assert chrome, "no chrome"
    p = Path(tmp_path) / "d.html"
    page, h = sd.render_html(_session())
    p.write_text(page, encoding="utf-8")
    png = sd.render_png(p, Path(tmp_path) / "d.png", h, 1, chrome)
    assert png and png.stat().st_size > 1000


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            if "tmp_path" in inspect.signature(fn).parameters:
                with tempfile.TemporaryDirectory() as tmp:
                    fn(Path(tmp))
            else:
                fn()
            print(f"  [PASS] {name}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  [FAIL] {name}: {exc!r}")
    print("OK" if not failures else f"{failures} FAILED")
    sys.exit(1 if failures else 0)
