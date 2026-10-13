# Agents-Core Thai → English Translation Batches (On-Demand Docs & Code Comments)

**Backlog item:** `f2209b5b` item 5 (due 2026-10-23)  
**Source snapshot:** `docs/ops/thai-inventory-2026-10-14/rows.jsonl` (`README.md`, `summary.md`)  
**Scope:** Rows in `rows.jsonl` with `repo == "Agents-Core"` whose `kinds` has a `"doc"` or `"comment"` key.

## Totals & Reconciliation with `rows.jsonl`

- **Totals line:** **393 in-scope files** | **104,654 translate characters** (74,037 keep characters; 178,691 total Thai characters) | **27 batches** (274 files, 99,614 translate characters, 69,245 keep characters) | **119 skipped files** (5,040 translate characters, 4,792 keep characters).

| Category | Files | `translate` chars | `keep` chars | Total `thai` chars | Batches | Notes |
|---|---:|---:|---:|---:|---:|---|
| In-scope `doc` batches (`B01`–`B20`) | 166 | 89,522 | 30,334 | 119,856 | 20 | Ordered high-value (`runbooks`, `ops`, `design`, `skills`) → archives (`reports`, `output`) |
| In-scope `comment` batches (`B21`–`B27`) | 108 | 10,092 | 38,911 | 49,003 | 7 | Placed last; all marked **needs comment-only check** (`tools/comment_only_check.py`) |
| **Batched subtotal (`B01`–`B27`)** | **274** | **99,614** | **69,245** | **168,859** | **27** | Every batch ≤ 20 files and ≤ 8,000 `translate` chars |
| Skipped `doc` files (`S1`, `S2`, `S3`, `S4`) | 71 | 4,628 | 3,425 | 8,053 | — | Generated reports/logs, source descriptions, user-facing copy, archived letters, `translate <= 15` |
| Skipped `comment` files (`S4`) | 48 | 412 | 1,367 | 1,779 | — | Almost all keep-kinds / dust threshold (`translate <= 15`) |
| **Skipped subtotal** | **119** | **5,040** | **4,792** | **9,832** | — | Every skipped file listed below with its rule and reason |
| **Total in-scope (`doc` + `comment` in `rows.jsonl`)** | **393** | **104,654** | **74,037** | **178,691** | **27** | 237 `doc` files (94,150 `translate`) + 156 `comment` files (10,504 `translate`) |

*Reconciliation with `rows.jsonl` and `summary.md`:* `rows.jsonl` contains 1,269 rows across the 3 public repos (`Agents-Core`, `Agents-Rules`, `Chatudo-Webapp`), of which 1,197 rows have `repo == "Agents-Core"`. Among those 1,197 `Agents-Core` rows:
- **393 rows** have `"doc"` (237 files, 94,150 `translate` chars) or `"comment"` (156 files, 10,504 `translate` chars) in `kinds` → **in scope (104,654 `translate` chars)**.
- **41 rows** have `translate > 0` from `"always_loaded"` or `"skill_body"` only (5 `T0_session` role files = 3,430 `translate` chars; 36 `T2_trigger` `SKILL.md` files = 8,598 `translate` chars; subtotal = 12,028 `translate` chars, already tracked under T0/T2 skill & role work).
- **763 rows** have `translate == 0` (100% keep-kinds: `user_facing`, `source_material`, `data`, `runtime_string`, `test_fixture`, `ceo_quote`, `quoted_phrase`, `title_name`, `trigger_phrase`).
- Combined `Agents-Core` `translate` in `rows.jsonl` is `104,654 + 12,028 = 116,682` chars, which matches `summary.md`'s Agents-Core total.

---

## Skip Rules Used

Every in-scope file that is not assigned to a PR batch appears in the **Skip List** at the end of this document under one of four explicit rules:

1. **Rule `S1` — Generated report, raw execution log, runtime state dump, or launchd XML plist (11 files, 2,845 `translate` chars):**
   - Machine-generated alignment output (`docs/reports/task-ee30ba95/timings-alignment-report.txt`), raw `.log` stdout captures (`docs/reports/banchi-fb-repost3/*.log`, `state/banchi/*.log`), transient SomPong LINE state dumps (`state/sompong-line/*.md`), and macOS launchd `.plist` XML files (`scripts/com.mooniex.cfo-claude-usage.plist`, `state/mac-blueprint-20260925/LaunchAgents/com.mooniex.cfo-claude-usage.plist`). Translating generated logs or XML plist keys/strings wastes review time and risks breaking plist parsing or falsifying historical stdout logs.
2. **Rule `S2` — Source transcript/metadata or user-facing Thai copy misclassified as `doc` (10 files, 1,361 `translate` chars):**
   - Scraped YouTube `.description` files under `output/research/putterlu/*.description` (7 files: external Thai source material whose `.description` suffix fell through to the markdown lexer), user-facing LINE broadcast copy in `output/mooniex-posters/gold-giveaway-recap/line-text*.md` (2 files), and the user-facing Thai copy sample `knowledge/content-knowledge/skills/rebate-copy/example.md` (1 file). Per the CEO order, external source material and user-facing Thai copy stay in Thai.
3. **Rule `S3` — Archived inter-session letter not worth review (`translate <= 15` chars) (2 files, 20 `translate` chars):**
   - Point-in-time CTO-to-console-owner handoff letters from September (`docs/ops/letters/2026-09-25-cto-6ebacd0e-to-console-owner-run-inbox-p1.md` with 14 `translate` chars; `docs/ops/letters/2026-09-26-cto-885ae930-to-console-owner-relay-idp-fix.md` with 6 `translate` chars) where almost all Thai is `ceo_quote`/`quoted_phrase` and the archive is never reopened by active workflows. (The 3 larger CTO handoff letters with 187–1,094 `translate` chars are grouped in batch `B13`.)
4. **Rule `S4` — Almost all keep-kinds / tiny dust threshold (`translate <= 15` chars) (96 files: 48 `doc` + 48 `comment`, 814 `translate` chars, 4,350 `keep` chars):**
   - Files with 1–15 translatable Thai characters where either (a) Thai is overwhelmingly `keep` kinds (`ceo_quote`, `quoted_phrase`, `user_facing`, `runtime_string`, `title_name`) and the `doc`/`comment` count is a single Thai label, name, or lexer boundary artifact, or (b) the file has only a few characters of Thai comment/prose whose token savings (< 10 tokens on demand) do not justify a PR review cycle.

---

## Batch Summary Table (Ordered by Value, Code Comments Last)

| Batch ID | Area | Status / Gate | Files | `translate` chars | `keep` chars | Total `thai` |
|---|---|---|---:|---:|---:|---:|
| **B01** | `docs/runbooks` + `playbooks` + `docs/e2e` | Ready (doc) | 4 | 4,891 | 154 | 5,045 |
| **B02** | `docs/ops` (core ops docs & audits) | Ready (doc) | 11 | 729 | 824 | 1,553 |
| **B03** | `docs/ops/briefs` | Ready (doc) | 7 | 1,640 | 227 | 1,867 |
| **B04** | `docs/design` + `docs/org` + `docs/tasks` + `claude-home` | Ready (doc) | 9 | 1,671 | 1,060 | 2,731 |
| **B05** | `.claude/skills` references + `knowledge` | Ready (doc) | 5 | 383 | 144 | 527 |
| **B06** | `docs/plans` (Part 1: Khao Niao workflow) | Ready (doc) | 1 | 7,925 | 619 | 8,544 |
| **B07** | `docs/plans` (Part 2: Khao Niao posting & Animal Series) | Ready (doc) | 2 | 7,509 | 1,072 | 8,581 |
| **B08** | `docs/plans` (Part 3: Mimi calendar & Week 1 posts) | Ready (doc) | 2 | 7,313 | 1,033 | 8,346 |
| **B09** | `docs/plans` (Part 4: Absence/Astra grading & tool-value) | Ready (doc) | 3 | 5,911 | 256 | 6,167 |
| **B10** | `docs/briefs` | Ready (doc) | 11 | 3,656 | 213 | 3,869 |
| **B11** | `docs/research` + `research` | Ready (doc) | 14 | 5,542 | 3,032 | 8,574 |
| **B12** | `prototypes` (catalogs, specs & runlogs) | Ready (doc) | 19 | 6,790 | 2,415 | 9,205 |
| **B13** | `docs/ops/letters` | Ready (doc) | 3 | 2,200 | 426 | 2,626 |
| **B14** | `docs/reports` (Part 1: ILAG promo & Absence editor notes) | Ready (doc) | 3 | 7,439 | 222 | 7,661 |
| **B15** | `docs/reports` (Part 2: Absence overnight & Flow/voice reports) | Ready (doc) | 12 | 7,804 | 1,612 | 9,416 |
| **B16** | `docs/reports` (Part 3: Banchi & task reports, 138–254 chars) | Ready (doc) | 20 | 3,824 | 2,681 | 6,505 |
| **B17** | `docs/reports` (Part 4: Banchi & teaser reports, 57–133 chars) | Ready (doc) | 18 | 1,649 | 1,991 | 3,640 |
| **B18** | `docs/reports` (Part 5: Banchi & Flow reports, 16–48 chars) | Ready (doc) | 15 | 449 | 998 | 1,447 |
| **B19** | `output/research` (Part 1: Thai trailer narration study) | Ready (doc) | 1 | 7,535 | 10,117 | 17,652 |
| **B20** | `output` (Part 2: research studies, Lunar KB & GDrive bridge) | Ready (doc) | 6 | 4,662 | 1,238 | 5,900 |
| **B21** | `tools/*.py` comments (Part 1: top tools, 59–682 chars) | **needs comment-only check** | 16 | 3,142 | 2,987 | 6,129 |
| **B22** | `tools/**` comments (Part 2: tools & subpackages, 19–92 chars) | **needs comment-only check** | 20 | 802 | 899 | 1,701 |
| **B23** | `runners/*.py` + `lib/*.py` + `windows/*` + skill scripts comments | **needs comment-only check** | 12 | 728 | 16,873 | 17,601 |
| **B24** | `scripts/**` comments (launchers, hooks & utilities) | **needs comment-only check** | 18 | 1,234 | 3,259 | 4,493 |
| **B25** | `docs/prompts/**` + `docs/reports/khaoniao-family-style/*.py` comments | **needs comment-only check** | 13 | 1,109 | 850 | 1,959 |
| **B26** | `docs/scripts/*.py` comments (episode `.data.py` & common modules) | **needs comment-only check** | 20 | 2,132 | 10,702 | 12,834 |
| **B27** | `prototypes/**` + `output/reels/**` + `docs/scripts/taachang-ACT3.data.py` comments | **needs comment-only check** | 9 | 945 | 3,341 | 4,286 |
| **Total** | **All 27 PR Batches** | **20 doc + 7 comment** | **274** | **99,614** | **69,245** | **168,859** |

---

## Detailed Batch Plans (`B01`–`B18`)

### Batch `B01` — Operational Runbooks, Playbooks & E2E Smoke Docs
- **ID:** `B01`
- **Area:** `docs/runbooks` + `playbooks` + `docs/e2e`
- **File count:** 4
- **Translate characters:** 4,891
- **Keep characters:** 154
- **Risk note for reviewer:** Mixed files with **CEO quotes** (`winbox-checklist.md`: 11 chars) and **quoted UI/CLI phrases** (`winbox-recovery.md`: 143 chars). Verify that Windows/Winbox UI labels in quotes and exact CEO wording remain in Thai while procedural steps move to English. Also note `playbooks/cfo-claude-usage-feed.md` is a `T2_trigger` playbook.
- **Files:**
  1. `docs/runbooks/winbox-recovery.md` — `translate`: 3,351 | `keep`: 143 | `kinds`: `{"doc": 3351, "quoted_phrase": 143}`
  2. `docs/runbooks/winbox-checklist.md` — `translate`: 1,468 | `keep`: 11 | `kinds`: `{"doc": 1468, "ceo_quote": 11}`
  3. `docs/e2e/winbox-smoke-2026-09-18.md` — `translate`: 37 | `keep`: 0 | `kinds`: `{"doc": 37}`
  4. `playbooks/cfo-claude-usage-feed.md` — `translate`: 35 | `keep`: 0 | `kinds`: `{"doc": 35}`

