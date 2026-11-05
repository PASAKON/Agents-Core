import time, sys
from playwright.sync_api import sync_playwright
S, lang = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    it=page.locator("tp-yt-paper-item", has_text=lang)
    n=it.count(); print("matches", n, [it.nth(i).inner_text().strip() for i in range(min(n,6))])
    exact=page.locator("tp-yt-paper-item").filter(has=page.get_by_text(lang, exact=True))
    print("exact", exact.count())
    (exact if exact.count() else it).first.click(); time.sleep(3)
    print(page.evaluate("() => document.body.innerText.split(String.fromCharCode(10)).join(' / ').slice(300,1500)"))
    page.screenshot(path=S+"/shots/08-picked.png")
