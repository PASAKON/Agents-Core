#!/usr/bin/env python3
"""MoonieX personal-branding quote-poster workflow.

GPT-2 bakes a HUGE random art-headline (the keyword) + Thai quote on a navy+gold scene,
then the mooniex_logo node composites the moon+MOONIEX lockup top-right. Batch or single.
Locked spec: memory `reference_mooniex_poster_recipe.md`.

  python scripts/mooniex_poster.py dry                  # print prompts, NO gen (free)
  python scripts/mooniex_poster.py gen --indices 1,11   # gen specific quotes
  python scripts/mooniex_poster.py gen --count 30        # gen all 30
  python scripts/mooniex_poster.py stamp --indices 1     # re-composite logo only (free)

Cost ~$0.19/image (fal openai/gpt-image-2/edit, high). Prints estimate + indices before
any paid call — confirm spend per the ASK-before-paid rule.
"""
import sys, os, json, base64, argparse, random, urllib.request, urllib.error, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mooniex_logo import stamp_corner  # logo workflow node

BASE = "/Users/gob/Projects/Agents/output/personal-brand"
CROP = os.path.join(BASE, "_ref_crop.png")
OUT = "/Users/gob/Projects/Agents/output/mooniex-posters"
ENV = "/Users/gob/Projects/mooniex-claudeflow/.env"
ENDPOINT = "https://fal.run/openai/gpt-image-2/edit"
COST_PER_IMAGE = 0.19
WORKFLOW_KEY = "trader_mindset"  # ClaudeFlow workflow name (after economic_calendar, tradetech)

# (keyword shown HUGE, supporting Thai line)
QUOTES = [
    ("วินัย", "กำไรที่คนอื่นมองไม่เห็น"),
    ("ตัดขาดทุน", "อยู่รอดก่อน ค่อยพูดเรื่องกำไร"),
    ("มีแผน", "แผนที่ทำตามได้ ดีกว่าแผนสมบูรณ์ที่ทำไม่ได้"),
    ("คุมความเสี่ยง", "ความเสี่ยงที่คุมได้ คือ อิสรภาพที่แท้จริง"),
    ("รอเป็น", "กำไรมาจากการรอ ขาดทุนมาจากการรีบ"),
    ("อยู่ให้รอด", "อย่าเทรดเพื่อเอาคืน จงเทรดเพื่ออยู่ต่อ"),
    ("ค่าคาดหวัง", "ระบบที่ดีไม่ต้องถูกทุกไม้ แค่ถูกตอนไม้ใหญ่"),
    ("รักษาทุน", "เงินทุน คือ ชีวิตของเทรดเดอร์"),
    ("รู้จักหยุด", "หยุดเมื่อควรหยุด เก่งกว่าเข้าเมื่ออยากเข้า"),
    ("ไม่เจ๊ง", "พอร์ตโต เพราะไม่เจ๊ง ไม่ใช่เพราะกล้า"),
    ("อดทน", "ตลาดไม่ให้รางวัลคนเก่ง แต่ให้คนที่อดทน"),
    ("ชนะใจตัวเอง", "ศัตรูที่ใหญ่ที่สุดของเทรดเดอร์ คือ ตัวเอง"),
    ("ใจนิ่ง", "ควบคุมอารมณ์ได้ ก็ควบคุมพอร์ตได้"),
    ("เรียบง่าย", "ความเรียบง่าย คือ ที่สุดของกลยุทธ์"),
    ("รอจังหวะ", "ถ้าใจสั่น มืออย่ากดออเดอร์"),
    ("ไม่ยอมแพ้", "คนที่รอด ไม่ใช่คนไม่พลาด แต่คือคนไม่ยอมแพ้"),
    ("มองภาพรวม", "อย่าให้ไม้เดียว มาตัดสินทั้งเส้นทาง"),
    ("ความสงบ", "อาวุธลับในตลาดที่ผันผวน"),
    ("เตรียมพร้อม", "กลัวให้น้อยลง วางแผนให้มากขึ้น"),
    ("มีวินัย", "วันที่เบื่อจะทำตามระบบ คือวันที่สำคัญที่สุด"),
    ("เริ่มก่อน", "ทุกความสำเร็จ เริ่มจากวันที่ยังไม่มีใครเชื่อ"),
    ("ลงมือ", "ลงมือวันนี้ ดีกว่าสมบูรณ์แบบที่ไม่มีจริง"),
    ("วันละนิด", "เก่งขึ้นวันละนิด ดีกว่าเพอร์เฟกต์แล้วหยุด"),
    ("เกมของเรา", "อย่าเทียบบทที่ 1 ของคุณ กับบทที่ 20 ของคนอื่น"),
    ("ล้มแล้วลุก", "ความล้มเหลว คือ ค่าเล่าเรียนของความสำเร็จ"),
    ("โฟกัส", "โฟกัสสิ่งที่คุมได้ ปล่อยสิ่งที่คุมไม่ได้"),
    ("ลงทุนความรู้", "การลงทุนที่ไม่เคยขาดทุน"),
    ("ไม่หยุดเดิน", "คนที่ไปถึงฝัน คือ คนที่ไม่ยอมหยุดเดิน"),
    ("สม่ำเสมอ", "วินัยในวันธรรมดา สร้างผลลัพธ์ที่ไม่ธรรมดา"),
    ("เตรียมวันนี้", "อนาคตเป็นของคนที่เตรียมตัวตั้งแต่วันนี้"),
]

