"""Read-only: is a Studio editor change pending/processing on this video? Prints every line mentioning processing or
the edit, from the details page, the editor and the content list.   python yt_edit_status.py <video_id> <channel_id>"""
import re, sys, time
from playwright.sync_api import sync_playwright

vid, ch = sys.argv[1:3]
PAT = re.compile(r"ประมวลผล|การแก้ไข|processing|edit", re.I)
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    try:
        for url in (f"https://studio.youtube.com/video/{vid}/editor", f"https://studio.youtube.com/video/{vid}/edit",
                    f"https://studio.youtube.com/channel/{ch}/videos/upload"):
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(25)
            t = page.evaluate("() => document.body.innerText")
            hits = sorted({l.strip()[:160] for l in t.split("\n") if PAT.search(l)})
            print("==", url.split("studio.youtube.com")[1]); [print("  ", h) for h in hits[:25]]
            if "videos/upload" in url:
                i = t.find("THE SHADOW BELOW")
                print("   row:", t[i:i + 300].replace("\n", " / ") if i >= 0 else "not found")
    finally:
        page.close()
