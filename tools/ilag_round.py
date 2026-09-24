"""Finish one ChatGPT image round for the ILAG TopView trailer, with no model in the loop.

After `tools/chatgpt_images.py` has run on winbox, this pulls the named PNGs to Contabo,
refuses duplicates (md5 against every earlier round), builds the numbered contact sheet
the CEO reviews, uploads each image into the project's Drive Element/ (md5 checked by id,
one logs.txt line each, then a snapshot), and writes 1024-px JPEG refs + the ledger + the
sheet into the repo. IRON §53: rounds 4-6 were done by hand with per-round scripts.

    python3 tools/ilag_round.py --round 7 \
        --item crt_eye_v4="was #2, a touch of violet" --item loc_storm_pillars_A_v2="was #4, taller"

Needs ILAG_LOG_ACTOR=AI:<role>-<sid>. Drive ids: the project built 2026-09-24
(gdrive-filing: YT: ILAG/รอตั้งชื่อ (Topview Wan3 Challenge 2026)).
"""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts/gdrive-bridge"))
import ilag_rest as d  # noqa: E402

WINBOX_OUT = "C:/mooniex/ilag-runner/out"
STAGE = Path(os.environ.get("ILAG_STAGE", "/tmp/ilag-rounds"))
REFS = REPO / "docs/promo/topview-trailer/refs"
IDS = {"logs": "1asL3Woa5f1Lz3qhdHHTRrB-krpSRXDBY",
       "Element/Character": "1IXrrVe0WcdSNVjFxQHh5APm3Sr-8NsXa",
       "Element/Location": "1mrnHtqYNcqUa5lyw_vVxxh0tvu-CJf71",
       "Element/Prop": "1FUwd7qPAsBtrVjFxoOZpcHlbnK1fkjPf",
       "All Scene": "1LTme3KAdrsQgYv_F6J7pf9cq8BYp7NPD",
       "Soundtrack": "1eETTWwzOY3u5z_mcmhv4Ln-NsuuOdmVD",
       "Final Draft": "1NkLTYnK4kRCZbeaZePLTO4hp0LihZDNP"}


def place(name: str) -> str:
    if name.startswith(("char_", "villagers", "creature")):
        return "Element/Character"
    if name.startswith("prop"):
        return "Element/Prop"
    return "Element/Location"


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def contact_sheet(items, title, out: Path):
    from PIL import Image, ImageDraw, ImageFont
    cols, tw, th, pad, lab, head = 4, 720, 480, 16, 44, 70
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font, hfont = ImageFont.truetype(bold, 28), ImageFont.truetype(bold, 36)
    rows = -(-len(items) // cols)
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, head + rows * (th + lab + pad) + pad), (24, 26, 32))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, pad + 12), title, font=hfont, fill=(255, 214, 102))
    for i, (p, tag) in enumerate(items):
        x0, y0 = pad + (i % cols) * (tw + pad), pad + head + (i // cols) * (th + lab + pad)
        im = Image.open(p).convert("RGB")
        im.thumbnail((tw, th))
        sheet.paste(im, (x0 + (tw - im.width) // 2, y0 + (th - im.height) // 2))
        dr.text((x0, y0 + th + 6), f"{i + 1}. {p.stem}  ({tag})", font=font, fill=(235, 235, 235))
    sheet.save(out, quality=85)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True)
    ap.add_argument("--item", action="append", required=True, help='name="tag shown on the sheet"')
    ap.add_argument("--no-drive", action="store_true")
    a = ap.parse_args()
    if not os.environ.get("ILAG_LOG_ACTOR") and not a.no_drive:
        raise SystemExit("set ILAG_LOG_ACTOR=AI:<role>-<sid> first")
    items = [tuple(x.split("=", 1)) if "=" in x else (x, "") for x in a.item]
    stage = STAGE / f"r{a.round}"
    stage.mkdir(parents=True, exist_ok=True)

    # 1. pull + duplicate guard against every earlier round
    seen = {md5(p): p for p in STAGE.rglob("*.png") if p.parent != stage}
    paths = []
    for name, _ in items:
        dst = stage / f"{name}.png"
        subprocess.run(["scp", "-q", f"winbox:{WINBOX_OUT}/{name}.png", str(dst)], check=True)
        h = md5(dst)
        if h in seen:
            raise SystemExit(f"DUPLICATE: {name} has the same md5 as {seen[h]}")
        seen[h] = dst
        paths.append(dst)
    subprocess.run(["scp", "-q", f"winbox:{WINBOX_OUT}/ledger.json", str(stage / "ledger.json")], check=True)

    # 2. contact sheet + repo copies
    rep = REPO / f"docs/reports/ilag-trailer-round{a.round}"
    rep.mkdir(parents=True, exist_ok=True)
    sheet = rep / "contact-sheet.jpg"
    contact_sheet([(p, t) for p, (_, t) in zip(paths, items)], f"ROUND {a.round}", sheet)
    (rep / "ledger.json").write_bytes((stage / "ledger.json").read_bytes())
    from PIL import Image
    for p in paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((1024, 1024))
        im.save(REFS / f"{p.stem}.jpg", quality=85)
    print("sheet", sheet)

    # 3. Drive: upload into Element/, one log line each, then a snapshot
    if not a.no_drive:
        for p in paths:
            rel = place(p.stem)
            info, made = d.upload(p, p.name, IDS[rel])
            if made:
                d.append_log(IDS["logs"], [d.line("ADD", "FILE", p.name, d.link(info["id"]), rel, len(d.ls(IDS[rel])),
                                                  f"ChatGPT image, round {a.round} (zero-model runner on winbox), md5 {info['md5Checksum']}")])
            print(p.stem, info["id"], "uploaded" if made else "existed")
        snap = [f"--- SNAPSHOT {d.now()} by {d.ACTOR} ---"]
        snap += [f"{rel:18} {len(d.ls(IDS[rel]))} files" for rel in
                 ["All Scene", "Element/Character", "Element/Location", "Element/Prop", "Soundtrack", "Final Draft"]]
        snap += ["--- END ---"]
        d.append_log(IDS["logs"], snap)
        print("\n".join(snap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
