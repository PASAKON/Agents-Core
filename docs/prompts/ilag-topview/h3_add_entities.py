"""Add the ILAG trailer's Elements to the MiniMax H3 studio over its HTTP API (Mac, via the tailnet).

API as briefed by CTO cto-6bfdc084 (2026-09-25): POST /api/upload (multipart, correct MIME) -> {"file"},
POST /api/entities {kind,name,atId,notes,refs:[{id,kind,file,label}]}; atId is made unique server-side.
WARNING: the POST response is the WHOLE entity list; it is discarded unread. Only a 409 (duplicate name, ComfyRunpod 662d9b8) body is read, for the clashing id. New entities carry "group": GROUP.
CEO: "ห้ามยุ่งหรือดูรูปอื่นๆ ที่แอดไว้นะ อันนั้นงานของคนอื่น" -> this script never prints, opens or edits
anybody else's entity: it reads the existing atIds into memory only to refuse a collision, and it
touches nothing but the rows it creates. One request at a time (the API has no lock).

    python3 h3_add_entities.py --files <dir with the PNGs> [--dry-run]
"""
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path

BASE = "http://100.64.2.37:4100"
HERE = Path(__file__).parent
# Every entity of this film goes in one studio group (ComfyRunpod 662d9b8); the CEO's own
# entities sit in other groups and are never touched.
GROUP = "ILAG TopView"


def curl(*args):
    r = subprocess.run(["curl", "-s", "-m", "120", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"curl failed ({r.returncode}): {r.stderr[:200]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", required=True, help="dir holding <drive_name> or ref-<atId>.png files")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", type=lambda s: set(s.split(",")), default=None,
                    help="add only these atIds (a later addition; the rest already exist)")
    a = ap.parse_args()
    man = json.loads((HERE / "h3-entities.json").read_text(encoding="utf-8"))["entities"]
    if a.only:
        man = [e for e in man if e["atId"] in a.only]
        if {e["atId"] for e in man} != a.only:
            raise SystemExit(f"not in h3-entities.json: {a.only - {e['atId'] for e in man}}")
    src = Path(a.files)

    # 1. local files, md5 against the manifest (= Drive's md5)
    plan = []
    for e in man:
        p = src / e["drive_name"]
        if not p.exists():
            raise SystemExit(f"missing file for @{e['atId']}: {p}")
        h = hashlib.md5(p.read_bytes()).hexdigest()
        if h != e["md5"]:
            raise SystemExit(f"md5 mismatch for @{e['atId']}: {h} vs {e['md5']}")
        plan.append((e, p))

    # 2. collisions: existing atIds held in memory only, never printed
    existing = json.loads(curl(f"{BASE}/api/entities"))
    rows = existing if isinstance(existing, list) else existing.get("entities", [])
    taken = {str(r.get("atId", "")).lower() for r in rows if isinstance(r, dict)}
    clash = [e["atId"] for e, _ in plan if e["atId"].lower() in taken]
    print(f"{len(plan)} to add · md5 all match · atId collisions: {clash or 'none'}")
    if clash:
        raise SystemExit("STOP: those handles are already taken; nothing was created")
    if a.dry_run:
        return

    # 3. upload + create, one at a time
    done = []
    for e, p in plan:
        up = json.loads(curl("-F", f"file=@{p};type=image/png", f"{BASE}/api/upload"))
        body = {"kind": e["kind"], "name": e["name"], "atId": e["atId"], "notes": e["description"], "group": GROUP,
                "refs": [{"id": "r1", "kind": "image", "file": up["file"], "label": "identity"}]}
        resp = HERE / ".entity-post.json"
        code = curl("-o", str(resp), "-w", "%{http_code}", "-H", "Content-Type: application/json",
                    "-d", json.dumps(body), f"{BASE}/api/entities?return=saved").strip()
        try:
            if code == "409":
                # Duplicate name (ComfyRunpod 662d9b8): the body names the entity that already has it.
                # Treat it as "already exists, use that id"; never retry with a suffix.
                err = json.loads(resp.read_text(encoding="utf-8") or "{}")
                cid = next((v for k, v in err.items() if "id" in k.lower() and isinstance(v, str)), None)
                done.append({"atId": e["atId"], "server_atId": None, "id": cid, "upload": up["file"],
                             "md5": e["md5"], "status": "exists-409"})
                print(f"@{e['atId']:15} -> 409 name already exists, id {cid}; not created")
                continue
            if code not in ("200", "201"):
                raise SystemExit(f"POST /api/entities for @{e['atId']} answered HTTP {code}")
        finally:
            # Even with ?return=saved the success body is discarded unread; without it the POST
            # answers with EVERY entity (other people's included). Only a 409 error body is read.
            resp.unlink(missing_ok=True)
        # Find our row by the upload filename, which only this run knows.
        rows = json.loads(curl(f"{BASE}/api/entities"))
        ent = next((r for r in rows if any(isinstance(x, dict) and x.get("file") == up["file"] for x in r.get("refs", []))), {})
        got = ent.get("atId")
        done.append({"atId": e["atId"], "server_atId": got, "id": ent.get("id"), "upload": up["file"], "md5": e["md5"]})
        print(f"@{e['atId']:15} -> id {done[-1]['id']}  file {up['file']}  atId {got}")
        if got != e["atId"]:
            print(f"  WARNING: server gave the handle {got!r}")
        time.sleep(0.3)
    # Append: an --only run must not wipe the record of the entities created before it.
    rec = HERE / "h3-entities-created.json"
    prior = json.loads(rec.read_text(encoding="utf-8")) if rec.exists() else []
    rec.write_text(json.dumps(prior + done, indent=1, ensure_ascii=False), encoding="utf-8")
    print("created", len(done))


if __name__ == "__main__":
    sys.exit(main())
