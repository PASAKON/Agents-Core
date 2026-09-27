"""Read-only: is the winbox debug Chrome (CDP 9224) signed in to YouTube, and as which channel? Clicks nothing."""
import time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    ctx = b.contexts[0]
    page = ctx.new_page()
    try:
        page.goto("https://studio.youtube.com/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)
        print("URL:", page.url)
        print("TITLE:", page.title())
        name = page.evaluate("""() => { const e = document.querySelector('#entity-name, ytcp-entity-name, .entity-name');
                                        return e ? e.innerText.trim() : null; }""")
        print("CHANNEL:", name)
        txt = page.evaluate("() => document.body ? document.body.innerText.slice(0, 400) : ''")
        print("TEXT:", " / ".join(t.strip() for t in txt.splitlines() if t.strip())[:400])
    finally:
        page.close()
