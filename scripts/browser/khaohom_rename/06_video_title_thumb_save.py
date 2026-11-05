import time, json
from playwright.sync_api import sync_playwright
S="C:/mooniex/khaohom-ep01b"
kit=json.load(open(S+"/kit.json",encoding="utf-8"))
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    pg=[x for x in b.contexts[0].pages if "studio.youtube" in x.url][0]
    tb=pg.locator("#title-textarea #textbox")
    tb.click(); pg.keyboard.press("Control+A"); pg.keyboard.insert_text(kit["title"]); time.sleep(1)
    print("title:", tb.inner_text())
    pg.locator("input[type=file]").first.set_input_files(S+"/cover-1280x720.png"); time.sleep(8)
    pg.screenshot(path=S+"/shots/09-video-title-thumb.png")
    save=pg.locator("#save"); print("save visible", save.count(), save.is_enabled() if save.count() else None)
    if save.count(): save.click(); time.sleep(6)
    pg.screenshot(path=S+"/shots/10-video-saved.png")
    print(pg.evaluate("() => document.body.innerText.slice(0,200)"))
