from helpers import *
import re
t=Tab(sys.argv[1])
OPEN="""(()=>{if(document.querySelector('button[role=menuitem]')) return 'open'; const b=[...document.querySelectorAll('flow-prompt-box-settings button')].find(x=>/Omni|Veo/.test(x.innerText)&&x.getAttribute('aria-haspopup')); if(!b) return 'nomodelbtn'; b.click(); return 'clicked'})()"""
def pick(prefix):
    return t.ev("(()=>{const o=[...document.querySelectorAll('button[role=menuitem]')].find(e=>e.innerText.replace(/\s+/g,' ').trim().startsWith(%s)); if(!o) return 'noopt'; o.click(); return 'picked'})()"%json.dumps(prefix))
def toggles():
    return json.loads(t.ev("JSON.stringify([...document.querySelectorAll('flow-prompt-box-settings mat-button-toggle')].map(e=>({t:e.innerText.replace(/\s+/g,' ').trim(),c:e.className.includes('checked')})))"))
def price():
    m=re.search(r"ใช้ (\d[\d,]*) เครดิต",panel(t)); return m.group(1) if m else "?"
def clickt(label):
    return t.ev("(()=>{const e=[...document.querySelectorAll('flow-prompt-box-settings mat-button-toggle')].find(e=>e.innerText.replace(/\s+/g,' ').trim().endsWith(%s)); if(!e) return 'none'; e.querySelector('button').click(); return 'ok'})()"%json.dumps(label))
for m in sys.argv[2:]:
    t.ev(OPEN); time.sleep(0.8); pick(m); time.sleep(1.5)
    tg=toggles()
    cur=[x['t'] for x in tg if x['c']]
    res=[x['t'] for x in tg if re.fullmatch(r"\d+p",x['t'])]
    dur=[x['t'] for x in tg if 'วินาที' in x['t']]
    print("==",m,"| default checked:",cur,"| res opts:",res,"| dur opts:",dur,"| price",price())
    for r in (res or [None]):
        if r: clickt(r); time.sleep(0.8)
        for d in (dur or [None]):
            if d: clickt(d); time.sleep(0.8)
            print("   ",m,r,d,"->",price(),"| checked:",[x['t'] for x in toggles() if x['c']])
