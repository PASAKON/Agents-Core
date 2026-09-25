"""Fire the P1 main scenes on the MiniMax H3 studio (Mac, over the tailnet) and bring the clips home.

API (MAC CTO 6bfdc084, docs/ops/letters/2026-09-25-cto-6bfdc084-to-cto-e1e3d3ef-h3-render-api.md):
POST /api/shots/render {name, prompt, duration_s (4-15), resolution, aspect} -> {job_id, refs, tags, position};
409 = no pod running (nothing queued); 400 = bad input / unknown @handle / over the 9-image cap.
GET /api/shots/render?id=<job_id> -> {status: pending|running|done|error|skipped, error?, files, download_url}
(download_url is RELATIVE to BASE). Live since ComfyRunpod da6116c; docs in the ...-render-api-ready.md letter.

Rules this script enforces:
- 360p ONLY (CEO 2026-09-25: "ให้ยิงที่ 360p เท่านั้นนะ"); the resolution is not a flag.
- Enqueue ALL shots back to back: the studio stops the pod the moment its queue is empty, so firing one at
  a time would close the pod after the first clip (MAC CTO, measured in queueRunner.ts).
- --cancel deletes only my own pending items (ledger id + ILAG- name + pending), one at a time, count-checked.
- Plain enqueue never starts or stops a pod: a 409 stops the run. Only --run-all touches /api/pod/*, and only
  because the CEO ordered it (2026-09-25 "ยิงได้" twice with the pod off; "ยิงเสร็จอย่าลืมปิด pod"):
  POST /api/pod/start, watch GET /api/pod/status, queue the moment it is ready (an idle ready pod may be
  stopped by the queue runner), collect, then make sure the pod is off. COST CAP: pod costSoFar > $3 = stop it.
- The prompt is ONLY the text between the PASTE markers of each m*.txt.

    python3 h3_fire.py [--only m01,m03] [--dry-run]          # enqueue
    python3 h3_fire.py --collect                               # poll, download, file to Drive Previz/
"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path

BASE = "http://100.64.2.37:4100"
HERE = Path(__file__).parent
LEDGER = HERE / "h3-fire-ledger.json"
RESOLUTION = "360p"
START = "=== ↓↓↓ PASTE FROM HERE ↓↓↓"
STOP = "=== ↑↑↑ PASTE STOPS HERE ↑↑↑"


def paste_block(text: str) -> str:
    a = text.index(START)
    a = text.index("\n", a) + 1
    return text[a:text.index(STOP)].strip()


def curl(*args):
    r = subprocess.run(["curl", "-s", "-m", "120", "-w", "\n%{http_code}", *args], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    return int(code or 0), body


def load():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}


def save(led):
    LEDGER.write_text(json.dumps(led, indent=1, ensure_ascii=False))


def shots(only, series="m"):
    out = []
    for p in sorted(HERE.glob(f"{series}[0-9][0-9]-*.txt")):
        key = p.name[:3]
        if only and key not in only:
            continue
        text = p.read_text(encoding="utf-8")
        prompt = paste_block(text)
        secs = int(re.match(r"(\d+)s · ", prompt).group(1))
        out.append({"key": key, "name": f"ILAG-{key.upper()}-{p.stem[4:]}", "prompt": prompt, "duration_s": secs})
    return out


def enqueue(a):
    led = load()
    if a.retake:  # keep the old take's row under <key>_t<N>, then queue the key again
        for s0 in shots(a.only, a.series):
            k = s0["key"]
            if k in led:
                n = 1 + sum(1 for x in led if x.startswith(k + "_t"))
                led[f"{k}_t{n}"] = led.pop(k)
        if not a.dry_run:
            save(led)
    todo = [s for s in shots(a.only, a.series) if s["key"] not in led]
    for s in todo:
        handles = re.findall(r"@\w+", s["prompt"])
        print(f"{s['key']} {s['duration_s']}s {RESOLUTION} {len(s['prompt'].split())} words refs={handles}")
    if a.dry_run or not todo:
        return
    for s in todo:  # back to back, no waiting between them
        body = {"name": s["name"], "prompt": s["prompt"], "duration_s": s["duration_s"],
                "resolution": RESOLUTION, "aspect": "16:9"}
        code, resp = curl("-H", "Content-Type: application/json", "-d", json.dumps(body), f"{BASE}/api/shots/render")
        if code == 409:
            raise SystemExit(f"409 at {s['key']}: no pod ready. Nothing more fired; ask the CEO to open the pod.")
        if code != 200:
            # a 400 is this shot's own input (unknown @handle, cap, seconds): log it and keep queuing the rest,
            # or the pod would render a partial batch and switch itself off
            print(f"REJECTED {s['key']} ({code}): {resp[:300]}")
            continue
        j = json.loads(resp)
        led[s["key"]] = {"job_id": j["job_id"], "name": s["name"], "queued": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                         "position": j.get("position"), "refs": j.get("refs"), "status": "queued"}
        save(led)
        print(f"queued {s['key']} job {j['job_id']} position {j.get('position')} refs {j.get('refs')}")


def cancel(a):
    """Delete MY OWN pending queue items, one at a time (CEO 2026-09-25: "จัดการ Queue ได้เลย เพราะงานเป็นของคุณทั้งหมด
    ... อย่าลบของคนอื่น"). An item is deleted only if its id is in this ledger, its name starts with ILAG-, and it is
    still pending; after each DELETE the queue must shrink by exactly that one id, otherwise stop."""
    led = load()
    mine = {r["job_id"]: k for k, r in led.items() if r.get("job_id")}
    wanted = {r["job_id"] for k, r in led.items() if r.get("job_id") and k.split("_t")[0] in (a.only or set())}

    def items():
        return json.loads(curl(f"{BASE}/api/queue")[1])["items"]

    for jid in sorted(wanted):
        before = items()
        it = next((i for i in before if i["id"] == jid), None)
        if it is None:
            continue
        if jid not in mine or not it["name"].startswith("ILAG-") or it["status"] != "pending":
            raise SystemExit(f"STOP: {jid} is not a pending item of mine ({it['name']}, {it['status']})")
        if a.dry_run:
            print(f"would delete {jid} {it['name']}")
            continue
        curl("-o", "/dev/null", "-X", "DELETE", f"{BASE}/api/queue?id={jid}")
        gone = {i["id"] for i in before} - {i["id"] for i in items()}
        if gone != {jid}:
            raise SystemExit(f"STOP: deleting {jid} removed {gone}")
        print(f"deleted {jid} {it['name']}")


def collect(a):
    sys.path.insert(0, str(HERE.parents[2] / "scripts/gdrive-bridge"))
    import ilag_rest as d
    previz = d.child("1fdS2YrDWrEF_trd4YzgoyxOBsH3e2oon", "Previz")["id"]
    led = load()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for key, row in sorted(led.items()):
        if "_t" in key or row.get("status") == "filed":
            continue
        code, resp = curl(f"{BASE}/api/shots/render?id={row['job_id']}")
        j = json.loads(resp) if code == 200 else {}
        row["status"] = j.get("status", f"http {code}")
        if j.get("error"):
            row["error"] = j["error"]
        if row["status"] == "done" and j.get("download_url"):
            tagk = f"{key[0].upper()}{int(key[1:])}"
            take = 1 + sum(1 for f in d.ls(previz) if f["name"].startswith(f"{tagk}-H3-take"))
            name = f"{tagk}-H3-take{take}.mp4"
            dst = out / name
            url = j["download_url"]
            url = BASE + url if url.startswith("/") else url
            subprocess.run(["curl", "-s", "-f", "-m", "600", "-o", str(dst), url], check=True)
            info, made = d.upload(dst, name, previz)
            if made:
                d.append_log("1asL3Woa5f1Lz3qhdHHTRrB-krpSRXDBY", [d.line(
                    "ADD", "FILE", name, d.link(info["id"]), "Previz", len(d.ls(previz)),
                    f"MiniMax H3 360p previz of {row['name']}, job {row['job_id']}, md5 {info['md5Checksum']}")])
            row.update(status="filed", file=name, drive_id=info["id"], local=str(dst))
        print(f"{key} {row['status']} {row.get('file', '')} {row.get('error', '')}")
        save(led)


def wait(a):
    while True:
        collect(a)
        left = [k for k, r in load().items() if "_t" not in k and r.get("status") not in ("filed", "error", "skipped")]
        if not left:
            print("ALL FINISHED")
            return
        print(f"waiting on {left}")
        time.sleep(45)


COST_CAP_USD = 3.0


def pod_status():
    code, body = curl(f"{BASE}/api/pod/status")
    return json.loads(body) if code == 200 else {"state": f"http {code}"}


def pod_stop(reason):
    code, body = curl("-X", "POST", f"{BASE}/api/pod/stop")
    print(f"{time.strftime('%H:%M:%S')} POD STOP ({reason}): {code} {body[:200]}")


def run_all(a):
    st = pod_status()
    print(f"{time.strftime('%H:%M:%S')} before: {st}")
    if a.start_pod and st.get("state") in (None, "off"):
        code, body = curl("-X", "POST", f"{BASE}/api/pod/start")
        print(f"{time.strftime('%H:%M:%S')} POD START: {code} {body[:300]}")
        if code not in (200, 201, 202):
            raise SystemExit("the studio refused to start the pod; nothing queued")
    last, t0 = None, time.time()
    # The pod is shared: costSoFar counts every user's renders since the pod started, so the cap is on what the
    # cost grows by while this run waits (measured 2026-09-25: $3.44 on the meter from other people's work).
    base = st.get("costSoFar") or 0
    while True:
        st = pod_status()
        view = (st.get("state"), st.get("stockStatus"), st.get("gpu"))
        if view != last:
            print(f"{time.strftime('%H:%M:%S')} pod {view} cost ${st.get('costSoFar')}")
            last = view
        if (st.get("costSoFar") or 0) - base > COST_CAP_USD:
            pod_stop(f"cost cap ${COST_CAP_USD} passed during boot"); return
        if st.get("state") == "ready":
            break
        if a.start_pod and st.get("state") in ("off", "error", "failed") and time.time() - t0 > 60:
            raise SystemExit(f"pod did not come up: {st}")
        if a.start_pod and time.time() - t0 > 25 * 60:
            pod_stop("not ready after 25 min"); return
        if not a.start_pod and time.time() - t0 > a.max_wait_min * 60:
            raise SystemExit(f"no pod after {a.max_wait_min} min; nothing queued")
        time.sleep(5)
    enqueue(a)
    while True:
        collect(a)
        st = pod_status()
        left = [k for k, r in load().items() if "_t" not in k and r.get("status") not in ("filed", "error", "skipped")]
        print(f"{time.strftime('%H:%M:%S')} pod {st.get('state')} cost ${st.get('costSoFar')} waiting on {left}")
        if (st.get("costSoFar") or 0) - base > COST_CAP_USD:
            if others_waiting():
                print(f"{time.strftime('%H:%M:%S')} cost cap passed but other people's renders are queued: NOT "
                      "stopping their pod"); collect(a); return
            pod_stop(f"cost cap ${COST_CAP_USD} passed"); collect(a); return
        if not left:
            break
        time.sleep(30)
    for _ in range(20):  # the queue runner should switch the pod off by itself; confirm, else stop it
        st = pod_status()
        if st.get("state") == "off":
            print(f"{time.strftime('%H:%M:%S')} ALL FINISHED, pod is OFF by itself, cost ${st.get('costSoFar')}")
            return
        n = others_waiting()
        if n:
            print(f"{time.strftime('%H:%M:%S')} ALL FINISHED (mine); the pod is serving {n} other queued render(s), "
                  f"left on, it stops itself when the queue is empty; cost ${st.get('costSoFar')}")
            return
        time.sleep(15)
    pod_stop("queue done but the pod was still on after 5 min")
    print("final:", pod_status())


def others_waiting():
    """How many queue items that are not mine are pending or running (read in memory, names never printed)."""
    mine = {r["job_id"] for r in load().values() if r.get("job_id")}
    items = json.loads(curl(f"{BASE}/api/queue")[1]).get("items", [])
    return sum(1 for i in items if i.get("id") not in mine and i.get("status") in ("pending", "running"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=lambda s: set(s.split(",")), default=None)
    ap.add_argument("--series", default="m", help="m = P1 main scenes, o = the new opening (O1-O4)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--retake", action="store_true", help="queue the selected shots again as a new take")
    ap.add_argument("--cancel", action="store_true", help="delete my own PENDING items for --only keys (verified one by one)")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--run-all", action="store_true", help="wait for a READY pod, queue all at once, collect, confirm the pod is off")
    ap.add_argument("--start-pod", action="store_true", help="with --run-all: also POST /api/pod/start (needs the CEO's OK + a permission rule)")
    ap.add_argument("--max-wait-min", type=int, default=240)
    ap.add_argument("--wait", action="store_true", help="collect every 45 s until every shot is filed or failed")
    ap.add_argument("--out", default="/tmp/ilag-h3-previz")
    a = ap.parse_args()
    if a.cancel:
        cancel(a)
    elif a.run_all:
        run_all(a)
    elif a.wait:
        wait(a)
    elif a.collect:
        collect(a)
    else:
        enqueue(a)


if __name__ == "__main__":
    main()
