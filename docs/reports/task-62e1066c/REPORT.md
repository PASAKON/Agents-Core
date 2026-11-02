# Report: task-62e1066c — XM MyPartners Navigation Skill & Read-Only Account Lookup

- **Date:** 2026-11-02
- **Project:** `sompongadmin` (PH `#3bea1120`, completed via CTO takeover `#f69c4825`)
- **Host / Browser Home:** `winbox:9224` (`config/agy-browse.yaml` port `9224`, label `xm-partners`)

## Files Changed

- `.claude/skills/BROWSER_OPERATOR_Knowledge_XmPartners/SKILL.md` — Part A: read-only navigation map for `https://mypartners.xm.com` (entry URLs, hash routes, exact CSS selectors for `#/reports/trader-list/real` and `#/reports/traders-trades`, period-picker values, `tfoot` grand-total structure, and forbidden write/payout routes). Contains **zero client PII or account numbers**.
- `docs/reports/task-62e1066c/REPORT.md` — this report (redacted summary; raw account numbers and trade rows stored only in `/home/sompong/private/xm-order-39ed-result.log` on Contabo, mode `0600`, and gitignored `state/logs/xm-order-39ed-result.log` on Winbox).

## Part A — XM Partner Area Navigation Skill

Created `.claude/skills/BROWSER_OPERATOR_Knowledge_XmPartners/SKILL.md` covering:
1. **Entry & session check:** `https://mypartners.xm.com/#/` (`"ภาพรวม | แพลตฟอร์มสำหรับแอฟฟิลิเอต"`). Documented the cold-load SPA token refresh behavior (brief `/#/login` render before redirecting to `/#/`) and why `agy_browse.py --port 9224 goto "https://mypartners.xm.com/#/..."` must be used instead of clicking top-nav dropdown labels near the header USD balance bar (`MONEY_RE`).
2. **Real Trader List (`#/reports/trader-list/real`):** `select.period-picker-filter__display` (must be set to `"5"` = `ปีนี้และปีที่ผ่านมา` so accounts registered in prior months are returned), `select#brandPicker`, `select#labeled-element5`, `input#mt4IdSelect`, and all 19 result columns (`หมายเลขลูกค้า`, `MT4/MT5 ID`, `แพลตฟอร์มซื้อขาย`, `ประเภทบัญชี`, `แคมเปญ`, `รหัสพันธมิตร`, `แผนรีเบตสำหรับนักเทรด`, etc.).
3. **Trader Transactions (`#/reports/traders-trades`):** `select.period-picker-filter__display`, `select#labeled-element6`, `input#mt4IdSelect`, the column picker (`เพิ่มหรือลบแถว`), and the `table tfoot` (`ทั้งหมด`) grand-total row that sums `Lots`, `แอฟฟิลิเอตคอมฯ` (real IB commission credited to us), `แคมเปญ รีเบต คอมมิชชั่น`, and `ค่าคอมรีเบตสำหรับนักเทรด` (rebate paid/credited to the client) across all pages on the server.
4. **Forbidden routes:** `#/payments/request-payments`, `#/auto-rebate/addV2`, `#/auto-rebate/editV2`, `#/auto-rebate/move-traders`, `#/auto-rebate/campaigns`, and `#/v2/campaign-rebate*`.

## Part B — Read-Only Account Lookup Summary (Redacted)

All three accounts from the private order file were **FOUND** under our IB on `https://mypartners.xm.com`. Full unredacted details are written to `/home/sompong/private/xm-order-39ed-result.log` (`mode 0600`, owner `sompong:sompong`) on Contabo.

| Account Slot | Platform & Account Type | Registered (EET) | Campaign (`แคมเปญ`) | Partner Code (`รหัสพันธมิตร`) | Active Auto-Rebate Plan (`แผนรีเบตฯ`) | Window `2026-10-21..2026-10-31` (Trades / Lots / IB Comm to Us / Rebate to Client) | Window `2026-10-28..2026-10-31` (Trades / Lots / IB Comm to Us / Rebate to Client) | Window `2026-11-01..2026-11-02` Nov MTD (Trades / Lots / IB Comm to Us / Rebate to Client) |
|---|---|---|---|---|---|---|---|---|
| **Account 1** (old account) | `MT5` · `Ultra Low Standard - USD` | `28/01/2026 04:05` | `Mooniex (Event)` | `MNVIP30` | `MNVIP30` | `563` trades · `22.96000` Lots · IB `\$157.30400` · Client Rebate `\$3.41600` | `81` trades · `4.47000` Lots · IB `\$31.29000` · Client Rebate `\$0.00000` | `34` trades · `0.71000` Lots · IB `\$2.48500` · Client Rebate `\$2.48500` |
| **Account 2** (new account, 28 Oct) | `MT5` · `Ultra Low Standard - USD` | `28/10/2026 06:24` | `Mooniex (Event)` | `MNVIP30` | `MNVIP30` | `276` trades · `3.77000` Lots · IB `\$26.39000` · Client Rebate `\$0.00000` | `276` trades · `3.77000` Lots · IB `\$26.39000` · Client Rebate `\$0.00000` | `0` trades · `0.00000` Lots · IB `\$0.00000` · Client Rebate `\$0.00000` |
| **Account 3** (Standard) | `MT5` · `Standard - USD` | `19/02/2026 17:47` | `Mooniex (Funds)` | `MNFUNDS` | `MNVIP30` | `1,437` trades · `14.22220` Lots · IB `\$159.45990` · Client Rebate `\$11.20834` | `644` trades · `6.37700` Lots · IB `\$76.52481` · Client Rebate `\$0.00000` | `71` trades · `0.68190` Lots · IB `\$4.09122` · Client Rebate `\$4.09122` |

### Key Findings from the Read-Only Check
1. All three accounts are already assigned to **`แผนรีเบตสำหรับนักเทรด: MNVIP30`** in `#/reports/trader-list/real` (Accounts 1 & 2 under campaign `Mooniex (Event)` / code `MNVIP30`; Account 3 under campaign `Mooniex (Funds)` / code `MNFUNDS` with auto-rebate plan `MNVIP30`).
2. Between `2026-10-28` and `2026-10-31`, `ค่าคอมรีเบตสำหรับนักเทรด` (auto-rebate credited to the client) was `\$0.00000` on all three accounts while 100% of the commission landed in our IB (`แอฟฟิลิเอตคอมฯ`: `\$31.29000`, `\$26.39000`, `\$76.52481`).
3. Starting `2026-11-01`, the 50% `MNVIP30` auto-rebate split is actively crediting on new trades (`Account 1`: IB `\$2.48500` / Client Rebate `\$2.48500`; `Account 3`: IB `\$4.09122` / Client Rebate `\$4.09122`).
4. **Zero edits made:** all operations were strictly read-only.

## Verification & Privacy Check
- `gitleaks git --log-opts="origin/main..HEAD" --no-banner` → `0 leaks found`.
- Verified no 6+ digit account/client IDs appear in `.claude/skills/BROWSER_OPERATOR_Knowledge_XmPartners/SKILL.md` or `docs/reports/task-62e1066c/REPORT.md`.
