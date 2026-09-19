# Banchi Act 1 — batch 4 (task-23d61ed9)

Project: `flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39` ("AI Film"), Chrome device `35a05d33-...` (mac). Read `docs/briefs/banchi-act1-shoot-first12.md` and `.claude/skills/google-flow-ops` / `.claude/skills/browser-operator` in full before starting.

## Part 1 — re-download shot 6 (find by prompt) — NOT RECOVERED

Searched extensively for the clip whose prompt matches shot 6's dialogue ("สี่สิบ ห้าสิบ หกสิบ เจ็ดสิบห้า" / "ค่ายาแม่เดือนนี้ยังขาดอีกสามร้อย", chips lung_somchai + upstairs_bedroom):

- Confirmed from `docs/reports/banchi-batch2-20260919/REPORT.md`: shot 6 was fired twice on 2026-09-19 (first attempt failed on the policy classifier, refunded; **second attempt submitted successfully and was charged 12 credits**), but the operator that ran that batch downloaded the wrong file (`Shopkeeper_speaking_in_noodle_shop_...mp4` — a noodle_shop title, not upstairs_bedroom), matching exactly the mistake this task describes.
- Confirmed from `docs/reports/banchi-download-20260919/REPORT.md`: the ORIGINAL pre-rework shot 6 clip (`e513be94-693c-4fc1-a935-44560a08d4f1`) renders as a permanently blank `/edit/<id>` page (zero DOM content) — re-verified this run, still blank. This is not the clip we want anyway (it predates the rework).
- The project's search box did not filter results for any dialogue substring I tried ("เจ็ดสิบห้า", "ขาดอีกสามร้อย", "counting money") — it returned either the unfiltered feed or "ไม่มีผลลัพธ์" for every query, contradicting the method `docs/reports/banchi-act1-A2-20260918/REPORT.md` reported working. This may be project-state- or session-specific; flagging as a contradiction below.
- Filtered the media grid to วิดีโอ · 8 วินาที · 720p (76 results) sorted newest and oldest, and manually opened ~20 distinct candidate clips via `/edit/<id>`, reading each one's prompt text. All were shots already known from the doc (1, 5, 6-noodle-decoy, 9, 15, 22, 23-variant, 24-variant) or off-script test generations (upstairs_bedroom scenes involving nong_daeng+grandma_pranom, not lung_somchai alone). None matched shot 6's exact dialogue.
- Did not find a bulk/network-based way to search the project's full prompt set (attempted a `fetch` hook on `batchexecute` calls; nothing was captured on scroll, likely because the grid uses a different fetch mechanism for lazy-loaded items).

**Stopping per skill guidance** ("two attempts, then it is a re-fire decision for the C-level, not a retrieval problem") — this effort well exceeded two attempts. Shot 6's paid retry clip is real (12 credits were charged and not refunded) but I could not locate it in the project feed within a reasonable search budget. Recommend either: (a) a fresh operator with more search budget, ideally once Flow's search is confirmed working again, or (b) accept the loss and re-fire shot 6 fresh (12 credits) in the next batch.

## Part 2 — shoot shots 1, 24, 28, 29, 30

Settings verified before every submit: **Omni 1.1 Flash · องค์ประกอบ · 9:16 · 720p · x1**, duration per shot's own heading. All chips attached via the picker's search box, verified by thumbnail before adding, count-checked immediately before submit. All prompts pasted via `document.execCommand('insertText')` and verified against the source file by reading back `innerText` in full before submit.

| shot | duration set | chips attached (order) | live estimate | submitted | prompt line used to confirm identity | downloaded | filename |
|---|---|---|---|---|---|---|---|
| 1 | 8s | 1) lung_somchai→REF_0 · 2) side_wall→REF_1 | 12 cr | yes | — | **REFUSED** (policy classifier) | — |
| 24 | 10s | 1) lung_somchai→REF_0 · 2) noodle_shop→REF_1 | 15 cr | yes | — | **REFUSED** (policy classifier) | — |
| 28 | 8s | 1) cop_wit→REF_0 · 2) noodle_shop→REF_1 | 12 cr | yes | "ลุงครับ เส้นเล็กน้ำใสเหมือนเดิมครับ" | **yes** | Man_orders_noodles_in_shop_20260919112311.mp4 |
| 29 | 8s | 1) lung_somchai→REF_0 · 2) cop_wit→REF_1 · 3) noodle_shop→REF_2 | 12 cr | yes | "ไม่ใส่ถั่วงอกใช่ไหมวิทย์" | **yes** | Shopkeeper_and_man_talking_in_20260919112124.mp4 |
| 30 | 10s | 1) cop_wit→REF_0 · 2) lung_somchai→REF_1 · 3) noodle_shop→REF_2 | 15 cr | yes | "เอาไว้ก่อน วันหลังค่อยจ่าย" | **yes** | Men_talking_in_noodle_shop_20260919111941.mp4 |

