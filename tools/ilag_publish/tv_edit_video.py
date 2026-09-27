"""Replace the video of an already-submitted TopView challenge entry (My submissions -> Edit), keeping every other field.

    python tv_edit_video.py                      probe: open the edit form, print fields/files/buttons, change nothing
    python tv_edit_video.py --video F.mp4        also remove the old video, set F (CDP, >50 MB), wait for the upload,
                                                 print the form again; the tab is left open, nothing saved
    python tv_edit_video.py --video F.mp4 --go   and click the form's save/submit button

Written 2026-09-27: v1 of THE SHADOW BELOW carried the credits twice (the CEO's cut already ended with them), and the
page says "Each entry can be edited or withdrawn before the deadline". "Project Videos" may hold several videos, so the
old one is removed first and the form must show exactly one video before --go saves.
"""
import argparse, json, re, sys, time
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--title", default="THE SHADOW BELOW")
ap.add_argument("--video")
ap.add_argument("--go", action="store_true")
a = ap.parse_args()


def say(*x):
    print(time.strftime("%H:%M:%S"), *x, flush=True)


FORM = """() => { const vis = e => e.offsetParent !== null;
    const d = [...document.querySelectorAll('[role=dialog], .ant-modal, [class*=modal], [class*=Modal], form')].filter(vis);
    const r = d.length ? d[d.length - 1] : document.body;
    return {
      text: r.innerText.replace(/\\s+/g, ' ').slice(0, 1500),
      values: [...r.querySelectorAll('input[type=text], textarea')].filter(vis).map(e => e.value),
      files: [...r.querySelectorAll('input[type=file]')].map(e => (e.getAttribute('accept') || '') + (e.multiple ? ' multiple' : '')),
      videos: [...r.querySelectorAll('video')].map(v => (v.currentSrc || v.src || '').slice(0, 90)),
      buttons: [...r.querySelectorAll('button, [role=button]')].filter(vis).map(e => ((e.innerText || '').trim().slice(0, 30) + '|' +
               (e.getAttribute('aria-label') || '') + '|' + (e.disabled ? 'disabled' : ''))).filter(s => s !== '||')
    }; }"""


# the edit form is inline (not a modal): scope to the ancestor of the video file input that also holds the name field
SECTION = r"""() => { const vis = e => e.offsetParent !== null;
    const vin = [...document.querySelectorAll('input[type=file]')].find(e => /mp4/.test(e.getAttribute('accept') || ''));
    if (!vin) return {error: 'no video input'};
    let form = vin; while (form.parentElement && !/Project Name/.test(form.innerText || '')) form = form.parentElement;
    let vsec = vin; while (vsec.parentElement && !/Project Video/.test(vsec.innerText || '')) vsec = vsec.parentElement;
    const desc = el => el.tagName + (el.id ? '#' + el.id : '') + '.' + String(el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className || '').slice(0, 60)
        + ' "' + (el.innerText || '').trim().slice(0, 30) + '" aria=' + (el.getAttribute('aria-label') || '') + (el.disabled ? ' disabled' : '');
    return {
      videoSectionText: vsec.innerText.replace(/\s+/g, ' ').slice(0, 400),
      videoSectionClickables: [...vsec.querySelectorAll('button, [role=button], svg, [class*=delete], [class*=Delete], [class*=remove], [class*=Remove], [class*=close], [class*=Close]')]
          .filter(vis).map(desc).slice(0, 30),
      videoSectionVideos: [...vsec.querySelectorAll('video')].map(v => (v.currentSrc || v.src || '').slice(0, 120)),
      formValues: [...form.querySelectorAll('input[type=text], textarea')].map(e => e.value),
      formButtons: [...form.querySelectorAll('button')].filter(vis).map(desc),
      formTextTail: form.innerText.replace(/\s+/g, ' ').slice(-300)
    }; }"""


