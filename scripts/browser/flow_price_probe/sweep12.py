from helpers import *
import re
t=Tab(sys.argv[1])
def setv(v):
    return t.ev("(()=>{const i=document.querySelector('flow-duration-slider input'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,%d); i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true})); return i.value})()"%v)
def price():
    p=panel(t); m=re.search(r"ใช้ (\d[\d,]*) เครดิต",p); d=re.search(r"ความยาว \| (\d+) วินาที",p); return (m.group(1) if m else "?"), (d.group(1) if d else "?")
def clickt(label):
    return t.ev("(()=>{const e=[...document.querySelectorAll('flow-prompt-box-settings mat-button-toggle')].find(e=>/(^|\s)%s(\s|$)/.test(e.innerText.replace(/\s+/g,' ').trim())); if(!e) return 'none'; e.querySelector('button').click(); return 'ok'})()"%label)
for r in ["360p","720p"]:
    print(r,clickt(r)); time.sleep(1)
    print("  checked:",[x for x in t.ev("JSON.stringify([...document.querySelectorAll('flow-prompt-box-settings mat-button-toggle.mat-button-toggle-checked')].map(e=>e.innerText.replace(/\s+/g,' ').trim()))") .split('","')])
    out=[]
    for v in range(0,13):
        setv(v); time.sleep(0.6); pr,d=price(); out.append(f"{d}s={pr}")
    print("  ",r," ".join(out))