### Batch `B02` — Core Operations Docs & Audits (`docs/ops`)
- **ID:** `B02`
- **Area:** `docs/ops` (top-level ops docs & `bl-split-ab-2026-09-25`)
- **File count:** 11
- **Translate characters:** 729
- **Keep characters:** 824
- **Risk note for reviewer:** High concentration of **CEO quotes** (394 chars across `PLAN.md`, `BRIEF-arm1.md`, `BRIEF-seg.md`, `skill-film-inventory-2026-09-25.md`, `TOOLING.md`) and **quoted phrases / titles** (430 chars, especially in `google-ultra-benefits-audit.md` and `google-flow-ultra-audit.md`). Keep all quoted CEO instructions, film titles (`«…»`), and UI strings intact.
- **Files:**
  1. `docs/ops/caveman-plugin-2026-09-25.md` — `translate`: 182 | `keep`: 0 | `kinds`: `{"doc": 182}`
  2. `docs/ops/skill-film-inventory-2026-09-25.md` — `translate`: 126 | `keep`: 82 | `kinds`: `{"doc": 126, "ceo_quote": 46, "quoted_phrase": 36}`
  3. `docs/ops/image-budget-hook-2026-09-25.md` — `translate`: 100 | `keep`: 0 | `kinds`: `{"doc": 100}`
  4. `docs/ops/cache-cold-guard-2026-09-25.md` — `translate`: 99 | `keep`: 0 | `kinds`: `{"doc": 99}`
  5. `docs/ops/google-ultra-benefits-audit.md` — `translate`: 83 | `keep`: 243 | `kinds`: `{"quoted_phrase": 243, "doc": 83}`
  6. `docs/ops/google-flow-ultra-audit.md` — `translate`: 40 | `keep`: 84 | `kinds`: `{"quoted_phrase": 74, "doc": 40, "title_name": 10}`
  7. `docs/ops/bl-split-ab-2026-09-25/TOOLING.md` — `translate`: 25 | `keep`: 47 | `kinds`: `{"ceo_quote": 30, "doc": 25, "quoted_phrase": 17}`
  8. `docs/ops/bl-split-ab-2026-09-25/BRIEF-arm1.md` — `translate`: 22 | `keep`: 69 | `kinds`: `{"ceo_quote": 52, "doc": 22, "quoted_phrase": 17}`
  9. `docs/ops/bl-split-ab-2026-09-25/BRIEF-seg.md` — `translate`: 20 | `keep`: 76 | `kinds`: `{"ceo_quote": 52, "quoted_phrase": 24, "doc": 20}`
  10. `docs/ops/bl-split-ab-2026-09-25/PLAN.md` — `translate`: 16 | `keep`: 218 | `kinds`: `{"ceo_quote": 214, "doc": 16, "quoted_phrase": 4}`
  11. `docs/ops/flow-operator-design.md` — `translate`: 16 | `keep`: 5 | `kinds`: `{"doc": 16, "title_name": 5}`

### Batch `B03` — Operations Briefs (`docs/ops/briefs`)
- **ID:** `B03`
- **Area:** `docs/ops/briefs`
- **File count:** 7
- **Translate characters:** 1,640
- **Keep characters:** 227
- **Risk note for reviewer:** Contains **CEO quotes** (187 chars across `iq-web-localhost.md`, `taachang-characters.md`, `ep4-fb-post.md`) and **character/series titles** (`title_name`: 40 chars). Also note that `ilag-trailer-round5a.md`, `round6.md`, and `round9.md` contain character/scene descriptions — reviewer must ensure any spoken Thai dialogue or character names needed for prompts are preserved while internal brief instructions move to English.
- **Files:**
  1. `docs/ops/briefs/ilag-trailer-round5a.md` — `translate`: 496 | `keep`: 0 | `kinds`: `{"doc": 496}`
  2. `docs/ops/briefs/ilag-trailer-round6.md` — `translate`: 437 | `keep`: 0 | `kinds`: `{"doc": 437}`
  3. `docs/ops/briefs/ilag-trailer-round9.md` — `translate`: 309 | `keep`: 0 | `kinds`: `{"doc": 309}`
  4. `docs/ops/briefs/iq-web-localhost.md` — `translate`: 202 | `keep`: 79 | `kinds`: `{"doc": 202, "ceo_quote": 79}`
  5. `docs/ops/briefs/h3-studio-add-ilag-entities.md` — `translate`: 129 | `keep`: 0 | `kinds`: `{"doc": 129}`
  6. `docs/ops/briefs/taachang-characters.md` — `translate`: 51 | `keep`: 83 | `kinds`: `{"ceo_quote": 69, "doc": 51, "title_name": 14}`
  7. `docs/ops/briefs/ep4-fb-post.md` — `translate`: 16 | `keep`: 65 | `kinds`: `{"ceo_quote": 39, "title_name": 26, "doc": 16}`

### Batch `B04` — Architecture, Org & Tooling Design (`docs/design`, `docs/org`, `docs/tasks`, `claude-home`)
- **ID:** `B04`
- **Area:** `docs/design` + `docs/org` + `docs/tasks` + `claude-home/tools`
- **File count:** 9
- **Translate characters:** 1,671
- **Keep characters:** 1,060
- **Risk note for reviewer:** Heavy **CEO quotes** (890 chars across `secretary-profiles.md`, `sompong-coo-prompt.md`, `run-inbox/QUESTIONS.md`, `run-inbox/DESIGN.md`, `drive-archive-gate.md`) and **user-facing/persona examples** in `sompong-coo-prompt.md` and `secretary-profiles.md`. Reviewer must ensure SomPong/secretary Thai persona sample lines and CEO quotes stay in Thai while architectural prose moves to English.
- **Files:**
  1. `docs/design/sompong-coo-prompt.md` — `translate`: 756 | `keep`: 111 | `kinds`: `{"doc": 756, "ceo_quote": 111}`
  2. `docs/design/secretary-profiles.md` — `translate`: 303 | `keep`: 622 | `kinds`: `{"ceo_quote": 619, "doc": 303, "quoted_phrase": 3}`
  3. `docs/design/run-inbox/QUESTIONS.md` — `translate`: 186 | `keep`: 125 | `kinds`: `{"doc": 186, "ceo_quote": 110, "quoted_phrase": 15}`
  4. `docs/design/winbox-zero-human.md` — `translate`: 151 | `keep`: 0 | `kinds`: `{"doc": 151}`
  5. `docs/design/org-mesh.md` — `translate`: 142 | `keep`: 0 | `kinds`: `{"doc": 142}`
  6. `docs/org/SKILL-INDEX.md` — `translate`: 70 | `keep`: 119 | `kinds`: `{"title_name": 104, "doc": 70, "quoted_phrase": 15}`
  7. `claude-home/tools/drive-archive-gate.md` — `translate`: 22 | `keep`: 19 | `kinds`: `{"doc": 22, "ceo_quote": 19}`
  8. `docs/tasks/HARVEST-20260911.md` — `translate`: 21 | `keep`: 0 | `kinds`: `{"doc": 21}`
  9. `docs/design/run-inbox/DESIGN.md` — `translate`: 20 | `keep`: 64 | `kinds`: `{"quoted_phrase": 33, "ceo_quote": 31, "doc": 20}`

### Batch `B05` — Skill References & Knowledge Docs (`.claude/skills`, `knowledge`)
- **ID:** `B05`
- **Area:** `.claude/skills` reference docs + `knowledge` (`brand-knowledge`, `content-knowledge`, `people-knowledge`)
- **File count:** 5
- **Translate characters:** 383
- **Keep characters:** 144
- **Risk note for reviewer:** Mixed files containing **CEO quotes** (`mooniex/BRAND.md`: 27 chars), **quoted phrases / Thai content anti-patterns** (`anti-content-slop.md`: 84 chars; `mooniex/BRAND.md`: 31 chars), and **proper names / contact details** (`ceo-contacts.md`: 22 chars). Keep Thai proper names, brand slogans, and quoted Thai slop examples in Thai.
- **Files:**
  1. `.claude/skills/CMO_Procedure_BlackLiquidity_Cut/edl/SCHEMA.md` — `translate`: 217 | `keep`: 2 | `kinds`: `{"doc": 217, "quoted_phrase": 2}`
  2. `knowledge/brand-knowledge/brands/axi/BRAND.md` — `translate`: 92 | `keep`: 0 | `kinds`: `{"doc": 92}`
  3. `knowledge/content-knowledge/craft/anti-content-slop.md` — `translate`: 32 | `keep`: 84 | `kinds`: `{"quoted_phrase": 84, "doc": 32}`
  4. `knowledge/people-knowledge/ceo-contacts.md` — `translate`: 22 | `keep`: 0 | `kinds`: `{"doc": 22}`
  5. `knowledge/brand-knowledge/brands/mooniex/BRAND.md` — `translate`: 20 | `keep`: 58 | `kinds`: `{"quoted_phrase": 31, "ceo_quote": 27, "doc": 20}`

### Batch `B06` — Plans Part 1: Khao Niao Weekly Workflow (`docs/plans`)
- **ID:** `B06`
- **Area:** `docs/plans` (Part 1)
- **File count:** 1
- **Translate characters:** 7,925
- **Keep characters:** 619
- **Risk note for reviewer:** Single large mixed file near the 8,000-char ceiling (7,925 `translate` chars) with **CEO quotes** (218 chars), **episode/page titles** (`title_name`: 361 chars), and **quoted phrases** (40 chars). Reviewer must verify that unquoted Thai episode titles, character names, or user-facing caption drafts embedded in tables stay in Thai while workflow prose moves to English.
- **Files:**
  1. `docs/plans/khaoniao-week-workflow-2026-10-01.md` — `translate`: 7,925 | `keep`: 619 | `kinds`: `{"doc": 7925, "title_name": 361, "ceo_quote": 218, "quoted_phrase": 40}`

### Batch `B07` — Plans Part 2: Khao Niao Posting & Animal Series Channel Plans (`docs/plans`)
- **ID:** `B07`
- **Area:** `docs/plans` (Part 2)
- **File count:** 2
- **Translate characters:** 7,509
- **Keep characters:** 1,072
- **Risk note for reviewer:** Mixed files with **CEO quotes** (396 chars), **series/episode titles** (`title_name`: 611 chars), and **user-facing post/hook concepts** inside `khaoniao-posting-plan-2026-09-30.md`. Keep Thai post titles, hook lines, and CEO quotes in Thai; translate only internal scheduling/strategy prose.
- **Files:**
  1. `docs/plans/khaoniao-posting-plan-2026-09-30.md` — `translate`: 7,094 | `keep`: 362 | `kinds`: `{"doc": 7094, "ceo_quote": 256, "title_name": 92, "quoted_phrase": 14}`
  2. `docs/plans/animal-series-channel-plan-2026-09-28.md` — `translate`: 415 | `keep`: 710 | `kinds`: `{"title_name": 519, "doc": 415, "ceo_quote": 140, "quoted_phrase": 51}`

### Batch `B08` — Plans Part 3: Mimi Weekly Calendar & Week 1 Posts (`docs/plans`)
- **ID:** `B08`
- **Area:** `docs/plans` (Part 3)
- **File count:** 2
- **Translate characters:** 7,313
- **Keep characters:** 1,033
- **Risk note for reviewer:** High **user-facing text** risk: both files mix internal calendar/posting strategy with actual Thai post copy, captions, and episode titles (`title_name`: 1,033 chars). Reviewer must ensure all Thai Facebook/Reels caption text and post titles remain in Thai and only internal planning notes move to English.
- **Files:**
  1. `docs/plans/mimi-weekly-calendar.md` — `translate`: 5,260 | `keep`: 870 | `kinds`: `{"doc": 5260, "title_name": 870}`
  2. `docs/plans/mimi-week1-posts.md` — `translate`: 2,053 | `keep`: 163 | `kinds`: `{"doc": 2053, "title_name": 163}`

### Batch `B09` — Plans Part 4: Grading Briefs & Tool-Value Enforcement (`docs/plans`)
- **ID:** `B09`
- **Area:** `docs/plans` (Part 4)
- **File count:** 3
- **Translate characters:** 5,911
- **Keep characters:** 256
- **Risk note for reviewer:** Contains **CEO quotes** (`tool-value-weekly-and-enforcement-2026-10-13.md`: 35 chars) and **quoted phrases** (221 chars across all 3 files). Verify that color-grading shot references and CEO directive quotes stay intact.
- **Files:**
  1. `docs/plans/absence-grading-plan-20260911.md` — `translate`: 2,350 | `keep`: 18 | `kinds`: `{"doc": 2350, "quoted_phrase": 18}`
  2. `docs/plans/astra-grading-brief.md` — `translate`: 2,244 | `keep`: 83 | `kinds`: `{"doc": 2244, "quoted_phrase": 83}`
  3. `docs/plans/tool-value-weekly-and-enforcement-2026-10-13.md` — `translate`: 1,317 | `keep`: 155 | `kinds`: `{"doc": 1317, "quoted_phrase": 120, "ceo_quote": 35}`

### Batch `B10` — Project & Production Briefs (`docs/briefs`)
- **ID:** `B10`
- **Area:** `docs/briefs`
- **File count:** 11
- **Translate characters:** 3,656
- **Keep characters:** 213
- **Risk note for reviewer:** Mixed files with **CEO quotes** (18 chars in `account-split-plan.md` and `migrate-mooniex-to-official-account.md`), **quoted phrases** (147 chars), and **film/page titles** (`title_name`: 48 chars). Keep Thai Facebook page names, character voice sample lines, and CEO quotes in Thai.
- **Files:**
  1. `docs/briefs/account-split-plan.md` — `translate`: 1,488 | `keep`: 31 | `kinds`: `{"doc": 1488, "quoted_phrase": 25, "ceo_quote": 6}`
  2. `docs/briefs/migrate-mooniex-to-official-account.md` — `translate`: 1,306 | `keep`: 54 | `kinds`: `{"doc": 1306, "quoted_phrase": 42, "ceo_quote": 12}`
  3. `docs/briefs/banchi-policy-bisect.md` — `translate`: 192 | `keep`: 80 | `kinds`: `{"doc": 192, "quoted_phrase": 80}`
  4. `docs/briefs/fb-page-ilag-drama.md` — `translate`: 190 | `keep`: 0 | `kinds`: `{"doc": 190}`
  5. `docs/briefs/banchi-voice-save-probe.md` — `translate`: 178 | `keep`: 5 | `kinds`: `{"doc": 178, "title_name": 5}`
  6. `docs/briefs/banchi-custom-voices-v2.md` — `translate`: 83 | `keep`: 0 | `kinds`: `{"doc": 83}`
  7. `docs/briefs/banchi-assets-build.md` — `translate`: 61 | `keep`: 5 | `kinds`: `{"doc": 61, "title_name": 5}`
  8. `docs/briefs/banchi-voices-and-plates.md` — `translate`: 59 | `keep`: 5 | `kinds`: `{"doc": 59, "title_name": 5}`
  9. `docs/briefs/banchi-act1-shoot-first12.md` — `translate`: 48 | `keep`: 5 | `kinds`: `{"doc": 48, "title_name": 5}`
  10. `docs/briefs/CODEX-winbox-shoot.md` — `translate`: 28 | `keep`: 23 | `kinds`: `{"doc": 28, "title_name": 23}`
  11. `docs/briefs/banchi-custom-voices.md` — `translate`: 23 | `keep`: 5 | `kinds`: `{"doc": 23, "title_name": 5}`

