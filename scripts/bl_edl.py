#!/usr/bin/env python3
"""bl_edl.py — shared pure functions for the BLACK LIQUIDITY layered EDL.

Schema: .claude/skills/blackliquidity-cut/edl/SCHEMA.md
Used by both scripts/bl_compose.py (layers -> index.html, P1 only) and
scripts/bl_check.py (the P1 gate). Kept in one place so the two tools can
never disagree about what a valid P1 event looks like.

Stdlib only, on purpose — a test file importing anything requirements.txt
does not have stops CI collection for every session (evidence: 47f9d942).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class EDLError(Exception):
    """A structural defect in an EDL layer — always fatal, never silently
    ignored. Every raise site names the offending event id so a worker does
    not have to bisect the file by hand."""


ROLES = {"avatar", "scene", "broll", "real_still", "real_clip"}
REAL_ROLES = {"real_still", "real_clip"}
DARKEN_LEGAL_ROLES = {"scene", "broll"}
AVATAR_MODES = {"full", "composite", "none"}
PLATE_KINDS = {"video", "image"}

SKILL_DIR = Path(__file__).resolve().parents[1] / ".claude/skills/blackliquidity-cut"
DEFAULT_TEMPLATE = SKILL_DIR / "template" / "index.html"
DEFAULT_REGISTRY = SKILL_DIR / "edl" / "event_types.json"

# The avatar composite's own box, §6d of SKILL.md: CSS is bottom-anchored,
# height 56% of the 1920 canvas (top edge at 44.2% +/- 3.1, so y=845), left
# edge at x=0 (`.avatar-comp { left:0; ... transform: translateX(-6%) }`).
# The measured x-center of the actual body mass is ~37% (~400px); this box's
# right edge is set wider than that on purpose -- a HARD safety check should
# err toward catching a real overlap over missing one, not toward the
# tightest box that fits the average frame.
AVATAR_BOX = {"x0": 0, "y0": 845, "x1": 480, "y1": 1920}


# --------------------------------------------------------------- loading
def load_json(path: Path) -> dict:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise EDLError(f"{path}: not found")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise EDLError(f"{path}: invalid JSON -- {e}")


def load_registry(path: Path | None = None) -> dict[str, Any]:
    doc = load_json(path or DEFAULT_REGISTRY)
    return doc.get("types", {})


# ------------------------------------------------------------- P1 shape
def validate_p1(doc: dict) -> None:
    """Raise EDLError on the first structural defect in a P1 layer.

    This is the shape a compose can trust enough to render: required fields,
    legal enum values, and the avatar_mode/role combinations §6d allows. It
    does NOT check timeline coverage, media existence, lipsync-offset math,
    or the evidence-box rule -- those need a media root and/or the whole
    event list at once and live in bl_check.py's P1 gate (deliverable 3).
    """
    for key in ("episode", "duration", "audio", "events"):
        if key not in doc:
            raise EDLError(f"p1: missing top-level '{key}'")
    if "media" not in doc["audio"]:
        raise EDLError("p1: audio.media missing")
    if not isinstance(doc["events"], list) or not doc["events"]:
        raise EDLError("p1: events must be a non-empty list")

    offsets = doc.get("lipsync_offsets", {})
    seen_ids: set[str] = set()
    for ev in doc["events"]:
        if "id" not in ev:
            raise EDLError("p1: event missing 'id'")
        eid = ev["id"]
        if eid in seen_ids:
            raise EDLError(f"p1 {eid}: duplicate id")
        seen_ids.add(eid)
        for key in ("t0", "t1", "type", "params"):
            if key not in ev:
                raise EDLError(f"p1 {eid}: missing '{key}'")
        if ev["type"] != "plate":
            raise EDLError(f"p1 {eid}: unknown type '{ev['type']}' -- P1 has exactly one type, 'plate'")
        if not (ev["t0"] < ev["t1"]):
            raise EDLError(f"p1 {eid}: t0 {ev['t0']} must be < t1 {ev['t1']}")

        p = ev["params"]
        role = p.get("role")
        if role not in ROLES:
            raise EDLError(f"p1 {eid}: unknown role '{role}'")
        kind = p.get("kind")
        if kind not in PLATE_KINDS:
            raise EDLError(f"p1 {eid}: unknown kind '{kind}'")
        if "media" not in p:
            raise EDLError(f"p1 {eid}: params.media missing")
        mode = p.get("avatar_mode")
        if mode not in AVATAR_MODES:
            raise EDLError(f"p1 {eid}: unknown avatar_mode '{mode}'")

        if role == "avatar":
            if mode != "full":
                raise EDLError(f"p1 {eid}: role 'avatar' requires avatar_mode 'full', got '{mode}'")
            if not p.get("lipsync_part"):
                raise EDLError(f"p1 {eid}: role 'avatar' requires params.lipsync_part")
        else:
            if mode == "full":
                raise EDLError(f"p1 {eid}: avatar_mode 'full' is only legal on role 'avatar' (§6d: composite only over a plate)")
            if mode == "composite":
                av = p.get("avatar")
                if not av or "media" not in av:
                    raise EDLError(f"p1 {eid}: avatar_mode 'composite' requires params.avatar.media")
                if not av.get("lipsync_part") and "media_start" not in av:
                    raise EDLError(f"p1 {eid}: params.avatar needs lipsync_part or media_start")
            if mode == "none" and p.get("avatar"):
                raise EDLError(f"p1 {eid}: avatar_mode 'none' must not carry params.avatar")
            if "lipsync_part" not in p and "media_start" not in p:
                raise EDLError(f"p1 {eid}: role '{role}' needs params.media_start")

        if p.get("darken") and role not in DARKEN_LEGAL_ROLES:
            raise EDLError(
                f"p1 {eid}: darken=true is illegal on role '{role}' "
                f"(only scene/broll -- §6d: real footage must stay legible, never darkened)")
        if role in REAL_ROLES and not p.get("real_source"):
            raise EDLError(f"p1 {eid}: role '{role}' requires params.real_source")


# --------------------------------------------------------- lipsync seating
def p1_media_start(ev: dict, offsets: dict) -> float:
    """The seek offset into a plate's own media file. `bl_tools.py offsets`
    finds the one true offset per lipsync part; this is the formula that
    turns it into a seek position, so an author never writes it by hand:
    media_start = t0 - offsets[part]."""
    p = ev["params"]
    part = p.get("lipsync_part")
    if part is not None:
        if part not in offsets:
            raise EDLError(f"p1 {ev['id']}: lipsync_part '{part}' has no entry in lipsync_offsets")
        return round(ev["t0"] - offsets[part], 3)
    return round(float(p["media_start"]), 3)


def p1_avatar_media_start(ev: dict, offsets: dict) -> float:
    av = ev["params"]["avatar"]
    part = av.get("lipsync_part")
    if part is not None:
        if part not in offsets:
            raise EDLError(f"p1 {ev['id']}: avatar lipsync_part '{part}' has no entry in lipsync_offsets")
        return round(ev["t0"] - offsets[part], 3)
    return round(float(av["media_start"]), 3)


def check_lipsync_seating(events: list[dict], offsets: dict) -> list[str]:
    """'Lipsync parts are seated continuously' (deliverable 3): a part can
    only be seated at a media position that has actually started playing by
    that point in the master clock. media_start = t0 - offsets[part]; if
    that is negative, the event asks to show a part of the file that, per
    its own measured offset, has not begun yet at this event's t0 -- a real,
    catchable seating defect, not a tautology of the derivation formula."""
    problems = []
    for ev in events:
        p = ev["params"]
        uses = []
        if p.get("lipsync_part"):
            uses.append(("plate", p["lipsync_part"], p1_media_start))
        if p.get("avatar_mode") == "composite" and p.get("avatar", {}).get("lipsync_part"):
            uses.append(("avatar", p["avatar"]["lipsync_part"], p1_avatar_media_start))
        for where, part, fn in uses:
            if part not in offsets:
                problems.append(f"{ev['id']} ({where}): lipsync part '{part}' has no entry in lipsync_offsets")
                continue
            ms = fn(ev, offsets)
            if ms < -1e-6:
                problems.append(
                    f"{ev['id']} ({where}): part '{part}' would seat at media_start {ms:.3f}s (<0) -- "
                    f"its own offset {offsets[part]:.2f}s is later than this event's t0 {ev['t0']:.2f}s")
    return problems


# ------------------------------------------------------------- coverage
def check_coverage(events: list[dict], duration: float) -> list[str]:
    """'Every second of the voice track is covered, with no overlaps or
    gaps' (deliverable 3)."""
    problems = []
    evs = sorted(events, key=lambda e: e["t0"])
    cur = 0.0
    for ev in evs:
        if ev["t0"] > cur + 1e-6:
            problems.append(f"gap {cur:.3f}s-{ev['t0']:.3f}s before {ev['id']}")
        elif ev["t0"] < cur - 1e-6:
            problems.append(f"overlap: {ev['id']} starts at {ev['t0']:.3f}s, {cur - ev['t0']:.3f}s before {cur:.3f}s ends")
        cur = max(cur, ev["t1"])
    if cur < duration - 1e-6:
        problems.append(f"gap {cur:.3f}s-{duration:.3f}s after the last event (track is {duration:.3f}s)")
    elif cur > duration + 1e-6:
        problems.append(f"last event ends at {cur:.3f}s, past the track duration {duration:.3f}s")
    return problems


