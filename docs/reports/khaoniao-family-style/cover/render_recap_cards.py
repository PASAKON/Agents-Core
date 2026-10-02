"""Recap (Sun 11 Oct) title card + end card + 3 cover candidates. Run on winbox: python render_recap_cards.py [cards|covers rA rB rC]
Same renderer as render_ep5_cards.py / render_ep5_cover.py. The recap badge is «EP.1–5» (card.html/cover.html `badge` + `bs` params, 2026-10-02).
The Sunday end card promises FRIDAY, never «พรุ่งนี้»."""
import subprocess, sys, pathlib, tempfile, shutil
from urllib.parse import quote
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D = pathlib.Path(r"C:\mooniex\khaoniao\cover")
def shot(page, pairs, out):
    q = "&".join(f"{k}={quote(v)}" for k, v in pairs); prof = tempfile.mkdtemp(prefix="rc")
    subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1080,1920", f"--user-data-dir={prof}", "--virtual-time-budget=12000",
                    "--allow-file-access-from-files", f"--screenshot={out}", f"file:///C:/mooniex/khaoniao/cover/{page}?{q}"],
                   timeout=90, capture_output=True)
    shutil.rmtree(prof, ignore_errors=True); print(out.name, out.exists() and out.stat().st_size)
mode = sys.argv[1] if len(sys.argv) > 1 else "cards"
if mode == "cards":
    shot("card.html", [("mode", "title"), ("badge", "EP.1–5"), ("bs", "72"), ("sub", "รวมช็อตเด็ด"), ("l1", "รวมช็อตเด็ด 5 ตอนแรก"), ("l2", "ช็อตไหนที่คุณชอบที่สุด?")], D / "card-title-recap.png")
    shot("card.html", [("mode", "end"), ("l1", "ตอนใหม่ ศุกร์นี้ 19:30")], D / "card-end-recap.png")
else:
    for key in sys.argv[2:]:
        shot("cover.html", [("img", key), ("badge", "EP.1–5"), ("bs", "50"), ("sub", "รวมช็อตเด็ด"), ("l1", "รวมช็อตเด็ด 5 ตอนแรก"), ("l2", "ช็อตไหนที่คุณชอบที่สุด?")], D / f"cover-{key}.png")
