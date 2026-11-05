import time, sys, json
from playwright.sync_api import sync_playwright
S=sys.argv[1]; label=sys.argv[2]; code=sys.argv[3]
kit=json.load(open(S+"/kit.json",encoding="utf-8"))["tr"][code]
JS_ROW="""(label) => { const lab=[...document.querySelectorAll('div.language-text')].find(e=>e.innerText.trim()===label); if(!lab) return null; const b=lab.getBoundingClientRect(); return b.y+b.height/2; }"""
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    if page.locator("textarea:visible").count()==0:
        y=page.evaluate(JS_ROW,label); print("row y",y)
        page.mouse.move(700,y); time.sleep(1); page.mouse.move(677,y+1); time.sleep(1); page.mouse.click(677,y+1); time.sleep(3)
    print("dialog lang:", page.evaluate("() => { const t=document.body.innerText; const i=t.indexOf('คำแปล (โดย'); return t.slice(i, i+120).split(String.fromCharCode(10)).join(' / ') }"))
    tas=page.locator("ytcp-dialog textarea:visible, tp-yt-paper-dialog textarea:visible, textarea:visible")
    print("textareas", tas.count(), [tas.nth(i).get_attribute("aria-label") for i in range(tas.count())])
    editable=[i for i in range(tas.count()) if not tas.nth(i).is_disabled() and not tas.nth(i).get_attribute("readonly")]
    print("editable idx", editable)
    t_ta, d_ta = tas.nth(editable[0]), tas.nth(editable[1])
    t_ta.click(); t_ta.fill(kit["title"]); time.sleep(.5)
    d_ta.click(); d_ta.fill(kit["description"]); time.sleep(.5)
    print("title len", len(t_ta.input_value()), "desc len", len(d_ta.input_value()), "expected", len(kit["title"]), len(kit["description"]))
    page.screenshot(path=S+f"/shots/13-{code}.png")
    if len(sys.argv)>4 and sys.argv[4]=="publish":
        page.get_by_text("เผยแพร่", exact=True).last.click(); time.sleep(4)
        print(page.evaluate("() => document.body.innerText.split(String.fromCharCode(10)).join(' / ').slice(300,900)"))
