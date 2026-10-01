"""Render cover.html to PNG with headless Chrome on winbox (real Thai fonts).  python render.py A B C
Inputs expected in C:\\mooniex\\khaoniao\\cover\\ : A.png B.png C.png (1080x1920 frames) + logo-3-mark.png + cover.html"""
import subprocess, sys, pathlib, tempfile, shutil
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D = pathlib.Path(r"C:\mooniex\khaoniao\cover")
for key in (sys.argv[1:] or ["A", "B", "C"]):
    extra = ""
    if "=" in key:                      # e.g. A&top=1000
        key, extra = key.split("&", 1)[0], "&" + key.split("&", 1)[1]
    out = D / f"cover-{key}.png"
    prof = tempfile.mkdtemp(prefix="cv")
    url = f"file:///C:/mooniex/khaoniao/cover/cover.html?img={key}{extra}"
    subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1080,1920", f"--user-data-dir={prof}", "--virtual-time-budget=12000",
                    "--allow-file-access-from-files", f"--screenshot={out}", url], timeout=90, capture_output=True)
    shutil.rmtree(prof, ignore_errors=True)
    print(key, out.exists() and out.stat().st_size)
