---
name: CMO_Workflow_MimiPage_Weekly
kind: workflow
owner: CMO
description: >-
  WORKFLOW — Weekly rhythm of the Mimi page «บ้านนี้มีมีมี่»: 3 video episodes Fri/Sat/Sun and one poster post Mon–Thu, all at 19:30, prepared and scheduled ahead, then supervised. Trigger on /CMO_Workflow_MimiPage_Weekly, "มีมี่ สัปดาห์นี้", "ตารางโพสต์มีมี่", "คุมงานเพจมีมี่". Not for story rules, the engine, QC or the cut recipe.
created_by: agent
author: {role: cmo, date: "2026-10-02"}
audience: [cmo, script_writer, content_strategist, browser_operator, video_editor]
---

# Mimi page — the weekly workflow

Written from EP1 (posted Fri 2 Oct 2026) and EP2 (shot, cut and scheduled Fri 2 Oct for Sat 3 Oct), after the CEO's
rhythm ruling of 2026-10-02 (his words, verbatim, typos kept):

> "เราจะมี อาทิตย์ละ 3 EP ที่เป้น Video ศุกร์ เสาร์ อาทิตย์ / และ โพส ถึงแฟน เพจ และ Update การทำงานของเรา จะมี จันทร์ - พฤหัส
> วันละ 1 ครั้งตามเวลา คุณออกแบบ โพส + โปสเตอร์ ไว้ / ทำทั้งหมด ให้เพียงพอ สำหรับ 1 สัปดาแล้วตั้งงเลา ตัวเองมาคุมงาน Automation"

This file holds the ORDER, the GATE that ends each step and the POINTER to the skill or tool that owns the rule.
The story is `CMO_Standard_Story_FamilyDogSeries`; the shoot is `CMO_Knowledge_Flow_Omni1.1`; QC is
`CMO_Gate_Flow_Omni1.1_FilmQC`; the cut is `CMO_Workflow_ShortFilm` Step 9; Facebook driving is
`BROWSER_OPERATOR_Protocol_Playbook`. Read the owner before doing a step.

## 1 · The week (Thai time; one slot, 19:30, every day)

| Day | 19:30 slot | Kind | Credits |
|---|---|---|---|
| Fri · Sat · Sun | **Video episode** (Reel, 3:00 incl. piano bed, title card, end card, cover) | 3 per week | ~330 each (cap set per episode, §4) |
| Mon | **Fan post + poster** — the week opens: the schedule poster «ศุก เสาร์ อาทิตย์ 19:30» or a «ถามแฟนเพจ» post | fan | 0 |
| Tue | **Work-update post + poster** — behind the scenes of the next episode (what we are shooting, a real frame, a number) | update | 0 |
| Wed | **Fan post + poster** — ask the fans about their own dogs, or a Mimi fact, or a still from last week | fan | 0 |
| Thu | **Teaser post + poster** — a still from Friday's episode, one spoken line, «พรุ่งนี้ 19:30» | teaser | 0 |

- 19:30 is the one daily appointment, so the page becomes a habit; the cat page's measured windows are 05:00 and
  16:00–20:30 (`docs/plans/khaoniao-week-workflow-2026-10-01.md` §1) and 19:30 sits inside them. Test 05:00 only in a later week.
- Posts are shaped like the cat page's ordinary posts: line one is the hook, the AI label closes the caption, ≤5 hashtags,
  no links (a link goes in the first comment), never ask for likes or shares.
- **The weekly calendar lives in `docs/plans/mimi-weekly-calendar.md`** (one row per slot: kind, title, files, status,
  scheduled yes/no, first comment, numbers). Update the row the same turn the state changes.
- Contabo's clock is CEST: **cron hour = Thai hour − 5** (`TZ=Asia/Bangkok date` first, always).

## The steps

One episode's day is **D** (its post day); lead times are the minimum. The order, tools, owner skills and gates of the
nodes are in `flow.yaml`; this section is the how and the traps.

### Step 1 · Real family fact [node: fact]
D−6. Ask the CEO for a real story from the house; the same turn he tells one it becomes a dated row in the story bible §7. No fact
by D−5 → offer him two [แต่ง] concepts built from existing facts and let him pick; never write an invented fact down as true.

### Step 2 · Script and sheet [node: script]
D−5. Script v1 (`docs/scripts/khaoniao-epN-SCRIPT-v1.md`): Structure gate, the 3-second rule, one question in four places,
plant → payoff table, [จริง]/[แต่ง] split, a credits line. Then the shot data file, the built sheet and the lint
(`tools/shotsheet_lint.py` PASS, 100 % spoken). Reuse the plates; a new plate is its own one-off task. Commit all three files.

