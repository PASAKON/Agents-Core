# Recovery: shots 54, 55, 57 (Omni 1.1 Flash) — download only, zero credits

task-46c9b5b1, recovering three clips fired by task-34350c98 whose process died
before it downloaded or pushed anything. **No generation was fired in this
task.** Balance recorded at both ends below.

## 1. Balance

| | Value |
|---|---|
| Balance at start | **52 credits** |
| Balance at end | **52 credits** |
| Delta | **0** — downloading a card costs nothing, confirmed by direct before/after read of the account menu |
| Generations fired this task | **0** |

## 2. The three files

Identified by prompt text on the card, not by grid position (position only
confirmed "newest first" matched the expected 08:35–09:05 window). All three
are the newest three Omni 1.1 Flash / 8s / 9:16 cards in the project, dated
8 ก.ย. 2026 (2026-09-08) on the card. An older, unrelated Veo 3.1 Fast card
with a similar "young man stands alone" prompt (dated 7 ก.ย. 2026) sits lower
in the same grid — not touched.

| File | Bytes | Matched card by prompt fragment |
|---|---|---|
| `shot54-omni.mp4` | 2,215,365 | "...presses the envelope firmly back into his son's open hands..." |
| `shot55-omni.mp4` | 1,867,469 | "...holds his son's folded hands a moment longer before releasing them..." |
| `shot57-omni.mp4` | 1,774,871 | "...stands alone at the counter, envelope now held in both hands..." |

All three, plus frame stills, live in
`docs/reports/omni-voiced-scene-20260908/`. Each was committed and pushed
immediately after its own download, before the next download started — no
clip was left un-pushed at the end of a step this time.

## 3. ffprobe

| | shot54 | shot55 | shot57 |
|---|---|---|---|
| Video codec | h264 | h264 | h264 |
| Resolution | 720x1280 | 720x1280 | 720x1280 |
| Frame rate | 24/1 | 24/1 | 24/1 |
| Audio codec | aac, 48000 Hz, stereo | aac, 48000 Hz, stereo | aac, 48000 Hz, stereo |
| Duration | 8.000000 s | 8.000000 s | 8.000000 s |
| Audio stream present | **yes** | **yes** | **yes** |

All three are mechanically sound 8-second 720p vertical clips with an audio
track. I have no ears; I did not attempt to judge how anything sounds, only
whether the track exists.

Frame stills at 0s / 4s / 7.9s (8.0s itself is past EOF on an 8.000s clip) are
alongside each clip: `shot54_frame_*.jpg`, `shot55_frame_*.jpg`,
`shot57_frame_*.jpg`.

**Mouth-open check at the dialogue beat** (visual only, no audio judgement):
- **shot54** (dialogue: "เงินนี้พ่อตั้งใจหามาให้ลูก"): at all three sampled
  instants (0s, 4s, 7.9s) the father's mouth reads closed/neutral in the
  still. This does not mean the line isn't spoken somewhere in the 8s window
  — only that none of my three fixed sample points caught an open mouth.
- **shot55** (dialogue, as stored — see §5, it is truncated): at 0s and 4s the
  father's mouth (profile, left side of frame) reads slightly parted, plausibly
  mid-word. At 7.9s it reads closed, coinciding with the hands separating —
  matches the prompt's "before releasing them" beat.
- **shot57**: SILENT shot in both the stored prompt and the canonical script
  (no dialogue line). No mouth-open check applies; ambient-only audio track
  confirmed present.

## 4. Verbatim stored prompts

Copied character-for-character from each card's `.text-part` DOM node via
`javascript_tool` (`textContent`), not retyped, not translated, not read off a
screenshot.

**shot54:**
```
Medium shot, static camera. A man presses the envelope firmly back into his son's open hands, closing the younger man's fingers over it with his own. Counter of the noodle shop, late night. Single overhead bulb. Contemporary Thai realist drama, shot on 35mm, muted colour.
@lung_somchai speaks in Thai. He says, in Thai: เงินนี้พ่อตั้งใจหามาให้ลูก soft, absolute tone.
Voice: a tired 58-year-old Thai noodle-shop owner. Low, gravelly, unhurried. Warm underneath but holding something back. Never raises his voice.
Ambient noise: simmer continuing under him.
```

**shot55:**
```
Close-up, static camera on both faces in profile. A man holds his son's folded hands a moment longer before releasing them. Counter of the noodle shop, late night. Single overhead bulb. Contemporary Thai realist drama, shot on 35mm, muted colour.
@lung_somchai speaks in Thai. He says, in Thai: ไม่ต้องรู้ว่ามันมาจากไหน
Voice: a tired 58-year-old Thai noodle-shop owner. Low, gravelly, unhurried. Warm underneath but holding something back. Never raises his voice.
Ambient noise: simmer continuing under him.
```

**shot57:**
```
Close-up, static camera. A young man stands alone at the counter, envelope now held in both hands, watching his father's back at the wok without moving. Counter of the noodle shop, late night. Single overhead bulb. Contemporary Thai realist drama, shot on 35mm, muted colour.
Ambient noise: distant simmer, street gone quiet.
```

## 5. Comparison against `docs/scripts/ngoen-tee-por-EP1.md` — per shot

Canonical dialogue (shot table, §4 of the script):
- Shot 54: `เงินนี้พ่อตั้งใจหามาให้ลูก` (9 syllables)
- Shot 55: `ไม่ต้องรู้ว่ามันมาจากไหน แค่ใช้มันให้คุ้ม` (13 syllables)
- Shot 57: `SILENT`

