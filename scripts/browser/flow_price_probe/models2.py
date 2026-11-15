from helpers import *
t=Tab(sys.argv[1])
OPEN="""(()=>{if(document.querySelector('button[role=menuitem]')) return 'open'; const b=[...document.querySelectorAll('flow-prompt-box-settings button')].find(x=>/Omni|Veo/.test(x.innerText)&&x.getAttribute('aria-haspopup')); if(!b) return 'nomodelbtn'; b.click(); return 'clicked'})()"""
def pick(prefix):
    return t.ev("(()=>{const o=[...document.querySelectorAll('button[role=menuitem]')].find(e=>e.innerText.replace(/\s+/g,' ').trim().startsWith(%s)); if(!o) return 'noopt'; o.click(); return 'picked'})()"%json.dumps(prefix))
for m in ["Omni 1.2 Flash","Omni 1.1 Flash","Veo 3.1 - Lite","Veo 3.1 - Fast","Veo 3.1 - Quality"]:
    print(m,"open:",t.ev(OPEN)); time.sleep(1); print(" ",pick(m)); time.sleep(1.5)
    print(" PANEL:",panel(t))
