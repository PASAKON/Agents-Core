---
name: BROWSER_OPERATOR_Knowledge_XmPartners
kind: knowledge
description: "KNOWLEDGE — How to navigate the XM Partner Area (mypartners.xm.com) on winbox port 9224 in read-only mode: entry URLs, hash routes, exact CSS selectors and period-picker values for looking up an MT4/MT5 trading account, reading trader campaign/rebate plans, and reading LOT/commission/rebate reports, plus the forbidden write/payout routes. Trigger on /BROWSER_OPERATOR_Knowledge_XmPartners, 'XM Partner', 'mypartners.xm.com', 'เช็คพอร์ต XM', 'เช็ครีเบต XM', 'XM IB', or any task that inspects XM affiliate/trader reports on port 9224. Do NOT use for Exness or for making account/rebate changes without a CEO question-card confirmation."
owner: COO
audience: [cxo, worker]
created_by: agent
author: {role: cto, date: "2026-11-02"}
improved_by: []
aka: []
verified: "2026-11-02"
refresh_after: "2026-12-02"
---

# XM Partner Area (`mypartners.xm.com`) — Read-Only Navigation Map

Measured on `winbox:9224` (`config/agy-browse.yaml` port `9224`, label `xm-partners`) during `task-62e1066c` (2026-11-02). Contains **no client PII or account numbers**.

## 1. Entry URL, Session Check & Browser Home

- **Host & Port:** `winbox` desktop Chrome on CDP port `9224` (`allowed_hosts: [mypartners.xm.com]` in `config/agy-browse.yaml`). Never touch the ChatGPT tab on the same Chrome instance.
- **Entry URL:** `https://mypartners.xm.com/#/` (Aurelia SPA).
  - **Signed-in dashboard:** title is `"ภาพรวม | แพลตฟอร์มสำหรับแอฟฟิลิเอต"`, header shows `"ยินดีต้อนรับ คุณ Pasakon"` (`A<partner-id>`).
  - **Signed-out / login screen:** redirects to `https://mypartners.xm.com/#/login` with title `"login | แพลตฟอร์มสำหรับแอฟฟิลิเอต"` and fields `หมายเลขพันธมิตร` / `รหัสผ่าน`. Note: on first cold navigation to `https://mypartners.xm.com/`, the SPA may briefly render `/#/login` for 1–2 seconds while refreshing its token before redirecting to `/#/`. Wait 3 seconds and re-check `tabs` before concluding the session is expired. If it remains on `/#/login`, stop and open a login relay request (`relay-login` skill) — never type credentials.
- **Always navigate by hash URL (`goto`), not top-nav clicks:**
  - The top bar displays live USD balances (`ผลตอบแทนรวมสะสม $...`, `การจ่าย Lot รีเบตต่อไป รวม: $...`). Clicking top-nav dropdown labels such as `รีเบตสำหรับนักเทรด` via `agy_browse.py click` can match an ancestor element containing `$` and be refused by `MONEY_RE` (`click refused: the control reads like money`).
  - Instead, jump straight to any report page with `agy_browse.py --port 9224 goto "https://mypartners.xm.com/#/..."` followed by `wait-text`.

## 2. Top-Level Navigation & Hash Routes

| Thai Menu | Submenu | Hash Route (`https://mypartners.xm.com/...`) | Mode |
|---|---|---|---|
| **หน้าหลัก** | ภาพรวม (Dashboard + 10 most recent traders) | `#/` | **Read-only** |
| **แคมเปญ** | เทรดเดอร์แคมเปญ | `#/campaigns/trader-campaigns` | Read-only (do not create/edit) |
| | ซับแอฟฟิลิเอทแคมเปญ | `#/campaigns/sub-affiliate-campaigns` | Read-only |
| **ลิงก์** | ลิงก์แอฟฟิลิเอท | `#/links/affiliate-links` | **Read-only** |
| | ลิงก์ซับแอฟฟิลิเอท | `#/links/sub-affiliate-links` | **Read-only** |
| **รายงาน** | สถิติ Lot รีเบต (Lot Rebate Statistics) | `#/reports/lot-rebate-statistics` | **Read-only** |
| | เทรดเดอร์ลิสต์ (Real Trader List) | `#/reports/trader-list/real` | **Read-only** |
| | ลิสต์ของเทรดเดอร์เดโม (Demo Trader List) | `#/reports/trader-list/demo` | **Read-only** |
| | ธุรกรรมของเทรดเดอร์ (Trader Transactions / Lots) | `#/reports/traders-trades` | **Read-only** |
| | ข้อมูลซับแอฟฟิลิเอท | `#/reports/sub-affiliate-info` | **Read-only** |
| | การปรับเปลี่ยน (Adjustments) | `#/reports/adjustments` | **Read-only** |
| | รายงาน Social Trading | `#/reports/social-trading-competitions` | **Read-only** |
| | รายละเอียดของเงินอัตโนมัติ | `#/auto-fund-support` | **Read-only** |
| | ผลตอบแทนรวมสะสม | `#/all-time-earnings-breakdown` | **Read-only** |
| **รีเบตสำหรับนักเทรด** | รายงานนักเทรดตามแผนรีเบต | `#/auto-rebate/report` | **Read-only** |
| | เพิ่มแผน / แก้ไขแผน / ย้ายนักเทรด / เชื่อมต่อแคมเปญ | `#/auto-rebate/addV2`, `editV2`, `move-traders`, `campaigns` | **FORBIDDEN (Write)** |
| **ผู้ดูแลแคมเปญ** | รายงานนักเทรด / วิเคราะห์ผลการดำเนินงาน / สรุปเฉพาะจุด | `#/campaign-rebate/reporting/...` | **Read-only** |
| | เพิ่ม / มอบหมาย / แก้ไขแผนแคมเปญรีเบต | `#/v2/campaign-rebate`, `assign-campaign-handlers`, `history` | **FORBIDDEN (Write)** |
| **การชำระเงิน** | ประวัติการชำระเงิน | `#/payments/payment-history` | **Read-only** |
| | ร้องขอการชำระเงิน (Request Payout / E-Wallet) | `#/payments/request-payments` | **FORBIDDEN (Money)** |

