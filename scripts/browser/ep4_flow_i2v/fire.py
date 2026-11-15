from drv import *
import sys,re
shot=sys.argv[1]; CAP=60  # per-clip hard cap
# task-255aea73 cap: read from task, not hard-coded. START_BAL = balance before the first shot of this task;
# TASK_CAP = 5760 (96 x 60); FLOOR = never let the balance drop under 1000. Override via env.
import os
TASK_CAP=int(os.environ.get("TASK_CAP","5760")); START_BAL=int(os.environ.get("START_BAL","6810")); FLOOR=int(os.environ.get("BAL_FLOOR","1000"))
d=D()
def bal(p):
    p.locator('[aria-label="รายละเอียดบัญชี"]').first.click(force=True); p.wait_for_timeout(1800)
    m=re.search(r"เครดิต Google Flow ([\d,]+) เครดิต",p.evaluate("document.body.innerText"))
    p.locator(".cdk-overlay-container button").filter(has_text="close").first.click(timeout=5000); p.wait_for_timeout(800)
    assert p.evaluate("document.querySelectorAll('.cdk-overlay-backdrop').length")==0,"backdrop left"
    return int(m.group(1).replace(",","")) if m else None
try:
    p=d.page
    want=open(f"C:/mooniex/ep4s/prompt_S{shot}.txt",encoding="utf-8").read()
    got=p.evaluate("[...document.querySelectorAll('[contenteditable=true] p')].map(x=>x.innerText).join(' ')")
    norm=lambda s:re.sub(r"\s+"," ",s).strip()
    assert norm(got)==norm(want),"prompt mismatch"
    slots=p.evaluate(r"""JSON.stringify([...document.querySelectorAll('.frame-trigger')].map(e=>!!e.querySelector('img.chip-image')))""")
    print("slots start/end has image:",slots)
    assert slots=="[true,false]","slots must be start-only: "+slots
    p.get_by_label("ทริกเกอร์การตั้งค่า").click(); p.wait_for_timeout(900)
    pn=p.evaluate("(document.querySelector('flow-prompt-box-settings')||{}).innerText||''").replace("\n"," | ")
    p.keyboard.press("Escape"); p.wait_for_timeout(500)
    m=re.search(r"Omni 1\.2 Flash.*ความยาว \| 15 วินาที.*การสร้างจะใช้ (\d+) เครดิต",pn); assert m,"settings: "+pn
    est=int(m.group(1)); assert est<=CAP,f"estimate {est}"
    bar=p.evaluate("(()=>{let e=document.querySelector('[contenteditable=true]'); for(let i=0;i<8&&e;i++){ if((e.innerText||'').includes('720p')) return e.innerText; e=e.parentElement } return ''})()").replace(chr(10)," ")
    print("bar:",bar[-120:]); assert "720p" in bar and "15 วินาที" in bar and "x1" in bar, "not 720p/15s/x1: "+bar[-120:]
    b0=bal(p); print("balance before",b0,"estimate",est)
    assert b0 and b0>=est and (START_BAL-(b0-est))<=TASK_CAP and (b0-est)>=FLOOR, f"total cap/floor: b0={b0} est={est} start={START_BAL} cap={TASK_CAP} floor={FLOOR}"
    btn=p.locator('button[aria-label="เริ่มสร้าง"]').first
    print("CLICK submit"); btn.click(timeout=8000)
    p.wait_for_timeout(12000)
    b1=bal(p); print("balance after",b1,"delta",None if b1 is None else b0-b1)
    print("url path:",p.evaluate("location.pathname.slice(0,12)"))
    print(p.evaluate(r"document.body.innerText.replace(/\n+/g,' | ').slice(0,200)"))
finally: d.close()
