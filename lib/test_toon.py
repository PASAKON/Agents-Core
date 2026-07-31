"""Tests for lib.toon. Plain-script style (no pytest dependency), matching
lib/test_recall.py / lib/test_reflect.py.

Run:  python -m lib.test_toon
"""
from __future__ import annotations

import json

from . import toon


def _check(name: str, cond: bool) -> bool:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    return cond


def test_flat_dict() -> bool:
    ok = True
    d = {"id": "task-1", "status": "done", "iteration": 2, "worktree": None}
    out = toon.encode(d)
    ok &= _check("key: value per line", out ==
                 'id: task-1\nstatus: done\niteration: 2\nworktree: null')
    ok &= _check("empty dict -> empty string", toon.encode({}) == "")
    return ok


def test_dict_value_quoting() -> bool:
    ok = True
    ok &= _check("colon forces quoting",
                 toon.encode({"title": "fix: bug"}) == 'title: "fix: bug"')
    ok &= _check("comma forces quoting",
                 toon.encode({"a": "x,y"}) == 'a: "x,y"')
    ok &= _check("numeric-looking string quoted",
                 toon.encode({"a": "42"}) == 'a: "42"')
    ok &= _check("plain word unquoted",
                 toon.encode({"a": "hello"}) == "a: hello")
    ok &= _check("newline escaped",
                 toon.encode({"a": "line1\nline2"}) == 'a: "line1\\nline2"')
    ok &= _check("bool/null literals",
                 toon.encode({"a": True, "b": False, "c": None}) ==
                 "a: true\nb: false\nc: null")
    return ok


def test_tabular_list_root() -> bool:
    ok = True
    hits = [
        {"path": "a.md", "line": 3, "text": "foo"},
        {"path": "b.md", "line": 9, "text": "bar"},
    ]
    out = toon.encode(hits)
    expected = "[2]{path,line,text}:\na.md,3,foo\nb.md,9,bar"
    ok &= _check("uniform dict list -> header + rows", out == expected)
    ok &= _check("empty list -> [0]:", toon.encode([]) == "[0]:")
    ok &= _check("scalar list -> inline",
                 toon.encode(["a", "b", "c"]) == "[3]: a,b,c")
    return ok


def test_tabular_list_field() -> bool:
    ok = True
    d = {"hits": [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]}
    out = toon.encode(d)
    expected = "hits[2]{id,name}:\n  1,Alice\n  2,Bob"
    ok &= _check("nested uniform list -> header + indented rows", out == expected)
    return ok


def test_json_fallback_non_uniform() -> bool:
    ok = True
    # different key sets across items -> not tabular -> json fallback
    mixed = [{"a": 1, "b": 2}, {"a": 1, "c": 3}]
    out = toon.encode(mixed)
    ok &= _check("non-uniform keys falls back to json",
                 out == json.dumps(mixed, default=str))
    ok &= _check("fallback output round-trips as JSON",
                 json.loads(out) == mixed)
    return ok


def test_json_fallback_nested_values() -> bool:
    ok = True
    # a column containing a non-scalar (nested dict) disqualifies tabular form
    nested = [{"id": 1, "meta": {"x": 1}}, {"id": 2, "meta": {"x": 2}}]
    out = toon.encode(nested)
    ok &= _check("non-scalar column falls back to json",
                 out == json.dumps(nested, default=str))

    d = {"project": {"key": "p", "nested": {"deep": 1}}}
    out2 = toon.encode(d)
    ok &= _check("nested dict field value stays json",
                 out2 == f'project: {json.dumps(d["project"], default=str)}')
    return ok


def test_scalar_root() -> bool:
    ok = True
    ok &= _check("None -> null (matches json.dumps(None))", toon.encode(None) == "null")
    ok &= _check("string scalar", toon.encode("hello") == "hello")
    ok &= _check("int scalar", toon.encode(42) == "42")
    return ok


def test_get_task_like_row() -> bool:
    """Real get_task rows are flat sqlite dicts — touches/depends_on are
    JSON-encoded TEXT columns (still strings at this layer), never actual
    lists. Confirms that shape round-trips through the scalar dict path
    unchanged (no data-shape change, only serialization)."""
    ok = True
    row = {
        "id": "task-abc123",
        "project": "mooniex-agents",
        "role": "developer",
        "status": "review",
        "touches": '["lib/toon.py", "runners/cto_mcp_server.py"]',
        "iteration": 0,
        "report": None,
    }
    out = toon.encode(row)
    ok &= _check("touches stays a quoted JSON-string scalar, not restructured",
                 'touches: "[\\"lib/toon.py\\", \\"runners/cto_mcp_server.py\\"]"' in out)
    ok &= _check("report None -> null", "report: null" in out)
    ok &= _check("line count matches field count", len(out.splitlines()) == len(row))
    return ok


def main() -> int:
    suites = [
        test_flat_dict, test_dict_value_quoting, test_tabular_list_root,
        test_tabular_list_field, test_json_fallback_non_uniform,
        test_json_fallback_nested_values, test_scalar_root,
        test_get_task_like_row,
    ]
    all_ok = True
    for s in suites:
        print(f"{s.__name__}:")
        all_ok &= s()
    print("\n" + ("ALL PASS" if all_ok else "SOME FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