## 3. Looking Up a Client's Trading Account (`#/reports/trader-list/real`)

Use this page to verify whether an MT4/MT5 account is under our IB, its Client ID (`หมายเลขลูกค้า`), account type (`ประเภทบัญชี`), campaign (`แคมเปญ`), partner code (`รหัสพันธมิตร`), and assigned auto-rebate plan (`แผนรีเบตสำหรับนักเทรด`, e.g., `MOONIEX`, `MNFUNDS`, `MNVIP30`).

### Controls & Exact CSS Selectors
- **Report Mode (`รายงาน:`):** `select.form-control.au-target` (first select)
  - Option 0: `การลงทะเบียนเทรดเดอร์ใหม่` (New trader registrations — default)
  - Option 1: `ลูกค้าใหม่ที่ทำการฝากเงิน` (New depositing clients)
- **Date Range (`กรอบระยะเวลา:`):** `select.period-picker-filter__display`
  - `value="0"` → `วันนี้` (Today)
  - `value="1"` → `เดือนนี้` (This Month — **default; will miss accounts registered in earlier months!**)
  - `value="2"` → `เดือนที่ผ่านมา` (Last Month)
  - `value="3"` → `เดือนนี้และเดือนที่ผ่านมา` (This Month & Last Month)
  - `value="4"` → `ปีนี้` (This Year)
  - `value="5"` → `ปีนี้และปีที่ผ่านมา` (This Year & Last Year — **use `"5"` when looking up an account by ID**)
  - `value="6"` → `กำหนดเอง` (Custom range)
- **Trader Brand (`แบรนด์ของเทรดเดอร์:`):** `select#brandPicker` (default `ทั้งหมด`)
- **Campaign (`แคมเปญ:`):** `select#labeled-element5` (or `select#labeled-element1`; default `ทั้งหมด`)
- **MT4/MT5 ID Search Input (`MT4/MT5 ID:`):** `input#mt4IdSelect`
- **Submit / Generate Report Button:** `button[type=submit]` (label `"สร้างรายงาน"`).
  - With `agy_browse.py`, focus `#mt4IdSelect` (`type "#mt4IdSelect" "<id>"`) and send `key Enter` to trigger report generation without hitting the `button[type=submit]` fire guard.

### Result Table Columns (`table`)
1. `หมายเลขลูกค้า` (Client ID)
2. `MT4/MT5 ID` (Trading Account Number)
3. `แพลตฟอร์มซื้อขาย` (`MT4` / `MT5`)
4. `ประเภทบัญชี` (e.g., `Ultra Low Standard - THB`, `Standard`, `Shares`)
5. `เวลาที่เริ่มสมัคร (EET)` (Registration timestamp)
6. `ได้รับการยืนยันเรียบร้อยแล้ว` (Validated flag)
7. `เวลาที่เปิดใช้งาน (EET)` (Activation timestamp)
8. `ประเทศ` (Country)
9. `แคมเปญ` (Campaign name, e.g., `Mooniex (Main)`, `Mooniex (Funds)`, `Mooniex (Event)`)
10. `รหัสพันธมิตร` (Partner / Link code, e.g., `MOONIEX`, `MNFUNDS`, `MNVIP30`)
11. `แบรนด์ของเทรดเดอร์` (e.g., `XM Global`)
12. `URL สำหรับอ้างอิง` (Referrer URL)
13. `แผนรีเบตสำหรับนักเทรด` (Active Auto-Rebate scheme name, e.g., `MOONIEX`, `MNFUNDS`, `MNVIP30`)
14. `โมบายแอป`, `TNCR`, `สถานะคลับนักเทรด`, `แท็ก`, `เวลาที่คลิก (EET)`, `ประเภท Social Trading`

