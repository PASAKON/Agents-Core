# REPORT task-136c0b0f

## Executive Summary

Between 1–15 Oct 2026, the task hub recorded **288** (measured) tasks across **11** (measured) worker roles.
- **Claude load (explicit `claude` + default `empty` runner):** **181** (derived) tasks (**62.85%**, derived, of all **288** measured tasks), comprising **108** (measured) explicit `claude` tasks (**37.50%**, derived) and **73** (measured) `empty` runner tasks (**25.35%**, derived) that ran on the default runner (Claude).
- **Outside runner load (`codex` + `agy`):** **107** (derived) tasks (**37.15%**, derived), comprising **65** (measured) `codex` tasks (**22.57%**, derived) and **42** (measured) `agy` tasks (**14.58%**, derived).
- **Trend (1–7 Oct vs 8–15 Oct):** Total tasks shifted from **148** (measured) in 1–7 Oct to **140** (measured) in 8–15 Oct (**−8**, derived, or **−5.41%**, derived). Effective Claude tasks (`claude` + `empty`) dropped from **103** (derived; **69.59%** share, derived) to **78** (derived; **55.71%** share, derived), a reduction of **−25** (derived) tasks (**−13.88 percentage points**, derived), driven by a **−29** (derived) drop in `empty` default-runner tasks (**51** measured → **22** measured) and a **+17** (derived) expansion in outside runners (`codex` **+5** derived, `agy` **+12** derived).
- **Primary candidate roles to move off Claude:** `developer` accounts for **149** (derived) of all **181** (derived) effective Claude tasks (**82.32%**, derived; **95** measured explicit `claude` + **54** measured `empty`), followed by `security_engineer` (**8** derived; **4.42%** share, derived), `video_editor` (**7** derived; **3.87%** share, derived), `browser_operator` (**6** derived; **3.31%** share, derived), `backend_dev` (**5** measured `empty`; **2.76%** share, derived), and `script_writer` (**3** measured `empty`; **1.66%** share, derived).

---

## 1. Tasks Created 1–15 Oct (Full Window)

### 1a. Count by Runner (1–15 Oct)

Empty `runner` values (`""`) ran on the default runner (Claude). Both raw runner counts and combined effective Claude counts (`claude` + `empty`) are shown below.

| Runner | Task Count (1–15 Oct) | Share of All Tasks (288 measured) | Effective Runner Group | Group Task Count | Group Share |
| :--- | ---: | ---: | :--- | ---: | ---: |
| `claude` | 108 (measured) | 37.50% (derived) | Effective Claude (`claude` + `empty`) | 181 (derived) | 62.85% (derived) |
| `empty` (default = Claude) | 73 (measured) | 25.35% (derived) | Effective Claude (`claude` + `empty`) | — | — |
| `codex` | 65 (measured) | 22.57% (derived) | Outside (`codex` + `agy`) | 107 (derived) | 37.15% (derived) |
| `agy` | 42 (measured) | 14.58% (derived) | Outside (`codex` + `agy`) | — | — |
| **Total** | **288** (measured) | **100.00%** (derived) | **All Runners** | **288** (measured) | **100.00%** (derived) |

### 1b. Count by `runner_model` and `runner × runner_model` (1–15 Oct)

| `runner_model` | `claude` | `codex` | `agy` | `empty` (default = Claude) | Total Tasks | Share of All Tasks (288 measured) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `(empty)` | 66 (measured) | 64 (measured) | 3 (measured) | 72 (measured) | **205** (measured) | 71.18% (derived) |
| `claude-sonnet-5-5` | 34 (measured) | 0 (measured) | 0 (measured) | 0 (measured) | **34** (measured) | 11.81% (derived) |
| `gemini-3.8-flash-high` | 1 (measured) | 0 (measured) | 25 (measured) | 1 (measured) | **27** (measured) | 9.38% (derived) |
| `claude-sonnet-5-5-high` | 0 (measured) | 0 (measured) | 8 (measured) | 0 (measured) | **8** (measured) | 2.78% (derived) |
| `sonnet` | 7 (measured) | 0 (measured) | 0 (measured) | 0 (measured) | **7** (measured) | 2.43% (derived) |
| `gemini-4-argon-high` | 0 (measured) | 0 (measured) | 5 (measured) | 0 (measured) | **5** (measured) | 1.74% (derived) |
| `claude-sonnet-4-6` | 0 (measured) | 0 (measured) | 1 (measured) | 0 (measured) | **1** (measured) | 0.35% (derived) |
| `gpt-6-sol` | 0 (measured) | 1 (measured) | 0 (measured) | 0 (measured) | **1** (measured) | 0.35% (derived) |
| **Total** | **108** (measured) | **65** (measured) | **42** (measured) | **73** (measured) | **288** (measured) | **100.00%** (derived) |

