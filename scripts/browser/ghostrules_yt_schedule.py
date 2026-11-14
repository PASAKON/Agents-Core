"""Schedule one Ghost Rules video in YouTube Studio over winbox Chrome 9226 (tunnel 127.0.0.1:19226).

usage:
  python yt_schedule.py <video_id> <DD> <Mon-abbr-Thai> <YYYY> <HH:MM> <shot_prefix> [--dry-run]
  e.g. python yt_schedule.py K1djkamjxJE 14 พ.ย. 2026 19:00 /path/sched_ep3 --dry-run
--dry-run does everything EXCEPT the final Save (#save): it fills the schedule dialog, presses Done (#save-button), screenshots,
then discards the unsaved edit by reloading and reads the stored visibility back.
Real run: presses Save, waits for it to settle, reloads, reads visibility back. Never touches thumbnails/title.
Studio must already be on the Ghost Rules channel (checked via the dashboard #entity-name before anything is done).
Run with the org venv (needs websockets): /opt/MoonieXHQ/Agents/Core/.venv/bin/python
Uses Emulation.setFocusEmulationEnabled (background-tab fix) and stable ids (#select-button, #second-container-expand-button,
#datepicker-trigger, #time-of-day-container, #save-button, #save), never button text."""
import sys, time, json, base64
sys.path.insert(0, '/opt/MoonieXHQ/Work/cn-series/publish')
from cdp_raw import Tab

args = [a for a in sys.argv[1:] if not a.startswith('--')]
DRY = '--dry-run' in sys.argv
VID, DD, MON, YYYY, HHMM, PFX = args[:6]
DATE_TXT = f"{int(DD)} {MON} {YYYY}"
URL = "https://studio.youtube.com/video/" + VID + "/edit"
VIS = "((document.querySelector('ytcp-video-metadata-visibility')||{}).innerText||'').replace(/\\s+/g,' ').trim()"
SAVE = "(()=>{const s=document.querySelector('ytcp-button#save');return s?(s.getAttribute('aria-disabled')==='true'?'disabled':'enabled'):'nosave'})()"


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
        print("screenshot:", p, flush=True)
    except TimeoutError:
        print("screenshot timed out:", p, flush=True)


def open_edit(t):
    t.goto(URL, 8)
    if not wait_for(t, "!!document.querySelector('ytcp-video-metadata-visibility #select-button')", bool, 45):
        raise SystemExit("FAIL: visibility box never appeared title=" + str(t.js("document.title")) + " body=" + str(t.js("(document.body.innerText||'').slice(0,80)")))
    time.sleep(2)


