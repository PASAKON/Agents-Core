"""EP2 title card (mode=title, ep=2). Run on winbox: python render_ep2_title.py  -> C:\\mooniex\\khaoniao\\cover\\card-title-ep2.png
Same renderer as render_cards.py (Chrome headless, real Itim); the query carries the episode's own words."""
import subprocess, pathlib, tempfile, shutil
from urllib.parse import quote
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D = pathlib.Path(r"C:\mooniex\khaoniao\cover")
q = "&".join(f"{k}={quote(v)}" for k, v in [("ep", "2"), ("sub", "วันอาบน้ำ"), ("l1", "ทำไมมีมี่หายตัว"), ("l2", "ทั้งบ้านเลย?")])
out = D / "card-title-ep2.png"; prof = tempfile.mkdtemp(prefix="cd")
subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                "--window-size=1080,1920", f"--user-data-dir={prof}", "--virtual-time-budget=12000",
                "--allow-file-access-from-files", f"--screenshot={out}", f"file:///C:/mooniex/khaoniao/cover/card.html?mode=title&{q}"],
               timeout=90, capture_output=True)
shutil.rmtree(prof, ignore_errors=True); print("title-ep2", out.exists() and out.stat().st_size)