### Batch `B11` — Internal Research & Audits (`docs/research` + `research`)
- **ID:** `B11`
- **Area:** `docs/research` + `research`
- **File count:** 14
- **Translate characters:** 5,542
- **Keep characters:** 3,032
- **Risk note for reviewer:** High **user-facing & external UI quote** density (`keep`: 3,032 chars, including 487 chars of `ceo_quote` and 2,488 chars of `quoted_phrase`). `fastwork-listings-draft.md` and `fastwork-seller-onboarding*.md` contain Thai marketplace UI labels and seller listing copy that must stay in Thai if customer-facing, while internal analysis/pricing notes move to English.
- **Files:**
  1. `research/fastwork-prices.md` — `translate`: 2,076 | `keep`: 432 | `kinds`: `{"doc": 2076, "quoted_phrase": 432}`
  2. `research/fastwork-listings-draft.md` — `translate`: 1,322 | `keep`: 40 | `kinds`: `{"doc": 1322, "ceo_quote": 29, "quoted_phrase": 11}`
  3. `research/fastwork-seller-onboarding-part3.md` — `translate`: 666 | `keep`: 277 | `kinds`: `{"doc": 666, "quoted_phrase": 185, "ceo_quote": 92}`
  4. `research/ngoen-tee-por-EP1-structure-audit.md` — `translate`: 434 | `keep`: 160 | `kinds`: `{"doc": 434, "quoted_phrase": 139, "title_name": 18, "ceo_quote": 3}`
  5. `research/catseries-teardown-2026-09-28.md` — `translate`: 261 | `keep`: 345 | `kinds`: `{"quoted_phrase": 276, "doc": 261, "ceo_quote": 48, "title_name": 21}`
  6. `research/fastwork-seller-onboarding.md` — `translate`: 177 | `keep`: 392 | `kinds`: `{"quoted_phrase": 200, "ceo_quote": 192, "doc": 177}`
  7. `research/fb-thai-ai-drama-pages.md` — `translate`: 157 | `keep`: 195 | `kinds`: `{"quoted_phrase": 186, "doc": 157, "ceo_quote": 9}`
  8. `research/fastwork-seller-onboarding-part2.md` — `translate`: 137 | `keep`: 457 | `kinds`: `{"quoted_phrase": 400, "doc": 137, "ceo_quote": 57}`
  9. `research/fastwork-signup-requirements.md` — `translate`: 125 | `keep`: 199 | `kinds`: `{"quoted_phrase": 199, "doc": 125}`
  10. `docs/research/2026-10-01-bl-tiktokshop-basket-first-checks.md` — `translate`: 59 | `keep`: 183 | `kinds`: `{"quoted_phrase": 165, "doc": 59, "ceo_quote": 18}`
  11. `docs/research/2026-09-19-flow-policy-refusals.md` — `translate`: 42 | `keep`: 79 | `kinds`: `{"quoted_phrase": 79, "doc": 42}`
  12. `research/flow-account-audit-20260917.md` — `translate`: 38 | `keep`: 180 | `kinds`: `{"quoted_phrase": 162, "doc": 38, "title_name": 18}`
  13. `research/fb-page-ilag-created.md` — `translate`: 30 | `keep`: 15 | `kinds`: `{"doc": 30, "quoted_phrase": 15}`
  14. `docs/research/2026-09-26-youtube-shorts-income-model.md` — `translate`: 18 | `keep`: 78 | `kinds`: `{"ceo_quote": 41, "quoted_phrase": 37, "doc": 18}`

### Batch `B12` — Prototype Specs, Catalogs & Runlogs (`prototypes`)
- **ID:** `B12`
- **Area:** `prototypes`
- **File count:** 19
- **Translate characters:** 6,790
- **Keep characters:** 2,415
- **Risk note for reviewer:** Mixed files with **CEO quotes** (965 chars across `bl59-script/RUNLOG.md`, `bl58-script/RUNLOG.md`, `bl60-script/RUNLOG.md`, `mypasakon-voice/analysis.md`, `bl61-script/RUNLOG.md`), **user-facing Headlines/Topics** (`bl58..61-script/HEADLINE.md` and `TOPICS.md`), and **voice/speech cadence examples** in `mypasakon-voice/analysis.md`. Reviewer must keep Thai headline options, spoken script quotes, and CEO feedback in Thai while translating analytical/catalog descriptions (`bl-broll-catalog/CATALOG.md`).
- **Files:**
  1. `prototypes/bl-broll-catalog/CATALOG.md` — `translate`: 3,531 | `keep`: 0 | `kinds`: `{"doc": 3531}`
  2. `prototypes/mypasakon-voice/analysis.md` — `translate`: 1,185 | `keep`: 209 | `kinds`: `{"doc": 1185, "quoted_phrase": 155, "ceo_quote": 54}`
  3. `prototypes/bl59-script/RUNLOG.md` — `translate`: 448 | `keep`: 771 | `kinds`: `{"ceo_quote": 667, "doc": 448, "quoted_phrase": 104}`
  4. `prototypes/bl-model-bakeoff/voicelib/INDEX.md` — `translate`: 251 | `keep`: 0 | `kinds`: `{"doc": 251}`
  5. `prototypes/mypasakon-voice/WIKI-DRAFT-research-page.md` — `translate`: 241 | `keep`: 102 | `kinds`: `{"doc": 241, "quoted_phrase": 84, "ceo_quote": 18}`
  6. `prototypes/bl60-script/RUNLOG.md` — `translate`: 156 | `keep`: 382 | `kinds`: `{"quoted_phrase": 325, "doc": 156, "ceo_quote": 57}`
  7. `prototypes/bl58-script/RUNLOG.md` — `translate`: 149 | `keep`: 426 | `kinds`: `{"quoted_phrase": 326, "doc": 149, "ceo_quote": 100}`
  8. `prototypes/mypasakon-voice/RECIPE.md` — `translate`: 128 | `keep`: 20 | `kinds`: `{"doc": 128, "ceo_quote": 20}`
  9. `prototypes/bl59-script/HEADLINE.md` — `translate`: 118 | `keep`: 46 | `kinds`: `{"doc": 118, "quoted_phrase": 46}`
  10. `prototypes/bl61-script/RUNLOG.md` — `translate`: 118 | `keep`: 123 | `kinds`: `{"doc": 118, "quoted_phrase": 82, "ceo_quote": 41}`
  11. `prototypes/bl60-script/HEADLINE.md` — `translate`: 117 | `keep`: 36 | `kinds`: `{"doc": 117, "quoted_phrase": 36}`
  12. `prototypes/bl61-script/HEADLINE.md` — `translate`: 83 | `keep`: 39 | `kinds`: `{"doc": 83, "quoted_phrase": 39}`
  13. `prototypes/bl58-script/HEADLINE.md` — `translate`: 70 | `keep`: 35 | `kinds`: `{"doc": 70, "quoted_phrase": 35}`
  14. `prototypes/bl59-script/TOPICS.md` — `translate`: 58 | `keep`: 76 | `kinds`: `{"quoted_phrase": 76, "doc": 58}`
  15. `prototypes/bl-reply-bot/RESEARCH.md` — `translate`: 44 | `keep`: 138 | `kinds`: `{"quoted_phrase": 130, "doc": 44, "ceo_quote": 8}`
  16. `prototypes/bl-jev-scoreboard/example/scoreboard/SCOREBOARD.md` — `translate`: 40 | `keep`: 0 | `kinds`: `{"doc": 40}`
  17. `prototypes/lungtun-style-reel/DESIGN.md` — `translate`: 21 | `keep`: 5 | `kinds`: `{"doc": 21, "quoted_phrase": 5}`
  18. `prototypes/bl-jev-scoreboard/SCOREBOARD.md` — `translate`: 16 | `keep`: 0 | `kinds`: `{"doc": 16}`
  19. `prototypes/bl-tiktok-ops/README.md` — `translate`: 16 | `keep`: 7 | `kinds`: `{"doc": 16, "ceo_quote": 7}`

### Batch `B13` — Archived CTO Handoff Letters (`docs/ops/letters`)
- **ID:** `B13`
- **Area:** `docs/ops/letters`
- **File count:** 3
- **Translate characters:** 2,200
- **Keep characters:** 426
- **Risk note for reviewer:** High **CEO quote** risk (`ceo_quote`: 386 chars, plus unquoted paraphrased CEO notes in `ceo-notes-round2.md` and `ceo-notes-p1-round1.md`). Under Iron Rule 3, direct CEO words are evidence and must stay in the original Thai; translate only the CTO-to-CTO commentary and action summaries.
- **Files:**
  1. `docs/ops/letters/2026-09-25-cto-6bfdc084-to-cto-e1e3d3ef-ceo-notes-round2.md` — `translate`: 1,094 | `keep`: 400 | `kinds`: `{"doc": 1094, "ceo_quote": 373, "quoted_phrase": 27}`
  2. `docs/ops/letters/2026-09-25-cto-6bfdc084-to-cto-e1e3d3ef-ceo-notes-p1-round1.md` — `translate`: 919 | `keep`: 26 | `kinds`: `{"doc": 919, "ceo_quote": 13, "quoted_phrase": 13}`
  3. `docs/ops/letters/2026-09-25-cto-e1e3d3ef-to-cto-6bfdc084-offline-queue.md` — `translate`: 187 | `keep`: 0 | `kinds`: `{"doc": 187}`

### Batch `B14` — Reports Part 1: ILAG Promotion & Absence Editor Instructions (`docs/reports`)
- **ID:** `B14`
- **Area:** `docs/reports` (Part 1)
- **File count:** 3
- **Translate characters:** 7,439
- **Keep characters:** 222
- **Risk note for reviewer:** Mixed files with **quoted phrases / user-facing copy** (`promotion-plan-ilag.md`: 200 chars; `absence-editor-instructions-20260911.md`: 22 chars). In `promotion-plan-ilag.md`, keep any sample Thai post copy or page titles in Thai; in the Absence editor instruction files, keep any Thai subtitle/title card strings in Thai while translating the editing instructions.
- **Files:**
  1. `docs/reports/promotion-plan-ilag.md` — `translate`: 4,451 | `keep`: 200 | `kinds`: `{"doc": 4451, "quoted_phrase": 200}`
  2. `docs/reports/absence-editor-instructions-20260911.md` — `translate`: 1,759 | `keep`: 22 | `kinds`: `{"doc": 1759, "quoted_phrase": 22}`
  3. `docs/reports/absence-editor-instructions-20260910.md` — `translate`: 1,229 | `keep`: 0 | `kinds`: `{"doc": 1229}`

### Batch `B15` — Reports Part 2: Absence Overnight & Flow/Voice Reports (`docs/reports`)
- **ID:** `B15`
- **Area:** `docs/reports` (Part 2)
- **File count:** 12
- **Translate characters:** 7,804
- **Keep characters:** 1,612
- **Risk note for reviewer:** Contains **CEO quotes** (283 chars across `absence-overnight-20260911.md`, `scene1-v2-shoot-20260918/REPORT.md`, `film-transcript/FINDINGS.md`), **film titles** (`title_name`: 405 chars), and **quoted Thai voice/TTS test lines** (`quoted_phrase`: 924 chars). Preserve all Thai TTS test phrases and CEO quotes verbatim.
- **Files:**
  1. `docs/reports/absence-overnight-20260911.md` — `translate`: 3,656 | `keep`: 205 | `kinds`: `{"doc": 3656, "ceo_quote": 167, "quoted_phrase": 38}`
  2. `docs/reports/FINDING-stale-report-md.md` — `translate`: 577 | `keep`: 0 | `kinds`: `{"doc": 577}`
  3. `docs/reports/flow-voices-recon-20260908.md` — `translate`: 526 | `keep`: 12 | `kinds`: `{"doc": 526, "quoted_phrase": 12}`
  4. `docs/reports/scene1-v2-shoot-20260918/REPORT.md` — `translate`: 411 | `keep`: 201 | `kinds`: `{"doc": 411, "quoted_phrase": 112, "ceo_quote": 89}`
  5. `docs/reports/fb-story-attach/REPORT.md` — `translate`: 403 | `keep`: 70 | `kinds`: `{"doc": 403, "quoted_phrase": 55, "title_name": 15}`
  6. `docs/reports/banchi-voices-v3-20260918/REPORT.md` — `translate`: 398 | `keep`: 0 | `kinds`: `{"doc": 398}`
  7. `docs/reports/flow-frames-to-video-20260907.md` — `translate`: 342 | `keep`: 340 | `kinds`: `{"doc": 342, "quoted_phrase": 340}`
  8. `docs/reports/flow-voices-installed-20260908.md` — `translate`: 329 | `keep`: 157 | `kinds`: `{"doc": 329, "quoted_phrase": 157}`
  9. `docs/reports/task-c32c40e8/REPORT.md` — `translate`: 318 | `keep`: 0 | `kinds`: `{"doc": 318}`
  10. `docs/reports/flow-thaitext-20260918/REPORT.md` — `translate`: 306 | `keep`: 15 | `kinds`: `{"doc": 306, "quoted_phrase": 15}`
  11. `docs/reports/omni-voiced-scene-20260908.md` — `translate`: 277 | `keep`: 26 | `kinds`: `{"doc": 277, "quoted_phrase": 26}`
  12. `docs/reports/film-transcript/FINDINGS.md` — `translate`: 261 | `keep`: 586 | `kinds`: `{"title_name": 390, "doc": 261, "quoted_phrase": 169, "ceo_quote": 27}`

