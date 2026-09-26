"""(winbox copy: C:/mooniex/ilag-runner/tools/collect_tasks.py) Collect finished Wan3 clips by TopView board task id (read-only; clicks nothing).

    python collect_tasks.py --out DIR g1=<taskId> g3=<taskId> ...

Polls board.task.getBatchDetail (the call the board page itself makes) every 60 s. When a task leaves the running
states, every .mp4 URL in its result is downloaded as <key>.mp4, <key>-2.mp4 ... (a 4K upscale may be a second
file), with bytes, md5 and the credits the task recorded. Stops when every task has ended. Parallel runs on one
board cannot be mixed up this way, because each clip is fetched by its own task id.
"""
import argparse, hashlib, json, re, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

RUNNING = {"init", "running", "queue", "queued", "pending", "processing", "waiting", "upscaling"}
BOARD = "https://www.topview.ai/board/4252ab7766ad4150b3829427362f80f0?tool-type=video-edit&model-id=qwen-wan3.0-video"
JS = """async (ids) => {
  const input = encodeURIComponent(JSON.stringify({"0": {"taskIds": ids}}));
  const r = await fetch('/api/trpc/board.task.getBatchDetail?batch=1&input=' + input, {credentials: 'include'});
  return await r.text();
}"""


def tasks_of(text):
    data = json.loads(text)[0]["result"]["data"]
    data = data.get("data", data) if isinstance(data, dict) else data
    if isinstance(data, dict):
        data = data.get("list") or data.get("tasks") or list(data.values())
    return {t["taskId"]: t for t in data if isinstance(t, dict) and "taskId" in t}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--poll-s", type=int, default=60)
    ap.add_argument("--max-hours", type=float, default=4)
    a = ap.parse_args()
    want = dict(p.split("=", 1) for p in a.pairs)          # key -> taskId
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "collected.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    t0, last = time.time(), {}
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp("http://127.0.0.1:9224")
        page = b.contexts[0].new_page()
        page.goto(BOARD, wait_until="domcontentloaded", timeout=60000)
        try:
            while time.time() - t0 < a.max_hours * 3600:
                todo = {k: v for k, v in want.items() if k not in summary}
                if not todo:
                    break
                tasks = tasks_of(page.evaluate(JS, list(todo.values())))
                for key, tid in todo.items():
                    t = tasks.get(tid)
                    if not t:
                        continue
                    st = str(t.get("status"))
                    if last.get(key) != st:
                        print(f"{time.strftime('%H:%M:%S')} {key} {tid[:8]} status={st} cost={t.get('creditsCost')}", flush=True)
                        last[key] = st
                    if st.lower() in RUNNING:
                        continue
                    urls = list(dict.fromkeys(re.findall(r"https?://[^\"\\\\ ]+?\.mp4[^\"\\\\ ]*",
                                                          json.dumps(t.get("result"), ensure_ascii=False))))
                    files = []
                    for i, u in enumerate(urls, 1):
                        r = page.request.get(u, timeout=600_000)
                        if r.status != 200:
                            files.append({"url": u[:200], "error": f"HTTP {r.status}"}); continue
                        data = r.body()
                        path = out / (f"{key}.mp4" if i == 1 else f"{key}-{i}.mp4")
                        path.write_bytes(data)
                        files.append({"file": path.name, "bytes": len(data), "md5": hashlib.md5(data).hexdigest(),
                                      "url": u[:200]})
                    summary[key] = {"taskId": tid, "status": st, "creditsCost": t.get("creditsCost"),
                                    "errorMessage": t.get("errorMessage"), "completedAt": t.get("completedAt"),
                                    "files": files}
                    # Two collectors sharing one --out each loaded collected.json at start; the later write dropped
                    # the other's entries (g2/g6r2 lost, 2026-09-26). Merge with what is on disk now.
                    on_disk = json.loads(summary_path.read_text()) if summary_path.exists() else {}
                    summary = {**on_disk, **summary}
                    summary_path.write_text(json.dumps(summary, indent=1, ensure_ascii=False))
                    print(f"{time.strftime('%H:%M:%S')} {key} ENDED status={st} files={[f.get('file') or f.get('error') for f in files]}", flush=True)
                time.sleep(a.poll_s)
        finally:
            page.close()
    print("DONE" if all(k in summary for k in want) else "STOPPED (time)", json.dumps(summary, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
