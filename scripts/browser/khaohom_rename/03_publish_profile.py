import time
from playwright.sync_api import sync_playwright
S="C:/mooniex/khaohom-ep01b"
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    pg=[x for x in b.contexts[0].pages if "studio.youtube" in x.url][0]
    pg.get_by_role("button",name="เผยแพร่").first.click(); time.sleep(6)
    pg.screenshot(path=S+"/shots/03-basic-published.png")
    pg.reload(wait_until="domcontentloaded"); time.sleep(8)
    inp=pg.locator("input:visible")
    print("after reload:", inp.nth(0).input_value(), inp.nth(1).input_value())
    print(pg.evaluate("() => document.body.innerText").count("เผยแพร่"))
