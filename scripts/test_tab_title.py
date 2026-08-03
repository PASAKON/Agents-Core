"""Tests for scripts/tab-title.sh (IRON-RULES §32 live tab titles).

Covers:
  1. set-mode writes state/tab-titles/<role>-<sid>.title = "<base> <summary>"
  2. truncation to 60 chars with trailing ellipsis
  3. OSC-1 escape written to the saved tty (faked as a regular file)
  4. --reassert re-emits the saved title without recomputing
  5. missing session env -> exit 2
  6. missing .base file falls back to "<ROLE> #<sid>" prefix

Run via:   python scripts/test_tab_title.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# OSC 1 = icon/tab name only. Deliberately NOT OSC 0, which would also rewrite
# the window title and wipe the Main Tab (goal + progress + clock) owned by
# tools/maintab.py via OSC 2. Asserting the exact code guards that regression.
OSC_PREFIX = "\x1b]1;"
OSC_SUFFIX = "\x07"


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _stage(tmp: Path) -> Path:
    """Copy tab-title.sh into a fake root with patched ROOT + osascript shim."""
    fake_root = tmp / "fake-root"
    (fake_root / "scripts").mkdir(parents=True)
    (fake_root / "state" / "tab-titles").mkdir(parents=True)
    (fake_root / "state" / "locks").mkdir(parents=True)

    src = (ROOT / "scripts" / "tab-title.sh").read_text()
    patched = src.replace(
        'ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"',
        f'ROOT="{fake_root}"',
    )
    script = fake_root / "scripts" / "tab-title.patched.sh"
    script.write_text(patched)
    script.chmod(0o755)

    shim = tmp / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "osascript").write_text(
        f'#!/usr/bin/env bash\nprintf "%s\\n" "$@" >> "{tmp}/osascript.log"\nexit 0\n'
    )
    (shim / "osascript").chmod(0o755)
    return script


def _env(tmp: Path, sid: str = "testsid1") -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{tmp}/bin:{env.get('PATH', '')}"
    env["CXO_ROLE"] = "cto"
    env["CXO_SESSION_ID"] = sid
    env.pop("CTO_SESSION_ID", None)
    return env


def test_set_writes_title_and_tty(tmp: Path, script: Path) -> bool:
    fake_root = script.parent.parent
    sid = "testsid1"
    (fake_root / "state" / "tab-titles" / f"cto-{sid}.base").write_text(
        f"CTO #{sid}\n")
    faketty = fake_root / "state" / "faketty"
    faketty.write_text("")
    (fake_root / "state" / "locks" / f"cto-{sid}.tty").write_text(
        str(faketty) + "\n")

    r = subprocess.run(["bash", str(script), "✅ ทดสอบ title"],
                       env=_env(tmp), capture_output=True, text=True,
                       timeout=15)
    title_file = fake_root / "state" / "tab-titles" / f"cto-{sid}.title"
    expected = f"CTO #{sid} ✅ ทดสอบ title"
    tty_content = faketty.read_text()
    return (
        r.returncode == 0
        and title_file.read_text().strip() == expected
        and (OSC_PREFIX + expected + OSC_SUFFIX) in tty_content
    )


def test_truncation(tmp: Path, script: Path) -> bool:
    fake_root = script.parent.parent
    sid = "testsid1"
    long_summary = "⏳ " + "x" * 100
    r = subprocess.run(["bash", str(script), long_summary],
                       env=_env(tmp), capture_output=True, text=True,
                       timeout=15)
    title = (fake_root / "state" / "tab-titles" / f"cto-{sid}.title"
             ).read_text().strip()
    return r.returncode == 0 and len(title) == 60 and title.endswith("…")


def test_reassert(tmp: Path, script: Path) -> bool:
    fake_root = script.parent.parent
    sid = "testsid1"
    saved = "CTO #testsid1 🏁 ครบทุกงาน ปิดได้"
    (fake_root / "state" / "tab-titles" / f"cto-{sid}.title").write_text(
        saved + "\n")
    faketty = fake_root / "state" / "faketty"
    faketty.write_text("")  # clear

    r = subprocess.run(["bash", str(script), "--reassert"],
                       env=_env(tmp), capture_output=True, text=True,
                       timeout=15)
    return (
        r.returncode == 0
        and (OSC_PREFIX + saved + OSC_SUFFIX) in faketty.read_text()
    )


def test_missing_env_exits_2(tmp: Path, script: Path) -> bool:
    env = _env(tmp)
    env.pop("CXO_SESSION_ID", None)
    env.pop("CTO_SESSION_ID", None)
    r = subprocess.run(["bash", str(script), "⏳ x"],
                       env=env, capture_output=True, text=True, timeout=15)
    return r.returncode == 2


def test_missing_base_falls_back(tmp: Path, script: Path) -> bool:
    fake_root = script.parent.parent
    sid = "nobase01"
    env = _env(tmp, sid=sid)
    r = subprocess.run(["bash", str(script), "💤 ว่าง"],
                       env=env, capture_output=True, text=True, timeout=15)
    title = (fake_root / "state" / "tab-titles" / f"cto-{sid}.title"
             ).read_text().strip()
    return r.returncode == 0 and title == f"CTO #{sid} 💤 ว่าง"


def main() -> int:
    fails = 0
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        script = _stage(tmp)

        r = test_set_writes_title_and_tty(tmp, script); fails += not r
        _mark(r, "set-mode persists title + writes OSC-1 escape to saved tty")
        r = test_truncation(tmp, script); fails += not r
        _mark(r, "long summary truncated to 60 chars with ellipsis")
        r = test_reassert(tmp, script); fails += not r
        _mark(r, "--reassert re-emits saved title to tty")
        r = test_missing_env_exits_2(tmp, script); fails += not r
        _mark(r, "missing session env -> exit 2")
        r = test_missing_base_falls_back(tmp, script); fails += not r
        _mark(r, "missing .base file -> '<ROLE> #<sid>' fallback prefix")

    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