### Batch `B16` — Reports Part 3: Banchi & Task Reports, 138–254 chars (`docs/reports`)
- **ID:** `B16`
- **Area:** `docs/reports` (Part 3)
- **File count:** 20
- **Translate characters:** 3,824
- **Keep characters:** 2,681
- **Risk note for reviewer:** Mixed files with **CEO quotes** (36 chars in `banchi-fb-repost3/REPORT.md` and `fb-groups-share-banchi/REPORT.md`), **film/group titles** (`title_name`: 765 chars), and **quoted Thai dialogue / Facebook group names** (`quoted_phrase`: 1,880 chars). Keep all Thai dialogue lines, Facebook group names, and CEO quotes intact.
- **Files:**
  1. `docs/reports/banchi-voices-20260918/REPORT.md` — `translate`: 254 | `keep`: 5 | `kinds`: `{"doc": 254, "title_name": 5}`
  2. `docs/reports/task-9c6daaf7/REPORT.md` — `translate`: 239 | `keep`: 127 | `kinds`: `{"doc": 239, "quoted_phrase": 127}`
  3. `docs/reports/task-3ae66e7a/REPORT.md` — `translate`: 237 | `keep`: 696 | `kinds`: `{"title_name": 673, "doc": 237, "quoted_phrase": 23}`
  4. `docs/reports/fb-groups-ilag/REPORT.md` — `translate`: 227 | `keep`: 49 | `kinds`: `{"doc": 227, "quoted_phrase": 34, "title_name": 15}`
  5. `docs/reports/banchi-fb-repost3/REPORT.md` — `translate`: 218 | `keep`: 340 | `kinds`: `{"quoted_phrase": 311, "doc": 218, "title_name": 15, "ceo_quote": 14}`
  6. `docs/reports/banchi-policy-bisect-20260919/REPORT.md` — `translate`: 216 | `keep`: 32 | `kinds`: `{"doc": 216, "quoted_phrase": 32}`
  7. `docs/reports/taachang-characters/REPORT.md` — `translate`: 211 | `keep`: 183 | `kinds`: `{"doc": 211, "quoted_phrase": 169, "title_name": 14}`
  8. `docs/reports/task-2db3174c/REPORT.md` — `translate`: 209 | `keep`: 23 | `kinds`: `{"doc": 209, "title_name": 23}`
  9. `docs/reports/fb-groups-share-banchi/REPORT.md` — `translate`: 202 | `keep`: 289 | `kinds`: `{"quoted_phrase": 267, "doc": 202, "ceo_quote": 22}`
  10. `docs/reports/banchi-batch2-20260919/REPORT.md` — `translate`: 192 | `keep`: 0 | `kinds`: `{"doc": 192}`
  11. `docs/reports/banchi-batch3-20260919/REPORT.md` — `translate`: 192 | `keep`: 49 | `kinds`: `{"doc": 192, "quoted_phrase": 44, "title_name": 5}`
  12. `docs/reports/teaser-shoot-winbox-20260907.md` — `translate`: 191 | `keep`: 165 | `kinds`: `{"doc": 191, "quoted_phrase": 165}`
  13. `docs/reports/banchi-voice-probe-20260918/REPORT.md` — `translate`: 185 | `keep`: 5 | `kinds`: `{"doc": 185, "title_name": 5}`
  14. `docs/reports/banchi-batch4-20260919/REPORT.md` — `translate`: 162 | `keep`: 189 | `kinds`: `{"quoted_phrase": 189, "doc": 162}`
  15. `docs/reports/banchi-assetaudit-20260918/REPORT.md` — `translate`: 156 | `keep`: 0 | `kinds`: `{"doc": 156}`
  16. `docs/reports/banchi-batch5-20260919/REPORT.md` — `translate`: 156 | `keep`: 115 | `kinds`: `{"doc": 156, "quoted_phrase": 115}`
  17. `docs/reports/task-811dfc2f/REPORT.md` — `translate`: 155 | `keep`: 15 | `kinds`: `{"doc": 155, "title_name": 15}`
  18. `docs/reports/flow-runner-build/REPORT-iter2.md` — `translate`: 145 | `keep`: 141 | `kinds`: `{"doc": 145, "quoted_phrase": 136, "title_name": 5}`
  19. `docs/reports/banchi-shootB-20260919/REPORT.md` — `translate`: 139 | `keep`: 50 | `kinds`: `{"doc": 139, "quoted_phrase": 50}`
  20. `docs/reports/task-cfdc75a8/WORKLOG.md` — `translate`: 138 | `keep`: 208 | `kinds`: `{"quoted_phrase": 208, "doc": 138}`

### Batch `B17` — Reports Part 4: Banchi & Teaser Reports, 57–133 chars (`docs/reports`)
- **ID:** `B17`
- **Area:** `docs/reports` (Part 4)
- **File count:** 18
- **Translate characters:** 1,649
- **Keep characters:** 1,991
- **Risk note for reviewer:** High **CEO quote** count (792 chars across `banchi-fb-unavailable/REPORT.md`, `banchi-fb-post/REPORT.md`, `banchi-fb-repost/REPORT.md`, `banchi-fb-repost2/REPORT.md`) and **quoted dialogue/captions** (`quoted_phrase`: 1,141 chars). Do not translate quoted Facebook captions, subtitle excerpts, or CEO directives.
- **Files:**
  1. `docs/reports/banchi-fb-unavailable/REPORT.md` — `translate`: 133 | `keep`: 813 | `kinds`: `{"ceo_quote": 585, "quoted_phrase": 228, "doc": 133}`
  2. `docs/reports/banchi-fb-repost2/REPORT.md` — `translate`: 131 | `keep`: 52 | `kinds`: `{"doc": 131, "ceo_quote": 37, "quoted_phrase": 15}`
  3. `docs/reports/banchi-covers-chatgpt/REPORT.md` — `translate`: 130 | `keep`: 10 | `kinds`: `{"doc": 130, "quoted_phrase": 10}`
  4. `docs/reports/teaser-shoot-winbox-20260907-run2.md` — `translate`: 111 | `keep`: 29 | `kinds`: `{"doc": 111, "quoted_phrase": 29}`
  5. `docs/reports/flow-parallel-20260918/REPORT.md` — `translate`: 110 | `keep`: 46 | `kinds`: `{"doc": 110, "quoted_phrase": 46}`
  6. `docs/reports/teaser-shoot-20260907.md` — `translate`: 109 | `keep`: 0 | `kinds`: `{"doc": 109}`
  7. `docs/reports/task-a40d2d8e/REPORT.md` — `translate`: 99 | `keep`: 0 | `kinds`: `{"doc": 99}`
  8. `docs/reports/banchi-voices-v2-20260918/REPORT.md` — `translate`: 98 | `keep`: 12 | `kinds`: `{"doc": 98, "quoted_phrase": 12}`
  9. `docs/reports/banchi-voices-plates-20260918/REPORT.md` — `translate`: 86 | `keep`: 5 | `kinds`: `{"doc": 86, "title_name": 5}`
  10. `docs/reports/banchi-act1-B2-20260918/REPORT.md` — `translate`: 84 | `keep`: 17 | `kinds`: `{"doc": 84, "quoted_phrase": 12, "title_name": 5}`
  11. `docs/reports/task-8f940c57/REPORT.md` — `translate`: 80 | `keep`: 22 | `kinds`: `{"doc": 80, "quoted_phrase": 22}`
  12. `docs/reports/banchi-shootA-20260919/REPORT.md` — `translate`: 74 | `keep`: 122 | `kinds`: `{"quoted_phrase": 122, "doc": 74}`
  13. `docs/reports/banchi-fb-repost/REPORT.md` — `translate`: 71 | `keep`: 156 | `kinds`: `{"quoted_phrase": 117, "doc": 71, "ceo_quote": 39}`
  14. `docs/reports/banchi-plates-20260918/REPORT.md` — `translate`: 71 | `keep`: 5 | `kinds`: `{"doc": 71, "title_name": 5}`
  15. `docs/reports/scene1-v2-shot3-retake-20260918/REPORT.md` — `translate`: 70 | `keep`: 261 | `kinds`: `{"quoted_phrase": 261, "doc": 70}`
  16. `docs/reports/banchi-fb-post/REPORT.md` — `translate`: 68 | `keep`: 302 | `kinds`: `{"quoted_phrase": 133, "ceo_quote": 131, "doc": 68, "title_name": 38}`
  17. `docs/reports/banchi-plates-reharvest-20260923/REPORT.md` — `translate`: 67 | `keep`: 38 | `kinds`: `{"doc": 67, "quoted_phrase": 33, "title_name": 5}`
  18. `docs/reports/teaser-subtitled-20260917/README.md` — `translate`: 57 | `keep`: 101 | `kinds`: `{"quoted_phrase": 101, "doc": 57}`

### Batch `B18` — Reports Part 5: Banchi & Flow Reports, 16–48 chars (`docs/reports`)
- **ID:** `B18`
- **Area:** `docs/reports` (Part 5)
- **File count:** 15
- **Translate characters:** 449
- **Keep characters:** 998
- **Risk note for reviewer:** `keep` (998 chars) is more than 2× `translate` (449 chars), including **CEO quotes** (235 chars in `khaoniao-family-style/STYLE-CARD.md` and `higgsfield-downgrade-20260906.md`) and **quoted dialogue/UI labels** (719 chars). Reviewer should verify that only the small pockets of unquoted Thai prose are translated.
- **Files:**
  1. `docs/reports/banchi-act1-shootB2-20260918/REPORT.md` — `translate`: 48 | `keep`: 5 | `kinds`: `{"doc": 48, "title_name": 5}`
  2. `docs/reports/khaoniao-family-style/STYLE-CARD.md` — `translate`: 45 | `keep`: 321 | `kinds`: `{"ceo_quote": 231, "quoted_phrase": 66, "doc": 45, "title_name": 24}`
  3. `docs/reports/banchi-assets-20260918/REPORT.md` — `translate`: 43 | `keep`: 40 | `kinds`: `{"doc": 43, "quoted_phrase": 35, "title_name": 5}`
  4. `docs/reports/banchi-shootA-20260919/replay-notes.js.md` — `translate`: 43 | `keep`: 162 | `kinds`: `{"quoted_phrase": 162, "doc": 43}`
  5. `docs/reports/banchi-act1-A2-20260918/REPORT.md` — `translate`: 38 | `keep`: 57 | `kinds`: `{"quoted_phrase": 52, "doc": 38, "title_name": 5}`
  6. `docs/reports/banchi-retrieval2-20260919/REPORT.md` — `translate`: 30 | `keep`: 0 | `kinds`: `{"doc": 30}`
  7. `docs/reports/omni-vs-veo-shot58-20260908.md` — `translate`: 30 | `keep`: 54 | `kinds`: `{"quoted_phrase": 54, "doc": 30}`
  8. `docs/reports/flow-runner-build/REPORT-iter3.md` — `translate`: 27 | `keep`: 24 | `kinds`: `{"doc": 27, "quoted_phrase": 24}`
  9. `docs/reports/banchi-act1-shootA2-20260918/REPORT.md` — `translate`: 26 | `keep`: 5 | `kinds`: `{"doc": 26, "title_name": 5}`
  10. `docs/reports/banchi-download-20260919/REPORT.md` — `translate`: 23 | `keep`: 43 | `kinds`: `{"quoted_phrase": 43, "doc": 23}`
  11. `docs/reports/flow-runner-build/REPORT.md` — `translate`: 22 | `keep`: 0 | `kinds`: `{"doc": 22}`
  12. `docs/reports/higgsfield-downgrade-20260906.md` — `translate`: 22 | `keep`: 29 | `kinds`: `{"quoted_phrase": 25, "doc": 22, "ceo_quote": 4}`
  13. `docs/reports/banchi-act1-retrieve-20260918/REPORT.md` — `translate`: 19 | `keep`: 256 | `kinds`: `{"quoted_phrase": 256, "doc": 19}`
  14. `docs/reports/banchi-retrieval-20260919/REPORT.md` — `translate`: 17 | `keep`: 0 | `kinds`: `{"doc": 17}`
  15. `docs/reports/flow-plates-20260907.md` — `translate`: 16 | `keep`: 2 | `kinds`: `{"doc": 16, "quoted_phrase": 2}`

### Batch `B19` — Output Part 1: Thai Trailer Narration Study (`output/research`)
- **ID:** `B19`
- **Area:** `output/research` (Part 1)
- **File count:** 1
- **Translate characters:** 7,535
- **Keep characters:** 10,117
- **Risk note for reviewer:** Single large mixed research file where `keep` (`quoted_phrase`: 10,117 chars of quoted Thai trailer narration and voiceover cadence examples) exceeds `translate` (7,535 chars of analytical prose). Do not translate any quoted Thai trailer voiceover excerpts, cadence patterns, or linguistic specimens; translate only the analytical explanations.
- **Files:**
  1. `output/research/2026-08-04-thai-trailer-narration-study.md` — `translate`: 7,535 | `keep`: 10,117 | `kinds`: `{"quoted_phrase": 10117, "doc": 7535}`

