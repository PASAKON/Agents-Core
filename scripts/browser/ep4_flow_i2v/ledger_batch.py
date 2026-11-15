"""Append credit-ledger rows for one batch. Run from the repo root with system python (fcntl is stubbed on Windows).
Usage: python scripts/browser/ep4_flow_i2v/ledger_batch.py NN   (reads C:/mooniex/ep4s/fired.jsonl rows tagged batch NN,
and C:/mooniex/ep4s/refused.jsonl rows {"shot","batch","reason"} whose credits were refunded)."""
import sys,types,json
sys.stdout.reconfigure(encoding="utf-8")
fc=types.ModuleType("fcntl"); fc.LOCK_EX=2; fc.LOCK_UN=8; fc.flock=lambda *a,**k:None; sys.modules["fcntl"]=fc
sys.path.insert(0,".")
from tools import credit_ledger as cl
nn=sys.argv[1]; TASK="task-255aea73"
base=["add","--who","browser_operator-"+TASK,"--engine","flow","--channel","CnDrama","--kind","production","--task",TASK]
fired=[json.loads(l) for l in open("C:/mooniex/ep4s/fired.jsonl") if l.strip()]
refused={}
try:
    for l in open("C:/mooniex/ep4s/refused.jsonl"):
        if l.strip(): r=json.loads(l); refused[r["shot"]]=r
except FileNotFoundError: pass
for r in fired:
    if r.get("batch")!=nn: continue
    s=r["shot"]
    cl.main(base+["--credits","60","--purpose",f"EP04-S{s} Omni 1.2 Flash 720p 15s 16:9 x1 image-to-video, start frame only (batch {nn} of the 96-shot run, CEO Q-20261115-0316-1909, cap 5760)","--before",str(r["before"]),"--after",str(r["after"])])
    if s in refused:
        cl.main(["add","--who","browser_operator-"+TASK,"--engine","flow","--channel","CnDrama","--kind","other","--task",TASK,"--credits","60","--purpose",f"REFUND of the EP04-S{s} row above: Flow refused the prompt ({refused[s]['reason']}) and returned the credits; no clip made","--note","refund row; negates the previous S"+s+" spend row"])
