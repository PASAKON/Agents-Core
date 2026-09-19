# Banchi Act 1 — batch 2 shoot (shots 1, 6, 18, 19, 20, 21)

Project: `flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39`
Model: Omni 1.1 Flash · องค์ประกอบ · 9:16 · 720p · x1 throughout.

## Per-shot table

| shot | duration set | chips (ATTACH order) | live estimate | submitted | downloaded | filename |
|---|---|---|---|---|---|---|
| 1 | 8s | 1) lung_somchai→REF_0 · 2) side_wall→REF_1 | 12 cr | yes (attempt 1) | **no** | — |
| 1 (retry) | 8s | 1) lung_somchai→REF_0 · 2) side_wall→REF_1 | 12 cr | yes (attempt 2) | **no** | — |
| 6 | 8s | 1) lung_somchai→REF_0 · 2) upstairs_bedroom→REF_1 | 12 cr | yes (attempt 1) | no (failed) | — |
| 6 (retry) | 8s | 1) lung_somchai→REF_0 · 2) upstairs_bedroom→REF_1 | 12 cr | yes (attempt 2) | **yes** | Shopkeeper_speaking_in_noodle_shop_20260919104227.mp4 |
| 18 | 8s | 1) lung_somchai→REF_0 · 2) nong_daeng→REF_1 · 3) noodle_shop→REF_2 | 12 cr | yes | yes | ดาวน์โหลด (3).zip |
| 19 | 4s | 1) nong_daeng→REF_0 · 2) staircase→REF_1 | 7 cr | yes | yes | ดาวน์โหลด (2).zip |
| 20 | 10s | 1) nong_daeng→REF_0 · 2) grandma_pranom→REF_1 · 3) upstairs_bedroom→REF_2 | 15 cr | yes | yes | ดาวน์โหลด (1).zip |
| 21 | 8s | 1) nong_daeng→REF_0 · 2) grandma_pranom→REF_1 · 3) upstairs_bedroom→REF_2 | 12 cr | yes | yes | ดาวน์โหลด.zip |

**Error text (shot 1, both attempts; shot 6, first attempt), verbatim:**
```
ล้มเหลว
การสร้างนี้อาจละเมิดนโยบายของเรา โปรดลองใช้พรอมต์อื่นหรือส่งความคิดเห็น
ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้
```
("Failed — this generation may violate our policy, try a different prompt or send feedback. The system did not charge you for this generation.") All three failures were refunded — confirmed 0 credits deducted for any of them.

## Credits

Only successful generations were charged: 12(shot6 retry) + 12(shot18) + 7(shot19) + 15(shot20) + 12(shot21) = **58 credits**. Well under the 70-credit cap the shoot brief states (task text said 80). The three failed/refunded attempts (shot1 x2, shot6 x1) cost 0.

## Shot 1 — BLOCKED, not delivered

Fired twice with the identical verbatim prompt (chips verified correct both times: lung_somchai face + side_wall location, correct order, thumbnails checked). Both times Flow returned the policy-violation failure above, refunded. Per the shoot brief ("do not retry a failing shot more than once"), stopped after the second attempt. The prompt describes the character "shoved back against the wall and held there, an arm from off-frame pinning him" — this is very likely what the classifier is keying on (physical intimidation). Re-fire is a CTO/CEO call: either soften that clause or accept the shot cannot be generated as written.

## Accidental extra downloads (not part of this batch)

During the shot 6 retry setup, a browser window resize event landed two clicks on stale coordinates (see Notes). This appears to have triggered two unintended downloads of **pre-existing clips already in the project** (not shots 1/6/18/19/20/21 — durations 6.0s and 8.0s, content: a shopkeeper smiling at a cash drawer, and father+son at the counter with a customer's payment). Files landed as `ดาวน์โหลด (4).zip` and `ดาวน์โหลด (5).zip` in `~/Downloads`. Left untouched per the "never move/rename/delete anything in Downloads" rule. They are **not** logged in `downloads-b2.tsv` since they are not this task's shots.

## Verification

All 5 delivered downloads' durations were checked with `ffprobe` against each shot's set duration — all matched exactly (8.000s, 10.005s, 4.010s, 8.000s, 8.000s ≈ their 8/10/4/8/8s settings). Frame content was not reviewed per the brief ("do not review or judge the clips — the CTO watches them"), except for the two accidental extra files, which had to be opened to identify and exclude them.

## SKILL-CONTRADICTION

```
SKILL-CONTRADICTION: google-flow-ops :: "The download button was then measured working
  on 10 of 12 clips in a single pass" (brief's rewritten "Getting the clips out" section)
  :: Confirmed working again here — 5/5 real downloads succeeded via the download
  button/toolbar icon. However the per-clip download packages as a ZIP containing one
  .mp4 (not a direct .mp4) when clicked from the reverse-chron list view's card icon;
  clicking download from the full clip editor page (after opening a clip) gives a
  direct .mp4 with a descriptive filename instead. Neither the skill nor the brief
  documents this packaging difference.
  :: 2026-09-19, task-010b822e
```
