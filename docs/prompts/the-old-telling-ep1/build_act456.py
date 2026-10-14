#!/usr/bin/env python3
"""The Old Telling EP1 ACT 4, 5 and 6 (Thai cut, about 4:30 to 10:00): shots as DATA (act4_shots.py, act5_shots.py, act6_shots.py), one template, no paid call unless --fire.

    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act456.py --act 4                       # write shots4/*.txt + cards-act4.json
    .venv/bin/python -I docs/prompts/the-old-telling-ep1/build_act456.py --act 4 --fire [--only s03a,s04a]   # queue on the studio

Same method as build_act3.py (lengths on the measured H3 grid: 4 s = 107 f, 5 = 124, 6 = 141, 7 = 175, 8 = 192, 15 = 362 at 24 fps; narration is never bound to H3).
No shot of these three ACTs carries a spoken line of its own: Eurydice, the Thracian woman and the head are voice-only lines laid in the edit. Rules from build.py:
each @ref exactly once, adults 18+ and no child, no blush or red ears, no gore or wounds, the studio h3Model must equal --model (CEO owns it),
`--fire` prints ONLY ids of the rows it creates, never the queue (the shared Colab belongs to the CEO too).
CEO 2026-10-10: 'ทำ ARCT 4-6 ต่อได้เลย อณุมติ CU เพิ่มอีก 200 ใช้เสร็จแล้วปิดให้ด้วย'; at most ONE retake per scene, only for a scene that breaks the rules.
"""
import argparse, hashlib, importlib, json, pathlib, re, sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import build  # REFS, GRADE, HOUSE_NEG
import h3_setup as h

QUALITY, ASPECT = "1080p", "16:9"
GRID = {4: 107, 5: 124, 6: 141, 7: 175, 8: 192, 15: 362}  # request seconds -> frames (rules.ts, measured)


def paste_block(s):
    parts = [s["header"], "", s["heading"], ""]
    over = s.get("refover", {})
    parts += ["REFERENCES, each with a job:", "\n".join(over.get(k, build.REFS[k]) for k in s["refs"]), ""]
    parts += ["THE FRAME: " + s["frame"], "", "WHAT HAPPENS:", "\n".join(s["beats"]), "", s["sound"]]
    parts += ["", build.GRADE, "", s["crit"], "", build.HOUSE_NEG]
    return "\n".join(parts)


