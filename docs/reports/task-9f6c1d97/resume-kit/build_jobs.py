import re, json, sys
src = open('/opt/MoonieXHQ/Work/cn-series/plan/EP04-stills.md', encoding='utf-8').read()
start = src.index('## Per-shot first frames')
body = src[start:]
blocks = re.split(r'\n### (?=EP04-S\d{3})', body)[1:]
jobs = []
for b in blocks:
    head, rest = b.split('\n', 1)
    m = re.match(r'(EP04-S\d{3}) \| ([^|]+) \|', head)
    sid, kind = m.group(1), m.group(2).strip()
    refs = re.findall(r'states/([A-Za-z0-9_]+\.png)', rest.split('Output plate')[0])
    pm = re.search(r'ChatGPT prompt: (.*)', rest)
    jobs.append(dict(name=sid, kind=kind, refs=refs, prompt=pm.group(1).strip()))
json.dump(jobs, open(sys.argv[1], 'w'), ensure_ascii=False, indent=1)
print(len(jobs), sum(1 for j in jobs if j['kind'].startswith('still')), max(len(j['refs']) for j in jobs), min(len(j['refs']) for j in jobs))
import collections
print(collections.Counter(len(j['refs']) for j in jobs))
print(max(len(j['prompt']) for j in jobs))
