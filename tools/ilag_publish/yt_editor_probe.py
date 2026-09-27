"""Read-only: open the Studio editor for a video and print what it offers (trim, blockers such as a running A/B test),
without changing anything.   python yt_editor_probe.py <video_id>"""
import sys, time
from playwright.sync_api import sync_playwright

vid = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto(f"https://studio.youtube.com/video/{vid}/editor", wait_until="domcontentloaded", timeout=60000)
    time.sleep(15)
    print("url:", page.url)
    t = page.evaluate("() => document.body.innerText")
    print(t[:2500].replace("\n", " / "))
    ids = page.evaluate("""() => [...document.querySelectorAll('[id]')].map(e => e.id)
        .filter(i => /trim|cut|editor|save|discard|revert/i.test(i)).slice(0, 60)""")
    print("ids:", ids)
    page.close()