### Batch `B20` — Output Part 2: Research Studies, Lunar KB Draft & GDrive Bridge Docs (`output`)
- **ID:** `B20`
- **Area:** `output` (Part 2: `output/research`, `output/gdrive-bridge`, `output/lunar-kb-migration-rewrite-draft.md`)
- **File count:** 6
- **Translate characters:** 4,662
- **Keep characters:** 1,238
- **Risk note for reviewer:** Contains **CEO quotes** (417 chars across `2026-08-04-jadoodoo-kospi-crash.md`, `2026-06-10-thai-chuay-thai-plus-60-40.md`, and `lunar-kb-migration-rewrite-draft.md`) and **quoted Thai phrases / KB sample snippets** (`quoted_phrase`: 821 chars). In `2026-08-04-jadoodoo-kospi-crash.md`, `keep` (455) > `translate` (211); preserve all CEO quotes and Thai source headlines verbatim.
- **Files:**
  1. `output/research/2026-06-10-thai-chuay-thai-plus-60-40.md` — `translate`: 2,395 | `keep`: 186 | `kinds`: `{"doc": 2395, "quoted_phrase": 150, "ceo_quote": 36}`
  2. `output/lunar-kb-migration-rewrite-draft.md` — `translate`: 1,462 | `keep`: 356 | `kinds`: `{"doc": 1462, "quoted_phrase": 354, "ceo_quote": 2}`
  3. `output/gdrive-bridge/deploy-verification.md` — `translate`: 430 | `keep`: 18 | `kinds`: `{"doc": 430, "quoted_phrase": 18}`
  4. `output/research/2026-08-04-jadoodoo-kospi-crash.md` — `translate`: 211 | `keep`: 455 | `kinds`: `{"ceo_quote": 379, "doc": 211, "quoted_phrase": 76}`
  5. `output/gdrive-bridge/redeploy-v3.md` — `translate`: 142 | `keep`: 207 | `kinds`: `{"quoted_phrase": 207, "doc": 142}`
  6. `output/research/putterlu/SUMMARY.md` — `translate`: 22 | `keep`: 16 | `kinds`: `{"doc": 22, "quoted_phrase": 16}`

---

## Tier 4 — Code-Comment Batches (`B21`–`B27`) — **needs comment-only check**

All batches in Tier 4 translate **code comments only** (`kinds.comment`) and must wait until `tools/comment_only_check.py` (backlog `f2209b5b` item 4) is merged so CI can verify that zero tokens outside comments/docstrings were altered.

### Batch `B21` — Tools Comments Part 1: Top Tools, 59–682 chars (`tools/*.py` comments) — **needs comment-only check**
- **ID:** `B21`
- **Area:** `tools/*.py` comments (Part 1)
- **Status:** **needs comment-only check** (`tools/comment_only_check.py`)
- **File count:** 16
- **Translate characters:** 3,142
- **Keep characters:** 2,987
- **Risk note for reviewer:** **needs comment-only check.** Mixed Python tools with high **runtime string** counts (`runtime_string`: 2,987 chars — Facebook UI selectors, Thai regex patterns, Flow DOM labels, invoice strings). Touch `#` comments and docstrings only; `tools/comment_only_check.py` must pass with zero AST/bytecode diff.
- **Files:**
  1. `tools/fb_page_post.py` — `translate`: 682 | `keep`: 291 | `kinds`: `{"comment": 682, "runtime_string": 291}`
  2. `tools/fb_reel_post.py` — `translate`: 589 | `keep`: 600 | `kinds`: `{"runtime_string": 600, "comment": 589}`
  3. `tools/flow_shoot.py` — `translate`: 400 | `keep`: 432 | `kinds`: `{"runtime_string": 432, "comment": 400}`
  4. `tools/flow_upload_element.py` — `translate`: 261 | `keep`: 127 | `kinds`: `{"comment": 261, "runtime_string": 127}`
  5. `tools/session_diagram.py` — `translate`: 158 | `keep`: 324 | `kinds`: `{"runtime_string": 324, "comment": 158}`
  6. `tools/lakorn_poster.py` — `translate`: 125 | `keep`: 64 | `kinds`: `{"comment": 125, "runtime_string": 64}`
  7. `tools/fb_group_share.py` — `translate`: 120 | `keep`: 311 | `kinds`: `{"runtime_string": 311, "comment": 120}`
  8. `tools/shotsheet_lint.py` — `translate`: 120 | `keep`: 7 | `kinds`: `{"comment": 120, "runtime_string": 7}`
  9. `tools/org_inspector.py` — `translate`: 108 | `keep`: 0 | `kinds`: `{"comment": 108}`
  10. `tools/build_shotsheet.py` — `translate`: 96 | `keep`: 450 | `kinds`: `{"runtime_string": 450, "comment": 96}`
  11. `tools/contabo_invoice_reminder.py` — `translate`: 96 | `keep`: 219 | `kinds`: `{"runtime_string": 219, "comment": 96}`
  12. `tools/ilag_theme.py` — `translate`: 85 | `keep`: 74 | `kinds`: `{"comment": 85, "runtime_string": 74}`
  13. `tools/bl_checker.py` — `translate`: 83 | `keep`: 0 | `kinds`: `{"comment": 83}`
  14. `tools/burned_text_scan.py` — `translate`: 82 | `keep`: 2 | `kinds`: `{"comment": 82, "runtime_string": 2}`
  15. `tools/chatgpt_images.py` — `translate`: 78 | `keep`: 49 | `kinds`: `{"comment": 78, "runtime_string": 49}`
  16. `tools/delegate.py` — `translate`: 59 | `keep`: 37 | `kinds`: `{"comment": 59, "runtime_string": 37}`

### Batch `B22` — Tools Comments Part 2: Remaining Tools & Subpackages, 19–92 chars (`tools/**` comments) — **needs comment-only check**
- **ID:** `B22`
- **Area:** `tools/**` comments (Part 2: `tools/*.py`, `tools/ilag_publish/*.py`, `tools/mimi_fb_post/*.py`)
- **Status:** **needs comment-only check** (`tools/comment_only_check.py`)
- **File count:** 20
- **Translate characters:** 802
- **Keep characters:** 899
- **Risk note for reviewer:** **needs comment-only check.** Mixed files with **runtime strings** (804 chars — YouTube Studio / Facebook UI labels, Thai transcript regexes) and **user-facing text** (`tools/mimi_fb_post/fix_post_caption.py`: 95 chars of Thai Facebook caption text). Translate `#` comments only; do not alter any string literals.
- **Files:**
  1. `tools/ilag_publish/yt_trim_end.py` — `translate`: 92 | `keep`: 101 | `kinds`: `{"runtime_string": 101, "comment": 92}`
  2. `tools/disk_queue.py` — `translate`: 59 | `keep`: 0 | `kinds`: `{"comment": 59}`
  3. `tools/send_to_worker.py` — `translate`: 57 | `keep`: 0 | `kinds`: `{"comment": 57}`
  4. `tools/email_ceo.py` — `translate`: 56 | `keep`: 1 | `kinds`: `{"comment": 56, "runtime_string": 1}`
  5. `tools/send_to_cxo.py` — `translate`: 53 | `keep`: 0 | `kinds`: `{"comment": 53}`
  6. `tools/ilag_publish/yt_ab_set.py` — `translate`: 50 | `keep`: 52 | `kinds`: `{"runtime_string": 52, "comment": 50}`
  7. `tools/work_watch.py` — `translate`: 46 | `keep`: 0 | `kinds`: `{"comment": 46}`
  8. `tools/mimi_fb_post/fix_post_caption.py` — `translate`: 42 | `keep`: 95 | `kinds`: `{"user_facing": 95, "comment": 42}`
  9. `tools/bl_tiktok_cta.py` — `translate`: 40 | `keep`: 8 | `kinds`: `{"comment": 40, "runtime_string": 8}`
  10. `tools/continuity_sheet.py` — `translate`: 36 | `keep`: 2 | `kinds`: `{"comment": 36, "runtime_string": 2}`
  11. `tools/ilag_publish/yt_vis.py` — `translate`: 36 | `keep`: 0 | `kinds`: `{"comment": 36}`
  12. `tools/mimi_fb_post/schedule_photo_post.py` — `translate`: 36 | `keep`: 288 | `kinds`: `{"runtime_string": 288, "comment": 36}`
  13. `tools/ilag_publish/yt_subs_upload.py` — `translate`: 30 | `keep`: 77 | `kinds`: `{"runtime_string": 77, "comment": 30}`
  14. `tools/yt_studio_upload.py` — `translate`: 29 | `keep`: 7 | `kinds`: `{"comment": 29, "runtime_string": 7}`
  15. `tools/agy_browse.py` — `translate`: 28 | `keep`: 52 | `kinds`: `{"runtime_string": 52, "comment": 28}`
  16. `tools/flow_balance_ws.py` — `translate`: 27 | `keep`: 21 | `kinds`: `{"comment": 27, "runtime_string": 21}`
  17. `tools/clip_review.py` — `translate`: 22 | `keep`: 0 | `kinds`: `{"comment": 22}`
  18. `tools/film_transcript.py` — `translate`: 22 | `keep`: 158 | `kinds`: `{"runtime_string": 158, "comment": 22}`
  19. `tools/flow_cdp.py` — `translate`: 22 | `keep`: 22 | `kinds`: `{"comment": 22, "runtime_string": 22}`
  20. `tools/credit_ledger.py` — `translate`: 19 | `keep`: 15 | `kinds`: `{"comment": 19, "runtime_string": 15}`

### Batch `B23` — Runners, Lib, Windows & Skill Scripts Comments (`runners`, `lib`, `windows`, `.claude/skills/**/scripts`) — **needs comment-only check**
- **ID:** `B23`
- **Area:** `runners/*.py` + `lib/*.py` + `windows/**` + `.claude/skills/**/scripts/*.py` comments
- **Status:** **needs comment-only check** (`tools/comment_only_check.py`)
- **File count:** 12
- **Translate characters:** 728
- **Keep characters:** 16,873
- **Risk note for reviewer:** **needs comment-only check.** Very high **runtime string** volume (`keep`: 16,873 chars vs `translate`: 728 chars), especially in `runners/secretary_server.py` (14,862 chars of Thai bot replies/prompts), `windows/desktop/ceo_button.ps1` (1,090 chars of CEO desktop button UI labels), and `.claude/skills/CMO_Procedure_ReelEditor_TH/scripts/timeline_example.py` (645 chars of Thai subtitle examples). Verify via `tools/comment_only_check.py` (and manual diff on `.ps1`/`.sh`) that only `#` comments are modified.
- **Files:**
  1. `runners/relay_mcp_server.py` — `translate`: 133 | `keep`: 172 | `kinds`: `{"runtime_string": 172, "comment": 133}`
  2. `runners/secretary_server.py` — `translate`: 132 | `keep`: 14,862 | `kinds`: `{"runtime_string": 14862, "comment": 132}`
  3. `runners/drive_photo_broker.py` — `translate`: 84 | `keep`: 0 | `kinds`: `{"comment": 84}`
  4. `windows/cookierun_backup_stream.py` — `translate`: 77 | `keep`: 0 | `kinds`: `{"comment": 77}`
  5. `.claude/skills/CMO_Procedure_BlackLiquidity_JevEditor/scripts/jev_edit_lib.py` — `translate`: 62 | `keep`: 56 | `kinds`: `{"comment": 62, "runtime_string": 56}`
  6. `.claude/skills/CMO_Procedure_BlackLiquidity_JevEditor/scripts/jev_edit.py` — `translate`: 52 | `keep`: 0 | `kinds`: `{"comment": 52}`
  7. `windows/cookierun_idm_ab.py` — `translate`: 49 | `keep`: 0 | `kinds`: `{"comment": 49}`
  8. `.claude/skills/CMO_Procedure_ReelEditor_TH/scripts/timeline_example.py` — `translate`: 48 | `keep`: 645 | `kinds`: `{"runtime_string": 645, "comment": 48}`
  9. `lib/link_reader.py` — `translate`: 36 | `keep`: 0 | `kinds`: `{"comment": 36}`
  10. `windows/cookierun_idm_train_colab.py` — `translate`: 23 | `keep`: 0 | `kinds`: `{"comment": 23}`
  11. `windows/desktop/ceo_button.ps1` — `translate`: 16 | `keep`: 1,090 | `kinds`: `{"runtime_string": 1090, "comment": 16}`
  12. `windows/desktop/install_ceo_buttons.sh` — `translate`: 16 | `keep`: 48 | `kinds`: `{"runtime_string": 48, "comment": 16}`

