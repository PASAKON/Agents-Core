# -*- coding: utf-8 -*-
"""Upload the two NEW EP2 plates into the EP1 Flow project as Elements (free: upload + rename + add to prompt).
The other six EP2 handles (mimi__dry, mimi__wet, mother__home, brother__wfh, loc__living, loc__dining) are already in
that project from EP1. Run ON winbox:  C:\\mooniex\\pwvenv\\Scripts\\python.exe ep2_upload.py
Ledger C:\\mooniex\\khaoniao\\ep2\\elements.txt keeps each finished name, so a rerun resumes. Pattern: ep1_upload.py."""
import os, re, subprocess, sys
from pathlib import Path
CORE = r"C:\mooniex\Agents\Core"
PLATES = Path(r"C:\mooniex\khaoniao\ep2\plates")
LEDGER = Path(r"C:\mooniex\khaoniao\ep2\elements.txt")
PROJECT = "https://flow.google.com/project/29b3326b-2db3-4233-9897-259924b797c9"
ORDER = ["loc__bathroom", "loc__sofa_low"]
env = dict(os.environ, PYTHONIOENCODING="utf-8")
lines = LEDGER.read_text(encoding="utf-8").splitlines() if LEDGER.exists() else []
done = {l[6:] for l in lines if l.startswith("DONE: ")}
for n in [x for x in ORDER if x not in done]:
    cmd = [sys.executable, "tools/flow_upload_element.py", "--file", str(PLATES / f"{n}.png"), "--name", n,
           "--project-url", PROJECT]
    r = subprocess.run(cmd, cwd=CORE, env=env, capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout + r.stderr).strip().splitlines()
    if r.returncode != 0:
        print(f"FAIL {n} rc={r.returncode}"); print("\n".join(out[-8:])); sys.exit(1)
    with LEDGER.open("a", encoding="utf-8") as f: f.write(f"DONE: {n}\n")
    print(f"ok {n} | {out[-1][:100] if out else ''}")
print("done:", len(done) + len([x for x in ORDER if x not in done]), "/", len(ORDER))
