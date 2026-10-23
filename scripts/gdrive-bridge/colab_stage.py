#!/usr/bin/env python3
"""Put one finished Colab take into Drive `ALL DRAFT/YT: คลิปจีน/00 พักงาน (Colab)/` (CEO 2026-10-23).

    python3 scripts/gdrive-bridge/colab_stage.py <take dir>            # upload + md5 by id, keep local
    python3 scripts/gdrive-bridge/colab_stage.py <take dir> --clear    # ... then delete the local clips

The take dir is what ComfyRunpod scripts/colab/run_take.py wrote: NN.mp4 + timings.json (+ job.json,
logs). It lands in `<YYYY-MM-DD>_<take dir name>/` under the staging folder. Every file is checked by
md5 read back by id (CXO_Rules_GDrive_Filing rule 12). A file whose name already exists there is never
overwritten (rule 11): the run stops and says so. --clear deletes only the mp4s whose md5 matched.
Rules for what happens next: CXO_Rules_GDrive_Filing §YT: คลิปจีน.
"""
import argparse
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ilag_rest as r  # noqa: E402

STAGING = "1An6wwRjpawETXztPUerdsMJ6aWMtYEzW"   # ALL DRAFT/YT: คลิปจีน/00 พักงาน (Colab)
KEEP = ("timings.json", "job.json", "remote.log", "guard.log")


def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument("take_dir")
    ap.add_argument("--clear", action="store_true", help="delete the local mp4s after their md5 matched")
    a = ap.parse_args()
    take = Path(a.take_dir).resolve()
    clips = sorted(take.glob("[0-9][0-9].mp4"))
    if not clips:
        sys.exit(f"no NN.mp4 in {take}")
    day = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    folder, _ = r.mkfolder(STAGING, f"{day}_{take.name}")
    done = []
    for f in clips + [take / k for k in KEEP if (take / k).is_file()]:
        info, made = r.upload(f, f.name, folder)
        local = hashlib.md5(f.read_bytes()).hexdigest()
        if not made and info.get("md5Checksum") != local:
            sys.exit(f"STOP {f.name}: a different file of that name is already in the folder (rule 11)")
        print(f"ok {f.name} md5 {local} {'uploaded' if made else 'already there'}")
        done.append(f)
    if a.clear:
        for f in done:
            if f.suffix == ".mp4":
                f.unlink()
        print(f"cleared {sum(1 for f in done if f.suffix == '.mp4')} local clip(s)")
    print(f"folder {r.flink(folder)}")


if __name__ == "__main__":
    main()
