"""Week-1 weekday posters. Run ON WINBOX:  python render_posters.py [key ...]  -> C:\\mooniex\\khaoniao\\poster\\out\\poster-<key>.png
Same renderer as ../cover/render.py (poster.html + Chrome headless, real Itim, fresh --user-data-dir, 1080x1350).
The picture is a real frame cut from an episode (frames\\<img>.png, 720x1280); the text below IS the post's lettering —
edit it here and re-render, never retouch a PNG. Facts in the text must be true on the day it is posted:
tue (aired) is true only after EP3 is live; tue_prep is the fallback if EP3 is late. See docs/plans/mimi-week1-posts.md."""
import subprocess, sys, pathlib, tempfile, shutil
from urllib.parse import quote
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D = pathlib.Path(r"C:\mooniex\khaoniao\poster"); OUT = D / "out"; OUT.mkdir(exist_ok=True)
P = {
 # Monday 5 Oct: the week opens — the rhythm, in the page's voice
 "mon": dict(img="mon", oy="250", bB="จ.", bS="5 ต.ค.", l1="ตอนใหม่ของมีมี่", l2="ศุกร์ · เสาร์ · อาทิตย์",
             c1="19:30 น. ทุกสัปดาห์", c2="จันทร์–พฤหัส มีโพสต์ใหม่ทุกวัน 19:30"),
 # Tuesday 6 Oct: work update. 'aired' = true once EP3 is live (Sun 4 Oct 19:30); 'prep' = fallback if EP3 is late
 "tue": dict(img="tue", oy="340", bB="EP.3", bS="เบื้องหลัง", l1="มีมี่ตัวสั่นตอนอาบน้ำ", l2="แล้วกลิ้งทับผ้าให้แห้ง",
             c1="เรื่องจริงจากบ้านเรา เล่าเป็นตอนที่ 3", c2="18 ช็อต ต่อกันเป็น 3 นาที"),
 "tue_prep": dict(img="tue", oy="340", bB="EP.3", bS="กำลังเตรียม", l1="มีมี่ตัวสั่นตอนอาบน้ำ", l2="แล้วกลิ้งทับผ้าให้แห้ง",
             c1="เรื่องจริงจากบ้านเรา บทพร้อมแล้ว", c2="18 ช็อต · กำลังเตรียมถ่าย"),
 # Wednesday 7 Oct: one concrete question to the fans
 "wed": dict(img="wed", oy="250", bB="?", bS="ถามหน่อย", l1="หมาของคุณ", l2="ทำอะไรหลังอาบน้ำ?",
             c1="มีมี่ตัวสั่นแล้วกลิ้งทับผ้า", c2="บ้านคุณล่ะ เล่าให้มีมี่ฟังหน่อย"),
 # Thursday 8 Oct teaser: a real still of EP4 (shot 15 @6 s) in frames\\thu.png + one line spoken in EP4 shot 10 («อยากได้คืน ต้องลุกมาเอาเอง», heard in the transcript).
 # Rendered 2026-10-02 after EP4 existed; the thu_tpl stand-in is retired.
 "thu": dict(img="thu", oy="250", bB="EP.4", bS="ศุกร์นี้", q="อยากได้คืน ต้องลุกมาเอาเอง",
             l1="พรุ่งนี้", l2="19:30 ตอนใหม่", c1="บ้านนี้มีมีมี่", c2=""),
}
keys = sys.argv[1:] or list(P)
for key in keys:
    q = "&".join(f"{k}={quote(v)}" for k, v in P[key].items())
    out = OUT / f"poster-{key}.png"; prof = tempfile.mkdtemp(prefix="pt")
    subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1080,1350", f"--user-data-dir={prof}", "--virtual-time-budget=12000",
                    "--allow-file-access-from-files", f"--screenshot={out}", f"file:///C:/mooniex/khaoniao/poster/poster.html?{q}"],
                   timeout=90, capture_output=True)
    shutil.rmtree(prof, ignore_errors=True); print(key, out.exists() and out.stat().st_size)
