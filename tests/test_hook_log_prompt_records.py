"""The prompt hook must surface a DEV's whole report, not just its header line.

Regression for 2026-09-19 (task-2e5cd54e): a DEV wrote a full blocker report --
what it had already built, the Drive folder, the exact 402 text, and the fact
that zero money had been spent -- and the CTO saw four words, "Blocked.
Summary:". Nothing was lost in transit; the report was in cto.log the whole
time. The hook filtered line by line, and only the first line of a dev_message
carries the "] <role> task-<id>:" prefix, so every following line was dropped.
The CEO noticed before the CTO did.
"""
import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("hooklog", ROOT / "scripts" / "hook-log-prompt.py")
hooklog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hooklog)

BLOCKER = """[2026-09-19T02:55:04] developer task-deadbe: Blocked. Summary:
**Done so far:**
- fal balance recorded before start: **$15.6265775**. Zero fal spend so far.
- Folder: https://drive.google.com/drive/folders/15Wi2CTwnhV4pVJjQFXhUTYdxCmcOQ7TI
**Blocked:** `script` stage failed - 402, "can only afford 93 tokens".
[2026-09-19T02:57:21] CTO: unrelated line that must not be surfaced
"""


def _run(monkey_log: Path, prompt: str = "status?") -> str:
    hooklog.LOG = monkey_log
    hooklog.STATE = monkey_log.parent / ".pos"
    # SID is read at import time from the REAL session's env. Left alone, the
    # first-fire branch of _read_offset starts at EOF and the fixture log reads
    # as "nothing new" -- the test would pass an empty string to every assert.
    hooklog.SID = ""
    hooklog.STATE.write_text("0")
    out = io.StringIO()
    stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"prompt": prompt}))
    try:
        with redirect_stdout(out):
            hooklog.main()
    finally:
        sys.stdin = stdin
    return out.getvalue()


def test_group_records_keeps_body_with_its_header():
    lines = [l for l in BLOCKER.splitlines() if l.strip()]
    records = hooklog._group_records(lines)
    assert len(records) == 2, records
    assert records[0][0].endswith("Blocked. Summary:")
    assert len(records[0]) == 5, "header + 4 body lines"
    assert records[1][0].endswith("unrelated line that must not be surfaced")


def test_body_lines_reach_the_cto(tmp_path, monkeypatch):
    monkeypatch.setenv("CTO_SESSION", "1")
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    log = tmp_path / "cto.log"
    log.write_text(BLOCKER, encoding="utf-8")
    text = _run(log)
    assert "Blocked. Summary:" in text
    # the three facts that were invisible before the fix
    assert "$15.6265775" in text, "the DEV said it had spent nothing; the CTO never saw it"
    assert "drive.google.com/drive/folders/15Wi2CTwnhV4pVJjQFXhUTYdxCmcOQ7TI" in text
    assert "can only afford 93 tokens" in text
    # a plain CEO line is still not DEV activity
    assert "unrelated line that must not be surfaced" not in text


def test_one_huge_report_is_capped_but_says_where_the_rest_is(tmp_path, monkeypatch):
    monkeypatch.setenv("CTO_SESSION", "1")
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    body = "\n".join(f"- line {i}" for i in range(hooklog.MAX_BODY_LINES + 25))
    log = tmp_path / "cto.log"
    log.write_text(f"[2026-09-19T03:00:00] developer task-abc123: Report\n{body}\n", encoding="utf-8")
    text = _run(log)
    assert "- line 0" in text
    assert f"- line {hooklog.MAX_BODY_LINES + 24}" not in text, "should be capped"
    assert "more lines - full text in" in text, "a cap must name where the rest lives"
