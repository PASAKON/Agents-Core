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
import os
import re
import sys
from pathlib import Path

COST = {4: 6, 6: 9, 8: 12, 10: 15}

# Where the downloaded plates live. The CEO's rule (2026-09-18) is that no shot
# sheet gets written until every plate in it has actually been looked at, once,
# as one montage — after two Act 1 drafts were written from memory and the real
# plates then contradicted them three ways in ninety seconds.
PLATE_DIR = Path(os.environ.get("BANCHI_PLATES", Path.home() / "Desktop" / "banchi-plates"))


def load(path: Path):
    spec = importlib.util.spec_from_file_location("sheetdata", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CHIP_CAP = 10   # measured on the live product, task-68653632 2026-09-18


def check_plates(d) -> None:
    """Refuse to build a sheet that references a plate nobody has on disk.

    This is the rule the CEO wrote on 2026-09-18 ("ในการเขียนบทหนัง จะต้องดูภาพ
    ของตัวละครก่อน อย่างน้อย 1 ครั้ง ให้ครบทุกตัวละคร"), made mechanical. A
    remembered rule gets skipped; this one cannot be. Two handles in the first
    draft — @cop_wit and @side_wall — turned out never to have existed as assets
    at all, and nothing caught it until an operator scrolled the project by hand.

    There is deliberately no flag to skip this. A rule with an opt-out is not a
    rule; that lesson cost a merge gate once already.
    """
    used = set()
    for shot in d.SHOTS:
        _, _, _, chars, loc, *_ = shot
        used.update(d.CHAR[c][0] for c in chars)
        used.add(d.LOC[loc][0])

    missing = sorted(h for h in used if not (PLATE_DIR / f"{h.lstrip('@')}.png").exists())
    if missing:
        raise SystemExit(
            "refusing to build: no downloaded plate for "
            + ", ".join(missing)
            + f"\n  looked in: {PLATE_DIR}"
            + "\n  a sheet may not be written for an asset nobody has looked at."
            + "\n  fix: run the plate harvest (docs/briefs/banchi-plates-harvest.md),"
            + " or point BANCHI_PLATES at the folder that holds them."
        )


def build(d, act: str = "?") -> str:
    out, t = [], 0.0
    total_cost = 0
    out.append(f"# «บัญชี» — องก์ {act}\n")
    out.append(f"**สร้างจาก `docs/scripts/banchi-ACT{act}.data.py` ด้วย `tools/build_shotsheet.py` — "
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
        # Props ride on the shot's own declaration that it contains them: a shot
        # listing NOT["money"] is a shot with banknotes in frame, so it gets the
        # money Element rather than forty words hoping for one. Describing a prop
        # loses to the scene's context; binding it does not (2026-09-22: six Act 3
        # clips rendered a real Thai note with the royal portrait, while every
        # chip-bound character and location stayed correct across 148 clips).
        # No getattr default here on purpose. The first version of this used
        # `getattr(d, "PROP_FOR_NOT", {})`, ACT6 inherits only named symbols from
        # ACT1 and so did not have it, and the whole feature silently did nothing
        # — the sheet built clean with no money chip on any money shot. A lookup
        # that defaults to empty cannot tell you it found nothing.
        # NO automatic prop attachment. The first version of this keyed off
        # NOT["money"] on the theory that it marked a shot containing banknotes.
        # It does not: that entry is a PROHIBITION ("...also no notebook, no pen,
        # no paper, no ledger of any kind"), carried by 22 shots, most of which
        # have no money in frame at all — shot 133 is two people looking at empty
        # tables. Attaching the money Element to all of them would have put
        # banknotes into scenes written to be empty of them, which is worse than
        # the bug it was meant to fix. Which shots actually hold money in frame is
        # a reading of the action line, and belongs to a human.
        prop_map = d.PROP_FOR_NOT
        # Per-shot props, chosen by a human from the action line (see
        # PROPS_BY_SHOT). No getattr default: a missing map must fail loudly,
        # not silently attach nothing — that exact silence cost a whole feature
        # on 2026-09-22.
        for handle in d.PROPS_BY_SHOT.get(n, []):
            if handle not in [h for h, _ in chips]:
                chips.append((handle, ""))

        # The ceiling is Flow's, not ours. The Ultra audit (task-68653632,
        # 2026-09-18) read a reference-chip cap of 10 off the live product; the 3
        # written here before that was never sourced.
        if len(chips) > CHIP_CAP:
            raise SystemExit(f"shot {n}: {len(chips)} chips — Flow's cap is {CHIP_CAP}")
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
            # The voice description is restated on every single line on purpose.
            # A prompt governs only its own shot, so the voice is restated on
            # every line. (An earlier version of this comment claimed Flow cannot
            # save a custom voice at all — that was wrong and was corrected the
            # same day: the save button works once ตัวอย่างบทสนทนา is filled, and
            # five voices were saved that way on 2026-09-18.)
            # Hard failure, not a silent fallback. A character with no VOICE block
            # renders "speaks Thai, <direction>" and reads as a missing line only
            # if someone happens to look — @nong_daeng_suit slipped through
            # exactly that way on 2026-09-18.
            if sp not in getattr(d, "VOICE", {}):
                raise SystemExit(f"shot {n}: speaker {sp!r} has no VOICE block")
            voice = d.VOICE[sp][1]
            spoken = f"speaks Thai in {voice}, {direction}" if voice else f"speaks Thai, {direction}"
            out.append(f'{d.CHAR[sp][2]} <IMAGE_REF_{idx}> {spoken}, and says: "{line}"')
        out.append("")
        out.append("The face of whoever is speaking stays in frame for the whole line.")
        if nots:
            # A key that is also a CHARACTER key is a continuity rule for that
            # character ("she stays propped on the pillows, the cannula stays
            # on"), so it only means anything in a shot she is actually in. Ten
            # shots once listed "ya" intending to keep her OUT and were handed
            # her sickroom continuity instead: shot 65 rendered the son wearing
            # her nasal cannula at her bedside, and nine more were queued to do
            # the same, including Act 7, set a year after she dies. Exclusions
            # are spelled "no<character>" and carry no such trap.
            for k in nots:
                if k in d.CHAR and k not in chars:
                    sys.exit(
                        f"shot {n}: negatives list '{k}', which is {k}'s continuity "
                        f"rule, but {k} is not in this shot's cast {list(chars)}. "
                        f"That rule describes how {k} looks while present — emitting "
                        f"it here tells the model to put {k}'s wardrobe and equipment "
                        f"on whoever IS in frame. To keep {k} out, use 'no{k}'."
                    )
            out.append(" ".join(d.NOT[k] for k in nots))
        out.append(f"{framing}. {d.STYLE}")
        out.append("```")

    mins, secs = int(t) // 60, int(t) % 60
    out.insert(3, f"**{len(d.SHOTS)} ช็อต · {int(t)} วินาที = {mins}:{secs:02d} · "
                  f"~{total_cost} เครดิต ที่ 720p**\n")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    data, dest = Path(sys.argv[1]), Path(sys.argv[2])
    d = load(data)
    check_plates(d)
    m = re.search(r"ACT(\w+)", data.stem)
    dest.write_text(build(d, m.group(1) if m else "?"), encoding="utf-8")
    print(f"built {dest} from {data}")
