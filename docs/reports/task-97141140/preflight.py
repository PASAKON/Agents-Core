"""Read-only M3 input audit; writes evidence in this report directory."""
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path('/opt/MoonieXHQ/Agents/Core/worktrees')
M2 = ROOT / 'mooniex-agents__video_editor__task-c7065d2a/docs/reports/task-c7065d2a'
WORK = Path('/opt/MoonieXHQ/Work')
shots = json.loads((M2 / 'shot_schedule.json').read_text())
mix = WORK / 'task-c7065d2a/out/ep02_m2_mix.wav'
media = []
for directory, subdirs, files in os.walk(WORK):
    subdirs[:] = [d for d in subdirs if d not in {'tmp', '.git', 'node_modules', '.venv', '.cache'}]
    for name in files:
        path = Path(directory) / name
        if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'} and 'ep02' in str(path).lower():
            media.append(str(path))
data = {
    'schedule_source': str(M2 / 'shot_schedule.json'),
    'shots': len(shots),
    'unique_plates': len({s['plate'] for s in shots}),
    'max_shot_seconds': max(s['end'] - s['start'] for s in shots),
    'schedule_end_seconds': max(s['end'] for s in shots),
    'mix_path': str(mix),
    'mix_md5': hashlib.md5(mix.read_bytes()).hexdigest(),
    'free_bytes': shutil.disk_usage(WORK).free,
    'ep02_image_candidates_under_work': sorted(media),
    'paper_directory_files': sorted(str(p) for p in (WORK / 'ghostrules-full/ep02/paper').iterdir()),
}
assert data['shots'] == 97
assert data['unique_plates'] == 77
assert data['max_shot_seconds'] <= 12.000001
assert data['free_bytes'] > 10_000_000_000
Path(__file__).with_name('preflight.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps(data, indent=2))
