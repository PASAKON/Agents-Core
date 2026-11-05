import time
from playwright.sync_api import sync_playwright
S="C:/mooniex/khaohom-ep01b"
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    pg=[x for x in b.contexts[0].pages if "studio.youtube" in x.url][0]
    pg.set_default_timeout(8000)
    if not pg.locator("tp-yt-paper-radio-button[name=PUBLIC]").is_visible():
        pg.get_by_text("ส่วนตัว", exact=True).first.click(); time.sleep(2)
    pg.locator("tp-yt-paper-radio-button[name=PUBLIC]").click(); time.sleep(1)
    print("public checked:", pg.evaluate("() => document.querySelector('tp-yt-paper-radio-button[name=PUBLIC]').getAttribute('aria-checked')"))
    pg.screenshot(path=S+"/shots/15-vis-public-picked.png")
    pg.get_by_text("เสร็จสิ้น", exact=True).first.click(); time.sleep(2)
    pg.locator("#save").click(); time.sleep(6)
    pg.screenshot(path=S+"/shots/16-vis-saved.png")
    print(pg.evaluate("() => document.body.innerText").split("ระดับการแชร์")[1][:80].replace(chr(10)," / "))
