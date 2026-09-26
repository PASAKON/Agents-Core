"""Download every reference picture the Wan3 jobs need from the film's Drive Element/ folders.

    python3 fetch_refs.py wan3/*.wan3.json --out /tmp/ilag-wan3/refs

Each job lists its pictures as Drive paths under Element/ ("Character/ref-Strong.png"); the file lands at
<out>/<basename>, which is what tools/topview_wan3.py looks for (--refs). Files already present with the Drive md5
are skipped. Read-only on Drive.
"""
import argparse, hashlib, json, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[2] / "scripts/gdrive-bridge"))
import ilag_rest as d  # noqa: E402

ELEMENT = {"Character": "1IXrrVe0WcdSNVjFxQHh5APm3Sr-8NsXa", "Location": "1mrnHtqYNcqUa5lyw_vVxxh0tvu-CJf71",
           "Prop": "1FUwd7qPAsBtrVjFxoOZpcHlbnK1fkjPf"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    want = sorted({p for j in a.jobs for p in json.loads(j.read_text(encoding="utf-8"))["images"]})
    listing = {folder: {f["name"]: f for f in d.ls(fid)} for folder, fid in ELEMENT.items()}
    for path in want:
        folder, name = path.split("/", 1)
        f = listing[folder].get(name)
        if not f:
            raise SystemExit(f"not on Drive: Element/{path}")
        dst = a.out / name
        if dst.exists() and hashlib.md5(dst.read_bytes()).hexdigest() == f.get("md5Checksum"):
            print(f"have {name}")
            continue
        req = urllib.request.Request(d.s.DRIVE_FILES + "/" + f["id"] + "?alt=media",
                                     headers={"Authorization": "Bearer " + d.s.access_token()})
        dst.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        ok = hashlib.md5(dst.read_bytes()).hexdigest() == f.get("md5Checksum")
        print(f"got  {name} {dst.stat().st_size} bytes md5 {'ok' if ok else 'MISMATCH'}")
        if not ok:
            raise SystemExit(f"md5 mismatch on {name}")
    print(f"{len(want)} pictures in {a.out}")


if __name__ == "__main__":
    main()
