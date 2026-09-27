"""Read-only: reload the challenge page and look for our entry (my submissions / review state)."""
import time, re
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.goto("https://www.topview.ai/activity/topview-wan3-challenge", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    t = page.evaluate("() => document.body.innerText")
    i = t.find("THE SHADOW BELOW")
    print("found title:", i >= 0)
    if i >= 0: print("context:", t[max(0, i - 300):i + 300].replace("\n", " / "))
    for k in ("My submission", "My Submission", "Under review", "Pending", "Reviewing", "Approved", "submitted"):
        j = t.find(k)
        if j >= 0: print(k, "->", t[max(0, j - 80):j + 160].replace("\n", " / "))
    page.close()
