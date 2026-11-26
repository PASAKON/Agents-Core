#!/usr/bin/env python3
"""GhostRules EP3 paper renderer (adapted from EP1 paper/render.py: plate + camera + lamp flicker + dust / rain + grain).
usage: render_ep3.py plan            -> writes shots.json (frame-exact windows) and prints the table
       render_ep3.py render [ids...] -> renders chunks (WORKERS env, default 2) under nice
Inputs: OUT/timeline.json + OUT/cue_ledger.json from build_mix.py (new timeline incl. the jump-scare hole)."""
import os, sys, json, math, subprocess
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np, cv2
cv2.setNumThreads(1)
sys.path.insert(0, "/opt/MoonieXHQ/Work/task-f143f9cf/in")
from aud import rd
G = "/opt/MoonieXHQ/Work/ghostrules-full/ep03"
WK = "/opt/MoonieXHQ/Work/task-f143f9cf"; OUT = f"{WK}/out"; CH = os.environ.get("CHUNKS", f"{OUT}/chunks")
IMG = f"{G}/paper/img"; TAKES = "/opt/MoonieXHQ/Work/task-af2d7f8f/in/takes"
W, H, FPS = 1920, 1080, 30
FLASHBACK = {"S02", "S03", "S19"}
RAIN_PLATES = {"P006", "P007", "P008"}      # outdoors in the rain (S02-01..03); audio rain = same window
LIGHTNING_PLATES = {"P070"}                 # S18-02 "Lightning through balcony curtain" (no thunder authorised)
CARD_TXT = {"CARD-1": ("I", (0.49, 0.47)), "CARD-2": ("II", (0.53, 0.44)), "CARD-3": ("III", (0.50, 0.46)),
            "CARD-4": ("IV", (0.45, 0.46)), "CARD-5": ("V", (0.50, 0.47)), "CARD-6": ("GHOST RULES", (0.50, 0.50))}

def plan_shots():
    plan = json.load(open(f"{G}/plan/PLAN.json")); tl = json.load(open(f"{OUT}/timeline.json")); led = json.load(open(f"{OUT}/cue_ledger.json"))
    js = led["jump_scare"]; STING = js["sting_time_s"]; hole = (js["narration_hole"]["from_s"], js["narration_hole"]["to_s"])
    takes = {t["take"]: t for t in tl["takes"]}
    c06 = takes["c06"]; shift = js["timeline_shift_after_hole_s"]
    def pauses(take):
        x = rd(f"{TAKES}/{take}.wav", sr=24000); w = 480; n = len(x) // w
        e = np.array([np.sqrt((x[i * w:(i + 1) * w] ** 2).mean()) for i in range(n)]) < 0.012
        out = []; i = 0
        while i < n:
            if e[i]:
                j = i
                while j < n and e[j]: j += 1
                if (j - i) * 0.02 >= 0.2 and i > 5 and j < n - 5: out.append((i + j) / 2 * 0.02)
                i = j
            else: i += 1
        t0 = takes[take]["start"]
        res = []
        for p in out:
            if take == "c06":
                if p <= 12.85: res.append(t0 + p)
                elif p >= 13.45: res.append(t0 + 12.85 + (hole[1] - (t0 + 12.85)) + (p - 13.45))
            else: res.append(t0 + p)
        return res
    shots = []
    for c in tl["cards"]:
        pid = {0: "CARD-1"}.get(0)  # placeholder
    order = [c for c in plan["cards"]]
    # cards in timeline order map 1:1 to plan cards
    for c, pc in zip(tl["cards"], plan["cards"]):
        shots.append(dict(id=pc["plate_id"], plate=pc["plate_id"], t0=c["start"], t1=c["end"], kind="card", scene=None))
    for s in plan["scenes"]:
        t = takes[s["take"]]; W0, W1 = t["start"], t["next_boundary"]
        sh = s["shots"]; d = [x["end"] - x["start"] for x in sh]; D = sum(d)
        ps = pauses(s["take"]); cum = 0; bounds = []
        for k in range(len(sh) - 1):
            cum += d[k]; tgt = W0 + (W1 - W0) * cum / D
            bounds.append(tgt)
        # snap to nearest voice pause within +-2 s
        snapped = []
        for k, b in enumerate(bounds):
            if s["id"] == "S06" and k == 1: snapped.append(STING); continue
            cand = [p for p in ps if abs(p - b) <= 2.0 and (not snapped or p > snapped[-1] + 2.0) and not (hole[0] < p < hole[1])]
            if s["id"] == "S06" and k == 2: cand = [p for p in cand if p > STING + 2.0]
            snapped.append(min(cand, key=lambda p: abs(p - b)) if cand else b)
        for k in range(1, len(snapped)):          # keep order and >= 1.6 s
            if snapped[k] < snapped[k - 1] + 1.6: snapped[k] = snapped[k - 1] + 1.6 if s["id"] != "S06" or k != 1 else snapped[k]
        edges = [W0] + snapped + [W1]
        for k, x in enumerate(sh):
            shots.append(dict(id=x["id"], plate=x["plate_id"], t0=edges[k], t1=edges[k + 1], kind="shot", scene=s["id"], beat=x["beat"],
                              flashback=s["id"] in FLASHBACK))
    shots.sort(key=lambda r: r["t0"])
    # frame-exact, no drift, gap-free
    for i, r in enumerate(shots):
        r["f0"] = int(round(r["t0"] * FPS)); r["f1"] = int(round(shots[i + 1]["t0"] * FPS)) if i + 1 < len(shots) else int(round(tl["duration"] * FPS))
    shots[0]["f0"] = 0
    return shots

