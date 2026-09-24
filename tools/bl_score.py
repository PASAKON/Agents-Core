#!/usr/bin/env python3
"""BLACK LIQUIDITY Scorer -- measure the Scripter against a human cut and its
own cost (task-67bb7a11).

Usage:
    python3 tools/bl_score.py --beats beats.json --truth ground_truth_beats.json \
        [--transcript session.jsonl | --usage scripter_usage.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CANVAS_W, CANVAS_H = 1080, 1920


def normalize_box(box: list[float] | tuple, extra: dict, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H
                   ) -> tuple[float, float, float, float]:
    nw = extra.get("native_w", canvas_w) or canvas_w
    nh = extra.get("native_h", canvas_h) or canvas_h
    x, y, w, h = box
    return x / nw, y / nh, w / nw, h / nh


def iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    ax0, ay0, aw, ah = box_a
    bx0, by0, bw, bh = box_b
    ax1, ay1, bx1, by1 = ax0 + aw, ay0 + ah, bx0 + bw, by0 + bh
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def score(beats: list[dict], truth: list[dict]) -> dict:
    beats_by_tag = {b["tag"]: b for b in beats}
    truth_by_tag = {t["tag"]: t for t in truth}
    truth_tags = [t["tag"] for t in truth]
    beat_tags = [b["tag"] for b in beats]

    common = [t for t in truth_tags if t in beats_by_tag]
    missing = [t for t in truth_tags if t not in beats_by_tag]
    extra = [t for t in beat_tags if t not in truth_by_tag]

    rows, ious = [], []
    mode_matches = 0
    for tag in common:
        b, t = beats_by_tag[tag], truth_by_tag[tag]
        mode_match = b.get("mode") == t.get("mode")
        mode_matches += int(mode_match)
        b_box = (b.get("extra") or {}).get("box")
        t_box = (t.get("extra") or {}).get("box")
        iou_val = None
        if b_box and t_box:
            iou_val = iou(normalize_box(b_box, b.get("extra") or {}), normalize_box(t_box, t.get("extra") or {}))
            ious.append(iou_val)
        rows.append({"tag": tag, "truth_mode": t.get("mode"), "beats_mode": b.get("mode"),
                     "mode_match": mode_match, "iou": iou_val})

    return {
        "common": common, "missing": missing, "extra": extra, "rows": rows,
        "mode_agreement_pct": (100.0 * mode_matches / len(common)) if common else 0.0,
        "mean_iou": (sum(ious) / len(ious)) if ious else None,
        "n_iou": len(ious),
    }


def render_markdown(result: dict, usage: dict | None = None) -> str:
    lines = ["# BLACK LIQUIDITY Scorer", ""]
    lines.append(f"- common beats (in both truth and produced): {len(result['common'])}")
    lines.append(f"- missing (in truth, not produced): {result['missing'] or '(none)'}")
    lines.append(f"- extra (produced, not in truth): {result['extra'] or '(none)'}")
    n_common = len(result["common"])
    matches = sum(r["mode_match"] for r in result["rows"])
    lines.append(f"- mode agreement: {result['mode_agreement_pct']:.1f}% ({matches}/{n_common})")
    if result["mean_iou"] is not None:
        lines.append(f"- mean IoU (over {result['n_iou']} beats with a box on both sides): {result['mean_iou']:.3f}")
    else:
        lines.append("- mean IoU: n/a (no common beat had a box on both sides)")
    lines.append("")
    lines.append("| tag | truth mode | scripter mode | match | IoU |")
    lines.append("|---|---|---|---|---|")
    for r in result["rows"]:
        iou_s = f"{r['iou']:.3f}" if r["iou"] is not None else "-"
        lines.append(f"| {r['tag']} | {r['truth_mode']} | {r['beats_mode']} | {'yes' if r['mode_match'] else 'no'} | {iou_s} |")

    if usage:
        lines += ["", "## Scripter run cost"]
        lines.append(f"- backend: {usage.get('backend', '?')}")
        lines.append(f"- turns: {usage.get('turns', '?')}")
        tok = usage.get("tokens", {}) or {}
        lines.append(f"- tokens: input={tok.get('input_tokens', 0)} "
                      f"cache_write={tok.get('cache_creation_input_tokens', 0)} "
                      f"cache_read={tok.get('cache_read_input_tokens', 0)} output={tok.get('output_tokens', 0)}")
        api_equiv = usage.get("cost_usd_api_equivalent")
        if api_equiv is not None:
            lines.append(f"- API-equivalent $ (Sonnet 5 pricing table): ${api_equiv:.4f}")
        max_plan = usage.get("cost_usd_reported_max_plan")
        if max_plan is not None:
            lines.append(f"- Max-plan reported $ (claude -p's own total_cost_usd): ${max_plan:.4f}")
        if usage.get("wall_seconds") is not None:
            lines.append(f"- wall seconds: {usage['wall_seconds']}")
    return "\n".join(lines)


def usage_from_args(args) -> dict | None:
    if args.usage:
        return json.loads(Path(args.usage).read_text(encoding="utf-8"))
    if args.transcript:
        from tools.bl_scripter import usage_from_transcript, _cost_from_token_dict
        t = usage_from_transcript(Path(args.transcript))
        return {
            "backend": "claude-p", "turns": t["turns"], "tokens": t["tokens"],
            "cost_usd_api_equivalent": round(_cost_from_token_dict(t["tokens"]), 6),
            "wall_seconds": None,
        }
    return None


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--beats", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--transcript", default=None, help="session .jsonl to derive tokens/turns from")
    ap.add_argument("--usage", default=None, help="scripter_usage.json (preferred over --transcript)")
    ap.add_argument("--out", default=None, help="also write the markdown report here")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    beats = json.loads(Path(args.beats).read_text(encoding="utf-8"))
    truth = json.loads(Path(args.truth).read_text(encoding="utf-8"))
    result = score(beats, truth)
    usage = usage_from_args(args)
    md = render_markdown(result, usage)
    print(md)
    if args.out:
        Path(args.out).write_text(md + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
