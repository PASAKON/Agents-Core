# `@nong_daeng_suit` — and a free experiment: reference image vs description

## The job

Make ต้น's job-hunting wardrobe plate. Do it **twice, two different ways**, and
report which one held his face better. Images are free, so the second arm costs
nothing but a few minutes and settles a technique question that affects every
future asset in this production.

Project: **"AI Film"** on `flow.google.com`. Model **Nano Banana Pro**. Read the
credit balance at the start and at the end — image generation has measured 0
credits every time and must stay that way. Never press Submit in the video
composer.

## The question being settled

Every character variant so far has been made by **describing** the character
from scratch. The CEO's proposal is to instead **attach the existing plate as a
reference** and change only the clothes — which should hold the face far better.

The reason this is not obvious: a rule already in the skill says **the prompt
overrides the reference image**. So if arm A attaches the reference *and* repeats
the full face description, it is not testing anything — it is description-mode
with a picture attached. **Arm A's prompt must say almost nothing about his
face.** That is the whole design.

## Arm A — reference-led (the one we expect to win)

Attach **`@nong_daeng`** as a reference and generate with a prompt that changes
only the wardrobe. Say nothing about his face, hair, age or build — the reference
is supposed to carry all of it:

> `<IMAGE_REF_0>` wearing a plain inexpensive dark-grey suit jacket over a white
> shirt with an open collar and no tie, the jacket a little loose on the
> shoulders. Same man, same face, same hair. Plain neutral studio background.
> Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural
> light.

If the reference cannot be attached in image mode, **say so explicitly and how
you tried** — that is a finding worth as much as the image, and it is not
currently recorded anywhere.

## Arm B — description-only (the control)

Same shot, no reference, the full block from `docs/scripts/banchi-ACT1.data.py`:

> a Thai man of 24, slim, oval-faced, with thick black hair swept back, dark
> brown eyes, clean-shaven, in a plain inexpensive dark-grey suit jacket over a
> white shirt with an open collar and no tie, the jacket a little loose on the
> shoulders. Plain neutral studio background. Contemporary Thai realist drama,
> shot on 35mm, desaturated colour, natural light.

## What to do with the two results

1. Download **both** to `~/Desktop/banchi-plates/` as `nong_daeng_suit_A_ref.png`
   and `nong_daeng_suit_B_desc.png`. Also make sure `nong_daeng.png` (the
   original) is there — the comparison is meaningless without it.
2. **Do not pick a winner.** You have no eye and the CTO does; your job is to
   produce both and describe *mechanically* what differed — whether the
   reference attached at all, how many attempts each took, any error text.
3. Leave BOTH in the project. Do not rename either to `@nong_daeng_suit` yet —
   the CTO names the winner after looking at them.

## Budget

40 steps, 3 screenshots. Answer in text.

## Deliverable

`docs/reports/banchi-suit-plate-20260918/REPORT.md`:
1. whether a reference image could be attached in image mode, and the exact path
   that worked (or every path that failed)
2. attempts needed per arm
3. both file paths and sizes on disk
4. credit balance before and after
5. `SKILL-ADDITION:` block if the reference-in-image-mode path is real — it is
   not in `google-flow-ops` today
