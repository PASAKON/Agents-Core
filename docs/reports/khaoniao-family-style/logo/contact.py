from PIL import Image, ImageDraw, ImageFont
import glob
D = "/opt/MoonieXHQ/Assets/Agents/Core/khaoniao-family/page-art/logo"
font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F = ImageFont.truetype(font, 54); S = ImageFont.truetype(font, 24)
W, rowh, pad = 1560, 580, 30
sheet = Image.new("RGB", (W, 60 + 3 * rowh), (245, 245, 245))
d = ImageDraw.Draw(sheet)
d.text((pad, 14), "Logo lettering for the page name - pick L1, L2 or L3 (cover C3 + profile P3)", fill=(30, 30, 30), font=S)
names = {1: "gold serif", 2: "sticker", 3: "kid hand"}
for i in (1, 2, 3):
    y = 60 + (i - 1) * rowh
    d.text((pad, y + 6), f"L{i}", fill=(20, 20, 20), font=F)
    d.text((pad, y + 70), names[i], fill=(90, 90, 90), font=S)
    cov = Image.open(f"{D}/logo-{i}-cover.png").convert("RGB").resize((960, 540))
    sheet.paste(cov, (170, y))
    dd = ImageDraw.Draw(sheet)
    top, bot = y + int(149 * 540 / 941), y + int(792 * 540 / 941)
    dd.rectangle((170, top, 170 + 959, bot), outline=(230, 30, 30), width=3)
    dd.text((176, bot + 6), "red = desktop crop 2.6:1", fill=(200, 30, 30), font=S)
    pr = Image.open(f"{D}/logo-{i}-profile.png").convert("RGBA").resize((400, 400))
    bg = Image.new("RGBA", (400, 400), (150, 160, 175, 255)); bg.alpha_composite(pr)
    sheet.paste(bg.convert("RGB"), (1160, y))
    mk = Image.open(f"{D}/logo-{i}-mark.png").convert("RGBA").resize((400, 130))
    bg2 = Image.new("RGBA", (400, 130), (70, 90, 120, 255)); bg2.alpha_composite(mk)
    sheet.paste(bg2.convert("RGB"), (1160, y + 410))
sheet.save(f"{D}/contact-logo.jpg", quality=88)
print(sheet.size)
