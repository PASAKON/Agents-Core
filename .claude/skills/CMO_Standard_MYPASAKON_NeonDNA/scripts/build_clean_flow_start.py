import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

KIT_DIR = Path("/Users/gob/.gemini/antigravity/brain/5e00df47-82c6-4268-a12f-3377d70c2d23/scratch/mypasakon_neon_kit")
SCRATCH = Path("/Users/gob/.gemini/antigravity/brain/5e00df47-82c6-4268-a12f-3377d70c2d23/scratch")
FLOW_DIR = KIT_DIR / "flow_inputs"
FLOW_DIR.mkdir(parents=True, exist_ok=True)

# Extract pure black chart area from capture3.mp4 (x=266..982, y=28..424 in 1248x660 -> 716x396)
chart_crop = FLOW_DIR / "clean_chart_crop.png"
subprocess.run([
    "ffmpeg", "-y", "-ss", "2.0", "-i", str(SCRATCH / "capture3.mp4"),
    "-vf", "crop=716:396:266:28,scale=960:530",
    "-frames:v", "1", "-update", "1", str(chart_crop)
], check=True)

HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1080px; height: 1920px;
    background: radial-gradient(circle at 50% 25%, #0A1F14 0%, #040A07 70%);
    font-family: 'Archivo', sans-serif;
    color: #F4FFF8;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 70px 60px;
    gap: 36px;
  }}
  .window {{
    width: 960px;
    background: rgba(6, 14, 10, 0.95);
    border: 2px solid rgba(124, 255, 0, 0.45);
    border-left: 10px solid #7CFF00;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.85), 0 0 40px rgba(124, 255, 0, 0.14);
    clip-path: polygon(0 0, calc(100% - 28px) 0, 100% 28px, 100% 100%, 28px 100%, 0 calc(100% - 28px));
    overflow: hidden;
  }}
  .win-bar {{
    height: 54px;
    background: rgba(124, 255, 0, 0.08);
    border-bottom: 1px solid rgba(124, 255, 0, 0.25);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
    color: #7CFF00;
    letter-spacing: 1.5px;
  }}
  .dots {{ display: flex; gap: 10px; }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; background: #7CFF00; box-shadow: 0 0 10px #7CFF00; }}
  .chart-wrap {{
    position: relative;
    width: 960px;
    height: 526px;
    background: #020503;
  }}
  .chart-wrap img {{
    width: 100%; height: 100%; object-fit: cover;
    filter: contrast(1.25) saturate(1.2) hue-rotate(-5deg);
  }}
  .term-body {{
    padding: 32px 34px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px;
    line-height: 1.75;
    color: #D2F7E1;
    background: #030806;
  }}
  .cmd {{ color: #7CFF00; font-weight: 700; }}
  .dim {{ color: #648E76; }}
  .ok {{ color: #00E676; font-weight: 700; }}
  .metrics {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    width: 960px;
  }}
  .m-card {{
    background: rgba(8, 20, 14, 0.92);
    border: 1.5px solid rgba(124, 255, 0, 0.35);
    border-top: 6px solid #7CFF00;
    padding: 24px 26px;
  }}
  .m-lbl {{ font-size: 16px; color: #78A88C; letter-spacing: 2px; margin-bottom: 8px; }}
  .m-val {{ font-size: 40px; font-weight: 800; color: #F4FFF8; }}
  .m-val span {{ color: #7CFF00; }}
</style>
</head>
<body>
  <div class="window">
    <div class="win-bar">
      <div class="dots"><div class="dot"></div><div class="dot" style="opacity:0.5"></div></div>
      <div>CLAUDE CODE · XAUUSD AUTONOMOUS ENGINE</div>
      <div>LIVE · 8M</div>
    </div>
    <div class="chart-wrap">
      <img src="file://{chart_crop}" />
    </div>
  </div>

  <div class="metrics">
    <div class="m-card">
      <div class="m-lbl">AI ENGINE</div>
      <div class="m-val"><span>CLAUDE</span> CODE</div>
    </div>
    <div class="m-card">
      <div class="m-lbl">SYMBOL</div>
      <div class="m-val">XAUUSD<span>.c</span></div>
    </div>
    <div class="m-card">
      <div class="m-lbl">UPTIME</div>
      <div class="m-val"><span>8</span> MONTHS</div>
    </div>
  </div>

  <div class="window">
    <div class="win-bar">
      <div>TERMINAL · ORDER EXECUTION BRIDGE</div>
      <div>MT5 CONNECTED</div>
    </div>
    <div class="term-body">
      <div><span class="cmd">$ claude-quant</span> --symbol XAUUSDc --mode live-execution</div>
      <div class="dim">[08:14:02] Analyzing H1/M15 liquidity sweep &amp; orderflow...</div>
      <div><span class="ok">[EXEC]</span> BUY STOP 0.03 XAUUSDc @ 4163.195 &rarr; <span class="cmd">FILLED</span></div>
      <div><span class="ok">[EXEC]</span> TAKE PROFIT #4556 @ 4163.706 &rarr; <span class="cmd">+100% SYNC</span></div>
      <div><span class="ok">[RISK]</span> Drawdown 0.00% · Equity $1,015.18 · 8-Month Live Verified</div>
    </div>
  </div>
</body>
</html>
"""

html_path = FLOW_DIR / "claude_quant_start.html"
out_png = FLOW_DIR / "claude_quant_start.png"
html_path.write_text(HTML, encoding="utf-8")

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=True,
    )
    page = browser.new_page(viewport={"width": 1080, "height": 1920})
    page.goto(f"file://{html_path}", wait_until="networkidle")
    page.wait_for_timeout(500)
    page.screenshot(path=str(out_png))
    browser.close()

print("Saved:", out_png)
