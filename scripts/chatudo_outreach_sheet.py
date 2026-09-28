#!/usr/bin/env python3
"""Build the Chatudo outreach tracker (plan work package O1) as an .xlsx that Drive converts to a Google Sheet.

Why an .xlsx: the Drive OAuth this org holds has the `drive` scope but the Sheets API is not enabled in its
Cloud project (probed 2026-09-28: 403 "Google Sheets API has not been used in project 407008779435"). A
Drive upload with mimeType application/vnd.google-apps.spreadsheet converts the file, formulas included.

Tabs (Thai labels, CEO reads them):
  ร้าน           one row per shop: segment, owner, message variant, the draft, contact dates, day-3 / day-7
                 follow-up due dates, replied, reached owner, demo, pilot, and a "next action" formula.
  สรุปวันจันทร์    funnel counts for the Monday 10:00 review: per segment, per message variant, segment x
                 variant, per week, today's to-do counts, and the G1 check (31 Oct).
  ข้อความ         the 3 first-message variants (A/B/C) the CMO writes; {เจ้าของ} and {ร้าน} are filled in.
  วิธีใช้          how to use it, in five lines.

Every count is a formula, so nothing has to be run on Monday. The drafts are a mail-merge formula ($0, no
model call); per-shop AI drafting can be added later from a Claude Code session.

Usage:
  python3 scripts/chatudo_outreach_sheet.py --out /path/tracker.xlsx            # empty tracker
  python3 scripts/chatudo_outreach_sheet.py --out /path/t.xlsx --sample 12      # local self-test rows
Needs openpyxl.
"""
import argparse
import datetime as dt

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROWS = 500  # formula rows on the shop tab (the plan lists ~450 shops)
FIRST = 2   # first data row on the shop tab
LAST = FIRST + ROWS - 1

SEGMENTS = [
    "คอร์สออนไลน์ / สัมมนา",
    "ร้านจองคิว (ทำผม เล็บ สปา)",
    "ร้านเล็กขายของในแชท",
    "คลินิกความงาม",
]
VARIANTS = ["A", "B", "C"]
YES, NO = "ใช่", "ไม่"
OWNER_SOURCES = ["หน้าความโปร่งใสของเพจ", "เว็บไซต์", "กรมพัฒนาธุรกิจการค้า", "หน้าแบรนด์ / ผู้สอน", "อื่น ๆ"]
CHANNELS = ["Inbox เพจ (FB ส่วนตัว CEO)", "อีเมล", "Inbox เพจ + อีเมล"]
FIRST_MONDAY = dt.date(2026, 9, 28)  # week 1 of the plan: outreach starts Thu 1 Oct
WEEKS = 10
G1_DATE = dt.date(2026, 10, 31)

# column letter -> (header, width, kind); kind drives validation / number format
COLS = {
    "A": ("#", 5, "int"),
    "B": ("กลุ่ม", 24, "segment"),
    "C": ("ชื่อร้าน / เพจ", 26, "text"),
    "D": ("ลิงก์เพจ Facebook", 28, "text"),
    "E": ("ลิงก์ Meta Ad Library", 24, "text"),
    "F": ("เว็บไซต์ / LINE OA", 22, "text"),
    "G": ("ชื่อเจ้าของ", 18, "text"),
    "H": ("ได้ชื่อเจ้าของจาก", 20, "owner_src"),
    "I": ("อีเมลเจ้าของ", 22, "text"),
    "J": ("ข้อความแบบ", 10, "variant"),
    "K": ("ร่างข้อความแรก (เติมชื่อให้แล้ว)", 48, "formula"),
    "L": ("วันที่ทัก", 12, "date"),
    "M": ("ช่องทาง", 22, "channel"),
    "N": ("ตามครั้งที่ 1 ครบ (วันที่ 3)", 14, "formula_date"),
    "O": ("ตามครั้งที่ 1 ส่งแล้ว", 13, "date"),
    "P": ("ตามครั้งที่ 2 ครบ (วันที่ 7)", 14, "formula_date"),
    "Q": ("ตามครั้งที่ 2 ส่งแล้ว", 13, "date"),
    "R": ("ร้านตอบ", 9, "yesno"),
    "S": ("วันที่ตอบ", 12, "date"),
    "T": ("ถึงเจ้าของ", 10, "yesno"),
    "U": ("โทรแล้ว (วันที่)", 13, "date"),
    "V": ("เปิด demo (พักไว้)", 11, "yesno"),
    "W": ("ร้านนำร่อง", 10, "yesno"),
    "X": ("วันติดตั้ง", 12, "date"),
    "Y": ("ต้องทำต่อ", 18, "formula"),
    "Z": ("สัปดาห์ที่ทัก (จันทร์)", 13, "formula_date"),
    "AA": ("หมายเหตุ", 30, "text"),
}
DATE_FMT = "dd/mm/yyyy"
# COUNTIFS criteria. Not "<>": the local evaluator used for the self-test reads it differently from
# Sheets/Excel, and these two mean the same thing in all three (text of >=1 char; a real date).
NONEMPTY_TEXT = '"?*"'
HAS_DATE = '">0"'

