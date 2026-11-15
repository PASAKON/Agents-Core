import sys,time,json; sys.path.insert(0,".")
from cdp import *
def panel(t): return (t.ev("(document.querySelector('flow-prompt-box-settings')||{}).innerText||'nopanel'") or "").replace("\n"," | ")
def checked(t): return t.ev("[...document.querySelectorAll('flow-prompt-box-settings mat-button-toggle.mat-button-toggle-checked')].map(e=>e.innerText.trim().replace(/\n/g,' ')).join(' ; ')")
def click_toggle(t,label):
    return t.ev("(()=>{const els=[...document.querySelectorAll('flow-prompt-box-settings mat-button-toggle')].filter(e=>e.innerText.replace(/\s+/g,' ').trim().endsWith(%s)||e.innerText.includes(%s)); if(!els.length) return 'none'; els[0].querySelector('button').click(); return 'clicked '+els.length})()"%(json.dumps(label),json.dumps(label)))
