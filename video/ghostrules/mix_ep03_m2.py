"""Offline EP3 M2 review build; source files are immutable, all media stays in Work."""
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import wave

import numpy as np

WORK = Path('/root/MoonieXHQ/Work/task-af2d7f8f')
IN = WORK / 'in'
OUT = WORK / 'out'
REPORT = Path('docs/reports/task-af2d7f8f')
BASE = Path('/opt/MoonieXHQ/Work/ghost-pilot')
SR = 24000


def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def decode(path):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
                                   '-ar', str(SR), '-ac', '2', '-f', 'f32le', 'pipe:1'])
    return np.frombuffer(raw, dtype='<f4').reshape(-1, 2).copy()


def ramp(x, seconds=.005):
    n = min(round(seconds * SR), len(x)//2)
    x[:n] *= np.linspace(0, 1, n)[:, None]
    x[-n:] *= np.linspace(1, 0, n)[:, None]
    return x


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(WORK).free
    if free < 10_000_000_000 + 300_000_000:
        raise RuntimeError('10 GB reserve plus staging/output budget unavailable')
    sources = [Path('/opt/MoonieXHQ/Work/ghostrules-full/ep03/plan/PLAN.json')]
    sources += sorted((BASE/'ep03/voice/takes').glob('*'))
    sources += sorted(Path('/opt/MoonieXHQ/Work/ghostrules-full/ep03/words').glob('*.json'))
    sources += sorted((BASE/'sfx-horror-pack').glob('*.wav'))
    manifest = []
    for src in sources:
        group = 'words' if src.parent.name == 'words' else ('sfx' if src.parent.name == 'sfx-horror-pack' else 'takes')
        dst = IN / (src.name if src.name == 'PLAN.json' else group+'/'+src.name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        manifest.append(dict(source=str(src), staged=str(dst), md5=hashlib.md5(dst.read_bytes()).hexdigest()))
    dump('input_manifest.json', manifest)
    plan = json.loads((IN/'PLAN.json').read_text())
    # No substitutions for unavailable surface-specific Foley; no generic horror hits.
    mapping = {
        ('c07', 'fast heartbeat'): ('fast_heartbeat_12.wav', 2.0),
        ('c15', 'lock turn'): ('old_iron_door_lock_05.wav', None),
        ('c16', 'wardrobe impacts'): ('door_slam_heavy_02.wav', None),
        ('c17', 'bathroom close and lock'): ('door_slam_heavy_02.wav', None),
        ('c18', 'wardrobe knocks'): ('wood_door_knock_01.wav', None),
        ('c18', 'bathroom pounding'): ('door_slam_heavy_02.wav', None),
        ('c18', 'entry knob'): ('old_iron_door_lock_05.wav', None),
    }
    segments, voices, cues, omitted, cards = [], [], [], [], []
    cursor = 2.4
    cards.append(dict(start=0, end=cursor, kind='act_card'))
    for scene in plan['scenes']:
        cid = scene['take']
        if cid in ('c04', 'c12', 'c18', 'c20'):
            cards.append(dict(start=cursor, end=cursor+2.4, kind='act_card'))
            cursor += 2.4
        x = decode(IN/'takes'/f'{cid}.wav')
        # Keep all narration: unverified source ASR is insufficient for a destructive word edit.
        start = round(cursor*SR)/SR
        end = start+len(x)/SR
        voices.append((start, ramp(x)*.85))
        cursor = end+.25
        for request in scene['sfx']:
            spec = mapping.get((cid, request['event']))
            if spec is None:
                omitted.append(dict(take=cid, **request, reason='No verified matching asset; character voices and stopped events retained only in narration'))
                continue
            assert request['anchor'] in scene['transcript']
            filename, limit = spec
            fx = decode(IN/'sfx'/filename)
            active = np.flatnonzero(np.max(np.abs(fx), axis=1) > .001)
            fx = fx[max(0, active[0]-120):min(len(fx), active[-1]+121)]
            if limit is not None:
                fx = fx[:round(limit*SR)]
            fx = ramp(fx, .025)*.18
            at = math.ceil(cursor*24)/24
            cues.append(dict(take=cid, event=request['event'], anchor=request['anchor'], source=filename,
                             start=at, end=at+len(fx)/SR, frame=round(at*24), gain=.18,
                             placement='after complete take; editorial delay requires listening review'))
            voices.append((at, fx))
            cursor = at+len(fx)/SR+.25
        cursor = max(cursor, end+.5)
        segments.append(dict(take=cid, original_plan_start=scene['start'], start=start,
                             voice_end=end, next_boundary=cursor, duration=len(x)/SR))
    cards.append(dict(start=cursor, end=cursor+3.2, kind='outro_card'))
    duration = cursor+3.2
    mix = np.zeros((math.ceil(duration*SR), 2), np.float32)
    for at, x in voices:
        a = round(at*SR)
        mix[a:a+len(x)] += x
    del voices
    # EP2 equal-power 2s loop, constrained to planned exposed outdoor rain.
    rain = decode(IN/'sfx/rain_metal_roof_13.wav')
    active = np.flatnonzero(np.max(np.abs(rain), axis=1) > .002)
    rain = rain[active[0]:active[-1]+1]
    fade = 2*SR
    assert len(rain) > 2*fade
    rain[:fade] *= np.sin(np.linspace(0, np.pi/2, fade))[:, None]
    rain[-fade:] *= np.cos(np.linspace(0, np.pi/2, fade))[:, None]
    s2 = segments[1]
    rain_start = s2['start']
    rain_end = rain_start + 68.483-44.293
    a, b = round(rain_start*SR), round(rain_end*SR)
    bed = np.zeros((b-a, 2), np.float32)
    step = len(rain)-fade
    for offset in range(-step, len(bed), step):
        l, r = max(0, offset), min(len(bed), offset+len(rain))
        if r > l:
            bed[l:r] += rain[l-offset:r-offset]*.20
    ramp(bed, .25)
    mix[a:b] += bed
    del bed
    peak = float(np.max(np.abs(mix)))
    gain = min(1, 10**(-1.5/20)/max(peak, 1e-9))
    mix *= gain
    path = OUT/'ep03_m2_mix.wav'
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        for i in range(0, len(mix), SR):
            w.writeframes((mix[i:i+SR]*32767).astype('<i2').tobytes())
    normalized = WORK/'tmp/normalized.wav'
    normalized.parent.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-af',
                    'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', str(SR), '-c:a', 'pcm_s16le',
                    str(normalized)], check=True)
    # Sandbox mounts may put tmp and out on different devices.
    shutil.copyfile(normalized, path)
    normalized.unlink()
    overlap = [(c['event'], s['take']) for c in cues for s in segments
               if c['start'] < s['voice_end'] and c['end'] > s['start']]
    assert not overlap
    assert all(c['end'] <= d['start'] for c, d in zip(cues, cues[1:]))
    assert shutil.disk_usage(WORK).free >= 10_000_000_000
    dump('timeline.json', dict(duration=len(mix)/SR, fps=24, takes=segments, cards=cards,
                               rain_intervals=[[rain_start, rain_end]], crossfade_seconds=2))
    dump('cue_ledger.json', dict(cues=cues, omitted=omitted, jump_scares=0, narration_overlaps=overlap,
                               narration_ducking=False, thunder_count=0))
    scan = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(path), '-af',
                           'silencedetect=noise=-50dB:d=0.3', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    (OUT/'silencedetect.txt').write_text(scan.stderr)
    gaps = []; current = None
    for line in scan.stderr.splitlines():
        match = re.search(r'silence_start: ([0-9.]+)', line)
        if match: current = float(match[1])
        match = re.search(r'silence_end: ([0-9.]+) .*silence_duration: ([0-9.]+)', line)
        if match:
            gaps.append(dict(start=current, end=float(match[1]), duration=float(match[2])))
    dump('silence_gaps.json', dict(threshold_db=-50, minimum_seconds=.3, gaps=gaps,
                                  count=len(gaps), total_seconds=sum(g['duration'] for g in gaps)))
    loud = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(path), '-af', 'ebur128=peak=true',
                           '-f', 'null', '-'], capture_output=True, text=True, check=True)
    (OUT/'loudness.txt').write_text(loud.stderr[loud.stderr.rfind('Summary:'):])
    dump('mix_metrics.json', dict(duration=len(mix)/SR, pre_normalization_peak_dbfs=20*math.log10(float(np.max(np.abs(mix)))),
                                 normalization='ffmpeg loudnorm I=-14 TP=-1.5 LRA=11; final measurement in loudness.txt',
                                 gain=gain, sample_rate=SR, free_before=free,
                                 free_after=shutil.disk_usage(WORK).free, cue_count=len(cues)))
    (OUT/'MD5SUMS').write_text(''.join(hashlib.md5(p.read_bytes()).hexdigest()+'  '+p.name+'\n'
                                     for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'MD5SUMS'))
    print(json.dumps(dict(duration=len(mix)/SR, cues=len(cues), omitted=len(omitted), gaps=len(gaps), free=shutil.disk_usage(WORK).free)))


if __name__ == '__main__':
    main()
