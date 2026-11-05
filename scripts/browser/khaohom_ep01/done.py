import time, sys
from playwright.sync_api import sync_playwright
S=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    print("btn:", page.evaluate("() => (document.querySelector('#done-button')||{}).innerText"))
    page.locator("#done-button").first.click(); time.sleep(6)
    print(page.evaluate("() => document.body.innerText.slice(0,0)"))
    txt=page.evaluate("() => [...document.querySelectorAll('ytcp-prechecks-warning-dialog, ytcp-uploads-still-processing-dialog, ytcp-video-share-dialog, tp-yt-paper-dialog')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\s+/g,' ').slice(0,300))")
    print(txt)
    page.screenshot(path=S+"/shots/05-after-save.png")
