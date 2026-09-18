# «บัญชี» Act 1 — shot 9 reshoot + shots 13-17 (task-9802d99c)

Google Flow project "AI Film" (`e88671f5-9ae8-4946-84a6-8b8e31dc0d39`), Chrome
device `35a05d33-...` (mac). Read `docs/briefs/banchi-act1-shoot-first12.md`
and `.claude/skills/google-flow-ops` in full before starting.

Mid-task the CTO sent a letter overriding the URL-capture requirement for the
remaining shots (see Issues/Notes below) — shot 9 has a full signed URL,
shots 13-17 have clip id only, per that instruction.

## Shot table

| shot | duration set | chips attached (order) | live credit estimate | submitted | clip id | URL captured |
|---|---|---|---|---|---|---|
| 9 (RE-SHOOT) | 10s | nong_daeng, lung_somchai, noodle_shop | 15 | ✅ | `235c8a10-1582-4253-afe6-a96d6480c1d9` | ✅ |
| 13 | 8s | lung_somchai, nong_daeng, noodle_shop | 12 | ✅ | `7f865343-874d-463b-a002-a51f738bb4c6` | ❌ not retrieved (2 attempts) |
| 14 | 6s | lung_somchai, noodle_shop | 10 | ✅ | `e07eb86b-6928-436b-83d5-032fb87dad4d` | ❌ not retrieved (2 attempts) |
| 15 | 8s | nong_daeng, staircase | 12 | ✅ | `49759b5b-44dc-436d-82ef-b713ed2312d6` | ❌ not retrieved (2 attempts) |
| 16 | 6s | nong_daeng, staircase | 10 | ✅ | `cda89bb8-3d90-42ce-a8ac-770555ffb0d5` | not attempted (CTO stopped retrieval) |
| 17 | 6s | nong_daeng, noodle_shop | 10 | ✅ | `4efd06e8-31eb-402f-b463-9b652fcd83f4` | not attempted (CTO stopped retrieval) |

**Total live-estimate credits: 69** (within the 80 cap). No error text was
returned by Flow on any of the 6 submits — all fired cleanly.

Settings (Omni 1.1 Flash · องค์ประกอบ · 9:16 · 720p · duration · x1) were
re-read from the DOM (`mat-button-toggle-checked` state, or a zoomed
screenshot of the settings panel) immediately before every single submit —
none were trusted to persist from the prior shot.

Every chip was attached via the picker's exact-text search box (never a
label match) and verified by **zooming into its thumbnail** before/after
attach, per the skill's hard rule — this caught nothing wrong, but two false
alarms were investigated and resolved (see Issues). The `@noodle_shop` /
`@noodle_shop_thriving` near-namesake was checked explicitly on every attach.

Prompt text for every shot was pasted via `document.execCommand('insertText')`
and verified against the source `docs/scripts/banchi-ACT1.md` block by reading
back `innerText` (full string, not truncated) before submit. Shot 9's rewritten
line — `"เมื่อคืนผมส่งใบสมัครไปอีกสองแห่งแล้วนะพ่อ"` — was confirmed to match the
current sheet exactly; no text from the old stuttering take was reused.

Mute-before-play was applied on every clip touched
(`document.querySelectorAll('video').forEach(v=>{v.muted=true;v.volume=0})`,
also extended to `audio` elements found via canvas-based players). The
download button was never clicked. The account menu credit balance was never
read.

## Issues / Blockers

