import json, shutil
p = r'C:\mooniex\ep04-shots\out\ledger.json'
shutil.copy(p, r'C:\mooniex\ep04-shots\out\ledger.before-retry.json')
d = json.load(open(p, encoding='utf-8'))
rows = d.get('rows', d) if isinstance(d, dict) else d
print(type(d), list(d)[:3] if isinstance(d, dict) else len(d))
tgt = rows if isinstance(rows, dict) else None
for n in ('EP04-S029','EP04-S039','EP04-S040'):
    print(n, tgt.get(n, {}).get('status'), tgt.get(n, {}).get('chat_url'))
    tgt.pop(n, None)
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
