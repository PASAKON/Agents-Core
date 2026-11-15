"""python finish_batch.py NN shot shot ...  -> scan feed, download done clips (720p original), strip + Contabo copy + md5,
tag fired rows, record refusals, write ledger rows (in the worktree). Prints a one-line summary. Never retries a refusal."""
import sys,os,subprocess,json,re
os.environ["PYTHONIOENCODING"]="utf-8"
W="C:/mooniex/ep4s"; PW="C:/mooniex/pwvenv/Scripts/python.exe"
REPO="C:/Users/passg/mooniex/worktrees/mooniex-agents__browser_operator__task-255aea73"
nn=sys.argv[1]; shots=sys.argv[2:]
def run(a,cwd=W,t=900): return subprocess.run(a,cwd=cwd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=t)
sc=run([PW,"scan_batch.py"]+shots); st=json.loads(sc.stdout.strip().splitlines()[-1]); print("scan:",{k:v[:30] for k,v in st.items()},flush=True)
done=[s for s,v in st.items() if v=="done"]; ref=[s for s,v in st.items() if v.startswith("refused")]; other=[s for s,v in st.items() if s not in done+ref]
got=[]
if done:
    r=run([PW,"dl_batch.py"]+done); print(ascii(r.stdout[-700:]),flush=True)
    res=eval(r.stdout.strip().splitlines()[-1])
    redo=[s for s,v in res.items() if v!="ok"]
    if redo:
        r=run([PW,"dl_batch.py"]+redo); res.update(eval(r.stdout.strip().splitlines()[-1]))
    got=[s for s in done if res.get(s)=="ok"]; other+=[s for s in done if s not in got]
for s in got:
    f=f"{W}/clips/EP04-S{s}_v1.mp4"; pr=run(["ffprobe","-v","error","-show_entries","stream=width,height,duration","-of","csv=p=0",f]).stdout.split()
    if not pr or not pr[0].startswith("1280,720"): print("PROBE odd",s,pr)
if got: print(run(["python","post_batch.py",nn,",".join(got)]).stdout[-400:])
rows=[json.loads(l) for l in open(W+"/fired.jsonl") if l.strip()]
for r in rows:
    if r["shot"] in shots and "batch" not in r: r["batch"]=nn
open(W+"/fired.jsonl","w").write("\n".join(json.dumps(r) for r in rows)+"\n")
with open(W+"/refused.jsonl","a",encoding="utf-8") as f:
    for s in ref: f.write(json.dumps({"shot":s,"batch":nn,"reason":"policy refusal: "+st[s][8:200]},ensure_ascii=False)+"\n")
# ledger: only shots of this batch; refused rows get refund rows (ledger_batch reads refused.jsonl)
print(run(["python","scripts/browser/ep4_flow_i2v/ledger_batch.py",nn],cwd=REPO).stderr[-300:])
run(["git","add","-A"],cwd=REPO); run(["git","commit","-qm",f"browser_operator: EP04 Flow batch {nn} ledger rows (task-255aea73)","-m","Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"],cwd=REPO)
print(f"BATCH {nn}: downloaded={got} refused={ref} other={other}")
