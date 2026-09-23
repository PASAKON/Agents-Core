import re, sys, math
import numpy as np
rows=[]
for l in open(sys.argv[1]):
    m=re.match(r"\s*([\d.]+) scale=([\d.]+) cx=\s*([\d.]+) cy=\s*([\d.]+) top=\s*([\d.]+) ncc=([\d.]+)",l)
    if m: rows.append(tuple(map(float,m.groups())))
A=np.array(rows)
E={
 "linear":lambda p:p,
 "sine.out":lambda p:np.sin(p*math.pi/2),
 "power1.out":lambda p:1-(1-p)**2,
 "power2.out":lambda p:1-(1-p)**3,
 "power3.out":lambda p:1-(1-p)**4,
 "power4.out":lambda p:1-(1-p)**5,
 "expo.out":lambda p:np.where(p>=1,1,1-2**(-10*p)),
 "circ.out":lambda p:np.sqrt(1-(p-1)**2),
 "back.out":lambda p:1+2.70158*(p-1)**3+1.70158*(p-1)**2,
 "power2.inOut":lambda p:np.where(p<.5,4*p**3,1-(-2*p+2)**3/2),
 "sine.inOut":lambda p:-(np.cos(math.pi*p)-1)/2,
}
wins=[(0,1.85,"opening drop only")]
for t0,t1,name in wins:
    W=A[(A[:,0]>=t0-1e-6)&(A[:,0]<t1)]
    t,s,cx,cy,top,ncc=W.T
    print(f"\n== {name}  frames={len(W)}  ncc min={ncc.min():.2f} median={np.median(ncc):.2f}")
    for lab,v in (("scale",s),("cy",cy),("cx",cx)):
        d=np.abs(np.diff(v))
        print(f"  {lab}: start {v[:3].mean():.2f}  end {v[-3:].mean():.2f}  biggest 1-frame jump {d.max():.2f} at t={t[1:][d.argmax()]:.3f}")
    # motion segment on cy (or scale if cy barely moves): 2%..98% of total change
    key = cy if abs(cy[-3:].mean()-cy[:3].mean())>40 else s
    a,b=key[:3].mean(),key[-3:].mean()
    if abs(b-a)<1e-6: continue
    p=(key-a)/(b-a)
    i0=np.argmax(p>0.02); i1=len(p)-np.argmax((p<0.98)[::-1])
    i1=min(i1,len(p)-1)
    dur=t[i1]-t[i0]
    print(f"  motion {t[i0]:.3f}->{t[i1]:.3f}  duration {dur:.3f}s ({round(dur*30)} frames)")
    if dur<=0.05: print("  -> hard cut (no in-between frames)"); continue
    seg=slice(max(i0-1,0),i1+1); tt=(t[seg]-t[max(i0-1,0)])/(t[i1]-t[max(i0-1,0)]); pp=np.clip(p[seg],-.2,1.2)
    res=sorted(((float(np.sqrt(np.mean((f(tt)-pp)**2))),n) for n,f in E.items()))
    print("  easing RMSE: "+"  ".join(f"{n} {r:.3f}" for r,n in res[:5]))
