#!/usr/bin/env python3
"""Build GhostRules EP4 universal NO-TEXT cover with fixed top-right channel logo.

Rules enforced (CEO Q-20261114-0005-c5b4 / state/ph-briefs/project_head-f85ae4fe.md /
CMO_Standard_GhostChannel_DNA §7):
  - ONE cover with NO language text (zero Thai/English/other text)
  - Channel logo fixed top-right: watermark_150.png resized to 118x118 at (W - 118 - 28, 24)
  - NO EP number anywhere
  - Never a film frame (input must be dedicated ChatGPT paper-cut diorama key art
    generated with key_scene.png attached via prompts_ep04_cover.json)
  - Source video (/opt/MoonieXHQ/Work/task-0ef63967/out/ghostrules_ep04_full_1080p_v3.mp4)
    is verified read-only (md5 3f7fb90423deb73d7a7d802b2157564e) and never modified.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from PIL import Image

W, H = 1280, 720
LOGO_SIZE = 118
LOGO_MARGIN_RIGHT = 28
LOGO_MARGIN_TOP = 24

DEFAULT_LOGO = Path("/opt/MoonieXHQ/Work/ghostrules-full/channel-kit/watermark_150.png")
DEFAULT_OUT_DIR = Path("/opt/MoonieXHQ/Work/task-b24809a4/out")
SOURCE_MP4 = Path("/opt/MoonieXHQ/Work/task-0ef63967/out/ghostrules_ep04_full_1080p_v3.mp4")
EXPECTED_SOURCE_MD5 = "3f7fb90423deb73d7a7d802b2157564e"


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_cover(raw_image: Path, out_dir: Path, logo_path: Path = DEFAULT_LOGO) -> dict[str, str]:
    if not raw_image.is_file():
        raise FileNotFoundError(f"Raw ChatGPT cover image not found: {raw_image}")
    if not logo_path.is_file():
        raise FileNotFoundError(f"Channel logo not found: {logo_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    # Center-crop to 16:9 if raw aspect differs (e.g. 1536x1024 -> 1536x864), then LANCZOS to 1280x720
    img = Image.open(raw_image).convert("RGBA")
    src_w, src_h = img.size
    target_ratio = W / H
    src_ratio = src_w / src_h
    if abs(src_ratio - target_ratio) > 0.01:
        if src_ratio > target_ratio:
            new_w = int(round(src_h * target_ratio))
            left = (src_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, src_h))
        else:
            new_h = int(round(src_w / target_ratio))
            # Bias crop slightly downward to preserve character head & window haunting
            top = (src_h - new_h) // 2
            img = img.crop((0, top, src_w, top + new_h))

    img = img.resize((W, H), Image.LANCZOS)

    # Fixed top-right logo: (1280 - 118 - 28, 24) = (1134, 24)
    logo = Image.open(logo_path).convert("RGBA").resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
    img.alpha_composite(logo, (W - LOGO_SIZE - LOGO_MARGIN_RIGHT, LOGO_MARGIN_TOP))

    rgb = img.convert("RGB")
    out_jpg = out_dir / "ep04_cover_notext.jpg"
    out_png = out_dir / "ep04_cover_notext.png"
    out_320 = out_dir / "ep04_cover_notext_320.jpg"

    rgb.save(out_jpg, quality=92)
    rgb.save(out_png)
    rgb.resize((320, 180), Image.LANCZOS).save(out_320, quality=90)

    return {
        "jpg": str(out_jpg),
        "jpg_md5": md5_file(out_jpg),
        "png": str(out_png),
        "png_md5": md5_file(out_png),
        "preview_320": str(out_320),
        "preview_320_md5": md5_file(out_320),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw",
        type=Path,
        default=DEFAULT_OUT_DIR / "ep04_cover_raw.png",
        help="Path to raw 16:9 ChatGPT cover key art PNG",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory (/opt/MoonieXHQ/Work/task-b24809a4/out)",
    )
    parser.add_argument(
        "--logo",
        type=Path,
        default=DEFAULT_LOGO,
        help="Path to watermark_150.png",
    )
    parser.add_argument(
        "--verify-source-mp4",
        action="store_true",
        help="Verify source EP4 MP4 md5 matches 3f7fb90423deb73d7a7d802b2157564e",
    )
    args = parser.parse_args()

    if args.verify_source_mp4 and SOURCE_MP4.is_file():
        actual_md5 = md5_file(SOURCE_MP4)
        assert actual_md5 == EXPECTED_SOURCE_MD5, (
            f"Source MP4 md5 mismatch: got {actual_md5}, expected {EXPECTED_SOURCE_MD5}"
        )
        print(f"source_mp4={SOURCE_MP4} md5={actual_md5} (OK)")

    result = build_cover(args.raw, args.out_dir, args.logo)
    for k, v in result.items():
        print(f"{k}={v}")


if __name__ == "__main__":
    main()
