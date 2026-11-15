"""Fire a list of EP04 shots one by one: prep.py -> verify.py (start-frame identity) -> fire.py.
Run with system python (needs PIL for verify). Usage: python run_batch.py 002 003 ...
Appends one JSON line per shot to C:/mooniex/ep4s/fired.jsonl. Stops at the first failure (no retry, no reword)."""
import os; os.environ["PYTHONIOENCODING"]="utf-8"
import subprocess,sys,json,re,time
PW="C:/mooniex/pwvenv/Scripts/python.exe"; W="C:/mooniex/ep4s"
def run(a,**k): return subprocess.run(a,cwd=W,capture_output=True,text=True,encoding="utf-8",errors="replace",**k)
for s in sys.argv[1:]:
    r=run([PW,"prep.py",s],timeout=240)
    if r.returncode or "prompt ok: True" not in r.stdout: print("PREP FAIL",s,ascii(r.stdout[-300:]),ascii(r.stderr[-400:])); sys.exit(1)
    v=run(["python","verify.py","chip.bin","S"+s])
    if v.returncode: print("VERIFY FAIL",s,v.stdout); sys.exit(1)
    f=run([PW,"fire.py",s],timeout=240)
    m0=re.search(r"balance before (\d+) estimate (\d+)",f.stdout); m1=re.search(r"balance after (\d+) delta (\d+)",f.stdout)
    rec={"shot":s,"t":time.strftime("%H:%M:%S"),"before":m0 and int(m0.group(1)),"after":m1 and int(m1.group(1)),"rc":f.returncode}
    open(W+"/fired.jsonl","a").write(json.dumps(rec)+"\n"); print(rec,flush=True)
    if f.returncode or not m1: print("FIRE FAIL",s,ascii(f.stdout[-500:]),ascii(f.stderr[-500:])); sys.exit(1)
    if int(m1.group(2))!=60: print("COST != 60, stop",rec); sys.exit(1)
