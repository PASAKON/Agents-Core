import time
from playwright.sync_api import sync_playwright
S="C:/mooniex/khaohom-ep01b"
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    pg=[x for x in b.contexts[0].pages if "studio.youtube" in x.url][0]
    inp=pg.locator("input:visible")
    inp.nth(0).click(); inp.nth(0).fill("365 to Survive"); time.sleep(1)
    inp.nth(1).click(); inp.nth(1).fill("365tosurvive"); time.sleep(3)
    print(pg.evaluate("() => document.body.innerText").split("แฮนเดิล")[-1][:600])
    pg.screenshot(path=S+"/shots/02-basic-filled.png")
    print(inp.nth(0).input_value(), inp.nth(1).input_value())
    print(pg.evaluate("() => [...document.querySelectorAll('[error], .error-text, [invalid]')].map(e=>e.innerText||e.tagName).slice(0,5)"))
