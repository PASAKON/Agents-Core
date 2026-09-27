"""Read-only: which channels can the signed-in Google account switch to? Opens youtube.com/channel_switcher, clicks nothing."""
import time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    try:
        page.goto("https://www.youtube.com/channel_switcher", wait_until="domcontentloaded", timeout=60000)
        time.sleep(6)
        print("URL:", page.url)
        txt = page.evaluate("() => document.body ? document.body.innerText : ''")
        print("TEXT:", " / ".join(t.strip() for t in txt.splitlines() if t.strip())[:700])
    finally:
        page.close()
