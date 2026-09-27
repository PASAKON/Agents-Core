"""Read-only: open the video's details page, open the A/B test button, and print what a RUNNING test offers
(stop / edit / report), without clicking any of it.   python yt_ab_probe.py <video_id>"""
import sys, time
from playwright.sync_api import sync_playwright

vid = sys.argv[1]
DLG = """() => [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog, ytcp-ab-test-dialog, [role=dialog]')]
    .filter(e => e.offsetParent !== null).map(e => e.innerText.replace(/\\s+/g, ' ').slice(0, 900)).join(' || ')"""
BTNS = """() => { const d = [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog, [role=dialog]')].filter(e => e.offsetParent !== null);
    const root = d.length ? d[d.length - 1] : document;
    return [...root.querySelectorAll('button, ytcp-button, [role=button], tp-yt-paper-radio-button, [role=radio]')].filter(e => e.offsetParent !== null)
      .map(e => (e.id || '') + ':' + (e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 50) + ':' + (e.getAttribute('aria-label') || '')); }"""


def run(page):
    page.goto(f"https://studio.youtube.com/video/{vid}/edit", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    ab = page.locator("#ab-test-button")
    print("ab button:", ab.count(), ab.first.inner_text().strip().replace("\n", " ") if ab.count() else "")
    ab.first.click(force=True, timeout=8000); time.sleep(6)
    print("dialog:", page.evaluate(DLG))
    print("buttons:", page.evaluate(BTNS))
    for src in page.evaluate("""() => { const d = [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog, [role=dialog]')].filter(e => e.offsetParent !== null);
            const r = d.length ? d[d.length - 1] : document;
            return [...r.querySelectorAll('img')].filter(i => i.offsetParent !== null && i.naturalWidth > 100).map(i => i.src); }"""):
        print("IMG", src)


with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    try:
        run(page)
    finally:
        page.close()
