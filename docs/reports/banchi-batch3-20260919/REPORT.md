# «บัญชี» Act 1 — shots 22–27 (task-6690897e)

Google Flow project "AI Film" (`e88671f5-9ae8-4946-84a6-8b8e31dc0d39`), Chrome
device `35a05d33-...` (mac). Read `docs/briefs/banchi-act1-shoot-first12.md`
and `.claude/skills/google-flow-ops` in full before starting. Another operator
was shooting shots 1, 6, 18–21 in the same project in parallel (confirmed by
that operator's downloads landing in the same `~/Downloads` in the same window
— see Notes).

## Shot table

| shot | duration set | chips attached (order) | live credit estimate | submitted | downloaded | filename |
|---|---|---|---|---|---|---|
| 22 | 8s | grandma_pranom, nong_daeng, upstairs_bedroom | 12 | ✅ | ✅ | `ดาวน์โหลด (8).zip` |
| 23 | 6s | nong_daeng, grandma_pranom, upstairs_bedroom | 10 | ✅ | ✅ | `ดาวน์โหลด (7).zip` |
| 24 | 10s | lung_somchai, noodle_shop | 15 | ✅ (attempt 1) — **FAILED, not charged** | ❌ | — |
| 24 (retry) | 10s | lung_somchai, noodle_shop | 15 | ✅ (attempt 2, verbatim identical prompt) — **FAILED, not charged** | ❌ | — |
| 25 | 8s | lung_somchai, noodle_shop | 12 | ✅ | ✅ | `ดาวน์โหลด (6).zip` |
| 26 | 8s | nong_daeng, lung_somchai, noodle_shop | 12 | ✅ | ✅ | `ดาวน์โหลด (5).zip` |
| 27 | 6s | lung_somchai, noodle_shop | 10 | ✅ | ✅ | `ดาวน์โหลด (4).zip` |

**Total credits actually charged: 56** (12+10+12+12+10; shot 24's two failed
attempts were not charged per Flow's own message). Well within the 80-credit
cap. 5 of 6 shots delivered.

Settings (Omni 1.1 Flash · องค์ประกอบ · 9:16 · 720p · duration · x1) were set
and re-verified via the settings-panel zoom immediately before every single
submit — duration was changed per shot's own heading (8/6/10/8/10/8/6s in
submission order) and never trusted to persist from the prior shot.

Every chip was attached via the picker's exact-text **search box**, verified by
looking at the preview image (a face for a character, an interior for a
location) before clicking "เพิ่มไปยังพรอมต์", then the chip thumbnail row was
zoomed/screenshotted to confirm both count and left-to-right order matched the
shot's ATTACH line before every submit. The `@noodle_shop` / `@noodle_shop_thriving`
near-namesake was checked explicitly on every attach (4 shots used noodle_shop).

Prompt text for every shot was pasted via `document.execCommand('insertText')`
and verified against the source `docs/scripts/banchi-ACT1.md` block by reading
back `innerText.length` (matched the source string's length exactly every
time) plus a visual read of the expanded composer before submit. The money
shots (24, 25, 26, 27) all carry the full NOT-LIST paragraph about the prop
banknotes, pasted verbatim as instructed.

Mute-before-play snippet was run once on page load (before any other action)
per the brief and `google-flow-ops`/`browser-operator` skills. No clip was
ever played or scrubbed in this session — clips were verified as finished
purely from the feed thumbnail/still frame, never watched.

The account credit balance was never read from the account menu, per the
brief. Only the live per-shot estimate in the settings panel was used.

## Shot 24 — failed twice, not retried a third time

Both attempts returned Flow's own failure card, verbatim:

```
ล้มเหลว
การสร้างนี้อาจละเมิดนโยบายของเรา โปรดลองใช้พรอมต์อื่น หรือส่งความคิดเห็น
ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้
```

