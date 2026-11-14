# usage: rev.py ok|retry|fail SHOT[,SHOT..] "note"   (shot = number)
import sys, json, shutil, os
R='/opt/MoonieXHQ/Work/cn-series/stills/ep04/'
J='/opt/MoonieXHQ/Work/cn-series/plan/EP04-shots-review.json'
d=json.load(open(J)) if os.path.exists(J) else {}
st, shots, note = sys.argv[1], sys.argv[2].split(','), sys.argv[3] if len(sys.argv)>3 else ''
for s in shots:
    n='EP04-S%03d'%int(s); e=d.setdefault(n,{'status':None,'tries':0,'note':'','rejected':[]})
    if st=='ok':
        shutil.copy(R+'_incoming/'+n+'.png', R+n+'.png'); e['status']='ok'
        if not e['tries']: e['tries']=1
    elif st=='reject':  # move incoming to rejected, tries counted
        os.makedirs('/opt/MoonieXHQ/Work/cn-series/plan/EP04-shots-rejected',exist_ok=True)
        k=len(e['rejected'])+1; dst='/opt/MoonieXHQ/Work/cn-series/plan/EP04-shots-rejected/%s_try%d.png'%(n,k)
        shutil.move(R+'_incoming/'+n+'.png', dst); e['rejected'].append(dst.split('/')[-1]); e['status']='retry'; e['tries']=k
    elif st=='fail': e['status']='marked_fail'
    if note: e['note']=(e['note']+' | '+note).strip(' |') if st=='reject' else note
json.dump(d,open(J,'w'),indent=1,ensure_ascii=False)
