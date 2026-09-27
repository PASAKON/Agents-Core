"""Upload an SRT as the video-language captions: translations page -> 'อัปโหลดด้วยตนเอง' -> 'มีการกำหนดเวลา' (with
timing) -> Continue -> file -> Publish/Done. Prints the dialog at each step; --go actually publishes."""
import sys, time, json, re
from playwright.sync_api import sync_playwright
vid, srt = sys.argv[1], sys.argv[2]
def say(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
def dialog_text(page):
    return page.evaluate("() => [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog, ytgn-video-translations-dialog')].filter(e => e.offsetParent !== null).map(e => e.innerText.replace(/\\s+/g,' ').trim().slice(0, 400)).join(' || ')")
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto(f"https://studio.youtube.com/video/{vid}/translations", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    say("page:", page.evaluate("() => (document.querySelector('#main') || document.body).innerText.replace(/\\s+/g,' ').slice(0, 160)"))
    page.locator("#upload-default-language-button").first.click(); time.sleep(4)
    say("dialog 1:", dialog_text(page))
    opt = page.get_by_text("กำกับเวลา", exact=True)
    say("with-timing options:", opt.count())
    opt.first.click(); time.sleep(1)
    cont = page.get_by_role("button", name=re.compile("ดำเนินการต่อ"))
    say("continue buttons:", cont.count())
    # Continue opens the OS file chooser from an input created on the click; catch that chooser (the SRT is tiny, so
    # Playwright's 50 MB CDP limit does not apply). Setting a file on the page's first file input did nothing.
    with page.expect_file_chooser(timeout=20000) as fc:
        cont.first.click()
    fc.value.set_files(srt)
    say("file chooser filled")
    for i in range(12):
        time.sleep(3)
        hits = page.evaluate("""() => [...document.querySelectorAll('*')].filter(e => e.children.length === 0 && e.offsetParent !== null
            && /เผยแพร่|บันทึกฉบับร่าง|Publish|ข้อผิดพลาด|ไม่รองรับ/.test(e.innerText || '')).map(e => e.tagName + ':' + e.innerText.trim().slice(0, 60)).slice(0, 8)""")
        if hits:
            say("found:", hits, page.url); break
    else:
        say("nothing with Publish/error text after 36 s", page.url)
    say("dialog 2:", dialog_text(page)[:500])
    btns = page.evaluate("() => [...document.querySelectorAll('ytcp-button, button')].filter(e => e.offsetParent !== null).map(e => (e.innerText||'').trim()).filter(t => t && t.length < 20)")
    say("buttons:", json.dumps(sorted(set(btns)), ensure_ascii=False))
    say("overlay:", page.evaluate("() => [...document.querySelectorAll('ytve-editor, ytve-modal-host, ytgn-caption-editor, ytve-captions-editor, [role=dialog]')].filter(e => e.offsetParent !== null).map(e => e.tagName + ':' + e.innerText.replace(/\\s+/g,' ').slice(0, 300)).join(' || ')"))
    if "--go" in sys.argv:
        pub = page.get_by_role("button", name=re.compile(r"^\s*(เผยแพร่|เสร็จสิ้น)\s*$"))
        say("publish buttons:", pub.count())
        pub.last.click(); time.sleep(8)
        say("page after:", page.evaluate("() => (document.querySelector('#main') || document.body).innerText.replace(/\\s+/g,' ').slice(0, 400)"))
    page.close()
