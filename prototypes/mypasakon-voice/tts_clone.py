#!/usr/bin/env python3
"""Speak a script in the CEO's cloned voice (fal Seed Audio 1.0) and hand back one file.

Everything the CEO rejected on 2026-09-22/23 is a check in here, because a rule that
lives in a document gets skipped and a rule that lives in the script does not:

  * the reference must be a Rawcut (see RECIPE.md) - we only warn, since only a human
    can tell one source from another, but we DO refuse a reference that is band-limited
  * no chunk may run longer than MAX_CHUNK_SEC. Seed Audio invents silent holes inside
    long generations - measured 12.26 s of dead air inside one 27 s chunk - so an
    over-long chunk is re-split and re-fired rather than shipped
  * every chunk is stripped of head/tail silence and any internal pause over
    MAX_PAUSE_SEC, which is what the CEO heard as "dead air"
  * the joined file is verified: no silence over 0.6 s survives, or we raise

Usage:  python3 tts_clone.py SCRIPT.md REFERENCE.mp3 OUT.mp3
The script is split on BLANK LINES - they are breath points and they are load-bearing.
"""
import json, os, re, subprocess, sys, time, urllib.error, urllib.request

import numpy as np

ENDPOINT       = 'bytedance/seed-audio-1.0'
MAX_CHUNK_SEC  = 25.0    # above this the model starts inventing silence
MAX_PAUSE_SEC  = 0.55    # any gap inside speech longer than this is collapsed to it
JOIN_SEC       = 0.35    # fixed gap between chunks
CHARS_PER_SEC  = 15.0    # measured on real takes; only used for the first guess
SR             = 48000


def _key():
    for path in ('.env', os.path.expanduser('~/Projects/Agents/.env')):
        if not os.path.exists(path):
            continue
        for line in open(path, encoding='utf-8'):
            if line.startswith('FAL_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('FAL_API_KEY not found in .env')


KEY = _key()
H = {'Authorization': f'Key {KEY}', 'Content-Type': 'application/json'}


def call(url, body=None):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body else None,
        headers=H, method='POST' if body else 'GET')
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw[:300]}


def balance():
    req = urllib.request.Request('https://rest.fal.ai/billing/user_balance',
                                 headers={'Authorization': f'Key {KEY}'})
    with urllib.request.urlopen(req) as r:
        return float(r.read().decode().strip())   # fal answers a bare number, not an object