### 1c. Count by `role × runner` (1–15 Oct)

| Role | `claude` | `empty` (default = Claude) | Effective Claude (`claude` + `empty`) | `codex` | `agy` | Total Tasks | Role Share of All Tasks |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `developer` | 95 (measured) | 54 (measured) | 149 (derived) | 57 (measured) | 38 (measured) | **244** (measured) | 84.72% (derived) |
| `security_engineer` | 4 (measured) | 4 (measured) | 8 (derived) | 1 (measured) | 1 (measured) | **10** (measured) | 3.47% (derived) |
| `backend_dev` | 0 (measured) | 5 (measured) | 5 (derived) | 2 (measured) | 2 (measured) | **9** (measured) | 3.12% (derived) |
| `video_editor` | 4 (measured) | 3 (measured) | 7 (derived) | 0 (measured) | 0 (measured) | **7** (measured) | 2.43% (derived) |
| `browser_operator` | 4 (measured) | 2 (measured) | 6 (derived) | 0 (measured) | 0 (measured) | **6** (measured) | 2.08% (derived) |
| `researcher` | 0 (measured) | 0 (measured) | 0 (derived) | 4 (measured) | 0 (measured) | **4** (measured) | 1.39% (derived) |
| `script_writer` | 0 (measured) | 3 (measured) | 3 (derived) | 0 (measured) | 0 (measured) | **3** (measured) | 1.04% (derived) |
| `content_strategist` | 0 (measured) | 1 (measured) | 1 (derived) | 0 (measured) | 1 (measured) | **2** (measured) | 0.69% (derived) |
| `devops_engineer` | 0 (measured) | 1 (measured) | 1 (derived) | 0 (measured) | 0 (measured) | **1** (measured) | 0.35% (derived) |
| `reviewer` | 0 (measured) | 0 (measured) | 0 (derived) | 1 (measured) | 0 (measured) | **1** (measured) | 0.35% (derived) |
| `tester` | 1 (measured) | 0 (measured) | 1 (derived) | 0 (measured) | 0 (measured) | **1** (measured) | 0.35% (derived) |
| **Total** | **108** (measured) | **73** (measured) | **181** (derived) | **65** (measured) | **42** (measured) | **288** (measured) | **100.00%** (derived) |

---

## 2. Two-Window Split: 1–7 Oct vs 8–15 Oct (and Change)

Window definitions (by UTC `created_at` date):
- **Window 1 (1–7 Oct):** `2026-10-01T00:00:00+00:00` through `2026-10-07T23:59:59+00:00` (**148** measured tasks).
- **Window 2 (8–15 Oct):** `2026-10-08T00:00:00+00:00` through `2026-10-15T23:59:59+00:00` (**140** measured tasks).

### 2a. By Runner (1–7 Oct vs 8–15 Oct)

| Runner | 1–7 Oct Count | 1–7 Oct Share | 8–15 Oct Count | 8–15 Oct Share | Change (Count) | Change (% / Share pp) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `claude` | 52 (measured) | 35.14% (derived) | 56 (measured) | 40.00% (derived) | +4 (derived) | +7.69% / +4.86 pp (derived) |
| `empty` (default = Claude) | 51 (measured) | 34.46% (derived) | 22 (measured) | 15.71% (derived) | −29 (derived) | −56.86% / −18.75 pp (derived) |
| **Effective Claude (`claude` + `empty`)** | **103** (derived) | **69.59%** (derived) | **78** (derived) | **55.71%** (derived) | **−25** (derived) | **−24.27% / −13.88 pp** (derived) |
| `codex` | 30 (measured) | 20.27% (derived) | 35 (measured) | 25.00% (derived) | +5 (derived) | +16.67% / +4.73 pp (derived) |
| `agy` | 15 (measured) | 10.14% (derived) | 27 (measured) | 19.29% (derived) | +12 (derived) | +80.00% / +9.15 pp (derived) |
| **Outside Runners (`codex` + `agy`)** | **45** (derived) | **30.41%** (derived) | **62** (derived) | **44.29%** (derived) | **+17** (derived) | **+37.78% / +13.88 pp** (derived) |
| **Total** | **148** (measured) | **100.00%** (derived) | **140** (measured) | **100.00%** (derived) | **−8** (derived) | **−5.41%** (derived) |