# --------------------------------------------------------- media existence
def check_media_exists(doc: dict, media_root: Path) -> list[str]:
    """'Every referenced media file exists' (deliverable 3)."""
    problems = []
    media_root = Path(media_root)

    def want(rel: str, where: str):
        if not (media_root / rel).exists():
            problems.append(f"{where}: media '{rel}' not found under {media_root}")

    want(doc["audio"]["media"], "audio")
    for ev in doc["events"]:
        p = ev["params"]
        want(p["media"], ev["id"])
        if p.get("avatar_mode") == "composite":
            want(p["avatar"]["media"], f"{ev['id']} (avatar)")
    return problems


# ---------------------------------------------------- avatar/evidence box
def _boxes_intersect(a: dict, b: dict) -> bool:
    return a["x0"] < b["x"] + b["w"] and b["x"] < a["x1"] and a["y0"] < b["y"] + b["h"] and b["y"] < a["y1"]


def check_avatar_evidence_overlap(events: list[dict], media_root: Path) -> list[str]:
    """HARD rule, §6d: the avatar must never cover the evidence element on a
    real-footage plate. Only fires when avatar_mode=composite over a real_*
    plate. A plate the check cannot prove safe (no evidence_box on record)
    fails closed, not open -- see SCHEMA.md."""
    problems = []
    manifest_path = Path(media_root) / "real" / "REAL_MANIFEST.json"
    manifest = None
    manifest_by_file: dict[str, dict] = {}

    for ev in events:
        p = ev["params"]
        if p.get("avatar_mode") != "composite" or p.get("role") not in REAL_ROLES:
            continue
        if manifest is None:
            if not manifest_path.exists():
                problems.append(
                    f"{ev['id']}: avatar composites over a real-footage plate but "
                    f"{manifest_path} does not exist -- cannot verify the evidence box")
                manifest = []
                continue
            manifest = load_json(manifest_path)
            if not isinstance(manifest, list):
                raise EDLError(f"{manifest_path}: expected a list of entries")
            manifest_by_file = {m.get("file"): m for m in manifest}
        src = p.get("real_source")
        entry = manifest_by_file.get(src)
        if entry is None:
            problems.append(f"{ev['id']}: real_source '{src}' not found in {manifest_path}")
            continue
        boxes = entry.get("evidence_box")
        if not boxes:
            problems.append(
                f"{ev['id']}: {manifest_path} entry '{src}' has no evidence_box -- "
                f"cannot prove the composited avatar clears it, treated as unsafe")
            continue
        for box in boxes:
            if _boxes_intersect(AVATAR_BOX, box):
                problems.append(
                    f"{ev['id']}: avatar composite box (x{AVATAR_BOX['x0']}-{AVATAR_BOX['x1']} "
                    f"y{AVATAR_BOX['y0']}-{AVATAR_BOX['y1']}) overlaps the evidence box "
                    f"{box} on '{src}' -- move the plate, not the avatar (§6d)")
    return problems


