#!/usr/bin/env python3
"""tools/session_diagram.py — draw a session worktree as a diagram-design tree.

The `/session-worktree` skill reconstructs the session as a tree (entry problem
→ numbered work items → sub-steps, each with a status and a work-type tag).
This script takes that tree as JSON and renders it ONCE, deterministically, in
the visual system of the `diagram-design` skill (cathrynlavery/diagram-design
v2.6.17, vendored under ~/.claude/skills/diagram-design): default editorial
skin, Instrument Serif / Geist / Geist Mono (+ Noto Thai), 4px grid,
orthogonal connectors, legend strip, accessible-SVG contract.

Why a script and not the model drawing by hand: a hand-drawn diagram costs
~15 minutes of geometry per picture; the worktree runs many times per day.
The model writes the JSON (the same facts as the emoji tree), the script owns
the geometry — text and picture come from one source and cannot disagree.

Outputs, next to each other in --out-dir (default state/session-diagrams/),
under a STABLE basename — the session id — so a later run of the same session
overwrites the files and the Artifact tool republishes the same URL:
  <basename>.html            self-contained page (CSS + inline SVG, Google Fonts only)
  <basename>.artifact.html   the page body only (title + fonts + style + svg) —
                             what the Artifact tool wants; the skill publishes
                             this one and puts the link on its last line
                             (CEO 2026-09-09: the link, not a Telegram photo)
  <basename>.png             optional, --png: rendered with headless Chrome at
                             --scale (auto-lowered so Telegram's sendPhoto
                             w+h ≤ 10000 holds)

Flags:
  --print-tree      also print the 🌳 text tree in the skill's format
  --stamp           append -YYYYmmdd-HHMM to the default basename (archival copy)
  --send            opt-in: push the PNG (or HTML when no Chrome) to the CEO's
                    Telegram via lib.telegram_out.send_media_to_ceo — a real
                    file, never a link (CEO order #38). Not the default route.
  --check           run diagram-design's own scripts/self_check.py on the HTML
  --sample          print a sample JSON and exit (the schema, by example)

JSON shape (see --sample):
  {"session": "cto-1234abcd", "date": "YYYY-MM-DD",
   "entry_problem": "one sentence",
   "dod": [{"text": "...", "done": false}],
   "nodes": [{"id": "1", "status": "done|doing|todo|blocked", "type": "BUILD",
              "title": "...", "evidence": "sha:abc1234", "blocked_on": "...",
              "issue": 141, "children": [...]}],
   "close": {"status": "todo", "title": "Done · Close Session"}}

Exit codes: 0 rendered; 1 bad input; 2 --check failed; 3 --send failed.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = ROOT / "state" / "session-diagrams"
SKILL_DIR = Path.home() / ".claude" / "skills" / "diagram-design"

# ---- diagram-design default skin (references/style-guide.md) -----------------
PAPER = "#f5f5f5"
INK = "#2d3142"
MUTED = "#4f5d75"
SOFT = "#7a8399"
ACCENT = "#eb6c36"
ACCENT_TINT = "rgba(235,108,54,0.08)"
ACCENT_05 = "rgba(235,108,54,0.05)"
RULE = "rgba(45,49,66,0.12)"
INK_02 = "rgba(45,49,66,0.02)"
INK_05 = "rgba(45,49,66,0.05)"
INK_20 = "rgba(45,49,66,0.20)"
INK_40 = "rgba(45,49,66,0.40)"
FONT_SANS = "'Geist', 'Noto Sans Thai', system-ui, sans-serif"
FONT_SERIF = "'Instrument Serif', 'Noto Serif Thai', serif"
FONT_MONO = "'Geist Mono', 'Noto Sans Thai', ui-monospace, monospace"
FONT_LINK = (
    "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1"
    "&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600"
    "&family=Noto+Sans+Thai:wght@400;600&family=Noto+Serif+Thai:wght@400&display=swap"
)

STATUSES = ("done", "doing", "todo", "blocked")
STATUS_EMOJI = {"done": "✅", "doing": "🔄", "todo": "⬜", "blocked": "🔴"}
STATUS_WORD = {"done": "DONE", "doing": "DOING", "todo": "TODO", "blocked": "BLOCKED"}
TYPE_GLYPH = {
    "READ": "🔍", "RECON": "🔍", "RESEARCH": "📚", "ANALYZE": "🧠", "DECIDE": "🧠",
    "BUILD": "🔨", "FIX": "🔧", "DESIGN": "🎨", "SETUP": "⚙️", "TEST": "🧪",
    "VERIFY": "🧪", "SHIP": "🚀", "DOC": "📝", "CLOSE": "🏁",
}
# node treatment = SKILL.md §5 table + type-kanban.md card states
TREATMENT = {
    "done": dict(fill=INK_05, stroke=MUTED, dash=None),          # store
    "doing": dict(fill=ACCENT_TINT, stroke=ACCENT, dash=None),   # focal
    "todo": dict(fill=INK_02, stroke=INK_20, dash="4,3"),        # optional
    "blocked": dict(fill=ACCENT_05, stroke=ACCENT, dash="4,4"),  # security / blocked card
}
CHIP_COLOR = {"done": MUTED, "doing": ACCENT, "todo": SOFT, "blocked": ACCENT}

# ---- geometry (everything on the 4px grid) -----------------------------------
W = 880
M = 40
ROW_H = 48
ROW_GAP = 12
INDENT = 32
TREE_LEFT = M + 24          # x of a depth-0 box
DOD_ROW = 16
TELEGRAM_PHOTO_MAX_SUM = 10000   # sendPhoto: width + height ≤ 10000 px

SAMPLE = {
    "session": "cto-1234abcd",
    "date": "2026-09-08",
    "entry_problem": "ทำให้ /session-worktree ปิดท้ายด้วย diagram ภาพรวม session ที่ส่งถึง CEO ได้จริง",
    "dod": [
        {"text": "diagram-design ติดตั้งเป็น external skill", "done": True},
        {"text": "tools/session_diagram.py ผ่าน self_check + tests", "done": False},
    ],
    "nodes": [
        {"status": "done", "type": "SETUP", "title": "Clone diagram-design + symlink into ~/.claude/skills",
         "evidence": "pinned 2724fd2 · v2.6.17"},
        {"status": "doing", "type": "BUILD", "title": "Renderer: JSON → HTML/PNG in the diagram-design system",
         "children": [
             {"status": "done", "type": "READ", "title": "Read style-guide, type-tree, export refs"},
             {"status": "todo", "type": "TEST", "title": "self_check + unit tests green"},
         ]},
        {"status": "blocked", "type": "SHIP", "title": "Send picture to CEO from /session-worktree",
         "blocked_on": "Chrome บน Contabo ยังไม่มี", "issue": 0},
    ],
    "close": {"status": "todo", "title": "Done · Close Session"},
}


# ---- text metrics ------------------------------------------------------------
def _char_w(ch: str, mono: bool) -> float:
    """Advance width in em. Per character, never per script (style-guide.md)."""
    if unicodedata.combining(ch):
        return 0.0
    o = ord(ch)
    if o == 0x0E31 or 0x0E34 <= o <= 0x0E3A or 0x0E47 <= o <= 0x0E4E:
        return 0.0                                   # Thai marks not flagged as combining
    if o == 0x200B or o == 0xFE0F:
        return 0.0                                   # zero-width / variation selector
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 1.0
    if o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF:
        return 1.25                                  # emoji / symbols
    if 0x0E00 <= o <= 0x0E7F:
        return 0.62                                  # Thai base glyphs (Noto Sans Thai)
    return 0.62 if mono else 0.60


def text_width(s: str, size: float, mono: bool = False) -> float:
    return sum(_char_w(c, mono) for c in s) * size


def fit(s: str, size: float, max_w: float, mono: bool = False) -> str:
    """Truncate with an ellipsis so the text stays inside max_w."""
    if text_width(s, size, mono) <= max_w:
        return s
    ell = "…"
    out = ""
    for c in s:
        if text_width(out + c + ell, size, mono) > max_w:
            break
        out += c
    return out.rstrip() + ell


def wrap(s: str, size: float, max_w: float, max_lines: int) -> list[str]:
    """Greedy word wrap; a word wider than the line (Thai has no spaces) is
    broken by character. The last permitted line is truncated."""
    lines: list[str] = []
    cur = ""
    for word in s.split(" "):
        cand = (cur + " " + word).strip()
        if text_width(cand, size) <= max_w:
            cur = cand
            continue
        if cur:
            lines.append(cur)
            cur = ""
        while text_width(word, size) > max_w:      # break an over-long word
            piece = ""
            for c in word:
                if text_width(piece + c, size) > max_w:
                    break
                piece += c
            lines.append(piece)
            word = word[len(piece):]
        cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit(lines[-1] + "…", size, max_w)
    return lines or [""]


def up4(v: float) -> int:
    return int(-(-v // 4) * 4)


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


# ---- model -------------------------------------------------------------------
class Node:
    def __init__(self, raw: dict, nid: str, depth: int):
        self.id = nid
        self.depth = depth
        self.status = str(raw.get("status", "todo")).lower()
        if self.status not in STATUSES:
            raise ValueError(f"node #{nid}: status must be one of {STATUSES}, got {self.status!r}")
        self.type = str(raw.get("type", "BUILD")).upper().strip() or "BUILD"
        self.title = str(raw.get("title", "")).strip()
        if not self.title:
            raise ValueError(f"node #{nid}: title is required")
        self.evidence = str(raw.get("evidence") or "").strip()
        self.blocked_on = str(raw.get("blocked_on") or "").strip()
        issue = raw.get("issue")
        self.issue = int(issue) if issue not in (None, "", 0, "0") else None
        self.children = [
            Node(c, f"{nid}.{j + 1}" if not c.get("id") else str(c["id"]), depth + 1)
            for j, c in enumerate(raw.get("children") or [])
        ]
        if self.status == "blocked" and not self.blocked_on:
            self.blocked_on = "?"

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


class Session:
    def __init__(self, data: dict):
        if not isinstance(data, dict):
            raise ValueError("top level must be an object")
        self.entry_problem = str(data.get("entry_problem", "")).strip()
        if not self.entry_problem:
            raise ValueError("entry_problem is required")
        self.session = str(data.get("session") or _session_id_from_env() or "session")
        self.date = str(data.get("date") or datetime.now().strftime("%Y-%m-%d"))
        self.dod = [
            {"text": str(d.get("text", "")).strip(), "done": bool(d.get("done"))}
            for d in (data.get("dod") or []) if str(d.get("text", "")).strip()
        ]
        raw_nodes = data.get("nodes") or []
        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise ValueError("nodes must be a non-empty list")
        self.nodes = [
            Node(n, str(n.get("id") or i + 1), 0) for i, n in enumerate(raw_nodes)
        ]
        close = data.get("close") or {}
        all_done = all(n.status == "done" for top in self.nodes for n in top.walk())
        self.close = Node(
            {"status": close.get("status") or ("done" if all_done else "todo"),
             "type": "CLOSE", "title": close.get("title") or "Done · Close Session",
             "evidence": close.get("evidence", "")},
            str(close.get("id") or len(self.nodes) + 1), 0,
        )

    def all_nodes(self) -> list[Node]:
        out: list[Node] = []
        for top in self.nodes:
            out.extend(top.walk())
        out.append(self.close)
        return out

    def counts(self) -> dict:
        nodes = self.all_nodes()
        c = {s: sum(1 for n in nodes if n.status == s) for s in STATUSES}
        c["total"] = len(nodes)
        return c

    def type_tally(self) -> list[tuple[str, int]]:
        tally: dict[str, int] = {}
        for n in self.all_nodes():
            if n.type != "CLOSE":
                tally[n.type] = tally.get(n.type, 0) + 1
        return sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))

    def blockers(self) -> list[Node]:
        return [n for n in self.all_nodes() if n.status == "blocked"]


def _session_id_from_env() -> str | None:
    """`<role>-<id>` from the launcher env, e.g. cto-576f0aff. CXO_SESSION is a
    0/1 flag, not an id — the id lives in <ROLE>_SESSION_ID."""
    role = os.environ.get("CXO_ROLE", "").strip().lower()
    candidates = [f"{role.upper()}_SESSION_ID"] if role else []
    candidates += ["CXO_SESSION_ID", "CTO_SESSION_ID"]
    for var in candidates:
        v = os.environ.get(var, "").strip()
        if len(v) >= 4:
            return f"{role}-{v}" if role else v
    return None


# ---- text tree (the skill's 🌳 format) ----------------------------------------
def render_tree_text(s: Session) -> str:
    lines = [f"🌳 SESSION WORKTREE — {s.date}", f"🎯 main: {s.entry_problem}", "│"]

    def line(n: Node, prefix: str) -> str:
        glyph = TYPE_GLYPH.get(n.type, "🔨")
        out = f"{prefix}{STATUS_EMOJI[n.status]} #{n.id}  {glyph} {n.type:<7} — {n.title}"
        if n.evidence:
            out += f" ............. {n.evidence}"
        if n.status == "doing":
            out += "                ⬅️ อยู่ตรงนี้"
        if n.status == "blocked":
            out += f" · BLOCKED: รอ {n.blocked_on}"
            if n.issue:
                out += f" · GH#{n.issue}"
        return out

    def emit(nodes: list[Node], indent: str) -> None:
        for i, n in enumerate(nodes):
            last = i == len(nodes) - 1
            lines.append(line(n, indent + ("└─ " if last else "├─ ")))
            if n.children:
                emit(n.children, indent + ("   " if last else "│  "))

    emit(s.nodes, "")
    lines.append(line(s.close, "└─ "))
    c = s.counts()
    lines.append("")
    lines.append(f"📊 ✅ {c['done']}/{c['total']}   🔄 {c['doing']}   ⬜ {c['todo']}   🔴 {c['blocked']}")
    tally = s.type_tally()
    if c["total"] > 2 and tally:
        lines.append("📈 ตามชนิดงาน: " + " · ".join(
            f"{TYPE_GLYPH.get(t, '🔨')} {t} ×{k}" for t, k in tally))
    blockers = s.blockers()
    if blockers:
        lines.append("")
        lines.append(f"🔴 BLOCKERS ({len(blockers)})")
        for n in blockers:
            lines.append(f"  • #{n.id} — รอ {n.blocked_on}" + (f" · GH#{n.issue}" if n.issue else ""))
    return "\n".join(lines)


# ---- SVG ---------------------------------------------------------------------
def _text(x: float, y: float, s: str, size: float, fill: str, family: str, *,
          weight: str | None = None, anchor: str | None = None, ls: str | None = None,
          style: str | None = None) -> str:
    attrs = [f'x="{x:g}"', f'y="{y:g}"', f'fill="{fill}"', f'font-size="{size:g}"',
             f'font-family="{esc(family)}"']
    if weight:
        attrs.append(f'font-weight="{weight}"')
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    if ls:
        attrs.append(f'letter-spacing="{ls}"')
    if style:
        attrs.append(f'font-style="{style}"')
    return f"<text {' '.join(attrs)}>{esc(s)}</text>"


def _chip(x: int, y: int, label: str, color: str) -> tuple[str, int]:
    """Rectangular type tag (rx=2, never a pill). Returns (svg, width)."""
    w = max(28, up4(text_width(label, 8, mono=True) * 1.08 + 12))
    svg = (f'<rect x="{x}" y="{y}" width="{w}" height="12" rx="2" fill="transparent" '
           f'stroke="{color}" stroke-width="0.8"/>'
           + _text(x + w / 2, y + 9, label, 8, color, FONT_MONO, anchor="middle", ls="0.08em"))
    return svg, w


def render_svg(s: Session) -> tuple[str, int]:
    """Returns (svg markup, height). Draw order: bg → header → DoD → rule →
    connectors → nodes → legend (connectors before nodes, SKILL.md §6)."""
    parts: list[str] = []
    y = M

    # header — eyebrow + the entry problem as the headline
    parts.append(_text(M, y + 8, f"SESSION WORKTREE · {s.date} · {s.session}", 8, MUTED,
                       FONT_MONO, ls="0.18em"))
    y += 40
    head_lines = wrap(s.entry_problem, 24, W - 2 * M, 3)
    for i, ln in enumerate(head_lines):
        parts.append(_text(M, y + i * 28, ln, 24, INK, FONT_SERIF))
    y += (len(head_lines) - 1) * 28 + 24

    # definition of done (optional)
    if s.dod:
        parts.append(_text(M, y, "DEFINITION OF DONE", 8, MUTED, FONT_MONO, ls="0.18em"))
        y += 12
        for d in s.dod:
            fill = INK if d["done"] else "transparent"
            parts.append(f'<rect x="{M}" y="{y}" width="8" height="8" rx="1" fill="{fill}" '
                         f'stroke="{INK}" stroke-width="0.8"/>')
            parts.append(_text(M + 16, y + 8, fit(d["text"], 11, W - 2 * M - 16), 11,
                               MUTED if d["done"] else INK, FONT_SANS))
            y += DOD_ROW
        y += 8

    # rule between header and tree
    y_rule = up4(y)
    parts.append(f'<line x1="{M}" y1="{y_rule}" x2="{W - M}" y2="{y_rule}" stroke="{RULE}" stroke-width="0.8"/>')
    y = y_rule + 20

    # place nodes
    placed: list[tuple[Node, int]] = []   # (node, y)
    order: list[Node] = []
    for top in s.nodes:
        order.extend(top.walk())
    order.append(s.close)
    for n in order:
        placed.append((n, y))
        y += ROW_H + ROW_GAP
    ypos = {n.id: yy for n, yy in placed}

    def x0(depth: int) -> int:
        return TREE_LEFT + depth * INDENT

    # connectors — a vertical spine per parent, T-stubs into each child, and a
    # rounded r=8 elbow into the last child (orthogonal, never diagonal)
    conn: list[str] = []

    def spine(xs: int, y_from: int, children: list[Node], depth: int) -> None:
        if not children:
            return
        xt = x0(depth)
        last_mid = ypos[children[-1].id] + ROW_H // 2
        conn.append(f'<path d="M {xs},{y_from} V {last_mid - 8} Q {xs},{last_mid} {xs + 8},{last_mid} H {xt}" '
                    f'fill="none" stroke="{MUTED}" stroke-width="1"/>')
        for c in children[:-1]:
            mid = ypos[c.id] + ROW_H // 2
            conn.append(f'<line x1="{xs}" y1="{mid}" x2="{xt}" y2="{mid}" stroke="{MUTED}" stroke-width="1"/>')

    spine(TREE_LEFT - 16, y_rule, s.nodes + [s.close], 0)
    for n in order:
        if n.children:
            spine(x0(n.depth) + 16, ypos[n.id] + ROW_H, n.children, n.depth + 1)
    parts.extend(conn)

    # node boxes
    for n, yy in placed:
        x = x0(n.depth)
        w = W - M - x
        t = TREATMENT[n.status]
        dash = f' stroke-dasharray="{t["dash"]}"' if t["dash"] else ""
        parts.append(f'<rect x="{x}" y="{yy}" width="{w}" height="{ROW_H}" rx="6" fill="{PAPER}"/>')
        parts.append(f'<rect x="{x}" y="{yy}" width="{w}" height="{ROW_H}" rx="6" fill="{t["fill"]}" '
                     f'stroke="{t["stroke"]}" stroke-width="1"{dash}/>')
        cx = x + 12
        if n.status == "blocked":
            parts.append(f'<rect x="{x + 4}" y="{yy + 8}" width="4" height="32" rx="1" fill="{ACCENT}"/>')
            cx = x + 16
        chip_svg, cw = _chip(cx, yy + 12, STATUS_WORD[n.status], CHIP_COLOR[n.status])
        parts.append(chip_svg)
        cx += cw + 4
        chip_svg, cw = _chip(cx, yy + 12, n.type, INK_40 if n.status != "doing" else MUTED)
        parts.append(chip_svg)
        cx += cw + 8
        nid = f"#{n.id}"
        parts.append(_text(cx, yy + 22, nid, 9, MUTED, FONT_MONO))
        cx += up4(text_width(nid, 9, mono=True) + 8)
        right_pad = 12
        if n.status == "doing":
            here = "◀ HERE"
            right_pad += up4(text_width(here, 8, mono=True) * 1.1 + 16)
            parts.append(_text(x + w - 12, yy + 22, here, 8, ACCENT, FONT_MONO, anchor="end", ls="0.12em"))
        title_w = x + w - right_pad - cx
        parts.append(_text(cx, yy + 22, fit(n.title, 12, title_w), 12, INK, FONT_SANS, weight="600"))
        sub = ""
        sub_color = MUTED
        if n.status == "blocked":
            sub = f"BLOCKED · รอ {n.blocked_on}" + (f" · GH#{n.issue}" if n.issue else "")
            sub_color = ACCENT
        elif n.evidence:
            sub = n.evidence
        if sub:
            parts.append(_text(x + 12, yy + 38, fit(sub, 9, w - 24, mono=True), 9, sub_color, FONT_MONO))

    # legend strip + counts
    y = placed[-1][1] + ROW_H + 28
    parts.append(f'<line x1="{M}" y1="{y}" x2="{W - M}" y2="{y}" stroke="{RULE}" stroke-width="0.8"/>')
    parts.append(_text(M, y + 16, "LEGEND", 8, MUTED, FONT_MONO, ls="0.18em"))
    c = s.counts()
    parts.append(_text(W - M, y + 16,
                       f"{c['done']}/{c['total']} DONE · {c['doing']} DOING · {c['todo']} TODO · {c['blocked']} BLOCKED",
                       8, MUTED, FONT_MONO, anchor="end", ls="0.08em"))
    sw_y = y + 32
    lx = M
    for status, label in (("done", "Done"), ("doing", "Doing · here"), ("todo", "Not started"), ("blocked", "Blocked")):
        t = TREATMENT[status]
        dash = f' stroke-dasharray="{t["dash"]}"' if t["dash"] else ""
        parts.append(f'<rect x="{lx}" y="{sw_y}" width="16" height="12" rx="2" fill="{t["fill"]}" '
                     f'stroke="{t["stroke"]}" stroke-width="1"{dash}/>')
        parts.append(_text(lx + 24, sw_y + 9, label, 9, MUTED, FONT_SANS))
        lx += 24 + up4(text_width(label, 9) + 40)
    tally = s.type_tally()
    if tally:
        parts.append(_text(W - M, sw_y + 9, " · ".join(f"{t} ×{k}" for t, k in tally), 8, SOFT,
                           FONT_MONO, anchor="end", ls="0.06em"))
    h = up4(sw_y + 12 + 20)

    desc = (f"Session worktree: {c['done']} of {c['total']} work items done, {c['doing']} in progress, "
            f"{c['blocked']} blocked, for the entry problem: {s.entry_problem}")
    svg = (f'<svg viewBox="0 0 {W} {h}" width="{W}" height="{h}" xmlns="http://www.w3.org/2000/svg" '
           f'role="img" aria-labelledby="session-tree-title session-tree-desc">\n'
           f'<title id="session-tree-title">{esc(fit(s.entry_problem, 12, 700))}</title>\n'
           f'<desc id="session-tree-desc">{esc(desc)}</desc>\n'
           f'<defs></defs>\n<rect width="100%" height="100%" fill="{PAPER}"/>\n'
           + "\n".join(parts) + "\n</svg>")
    return svg, h


def render_html(s: Session) -> tuple[str, int]:
    svg, h = render_svg(s)
    title = esc(f"Session worktree · {s.date} · {s.session}")
    page = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link href="{FONT_LINK}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ background: {PAPER}; }}
    body {{ width: {W}px; color: {INK}; font-family: {FONT_SANS}; }}
    svg {{ display: block; width: {W}px; height: {h}px; }}
  </style>
</head>
<body>
{svg}
</body>
</html>
"""
    return page, h


