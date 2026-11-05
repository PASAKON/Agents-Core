import time, sys
from playwright.sync_api import sync_playwright
S=sys.argv[1]
want=[("สเปน",None),("โปรตุเกส (บราซิล)",None),("ฮินดี",None),("อินโดนีเซีย",None)]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    for name,_ in want:
        page.get_by_text("เพิ่มภาษา", exact=True).first.click(); time.sleep(2)
        cands=page.locator("tp-yt-paper-item").filter(has_text=name)
        print(name, "->", [cands.nth(i).inner_text().strip() for i in range(cands.count())])
        ex=page.locator("tp-yt-paper-item").filter(has=page.get_by_text(name, exact=True))
        if ex.count()==0: print("NO EXACT for", name); page.keyboard.press("Escape"); continue
        ex.first.click(); time.sleep(3)
    print(page.evaluate("() => document.body.innerText.split(String.fromCharCode(10)).join(' / ').slice(380,1500)"))
    page.screenshot(path=S+"/shots/09-rows.png")
