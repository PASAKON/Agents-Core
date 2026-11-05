import time, sys
from playwright.sync_api import sync_playwright
S=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    for i in range(3):
        page.locator("#next-button").first.click(); time.sleep(3)
    r=page.locator("tp-yt-paper-radio-button[name=PRIVATE]"); print("private radios", r.count())
    r.first.click(); time.sleep(1)
    print("checked:", page.evaluate("() => (document.querySelector('tp-yt-paper-radio-button[name=PRIVATE]')||{}).getAttribute('aria-checked')"))
    print("url:", page.evaluate("() => { const a=document.querySelector('.video-url-fadeable a, a.ytcp-video-info'); return a?a.href:null }"))
    print("progress:", page.evaluate("() => (document.querySelector('ytcp-video-upload-progress')||{}).innerText"))
    page.screenshot(path=S+"/shots/04-visibility.png")