def render_artifact_html(s: Session) -> str:
    """Page body for the Artifact tool — no doctype/html/head/body (the tool
    wraps it). Responsive: the SVG scales with the viewport via its viewBox."""
    svg, _h = render_svg(s)
    title = esc(f"Session worktree · {s.date} · {s.session}")
    return f"""<title>{title}</title>
<link href="{FONT_LINK}" rel="stylesheet">
<style>
  body {{ margin: 0; padding: 24px 16px; background: {PAPER}; color: {INK}; font-family: {FONT_SANS}; }}
  .frame {{ max-width: {W}px; margin: 0 auto; }}
  .frame svg {{ display: block; width: 100%; height: auto; }}
</style>
<div class="frame">
{svg}
</div>
"""


def default_basename(s: Session, stamp: bool = False) -> str:
    """Stable per session (so republishing keeps one Artifact URL); --stamp for an archival copy."""
    return f"{s.session}-{datetime.now().strftime('%Y%m%d-%H%M')}" if stamp else s.session


# ---- PNG via headless Chrome ---------------------------------------------------
CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium",
)


def find_chrome(explicit: str | None = None) -> str | None:
    for cand in ([explicit] if explicit else []) + [os.environ.get("SESSION_DIAGRAM_CHROME", "")] + list(CHROME_CANDIDATES):
        if not cand:
            continue
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return None


