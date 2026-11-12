"""Offline, two-ink paper covers and upload copy. No network or generation APIs."""
import hashlib
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path('/root/MoonieXHQ/Work/task-642b8fd9/out')
RED = '#C7192D'
WHITE = '#FFFFFF'
FONT = '/root/.fonts/NotoSansThai.ttf'
S = 2

def cover(key, normal, emphasis, motif):
    im = Image.new('RGB', (1280*S, 720*S), RED)
    d = ImageDraw.Draw(im)
    def poly(points, fill=WHITE):
        d.polygon([(int(x*S), int(y*S)) for x,y in points], fill=fill)
    def line(points, fill=WHITE, width=3):
        d.line([(int(x*S), int(y*S)) for x,y in points], fill=fill, width=width*S)
    def ellipse(box, fill=WHITE):
        d.ellipse(tuple(int(v*S) for v in box), fill=fill)
    rng = random.Random(42+motif)
    # Ragged outside edge and fibrous, screen-printed flecks, all in two inks.
    for x in range(0,1280,13):
        poly([(x,0),(x+14,0),(x+14,rng.randint(5,12)),(x,rng.randint(5,12))])
        poly([(x,720),(x+14,720),(x+14,720-rng.randint(5,12)),(x,720-rng.randint(5,12))])
    for _ in range(1700):
        x,y=rng.randrange(1280),rng.randrange(720)
        line([(x,y),(x+rng.randrange(1,4),y)], width=1)
    # Left headline uses white normal copy and larger red emphasis on torn white stock.
    def txt(text, x,y,size,fill,max_width):
        font=ImageFont.truetype(FONT,size*S)
        if hasattr(font,'set_variation_by_axes'):
            try: font.set_variation_by_axes([800,100])
            except (OSError,ValueError): pass
        while d.textlength(text,font=font)>max_width*S:
            size-=1; font=ImageFont.truetype(FONT,size*S)
        d.text((x*S,y*S),text,font=font,fill=fill,stroke_width=S,stroke_fill=fill)
        return size
    sizes=[txt(normal,58,155,57,WHITE,600)]
    poly([(35,295),(654,280),(670,300),(655,327),(671,350),(659,380),(672,413),(655,447),(668,480),(651,516),(39,529),(48,501),(32,470),(45,439),(32,405),(47,370),(33,338)])
    sizes.append(txt(emphasis,58,325,92,RED,580))
    assert sizes[1]>sizes[0], sizes
    # Angled shop floor and fixtures behind the single story-specific hero motif.
    line([(710,625),(1250,625)],width=4)
    line([(715,675),(1247,675)],width=2)
    for x in [750,910,1070,1230]: line([(1000,460),(x,710)],width=2)
    if motif==1:
        # Seven-rule sheet with one dangerous red rule; text deliberately not invented.
        poly([(795,86),(1195,118),(1213,551),(803,598),(781,567),(791,540),(774,505),(788,475),(773,440)])
        poly([(815,66),(922,74),(918,112),(808,104)],RED)
        poly([(1093,100),(1204,109),(1200,147),(1089,138)],RED)
        for n in range(7):
            y=161+n*47
            line([(838,y),(1149,y+12)],RED,4 if n!=4 else 16)
        poly([(1062,516),(1249,552),(1249,612),(1032,562)],RED)
        line([(1062,516),(1249,552)],WHITE,3)
    elif motif==2:
        # Woman in red: white face/neck, red paper dress, white hair contour. No red face/ears.
        poly([(800,91),(1198,91),(1198,606),(800,606)])
        poly([(816,106),(1182,106),(1182,592),(816,592)],RED)
        poly([(927,150),(964,115),(1019,113),(1060,147),(1092,297),(1052,315),(934,304),(905,276)])
        poly([(939,159),(973,136),(1029,149),(1053,273),(1023,290),(949,280)],RED)
        poly([(997,167),(1029,173),(1038,228),(1019,257),(998,239)])
        poly([(1005,251),(1025,253),(1030,290),(995,291)])
        poly([(950,284),(1055,279),(1122,575),(881,575)])
        poly([(957,303),(1046,299),(1099,558),(902,558)],RED)
        line([(948,328),(929,458)],WHITE,6)
        line([(1053,327),(1083,446)],WHITE,6)
        # Wilted garland in her hand.
        for x,y in [(1080,458),(1092,470),(1095,486),(1083,499),(1070,485)]: ellipse((x-6,y-6,x+6,y+6))
        ellipse((960,587,1048,597))
    else:
        # Previous clerk trapped behind freezer glass; white face/hands, red negative space.
        poly([(766,90),(1212,112),(1225,601),(754,620)])
        poly([(789,117),(1185,135),(1194,572),(781,592)],RED)
        line([(1151,293),(1155,408)],WHITE,12)
        poly([(898,470),(916,345),(1078,346),(1101,470)])
        poly([(925,363),(1062,363),(1080,468),(915,468)],RED)
        ellipse((947,228,1035,338))
        poly([(944,258),(951,222),(1015,214),(1041,251),(1011,246),(995,259)],RED)
        line([(964,280),(978,280)],RED,5)
        line([(1006,280),(1020,280)],RED,5)
        ellipse((981,304,998,324),RED)
        for x,y in [(863,289),(1100,285)]:
            ellipse((x-21,y,x+21,y+57))
            for k in range(4): line([(x-17+k*11,y+10),(x-21+k*12,y-38+(k%2)*8)],WHITE,7)
            line([(x,y+48),(x+(-10 if x<900 else 10),y+100)],WHITE,16)
        for i in range(8): line([(797,149+i*53),(1172,161+i*53)],WHITE,1)
    # Exact two-colour palette, with high-resolution glyph shaping before reduction.
    im=im.resize((1280,720),Image.Resampling.LANCZOS)
    pal=Image.new('P',(1,1)); pal.putpalette([199,25,45,255,255,255]+[255,255,255]*254)
    im=im.quantize(palette=pal,dither=Image.Dither.NONE).convert('RGB')
    im.save(OUT/f'cover_{key}.png',optimize=True)
    return {'file':f'cover_{key}.png','normal':normal,'emphasis':emphasis,'normal_px':sizes[0],'emphasis_px':sizes[1]}

