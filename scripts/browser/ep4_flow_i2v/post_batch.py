"""Post-batch chores (system python + ffmpeg + PIL). Usage: python post_batch.py NN shot,shot,... [--refused shot,...]
1. strip (frames 0/5/10/14 s per clip) -> C:/mooniex/ep4s/strip_NN.jpg
2. scp clips to Contabo flow/ep04, compare md5 there, append MD5SUMS, delete the local copy only on match
3. scp the strip to Contabo plan/EP04-flow-strip-NN.jpg
Media never goes in git."""
import sys,subprocess,hashlib,os
from PIL import Image,ImageDraw
W="C:/mooniex/ep4s"; DST="/opt/MoonieXHQ/Work/cn-series"
nn=sys.argv[1]; shots=[s for s in sys.argv[2].split(",") if s]
def md5(f): return hashlib.md5(open(f,"rb").read()).hexdigest()
tw,th=320,180; rows=[]
for s in shots:
    clip=f"{W}/clips/EP04-S{s}_v1.mp4"; ims=[]
    for t in (0,5,10,14):
        out=f"{W}/fr/{s}_{t}.jpg"; os.makedirs(f"{W}/fr",exist_ok=True)
        subprocess.run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",clip,"-frames:v","1","-vf",f"scale={tw}:{th}",out],check=True)
        ims.append(Image.open(out))
    rows.append((s,ims))
sheet=Image.new("RGB",(60+tw*4,th*len(rows)),"black"); dr=ImageDraw.Draw(sheet)
for i,(s,ims) in enumerate(rows):
    dr.text((4,i*th+4),"S"+s,fill="white")
    for j,im in enumerate(ims): sheet.paste(im,(60+j*tw,i*th))
strip=f"{W}/strip_{nn}.jpg"; sheet.save(strip,quality=80)
subprocess.run(["scp","-q",strip,f"contabo:{DST}/plan/EP04-flow-strip-{nn}.jpg"],check=True)
ok=[]; lines=[]
for s in shots:
    f=f"{W}/clips/EP04-S{s}_v1.mp4"; loc=md5(f)
    subprocess.run(["scp","-q",f,f"contabo:{DST}/flow/ep04/"],check=True)
    r=subprocess.run(["ssh","contabo",f"md5sum {DST}/flow/ep04/EP04-S{s}_v1.mp4"],capture_output=True,text=True).stdout.split()[0]
    if r==loc: ok.append(s); lines.append(f"{loc}  EP04-S{s}_v1.mp4"); os.remove(f)
    else: print("MD5 MISMATCH",s,loc,r)
if lines: subprocess.run(["ssh","contabo",f"cat >> {DST}/flow/ep04/MD5SUMS"],input="\n".join(lines)+"\n",text=True,check=True)
print("verified+deleted local:",ok,"strip:",strip)
