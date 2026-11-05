import time
from playwright.sync_api import sync_playwright
S="C:/mooniex/khaohom-ep01b"
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    pg=[x for x in b.contexts[0].pages if "studio.youtube" in x.url][0]
    fi=pg.locator("input[type=file]")
    print("file inputs", fi.count(), [fi.nth(i).get_attribute("accept") for i in range(fi.count())])
    fi.nth(2).set_input_files("C:/mooniex/khaohom-ep01b/watermark-150x150.png"); time.sleep(4)
    pg.screenshot(path=S+"/shots/04-wm-set.png")
    t=pg.evaluate("() => document.body.innerText"); i=t.find("ลายน้ำของวิดีโอ"); print(t[i:i+400].replace(chr(10)," / "))
    print([b.inner_text() for b in pg.locator("button:visible").all()][-12:])
