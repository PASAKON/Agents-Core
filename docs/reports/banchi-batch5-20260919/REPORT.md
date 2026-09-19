# Banchi Act 1 — batch 5 (task-b6d70b80)

Project: `flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39` ("AI Film"), Chrome device `35a05d33-...` (mac). Read `docs/briefs/banchi-act1-shoot-first12.md` and `.claude/skills/google-flow-ops` / `.claude/skills/browser-operator` in full before starting. Only operator in this project — every new clip in the feed was mine.

This finishes Act 1: shots 1, 6, 24, 31, 32, 33, 34.

Settings verified before every submit: **Omni 1.1 Flash · องค์ประกอบ · 9:16 · 720p · x1**, duration per shot's own heading (all six settings re-read via DOM/JS check immediately before each submit, not from memory).

| shot | duration set | chips attached (order) | live estimate | submitted | prompt line used to confirm identity | downloaded | filename |
|---|---|---|---|---|---|---|---|
| 1 | 8s | 1) lung_somchai→REF_0 · 2) side_wall→REF_1 | 12 cr | yes | — | **REFUSED** (policy classifier, 3rd time) | — |
| 6 | 8s | 1) lung_somchai→REF_0 · 2) upstairs_bedroom→REF_1 | 12 cr | yes | — | **REFUSED** (policy classifier) | — |
| 24 | 10s | 1) lung_somchai→REF_0 · 2) noodle_shop→REF_1 | 15 cr | yes | — | **REFUSED** (policy classifier, 3rd time) | — |
| 31 | 8s | 1) cop_wit→REF_0 · 2) lung_somchai→REF_1 · 3) noodle_shop→REF_2 | 12 cr | yes | "ผมวางไว้ตรงนี้นะลุง" | **yes** | Men_arguing_in_noodle_shop_20260919114832.mp4 |
| 32 | 8s | 1) lung_somchai→REF_0 · 2) noodle_shop→REF_1 | 12 cr | yes | "เอาคืนไป ลุงไม่รับหรอก" | **yes** | Man_returning_money_at_noodle_20260919114755.mp4 |
| 33 | 10s | 1) nong_daeng→REF_0 · 2) lung_somchai→REF_1 · 3) noodle_shop→REF_2 | 15 cr | yes | "พ่อไม่เคยเก็บตังค์พี่วิทย์เลยใช่ไหม" | **yes** | Men_talking_in_noodle_shop_20260919114714.mp4 |
| 34 | 6s | 1) lung_somchai→REF_0 · 2) noodle_shop→REF_1 | 10 cr | yes | "ก็แค่ก๋วยเตี๋ยวชามเดียวลูก" | **yes** | Man_wiping_counter_in_shop_20260919114549.mp4 |

**Credits spent: 12 + 12 + 15 + 10 = 49.** Shots 1, 6 and 24 were refused and refunded (0 credits each, confirmed by the exact refusal text below and the live estimate flow showing no deduction). **Total: 49, well under the 95-credit cap.**

Clip ids (captured from each `/edit/<id>` URL when confirming identity, before download):
- shot 31: `29424560-8b72-4e29-bbd4-78ebfc0c353f`
- shot 32: `c7208025-516d-472b-abbc-b1576192a2f3`
- shot 33: `da038a50-15da-41e0-acb2-89beb930be12`
- shot 34: `e49ab9ba-cbdc-4121-ae0e-51b871a9af08`

## Shots 1, 6 and 24 — refused, verbatim, not retried

All three used the sheet's current (already-rewritten, re-staged) prompt text, verbatim, exactly as instructed. All three were refused with identical text:

```
ล้มเหลว
การสร้างนี้อาจละเมิดนโยบายของเรา โปรดลองใช้พรอมต์อื่นหรือส่งความคิดเห็น
ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้
```

("Failed — this generation may violate our policy, try a different prompt or send feedback. The system did not charge you for this generation.")

Per the task's instruction, none were retried and no prompt was reworded by me.

- **Shot 1** — this is its **third** documented refusal (batch2 once, batch4 once, this run once), despite being re-staged with no other person, no arm, no shadow, nobody off-frame. Per the brief, logging verbatim and moving on — this is a CTO/CEO call now.
- **Shot 24** — also its **third** documented refusal (batch2, batch4, this run), despite the current text having no money visible at all (he counts costs on his fingers). Same call needed.
- **Shot 6** — the task brief described this as fresh/no-history, but it was refused here for the first time on the current text. Identified by its own aria-label title ("Man counting money in bedroom") matching its unique location+content combination — no other submitted shot this run used upstairs_bedroom with counting content. Worth flagging: shot 6's prompt still carries the same theatrical-prop-money NOT-LIST paragraph as shots 6/24/25/26/27/31/32 (money handling scenes) — those other five all succeeded, so the money-prop paragraph itself is not the trigger; something specific to shot 6's combination (counting coins+notes into a cloth pouch, alone in the dark bedroom) may be.

