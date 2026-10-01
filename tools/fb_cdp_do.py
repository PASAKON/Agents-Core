#!/usr/bin/env python3
"""fb_cdp_do.py <actions.json> <out-prefix> — drive a Facebook page over CDP (default http://127.0.0.1:9281) from a JSON action list; writes <out>.txt (frames, UI list, dialogs, body) and <out>.png.
Actions: goto click clickvis clickrole clicksel fill ffill fclick fclicksel key type wait upload choose(file chooser) drag mouse eval. Env NOVIEW=1 keeps the browser window size (headed Chrome).
Used 2026-10-01 for the Mimi page (name, bio, cover, profile photo, EP1 Reel schedule). Runs on winbox, whose venv has playwright. Click by element, not by screenshot coordinates.
"""
# usage: fb_do.py actions.json out_prefix   (actions: goto/click/fill/key/wait/upload/shot, list of dicts)
import json, sys, os
from playwright.sync_api import sync_playwright
acts = json.load(open(sys.argv[1], encoding="utf-8")); out = sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9281")
    pg = b.contexts[0].pages[0]
    if not os.environ.get("NOVIEW"): pg.set_viewport_size({"width": 1280, "height": 900})
    for a in acts:
        k = a["do"]
        try:
            if k == "goto": pg.goto(a["url"], wait_until="domcontentloaded")
            elif k == "click": pg.get_by_text(a["text"], exact=a.get("exact", True)).nth(a.get("nth", 0)).click(timeout=8000)
            elif k == "clickrole": pg.get_by_role(a["role"], name=a["text"], exact=a.get("exact", True)).nth(a.get("nth", 0)).click(timeout=8000)
            elif k in ("fclick", "ffill"):
                done = False
                for fr in pg.frames:
                    loc = fr.get_by_text(a["text"], exact=True) if k == "fclick" else fr.locator(a["sel"])
                    if loc.count() > 0:
                        t0 = loc.nth(a.get("nth", 0))
                        t0.click(timeout=8000) if k == "fclick" else t0.fill(a["value"], timeout=8000)
                        done = True; break
                if not done: raise Exception("not in any frame: " + str(a.get("text") or a.get("sel")))
            elif k == "fclicksel":
                done = False
                for fr in pg.frames:
                    if fr.locator(a["sel"]).count() > 0:
                        fr.locator(a["sel"]).nth(a.get("nth", 0)).click(timeout=8000); done = True; break
                if not done: raise Exception("no such selector in any frame: " + a["sel"])
            elif k == "mouse": pg.mouse.click(a["x"], a["y"])
            elif k == "clicksel": pg.locator(a["sel"]).nth(a.get("nth", 0)).click(timeout=8000)
            elif k == "fill": pg.locator(a["sel"]).nth(a.get("nth", 0)).fill(a["value"], timeout=8000)
            elif k == "key": pg.keyboard.press(a["key"])
            elif k == "upload": pg.locator(a["sel"]).nth(a.get("nth", 0)).set_input_files(a["path"])
            elif k == "choose":
                with pg.expect_file_chooser(timeout=10000) as fc:
                    pg.get_by_text(a["text"], exact=a.get("exact", True)).nth(a.get("nth", 0)).click(timeout=8000)
                fc.value.set_files(a["path"])
            elif k == "drag":
                pg.mouse.move(a["x1"], a["y1"]); pg.mouse.down(); pg.mouse.move(a["x2"], a["y2"], steps=12); pg.mouse.up()
            elif k == "type":
                pg.keyboard.type(a["value"], delay=a.get("delay", 8))
            elif k == "clickvis":
                els = pg.get_by_text(a["text"], exact=True).all(); hit = False
                if a.get("last"): els = els[::-1]
                for el in els:
                    if el.is_visible():
                        bb = el.bounding_box()
                        if bb and bb["y"] > a.get("miny", 0) and bb["x"] < a.get("maxx", 99999):
                            el.click(timeout=8000); hit = True; print("clicked at", int(bb["x"]), int(bb["y"])); break
                if not hit: raise Exception("no visible match for " + a["text"] + " of " + str(len(els)))
            elif k == "eval":
                print("EVAL:", pg.evaluate(a["js"]))
            elif k == "wait": pg.wait_for_timeout(a["ms"])
            print("ok", k, a.get("text") or a.get("sel") or a.get("url") or "")
        except Exception as e:
            print("FAIL", k, a.get("text") or a.get("sel") or "", str(e)[:150].replace("\n", " "))
    pg.wait_for_timeout(2500)
    try: pg.screenshot(path=out + ".png", timeout=12000)
    except Exception as e:
        print("screenshot via CDP:", str(e)[:60])
        try:
            import base64
            cs = pg.context.new_cdp_session(pg)
            open(out + ".png", "wb").write(base64.b64decode(cs.send("Page.captureScreenshot", {"format": "png"})["data"]))
        except Exception as e2: print("screenshot skipped:", str(e2)[:80])
    ui = pg.evaluate("""() => { const v=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0}; return [...document.querySelectorAll('input,textarea,[role=button],button,a[role=link]')].filter(v).map(e=>(e.tagName+'|'+(e.getAttribute('aria-label')||'')+'|'+(e.value||'')+'|'+(e.innerText||'').slice(0,40).replace(/\\n/g,' '))).filter(s=>!/^A\\|\\|\\|$/.test(s)).slice(0,140).join('\\n') }""")
    fr_txt = "\n".join("[frame %d %s] " % (i, f.url[:80]) + f.evaluate("document.body ? document.body.innerText.slice(0,1500) : ''").replace("\n", " | ")[:700] for i, f in enumerate(pg.frames))
    dl = "\n=====FRAMES=====\n" + fr_txt + "\n=====UI=====\n" + ui + "\n=====DIALOGS=====\n" + "\n---\n".join(pg.locator("[role=dialog]").all_inner_texts())[:3000]
    open(out + ".txt", "w", encoding="utf-8").write(pg.title() + dl + "\n=====BODY=====\n" + pg.inner_text("body")[:30000])
    print("done", pg.title())
