"""EP3 cover candidates. Run on winbox: python render_ep3_cover.py e3A e3B e3C  -> C:\\mooniex\\khaoniao\\cover\\cover-<key>.png
Same renderer as render.py (cover.html + Chrome headless, real Itim); the picture is a real frame cut from the episode
(C:\\mooniex\\khaoniao\\cover\\<key>.png, 1080x1920); the query carries the episode's own words (ep=3)."""
import subprocess, sys, pathlib, tempfile, shutil
from urllib.parse import quote
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D = pathlib.Path(r"C:\mooniex\khaoniao\cover")
for key in sys.argv[1:]:
    q = "&".join(f"{k}={quote(v)}" for k, v in [("img", key), ("ep", "3"), ("sub", "หลังอาบน้ำ"), ("l1", "ทำไมมีมี่ไม่สะบัดตัว"), ("l2", "แต่กลิ้งทับผ้าแทน?")])
    out = D / f"cover-{key}.png"; prof = tempfile.mkdtemp(prefix="cv")
    subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1080,1920", f"--user-data-dir={prof}", "--virtual-time-budget=12000",
                    "--allow-file-access-from-files", f"--screenshot={out}", f"file:///C:/mooniex/khaoniao/cover/cover.html?{q}"],
                   timeout=90, capture_output=True)
    shutil.rmtree(prof, ignore_errors=True); print(key, out.exists() and out.stat().st_size)