### Batch `B24` — Scripts Comments: Launchers, Hooks & Utilities (`scripts/**` comments) — **needs comment-only check**
- **ID:** `B24`
- **Area:** `scripts/**` comments
- **Status:** **needs comment-only check** (`tools/comment_only_check.py`)
- **File count:** 18
- **Translate characters:** 1,234
- **Keep characters:** 3,259
- **Risk note for reviewer:** **needs comment-only check.** Contains Python, Bash (`.sh`), and JavaScript (`.js`) files with **runtime strings** (3,259 chars, notably `scripts/chatudo_outreach_sheet.py` with 2,419 chars of Thai outreach sheet strings, `scripts/tm_checks.py` with 297 chars, and `scripts/invoice_gen/generate_invoice.py` with 214 chars). Ensure `tools/comment_only_check.py` validates `.py` files and reviewer inspects `.sh`/`.js` diffs to confirm only `#`/`//` comments changed.
- **Files:**
  1. `scripts/cfo-claude-usage-feed.sh` — `translate`: 234 | `keep`: 0 | `kinds`: `{"comment": 234}`
  2. `scripts/tm_checks.py` — `translate`: 129 | `keep`: 297 | `kinds`: `{"runtime_string": 297, "comment": 129}`
  3. `scripts/hook-image-budget.py` — `translate`: 100 | `keep`: 105 | `kinds`: `{"runtime_string": 105, "comment": 100}`
  4. `scripts/chatudo_outreach_sheet.py` — `translate`: 85 | `keep`: 2,419 | `kinds`: `{"runtime_string": 2419, "comment": 85}`
  5. `scripts/hook-rename-nudge.py` — `translate`: 74 | `keep`: 0 | `kinds`: `{"comment": 74}`
  6. `scripts/invoice_gen/generate_invoice.py` — `translate`: 73 | `keep`: 214 | `kinds`: `{"runtime_string": 214, "comment": 73}`
  7. `scripts/hook-phone-only-commands.py` — `translate`: 68 | `keep`: 0 | `kinds`: `{"comment": 68}`
  8. `scripts/cto-claude.sh` — `translate`: 65 | `keep`: 10 | `kinds`: `{"comment": 65, "runtime_string": 10}`
  9. `scripts/cxo-claude.sh` — `translate`: 65 | `keep`: 10 | `kinds`: `{"comment": 65, "runtime_string": 10}`
  10. `scripts/gdrive-bridge/ilag_sync.py` — `translate`: 56 | `keep`: 0 | `kinds`: `{"comment": 56}`
  11. `scripts/stream_backup_to_drive.py` — `translate`: 56 | `keep`: 0 | `kinds`: `{"comment": 56}`
  12. `scripts/previz/s2aw_previz.py` — `translate`: 53 | `keep`: 0 | `kinds`: `{"comment": 53}`
  13. `scripts/hook-gdrive-skill-gate.py` — `translate`: 46 | `keep`: 11 | `kinds`: `{"comment": 46, "runtime_string": 11}`
  14. `scripts/session-rename.sh` — `translate`: 38 | `keep`: 0 | `kinds`: `{"comment": 38}`
  15. `scripts/tab-title.sh` — `translate`: 30 | `keep`: 0 | `kinds`: `{"comment": 30}`
  16. `scripts/browser/banchi-plates-download.js` — `translate`: 27 | `keep`: 0 | `kinds`: `{"comment": 27}`
  17. `scripts/idle-ping-watcher.sh` — `translate`: 18 | `keep`: 39 | `kinds`: `{"runtime_string": 39, "comment": 18}`
  18. `scripts/tm_prompt_eval.py` — `translate`: 17 | `keep`: 154 | `kinds`: `{"runtime_string": 154, "comment": 17}`

### Batch `B25` — Prompt & Report Builder Script Comments (`docs/prompts/**`, `docs/reports/khaoniao-family-style/**`) — **needs comment-only check**
- **ID:** `B25`
- **Area:** `docs/prompts/**` + `docs/reports/khaoniao-family-style/**` (`*.py` comments)
- **Status:** **needs comment-only check** (`tools/comment_only_check.py`)
- **File count:** 13
- **Translate characters:** 1,109
- **Keep characters:** 850
- **Risk note for reviewer:** **needs comment-only check.** Contains **user-facing Thai shot/dialogue strings** (`docs/prompts/last-bell/build_shots.py`: 116 chars; `docs/prompts/ilag-topview/build.py`: 10 chars) and **runtime poster title/caption strings** (`docs/reports/khaoniao-family-style/posters/render_posters.py`: 724 chars). Translate `#` comments only; leave all prompt/poster string literals untouched.
- **Files:**
  1. `docs/prompts/ilag-topview/wan3_prompt.py` — `translate`: 496 | `keep`: 0 | `kinds`: `{"comment": 496}`
  2. `docs/prompts/ilag-topview/build.py` — `translate`: 206 | `keep`: 10 | `kinds`: `{"comment": 206, "user_facing": 10}`
  3. `docs/prompts/ilag-topview/h3_fire.py` — `translate`: 95 | `keep`: 0 | `kinds`: `{"comment": 95}`
  4. `docs/prompts/ilag-topview/h3_add_entities.py` — `translate`: 52 | `keep`: 0 | `kinds`: `{"comment": 52}`
  5. `docs/reports/khaoniao-family-style/build_page_assets.py` — `translate`: 52 | `keep`: 0 | `kinds`: `{"comment": 52}`
  6. `docs/prompts/ilag-topview/finish.py` — `translate`: 38 | `keep`: 0 | `kinds`: `{"comment": 38}`
  7. `docs/prompts/ilag-topview/looks.py` — `translate`: 35 | `keep`: 0 | `kinds`: `{"comment": 35}`
  8. `docs/reports/khaoniao-family-style/build_ep1_plates.py` — `translate`: 32 | `keep`: 0 | `kinds`: `{"comment": 32}`
  9. `docs/prompts/last-bell/build_shots.py` — `translate`: 25 | `keep`: 116 | `kinds`: `{"user_facing": 116, "comment": 25}`
  10. `docs/reports/khaoniao-family-style/posters/render_posters.py` — `translate`: 25 | `keep`: 724 | `kinds`: `{"runtime_string": 724, "comment": 25}`
  11. `docs/prompts/ilag-topview/credits.py` — `translate`: 19 | `keep`: 0 | `kinds`: `{"comment": 19}`
  12. `docs/reports/khaoniao-family-style/build_ep2_plates.py` — `translate`: 18 | `keep`: 0 | `kinds`: `{"comment": 18}`
  13. `docs/reports/khaoniao-family-style/build_prompts.py` — `translate`: 16 | `keep`: 0 | `kinds`: `{"comment": 16}`

### Batch `B26` — Episode Script Data Comments (`docs/scripts/*.py` comments) — **needs comment-only check**
- **ID:** `B26`
- **Area:** `docs/scripts/*.py` comments
- **Status:** **needs comment-only check** (`tools/comment_only_check.py`)
- **File count:** 20
- **Translate characters:** 2,132
- **Keep characters:** 10,702
- **Risk note for reviewer:** **needs comment-only check.** High-risk mixed files: `keep` is **10,702 chars of `user_facing` Thai film dialogue and voiceover lines** embedded in Python data structures (`banchi-ACT1..7`, `khaoniao-ep1..5`, `ep3`, `ep4`, `taachang`). Only `#` comments (scene notes, director annotations) may be translated; `tools/comment_only_check.py` is mandatory to guarantee zero dialogue strings change.
- **Files:**
  1. `docs/scripts/ep3-ACTins.data.py` — `translate`: 353 | `keep`: 242 | `kinds`: `{"comment": 353, "user_facing": 242}`
  2. `docs/scripts/banchi-ACT6.data.py` — `translate`: 258 | `keep`: 1,923 | `kinds`: `{"user_facing": 1923, "comment": 258}`
  3. `docs/scripts/banchi-ACT1.data.py` — `translate`: 238 | `keep`: 1,906 | `kinds`: `{"user_facing": 1906, "comment": 238}`
  4. `docs/scripts/ep4-ACTacting.data.py` — `translate`: 204 | `keep`: 0 | `kinds`: `{"comment": 204}`
  5. `docs/scripts/banchi-ACT7.data.py` — `translate`: 156 | `keep`: 1,065 | `kinds`: `{"user_facing": 1065, "comment": 156}`
  6. `docs/scripts/khaoniao-ep5-ACT1.data.py` — `translate`: 123 | `keep`: 26 | `kinds`: `{"comment": 123, "user_facing": 26}`
  7. `docs/scripts/ep4-common.py` — `translate`: 117 | `keep`: 73 | `kinds`: `{"comment": 117, "user_facing": 73}`
  8. `docs/scripts/khaoniao-ep3-ACT1.data.py` — `translate`: 93 | `keep`: 29 | `kinds`: `{"comment": 93, "user_facing": 29}`
  9. `docs/scripts/khaoniao-ep2-ACT1.data.py` — `translate`: 86 | `keep`: 24 | `kinds`: `{"comment": 86, "user_facing": 24}`
  10. `docs/scripts/khaoniao-ep4-ACT1.data.py` — `translate`: 82 | `keep`: 19 | `kinds`: `{"comment": 82, "user_facing": 19}`
  11. `docs/scripts/khaoniao-ep1-ACT1.data.py` — `translate`: 78 | `keep`: 40 | `kinds`: `{"comment": 78, "user_facing": 40}`
  12. `docs/scripts/ep3-ACT1.data.py` — `translate`: 70 | `keep`: 74 | `kinds`: `{"user_facing": 74, "comment": 70}`
  13. `docs/scripts/banchi-ACT5.data.py` — `translate`: 56 | `keep`: 1,200 | `kinds`: `{"user_facing": 1200, "comment": 56}`
  14. `docs/scripts/banchi-ACT4.data.py` — `translate`: 53 | `keep`: 1,381 | `kinds`: `{"user_facing": 1381, "comment": 53}`
  15. `docs/scripts/ep3-ACT3.data.py` — `translate`: 35 | `keep`: 0 | `kinds`: `{"comment": 35}`
  16. `docs/scripts/ep3-ACT2.data.py` — `translate`: 28 | `keep`: 0 | `kinds`: `{"comment": 28}`
  17. `docs/scripts/taachang-ACT1.data.py` — `translate`: 28 | `keep`: 26 | `kinds`: `{"comment": 28, "user_facing": 26}`
  18. `docs/scripts/banchi-ACT3.data.py` — `translate`: 26 | `keep`: 1,163 | `kinds`: `{"user_facing": 1163, "comment": 26}`
  19. `docs/scripts/banchi-ACT2.data.py` — `translate`: 25 | `keep`: 1,467 | `kinds`: `{"user_facing": 1467, "comment": 25}`
  20. `docs/scripts/taachang-ACT2.data.py` — `translate`: 23 | `keep`: 44 | `kinds`: `{"user_facing": 44, "comment": 23}`

### Batch `B27` — Prototypes, Reels & Remaining Script Comments (`prototypes/**`, `output/reels/**`, `docs/scripts/taachang-ACT3.data.py`) — **needs comment-only check**
- **ID:** `B27`
- **Area:** `prototypes/**` + `output/reels/**` + `docs/scripts/taachang-ACT3.data.py` comments
- **Status:** **needs comment-only check** (`tools/comment_only_check.py`)
- **File count:** 9
- **Translate characters:** 945
- **Keep characters:** 3,341
- **Risk note for reviewer:** **needs comment-only check.** Contains **test fixtures / evaluation ground truth** (`prototypes/bl-ref-census/scripts/build_groundtruth.py`: 1,059 `runtime_string` chars; `prototypes/bl-model-bakeoff/tts/thai_tts_prep.py`: 343 `user_facing` chars; `output/reels/mooniex-trading-psychology-test/timeline.py`: 554 `runtime_string` chars) and **user-facing HTML UI text** (`prototypes/bl50-worker/cut/index.html`: 1,120 `user_facing` chars vs 44 `comment` chars). Translate only Python `#` comments and HTML `<!-- -->` comments.
- **Files:**
  1. `output/reels/mooniex-trading-psychology-test/timeline.py` — `translate`: 553 | `keep`: 554 | `kinds`: `{"runtime_string": 554, "comment": 553}`
  2. `prototypes/bl-ref-census/scripts/build_groundtruth.py` — `translate`: 70 | `keep`: 1,059 | `kinds`: `{"runtime_string": 1059, "comment": 70}`
  3. `prototypes/bl-broll-catalog/delete_verified.py` — `translate`: 57 | `keep`: 0 | `kinds`: `{"comment": 57}`
  4. `prototypes/bl-model-bakeoff/avatar/omni_run.py` — `translate`: 57 | `keep`: 0 | `kinds`: `{"comment": 57}`
  5. `prototypes/bl-ep60/make_plates.py` — `translate`: 55 | `keep`: 219 | `kinds`: `{"runtime_string": 219, "comment": 55}`
  6. `prototypes/bl-model-bakeoff/tts/thai_tts_prep.py` — `translate`: 48 | `keep`: 343 | `kinds`: `{"user_facing": 343, "comment": 48}`
  7. `prototypes/bl50-worker/cut/index.html` — `translate`: 44 | `keep`: 1,120 | `kinds`: `{"user_facing": 1120, "comment": 44}`
  8. `prototypes/bl-ep59/make_plates.py` — `translate`: 38 | `keep`: 27 | `kinds`: `{"comment": 38, "runtime_string": 27}`
  9. `docs/scripts/taachang-ACT3.data.py` — `translate`: 23 | `keep`: 19 | `kinds`: `{"comment": 23, "user_facing": 19}`

---

## Skip List (119 Files — 5,040 Translate Chars, 4,792 Keep Chars)

Every in-scope file not in `B01`–`B27` appears below with its skip rule (`S1`–`S4`), `translate` chars, `keep` chars, `kinds`, and specific reason.

### Rule `S1` — Generated Reports, Execution Logs, Runtime State Snapshots, and OS Plist Artifacts (11 files, 2,845 `translate` chars, 318 `keep` chars)

