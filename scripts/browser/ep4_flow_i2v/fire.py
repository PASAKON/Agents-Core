from drv import *
import sys,re
shot=sys.argv[1]; CAP=60
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
    b0=bal(p); print("balance before",b0,"estimate",est)
    assert b0 and b0>=est and (6930-(b0-est))<=180, "total cap"
    btn=p.locator('button[aria-label="เริ่มสร้าง"]').first
    print("CLICK submit"); btn.click(timeout=8000)
    p.wait_for_timeout(12000)
    b1=bal(p); print("balance after",b1,"delta",None if b1 is None else b0-b1)
    print("url path:",p.evaluate("location.pathname.slice(0,12)"))
    print(p.evaluate(r"document.body.innerText.replace(/\n+/g,' | ').slice(0,200)"))
finally: d.close()
