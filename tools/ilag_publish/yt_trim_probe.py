"""Probe (no save): open the Studio editor, enter Trim, and print the controls it shows (time boxes, New cut, Save),
so yt_trim_end.py can be written against real selectors.   python yt_trim_probe.py <video_id> [--newcut]
The editor's timeline overlays its own buttons (Playwright: "scroll-area ... intercepts pointer events"), so every
click is forced; the tab is always closed unsaved, which discards the edit."""
import sys, time
from playwright.sync_api import sync_playwright

vid = sys.argv[1]


def dump(page, tag):
    info = page.evaluate("""() => {
        const vis = e => e.offsetParent !== null;
        const inputs = [...document.querySelectorAll('input, [contenteditable=true]')].filter(vis).map(e =>
            ({id: e.id, aria: e.getAttribute('aria-label'), val: e.value !== undefined ? e.value : e.innerText,
              ph: e.getAttribute('placeholder'), host: e.closest('[id]') ? e.closest('[id]').id : ''}));
        const btns = [...document.querySelectorAll('button, ytcp-button, [role=button]')].filter(vis).map(e =>
            ((e.id || '') + ':' + (e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 40) + ':' + (e.getAttribute('aria-label') || '')
             + ':' + (e.getAttribute('aria-disabled') || ''))).filter(s => s.replace(/:/g, '').trim());
        const ed = document.querySelector('#video-editor');
        return {inputs, btns: btns.slice(0, 80), text: ed ? ed.innerText.replace(/\\s+/g, ' ').slice(0, 1200) : ''};
    }""")
    print("==", tag)
    print("inputs:", info["inputs"])
    print("buttons:", info["btns"])
    print("text:", info["text"])


def run(page):
    page.goto(f"https://studio.youtube.com/video/{vid}/editor", wait_until="domcontentloaded", timeout=60000)
    time.sleep(15)
    start = page.get_by_text("เริ่มต้นใช้งาน", exact=True)
    if start.count():
        start.first.click(force=True, timeout=8000); time.sleep(4); print("clicked เริ่มต้นใช้งาน")
    dump(page, "editor")
    page.locator("#entrypoint-trim-row, #add-trim-icon-button").first.click(force=True, timeout=8000)
    time.sleep(5)
    dump(page, "after trim click")
    if "--newcut" in sys.argv:
        nc = page.get_by_text("ตัดใหม่", exact=False)
        print("new-cut matches:", nc.count())
        if nc.count():
            nc.first.click(force=True, timeout=8000); time.sleep(3)
            dump(page, "after new cut")
    print("closing tab unsaved (discards)")


with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    try:
        run(page)
    finally:
        page.close()
