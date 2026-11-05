import time, re, sys
from playwright.sync_api import sync_playwright
S = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    ctx = b.contexts[0]
    pg = ctx.new_page()
    try:
        pg.set_viewport_size({"width": 1280, "height": 800})
        pg.goto("https://www.youtube.com/channel_switcher", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)
        pg.get_by_text("เอาชีวิตรอดกับข้าวหอม", exact=True).first.click()
        time.sleep(6)
        pg.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)
        print("url", pg.url)
        print("entity", pg.evaluate("() => (document.querySelector('#entity-name')||{}).innerText"))
        # public handle check (read-only)
        pg2 = ctx.new_page()
        try:
            r = pg2.goto("https://www.youtube.com/@survive365days", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)
            print("handle page status", r.status, pg2.url, "|", pg2.title())
            print(pg2.evaluate("() => document.body.innerText.slice(0,300)"))
        finally:
            pg2.close()
        pg.screenshot(path=S + "/shots/01-studio-home.png")
    finally:
        pg.close()
