"""Minimal TOON (Token-Oriented Object Notation) encoder.

IRON-RULES §38 / decisions/0010-toon-encoding-adoption.md: MCP tool output
fed into a Claude Code session's context should be TOON-encoded instead of
raw `json.dumps` wherever the data shape is uniform enough to benefit —
YAML-style `key: value` lines for a flat dict, one header + comma rows for
a list of same-shaped dicts (github.com/toon-format/spec).

No official Python port exists to depend on: PyPI's `toon-format` package
(github.com/toon-format/toon-python, linked from the spec repo) is a
namespace-reservation stub as of 2026-07-31 — "Full implementation coming
soon", no `encode`/`decode` — so this implements the subset of the spec
this codebase actually needs:

  - dict of scalars           -> "key: value" lines
  - list of same-shaped dicts (scalar values only) -> "[N]{f1,f2}:" header
    + one comma-row per item
  - anything else (empty/non-uniform lists, nested dict/list values,
    mixed key sets) -> falls back to `json.dumps` for that value, per the
    ADR's "deeply nested / non-uniform JSON does not benefit, leave as
    JSON" rule. This is an encode-only helper — nothing in this codebase
    re-parses these tool results, so no decoder is implemented.
"""
from __future__ import annotations

import json
import re
from typing import Any

_SCALAR_TYPES = (str, int, float, bool, type(None))
_NUMERIC_RE = re.compile(r"^[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
_BARE_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _is_scalar(v: Any) -> bool:
    return isinstance(v, _SCALAR_TYPES)


def _needs_quote(s: str, delim: str) -> bool:
    if s == "" or s != s.strip():
        return True
    if s in ("true", "false", "null"):
        return True
    if _NUMERIC_RE.match(s):
        return True
    if any(c in s for c in (":", '"', "\\", "[", "]", "{", "}", delim)):
        return True
    if any(ord(c) < 0x20 for c in s):
        return True
    if s.startswith("-") or s.startswith("#"):
        return True
    return False


def _encode_scalar(v: Any, delim: str) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):  # NaN / Infinity
            return "null"
        return str(int(v)) if v == int(v) else repr(v)
    s = str(v)
    if _needs_quote(s, delim):
        escaped = (
            s.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    return s


def _encode_key(k: Any) -> str:
    s = str(k)
    if _BARE_KEY_RE.match(s):
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _uniform_scalar_fields(items: list) -> list[str] | None:
    """Field list if every item is a dict, all share the same key set, and
    every value is a scalar. None if the array doesn't qualify for tabular
    form (caller falls back to json.dumps)."""
    if not items or not all(isinstance(i, dict) for i in items):
        return None
    fields = list(items[0].keys())
    key_set = set(fields)
    for it in items:
        if set(it.keys()) != key_set:
            return None
        if not all(_is_scalar(v) for v in it.values()):
            return None
    return fields


def _encode_list(items: list, delim: str) -> str:
    if not items:
        return "[0]:"
    if all(_is_scalar(i) for i in items):
        vals = delim.join(_encode_scalar(i, delim) for i in items)
        return f"[{len(items)}]: {vals}"
    fields = _uniform_scalar_fields(items)
    if fields is None:
        return json.dumps(items, default=str)
    header = f"[{len(items)}]{{{delim.join(_encode_key(f) for f in fields)}}}:"
    rows = [
        delim.join(_encode_scalar(it[f], delim) for f in fields)
        for it in items
    ]
    return "\n".join([header] + rows)


def _encode_field_value(key: str, v: Any, delim: str) -> str:
    """Render one `key: ...` line (or header+rows block) for a dict field."""
    if _is_scalar(v):
        return f"{key}: {_encode_scalar(v, delim)}"
    if isinstance(v, list):
        if not v:
            return f"{key}: []"
        if all(_is_scalar(i) for i in v):
            vals = delim.join(_encode_scalar(i, delim) for i in v)
            return f"{key}[{len(v)}]: {vals}"
        fields = _uniform_scalar_fields(v)
        if fields is None:
            return f"{key}: {json.dumps(v, default=str)}"
        header = f"{key}[{len(v)}]{{{delim.join(_encode_key(f) for f in fields)}}}:"
        rows = [
            "  " + delim.join(_encode_scalar(it[f], delim) for f in fields)
            for it in v
        ]
        return "\n".join([header] + rows)
    # dict values (or any other non-scalar) stay JSON — nested-object support
    # is out of scope per the ADR; this is still lossless, just not compact.
    return f"{key}: {json.dumps(v, default=str)}"


def _encode_dict(d: dict, delim: str) -> str:
    return "\n".join(
        _encode_field_value(_encode_key(k), v, delim) for k, v in d.items()
    )


def encode(value: Any, *, delimiter: str = ",") -> str:
    """Encode `value` as TOON.

    - dict -> "key: value" lines (list/dict field values recurse one level;
      further nesting falls back to json.dumps for that field).
    - list -> tabular header + rows when every item is a dict sharing the
      same scalar-only fields; inline comma row when every item is a
      scalar; json.dumps otherwise.
    - scalar -> single TOON-encoded token (matches json.dumps for None/
      bool/str/number so callers that pass a possibly-missing row through
      unchanged, e.g. `get_task` on an unknown id, still get sane output).
    """
    if isinstance(value, list):
        return _encode_list(value, delimiter)
    if isinstance(value, dict):
        return _encode_dict(value, delimiter)
    return _encode_scalar(value, delimiter)