### 2b. By `runner_model` and `runner × runner_model` (1–7 Oct vs 8–15 Oct)

| `runner_model` | Runner | 1–7 Oct | 8–15 Oct | Total (1–15 Oct) | Change (Count) | Change (%) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `(empty)` | *All runners* | **125** (measured) | **80** (measured) | **205** (measured) | **−45** (derived) | **−36.00%** (derived) |
| ↳ `(empty)` | `claude` | 42 (measured) | 24 (measured) | 66 (measured) | −18 (derived) | −42.86% (derived) |
| ↳ `(empty)` | `codex` | 30 (measured) | 34 (measured) | 64 (measured) | +4 (derived) | +13.33% (derived) |
| ↳ `(empty)` | `agy` | 3 (measured) | 0 (measured) | 3 (measured) | −3 (derived) | −100.00% (derived) |
| ↳ `(empty)` | `empty` | 50 (measured) | 22 (measured) | 72 (measured) | −28 (derived) | −56.00% (derived) |
| `claude-sonnet-5-5` | `claude` (all) | **9** (measured) | **25** (measured) | **34** (measured) | **+16** (derived) | **+177.78%** (derived) |
| `gemini-3.8-flash-high` | *All runners* | **9** (measured) | **18** (measured) | **27** (measured) | **+9** (derived) | **+100.00%** (derived) |
| ↳ `gemini-3.8-flash-high` | `agy` | 7 (measured) | 18 (measured) | 25 (measured) | +11 (derived) | +157.14% (derived) |
| ↳ `gemini-3.8-flash-high` | `claude` | 1 (measured) | 0 (measured) | 1 (measured) | −1 (derived) | −100.00% (derived) |
| ↳ `gemini-3.8-flash-high` | `empty` | 1 (measured) | 0 (measured) | 1 (measured) | −1 (derived) | −100.00% (derived) |
| `claude-sonnet-5-5-high` | `agy` (all) | **4** (measured) | **4** (measured) | **8** (measured) | **0** (derived) | **0.00%** (derived) |
| `sonnet` | `claude` (all) | **0** (measured) | **7** (measured) | **7** (measured) | **+7** (derived) | **N/A (new)** |
| `gemini-4-argon-high` | `agy` (all) | **0** (measured) | **5** (measured) | **5** (measured) | **+5** (derived) | **N/A (new)** |
| `claude-sonnet-4-6` | `agy` (all) | **1** (measured) | **0** (measured) | **1** (measured) | **−1** (derived) | **−100.00%** (derived) |
| `gpt-6-sol` | `codex` (all) | **0** (measured) | **1** (measured) | **1** (measured) | **+1** (derived) | **N/A (new)** |
| **Total** | **All** | **148** (measured) | **140** (measured) | **288** (measured) | **−8** (derived) | **−5.41%** (derived) |

### 2c. By `role × runner` (1–7 Oct vs 8–15 Oct and Change)

