#!/usr/bin/env python3
"""Kling v3 Pro vs Wan 3.0 bake-off for BLACK LIQUIDITY b-roll.

Submits every job first, then polls — 10 sequential waits would take an hour.
DRY-RUN unless --go. Refuses to start if the fal balance is under the estimate.

Params that are NOT defaults, and why:
  kling generate_audio=False        default True bills $0.168/s instead of $0.112
  wan   audio=False                 b-roll carries no sound
  wan   enable_prompt_expansion=False  default True rewrites the prompt; the two
                                    models must receive the same literal words
  topaz upscale_factor=1.5          720x1280 -> 1080x1920; the default 2 lands
                                    above 1080p and jumps to the $0.08/s tier
"""
import argparse, json, os, re, sys, time, urllib.request, pathlib

ROOT, ENV = pathlib.Path(__file__).parent, "/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env"
OUT, DESKTOP = ROOT / "out", pathlib.Path.home() / "Desktop"
BALANCE_URL, QUEUE = "https://rest.fal.ai/billing/user_balance", "https://queue.fal.run"
KLING = "fal-ai/kling-video/v3/pro/text-to-video"
WAN, TOPAZ, SYNC = "alibaba/wan-3.0/text-to-video", "fal-ai/topaz/upscale/video", "fal-ai/sync-lipsync"
R = {"kling": 0.112, "wan1080": 0.20, "wan720": 0.10, "topaz": 0.02, "sync": 0.70/60}

def key():
    m = re.search(r'^FAL_API_KEY=(.+)$', open(ENV).read(), re.M)
    if not m: sys.exit("FAL_API_KEY missing")
    return m.group(1).strip()

def get(url, k, data=None, timeout=60):
    req = urllib.request.Request(url, method="POST" if data else "GET",
        data=json.dumps(data).encode() if data else None,
        headers={"Authorization": "Key " + k, **({"Content-Type": "application/json"} if data else {})})
    return urllib.request.urlopen(req, timeout=timeout).read()

def kl(p):  return {"prompt": p, "duration": "5", "aspect_ratio": "9:16", "generate_audio": False}
def wan(p, res="1080p"): return {"prompt": p, "duration": 5, "aspect_ratio": "9:16",
                                 "resolution": res, "audio": False, "enable_prompt_expansion": False}

def build(pr):
    j = []
    j.append(("BL-A-Kling",      "A objects/hands/chart · Kling 1080p",  KLING, kl(pr["A"]["prompt"]),  5*R["kling"]))
    j.append(("BL-A-Wan",        "A objects/hands/chart · Wan 1080p",    WAN,   wan(pr["A"]["prompt"]), 5*R["wan1080"]))
    j.append(("BL-A-Wan720up",   "A · Wan 720p (-> Topaz 1.5x)",         WAN,   wan(pr["A"]["prompt"], "720p"), 5*R["wan720"]+5*R["topaz"]))
    for s, nm in (("B", "Phone"), ("C", "Court"), ("D", "Bank")):
        j.append((f"BL-{nm}-Kling", f"{s} {pr[s]['label']} · Kling 1080p", KLING, kl(pr[s]["prompt"]),  5*R["kling"]))
        j.append((f"BL-{nm}-Wan",   f"{s} {pr[s]['label']} · Wan 1080p",   WAN,   wan(pr[s]["prompt"]), 5*R["wan1080"]))
    return j

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--go", action="store_true")
    ap.add_argument("--only", action="append", default=[]); a = ap.parse_args()
    pr = json.load(open(ROOT / "prompts.json"))
    jobs = [x for x in build(pr) if not a.only or x[0] in a.only]
    total = sum(x[4] for x in jobs)
    print(f"\n  {'file':<16} {'what':<46} {'$':>5}")
    for n, w, m, p, e in jobs: print(f"  {n:<16} {w:<46} {e:>5.2f}")
    print(f"  {'':<16} {'TOTAL':<46} {total:>5.2f}")
    k = key(); bal = float(get(BALANCE_URL, k))
    print(f"\n  fal balance ${bal:.2f} -> after ${bal-total:.2f}")
    if bal < total: sys.exit("  BLOCK: balance under estimate (IRON §28)")
    if not a.go: print("\n  DRY RUN — nothing submitted.\n"); return

    OUT.mkdir(exist_ok=True); live = []
    for n, w, m, p, e in jobs:                       # submit everything first
        try:
            rid = json.loads(get(f"{QUEUE}/{m}", k, p))["request_id"]
            print(f"  submit {n:<16} {rid}"); live.append([n, w, m, rid, e])
        except Exception as ex: print(f"  submit {n:<16} ERROR {ex}")
    json.dump([[n,w,m,r,e] for n,w,m,r,e in live], open(OUT/"submitted.json","w"), indent=2)

    done, t0 = [], time.time()
    while live and time.time() - t0 < 2700:
        for row in list(live):
            n, w, m, rid, e = row
            try: st = json.loads(get(f"{QUEUE}/{m}/requests/{rid}/status", k))["status"]
            except Exception: continue
            if st == "COMPLETED":
                d = json.loads(get(f"{QUEUE}/{m}/requests/{rid}", k))
                u = (d.get("video") or {}).get("url") or d.get("video_url") or d.get("url")
                urllib.request.urlretrieve(u, OUT / f"{n}.mp4")
                print(f"  DONE   {n:<16} ({time.time()-t0:.0f}s)")
                done.append({"file": n, "what": w, "model": m, "request_id": rid, "est_usd": round(e,4)})
                live.remove(row)
            elif st == "FAILED":
                print(f"  FAILED {n:<16}"); done.append({"file": n, "what": w, "error": "FAILED"}); live.remove(row)
        json.dump(done, open(OUT/"ledger.json","w"), indent=2, ensure_ascii=False)
        if live: time.sleep(15)

    # T4: upscale the 720p Wan take to 1080x1920
    src = OUT / "BL-A-Wan720up.mp4"
    if src.exists():
        try:
            up = json.loads(get(f"https://fal.run/{TOPAZ}", k,
                 {"video_url": json.loads(get(f"{QUEUE}/{WAN}/requests/"+
                    [r['request_id'] for r in done if r['file']=='BL-A-Wan720up'][0], k)).get("video",{}).get("url"),
                  "upscale_factor": 1.5, "model": "Proteus", "H264_output": True}, timeout=1800))
            urllib.request.urlretrieve((up.get("video") or {}).get("url") or up.get("video_url"), OUT/"BL-A-Wan720up.mp4")
            print("  DONE   BL-A-Wan720up (upscaled)")
        except Exception as ex: print(f"  upscale ERROR {ex}")

    for f in OUT.glob("BL-*.mp4"):
        (DESKTOP / f.name).write_bytes(f.read_bytes())
    print(f"\n  copied to {DESKTOP}\n")

if __name__ == "__main__": main()
