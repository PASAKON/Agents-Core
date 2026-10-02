#!/usr/bin/env python3
"""schedule_photo_post.py <key> <poster.png> <caption_file> <day> <weekday_th>
Photo post from the Page profile on winbox :9281, scheduled <day> Oct 2026 19:30.
Order: upload -> AI label -> caption LAST -> next. Gates before the press (box length, AI chip ON, schedule
string, INPUTS). After the press: read the Scheduled list; if the row shows no caption, fix it through
«แก้ไขโพสต์» (caption + AI label + บันทึก) and read the list again. Never touches «ลบโพสต์»."""
import json, re, subprocess, sys
import os
S = os.environ.get("FBX_WORK", "/tmp/fbx")  # work dir: needs fb/ (action JSONs + results) and run_fbx.sh next to it
key, img, capf, day, wd = sys.argv[1:6]
cap = open(capf, encoding="utf-8").read().rstrip("\n")
first = cap.splitlines()[0]
W = "C:\\mooniex\\khaoniao\\sched\\"
PROFILE = "https://www.facebook.com/profile.php?id=61594776486312"


def run(name, acts):
    p = f"{S}/fb/{key}_{name}.json"
    json.dump(acts, open(p, "w"), ensure_ascii=False)
    out = subprocess.run([f"{S}/run_fbx.sh", p, f"{key}{name}", "40"], capture_output=True, text=True).stdout
    txt = open(f"{S}/fb/{key}{name}.txt", encoding="utf-8").read()
    j = txt.find("=====DIALOGS====="); k = txt.find("=====BODY=====")
    return out, txt[j:k], txt


def fails(out):
    return [l[:160] for l in out.splitlines() if l.startswith("FAIL")]


FOCUS = {"do": "eval", "js": "() => { const t=document.querySelector('[role=dialog] [role=textbox][contenteditable=true]'); if(!t) return 'NOBOX'; t.focus(); return 'focused' }"}
SCHED_LIST = [
    {"do": "goto", "url": PROFILE}, {"do": "wait", "ms": 6000},
    {"do": "clickvis", "text": "จัดการโพสต์"}, {"do": "wait", "ms": 4000},
    {"do": "clickvis", "text": "กำหนดเวลาแล้ว"}, {"do": "wait", "ms": 6000}]


def parse_rows(txt):
    b = txt[txt.find("=====BODY====="):].replace("\xa0", " ")
    lines = b.split("\n")
    rows = []
    for i, l in enumerate(lines):
        if l.strip().startswith("กำหนดเวลาแล้ว •") and i + 1 < len(lines):
            c = i - 1
            while c > 0 and not lines[c].strip():
                c -= 1
            rows.append((lines[c].strip(), lines[i + 1].strip()))
    return rows


def find_row(rows):
    for k, (c, d) in enumerate(rows):
        if wd in d or d.startswith(f"{day} ต.ค."):
            return k, c, d
    return None, None, None


# ---- stage a: composer ----
o, d, _ = run("a", [
    {"do": "goto", "url": PROFILE}, {"do": "wait", "ms": 6000},
    {"do": "click", "text": "คุณกำลังคิดอะไรอยู่", "exact": False, "nth": 0}, {"do": "wait", "ms": 4000},
    {"do": "upload", "sel": "input[type=file]", "nth": 1, "path": W + img}, {"do": "wait", "ms": 8000},
    {"do": "clickvis", "text": "ป้ายกำกับ AI ปิดอยู่", "last": True}, {"do": "wait", "ms": 3000},
    {"do": "clicksel", "sel": 'input[aria-label="เพิ่มป้าย AI"]'}, {"do": "wait", "ms": 1500},
    {"do": "eval", "js": "() => 'AI ' + document.querySelector('input[aria-label=\"เพิ่มป้าย AI\"]').checked"},
    {"do": "clickvis", "text": "เข้าใจแล้ว", "last": True}, {"do": "wait", "ms": 2500},
    FOCUS, {"do": "wait", "ms": 800}, {"do": "type", "value": cap, "delay": 6}, {"do": "wait", "ms": 1500},
    {"do": "eval", "js": "() => { const t=document.querySelector('[role=dialog] [role=textbox][contenteditable=true]'); const dl=[...document.querySelectorAll('[role=dialog]')].map(x=>x.innerText||'').join(' '); return 'BOXLEN ' + (t?(t.innerText||'').length:-1) + ' CHIP ' + dl.includes('ป้ายกำกับ AI เปิดอยู่') }"},
])
m = re.search(r"BOXLEN (-?\d+) CHIP (true|false)", o)
boxlen, chip = (int(m.group(1)), m.group(2) == "true") if m else (-1, False)
okA = ("AI true" in o) and ("NOBOX" not in o) and boxlen >= len(cap) - 5 and chip and not fails(o)
print("stage a", "AI true" in o, "boxlen", boxlen, "need", len(cap), "chip", chip, "fails", fails(o), flush=True)
assert okA, o