### Step 3 · Script and credit OK [node: approve]
D−4. **One message to the CEO for the whole batch of episodes**: the scripts, the exact credits per episode (test + shoot + reshoot cap),
the live balance, and what stays in reserve. Wait for his OK in chat; his OK for a total covers several episodes, a second round on an
episode needs a new one (§4).

### Step 4 · Flow shoot [node: shoot]
D−3/D−2 on winbox, one render job at a time (`free -m` on Contabo first). Dry-run is free; a paid test only for what Flow has never
done; then the full shoot with `--credit-cap`. A failed download stall is uncharged: `pull` first, one re-fire second. Ledger row per spend.

### Step 5 · Film QC [node: qc]
D−2. Transcript vs script, burned-text scan, contact sheet by eye (one-line reason before each image read). Reshoot ≤3 shots with a
one-line reason each; framing hides wardrobe, so a reshoot can lose garments: keep the original if the reshoot is worse.

### Step 6 · Cut, music, cover [node: cut]
D−2/D−1. First shot trimmed, title card across 1:00, end card, piano bed, cover (`cover.html ?sub=…` on winbox Chrome), 540p preview.
Recipe is `CMO_Workflow_ShortFilm` Step 9. The end card's teaser must name the next episode's day correctly (§5).

### Step 7 · Mon-Thu posters [node: posters]
Once a week, before Sunday night. Four posters and captions in one winbox render pass (§3), contact sheet looked at once, fixed by number.

### Step 8 · CEO watches 540p [node: preview]
D−1 by 18:00. Send the 540p file and the poster contact sheet; ask one question: OK, or what to change. The same message asks his go for the
final «กำหนดเวลา» press (the permission layer refuses it otherwise). No OK by D−1 22:00 → do not schedule; use the fallback (§7).

### Step 9 · Schedule on the Page [node: schedule]
D−1. Reel from the Page profile (not Business Suite) with `tools/fb_cdp_do.py` on winbox :9281, AI label ON, date by the calendar popup
(`clickvis` the day number), time by `fill` + Tab. Read the Manage posts list back: «กำหนดเวลาแล้ว». One of my own hung tabs times out
the attach: check `tools/flow_tabs_health.py --port 9281` first.

### Step 10 · First comments armed [node: comment]
D−1. One one-shot cron per episode at D 19:33 (§5) and one at D 19:45 for the live check; `CronList` shows them. Re-arm at every session
start; recurring jobs die after 7 days.

### Step 11 · Live check and numbers [node: watch]
D 19:35 and onward (§6). Done when the post is public, the first comment is up, the calendar row and the ledger row are written.

## 3 · Monday–Thursday posts (zero credits, designed ahead)

- One post = one **poster** (1080×1350, 4:5) + caption + (Thursday only) a first-comment line. Poster lettering is set in real Thai fonts
  by HTML → headless Chrome on winbox (`docs/reports/khaoniao-family-style/cover/`), with the real Itim font, the L3 logo mark
  (`page-art/logo/logo-3-mark.png`) and **real episode frames** — never an image model (Thai text garbles; brand rule).
- Posters per week: Monday schedule/«ถามแฟนเพจ», Tuesday update, Wednesday fan, Thursday teaser. Build all four in one winbox render
  pass; look at the contact sheet once; fix by number.
- **Update posts say true things about our work**: the real number of shots done, the real credit cost bracket (never the balance),
  a real frame. Never fake progress; a post that cannot be true tonight moves to the next slot.
