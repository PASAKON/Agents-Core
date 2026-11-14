import json, hashlib, os
R='/opt/MoonieXHQ/Work/cn-series/'
rl=json.load(open('/opt/MoonieXHQ/Work/task-9f6c1d97/tmp/claude-0/-opt-MoonieXHQ-Agents-Core-worktrees-mooniex-agents--video-editor--task-9f6c1d97/b1f9a8c9-223a-427d-8d11-c5ff866f7d54/scratchpad/runner_ledger.json'))
rv=json.load(open(R+'plan/EP04-shots-review.json'))
retry={19:'brief says covered beads, abacus uncovered',28:'abacus glows before the flick'}
out={}
for i in range(1,121):
    n='EP04-S%03d'%i; e=rv.get(n); p=R+'stills/ep04/%s.png'%n
    row={'shot':n,'status':'not_started','tries':0,'md5':None,'bytes':None,'chat_url':None,'note':'','rejected':[]}
    if e:
        row['tries']=e['tries']; row['note']=e['note']; row['rejected']=e['rejected']
        row['status']=e['status'] if e['status']!='marked_fail' else 'marked_fail'
    if os.path.exists(p):
        b=open(p,'rb').read(); row['md5']=hashlib.md5(b).hexdigest(); row['bytes']=len(b); row['status']='ok'
    elif e: row['status']='retry_pending'
    if i in retry: row['status']='ok_retry_pending' if row['status']=='ok' else row['status']; row['retry_reason']=retry[i]
    if n in rl and rl[n].get('status')=='done': row['chat_url']=rl[n]['chat_url']
    if n=='EP04-S062': row['status']='stopped_quota'; row['note']='ChatGPT image quota hit, reset 22:30 (winbox clock)'; row['tries']=0
    out[n]=row
json.dump(out,open(R+'plan/EP04-shots-ledger.json','w'),indent=1,ensure_ascii=False)
import collections; print(collections.Counter(v['status'] for v in out.values()))
