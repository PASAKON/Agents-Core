"""Regression test: CTO model/effort routing has one source of truth.

Before this fix, three places could each claim a different answer for
"what model/effort does the CTO run at":
  1. policies/agents.yaml (the canonical policy, per ADR 0009)
  2. scripts/cto-claude.sh — hardcoded 'claude-sonnet-5'/'claude-fable-5'/xhigh
     literals, independent of the yaml
  3. runners/cto_chat.py — read `model` from the yaml correctly, but
     hardcoded effort="max" instead of reading `effort` from the yaml

They only agreed because someone kept the hardcoded copies in sync by hand.
This test proves both launchers now resolve from the yaml instead of
carrying their own copy.

Run via:   python scripts/test_model_routing_consistency.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.config import role as get_role  # noqa: E402

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def main() -> int:
    canonical = get_role("cto")
    c_model = canonical.get("model")
    c_fallback = canonical.get("fallback_model")
    c_effort = canonical.get("effort")

    # --- 1: cto-claude.sh no longer hardcodes the literals ---
    sh_text = (ROOT / "scripts" / "cto-claude.sh").read_text()
    _mark("--model 'claude-sonnet-5'" not in sh_text,
          "cto-claude.sh does not hardcode the model literal")
    _mark("--effort xhigh" not in sh_text,
          "cto-claude.sh does not hardcode the effort literal")
    _mark('from lib.config import role as get_role' in sh_text,
          "cto-claude.sh resolves via lib.config.role() like cxo-claude.sh")

    # --- 2: cto-claude.sh's resolver snippet, actually run, matches the yaml ---
    snippet_match = re.search(
        r'IFS=. .*?<<<"\$\(source.*?\n(.*?)\n"\)"', sh_text, re.S,
    )
    _mark(snippet_match is not None, "found the model-resolution snippet in cto-claude.sh")
    if snippet_match:
        py_src = snippet_match.group(1)
        r = subprocess.run(
            [sys.executable, "-c", py_src],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        out = r.stdout.strip()
        _mark(r.returncode == 0, f"resolver snippet runs cleanly (stderr: {r.stderr[:200]!r})")
        expected = f"{c_model} {c_fallback} {c_effort}"
        _mark(out == expected,
              f"resolver snippet output matches agents.yaml: got {out!r}, want {expected!r}")

    # --- 3: cto_chat.py no longer hardcodes effort="max" ---
    chat_text = (ROOT / "runners" / "cto_chat.py").read_text()
    _mark('_effort: str | None = "max"' not in chat_text,
          "cto_chat.py does not hardcode effort=max")
    _mark('get_role("cto").get("effort")' in chat_text,
          "cto_chat.py resolves effort from agents.yaml")

    print(f"\n{'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
