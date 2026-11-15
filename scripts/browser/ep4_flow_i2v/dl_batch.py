"""Download the 720p original of each given shot's finished card. Usage: python dl_batch.py 001 002 ...
Opens the card (click preview) -> /edit page -> ดาวน์โหลดสื่อ -> '720p ขนาดดั้งเดิม' only (refuses เครดิต/4K), saves clips/EP04-S###_v1.mp4."""
from drv import *
import re,sys,os
sheet=open("C:/mooniex/ep4s/EP04-FULL-SHEET.md",encoding="utf-8").read()
def snip(shot):
    blk=re.search(r"## EP04-S%s \|.*?(?=\n## EP04-S|\Z)"%shot,sheet,re.S).group(0)
    body=re.search(r"Google Flow prompt \(15s\): (.*?)\n\nLines:",blk,re.S).group(1)
    return re.sub(r"\s+"," ",body.split("Any emblem is abstract relief only. ")[1][:60])
MARK=r"""(sn)=>{ const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); let n,hit=null;
  while(n=w.nextNode()){ if(n.textContent.replace(/\s+/g,' ').includes(sn)){ hit=n.parentElement; break } }
  if(!hit) return 'nocard';
  let e=hit,best=hit; for(let i=0;i<14&&e;i++){ const c=(e.innerText.match(/The attached first frame/g)||[]).length; if(c===1) best=e; else break; e=e.parentElement }
  document.querySelectorAll('[data-pick]').forEach(x=>x.removeAttribute('data-pick')); best.setAttribute('data-pick','1');
  const bad=/ล้มเหลว|ละเมิดนโยบาย/.test(best.innerText); const pct=(best.innerText.match(/\d+%/)||[''])[0];
  return JSON.stringify({bad,pct,video:!!best.querySelector('video')}) }"""
d=D(); res={}
try:
    p=d.page; home="https://flow.google.com/project/fc0fa309-571a-4584-a099-710123b78c80"
    for shot in sys.argv[1:]:
        p.goto(home,wait_until="domcontentloaded"); p.wait_for_timeout(3500)
        r=p.evaluate(MARK,snip(shot))
        for _i in range(12):
            if r!="nocard": break
            p.mouse.move(500,300); p.mouse.wheel(0,600); p.wait_for_timeout(700); r=p.evaluate(MARK,snip(shot))
        print(shot,"card:",r,flush=True)
        if r=="nocard": res[shot]="nocard"; continue
        import json as _j; st=_j.loads(r)
        if st["bad"]: res[shot]="refused"; continue
        if st["pct"]: res[shot]="notready"; continue
        card=p.locator("[data-pick='1']"); card.evaluate("e=>e.scrollIntoView({block:'start'})"); p.wait_for_timeout(900)
        bb=card.bounding_box(); p.mouse.click(bb["x"]+140,bb["y"]+100); p.wait_for_timeout(3500)
        if "/edit/" not in p.url:
            card.evaluate("e=>e.scrollIntoView({block:'start'})"); p.wait_for_timeout(900); bb=card.bounding_box(); p.mouse.click(bb["x"]+140,bb["y"]+100); p.wait_for_timeout(3500)  # one retry
        if "/edit/" not in p.url: print("  not on edit:",p.url); res[shot]="noedit"; continue
        d.mute()
        p.locator('[aria-label="ดาวน์โหลดสื่อ"]').first.click(); p.wait_for_timeout(1200)
        it=p.get_by_role("menuitem").filter(has_text="720p").first
        txt=it.inner_text().replace("\n"," ")
        if "เครดิต" in txt or "4K" in txt: print("  REFUSE menu item:",txt); res[shot]="menu?"; continue
        with p.expect_download(timeout=120000) as dl: it.click()
        out=f"C:/mooniex/ep4s/clips/EP04-S{shot}_v1.mp4"; dl.value.save_as(out)
        print("  saved",out,os.path.getsize(out),"item:",txt,flush=True); res[shot]="ok"
finally: d.close()
print(res)
