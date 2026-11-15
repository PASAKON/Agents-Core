# -*- coding: utf-8 -*-
"""Ghost EP5 opening clips (task-c791c9d0), raw-CDP, start-frame-only. Run on winbox:
  C:/mooniex/pwvenv/Scripts/python.exe go4.py <bal|state|up|prep|probe|set N|fire> <SHOT e.g. S01-01> ; HARD cap 18 credits/clip, ONE submit click.
Plates in C:/mooniex/ghost_flow/ep05/plates/."""
from cdp import *
import re, sys
STEP = sys.argv[1]; SHOT = sys.argv[2] if len(sys.argv) > 2 else "S01-01"
if STEP == "set": SHOT = sys.argv[3] if len(sys.argv) > 3 else "S01-01"
CAP = 18; DIR = "C:/mooniex/ghost_flow/ep05/plates/"; NAME = SHOT + ".png"
ACTIONS = {
"S01-01": "A chained locker door in a dark hospital cold-storage room. The heavy chain links tremble and sway as something knocks softly from inside; the padlock swings. Slow camera drift.",
"S01-02": "Close on the chain across the locker. The links tremble and rattle as faint knocking is heard from inside, the padlock swinging. Slow camera push-in.",
"S01-03": "Reverse angle: the chained locker door shudders as something knocks from inside, the chain rattles and sways, and the night orderly in the background flinches. Slow camera drift.",
"S01-04": "An anonymous night orderly reacts to the warning: he slowly turns his head toward the sound, freezes, and holds his breath, shoulders tense. Slow camera drift.",
"S01-05": "Close on the night orderly: his head turns slowly, he swallows and breathes in restrained, shaky breaths while his eyes stay fixed on the locker. Slow camera push-in.",
"S01-06": "A hand grips the emergency cooling lever and pulls it down; the lever pivots and clunks into place while the locker stays closed. Overhead lights flicker once. Slow camera drift.",
"S02-01": "Non, a young man, walks slowly toward an old suburban hospital building that is intact. His six-step walk grows slightly smaller as he approaches; a lamp flickers. Slow camera drift.",
"S02-02": "Close on Non as he walks toward the old hospital, slows, stops and looks up at the building. Slow camera drift.",
"S02-03": "Reverse angle from the hospital entrance: Non walks closer through the dark yard toward the camera, glancing back over his shoulder. Slow camera drift.",
"S02-04": "At the night duty desk Non opens the temperature record book; the page bends and settles under his hand. A desk lamp flickers. Slow camera drift.",
"S02-05": "At the duty desk Non holds a pen and writes in the temperature record, the pen following writing strokes across the page, then pauses. Slow camera drift.",
}
PREFIX = "The attached first frame is second 0; keep characters, costume, room and lighting exactly, and animate forward from it. "
SUFFIX = (" Eerie, slow and tense horror mood, paper-craft illustrated style, cool blue-grey light, deep shadows. "
"Purposeful motion: characters act, objects move (chains sway, doors, lights flicker), slow camera drift. "
"No glowing objects, no orbs, no magic light. No signs, banners, plaques or written marks anywhere in frame. No blood, no gore.")
PROMPT = PREFIX + ACTIONS[SHOT] + SUFFIX
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
    has = lambda: t.ev("document.querySelectorAll('[aria-label=\"%s\"]').length" % NAME)
    if has(): print("have")
    else:
        t.call("Page.setInterceptFileChooserDialog", enabled=True)
        t.click("document.querySelector('[aria-label=\"เมนูเพิ่มสื่อ\"]')"); time.sleep(1)
        t.click("[...document.querySelectorAll('[role=menuitem]')].find(e=>e.innerText.includes('อัปโหลด'))")
        ev = None; t0 = time.time()
        while time.time() - t0 < 15 and not ev:
            time.sleep(0.5); t.events += []
            t.s.settimeout(1)
            try: r = t._recv(); t.events.append(r)
            except Exception: pass
            ev = next((e for e in t.events if e.get("method") == "Page.fileChooserOpened"), None)
        print("chooser", ev and ev["params"])
        t.call("DOM.setFileInputFiles", files=[DIR.replace("/", "\\") + NAME], backendNodeId=ev["params"]["backendNodeId"])
        t.call("Page.setInterceptFileChooserDialog", enabled=False)
        for _ in range(60):
            if has(): break
            time.sleep(1)
        print("uploaded", has())
