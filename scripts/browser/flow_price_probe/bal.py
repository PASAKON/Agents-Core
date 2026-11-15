import sys,re,time; sys.path.insert(0,".")
from cdp import *
t=Tab(sys.argv[1])
print("btn",t.ev("""(()=>{const b=document.querySelector('[aria-label="รายละเอียดบัญชี"]'); if(!b) return 'none'; b.click(); return 'clicked'})()"""))
time.sleep(2)
txt=t.ev("document.body.innerText") or ""
t.call("Input.dispatchKeyEvent",type="keyDown",key="Escape",code="Escape",windowsVirtualKeyCode=27)
t.call("Input.dispatchKeyEvent",type="keyUp",key="Escape",code="Escape",windowsVirtualKeyCode=27)
i=txt.find("Google Flow")
for m in re.finditer(r"[^\n]*เครดิต[^\n]*",txt): print("LINE:",m.group(0)[:120])
