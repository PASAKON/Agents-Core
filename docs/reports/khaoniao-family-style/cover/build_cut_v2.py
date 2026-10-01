import subprocess, sys
S="/tmp/claude-0/-opt-MoonieXHQ-Agents-Core/b593810f-ebad-49cc-8ae4-51d5c7879552/scratchpad"; P=S+"/ep1prod"
def src(n):
    if n in (8,17): return f"{S}/rs1/shot-{n:02d}.mp4"
    if n==6: return f"{P}/shot-06-patched.mp4"
    return f"{P}/shot-{n:02d}.mp4"
TITLE, END, MORN = 2.6, 3.5, 2.4
segs=[("v",1,0.8,9.2,0.03)]+[("v",n,0,10.0,0.03) for n in (2,3,4)]+[("v",5,0,8.9,0.3),("v",6,0,10.0,0.03),
      ("card","title",0,TITLE,0),("v",7,0,10.0,0.03),("v",8,0,10.0,0.03),("v",1,6.0,4.0,0.03)]+[("v",n,0,10.0,0.03) for n in range(9,19)]+[("card","end",0,END,0)]
cmd=["ffmpeg","-y","-v","error"]; fc=[]; labels=""; k=0; t=0.0; marks=[]
for i,(kind,n,ss,dur,fo) in enumerate(segs):
    marks.append((i,kind,n,round(t,2)))
    if kind=="v":
        if ss: cmd+=["-ss",str(ss)]
        cmd+=["-t",str(dur),"-i",src(n)]
        vin,ain=k,k; k+=1
    else:
        cmd+=["-loop","1","-framerate","24","-t",str(dur),"-i",f"{S}/cards/card-{n}.png","-f","lavfi","-t",str(dur),"-i","anullsrc=r=48000:cl=mono"]
        vin,ain=k,k+1; k+=2
    if kind=="v":
        fc.append(f"[{vin}:v]setsar=1,fps=24,format=yuv420p[v{i}]")
        fc.append(f"[{ain}:a]aresample=48000,aformat=channel_layouts=mono,afade=t=in:d=0.03,afade=t=out:st={dur-fo:.2f}:d={fo}[a{i}]")
    else:
        fc.append(f"[{vin}:v]scale=720:1280:flags=lanczos,setsar=1,fps=24,format=yuv420p[v{i}]")
        fc.append(f"[{ain}:a]aformat=channel_layouts=mono[a{i}]")
    labels+=f"[v{i}][a{i}]"; t+=dur
# "เมื่อเช้า" over the first MORN s of shot 2 (segment index 1)
cmd+=["-loop","1","-framerate","24","-t",str(MORN),"-i",f"{S}/cards/card-morning.png"]
mi=k
fc.append(f"[{mi}:v]scale=720:1280:flags=lanczos,format=rgba,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={MORN-0.3:.1f}:d=0.3:alpha=1[mo]")
fc=[f.replace("[v1]","[v1pre]") if f.endswith("[v1]") else f for f in fc]
fc.append("[v1pre][mo]overlay=0:0:eof_action=pass,format=yuv420p[v1]")
fc.append(f"{labels}concat=n={len(segs)}:v=1:a=1[v][a]")
out=sys.argv[1]
cmd+=["-filter_complex",";".join(fc),"-map","[v]","-map","[a]","-c:v","libx264","-crf","21","-preset","medium","-c:a","aac","-b:a","128k","-movflags","+faststart",out]
subprocess.run(cmd,check=True)
for m in marks: print(m)
print("total %.2f"%t)