# ------------------------------------------------------------------ rendering
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); VIG = (1 - 0.30 * ((xx - W / 2) ** 2 / (W / 2) ** 2 + (yy - H / 2) ** 2 / (H / 2) ** 2))[..., None]
COOL = np.float32([[1.00, 0.02, 0.00], [0.00, 1.00, 0.02], [0.00, 0.00, 1.00]])
def grade_plate(img, flash):
    f = img.astype(np.float32)                      # BGR
    if flash:                                       # sepia flashback: clearly different from the cool present
        g = f.mean(2, keepdims=True); f = 0.30 * f + 0.70 * g                  # desaturate
        f = f * np.float32([0.78, 0.92, 1.12]) + np.float32([-6, 4, 14])       # BGR sepia push
        f = (f - 128) * 0.92 + 134                                              # faded blacks
    else:                                           # present: cool paper night
        f = f * np.float32([1.05, 1.00, 0.95])
    return np.clip(f * VIG, 0, 255).astype(np.uint8)

def load_plate(pid, flash):
    a = cv2.imread(f"{IMG}/{pid}.png"); a = cv2.resize(a, (W, H), interpolation=cv2.INTER_CUBIC)
    glow_src = a.astype(np.float32); lum = glow_src.mean(2)
    warm = (glow_src[..., 2] > 200) & (glow_src[..., 1] > 120) & (glow_src[..., 0] < 170) & (lum > 170)   # EP1 lamp detector
    bulbs = cv2.GaussianBlur(warm.astype(np.float32), (0, 0), 16)
    glow = np.clip(bulbs[..., None] * np.float32([110, 190, 255]) * 0.5, 0, 255).astype(np.uint8)
    return grade_plate(a, flash), glow, float(bulbs.max())

def card_frame(pid, base, t, dur):
    from PIL import Image, ImageDraw, ImageFont
    txt, (cx, cy) = CARD_TXT[pid]
    a = min(1.0, max(0.0, (t - 0.25) / 0.9)); a = a * a * (3 - 2 * a)          # ink reveal
    sc = 1.18 - 0.18 * a; fr = base.copy()
    if a <= 0: return fr
    big = pid != "CARD-6"; size = int((300 if len(txt) < 3 else 250 if big else 120) * sc)
    f = ImageFont.truetype("/opt/MoonieXHQ/Work/ghostrules-full/channel-kit/fonts/Prompt-Bold.ttf", size)
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); bb = d.textbbox((0, 0), txt, font=f)
    d.text((cx * W - (bb[2] + bb[0]) / 2, cy * H - (bb[3] + bb[1]) / 2), txt, font=f, fill=int(255 * a))
    m = (np.asarray(im).astype(np.float32) / 255)[..., None]
    ink = np.float32([30, 40, 70]) if big else np.float32([205, 225, 240])      # BGR: dark ink on paper, pale on dark panel
    return np.clip(fr.astype(np.float32) * (1 - m * 0.92) + ink * m * 0.92, 0, 255).astype(np.uint8)