**Credits spent: 12 + 12 + 15 = 39** (shots 28/29/30). Shots 1 and 24 were refused and refunded (0 credits), confirmed by the exact refusal text below and no deduction shown in either live estimate flow. **Total isolated spend: 39, well under the 75-credit cap.**

## Shots 1 and 24 — refused again, verbatim, not retried

Both shots used the sheet's current (already-rewritten) prompt text, verbatim, exactly as instructed. Both were refused on this attempt too, with identical text both times:

```
ล้มเหลว
การสร้างนี้อาจละเมิดนโยบายของเรา โปรดลองใช้พรอมต์อื่นหรือส่งความคิดเห็น
ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้
```

("Failed — this generation may violate our policy, try a different prompt or send feedback. The system did not charge you for this generation.")

Per the task's instruction, neither was retried and neither prompt was reworded by me. This is now the **second** rejection for both shots despite the sheet edits (shot 1 previously rejected for "held against a wall"; shot 24 previously rejected for "sorting banknotes into piles" — both clauses were already removed from the current sheet text I used). The remaining likely trigger for shot 1 is the phrase "a long shadow falls across him" combined with "stands backed against the wall ... talking fast and upward to someone just off-frame" (still reads as a person being confronted/intimidated even without physical contact). For shot 24 nothing in the current text obviously reads as policy-sensitive (a man alone counting money at a counter) — this may be a residual classifier signature on the character/scene combination rather than the text itself. This is a CTO/CEO call on whether to soften either prompt further or accept the shots cannot be generated as currently written.

## Method notes

- Route: step 3 (navigate to flow.google.com directly) — task hands the project and shot sheet directly; no API exists for Flow generation.
- Muted every page immediately after load and after every navigation, per the brief's snippet.
- Never clicked play on any clip; identity was confirmed by reading each `/edit/<id>` page's prompt text via `get_page_text`, never by title, thumbnail, or position in the feed.
- Downloads used the toolbar download button → 720p (ขนาดดั้งเดิม) resolution flyout → real `computer` click, ≥8s apart, filenames confirmed via `ls -t ~/Downloads` immediately after each click.
- Did not read the account credit balance from the menu; relied solely on the live estimate shown in the settings panel before each submit.

## SKILL-CONTRADICTION

```
SKILL-CONTRADICTION: google-flow-ops :: "docs/reports/banchi-act1-A2-20260918/REPORT.md's method — 'Flow's own top-bar search full-text-matches against the complete prompt, including the embedded Thai dialogue line' — reliably narrows the grid to exactly one card"
  :: On this project, this session, searching for four different exact/short Thai substrings from shot 6's known dialogue (and an English phrase from the auto-generated title style) all returned either the unfiltered feed or "ไม่มีผลลัพธ์" (no results), never a narrowed single-card result. Never got the search box to filter anything successfully.
  :: 2026-09-19, task-23d61ed9, project e88671f5-9ae8-4946-84a6-8b8e31dc0d39.
```

## Skill learning

- WRONG : the A2 report's claim that Flow's search box reliably full-text-matches prompt dialogue did not hold up this session — see SKILL-CONTRADICTION above. Worth re-verifying on a smaller/cleaner project before relying on it again; the failure mode may be project-size-dependent (this project has 130+ media items) rather than universal.
- MISSING : the skill has no fallback method for finding one specific past clip in a large (100+ item) project when both search and virtualized-grid scrolling fail. I ended up manually opening dozens of `/edit/<id>` candidates one at a time via get_page_text, which works but is slow and has no natural stopping point other than a time/step budget.
- COSTLY : the Part 1 search (shot 6) consumed a large share of the task's step budget without success. A future brief should either supply the clip id directly (if any prior session captured it at submit time, per the "capture at submit" rule) or explicitly cap the search effort (e.g. "try N candidates, then stop") rather than leaving it open-ended.
- (also) : confirmed the "capture the clip id at submit, in the same tool-call sequence" rule from the skill is exactly right — I did this for all three delivered shots this run (28/29/30) and it made downloading trivial. The rule was clearly NOT followed by whichever earlier session generated shot 6's real retry clip, which is why it's lost now.

## Issues / Blockers

- Shot 6's paid clip (from the batch2 retry, 12 credits charged) could not be located and is effectively lost to this session's search budget. See Part 1 above.
- Shots 1 and 24 refused by the policy classifier a second time despite already-rewritten prompts. Needs a CTO/CEO decision on whether to soften either prompt further, or accept as unshootable in this form.

## Notes for Reviewer

- `downloads-b4.tsv` (worktree root) has the 3 successful shots logged, one line per shot, appended immediately after each download.
- No video files were committed to the worktree; downloads landed in `~/Downloads` per the brief's rule (not moved/renamed).