STYLES = [
    "expressive hand-painted INK-BRUSH lettering with bold textured strokes",
    "glossy CHROME METALLIC 3D lettering with reflective bevels",
    "flowing bold CALLIGRAPHY-style script lettering",
    "ENGRAVED EMBOSSED serif display with carved metal depth",
    "bold condensed STENCIL display lettering",
    "sleek LIQUID-GOLD lettering with smooth molten highlights",
]
POSES = [
    "stands three-quarter view, confident",
    "sits at a trading desk leaning back confidently",
    "stands with arms crossed",
    "stands with hands in his pockets",
    "leans forward with forearms on a trading desk",
]
SCENES = [
    "in front of a wall of monitors showing gold candlestick charts, blurred into warm gold bokeh",
    "with a large curved LED screen of gold candlestick charts blurred behind",
    "on a real navy trading floor at golden hour with warm gold bokeh",
    "by a dark penthouse window at night, city lights and gold reflections in warm bokeh",
    "beside a glass desk with a faint gold holographic chart reflection",
]

PRE = (
    "Identity (Critical): strictly reference @image1 — preserve the exact face, proportions, "
    "skin tone and hairstyle of the man; keep his black suit and black turtleneck; he must "
    "stay clearly recognizable. Palette STRICTLY deep navy (#0c1c2b) + warm champagne gold "
    "(#cdac65) only — NO cyan, purple, magenta, teal or blue neon. Premium institutional "
    "fintech, photorealistic, 8k. 1:1 bold editorial personal-brand poster. Keep the TOP-RIGHT "
    "corner clean and empty for a logo. Do NOT add any logo, badge, English wordmark or "
    "watermark. Render all Thai text accurately and legibly. ")


def build_prompt(idx):
    kw, sub = QUOTES[idx - 1]
    rnd = random.Random(idx * 7919)
    style = rnd.choice(STYLES); pose = rnd.choice(POSES); scene = rnd.choice(SCENES)
    return (PRE + f"The man {pose}, {scene}, warm gold rim light. A HUGE champagne-gold Thai "
            f"display headline reading '{kw}' dominating the upper area, rendered as {style}. "
            f"A smaller white-and-gold Thai line '{sub}' below it.")


def load_key():
    m = re.search(r"^FAL_API_KEY=(.+)$", open(ENV, encoding="utf-8").read(), re.M)
    if not m:
        sys.exit("FAL_API_KEY not found in " + ENV)
    return m.group(1).strip().strip('"').strip("'")


def gen_one(key, uri, idx):
    payload = {"prompt": build_prompt(idx), "image_urls": [uri], "image_size": "square_hd",
               "quality": "high", "num_images": 1, "output_format": "png"}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    print(f"[q{idx:02d}] POST ({len(body)}B) ...")
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"[q{idx:02d}] HTTP {e.code}: {e.read().decode()[:400]}"); return False
    imgs = data.get("images") or []
    if not imgs:
        print(f"[q{idx:02d}] no images: {json.dumps(data)[:300]}"); return False
    urllib.request.urlretrieve(imgs[0]["url"], os.path.join(OUT, f"q{idx:02d}.png"))
    print(f"[q{idx:02d}] OK -> q{idx:02d}.png")
    return True


def stamp_one(idx):
    from PIL import Image
    src = os.path.join(OUT, f"q{idx:02d}.png")
    if not os.path.exists(src):
        print(f"[q{idx:02d}] no clean image"); return
    out = stamp_corner(Image.open(src))
    out.convert("RGB").save(os.path.join(OUT, f"q{idx:02d}_final.png"))
    print(f"[q{idx:02d}] stamped -> q{idx:02d}_final.png")


def parse_indices(args):
    if args.indices:
        return [int(x) for x in args.indices.split(",") if x.strip()]
    start = args.start or 1
    return list(range(start, start + (args.count or len(QUOTES))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dry", "gen", "stamp"])
    ap.add_argument("--indices"); ap.add_argument("--count", type=int); ap.add_argument("--start", type=int)
    args = ap.parse_args()
    idxs = [i for i in parse_indices(args) if 1 <= i <= len(QUOTES)]
    os.makedirs(OUT, exist_ok=True)

    if args.mode == "dry":
        for i in idxs:
            print(f"\n===== q{i:02d}  keyword='{QUOTES[i-1][0]}' =====\n{build_prompt(i)}")
        print(f"\n{len(idxs)} prompts. gen cost ≈ ${len(idxs)*COST_PER_IMAGE:.2f}")
        return
    if args.mode == "stamp":
        for i in idxs:
            stamp_one(i)
        return
    print(f"About to gen {len(idxs)} image(s): q{idxs[0]:02d}..q{idxs[-1]:02d}  ≈ ${len(idxs)*COST_PER_IMAGE:.2f}")
    key = load_key()
    uri = "data:image/png;base64," + base64.b64encode(open(CROP, "rb").read()).decode()
    ok = 0
    for i in idxs:
        if gen_one(key, uri, i):
            stamp_one(i); ok += 1
    print(f"done: {ok}/{len(idxs)} -> {OUT}")


if __name__ == "__main__":
    main()
