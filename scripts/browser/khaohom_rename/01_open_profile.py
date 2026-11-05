import time, sys
from playwright.sync_api import sync_playwright
S="C:/mooniex/khaohom-ep01b"
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    ctx = b.contexts[0]
    pg = ctx.new_page()
    pg.set_viewport_size({"width": 1280, "height": 800})
    pg.goto("https://www.youtube.com/channel_switcher", wait_until="domcontentloaded", timeout=60000)
    time.sleep(5)
    pg.get_by_text("เอาชีวิตรอดกับข้าวหอม", exact=True).first.click()
    time.sleep(6)
    pg.goto("https://studio.youtube.com/channel/UCA3806sh7qlV1S_oCIxlnjg/editing/profile", wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)
    print(pg.url)
    print(pg.evaluate("() => document.body.innerText.slice(0,1500)"))
    pg.screenshot(path=S+"/shots/01-basic-before.png")
    print("TAB LEFT OPEN")