| Role | Runner (`claude` / `empty` / Eff. Claude / `codex` / `agy` / Total) | 1–7 Oct (W1) | 8–15 Oct (W2) | Change (W2 − W1) |
| :--- | :--- | :--- | :--- | :--- |
| `developer` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 46 / 42 / **88** / 28 / 13 / **129** (measured; Eff. Claude derived) | 49 / 12 / **61** / 29 / 25 / **115** (measured; Eff. Claude derived) | +3 / −30 / **−27** / +1 / +12 / **−14** (derived) |
| `security_engineer` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 1 / 0 / **1** / 0 / 0 / **1** (measured; Eff. Claude derived) | 3 / 4 / **7** / 1 / 1 / **9** (measured; Eff. Claude derived) | +2 / +4 / **+6** / +1 / +1 / **+8** (derived) |
| `backend_dev` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 0 / 3 / **3** / 2 / 2 / **7** (measured; Eff. Claude derived) | 0 / 2 / **2** / 0 / 0 / **2** (measured; Eff. Claude derived) | 0 / −1 / **−1** / −2 / −2 / **−5** (derived) |
| `video_editor` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 4 / 2 / **6** / 0 / 0 / **6** (measured; Eff. Claude derived) | 0 / 1 / **1** / 0 / 0 / **1** (measured; Eff. Claude derived) | −4 / −1 / **−5** / 0 / 0 / **−5** (derived) |
| `browser_operator` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 1 / 1 / **2** / 0 / 0 / **2** (measured; Eff. Claude derived) | 3 / 1 / **4** / 0 / 0 / **4** (measured; Eff. Claude derived) | +2 / 0 / **+2** / 0 / 0 / **+2** (derived) |
| `researcher` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 0 / 0 / **0** / 0 / 0 / **0** (measured; Eff. Claude derived) | 0 / 0 / **0** / 4 / 0 / **4** (measured; Eff. Claude derived) | 0 / 0 / **0** / +4 / 0 / **+4** (derived) |
| `script_writer` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 0 / 2 / **2** / 0 / 0 / **2** (measured; Eff. Claude derived) | 0 / 1 / **1** / 0 / 0 / **1** (measured; Eff. Claude derived) | 0 / −1 / **−1** / 0 / 0 / **−1** (derived) |
| `content_strategist` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 0 / 0 / **0** / 0 / 0 / **0** (measured; Eff. Claude derived) | 0 / 1 / **1** / 0 / 1 / **2** (measured; Eff. Claude derived) | 0 / +1 / **+1** / 0 / +1 / **+2** (derived) |
| `devops_engineer` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 0 / 1 / **1** / 0 / 0 / **1** (measured; Eff. Claude derived) | 0 / 0 / **0** / 0 / 0 / **0** (measured; Eff. Claude derived) | 0 / −1 / **−1** / 0 / 0 / **−1** (derived) |
| `reviewer` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 0 / 0 / **0** / 0 / 0 / **0** (measured; Eff. Claude derived) | 0 / 0 / **0** / 1 / 0 / **1** (measured; Eff. Claude derived) | 0 / 0 / **0** / +1 / 0 / **+1** (derived) |
| `tester` | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 0 / 0 / **0** / 0 / 0 / **0** (measured; Eff. Claude derived) | 1 / 0 / **1** / 0 / 0 / **1** (measured; Eff. Claude derived) | +1 / 0 / **+1** / 0 / 0 / **+1** (derived) |
| **Total** | `claude` / `empty` / **Eff. Claude** / `codex` / `agy` / **Total** | 52 / 51 / **103** / 30 / 15 / **148** (measured; Eff. Claude derived) | 56 / 22 / **78** / 35 / 27 / **140** (measured; Eff. Claude derived) | +4 / −29 / **−25** / +5 / +12 / **−8** (derived) |

---

## 3. Rough Worker Minutes (`updated_at − spawned_at`)

All worker minute figures below are **rough** upper bounds (`updated_at − spawned_at` in minutes) because `updated_at` reflects the latest status/review update rather than pure active worker runtime (for example, 17 `mooniex-bedrock` tasks spawned on 4–5 Oct were batch-updated to `done` at `2026-10-14T08:09:49–55+00:00`, adding ~13,000+ rough minutes each).

Out of **288** (measured) total tasks, **213** (measured) have both `spawned_at` and `updated_at` present (**75** measured tasks have an empty `spawned_at`).
- *Timestamp format note:* One `empty`-runner `developer` row created `2026-10-01T14:14:17+00:00` has `updated_at` formatted as `2026-10-01 14:46:53` (without `+00:00`). Since all exported times are UTC, this row is included (**32.03** derived rough minutes = **1,922** derived seconds). Footnotes show the exact values if a strict offset-requiring parser excludes that single row (**212** measured tasks).

### 3a. Rough Worker Minutes per Runner

