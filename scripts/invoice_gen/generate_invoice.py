#!/usr/bin/env python3
"""
Invoice / Quotation PDF generator — FlowAccount-style, Thai.

Reads a JSON data file, renders an HTML template, then prints to PDF via
headless Google Chrome (no third-party deps). The two signature blocks at
the bottom are left BLANK so the document can be signed by hand or by
inserting a signature image afterwards.

Usage:
    python3 generate_invoice.py <data.json> [out.pdf]

Data schema (see sample_axi.json):
    doc_type   : "quotation" | "invoice"   -> ใบเสนอราคา / ใบแจ้งหนี้
    doc_no     : str                        e.g. "QT2026030001"
    date       : str (DD/MM/YYYY)
    due_date   : str (invoice only, optional)
    accent     : str hex (optional; default orange for QT, blue for INV)
    seller     : {name, address}
    contact    : str (optional)
    customer   : {name, lines: [str, ...]}
    items      : [{desc, sub:[str,...], qty, unit, amount?}]
    currency   : "THB" | "USD"
    total      : number (optional; default = sum of item amounts)
    fx_rate    : str (optional)   e.g. "1 USD = 30.939 บาท"
    amount_words : str (optional) e.g. "(ห้าหมื่นบาทถ้วน)"
    notes      : [str, ...]
    sign_left_label   : str (optional)  default ผู้สั่งซื้อสินค้า / ผู้รับสินค้า / บริการ
    customer_sign_name: str (optional)  default = customer.name
    footer     : str (optional)         small line at the very bottom
"""
import html
import json
import os
import subprocess
import sys

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
* { box-sizing: border-box; }
@page { size: A4; margin: 0; }
html, body { margin: 0; padding: 0; }
body {
  font-family: 'Sarabun','Noto Sans Thai','Thonburi',sans-serif;
  font-size: 13px; color: #2b2b2b; -webkit-print-color-adjust: exact;
}
.page { position: relative; width: 210mm; min-height: 297mm; padding: 16mm 14mm; }
.corner { position: absolute; top: 0; right: 0; width: 0; height: 0;
  border-top: 64px solid var(--accent); border-left: 64px solid transparent; }
