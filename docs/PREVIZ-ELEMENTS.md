# Previz as Higgsfield Elements — the two-operator split

CEO, 2026-09-04. Uploading a previz and verifying it in Higgsfield is the slow,
flaky half of generating a clip: on 2026-09-04 one operator spent 36 minutes on
a single stalled upload and fired nothing, and the same scene had stalled the
same way in the previous wave. That work has no business sitting in front of
the composer.

So it moves out. Previz go into Higgsfield **once**, as video Elements, done by
an operator whose whole job is uploading and verifying. Everyone who writes and
fires prompts refers to a previz by `@handle`, types it, and never opens a file
picker.

## The three facts this rests on

Two came from the CEO on 2026-09-04, one is measured and already in the skills.

1. **A video Element does not consume a reference slot.** It is counted
   separately from image Elements, so no sheet has to drop a character to make
   room.

   > **The six-reference cap is dead — CEO 2026-09-05, "ใส่มาให้หมดทุกคนเลย".**
   > It was never a platform limit. I invented it after S2P take 1 came back
   > missing Valder and I blamed "thirteen Elements, the model dropped one" — a
   > diagnosis I had already recorded as probably wrong once we learned an
   > unbound chip fails silently and looks identical. Meanwhile
   > `s2p-fix1-the-tour.txt` had been binding thirteen the whole time. The cap
   > was suppressing character binding in seven sheets for no measured reason.
   > **Bind every character that has an Element.** If a render does come back
   > with people merged or missing, drop props first, then characters with no
   > beat — never someone with a line, a look or a position.
2. **A video Element's file cannot be swapped in place.** A re-rendered previz
   is always a *new* Element. This is why the version lives in the handle.
3. **The Unlimited render slot is one generation, account-wide, and a second
   fire is refused by a toast rather than queued.** Uploading an Element is not
   a generation, so the uploader never touches that slot — which is precisely
   why these two roles can run at the same time when nothing else can.

## The handle

```
project_absence_previz_<scene>_v<n>
```

`<scene>` — the scene id lowercased. The reverse angle is its **own token**:

| file | handle |
|---|---|
| `S2N-Render.MP4` | `project_absence_previz_s2n_v1` |
| `S2NB-Render.MP4` | `project_absence_previz_s2n_b_v1` |
| `S2b-Render.MP4` | `project_absence_previz_s2b_v1` |
| `S2b-Split-Render.MP4` | `project_absence_previz_s2b_split_v1` |
| `S2Eb-Render.MP4` | `project_absence_previz_s2eb_v1` |

Keeping `_b` separate is not decoration. `S2b` is the phone call and `S2B`
would be the reverse angle of `S2` — lowercase them naively and two unrelated
scenes claim one Element, which is invisible inside Higgsfield. Only an
uppercase trailing `B` on an uppercase stem is treated as an angle, so `S10b`,
`S12a` and `S2Eb` keep their own letters.

`<n>` — starts at 1, **bumped on every byte change, never reused**. That single
rule is what makes a stale reference impossible rather than merely unlikely: the
sheet names `_v3`, so firing against `_v2` is not something an operator can do
by forgetting.

## The registry

`docs/previz-elements.tsv`, one row per previz, generated — never hand-written
except for the status column.

```
handle · scene · angle · file · md5 · frames · duration_s · status · updated
```

`status` is `pending` (needs uploading), `live` (in Higgsfield, verified),
`stale` (superseded by a newer version), or `cancelled` (never upload — DH1-DH4
are cancelled by standing decision).

```bash
python3 scripts/previz/register.py            # report drift, write nothing
python3 scripts/previz/register.py --write    # update the registry
```

Run it after **every** render. It hashes each file, bumps the version where the
bytes moved, and refuses to write a registry in which two files claim one
handle — a check that caught a real collision on its first run
(`S7-Blender.MP4` against `S7_previz_16x9.mp4`).

## The two roles

