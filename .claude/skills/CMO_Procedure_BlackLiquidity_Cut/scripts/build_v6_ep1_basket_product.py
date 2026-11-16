#!/usr/bin/env python3
"""
build_v6_ep1_basket_product.py — Build Clip #2 (BL-EP1-V6-65s-Basket-WordSynced-RealProductReff.mp4):
  1. Uses the 100% Word-Synced V6 schedule + the 4 Veo 3.1 Screen-Logic shots + the 3 new Veo 3.1
     BLACK LIQUIDITY Product Footage shots (generated from the real 3D Sleep Mask REFF images):
       - PROD01_BL_03_put_on_rest.mp4  (at 44.10 - 48.40s: "ใส่ผ้าปิดตาตัดแสงทันที ให้สมองเข้าโหมดพักเร็วที่สุด")
       - PROD01_BL_01_inspect_cups.mp4 (at 58.08 - 62.16s: "ตัวช่วยพักสายตาที่คัดมา ใช้งานดีเหมือนตัวท็อป")
       - PROD01_BL_02_desk_showcase.mp4 (at 62.16 - 65.44s: "ราคาเข้าถึงง่ายกว่า ↙ กดดูในตะกร้าได้เลย")
  2. Embeds the 3 Real Product REFF images (`prod01_ref_01.jpg`, `prod01_ref_02.jpg`, `prod01_ref_03.jpg`)
     as a sleek animated BLACK LIQUIDITY Product Reference Showcase Card on screen during the product beat
     (58.12s - 65.40s) so the viewer sees the exact real product alongside the BL-themed video footage.
  3. Files the 3 REFF images and 3 Product Footage clips into Google Drive:
     `ALL DRAFT/BLACK LIQUIDITY/00_PRODUCT_LIBRARY/PROD-01_ผ้าปิดตา3D-ตัดแสง100%/{REFF,FOOTAGE}`
     and PATCHes `1ks85qoSgNhF_Dg--EZFlIeo6pMJCUI9E` on Google Drive.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np

sys.path.insert(0, "/Users/gob/MoonieXHQ/Agents/Core/scripts")
import build_bl_v4_lungtep_style as v4

sys.path.insert(0, "/Users/gob/MoonieXHQ/Agents/Core/scripts/gdrive-bridge")
import ilag_rest

sys.path.insert(0, "/Users/gob/.gemini/antigravity/brain/1ec08f78-528c-484f-be60-038384d3be35/scratch")
import build_v6_ep1_word_synced as v6_pure

BROLL_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/broll-incoming")
WORK_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/basket-pilot1-work")
BRAIN_DIR = Path("/Users/gob/.gemini/antigravity/brain/1ec08f78-528c-484f-be60-038384d3be35")
PROD_REFF_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/product-library/PROD-01_3D-Sleep-Eye-Mask/REFF")
PROD_FOOTAGE_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/product-library/PROD-01_3D-Sleep-Eye-Mask/FOOTAGE")

BL_DRIVE_ROOT = "1nH2aZ6B8wuI9KoxMSS4hAk77cGq0Z1WY"


def build_ep1_v6_basket_schedule() -> List[Dict[str, object]]:
    # Start from the 23-clause Word-Synced V6 Pure schedule (0.00 - 58.08s) and add the 2 Product CTA cuts (58.08 - 65.44s)
    sched: List[Dict[str, object]] = []
    for seg in v6_pure.EP1_V6_WORD_SYNCED_SCHEDULE:
        d = dict(seg)
        # At 44.10 - 48.40s ("SLEEP ใส่ผ้าปิดตาตัดแสงทันที"), use the new Veo 3.1 Product shot PROD01_BL_03_put_on_rest!
        if abs(float(d["start"]) - 44.10) < 0.05:
            d["clip"] = "PROD01_BL_03_put_on_rest"
            d["mstart"] = 0.20
            d["scale"] = 1.06
        # Trim the last pure segment from 58.50s to 58.08s where the Basket CTA starts
        if abs(float(d["end"]) - 58.50) < 0.05:
            d["end"] = 58.08
        sched.append(d)

    # Add Beat 6 Product Showcase cuts (58.08 - 61.80s and 61.80 - 65.44s)
    sched.append({
        "start": 58.08, "end": 61.80,
        "clip": "PROD01_BL_02_desk_showcase", "mstart": 0.20,
        "scale": 1.08, "focus": (0.50, 0.50),
        "trans": "exposure_flash", "sfx": "sub_drop_flash",
    })
    sched.append({
        "start": 61.80, "end": 65.44,
        "clip": "PROD01_BL_01_inspect_cups", "mstart": 0.20,
        "scale": 1.16, "focus": (0.58, 0.58),
        "trans": "scale_punch", "sfx": "shutter_pop",
    })
    return sched


def inject_real_product_reff_into_basket_html(wdir: Path) -> None:
    """Copy the 3 real product REFF images into wdir/clips/ and add a sleek REFF 3-photo showcase card at 58.12 - 65.40s."""
    clips_dir = wdir / "clips"
    clips_dir.mkdir(exist_ok=True)
    for i in (1, 2, 3):
        shutil.copy2(PROD_REFF_DIR / f"prod01_ref_0{i}.jpg", clips_dir / f"prod01_ref_0{i}.jpg")
    shutil.copy2(PROD_REFF_DIR / "prod01_ref_clean_mask.png", clips_dir / "prod01_ref_clean_mask.png")

    html_path = wdir / "index.html"
    html = html_path.read_text(encoding="utf-8")

    # Remove the old overlapping calloutBox(58.30, ...)
    html = re.sub(r'^\s*calloutBox\(58\.30,[^\n]+\n', '', html, flags=re.M)

    # Replace or add CSS for .bl-prod-reff-card
    css_Marker = "/* --- REAL PRODUCT REFF CARD --- */"
    if css_Marker not in html:
        prod_css = """
      /* --- REAL PRODUCT REFF CARD --- */
      .bl-prod-reff-card {
        position: absolute;
        left: 120px;
        width: 720px;
        top: 420px;
        background: rgba(8, 9, 12, 0.92);
        border: 2px solid #FF2D40;
        border-radius: 20px;
        padding: 16px 20px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.85), 0 0 28px rgba(255, 45, 64, 0.32);
        z-index: 28;
        opacity: 0;
        pointer-events: none;
      }
      .bl-prod-reff-hdr {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
      }
      .bl-prod-reff-badge {
        background: #E0202F;
        color: #FFFFFF;
        font-family: 'Kanit', sans-serif;
        font-weight: 800;
        font-size: 24px;
        padding: 4px 14px;
        border-radius: 8px;
        letter-spacing: 0.5px;
      }
      .bl-prod-reff-title {
        color: #F4DF14;
        font-family: 'Kanit', sans-serif;
        font-weight: 700;
        font-size: 26px;
      }
      .bl-prod-reff-grid {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 12px;
      }
      .bl-prod-reff-imgbox {
        background: #FFFFFF;
        border-radius: 12px;
        overflow: hidden;
        height: 175px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1.5px solid rgba(255, 255, 255, 0.25);
      }
      .bl-prod-reff-imgbox img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
