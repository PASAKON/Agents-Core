# Tool value: weekly report + enforcing outside runners (plan, 2026-10-13)

**Order.** CEO 13 Oct 2026, relayed by SomPong (COO):
"Week นี้ สิ่งที่ต้องมีและเห็นได้ชัดคือ Haiku ช่วยเราได้มากขึ้นแค่ไหน / Jules ใช้งานบ่อยแค่ไหน / AGY ใช้เต็ม
ประสิทธิภาพไหม / ChatGPT เอามาใช้งาน ORG เพิ่มไหม / JEV เอามาใช้ช่วยประหยัดไปได้เท่าไหร่ … เปรียบเทียบระหว่าง
week ที่ผ่านมากับ week นี้ว่าเราใช้สิ่งที่มีอยู่คุ้มค่าแค่ไหน", then "ให้ CTO เขียนแผนแบบละเอียดมาเลยว่าจะจัดการยังไง",
then "ทำเป็นระบบบังคับใช้ยังไง skill แบบไหน". First report due **Mon 19 Oct 2026**.

**Author.** CONTABO CTO #8fb0f1b1, supervised by CONTABO CTO #e106b78b. **Status: PLAN.** Nothing in §3, §4 or
§6 is built yet. The baseline numbers in §1 were read today, read-only, with no paid call.

**Labels.**
- **MEASURED**: read today from a log, a ledger or the hub.
- **ESTIMATE**: computed, with the basis stated.
- **BOUND**: a ceiling, not a value.
- **ไม่มีข้อมูล**: no source exists, or the source sits on a host this session cannot reach.

**Calendar.** 6 Oct 2026 is a Tuesday, so the CEO's weeks run Tue–Mon: "last week" = Tue 6 → Mon 12 Oct, and
"this week" = Tue 13 → Mon 19 Oct. Contabo's clock is CEST, so Bangkok = clock + 5 h until 25 Oct and clock + 6 h
after it. Every time below is Bangkok time (BKK) unless it says UTC.

---

## 0. สรุปสำหรับ CEO

- **สัปดาห์ 6–12 ต.ค. (วัดแล้ว):**
  - Claude: ใช้เต็มเพดานตั้งแต่จันทร์ 12 ต.ค. 08:57 และค้างที่เพดานประมาณ 32 ชั่วโมงจนรีเซ็ตอังคาร 17:00
  - AGY-Gemini (แพ็กเกจ Google $100): ใช้แค่ประมาณ 3% ของโควตาสัปดาห์
  - Codex/ChatGPT: 17 งาน (CEO สั่งเมื่อ 10 ต.ค.) ใช้ประมาณ 50% ของโควตาสัปดาห์
  - Jules: 0 PR ตั้งแต่ 28 ก.ย. (เพดาน 300 session ต่อวัน)
  - Haiku 5.5: 1 ข้อความ
  - JEV: 0 ครั้งบน Contabo
- **ปัญหาไม่ใช่ "ของไม่พอ" แต่งานไม่ถูกส่งไปหาเครื่องมือที่ยังว่าง** ระหว่างที่ Claude ค้างเพดาน 32 ชม. Gemini ยังเหลือ 97%
- **(A) วัดผล:** สคริปต์เดียว `tools/tool_value.py` รันอัตโนมัติทุกจันทร์ 08:00 น. เวลาไทย ได้ตารางตัวเลข 2 สัปดาห์ +
  สรุปไทย 5 บรรทัด ส่งผ่าน SomPong ใช้ token ของโมเดล = 0 (ตัวเลขทั้งหมดมาจาก log ที่มีอยู่แล้ว)
- **(B) บังคับใช้:** ใช้ code ที่จุด `delegate_task` (มีอยู่แล้ว ขยาย 3 จุด) + hook ที่ Agent tool (สัปดาห์แรกเก็บ log
  อย่างเดียว) + เกณฑ์ขั้นต่ำต่อเครื่องมือ (ต่ำกว่าเกณฑ์ = ได้เจ้าของ + งานที่ต้องย้ายเป็น LungNote todo มีกำหนดวัน) +
  skill 2 ตัว (`COO_Procedure_ToolValueWeekly`, `CXO_Gate_RouteFirst`) + กฎ IRON §59 ข้อ 7 (ต้องให้ CEO ตัดสิน)
- **ตัวเลขที่จริงได้ตั้งแต่วันนี้:** โควตา Claude/Codex/AGY · จำนวนงานต่อ runner · Haiku บน Contabo · JEV บน Contabo ·
  Jules ขั้นต่ำจาก GitHub
- **ตัวเลขที่ยังไม่มี:** Mac กับ winbox (จำนวน session จริงของ Jules, JEV บน Mac, รูป ChatGPT บน winbox) จริงได้เร็วสุด
  19 ต.ค. ถ้าติดตั้ง collector บน Mac ทันในวันศุกร์ 16 ต.ค. ถ้าไม่ทัน รายงานแรกจะเขียน "ไม่มีข้อมูล"

---

## 1. Baseline read today (Tue 13 Oct, about 19:30 BKK)

"This week" covers only 13 Oct 00:00 → about 19:10 BKK, a single partial day.

