#!/opt/MoonieXHQ/Work/ghost-pilot/.rembg-venv/bin/python
# -*- coding: utf-8 -*-
"""Step 1 of BRIEF-ep07-build.md: Generate RGBA cutouts for Ghost Rules EP07 plates P01..P56.

Runs with /opt/MoonieXHQ/Work/ghost-pilot/.rembg-venv/bin/python using
rembg.new_session('isnet-general-use') (cached in /root/.rembg/models, no network).
Saves cutouts/Pxx_fg.png; skips a cutout when the plate is an empty location,
is the P38 jump-scare CALM/REVEAL pair, or when foreground covers >55%
(motion = camera move only).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("U2NET_HOME", "/root/.rembg/models")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
from PIL import Image
import rembg

EP07_DIR = Path("/opt/MoonieXHQ/Work/ghost-pilot/ep07")
PLATES_DIR = EP07_DIR / "plates"
CUTOUTS_DIR = EP07_DIR / "cutouts"

# Empty-location / full-scene plates or special jump-scare plates where camera-only
# or custom CALM/REVEAL motion is used if rembg segments >55% or <0.5% of the frame.
EMPTY_LOCATION_PLATES: set[str] = set()
SKIP_ALWAYS = {"P38"}  # P38 uses P38.png (CALM) + P38_REVEAL.png (REVEAL) jump-scare renderer


def main() -> int:
    CUTOUTS_DIR.mkdir(parents=True, exist_ok=True)
    session = rembg.new_session("isnet-general-use")
    manifest: dict[str, dict] = {}

    for idx in range(1, 57):
        pid = f"P{idx:02d}"
        src_path = PLATES_DIR / f"{pid}.png"
        out_path = CUTOUTS_DIR / f"{pid}_fg.png"
        if not src_path.exists():
            raise FileNotFoundError(f"Missing input plate: {src_path}")

        if pid in SKIP_ALWAYS or pid in EMPTY_LOCATION_PLATES:
            out_path.unlink(missing_ok=True)
            manifest[pid] = {
                "plate": pid,
                "status": "skipped",
                "reason": "jump_scare_pair" if pid == "P38" else "empty_location",
                "fg_coverage": 0.0,
            }
            print(f"[{pid}] skipped ({manifest[pid]['reason']})", flush=True)
            continue

        # Reuse existing cutout if already generated in cutouts/ or cut_test/
        cut_test_path = EP07_DIR / "cut_test" / f"{pid}_fg.png"
        if out_path.exists() and out_path.stat().st_size > 1000:
            fg_im = Image.open(out_path).convert("RGBA")
            alpha = np.asarray(fg_im)[..., 3]
        elif cut_test_path.exists() and cut_test_path.stat().st_size > 1000:
            fg_im = Image.open(cut_test_path).convert("RGBA")
            alpha = np.asarray(fg_im)[..., 3]
        else:
            src_im = Image.open(src_path).convert("RGB")
            fg_im = rembg.remove(src_im, session=session)
            alpha = np.asarray(fg_im)[..., 3]

        # Measure foreground coverage using solid alpha threshold (>140 matches inpaint hole threshold)
        fg_cov = float((alpha > 140).mean())
        fg_any = float((alpha > 30).mean())

        if fg_cov > 0.55 or fg_any > 0.65:
            out_path.unlink(missing_ok=True)
            manifest[pid] = {
                "plate": pid,
                "status": "skipped",
                "reason": f"fg_coverage_gt_55pct ({fg_cov:.3f}, any={fg_any:.3f})",
                "fg_coverage": round(fg_cov, 4),
            }
            print(f"[{pid}] skipped: fg covers {fg_cov * 100:.1f}% > 55% (camera move only)", flush=True)
        elif fg_cov < 0.003:
            out_path.unlink(missing_ok=True)
            manifest[pid] = {
                "plate": pid,
                "status": "skipped",
                "reason": f"empty_or_tiny_fg ({fg_cov:.4f})",
                "fg_coverage": round(fg_cov, 4),
            }
            print(f"[{pid}] skipped: empty/tiny fg {fg_cov * 100:.2f}% (camera move only)", flush=True)
        else:
            if not out_path.exists():
                fg_im.save(out_path)
            manifest[pid] = {
                "plate": pid,
                "status": "ok",
                "file": str(out_path),
                "fg_coverage": round(fg_cov, 4),
            }
            print(f"[{pid}] saved {out_path.name} (fg_coverage={fg_cov * 100:.1f}%)", flush=True)

    manifest_path = CUTOUTS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    skipped = [k for k, v in manifest.items() if v["status"] != "ok"]
    print(f"Cutouts complete: {56 - len(skipped)} saved, {len(skipped)} skipped ({', '.join(skipped)})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