HEAD_FILL = PatternFill("solid", fgColor="1F2937")
HEAD_FONT = Font(bold=True, color="FFFFFF")
CALC_FILL = PatternFill("solid", fgColor="F3F4F6")  # formula columns: do not type here
AMBER = PatternFill("solid", fgColor="FDE7C2")
GREEN = PatternFill("solid", fgColor="D6F2E0")
GREY = PatternFill("solid", fgColor="E5E7EB")

SHOP = "ร้าน"
SUM = "สรุปวันจันทร์"
MSG = "ข้อความ"
HOW = "วิธีใช้"


def q(sheet):
    return f"'{sheet}'"


def rng(col):
    return f"{q(SHOP)}!${col}${FIRST}:${col}${LAST}"


def shop_formulas(r):
    c = lambda col: f"{col}{r}"  # noqa: E731
    draft = (
        f'IF(OR({c("C")}="",{c("J")}=""),"",'
        f'IFERROR(SUBSTITUTE(SUBSTITUTE(VLOOKUP({c("J")},{q(MSG)}!$A$3:$B$5,2,FALSE),'
        f'"{{เจ้าของ}}",IF({c("G")}="","คุณเจ้าของร้าน","คุณ"&{c("G")})),"{{ร้าน}}",{c("C")}),""))'
    )
    nxt = (
        f'IF({c("C")}="","",'
        f'IF({c("W")}="{YES}",IF({c("X")}="","ติดตั้งร้านนำร่อง","นำร่องแล้ว"),'
        f'IF({c("R")}="{YES}",IF({c("U")}="","โทรหาเจ้าของ","รอผลหลังโทร"),'
        f'IF({c("L")}="","ทักครั้งแรก",'
        f'IF(AND({c("O")}="",TODAY()>={c("N")}),"ตามครั้งที่ 1",'
        f'IF(AND({c("O")}<>"",{c("Q")}="",TODAY()>={c("P")}),"ตามครั้งที่ 2",'
        f'IF({c("Q")}<>"","หยุด (ตามครบ 2 ครั้ง)","รอ")))))))'
    )
    return {
        "K": "=" + draft,
        "N": f'=IF({c("L")}="","",{c("L")}+3)',
        "P": f'=IF({c("L")}="","",{c("L")}+7)',
        "Y": "=" + nxt,
        "Z": f'=IF({c("L")}="","",{c("L")}-WEEKDAY({c("L")},3))',
    }


