"""Render card.html modes to PNG on winbox (transparent for 'morning').  python render_cards.py morning title end
Needs C:\\mooniex\\khaoniao\\cover\\card.html and logo-3-mark.png (copied by the caller)."""
import subprocess, sys, pathlib, tempfile, shutil
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D = pathlib.Path(r"C:\mooniex\khaoniao\cover")
for mode in (sys.argv[1:] or ["morning", "title", "end"]):
    out = D / f"card-{mode}.png"; prof = tempfile.mkdtemp(prefix="cd")
    url = f"file:///C:/mooniex/khaoniao/cover/card.html?mode={mode}"
    subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1080,1920", f"--user-data-dir={prof}", "--virtual-time-budget=12000",
                    "--default-background-color=00000000", "--allow-file-access-from-files", f"--screenshot={out}", url],
                   timeout=90, capture_output=True)
    shutil.rmtree(prof, ignore_errors=True); print(mode, out.exists() and out.stat().st_size)
