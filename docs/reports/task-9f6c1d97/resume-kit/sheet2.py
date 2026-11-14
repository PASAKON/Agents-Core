# sheet2.py out.jpg cols thumbw first last  (reads stills/ep04/EP04-S###.png; missing = black "pending")
import sys, os
from PIL import Image, ImageDraw, ImageFont
out, cols, tw, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
th=int(tw*9/16); ids=list(range(a,b+1)); rows=(len(ids)+cols-1)//cols
sh=Image.new('RGB',(cols*tw,rows*th),'black'); f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', max(14,tw//12))
for i,n in enumerate(ids):
    p='/opt/MoonieXHQ/Work/cn-series/stills/ep04/EP04-S%03d.png'%n
    x,y=(i%cols)*tw,(i//cols)*th
    d=ImageDraw.Draw(sh)
    if os.path.exists(p): sh.paste(Image.open(p).convert('RGB').resize((tw,th)),(x,y))
    else: d.text((x+10,y+th//2-10),'pending retry',fill='gray',font=f)
    d.rectangle((x,y,x+tw//4,y+tw//10),fill='black'); d.text((x+6,y+2),'%03d'%n,fill='yellow',font=f)
sh.save(out,quality=85)
