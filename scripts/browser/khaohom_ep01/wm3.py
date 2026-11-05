import sys, time
from playwright.sync_api import sync_playwright
S=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    page.locator("input[type=file]").nth(2).set_input_files("C:/mooniex/khaohom-ep01/postkit/watermark-150x150.png"); time.sleep(4)
    t=page.evaluate("() => document.body.innerText"); i=t.find("ลายน้ำของวิดีโอ"); print(t[i:i+500].replace(chr(10)," / "))
    print("dialogs:", page.evaluate("() => [...document.querySelectorAll('ytcp-dialog, tp-yt-paper-dialog')].filter(e=>e.offsetParent).map(e=>e.innerText.slice(0,200))"))
    page.screenshot(path=S+"/shots/18-wm-set.png")
