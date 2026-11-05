import sys, time
from playwright.sync_api import sync_playwright
S=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    page.get_by_text("เสร็จ", exact=True).last.click(); time.sleep(3)
    t=page.evaluate("() => document.body.innerText"); i=t.find("ลายน้ำของวิดีโอ"); print(t[i:i+600].replace(chr(10)," / "))
    page.screenshot(path=S+"/shots/19-wm-done.png")