## Identifying my own failed submissions among the feed

The project feed's auto-generated card titles are not unique (multiple pre-existing "Men talking in noodle shop" cards from earlier batches share a title with my new shot 33). I did not rely on title or position to confirm any SUCCESSFUL clip — every one of shots 31/32/33/34 was confirmed by reading the full prompt text on its own `/edit/<id>` page and checking for a distinctive Thai dialogue line unique to that shot (see table above), before clicking download.

For the three **failed** cards, no `/edit/<id>` page exists (a failed generation never renders), so identity had to come from the card's own `aria-label` (Flow's own accessibility title, read via JS, not eyeballed from the grid) plus process-of-elimination against which shots I had just submitted. This is weaker evidence than a full prompt-text match, but sufficient here since exactly 3 shots were submitted with known failure-prone content (1, 6, 24) and exactly 3 cards failed, with aria-labels ("Man pleading against alley wall", "Man counting money in bedroom", "Man counting costs in noodle sho…") matching those three shots' content unambiguously and matching none of the other four.

## Method notes

- Route: navigated directly to the known project URL (`flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39`), reused from the batch4 report — no API exists for Flow generation.
- Muted the page immediately after first load via the brief's snippet; only one page/tab was used for the whole session, so no re-mute was needed.
- Never clicked play on any clip. Identity was confirmed by reading each `/edit/<id>` page's prompt text via `document.body.innerText`, never by title, thumbnail, or position in the feed.
- Downloads used the toolbar download button → 720p (ขนาดดั้งเดิม) resolution flyout → real `computer` click, confirming batch4's finding that the download button works on this project (the wider skill's "download button is dead" note is from a different account/date and does not apply here). Never touched the 4K option (50 credits).
- Downloads were ≥8s apart in every case — each download was followed by a full identity-check-and-navigate cycle for the next clip (multiple tool calls, several seconds each) before the next download click.
- Did not read the account credit balance from the menu; relied solely on the live estimate shown in the settings panel, re-verified via DOM read before each submit.
- One early mis-click (closing the settings panel, then a mistimed submit click) cleared shot 1's first attempt's chips and prompt before it ever reached Submit — confirmed via the "ต้องระบุพรอมต์" (must specify a prompt) tooltip and an empty composer, meaning nothing was charged. Redid the attach+prompt from scratch; the actual submitted/refused shot 1 in the table above is the second, clean attempt.
- Screenshot budget: used more than the 5 budgeted (~14) — mostly during initial settings-panel verification and identity-confirmation clicks. Switched to JS/DOM reads (`document.body.innerText`, `querySelectorAll` chip counts) instead of screenshots for the bulk of the routine verify-before-submit checks once the pattern was established, which is what kept the rest of the run efficient. Flagging this as an overrun rather than hiding it.

## SKILL-OVERRIDE

None — followed `google-flow-ops` and `browser-operator` as written, using the download-button method (not the CDN-sniff fallback) since it is this project's proven-working path per the same-day batch4 report.

## Skill learning

- WRONG : none confirmed false this run.
- MISSING : the skill doesn't document that a mistimed click sequence around the settings panel can silently clear an in-progress composer (chips + prompt) without submitting anything — distinct from the documented "expanding the textbox or clicking the composer's own x" trap. Worth adding: closing the settings dropdown via its own X, immediately followed by a click near where Submit normally sits, can land on a stale coordinate and produce the same "everything wiped, nothing submitted" result. Recovery is identical (redo attach+prompt), and no credit was lost, but it cost several extra tool calls.
- COSTLY : re-confirming settings via a full screenshot after every duration change; switching to a regex DOM read (`document.body.innerText.match(/วิดีโอ[\s\S]{0,40}x\d/)`) for the collapsed-pill state was much cheaper and should be the default read method, reserving screenshots for the picker (to visually confirm chip thumbnails) and post-submit sanity checks.
- (also) : confirms the "capture the clip id at submit, in the same tool-call sequence" style approach is right, but in this project the composer does NOT navigate to `/edit/<id>` on submit — it stays on the project page. The id has to be captured later, when confirming identity by prompt text before download (which is what this run did), not at submit time itself.

## Issues / Blockers

- Shots 1 and 24 refused a third time each, on prompt text that was already re-staged specifically to address prior refusals. Needs a CTO/CEO decision: cut them from Act 1, or attempt a further re-stage.
- Shot 6 refused for the first time on its current text — new information the task brief didn't anticipate ("no history" was wrong for the current wording). Needs the same CTO/CEO call.

## Notes for Reviewer

- `downloads-b5.tsv` (worktree root) has the 4 successful shots logged, one line per shot, appended immediately after each download.
- No video files were committed to the worktree; downloads landed in `~/Downloads` per the brief's rule (not moved/renamed/deleted).
