"""Poll the feed (no reload) until none of the given shots is still generating. Prints JSON {shot: done|refused|failed|nocard}.
Usage: python scan_batch.py 013 014 ...  (timeout ~9 min)"""
from drv import *
import re,sys,json,time
sheet=open("C:/mooniex/ep4s/EP04-FULL-SHEET.md",encoding="utf-8").read()
def snip(shot):
    blk=re.search(r"## EP04-S%s \|.*?(?=\n## EP04-S|\Z)"%shot,sheet,re.S).group(0)
    body=re.search(r"Google Flow prompt \(15s\): (.*?)\n\nLines:",blk,re.S).group(1)
    return re.sub(r"\s+"," ",body.split("Any emblem is abstract relief only. ")[1][:60])
JS=r"""(sn)=>{ const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); let n,hit=null;
  while(n=w.nextNode()){ if(n.textContent.replace(/\s+/g,' ').includes(sn)){ hit=n.parentElement; break } }
  if(!hit) return 'nocard';
  let e=hit,best=hit; for(let i=0;i<14&&e;i++){ const c=(e.innerText.match(/The attached first frame/g)||[]).length; if(c===1) best=e; else break; e=e.parentElement }
  const t=best.innerText;
  if(/ล้มเหลว|ละเมิดนโยบาย/.test(t)) return 'refused:'+t.replace(/\s+/g,' ').slice(0,260);
  if(/\d+%/.test(t.slice(0,40))) return 'pending';
  return 'done' }"""
d=D()
try:
    p=d.page; shots=sys.argv[1:]; t0=time.time(); res={}
    while True:
        res={s:p.evaluate(JS,snip(s)) for s in shots}
        if all(not v.startswith("pending") for v in res.values()) or time.time()-t0>540: break
        p.wait_for_timeout(15000)
    print(json.dumps(res,ensure_ascii=False))
finally: d.close()
