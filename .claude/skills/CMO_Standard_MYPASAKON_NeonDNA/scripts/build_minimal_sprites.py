from pathlib import Path
from playwright.sync_api import sync_playwright

KIT_DIR = Path("/Users/gob/.gemini/antigravity/brain/5e00df47-82c6-4268-a12f-3377d70c2d23/scratch/mypasakon_neon_kit")
OUT_DIR = KIT_DIR / "sprites_minimal"
OUT_DIR.mkdir(parents=True, exist_ok=True)

COMMON_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=Kanit:wght@500;600;700;800&family=JetBrains+Mono:wght@600;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  width: 1080px; height: 1920px;
  background: transparent;
  font-family: 'Kanit', 'Archivo', sans-serif;
  overflow: hidden;
  position: relative;
}
/* Style A: RAZOR CHAMFER (12px spine -> 4px top -> 1px hairline, 45-deg cut corners) */
.razor-frame {
  position: absolute;
  border-top: 4px solid #7CFF00;
  border-left: 12px solid #7CFF00;
  border-right: 1.5px solid rgba(124, 255, 0, 0.55);
  border-bottom: 1.5px solid rgba(124, 255, 0, 0.55);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.85), 0 0 32px rgba(124, 255, 0, 0.18);
  pointer-events: none;
}
.razor-frame::before {
  content: "";
  position: absolute;
  top: -4px; right: -2px;
  width: 28px; height: 28px;
  background: linear-gradient(225deg, #040A07 46%, #7CFF00 47%, #7CFF00 58%, transparent 59%);
}
.razor-frame::after {
  content: "";
  position: absolute;
  bottom: -2px; right: -2px;
  width: 36px; height: 6px;
  background: #7CFF00;
  box-shadow: 0 0 12px #7CFF00;
}
.pill {
  position: absolute;
  transform: translateX(-50%);
  background: rgba(6, 14, 10, 0.92);
  border: 1.5px solid rgba(124, 255, 0, 0.65);
  border-left: 6px solid #7CFF00;
  padding: 8px 26px;
  font-family: 'Archivo', 'Kanit', sans-serif;
  font-weight: 800;
  font-size: 26px;
  letter-spacing: 1px;
  color: #F4FFF8;
  box-shadow: 0 10px 28px rgba(0,0,0,0.8);
  white-space: nowrap;
}
.pill span { color: #7CFF00; }
.sub-pill {
  position: absolute;
  left: 540px;
  transform: translateX(-50%);
  background: rgba(4, 10, 7, 0.88);
  border: 1.5px solid rgba(124, 255, 0, 0.45);
  border-left: 8px solid #7CFF00;
  padding: 12px 38px;
  font-family: 'Kanit', sans-serif;
  font-weight: 800;
  font-size: 56px;
  line-height: 1.15;
  color: #F4FFF8;
  box-shadow: 0 16px 42px rgba(0,0,0,0.88), 0 0 28px rgba(124, 255, 0, 0.14);
  white-space: nowrap;
}
.sub-pill .hi { color: #7CFF00; }
.disclaimer {
  position: absolute;
  left: 540px; top: 1790px;
  transform: translateX(-50%);
  font-family: 'Kanit', sans-serif;
  font-weight: 500;
  font-size: 22px;
  letter-spacing: 0.5px;
  color: rgba(215, 245, 228, 0.72);
  background: rgba(4, 10, 7, 0.75);
  padding: 6px 22px;
  border-radius: 99px;
  border: 1px solid rgba(124, 255, 0, 0.22);
  white-space: nowrap;
}
"""

def wrap_html(body_html: str) -> str:
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{COMMON_CSS}</style></head><body>{body_html}</body></html>"

# 1. Beat 1 Frame Overlay (0.00 - 3.70s): Top Style A frame around x=84..996, y=120..600 + pill "LIVE XAUUSD"
BEAT1_FRAME = """
<div class="razor-frame" style="left:84px; top:120px; width:912px; height:480px;"></div>
<div class="pill" style="left:540px; top:94px;"><span>●</span> LIVE XAUUSD</div>
<div class="disclaimer">MYPASAKON AI LAB · สร้างระบบอัตโนมัติจากประสบการณ์จริง</div>
"""

# 2. Beat 2 Frame Overlay (3.70 - 7.56s): Bottom Style A workspace frame around x=72..1008, y=920..1720
BEAT2_FRAME = """
<div class="razor-frame" style="left:72px; top:920px; width:936px; height:800px;"></div>
<div class="disclaimer">MYPASAKON AI LAB · สร้างระบบอัตโนมัติจากประสบการณ์จริง</div>
"""

# 3. Beat 3 Dark Canvas Base + Avatar Ring + 3 Progressive Cards (7.56 - 11.93s)
def make_beat3_card(idx: str, name: str, desc: str, top_px: int) -> str:
    return f"""
    <div style="
      position:absolute; left:110px; top:{top_px}px; width:860px; height:190px;
      background: rgba(9, 20, 14, 0.94);
      border-top: 4px solid #7CFF00;
      border-left: 12px solid #7CFF00;
      border-right: 1.5px solid rgba(124, 255, 0, 0.38);
      border-bottom: 1.5px solid rgba(124, 255, 0, 0.38);
      box-shadow: 0 20px 50px rgba(0,0,0,0.85);
      display:flex; align-items:center; justify-content:space-between;
      padding: 0 44px;
    ">
      <div style="display:flex; align-items:center; gap:26px;">
        <div style="font-family:'JetBrains Mono',monospace; font-size:28px; font-weight:700; color:#7CFF00; opacity:0.85;">{idx}</div>
        <div style="font-family:'Archivo',sans-serif; font-size:54px; font-weight:800; color:#F4FFF8; letter-spacing:0.5px;">{name}</div>
      </div>
      <div style="
        font-family:'Kanit',sans-serif; font-size:32px; font-weight:600; color:#FF6B6B;
        background: rgba(255, 70, 70, 0.12); border: 1.5px solid rgba(255, 107, 107, 0.4);
        padding: 10px 26px; border-radius: 10px;
      ">✕ {desc}</div>
    </div>
    """

def make_beat3_stage(step: int, sub_html: str) -> str:
    cards = ""
    if step >= 1:
        cards += make_beat3_card("01", "ChatGPT", "ส่งคำสั่งเทรดไม่ได้", 650)
    if step >= 2:
        cards += make_beat3_card("02", "Gemini", "เชื่อมพอร์ตจริงไม่ได้", 870)
    if step >= 3:
        cards += make_beat3_card("03", "Grok", "ไม่มีระบบคุมพอร์ต", 1090)
    return f"""
    <!-- Avatar Neon Ring at cx=540, cy=280, r=190 (380x380) -->
    <div style="
      position:absolute; left:350px; top:90px; width:380px; height:380px;
      border-radius:50%; border: 6px solid #7CFF00;
      box-shadow: 0 0 42px rgba(124, 255, 0, 0.50), inset 0 0 22px rgba(124, 255, 0, 0.28);
    "></div>
    <div class="sub-pill" style="top:508px; font-size:50px;">{sub_html}</div>
    {cards}
    <div class="disclaimer">MYPASAKON AI LAB · สร้างระบบอัตโนมัติจากประสบการณ์จริง</div>
    """

# 4. Beat 4 Before/After Frame Overlay (11.93 - 15.00s):
# Top muted box (x=120..960, y=120..440) + Curved Arrow + Middle Hero Style A box (x=120..960, y=500..980)
BEAT4_FRAME = """
<!-- Top Muted Box: Generic AI Bot -->
<div style="
  position:absolute; left:120px; top:120px; width:840px; height:320px;
  border: 2px solid rgba(160, 195, 175, 0.35);
  box-shadow: 0 18px 40px rgba(0,0,0,0.75);
"></div>
<div class="pill" style="left:540px; top:94px; border-left-color:#88A896; color:#C5DDD0; font-size:24px;">บอทเทรดทั่วไป</div>

<!-- Middle Hero Style A Box: Claude Code Live -->
<div class="razor-frame" style="left:120px; top:500px; width:840px; height:480px;"></div>
<div class="pill" style="left:540px; top:472px;"><span>●</span> Claude Code · เทรดจริง</div>

<!-- Keanu-style Curved Connector Arrow from Top Box to Hero Box -->
<svg style="position:absolute; left:36px; top:250px; width:140px; height:520px; overflow:visible;" viewBox="0 0 140 520">
  <defs>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <path d="M 85 30 C 10 90, 10 350, 82 420" fill="none" stroke="#7CFF00" stroke-width="7" stroke-linecap="round" filter="url(#glow)"/>
  <path d="M 62 398 L 88 424 L 56 436" fill="none" stroke="#7CFF00" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>
</svg>

<div class="disclaimer">MYPASAKON AI LAB · สร้างระบบอัตโนมัติจากประสบการณ์จริง</div>
"""

# Subtitles for Beats 1, 2, 4 (placed on speaker's chest or clean divider, never on face)
SUBS = {
    "sub_01": ('<div class="sub-pill" style="top:1540px;">นี่คือ <span class="hi">AI ที่ผมใช้</span></div>'),
    "sub_02": ('<div class="sub-pill" style="top:1540px;"><span class="hi">เทรดจริง</span></div>'),
    "sub_03": ('<div class="sub-pill" style="top:780px;">มาตลอด <span class="hi">8 เดือน</span></div>'),
    "sub_04": ('<div class="sub-pill" style="top:780px;"><span class="hi">&gt;_ Claude Code</span></div>'),
    "sub_09": ('<div class="sub-pill" style="top:1620px;">บอทเทรด <span class="hi">AI Agent</span></div>'),
    "sub_10": ('<div class="sub-pill" style="top:1620px;">ลองมาหมดแล้ว<span class="hi">จริงๆ</span></div>'),
}

PAGES = {
    "beat1_frame.png": BEAT1_FRAME,
    "beat2_frame.png": BEAT2_FRAME,
    "beat3_step0.png": make_beat3_stage(0, 'ลองมา<span class="hi">หมดแล้ว</span>'),
    "beat3_step1.png": make_beat3_stage(1, 'ทั้ง <span class="hi">ChatGPT</span>'),
    "beat3_step2.png": make_beat3_stage(2, 'ทั้ง <span class="hi">Gemini</span>'),
    "beat3_step3.png": make_beat3_stage(3, 'ทั้ง <span class="hi">Grok</span>'),
    "beat4_frame.png": BEAT4_FRAME,
}
for k, v in SUBS.items():
    PAGES[f"{k}.png"] = v

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=True,
    )
    page = browser.new_page(viewport={"width": 1080, "height": 1920})
    for fname, body in PAGES.items():
        html_file = OUT_DIR / (fname + ".html")
        html_file.write_text(wrap_html(body), encoding="utf-8")
        page.goto(f"file://{html_file}", wait_until="networkidle")
        page.wait_for_timeout(150)
        page.screenshot(path=str(OUT_DIR / fname), omit_background=True)
        print("Rendered:", fname)
    browser.close()
