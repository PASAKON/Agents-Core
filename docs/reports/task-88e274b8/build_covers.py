"""Local, deterministic EP2 plate composites. No generation or network calls."""
from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps, features

OUT = Path('/root/MoonieXHQ/Work/task-88e274b8/out')
PLATES = Path('/opt/MoonieXHQ/Work/ghostrules-full/ep02/paper/img')
FONT = '/root/.fonts/NotoSansThai.ttf'
SIZE = (1280, 720)
RED = '#FF444C'
WHITE = '#FFFFFF'

def font(size):
    f = ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.RAQM)
    f.set_variation_by_name('Bold')
    return f

def text(im, words, xy, size, color):
    f = font(size)
    d = ImageDraw.Draw(im)
    box = d.textbbox(xy, words, font=f, anchor='lt', stroke_width=2)
    assert box[0] >= 30 and box[1] >= 25 and box[2] <= 1250 and box[3] <= 685, box
    # Soft black backing is shadow, not an additional text ink.
    shadow = Image.new('RGBA', SIZE)
    ImageDraw.Draw(shadow).text((xy[0]+2, xy[1]+5), words, font=f, anchor='lt', fill='black', stroke_width=6, stroke_fill='black')
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(im).text(xy, words, font=f, anchor='lt', fill=color)
    return list(box)

def shade(im, side):
    mask = Image.new('L', SIZE)
    values = []
    for y in range(720):
        for x in range(1280):
            t = x / 1280 if side == 'left' else (1279-x)/1280
            values.append(int(235 * max(0, 1-t/0.64)**1.3))
    mask.putdata(values)
    im.alpha_composite(Image.merge('RGBA', (Image.new('L',SIZE),)*3+(mask,)))

def make(name, plate, crop, side, lines):
    source = PLATES / (plate + '.png')
    original = Image.open(source).convert('RGB')
    assert 0 <= crop[0] < crop[2] <= original.width
    assert 0 <= crop[1] < crop[3] <= original.height
    im = original.crop(crop).resize(SIZE, Image.Resampling.LANCZOS)
    # Neutralise all existing skin warmth: no red face, ears or added blush.
    gray = ImageOps.grayscale(im)
    im = ImageOps.colorize(gray, '#060D16', '#DDE8ED')
    im = ImageEnhance.Contrast(im).enhance(1.12).convert('RGBA')
    shade(im, side)
    boxes = [text(im, *line) for line in lines]
    im = im.convert('RGB')
    im.save(OUT / name, optimize=True)
    return {'file':name, 'source':str(source), 'source_md5':hashlib.md5(source.read_bytes()).hexdigest(), 'crop':crop, 'text':[l[0] for l in lines], 'text_boxes':boxes, 'font_sizes':[l[2] for l in lines], 'size':SIZE, 'bytes':(OUT/name).stat().st_size}

def main():
    assert features.check('raqm'), 'Thai shaping requires libraqm'
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [
        make('cover_C_previous_clerk.png', 's61', (0,0,1672,941), 'left', [
            ('คนเก่า',(55,260),137,WHITE), ('ยังอยู่',(55,440),153,RED)]),
        make('cover_A_freezer.png', 's63', (190,0,1672,834), 'right', [
            ('ห้ามเปิด',(760,230),115,RED), ('ตู้แช่',(790,400),150,WHITE)]),
        make('cover_B_counter.png', 's28', (180,100,1672,939), 'right', [
            ('อย่ามอง',(775,150),113,WHITE), ('ข้างล่าง',(765,305),110,RED)]),
    ]
    strip = Image.new('RGB', (504,94))
    for i,row in enumerate(rows):
        strip.paste(Image.open(OUT/row['file']).resize((168,94),Image.Resampling.LANCZOS),(168*i,0))
    strip.save(OUT/'mobile_preview_strip.png')
    (OUT/'provenance.json').write_text(json.dumps({'order':['C','A','B'],'pillow':Image.__version__,'raqm':features.check('raqm'),'font':FONT,'font_md5':hashlib.md5(Path(FONT).read_bytes()).hexdigest(),'covers':rows},ensure_ascii=False,indent=2)+'\n')
    shutil.copyfile(Path(__file__).with_name('RESEARCH.md'), OUT/'RESEARCH.md')
    files = [OUT/row['file'] for row in rows]+[OUT/'mobile_preview_strip.png',OUT/'provenance.json',OUT/'RESEARCH.md']
    (OUT/'MD5SUMS').write_text(''.join(hashlib.md5(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
    print(json.dumps(rows,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
