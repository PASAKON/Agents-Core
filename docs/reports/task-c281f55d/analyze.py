"""Read cached captions without counting rolling-caption duplicates. No downloads."""
import argparse
import html
import json
import re
from pathlib import Path

BASE = Path('/opt/MoonieXHQ/Work/cn-dub-teardown')

def seconds(value):
    h, m, s = map(float, value.split(':'))
    return h * 3600 + m * 60 + s

def cues(path):
    result = []
    for block in path.read_text().split('\n\n'):
        lines = block.splitlines()
        timing = next((i for i, line in enumerate(lines) if ' --> ' in line), None)
        if timing is None:
            continue
        start, end = lines[timing].split(' --> ')
        start, end = seconds(start), seconds(end.split()[0])
        if end - start < .02:
            continue
        # YouTube puts previous rolling text first and newly timed text last.
        body = [line.strip() for line in lines[timing + 1:] if line.strip()]
        if not body:
            continue
        line = body[-1]
        tokens = re.split(r'<(\d\d:\d\d:\d\d\.\d+)>', line)
        t = start
        for i, token in enumerate(tokens):
            if i % 2:
                t = seconds(token)
            else:
                text = html.unescape(re.sub(r'<[^>]+>', '', token)).strip()
                if text:
                    result.append((t, text))
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--read', action='store_true')
    args = parser.parse_args()
    windows = [('A opening', 'top', 0, 600), ('A hour1', 'top', 3600, 3720),
               ('A hour2', 'top', 7200, 7320), ('A final5', 'top', 11461, 11761),
               ('B sword', 'dub', 0, 180)]
    for label, source, start, end in windows:
        data = cues(BASE / 'downloads' / f'{source}.th.vtt')
        print(label)
        for a in range(start, end, 30):
            text = ''.join(s for t, s in data if a <= t < min(a + 30, end))
            if args.read:
                print(a, text)
            else:
                print(json.dumps({'start': a, 'end': min(a+30,end),
                                  'caption_characters': len(text),
                                  'markers': {s: text.count(s) for s in ['ครับ','พี่','ข้า','เจ้า','กู','มึง']}}, ensure_ascii=False))

if __name__ == '__main__':
    main()