elif STEP == "prep":
    for i in (0, 1):
        if t.ev("!!document.querySelectorAll('.frame-trigger')[%d].querySelector('img.chip-image')" % i):
            t.click("document.querySelectorAll('.frame-trigger')[%d].querySelector('button.chip-container')" % i); time.sleep(1)
    t.click("document.querySelectorAll('.frame-trigger')[0].querySelector('button.empty-chip')"); time.sleep(1.5)
    t.click("document.querySelector('.cdk-overlay-container input[placeholder=\"ค้นหาเนื้อหา\"]')")
    t.call("Input.insertText", text=SHOT); time.sleep(2)
    t.click("[...document.querySelectorAll('.cdk-overlay-container .asset-item')].find(e=>e.innerText.includes('%s'))" % NAME); time.sleep(1.5)
    # row click may attach the frame at once (picker closes); only if the slot is still empty press the add <button>
    time.sleep(1.5)
    filled = lambda: t.ev("!!document.querySelectorAll('.frame-trigger')[0].querySelector('img.chip-image')")
    ADD = "[...document.querySelectorAll('.cdk-overlay-container button')].filter(e=>e.innerText.includes('เพิ่มไปยังพรอมต์')).pop()"
    for attempt in range(3):
        if filled(): break
        for _ in range(8):
            if t.ev("!!(%s)" % ADD): break
            time.sleep(0.5)
        if t.ev("!!(%s)" % ADD):
            time.sleep(1.0); t.click(ADD)
            for _ in range(8):
                time.sleep(0.5)
                if filled(): break
    print("slots", slots())
    t.ev("(()=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('selectAll'); document.execCommand('delete')})()")
    t.ev("(()=>{const e=document.querySelector('[contenteditable=true]'); e.focus(); document.execCommand('insertText',false,%s)})()" % json.dumps(PROMPT)); time.sleep(0.8)
    print("prompt_ok", prompt_ok())
elif STEP == "probe":
    print("panel:", panel()); t.key("Escape", "Escape", 27)
elif STEP == "set":
    panel()
    t.ev(r"""(()=>{const e=[...document.querySelectorAll('flow-prompt-box-settings mat-button-toggle')].find(e=>/(^|\s)720p(\s|$)/.test(e.innerText.replace(/\s+/g,' ').trim())); if(e) e.querySelector('button').click()})()"""); time.sleep(0.8)
    v = int(sys.argv[2])
    t.ev("(()=>{const i=document.querySelector('flow-duration-slider input'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,%d); i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true}))})()" % v); time.sleep(1)
    print("panel:", (t.ev("(document.querySelector('flow-prompt-box-settings')||{}).innerText||''") or "").replace("\n", " | ")); t.key("Escape", "Escape", 27)
elif STEP == "fire":
    assert prompt_ok(), "prompt mismatch"; assert slots() == "[true,false]", "slots " + str(slots())
    pn = panel(); t.key("Escape", "Escape", 27); time.sleep(0.6)
    assert "Omni 1.2 Flash" in pn and "720p" in pn, pn[:300]
    est = int(re.search(r"การสร้างจะใช้ (\d+) เครดิต", pn).group(1)); print("est", est, "|", pn[:300]); assert est <= CAP
    b0 = bal(); print("bal before", b0)
    t.click("document.querySelector('button[aria-label=\"เริ่มสร้าง\"]')"); time.sleep(12)
    print("bal after", bal(), "path", t.ev("location.pathname"))
else: print("unknown step")