| Runner | Tasks (All) | Tasks with `spawned_at` & `updated_at` | Rough Total Seconds (derived) | Rough Total Minutes (derived) | Rough Median Seconds (derived) | Rough Median Minutes (derived) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `claude` | 108 (measured) | 92 (measured) | 3,279,782 s | **54,663.03 min** | 3,110.5 s | **51.84 min** |
| `empty` (default = Claude)* | 73 (measured) | 23 (measured) | 327,780 s | **5,463.00 min** | 4,191.0 s | **69.85 min** |
| **Effective Claude (`claude` + `empty`)*** | **181** (derived) | **115** (derived) | **3,607,562 s** | **60,126.03 min** | **3,231.0 s** | **53.85 min** |
| `codex` | 65 (measured) | 59 (measured) | 13,673,331 s | **227,888.85 min** | 1,241.0 s | **20.68 min** |
| `agy` | 42 (measured) | 39 (measured) | 604,770 s | **10,079.50 min** | 651.0 s | **10.85 min** |
| **All Runners*** | **288** (measured) | **213** (measured) | **17,885,663 s** | **298,094.38 min** | **2,190.0 s** | **36.50 min** |

*\*If the single row with `updated_at = "2026-10-01 14:46:53"` is excluded: `empty` has **22** (measured) tasks, rough total = **325,858 s** (**5,430.97 min**, derived), rough median = **3,951.0 s** (**65.85 min**, derived); Effective Claude (`claude` + `empty`) has **114** (derived) tasks, rough total = **3,605,640 s** (**60,094.00 min**, derived), rough median = **3,295.0 s** (**54.92 min**, derived); All Runners has **212** (measured) tasks, rough total = **17,883,741 s** (**298,062.35 min**, derived), rough median = **2,229.5 s** (**37.16 min**, derived).*

### 3b. Rough Worker Minutes per Role

| Role | Tasks (All) | Tasks with `spawned_at` & `updated_at` | Rough Total Seconds (derived) | Rough Total Minutes (derived) | Rough Median Seconds (derived) | Rough Median Minutes (derived) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `developer`* | 244 (measured) | 182 (measured) | 17,223,073 s | **287,051.22 min** | 2,271.0 s | **37.85 min** |
| `security_engineer` | 10 (measured) | 8 (measured) | 407,197 s | **6,786.62 min** | 5,514.0 s | **91.90 min** |
| `video_editor` | 7 (measured) | 7 (measured) | 112,524 s | **1,875.40 min** | 12,879.0 s | **214.65 min** |
| `browser_operator` | 6 (measured) | 6 (measured) | 94,063 s | **1,567.72 min** | 4,975.5 s | **82.93 min** (82.925) |
| `script_writer` | 3 (measured) | 3 (measured) | 18,264 s | **304.40 min** | 7,520.0 s | **125.33 min** |
| `researcher` | 4 (measured) | 4 (measured) | 15,573 s | **259.55 min** | 158.0 s | **2.63 min** |
| `devops_engineer` | 1 (measured) | 1 (measured) | 12,030 s | **200.50 min** | 12,030.0 s | **200.50 min** |
| `tester` | 1 (measured) | 1 (measured) | 2,508 s | **41.80 min** | 2,508.0 s | **41.80 min** |
| `content_strategist` | 2 (measured) | 1 (measured) | 431 s | **7.18 min** | 431.0 s | **7.18 min** |
| `backend_dev` | 9 (measured) | 0 (measured) | 0 s | **N/A (0 tasks)** | N/A | **N/A (0 tasks)** |
| `reviewer` | 1 (measured) | 0 (measured) | 0 s | **N/A (0 tasks)** | N/A | **N/A (0 tasks)** |
| **Total*** | **288** (measured) | **213** (measured) | **17,885,663 s** | **298,094.38 min** | **2,190.0 s** | **36.50 min** |

*\*If the single `developer` row with `updated_at = "2026-10-01 14:46:53"` is excluded: `developer` has **181** (measured) tasks, rough total = **17,221,151 s** (**287,019.18 min**, derived), rough median = **2,273.0 s** (**37.88 min**, derived).*

---

## 4. `runner_fit` Records: Runs and First-Pass Rate by `runner:model × job_type`