("Failed — this generation may violate our policy. Please try a different
prompt or send feedback. The system did not charge you for this generation.")

The second attempt used the byte-identical prompt (verified via
`innerText.length`, 2491 chars both times) and identical chips/settings — no
material differed. Per the brief ("Do not retry a failing shot more than
once"), I stopped after the second failure and moved to shot 25. This is the
same shot the brief flagged as a money-counting shot with an invented-prop-money
NOT-LIST paste, so the block was correctly included both times; the block did
not prevent the policy flag either time.

## Issues / Blockers

**Composer got silently cleared twice mid-task**, costing two full chip+prompt
re-entries (once for shot 22, once for shot 25):

1. After shot 22's first chip+prompt entry, I reopened the **settings dropdown
   panel** (to re-verify duration/estimate) and closed it via its `X`. This
   cleared every chip and the entire prompt text with no warning — a
   subsequent submit attempt returned "ต้องระบุพรอมต์" (must specify a prompt),
   not a real submission, so no credit was spent. **Fix applied for the rest
   of the run: set duration BEFORE attaching any chips, and never reopen the
   settings panel once chips/text are in the composer** — only zoom-read the
   collapsed settings pill's text for re-verification.
2. Separately for shot 25, I clicked what I believed was the failed-card's own
   close/dismiss `X` to read its error text fully, but the click actually
   landed on my own composer's collapse `X` (same screen coordinates,
   different overlay, z-order coincidence) and cleared shot 25's chips+prompt
   again. No credit was spent (nothing had been submitted yet). **Fix: never
   click any `X` near the composer overlay for any reason — read overlay
   content via `zoom` only, without dismissing anything.**

Both incidents cost time but zero credits, since neither ever produced a real
submission while cleared.

**Shot 24 failed twice as a probable Flow content-policy flag**, not a chip,
prompt-fidelity, or settings problem — see above. This is the CEO-flagged risk
class for this shot (invented prop money vs. real Thai banknotes), but the
NOT-LIST text was pasted verbatim both times and the failure message names
"policy," not a specific reason. A C-level should decide whether to re-word
the prompt (e.g., soften "sorting worn banknotes into piles" or move more of
the NOT-LIST framing earlier in the prompt) before a third attempt — I did not
attempt a third fire per the one-retry rule.

**Identifying my own downloads in a shared `~/Downloads`**: files land as
generic `ดาวน์โหลด (N).zip` with no shot number embedded, exactly as the
`google-flow-ops` skill warns. Another operator (shots 1, 6, 18–21, same
project) was downloading in the same window — 5 zip files (`.zip` through
`(3).zip`) landed at ~1/minute between 10:33–10:36 before I fired my first
download at 10:39, then my 5 downloads landed cleanly spaced by my own
8+ second waits (10:39:40, 10:41:00, 10:42:51, 10:43:46, 10:44:27) with no
further files from the other operator interleaved. I did not move, rename, or
open any file in Downloads besides reading `stat` timestamps.

No Chrome blocked-downloads indicator appeared at any point.

## Replay Script

- path: none
- covers: n/a
- brittle: n/a — this was one-off shot generation + download, not a repeatable
  flow (each shot has unique chips/prompt/duration). The mechanical steps
  (mute snippet, settings-panel duration set, search-box chip attach,
  execCommand paste, download-then-stat-Downloads) are already fully
  documented in `.claude/skills/google-flow-ops` and `browser-operator` for
  the next operator to follow by hand.

## Files Changed

- `downloads-b3.tsv` — new, 5 rows (shot, filename), one per successful
  download, appended immediately after each download per the brief
- `docs/reports/banchi-batch3-20260919/REPORT.md` — this file

## Skill learning

- WRONG    : (none) — no rule in `google-flow-ops` or `browser-operator` was
  proven false this run.
- MISSING  : Neither skill warns that **reopening the settings dropdown panel
  after chips+prompt are already entered, then closing it via its `X`, clears
  the entire composer** (chips and prompt text, silently, with only a later
  "ต้องระบุพรอมต์" submit error as the tell). The skills document that
  *expanding the prompt textbox* or the *composer's own `x`* clears chips, but
  not that the **settings panel's own close button** does the same. This cost
  a full shot 22 chip+prompt re-entry.
- COSTLY   : The two composer-clear incidents above (settings-panel X, then a
  misclicked overlay-X meant to read a failed card) were the most expensive
  steps — each cost a full chip-search+attach+paste redo (~8 browser actions).
  Knowing in advance "never touch any X near the composer once chips/prompt
  are staged; verify duration before attaching chips, not after" would have
  prevented both.
- (none)   : n/a — see MISSING/COSTLY above, not empty this run.

## Notes for Reviewer

- Shot 24 needs a C-level call: re-word and re-fire a third time, or accept
  the gap in Act 1's shot list. I stopped at 2 failures per the brief's
  explicit one-retry rule.
- All 5 delivered clips are `.zip` files in `~/Downloads` (not extracted, not
  moved, not renamed) — per `google-flow-ops`, clips do not belong in this
  git repo; the CTO/C-level should pull them to Drive per the ILAG/
  `gdrive-filing` rules before this branch merges.
- Video content was never reviewed or judged, per the brief — only shot
  number, duration, chip identity/order, and prompt-text fidelity were
  checked mechanically.