**Shot 54 — MATCH.** The stored dialogue line
`เงินนี้พ่อตั้งใจหามาให้ลูก` is byte-for-byte identical to the canonical
script line, and the rest of the stored prompt matches the script's own Veo
prompt block for shot 54 almost word for word (the "Voice:" line is a
2026-09-08 addition for the voice-lock experiment, not present in the
original Veo prompt text, and is not a corruption — it's the intended
performance-direction text carried in-prompt per
`docs/reports/flow-voices-installed-20260908.md`'s finding that Flow's own
voice-save UI is broken).

**Shot 55 — DIFFER. Truncated, not just re-worded.** The stored line is
`ไม่ต้องรู้ว่ามันมาจากไหน` and stops there — mid-sentence.

- Canonical (script): `ไม่ต้องรู้ว่ามันมาจากไหน แค่ใช้มันให้คุ้ม`
  ("You don't need to know where it's from — just make it worth it.")
- Stored (Flow, verbatim): `ไม่ต้องรู้ว่ามันมาจากไหน`
  ("You don't need to know where it's from.")

The entire second clause — `แค่ใช้มันให้คุ้ม`, "just use it well / make it
worth it" — and the tone descriptor (`tender, final tone`, present on every
other dialogue line's card in this set) are both missing from the stored
prompt. This is exactly the corruption/truncation the previous worker
(task-34350c98) reported experiencing when sending this brief, now confirmed
from Flow's own stored copy rather than reconstructed from memory. The clip
was generated against the truncated half-line, not the full line — this
shot's dialogue payoff is incomplete in the actual asset, and it is a CTO call
whether that is acceptable or the shot needs to be re-fired with the full
line. **Not fixed and not re-fired here, per task instructions.**

**Shot 57 — MATCH.** Canonical is `SILENT` (no dialogue); the stored prompt
also carries no dialogue line. The rest of the stored prompt text matches the
script's Veo prompt block for shot 57 word for word.

## 6. Picture continuity — 54 → 55 → 57, and against `shot58-omni.mp4` on `main`

Reviewed frame stills directly (0s/7.9s for 54 and 57, 0s/4s/7.9s for 55) plus
the existing `docs/reports/omni-vs-veo-shot58-20260908/omni_frame_0s.jpg` on
`main` for shot 58.

- **Wardrobe.** Father (`@lung_somchai`): faded navy apron over a plain white
  short-sleeve tee in all four shots — frontal in 54/55, from-behind in 57
  (background, blurred) and 58 (full frame, apron straps crossing the back
  visible), all consistent in colour and cut. Son (`@nong_daeng`): plain grey
  polo shirt with a thin chain necklace in all three shots he appears in
  (54, 55, 57) — consistent.
- **Set/props.** Same steel-shelved counter, glass display cabinet, single
  overhead bulb, and stainless wok/pot station recur across all four frames.
  57 and 58 both show the wok station from slightly different angles with
  matching hardware (round steel basin, hanging bulb, glass cabinet edge).
- **Blocking progression reads as one continuous scene.** 54: father presses
  envelope into son's open hands (medium, frontal). 55: closer profile
  two-shot, hands now folded together on the counter, father about to release
  them — geometrically a plausible push-in from 54's setup. 57: son now alone,
  envelope re-gripped in both hands, watching father's back at the wok —
  consistent with 55 having just ended and father having turned away (matches
  the script's shot 56 stage direction, not generated in this batch).
  58 (on `main`): father alone at the wok, back to camera — same beat 57
  is watching.
- **No drift observed** in face geometry, hair colour/style, or build across
  the four frames compared. I cannot certify pixel-identical facial geometry
  from stills at this size (same caveat as the shot58 A/B report) — a
  full-face reviewer pass is a human call, not mine.

## 7. Cost/action log

| Action | Result |
|---|---|
| Navigate to project, resize 1024x768 | Screenshot came back 1456x819 (later 1568x744 after further navigation) — `resize_window` reported success but did not visibly change the rendered viewport size on this box, consistent with prior winbox findings |
| Read balance (account menu) | 52 credits, before and after |
| Download shot54 card | Zip landed as `ดาวน์โหลด (5).zip` containing one `.mp4`, no hang |
| Download shot55 card | Zip landed as `ดาวน์โหลด (6).zip`, no hang |
| Download shot57 card | Zip landed as `ดาวน์โหลด (7).zip`; the click also navigated the tab to a `/edit/<id>` page (matches the known "download can navigate to the clip's edit page" behaviour) — the export still completed and the correct file arrived, confirmed by matching prompt text inside the zip before trusting it |
| Re-check balance | 52 credits — unchanged, confirms downloads cost 0 as expected |

No export hang was encountered (google-flow-ops flags this as common); all
three exports completed on the first click.

## 8. Replay script

**None.** This was a one-off recovery of three specific already-rendered
cards, identified by exact prompt text — there's no repeatable flow here to
script (the "flow" is "click download on a specific card and read the zip"),
and a script keyed to this project's specific card ordering would be dead the
moment the grid changes.

## 9. SKILL-CONTRADICTION

None found this task. The `google-flow-ops` "chip attach: the ⋮ menu is gone"
and asset-item selector notes were not exercised (no ingredients were
attached — no generation was fired), and the download flow behaved as the
skill's winbox section describes (edit-page navigation on download click).

## 10. Budget

- Time: well under the 45-minute budget.
- Screenshots/zooms: **9** used against an 8 budget — one over. The overage
  was a second attempt to reach the account menu after a page scroll moved
  it out of the first zoom region I tried; I did not repeat the mistake and
  did not spend further screenshots recovering from it.
- Browser actions: ~20 (well under the 40-action default cap).