Both may be live at once, in separate Chrome tabs, because the uploader never
generates. `tab_guard` is registered in `~/.claude/settings.json` and will deny
either one closing or hijacking the other's tab.

### Operator P — previz uploader

1. `python3 scripts/previz/register.py` and read the pending rows.
2. Upload **only the handles the task names.** 58 rows are pending and roughly
   half are cited by no live sheet; uploading everything is waste.
3. Create each as a video Element under its exact handle, character for
   character.
4. Verify: the Element exists, plays, and its duration matches `duration_s`.
5. Set the row to `live`, commit the registry.
6. Never fires a generation. Never opens the composer.

### Operator G — generator

1. `git merge origin/main`, then read the sheet.
2. The sheet names the handle. Confirm the registry says `live` for it —
   `grep <handle> docs/previz-elements.tsv`. If it says `pending`, stop and
   report; do not fall back to attaching the file.
3. Type `@handle` with the other Elements, set the six fields, confirm the
   struck-to-zero price, fire.
4. Never uploads a video. Never touches a file input.

## What changes in a prompt sheet

One line. The paragraph that reads

> the reference video (Video 1) is the CAMERA AND BLOCKING REFERENCE for this
> shot — a 20-second grey previz of this exact scene.

becomes

> `@project_absence_previz_s2n_v1` is the CAMERA AND BLOCKING REFERENCE for this
> shot — a 20-second grey previz of this exact scene.

Nothing else moves: the Element list, the position map, the negatives and the
scaffolding clause are all unchanged.

## When the upload is down — the CEO's escalation ladder

CEO, 2026-09-05, after the video-reference upload hung for two and a half hours
and stopped the whole queue. The queue keeps moving; degraded blocking beats no
footage.

**No clip is ever skipped, and every clip gets its own upload attempt.** Run
this loop per clip, for as long as the outage lasts:

1. **Attach the previz and wait — 10 to 20 minutes, no more.**
2. **If it resolves:** fire normally, with the previz. The outage is over for
   now; keep using it on every following clip until it hangs again.
3. **If it has not resolved: FIRE THAT CLIP ANYWAY, WITHOUT THE PREVIZ.** Do
   not skip it and do not park it. Flag the take, file it, move on.
4. **On the next clip: RELOAD THE PAGE ONCE**, then go back to step 1.

Do not retry the same clip with another file, another tab, or a remux —
task-c6bec902 spent half an hour proving three files across two tabs all hang
and that a faststart remux changes nothing. One attempt per clip is the whole
budget; the retry is the *next* clip, which is why the loop never stalls.

⚠️ **RELOAD THE TAB. DO NOT RESTART CHROME.** Restarting it once tonight brought
Higgsfield back **logged out** and cost the queue several hours (task-2df7d670).
A page reload is free; a browser restart needs the CEO to sign in again.

Because each clip retries independently, the moment the endpoint recovers the
very next clip picks it up automatically — nobody has to notice or intervene.

Firing without it is a real cost, not a free win — the previz is where camera
position and blocking come from, and prose does not carry blocking the way it
carries costume. Expect the framing and the marks to drift, flag the take
accordingly, and file it like any other. The editor decides what is usable.

Prefer the small files when probing: `S2O-Render.MP4` is 3.6 MB, against a
median of 1.47 MB and a maximum of 6.13 MB (`S2PB-Render.MP4`) across the 56
previz. Size is not the cause — the identical file uploaded fine six hours
before it started hanging — but there is no reason to probe with the largest.

## Roll it out on one clip first

Before 24 sheets are rewritten, one previz goes up as an Element and one clip
fires from it, and the result is compared against a take we already have from
the `@Video 1` path. What is being checked is not whether the handle resolves —
it is whether an Element behaves the *same way as a motion and blocking
reference* as an attached video does. Nothing in this repo documents that, and
the CEO has not tested it either. If it turns out weaker, we learn it on clip
one rather than on clip twenty, and the `@Video 1` path is still there.

`S2N` is the natural probe: it has stalled on upload twice, so it is the clip
with the most to gain.
