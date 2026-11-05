import time, sys, json
from playwright.sync_api import sync_playwright
S="C:/mooniex/khaohom-ep01b"; label=sys.argv[1]; code=sys.argv[2]; pub=len(sys.argv)>3
kit=json.load(open(S+"/kit.json",encoding="utf-8"))["tr"][code]
JS_ROW="""(label) => { const lab=[...document.querySelectorAll('div.language-text')].find(e=>e.innerText.trim()===label); if(!lab) return null; const b=lab.getBoundingClientRect(); return b.y+b.height/2; }"""
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    if page.locator("textarea:visible").count()==0:
        y=page.evaluate(JS_ROW,label); print("row y",y)
        page.mouse.move(700,y); time.sleep(1); page.mouse.move(677,y+1); time.sleep(1); page.mouse.click(677,y+1); time.sleep(3)
    tas=page.locator("textarea:visible")
    ed=[i for i in range(tas.count()) if not tas.nth(i).is_disabled() and not tas.nth(i).get_attribute("readonly")]
    print("textareas", tas.count(), "editable", ed)
    t_ta, d_ta = tas.nth(ed[0]), tas.nth(ed[1])
    print("old title:", t_ta.input_value()); print("desc len now", len(d_ta.input_value()), "kit", len(kit["description"]), "same", d_ta.input_value().strip()==kit["description"].strip())
    t_ta.click(); t_ta.fill(kit["title"]); time.sleep(.5)
    print("new title:", t_ta.input_value(), "| expected", kit["title"], t_ta.input_value()==kit["title"])
    page.screenshot(path=S+f"/shots/12-{code}.png")
    if pub:
        page.get_by_text("เผยแพร่", exact=True).last.click(); time.sleep(4)
        print("published; dialog open:", page.locator("textarea:visible").count())
