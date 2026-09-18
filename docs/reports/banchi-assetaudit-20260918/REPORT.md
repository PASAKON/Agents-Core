# Asset + voice audit — AI Film project, 2026-09-18

Task: task-70d351e4. Project: `AI Film`,
https://flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39

No video or image generation was run. Credit balance before and after are
identical.

## Credit balance

| | Balance |
|---|---|
| Start | 9,989 เครดิต |
| End | 9,989 เครดิต |
| Delta | **0** |

## PART 1 — Asset inventory

All 19 expected assets (14 built earlier today + 4 original characters + the
original location) were found present, by exact handle, in the `ตัวละคร` tab:

**Characters (new):** @cop_wit, @jae_muay, @staff_a
**Locations (new):** @upstairs_bedroom, @back_alley, @side_wall, @street_front,
@staircase, @noodle_shop_thriving
**Props (new):** @bedrail_marks, @fathers_phone, @qr_sign, @empty_pill_pack,
@money_fold
**Originals:** @lung_somchai, @nong_daeng, @grandma_pranom, @lender_cherd,
@noodle_shop

Nothing missing. Nothing renamed. No duplicate of a manifest handle exists —
Flow enforces unique `@handle`s, so a rename or duplicate would have shown as
a different name, and none did.

**Unexpected extras found (not in the 14+5 manifest), also in the `ตัวละคร`
tab:**

- `@test_char3` — young woman, bob-length dark hair. Does not match the
  description of any of the 19 manifest characters (no young bobbed-hair
  woman in the cast).
- `@test_char4` — elderly woman, grey hair, dark floral blouse, gold necklace.
  Visually distinct from @grandma_pranom (@grandma_pranom is frailer, white
  hair, nasal cannula, floral nightgown — a different woman, different
  costume, different props) but similar enough in age/gender that it is worth
  flagging in case it was an earlier draft of that character.
- `@prop_envelope` — a plain paper envelope prop, not named anywhere in the
  14-item manifest.

These three read as leftover test/draft artifacts from earlier work, not as
renames or duplicates of anything on the manifest — none of the 19 real
assets is missing or doubled. Recommend the CEO/CTO decide whether to delete
them; left untouched for this task since deletion wasn't in scope.

## PART 2 — Voices, before state (read from each character's own page)

| Character | Voice row before |
|---|---|
| @lung_somchai | **เลือกเสียง (none)** |
| @nong_daeng | **เลือกเสียง (none)** |
| @grandma_pranom | **เลือกเสียง (none)** |
| @lender_cherd | algieba (per task brief, this is a known deliberate difference from the script's Umbriel — not touched) |
| @cop_wit | achird |
| @jae_muay | laomedeia |
| @staff_a | achernar |

This confirms the task's premise: all three of @lung_somchai, @nong_daeng
and @grandma_pranom had genuinely lost their voice binding — not just an
earlier audit's misread. @cop_wit, @jae_muay and @staff_a were all still
correctly bound (achird / laomedeia / achernar) — none of those needed
rebinding.

## PART 3 — Binding the three voice locks

Bound via each character's own page → เลือกเสียง → search box (typing the
exact preset name, to avoid the virtualized-list mismatch noted below) →
select → เพิ่มลงในตัวละคร.

| Character | Before | Bound to | After (confirmed on character page) |
|---|---|---|---|
| @lung_somchai | none | Algenib | **algenib**, with play control + นำออก |
| @nong_daeng | none | Iapetus | **iapetus**, with play control + นำออก |
| @grandma_pranom | none | Gacrux | **gacrux**, with play control + นำออก |

@lender_cherd was read only — confirmed still `algieba`, per the task's
explicit instruction not to touch it. @cop_wit / @jae_muay / @staff_a were
read only — all three confirmed intact, no rebind needed.

**One near-miss worth recording for the skill:** the `find` tool's natural-
language search inside the เลือกเสียง dialog returned the wrong voice once —
it labelled option ref_711 "Iapetus" while the DOM's own accessible-tree read
(`read_page`) showed that same ref was actually **Fenrir** ("Male, excitable,
younger pitch" — Fenrir's real label, not Iapetus's "Male, clear, mid-low
pitch"). Caught by cross-checking the description text against the skill's
own preset table before clicking, not by trusting `find`. Switched to typing
the exact preset name into the dialog's own search box for every subsequent
bind, which is the reliable path.

## PART 4 — Reload persistence test

After confirming all three, the page was hard-reloaded (Cmd+Shift+R) at the
project root (the media list), then each of the three characters was opened
again and its voice row re-read.

| Character | Voice after hard reload |
|---|---|
| @lung_somchai | algenib — **survived** |
| @nong_daeng | iapetus — **survived** |
| @grandma_pranom | gacrux — **survived** |

**After a reload, 3 of 3 bindings survived.**

This means the reload itself is not the mechanism behind today's mystery —
a freshly-bound voice does persist across a hard reload and a navigate-away/
navigate-back cycle. Whatever caused @lung_somchai, @nong_daeng and
@grandma_pranom to come up unbound before this task started (contradicting
the production record that Iapetus was already CEO-approved on @nong_daeng
2026-09-18) happened through some other path — not a reload. Candidates not
ruled out by this test: an earlier session's `รีเซ็ต`/save-flow interaction
(the skill documents the customize-performance save button as permanently
broken on this account), a bind that was made but never confirmed before the
tab/session ended, or the bind having been made on a different character
object than the one currently in the manifest (e.g. if a character was
deleted and recreated with the same handle).

## Credit balance, confirmed again

9,989 → 9,989. No estimate above 0 was ever shown; no Upgrade/Subscribe/Buy
button was clicked.

## Skill learning

- WRONG    : none — google-flow-ops's voice-binding steps (character page →
  เลือกเสียง → dialog → search box → select → เพิ่มลงในตัวละคร) worked exactly
  as documented on the first attempt for all three characters.
- MISSING  : the skill doesn't warn that the เลือกเสียง dialog's virtualized
  list can make `find`'s natural-language matching pick the wrong option by
  position (it returned Fenrir's ref when asked for "Iapetus option in
  list") — the same class of virtualization trap the skill already documents
  for the ingredient/asset picker, just not for the voice dialog specifically.
  Worth a line: always type the exact preset name into the dialog's own
  search box and verify the returned single result's description string
  against the skill's own preset table before clicking, rather than trusting
  a natural-language element match in that dialog.
- COSTLY   : nothing was costly in credits (this task spent 0), but the
  slowest single step was scrolling/JS-extracting the full ~22-item ตัวละคร
  list to confirm no asset was missing, since the list is virtualized and a
  single scroll position only renders ~12-14 of the ~22 items at a time.
  Running the same `document.querySelectorAll` text-extraction JS snippet
  twice, once before and once after scrolling to the bottom, then taking the
  union, was what actually got a complete list — a single read (as the task's
  "read the character page, not the picker list" framing might suggest) is
  not enough for a tab-level inventory check; the picker/list DOM needs the
  same union-of-scroll-positions treatment.

SKILL-CONTRADICTION: none filed — no rule in google-flow-ops was found to be
wrong by this run.
