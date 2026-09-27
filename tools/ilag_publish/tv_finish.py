"""Attach to the TopView tab where tv_submit.py filled the form, wait until the video upload finishes (the form's last
button leaves "Uploading..."), re-read every field, and with --submit click the submit button. Prints each state."""
import sys, time, json, re
from playwright.sync_api import sync_playwright
def say(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    pages = [pg for pg in b.contexts[0].pages if "topview-wan3-challenge" in pg.url]
    if not pages:
        sys.exit("STOP: no challenge tab")
    # two challenge tabs can be open (an earlier attempt that failed on the first field); take the filled one
    filled = [pg for pg in pages if "THE SHADOW BELOW" in pg.evaluate(
        "() => [...document.querySelectorAll('input[type=text]')].map(e => e.value).join('|')")]
    say("challenge tabs:", len(pages), "filled:", len(filled))
    if not filled:
        sys.exit("STOP: no tab with the filled form")
    page = filled[-1]
    last = None
    for i in range(180):
        btns = page.evaluate("""() => [...document.querySelectorAll('button')].filter(e => e.offsetParent !== null)
            .map(e => [(e.innerText||'').trim(), e.disabled])""")
        tail = btns[-3:]
        if tail != last:
            say("buttons:", json.dumps(tail, ensure_ascii=False)); last = tail
        if not any(t.startswith("Uploading") for t, _ in btns):
            break
        time.sleep(10)
    body = page.evaluate("() => document.body.innerText")
    vals = page.evaluate("""() => [...document.querySelectorAll('input[type=text], textarea')].filter(e => e.offsetParent !== null).map(e => e.value)""")
    say("values:", json.dumps(vals, ensure_ascii=False))
    say("files shown:", [n for n in ("TSB-Cover-A-Shadow", "ILAG-Studio-avatar", "THE-SHADOW-BELOW-4K-topview") if n in body])
    cands = [t for t, d in btns if re.fullmatch(r"(Submit|Confirm|Save)( .*)?", t)]
    say("submit candidates:", cands)
    if "--submit" in sys.argv:
        need = ["THE SHADOW BELOW", "ILAG Studio", "https://www.topview.ai/board/4252ab7766ad4150b3829427362f80f0",
                "https://youtu.be/QR0EYsIMNR4"]
        if not all(v in vals for v in need):
            sys.exit("STOP: a text field does not read back")
        if not cands:
            sys.exit("STOP: no submit button")
        page.locator("button", has_text=re.compile(r"^\s*" + re.escape(cands[-1]) + r"\s*$")).last.click()
        time.sleep(12)
        say("after submit:", page.evaluate("() => document.body.innerText").replace("\n", " / ")[:700])
