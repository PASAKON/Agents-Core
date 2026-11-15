import sys, json, re, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright
CDP="http://127.0.0.1:9226"
def project_url():
    for t in json.load(urllib.request.urlopen(CDP+"/json/list",timeout=8)):
        if t["type"]=="page" and "/project/" in t["url"] and "/edit/" not in t["url"]: return t["url"]
    raise SystemExit("no project tab")
class D:
    def __init__(s):
        s.pw=sync_playwright().start(); s.b=s.pw.chromium.connect_over_cdp(CDP); s.ctx=s.b.contexts[0]
        # reuse my own tab if title marked, else new
        s.page=None
        for p in s.ctx.pages:
            try:
                if p.evaluate("window.name")=="ep4s_op": s.page=p
            except Exception: pass
        if s.page is None:
            s.page=s.ctx.new_page(); s.page.set_viewport_size({"width":1600,"height":1000})
            s.page.goto(project_url(),wait_until="domcontentloaded",timeout=45000); s.page.evaluate("window.name='ep4s_op'")
            s.page.wait_for_timeout(3000)
        s.mute()
    def mute(s): s.page.evaluate("document.querySelectorAll('video,audio').forEach(v=>{v.muted=true;v.volume=0})")
    def close(s):
        try: s.b.close()
        except Exception: pass
        try: s.pw.stop()
        except Exception: pass