.title { text-align: right; color: var(--accent); }
.title h1 { margin: 0; font-size: 26px; font-weight: 700; }
.title .sub { font-size: 13px; color: var(--accent); }
.head { display: flex; justify-content: space-between; margin-top: 6px; }
.seller .name { font-weight: 600; }
.seller .addr { color: #555; max-width: 78mm; line-height: 1.45; margin-top: 2px; }
.meta { border-collapse: collapse; min-width: 70mm; }
.meta td { padding: 2px 6px; vertical-align: top; }
.meta td:first-child { color: var(--accent); white-space: nowrap; }
.cust { margin-top: 14px; }
.cust .lbl { color: var(--accent); }
.cust .name { font-weight: 600; }
.cust .ln { color: #555; line-height: 1.4; }
table.items { width: 100%; border-collapse: collapse; margin-top: 16px; }
table.items thead td { border-bottom: 1.5px solid #888; color: #555;
  padding: 6px 8px; font-weight: 400; }
table.items tbody td { padding: 6px 8px; vertical-align: top;
  border-bottom: 1px solid #e5e5e5; }
.c { text-align: center; } .r { text-align: right; white-space: nowrap; }
td .desc { font-weight: 400; }
td .sub { color: #666; font-size: 12px; line-height: 1.5; }
.totals { display: flex; justify-content: flex-end; margin-top: 10px; }
.totals table { border-collapse: collapse; min-width: 80mm; }
.totals td { padding: 4px 8px; }
.totals td.k { color: var(--accent); text-align: right; }
.totals td.v { text-align: right; white-space: nowrap; }
.fx { color: var(--accent); margin-top: 8px; }
.words { margin-top: 6px; }
.notes { margin-top: 16px; }
.notes .lbl { color: var(--accent); }
.notes div { line-height: 1.5; }
.signs { display: flex; justify-content: space-between; margin-top: 32px; gap: 24px;
  page-break-inside: avoid; }
.signs .col { width: 48%; }
.signs .inname { margin-bottom: 42px; }
.sigrow { display: flex; gap: 16px; }
.sigcell { flex: 1; text-align: center; }
.sigline { border-bottom: 1px solid #333; height: 0; margin-bottom: 4px; }
.siglabel { color: #555; font-size: 12px; }
.foot { text-align: center; color: #aaa; font-size: 11px; margin-top: 24px; }
"""

LABELS = {
    "th": {
        "quotation": "ใบเสนอราคา", "invoice": "ใบแจ้งหนี้", "original": "ต้นฉบับ",
        "no": "เลขที่", "date": "วันที่", "due": "ครบกำหนด", "seller": "ผู้ขาย", "contact": "ผู้ติดต่อ",
        "customer": "ลูกค้า", "desc": "รายละเอียด", "qty": "จำนวน", "unit": "ราคาต่อหน่วย", "amount": "ยอดรวม",
        "subtotal": "รวมเป็นเงิน", "grandtotal": "จำนวนเงินรวมทั้งสิ้น", "fx": "อัตราแลกเปลี่ยน", "notes": "หมายเหตุ",
        "for": "ในนาม", "received": "ผู้รับสินค้า / บริการ", "ordered": "ผู้สั่งซื้อสินค้า",
        "approved": "ผู้อนุมัติ", "sdate": "วันที่", "baht": "บาท",
    },
    "en": {
        "quotation": "QUOTATION", "invoice": "INVOICE", "original": "ORIGINAL",
        "no": "No.", "date": "Date", "due": "Due Date", "seller": "Seller", "contact": "Contact",
        "customer": "Customer", "desc": "Description", "qty": "Qty", "unit": "Unit Price", "amount": "Amount",
        "subtotal": "Subtotal", "grandtotal": "Grand Total", "fx": "Exchange Rate", "notes": "Notes",
        "for": "For", "received": "Received by", "ordered": "Ordered by",
        "approved": "Approved by", "sdate": "Date", "baht": "THB",
    },
}


def esc(s):
    return html.escape(str(s))


def money(n):
    return f"{float(n):,.2f}"


def render_html(d):
    is_inv = d["doc_type"] == "invoice"
    L = LABELS.get(d.get("lang", "th"), LABELS["th"])
    accent = d.get("accent") or ("#2E9BD6" if is_inv else "#E8821E")
    title = L["invoice"] if is_inv else L["quotation"]
    subtitle = d.get("subtitle", L["original"] if is_inv else "")
    cur = d.get("currency", "THB")
    suffix = L["baht"] if cur == "THB" else cur

    rows = ""
    total = 0.0
    for i, it in enumerate(d["items"], 1):
        amt = it.get("amount", float(it["qty"]) * float(it["unit"]))
        total += amt
        subs = "".join(f'<div class="sub">{esc(s)}</div>' for s in it.get("sub", []))
        rows += (
            f'<tr><td class="c">{i}</td>'
            f'<td><div class="desc">{esc(it["desc"])}</div>{subs}</td>'
            f'<td class="r">{esc(it["qty"])}</td>'
            f'<td class="r">{money(it["unit"])}</td>'
            f'<td class="r">{money(amt)}</td></tr>'
        )
    grand = d.get("total", total)

    meta = (
        f'<tr><td>{L["no"]}</td><td>{esc(d["doc_no"])}</td></tr>'
        f'<tr><td>{L["date"]}</td><td>{esc(d["date"])}</td></tr>'
    )
    if is_inv and d.get("due_date"):
        meta += f'<tr><td>{L["due"]}</td><td>{esc(d["due_date"])}</td></tr>'
    meta += f'<tr><td>{L["seller"]}</td><td>{esc(d["seller"]["name"])}</td></tr>'
    if d.get("contact"):
        meta += f'<tr><td>{L["contact"]}</td><td>{esc(d["contact"])}</td></tr>'

    cust_lines = "".join(f'<div class="ln">{esc(l)}</div>' for l in d["customer"].get("lines", []))
    fx = f'<div class="fx">{L["fx"]}&nbsp;&nbsp;{esc(d["fx_rate"])}</div>' if d.get("fx_rate") else ""
    words = f'<div class="words">{esc(d["amount_words"])}</div>' if d.get("amount_words") else ""
    notes_items = "".join(f"<div>{esc(n)}</div>" for n in d.get("notes", []))
    notes = f'<div class="notes"><div class="lbl">{L["notes"]}</div>{notes_items}</div>' if notes_items else ""

    sign_left = d.get("sign_left_label", L["received"] if is_inv else L["ordered"])
    cust_sign = d.get("customer_sign_name", d["customer"]["name"])
    foot = f'<div class="foot">{esc(d["footer"])}</div>' if d.get("footer") else ""

    return f"""<!DOCTYPE html><html lang="th"><head><meta charset="utf-8">
<style>:root{{--accent:{accent};}}{CSS}</style></head>
<body><div class="page">
  <div class="corner"></div>
  <div class="title"><h1>{title}</h1><div class="sub">{esc(subtitle)}</div></div>
  <div class="head">
    <div class="seller"><div class="name">{esc(d["seller"]["name"])}</div>
      <div class="addr">{esc(d["seller"]["address"])}</div></div>
    <table class="meta">{meta}</table>
  </div>
  <div class="cust"><div class="lbl">{L["customer"]}</div>
    <div class="name">{esc(d["customer"]["name"])}</div>{cust_lines}</div>
  <table class="items">
    <thead><tr><td class="c">#</td><td>{L["desc"]}</td><td class="r">{L["qty"]}</td>
      <td class="r">{L["unit"]}</td><td class="r">{L["amount"]}</td></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="totals"><table>
    <tr><td class="k">{L["subtotal"]}</td><td class="v">{money(grand)} {suffix}</td></tr>
    <tr><td class="k">{L["grandtotal"]}</td><td class="v">{money(grand)} {suffix}</td></tr>
  </table></div>
  {fx}{words}{notes}
  <div class="signs">
    <div class="col"><div class="inname">{L["for"]} {esc(cust_sign)}</div>
      <div class="sigrow">
        <div class="sigcell"><div class="sigline"></div><div class="siglabel">{esc(sign_left)}</div></div>
        <div class="sigcell"><div class="sigline"></div><div class="siglabel">{L["sdate"]}</div></div>
      </div></div>
    <div class="col"><div class="inname">{L["for"]} {esc(d["seller"]["name"])}</div>
      <div class="sigrow">
        <div class="sigcell"><div class="sigline"></div><div class="siglabel">{L["approved"]}</div></div>
        <div class="sigcell"><div class="sigline"></div><div class="siglabel">{L["sdate"]}</div></div>
      </div></div>
  </div>
  {foot}
</div></body></html>"""


def generate_one(d, out_pdf=None):
    if not out_pdf:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "invoices")
        out_dir = os.path.abspath(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        out_pdf = os.path.join(out_dir, f"{d['doc_no']}.pdf")

    html_str = render_html(d)
    html_path = out_pdf.replace(".pdf", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_str)

    if not os.path.exists(CHROME):
        print(f"HTML written: {html_path}\nChrome not found at {CHROME}; open the HTML and Print > Save as PDF.")
        return out_pdf

    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         "--virtual-time-budget=3000", f"--print-to-pdf={out_pdf}", f"file://{html_path}"],
        check=True, capture_output=True,
    )
    print(f"PDF:  {out_pdf}")
    return out_pdf


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)

    # A JSON list = batch: generate one PDF per invoice object.
    if isinstance(data, list):
        for d in data:
            generate_one(d)
    else:
        generate_one(data, sys.argv[2] if len(sys.argv) > 2 else None)


if __name__ == "__main__":
    main()
