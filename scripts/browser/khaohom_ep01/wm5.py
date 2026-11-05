import sys, time
from playwright.sync_api import sync_playwright
S=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    page.get_by_text("เผยแพร่", exact=True).first.click(); time.sleep(5)
    page.reload(wait_until="domcontentloaded"); time.sleep(8)
    t=page.evaluate("() => document.body.innerText"); i=t.find("ลายน้ำของวิดีโอ"); print(t[i:i+400].replace(chr(10)," / "))
    page.screenshot(path=S+"/shots/20-wm-published.png")
