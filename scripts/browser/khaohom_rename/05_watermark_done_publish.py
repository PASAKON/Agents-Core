import time
from playwright.sync_api import sync_playwright
S="C:/mooniex/khaohom-ep01b"
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    pg=[x for x in b.contexts[0].pages if "studio.youtube" in x.url][0]
    pg.get_by_text("เสร็จ", exact=True).last.click(); time.sleep(3)
    pg.get_by_text("เผยแพร่", exact=True).first.click(); time.sleep(6)
    pg.reload(wait_until="domcontentloaded"); time.sleep(8)
    pg.screenshot(path=S+"/shots/06-profile-published.png", full_page=False)
    fi=pg.locator("input:visible"); print(fi.nth(0).input_value(), fi.nth(1).input_value())
    # wm thumbnail src
    print(pg.evaluate("() => [...document.querySelectorAll('img')].map(i=>i.src.slice(0,90)+'|'+i.naturalWidth).filter(s=>!s.startsWith('data')).slice(0,8)"))
