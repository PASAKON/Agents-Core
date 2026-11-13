#!/usr/bin/env python3
"""Read-only checks for the EP04 text handoff; no media or API calls."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'script/EP04-full-script.md').read_text()
SHEET = (ROOT / 'plan/EP04-FULL-SHEET.md').read_text()
STILLS = (ROOT / 'plan/EP04-stills.md').read_text()
REFS = Path('/opt/MoonieXHQ/Work/cn-series/chars/states')


def sections(text, prefix):
    return re.findall(prefix + r' (EP04-S\d{3}) \| ([^\n]+)\n(.*?)(?=\n##|\Z)', text, re.S)


def seconds(value):
    minute, second = map(int, value.split(':'))
    return minute * 60 + second


script = sections(SCRIPT, '###')
sheet = sections(SHEET, '##')
stills = sections(STILLS, '###')
expected = [f'EP04-S{n:03}' for n in range(1, 121)]
for document in (script, sheet, stills):
    assert [row[0] for row in document] == expected, 'Missing, duplicate or unordered shot ID'

for path in ROOT.rglob('*.md'):
    text = path.read_text()
    forbidden = ['bl' + 'ush', '\u0e2b\u0e19\u0e49\u0e32\u0e41\u0e14\u0e07', '\u0e2b\u0e39\u0e41\u0e14\u0e07', chr(171), chr(187), chr(8212)]
    assert not any(word in text.lower() for word in forbidden), f'Forbidden text: {path}'

types = []
effects = []
retention = [5]
spoken_lengths = []
peaks = [20, 32, 56, 76, 92, 108]
family = []
for n, (script_row, sheet_row, still_row) in enumerate(zip(script, sheet, stills), 1):
    sid, timing, script_body = script_row
    _, sheet_timing, body = sheet_row
    assert timing.split(' | ')[0] == sheet_timing.split(' | ')[0]
    start, end = timing.split(' | ')[0].split('-')
    assert seconds(start) == (n - 1) * 15 and seconds(end) == n * 15
    assert '15s' in timing and '15s' in sheet_timing
    lines = body.split('\nLines:\n', 1)[1].strip()
    assert lines == script_body.strip(), f'Line mismatch: {sid}'
    spoken = re.sub(r'^(?:N(?:→"[^"]+")?|ใจ):\s*', '', lines, flags=re.M)
    spoken_lengths.append(len(spoken.replace('\n', '')))
    kind = re.search(r'^Type: (.+)$', body, re.M).group(1)
    assert kind in ('flow', 'still+fx')
    types.append(kind)
    stamp = re.search(r'^Retention: (\d\d:\d\d)', body, re.M).group(1)
    retention.append(seconds(stamp))
    assert seconds(stamp) == (n - 1) * 15 + 12
    if n in peaks:
        assert 'Role: PEAK' in body and kind == 'flow'
    if n - 1 in peaks:
        assert 'Role: COMIC' in body and kind == 'flow'
    if kind == 'still+fx':
        assert n == 1 or types[-2] != kind, 'Adjacent stills'
        effect = re.search(r'^Effect: (.+)$', body, re.M).group(1)
        assert not effects or effect != effects[-1], 'Repeated particle effect'
        effects.append(effect)
        assert 'Camera: slow ' in body and 'over 15 s' in body
        assert '| still+fx plate |' in f'| {still_row[1]}'
    else:
        assert 'Google Flow prompt (15s):' in body
        assert '| first-frame |' in f'| {still_row[1]}'
    if n in (39, 40, 42):
        assert 'Family backroom' in body
        family.append(n)

assert types[0] == types[-1] == 'flow'
assert 0.10 <= types.count('still+fx') / 120 <= 0.20
assert max(b - a for a, b in zip(retention, retention[1:])) <= 18
for low, high in ((1, 40), (41, 80), (81, 120)):
    assert sum(low <= peak <= high for peak in peaks) == 2

new = set(re.findall(r'^### NEW (\S+\.png)$', STILLS, re.M))
all_refs = set(re.findall(re.escape(str(REFS)) + r'/([^\s]+\.png)', SHEET + STILLS))
missing = sorted(name for name in all_refs if name not in new and not (REFS / name).is_file())
assert not missing, f'Unknown reference paths: {missing}'
assert len(new) == 19

print(json.dumps({
    'status': 'PASS', 'shots': 120, 'duration_seconds': 1800,
    'flow': types.count('flow'), 'still_fx': types.count('still+fx'),
    'still_percent': types.count('still+fx') / 120 * 100,
    'max_planned_retention_gap_seconds': max(b - a for a, b in zip(retention, retention[1:])),
    'peak_shots': peaks, 'comic_shots': [n + 1 for n in peaks],
    'new_reference_plates': len(new), 'existing_reference_paths': len(all_refs - new),
    'spoken_characters_including_spaces_and_quotes': sum(spoken_lengths),
    'spoken_characters_per_shot_min_max': [min(spoken_lengths), max(spoken_lengths)],
    'luo_mei_family_shots': family,
    'limits': 'Text structure only. Does not validate actual audio, rendered frames, acting, continuity of reference images or originality against external works.'
}, ensure_ascii=False, indent=2))