"""
        html = html.replace("</style>", prod_css + "\n    </style>")

    # Add HTML element inside #stage
    if 'id="prod-reff-card"' not in html:
        prod_html = """
      <div class="bl-prod-reff-card" id="prod-reff-card">
        <div class="bl-prod-reff-hdr">
          <span class="bl-prod-reff-badge">สินค้าแนะนำในตะกร้า</span>
          <span class="bl-prod-reff-title">ผ้าปิดตา 3D Memory Foam · ตัดแสง 100%</span>
        </div>
        <div class="bl-prod-reff-grid">
          <div class="bl-prod-reff-imgbox"><img src="clips/prod01_ref_01.jpg" alt="REFF 1"></div>
          <div class="bl-prod-reff-imgbox"><img src="clips/prod01_ref_02.jpg" alt="REFF 2"></div>
          <div class="bl-prod-reff-imgbox"><img src="clips/prod01_ref_03.jpg" alt="REFF 3"></div>
        </div>
      </div>
"""
        html = html.replace('<div class="bug" id="bug">', prod_html + '\n      <div class="bug" id="bug">')

    # Update animation so #prod-reff-card sits at top=420 during desk macro (58.12 - 61.80s)
    # and slides down to top=830 (below the host's hands/face, above kinetic 1150) during 61.80 - 65.40s!
    html = re.sub(
        r'// --- ANIMATE REAL PRODUCT REFF CARD ---[\s\S]*?(?=window\.__timelines\["main"\] = tl;)',
        '',
        html,
    )
    anim_js = """
      // --- ANIMATE REAL PRODUCT REFF CARD ---
      tl.set("#prod-reff-card", { opacity: 0, top: 420, scale: 0.94 }, 0);
      tl.to("#prod-reff-card", { opacity: 1, top: 420, scale: 1.0, duration: 0.28, ease: "expo.out" }, 58.12);
      tl.to("#prod-reff-card", { top: 830, scale: 0.92, duration: 0.32, ease: "expo.out" }, 61.80);
      tl.to("#prod-reff-card", { opacity: 0, duration: 0.18 }, 65.35);
