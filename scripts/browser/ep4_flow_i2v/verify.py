import sys,glob,io
from PIL import Image
import numpy as np
def sig(im): return np.asarray(im.convert("RGB").resize((32,18)),dtype=float)
chip=sig(Image.open(sys.argv[1]))
best=[]
for f in glob.glob("C:/mooniex/ep4s/stills/EP04-S*.png"):
    best.append((float(np.abs(sig(Image.open(f))-chip).mean()),f.split("-")[-1][:-4]))
best.sort(); print(best[:3])
exp=sys.argv[2] if len(sys.argv)>2 else None
if exp: sys.exit(0 if best[0][1]==exp and best[0][0]<8 else 1)
