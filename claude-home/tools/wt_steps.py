"""Worktree cleanup, CEO order 2026-09-05, split into auditable steps: dupes | preserve | remove | gate"""
import subprocess, os, sys, json
sys.path.insert(0, "/Users/gob/Projects/Agents")
from lib.config import get_project
STEP = sys.argv[1]
ROOT = "/Users/gob/Projects/Agents/worktrees"
NEVER = {"mooniex-agents__browser_operator__task-5c88321f"}
A = ["mooniex-agents__browser_operator__task-0d531808","mooniex-agents__developer__task-2a175884",
 "mooniex-claudeflow__developer__task-65398390","mooniex-claudeflow__developer__task-bfa50f99",
 "mooniex-claudeflow__developer__task-4c111a17","mooniex-claudeflow__developer__task-b45de2bd",
 "mooniex-webapp__exness-source-puller","mooniex-webapp__xm-signup-email"]
B = ["mooniex-agents__browser_operator__task-f693a4ee","mooniex-agents__browser_operator__task-90699119",
 "mooniex-agents__browser_operator__task-c0adb413","mooniex-agents__browser_operator__task-1b8d7945",
 "mooniex-agents__browser_operator__task-66d5a582","mooniex-agents__browser_operator__task-f351806c",
 "mooniex-agents__browser_operator__task-4da71aee","mooniex-agents__browser_operator__task-9ba8e06b",
 "mooniex-agents__browser_operator__task-a13469e9","mooniex-agents__browser_operator__task-da1c3064"]
COMFY = ["comfy-runpod-worker__browser_operator__task-610ce4dc","comfy-runpod-worker__developer__task-3417a066"]
def git(wt,*a,check=True):
    r=subprocess.run(["git","-C",wt,*a],capture_output=True,text=True)
    if check and r.returncode: raise RuntimeError(f"git {' '.join(a)} @ {os.path.basename(wt)}: {r.stderr.strip()[:200]}")
    return r.returncode,r.stdout.strip()
def clean(wt): return git(wt,"status","--porcelain")[1]==""
def merged(wt): return git(wt,"merge-base","--is-ancestor","HEAD","main",check=False)[0]==0
def pushed(wt):
    rc,_=git(wt,"rev-parse","--abbrev-ref","--symbolic-full-name","@{u}",check=False)
    return rc==0 and git(wt,"rev-list","--count","@{u}..HEAD")[1]=="0"
def proj_of(n): return n.split("__",1)[0]
def task_of(n): return n.split("__task-")[1] if "__task-" in n else n
if STEP=="dupes":
    wt=os.path.join(ROOT,"mooniex-agents__browser_operator__task-c0adb413"); n=0
    for l in git(wt,"status","--porcelain")[1].splitlines():
        p=l[3:].strip()
        if l.startswith("??") and p.lower().endswith(".mp4"):
            m=os.path.join("/Users/gob/Projects/Agents",p)
            assert os.path.isfile(m) and subprocess.run(["cmp","-s",os.path.join(wt,p),m]).returncode==0, p
            os.remove(os.path.join(wt,p)); n+=1
    print("removed duplicate MP4 copies:",n)
    for c in COMFY:
        t=os.path.join(ROOT,c,"TASK.md")
        if os.path.exists(t): os.remove(t); print("removed regenerable",c+"/TASK.md")
elif STEP=="preserve":
    for n in B:
        wt=os.path.join(ROOT,n)
        if not os.path.isdir(wt): print("missing",n); continue
        did=[]
        if not clean(wt):
            k=len(git(wt,"status","--porcelain")[1].splitlines())
            git(wt,"add","-A"); git(wt,"commit","-q","-m",f"wip(task-{task_of(n)}): preserve worktree state before cleanup (IRON-RULES §48)\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01PiaYLbxJV3Nq22ZhwQk45r"); did.append(f"committed {k}")
        if not pushed(wt):
            br=git(wt,"rev-parse","--abbrev-ref","HEAD")[1]; git(wt,"push","-q","-u","origin",br); did.append(f"pushed {br}")
        print(f"{n}: {', '.join(did) or 'already clean+pushed'} | clean={clean(wt)} pushed={pushed(wt)}")
elif STEP in ("gate","remove"):
    tot=0; done=0
    for n in A+B+COMFY:
        assert n not in NEVER
        wt=os.path.join(ROOT,n)
        if not os.path.isdir(wt): print("missing",n); continue
        mb=int(subprocess.run(["du","-sk",wt],capture_output=True,text=True).stdout.split()[0])/1024
        c,m,p=clean(wt),merged(wt),pushed(wt)
        ok=c and (m or p)
        if STEP=="gate" or not ok:
            print(f"{'OK  ' if ok else 'LEFT'} {n:58} {mb:6.0f}MB clean={c} merged={m} pushed={p}"); continue
        repo=get_project(proj_of(n))["path"]
        r=subprocess.run(["git","-C",repo,"worktree","remove",wt],capture_output=True,text=True)
        if r.returncode: print(f"FAIL {n}: {r.stderr.strip()[:200]}"); continue
        tot+=mb; done+=1; print(f"removed {n} ({mb:.0f}MB)")
    print(f"== {STEP}: {done} removed, {tot/1024:.2f} GB")