def check(s, text):
    for k in s["refs"]:
        n = len(re.findall(r"@" + k + r"\b", text))
        if n != 1:
            sys.exit(f"{s['key']}: @{k} appears {n} times (rule 2: exactly once)")
    for bad in ("blush", "flushed", "red cheek", "red ear", "หน้าแดง", "หูแดง"):
        for m in re.finditer(bad, text):
            if "no " not in text[max(0, m.start() - 4):m.start()]:
                sys.exit(f"{s['key']}: '{bad}' outside the closing negation")
    if f"[{s['hold']}] Hold" not in text:
        sys.exit(f"{s['key']}: no hold beat at {s['hold']} (rule 13)")
    if text.count("@") != len(s["refs"]):
        sys.exit(f"{s['key']}: stray @ in the paste block")
    if s["sec"] not in GRID:
        sys.exit(f"{s['key']}: {s['sec']} s is not a request length we planned")
    if "—" in text:
        sys.exit(f"{s['key']}: em dash in the paste block")
    for bad in ("nude", "naked", "bare chest", "gore", "bleeding"):
        for m in re.finditer(bad, text):
            if "no " not in text[max(0, m.start() - 4):m.start()] and "no bare skin" not in text[max(0, m.start() - 14):m.start() + 12]:
                sys.exit(f"{s['key']}: '{bad}' outside a negation")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--act", type=int, required=True, choices=[4, 5, 6])
    ap.add_argument("--fire", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--model", default="cobijada")
    a = ap.parse_args()
    shots = importlib.import_module(f"act{a.act}_shots").SHOTS
    out = HERE / f"shots{a.act}"; out.mkdir(exist_ok=True)
    keys = [s["key"] for s in shots]
    if len(set(keys)) != len(keys):
        sys.exit("duplicate shot key")
    only = [x for x in a.only.split(",") if x]
    for x in only:
        if x not in keys:
            sys.exit(f"--only {x}: no such shot in ACT {a.act}")
    cards, total_s = [], 0.0
    for s in shots:
        text = paste_block(s); check(s, text)
        frames = GRID[s["sec"]]; total_s += frames / 24
        notes = (f"=== NOTES · DO NOT PASTE ANY OF THIS ===\n{s['title']} · {s['sec']}s request ({frames} frames, {frames/24:.2f} s) · {QUALITY} · {ASPECT} · The Old Telling EP1 ACT {a.act} · covers sentences {s['line']}\n"
                 f"Entities (group 'The Old Telling'): {', '.join('@' + k for k in s['refs']) or 'none'}. Audio bound: none.\nNarration is NOT in this clip; it is mixed in the edit.\n=== END NOTES ===\n\n")
        (out / f"{s['key']}.txt").write_text(notes + "=== ↓↓↓ PASTE FROM HERE ↓↓↓ ===\n\n" + text + "\n\n=== ↑↑↑ PASTE STOPS HERE ↑↑↑ ===\n", encoding="utf-8")
        cards.append(dict(key=s["key"], batchTitle=f"The Old Telling EP1 ACT{a.act} {s['key']}", aspect=ASPECT,
                          card=dict(originalIndex=1, title=s["title"], prompt=text, include=True, linkAbove=False, seconds=s["sec"], quality=QUALITY,
                                    rating="safe", ratedSha256=hashlib.sha256(text.encode("utf-8")).hexdigest(), audios=[])))
        print(f"{s['key']}: {s['sec']}s -> {frames} f {frames/24:.2f} s · {len(text.split())} words · refs {s['refs']}")
    (out / f"cards-act{a.act}.json").write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ACT {a.act}: total requested picture {total_s:.2f} s in {len(shots)} shots · est CU at 0.10 per second {total_s * 0.10:.1f} (all-in about x1.35 = {total_s * 0.135:.1f})")
    if not a.fire:
        return
    code, st = h.api("/api/settings")
    cur = st.get("h3Model", "stock")
    if cur != a.model:
        sys.exit(f"STOP: studio h3Model is {cur!r}, --model says {a.model!r}. The CEO owns that setting; nothing queued.")
    created = {r["atId"] for r in json.loads((HERE / "h3-entities-created.json").read_text(encoding="utf-8")) if r.get("id")}
    miss = sorted({k for s in shots for k in s["refs"]} - created)
    if miss:
        sys.exit(f"no entity of ours for {miss}")
    fired_path = HERE / f"h3-fired-act{a.act}.json"
    already = {r["clip"] for r in json.loads(fired_path.read_text(encoding="utf-8"))} if fired_path.exists() else set()
    rows = []
    for c in cards:
        if only and c["key"] not in only:
            continue
        if c["key"] in already and not only:
            print(f"{c['key']}: already fired (h3-fired-act{a.act}.json), skipped; name it in --only for the one retake")
            continue
        code, res = h.api("/api/scenes/enqueue", {"batchTitle": c["batchTitle"], "aspect": ASPECT, "cards": [dict(c["card"])]})
        if code != 200:
            sys.exit(f"{c['key']}: enqueue answered HTTP {code}: {str(res)[:200]}")
        ids = [i.get("id") for i in (res.get("queued") or []) if isinstance(i, dict)]  # `items` is everybody's queue: never printed
        rows.append({"clip": c["key"], "ids": ids, "routes": res.get("routes"), "routeCostUsd": res.get("routeCostUsd"), "h3Model": cur})
        print(f"{c['key']}: queued {len(ids)} ids {ids} · routes {res.get('routes')} · routeCostUsd {res.get('routeCostUsd')}")
        h.record(fired_path.name, [rows[-1]])
    q = h.api("/api/queue")[1]
    q = q if isinstance(q, list) else q.get("items", q.get("queue", []))
    mine = {i for r in rows for i in r["ids"]}
    for it in q:
        if it.get("id") in mine:
            print(f"item {it['id']} status {it.get('status')} savedRefs {len(it.get('savedRefs') or [])} quality {it.get('quality')} seconds {it.get('seconds')} frames {it.get('frames')}")


main()
