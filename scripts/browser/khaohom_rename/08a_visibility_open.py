import time
from playwright.sync_api import sync_playwright
S="C:/mooniex/khaohom-ep01b"
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    pg=[x for x in b.contexts[0].pages if "studio.youtube" in x.url][0]
    pg.goto("https://studio.youtube.com/video/fuwKC8xjUFc/edit", wait_until="domcontentloaded", timeout=60000); time.sleep(10)
    pg.locator("ytcp-video-metadata-visibility, #privacy-radios, ytcp-icon-button#select-button, ytcp-text-dropdown-trigger").first.click() if False else None
    pg.get_by_text("ส่วนตัว", exact=True).first.click(); time.sleep(2)
    pg.screenshot(path=S+"/shots/14-vis-dropdown.png")
