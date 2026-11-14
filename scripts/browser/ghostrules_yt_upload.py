"""Upload ONE Ghost Rules video as PRIVATE through YouTube Studio on winbox Chrome 9226 (tunnel 127.0.0.1:19226), raw CDP.

usage: python yt_upload.py <video_path_on_winbox> <thumb_path_on_winbox> <TH_dir> <shot_prefix>
  TH_dir holds title.txt, description.txt, tags.txt (comma separated). Always saves PRIVATE; scheduling is yt_schedule.py.
Fixes carried over from earlier runs: Emulation.setFocusEmulationEnabled (background tab paints no frames); DOM.setFileInputFiles
(Chrome reads the path itself, any size); NEVER close the tab once the file is set and the upload % is still counting (that kills
the upload), so on any failure after the file is set the tab is LEFT OPEN and its id printed; tags = one chip per tag + Enter.
Studio must already be on the Ghost Rules channel (checked via #entity-name)."""
import sys, time, json, base64, re
sys.path.insert(0, '/opt/MoonieXHQ/Work/cn-series/publish')
from cdp_raw import Tab

VIDEO, THUMB, THDIR, PFX = sys.argv[1:5]
title = open(THDIR + '/title.txt', encoding='utf-8').read().strip()
desc = open(THDIR + '/description.txt', encoding='utf-8').read().strip()
tags = [x.strip() for x in open(THDIR + '/tags.txt', encoding='utf-8').read().strip().split(',') if x.strip()]
CHANNEL = "https://studio.youtube.com/channel/UCBhmXUsXrAFPXJJeyC4vcxQ"


def say(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)


def wait_for(t, expr, want, secs, step=1.0):
    end, v = time.time() + secs, None
    while time.time() < end:
        v = t.js(expr)
        if want(v): return v
        time.sleep(step)
    return v


def shot(t, name):
    p = f"{PFX}_{name}.png"
    try:
        open(p, 'wb').write(base64.b64decode(t.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True}, timeout=25)["data"]))
        say("screenshot:", p)
    except TimeoutError: say("screenshot timed out:", p)


def key(t, k, code, vk):
    for typ in ("keyDown", "keyUp"):
        t.call("Input.dispatchKeyEvent", {"type": typ, "key": k, "code": code, "windowsVirtualKeyCode": vk})


def fill(t, sel, text):
    t.js("(()=>{const e=document.querySelector(%s);e.focus();document.execCommand('selectAll');document.execCommand('delete');return 'ok'})()" % json.dumps(sel))
    t.call("Input.insertText", {"text": text})
    time.sleep(1)
    got = t.js("document.querySelector(%s).innerText" % json.dumps(sel)) or ''
    norm = lambda s: re.sub(r'\s+', ' ', s).strip()
    say(sel, "chars", len(got), "match" if norm(got) == norm(text) else "MISMATCH")
    if norm(got) != norm(text): raise RuntimeError("text mismatch in " + sel + ": " + got[:80])


