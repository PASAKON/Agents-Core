"""Publish a Studio DRAFT: content list -> the row's "แก้ไขฉบับร่าง" (Edit draft) -> visibility step -> PUBLIC ->
report the Done button's state -> click it -> re-read the row. Prints each step."""
import sys, time, json
from playwright.sync_api import sync_playwright
title_part, ch = sys.argv[1], sys.argv[2]
def say(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto(f"https://studio.youtube.com/channel/{ch}/videos/upload", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    row = page.locator("ytcp-video-row", has_text=title_part).first
    say("row:", row.inner_text().replace("\n", " ")[:160])
    row.get_by_text("แก้ไขฉบับร่าง").first.click()
    page.wait_for_selector("ytcp-uploads-dialog #next-button", timeout=60000)
    time.sleep(4)
    for i in range(4):
        if page.locator("tp-yt-paper-radio-button[name=PUBLIC]").count() and page.locator("tp-yt-paper-radio-button[name=PUBLIC]").first.is_visible():
            break
        page.locator("#next-button").first.click(); time.sleep(3); say("next", i + 1)
    page.locator("tp-yt-paper-radio-button[name=PUBLIC]").first.click(); time.sleep(1)
    done = page.locator("#done-button").first
    say("done button:", json.dumps(page.evaluate("""() => { const d = document.querySelector('#done-button');
        return d ? {text: d.innerText.trim(), disabled: d.hasAttribute('disabled') || d.getAttribute('aria-disabled')} : null; }"""), ensure_ascii=False))
    if "--publish" in sys.argv:
        done.click(); time.sleep(10)
        say("after click:", page.evaluate("() => (document.querySelector('ytcp-video-share-dialog, ytcp-prechecks-warning-dialog, tp-yt-paper-dialog[opened]') || {}).innerText || 'no dialog'")[:300])
        page.goto(f"https://studio.youtube.com/channel/{ch}/videos/upload", wait_until="domcontentloaded", timeout=60000)
        time.sleep(12)
        say("row now:", page.locator("ytcp-video-row", has_text=title_part).first.inner_text().replace("\n", " ")[:200])
    page.close()