- A fan post asks one concrete question about the fan's own dog; replies go out as the Page in the page's voice, the CEO's rules
  for tone and language (his name, the commenter's language, no crude words) apply.
- Privacy on every poster and caption: no gatepost house-number plate, no framed picture on the shelf, no real-person faces other than the cartoon cast.
- Zero-credit bank for fallback days: stills and covers of finished episodes, clips from `Assets/Agents/Core/khaoniao-family/ep*/clips`,
  the schedule poster, a «ขอบคุณ» poster. Keep the bank list in the calendar file.

## 4 · Credits and approvals

- Flow credits are the CEO's money: **state the exact number (test + shoot + reshoot cap) and the live balance, and wait for his OK** before the first
  paid job of a batch. One OK may cover several episodes if he names the total. A second round on the same episode needs a new OK.
- Measured base: 720p/10 s = 15 cr/shot; 360p/8 s = 6 cr/shot; a failed download stall is uncharged; EP2 = 333 charged
  (test 18 + 255 + re-fire 15 + reshoot 45) + 5 Flow Music. Plan **≤330 per episode**; 3 episodes = 990.
- The pool is shared with ILAG and is not carried over: ask the CEO the reset day once (open question) and keep ≥250 in reserve.
- Every spend is a ledger row the same turn: `bash scripts/hub/org-python.sh -m tools.credit_ledger add --who <session> --engine flow|flow-music --credits N --channel "บ้านนี้มีมีมี่" --purpose … --kind test|production|reshoot --before B --after A`, then commit `docs/ops/credit-ledger.jsonl`.
- Pushing the repo publishes it (the repo is public): never push without the CEO.
- Drive: the folder `ALL DRAFT/FB: บ้านนี้มีมีมี่/EP<N>/` is created only after he approves the path (`CXO_Rules_GDrive_Filing` rule 3).

## 5 · The first comment (it depends on the calendar)

Every episode gets a first comment in the page's voice at 19:33 (3 minutes after the Reel goes live): thanks, the AI label wording,
and the **promise of the next episode computed from the calendar, never copied from the last one**:

| Episode day | Next episode | Wording |
|---|---|---|
| Friday | Saturday | «พรุ่งนี้ 19:30 มีตอนใหม่» |
| Saturday | Sunday | «พรุ่งนี้ 19:30 มีตอนใหม่» |
| Sunday | next Friday | «ศุกร์นี้ 19:30 มีตอนใหม่ ระหว่างนี้จันทร์–พฤหัสมีโพสต์ใหม่ทุกวัน 19:30» |

- Thursday's teaser says «พรุ่งนี้ 19:30»; Monday–Wednesday posts say «ศุกร์นี้».
- **Mechanism today = a session-only one-shot cron** (`CronCreate recurring:false`, Contabo local time = Thai − 5 h). It dies with the session
  and `durable` has no effect; recurring jobs expire after 7 days. So: re-arm at every session start (`CronList` first), and every Friday
  re-create the week's crons. **The durable fix is a Graph API path** (Page token → scheduled posts + timed comments from a Contabo timer,
  token in Infisical) — it needs the CEO's Facebook app/token step; propose it, do not start it unasked (`project_meta_page_api_plan`).
- The comment is posted as the **Page**, not the personal profile: the composer's identity name must read «บ้านนี้มีมีมี่»; if it shows a personal name,
  stop and hand the CEO the text (`tools/fb_reel_post.py` exit 7 logic).

## 6 · Supervision loop (the CMO "คุมงาน")

| When | Check | If it fails |
|---|---|---|
| D 19:35 | The post is live on the Page (Manage posts shows it published; open the permalink); the first comment is posted | Not live → open the composer, look why (login wall, wrong identity, schedule lost); post by hand as the CEO's fallback and tell him in one line |
| D 21:30 | Replies: answer the real ones, ignore spam, note any new family fact a fan or the CEO gives (→ Family log) | — |
| D+1 08:00 | Numbers: views, 3-second hold if shown, comments; one row in the calendar file (**MEASURED**, never estimates dressed as data) | — |
| Every Sunday night | Next week is complete: 3 episodes scheduled or in the pipeline with dates, 4 posters + captions scheduled, crons armed, credit balance vs plan | List the gap to the CEO with the cheapest fix |
| Every Sunday night | **Weekly report to the CEO** (≤12 lines, table): posted vs planned, numbers per post, credits used/left, what is blocked on him | — |

## 7 · When an episode is late

Never leave a slot silently empty and never post an episode that failed QC. If step 8 or QC is not done by D−1 22:00, move the post to the
fallback in this order: (1) the day's zero-credit poster from the bank, (2) a «วันนี้พักผ่อน ตอนใหม่พรุ่งนี้» note only if the CEO agrees,
(3) shift the whole row and tell him in one line why. Update the first-comment promise of the previous episode if the date moved
(edit the comment by hand).

## 8 · What every weekly report ends with

The CMO report format applies (answer first, ≤12 lines, the `## Skill learning` block). Add the calendar row link and the credit line:
`balance → after plan`.

## Field notes
- 2026-10-02 [MISSING] §5 — the EP2 first comment promises «พรุ่งนี้ 19:30 มีตอนใหม่»; written on the old one-clip-a-day assumption it only stays true because EP3 falls on Sunday 4 Oct. The Sunday episode's comment must NOT say «พรุ่งนี้» (next is Friday) · evidence: CEO rhythm ruling 2026-10-02, EP2 comment text · status: pending
- 2026-10-02 [MISSING] §5 — `CronCreate` is session-only (`durable` has no effect, recurring jobs expire after 7 days), so the first-comment automation dies with the CMO session and with every compaction restart; the durable path is the Graph API plan, not built · evidence: CronCreate tool description, cron d5a74e3e · status: pending