### Rules Stated and Used
Data set 2 contains **28** (measured) JSON records. Two definitions of "first-pass" exist in the schema and prompt:
1. **Prompt Formula Rule (`result == "pass" and iteration <= 1`):** Evaluates whether `result == "pass"` and `iteration <= 1` (if `iteration` is present; in all **28** measured records, `iteration` is present and is `0` or `1`). Under this rule, **24** (derived) of **28** (measured) runs pass (**85.71%**, derived).
2. **Recorded `first_pass` Field Rule (`first_pass == true`, i.e., `result == "pass" and iteration <= 1 and not reviewer_fix`):** Uses the boolean `"first_pass"` field directly recorded in each JSON object, which sets `first_pass: false` whenever `reviewer_fix: true` even if `result == "pass"` and `iteration <= 1`. Under this rule, **16** (measured) of **28** (measured) runs pass on the first pass without reviewer fix (**57.14%**, derived).

Both metrics are reported side-by-side below so re-derivation under either convention is exact. Additionally, for `codex` where `"model"` is `""` (1 record) or `null` (6 records), both the combined `codex:(default/empty)` rows and the split `codex:""` vs `codex:null` rows are shown.

| `runner:model` | `job_type` | Runs (measured) | Formula Pass Count (`result=="pass" & iter<=1`) | Formula First-Pass Rate (derived) | Recorded `first_pass == true` Count (measured) | Recorded `first_pass` Rate (derived) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `agy:gemini-4-argon-high` | `fix` | 4 (measured) | 4 (derived) | 100.00% (derived) | 2 (measured) | 50.00% (derived) |
| `agy:gemini-4-argon-high` | `code` | 2 (measured) | 1 (derived) | 50.00% (derived) | 0 (measured) | 0.00% (derived) |
| `agy:gemini-4-argon-high` | `docs` | 2 (measured) | 2 (derived) | 100.00% (derived) | 1 (measured) | 50.00% (derived) |
| `agy:gemini-4-argon-high` | `research` | 1 (measured) | 1 (derived) | 100.00% (derived) | 0 (measured) | 0.00% (derived) |
| `agy:gemini-4-argon-high` | `skill` | 1 (measured) | 0 (derived) | 0.00% (derived) | 0 (measured) | 0.00% (derived) |
| *Subtotal `agy:gemini-4-argon-high`* | *All* | *10 (measured)* | *8 (derived)* | *80.00% (derived)* | *3 (measured)* | *30.00% (derived)* |
| `agy:gemini-3.8-flash-high` | `code` | 3 (measured) | 3 (derived) | 100.00% (derived) | 1 (measured) | 33.33% (derived) |
| `agy:gemini-3.8-flash-high` | `docs` | 1 (measured) | 1 (derived) | 100.00% (derived) | 1 (measured) | 100.00% (derived) |
| `agy:gemini-3.8-flash-high` | `tests` | 1 (measured) | 0 (derived) | 0.00% (derived) | 0 (measured) | 0.00% (derived) |
| *Subtotal `agy:gemini-3.8-flash-high`* | *All* | *5 (measured)* | *4 (derived)* | *80.00% (derived)* | *2 (measured)* | *40.00% (derived)* |
| `codex:(empty/null)` (`model: null`) | `research` | 4 (measured) | 4 (derived) | 100.00% (derived) | 4 (measured) | 100.00% (derived) |
| `codex:(empty/null)` (`model: null`) | `code` | 2 (measured) | 2 (derived) | 100.00% (derived) | 2 (measured) | 100.00% (derived) |
| `codex:(empty/null)` (`model: ""`) | `tests` | 1 (measured) | 1 (derived) | 100.00% (derived) | 1 (measured) | 100.00% (derived) |
| *Subtotal `codex:(empty/null)`* | *All* | *7 (measured)* | *7 (derived)* | *100.00% (derived)* | *7 (measured)* | *100.00% (derived)* |
| `codex:gpt-6-sol` | `code` | 1 (measured) | 1 (derived) | 100.00% (derived) | 0 (measured) | 0.00% (derived) |
| `claude:claude-sonnet-5-5` | `fix` | 4 (measured) | 3 (derived) | 75.00% (derived) | 3 (measured) | 75.00% (derived) |
| `claude:claude-opus-5-5`* | `code` | 1 (measured) | 1 (derived) | 100.00% (derived) | 1 (measured) | 100.00% (derived) |
| **Total** | **All** | **28** (measured) | **24** (derived) | **85.71%** (derived) | **16** (measured) | **57.14%** (derived) |