| Tool | Unit | 6–12 Oct | 13 Oct (partial) | Source (host) | Label |
|---|---|---|---|---|---|
| Claude (the scarce plan) | % of weekly quota used, sum of drops | 104% (hit the cap Mon 12 Oct 08:57; ~32 h at cap until the Tue 17:00 reset) | 8% (since the reset) | `state/reports/quota-history.jsonl` (Contabo) | MEASURED |
| Codex / ChatGPT | % of weekly quota used, sum of drops | 50.0% (window 3–10 Oct peaked at 97%) | 9% | same | MEASURED |
| Codex / ChatGPT | worker tasks (hub) | 17 (16 done, 1 cancelled), all created 10 Oct by CEO order "ให้ ChatGPT เป็นคน Work" | 1 (in review) | hub `tasks.runner='codex'` | MEASURED |
| AGY Gemini bucket | % of weekly quota used | 3.4% | 0% | quota-history | MEASURED |
| AGY Claude bucket (Sonnet 4.6 on Google's plan) | % of weekly quota used | 18.3% | 0% | quota-history | MEASURED |
| AGY | worker tasks (hub) | 5 (all done; Mac, ComfyRunpod) | 0 | hub `tasks.runner='agy'` | MEASURED |
| AGY browse CLI | calls | 0 on Contabo (log: 30 on 1 Oct, 1 on 4 Oct) | 0 | `state/agy-browse.jsonl` (Contabo) | MEASURED (Mac: ไม่มีข้อมูล) |
| Jules | PRs from a Jules session branch (`-<sessionId>`) | 0 in all 7 allowlisted repos + Console + Option; the last was 28 Sep | 0 | GitHub, readable from Contabo | MEASURED, lower bound |
| Jules | sessions per day vs the 300/day plan | ไม่มีข้อมูล | ไม่มีข้อมูล | Jules API (key only on the Mac) | — |
| Haiku 5.5 (Claude Code) | assistant messages | 1 (against Opus 1,934 and Sonnet 273) | 4 (against Opus 1,113 and Sonnet 888) | Contabo transcripts, deduped by `message.id` | MEASURED (Mac: ไม่มีข้อมูล) |
| Haiku 5.5 (paid API) | live jobs | 0: every paid Haiku call is 4.5, flat-priced | 0 | `docs/ops/haiku-5-5-price-cliff-2026-10-13.md` (cto-61a8f144) | MEASURED |
| JEV | `decide()` calls · $ saved | 0 on Contabo (October so far: 2 calls on 1 Oct, $0.0001 spent, $0.092 "saved") | 0 | `state/decisions/2026-10.jsonl` + `tools/decide.py report` | MEASURED calls; saved = ESTIMATE |
| JEV | BL JevEditor episodes scored | none found since 5 Oct (only checkout copies in worktrees) | 0 | `prototypes/bl-*/decisions.jsonl` | MEASURED (Mac: ไม่มีข้อมูล) |
| Claude workers | worker tasks (hub) | 33 (29 done): 24 pinned with an `override:` line (13 of them "in-session"), 4 the router's own pick, 4 security_engineer (an unrouted role), 1 with neither | 6 | hub | MEASURED |

**What the table says.** The org paid for idle capacity while its scarce plan was at the cap:

- For ~32 h (Mon 12 08:57 → Tue 13 17:00), Claude sat at 100% while AGY-Gemini still had ~97% of its week left.
- Per `config/plans.yaml`: Claude $20/month (since 29 Sep), Google $100, OpenAI $20.
- The Google plan is the largest, and its main bucket was ~3% used.

---

## 2. Per tool: unit, source, reach, back-fill, value, gap

### 2.0 Where each source lives, and how the Monday job reaches it

| Source | What it holds (checked today) | Host | Reach |
|---|---|---|---|
| `state/reports/quota-history.jsonl` (written with `state/quota-snapshot.json` by `tools/quota.py`) | One row per bucket every ~10 min since 30 Sep 06:19 UTC: 1,905 rows for each of claude, codex, agy-gemini and agy-claude. Fields: `weekly_remaining`, `daily_remaining`, the reset times, `source`, `error` (≤3 errors per bucket) | Contabo | local file |
| `/opt/claude-usage-monitor/usage.json` | Latest snapshot only (5 h + 7 day utilisation). History comes from the file above | Contabo | local (read via quota.py) |
| Hub `tasks` + `events` (Postgres) | Per task: `role`, `runner`, `runner_model`, `status`, `host`, `owner_cto`, `description` (the `override:` line), `delegate_log` (the `router:` line). Events keep earlier values: 228 `fields_set` rows since 6 Oct | hub | `scripts/hub/org-python.sh` |
| `tools/route.py` | **No log file of its own.** It returns a `Choice`, and `tools/delegate.py:_route_runner` writes the decision onto the task row (`runner`, `runner_model`, `delegate_log`). `route.py --plan developer --size M --host contabo` today ranks agy-gemini first (`ok`) | Contabo/Mac | via the hub rows |
| `tools/forecast.py` `SEED_COSTS` + `state/cost-table.json` | Seed % of weekly quota per job size (claude S3/M8/L20, codex 1/3/8, agy-gemini 0.3/1/3). `cost-table.json` is `{}`: no learned cells yet | Contabo | local |
| Claude Code transcripts | `/root/.claude/projects` (514 MB; 243 files touched since 5 Oct), `/home/sompong/…`, `/home/secretary/…`. Per assistant message: `model` and `usage` | Contabo; Mac has its own | local; the Mac needs a collector |
| `/root/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | One file per Codex session: `token_count` events and `rate_limits.primary.used_percent`. Sessions per day: 3 Oct 1, 4 Oct 10, 5 Oct 23, 10 Oct 23, 13 Oct 4, other days 0 | Contabo; winbox has its own; Codex is not signed in on the Mac | local; winbox needs a collector |
| `tools/jules.py`, `tools/jules_batch.py` | API client + batch runner. Ledger `state/jules/<batch>.jsonl`. **Not on Contabo:** no `state/jules/`, no `~/.config/mooniex/jules.env` | Mac | Mac collector, or the key moved to Infisical (a secret step) |
| GitHub PR branches | Jules opens `<slug>-<sessionId>` branches. 14 such PRs in total, the last on 28 Sep | GitHub | `gh` from Contabo |
| `tools/agy_browse.py` → `state/agy-browse.jsonl` | One line per call (`ts`, `verb`, `port`, `exit`). A worker writes the line under `ORG_ROOT`, which is unset for agy, so its lines land in the worktree's `state/` and leave with the worktree | Contabo / Mac / worktrees | local; the Mac needs a collector |
| `lib/decision_ledger.py` → `state/decisions/YYYY-MM.jsonl` | One row per `decide()`: `site`, `provider`, `cost_usd`, `counterfactual_usd`, `prompt_cliff` (since 482840c6). `decide.py report` sums it | each host | local per host |
| BL JevEditor `decisions.jsonl` + `jev_edit.py score` | Per episode: Jev's choices, `net_saved_usd`, `editor_tokens_per_video_min` (RUNLOG: `prototypes/bl-jev-scoreboard/RUNLOG.md`) | wherever the episode ran | per-episode folder |
| `tools/jev_lab.py balance` → `docs/ops/jev-lab-2026-09-23/balance.jsonl` | OpenRouter key usage daily/weekly/monthly. The key is shared with other users. 5 rows; last 1 Oct: account $144.40 used of $150 credits | Contabo | local (the tool reads the key itself and never prints it) |
| `tools/credit_ledger.py` → `docs/ops/credit-ledger.jsonl` | Generation credits (Flow, Higgsfield, …). 31 rows: 0 in 6–12 Oct, 3 on 13 Oct (Flow). Not one of the five tools; feeds the Google-plan context column only | git (any host) | local |
| `tools/chatgpt_images.py` ledger | One JSON ledger per output folder, on winbox (CDP :9224) | winbox | winbox collector |
| Supabase `webapp_cfo_api_events` | Every ClaudeFlow paid model call, with `model` and the `prompt_cliff` tag (live after the next ClaudeFlow image rebuild) | Supabase | read-only REST, credentials through Infisical |

**Reach design: pull, not push.**
- The Mac's sshd is closed by design (`config/hosts.yaml`: `mac.ssh: null`).
- winbox's mesh key waits on Agents-Core#238.
- So each host runs its own small collector and writes **one hub row per host per week**:
  - `events(task_id NULL, actor='<host>', kind='tool_usage_week', payload=<json>)`.
  - `events.task_id` is nullable, and 32 rows already use NULL, so no schema change is needed.
- The Monday report on Contabo reads those rows. A missing row prints `ไม่มีข้อมูล (<host> ไม่ส่ง)`. It never prints a zero.

### 2.1 Haiku 5.5: "ช่วยเราได้มากขึ้นแค่ไหน"

- **Unit.**
  - Claude Code: assistant messages and output tokens per model, Haiku's share of all Claude-family output.
  - Paid API: calls on `claude-haiku-5-5`, and how many carry `prompt_cliff` = `near` / `over`.
- **Sources.**
  - Transcripts on Contabo (all three homes) and on the Mac. Dedupe by `message.id`: Claude Code rewrites the same
    message several times, so a plain sum double-counts about 2× (measured, jev scoreboard RUNLOG).
  - `webapp_cfo_api_events` and the `decide()` ledgers.
- **Back-fill.**
  - Transcripts: yes, while they are on disk. Claude Code prunes old transcripts, so the weekly collector must run
    every week.
  - CFO events and ledgers: yes.
- **Value metric.**
  - Claude-quota share moved to Haiku (ESTIMATE: output tokens weighted by API list price, because the subscription
    does not publish per-model weights).
  - Paid $: Haiku 5.5 against Sonnet 5.5 for the same request, on the ≤100k card (the cliff rule in ADR 0009
    addendum 2026-10-13 and `CFO_Rules_Finance` principle 6).
- **Gap and job to move this week: none.**
  - The 11 Oct trial failed on the two jobs it tested: note drafting 0.66 and report summaries 0.72 of Sonnet, against
    a 0.90 bar.
  - No other job has been tested.
  - Moving a job to Haiku needs a new trial with the CEO's approval. The report tracks the number so growth shows.
  - The one live use: zero-cost token counting with `claude -p --model claude-haiku-5-5` (cto-61a8f144).
- **Real from:** Contabo today (both weeks). Mac from the Mac collector (§3.2).

### 2.2 Jules: "ใช้งานบ่อยแค่ไหน"

- **Unit:** sessions created per Bangkok day, against the plan's 300/day (`CTO_Knowledge_Jules`, "Jules in Ultra").
  Outcome per session: PR opened, merged, closed, or no PR.
- **Sources:**
  - Jules API `GET /v1alpha/sessions` (`createTime`, `state`): free, account-level.
  - The `state/jules/*.jsonl` ledgers.
  - GitHub PR branches, as a lower bound readable from Contabo.
- **Reach:**
  - The key is only on the Mac, so a Mac collector does the read.
  - Later, when the Infisical migration reaches Agents-Core, the key moves to Infisical and the Contabo job reads it
    through `infisical run`. That is a secret step, not done in this plan.
- **Back-fill:**
  - Yes, through the API session list, if the API keeps September sessions (ไม่มีข้อมูล on retention).
  - The GitHub lower bound works now: 0 since 28 Sep.
- **Value metric:**
  - Share of capacity = sessions ÷ (300 × 7).
  - Claude quota saved = merged Jules PRs × the Claude cost of the same job size (ESTIMATE, §2.6), minus the Claude
    tokens spent reviewing them (MEASURED from the reviewer's transcript when the review task id is known).
- **Gap: 0 of ~2,100 sessions a week (if the plan size is right).**
  - Job to move this week: open issues in the allowlisted repos (`config/jules.yaml`) that fit the
    `CTO_Knowledge_Jules` §1 menu: tests, lint, docs, small fixes.
  - Excluded: secrets, deploys, prod data, files another session changed recently.
  - Pool today (MEASURED): Agents-Core 17, ClaudeFlow 14 and WebApp 3 open issues.
  - Owner: the Contabo CTO on duty. Target: ≥10 sessions by Mon 19 Oct.
- **Real from:** the GitHub lower bound today. The session count from the Mac collector (19 Oct at the earliest).

### 2.3 AGY (Antigravity): "ใช้เต็มประสิทธิภาพไหม"

- **Unit:**
  - % of each weekly bucket used (agy-gemini, agy-claude).
  - Worker tasks with `runner='agy'`.
  - `agy_browse` calls.
- **Sources:** quota-history (both weeks are complete), the hub, and the agy-browse logs.
  - The quota read is `agy -p /usage` on Contabo.
  - Treated as account-level. ASSUMED: verify once by reading `/usage` on the Mac in the same minute.
- **Back-fill:** quota and tasks yes. Browse calls only partly: worktree copies are lost.
  - Fix in the build: the audit line also writes a hub event.
- **Value metric:**
  - Bucket used % and idle %.
  - Claude quota saved by agy tasks (§2.6).
  - $ per used %: plan $ ÷ used % (ESTIMATE: the Google plan may cover more than AGY, see §7 Q2).
- **Gap: the largest one.**
  - Gemini bucket 3.4% used; the agy-claude bucket (Sonnet 4.6, Claude-grade, billed to Google) 18.3%.
  - The router already ranks agy-gemini first for `developer`, and Contabo lists agy in `runners`.
  - Why it idled anyway (MEASURED):
    - 24 developer tasks were pinned to Claude with an `override:` line.
    - The 17 Codex tasks were pinned by CEO order.
    - Only 11 tasks crossed the router. It picked agy 6 times, and 4 of those 6 were moved back to Claude by hand:
      - one agy run died on a permission prompt;
      - three needed Python plus a paid API through `infisical run`, which agy cannot do.
  - Jobs to move this week:
    - every `developer` task without a §59 Claude reason: runner left empty, so the router picks agy;
    - read-only browse jobs: through `agy_browse` (§60 / #188);
    - text roles that need Claude quality but no Claude-only tool: to the agy-claude bucket, after an A/B (§4 M5).
- **Real from:** today.

### 2.4 ChatGPT / Codex: "เอามาใช้งาน ORG เพิ่มไหม"

- **Unit:**
  - Codex worker tasks.
  - Codex CLI sessions and tokens.
  - Weekly % used.
  - ChatGPT image-runner images (ledger rows on winbox).
  - ChatGPT web chat use: ไม่มีข้อมูล (no log exists; nothing to build).
- **Sources:** the hub, rollout files on Contabo (MEASURED) and winbox (collector), quota-history, and the image-runner
  ledgers on winbox.
- **Back-fill:** yes for tasks, rollouts and quota. Images: only if the ledger folders still exist.
- **Value metric:**
  - Claude quota saved (§2.6).
  - Codex tokens per task (MEASURED from rollouts).
  - Redo rate: reopens, cancellations.
- **Gap: none. Codex is the one outside runner used close to full.**
  - Window 3–10 Oct peaked at 97%; 50% was used inside 6–12 Oct.
  - The growth came from one CEO order on 10 Oct, not from the router.
  - Watch item: on 13 Oct 11:09 UTC the Codex reset date moved from 17 Oct to 20 Oct while 31% was already used.
    Cause: ไม่มีข้อมูล. The report prints window dates next to the %.
- **Real from:** today (Contabo). winbox rollouts and images from the winbox collector.

### 2.5 JEV: "ช่วยประหยัดไปได้เท่าไหร่"

- **Unit:**
  - `decide()` calls per site and provider.
  - $ spent, $ counterfactual, $ saved.
  - BL episodes scored with `jev_edit.py score`.
- **Sources:** the `state/decisions/YYYY-MM.jsonl` files on each host (`decide.py report` already prints `saved_usd`),
  BL `decisions.jsonl`, and `jev_lab.py balance` for the OpenRouter credit level.
- **Back-fill:**
  - Ledgers: yes.
  - OpenRouter weekly usage: no. The `/key` endpoint gives only the current day, week and month, and the key is
    shared. Logging starts at the first Monday run.
- **Value metric:**
  - Σ(`counterfactual_usd` − `cost_usd`): an ESTIMATE, priced by each site's `config/decisions/*.yaml`.
  - Per BL episode: `net_saved_usd` and editor tokens per video minute (MEASURED).
- **Gap: JEV is almost unused.**
  - 10 decision sites are wired (`decide.py sites`).
  - Its paid rung is off by default: `DECIDE_PROVIDER` unset means rules only, and Jev is never asked (JevEditor field
    note 2026-10-01).
  - Job to move this week:
    - the CTO lists which wired sites run with `DECIDE_PROVIDER` unset;
    - the CMO's next BL episode runs `jev_edit.py plan` with Jev on.
  - Money flag: OpenRouter credits stood at $144.40 used of $150 on 1 Oct. If they run out, every Jev site falls back
    to rules. A top-up is the CEO's call (§7 Q3).
- **Real from:** Contabo today. Mac/winbox ledgers from the collectors.

### 2.6 One shared value metric: Claude quota saved

The CEO's question is "คุ้มไหม", and in this org's currency that is Claude weekly quota, because Claude is the plan
at the cap.

1. **Week 1 (19 Oct): seed estimate, labelled.**
   - For each outside task done in the week, add the Claude seed cost of its size (`forecast.infer_size` +
     `SEED_COSTS['claude']`: S 3%, M 8%, L 20%).
   - Last week this gives codex 236% + agy 76%. **The seed overstates, and the report says so.**
   - Evidence: the same seeds put Claude's own 29 done tasks at 419%, while the whole account (C-levels included)
     used 104%. That is ≥4× too high.
2. **From week 2: calibrated.**
   - Claude-worker tokens per task come from the worker transcripts (MEASURED, deduped).
   - Tokens per 1% of weekly quota = Claude transcript tokens in the week (all hosts, weighted by list price) ÷ the
     measured % used.
   - Saved % = the median Claude-worker tokens for that size × outside tasks ÷ tokens-per-%. Still an ESTIMATE, now
     anchored on measured tokens.
3. **$ view (ESTIMATE):** plan $ per week (`plans.yaml` × 12 / 52) ÷ used %. This is the "ราคาต่อ % ที่ใช้จริง"
   column. It shows an idle plan as expensive.
4. **Failures and redos (MEASURED, hub)** per runner: `cancelled`, `failed`, `stalled`, and reopens (a
   `status_review` followed by `status_in_progress` or `status_pending`, or "CTO Feedback (iter N)").
   - Last week: codex 16 done / 1 cancelled; agy 5 / 0; claude 29 done / 1 cancelled / 3 in review.

---

## 3. The Monday report (deliverables for A)

### 3.1 One command: `tools/tool_value.py`

```
bash scripts/hub/org-python.sh tools/tool_value.py collect [--host <self>] [--week <start-date>]   # read-only on sources; writes ONE hub event row
bash scripts/hub/org-python.sh tools/tool_value.py report  [--week <start-date>] [--dry-run]       # reads hub rows + Contabo sources; writes the report
```

- **`collect`** reads only the sources of §2.0 that exist on the host it runs on, and writes one
  `tool_usage_week` event:
  - a count per tool;
  - token sums per model;
  - quota drops;
  - a `missing: [...]` list for every source it could not read.
- **`report`**:
  - Builds the comparison table (previous week against current week, the delta, and a label per cell).
  - Builds the idle list (a tool below its floor, §4 M3).
  - Builds a Thai summary from a **fixed template**: no model call, 0 tokens.
  - Writes `state/reports/tool-value/<week>.md` and `.json` (gitignored; Agents-Core is public).
  - Sends the Thai summary + table as a hub letter to `coo`. SomPong relays it to the CEO.
- **Rules it must keep:**
  - Read-only on every source.
  - No paid call: the OpenRouter `/key` read and the Jules session list are free reads.
  - A key is read by the tool itself and never printed.
  - Bounded memory: it streams transcripts line by line and keeps only a set of message ids.
  - Never a zero for a missing source.
- **The week.**
  - Recurring: Mon 00:00 → Sun 24:00 BKK, reported the next Monday at 08:00.
  - **The first report (19 Oct) is the exception, cut to the CEO's ranges:**
    - Tue 6 → Mon 12 Oct (complete);
    - Tue 13 → Mon 19 Oct 07:00 (6 d 7 h).
    - Every count also shows a per-day rate, so the partial week compares fairly.
  - Quota % uses "sum of drops between consecutive samples inside the week". That handles resets in mid-week (Claude
    resets Tue 17:00 BKK; Codex and AGY windows roll).

### 3.2 Collectors per host

| Host | Runs | Reads | Earliest real |
|---|---|---|---|
| Contabo | systemd timer, Mon 07:30 BKK (`collect`), then 08:00 (`report`) | quota-history, hub, the 3 transcript homes, Codex rollouts, decisions, agy-browse, credit ledger, `jev_lab balance`, GitHub Jules branches | 19 Oct (built 14–16 Oct) |
| Mac | launchd, Mon 07:30 BKK; writes to the hub over the tailnet (the Mac already reaches the hub) | Mac transcripts, `state/jules/*.jsonl` + the Jules session list, agy-browse, decisions | 19 Oct **if** a Mac CTO session installs it by Fri 16 Oct; otherwise 26 Oct |
| winbox | Task Scheduler, in the desktop session, Mon 07:30 BKK | Codex rollouts, ChatGPT image ledgers, decisions | ไม่มีข้อมูล for 19 Oct. It needs a winbox session; 26 Oct at the earliest |

### 3.3 Schedule on Contabo

- Use `OnCalendar=Mon *-*-* 08:00:00 Asia/Bangkok`. systemd accepts a time zone in the calendar spec, which removes
  the CEST +5 h / CET +6 h arithmetic before and after the 25 Oct clock change.
- `Type=oneshot` in its own unit, with `MemoryMax=300M` and `Nice=10`.
- Before installing, run the tmux cgroup check in `CLAUDE.md`. The unit is new, so it holds no tmux pane, but the
  check is the rule.
- `Persistent=true`, so a run missed while the box was down fires at boot.

### 3.4 What the CEO receives (shape)

```
รายงานความคุ้มค่าเครื่องมือ — สัปดาห์ 13–19 ต.ค. เทียบ 6–12 ต.ค.
1. Claude: ใช้ X% (ก่อนหน้า 104%) · ชนเพดาน N ชม.
2. AGY: Gemini X% / Claude-bucket Y% · ต่ำกว่าเกณฑ์ → เจ้าของ <lane> ย้าย <งาน>
3. Jules: N session (ก่อนหน้า 0) จาก 2,100 · merge M
4. Codex/ChatGPT: N งาน · X% โควตา
5. JEV: N ครั้ง · ประหยัด $X (ประมาณการ) · Haiku: N ข้อความ
[numbers table, every cell labelled วัดจริง / ประมาณการ / ไม่มีข้อมูล]
```

### 3.5 Token cost of A

- Collect + report: **0 model tokens** (pure Python, template summary).
- SomPong's relay: one turn of its own.
- One-off build: §6.

---

## 4. Enforcement (B): a system, not a habit

### 4.1 Already enforced today (in code)

| Piece | Where | What it does |
|---|---|---|
| Router call on every delegate | `tools/delegate.py:_route_runner` → `tools/route.py:pick_runner` | For roles in `config/plans.yaml role_classes` (`developer` → dev_general, `tester` → dev_shell), and `browser_operator` when the brief uses `tools/agy_browse.py` with a CDP URL, picks the runner by weekly quota, then daily, then skill, then the CEO's order, and writes `router: …` to `delegate_log`. |
| Refusal of a hand pin without a reason | `tools/route.py:check_override`, called first in `_route_runner` (PermissionError since 2026-09-30) | A routed-role task with `model_hint` set, or `runner` set while `runner_model` is NULL, is refused unless its first description block has `override: <reason>`. |
| Rules | IRON §59 (card + rules 1–6), `CXO_Protocol_DevSpawn` §0 | The reasons that may force Claude: review/repair of another agent's code, security, silent-wrong-answer risk, a Claude-only tool, a CEO order, an A/B test, a box-bound job. |

### 4.2 What still leaks (MEASURED this week and last)

1. **Any text passes as a reason.**
   - `check_override` only checks that something follows `override:`.
   - Last week's reasons included "in-session Agent run by CTO …" (13 tasks), which is not on the §59 list.
2. **Claude work that never becomes a task.**
   - A C-level's own `Agent` tool calls (in-session Sonnet/Opus subagents) never reach `delegate_task`.
   - On Contabo this week, Sonnet already has 888 assistant messages in one partial day, against 273 in all of last
     week. Most are in-session agents (rows say "in-session Sonnet Agent" when anyone logs them at all).
3. **The C-level sessions themselves.**
   - Opus produced 1.50 M output tokens on Contabo last week, against Sonnet's 0.37 M.
   - SomPong's count (CEO order 13 Oct): 87% of 11 Oct's usage came from sessions open 8 h or more. No router touches
     this.
   - The lever is session discipline (one job per session, `/session-open`), not routing.
4. **A hand pin to a non-Claude runner bypasses the router.**
   - The router writes `runner_model=''` for codex, so a hand-set `runner='codex', runner_model=''` looks routed.
   - Harmless for Claude quota, but it skips the CEO's order (agy first). That is part of why AGY idled.
5. **Four of the five tools are not router candidates at all.**
   - `plans.yaml` buckets are claude, codex, agy-gemini and agy-claude.
   - Jules (asynchronous PR), JEV (decisions), Haiku and GLM have no path through the router.
6. **Unrouted worker roles.** These stay on Claude with no reason asked: web_designer, video_editor, data_analyst,
   prompt_engineer, ads_manager, content_strategist, script_writer. browser_operator also stays on Claude unless its
   brief names agy_browse.
7. **No one is told when a plan idles.** Nothing compares spend against use. This plan's report is the first thing
   that does.
8. **The router's shell detector misses some briefs.**
   - 3 of its 6 agy picks last week needed Python plus `infisical run`, and `forecast.needs_shell` did not catch them.
   - They were re-pinned by hand to Claude, not to Codex (dev_shell, the shell-capable outside runner).
   - T3 adds those markers to `needs_shell`, so the router sends such jobs to Codex.

### 4.3 Mechanisms (the proposal)

| # | Mechanism | Kind | Blast radius | How a bypass is detected | Token cost |
|---|---|---|---|---|---|
| M1 | **Delegate gate v2**, in code at the same choke point (`route.check_override`). (a) The reason must start with a code from a closed list: `review`, `security`, `silent-wrong`, `claude-tool`, `ceo-order`, `ab-test`, `box-bound`. "in-session" is not a reason. An in-session run declares its real code. (b) A hand pin to *any* runner needs the line, so CEO-order Codex work is recorded as `ceo-order`. (c) When the task's repo is in `config/jules.yaml` and `forecast.infer_size` says S/M with no secret/deploy words, the refusal message also prints the Jules command; it does not dispatch. | Gate (code) + skill `CXO_Gate_RouteFirst` documenting it | Every `delegate_task` of a routed role, on every host. Failure mode: a refusal the C-level fixes by editing one line. Escape `ORG_ROUTER=off` is kept for repair and logged. | Report lists every Claude-pinned task grouped by reason code; tasks with a `runner` but no `router:` event; delegates while `ORG_ROUTER=off` | 0 model tokens; a refusal adds ~120 tokens to the C-level's context |
| M2 | **Agent-tool hook** (PreToolUse on `Agent`, C-level sessions only, not workers or SomPong). Week 1 (to 19 Oct): **log only**, one hub event per call with session, subagent type, model and prompt length. From 26 Oct, only if the CEO agrees after seeing week 1: a dev-shaped Agent call (general-purpose, writes code) without `route: <task-id>` or `override: <code>` in its first line is refused, with a pointer to `create_task` + `delegate_task`. Explore/Plan/read-only agents are never blocked. | Gate (hook) | Every Agent call in every C-level session. Block mode risks false refusals of legitimate research; that is why week 1 is log-only. | Sidechain (subagent) transcript tokens per session in the report, against hook events; a gap = an unhooked path | 0 model tokens log-only; a refusal adds ~150 tokens |
| M3 | **Floors → owner → dated to-do.** The report flags a tool under its floor. The flag becomes a LungNote to-do with the owning lane, the job to move and a deadline (the next Monday). `/session-open` already surfaces dated to-dos, and `/session-close` refuses 🏁 while one is open, so the loop closes without anyone remembering. Proposed floors (CEO sets them, §7 Q1): metered buckets ≥50% of the weekly quota; Jules ≥10 sessions/week; JEV ≥1 call per wired site per week. | Procedure skill `COO_Procedure_ToolValueWeekly` + the script | One to-do per idle tool per week (≤5). | The next report shows whether the to-do moved the number; an unclosed to-do is visible at every session-open | 0 tokens to create; ~1 short turn per owner to act |
| M4 | **Rules line**: IRON §59 rule 7 + ADR 0009 addendum. "Outside runners first for eligible job types" (list in §5). Without a §59 reason code, an eligible job does not go to a Claude worker. | Rules (CEO ruling) | Every C-level, every lane. | M1 and M2 enforce it; the report measures it | 0 |
| M5 | **Widen routing after evidence.** Add `data_analyst` → dev_shell (codex), and text roles (`script_writer`, `content_strategist`, `prompt_engineer`) → a new class led by `agy:claude-sonnet-4-6` (Claude-grade, billed to Google), each only after a 10-item blind A/B like the Haiku trial. | Config change + A/B | One role at a time. | Report: per-role runner mix | A/B ≈ the Haiku trial's harness, reused; ask before running |

**SomPong's suggestion: accepted with three changes.**

1. The Gate already exists in code, so M1 extends the existing choke point rather than adding a parallel gate.
2. M2 covers the leak SomPong's version misses (in-session Agents), starting log-only.
3. The weekly report is a **Procedure, not a Workflow.** In `ALL_Protocol_SkillAuthor` §1, a Workflow "starts from
   nothing and ends at a public release". A weekly report is one bounded task with one output and a script, which is
   the Procedure test.

### 4.4 Skill kinds (7-kind table, `ALL_Protocol_SkillAuthor` §1)

| Skill | Kind | Owner | Holds |
|---|---|---|---|
| `COO_Procedure_ToolValueWeekly` (new) | Procedure | COO (runs and relays); the CTO builds and repairs the script | Input (the week), output (the report), the script, how to verify a number, the floors, how a flag becomes a to-do |
| `CXO_Gate_RouteFirst` (new) | Gate | CTO | The checks M1/M2 run, the reason codes, the verdict block, the escape hatch and its logging. The skill documents the gate; the code enforces it |
| IRON §59 rule 7 + ADR 0009 addendum | Rules (in IRON, not a skill) | CTO drafts, CEO rules | §5's list |
| `CTO_Knowledge_Jules`, `ALL_Knowledge_Jev` | Knowledge (update) | CTO | A field note with the measured weekly use; no rule change from one sighting (ADR 0026) |

---

## 5. Eligible job types → first runner (the draft for the Rules line)

| Job type | First runner | Then | Never outside (stays on Claude) |
|---|---|---|---|
| Code change in an allowlisted repo, size S/M, no secrets, deploy or prod data | Jules (asynchronous PR) | agy-gemini → codex via the router | — |
| Any other developer task | router (agy-gemini → agy-claude → codex → claude) | — | the §59 reasons |
| Task that must run shell (tests, psql, docker, systemctl) | codex (dev_shell) | claude | — |
| Read-only browsing / pulling numbers off a page | `agy_browse` (browser_agy) | Claude browser_operator with a reason | logins (§60 relay) |
| Typed decision with fixed options (route, classify, page state) | JEV via `decide()` (`DECIDE_PROVIDER=jev`) | rules | free text |
| Image plate through ChatGPT | `tools/chatgpt_images.py` on winbox | — | — |
| Drafting notes, report summaries | Sonnet (Haiku failed the trial on both) | — | — |
| Review/repair of another agent's code, security, silent-wrong-answer risk, Claude-only tools, C-level planning and merging | — | — | Claude |

---

## 6. Build plan to Mon 19 Oct

These are build tasks under the supervising CTO (#e106b78b). Code decisions are the CTO's call; the rule line and the
floors are the CEO's. Contabo RAM rule: one worker at a time, and `free -m` must show ≥1 GB available first.
Every task leaves `runner` empty so the router picks, and this plan's own build uses the outside runners it argues for.

| # | Task | Touches | Depends | By |
|---|---|---|---|---|
| T1 | `tools/tool_value.py collect/report` for the Contabo sources + tests with fixture files (no live reads in tests) | `tools/tool_value.py`, `tests/test_tool_value.py` | — | Wed 14 Oct |
| T2 | systemd units (collect 07:30, report 08:00, `Asia/Bangkok`), installed after the tmux cgroup check; a dry run that prints the 6–12 Oct table | `deploy/tool-value.*` | T1 | Thu 15 Oct |
| T3 | `check_override` v2 (M1 a/b/c) + the `needs_shell` markers (§4.2 item 8) + tests; `CXO_Gate_RouteFirst` | `tools/route.py`, `tools/forecast.py`, `tests/test_route*.py`, `tests/test_forecast*.py`, `.claude/skills/CXO_Gate_RouteFirst/` | — (serial with T1 on RAM only) | Thu 15 Oct |
| T4 | Agent-tool hook, log-only (M2) | `scripts/hook-agent-route-log.py`, `.claude/settings.json` | — | Fri 16 Oct |
| T5 | Mac collector (launchd) incl. the Jules session list; needs a Mac CTO session | `scripts/mac/tool-value-collect.*` | T1 | Fri 16 Oct |
| T6 | `COO_Procedure_ToolValueWeekly` + agy_browse hub event (fix the worktree-only audit) | `.claude/skills/COO_Procedure_ToolValueWeekly/`, `tools/agy_browse.py` | T1 | Fri 16 Oct |
| T7 | Full dry run Sun 18 Oct; real run Mon 19 Oct 08:00 BKK → SomPong → CEO | — | T1–T2 (T5 optional) | Mon 19 Oct |
| T8 | IRON §59 rule 7 + ADR 0009 addendum, drafted from §5 | Agents-Rules | the CEO's ruling at the 19 Oct report | after 19 Oct |
| T9 | winbox collector (Codex rollouts, ChatGPT image ledgers) | `windows/tool-value-collect.ps1` | T1, a winbox session | 26 Oct |

**Earliest date each metric is real**

| Metric | Real from |
|---|---|
| Claude, Codex and AGY quota %; tasks per runner; redo rates | today, both weeks |
| Haiku (Contabo), JEV (Contabo), agy_browse (Contabo), Jules lower bound (GitHub) | today |
| Claude quota saved | 19 Oct as a seed ESTIMATE; 26 Oct calibrated |
| Jules sessions/day, Mac Haiku/JEV/agy_browse | 19 Oct if T5 lands by 16 Oct, otherwise 26 Oct |
| winbox Codex, ChatGPT images | 26 Oct at the earliest |
| OpenRouter weekly credit | from the first Monday run (no back-fill) |

---

## 7. Questions for the CEO (asked once, in the 19 Oct report)

1. **Floors.** ≥50% of the weekly quota for AGY and Codex, ≥10 Jules sessions a week, ≥1 JEV call per wired site?
   (SomPong proposed 50%.)
2. **Which Google plan we pay for.** `config/plans.yaml` says Google $100/month; `CTO_Knowledge_Jules` says Jules runs
   on Google AI Ultra (300 sessions/day). The Jules capacity and the "$ per used %" column depend on it. CFO to
   confirm.
3. **OpenRouter credits.** $144.40 used of $150 on 1 Oct (MEASURED then, not since). JEV and the Haiku fallback stop
   when they run out. A top-up is money.
4. **The Rules line (§5) and M2 block mode.** Both wait for the CEO to see week 1's numbers.

Out of scope here:
- GLM (ADR 0009 tier 3, BytePlus $10/month) is not in `plans.yaml`, so whether it is still paid is ไม่มีข้อมูล. CFO.
- The Codex reset-date jump on 13 Oct (§2.4) is a watch item, not a question.
