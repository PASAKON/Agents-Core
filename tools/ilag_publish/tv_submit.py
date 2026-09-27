"""Fill the TopView Wan3 Challenge submission form and, only if every field reads back right and the video upload has
finished, click Submit. Without --submit it fills, reads back and stops (the tab stays open for a look).
Fields are found by their label text (the inputs carry no names). Files go in through CDP DOM.setFileInputFiles,
because Playwright over CDP refuses files over 50 MB."""
import sys, time, json, re
from playwright.sync_api import sync_playwright
V = {"Project Name*": "THE SHADOW BELOW", "Author Name*": "ILAG Studio",
     "Project Link*": "https://www.topview.ai/board/4252ab7766ad4150b3829427362f80f0",
     "Social Media Post Link*": "https://youtu.be/QR0EYsIMNR4"}
F = {"Cover*": r"C:\mooniex\ilag-final\TSB-Cover-A-Shadow-v2-1920x1080.png",
     "Author Avatar*": r"C:\mooniex\ilag-final\ILAG-Studio-avatar-900.jpg",
     "Project Videos*": r"C:\mooniex\ilag-final\THE-SHADOW-BELOW-4K-topview.mp4"}
def say(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
def xp(label, what):
    # the '*' is its own element in the live form, so match the label by its leading words on any element whose
    # full text starts with them and has no child element carrying the same text (the innermost match)
    name = label.rstrip("*")
    return (f"xpath=(//*[starts-with(normalize-space(.), '{name}') and string-length(normalize-space(.)) < "
            f"{len(name) + 4} and not(*[starts-with(normalize-space(.), '{name}')])])[last()]/following::{what}[1]")
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto("https://www.topview.ai/activity/topview-wan3-challenge", wait_until="domcontentloaded", timeout=60000)
    time.sleep(10)
    page.get_by_role("button", name="Submit work").first.click()
    time.sleep(6)
    for label, val in V.items():
        box = page.locator(xp(label, "textarea" if "Post Link" in label else "input[@type='text']")).first
        box.fill(val); time.sleep(0.3)
        say("filled", label, "->", box.input_value())
    cdp = page.context.new_cdp_session(page)
    for label, path in F.items():
        h = page.locator(xp(label, "input[@type='file']")).first.element_handle()
        # tag the input, then hand CDP a selector for it
        h.evaluate("(e, k) => e.setAttribute('data-cto-field', k)", label)
        root = cdp.send("DOM.getDocument", {"depth": -1, "pierce": True})["root"]["nodeId"]
        nid = cdp.send("DOM.querySelector", {"nodeId": root, "selector": f"input[data-cto-field='{label}']"})["nodeId"]
        cdp.send("DOM.setFileInputFiles", {"files": [path], "nodeId": nid})
        say("file set", label, path.split("\\")[-1])
        time.sleep(3)
    # wait for uploads to settle: no visible percent text in the form
    for i in range(120):
        txt = page.evaluate("() => document.body.innerText")
        pct = re.findall(r"\b\d{1,3}%", txt)
        if not pct:
            break
        if i % 4 == 0: say("uploading", pct[:4])
        time.sleep(10)
    form_txt = page.evaluate("() => document.body.innerText")
    say("form shows files:", [n for n in ("TSB-Cover-A-Shadow", "ILAG-Studio-avatar", "THE-SHADOW-BELOW-4K-topview") if n in form_txt])
    btns = page.evaluate("""() => [...document.querySelectorAll('button')].filter(e => e.offsetParent !== null)
        .map(e => [(e.innerText||'').trim(), e.disabled]).filter(x => x[0] && x[0].length < 30)""")
    say("buttons:", json.dumps(btns[-12:], ensure_ascii=False))
    ok = all(page.locator(xp(l, "textarea" if "Post Link" in l else "input[@type='text']")).first.input_value() == v for l, v in V.items())
    say("text fields read back ok:", ok)
    if "--submit" in sys.argv and ok:
        sub = page.locator("button", has_text=re.compile(r"^\s*Submit\s*$")).last
        say("submit button count:", page.locator("button", has_text=re.compile(r"^\s*Submit\s*$")).count())
        sub.click(); time.sleep(12)
        say("after submit:", page.evaluate("() => document.body.innerText").replace("\n", " / ")[:600])