def build_shop(ws, sample):
    for col, (head, width, kind) in COLS.items():
        cell = ws[f"{col}1"]
        cell.value = head
        cell.fill, cell.font = HEAD_FILL, HEAD_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[col].width = width
    ws.row_dimensions[1].height = 36
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:AA{LAST}"

    for r in range(FIRST, LAST + 1):
        ws[f"A{r}"] = r - FIRST + 1
        for col, f in shop_formulas(r).items():
            ws[f"{col}{r}"] = f
        for col, (_, _, kind) in COLS.items():
            if kind.startswith("formula"):
                ws[f"{col}{r}"].fill = CALC_FILL
            if kind in ("date", "formula_date"):
                ws[f"{col}{r}"].number_format = DATE_FMT
        ws[f"K{r}"].alignment = Alignment(wrap_text=False)

    def dv(values, col):
        v = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
        v.add(f"{col}{FIRST}:{col}{LAST}")
        ws.add_data_validation(v)

    for col, (_, _, kind) in COLS.items():
        if kind == "date":
            d = DataValidation(type="date", operator="greaterThan", formula1="46023", allow_blank=True,
                               showErrorMessage=True, errorTitle="ใส่เป็นวันที่",
                               error="พิมพ์วันที่แบบ วว/ดด/ปปปป (ค.ศ.) เช่น 01/10/2026 หรือกด Ctrl + ; เพื่อใส่วันนี้")
            d.add(f"{col}{FIRST}:{col}{LAST}")
            ws.add_data_validation(d)
    dv(SEGMENTS, "B")
    dv(OWNER_SOURCES, "H")
    dv(VARIANTS, "J")
    dv(CHANNELS, "M")
    for col in ("R", "T", "V", "W"):
        dv([YES, NO], col)

    y = f"Y{FIRST}:Y{LAST}"
    for text, fill in (("ทักครั้งแรก", AMBER), ("ตามครั้งที่", AMBER), ("โทรหา", GREEN),
                       ("ติดตั้ง", GREEN), ("หยุด", GREY)):
        ws.conditional_formatting.add(
            y, FormulaRule(formula=[f'ISNUMBER(SEARCH("{text}",Y{FIRST}))'], fill=fill))

    if sample:
        fill_sample(ws, sample)


def fill_sample(ws, n):
    """Synthetic rows for the local self-test only; never uploaded."""
    today = dt.date.today()
    for i in range(n):
        r = FIRST + i
        ws[f"B{r}"] = SEGMENTS[i % 4]
        ws[f"C{r}"] = f"ร้านทดสอบ {i + 1}"
        ws[f"G{r}"] = "สมชาย" if i % 2 == 0 else None
        ws[f"J{r}"] = VARIANTS[i % 3]
        if i < n - 2:  # the last two rows are not contacted yet
            ws[f"L{r}"] = today - dt.timedelta(days=i)
        if i in (4, 5, 6, 7, 8, 9):
            ws[f"O{r}"] = today - dt.timedelta(days=i - 3)
        if i in (8, 9):
            ws[f"Q{r}"] = today
        if i in (1, 2):
            ws[f"R{r}"], ws[f"S{r}"], ws[f"T{r}"] = YES, today, YES
        if i == 2:
            ws[f"U{r}"], ws[f"W{r}"] = today, YES


def build_messages(ws, sample=0):
    ws["A1"] = ("ข้อความแรก 3 แบบ (CMO เขียน, CEO ส่ง). ใส่ {เจ้าของ} กับ {ร้าน} ตรงที่ให้เติมชื่อ: "
                "{เจ้าของ} จะเป็น 'คุณ<ชื่อเจ้าของ>' หรือ 'คุณเจ้าของร้าน' ถ้ายังไม่รู้ชื่อ")
    ws["A1"].font = Font(bold=True)
    for col, head in zip("ABCD", ("แบบ", "ข้อความ", "ผู้เขียน", "แก้ล่าสุด")):
        ws[f"{col}2"] = head
        ws[f"{col}2"].fill, ws[f"{col}2"].font = HEAD_FILL, HEAD_FONT
    for i, v in enumerate(VARIANTS):
        ws[f"A{3 + i}"] = v
        # CMO fills; an empty template leaves the draft column empty. Sample text is for the self-test only.
        ws[f"B{3 + i}"] = f"[ทดสอบ {v}] สวัสดีครับ {{เจ้าของ}} ร้าน {{ร้าน}}" if sample else None
        ws[f"C{3 + i}"] = "CMO"
        ws[f"B{3 + i}"].alignment = Alignment(wrap_text=True, vertical="top")
    ws["A7"] = "ตามครั้งที่ 1 (วันที่ 3)"
    ws["A8"] = "ตามครั้งที่ 2 (วันที่ 7, ครั้งสุดท้าย)"
    for r in (7, 8):
        ws[f"C{r}"] = "CMO"
        ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 90
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 12