def pcm(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1',
                          '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def bandwidth(path):
    """99.5th-percentile frequency. An edited Audio/ file sits near 10 kHz, a Rawcut
    near 13.4 kHz, and that difference is what made the clone stop sounding hollow."""
    y = pcm(path)[:SR * 20]
    n, acc, cnt = 8192, None, 0
    for i in range(0, len(y) - n, n // 2):
        s = np.abs(np.fft.rfft(y[i:i + n] * np.hanning(n)))
        acc = s if acc is None else acc + s
        cnt += 1
    acc /= max(cnt, 1)
    f = np.fft.rfftfreq(n, 1 / SR)
    return float(f[np.where(np.cumsum(acc) / acc.sum() > 0.995)[0][0]])


def split_on_blank_lines(text, cap_chars):
    paras = [p.strip().replace('\n', ' ') for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks, cur = [], ''
    for p in paras:
        if not cur:
            cur = p
        elif len(cur) + 1 + len(p) <= cap_chars:
            cur += ' ' + p
        else:
            chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return chunks


def halve(text):
    """Split one over-long chunk at the sentence break nearest the middle."""
    marks = [m.end() for m in re.finditer(r'(นะครับ|ครับ|ค่ะ|นะฮะ)', text)]
    if not marks:
        mid = len(text) // 2
        return [text[:mid].strip(), text[mid:].strip()]
    mid = len(text) // 2
    cut = min(marks, key=lambda m: abs(m - mid))
    return [text[:cut].strip(), text[cut:].strip()]


def generate(text, ref_url):
    status, res = call(f'https://queue.fal.run/{ENDPOINT}',
                       {'prompt': text, 'audio_urls': [ref_url],
                        'multilingual': True, 'output_format': 'mp3'})
    if status >= 400:
        raise RuntimeError(f'submit {status}: {json.dumps(res, ensure_ascii=False)[:200]}')
    rid = res['request_id']
    for _ in range(300):
        time.sleep(2)
        st = call(f'https://queue.fal.run/{ENDPOINT}/requests/{rid}/status')[1]
        if st.get('status') == 'COMPLETED':
            break
        if st.get('status') in ('FAILED', 'ERROR'):
            raise RuntimeError(f'generation failed: {st}')
    audio = call(f'https://queue.fal.run/{ENDPOINT}/requests/{rid}')[1].get('audio') or {}
    if not audio.get('url'):
        raise RuntimeError('no audio in result')
    return audio['url'], float(audio.get('duration') or 0)


def strip_dead_air(y, thr_db=-38.0):
    """Trim head/tail silence and collapse any internal pause over MAX_PAUSE_SEC."""
    hop = SR // 100
    n = len(y) // hop
    if n == 0:
        return y, 0
    rms = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1))
    voiced = rms > 10 ** (thr_db / 20)
    idx = np.where(voiced)[0]
    if len(idx) == 0:
        return y, 0
    y = y[idx[0] * hop:(idx[-1] + 1) * hop]
    n = len(y) // hop
    rms = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1))
    voiced = rms > 10 ** (thr_db / 20)
    keep = np.ones(n, bool)
    cap, holes, i = int(MAX_PAUSE_SEC * 100), 0, 0
    while i < n:
        if not voiced[i]:
            j = i
            while j < n and not voiced[j]:
                j += 1
            if j - i > cap:
                keep[i + cap:j] = False
                holes += 1
            i = j
        else:
            i += 1
    return y[:n * hop].reshape(n, hop)[keep].reshape(-1), holes


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    script_path, ref_path, out_path = sys.argv[1:4]

    bw = bandwidth(ref_path)
    if bw < 12000:
        raise SystemExit(
            f'reference bandwidth is only {bw:.0f} Hz. Edited Audio/ files are band-limited '
            f'to ~10 kHz and clone hollow; cut the reference from a Rawcut instead (RECIPE.md).')
    print(f'reference bandwidth {bw:.0f} Hz - ok')

    text = open(script_path, encoding='utf-8').read()
    if '## บทพูด' in text:
        text = text.split('## บทพูด', 1)[1].split('---', 1)[0]
    text = text.strip()
    for banned in ('กู', 'มึง'):
        if banned in text:
            raise SystemExit(f'the script contains "{banned}" - that register belongs to '
                             f'BLACK LIQUIDITY, never to the CEO\'s own voice (RECIPE.md).')

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts/gdrive-bridge'))
    os.environ['FAL_KEY'] = KEY
    import fal_client
    ref_url = fal_client.upload_file(ref_path)

    queue = split_on_blank_lines(text, int(MAX_CHUNK_SEC * CHARS_PER_SEC))
    print(f'{len(text)} chars -> {len(queue)} chunks')

    spend0 = balance()
    pieces, resplits = [], 0
    while queue:
        chunk = queue.pop(0)
        url, dur = generate(chunk, ref_url)
        if dur > MAX_CHUNK_SEC and len(chunk) > 80:
            # over the cap: the model invents silence in here. Split and re-fire.
            resplits += 1
            print(f'  {dur:5.1f}s over the {MAX_CHUNK_SEC:.0f}s cap - re-splitting')
            queue = halve(chunk) + queue
            continue
        tmp = f'/tmp/_tts_{len(pieces):02d}.mp3'
        urllib.request.urlretrieve(url, tmp)
        y, holes = strip_dead_air(pcm(tmp))
        print(f'  chunk {len(pieces)+1}: {dur:5.1f}s -> {len(y)/SR:5.1f}s'
              f'{f"  ({holes} silent holes removed)" if holes else ""}')
        pieces.append(y)

    gap = np.zeros(int(JOIN_SEC * SR), dtype=np.float32)
    joined = np.concatenate([a for p in [(c, gap) for c in pieces] for a in p][:-1])
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1',
                    '-i', 'pipe:0', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
                    '-b:a', '192k', out_path, '-y'],
                   input=joined.astype(np.float32).tobytes(), check=True)

    # verify what we actually wrote, not what we intended to write
    det = subprocess.run(['ffmpeg', '-hide_banner', '-i', out_path, '-af',
                          'silencedetect=noise=-38dB:d=0.6', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    left = det.count('silence_start')
    print(f'\n{out_path}  {len(joined)/SR:.2f}s  '
          f'| re-splits {resplits} | silences >0.6s remaining {left}')
    if left:
        raise SystemExit('dead air survived the strip - do not ship this file')
    time.sleep(8)
    print(f'spend ${spend0 - balance():.4f}')


if __name__ == '__main__':
    main()
