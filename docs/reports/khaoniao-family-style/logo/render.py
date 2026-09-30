import subprocess, sys, pathlib, tempfile, shutil
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D = pathlib.Path(r"C:\mooniex\khaoniao\logo")
SIZE = {"cover": (1672, 941), "profile": (1254, 1254), "mark": (1600, 520)}
only = sys.argv[1:]  # e.g. 1-cover
for s in "123":
    for m, (w, h) in SIZE.items():
        tag = f"{s}-{m}"
        if only and tag not in only:
            continue
        out = D / f"logo-{tag}.png"
        prof = tempfile.mkdtemp(prefix="lg")
        url = f"file:///C:/mooniex/khaoniao/logo/logo.html?style={s}&mode={m}"
        cmd = [CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
               f"--window-size={w},{h}", f"--user-data-dir={prof}", "--virtual-time-budget=12000",
               "--default-background-color=00000000", "--allow-file-access-from-files",
               f"--screenshot={out}", url]
        try:
            subprocess.run(cmd, timeout=90, capture_output=True)
        except subprocess.TimeoutExpired:
            print("timeout", tag)
        shutil.rmtree(prof, ignore_errors=True)
        print(tag, out.exists() and out.stat().st_size)