"""
    html = html.replace('window.__timelines["main"] = tl;', anim_js + '\n      window.__timelines["main"] = tl;')

    html_path.write_text(html, encoding="utf-8")


def patch_drive_file(file_id: str, local_path: Path, mime_type: str, token: str) -> str:
    local_md5 = hashlib.md5(local_path.read_bytes()).hexdigest()
    url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media&fields=id,name,size,md5Checksum"
    data = local_path.read_bytes()
    req = urllib.request.Request(
        url,
        data=data,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": mime_type,
            "Content-Length": str(len(data)),
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    remote_md5 = meta.get("md5Checksum", "")
    assert remote_md5 == local_md5, f"MD5 mismatch: {remote_md5} != {local_md5}"
    return remote_md5


def main() -> None:
    # 1. Copy harvested PROD01_BL_*.mp4 clips into PROD_FOOTAGE_DIR for local organization too
    PROD_FOOTAGE_DIR.mkdir(parents=True, exist_ok=True)
    prod_clips = [
        ("PROD01_BL_01_inspect_cups.mp4", "PROD01_CHAR_FRONT_(inspect-3d-sleep-mask-cups)_(ตัวช่วยพักสายตา-ผ้าปิดตา3D)_(16-11-2026)_(Veo 3.1).mp4"),
        ("PROD01_BL_02_desk_showcase.mp4", "PROD01_BROLL_NONE_(3d-sleep-mask-on-trading-desk)_(ตัดแสงกวนตา-ราคาเข้าถึงง่าย-กดตะกร้า)_(16-11-2026)_(Veo 3.1).mp4"),
        ("PROD01_BL_03_put_on_rest.mp4", "PROD01_CHAR_FRONT_(put-on-3d-sleep-mask-rest)_(ใส่ผ้าปิดตาตัดแสงทันที-สมองเข้าโหมดพัก)_(16-11-2026)_(Veo 3.1).mp4"),
    ]
    for src_name, canonical_name in prod_clips:
        p = BROLL_DIR / src_name
        if not p.exists():
            raise FileNotFoundError(f"Missing product clip: {p}")
        shutil.copy2(p, PROD_FOOTAGE_DIR / canonical_name)

    # 2. Render Clip #2 Plate (65.44s)
    wdir = WORK_DIR / "cut_pilot1_A_v5_65s_basket"
    plate_dst = wdir / "clips" / "v4_plate_track.mp4"
    if plate_dst.is_symlink() or plate_dst.exists():
        plate_dst.unlink()
    sched = build_ep1_v6_basket_schedule()
    v4.render_v4_plate_track_scheduled(plate_dst, sched, 65.44)

    # 3. Inject Real Product REFF 3-Photo Showcase Card into index.html & render HyperFrames
    inject_real_product_reff_into_basket_html(wdir)
    out_mp4 = WORK_DIR / "finals_v5_mass_sfx" / "BL-EP1-V6-65s-Basket-WordSynced-RealProductReff.mp4"
    print(f"[HyperFrames] Rendering {out_mp4.name}...", flush=True)
    subprocess.run(
        ["npx", "--yes", "hyperframes", "render", "--output", str(out_mp4), "--fps", "30", "--quality", "standard"],
        cwd=str(wdir),
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sheet_path = BRAIN_DIR / "sheet_EP1_v6_65s_basket_product.jpg"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-i", str(out_mp4),
            "-vf", "fps=1/4.0,scale=360:640,tile=4x4",
            "-frames:v", "1", "-q:v", "3",
            str(sheet_path),
        ],
        check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"[DONE] Rendered {out_mp4.name} ({out_mp4.stat().st_size:,} bytes) + {sheet_path.name}", flush=True)

    # 4. Create 00_PRODUCT_LIBRARY/PROD-01_ผ้าปิดตา3D-ตัดแสง100%/{REFF,FOOTAGE} on Google Drive & upload
    lib_id, _ = ilag_rest.mkfolder(BL_DRIVE_ROOT, "00_PRODUCT_LIBRARY")
    prod_id, _ = ilag_rest.mkfolder(lib_id, "PROD-01_ผ้าปิดตา3D-ตัดแสง100%")
    reff_id, _ = ilag_rest.mkfolder(prod_id, "REFF")
    ftg_id, _ = ilag_rest.mkfolder(prod_id, "FOOTAGE")
    print(f"[Drive 00_PRODUCT_LIBRARY] lib={lib_id} · prod01={prod_id} · REFF={reff_id} · FOOTAGE={ftg_id}", flush=True)

    for i in (1, 2, 3):
        rf = PROD_REFF_DIR / f"prod01_ref_0{i}.jpg"
        info, _ = ilag_rest.upload(rf, rf.name, reff_id)
        print(f"  [REFF uploaded] {rf.name} -> {info['id']}", flush=True)

    for _, canonical_name in prod_clips:
        fp = PROD_FOOTAGE_DIR / canonical_name
        info, _ = ilag_rest.upload(fp, canonical_name, ftg_id)
        print(f"  [FOOTAGE uploaded] {canonical_name} -> {info['id']}", flush=True)

    # 5. Patch EP1 Basket MP4 & Sheet on Google Drive
    token = ilag_rest.s.access_token()
    md5_v = patch_drive_file("1ks85qoSgNhF_Dg--EZFlIeo6pMJCUI9E", out_mp4, "video/mp4", token)
    md5_s = patch_drive_file("1_lZ-C5ghz-uNK8Ng7iKwhE809zYsTbMr", sheet_path, "image/jpeg", token)
    print(f"[PATCH EP1 V6 Basket OK] video=1ks85qoSgNhF_Dg--EZFlIeo6pMJCUI9E (md5={md5_v}) | sheet=1_lZ-C5ghz-uNK8Ng7iKwhE809zYsTbMr (md5={md5_s})", flush=True)


if __name__ == "__main__":
    main()