## 4. Reading LOT, IB Commission & Client Rebate Reports (`#/reports/traders-trades`)

Use `#/reports/traders-trades` (`ธุรกรรมของเทรดเดอร์`) to read per-account or per-trade lots, real IB commission credited to us, and auto-rebate paid to the client.

### Controls & Exact CSS Selectors
- **Date Range (`กรอบระยะเวลา:`):** `select.period-picker-filter__display`
  - `value="0"` → `วันนี้`
  - `value="1"` → `เดือนนี้`
  - `value="2"` → `เดือนที่ผ่านมา`
  - `value="3"` → `กำหนดเอง` (reveals date range input `input.form-control.au-target` with format `DD/MM/YYYY - DD/MM/YYYY`)
- **Campaign (`แคมเปญ:`):** `select#labeled-element6` (default `ทั้งหมด`)
- **MT4/MT5 ID Search Input (`MT4/MT5 ID:`):** `input#mt4IdSelect`
- **Column Picker (`เพิ่มหรือลบแถว`):**
  - Default active columns (`แถวที่ถูกเลือก`):
    - `ประเภทบัญชี` (Account Type)
    - `สกุลเงินของบัญชี` (Currency)
    - `แบรนด์ของบัญชี` (Brand)
    - `กระเป๋าเงิน` (Wallet)
    - `แคมเปญ` (Campaign)
    - `เวลาเปิด` (Open Time EET)
    - `เวลาปิด` (Close Time EET)
    - `ประเภทของการซื้อขาย` (Buy/Sell)
    - `ประเภทของการเทรด` (Trade Type)
    - `ตราสาร` (Instrument)
    - `กลุ่มของตราสาร` (Instrument Group)
    - `Lots` (Closed Lots)
    - `แอฟฟิลิเอตคอมฯ` (Affiliate Commission — real IB commission credited to us)
    - `แคมเปญ รีเบต คอมมิชชั่น` (Campaign Rebate Commission)
    - `ค่าคอมรีเบตสำหรับนักเทรด` (Trader Rebate Commission — rebate paid/credited to the client)
  - Optional columns under `แถวที่มีอยู่` (click the column pill button, then click `button:has-text("ใช้")`):
    - `MT4/MT5 ID`, `คอมมิชชั่นรวม` (Total Commission), `เทรด #` (Ticket #), `ราคาปิด`, `ราคาเปิด`.

## 5. Forbidden Actions (Hard Guardrails)

- **NEVER click or visit write/payout endpoints:**
  - `#/payments/request-payments` (`ร้องขอการชำระเงิน`) or E-Wallet transfer controls.
  - `#/auto-rebate/addV2` (`เพิ่มแผน`), `#/auto-rebate/editV2` (`แก้ไขแผน`), `#/auto-rebate/move-traders` (`ย้ายนักเทรดไปยังแผนรีเบตอัตโนมัติอื่น`), `#/auto-rebate/campaigns` (`เชื่อมต่อแคมเปญ`), unless the CEO has explicitly confirmed each account and target plan on a Run Inbox question card (`Q-…`).
  - `#/v2/campaign-rebate`, `#/campaign-rebate/assign-campaign-handlers`, `#/v2/campaign-rebate/history`.
  - Account profile, password, 2FA, or language settings.
- **NEVER commit or print client PII / account numbers** into git branches, `REPORT.md`, skills, or chat logs. Store raw lookup output only in `/home/sompong/private/` (`mode 0600`) or gitignored `state/logs/` (`mode 0600`).

## Field notes

- 2026-11-02 [COSTLY] §1 — Clicking top-nav links (`รีเบตสำหรับนักเทรด`) via `agy_browse.py click` was refused by `MONEY_RE` (`click refused: the control reads like money ('$N')`) because the header balance bar (an amount) shares an ancestor container; navigating via `agy_browse.py --port 9224 goto "https://mypartners.xm.com/#/..."` bypasses the header DOM and lands cleanly · evidence: task-62e1066c on winbox:9224 · status: promoted
- 2026-11-02 [MISSING] §3 — `#/reports/trader-list/real` defaults `select.period-picker-filter__display` to `1` (`เดือนนี้`), which returns 0 rows for any MT4/MT5 ID registered in a prior month even when `#mt4IdSelect` is filled; always switch `select.period-picker-filter__display` to `5` (`ปีนี้และปีที่ผ่านมา`) before querying an account ID · evidence: task-62e1066c on winbox:9224 · status: promoted
