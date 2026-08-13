#!/usr/bin/env python3
"""Render the Frost Knight (Minecraft Marketplace) project BUDGET as a PDF.

HTML -> PDF via headless Google Chrome (no third-party deps) — same method as
scripts/invoice_gen/generate_invoice.py. Sarabun web font for Thai.

  python3 scripts/frost_knight_budget_pdf.py [out.pdf]
"""
import os, sys, subprocess, html

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DOC_DATE = "22/06/2026"
OUT_DEFAULT = os.path.expanduser(
    "~/Desktop/Frost-Knight-Minecraft/Frost-Knight-Budget.pdf")

# (section_title, [(id, desc, who, price), ...])
SECTIONS = [
    ("A. BOSS", [
        ("A1", "Boss model + texture", "จ้าง", "$150–300"),
        ("A2", "Boss animation set (idle / walk / swing / hit / sleep / death + 2 สกิล)", "จ้าง", "$100–220"),
        ("A3", "Boss bar art", "จ้าง", "$10–40"),
        ("A4", "Boss ดาบน้ำแข็ง — model + texture", "จ้าง", "$30–70"),
    ]),
    ("B. CLASSES ×3  (Archer / Knight / Wizard)", [
        ("B1", "Class player-animation set (3–5 ท่า + controller) — งานเฉพาะทาง", "specialist", "$100–250 /class → $300–750"),
        ("B2", "Class armor / ชุด — model + texture  (optional)", "จ้าง", "$40–120 /class → $120–360"),
    ]),
    ("C. WEAPONS (class)", [
        ("C1", "3 อาวุธ base (ขั้น 1) — model + texture", "จ้าง", "$25–60 /ชิ้น → $75–180"),
        ("C2", "ขั้น 2 + ขั้น 3 variant (6 ตัว, reuse ถูกลง)  (optional)", "จ้าง", "$15–40 /ชิ้น → $90–240"),
    ]),
    ("D. SHARED", [
        ("D1", "VFX / particle (เวท / ลูกศร / frost / slam)", "จ้าง / JSON เอง", "$30–120"),
        ("D2", "Sound (เพลง + SFX)", "royalty-free / จ้าง", "$0–150"),
        ("D3", "Build อารีน่า", "Champ", "$0"),
        ("D4", "Trailer", "Champ / editor", "$0–150"),
        ("D5", "Key art + screenshots", "gen แล้ว", "$0–30"),
        ("D6", "โค้ด (behavior / controller / script API / class system / packaging)", "นาย + Claude", "$0"),
        ("D7", "ประกอบ + ส่ง Partner review", "Champ", "$0"),
    ]),
]

SCENARIOS = [
    ("MVP  (งบ ~$500)", "Boss (เรียบลง) + 1 class + 1 อาวุธ + VFX/sound น้อย", "~$350–700"),
    ("Lean v1", "Boss + 3 class + อาวุธ base (ไม่มี armor / tier)", "~$700–1,500"),
    ("Full MMO", "+ armor 3 class + อาวุธ 3 ขั้น + trailer / sound เต็ม", "~$1,000–2,000+"),
]

NOTES = [
    "เงินสดออก = ค่า <b>art อย่างเดียว</b> — code / build / ประกอบ / ส่งรีวิว = $0 (เป็นส่วนหุ้นของนาย & Champ)",
    "<b>B1 (player animation 3 class) = ก้อนใหญ่สุด + เสี่ยงสุด</b> (งานเฉพาะทาง Bedrock, ราคาแกว่ง) → จ้าง specialist เท่านั้น",
    "<b>งบ $500 = พอแค่ MVP 1 class.</b> Full 3-class จริง ~$1,000–1,500",
    "ราคาขึ้นกับ network ของ Champ (ถูกกว่าได้ถ้าคอนเนคดี / แพงกว่าถ้าพรีเมียม) — นายถือเงิน + อนุมัติรายตัว คุมได้",
    "ตัวเลขนี้ = โปรดักต์ตัวแรก. Boss ตัวที่ 2 ถูกลงมาก (โค้ด + framework reuse, จ้างแค่ art ใหม่)",
    "ประมาณการสำหรับจ้าง freelancer Bedrock มือกลาง (USD). คืนทุนนายก่อน แล้วค่อยแบ่งกำไร 50/50",
]