*\*Note on `claude:claude-opus-5-5`: The record carries `"note": "C-level own work, not a worker; before the ruling"`. Excluding that 1 non-worker record yields **27** (derived) worker runs: **23/27** (**85.19%**, derived) under the formula rule and **15/27** (**55.56%**, derived) under `first_pass == true`.*

---

## 5. Roles Still Mostly on Claude (Ranked Candidates for Moving)

A role is "mostly on Claude" if >50% of its tasks ran on Claude (either under **Effective Claude** = `claude` + `empty` default, Total = **181** derived tasks, or under **Explicit `claude`** alone, Total = **108** measured tasks). All **8** roles with any Claude usage have ≥50% of their tasks on Effective Claude (**7** roles have >50%, and `content_strategist` is at exactly 50.00%).

| Rank (by Eff. Claude Tasks) | Role | Effective Claude Tasks (`claude` + `empty`) | Total Role Tasks | Claude % Within Role (Eff. Claude / Role Total) | Share of All 181 Effective Claude Tasks | Explicit `claude` Tasks | Share of All 108 Explicit `claude` Tasks | 8–15 Oct Eff. Claude / Role Total | Candidate Assessment |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **1** | `developer` | **149** (derived) | 244 (measured) | **61.07%** (derived) | **82.32%** (derived) | 95 (measured) | 87.96% (derived) | 61 / 115 (53.04%, derived) | **Primary candidate:** 82.32% of all Claude tasks; `codex` (57 tasks) and `agy` (38 tasks) already proven. |
| **2** | `security_engineer` | **8** (derived) | 10 (measured) | **80.00%** (derived) | **4.42%** (derived) | 4 (measured) | 3.70% (derived) | 7 / 9 (77.78%, derived) | **High candidate:** Grew from 1 to 9 tasks in W2; 80% on Claude, with 1 `codex` and 1 `agy` task already tried. |
| **3** | `video_editor` | **7** (derived) | 7 (measured) | **100.00%** (derived) | **3.87%** (derived) | 4 (measured) | 3.70% (derived) | 1 / 1 (100.00%, derived) | **100% on Claude:** All 7 tasks ran on `claude` (4) or `empty` (3); 1,875.40 rough min. |
| **4** | `browser_operator` | **6** (derived) | 6 (measured) | **100.00%** (derived) | **3.31%** (derived) | 4 (measured) | 3.70% (derived) | 4 / 4 (100.00%, derived) | **100% on Claude:** All 6 tasks on Claude, but browser tool dependency may constrain non-browser runners. |
| **5** | `backend_dev` | **5** (derived) | 9 (measured) | **55.56%** (derived) | **2.76%** (derived) | 0 (measured) | 0.00% (derived) | 2 / 2 (100.00%, derived) | **Default-runner candidate:** All 5 Claude tasks were unpinned (`empty` runner); can be routed to `codex`/`agy` by setting explicit runner. |
| **6** | `script_writer` | **3** (derived) | 3 (measured) | **100.00%** (derived) | **1.66%** (derived) | 0 (measured) | 0.00% (derived) | 1 / 1 (100.00%, derived) | **Default-runner candidate:** All 3 tasks had `empty` runner; text/docs generation fits `agy` (`docs` 100% pass). |
| **7 (tie)** | `devops_engineer` | **1** (derived) | 1 (measured) | **100.00%** (derived) | **0.55%** (derived) | 0 (measured) | 0.00% (derived) | 0 / 0 (N/A) | **Low volume:** 1 `empty`-runner task in W1, 0 in W2. |
| **7 (tie)** | `tester` | **1** (derived) | 1 (measured) | **100.00%** (derived) | **0.55%** (derived) | 1 (measured) | 0.93% (derived) | 1 / 1 (100.00%, derived) | **Low volume (prefer `codex`):** 1 explicit `claude` task; `runner_fit` shows `codex` passes `tests` (1/1) while `agy` failed `no-shell`. |
| *—* | *`content_strategist` (50%)* | *1 (derived)* | *2 (measured)* | *50.00% (derived)* | *0.55% (derived)* | *0 (measured)* | *0.00% (derived)* | *1 / 2 (50.00%, derived)* | *Already 50% on `agy` (the 1 `empty` task was cancelled before spawn).* |
| *—* | *`researcher` (0%)* | *0 (derived)* | *4 (measured)* | *0.00% (derived)* | *0.00% (derived)* | *0 (measured)* | *0.00% (derived)* | *0 / 4 (0.00%, derived)* | *Already 100% migrated to `codex` (4/4 tasks, 100% first-pass in `runner_fit`).* |
| *—* | *`reviewer` (0%)* | *0 (derived)* | *1 (measured)* | *0.00% (derived)* | *0.00% (derived)* | *0 (measured)* | *0.00% (derived)* | *0 / 1 (0.00%, derived)* | *Already on `codex` (1/1 task).* |

