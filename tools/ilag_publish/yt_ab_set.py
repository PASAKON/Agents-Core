"""Set up a Studio thumbnail A/B test ("ภาพปกเท่านั้น"), then (with --go) click ตั้งค่าการทดสอบ and save.
Each "เพิ่มภาพปก" opens a file chooser; the images are small, so Playwright's chooser works over CDP.

SLOT 1 IS PRE-FILLED WITH THE VIDEO'S CURRENT THUMBNAIL. Pass only the OTHER covers (at most two; YouTube tests three
in all). Measured 2026-09-27: run with A.jpg C.jpg on a video whose thumbnail was A, the test came out A / C / A — the
CEO spotted the duplicate on his phone. If a test is already running, its report offers "การทดสอบใหม่"; the script
clicks that first to replace it (the old test's data is dropped)."""
import sys, time, json
from playwright.sync_api import sync_playwright
vid = sys.argv[1]
files = [x for x in sys.argv[2:] if not x.startswith("--")][:2]
def say(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto(f"https://studio.youtube.com/video/{vid}/edit", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    page.locator("#ab-test-button").first.click(force=True); time.sleep(5)
    say("dialog open")
    nt = page.locator("ytcp-button, button", has_text="การทดสอบใหม่")
    if nt.count() and nt.first.is_visible():
        nt.first.click(force=True); time.sleep(5)
        say("replaced the running test via การทดสอบใหม่:", page.evaluate("""() => [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog')]
            .filter(e => e.offsetParent !== null).map(e => e.innerText.replace(/\\s+/g,' ').slice(0, 300)).join(' || ')"""))
        conf = page.locator("tp-yt-paper-dialog #confirm-button >> visible=true")
        if conf.count():
            say("a confirm appeared (the running test is deleted); accepting only with --replace or --go")
            if "--replace" not in sys.argv and "--go" not in sys.argv:
                page.close(); sys.exit(0)
            conf.first.click(force=True); time.sleep(5)
    page.locator("#chip-1").first.click(force=True); time.sleep(3)
    say("thumbnail-only chosen")
    for f in files:
        vis = page.locator("#select-button >> visible=true", has_text="เพิ่มภาพปก")
        if not vis.count():
            # the third slot sits below the fold of the dialog; bring its label into view first
            lab = page.get_by_text("ภาพปกที่ 3", exact=False)
            if lab.count():
                lab.last.scroll_into_view_if_needed(); time.sleep(1.5)
            vis = page.locator("#select-button >> visible=true")
            say("after scroll, select buttons visible:", vis.count(),
                page.evaluate("() => [...document.querySelectorAll('#select-button')].map(b => (b.innerText||'').trim() + '/' + (b.offsetParent !== null))"))
        say("add buttons visible:", vis.count())
        if not vis.count():
            say("no slot for", f); continue
        btn = vis.last
        with page.expect_file_chooser(timeout=20000) as fc:
            btn.click(force=True)
        fc.value.set_files(f)
        time.sleep(8)
        say("added", f.split("\\")[-1], "| slots left:", page.locator("#select-button", has_text="เพิ่มภาพปก").count())
    d = page.evaluate("""() => [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog')].filter(e => e.offsetParent !== null)
        .map(e => e.innerText.replace(/\\s+/g,' ').slice(0, 400)).join(' || ')""")
    say("dialog:", d)
    imgs = page.evaluate("""() => { const d = [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog')].filter(e => e.offsetParent !== null);
        const r = d.length ? d[d.length - 1] : document;
        return [...r.querySelectorAll('img')].filter(i => i.offsetParent !== null && i.naturalWidth > 100)
            .map(i => i.src.slice(0, 70) + ' ' + i.naturalWidth + 'x' + i.naturalHeight); }""")
    say("slot images:", imgs)
    st = page.locator("#set-test-button").first
    say("set-test disabled:", st.get_attribute("aria-disabled"))
    uploads = [i for i in imgs if "ytimg" not in i]
    if "--go" in sys.argv and (len(imgs) != 3 or len(uploads) != len(files)):
        say(f"STOP: expected 3 slots = the current thumbnail + {len(files)} uploads, saw {len(imgs)} ({len(uploads)} uploads); not set")
    elif "--go" in sys.argv:
        st.click(); time.sleep(8)
        say("after set:", page.evaluate("() => [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog')].filter(e => e.offsetParent !== null).map(e => e.innerText.replace(/\\s+/g,' ').slice(0, 300)).join(' || ') || 'no dialog'"))
        save = page.locator("#save").first
        say("save button:", save.inner_text().strip(), save.get_attribute("aria-disabled"))
        if save.get_attribute("aria-disabled") == "false":
            save.click(); time.sleep(8); say("saved")
    page.close()
