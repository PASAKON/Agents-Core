#!/usr/bin/env python3
"""EP6 hook «ผู้ต้องสงสัย» — transparent 720x1280 CCTV overlay cards, rendered by headless Chromium (Thai shaping is
correct there; PIL without raqm is not). Zero model: HTML -> PNG. Text is composed here, never generated.

  ep6_hook_overlay.py <out_dir> [--box x y w h]     writes cctv-a.png (REC + time + red box + label) and cctv-b.png (+ ticker)
Colours/fonts are the CCTV look (white-on-black monospace-ish, red box), NOT the brand palette: the hook is a parody
of a public street camera and lasts 2 s.
"""
import argparse, pathlib, sys
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--box", nargs=4, type=int, default=[190, 560, 340, 300], metavar=("X", "Y", "W", "H"))
ap.add_argument("--time", default="10:42:07")
a = ap.parse_args()
out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
bx, by, bw, bh = a.box

CSS = """
html,body{margin:0;background:transparent;width:720px;height:1280px;overflow:hidden;font-family:'Noto Sans Thai','Prompt',sans-serif}
.rec{position:absolute;left:34px;top:46px;color:#fff;font-weight:700;font-size:40px;letter-spacing:2px;text-shadow:0 0 6px #000,0 0 2px #000}
.dot{display:inline-block;width:26px;height:26px;border-radius:50%;background:#e11;margin-right:14px;vertical-align:-2px;box-shadow:0 0 10px #e11}
.cam{position:absolute;right:34px;top:50px;color:#fff;font-weight:600;font-size:30px;text-shadow:0 0 6px #000,0 0 2px #000;text-align:right}
.ts{position:absolute;right:34px;bottom:70px;color:#fff;font-weight:700;font-size:38px;letter-spacing:2px;text-shadow:0 0 6px #000,0 0 2px #000}
.box{position:absolute;border:6px solid #ff2a2a;box-shadow:0 0 14px rgba(255,42,42,.7)}
.box:before,.box:after{content:'';position:absolute;width:34px;height:34px;border:0 solid #fff}
.box:before{left:-6px;top:-6px;border-top-width:6px;border-left-width:6px}
.box:after{right:-6px;bottom:-6px;border-bottom-width:6px;border-right-width:6px}
.tag{position:absolute;background:#ff2a2a;color:#fff;font-weight:800;font-size:46px;padding:2px 20px 6px;white-space:nowrap}
.tick{position:absolute;left:0;right:0;bottom:170px;background:rgba(0,0,0,.72);color:#ffe14d;font-weight:700;font-size:40px;
 padding:14px 30px 18px;text-align:center;line-height:1.25}
"""
BASE = f"""<div class=rec><span class=dot></span>REC</div>
<div class=cam>CAM-03<br>กล้องสาธารณะ</div>
<div class=ts>{a.time}</div>
<div class=box style="left:{bx}px;top:{by}px;width:{bw}px;height:{bh}px"></div>
<div class=tag style="left:{bx - 6}px;top:{by - 66}px">ผู้ต้องสงสัย</div>"""
TICK = "<div class=tick>ความเร็ว 38 กม./ชม.<br>เจตนา: ไม่ทราบ</div>"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 720, "height": 1280})
    for name, body in (("cctv-a", BASE), ("cctv-b", BASE + TICK)):
        pg.set_content(f"<style>{CSS}</style>{body}")
        pg.wait_for_timeout(250)
        pg.screenshot(path=str(out / f"{name}.png"), omit_background=True)
    b.close()
print("wrote", out / "cctv-a.png", out / "cctv-b.png")
