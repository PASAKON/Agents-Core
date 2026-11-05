import sys, time
from playwright.sync_api import sync_playwright
S=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page=[pg for pg in b.contexts[0].pages if "studio.youtube" in pg.url][0]
    ins=page.locator("input[type=file]"); print("file inputs", ins.count())
    info=page.evaluate("""() => [...document.querySelectorAll('input[type=file]')].map(i=>{ let n=i, t=''; for(let k=0;k<8&&n;k++){ n=n.parentElement; if(n&&n.innerText&&n.innerText.length>5){t=n.innerText.slice(0,40);break;} } return i.accept+'|'+t })""")
    print(info)
