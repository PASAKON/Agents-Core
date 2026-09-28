#!/usr/bin/env python3
"""Put the Chatudo outreach tracker (plan O1) on Drive as a Google Sheet, and check what Google computes.

  verify FILE_ID   read-only: export the live Sheet, count formula errors, compare its TODAY() with Bangkok's date
  run              ensure PROJECT/CHATUDO/Sales & Outreach (CEO approved 2026-09-28), create the Sheet from a
                   12-row sample build, check Google's values, then replace the content with the empty tracker
                   (same file id, so nothing is deleted) and check again. Refuses if the Sheet already exists.

Live Sheet (2026-09-28): 1kqCYwXOJ2rdnOwAtitICTtoZ3WW01aBuz1cMP6Ta7e0 in PROJECT/CHATUDO/Sales & Outreach.

A converted Sheet starts on America/Los_Angeles, so TODAY() lags Bangkok until 14:00 and day-3/day-7 follow-ups
show a day late. The Sheets API is off on the org OAuth project, so only File > Settings (time zone Bangkok,
locale United Kingdom so 01/10/2026 parses as 1 Oct) fixes it. `verify` can tell only between 00:00 and 14:00
Bangkok, when the two dates differ; outside that window it says INCONCLUSIVE. The locale cannot be read back at all.

Auth: the Drive OAuth in ClaudeFlow's .env, through scripts/gdrive-bridge/ilag_sync.py (values never printed).
Needs openpyxl. Work files go to $CHATUDO_O1_DIR (default: the system temp dir).
"""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("CHATUDO_O1_DIR") or tempfile.gettempdir()
os.environ.setdefault("MOONIEX_CLAUDEFLOW_ENV", "/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env")
sys.path.insert(0, os.path.join(HERE, "gdrive-bridge"))
import ilag_sync as g  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

PROJECT_ID = "1HVLTPS09R4WvhYyOPW_0HHrfWxWGF-hQ"
L1, L2 = "CHATUDO", "Sales & Outreach"
TITLE = "Chatudo ตารางทักร้าน"
FOLDER = "application/vnd.google-apps.folder"
GSHEET = "application/vnd.google-apps.spreadsheet"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ERRS = {"#NAME?", "#ERROR!", "#VALUE!", "#REF!", "#N/A", "#DIV/0!", "#NUM!", "#NULL!"}
# chatudo_outreach_sheet.py --sample 12, 'ต้องทำต่อ' per row; rows 4 and 8 are due today, so they read 'รอ'
# while the Sheet's clock is a day behind Bangkok.
EXPECT_Y = ["รอ", "โทรหาเจ้าของ", "ติดตั้งร้านนำร่อง", "ตามครั้งที่ 1", "รอ", "รอ", "รอ", "ตามครั้งที่ 2",
            "หยุด (ตามครบ 2 ครั้ง)", "หยุด (ตามครบ 2 ครั้ง)", "ทักครั้งแรก", "ทักครั้งแรก"]


def children(fid):
    res = g.api(g.DRIVE_FILES, params={"q": f"'{fid}' in parents and trashed = false",
                                       "fields": "files(id,name,mimeType,webViewLink)", "pageSize": "200"})
    return res.get("files", [])


def ensure_folder(parent, name):
    for f in children(parent):
        if f["name"] == name and f["mimeType"] == FOLDER:
            return f["id"], False
    made = g.api(g.DRIVE_FILES, method="POST", params={"fields": "id"},
                 data=json.dumps({"name": name, "parents": [parent], "mimeType": FOLDER}).encode(),
                 headers={"Content-Type": "application/json"})
    return made["id"], True


def build(path, sample):
    cmd = [sys.executable, os.path.join(HERE, "chatudo_outreach_sheet.py"), "--out", path]
    if sample:
        cmd += ["--sample", str(sample)]
    subprocess.run(cmd, check=True)


