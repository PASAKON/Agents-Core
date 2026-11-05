"""Replay: set a custom thumbnail in YouTube Studio on the winbox :9224 Chrome (task-1e7f3980).
Run: C:\mooniex\pwvenv\Scripts\python.exe -I -X utf8 yt_thumb_after_verify.py <video_id> <png_path>
Needs the channel's phone verification done first (youtube.com/verify, done by the CEO by hand;
this script never types a number or a code). Takes the PC lease before, gives it back after (by the caller)."""
import sys
from playwright.sync_api import sync_playwright
VID, FILE = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224", timeout=30000)
    pg = b.contexts[0].new_page()
    try:
        pg.goto(f"https://studio.youtube.com/video/{VID}/edit", wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(8000)
        pg.set_input_files("#file-loader", FILE)      # brittle: Studio's hidden thumbnail input id
        pg.wait_for_timeout(6000)
        assert not pg.evaluate("document.querySelector('#save').hasAttribute('disabled')"), "save still disabled"
        pg.click("#save")                              # brittle: ytcp save button id
        pg.wait_for_timeout(8000)
        pg.reload(wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(9000)
        print("saved; verify visually / by ytimg md5 change")
    finally:
        pg.close()