META = {
 'th': {'title':'กะดึกร้านสะดวกซื้อ กับกฎที่ห้ามเชื่อ', 'description':'นนท์รับงานกะดึกที่ร้านสะดวกซื้อริมคลอง คืนละ 5,000 บาท เพื่อดูแลแม่ที่ต้องไปโรงพยาบาล สิ่งที่ผู้จัดการส่งให้ไม่ใช่คู่มือคิดเงิน แต่เป็นกระดาษกฎเจ็ดข้อ เมื่อรอยเท้าเปียกเดินเข้าร้านเอง และจำนวนคนในกล้องไม่ตรงกับที่ตาเห็น เขาจะไว้ใจกฎบนกระดาษได้แค่ไหน?\n\nเรื่องเล่าสยองขวัญจบในเรื่องเดียว ถ่ายทอดด้วยภาพสไตล์กระดาษ จาก RED SEAL ARCHIVE'},
 'en': {'title':'The Night Shift Store and the Rule You Must Not Trust', 'description':'Non takes a night shift at a canal-side convenience store for 5,000 baht a night to support his mother, who needs hospital visits. The manager hands him seven rules instead of register training. When wet footprints enter on their own and the security camera shows more people than he can see, can he trust the paper?\n\nA complete, standalone horror story told through paper-style visuals. RED SEAL ARCHIVE.'},
 'id': {'title':'Toko Shift Malam dan Aturan yang Tak Boleh Dipercaya', 'description':'Non menerima pekerjaan shift malam di minimarket tepi kanal dengan upah 5.000 baht per malam demi ibunya yang harus berobat ke rumah sakit. Alih-alih mengajarinya memakai kasir, manajer menyerahkan tujuh aturan. Saat jejak kaki basah muncul sendiri dan kamera keamanan menampilkan lebih banyak orang daripada yang ia lihat, bisakah ia mempercayai aturan itu?\n\nKisah horor yang tamat dalam satu cerita, dengan visual bergaya kertas. RED SEAL ARCHIVE.'},
 'hi': {'title':'रात की पाली की दुकान और वह नियम जिस पर भरोसा मत करना', 'description':'अस्पताल जाने वाली अपनी माँ की मदद के लिए नॉन नहर के किनारे एक दुकान में रात की नौकरी करता है। हर रात की मज़दूरी 5,000 बाट है। मैनेजर कैश रजिस्टर चलाना सिखाने के बजाय उसे सात नियमों का कागज़ थमा देता है। जब गीले पैरों के निशान अपने आप अंदर आने लगते हैं और कैमरे में उसकी आँखों से ज़्यादा लोग दिखते हैं, तो क्या वह उन नियमों पर भरोसा कर सकता है?\n\nकागज़ की कला जैसे दृश्यों में प्रस्तुत एक संपूर्ण, स्वतंत्र डरावनी कहानी। RED SEAL ARCHIVE.'},
 'ja': {'title':'深夜のコンビニ、信じてはいけないルール', 'description':'通院が必要な母を支えるため、ノンは運河沿いのコンビニで一晩5,000バーツの夜勤を引き受ける。店長が渡したのはレジの説明ではなく、七つのルールが書かれた紙だった。誰もいないのに濡れた足跡が店内に現れ、防犯カメラには目で見えるより多くの人影が映る。その紙を信じていいのか。\n\n紙細工風の映像で描く、一話完結のホラーストーリー。RED SEAL ARCHIVE。'},
 'vi': {'title':'Ca đêm ở cửa hàng và quy tắc không được tin', 'description':'Để chăm lo cho mẹ phải đi bệnh viện, Non nhận ca đêm tại một cửa hàng tiện lợi ven kênh với mức lương 5.000 baht mỗi đêm. Thay vì hướng dẫn dùng máy tính tiền, quản lý đưa anh tờ giấy ghi bảy quy tắc. Khi những dấu chân ướt tự xuất hiện và camera an ninh cho thấy nhiều người hơn mắt anh nhìn thấy, anh có thể tin tờ giấy ấy không?\n\nMột câu chuyện kinh dị độc lập, có kết thúc trọn vẹn, được thể hiện bằng hình ảnh theo phong cách giấy. RED SEAL ARCHIVE.'},
 'es': {'title':'La tienda del turno de noche y la regla que no debes creer', 'description':'Non acepta el turno de noche en una tienda junto a un canal por 5.000 baht la noche para ayudar a su madre, que necesita ir al hospital. En vez de enseñarle a usar la caja, el encargado le entrega siete reglas. Cuando aparecen huellas mojadas sin que entre nadie y la cámara muestra más personas de las que él puede ver, ¿puede fiarse de ese papel?\n\nUna historia de terror independiente y completa, narrada con imágenes de estilo de papel recortado. RED SEAL ARCHIVE.'},
 'zh-TW': {'title':'便利商店的夜班：千萬別相信那條規則', 'description':'為了照顧需要到醫院看診的母親，Non 接下運河旁便利商店的夜班，每晚薪資五千泰銖。店長沒有教他操作收銀機，只交給他一張寫著七條規則的紙。當濕腳印自行走進店內，監視器裡的人影又比肉眼看到的更多時，他還能相信紙上的規則嗎？\n\n以紙藝風格影像呈現的獨立恐怖故事，故事完整完結。RED SEAL ARCHIVE。'},
 'zh-CN': {'title':'便利店的夜班：千万别相信那条规则', 'description':'为了照顾需要到医院看病的母亲，Non 接下运河旁便利店的夜班，每晚工资五千泰铢。店长没有教他操作收银机，只交给他一张写着七条规则的纸。当湿脚印自行走进店内，监控画面里的人影又比肉眼看到的更多时，他还能相信纸上的规则吗？\n\n以纸艺风格画面呈现的独立恐怖故事，故事完整完结。RED SEAL ARCHIVE。'},
}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    specs=[cover('A_rules','กฎร้านนี้','ห้ามเชื่อ',1),cover('B_customer','ลูกค้าคนนี้','ห้ามมอง',2),cover('C_freezer','คนก่อนหน้า','ยังอยู่',3)]
    (OUT/'cover_copy.json').write_text(json.dumps(specs,ensure_ascii=False,indent=2)+'\n')
    (OUT/'metadata.json').write_text(json.dumps(META,ensure_ascii=False,indent=2)+'\n')
    (OUT/'metadata.md').write_text('\n\n'.join(f'## {lang}\n\n{v["title"]}\n\n{v["description"]}' for lang,v in META.items())+'\n')
    (OUT/'titles.md').write_text('# ตัวเลือกชื่อเรื่อง\n\nA. กะดึกร้านสะดวกซื้อ กับกฎที่ห้ามเชื่อ\n\nB. คืนละ 5,000 บาท แต่ห้ามมองหน้าลูกค้า\n\nC. พนักงานคนก่อน ยังอยู่ในตู้แช่หลังร้าน\n')
    # Static deliverable gates, not claims of video/audio QA.
    import re
    assert set(META)=={'th','en','id','hi','ja','vi','es','zh-TW','zh-CN'}
    for lang,v in META.items():
        assert 0<len(v['title'])<=100
        assert 0<len(v['description'])<=5000
        assert not re.search(r'\bEP\s*\.?\s*\d*',v['title']+' '+v['description'],re.I)
    assert not any(c in str(META['th']) for c in '«»—')
    for p in OUT.glob('cover_*.png'):
        img=Image.open(p)
        assert img.size==(1280,720)
        assert set(img.getdata())=={(199,25,45),(255,255,255)}
        assert p.stat().st_size<2_000_000
    (OUT/'validation.json').write_text(json.dumps({'status':'PASS','covers':3,'dimensions':[1280,720],'palette':['#C7192D','#FFFFFF'],'thai_source_plus_translations':len(META),'translation_languages':list(META)[1:],'title_lengths':{k:len(v['title']) for k,v in META.items()},'paid_api_calls':0},indent=2)+'\n')
    files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name not in {'MD5SUMS','CMO_LETTER.md'})
    (OUT/'MD5SUMS').write_text(''.join(f'{hashlib.md5(p.read_bytes()).hexdigest()}  {p.name}\n' for p in files))
    print((OUT/'MD5SUMS').read_text())

if __name__=='__main__': main()
