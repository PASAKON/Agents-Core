"""Cut a range out of a published video in the Studio editor (keeps the URL, views, A/B test).

    python yt_trim_end.py <video_id> <start m:ss:ff> <end m:ss:ff> [--save [--confirm]]

Built 2026-09-27 for THE SHADOW BELOW: the CEO's cut already ended with its own credits roll, and the finish appended a
second, silent one from frame 8274 (4:35:24 at 30 fps). The editor's time boxes are m:ss:ff (minutes, seconds,
FRAMES; aria-label "4 นาที 35 วินาที 24 เฟรม"), so the cut is frame-exact. Without --save it sets the cut, reads it
back, and closes the tab unsaved (discarded). With --save it clicks ตัด (approve) and บันทึก, and prints any dialog.
The timeline overlays its own buttons, so every click is forced.
"""
import re, sys, time
from playwright.sync_api import sync_playwright

vid, start, end = sys.argv[1:4]
SAVE = "--save" in sys.argv


def say(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def time_boxes(page):
    return page.evaluate("""() => [...document.querySelectorAll('input')].filter(e => e.offsetParent !== null)
        .map((e, i) => ({i, aria: (e.getAttribute('aria-label') || '').trim(), val: e.value,
                         owner: (e.closest('[id]') || {}).id || '', tag: (e.closest('*[class]') || {}).tagName || ''}))
        .filter(x => /นาที/.test(x.aria))""")


def cut_rows(page):
    return page.evaluate("""() => { const ed = document.querySelector('#video-editor');
        const t = ed ? ed.innerText.replace(/\\s+/g, ' ') : ''; const m = t.match(/วิดีโอตัดต่อ.{0,80}/); return m ? m[0] : t.slice(0, 300); }""")


def set_box(page, idx, value):
    box = page.locator("input:visible").nth(idx)
    box.click(force=True, timeout=8000)
    page.keyboard.press("Control+A")
    page.keyboard.type(value, delay=60)  # with the colons: a bare number is read as SECONDS (43524 -> 12:05:24)
    page.keyboard.press("Enter")
    time.sleep(1.5)


def run(page):
    page.goto(f"https://studio.youtube.com/video/{vid}/editor", wait_until="domcontentloaded", timeout=60000)
    time.sleep(15)
    intro = page.get_by_text("เริ่มต้นใช้งาน", exact=True)
    if intro.count():
        intro.first.click(force=True, timeout=8000); time.sleep(4)
    page.locator("#entrypoint-trim-row, #add-trim-icon-button").first.click(force=True, timeout=8000); time.sleep(5)
    page.locator("#new-cut-button").first.click(force=True, timeout=8000); time.sleep(3)
    boxes = time_boxes(page)
    say("time boxes:", boxes)
    # measured 2026-09-27 (dry run): the three time boxes are cut START, cut END, then the PLAYHEAD
    visible = page.evaluate("() => [...document.querySelectorAll('input')].filter(e => e.offsetParent !== null).map(e => (e.getAttribute('aria-label') || '').trim())")
    idx = [i for i, a in enumerate(visible) if "นาที" in a]
    if len(idx) != 3:
        sys.exit("STOP: expected exactly three time boxes (cut start, cut end, playhead)")
    s_i, e_i = idx[0], idx[1]
    say("before:", visible[s_i], "|", visible[e_i], "| row:", cut_rows(page))
    set_box(page, e_i, end)
    set_box(page, s_i, start)
    visible = page.evaluate("() => [...document.querySelectorAll('input')].filter(e => e.offsetParent !== null).map(e => (e.getAttribute('aria-label') || '').trim())")
    say("after:", [visible[i] for i in idx], "| row:", cut_rows(page))
    # the row text shows the focused box as an empty input, so the boxes' own labels are the read-back
    lab = lambda t: "%d นาที %d วินาที %d เฟรม" % tuple(int(x) for x in t.split(":"))
    ok = visible[s_i] == lab(start) and visible[e_i] == lab(end)
    page.keyboard.press("Tab"); time.sleep(1)
    say("cut boxes read", repr(visible[s_i]), repr(visible[e_i]), "->", ok, "| row after blur:", cut_rows(page))
    if not ok:
        sys.exit("STOP: the cut did not read back as asked; nothing saved")
    if not SAVE:
        say("dry run: closing unsaved"); return
    page.locator("#approve-cut-button").first.click(force=True, timeout=8000); time.sleep(3)
    say("approved; row:", cut_rows(page))
    page.locator("#save-button").first.click(force=True, timeout=8000); time.sleep(5)
    dlg = page.evaluate("""() => [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog, ytcp-confirmation-dialog')]
        .filter(e => e.offsetParent !== null).map(e => e.innerText.replace(/\\s+/g, ' ').slice(0, 400)).join(' || ')""")
    say("dialog:", dlg or "none")
    if dlg:
        # the confirm dialog's own buttons (measured: not #confirm-button); click the one that saves
        btns = page.evaluate("""() => { const d = [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog, ytcp-confirmation-dialog, [role=dialog]')]
                .filter(e => e.offsetParent !== null && /ความยาวใหม่/.test(e.innerText));
            if (!d.length) return [];
            return [...d[d.length - 1].querySelectorAll('button, ytcp-button, [role=button]')].filter(e => e.offsetParent !== null)
                .map((e, i) => ({i, id: e.id, text: (e.innerText || '').trim(), aria: e.getAttribute('aria-label') || ''})); }""")
        say("dialog buttons:", btns)
        say("dialog detail:", page.evaluate("""() => { const d = [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog, ytcp-confirmation-dialog, [role=dialog]')]
                .filter(e => e.offsetParent !== null && /ความยาวใหม่/.test(e.innerText));
            if (!d.length) return null; const r = d[d.length - 1];
            return {text: r.innerText.replace(/\\s+/g, ' '),
                    ctrls: [...r.querySelectorAll('[aria-disabled], [disabled], ytcp-checkbox-lit, tp-yt-paper-checkbox, [role=checkbox], input')]
                      .map(e => e.tagName + '#' + e.id + ' dis=' + e.getAttribute('aria-disabled') + '/' + e.hasAttribute('disabled')
                                + ' chk=' + e.getAttribute('aria-checked') + ' ' + (e.innerText || '').trim().slice(0, 40))}; }"""))
        # measured 2026-09-27: [#cancel-button ยกเลิก, #apply-button ยืนยันการเปลี่ยนแปลง]
        if "--confirm" not in sys.argv:
            say("a dialog asks for confirmation: read it above; rerun with --save --confirm to accept. Closing unsaved."); return
        yes = [b for b in btns if b["text"] in ("ยืนยันการเปลี่ยนแปลง", "Confirm changes")]
        if not yes:
            say("STOP: no save/confirm button in the dialog; closing unsaved"); return
        # a JS element.click() on the inner button did NOT register (measured: no processing state afterwards);
        # a real mouse click on the visible #apply-button does
        # #apply-button stays aria-disabled until #confirm-checkbox ("ฉันรับทราบว่าการเปลี่ยนแปลงเหล่านี้มีผลถาวร") is ticked
        page.locator("#confirm-checkbox #checkbox >> visible=true").last.click(force=True, timeout=8000); time.sleep(1.5)
        say("acknowledged; apply disabled:", page.locator("#apply-button >> visible=true").last.get_attribute("aria-disabled"))
        page.locator("#apply-button >> visible=true").last.click(force=True, timeout=8000)
        time.sleep(15); say("confirmed with", repr(yes[-1]["text"]))
        still = page.evaluate("""() => [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog, [role=dialog]')]
            .filter(e => e.offsetParent !== null && /ความยาวใหม่/.test(e.innerText)).length""")
        say("confirm dialog still open:", still)
    say("editor text:", page.evaluate("() => (document.querySelector('#video-editor') || document.body).innerText.replace(/\\s+/g, ' ').slice(0, 400)"))


with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
    page = b.contexts[0].new_page()
    page.set_viewport_size({"width": 1400, "height": 1000})
    try:
        run(page)
    finally:
        page.close()