t = Tab(19226)
rc = 0
try:
    t.call("Page.enable"); t.call("Runtime.enable")
    t.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    t.call("Emulation.setDeviceMetricsOverride", {"width": 1400, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    open_edit(t)
    print("mode:", "DRY-RUN (no Save)" if DRY else "REAL", "| target:", DATE_TXT, HHMM, flush=True)
    print("title:", t.js("(document.querySelector('#title-textarea #textbox')||{}).innerText"))
    print("visibility before:", t.js(VIS))
    t.js("(()=>{const b=document.querySelector('ytcp-video-metadata-visibility #select-button');b.scrollIntoView({block:'center'});b.click();return 'ok'})()")
    if not wait_for(t, "!!document.querySelector('#second-container-expand-button') && document.querySelector('#second-container-expand-button').getBoundingClientRect().width>0", bool, 20):
        raise SystemExit("FAIL: schedule expander not visible")
    t.js("document.querySelector('#second-container-expand-button').click()")
    if not wait_for(t, "!!document.querySelector('ytcp-datetime-picker #datepicker-trigger') && document.querySelector('ytcp-datetime-picker #datepicker-trigger').getBoundingClientRect().width>0", bool, 15):
        raise SystemExit("FAIL: schedule date picker not visible")
    print("default date shown:", t.js("document.querySelector('ytcp-datetime-picker #datepicker-trigger .dropdown-trigger-text').innerText.trim()"))
    print("timezone label:", t.js("(()=>{const b=document.querySelector('#timezone-select-button');return b?b.innerText.replace(/\\s+/g,' ').trim():null})()"))
    # date: open the calendar popup, type the date into its text input, Enter
    t.js("document.querySelector('ytcp-datetime-picker #datepicker-trigger').click()")
    time.sleep(2)
    n = wait_for(t, "[...document.querySelectorAll('ytcp-date-picker input, ytcp-date-picker tp-yt-paper-input input')].filter(i=>i.getBoundingClientRect().width>0).length", lambda v: v and v > 0, 10)
    print("date inputs visible:", n)
    if not n: shot(t, "x_datepicker_fail"); raise SystemExit("FAIL: date input not visible")
    # the typed date shows in the popup input but Enter does not commit it (dry run 14 Nov): click the day cell instead
    rect = t.js("(()=>{const dp=document.querySelector('ytcp-date-picker');const c=[...dp.querySelectorAll('*')].filter(e=>e.children.length===0&&(e.innerText||'').trim()==='%s'&&e.getBoundingClientRect().width>0)[0];if(!c)return null;const r=c.getBoundingClientRect();return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2,cls:c.className,tag:c.tagName,aria:c.getAttribute('aria-disabled')})})()" % str(int(DD)))
    print("day cell:", rect)
    if not rect: shot(t, "x_nodaycell"); raise SystemExit("FAIL: day cell not found")
    r = json.loads(rect)
    for typ in ("mouseMoved", "mousePressed", "mouseReleased"):   # real mouse events: the Polymer day cell ignores element.click()
        t.call("Input.dispatchMouseEvent", {"type": typ, "x": r["x"], "y": r["y"], "button": "left", "clickCount": 1})
    time.sleep(2)
    d = t.js("document.querySelector('ytcp-datetime-picker #datepicker-trigger .dropdown-trigger-text').innerText.trim()")
    print("date after:", d)
    if d != DATE_TXT: shot(t, "x_date_mismatch"); raise SystemExit(f"FAIL: date shows {d!r}, wanted {DATE_TXT!r}")
    # time
    t.js("(()=>{const i=document.querySelector('#time-of-day-container input');i.focus();i.select();return 'ok'})()")
    t.call("Input.insertText", {"text": HHMM})
    for typ in ("keyDown", "keyUp"):
        t.call("Input.dispatchKeyEvent", {"type": typ, "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
    time.sleep(2)
    tm = t.js("document.querySelector('#time-of-day-container input').value")
    print("time after:", tm)
    if tm.strip() != HHMM: shot(t, "x_time_mismatch"); raise SystemExit(f"FAIL: time shows {tm!r}, wanted {HHMM!r}")
    print("browser tz:", t.js("Intl.DateTimeFormat().resolvedOptions().timeZone + ' now=' + new Date().toString()"))
    t.js("document.querySelector('ytcp-datetime-picker #datepicker-trigger').scrollIntoView({block:'center'})")
    # commit the time: blur the field with Tab, then see whether Done enabled; else pick the matching option in the time dropdown
    for typ in ("keyDown", "keyUp"):
        t.call("Input.dispatchKeyEvent", {"type": typ, "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
    time.sleep(2)
    print("done after Tab:", t.js("(()=>{const b=[...document.querySelectorAll('ytcp-button#save-button')].find(b=>b.getBoundingClientRect().width>0);return b?b.getAttribute('aria-disabled'):'none'})()"))
    print("date re-read:", t.js("document.querySelector('ytcp-datetime-picker #datepicker-trigger .dropdown-trigger-text').innerText.trim()"))
    print("done button label:", t.js("(()=>{const b=[...document.querySelectorAll('ytcp-button#save-button')].find(b=>b.getBoundingClientRect().width>0);return b?b.innerText.trim()+'|'+b.getAttribute('aria-disabled'):'none'})()"))
    shot(t, "2_dialog_filled")
    print("done click:", t.js("(()=>{const b=[...document.querySelectorAll('ytcp-button#save-button')].find(b=>b.getBoundingClientRect().width>0);if(!b||b.getAttribute('aria-disabled')==='true')return 'none';b.click();return 'ok'})()"))
    print("visibility in form:", wait_for(t, VIS, lambda v: 'กำหนดเวลา' in (v or '') or 'Scheduled' in (v or ''), 10))
    sv = wait_for(t, SAVE, lambda v: v == 'enabled', 15)
    print("save button:", sv)
    if sv != 'enabled': raise SystemExit("FAIL: Save stayed " + str(sv))
    shot(t, "3_form_before_save")
    if DRY:
        print("DRY-RUN: Save NOT pressed; discarding the unsaved edit by reload")
        open_edit(t)
        after = t.js(VIS)
        print("visibility readback after discard:", after)
        if 'กำหนดเวลา' in after: print("!! scheduled after a dry run"); rc = 3
        else: print("OK: unchanged")
    else:
        print("save click:", t.js("(()=>{const s=document.querySelector('ytcp-button#save');if(!s||s.getAttribute('aria-disabled')==='true')return 'disabled';s.click();return 'ok'})()"))
        print("save settled:", wait_for(t, SAVE, lambda v: v == 'disabled', 40))
        time.sleep(4)
        open_edit(t)
        after = t.js(VIS)
        print("visibility readback after reload:", after)
        print("title readback:", t.js("(document.querySelector('#title-textarea #textbox')||{}).innerText"))
        print("thumb imgs:", t.js("JSON.stringify([...document.querySelectorAll('ytcp-thumbnails-compact-editor img, ytcp-thumbnail-editor img')].map(i=>i.src.slice(0,80)))"))
        shot(t, "4_readback")
        print("NOTE: the visibility box shows only 'กำหนดเวลาไว้'; the stored date/time is read back with yt_readback.py (dialog)")
finally:
    t.close()
sys.exit(rc)