# ---------------------------------------------------- P2-P4 shape + refs
def validate_layer(layer_name: str, doc: dict, registry: dict, earlier_ids: set[str]) -> set[str]:
    """Validate a P2/P3/P4 layer against the open-but-checked-in type
    registry and this file's own + earlier layers' ids. Returns the set of
    ids this layer defines (for the next layer's earlier_ids). Raises
    EDLError loudly on an unknown type or a dangling id (deliverable 2)."""
    for key in ("episode", "duration", "events"):
        if key not in doc:
            raise EDLError(f"{layer_name}: missing top-level '{key}'")
    if not isinstance(doc["events"], list):
        raise EDLError(f"{layer_name}: events must be a list")

    ids = set()
    for ev in doc["events"]:
        if "id" not in ev:
            raise EDLError(f"{layer_name}: event missing 'id'")
        eid = ev["id"]
        if eid in ids or eid in earlier_ids:
            raise EDLError(f"{layer_name} {eid}: duplicate id")
        for key in ("t0", "t1", "type", "params"):
            if key not in ev:
                raise EDLError(f"{layer_name} {eid}: missing '{key}'")
        if not (ev["t0"] < ev["t1"]):
            raise EDLError(f"{layer_name} {eid}: t0 {ev['t0']} must be < t1 {ev['t1']}")
        if ev["t0"] < -1e-6 or ev["t1"] > doc["duration"] + 1e-6:
            raise EDLError(f"{layer_name} {eid}: [{ev['t0']}, {ev['t1']}] falls outside [0, {doc['duration']}]")
        if ev["type"] not in registry:
            raise EDLError(
                f"{layer_name} {eid}: unknown type '{ev['type']}' -- not in the event-type "
                f"registry (edl/event_types.json). Add it there before using it.")
        for ref in ev.get("refs", []):
            if ref not in earlier_ids and ref not in ids:
                raise EDLError(f"{layer_name} {eid}: dangling id reference '{ref}'")
        ids.add(eid)
    return ids
