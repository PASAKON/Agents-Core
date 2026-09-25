"""Unit tests for tools/bl_ab_run.py's spawn-full/spawn-seg (task-99f3d2e8).

Only the pure, local pieces -- everything else in bl_ab_run.py drives ssh/
scp/delegate_task against a real box and has no unit test for the same
reason (no fixture can stand in for a real remote host). spawn-full/
spawn-seg are pure string plumbing over the checked-in BRIEF-*.md files, so
they're worth covering directly.

Run via: pytest tests/test_bl_ab_run.py -q
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

from tools import bl_ab_run as run


def _capture(func, args) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = func(args)
    assert rc == 0
    return buf.getvalue()


def test_brief_arm1_md_and_brief_seg_md_exist_on_disk():
    assert run.BRIEF_ARM1_PATH.is_file()
    assert run.BRIEF_SEG_PATH.is_file()


def test_brief_body_strips_the_explainer_above_the_marker():
    body = run._brief_body(run.BRIEF_ARM1_PATH)
    assert body.startswith("## Brief given to the worker")
    assert "CTO ruling 2026-09-25" not in body  # that's in the stripped explainer


def test_spawn_full_prints_brief_arm1_verbatim(capsys):
    class _NS: ...
    rc = run.cmd_spawn_full(_NS())
    assert rc == 0
    out = capsys.readouterr().out
    assert "## Brief given to the worker" in out
    assert "seconds 0.0 to" in out and "153.0333" in out
    assert "DRY RUN" in out and "NOT spawned" in out


def test_spawn_seg_substitutes_all_four_placeholders(tmp_path, capsys):
    segments = {"segments": [
        {"id": "seg02", "t0": 39.3, "t1": 65.8333, "frame_count": 796,
         "lines": [{"tag": "CONTEXT-3", "t0": 39.66, "t1": 43.16, "text": "x"},
                   {"tag": "MAIN-1", "t0": 54.84, "t1": 58.3, "text": "y"}]},
    ]}
    seg_path = tmp_path / "segments.json"
    seg_path.write_text(json.dumps(segments), encoding="utf-8")

    class _NS:
        segments = str(seg_path)
        seg = "seg02"

    rc = run.cmd_spawn_seg(_NS())
    assert rc == 0
    out = capsys.readouterr().out
    assert "{seg}" not in out and "{t0}" not in out and "{t1}" not in out and "{tags}" not in out
    assert "segment `seg02`" in out
    assert "39.3 to 65.8333" in out
    assert "CONTEXT-3, MAIN-1" in out
    assert "prototypes/bl-split-ep57/seg02/beats.json" in out
    assert "--t0 39.3 --t-max 65.8333" in out


def test_spawn_seg_unknown_segment_errors(tmp_path, capsys):
    seg_path = tmp_path / "segments.json"
    seg_path.write_text(json.dumps({"segments": [{"id": "seg01", "t0": 0, "t1": 1, "lines": []}]}),
                         encoding="utf-8")

    class _NS:
        segments = str(seg_path)
        seg = "seg99"

    rc = run.cmd_spawn_seg(_NS())
    assert rc == 1
    assert "not found" in capsys.readouterr().err


def test_brief_seg_template_has_no_stray_format_braces_outside_the_four_placeholders():
    # cmd_spawn_seg uses plain .replace(), not str.format(), specifically
    # because the brief's body is full of literal JSON-shaped braces
    # (beats.json's own {"tag","t0",...} shape) -- prove those substrings
    # survive a substitution untouched (they would raise/vanish under
    # .format()).
    body = run._brief_body(run.BRIEF_SEG_PATH)
    substituted = (body.replace("{seg}", "segXX").replace("{t0}", "0.0")
                        .replace("{t1}", "1.0").replace("{tags}", "TAG-1"))
    assert '{"tag", "t0", "t1", "mode", "extra"}' in substituted
    assert '{"cap": "<caption>"}' in substituted
