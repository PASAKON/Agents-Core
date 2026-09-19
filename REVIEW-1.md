# BL52 — CTO review: approved, with two layout changes the CEO signed off on

The cut is good. The CEO's words: "คลิปดีเลย". Gates green, seats right, nothing
bought. What follows is layout only — do not re-do the edit.

He reviewed it on his own phone, annotated two things, and I rendered mock
frames from YOUR cut until he approved the exact numbers. Both are now in the
skill (§6a and §6c) and in the kit template, so pull the skill again before you
start.

## 1. Brand bug — `right: 150px; top: 310px`

Was `right: var(--safe-right)` (240) and `top: 270`.

The 240 margin is there for the like/comment rail, and that rail starts at
y≈960 — 650px below the mark. Up here the only obstacle is TikTok's search icon
at `x 904-946, y 146-186`. At `right: 150` the logo ends at x930 with 54px of
visible frame left before the crop edge at x983, which is what he asked for:
"จดเกือบชิดขอบจอ แต่ห้ามชิดจนเกินไป ให้มีช่องว่างดูลอดผ่านได้". At `top: 310` it
clears the nav by 109px.

I first showed him `top: 350`; he said too low. **310 is the approved value** —
half that move. Do not split the difference again.

## 2. Every block above the rail is `.blk.wide`

This is the one that matters visually. `.blk` is 120 left / 240 right, so a
centred line lands on x480 while the frame's centre is 540. On a phone that
reads as leaning left with the right-hand side wasted, and that is exactly what
the CEO said: the top text "ดูเบี้ยวไปทางซ้าย" and "มันมีพื้นที่ว่างทางขวา…อยากให้ใช้
ส่วนนั้นให้คุ้มค่า".

Put the rule in `block()` so no block can miss it:

```js
var wide = (top < 900) ? " wide" : "";
var d = el('<div class="blk' + wide + ' ' + (cls || "") + '" ...');
```

**Do NOT widen everything.** I measured your cut: 18 of 40 blocks are at
top 470/520/760 and belong wide; the other 22 sit at 1090/1180/1320 and must
keep 240 or they run under the like/comment icons. Widening all of them was my
own first attempt and it was wrong.

After the change, one upper block should measure its text centre at ~540.

## Gates, then re-upload

`npm run check`, then `safezone` (I fixed two bugs in it today — it was
comparing a margin against a coordinate, and applying the rail's margin at
every height, so it will now pass `right: 150` and still catch a real one),
then look at a contact sheet, then `verify` with `--seat`.

Upload the new render to the same `Finals/` folder. Leave the old file; name
the new one so the newer is obvious. Report the new Drive link.

## Not yours to fix, recorded so you know I saw it

- **Loudness is -20.2 LUFS**, about 6 dB under what TikTok and YouTube
  normalise to. The skill has no loudness gate; I am adding one. Do not
  re-master this render by hand.
- **The on-screen pronouns.** You softened มึง/กู to คุณ/ผม citing the org's
  no-crude-language rule. That rule is about how an agent speaks, not about the
  channel's script — BL's own voice is มึง (EP7 "มึงเทรดทุกวัน…", EP8 "มึงกำลังโดน
  เอาเปรียบ", EP11 "โบรคมึงเป็น A-Book หรือ B-Book"), so the text now disagrees
  with the audio. Leave it as it is for this render; I am fixing the wording of
  the rule so the next cut does not face the same ambiguity. Flagging it was
  the right call.
