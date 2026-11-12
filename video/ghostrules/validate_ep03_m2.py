"""Independent delivery checks; run after mix_ep03_m2.py finishes."""
import hashlib
import json
from pathlib import Path
import shutil
import wave

OUT = Path('/root/MoonieXHQ/Work/task-af2d7f8f/out')
REPORT = Path('docs/reports/task-af2d7f8f')
timeline = json.loads((OUT/'timeline.json').read_text())
cues = json.loads((OUT/'cue_ledger.json').read_text())
gaps = json.loads((OUT/'silence_gaps.json').read_text())
for line in (OUT/'MD5SUMS').read_text().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.md5((OUT/name).read_bytes()).hexdigest() == digest, name
with wave.open(str(OUT/'ep03_m2_mix.wav')) as w:
    duration = w.getnframes()/w.getframerate()
    assert w.getnchannels() == 2 and w.getsampwidth() == 2 and w.getframerate() == 24000
    assert abs(duration-timeline['duration']) < .001
assert len(timeline['takes']) == 22
for cue in cues['cues']:
    assert abs(cue['start']*24-cue['frame']) < 1e-6
    for take in timeline['takes']:
        assert cue['end'] <= take['start'] or cue['start'] >= take['voice_end']
assert cues['jump_scares'] <= 2
assert all(g['start'] is not None and g['end'] > g['start'] for g in gaps['gaps'])
assert not list((OUT.parent/'tmp').glob('*.wav'))
free = shutil.disk_usage(OUT).free
assert free >= 10_000_000_000
result = dict(md5_manifest='all entries passed', duration=duration, take_count=22,
              cue_count=len(cues['cues']), unresolved_events=len(cues['omitted']),
              narration_overlaps=0, frame_grid='24 fps passed', silence_count=gaps['count'],
              silence_seconds=gaps['total_seconds'], longest_gap=max(gaps['gaps'], key=lambda x:x['duration']),
              free_bytes=free, intermediate_count=0,
              mix_md5=hashlib.md5((OUT/'ep03_m2_mix.wav').read_bytes()).hexdigest(),
              loudness=(OUT/'loudness.txt').read_text())
(REPORT/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
