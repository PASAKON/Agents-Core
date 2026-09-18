#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a «บัญชี» shot sheet from its data file.

Why this exists: in the first Act 1 shoot the bedroom rendered as two different
rooms on the same location chip, the grandmother sat up because one prompt forgot
to restate her posture, and a ledger appeared because one prompt never said not
to. Every one of those was a block written slightly differently in two places.

So the blocks live once, in the data file, and every prompt is assembled from
them. A set cannot drift between two shots unless someone edits the set itself.

    python3 tools/build_shotsheet.py docs/scripts/banchi-ACT1.data.py \
                                     docs/scripts/banchi-ACT1.md
"""
import importlib.util
import sys
from pathlib import Path

COST = {4: 6, 6: 9, 8: 12, 10: 15}


def load(path: Path):
    spec = importlib.util.spec_from_file_location("sheetdata", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(d) -> str:
    out, t = [], 0.0
    total_cost = 0
    out.append("# «บัญชี» — องก์ 1 (rework)\n")
    out.append("**สร้างจาก `docs/scripts/banchi-ACT1.data.py` ด้วย `tools/build_shotsheet.py` — "
               "ห้ามแก้ไฟล์นี้ตรงๆ แก้ที่ data แล้ว build ใหม่**\n")
    out.append("Omni 1.1 Flash · 9:16 · 720p (ทดสอบ 360p) · โหมด `องค์ประกอบ` · x1\n")
    out.append("""## กฎที่ไฟล์นี้ถูกสร้างมาให้เชื่อฟัง

1. **ความยาวช็อตตามประโยค** 4/6/8/10 วิ — ไม่ใช่ 8 วิตายตัว
2. **บทเริ่มในวินาทีแรก จบพร้อมช็อต** ไม่มี air ค้างท้าย
3. **กล้องอยู่ที่หน้าคนพูดเสมอ** — พูดนอกจอ = เสียงสุ่ม ไม่ใช่เสียงที่ล็อกไว้
4. **chip ไม่เกิน 3** ตัวที่ 4 ถูกปิดเงียบๆ · `<IMAGE_REF_N>` นับตามลำดับที่ใส่
5. **บล็อกหน้าตา/ฉาก/ท่า แปะคำต่อคำ** ทุกช็อต — ห้ามย่อ
6. **NOT-LIST** อุดสิ่งที่โมเดลเดาเองรอบก่อน: ธนบัตร สมุดบัญชี แว่นย่า ท่านั่ง
7. **อารมณ์เสียงอยู่ข้างบรรทัด** ตามรูปแบบของ Google เอง — `says, <direction>: "…"`
""")
    for (n, dur, framing, chars, lockey, tod, action, lines, nots) in d.SHOTS:
        lochandle, locdesc = d.LOC[lockey]
        def full(c):
            desc = d.CHAR[c][1]
            if c == "ton" and lockey == "shop":
                desc += d.APRON
            return desc
        chips = [(d.CHAR[c][0], full(c)) for c in chars] + [(lochandle, locdesc)]
        if len(chips) > 3:
            raise SystemExit(f"shot {n}: {len(chips)} chips — the 4th is silently disabled")
        start = f"{int(t)//60}:{int(t)%60:02d}"
        t += dur
        end = f"{int(t)//60}:{int(t)%60:02d}"
        total_cost += COST[dur]

        out.append(f"\n### SHOT {n} · {start}–{end} · {dur}s · {framing}")
        out.append("**ATTACH** " + " · ".join(
            f"{i+1}) `{h}`→REF_{i}" for i, (h, _) in enumerate(chips)))
        for sp, direction, line in lines:
            out.append(f"**บทพูด** {d.CHAR[sp][0].lstrip('@')} `\"{line}\"` — {direction}")
        out.append("```")
        refs = []
        for i, (h, desc) in enumerate(chips):
            kind = "location" if h == lochandle else "character"
            refs.append(f"Use <IMAGE_REF_{i}> as the {kind} reference for {h.lstrip('@')}.")
        out.append(" ".join(refs))
        out.append("")
        # the scene, with every block inline
        who = ", ".join(f"{full(c)} <IMAGE_REF_{i}>" for i, c in enumerate(chars))
        locref = f"<IMAGE_REF_{len(chars)}>"
        out.append(f"In {locdesc} {locref}, {tod}. {who} — {action}.")
        out.append("")
        for sp, direction, line in lines:
            idx = chars.index(sp)
            out.append(f'{d.CHAR[sp][2]} <IMAGE_REF_{idx}> speaks Thai, {direction}, and says: "{line}"')
        out.append("")
        out.append("The face of whoever is speaking stays in frame for the whole line.")
        if nots:
            out.append(" ".join(d.NOT[k] for k in nots))
        out.append(f"{framing}. {d.STYLE}")
        out.append("```")

    mins, secs = int(t) // 60, int(t) % 60
    out.insert(3, f"**{len(d.SHOTS)} ช็อต · {int(t)} วินาที = {mins}:{secs:02d} · "
                  f"~{total_cost} เครดิต ที่ 720p**\n")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    data, dest = Path(sys.argv[1]), Path(sys.argv[2])
    dest.write_text(build(load(data)), encoding="utf-8")
    print(f"built {dest} from {data}")