def esc(s):
    return html.escape(str(s))


def render_html():
    body = []
    for title, rows in SECTIONS:
        body.append(f'<tr class="sec"><td colspan="4">{esc(title)}</td></tr>')
        for _id, desc, who, price in rows:
            zero = ' class="zero"' if price == "$0" else ""
            body.append(
                f'<tr><td class="id">{esc(_id)}</td><td>{esc(desc)}</td>'
                f'<td class="who">{esc(who)}</td><td class="r"{zero}>{esc(price)}</td></tr>')
    rows_html = "\n".join(body)

    scen = "\n".join(
        f'<tr><td class="sname">{esc(n)}</td><td>{esc(g)}</td><td class="r tot">{esc(t)}</td></tr>'
        for n, g, t in SCENARIOS)

    notes = "\n".join(f"<li>{n}</li>" for n in NOTES)

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
* {{ box-sizing: border-box; }}
@page {{ size: A4; margin: 0; }}
html,body {{ margin:0; padding:0; }}
body {{ font-family:'Sarabun','Noto Sans Thai','Thonburi',sans-serif; color:#1f2933;
  font-size:12.5px; -webkit-print-color-adjust:exact; }}
.page {{ width:210mm; min-height:297mm; padding:15mm 14mm; position:relative; }}
.corner {{ position:absolute; top:0; right:0; width:0; height:0;
  border-top:62px solid #2c5f8a; border-left:62px solid transparent; }}
h1 {{ margin:0; font-size:23px; color:#2c5f8a; font-weight:700; }}
.sub {{ color:#52606d; margin-top:3px; font-size:12px; }}
.meta {{ color:#7b8794; font-size:11px; margin-top:2px; }}
table {{ width:100%; border-collapse:collapse; margin-top:14px; }}
.items td {{ padding:5px 8px; border-bottom:1px solid #e4e7eb; vertical-align:top; }}
.items tr.sec td {{ background:#eef3f8; color:#2c5f8a; font-weight:700; padding:6px 8px;
  border-bottom:1.5px solid #c9d6e2; }}
.items td.id {{ color:#9aa5b1; width:34px; }}
.items td.who {{ color:#52606d; white-space:nowrap; width:96px; }}
.r {{ text-align:right; white-space:nowrap; }}
.items td.zero {{ color:#3a9d5d; }}
h2 {{ font-size:14px; color:#2c5f8a; margin:20px 0 0; }}
.scen td {{ padding:7px 8px; border-bottom:1px solid #e4e7eb; }}
.scen td.sname {{ font-weight:600; white-space:nowrap; }}
.scen td.tot {{ font-weight:700; color:#2c5f8a; }}
.notes {{ margin:10px 0 0; padding-left:18px; color:#3e4c59; line-height:1.6; }}
.notes li {{ margin-bottom:3px; }}
.foot {{ margin-top:18px; color:#9aa5b1; font-size:10.5px; border-top:1px solid #e4e7eb;
  padding-top:8px; }}
</style></head><body><div class="page"><div class="corner"></div>
<h1>Frost Knight — Project Budget</h1>
<div class="sub">Minecraft Bedrock Marketplace — MMORPG Boss + 3 Classes</div>
<div class="meta">ประมาณการต้นทุน (จ้างศิลปิน Bedrock มือกลาง, USD) · {esc(DOC_DATE)}</div>

<table class="items">{rows_html}</table>

<h2>สรุปตามขอบเขต (เลือกได้)</h2>
<table class="scen">{scen}</table>

<h2>หมายเหตุ</h2>
<ul class="notes">{notes}</ul>

<div class="foot">ตัวเลขเป็นการประมาณการเพื่อวางแผนงบ ไม่ใช่ใบเสนอราคาผูกพัน · ราคาจริงยืนยันกับศิลปิน/Champ รายชิ้น</div>
</div></body></html>"""


def main():
    out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else OUT_DEFAULT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    html_path = "/tmp/frost_knight_budget.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(render_html())
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         "--virtual-time-budget=3000", f"--print-to-pdf={out}", f"file://{html_path}"],
        check=True, capture_output=True)
    print("PDF ->", out)


if __name__ == "__main__":
    main()
