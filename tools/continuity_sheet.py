#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Continuity sheet + pre-shoot flags for a Flow shot-sheet film — read before paying.

    python3 tools/continuity_sheet.py docs/scripts/banchi-ACT*.data.py [--out FILE.md]

Built 2026-09-23 from «จุดจบของเจ้าหนี้นอกระบบ» (banchi), where every one of these
cost a re-shoot that a table would have caught for free. It reads the same
`*.data.py` files `tools/build_shotsheet.py` renders, prints one row per shot
(time · place · who · wearing what · props) and a TRANSITION line wherever the
place or the time changes, then flags what the film taught us to fear.

Which flags are Flow-specific is said in the skill that owns this tool
(`CTO_Flow_Omni1.1_Continuity`). Measured on Google Flow · Omni 1.1 Flash
(องค์ประกอบ mode, 720p 9:16); on another generator they are hypotheses.

Flags (each names the shot):
  NIGHT-ON-DAY-PLATE  night/dusk/dawn/evening written over a location whose plate is
                      not a night plate — "night" lost to a daylight plate in all 71 shop
                      shots; the alley, whose plate IS night, came out dark.
  SICKBED             a healthy character staged on/at a patient's bed — ต้น got the
                      grandmother's nasal cannula every time he sat or lay on her bed.
  FLOW-DELETES        handcuffs anywhere; a uniformed character next to police lights;
                      the word "police" with a uniform — Flow deleted all of these
                      silently (11-arm A/B, google-flow-ops).
  FAST-LINE           > 10 Thai characters a second — shot 43 (10.5/s) burned a caption
                      three times at 6 s and was clean at 8 s.
  INAUDIBLE-SPEECH    "to himself", "under his breath", "whispered", "barely audible" —
                      two of the three captioned shots described speech meant not to
                      be heard.
  REF1-CLOSEUP        a close-up two-shot: whoever is second in the cast is REF_1 and,
                      in profile, lost his plate (hair in 106, a shirt in 149/150).

It never edits a data file and never spends anything. A flag is a question for the
person writing the sheet, not a verdict.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

THAI = re.compile(r"[฀-๿]")
NIGHTISH = re.compile(r"\b(night|dusk|dawn|evening|before dawn)\b", re.I)
INAUDIBLE = re.compile(r"to himself|to herself|under (his|her) breath|whisper|barely audible", re.I)
CUFFS = re.compile(r"handcuff|cuffed|\bcuffs\b", re.I)
LIGHTS = re.compile(r"light bar|red[- ]and[- ]blue|red and blue|siren|patrol", re.I)
NOBODY = re.compile(r"\b(nobody|no one|never)\b[^,;.]*", re.I)
ONBED = re.compile(r"\b(on|onto) (the|her|his) (edge of the )?bed\b|\blies\b|\blying\b|sits on the bed|on the bed", re.I)


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_").replace(".", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_night_plate(handle: str, desc: str) -> bool:
    return "night" in handle.lower() or bool(re.search(r"\bat night\b|\bnight\b", desc[:160], re.I))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data", nargs="+", type=Path)
    ap.add_argument("--patients", default="ya", help="CHAR keys who are bed-bound (default: ya)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    patients = set(args.patients.split(","))

    rows, flags, prev = [], [], None
    for path in args.data:
        d = load(path)
        act = re.search(r"ACT(\d+)", path.name)
        act = act.group(1) if act else "?"
        wardrobe = getattr(d, "WARDROBE", {})
        for (n, dur, framing, chars, lockey, tod, action, lines, nots) in d.SHOTS:
            lochandle, locdesc = d.LOC[lockey]
            who = []
            for c in chars:
                w = f" +{wardrobe[c]}" if c in wardrobe else ""
                who.append(f"{c}({d.CHAR[c][0]}{w})")
            place = (lochandle, tod)
            if prev and place != prev[0]:
                rows.append(f"| | **TRANSITION** {prev[0][0]} · {prev[0][1]} → {lochandle} · {tod} | | | |")
            prev = (place, n)
            rows.append(f"| {act} | {n} · {dur}s · {tod} · {lochandle} | {', '.join(who)} | {', '.join(nots) or '-'} | {action[:70]} |")

            text = " ".join([action] + [l for _, _, l in lines])
            descs = " ".join(d.CHAR[c][1] for c in chars)
            if NIGHTISH.search(tod) and not is_night_plate(lochandle, locdesc):
                flags.append((n, "NIGHT-ON-DAY-PLATE", f"'{tod}' on {lochandle}, whose plate is not a night plate"))
            staged = NOBODY.sub("", action)   # "nobody lies on the bed" is the fix, not the fault
            if lockey in ("room", "bedrail") and (set(chars) - patients) and ONBED.search(staged):
                flags.append((n, "SICKBED", "a healthy character is staged on/at the patient's bed — stage a chair beside it"))
            # the text and a cuffs NOT key — never the NOT *text*: NOT["nocuffs"] is the
            # prohibition ("No handcuffs…") and flagged shot 156 on its first run.
            if CUFFS.search(text) or "cuffed" in nots:
                flags.append((n, "FLOW-DELETES", "handcuffs — Flow deleted every take with them"))
            uniformed = any(c in wardrobe or "uniform" in d.CHAR[c][1].lower() for c in chars)
            if uniformed and LIGHTS.search(text):
                flags.append((n, "FLOW-DELETES", "uniformed character + police lights"))
            if uniformed and re.search(r"\bpolice\b", text + " " + descs, re.I):
                flags.append((n, "FLOW-DELETES", "the word 'police' with a uniform — describe the clothes, not the institution"))
            chars_n = sum(len(THAI.findall(l)) for _, _, l in lines)
            if dur and chars_n / dur > 10:
                flags.append((n, "FAST-LINE", f"{chars_n / dur:.1f} Thai chars/s in {dur}s — lengthen the shot or cut words"))
            if INAUDIBLE.search(action) or any(INAUDIBLE.search(t) for _, t, _ in lines):
                flags.append((n, "INAUDIBLE-SPEECH", "speech meant not to be heard invites burned captions"))
            if len(chars) >= 2 and framing.lower().startswith("close"):
                flags.append((n, "REF1-CLOSEUP", f"{chars[1]} is REF_1 in a close-up — put the character the shot is about first, faces 3/4 to camera"))

    out = ["# Continuity sheet", "", "| act | shot · s · time · place | who (plate +wardrobe) | NOT | action |",
           "|---|---|---|---|---|"] + rows
    out += ["", f"## Flags ({len(flags)})", ""]
    out += [f"- shot {n} · **{kind}** — {why}" for n, kind, why in flags] or ["- none"]
    text = "\n".join(out) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    kinds = {}
    for _, k, _ in flags:
        kinds[k] = kinds.get(k, 0) + 1
    print(f"{len(rows)} rows, {len(flags)} flags: {kinds}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
