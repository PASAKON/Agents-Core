"""AGY -> Claude reply rules in config/agy-settings.json (CEO 2026-11-27, Q-20261127-0326-cbff).

The CEO allowed exactly two message commands for headless AGY: `send_to_agy.py reply` and
`send_to_cxo.py`. Nothing else may ride on them: no chaining, no substitution, no `--spawn`.
Python's re stands in for agy's matcher on this regex subset.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = "bash scripts/hub/org-python.sh"


def _rules():
    allow = json.loads((ROOT / "config" / "agy-settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]
    return [re.compile(r[len("command(regex:"):-1]) for r in allow
            if r.startswith("command(regex:") and ("send_to_agy" in r or "send_to_cxo" in r)]


def _allowed(cmd):
    return any(rx.fullmatch(cmd) for rx in _rules())


def test_exactly_two_reply_rules():
    assert len(_rules()) == 2


def test_replies_are_allowed():
    for cmd in (f'{PY} tools/send_to_agy.py reply cgo-9cd5c56d "รับทราบ EP3 เริ่มแล้ว"',
                f"{PY} tools/send_to_agy.py reply cgo-9cd5c56d 'done: 3 clips' --from cto-agy-1ec08f78",
                f'{PY} tools/send_to_agy.py reply cgo-9cd5c56d "ok" --from cto-agy-1 --host contabo',
                f'bash /opt/MoonieXHQ/Agents/Core/scripts/hub/org-python.sh tools/send_to_cxo.py cgo "สรุป EP3"',
                f'{PY} tools/send_to_cxo.py --from cto-agy-1ec08f78 --subject "BL EP3" cgo "ok"'):
        assert _allowed(cmd), cmd


def test_nothing_else_rides_on_them():
    for cmd in (f'{PY} tools/send_to_cxo.py --spawn cgo "x"',
                f'{PY} tools/send_to_cxo.py --spawn "x"',
                f'{PY} tools/send_to_agy.py send cto-agy-1 "x"',
                f'{PY} tools/send_to_agy.py reply cgo "$(cat /etc/shadow)"',
                f'{PY} tools/send_to_agy.py reply cgo "`id`"',
                f'{PY} tools/send_to_agy.py reply cgo "a"; rm -rf x',
                f'{PY} tools/send_to_agy.py reply cgo "a" && curl x',
                f'{PY} tools/send_to_agy.py reply cgo "a" | sh',
                f'{PY} tools/send_to_agy.py reply cgo "a" > /etc/x',
                f"{PY} tools/send_to_cxo.py cgo 'a' ; id",
                f'{PY} tools/ask_run.py ask "x"',
                f'bash /tmp/scripts/hub/org-python.sh tools/send_to_cxo.py cgo "x"',
                f'{PY} tools/send_to_cxo.py cgo "a\nrm x"'):
        assert not _allowed(cmd), cmd