---

## Appendix: Counting Method and Filters

```python
# Pseudo-code / exact filters used to derive all numbers from Data Set 1 & Data Set 2:

# 1. Data Set 1 (288 CSV rows, header: id,created_at,spawned_at,updated_at,status,project,role,owner_role,runner,runner_model,iteration)
# - Date parsing: parse ISO-8601 UTC timestamps. (Note: row 288 has updated_at="2026-10-01 14:46:53",
#   which is UTC without "+00:00"; normalize by attaching UTC timezone).
# - Full window filter: "2026-10-01" <= created_at[:10] <= "2026-10-15" (matches all 288 rows).
# - Window 1 filter (1-7 Oct): "2026-10-01" <= created_at[:10] <= "2026-10-07" (148 rows).
# - Window 2 filter (8-15 Oct): "2026-10-08" <= created_at[:10] <= "2026-10-15" (140 rows).
# - Runner buckets:
#     raw_runner = row.runner if row.runner != "" else "empty"
#     effective_claude = (raw_runner in {"claude", "empty"})
# - Model buckets:
#     raw_model = row.runner_model if row.runner_model != "" else "(empty)"
# - Rough worker minutes (Section 3):
#     filter: row.spawned_at != "" and row.updated_at != "" (213 rows; 75 rows have spawned_at == "")
#     rough_minutes = (parse_utc(row.updated_at) - parse_utc(row.spawned_at)).total_seconds() / 60.0
#     total = sum(rough_minutes), median = statistics.median(rough_minutes)

# 2. Data Set 2 (28 JSONL runner_fit records)
# - Key: (record["runner"], record["model"] or "(empty/null)", record["job_type"])
# - Runs: count of records per key (total = 28).
# - First-pass Rule A (Prompt formula):
#     record["result"] == "pass" and (record.get("iteration") is None or record["iteration"] <= 1)
# - First-pass Rule B (Recorded boolean field):
#     record["first_pass"] is True  # equivalent to Rule A and not record.get("reviewer_fix", False)
```

---

## Execution Details

### Files Changed
- `docs/reports/task-136c0b0f/REPORT.md` (created)
- `REPORT.md` (created at worktree root as requested in `TASK.md`)

### Validation Performed
- Verified all **288** (measured) CSV task rows and **28** (measured) JSONL `runner_fit` records directly from `TASK.md`.
- Cross-checked row totals across runners (`108 + 73 + 65 + 42 = 288`), windows (`148 + 140 = 288`), models (`205 + 34 + 27 + 8 + 7 + 5 + 1 + 1 = 288`), roles (`244 + 10 + 9 + 7 + 6 + 4 + 3 + 2 + 1 + 1 + 1 = 288`), and rough worker seconds across runners and roles (`17,885,663 s` = `298,094.38 min` across `213` tasks with `spawned_at` and `updated_at`).
- Per the AGY Remote Worker Contract, used file tools only and left shell validation to the review process.

### Limitations
- `updated_at − spawned_at` is a rough upper bound on worker runtime because `updated_at` changes whenever a task is reviewed, cancelled, or batch-closed days after completion.
- In `runner_fit`, sample sizes per `runner:model × job_type` cell are small (1 to 4 runs per cell, 28 runs total).

## Blockers
- (none)

## Skill learning
- (none)
