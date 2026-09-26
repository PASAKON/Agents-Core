"""(winbox copy: C:/mooniex/ilag-runner/probe/fresh_balance.py) Read-only: load the board in a NEW tab (so the number is fresh, not a stale tab's), read the credit balance,
close the tab."""
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.goto("https://www.topview.ai/board/my-first-board?tool-type=video-edit&model-id=qwen-wan3.0-video",
              wait_until="domcontentloaded", timeout=60000)
    val = None
    for _ in range(60):
        el = page.query_selector('button[aria-label="Credits"]')
        if el and any(ch.isdigit() for ch in el.inner_text()):
            val = el.inner_text().strip()
            break
        time.sleep(1)
    print("fresh balance:", val)
    page.close()