def create_sheet(path, parent):
    boundary = "o1chatudoboundary"
    meta = json.dumps({"name": TITLE, "parents": [parent], "mimeType": GSHEET}).encode()
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode() + meta
            + f"\r\n--{boundary}\r\nContent-Type: {XLSX}\r\n\r\n".encode() + open(path, "rb").read()
            + f"\r\n--{boundary}--".encode())
    return g.api(g.DRIVE_UPLOAD, method="POST",
                 params={"uploadType": "multipart", "fields": "id,name,mimeType,webViewLink"},
                 data=body, headers={"Content-Type": f"multipart/related; boundary={boundary}"})


def replace_content(fid, path):
    return g.api(f"{g.DRIVE_UPLOAD}/{fid}", method="PATCH",
                 params={"uploadType": "media", "fields": "id,name,mimeType,modifiedTime"},
                 data=open(path, "rb").read(), headers={"Content-Type": XLSX})


def export(fid, out):
    url = f"{g.DRIVE_FILES}/{fid}/export?" + urllib.parse.urlencode({"mimeType": XLSX})
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + g.access_token()})
    with urllib.request.urlopen(req, timeout=120) as r:
        open(out, "wb").write(r.read())
    return load_workbook(out, data_only=True)


def errors(wb):
    return [f"{ws.title}!{c.coordinate}={c.value}" for ws in wb.worksheets for row in ws.iter_rows() for c in row
            if c.data_type == "e" or (isinstance(c.value, str) and c.value.strip() in ERRS)]


def day(v):
    return v.date().isoformat() if isinstance(v, dt.datetime) else (v.isoformat() if isinstance(v, dt.date) else v)


def main():
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    if step == "verify":
        wb = export(sys.argv[2], os.path.join(WORK, "o1-export-verify.xlsx"))
        now_bkk = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=7)
        bkk = now_bkk.date().isoformat()
        sheet_today = day(wb["สรุปวันจันทร์"]["B2"].value)
        # From 14:00 Bangkok, Pacific time is on the same date, so a match proves nothing then.
        if now_bkk.hour >= 14:
            verdict = "INCONCLUSIVE (run between 00:00 and 14:00 Bangkok)"
        else:
            verdict = "TZ OK" if sheet_today == bkk else "TZ WRONG"
        print(f"errors={len(errors(wb))} sheet TODAY()={sheet_today} bangkok={bkk} "
              f"{now_bkk:%H:%M} -> {verdict}")
        return
    if step != "run":
        raise SystemExit(__doc__)

    l1, made1 = ensure_folder(PROJECT_ID, L1)
    l2, made2 = ensure_folder(l1, L2)
    print(f"L1 {L1} {l1} {'CREATED' if made1 else 'existing'}")
    print(f"L2 {L2} {l2} {'CREATED' if made2 else 'existing'}")
    if any(f["name"] == TITLE for f in children(l2)):
        raise SystemExit(f"{TITLE!r} already exists in {L2}; use verify")

    sample, empty = os.path.join(WORK, "o1-sample.xlsx"), os.path.join(WORK, "o1-empty.xlsx")
    build(sample, 12)
    build(empty, 0)
    f = create_sheet(sample, l2)
    fid = f["id"]
    wb = export(fid, os.path.join(WORK, "o1-export-sample.xlsx"))
    shop = wb["ร้าน"]
    fails = [f"Y{2 + i}: {shop[f'Y{2 + i}'].value!r} != {want!r}" for i, want in enumerate(EXPECT_Y)
             if shop[f"Y{2 + i}"].value != want]
    print(f"sample: errors={errors(wb)[:10]} next-action mismatches={fails}")

    replace_content(fid, empty)
    wb2 = export(fid, os.path.join(WORK, "o1-export-empty.xlsx"))
    left = [f"{c}{r}" for r in range(2, 14) for c in "BCLY" if wb2["ร้าน"][f"{c}{r}"].value not in (None, "")]
    print(f"empty: errors={errors(wb2)[:10]} sample cells left={left} tabs={wb2.sheetnames}")
    print("SHEET", fid, f.get("webViewLink"))


if __name__ == "__main__":
    main()