def cnt(*pairs):
    """COUNTIFS over the shop tab; pairs of (column, criterion-expression)."""
    args = ",".join(f"{rng(col)},{crit}" for col, crit in pairs)
    return f"COUNTIFS({args})"


def pct(num, den):
    return f'=IF({den}=0,"",{num}/{den})'


def build_summary(ws):
    bold = Font(bold=True)
    ws["A1"] = "สรุปสำหรับทบทวนทุกวันจันทร์ 10:00 (คำนวณเองทั้งหมด ไม่ต้องกรอก)"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = "วันนี้"
    ws["B2"] = "=TODAY()"
    ws["B2"].number_format = DATE_FMT

    def header(row, labels):
        for j, lab in enumerate(labels):
            cell = ws.cell(row=row, column=1 + j, value=lab)
            cell.fill, cell.font = HEAD_FILL, HEAD_FONT
            cell.alignment = Alignment(wrap_text=True)

    # 1. per segment, cumulative
    r0 = 4
    ws[f"A{r0}"] = "1. สะสมตามกลุ่ม"
    ws[f"A{r0}"].font = bold
    header(r0 + 1, ["กลุ่ม", "ในรายชื่อ", "ทักแล้ว", "ร้านตอบ", "% ตอบ", "ถึงเจ้าของ", "% ถึงเจ้าของ",
                    "เปิด demo", "ร้านนำร่อง", "ติดตั้งแล้ว"])
    rows = SEGMENTS + ["รวม"]
    for i, seg in enumerate(rows):
        r = r0 + 2 + i
        ws[f"A{r}"] = seg
        if seg == "รวม":
            first, last = r0 + 2, r - 1
            for col in "BCDFHIJ":
                ws[f"{col}{r}"] = f"=SUM({col}{first}:{col}{last})"
            ws[f"A{r}"].font = bold
        else:
            s = f"$A{r}"
            ws[f"B{r}"] = "=" + cnt(("B", s), ("C", NONEMPTY_TEXT))
            ws[f"C{r}"] = "=" + cnt(("B", s), ("L", HAS_DATE))
            ws[f"D{r}"] = "=" + cnt(("B", s), ("R", f'"{YES}"'))
            ws[f"F{r}"] = "=" + cnt(("B", s), ("T", f'"{YES}"'))
            ws[f"H{r}"] = "=" + cnt(("B", s), ("V", f'"{YES}"'))
            ws[f"I{r}"] = "=" + cnt(("B", s), ("W", f'"{YES}"'))
            ws[f"J{r}"] = "=" + cnt(("B", s), ("W", f'"{YES}"'), ("X", HAS_DATE))
        ws[f"E{r}"] = pct(f"D{r}", f"C{r}")
        ws[f"G{r}"] = pct(f"F{r}", f"C{r}")
        for col in "EG":
            ws[f"{col}{r}"].number_format = "0%"
    seg_total_row = r0 + 2 + len(SEGMENTS)

    # 2. per message variant
    r1 = seg_total_row + 3
    ws[f"A{r1}"] = "2. ตามแบบข้อความ (ทดสอบ 3 แบบ)"
    ws[f"A{r1}"].font = bold
    header(r1 + 1, ["แบบ", "ทักแล้ว", "ร้านตอบ", "% ตอบ", "ถึงเจ้าของ", "% ถึงเจ้าของ", "ร้านนำร่อง"])
    for i, v in enumerate(VARIANTS):
        r = r1 + 2 + i
        ws[f"A{r}"] = v
        s = f"$A{r}"
        ws[f"B{r}"] = "=" + cnt(("J", s), ("L", HAS_DATE))
        ws[f"C{r}"] = "=" + cnt(("J", s), ("R", f'"{YES}"'))
        ws[f"D{r}"] = pct(f"C{r}", f"B{r}")
        ws[f"E{r}"] = "=" + cnt(("J", s), ("T", f'"{YES}"'))
        ws[f"F{r}"] = pct(f"E{r}", f"B{r}")
        ws[f"G{r}"] = "=" + cnt(("J", s), ("W", f'"{YES}"'))
        for col in "DF":
            ws[f"{col}{r}"].number_format = "0%"

    # 3. segment x variant: % reached owner
    r2 = r1 + 2 + len(VARIANTS) + 2
    ws[f"A{r2}"] = "3. % ถึงเจ้าของ แยกกลุ่ม x แบบข้อความ (ถึงเจ้าของ / ทักแล้ว)"
    ws[f"A{r2}"].font = bold
    header(r2 + 1, ["กลุ่ม"] + [f"แบบ {v}" for v in VARIANTS])
    for i, seg in enumerate(SEGMENTS):
        r = r2 + 2 + i
        ws[f"A{r}"] = seg
        for j, v in enumerate(VARIANTS):
            col = get_column_letter(2 + j)
            sent = cnt(("B", f"$A{r}"), ("J", f'"{v}"'), ("L", HAS_DATE))
            hit = cnt(("B", f"$A{r}"), ("J", f'"{v}"'), ("T", f'"{YES}"'))
            ws[f"{col}{r}"] = f'=IF({sent}=0,"",TEXT({hit}/{sent},"0%")&" ("&{hit}&"/"&{sent}&")")'

    # 4. per week (Monday to Sunday)
    r3 = r2 + 2 + len(SEGMENTS) + 2
    ws[f"A{r3}"] = "4. รายสัปดาห์ (จันทร์ถึงอาทิตย์)"
    ws[f"A{r3}"].font = bold
    header(r3 + 1, ["สัปดาห์เริ่ม", "ทักใหม่", "ร้านตอบ (ตามวันที่ตอบ)", "ถึงเจ้าของ (ตามสัปดาห์ที่ทัก)",
                    "ติดตั้งร้านนำร่อง (ตามวันติดตั้ง)", "เป้าทัก (20-30/วัน)"])
    for i in range(WEEKS):
        r = r3 + 2 + i
        ws[f"A{r}"] = FIRST_MONDAY + dt.timedelta(weeks=i)
        ws[f"A{r}"].number_format = DATE_FMT
        wk = f"$A{r}"
        ws[f"B{r}"] = "=" + cnt(("Z", wk))
        ws[f"C{r}"] = "=" + cnt(("S", f'">="&{wk}'), ("S", f'"<"&{wk}+7'))
        ws[f"D{r}"] = "=" + cnt(("Z", wk), ("T", f'"{YES}"'))
        ws[f"E{r}"] = "=" + cnt(("X", f'">="&{wk}'), ("X", f'"<"&{wk}+7'))
        ws[f"F{r}"] = "80-120" if i == 0 else "140-210"  # week 1 starts Thu 1 Oct: 4 days

    # 5. today
    r4 = r3 + 2 + WEEKS + 1
    ws[f"A{r4}"] = "5. ต้องทำวันนี้ (กรองคอลัมน์ 'ต้องทำต่อ' ในแท็บร้าน)"
    ws[f"A{r4}"].font = bold
    for i, label in enumerate(["ทักครั้งแรก", "ตามครั้งที่ 1", "ตามครั้งที่ 2", "โทรหาเจ้าของ", "ติดตั้งร้านนำร่อง"]):
        r = r4 + 1 + i
        ws[f"A{r}"] = label
        ws[f"B{r}"] = "=" + cnt(("Y", f'"{label}"'))

    # 6. G1
    r5 = r4 + 7
    ws[f"A{r5}"] = f"6. ประตู G1 ({G1_DATE:%d/%m/%Y} 18:00) ผ่านเมื่อครบทุกข้อ"
    ws[f"A{r5}"].font = bold
    header(r5 + 1, ["เกณฑ์", "ตอนนี้", "เป้า", "ผ่าน"])
    tot = seg_total_row
    g1 = [
        ("ทักแล้ว (ร้าน)", f"=C{tot}", 400, None),
        ("% ถึงเจ้าของ", f"=IF(C{tot}=0,0,F{tot}/C{tot})", 0.10, "0%"),
        ("ร้านนำร่องติดตั้ง", f"=J{tot}", 7, None),
    ]
    for i, (lab, val, goal, fmt) in enumerate(g1):
        r = r5 + 2 + i
        ws[f"A{r}"], ws[f"B{r}"], ws[f"C{r}"] = lab, val, goal
        ws[f"D{r}"] = f'=IF(B{r}>=C{r},"{YES}","ยัง")'
        if fmt:
            ws[f"B{r}"].number_format = ws[f"C{r}"].number_format = fmt
    ws[f"A{r5 + 5}"] = "เลือก 2 กลุ่มที่ดีที่สุดจากตาราง 1 (% ถึงเจ้าของ และจำนวนร้านนำร่อง)"

    ws.column_dimensions["A"].width = 30
    for col in "BCDEFGHIJ":
        ws.column_dimensions[col].width = 14
    return {"seg_total_row": seg_total_row, "variant_row": r1 + 2, "week_row": r3 + 2,
            "today_row": r4 + 1, "g1_row": r5 + 2}


