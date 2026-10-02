"""EP4 title card + end card. Run on winbox: python render_ep4_cards.py  -> C:\\mooniex\\khaoniao\\cover\\card-title-ep4.png, card-end-ep4.png
Same renderer as render_cards.py / render_ep2_title.py (Chrome headless, real Itim). The end card promises TOMORROW (EP5 is Saturday)."""
import subprocess, pathlib, tempfile, shutil
from urllib.parse import quote
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D = pathlib.Path(r"C:\mooniex\khaoniao\cover")
JOBS = {
    "title-ep4": [("mode", "title"), ("ep", "4"), ("sub", "ประชุมซูม"), ("l1", "ทำไมมีมี่ลากพี่ชายออกไปเดิน"), ("l2", "ทุกครั้งที่เขาประชุมซูมไม่หยุด?")],
    "end-ep4": [("mode", "end"), ("l1", "ตอนใหม่ พรุ่งนี้ 19:30")],
}
for name, pairs in JOBS.items():
    q = "&".join(f"{k}={quote(v)}" for k, v in pairs)
    out = D / f"card-{name}.png"; prof = tempfile.mkdtemp(prefix="cd")
    subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1080,1920", f"--user-data-dir={prof}", "--virtual-time-budget=12000",
                    "--allow-file-access-from-files", f"--screenshot={out}", f"file:///C:/mooniex/khaoniao/cover/card.html?{q}"],
                   timeout=90, capture_output=True)
    shutil.rmtree(prof, ignore_errors=True); print(name, out.exists() and out.stat().st_size)