| # | Path | Kind | Translate | Keep | `kinds` | Reason |
|---:|---|---|---:|---:|---|---|
| 1 | `docs/reports/task-ee30ba95/timings-alignment-report.txt` | `doc` | 1,977 | 0 | `{"doc": 1977}` | Generated forced-alignment timing output from `align_timings.py` containing Thai syllable/transcript tokens (`S1`). |
| 2 | `state/banchi/flow_shoot.log` | `doc` | 291 | 68 | `{"doc": 291, "quoted_phrase": 68}` | Captured stdout execution log from `tools/flow_shoot.py` (`S1`). |
| 3 | `state/sompong-line/profile-upload-retry.md` | `doc` | 111 | 136 | `{"quoted_phrase": 136, "doc": 111}` | Runtime state snapshot in `state/sompong-line/` (`keep` > `translate`) (`S1`). |
| 4 | `docs/reports/banchi-fb-repost3/real-run-2.log` | `doc` | 98 | 0 | `{"doc": 98}` | Raw CLI stdout log from Facebook repost run (`S1`). |
| 5 | `docs/reports/banchi-fb-repost3/real-run.log` | `doc` | 98 | 0 | `{"doc": 98}` | Raw CLI stdout log from Facebook repost run (`S1`). |
| 6 | `state/banchi/flow_shoot-runner-review-0923.log` | `doc` | 98 | 0 | `{"doc": 98}` | Captured runner execution log in `state/banchi/` (`S1`). |
| 7 | `state/sompong-line/oa-setup-report.md` | `doc` | 81 | 11 | `{"doc": 81, "quoted_phrase": 11}` | Runtime state snapshot in `state/sompong-line/` (`S1`). |
| 8 | `docs/reports/banchi-fb-repost3/dry-run.log` | `doc` | 47 | 0 | `{"doc": 47}` | Raw CLI stdout log from Facebook repost dry-run (`S1`). |
| 9 | `state/sompong-line/images-report.md` | `doc` | 36 | 103 | `{"quoted_phrase": 103, "doc": 36}` | Runtime state snapshot in `state/sompong-line/` (`keep` 2.9× `translate`) (`S1`). |
| 10 | `scripts/com.mooniex.cfo-claude-usage.plist` | `comment` | 4 | 0 | `{"comment": 4}` | macOS LaunchAgent XML `.plist` with 4 Thai chars in an XML comment (`S1`). |
| 11 | `state/mac-blueprint-20260925/LaunchAgents/com.mooniex.cfo-claude-usage.plist` | `comment` | 4 | 0 | `{"comment": 4}` | Captured machine-state backup of macOS LaunchAgent `.plist` (`S1`). |

### Rule `S2` — Source Transcripts, Scraped YouTube `.description` Captures, and User-Facing Thai Marketing Copy Fixtures (10 files, 1,361 `translate` chars, 52 `keep` chars)

| # | Path | Kind | Translate | Keep | `kinds` | Reason |
|---:|---|---|---:|---:|---|---|
| 12 | `output/mooniex-posters/gold-giveaway-recap/line-text-3posters.md` | `doc` | 595 | 16 | `{"doc": 595, "quoted_phrase": 16}` | User-facing Thai LINE OA broadcast copy deliverable for MoonieX gold giveaway posters (`S2`). |
| 13 | `output/mooniex-posters/gold-giveaway-recap/line-text.md` | `doc` | 316 | 16 | `{"doc": 316, "quoted_phrase": 16}` | User-facing Thai LINE OA broadcast copy deliverable for MoonieX gold giveaway (`S2`). |
| 14 | `knowledge/content-knowledge/skills/rebate-copy/example.md` | `doc` | 103 | 0 | `{"doc": 103}` | Canonical Thai marketing copy specimen for the `rebate-copy` skill (`S2`). |
| 15 | `output/research/putterlu/UrzGMsfJdxw.description` | `doc` | 77 | 5 | `{"doc": 77, "quoted_phrase": 5}` | Scraped `yt-dlp` YouTube video description source capture (`S2`). |
| 16 | `output/research/putterlu/t0LojwzpoAA.description` | `doc` | 77 | 5 | `{"doc": 77, "quoted_phrase": 5}` | Scraped `yt-dlp` YouTube video description source capture (`S2`). |
| 17 | `output/research/putterlu/KKl8Ur7NO6I.description` | `doc` | 53 | 5 | `{"doc": 53, "quoted_phrase": 5}` | Scraped `yt-dlp` YouTube video description source capture (`S2`). |
| 18 | `output/research/putterlu/OngHERwMB3s.description` | `doc` | 53 | 5 | `{"doc": 53, "quoted_phrase": 5}` | Scraped `yt-dlp` YouTube video description source capture (`S2`). |
| 19 | `output/research/putterlu/Cl1APJ-Bvmw.description` | `doc` | 29 | 0 | `{"doc": 29}` | Scraped `yt-dlp` YouTube video description source capture (`S2`). |
| 20 | `output/research/putterlu/OGi5toYaaJM.description` | `doc` | 29 | 0 | `{"doc": 29}` | Scraped `yt-dlp` YouTube video description source capture (`S2`). |
| 21 | `output/research/putterlu/lRx3bZOJ4gY.description` | `doc` | 29 | 0 | `{"doc": 29}` | Scraped `yt-dlp` YouTube video description source capture (`S2`). |

### Rule `S3` — Archived Inter-Agent Letters Not Worth Review (2 files, 20 `translate` chars, 72 `keep` chars)

| # | Path | Kind | Translate | Keep | `kinds` | Reason |
|---:|---|---|---:|---:|---|---|
| 22 | `docs/ops/letters/2026-09-25-cto-6ebacd0e-to-console-owner-run-inbox-p1.md` | `doc` | 14 | 6 | `{"doc": 14, "quoted_phrase": 6}` | Archived point-in-time inter-agent handoff letter with only 14 translatable Thai chars (`S3`). |
| 23 | `docs/ops/letters/2026-09-26-cto-885ae930-to-console-owner-relay-idp-fix.md` | `doc` | 6 | 66 | `{"quoted_phrase": 66, "doc": 6}` | Archived inter-agent letter where `keep` (66 chars) is 11× `translate` (6 chars) (`S3`). |

### Rule `S4` — Micro-Count Tail (`translate <= 15` Thai chars; 96 files: 48 `doc` + 48 `comment`, 814 `translate` chars, 4,350 `keep` chars)

#### `S4a` — `doc` Files with `translate <= 15` (48 files, 402 `translate` chars, 2,983 `keep` chars)

| # | Path | Kind | Translate | Keep | `kinds` | Reason |
|---:|---|---|---:|---:|---|---|
| 24 | `docs/briefs/chatudo-october-build.md` | `doc` | 15 | 135 | `{"quoted_phrase": 135, "doc": 15}` | Almost all keep-kinds (135 `keep` vs 15 `translate`, ≤ 15 chars) (`S4`). |
| 25 | `docs/design/login-relay/NEKO-EVAL-2026-09-26.md` | `doc` | 15 | 0 | `{"doc": 15}` | Micro-count tail (15 Thai chars; 1–2 Thai words in an English eval doc) (`S4`). |
| 26 | `docs/org/SKILL-KINDS-2026-09-27.md` | `doc` | 15 | 30 | `{"quoted_phrase": 30, "doc": 15}` | Mostly keep-kinds (30 `keep` vs 15 `translate`, ≤ 15 chars) (`S4`). |
| 27 | `docs/reports/cto-cb63de3a-ep4-post/REPORT.md` | `doc` | 15 | 43 | `{"quoted_phrase": 28, "title_name": 15, "doc": 15}` | Archived report with mostly keep-kinds (43 `keep` vs 15 `translate`) (`S4`). |
| 28 | `docs/briefs/banchi-plates-harvest.md` | `doc` | 14 | 5 | `{"doc": 14, "title_name": 5}` | Micro-count tail (14 Thai chars — film/character name mention) (`S4`). |
| 29 | `docs/design/login-relay/operator-tap-test-brief.md` | `doc` | 14 | 0 | `{"doc": 14}` | Micro-count tail (14 Thai chars) (`S4`). |
| 30 | `docs/ops/briefs/run-inbox-p1a-console.md` | `doc` | 14 | 0 | `{"doc": 14}` | Micro-count tail (14 Thai chars) (`S4`). |
| 31 | `docs/reports/banchi-plate-urls-20260918/REPORT.md` | `doc` | 14 | 0 | `{"doc": 14}` | Archived report with 14 Thai chars (`S4`). |
| 32 | `prototypes/mypasakon-voice/WIKI-DRAFT-index-line.txt` | `doc` | 14 | 0 | `{"doc": 14}` | Single-line prototype wiki index snippet with 14 Thai chars (`S4`). |
| 33 | `claude-home/CLAUDE.md` | `doc` | 13 | 9 | `{"doc": 13, "quoted_phrase": 9}` | Micro-count tail (13 Thai chars) (`S4`). |
| 34 | `docs/reports/ilag-trailer-chatgpt-characters-20260924/REPLAY.md` | `doc` | 13 | 47 | `{"quoted_phrase": 47, "doc": 13}` | Archived replay note with mostly keep-kinds (47 `keep` vs 13 `translate`) (`S4`). |
| 35 | `docs/reports/task-cfdc75a8/REPORT.md` | `doc` | 13 | 136 | `{"quoted_phrase": 136, "doc": 13}` | Almost all keep-kinds (136 `keep` vs 13 `translate`) (`S4`). |
| 36 | `docs/reports/task-ee30ba95/BRIEF-arm1-ep58.md` | `doc` | 13 | 39 | `{"quoted_phrase": 39, "doc": 13}` | Mostly keep-kinds (39 `keep` vs 13 `translate`) (`S4`). |
| 37 | `research/xxlmarkets-wikifx-fca-domain-202609.md` | `doc` | 13 | 312 | `{"quoted_phrase": 312, "doc": 13}` | Almost all keep-kinds (312 `keep` vs 13 `translate`) (`S4`). |
| 38 | `docs/briefs/banchi-clip-retrieval.md` | `doc` | 12 | 0 | `{"doc": 12}` | Micro-count tail (12 Thai chars) (`S4`). |
| 39 | `docs/reports/absence-draft3-cto-additions-20260909.md` | `doc` | 12 | 67 | `{"quoted_phrase": 52, "title_name": 15, "doc": 12}` | Almost all keep-kinds (67 `keep` vs 12 `translate`) (`S4`). |
| 40 | `docs/reports/google-flow-recon-20260907.md` | `doc` | 12 | 108 | `{"quoted_phrase": 108, "doc": 12}` | Almost all keep-kinds (108 `keep` vs 12 `translate`) (`S4`). |
| 41 | `output/gdrive-bridge/paste-verification.md` | `doc` | 12 | 60 | `{"quoted_phrase": 60, "doc": 12}` | Mostly keep-kinds (60 `keep` vs 12 `translate`) (`S4`). |
| 42 | `prototypes/bl57-realfootage/third-party/SOURCES.md` | `doc` | 12 | 136 | `{"quoted_phrase": 136, "doc": 12}` | Almost all keep-kinds (136 `keep` vs 12 `translate`) (`S4`). |
| 43 | `docs/char_gentleman_c_asset_log.md` | `doc` | 11 | 0 | `{"doc": 11}` | Micro-count tail (11 Thai chars) (`S4`). |
| 44 | `docs/reports/banchi-batch1-20260919/REPORT.md` | `doc` | 10 | 78 | `{"quoted_phrase": 73, "doc": 10, "title_name": 5}` | Almost all keep-kinds (78 `keep` vs 10 `translate`) (`S4`). |
| 45 | `docs/briefs/chatudo-cmo-front-office.md` | `doc` | 9 | 263 | `{"quoted_phrase": 263, "doc": 9}` | Almost all keep-kinds (263 `keep` vs 9 `translate`) (`S4`). |
| 46 | `docs/ops/bl-split-ab-2026-09-25/RUNLOG-task-99f3d2e8.md` | `doc` | 9 | 5 | `{"doc": 9, "quoted_phrase": 5}` | Micro-count tail (9 Thai chars in runlog) (`S4`). |
| 47 | `docs/WAVE5-AUTHORING-DOCTRINE.md` | `doc` | 8 | 0 | `{"doc": 8}` | Micro-count tail (8 Thai chars) (`S4`). |
| 48 | `docs/briefs/banchi-plate-urls.md` | `doc` | 7 | 0 | `{"doc": 7}` | Micro-count tail (7 Thai chars) (`S4`). |
| 49 | `docs/reports/grok-thai-lipsync-20260906.md` | `doc` | 7 | 94 | `{"quoted_phrase": 94, "doc": 7}` | Almost all keep-kinds (94 `keep` vs 7 `translate`) (`S4`). |
| 50 | `docs/reports/ilag-trailer-chatgpt-round2-20260924/REPORT.md` | `doc` | 7 | 38 | `{"quoted_phrase": 38, "doc": 7}` | Mostly keep-kinds (38 `keep` vs 7 `translate`) (`S4`). |
| 51 | `.claude/skills/CMO_Knowledge_Seedance2.5_Higgsfield/AB-LEDGER.md` | `doc` | 6 | 669 | `{"quoted_phrase": 669, "doc": 6}` | 99.1% keep-kinds (669 `keep` vs 6 `translate`) (`S4`). |
| 52 | `docs/SESSION-RENAME-STATE.md` | `doc` | 6 | 0 | `{"doc": 6}` | Micro-count tail (6 Thai chars) (`S4`). |
| 53 | `docs/design/secrets-infisical/PLAN.md` | `doc` | 6 | 63 | `{"quoted_phrase": 63, "doc": 6}` | Almost all keep-kinds (63 `keep` vs 6 `translate`) (`S4`). |
| 54 | `docs/design/sompong-coo-session.md` | `doc` | 6 | 141 | `{"quoted_phrase": 141, "doc": 6}` | Almost all keep-kinds (141 `keep` vs 6 `translate`) (`S4`). |
| 55 | `docs/reports/banchi-act1-review-20260918/REPAIR-NOTES.md` | `doc` | 6 | 0 | `{"doc": 6}` | Micro-count tail (6 Thai chars) (`S4`). |
| 56 | `docs/reports/task-ee30ba95/REPORT.md` | `doc` | 6 | 5 | `{"doc": 6, "quoted_phrase": 5}` | Micro-count tail (6 Thai chars) (`S4`). |
| 57 | `tools/ilag_publish/README.md` | `doc` | 6 | 38 | `{"quoted_phrase": 38, "doc": 6}` | Mostly keep-kinds (38 `keep` vs 6 `translate`) (`S4`). |
| 58 | `tools/mimi_fb_post/README.md` | `doc` | 6 | 26 | `{"quoted_phrase": 26, "doc": 6}` | Mostly keep-kinds (26 `keep` vs 6 `translate`) (`S4`). |
| 59 | `docs/ops/agy-browser.md` | `doc` | 5 | 0 | `{"doc": 5}` | Micro-count tail (5 Thai chars) (`S4`). |
| 60 | `docs/reports/higgsfield-support-reply-20260906.md` | `doc` | 5 | 12 | `{"quoted_phrase": 12, "doc": 5}` | Micro-count tail (5 Thai chars) (`S4`). |
| 61 | `research/regulator-license-registers-2026-09.md` | `doc` | 3 | 0 | `{"doc": 3}` | Micro-count tail (3 Thai chars) (`S4`). |
| 62 | `.claude/skills/CMO_Procedure_BlackLiquidity_Cut/BL-KIT.md` | `doc` | 2 | 35 | `{"quoted_phrase": 35, "doc": 2}` | Almost all keep-kinds (35 `keep` vs 2 `translate`) (`S4`). |
| 63 | `docs/design/sompong-photos.md` | `doc` | 2 | 154 | `{"quoted_phrase": 154, "doc": 2}` | 98.7% keep-kinds (154 `keep` vs 2 `translate`) (`S4`). |
| 64 | `docs/ops/briefs/h3-colab-safe-split-design.md` | `doc` | 2 | 0 | `{"doc": 2}` | Micro-count tail (2 Thai chars) (`S4`). |
| 65 | `docs/ops/colab-ultra-audit.md` | `doc` | 2 | 95 | `{"quoted_phrase": 95, "doc": 2}` | 97.9% keep-kinds (95 `keep` vs 2 `translate`) (`S4`). |
| 66 | `prototypes/bl50-worker/cut/BL-KIT.md` | `doc` | 2 | 35 | `{"quoted_phrase": 35, "doc": 2}` | Almost all keep-kinds (35 `keep` vs 2 `translate`) (`S4`). |
| 67 | `prototypes/bl51-first30/BL-KIT.md` | `doc` | 2 | 35 | `{"quoted_phrase": 35, "doc": 2}` | Almost all keep-kinds (35 `keep` vs 2 `translate`) (`S4`). |
| 68 | `prototypes/bl51-full-worker/BL-KIT.md` | `doc` | 2 | 35 | `{"quoted_phrase": 35, "doc": 2}` | Almost all keep-kinds (35 `keep` vs 2 `translate`) (`S4`). |
| 69 | `prototypes/bl51-worker-test/BL-KIT.md` | `doc` | 2 | 35 | `{"quoted_phrase": 35, "doc": 2}` | Almost all keep-kinds (35 `keep` vs 2 `translate`) (`S4`). |
| 70 | `docs/research/2026-09-18-google-flow-commercial-rights.md` | `doc` | 1 | 0 | `{"doc": 1}` | Micro-count tail (1 Thai char) (`S4`). |
| 71 | `prototypes/bl-ref-census/seed/README.md` | `doc` | 1 | 0 | `{"doc": 1}` | Micro-count tail (1 Thai char) (`S4`). |