def build_howto(ws):
    lines = [
        "วิธีใช้ตารางทักร้าน Chatudo",
        "1. แท็บ 'ร้าน': กรอกหนึ่งแถวต่อร้าน (กลุ่ม, ชื่อร้าน, ลิงก์, ชื่อเจ้าของ, แบบข้อความ A/B/C). ช่องสีเทาคำนวณเอง ไม่ต้องพิมพ์",
        "2. คัดลอก 'ร่างข้อความแรก' ไปส่ง แล้วใส่ 'วันที่ทัก'. วันตามครั้งที่ 1 (วันที่ 3) และครั้งที่ 2 (วันที่ 7) ขึ้นเอง",
        "3. ทุกเช้า กรองคอลัมน์ 'ต้องทำต่อ': ทักครั้งแรก / ตามครั้งที่ 1 / ตามครั้งที่ 2 / โทรหาเจ้าของ. ส่งแล้วใส่วันที่ในช่อง 'ส่งแล้ว'",
        "4. ร้านตอบ: ใส่ 'ใช่' + วันที่ตอบ. ถึงตัวเจ้าของจริง: ช่อง 'ถึงเจ้าของ' = ใช่. โทรเฉพาะร้านที่ตอบแล้ว. ตามครบ 2 ครั้งแล้วไม่ตอบ = หยุด",
        "5. วันจันทร์ 10:00 เปิดแท็บ 'สรุปวันจันทร์' ตัวเลขทุกช่องนับให้แล้ว. ข้อความ A/B/C อยู่ในแท็บ 'ข้อความ' (CMO เขียน)",
        "ที่มา: แผน Chatudo งาน O1 (CTO), CMO แผน #plan. ห้ามแทรกหรือลบคอลัมน์ในแท็บ 'ร้าน' เพราะสูตรสรุปอ้างตามตำแหน่ง",
    ]
    for i, t in enumerate(lines):
        ws[f"A{1 + i}"] = t
    ws["A1"].font = Font(bold=True, size=13)
    ws.column_dimensions["A"].width = 140


def build(out, sample=0):
    wb = Workbook()
    ws = wb.active
    ws.title = SHOP
    build_shop(ws, sample)
    layout = build_summary(wb.create_sheet(SUM))
    build_messages(wb.create_sheet(MSG), sample)
    build_howto(wb.create_sheet(HOW))
    wb.save(out)
    return layout


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int, default=0, help="synthetic rows for a local self-test only")
    a = ap.parse_args()
    print(build(a.out, a.sample))
