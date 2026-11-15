# -*- coding: utf-8 -*-
"""Ghost EP5 S15 Flow jump-scare test (task-f6d259cc), raw-CDP. Run on winbox:
  C:/mooniex/pwvenv/Scripts/python.exe go3.py <bal|state|up|prep [end]|probe|set N|fire|dl> ; HARD cap 20 credits, ONE submit click.
Plates in C:/mooniex/ghost_flow/s15/: GR5-S15-CALM.png (start), GR5-S15-REVEAL.png (end)."""
from cdp import *
import re, sys
STEP = sys.argv[1]; CAP = 20; DIR = "C:/mooniex/ghost_flow/s15/"
START = "GR5-S15-CALM.png"; END = "GR5-S15-REVEAL.png"
USE_END = (len(sys.argv) > 2 and sys.argv[2] == "end") or STEP == "fire" and "end" in sys.argv
PROMPT = ("The attached first frame is second 0; keep characters, costume, corridor and lighting exactly. Horror jump scare. "
"For the first three seconds almost nothing moves: the young guard stands still outside the open lift, faint wet footprints lead to the threshold, the fluorescent light hums. "
"Then a sudden fast snap: the camera whips into the lift mirror and a pale long-haired woman in a hospital gown is suddenly there in the reflection, close, her hand raised beckoning, hold one beat. "
"Sharp, abrupt timing, no slow fade. Paper-craft illustrated style, cool blue-grey light. "
"No glowing objects, no orbs, no magic light. No signs, banners, plaques or written marks anywhere in frame. No blood, no gore.")
norm = lambda s: re.sub(r"\s+", " ", s or "").strip()
t, tid = open_tab(); t.mute()
def overlay_close():
    t.ev(r"""(()=>{const b=[...document.querySelectorAll('.cdk-overlay-container button')].find(b=>/close/.test(b.innerText)); if(b) b.click(); return 1})()"""); time.sleep(0.8)
def bal():
    t.ev(r"""document.querySelector('[aria-label="รายละเอียดบัญชี"]').click()"""); time.sleep(1.8)
    m = re.search(r"เครดิต Google Flow ([\d,]+) เครดิต", t.ev("document.body.innerText") or "")
    overlay_close()
    assert t.ev("document.querySelectorAll('.cdk-overlay-backdrop').length") == 0, "backdrop left"
    return int(m.group(1).replace(",", "")) if m else None
def panel():
    t.ev(r"""document.querySelector('[aria-label="ทริกเกอร์การตั้งค่า"]').click()"""); time.sleep(1.0)
    return (t.ev("(document.querySelector('flow-prompt-box-settings')||{}).innerText||''") or "").replace("\n", " | ")
def slots(): return t.ev("JSON.stringify([...document.querySelectorAll('.frame-trigger')].map(e=>!!e.querySelector('img.chip-image')))")
def prompt_ok(): return norm(t.ev("[...document.querySelectorAll('[contenteditable=true] p')].map(x=>x.innerText).join(' ')")) == norm(PROMPT)
if STEP == "bal": print("balance", bal())
elif STEP == "state": print(t.ev("location.pathname"), "| slots", slots(), "| prompt_ok", prompt_ok())
elif STEP == "up":
    for NAME in (START, END):
        has = lambda: t.ev("document.querySelectorAll('[aria-label=\"%s\"]').length" % NAME)
        if has(): print("have", NAME); continue
        t.call("Page.setInterceptFileChooserDialog", enabled=True)
        t.click("document.querySelector('[aria-label=\"เมนูเพิ่มสื่อ\"]')"); time.sleep(1)
        t.click("[...document.querySelectorAll('[role=menuitem]')].find(e=>e.innerText.includes('อัปโหลด'))")
        ev = None; t0 = time.time()
        while time.time() - t0 < 15 and not ev:
            t.s.settimeout(1)
            try: r = t._recv(); t.events.append(r)
            except Exception: pass
            ev = next((e for e in t.events if e.get("method") == "Page.fileChooserOpened"), None)
        t.events = [e for e in t.events if e.get("method") != "Page.fileChooserOpened"]
        print("chooser", bool(ev))
        t.call("DOM.setFileInputFiles", files=[(DIR + NAME).replace("/", "\\")], backendNodeId=ev["params"]["backendNodeId"])
        t.call("Page.setInterceptFileChooserDialog", enabled=False)
        for _ in range(60):
            if has(): break
            time.sleep(1)
        print("uploaded", NAME, has())
