# REPORT task-4f702eb0

Reconciliation of `docs/ops/credit-ledger.jsonl` (`26` (derived) total entries across lines `1` (measured) to `26` (measured); total recorded spend across all engines = `2629.0` (derived) credits).

---

## 1. Summary Per Engine (and Unit)

| Engine | Unit | Number of Entries | Total Amount | First `ts` (Chronological & File Order) | Last `ts` (Chronological `ts` Order) | Last `ts` (File Order) | Initial `balance_before` | Balance at the End (`balance_after`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `flow` | `credits` | `24` (derived) | `2619.0` (derived) | `2026-09-28T00:27:00+07:00` (measured, line `1` (measured)) | `2026-10-03T00:19:12+07:00` (measured, line `11` (measured)) | `2026-10-02T20:51:47+07:00` (measured, line `26` (measured)) | `3298.0` (measured, line `1` (measured)) | See breakdown below: `863.0` (measured, line `26` (measured)) / missing on line `11` (measured) / `827.0` (derived) / `581.0` (measured, line `10` (measured)) / `545.0` (derived) / `679.0` (derived) |
| `flow-music` | `credits` | `2` (derived) | `10.0` (derived) | `2026-10-01T14:37:08+07:00` (measured, line `16` (measured)) | `2026-10-02T17:58:18+07:00` (measured, line `21` (measured)) | `2026-10-02T17:58:18+07:00` (measured, line `21` (measured)) | `30585.0` (measured, line `16` (measured)) | `30605.0` (measured, line `21` (measured)); theoretical `30575.0` (derived) |
| **All Engines** | `credits` | `26` (derived) | `2629.0` (derived) | `2026-09-28T00:27:00+07:00` (measured, line `1` (measured)) | `2026-10-03T00:19:12+07:00` (measured, line `11` (measured)) | `2026-10-02T20:51:47+07:00` (measured, line `26` (measured)) | — | — |

### End-of-Ledger Balance Values for `flow` (`unit: credits`)
- **Last entry in chronological (`ts`) order (line `11` (measured), `ts = 2026-10-03T00:19:12+07:00` (measured))**: `balance_after` is omitted/missing (`amount = 36.0` (measured)).
- **Last entry with a recorded `balance_after` in both chronological (`ts`) order and file order (line `26` (measured), `ts = 2026-10-02T20:51:47+07:00` (measured))**: `863.0` (measured).
- **Last recorded `balance_after` in `ts` order (line `26` (measured): `863.0` (measured)) minus subsequent un-balanced entry on line `11` (measured) (`amount = 36.0` (measured))**: `863.0 - 36.0 = 827.0` (derived).
- **Lowest recorded `balance_after` (line `10` (measured), `ts = 2026-10-02T20:07:00+07:00` (measured))**: `581.0` (measured); minus line `11` (measured) (`amount = 36.0` (measured)) = `545.0` (derived); minus both line `25` (measured) (`amount = 12.0` (measured)) and line `11` (measured) (`amount = 36.0` (measured)) = `533.0` (derived).
- **Initial `balance_before` (line `1` (measured): `3298.0` (measured)) minus total `flow` `amount` (`2619.0` (derived))**: `3298.0 - 2619.0 = 679.0` (derived).

### End-of-Ledger Balance Values for `flow-music` (`unit: credits`)
- **Last entry in both chronological (`ts`) order and file order (line `21` (measured), `ts = 2026-10-02T17:58:18+07:00` (measured))**: `30605.0` (measured).
- **Initial `balance_before` (line `16` (measured): `30585.0` (measured)) minus total `flow-music` `amount` (`10.0` (derived))**: `30585.0 - 10.0 = 30575.0` (derived).

---

## 2. Balance Chain Per Engine (in `ts` Order)

### 2.1 Full Chronological (`ts` Order) Balance Chain — Engine `flow` (`24` (derived) entries)

Note: Lines `8` (measured), `9` (measured), `10` (measured), and `11` (measured) appear in the file before lines `12` (measured) through `26` (measured), so sorting by `ts` orders the `flow` chain as: `1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 8, 9, 17, 18, 19, 20, 22, 23, 24, 10, 25, 26, 11`. (Lines `23` (measured) and `24` (measured) share identical `ts = 2026-10-02T19:54:16+07:00` (measured) and are ordered `23` then `24` by file and balance sequence.)

| `ts` Order # | Line # | `ts` (measured) | `amount` (measured) | `balance_before` (measured) | Expected `balance_before - amount` (derived) | `balance_after` (measured) | Within-Entry Diff `balance_after - (balance_before - amount)` (derived) | Prev `balance_after` (measured) | Between-Entry Gap `balance_before - prev_balance_after` (derived) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `1` (derived) | `1` (measured) | `2026-09-28T00:27:00+07:00` | `168.0` | `3298.0` | `3130.0` | `3130.0` | `0.0` | — | — |
| `2` (derived) | `2` (measured) | `2026-09-28T04:30:00+07:00` | `120.0` | `3130.0` | `3010.0` | `3010.0` | `0.0` | `3130.0` (line `1` (measured)) | `0.0` |
| `3` (derived) | `3` (measured) | `2026-09-28T18:50:28+07:00` | `108.0` | `3060.0` | `2952.0` | `2952.0` | `0.0` | `3010.0` (line `2` (measured)) | `+50.0` (`-50.0` rev) |
| `4` (derived) | `4` (measured) | `2026-09-28T19:03:24+07:00` | `21.0` | `2952.0` | `2931.0` | `2931.0` | `0.0` | `2952.0` (line `3` (measured)) | `0.0` |
| `5` (derived) | `5` (measured) | `2026-09-28T19:38:35+07:00` | `18.0` | `2931.0` | `2913.0` | `2913.0` | `0.0` | `2931.0` (line `4` (measured)) | `0.0` |
| `6` (derived) | `6` (measured) | `2026-09-28T19:46:55+07:00` | `38.0` | `2913.0` | `2875.0` | `2875.0` | `0.0` | `2913.0` (line `5` (measured)) | `0.0` |
| `7` (derived) | `7` (measured) | `2026-09-28T20:21:08+07:00` | `36.0` | `2875.0` | `2839.0` | `2839.0` | `0.0` | `2875.0` (line `6` (measured)) | `0.0` |
| `8` (derived) | `12` (measured) | `2026-10-01T04:41:07+07:00` | `12.0` | `2822.0` | `2810.0` | `2810.0` | `0.0` | `2839.0` (line `7` (measured)) | `-17.0` (`+17.0` rev) |
| `9` (derived) | `13` (measured) | `2026-10-01T04:54:51+07:00` | `6.0` | `2810.0` | `2804.0` | `2804.0` | `0.0` | `2810.0` (line `12` (measured)) | `0.0` |
| `10` (derived) | `14` (measured) | `2026-10-01T05:23:10+07:00` | `270.0` | `2804.0` | `2534.0` | `2534.0` | `0.0` | `2804.0` (line `13` (measured)) | `0.0` |
| `11` (derived) | `15` (measured) | `2026-10-01T06:23:00+07:00` | `30.0` | `2534.0` | `2504.0` | `2504.0` | `0.0` | `2534.0` (line `14` (measured)) | `0.0` |
| `12` (derived) | `8` (measured) | `2026-10-01T16:22:20+07:00` | `22.0` | `2554.0` | `2532.0` | `2532.0` | `0.0` | `2504.0` (line `15` (measured)) | `+50.0` (`-50.0` rev) |
| `13` (derived) | `9` (measured) | `2026-10-01T19:23:03+07:00` | `696.0` | `2532.0` | `1836.0` | `1836.0` | `0.0` | `2532.0` (line `8` (measured)) | `0.0` |
| `14` (derived) | `17` (measured) | `2026-10-02T17:58:07+07:00` | `18.0` | `1836.0` | `1818.0` | `1868.0` | `+50.0` (`-50.0` rev) | `1836.0` (line `9` (measured)) | `0.0` |
| `15` (derived) | `18` (measured) | `2026-10-02T17:58:10+07:00` | `255.0` | `1868.0` | `1613.0` | `1613.0` | `0.0` | `1868.0` (line `17` (measured)) | `0.0` |
| `16` (derived) | `19` (measured) | `2026-10-02T17:58:12+07:00` | `15.0` | `1613.0` | `1598.0` | `1598.0` | `0.0` | `1613.0` (line `18` (measured)) | `0.0` |
| `17` (derived) | `20` (measured) | `2026-10-02T17:58:15+07:00` | `45.0` | `1598.0` | `1553.0` | `1553.0` | `0.0` | `1598.0` (line `19` (measured)) | `0.0` |
| `18` (derived) | `22` (measured) | `2026-10-02T18:48:59+07:00` | `12.0` | `1553.0` | `1541.0` | `1541.0` | `0.0` | `1553.0` (line `20` (measured)) | `0.0` |
| `19` (derived) | `23` (measured) | `2026-10-02T19:54:16+07:00` | `285.0` | `1541.0` | `1256.0` | `1247.0` | `-9.0` (`+9.0` rev) | `1541.0` (line `22` (measured)) | `0.0` |
| `20` (derived) | `24` (measured) | `2026-10-02T19:54:16+07:00` | `15.0` | `1247.0` | `1232.0` | `1181.0` | `-51.0` (`+51.0` rev) | `1247.0` (line `23` (measured)) | `0.0` |
| `21` (derived) | `10` (measured) | `2026-10-02T20:07:00+07:00` | `111.0` | *(missing)* | *(missing)* | `581.0` | *(missing `balance_before`)* | `1181.0` (line `24` (measured)) | *(missing `balance_before`; see 2.4)* |
| `22` (derived) | `25` (measured) | `2026-10-02T20:09:05+07:00` | `12.0` | *(missing)* | *(missing)* | *(missing)* | *(missing both)* | `581.0` (line `10` (measured)) | *(missing both; see 2.4)* |
| `23` (derived) | `26` (measured) | `2026-10-02T20:51:47+07:00` | `270.0` | `1181.0` | `911.0` | `863.0` | `-48.0` (`+48.0` rev) | `581.0` (line `10` (measured)) / `1181.0` (line `24` (measured)) | `+600.0` vs line `10` (`0.0` vs line `24`) |
| `24` (derived) | `11` (measured) | `2026-10-03T00:19:12+07:00` | `36.0` | *(missing)* | *(missing)* | *(missing)* | *(missing both)* | `863.0` (line `26` (measured)) | *(missing both; see 2.4)* |

---

### 2.2 Full Chronological (`ts` Order) Balance Chain — Engine `flow-music` (`2` (derived) entries)

| `ts` Order # | Line # | `ts` (measured) | `amount` (measured) | `balance_before` (measured) | Expected `balance_before - amount` (derived) | `balance_after` (measured) | Within-Entry Diff `balance_after - (balance_before - amount)` (derived) | Prev `balance_after` (measured) | Between-Entry Gap `balance_before - prev_balance_after` (derived) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `1` (derived) | `16` (measured) | `2026-10-01T14:37:08+07:00` | `5.0` | `30585.0` | `30580.0` | `30580.0` | `0.0` | — | — |
| `2` (derived) | `21` (measured) | `2026-10-02T17:58:18+07:00` | `5.0` | `30610.0` | `30605.0` | `30605.0` | `0.0` | `30580.0` (line `16` (measured)) | `+30.0` (`-30.0` rev) |

---

### 2.3 Every Place Where `balance_after != balance_before - amount` (Within-Entry Discrepancies)

Across all `26` (derived) entries, `4` (derived) entries (all in `engine: "flow"`) have both balances present and `balance_after != balance_before - amount` (`0` (derived) in `engine: "flow-music"`):

1. **Line `17` (measured)** (`engine: "flow"`, `ts: 2026-10-02T17:58:07+07:00` (measured)):
   - `balance_before` = `1836.0` (measured), `amount` = `18.0` (measured)
   - Two values compared: `balance_after` = `1868.0` (measured) vs `balance_before - amount` = `1818.0` (derived)
   - Difference: `balance_after - (balance_before - amount)` = `+50.0` (derived) (or `(balance_before - amount) - balance_after` = `-50.0` (derived)).
   - Actual pool change: `balance_before - balance_after` = `1836.0 - 1868.0` = `-32.0` (derived; also recorded in field `delta_mismatch` = `-32.0` (measured)), vs `amount` = `18.0` (measured).

2. **Line `23` (measured)** (`engine: "flow"`, `ts: 2026-10-02T19:54:16+07:00` (measured)):
   - `balance_before` = `1541.0` (measured), `amount` = `285.0` (measured)
   - Two values compared: `balance_after` = `1247.0` (measured) vs `balance_before - amount` = `1256.0` (derived)
   - Difference: `balance_after - (balance_before - amount)` = `-9.0` (derived) (or `(balance_before - amount) - balance_after` = `+9.0` (derived)).
   - Actual pool change: `balance_before - balance_after` = `1541.0 - 1247.0` = `294.0` (derived; also recorded in field `delta_mismatch` = `294.0` (measured)), vs `amount` = `285.0` (measured).

3. **Line `24` (measured)** (`engine: "flow"`, `ts: 2026-10-02T19:54:16+07:00` (measured)):
   - `balance_before` = `1247.0` (measured), `amount` = `15.0` (measured)
   - Two values compared: `balance_after` = `1181.0` (measured) vs `balance_before - amount` = `1232.0` (derived)
   - Difference: `balance_after - (balance_before - amount)` = `-51.0` (derived) (or `(balance_before - amount) - balance_after` = `+51.0` (derived)).
   - Actual pool change: `balance_before - balance_after` = `1247.0 - 1181.0` = `66.0` (derived; also recorded in field `delta_mismatch` = `66.0` (measured)), vs `amount` = `15.0` (measured).

4. **Line `26` (measured)** (`engine: "flow"`, `ts: 2026-10-02T20:51:47+07:00` (measured)):
   - `balance_before` = `1181.0` (measured), `amount` = `270.0` (measured)
   - Two values compared: `balance_after` = `863.0` (measured) vs `balance_before - amount` = `911.0` (derived)
   - Difference: `balance_after - (balance_before - amount)` = `-48.0` (derived) (or `(balance_before - amount) - balance_after` = `+48.0` (derived)).
   - Actual pool change: `balance_before - balance_after` = `1181.0 - 863.0` = `318.0` (derived; also recorded in field `delta_mismatch` = `318.0` (measured)), vs `amount` = `270.0` (measured).

*(Note: Lines `10` (measured), `25` (measured), and `11` (measured) omit `balance_before` and/or `balance_after` and cannot be evaluated directly for `balance_after != balance_before - amount`; see Section 4.)*

---

### 2.4 Every Place Where `balance_before != previous balance_after` for the Same Engine in `ts` Order (Between-Entry Gaps)

#### Engine `flow`
1. **Line `3` (measured) vs previous `ts`-ordered entry Line `2` (measured)** (`2026-09-28T04:30:00+07:00` (measured) -> `2026-09-28T18:50:28+07:00` (measured)):
   - Line `2` (measured) `balance_after` = `3010.0` (measured)
   - Line `3` (measured) `balance_before` = `3060.0` (measured)
   - Difference: `balance_before - prev_balance_after` = `3060.0 - 3010.0` = `+50.0` (derived) (or `prev_balance_after - balance_before` = `-50.0` (derived)).

2. **Line `12` (measured) vs previous `ts`-ordered entry Line `7` (measured)** (`2026-09-28T20:21:08+07:00` (measured) -> `2026-10-01T04:41:07+07:00` (measured)):
   - Line `7` (measured) `balance_after` = `2839.0` (measured)
   - Line `12` (measured) `balance_before` = `2822.0` (measured)
   - Difference: `balance_before - prev_balance_after` = `2822.0 - 2839.0` = `-17.0` (derived) (or `prev_balance_after - balance_before` = `+17.0` (derived)).

3. **Line `8` (measured) vs previous `ts`-ordered entry Line `15` (measured)** (`2026-10-01T06:23:00+07:00` (measured) -> `2026-10-01T16:22:20+07:00` (measured)):
   - Line `15` (measured) `balance_after` = `2504.0` (measured)
   - Line `8` (measured) `balance_before` = `2554.0` (measured)
   - Difference: `balance_before - prev_balance_after` = `2554.0 - 2504.0` = `+50.0` (derived) (or `prev_balance_after - balance_before` = `-50.0` (derived)).

4. **Transitions involving entries with missing `balance_*` fields at the end of the `ts`-ordered `flow` chain (Lines `24` -> `10` -> `25` -> `26` -> `11`)**:
   - **Line `10` (measured) (`2026-10-02T20:07:00+07:00` (measured)) after Line `24` (measured) (`2026-10-02T19:54:16+07:00` (measured))**:
     - Line `24` (measured) `balance_after` = `1181.0` (measured); Line `10` (measured) has no `balance_before`, `amount` = `111.0` (measured), `balance_after` = `581.0` (measured).
     - Comparing Line `24` (measured) `balance_after` (`1181.0` (measured)) to Line `10` (measured) implied `balance_before` (`581.0 + 111.0 = 692.0` (derived)): difference = `692.0 - 1181.0` = `-489.0` (derived) (or `+489.0` (derived)).
     - Comparing Line `24` (measured) `balance_after` (`1181.0` (measured)) directly to Line `10` (measured) `balance_after` (`581.0` (measured)): difference = `581.0 - 1181.0` = `-600.0` (derived) (or `+600.0` (derived)).
   - **Line `25` (measured) (`2026-10-02T20:09:05+07:00` (measured)) after Line `10` (measured) (`2026-10-02T20:07:00+07:00` (measured))**:
     - Line `10` (measured) `balance_after` = `581.0` (measured); Line `25` (measured) has no `balance_before` and no `balance_after` (`amount` = `12.0` (measured)).
   - **Line `26` (measured) (`2026-10-02T20:51:47+07:00` (measured)) after Line `25` (measured) / Line `10` (measured) / Line `24` (measured)**:
     - Compared to the immediately preceding measured `balance_after` in `ts` order (Line `10` (measured), `balance_after` = `581.0` (measured)): Line `26` (measured) `balance_before` = `1181.0` (measured); difference = `1181.0 - 581.0` = `+600.0` (derived) (or `-600.0` (derived)).
     - Compared to Line `24` (measured) `balance_after` (`1181.0` (measured)): Line `26` (measured) `balance_before` = `1181.0` (measured); difference = `1181.0 - 1181.0` = `0.0` (derived) (though Line `10` (`amount = 111.0` (measured)) and Line `25` (`amount = 12.0` (measured)) have timestamps between Line `24` and Line `26`).
   - **Line `11` (measured) (`2026-10-03T00:19:12+07:00` (measured)) after Line `26` (measured) (`2026-10-02T20:51:47+07:00` (measured))**:
     - Line `26` (measured) `balance_after` = `863.0` (measured); Line `11` (measured) has no `balance_before` and no `balance_after` (`amount` = `36.0` (measured)).

#### Engine `flow-music`
1. **Line `21` (measured) vs previous `ts`-ordered entry Line `16` (measured)** (`2026-10-01T14:37:08+07:00` (measured) -> `2026-10-02T17:58:18+07:00` (measured)):
   - Line `16` (measured) `balance_after` = `30580.0` (measured)
   - Line `21` (measured) `balance_before` = `30610.0` (measured)
   - Difference: `balance_before - prev_balance_after` = `30610.0 - 30580.0` = `+30.0` (derived) (or `prev_balance_after - balance_before` = `-30.0` (derived)).

---

## 3. Totals Per `engine × kind` and Per `channel`

### 3.1 Totals Per `engine × kind`

| Engine | Unit | Kind | Number of Entries | Total Amount | Line Numbers (measured) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `flow` | `credits` | `test` | `11` (derived) | `435.0` (derived) | `1, 3, 4, 5, 6, 8, 12, 13, 17, 22, 25` |
| `flow` | `credits` | `production` | `7` (derived) | `1923.0` (derived) | `7, 9, 10, 14, 18, 23, 26` |
| `flow` | `credits` | `reshoot` | `6` (derived) | `261.0` (derived) | `2, 11, 15, 19, 20, 24` |
| **`flow` Subtotal** | `credits` | **All kinds** | **`24` (derived)** | **`2619.0` (derived)** | `1–15, 17–20, 22–26` |
| `flow-music` | `credits` | `test` | `0` (derived) | `0.0` (derived) | — |
| `flow-music` | `credits` | `production` | `2` (derived) | `10.0` (derived) | `16, 21` |
| `flow-music` | `credits` | `reshoot` | `0` (derived) | `0.0` (derived) | — |
| **`flow-music` Subtotal** | `credits` | **All kinds** | **`2` (derived)** | **`10.0` (derived)** | `16, 21` |
| **All Engines Combined** | `credits` | `test` | `11` (derived) | `435.0` (derived) | `1, 3, 4, 5, 6, 8, 12, 13, 17, 22, 25` |
| **All Engines Combined** | `credits` | `production` | `9` (derived) | `1933.0` (derived) | `7, 9, 10, 14, 16, 18, 21, 23, 26` |
| **All Engines Combined** | `credits` | `reshoot` | `6` (derived) | `261.0` (derived) | `2, 11, 15, 19, 20, 24` |
| **Grand Total** | `credits` | **All kinds** | **`26` (derived)** | **`2629.0` (derived)** | `1–26` |

### 3.2 Totals Per `channel` (Overall and by `engine × kind`)

| Channel | Engine | Kind | Number of Entries | Total Amount | Line Numbers (measured) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ILAG ละครสั้นคุณธรรม` | `flow` | `test` | `5` (derived) | `357.0` (derived) | `1, 3, 4, 6, 8` |
| `ILAG ละครสั้นคุณธรรม` | `flow` | `production` | `3` (derived) | `843.0` (derived) | `7, 9, 10` |
| `ILAG ละครสั้นคุณธรรม` | `flow` | `reshoot` | `2` (derived) | `156.0` (derived) | `2, 11` |
| **`ILAG ละครสั้นคุณธรรม` Total** | **`flow`** | **All kinds** | **`10` (derived)** | **`1356.0` (derived)** | `1, 2, 3, 4, 6, 7, 8, 9, 10, 11` |
| `บ้านนี้มีข้าวเหนียว` | `flow` | `test` | `1` (derived) | `18.0` (measured/derived) | `5` |
| **`บ้านนี้มีข้าวเหนียว` Total** | **`flow`** | **All kinds** | **`1` (derived)** | **`18.0` (measured/derived)** | `5` |
| `บ้านนี้มีมีมี่` | `flow` | `test` | `5` (derived) | `60.0` (derived) | `12, 13, 17, 22, 25` |
| `บ้านนี้มีมีมี่` | `flow` | `production` | `4` (derived) | `1080.0` (derived) | `14, 18, 23, 26` |
| `บ้านนี้มีมีมี่` | `flow` | `reshoot` | `4` (derived) | `105.0` (derived) | `15, 19, 20, 24` |
| `บ้านนี้มีมีมี่` (`flow` Subtotal) | `flow` | All kinds | `13` (derived) | `1245.0` (derived) | `12, 13, 14, 15, 17, 18, 19, 20, 22, 23, 24, 25, 26` |
| `บ้านนี้มีมีมี่` (`flow-music` Subtotal) | `flow-music` | `production` | `2` (derived) | `10.0` (derived) | `16, 21` |
| **`บ้านนี้มีมีมี่` Total** | **`flow` + `flow-music`** | **All kinds** | **`15` (derived)** | **`1255.0` (derived)** | `12–26` |
| **All Channels Grand Total** | **All Engines** | **All kinds** | **`26` (derived)** | **`2629.0` (derived)** | `1–26` |

---

## 4. Entries Missing Fields Others Carry & Backfilled Entries

### 4.1 Entries Missing `task` or `balance_*` (and Other Optional Fields)

1. **Missing `task` value (`"task": ""` — empty string where lines `1, 2, 3, 4, 5, 6, 7` (measured) carry a task ID)** — `19` (derived) entries:
   - Line numbers: `8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26` (measured).
   - *(Note: The JSON key `"task"` is present in all `26` (derived) entries; it is non-empty on `7` (derived) entries — lines `1, 2, 3, 4, 6, 7` (measured) with `"task-c816fbc0"` and line `5` (measured) with `"task-f895d6f6"` — and empty `""` on the `19` (derived) entries listed above.)*

2. **Missing `balance_before` key** — `3` (derived) entries:
   - Line `10` (measured) (`ts: 2026-10-02T20:07:00+07:00` (measured), `amount: 111.0` (measured), `balance_after: 581.0` (measured) — missing `balance_before` only).
   - Line `11` (measured) (`ts: 2026-10-03T00:19:12+07:00` (measured), `amount: 36.0` (measured) — missing both `balance_before` and `balance_after`).
   - Line `25` (measured) (`ts: 2026-10-02T20:09:05+07:00` (measured), `amount: 12.0` (measured) — missing both `balance_before` and `balance_after`).

3. **Missing `balance_after` key** — `2` (derived) entries:
   - Line `11` (measured) (`ts: 2026-10-03T00:19:12+07:00` (measured), `amount: 36.0` (measured) — missing both `balance_before` and `balance_after`).
   - Line `25` (measured) (`ts: 2026-10-02T20:09:05+07:00` (measured), `amount: 12.0` (measured) — missing both `balance_before` and `balance_after`).

4. **Missing `note` key** — `10` (derived) entries:
   - Line numbers: `4, 8, 9, 17, 18, 19, 20, 21, 22, 25` (measured).
   - *(Present on `16` (derived) entries: lines `1, 2, 3, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 23, 24, 26` (measured).)*

5. **Missing `delta_mismatch` key** — `22` (derived) entries:
   - Line numbers: `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 25` (measured).
   - *(Present only on `4` (derived) entries: lines `17` (`-32.0` (measured)), `23` (`294.0` (measured)), `24` (`66.0` (measured)), and `26` (`318.0` (measured)).)*

### 4.2 Backfilled Entries (`note` says `backfilled`)

There are `2` (derived) backfilled entries (totaling `288.0` (derived) credits):
1. **Line `1` (measured)**:
   - `ts`: `2026-09-28T00:27:00+07:00` (measured)
   - `engine`: `flow`, `unit`: `credits`, `kind`: `test`, `amount`: `168.0` (measured)
   - `balance_before`: `3298.0` (measured), `balance_after`: `3130.0` (measured)
   - `note`: `"run 09-27 23:17 to 09-28 00:27; backfilled 09-28 18:55"`
2. **Line `2` (measured)**:
   - `ts`: `2026-09-28T04:30:00+07:00` (measured)
   - `engine`: `flow`, `unit`: `credits`, `kind`: `reshoot`, `amount`: `120.0` (measured)
   - `balance_before`: `3130.0` (measured), `balance_after`: `3010.0` (measured)
   - `note`: `"time approximate (before the 04:50 Drive upload); backfilled 09-28 18:55"`

---

## Files Changed
- `docs/reports/task-4f702eb0/REPORT.md` (created)
- `REPORT.md` (created at worktree root with identical content)
- `docs/ops/credit-ledger.jsonl` was **not** modified.

## Validation Performed
- Read all `26` (derived) JSONL entries from `docs/ops/credit-ledger.jsonl` via `view_file`.
- Cross-checked all sums across `engine`, `kind`, and `channel` partitions (`2619.0 + 10.0 = 2629.0` (derived); `435.0 + 1933.0 + 261.0 = 2629.0` (derived); `1356.0 + 18.0 + 1255.0 = 2629.0` (derived)) and verified every within-entry balance delta and chronological (`ts`-ordered) between-entry balance transition.

## Limitations
- Per the AGY worker contract ("For AGY, use file tools only; leave shell validation to the review process"), only file tools were used.
- Entries on lines `10` (measured), `11` (measured), and `25` (measured) lack `balance_before` and/or `balance_after` in `docs/ops/credit-ledger.jsonl`, so both measured values and derived comparisons across those entries are reported.

## Blockers
- (none)

## Skill learning
- (none)