**Clip URL retrieval failed for shots 13, 14 and 15** despite the documented
`read_network_requests` method (mute, click play, filter
`flow-content.google/video`) working cleanly for shot 9. Two attempts each
(page reload + fresh tab) produced zero matching network entries, even though
the clip visibly played (canvas motion, timeline advanced). This reproduces
the exact contradiction task-f1dccff4 logged the day before on this same
project — the method is not reliable this session. Per the skill's own rule
("two attempts, then it is a re-fire decision for the C-level, not a
retrieval problem"), I stopped after two attempts each and moved on.

**Mid-task, the CTO sent a direct instruction (mailbox letter, 2026-09-18
20:06:51Z) to stop attempting URL capture entirely for the rest of the task**,
explaining the CTO will clear Chrome's disk cache after this task so every
clip becomes fetchable again in one pass, and that chasing an unrecoverable
capture wastes steps. I complied immediately: shots 16 and 17 were shot with
**no play, no `read_network_requests`, no retrieval attempt at all** — only
clip id and live credit estimate were recorded, appended to
`clips-batch1.tsv` as `<shot>\t<clip-id>` per that instruction. All settings/
chip/prompt verification (HARD rules) continued unchanged.

**The Flow tab's renderer froze completely partway through shot 13's
retrieval attempts** — `computer.screenshot` and `computer.zoom` returned
`CDP sendCommand "Page.captureScreenshot" timed out` on every call for a
sustained stretch (confirmed independently broken by testing a screenshot on
a brand-new tab to plain `google.com`, which worked instantly — the freeze was
scoped to that one Flow tab, not the extension). I fell back to
`javascript_tool`/`get_page_text`/`find` during the freeze, then closed the
stuck tab and opened a fresh one, per the skill's documented recovery. This
cost real time but no credits.

**A transient ~3-chip stale-composer state appeared once (before the tab
freeze/reload), traced to a stuck `cdk-overlay-backdrop`** left mounted from
an earlier picker interaction — clicks that should have landed on real page
elements were being intercepted by an invisible full-page backdrop. A hard
reload (`cmd+shift+r`) cleared it. No credits were spent while this was
happening (it was caught before any submit) and the eventual attaches for
shots 15-17 were all done fresh, in a new tab, with full visual thumbnail
verification.

**Two false-alarm chip-preview mismatches** (shots 15 and 17's `@staircase`/
initial `@noodle_shop` zoom) turned out to be stale frames caught mid-render
by the zoom call — re-zooming immediately after showed the correct image both
times. Flagging this as a real trap: a single zoom/screenshot right after
typing a search query can catch the *previous* query's preview still on
screen; the fix is to re-zoom once before trusting a "wrong" result.

**`computer` tool clicks on `ref_XXX` elements sometimes silently failed to
register** on the Flow composer (picker stayed open, chip count unchanged)
while the identical action via `document.querySelector(...).click()` in
`javascript_tool` worked immediately. This happened specifically on the
ingredient-picker's "เพิ่มไปยังพรอมต์" button and the settings-panel toggle
buttons. Switched to JS-direct clicks for those two controls for the rest of
the task.

## Files Changed

- `clips-batch1.tsv` (new) — 6 rows: shot 9 has a full signed CDN URL, shots
  13-17 have clip id only (per the CTO's mid-task override)
- `docs/reports/banchi-batch1-20260919/REPORT.md` (new) — this report

No source files were modified — this task only shot in Flow and recorded
clip ids/URLs.

## Commits

Will commit `clips-batch1.tsv` + this report now.

## Skill-overrides

None against `google-flow-ops` or `browser-operator`'s HARD rules — settings
re-verification, chip thumbnail verification, mute-before-play, no-download-
button, and no-account-menu-balance were all followed as written for every
shot. The stop-on-URL-capture change came from the CTO directly (not a
self-judged override of the brief), so it is not a skill-override in the
usual sense — it supersedes the brief's "capture per shot" instruction for
shots 16-17 by direct instruction.

## Skill learning

- **WRONG**: none of `google-flow-ops`'s documented mechanics were
  contradicted by direct testing — the URL-capture method's unreliability on
  this project was already flagged as a live contradiction by an earlier
  task (task-f1dccff4) the day before; this run adds three more data points
  (shots 13, 14, 15) to that same open contradiction rather than a new one.
- **MISSING**: the skill has no entry for "a `cdk-overlay-backdrop` left
  mounted after a picker interaction silently intercepts clicks elsewhere on
  the page" — worth adding next to the existing "chip attach is inconsistent"
  and "MCP tab group destruction" entries, since the symptom (clicks land on
  nothing, composer state looks stuck) looks identical to those two but the
  fix (hard reload, not a fresh tab or re-navigate) is different.
- **MISSING**: the skill doesn't note that `computer` tool ref-based clicks
  can silently no-op on the ingredient-picker's "เพิ่มไปยังพรอมต์" button and
  the settings-panel toggles specifically, while a JS `.click()` on the same
  element works immediately. Worth adding as a third documented click-flake
  alongside the existing two (immediate-attach-vs-second-click, and the `+`
  button toggling itself closed).
- **COSTLY**: chasing the CDN-URL contradiction for shots 13-15 (reload +
  fresh tab, twice each) before the CTO's stop instruction arrived ate a
  large share of this task's budget for zero retrieval payoff. The
  recommendation in task-f1dccff4's report ("re-verify with a single
  throwaway clip whether `read_network_requests` still misses the video fetch
  before spending budget on the full shot list") was followed here — shot 9
  confirmed the method still works sometimes, which is exactly why it looked
  worth continuing to try on 13-15 rather than escalating immediately. In
  hindsight, one failure (shot 13) after one success (shot 9) was already
  enough signal to escalate to the CTO instead of repeating the same 2-attempt
  cycle two more times.
