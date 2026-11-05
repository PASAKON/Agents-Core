import time, sys
from playwright.sync_api import sync_playwright
S=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    page.locator("#language-input").first.click(); time.sleep(1.5)
    opts=page.evaluate("() => [...document.querySelectorAll('tp-yt-paper-item, ytcp-text-menu tp-yt-paper-item')].filter(e=>e.offsetParent).map(e=>(e.innerText||'').trim()).slice(0,80)")
    print(len(opts), [o for o in opts if 'อังกฤษ' in o or 'English' in o])
    it=page.locator("tp-yt-paper-item", has_text="อังกฤษ (สหรัฐอเมริกา)")
    print("us count", it.count())
    if not it.count(): it=page.locator("tp-yt-paper-item", has_text="อังกฤษ")
    print("any count", it.count())
    it.first.click(); time.sleep(1.5)
    print(page.evaluate("() => (document.querySelector('#language-input')||{}).innerText"))
    page.screenshot(path=S+"/shots/03-lang.png")
