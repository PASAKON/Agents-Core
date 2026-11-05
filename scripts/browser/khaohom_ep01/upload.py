import time, re, sys, json
from playwright.sync_api import sync_playwright
S = sys.argv[1]
D = "C:/mooniex/khaohom-ep01"
VIDEO = chr(92).join(["C:", "mooniex", "khaohom-ep01", "video", "survive365-ep01-en.mp4"])
kit = json.load(open(S + "/kit.json", encoding="utf-8"))
def say(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
def set_file_local(page, selector, path):
    cdp = page.context.new_cdp_session(page)
    root = cdp.send("DOM.getDocument", {"depth": -1, "pierce": True})["root"]["nodeId"]
    node = cdp.send("DOM.querySelector", {"nodeId": root, "selector": selector})["nodeId"]
    if not node: raise SystemExit("no " + selector)
    cdp.send("DOM.setFileInputFiles", {"files": [path], "nodeId": node}); cdp.detach()
def fill_box(page, sel, text):
    box = page.locator(sel).first
    box.click(); page.keyboard.press("Control+A"); page.keyboard.press("Delete")
    page.evaluate("""([sel, text]) => { const el = document.querySelector(sel);
        const dt = new DataTransfer(); dt.setData('text/plain', text);
        el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true})); }""", [sel, text])
    time.sleep(1)
    got = box.inner_text().strip(); say(sel, len(got), "chars of", len(text)); return got
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()   # left open on purpose: closing it kills the upload
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)
    name = page.evaluate("() => (document.querySelector('#entity-name')||{}).innerText"); say("channel:", name)
    if "ข้าวหอม" not in (name or ""): sys.exit("STOP wrong channel " + str(name))
    page.locator("#upload-icon").first.click(); time.sleep(4)
    set_file_local(page, "input[type=file]", VIDEO); say("file set"); time.sleep(25); say("dialog:", page.evaluate("() => (document.querySelector('ytcp-uploads-dialog')||{}).innerText||''").replace(chr(10)," / ")[-300:])
    page.wait_for_selector("#title-textarea #textbox", timeout=120000); time.sleep(3)
    fill_box(page, "#title-textarea #textbox", kit["title"])
    fill_box(page, "#description-textarea #textbox", kit["description"])
    thumbs = page.locator("input[type=file][accept*=image]"); say("thumb inputs", thumbs.count())
    if thumbs.count():
        thumbs.first.set_input_files(D + "/postkit/cover-1280x720.png"); time.sleep(5); say("thumb set")
    page.locator("tp-yt-paper-radio-button[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]").first.click(); say("not for kids")
    page.locator("#toggle-button").first.click(); time.sleep(2)
    alt = page.locator("tp-yt-paper-radio-button[name=VIDEO_HAS_ALTERED_CONTENT_YES]")
    if alt.count(): alt.first.click(); say("altered content: yes")
    else: say("altered radio not found")
    tag = page.locator("#tags-container input").first
    for t in kit["tags"]:
        tag.click(); tag.fill(t); page.keyboard.press("Enter"); time.sleep(0.3)
    say("chips", page.locator("#tags-container ytcp-chip, #tags-container .chip").count())
    page.screenshot(path=S + "/shots/02-details.png")
    say("tab url", page.url)
    # dump language-related controls for the next step
    say("lang:", page.evaluate("() => [...document.querySelectorAll('ytcp-form-language-input, #language-input, ytcp-form-select')].map(e=>e.id+':'+(e.innerText||'').replace(/\s+/g,' ').slice(0,60)).join(' | ')"))
