# Why do shots 1, 6 and 24 fail Flow's policy classifier? Bisect it. ZERO credits.

Three shots have now been refused **eight times between them**, always with the
same uninformative text:

```
ล้มเหลว
การสร้างนี้อาจละเมิดนโยบายของเรา โปรดลองใช้พรอมต์อื่นหรือส่งความคิดเห็น
ระบบไม่ได้เรียกเก็บเงินจากคุณสำหรับการสร้างครั้งนี้
```

**Every refusal is refunded, so this costs nothing but time.** The CEO's
instruction is to keep going until the real cause is known, changing **one thing
at a time**, and then write it into the skill.

## The rule that makes this work: ONE variable per attempt

Previous attempts failed to teach us anything because each rewrite changed
several things at once. **Do not do that.** Run the ladder below in order, change
exactly one thing per rung, and record pass/fail for each. The first rung that
PASSES tells us which half the trigger is in; then narrow inside that half.

Do not skip rungs even if you think you know the answer. Do not reword anything
beyond what each rung specifies. Report the verbatim result of every attempt.

## Baseline — confirm it still fails

Submit shot 1 exactly as the sheet has it. Expect a refusal; if it PASSES,
stop immediately and report that, because then the classifier is
non-deterministic and that is the finding.

## The ladder for shot 1

Settings for every rung: **Omni 1.1 Flash · องค์ประกอบ · 9:16 · 360p · x1 · 8s.**
Use **360p** — refusals are free, but a pass at 360p costs only 6 credits instead
of 12, and a pass is what we want to reach cheaply.

| rung | change exactly this, nothing else | what a PASS would prove |
|---|---|---|
| **A** | Remove **both spoken lines** and the two `speaks Thai …` sentences. Keep everything else byte-identical. | the trigger is in the dialogue |
| **B** | Restore the dialogue. Remove only the **second** line (`อย่าเพิ่งไปที่ร้านเลยครับ ลูกผมอยู่ที่นั่น`) and its sentence. | the trigger is that line — most likely the mention of his child |
| **C** | Restore both lines. Remove only the **first** line instead. | the trigger is the first line |
| **D** | Both lines present. Replace the location block text with: `a plain indoor wall at night` (keep the `<IMAGE_REF_1>` chip attached and the reference sentence). | the trigger is the location description (dark alley before dawn) |
| **E** | Both lines present, original location. Replace the action with: `stands facing the camera and speaks`. | the trigger is the action |
| **F** | Both lines present, original everything, but detach `@side_wall` and run with only `@lung_somchai`. | the trigger involves the location plate itself |

Stop the ladder at the first rung that passes, then do ONE confirming run: put
back the thing you removed at that rung and check it fails again. **A pass that
does not re-fail when reverted proves nothing** — the classifier may just be
noisy, and that is a finding worth reporting too.

## Then do the same for shots 6 and 24, but only the rungs that matter

Once shot 1's trigger is known, test that same hypothesis first on shot 6 and
shot 24 before running their full ladders. They may share a cause: both mention
**ค่ายาแม่** (the mother's medicine money) and shot 1 mentions **ลูกผม** (my
son) — a dependent plus money distress is one hypothesis worth naming, but do
not assume it.

## Rules

- **Zero credits intended.** Refusals are refunded. If a rung PASSES it costs 6
  credits at 360p; that is expected and fine. **Hard cap 60 credits total.**
- Mute every page as the first action after it loads.
- Settings are not sticky — read them back before every submit.
- Record for EVERY attempt: rung, exact change made, submitted yes/no, verbatim
  result text, credits shown.
- Do not download anything. These are throwaway tests.
- ⛔ Never request desktop/computer-use access.

## Shot 1's full prompt, for reference — this is the baseline text

```

Use <IMAGE_REF_0> as the character reference for lung_somchai. Use <IMAGE_REF_1> as the location reference for side_wall.

In the side exterior wall of an old Bangkok shophouse before dawn — rough grey concrete with peeling paint and long water stains, an air-conditioner bracket, a rusted pipe running down to the ground, wet pavement, a single distant streetlamp <IMAGE_REF_1>, just before dawn. a Thai man of 58, lean, with a weathered square face, short greying black hair, deep-set brown eyes and light stubble, wearing a faded dark-blue cotton shopkeeper's apron over a plain white short-sleeved shirt and a worn leather watch on his left wrist <IMAGE_REF_0> — presses his back against the wall in the dark, alone, both hands open in front of him, talking fast and quietly toward the empty street.

The 58-year-old man in the dark-blue apron <IMAGE_REF_0> speaks Thai in the worn, low, gravelly voice of a tired man in his late fifties, fast and placating, and says: "ผมหาให้ครับ พรุ่งนี้เช้าผมหาให้ครบแน่นอน"
The 58-year-old man in the dark-blue apron <IMAGE_REF_0> speaks Thai in the worn, low, gravelly voice of a tired man in his late fifties, lower, pleading, and says: "อย่าเพิ่งไปที่ร้านเลยครับ ลูกผมอยู่ที่นั่น"

The face of whoever is speaking stays in frame for the whole line.
Medium shot, static camera with a slight handheld sway. Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
```

## Deliverable

`docs/reports/banchi-policy-bisect-20260919/REPORT.md`:
1. a row per attempt: rung · exact change · result verbatim
2. **the trigger, named** — or, if no rung passes, that fact stated plainly
3. a `SKILL-ADDITION:` block for `google-flow-ops` so the next script avoids it

Budget: 120 steps, 4 screenshots. Answer in text.