def render_shot(args):
    r, idx = args; n = min(r["f1"] - r["f0"], int(os.environ.get("TESTN", "100000"))); out = f"{CH}/{r['id']}.mp4"; os.makedirs(CH, exist_ok=True)
    flash = r.get("flashback", False); pid = r["plate"]
    if r["kind"] == "card": base = cv2.resize(cv2.imread(f"{IMG}/{pid}.png"), (W, H), interpolation=cv2.INTER_CUBIC); glow = None; bmax = 0
    else: base, glow, bmax = load_plate(pid, flash)
    ff = subprocess.Popen(["nice", "-n", "10", "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-threads", "2", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(idx + 11); dur = n / FPS
    gs = np.random.default_rng(7); amp = 6 if not flash else 9
    GR = [(gs.random((H, W, 1), dtype=np.float32) - 0.5) * 2 * amp for _ in range(6)]
    GP = [np.clip(g, 0, None).astype(np.uint8).repeat(3, 2) for g in GR]; GN = [np.clip(-g, 0, None).astype(np.uint8).repeat(3, 2) for g in GR]
    rain = pid in RAIN_PLATES; sting = r["id"] == "S06-03"
    rains = [(rng.random((nn, 2)) * [W + 300, H], ln, sp, al, th) for nn, ln, sp, al, th in [(240, 26, 900, 0.20, 1), (80, 60, 1700, 0.33, 2)]] if rain else []
    dust = [(rng.random((nn, 3)) * [W, H, 6.28], sz, sp, al) for nn, sz, sp, al in [(70, 1, 14, 0.35), (22, 2, 30, 0.5)]]
    push_in = idx % 2 == 0; strong = r["id"] == "S06-02"
    lt = rng.uniform(0.3, 0.6) * dur if pid in LIGHTNING_PLATES else None
    for i in range(n):
        t = i / FPS
        if r["kind"] == "card":
            fr = card_frame(pid, base, t, dur)
            k = 1.0 + 0.015 * (t / max(dur, 1e-3)); C = cv2.getRotationMatrix2D((W / 2, H / 2), 0, k)
            fr = cv2.warpAffine(fr, C, (W, H), borderMode=cv2.BORDER_REFLECT)
        else:
            p = t / max(dur, 1e-3); e = 0.5 - 0.5 * math.cos(math.pi * p)
            span = 0.11 if strong else 0.05
            cam = 1.0 + span * (e if (push_in or strong) else 1 - e)
            if sting: cam = 1.0 + 0.02 * p + 0.14 * math.exp(-i / 2.2)        # the hit: punch-in settles in ~8 frames
            C = cv2.getRotationMatrix2D((W / 2, H / 2), 0, cam)
            if sting and i < 4: C[0, 2] += (6 if i % 2 else -6); C[1, 2] += (4 if i % 2 else -4)
            fr = cv2.warpAffine(base, C, (W, H), borderMode=cv2.BORDER_REFLECT)
            if glow is not None and bmax > 0.05:
                fl = 0.55 + 0.35 * math.sin(t * 9.0) * (rng.random() < 0.5) + (0.9 if rng.random() < 0.04 else 0)
                fr = cv2.addWeighted(fr, 1.0, cv2.warpAffine(glow, C, (W, H)), fl, 0)
            if sting and i < 5: fr = cv2.addWeighted(fr, 1.0, np.full_like(fr, 255), 0.30 * (1 - i / 5), 0)
            if lt is not None and t >= lt:
                kk = math.exp(-(t - lt) * 3.0); fr = np.clip(fr.astype(np.float32) * (1 + 0.45 * kk * np.float32([0.45, 0.45, 1])), 0, 255).astype(np.uint8)
                if t - lt < 0.07 or 0.14 < t - lt < 0.19: fr = cv2.addWeighted(fr, 0.5, np.full_like(fr, 235), 0.5, 0)
            if rain:
                rl = np.zeros((H, W), np.float32)
                for pts, ln, sp, al, th in rains:
                    y = (pts[:, 1] + sp * t) % H; x = (pts[:, 0] - 0.18 * sp * t) % (W + 300) - 150
                    for xi, yi in zip(x.astype(int), y.astype(int)): cv2.line(rl, (xi, yi), (xi - int(ln * 0.18), yi + ln), al, th)
                rl8 = (rl * 255).astype(np.uint8); fr = cv2.addWeighted(fr, 1.0, cv2.merge([rl8, rl8, rl8]), 0.85, 0)
            else:
                for pts, sz, sp, al in dust:       # dust motes: indoor / dry plates
                    x = (pts[:, 0] + sp * t * 0.6 + 12 * np.sin(t * 0.5 + pts[:, 2])) % W; y = (pts[:, 1] - sp * t * 0.25 + 8 * np.sin(t * 0.7 + pts[:, 2] * 2)) % H
                    tw = al * (0.55 + 0.45 * np.sin(t * 2.0 + pts[:, 2] * 5))
                    for xi, yi, a_ in zip(x.astype(int), y.astype(int), tw):
                        x0, y0 = max(xi - sz, 0), max(yi - sz, 0); roi = fr[y0:yi + sz + 1, x0:xi + sz + 1]
                        if roi.size: roi[:] = (roi * (1 - a_) + np.float32([170, 215, 255]) * a_).astype(np.uint8)
        fr = cv2.subtract(cv2.add(fr, GP[i % 6]), GN[i % 6])
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait(); return r["id"], n, ff.returncode

if __name__ == "__main__":
    shots = plan_shots()
    if sys.argv[1] == "plan":
        json.dump(shots, open(f"{OUT}/shots.json", "w"), indent=1, ensure_ascii=False)
        for r in shots: print(r["id"], r["plate"], "%.3f-%.3f" % (r["t0"], r["t1"]), r["f0"], r["f1"], "%.1fs" % ((r["f1"] - r["f0"]) / FPS), r.get("beat", ""))
        print(len(shots), "shots, frames", shots[-1]["f1"])
    else:
        from multiprocessing import Pool
        want = sys.argv[2:] or [r["id"] for r in shots]
        jobs = [(r, i) for i, r in enumerate(shots) if r["id"] in want]
        with Pool(int(os.environ.get("WORKERS", "2"))) as P:
            for x in P.imap_unordered(render_shot, jobs): print(*x, flush=True)