#### `S4b` — `comment` Files with `translate <= 15` (48 files, 412 `translate` chars, 1,367 `keep` chars)

| # | Path | Kind | Translate | Keep | `kinds` | Reason |
|---:|---|---|---:|---:|---|---|
| 72 | `docs/prompts/ilag-topview/cover.py` | `comment` | 15 | 0 | `{"comment": 15}` | Micro-count comment tail (15 Thai chars) (`S4`). |
| 73 | `docs/reports/khaoniao-family-style/cover/card.html` | `comment` | 15 | 140 | `{"user_facing": 140, "comment": 15}` | Almost all keep-kinds (140 `user_facing` vs 15 `comment`) (`S4`). |
| 74 | `runners/drive_upload_broker.py` | `comment` | 15 | 0 | `{"comment": 15}` | Micro-count comment tail (15 Thai chars) (`S4`). |
| 75 | `scripts/install-drive-broker.sh` | `comment` | 15 | 0 | `{"comment": 15}` | Micro-count comment tail (15 Thai chars) (`S4`). |
| 76 | `docs/reports/khaoniao-family-style/cover/cover.html` | `comment` | 14 | 64 | `{"user_facing": 64, "comment": 14}` | Mostly keep-kinds (64 `user_facing` vs 14 `comment`) (`S4`). |
| 77 | `docs/reports/khaoniao-family-style/posters/poster.html` | `comment` | 14 | 14 | `{"comment": 14, "user_facing": 14}` | Micro-count comment tail (14 Thai chars) (`S4`). |
| 78 | `tools/film_cut_assemble.py` | `comment` | 14 | 0 | `{"comment": 14}` | Micro-count comment tail (14 Thai chars) (`S4`). |
| 79 | `windows/winbox-reinstall/winbox-bootstrap.ps1` | `comment` | 14 | 0 | `{"comment": 14}` | Micro-count comment tail (14 Thai chars) (`S4`). |
| 80 | `prototypes/bl-ep58/armA/render_window.py` | `comment` | 13 | 12 | `{"comment": 13, "runtime_string": 12}` | Micro-count comment tail (13 Thai chars) (`S4`). |
| 81 | `scripts/browser/grok-imagine-thai-test.js` | `comment` | 13 | 0 | `{"comment": 13}` | Micro-count comment tail (13 Thai chars) (`S4`). |
| 82 | `tools/ilag_publish/yt_publish_draft.py` | `comment` | 13 | 13 | `{"comment": 13, "runtime_string": 13}` | Micro-count comment tail (13 Thai chars) (`S4`). |
| 83 | `docs/scripts/ep4-ACT1.data.py` | `comment` | 11 | 0 | `{"comment": 11}` | Micro-count comment tail (11 Thai chars) (`S4`). |
| 84 | `docs/scripts/ep4-ACT2.data.py` | `comment` | 11 | 0 | `{"comment": 11}` | Micro-count comment tail (11 Thai chars) (`S4`). |
| 85 | `docs/scripts/ep4-ACT3.data.py` | `comment` | 11 | 0 | `{"comment": 11}` | Micro-count comment tail (11 Thai chars) (`S4`). |
| 86 | `runners/mac_agent.py` | `comment` | 11 | 0 | `{"comment": 11}` | Micro-count comment tail (11 Thai chars) (`S4`). |
| 87 | `prototypes/mypasakon-voice/analyze_style.py` | `comment` | 10 | 61 | `{"runtime_string": 61, "comment": 10}` | Mostly keep-kinds (61 `runtime_string` vs 10 `comment`) (`S4`). |
| 88 | `scripts/champa/queue_guard.py` | `comment` | 10 | 0 | `{"comment": 10}` | Micro-count comment tail (10 Thai chars) (`S4`). |
| 89 | `tools/ilag_round.py` | `comment` | 10 | 0 | `{"comment": 10}` | Micro-count comment tail (10 Thai chars) (`S4`). |
| 90 | `scripts/frost_knight_weapons.py` | `comment` | 9 | 0 | `{"comment": 9}` | Micro-count comment tail (9 Thai chars) (`S4`). |
| 91 | `tools/bl_compose.py` | `comment` | 9 | 0 | `{"comment": 9}` | Micro-count comment tail (9 Thai chars) (`S4`). |
| 92 | `.claude/skills/CMO_Procedure_ReelEditor_TH/scripts/timeline_template.py` | `comment` | 8 | 43 | `{"runtime_string": 43, "comment": 8}` | Mostly keep-kinds (43 `runtime_string` vs 8 `comment`) (`S4`). |
| 93 | `docs/reports/khaoniao-family-style/cover/render_ep3_cards.py` | `comment` | 8 | 62 | `{"runtime_string": 62, "comment": 8}` | Almost all keep-kinds (62 `runtime_string` vs 8 `comment`) (`S4`). |
| 94 | `docs/reports/khaoniao-family-style/cover/render_recap_cards.py` | `comment` | 8 | 115 | `{"runtime_string": 115, "comment": 8}` | Almost all keep-kinds (115 `runtime_string` vs 8 `comment`) (`S4`). |
| 95 | `docs/reports/task-ee30ba95/align_timings.py` | `comment` | 8 | 5 | `{"comment": 8, "runtime_string": 5}` | Micro-count comment tail (8 Thai chars) (`S4`). |
| 96 | `scripts/gen-alien-character.py` | `comment` | 8 | 0 | `{"comment": 8}` | Micro-count comment tail (8 Thai chars) (`S4`). |
| 97 | `scripts/skill-doctrine-lint.py` | `comment` | 8 | 0 | `{"comment": 8}` | Micro-count comment tail (8 Thai chars) (`S4`). |
| 98 | `tools/cookierun_teachers.py` | `comment` | 8 | 272 | `{"runtime_string": 272, "comment": 8}` | 97.1% keep-kinds (272 `runtime_string` vs 8 `comment`) (`S4`). |
| 99 | `tools/itermtab.py` | `comment` | 8 | 10 | `{"runtime_string": 10, "comment": 8}` | Micro-count comment tail (8 Thai chars) (`S4`). |
| 100 | `docs/scripts/ep5-ACT1.data.py` | `comment` | 7 | 0 | `{"comment": 7}` | Micro-count comment tail (7 Thai chars) (`S4`). |
| 101 | `docs/scripts/ep5-ACT2.data.py` | `comment` | 7 | 0 | `{"comment": 7}` | Micro-count comment tail (7 Thai chars) (`S4`). |
| 102 | `docs/scripts/ep5-ACT3.data.py` | `comment` | 7 | 0 | `{"comment": 7}` | Micro-count comment tail (7 Thai chars) (`S4`). |
| 103 | `docs/scripts/ep5-ACT4.data.py` | `comment` | 7 | 0 | `{"comment": 7}` | Micro-count comment tail (7 Thai chars) (`S4`). |
| 104 | `docs/scripts/ep5-common.py` | `comment` | 7 | 46 | `{"user_facing": 46, "comment": 7}` | Almost all keep-kinds (46 `user_facing` vs 7 `comment`) (`S4`). |
| 105 | `scripts/session_list.py` | `comment` | 7 | 11 | `{"runtime_string": 11, "comment": 7}` | Micro-count comment tail (7 Thai chars) (`S4`). |
| 106 | `tools/bl_tiktok_watch.py` | `comment` | 7 | 28 | `{"runtime_string": 28, "comment": 7}` | Mostly keep-kinds (28 `runtime_string` vs 7 `comment`) (`S4`). |
| 107 | `tools/drive_leg.py` | `comment` | 7 | 0 | `{"comment": 7}` | Micro-count comment tail (7 Thai chars) (`S4`). |
| 108 | `scripts/gdrive-bridge/upload_suno_cues.py` | `comment` | 6 | 0 | `{"comment": 6}` | Micro-count comment tail (6 Thai chars) (`S4`). |
| 109 | `scripts/prompt-lint.py` | `comment` | 6 | 0 | `{"comment": 6}` | Micro-count comment tail (6 Thai chars) (`S4`). |
| 110 | `tools/assemble_act.py` | `comment` | 5 | 0 | `{"comment": 5}` | Micro-count comment tail (5 Thai chars) (`S4`). |
| 111 | `tools/flow_ledger.py` | `comment` | 5 | 0 | `{"comment": 5}` | Micro-count comment tail (5 Thai chars) (`S4`). |
| 112 | `scripts/infisical/watch_login.sh` | `comment` | 4 | 0 | `{"comment": 4}` | Micro-count comment tail (4 Thai chars) (`S4`). |
| 113 | `output/console-design/iterm-mobile-console.html` | `comment` | 3 | 291 | `{"user_facing": 291, "comment": 3}` | 99.0% keep-kinds (291 `user_facing` vs 3 `comment`) (`S4`). |
| 114 | `runners/secretary_telegram_poll.py` | `comment` | 3 | 149 | `{"runtime_string": 149, "comment": 3}` | 98.0% keep-kinds (149 `runtime_string` vs 3 `comment`) (`S4`). |
| 115 | `scripts/hook-skill-write-reminder.py` | `comment` | 3 | 0 | `{"comment": 3}` | Micro-count comment tail (3 Thai chars) (`S4`). |
| 116 | `scripts/skill-curator.py` | `comment` | 3 | 0 | `{"comment": 3}` | Micro-count comment tail (3 Thai chars) (`S4`). |
| 117 | `scripts/skill-lint.py` | `comment` | 3 | 0 | `{"comment": 3}` | Micro-count comment tail (3 Thai chars) (`S4`). |
| 118 | `runners/sompong_photo_filer.py` | `comment` | 2 | 2 | `{"comment": 2, "runtime_string": 2}` | Micro-count comment tail (2 Thai chars) (`S4`). |
| 119 | `tools/bl_ab_run.py` | `comment` | 2 | 29 | `{"runtime_string": 29, "comment": 2}` | Almost all keep-kinds (29 `runtime_string` vs 2 `comment`) (`S4`). |