t = Tab(19226)
file_set = False
ok = False
try:
    t.call("Page.enable"); t.call("Runtime.enable")
    t.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    t.call("Emulation.setDeviceMetricsOverride", {"width": 1400, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    t.goto(CHANNEL, 10)
    name = wait_for(t, "(document.querySelector('#entity-name')||{}).innerText", bool, 40)
    say("studio channel:", name)
    if name != "Ghost Rules": raise SystemExit("STOP: Studio is on %r, not 'Ghost Rules'" % name)
    wait_for(t, "!!document.querySelector('#upload-icon')", bool, 30)
    t.js("document.querySelector('#upload-icon').click()")
    time.sleep(4)
    wait_for(t, "!!document.querySelector('input[type=file]')", bool, 30)
    t.set_files("input[type=file]", [VIDEO]); file_set = True
    say("file set:", VIDEO)
    if not wait_for(t, "(()=>{const e=document.querySelector('#title-textarea #textbox');return !!e&&e.getBoundingClientRect().width>0})()", bool, 120):
        raise RuntimeError("title box never appeared")
    time.sleep(3)
    vid_url = t.js("(()=>{const a=document.querySelector('.video-url-fadeable a, a.ytcp-video-info');return a?a.href:null})()")
    say("video url:", vid_url)
    fill(t, "#title-textarea #textbox", title)
    fill(t, "#description-textarea #textbox", desc)
    # thumbnail input in the wizard
    n = t.js("document.querySelectorAll('input[type=file][accept*=image]').length")
    say("thumbnail inputs:", n)
    if n:
        t.set_files("input[type=file][accept*=image]", [THUMB]); time.sleep(6); say("thumbnail file set")
    t.js("document.querySelector('tp-yt-paper-radio-button[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]').click()")
    say("audience: not made for kids")
    t.js("(()=>{const b=document.querySelector('#toggle-button');b.scrollIntoView({block:'center'});b.click();return 'ok'})()")
    time.sleep(2)
    say("altered radio:", t.js("(()=>{const r=document.querySelector('tp-yt-paper-radio-button[name=VIDEO_HAS_ALTERED_CONTENT_YES]');if(!r)return 'none';r.scrollIntoView({block:'center'});r.click();return r.getAttribute('aria-checked')})()"))
    time.sleep(1)
    # tags: one chip per tag + Enter
    say("tags box:", t.js("(()=>{const i=document.querySelector('#tags-container input');if(!i)return 'none';i.scrollIntoView({block:'center'});i.focus();return 'ok'})()"))
    for tg in tags:
        t.call("Input.insertText", {"text": tg}); key(t, "Enter", "Enter", 13); time.sleep(0.4)
    say("tag chips:", t.js("document.querySelectorAll('#tags-container ytcp-chip, ytcp-free-text-chip-bar ytcp-chip').length"), "wanted", len(tags))
    shot(t, "5_filled")
    say("kids/altered:", t.js("[...document.querySelectorAll('tp-yt-paper-radio-button')].filter(r=>/KIDS_NOT|ALTERED_CONTENT_YES/.test(r.getAttribute('name')||'')).map(r=>r.getAttribute('name')+':'+r.getAttribute('aria-checked')).join(',')"))
    say("thumb imgs in wizard:", t.js("JSON.stringify([...document.querySelectorAll('ytcp-thumbnails-compact-editor img, ytcp-thumbnail-editor img')].map(i=>i.src.slice(0,70)))"))
    for step in range(3):
        t.js("document.querySelector('#next-button').click()"); time.sleep(3); say("next", step + 1)
    if not wait_for(t, "!!document.querySelector('tp-yt-paper-radio-button[name=PRIVATE]') && document.querySelector('tp-yt-paper-radio-button[name=PRIVATE]').getBoundingClientRect().width>0", bool, 20):
        raise RuntimeError("visibility radios not found")
    t.js("document.querySelector('tp-yt-paper-radio-button[name=PRIVATE]').click()"); time.sleep(1)
    say("radios:", t.js("[...document.querySelectorAll('tp-yt-paper-radio-button')].filter(r=>r.getBoundingClientRect().width>0).map(r=>r.getAttribute('name')+':'+r.getAttribute('aria-checked')).join(',')"))
    shot(t, "6_private")
    # wait for the upload % to stop counting (tab must stay open)
    last = ''
    for i in range(160):
        st = t.js("((document.querySelector('ytcp-video-upload-progress .progress-label, .progress-label')||{}).innerText||'')")
        if not re.search(r"(อัปโหลด|Upload)\D{0,12}\d{1,3}\s?%", st or ''): break
        if i % 4 == 0: say("uploading:", (st or '').strip()[:80])
        time.sleep(15)
    say("upload status:", (st or '').strip()[:120])
    say("done click:", t.js("(()=>{const b=document.querySelector('#done-button');if(!b||b.getAttribute('aria-disabled')==='true')return 'disabled';b.click();return 'ok'})()"))
    time.sleep(8)
    shot(t, "7_saved")
    rec = {"title": title, "video_url": vid_url, "file": VIDEO, "thumb_file": THUMB}
    json.dump(rec, open(PFX + ".json", "w"), ensure_ascii=False, indent=1)
    ok = True
finally:
    if ok or not file_set:
        t.close()
    else:
        say("FAILED after the file was set: tab LEFT OPEN, target id", t.tid)
sys.exit(0 if ok else 1)
