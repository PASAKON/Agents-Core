#!/usr/bin/env python3
"""
tools/footage_catalog.py — Cross-Channel Timecode Footage Catalog & Zero-Context-Bloat Search CLI
for Agent Video Editors across MYPASAKON, BLACK LIQUIDITY, and TRADE TO THE MOON.

Index path:
  /Users/gob/MoonieXHQ/Agents/Core/prototypes/bl-broll-catalog/FOOTAGE_INDEX.jsonl

Commands:
  1. stats:
     python tools/footage_catalog.py stats
  2. search (returns top N matching timecode segments without reading the full catalog):
     python tools/footage_catalog.py search --channel BL --mode CHART_VIEWPORT --q "ถือออเดอร์ข้ามคืน ค่า Swap" --limit 5
     python tools/footage_catalog.py search --channel MYPASAKON --source-type LIFESTYLE --q "Porsche ขับรถ" --limit 5
  3. match-script (matches a full episode clause list with zero clip repetition):
     python tools/footage_catalog.py match-script --channel BL --clauses ep_clauses.json
  4. fetch (streams ONLY [start_s, end_s] from Google Drive via HTTP Range without full-file download):
     python tools/footage_catalog.py fetch --drive-id <id> --start 7.1 --end 11.8 --out cut.mp4 --frame-viewport
  5. sync (incremental Drive scan by drive_id + md5Checksum; skips 100% of already-indexed files):
     python tools/footage_catalog.py sync
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CORE_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = CORE_ROOT / "prototypes" / "bl-broll-catalog" / "FOOTAGE_INDEX.jsonl"


def load_index(path: Path = INDEX_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Missing index file: {path}")
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def tokenize_query(q: str) -> List[str]:
    if not q:
        return []
    # Split on whitespace and punctuation, plus extract 2+ char Thai/English substrings
    raw = [t.lower().strip() for t in re.split(r"[\s,;|/()\[\]·•\-_]+", q) if t.strip()]
    tokens = list(dict.fromkeys(raw))
    # Also split long Thai phrases by common trading keywords so compound Thai clauses match cleanly
    KEY_TERMS = [
        "กราฟ", "ทอง", "xauusd", "mt5", "mt4", "tradingview", "exness", "xm", "iq",
        "swap", "สวอป", "สเปรด", "spread", "ข่าว", "20:30", "สองทุ่มครึ่ง", "ตีสาม", "ตีสี่", "ตีสอง",
        "พอร์ตแดง", "ติดลบ", "คัดลอส", "stop loss", "sl", "tp", "ปิดสถานะ", "ปิดออเดอร์", "เคลียร์ไม้",
        "ซอยไม้", "ติดดอย", "ล้างพอร์ต", "กำไร", "พอร์ตฟ้า", "ถอนเงิน", "ฝากเงิน", "สมอง", "หลับลึก",
        "โดพามีน", "คอร์ติซอล", "ผ้าปิดตา", "porsche", "ขับรถ", "ร้านกาแฟ", "starbucks", "โน้ตบุ๊ก",
        "มือถือ", "drawdown", "ดรอว์ดาวน์", "คณิตศาสตร์", "ล็อกมือ", "15 นาที", "ไซด์เวย์", "เบรกเอาต์",
    ]
    q_low = q.lower()
    for kt in KEY_TERMS:
        if kt in q_low and kt not in tokens:
            tokens.append(kt)
    return tokens


def score_segment(
    entry: Dict[str, Any],
    seg: Dict[str, Any],
    tokens: List[str],
    prefer_mode: Optional[str] = None,
    prefer_beat: Optional[str] = None,
) -> float:
    score = 1.0
    if prefer_mode and seg.get("editor_mode") == prefer_mode:
        score += 6.0
    if prefer_beat and prefer_beat.upper() in [b.upper() for b in seg.get("fit_beats", [])]:
        score += 3.0

    haystack_kw = " ".join(seg.get("spoken_keywords_th", [])).lower()
    haystack_act = f"{seg.get('action_th', '')} {seg.get('action_en', '')}".lower()
    haystack_meta = f"{entry.get('filename', '')} {entry.get('symbol_timeframe', '')} {entry.get('platform', '')} {entry.get('broker', '')}".lower()

    for tok in tokens:
        if not tok:
            continue
        if tok in haystack_kw:
            score += 5.0
        if tok in haystack_act:
            score += 3.5
        if tok in haystack_meta:
            score += 2.0

    # Slight bonus for native 9:16 vertical clips and explicitly curated multi-segment overrides
    if entry.get("aspect") == "9:16":
        score += 0.8
    if seg.get("safe_crop"):
        score += 0.5
    return round(score, 2)


def filter_and_rank(
    entries: List[Dict[str, Any]],
    channel: str = "ALL",
    mode: Optional[str] = None,
    source_type: Optional[str] = None,
    platform: Optional[str] = None,
    broker: Optional[str] = None,
    person: Optional[str] = None,
    aspect: Optional[str] = None,
    theme: Optional[str] = None,
    min_dur: float = 0.0,
    query: str = "",
    beat: Optional[str] = None,
    exclude_keys: Optional[set[str]] = None,
) -> List[Tuple[float, Dict[str, Any], Dict[str, Any]]]:
    tokens = tokenize_query(query)
    ch_up = channel.upper()
    results: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []

    for e in entries:
        if e.get("source_type") == "BROKEN" or not e.get("segments"):
            continue
        caution = str(e.get("caution") or "")
        if "DO_NOT_USE" in caution or "never use" in caution.lower():
            continue

        ch_fit = [c.upper() for c in e.get("channel_fit", [])]
        if ch_up != "ALL" and ch_up not in ch_fit and "ALL" not in ch_fit:
            continue

        if source_type and e.get("source_type", "").upper() != source_type.upper():
            continue
        if platform and platform.upper() not in e.get("platform", "").upper():
            continue
        if person and e.get("person_shown", "").upper() != person.upper():
            continue
        if aspect and e.get("aspect") != aspect:
            continue
        if theme and theme.lower() not in e.get("theme_color", "").lower():
            continue

        # Broker lock check:
        # If caller specifies --broker NONE (generic content), exclude clips locked to a specific broker
        # If caller specifies --broker Exness, allow NONE or Exness
        b_lock = str(e.get("broker_lock", "NONE")).upper()
        if broker:
            b_req = broker.upper()
            if b_req == "NONE" and b_lock != "NONE":
                continue
            elif b_req != "NONE" and b_lock not in ("NONE", b_req):
                continue

        for seg in e.get("segments", []):
            seg_key = f"{e['drive_id']}:{seg['seg_id']}"
            if exclude_keys and (e["drive_id"] in exclude_keys or seg_key in exclude_keys):
                continue
            if mode and seg.get("editor_mode", "").upper() != mode.upper():
                continue
            seg_dur = float(seg.get("end_s", 0.0)) - float(seg.get("start_s", 0.0))
            if seg_dur < min_dur:
                continue

            sc = score_segment(e, seg, tokens, prefer_mode=mode, prefer_beat=beat)
            results.append((sc, e, seg))

    results.sort(key=lambda x: (-x[0], x[1]["phase"], x[1]["drive_id"]))
    return results


def cmd_stats(_args: argparse.Namespace) -> int:
    entries = load_index()
    total_segs = sum(len(e.get("segments", [])) for e in entries)
    by_phase = Counter(e.get("phase") for e in entries)
    by_stype = Counter(e.get("source_type") for e in entries)
    by_plat = Counter(e.get("platform") for e in entries)
    by_broker = Counter(e.get("broker_lock") for e in entries)
    by_person = Counter(e.get("person_shown") for e in entries)

    ch_counts = Counter()
    for e in entries:
        for c in set(e.get("channel_fit", [])):
            ch_counts[c] += 1

    print(f"=== MoonieX Shared Footage Catalog ({INDEX_PATH.name}) ===")
    print(f"Total Indexed Videos : {len(entries)} videos ({total_segs} timecode segments)")
    print(f"By Phase             : Phase 1 (Screen+AI)={by_phase[1]} | Phase 2 (Lifestyle)={by_phase[2]} | Phase 3 (Broker Events)={by_phase[3]}")
    print(f"By Source Type       : {dict(by_stype)}")
    print(f"By Platform          : {dict(by_plat)}")
    print(f"By Broker Lock       : {dict(by_broker)}")
    print(f"By Person Shown      : {dict(by_person)}")
    print(f"Usable by Channel    : {dict(ch_counts)}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    entries = load_index()
    ranked = filter_and_rank(
        entries,
        channel=args.channel,
        mode=args.mode,
        source_type=args.source_type,
        platform=args.platform,
        broker=args.broker,
        person=args.person,
        aspect=args.aspect,
        theme=args.theme,
        min_dur=args.min_dur,
        query=args.q or "",
        beat=args.beat,
    )
    top = ranked[: args.limit]
    if args.json:
        out = [
            {
                "score": sc,
                "drive_id": e["drive_id"],
                "filename": e["filename"],
                "drive_folder": e["drive_folder"],
                "source_type": e["source_type"],
                "platform": e["platform"],
                "broker_lock": e["broker_lock"],
                "person_shown": e["person_shown"],
                "channel_fit": e["channel_fit"],
                "aspect": e["aspect"],
                "theme_color": e["theme_color"],
                "seg_id": seg["seg_id"],
                "start_s": seg["start_s"],
                "end_s": seg["end_s"],
                "editor_mode": seg["editor_mode"],
                "safe_crop": seg.get("safe_crop"),
                "action_th": seg["action_th"],
                "spoken_keywords_th": seg.get("spoken_keywords_th", []),
                "caution": e.get("caution"),
            }
            for sc, e, seg in top
        ]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"[SEARCH] channel={args.channel} mode={args.mode or 'ANY'} q='{args.q or ''}' -> showing top {len(top)} of {len(ranked)} matching segments:")
    for idx, (sc, e, seg) in enumerate(top, 1):
        dur = round(float(seg["end_s"]) - float(seg["start_s"]), 2)
        print(
            f"  {idx:02d}. [score={sc:4.1f}] id={e['drive_id']} ({seg['seg_id']} {seg['start_s']:.2f}s..{seg['end_s']:.2f}s, {dur:.1f}s) "
            f"| {e['source_type']}/{e['platform']} | mode={seg['editor_mode']} | person={e['person_shown']} | broker={e['broker_lock']}"
        )
        print(f"      file: {e['filename']} ({e['aspect']}, {e['theme_color']})")
        print(f"      action: {seg['action_th']}")
        print(f"      keywords: {', '.join(seg.get('spoken_keywords_th', [])[:8])}")
    return 0


def cmd_match_script(args: argparse.Namespace) -> int:
    entries = load_index()
    clauses = json.loads(Path(args.clauses).read_text(encoding="utf-8"))
    used_ids: set[str] = set()
    plan: List[Dict[str, Any]] = []

    for idx, cl in enumerate(clauses, 1):
        c_start = float(cl.get("start", 0.0))
        c_end = float(cl.get("end", c_start + 2.5))
        need_dur = max(1.0, c_end - c_start)
        mode = cl.get("mode")
        stype = cl.get("source_type")
        text = cl.get("text", "")
        beat = cl.get("beat")

        ranked = filter_and_rank(
            entries,
            channel=args.channel,
            mode=mode,
            source_type=stype,
            broker=args.broker,
            min_dur=min(need_dur * 0.6, 2.5),
            query=text,
            beat=beat,
            exclude_keys=used_ids,
        )
        if not ranked:
            # Fallback relaxing mode constraint
            ranked = filter_and_rank(
                entries,
                channel=args.channel,
                broker=args.broker,
                query=text,
                exclude_keys=used_ids,
            )
        if not ranked:
            raise SystemExit(f"No matching footage found for clause #{idx}: {cl}")

        sc, e, seg = ranked[0]
        used_ids.add(e["drive_id"])
        plan.append({
            "clause_idx": idx,
            "start": c_start,
            "end": c_end,
            "spoken_text": text,
            "score": sc,
            "drive_id": e["drive_id"],
            "filename": e["filename"],
            "source_type": e["source_type"],
            "platform": e["platform"],
            "editor_mode": seg["editor_mode"],
            "seg_id": seg["seg_id"],
            "media_start_s": seg["start_s"],
            "media_end_s": seg["end_s"],
            "safe_crop": seg.get("safe_crop"),
            "action_th": seg["action_th"],
        })

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"=== Matched {len(plan)} Clauses for Channel={args.channel} (100% Unique Clips) ===")
        for row in plan:
            print(
                f"  #{row['clause_idx']:02d} [{row['start']:5.2f}s..{row['end']:5.2f}s] ({row['editor_mode']:14s}) "
                f"-> id={row['drive_id']} @{row['media_start_s']:.1f}..{row['media_end_s']:.1f}s | {row['action_th'][:58]}"
            )
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(CORE_ROOT / "scripts" / "gdrive-bridge"))
    import ilag_rest  # type: ignore

    token = ilag_rest.s.access_token()
    url = f"https://www.googleapis.com/drive/v3/files/{args.drive_id}?alt=media"
    dur = max(0.5, float(args.end) - float(args.start))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Look up safe_crop in index if not explicitly provided
    crop_filter = args.crop
    if not crop_filter and args.frame_viewport:
        for e in load_index():
            if e["drive_id"] == args.drive_id:
                for seg in e.get("segments", []):
                    if seg.get("safe_crop"):
                        crop_filter = seg["safe_crop"]
                        break

    if args.frame_viewport:
        c_part = f"{crop_filter}," if crop_filter else ""
        vf = (
            f"fps=30,{c_part}scale=860:770:force_original_aspect_ratio=decrease,"
            f"pad=860:770:(ow-iw)/2:(oh-ih)/2:color=0x07080A,"
            f"drawbox=x=0:y=0:w=860:h=770:color=0x2A2E35:t=3,"
            f"pad=1080:1920:110:430:color=0x07080A"
        )
    else:
        vf = "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    cmd = [
        "ffmpeg", "-nostdin", "-y",
        "-headers", f"Authorization: Bearer {token}\r\n",
        "-ss", f"{float(args.start):.2f}",
        "-t", f"{dur:.2f}",
        "-i", url,
        "-vf", vf,
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    print(f"[FETCHED] {out_path} ({out_path.stat().st_size:,} bytes) from drive_id={args.drive_id} [{args.start:.2f}s..{args.end:.2f}s]")
    return 0


def cmd_sync(_args: argparse.Namespace) -> int:
    sys.path.insert(0, str(CORE_ROOT / "scripts" / "gdrive-bridge"))
    import ilag_rest  # type: ignore

    entries = load_index()
    known = {e["drive_id"]: e.get("md5", "") for e in entries}

    roots = [
        ("1LJreOD8H3jUNzypxTnPwvq-pS7jkQNRd", "ALL DRAFT/ASSETS"),
        ("1n9PuChyLcl4_Sh88jvYJLGKHwVGcu5ZK", "ALL DRAFT/BLACK LIQUIDITY/00_PRODUCT_LIBRARY"),
        ("102wBUOSSzP97zC4KypyYuZNxTAtSpAzl", "ALL DRAFT/MYPASAKON/วิธีการใช้งาน APPs MT5"),
    ]
    new_files: List[Dict[str, Any]] = []

    def scan(fid: str, fpath: str) -> None:
        for it in ilag_rest.ls(fid):
            mt = it.get("mimeType", "")
            if mt == "application/vnd.google-apps.folder":
                scan(it["id"], f"{fpath}/{it['name']}")
            elif "video" in mt:
                if it["id"] not in known or (it.get("md5Checksum") and known[it["id"]] != it.get("md5Checksum")):
                    it["folder_path"] = fpath
                    new_files.append(it)

    for r_id, r_path in roots:
        scan(r_id, r_path)

    print(f"[SYNC] Indexed={len(known)} videos | Newly added or modified on Drive={len(new_files)} videos")
    for nf in new_files[:20]:
        print(f"  + NEW: {nf['id']} | {nf['folder_path']} | {nf['name']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="MoonieX Cross-Channel Timecode Footage Catalog CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats", help="Show summary counts of indexed videos & segments")

    p_s = sub.add_parser("search", help="Search timecode segments by channel, mode, platform, broker, and spoken keywords")
    p_s.add_argument("--channel", default="ALL", help="Channel filter: BL | MYPASAKON | TTTM | ALL")
    p_s.add_argument("--mode", help="Editor mode: CHART_VIEWPORT | FOOTAGE_FOCUS | CALM_TEXT_BG")
    p_s.add_argument("--source-type", help="REAL_SCREEN | AI_CHAR | AI_BROLL | PRODUCT | LIFESTYLE | BROKER_EVENT")
    p_s.add_argument("--platform", help="MT5_MOBILE | EXNESS_DESKTOP | EXNESS_MOBILE | IQ_OPTION | REAL_CAMERA")
    p_s.add_argument("--broker", help="NONE | Exness | XM | IQ_Option | FXGT | FXPro | Infinox | KCMTrade | OANDA")
    p_s.add_argument("--person", help="NONE | HANDS_ONLY | CEO_PASAKON | BL_AVATAR | CROWD_EVENT")
    p_s.add_argument("--aspect", help="9:16 | 16:9")
    p_s.add_argument("--theme", help="Theme color substring, e.g. Dark_Red, Dark_Green, Light")
    p_s.add_argument("--beat", help="Beat filter: HOOK | PAIN | MIRROR | MECHANISM | PIVOT | FIX | TAKEAWAY | PROOF")
    p_s.add_argument("--min-dur", type=float, default=0.0, help="Minimum segment duration in seconds")
    p_s.add_argument("--q", default="", help="Spoken Thai/English keywords or phrase")
    p_s.add_argument("--limit", type=int, default=5, help="Max segments to return (default 5)")
    p_s.add_argument("--json", action="store_true", help="Output JSON")

    p_m = sub.add_parser("match-script", help="Batch-match a JSON list of spoken clauses with zero clip repetition")
    p_m.add_argument("--channel", required=True, help="BL | MYPASAKON | TTTM")
    p_m.add_argument("--clauses", required=True, help="Path to JSON file of clauses")
    p_m.add_argument("--broker", default="NONE", help="Broker constraint (default NONE)")
    p_m.add_argument("--json", action="store_true", help="Output JSON")

    p_f = sub.add_parser("fetch", help="Stream-cut ONLY [start_s, end_s] from Drive via HTTP Range")
    p_f.add_argument("--drive-id", required=True, help="Google Drive file ID")
    p_f.add_argument("--start", type=float, required=True, help="Start time in seconds")
    p_f.add_argument("--end", type=float, required=True, help="End time in seconds")
    p_f.add_argument("--out", required=True, help="Output MP4 path")
    p_f.add_argument("--crop", help="Optional custom ffmpeg crop filter")
    p_f.add_argument("--frame-viewport", action="store_true", help="Frame into 860x770 (x=110, y=430) safe chart viewport")

    sub.add_parser("sync", help="Check Drive for newly uploaded videos not yet in FOOTAGE_INDEX.jsonl")

    args = ap.parse_args()
    if args.cmd == "stats":
        return cmd_stats(args)
    if args.cmd == "search":
        return cmd_search(args)
    if args.cmd == "match-script":
        return cmd_match_script(args)
    if args.cmd == "fetch":
        return cmd_fetch(args)
    if args.cmd == "sync":
        return cmd_sync(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