def render_png(html_path: Path, png_path: Path, h: int, scale: int, chrome: str, timeout: float = 40.0) -> Path | None:
    """Screenshot the page at exactly W×h CSS px. Chrome on macOS keeps running
    after writing the file (its updater/keystone child), so poll for the PNG
    and terminate the process instead of waiting for it to exit."""
    profile = tempfile.mkdtemp(prefix="session-diagram-chrome-")
    if png_path.exists():
        png_path.unlink()
    cmd = [chrome, f"--user-data-dir={profile}", "--headless", "--no-first-run", "--disable-gpu",
           "--hide-scrollbars", "--disable-background-networking", "--disable-component-update",
           "--disable-sync", "--disable-default-apps", "--no-default-browser-check", "--disable-extensions",
           f"--force-device-scale-factor={scale}", f"--window-size={W},{h}", "--virtual-time-budget=8000",
           f"--screenshot={png_path}", html_path.resolve().as_uri()]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.insert(1, "--no-sandbox")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + timeout
    last, stable = -1, 0
    try:
        while time.time() < deadline:
            size = png_path.stat().st_size if png_path.exists() else 0
            if size > 0:
                stable = stable + 1 if size == last else 0
                last = size
                if stable >= 2 or proc.poll() is not None:
                    break
            elif proc.poll() is not None:
                break
            time.sleep(0.25)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(profile, ignore_errors=True)
    return png_path if png_path.exists() and png_path.stat().st_size > 0 else None


