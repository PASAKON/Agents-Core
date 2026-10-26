"""Composite kit overlays over real "ขายชื่อ" EP1 frames and lay them out as one numbered contact sheet."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

K = Path(sys.argv[1]).resolve()
F, O, T = K / "frames", K / "overlays", K / "tiles"
T.mkdir(exist_ok=True)


def frame(t):
    return Image.open(F / f"f_{t}.png").convert("RGBA")


def bw(im):
    """Flashback look, v2 theme: black and white with a vignette to black (was sepia in v1)."""
    s = ImageEnhance.Contrast(ImageOps.grayscale(im.convert("RGB"))).enhance(1.12).convert("RGBA")
    w, h = s.size
    vig = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vig).ellipse((-w * 0.25, -h * 0.12, w * 1.25, h * 1.12), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(160))
    return Image.composite(s, Image.new("RGBA", (w, h), (0, 0, 0, 255)), vig)


def desat(im):
    return ImageEnhance.Brightness(ImageEnhance.Color(im.convert("RGB")).enhance(0.3)).enhance(0.78).convert("RGBA")


def blur(im):
    return im.filter(ImageFilter.GaussianBlur(16))


def page(_):
    return Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))


TILES = [
    ("โลโก้เดิมของเพจ ไม่วาดใหม่", page, None, ["emblem"]),
    ("ลายน้ำ (มุมซ้ายบน ตลอดเรื่อง)", frame, "78", ["wm"]),
    ("ฟอนต์ + สี ทอง ขาว ดำ", page, None, ["fonts"]),
    ("ข้ามเวลา", frame, "66", ["wm", "skip"]),
    ("ย้อนเวลา วันเดียวกัน (ใช้หลัง Hook)", frame, "141.4", ["wm", "rewcard"]),
    ("ย้อนอดีต: ภาพขาวดำ + ป้ายอดีต", (lambda t: bw(frame(t))), "30", ["wm", "flash", "ftag"]),
    ("กลับปัจจุบัน", frame, "30", ["wm", "now"]),
    ("ป้ายสถานที่ + เวลา", frame, "78", ["wm", "place"]),
    ("ชื่อตัวร้าย พื้นดำ", frame, "132", ["wm", "name"]),
    ("ชื่อตัวดี พื้นขาว (ใหม่)", frame, "0", ["wm", "namegood"]),
    ("หัวตอน ที่ 0:12-0:15", (lambda t: blur(frame(t))), "132", ["title"]),
    ("รู้ไว้: ความรู้ระหว่างเรื่อง (ใหม่)", frame, "66", ["wm", "fact"]),
    ("มุก AI หลุด: หยุดภาพ + สแตมป์ NG", (lambda t: desat(frame(t))), "141.4", ["wm", "ng"]),
    ("มุก AI หลุด: กรอกลับ", frame, "141.4", ["wm", "rew"]),
    ("มุก AI หลุด: เทค 2 (เล่นต่อ)", frame, "140.5", ["wm", "take2"]),
    ("ข้อคิดจากตอนนี้ ก่อนการ์ดจบ (ใหม่)", (lambda t: blur(frame(t))), "0", ["lesson"]),
    ("ท้ายตอน: ฉากหลุด AI", (lambda t: desat(frame(t))), "141.4", ["blooper"]),
    ("การ์ดจบ + คำถามค้างไปตอนหน้า", (lambda t: blur(frame(t))), "30", ["end"]),
    ("ซับไทย (ข้อเสนอ ดูแบบปิดเสียง)", frame, "132", ["wm", "sub"]),
    ("พื้นที่ปลอดภัยบน Reels", frame, "66", ["safe"]),
]

for i, (label, bg, t, layers) in enumerate(TILES, 1):
    im = bg(t).convert("RGBA")
    if bg is page:
        im = Image.new("RGBA", (1080, 1920), (10, 10, 10, 255))
    for name in layers:
        im.alpha_composite(Image.open(O / f"{name}.png").convert("RGBA"))
    im.convert("RGB").save(T / f"{i:02d}.png")

COLS, TW, TH, GAP, LAB, TOP = 5, 360, 640, 24, 76, 230
rows = (len(TILES) + COLS - 1) // COLS
W = COLS * TW + (COLS + 1) * GAP
H = TOP + rows * (TH + LAB + GAP) + GAP
sheet = Image.new("RGB", (W, H), (10, 10, 10))
d = ImageDraw.Draw(sheet)
ft = ImageFont.truetype(str(K / "fonts/Taviraj-SemiBold.ttf"), 30)
fh = ImageFont.truetype(str(K / "fonts/Taviraj-Bold.ttf"), 64)
fs = ImageFont.truetype(str(K / "fonts/Taviraj-Medium.ttf"), 32)
d.text((GAP, 28), "ILAG ชุดประจำช่อง v2 (ร่าง) ตอบเป็นเบอร์ได้เลย", font=fh, fill=(247, 198, 78))
d.text((GAP, 112), "ธีมใหม่ ทอง ขาว ดำ ตามดอกบัวในโลโก้ ตัวดีอยู่ฝั่งขาว ตัวร้ายอยู่ฝั่งดำ / ฟอนต์ OFL ใช้ฟรีถาวร",
       font=fs, fill=(235, 235, 235))
d.text((GAP, 160), "พื้นหลังคือเฟรมจริงจากเรื่องขายชื่อ EP1 / สแตมป์ NG ในตัวอย่างวางบนเทคปกติ ของจริงใช้เทคที่ AI พลาดจริง",
       font=fs, fill=(190, 190, 190))
for i in range(len(TILES)):
    r, c = divmod(i, COLS)
    x = GAP + c * (TW + GAP)
    y = TOP + r * (TH + LAB + GAP)
    tile = Image.open(T / f"{i + 1:02d}.png").resize((TW, TH), Image.LANCZOS)
    sheet.paste(tile, (x, y))
    d.rounded_rectangle((x, y + TH + 8, x + 58, y + TH + 58), 10, fill=(247, 198, 78))
    d.text((x + 29, y + TH + 33), str(i + 1), font=ft, fill=(10, 10, 10), anchor="mm")
    words, line, lines = TILES[i][0].split(" "), "", []
    for w in words:
        if d.textlength(line + w + " ", font=ft) > TW - 70:
            lines.append(line.strip())
            line = ""
        line += w + " "
    lines.append(line.strip())
    for j, ln in enumerate(lines[:2]):
        d.text((x + 68, y + TH + 10 + j * 34), ln, font=ft, fill=(235, 235, 240))
sheet.save(K / "out" / "ilag-kit-sheet-v2.jpg", quality=90)
print(sheet.size)
