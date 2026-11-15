"""python pipe.py NN a b   -> fire shots[a:b] then finish_batch (system python)."""
import sys,os,subprocess
os.environ["PYTHONIOENCODING"]="utf-8"
nn,a,b=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
sh=open("C:/mooniex/ep4s/shots.txt").read().split()[a:b]
r=subprocess.run(["python","run_batch.py"]+sh,cwd="C:/mooniex/ep4s")
if r.returncode: print("RUN_BATCH STOPPED rc",r.returncode); sys.exit(1)
subprocess.run(["python","finish_batch.py",nn]+sh,cwd="C:/mooniex/ep4s")
