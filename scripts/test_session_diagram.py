"""Tests for tools/session_diagram.py — the session map behind /session-worktree.

The map is a left→right picture of a session (START → goal blocks with task
checklists → dependent goals; separate lines as separate rows; detours that
return or park), kept in one JSON per session and patched between runs so the
model spends tokens only on what changed. These pin:

  1. map: files written, status text, stable basename = session id
  2. accessible-SVG contract (prefixed ids) and diagram-design's own
     self_check.py accepts the artifact page
  3. every <rect> sits on the 4px grid
  4. patch: set/add/evidence/here merge, auto-stamped times, run counter
  5. goal status inferred from tasks; times derived; here auto-advances
  6. refs (G2 / G2.3 / D1), unknown refs and dependency cycles raise
  7. detours render as DETOUR (return line) and PARKED (dead-end stub)
  8. untrusted text escaped, long text truncated
  9. tree text + status text formats
 10. artifact body has no document wrapper and carries both maps
 11. Telegram photo cap on the PNG scale

Clock is pinned with SESSION_DIAGRAM_NOW. PNG rendering (Chrome) only runs
with SESSION_DIAGRAM_CHROME_TEST=1.

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
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["SESSION_DIAGRAM_NOW"] = "2026-09-09T00:30"

from tools import session_diagram as sd  # noqa: E402

NOW = sd.now_local()


def _session(mutate=None) -> sd.Session:
    data = copy.deepcopy(sd.SAMPLE)
    if mutate:
        mutate(data)
    return sd.Session(data, session_id="t-0001")


@contextmanager
def _stdin(text: str):
    old = sys.stdin
    sys.stdin = io.StringIO(text)
    try:
        yield
    finally:
        sys.stdin = old


def _run(argv: list[str], stdin: str = "") -> tuple[int, str]:
    buf = io.StringIO()
    with _stdin(stdin), redirect_stdout(buf):
        rc = sd.main(argv)
    return rc, buf.getvalue()


def test_map_writes_files_and_status(tmp_path):
    rc, out = _run(["map", "--session", "t-0001", "--out-dir", str(tmp_path)], json.dumps(sd.SAMPLE))
    assert rc == 0, out
    for ext in ("json", "html", "artifact.html"):
        assert (Path(tmp_path) / f"t-0001.{ext}").is_file()
    assert out.startswith("📊 goals 1/4 · tasks 5/9 · 🔴 1 · ↪ 2 detours (1 parked)")
    assert "📍 G2.2 — goal map v2 ซ้าย→ขวา" in out
    assert "🔴 G4.1 — รอ CEO ตอบข้อ 3" in out
    assert "check: OK" in out and "artifact: " in out
    saved = json.loads((Path(tmp_path) / "t-0001.json").read_text(encoding="utf-8"))
    assert saved["runs"] == 1 and saved["here"] == "G2.2" and saved["session"] == "t-0001"


def test_accessible_contract_and_upstream_self_check(tmp_path):
    s = _session()
    body = sd.render_artifact_html(s, NOW)
    slug = "session-map"
    assert f'aria-labelledby="{slug}-title {slug}-desc"' in body
    assert f'<title id="{slug}-title">' in body and f'<desc id="{slug}-desc">' in body
    assert "<script" not in body
    p = Path(tmp_path) / "a.html"
    p.write_text(body, encoding="utf-8")
    ok, msg = sd.self_check(p)
    assert ok, msg


def test_rects_on_4px_grid():
    svg, _w, h = sd.render_map(_session(), NOW)
    assert h % 4 == 0
    seen = 0
    for m in re.finditer(r'<rect x="(-?\d+)" y="(-?\d+)" width="(\d+)" height="(\d+)"', svg):
        seen += 1
        for v in m.groups():
            assert int(v) % 4 == 0, m.group(0)
    assert seen > 20


def test_patch_merges_and_stamps_times():
    s = _session()
    changes = s.apply_patch(copy.deepcopy(sd.SAMPLE_PATCH), NOW)
    assert "G2.2 doing → done" in changes and "G2.3 todo → doing" in changes
    t2, t3 = s.ref("G2.2"), s.ref("G2.3")
    assert t2.status == "done" and t2.finished_at == "2026-09-09T00:30" and t2.started_at == "2026-09-09T00:10"
    assert t3.status == "doing" and t3.started_at == "2026-09-09T00:30" and not t3.finished_at
    assert t2.evidence == "c3d5d2b"
    assert (s.here_goal, s.here_task) == ("G2", 3)
    g3 = s.goal("G3")
    assert g3.tasks[-1].title == "แก้ SKILL.md เป็น map + patch" and g3.tasks[-1].n == 3
    assert g3.detours[-1].kind == "interrupt" and g3.detours[-1].id == "D3"
    assert s.goal("G4").status == "done" and s.goal("G4").times()[1] == "2026-09-09T00:30"


def test_goal_status_inferred_and_here_advances():
    s = _session()
    assert [g.status for g in s.goals] == ["done", "doing", "doing", "blocked"]
    assert s.goal("G1").times() == ("2026-09-08T22:30", "2026-09-08T22:42")
    s.apply_patch({"set": {"G2.2": "done"}}, NOW)          # no explicit here → moves to the goal
    assert (s.here_goal, s.here_task) == ("G2", None)
    s.apply_patch({"set": {"G2.3": "done", "G2": "done"}}, NOW)
    assert s.goal("G2").status == "done"
    assert s.here_goal == "G3" and s.here_task is None       # G3 is partly done → doing


def test_refs_and_errors():
    s = _session()
    assert isinstance(s.ref("G2.3"), sd.Task) and isinstance(s.ref("D1"), sd.Detour) and isinstance(s.ref("G2"), sd.Goal)
    for bad in ("G9", "G2.9", "D9"):
        try:
            s.ref(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad}")
    try:
        _session(lambda d: d["goals"][0].__setitem__("depends_on", ["G2"]))
    except ValueError as exc:
        assert "cycle" in str(exc)
    else:
        raise AssertionError("cycle not detected")
    try:
        s.apply_patch({"set": {"G2.1": "meh"}}, NOW)
    except ValueError:
        pass
    else:
        raise AssertionError("bad status accepted")


def test_detours_render_both_kinds():
    svg, _w, _h = sd.render_map(_session(), NOW)
    assert ">DETOUR<" in svg and ">PARKED<" in svg
    assert "↩ back on the line" in svg and "⊥ LungNote 0c2b506c" in svg
    g2 = _session().goal("G2")
    x = sd.col_x(g2.col)
    assert f'<line x1="{x + sd.GOAL_W - 24}"' in svg          # the interrupt's return line
    assert f'<line x1="{x + 12}"' in svg                       # the parked dead-end stub


def test_escaping_and_truncation():
    def mutate(d):
        d["goals"][0]["title"] = "<b>x</b> & " + "ก" * 300
        d["entry_problem"] = "ยาว " * 80
    svg, _w, _h = sd.render_map(_session(mutate), NOW)
    assert "<b>x</b>" not in svg and "&lt;b&gt;x&lt;/b&gt; &amp;" in svg
    assert "…" in svg
    assert 1 <= svg.count('font-size="24"') <= 2


def test_tree_and_status_text():
    s = _session()
    txt = sd.tree_text(s, NOW)
    assert txt.startswith("🌳 SESSION MAP — 2026-09-09 · t-0001 · run #0")
    assert "▶ start: CEO อยากเห็นภาพรวม" in txt
    assert "G2.2  🔨 BUILD  — goal map v2 ซ้าย→ขวา  ⏱ 00:10→now · 20 min  ⬅️ อยู่ตรงนี้" in txt
    assert "D2 ↪ PARKED — Contabo: clone + Chromium ⊥ PARKED · LungNote 0c2b506c" in txt
    assert "G1  ⚙️ รับ diagram-design" in txt and "⏱ 22:30→22:42 · 12 min" in txt
    st = sd.status_text(s, NOW)
    assert st.splitlines()[0].startswith("📊 goals 1/4 · tasks 5/9 · 🔴 1 · ↪ 2 detours (1 parked) · ⏱ ")


def test_artifact_body_no_wrapper_single_map():
    body = sd.render_artifact_html(_session(), NOW)
    assert body.startswith("<title>")
    for tag in ("<!DOCTYPE", "<html", "<head", "<body"):
        assert tag not in body
    assert body.count("<svg ") == 1 and 'class="session-map"' in body
    assert "overflow-x: auto" in body and "@media" not in body


def test_photo_scale_respects_telegram_cap():
    assert sd.photo_scale(2, 1104, 600) == 2
    assert sd.photo_scale(2, 1968, 3200) == 1


def test_cli_patch_then_show(tmp_path):
    rc, _ = _run(["map", "--session", "t-0002", "--out-dir", str(tmp_path)], json.dumps(sd.SAMPLE))
    assert rc == 0
    rc, out = _run(["patch", "--session", "t-0002", "--out-dir", str(tmp_path)], json.dumps(sd.SAMPLE_PATCH))
    assert rc == 0, out
    assert out.startswith("changes: ") and "G2.2 doing → done" in out and "+ task G3.3" in out
    assert "📍 G2.3 — tests เขียว + self_check" in out
    rc, out = _run(["show", "--tree", "--session", "t-0002", "--out-dir", str(tmp_path)])
    assert rc == 0 and "run #2" in out
    rc, out = _run(["patch", "--session", "t-0003", "--out-dir", str(tmp_path)], "{}")
    assert rc == 1


def test_png_render_optional(tmp_path):
    if os.environ.get("SESSION_DIAGRAM_CHROME_TEST") != "1":
        return
    chrome = sd.find_chrome()
    assert chrome
    page, w, h = sd.render_html(_session(), NOW)
    p = Path(tmp_path) / "d.html"
    p.write_text(page, encoding="utf-8")
    png = sd.render_png(p, Path(tmp_path) / "d.png", w, h, 1, chrome)
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
