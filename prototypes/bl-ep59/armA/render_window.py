#!/usr/bin/env python3
"""bl_compose for EP59 arm A, plus the things arm A's brief asks for that the tool does not do (task-4305b93b, EP58; reused here, task-2db3174c).

tools/ is not edited. This wrapper imports tools.bl_compose and wraps two of its functions for the length of one run:
  - apply_arm_a: after the CTO's plate/bug override, add (1) the date stamp under the headline, (2) a dark backing
    under the plate (SKILL.md §6d traps: text over a bright real page needs its own opaque backing; the plate has
    only an outline), both in the RENDER workdir's index.html only.
  - emit_pieces: an EVID beat with extra.shift is lifted that many px (bl_compose lifts COMP only). Used for MAIN-13,
    whose contents line sits at y 1835, in TikTok's bottom UI zone. The spotlight box is moved with the page.
Everything else is bl_compose.main() unchanged: same arguments, same range render, same output.

    python3 prototypes/bl-ep59/armA/render_window.py --beats prototypes/bl-ep59/armA/beats.json \
        --generator-dir /opt/MoonieXHQ/Work/bl-ep59/generator --t0 9.0667 --t-max 16.6 --out-dir <build> --out <part.mp4>

ARMA_SCRIM=0 turns the backing off (for a before/after look).
"""
import copy
import os
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools import bl_compose as bc  # noqa: E402

STAMP_TEXT = "ข้อมูลจาก Facebook + WikiFX ณ 1 ต.ค. 2569"   # CMO text for EP59; SKILL §6e: the brands' real spelling on screen
STAMP_TOP = 484          # plate text ends at y 474 (headline_layout)
SCRIM_SOLID, SCRIM_END = 490, 560

STAMP_CSS = (
    '<style id="arm-a-stamp">'
    '.hl-date{position:absolute;left:120px;width:840px;z-index:38;text-align:center;white-space:nowrap;'
    'font-family:Kanit,sans-serif;font-weight:600;font-size:26px;line-height:34px;color:var(--white)}'
    '.hl-date span{display:inline-block;padding:3px 18px 5px;border-radius:10px;background:rgba(7,8,10,.80)}'
    '.hl-scrim{position:absolute;left:0;top:0;width:1080px;z-index:36;pointer-events:none}'
    '</style>\n')


def stamp_html() -> str:
    return (f'<div id="hl-date" class="hl-date" style="top:{STAMP_TOP}px;height:40px">'
            f'<span>{escape(STAMP_TEXT)}</span></div>')


def scrim_html() -> str:
    return (f'<div id="hl-scrim" class="hl-scrim" style="height:{SCRIM_END}px;background:linear-gradient(to bottom,'
            f'rgba(7,8,10,.9) 0,rgba(7,8,10,.9) {SCRIM_SOLID}px,rgba(7,8,10,0) {SCRIM_END}px)"></div>')


_orig_apply = bc.apply_arm_a


def apply_arm_a_plus(html: str, headline: dict) -> str:
    out = _orig_apply(html, headline)
    if out.count("</head>") != 1 or out.count('<div id="hl" ') != 1:
        raise bc.ComposeError("arm A render wrapper: the composed page lost its </head> or its plate; not placing the stamp")
    out = out.replace("</head>", STAMP_CSS + "</head>")
    scrim = "" if os.environ.get("ARMA_SCRIM") == "0" else scrim_html() + "\n      "
    return out.replace('<div id="hl" ', scrim + '<div id="hl" ', 1).replace(
        '<div class="bug" id="bug">', stamp_html() + "\n      " + '<div class="bug" id="bug">', 1)


_orig_emit = bc.emit_pieces


def emit_pieces_evid_shift(beats, t_max, funcs, *args, **kw):
    lifted = {b["tag"]: b["extra"]["shift"] for b in beats
              if b["mode"] == "EVID" and (b.get("extra") or {}).get("shift")}
    if not lifted:
        return _orig_emit(beats, t_max, funcs, *args, **kw)
    beats2 = copy.deepcopy(beats)
    for b in beats2:
        if b["tag"] in lifted:
            ex = b["extra"]
            if ex.get("box"):
                x, y, w, h = ex["box"]
                ex["box"] = [x, y - ex["shift"], w, h]    # native coordinates of the lifted page: spotlight follows it
            ex.pop("shift")
    pieces = _orig_emit(beats2, t_max, funcs, *args, **kw)
    for tag, shift in lifted.items():
        pid = f'id="v_{tag.lower().replace("-", "")}"'
        hits = [i for i, p in enumerate(pieces["plates"]) if pid in p]
        for i in hits:
            if "top:0px;" not in pieces["plates"][i]:
                raise bc.ComposeError(f"EVID shift: plate of {tag} has no top:0px to lift: {pieces['plates'][i][:120]}")
            pieces["plates"][i] = pieces["plates"][i].replace("top:0px;", f"top:{-shift}px;", 1)
    return pieces


bc.apply_arm_a = apply_arm_a_plus
bc.emit_pieces = emit_pieces_evid_shift

if __name__ == "__main__":
    try:
        raise SystemExit(bc.main())
    except bc.ArmAError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(2)
    except bc.ComposeError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)
