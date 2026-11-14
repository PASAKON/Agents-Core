"""Read-only readback of a video's stored schedule: reload the edit page, open the visibility dialog, read the selected radio,
date and time, then discard (reload, accepting the leave prompt). usage: python yt_readback.py <video_id> <shot.png>"""
import sys, time, base64
sys.path.insert(0, '/opt/MoonieXHQ/Work/cn-series/publish')
from cdp_raw import Tab
vid, shot = sys.argv[1], sys.argv[2]
t = Tab(19226)
try:
    t.call("Page.enable"); t.call("Runtime.enable")
    t.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    t.call("Emulation.setDeviceMetricsOverride", {"width": 1400, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    t.goto(f"https://studio.youtube.com/video/{vid}/edit", 8)
    end = time.time() + 45
    while time.time() < end and not t.js("!!document.querySelector('ytcp-video-metadata-visibility #select-button')"): time.sleep(1)
    time.sleep(2)
    print("title:", t.js("(document.querySelector('#title-textarea #textbox')||{}).innerText"))
    print("visibility box:", t.js("document.querySelector('ytcp-video-metadata-visibility').innerText.replace(/\\s+/g,' ').trim()"))
    print("thumb imgs:", t.js("JSON.stringify([...document.querySelectorAll('ytcp-thumbnails-compact-editor img, ytcp-thumbnail-editor img, #still-picker img')].map(i=>i.src.slice(0,95)))"))
    print("kids:", t.js("[...document.querySelectorAll('tp-yt-paper-radio-button[name^=VIDEO_MADE_FOR_KIDS]')].map(r=>r.getAttribute('name')+':'+r.getAttribute('aria-checked')).join(',')"))
    t.js("(()=>{const b=document.querySelector('ytcp-video-metadata-visibility #select-button');b.scrollIntoView({block:'center'});b.click();return 'ok'})()")
    time.sleep(4)
    print("radios:", t.js("[...document.querySelectorAll('tp-yt-paper-radio-button')].filter(r=>r.getBoundingClientRect().width>0).map(r=>r.getAttribute('name')+':'+r.getAttribute('aria-checked')).join(',')"))
    t.js("(()=>{const e=document.querySelector('#second-container-expand-button');if(e&&e.getBoundingClientRect().width>0)e.click()})()")
    time.sleep(2)
    print("date:", t.js("(()=>{const e=document.querySelector('ytcp-datetime-picker #datepicker-trigger .dropdown-trigger-text');return e?e.innerText.trim():null})()"))
    print("time:", t.js("(()=>{const e=document.querySelector('#time-of-day-container input');return e?e.value:null})()"))
    print("dialog text:", t.js("(document.querySelector('ytcp-visibility-scheduler')||{innerText:''}).innerText.replace(/\\s+/g,' ').slice(0,200)"))
    try:
        open(shot, 'wb').write(base64.b64decode(t.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True}, timeout=25)["data"])); print("screenshot:", shot)
    except TimeoutError: print("screenshot timed out")
finally:
    t.close()