def photo_scale(requested: int, h: int) -> int:
    """Largest scale ≤ requested that keeps width+height within Telegram's sendPhoto cap."""
    scale = max(1, requested)
    while scale > 1 and scale * (W + h) > TELEGRAM_PHOTO_MAX_SUM:
        scale -= 1
    return scale


# ---- self-check via diagram-design's own validator ----------------------------
def self_check(html_path: Path) -> tuple[bool, str]:
    script = SKILL_DIR / "scripts" / "self_check.py"
    if not script.is_file():
        return True, f"self_check skipped (no {script})"
    r = subprocess.run([sys.executable, str(script), str(html_path)], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


# ---- CLI ---------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render a session worktree JSON as a diagram-design tree.")
    ap.add_argument("input", nargs="?", help="session JSON file ('-' = stdin)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--basename", help="output basename (default: the session id, stable across runs)")
    ap.add_argument("--stamp", action="store_true", help="append -YYYYmmdd-HHMM to the default basename")
    ap.add_argument("--png", action="store_true", help="also render a PNG with headless Chrome")
    ap.add_argument("--scale", type=int, default=2, help="device scale factor for the PNG (default 2)")
    ap.add_argument("--chrome", help="path to a Chrome/Chromium binary")
    ap.add_argument("--print-tree", action="store_true", help="print the 🌳 text tree first")
    ap.add_argument("--send", action="store_true", help="send the PNG (or HTML) to the CEO's Telegram")
    ap.add_argument("--check", action="store_true", help="run diagram-design's self_check.py on the HTML")
    ap.add_argument("--sample", action="store_true", help="print a sample JSON and exit")
    args = ap.parse_args(argv)

    if args.sample:
        print(json.dumps(SAMPLE, ensure_ascii=False, indent=2))
        return 0
    if not args.input:
        ap.error("input JSON required (or --sample)")
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        session = Session(json.loads(raw))
    except (OSError, ValueError, TypeError) as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 1

    if args.print_tree:
        print(render_tree_text(session))
        print("---")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = args.basename or default_basename(session, args.stamp)
    html_path = out_dir / f"{base}.html"
    if args.input == "-":                       # keep the stdin JSON next to the outputs
        (out_dir / f"{base}.json").write_text(raw, encoding="utf-8")
        print(f"json: {out_dir / f'{base}.json'}")
    page, h = render_html(session)
    html_path.write_text(page, encoding="utf-8")
    print(f"html: {html_path}")
    artifact_path = out_dir / f"{base}.artifact.html"
    artifact_path.write_text(render_artifact_html(session), encoding="utf-8")
    print(f"artifact: {artifact_path}")

    rc = 0
    if args.check:
        ok, msg = self_check(html_path)
        print(f"check: {'OK' if ok else 'FAIL'} — {msg}")
        if not ok:
            rc = 2

    png_path: Path | None = None
    if args.png:
        chrome = find_chrome(args.chrome)
        if not chrome:
            print("png: skipped — no Chrome/Chromium found (set SESSION_DIAGRAM_CHROME or --chrome)")
        else:
            scale = photo_scale(args.scale, h)
            png_path = render_png(html_path, out_dir / f"{base}.png", h, scale, chrome)
            print(f"png: {png_path} (scale {scale})" if png_path else "png: FAILED — Chrome produced no file")

    if args.send:
        sys.path.insert(0, str(ROOT))
        from lib.telegram_out import send_media_to_ceo  # noqa: E402
        c = session.counts()
        caption = (f"🌳 {session.date} · {session.session} — ✅ {c['done']}/{c['total']} · 🔄 {c['doing']} · 🔴 {c['blocked']}\n"
                   f"🎯 {session.entry_problem[:300]}")
        target = png_path or html_path
        res = send_media_to_ceo(str(target), caption)
        print(f"telegram: {'ok' if res.get('ok') else 'FAILED — ' + str(res.get('reason'))} ({target.name})")
        if not res.get("ok"):
            rc = rc or 3
    print(f"diagram: {png_path or html_path}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
