"""Read-only: visibility of one video from the Studio content list (Thai labels: สาธารณะ public, ส่วนตัว private,
ไม่เป็นสาธารณะ unlisted, ฉบับร่าง draft)."""
import sys, time, json
from playwright.sync_api import sync_playwright
vid, ch = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.goto(f"https://studio.youtube.com/channel/{ch}/videos/upload", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    rows = page.evaluate("""(vid) => [...document.querySelectorAll('ytcp-video-row')].map(r => r.innerText.replace(/\\s+/g,' ').trim().slice(0, 260))
        .filter(t => true).slice(0, 4)""", vid)
    for r in rows: print("ROW:", r)
    page.close()
