"""Read-only: list the Ghost Rules Studio content rows (video id, title, visibility/date text). usage: python yt_list.py [shot.png]"""
import sys, time, base64
sys.path.insert(0, '/opt/MoonieXHQ/Work/cn-series/publish')
from cdp_raw import Tab
t = Tab(19226)
try:
    t.call("Page.enable"); t.call("Runtime.enable")
    t.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    t.call("Emulation.setDeviceMetricsOverride", {"width": 1400, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    t.goto("https://studio.youtube.com/channel/UCBhmXUsXrAFPXJJeyC4vcxQ/videos/upload", 8)
    end = time.time() + 40
    while time.time() < end and not t.js("document.querySelectorAll('ytcp-video-row').length"): time.sleep(1)
    time.sleep(3)
    print(t.js("""JSON.stringify([...document.querySelectorAll('ytcp-video-row')].map(r=>{const a=r.querySelector('a#video-title, a[href*="/video/"]');const m=a&&a.href.match(/video\\/([\\w-]+)/);
      return {id:m&&m[1], title:(a&&a.innerText||'').trim().slice(0,70), vis:(r.querySelector('.tablecell-visibility')||{innerText:''}).innerText.replace(/\\s+/g,' ').trim(), date:(r.querySelector('.tablecell-date')||{innerText:''}).innerText.replace(/\\s+/g,' ').trim().slice(0,40)}}), null, 1)"""))
    if len(sys.argv) > 1:
        try: open(sys.argv[1], 'wb').write(base64.b64decode(t.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True}, timeout=25)["data"])); print("screenshot:", sys.argv[1])
        except TimeoutError: print("screenshot timed out")
finally:
    t.close()