def run(page):
    page.goto("https://www.topview.ai/activity/topview-wan3-challenge", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    page.get_by_text(re.compile(r"^\s*My submissions?\s*$", re.I)).first.click(); time.sleep(5)
    card = page.locator("xpath=//*[normalize-space(text())='%s']/ancestor::*[.//button[@aria-label='Edit']][1]" % a.title).first
    card.locator("button[aria-label='Edit']").first.click(); time.sleep(8)
    f = page.evaluate(SECTION)
    say("edit form:", json.dumps(f, ensure_ascii=False, indent=0))
    if not a.video:
        return
    before = f["formValues"]
    old_name = f["videoSectionText"].split("webm")[-1].strip()
    new_name = a.video.replace("/", "\\").split("\\")[-1]
    say("old video:", old_name, "-> new:", new_name)
    # the X next to the file name (a button holding svg.lucide-x) inside the Project Videos section
    x = page.locator("xpath=//input[@type='file' and contains(@accept,'mp4')]/ancestor::*[contains(normalize-space(.),'Project Video')][1]"
                     "//button[.//*[name()='svg' and contains(@class,'lucide-x')]]")
    say("remove buttons in the video section:", x.count())
    if x.count() != 1:
        raise SystemExit("STOP: expected exactly one remove button next to the old video; nothing saved")
    x.first.click(); time.sleep(3)
    say("after remove:", page.evaluate(SECTION)["videoSectionText"])
    cdp = page.context.new_cdp_session(page)
    page.evaluate("() => [...document.querySelectorAll('input[type=file]')].find(e => /mp4/.test(e.getAttribute('accept') || '')).setAttribute('data-cto-video', '1')")
    root = cdp.send("DOM.getDocument", {"depth": -1, "pierce": True})["root"]["nodeId"]
    nid = cdp.send("DOM.querySelector", {"nodeId": root, "selector": "input[data-cto-video='1']"})["nodeId"]
    cdp.send("DOM.setFileInputFiles", {"files": [a.video], "nodeId": nid})
    say("file set:", new_name)
    last = None
    for i in range(240):
        time.sleep(10)
        txt = page.evaluate(SECTION)["videoSectionText"]
        busy = re.findall(r"Uploading[^ ]*|\b\d{1,3}%", page.evaluate("() => document.body.innerText"))
        if (txt, busy[:3]) != last:
            say("video section:", txt[-120:], "| busy:", busy[:3]); last = (txt, busy[:3])
        if not busy and new_name in txt:
            break
    f2 = page.evaluate(SECTION)
    say("form after upload:", json.dumps({k: f2[k] for k in ("videoSectionText", "formValues")}, ensure_ascii=False))
    ok_video = new_name in f2["videoSectionText"] and (old_name == new_name or old_name not in f2["videoSectionText"])
    ok_vals = f2["formValues"] == before
    btns = page.evaluate("""() => [...document.querySelectorAll('button')].filter(e => e.offsetParent !== null)
        .map(e => [(e.innerText || '').trim(), e.disabled]).filter(x => /^(Submit|Save|Update|Confirm|Save changes|Resubmit)$/i.test(x[0]))""")
    say("checks: video only the new file =", ok_video, "| text fields unchanged =", ok_vals, "| save buttons:", btns)
    if not a.go:
        say("no --go: the tab stays open, NOTHING SAVED"); return
    if not (ok_video and ok_vals and btns and not btns[-1][1]):
        raise SystemExit("STOP: a check failed; nothing saved (tab left open)")
    page.locator("button:visible", has_text=re.compile(r"^\s*" + re.escape(btns[-1][0]) + r"\s*$")).last.click()
    time.sleep(12)
    say("clicked", repr(btns[-1][0]))
    page.goto("https://www.topview.ai/activity/topview-wan3-challenge", wait_until="domcontentloaded", timeout=60000)
    time.sleep(12)
    page.get_by_text(re.compile(r"^\s*My submissions?\s*$", re.I)).first.click(); time.sleep(5)
    t = page.evaluate("() => document.body.innerText")
    i = t.find(a.title)
    say("my submissions now:", t[i:i + 160].replace("\n", " / ") if i >= 0 else "entry not found")

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    try:
        run(page)
    finally:
        if not a.video:
            page.close()