o, d, _ = run("a2", [{"do": "clickvis", "text": "ถัดไป", "last": True}, {"do": "wait", "ms": 4000}])
assert "การตั้งค่าโพสต์" in d and not fails(o), o

# ---- stage b: schedule ----
o, d, _ = run("b", [
    {"do": "click", "text": "ตัวเลือกการกำหนดเวลา", "exact": False, "nth": 0}, {"do": "wait", "ms": 2500},
    {"do": "clicksel", "sel": 'input[type="text"]', "nth": 0}, {"do": "wait", "ms": 1500},
    {"do": "clickvis", "text": day, "last": True}, {"do": "wait", "ms": 1500},
    {"do": "fill", "sel": 'input[type="text"]', "nth": 1, "value": "19:30"}, {"do": "wait", "ms": 1000},
    {"do": "key", "key": "Tab"}, {"do": "wait", "ms": 1500},
    {"do": "eval", "js": "() => 'INPUTS ' + [...document.querySelectorAll('input[type=text]')].map(e=>e.value).join(' | ')"},
    {"do": "click", "text": "กำหนดเวลาเริ่มเป็นภายหลัง", "exact": True, "nth": 0}, {"do": "wait", "ms": 2500}])
want = f"{day} ตุลาคม เวลา 19:30 น."
ok = (want in d) and (f"INPUTS {day} ต.ค. 2026 | 19:30" in o) and not fails(o)
print("GATE", ok, "sched-string", want in d, "inputs", f"INPUTS {day} ต.ค. 2026 | 19:30" in o, flush=True)
assert ok, o

# ---- stage c: press ----
o, d, _ = run("c", [{"do": "clickvis", "text": "กำหนดเวลา", "last": True}, {"do": "wait", "ms": 12000}])
print("pressed", fails(o), flush=True)

# ---- stage d: read the list back, fix a missing caption ----
o, d, txt = run("d", SCHED_LIST)
rows = parse_rows(txt)
k, c, dt = find_row(rows)
print("LIST row", k, "|", dt, "|", (c or "")[:50], flush=True)
if k is None:
    print("RESULT NOT-IN-LIST", flush=True); sys.exit(3)
if c.startswith(first[:20]):
    print("RESULT OK caption present", flush=True); sys.exit(0)
print("caption missing -> edit fix", flush=True)
o, d, _ = run("e", SCHED_LIST + [
    {"do": "clicksel", "sel": "[aria-label='การดำเนินการสำหรับโพสต์นี้']", "nth": k}, {"do": "wait", "ms": 2000},
    {"do": "clickvis", "text": "แก้ไขโพสต์", "last": True}, {"do": "wait", "ms": 5000},
    FOCUS, {"do": "wait", "ms": 800}, {"do": "type", "value": cap, "delay": 6}, {"do": "wait", "ms": 1500},
    {"do": "eval", "js": "() => 'AIBEFORE ' + [...document.querySelectorAll('[role=dialog] input[type=checkbox]')][0].checked"},
    {"do": "eval", "js": "() => { const c=[...document.querySelectorAll('[role=dialog] input[type=checkbox]')][0]; if(!c.checked) c.click(); return 'AIAFTER ' + c.checked }"},
    {"do": "wait", "ms": 2000},
    {"do": "eval", "js": "() => 'AIFINAL ' + [...document.querySelectorAll('[role=dialog] input[type=checkbox]')][0].checked"},
])
print("edit prepared", fails(o), [l for l in o.splitlines() if l.startswith("EVAL")], flush=True)
if "AIFINAL true" not in o or fails(o):
    print("RESULT EDIT-NOT-READY", flush=True); sys.exit(4)
o, d, _ = run("f", [{"do": "clickvis", "text": "บันทึก", "last": True}, {"do": "wait", "ms": 7000}])
o, d, txt = run("g", SCHED_LIST)
rows = parse_rows(txt)
k, c, dt = find_row(rows)
print("LIST after fix", k, "|", dt, "|", (c or "")[:50], flush=True)
print("RESULT", "OK caption fixed" if (c or "").startswith(first[:20]) else "STILL-MISSING", flush=True)
