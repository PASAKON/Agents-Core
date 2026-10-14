#!/usr/bin/env python3
"""The Old Telling EP1: put the plates into the H3 studio and queue the four clips (Mac, studio on :4100).

    python3 -I docs/prompts/the-old-telling-ep1/h3_setup.py entities [--dry-run]
    python3 -I docs/prompts/the-old-telling-ep1/h3_setup.py audio
    python3 -I docs/prompts/the-old-telling-ep1/h3_setup.py fire --only e01 --model cobijada|stock [--dry-run]

Rules it enforces (CMO_Knowledge_MiniMax_H3 section 3 and 4):
- every entity goes in group "The Old Telling"; atIds and names are checked against the library IN MEMORY
  only; nothing of anybody else's entity is printed, opened or edited;
- one request at a time; a 409 means "already exists", never retried with a suffix;
- `fire` refuses unless --model equals the studio's global h3Model right now (the CEO owns that setting;
  this script never changes it), refuses an item whose @reference has no entity of ours, and prints only
  ids, counts, routes and cost, never prompt text.
Provenance (CEO 2026-10-05, every action auditable): h3-entities-created.json, h3-audio-uploaded.json,
h3-fired.json beside this file.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).parent
BASE = "http://127.0.0.1:4100"
GROUP = "The Old Telling"
PLATES = pathlib.Path("/private/tmp/claude-501/-Users-gob-MoonieXHQ-Agents-Core/4f1a10f5-0427-4c0c-bbaf-d71cf76492bf/scratchpad/plates")
AUDIO = pathlib.Path("/private/tmp/claude-501/-Users-gob-MoonieXHQ-Agents-Core/4f1a10f5-0427-4c0c-bbaf-d71cf76492bf/scratchpad/voice1/out/orpheus_word_15s.mp3")

# atId -> (kind, [(plate file, label)])
ENTITIES = {
    "ORPHEUS": ("character", [("ORPHEUS__face.png", "identity face"), ("ORPHEUS__wanderer.png", "identity full body")]),
    "ORPHEUS_ASHEN": ("character", [("ORPHEUS__face.png", "identity face"), ("ORPHEUS__ashen.png", "state after the cave")]),
    "KING": ("character", [("KING__face.png", "identity face")]),
    "EURYDICE": ("prop", [("EURYDICE__dress.png", "her dress")]),
    "ANIMALS": ("character", [("ANIMALS__three.png", "deer, wolf, fox")]),
    "LYRE": ("prop", [("lyre2.png", "the lyre")]),
    "MEADOW": ("location", [("MEADOW__dusk.png", "dusk with the flat stone")]),
    "MEADOW_GREY": ("location", [("MEADOW__grey.png", "after the sun is gone")]),
    "TELLER_ROOM": ("location", [("TELLER_ROOM__ring.png", "room with ringed hands")]),
    "THRONES": ("location", [("thrones.png", "king and queen on two thrones")]),
    "STAIR": ("location", [("underworld_stair.png", "stair to the daylight")]),
}


def api(path, body=None, method=None):
    req = urllib.request.Request(BASE + path, method=method or ("POST" if body is not None else "GET"),
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def upload(path, mime):
    out = subprocess.run(["curl", "-s", "-m", "120", "-F", f"file=@{path};type={mime}", f"{BASE}/api/upload"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"upload failed ({out.returncode}) for {path.name}")
    j = json.loads(out.stdout)
    if "file" not in j:
        sys.exit(f"upload of {path.name} answered {out.stdout[:120]}")
    return j["file"]


def record(name, rows, replace=False):
    p = HERE / name
    prior = [] if replace or not p.exists() else json.loads(p.read_text(encoding="utf-8"))
    p.write_text(json.dumps(prior + rows, indent=1, ensure_ascii=False), encoding="utf-8")


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


def cmd_entities(a):
    sys.path.insert(0, str(HERE))
    import build  # REFS is the single source of every entity's note
    rows = api("/api/entities")[1]
    rows = rows if isinstance(rows, list) else rows.get("entities", [])
    taken = {str(r.get("atId", "")).lower() for r in rows if isinstance(r, dict)}
    names = {str(r.get("name", "")).strip().lower() for r in rows if isinstance(r, dict)}
    plan = []
    for at, (kind, files) in ENTITIES.items():
        for f, _ in files:
            if not (PLATES / f).exists():
                sys.exit(f"missing plate {f}")
        name = f"Old Telling {at}"
        note = re.sub(r"^@[A-Z_]+: ", "", build.REFS[at])
        plan.append((at, kind, name, note, files))
    clash = [p[0] for p in plan if p[0].lower() in taken or p[2].lower() in names]
    print(f"{len(plan)} to add · plates all present · collisions: {clash or 'none'}")
    if clash:
        sys.exit("STOP: handle or name already taken; nothing was created")
    if a.dry_run:
        return
    done = []
    for at, kind, name, note, files in plan:
        refs = []
        for i, (f, label) in enumerate(files, 1):
            refs.append({"id": f"r{i}", "kind": "image", "file": upload(PLATES / f, "image/png"), "label": label})
        code, saved = api("/api/entities?return=saved", {"kind": kind, "name": name, "atId": at, "notes": note,
                                                         "group": GROUP, "refs": refs})
        if code == 409:
            cid = (saved.get("conflict") or {}).get("id") if isinstance(saved, dict) else None
            done.append({"atId": at, "id": cid, "status": "exists-409"})
            print(f"@{at:14} 409 already exists, id {cid}")
            continue
        if code not in (200, 201):
            sys.exit(f"POST entity @{at} answered HTTP {code}")
        got = saved.get("atId")
        done.append({"atId": at, "serverAtId": got, "id": saved.get("id"), "kind": kind, "group": GROUP,
                     "refs": [{"upload": r["file"], "plate": f, "md5": md5(PLATES / f)} for r, (f, _) in zip(refs, files)],
                     "source": "ChatGPT web plate via tools/chatgpt_images_bg.py, CEO approved 2026-10-09"})
        print(f"@{at:14} id {saved.get('id')}  refs {len(refs)}  atId {got}" + ("" if got == at else "  WARNING handle changed"))
    record("h3-entities-created.json", done)
    print("created", len(done))


def cmd_audio(a):
    name = upload(AUDIO, "audio/mpeg")
    record("h3-audio-uploaded.json", [{"source": AUDIO.name, "md5": md5(AUDIO), "upload": name}], replace=True)
    print("uploaded", AUDIO.name, "->", name)


def cmd_fire(a):
    code, st = api("/api/settings")
    cur = st.get("h3Model", "stock")
    if cur != a.model:
        sys.exit(f"STOP: studio h3Model is {cur!r}, --model says {a.model!r}. The CEO owns that setting; nothing queued.")
    created = {r["atId"]: r for r in json.loads((HERE / "h3-entities-created.json").read_text(encoding="utf-8")) if r.get("id")}
    audio = json.loads((HERE / "h3-audio-uploaded.json").read_text(encoding="utf-8"))[0]["upload"]
    cards = json.loads((HERE / "shots" / "cards.json").read_text(encoding="utf-8"))
    fired = []
    for c in cards:
        key = c["batchTitle"].rsplit(" ", 1)[1]
        if a.only and key not in a.only.split(","):
            continue
        card = dict(c["card"])
        tags = re.findall(r"^@([A-Z_]+):", card["prompt"], flags=re.M)
        miss = [t for t in tags if t not in created]
        if miss:
            sys.exit(f"{key}: no entity of ours for {miss}")
        card["audios"] = [audio if x == "orpheus_word_15s.mp3" else x for x in card.get("audios", [])]
        body = {"batchTitle": c["batchTitle"], "aspect": c["aspect"], "cards": [card]}
        print(f"{key}: {len(tags)} refs {tags} · audios {card['audios']} · h3Model {cur}")
        if a.dry_run:
            continue
        code, res = api("/api/scenes/enqueue", body)
        if code != 200:
            sys.exit(f"{key}: enqueue answered HTTP {code}: {str(res)[:300]}")
        # `items` is the WHOLE queue (other people's rows too); `queued` holds only the rows this call created,
        # prompt text included. Take ids from `queued` and never print the rows.
        ids = [i.get("id") for i in (res.get("queued") or []) if isinstance(i, dict)]
        print(f"{key}: queued {len(ids)} ids {ids} · routes {res.get('routes')} · routeCostUsd {res.get('routeCostUsd')} · warnings {len(res.get('warnings') or [])}")
        q = api("/api/queue")[1]
        q = q if isinstance(q, list) else q.get("items", q.get("queue", []))
        for it in q:
            if it.get("id") in ids:
                print(f"{key}: item {it['id']} status {it.get('status')} savedRefs {len(it.get('savedRefs') or [])} quality {it.get('quality')} seconds {it.get('seconds')} h3Model {it.get('h3Model')}")
        fired.append({"clip": key, "ids": ids, "routes": res.get("routes"), "routeCostUsd": res.get("routeCostUsd"), "h3Model": cur})
    if fired:
        record("h3-fired.json", fired)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("entities"); e.add_argument("--dry-run", action="store_true"); e.set_defaults(fn=cmd_entities)
    u = sub.add_parser("audio"); u.set_defaults(fn=cmd_audio)
    f = sub.add_parser("fire"); f.add_argument("--only"); f.add_argument("--model", required=True); f.add_argument("--dry-run", action="store_true"); f.set_defaults(fn=cmd_fire)
    a = ap.parse_args()
    a.fn(a)