elif STEP == "prep":
    def fill(idx, name, q):
        if t.ev("!!document.querySelectorAll('.frame-trigger')[%d].querySelector('img.chip-image')" % idx):
            t.click("document.querySelectorAll('.frame-trigger')[%d].querySelector('button.chip-container')" % idx); time.sleep(1)
        t.click("document.querySelectorAll('.frame-trigger')[%d].querySelector('button.empty-chip')" % idx); time.sleep(1.5)
        t.click("document.querySelector('.cdk-overlay-container input[placeholder=\"ค้นหาเนื้อหา\"]')")
        t.call("Input.insertText", text=q); time.sleep(2)
        t.click("[...document.querySelectorAll('.cdk-overlay-container .asset-item')].find(e=>e.innerText.includes('%s'))" % name); time.sleep(1.5)
        if t.ev("[...document.querySelectorAll('.cdk-overlay-container button')].some(e=>e.innerText.includes('เพิ่มไปยังพรอมต์'))"):
            t.click("[...document.querySelectorAll('.cdk-overlay-container button')].filter(e=>e.innerText.includes('เพิ่มไปยังพรอมต์')).pop()"); time.sleep(2.5)
        print("slots", slots())
    fill(0, START, "S15-CALM")
    if USE_END: fill(1, END, "S15-REVEAL")
    t.ev("(()=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('selectAll'); document.execCommand('delete')})()")
    t.ev("(()=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('insertText',false,%s)})()" % json.dumps(PROMPT)); time.sleep(0.8)
    print("prompt_ok", prompt_ok())
elif STEP == "prompt":
    t.ev("(()=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('selectAll'); document.execCommand('delete')})()")
    t.ev("(()=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('insertText',false,%s)})()" % json.dumps(PROMPT)); time.sleep(0.8)
    print("prompt_ok", prompt_ok(), "slots", slots())
elif STEP == "probe":
    print("panel:", panel()); t.key("Escape", "Escape", 27)
elif STEP == "set":
    panel()
    t.ev(r"""(()=>{const e=[...document.querySelectorAll('flow-prompt-box-settings mat-button-toggle')].find(e=>/(^|\s)720p(\s|$)/.test(e.innerText.replace(/\s+/g,' ').trim())); if(e) e.querySelector('button').click()})()"""); time.sleep(0.8)
    v = int(sys.argv[2])
    t.ev("(()=>{const i=document.querySelector('flow-duration-slider input'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,%d); i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true}))})()" % v); time.sleep(1)
    print("panel:", (t.ev("(document.querySelector('flow-prompt-box-settings')||{}).innerText||''") or "").replace("\n", " | ")); t.key("Escape", "Escape", 27)
elif STEP == "fire":
    assert prompt_ok(), "prompt mismatch"; assert slots() == ("[true,true]" if USE_END else "[true,false]"), "slots " + str(slots())
    pn = panel(); t.key("Escape", "Escape", 27); time.sleep(0.6)
    assert "Omni 1.2 Flash" in pn and "720p" in pn, pn[:300]
    est = int(re.search(r"การสร้างจะใช้ (\d+) เครดิต", pn).group(1)); print("est", est, "|", pn[:300]); assert est <= CAP
    b0 = bal(); print("bal before", b0)
    t.click("document.querySelector('button[aria-label=\"เริ่มสร้าง\"]')"); time.sleep(12)
    print("bal after", bal(), "path", t.ev("location.pathname"))
else: print("unknown step")
