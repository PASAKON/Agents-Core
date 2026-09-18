# Custom voices — บัญชี / "AI Film" project — v3 run

Project: `AI Film` (flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39)
Followed `google-flow-ops` skill's "Custom voices" section exactly (all three
fields before preview, preview → wait for play icon → save → bind → reload).

## Custom voices already present when I arrived

Checked the TOP of the `เลือกเสียง` preset list on `@lung_somchai` before
touching anything. One existing custom-voice row:

- **`Achernar {ตั้งชื่อให้เรียบร้อยตามกฏ @Charactor}`** — base Achernar, its name
  and performance-description fields are both leftover placeholder/instruction
  text (`{ต้องใส่ข้อความที่จะปรับแต่งตรงนี้ก่อนเป็น English}`), not a real cast
  voice. Does not match any of the 5 target names. Left it alone — deleting
  it wasn't asked for and it's a co-owned account.

No `Algenib @lung_somchai`, `Iapetus @nong_daeng`, `Vindemiatrix
@grandma_pranom`, `Rasalgethi @cop_wit`, or `Umbriel @lender_cherd` existed
yet. All 5 needed creating.

Also noted, not part of the task: 4 of 5 characters already had a *plain*
base preset bound (algenib / iapetus / vindemiatrix / rasalgethi). `@lender_cherd`
had **no voice bound at all** (`เลือกเสียง` button, unselected) — the wiki
ledger's "currently bound to algieba" is stale versus the live account.

## Per-voice results

| character | base | saved as | ตัวอย่างบทสนทนา used | ปรับแต่งประสิทธิภาพ used | saved | bound | name read back | survived reload |
|---|---|---|---|---|---|---|---|---|
| `@lung_somchai` | Algenib | `Algenib @lung_somchai` | แม่ ตื่นแล้วเหรอ นี่ยาเม็ดขาวก่อนนอน เม็ดเหลืองตอนเช้า | A tired Thai man in his late fifties... | ✅ | ✅ | `Algenib @lung_somchai` | ✅ |
| `@nong_daeng` | Iapetus | `Iapetus @nong_daeng` | ขอบคุณที่ให้ความสนใจ แต่ตำแหน่งนี้เต็มแล้ว | A Thai man of twenty-four... | ✅ | ✅ | `Iapetus @nong_daeng` | ✅ |
| `@grandma_pranom` | Vindemiatrix | `Vindemiatrix @grandma_pranom` | ต้นเหรอลูก... ย่าไม่เป็นไรหรอก ยาเมื่อเช้าก็กินแล้ว | A very frail Thai woman of seventy-nine... | ✅ | ✅ | `Vindemiatrix @grandma_pranom` | ✅ |
| `@cop_wit` | Rasalgethi | `Rasalgethi @cop_wit` | ลุงครับ เส้นเล็กน้ำใสเหมือนเดิมครับ | A calm Thai man in his early thirties... | ✅ | ✅ | `Rasalgethi @cop_wit` | ✅ |
| `@lender_cherd` | Umbriel | `Umbriel @lender_cherd` | พรุ่งนี้เช้า ผมมารับเอง อย่าให้ผมต้องมาสองรอบนะ | A Thai man of forty-five... | ✅ | ✅ | `Umbriel @lender_cherd` | ✅ |

All 5/5 saved on the first content attempt (no field content was ever
rejected), bound via `เพิ่มลงในตัวละคร`, name read back verbatim before
save in every case (the `ชื่อของเสียง` pre-fill bug the brief warned about —
showing the alphabetically-first preset's name instead of the selected
one — did **not** reproduce on any of the 5; it correctly showed
`<Selected Preset> คัสตอม` every time), and confirmed present after a full
page reload (navigate, not just soft refresh).

Preview → save-enabled timing measured 3 times: ~18s, ~20s, ~20s (the button
stayed `disabled` at the 10s poll and flipped to enabled by the 20s poll in
all three timed cases).

## One real hiccup — mid-task, not a field-filling mistake

While filling `@cop_wit`'s custom voice (after preview had already run once),
the MCP tab group was destroyed (`tabs_context_mcp` → "No tab group exists
for this session"), matching the known "shared Chrome" failure mode in
`google-flow-ops`. Everything typed for that character was lost. Recovered
per the skill's protocol: fresh tab, re-navigate to the character page,
re-verified from scratch (confirmed `rasalgethi` was still the *plain* bound
voice, i.e. nothing had silently saved), and redid the whole flow
successfully on the second attempt. This is the only reason `@cop_wit` in the
table above wasn't first-try.

No credits were spent — voice creation/binding is free, per the skill and
the task brief.

## Replay script

- path: none
- why: this flow is inherently per-character judgment (exact Thai dialogue
  line + English performance description supplied by the brief, base-preset
  selection from a virtualized/alphabetical list, and a name-field bug that
  has to be read back and caught live). There's no stable selector path worth
  scripting — the picker list order and dialog layout have already shown
  minor pixel drift between opens in this same session (dialog offset by
  ~10px after a scroll). Nothing here is a repeatable bulk operation; each
  future voice will be a new character with new text.

## Skill learning

- WRONG : none — the "Custom voices" section's procedure was followed
  exactly and worked first-try on 4 of 5 characters (5 of 5 once the tab
  group recovered). No contradiction found.
- MISSING : the skill doesn't mention that clicking a *search-filtered*
  single result in the `เลือกเสียง` list can close the whole dialog instead
  of selecting the row — happened twice on `@nong_daeng` (search "Iapetus" →
  click the one filtered result → dialog vanished, unsaved). Switching to
  scrolling the **unfiltered** list and clicking the row directly worked
  every time, for all 5 characters. Worth a line in the skill so the next
  operator doesn't burn 2 attempts finding this out.
- COSTLY : the tab-group destruction on `@cop_wit` (redo of ~2 minutes of
  clicking/typing). Nothing preventable on my end — it's the documented
  shared-Chrome risk, not a field-filling error.
- (none) : otherwise no surprises — `ชื่อของเสียง` pre-filled the *correct*
  selected preset's name in all 5 cases, contradicting nothing in the brief
  (the brief itself only says to verify it, which I did every time).
