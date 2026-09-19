# «บัญชี» องก์ 1 — shoot the first twelve shots. HARD CREDIT CAP.

This is the real shoot, not a test. The CEO is going to watch the result and
judge whether the rework worked, so every shot has to be the shot the sheet
describes.

## The sheet is the source. Do not improvise from it.

`docs/scripts/banchi-ACT1.md` in your worktree. Every shot block carries:

- a heading with its **duration** — `8s`, `6s`, `4s`, `10s`. Durations differ per
  shot on purpose; the length is set by how long the line takes to say. Set the
  duration control to match, every time.
- an **ATTACH** line giving the chips **in order**, e.g.
  `1) @lung_somchai→REF_0 · 2) @side_wall→REF_1`
- a fenced block that is **the prompt, verbatim**. Paste it whole. Do not
  shorten it, do not "clean it up", do not translate it, do not merge the lines.

## Settings, verified before every single submit

| | |
|---|---|
| model | **Omni 1.1 Flash** (not Veo) |
| mode | **องค์ประกอบ** (ingredients), not เฟรม |
| aspect | **9:16** |
| resolution | **720p** |
| quantity | **x1** |
| duration | **whatever that shot's heading says** |

None of these are sticky. The model silently reverts to the account default and
the aspect and quantity reset between prompts. **Read all six back before every
submit.** A shot fired at the wrong duration is a wasted credit and a reshoot.

## Attaching chips — the part that goes wrong

- **Order is the numbering.** `<IMAGE_REF_0>` is whatever you attached first.
  Attach in the order the ATTACH line lists, or every reference in the prompt
  points at the wrong picture and the shot is unusable while looking fine.
- **Never more than 3.** The UI accepts a 4th and silently disables it. No shot
  in this range needs more than 3.
- **Count the chips immediately before submitting.** Expanding the prompt box or
  clicking the composer's `x` clears every chip with no warning. The picker hides
  already-attached characters, so an attached one is one that has vanished from
  the list.
- **Never type a chip name from memory.** Use the picker; a near-namesake binds
  the wrong plate silently.

## Money

**HARD CAP: 70 credits for this task.** Each shot is 12 credits at 8s/720p, 9 at
6s, 6 at 4s, 15 at 10s. Your six shots should total **66**. If you are about to
cross 70, stop and report instead. A failed generation is refunded (`ล้มเหลว …
ระบบไม่ได้เรียกเก็บเงิน`) — a refund is not a reason to keep going past the cap.

Do not read the credit balance from the account menu — it is flaky and cost an
earlier run 25 minutes. Read the **live estimate in the settings panel** instead,
immediately before each submit. That is the number that matters anyway.

## Getting the clips out — use the download button

**This reverses an earlier version of this brief.** It used to forbid the
download button and tell you to sniff the signed CDN URL out of the network log.
That was wrong and it cost four runs: this player never fetches a video file at
all — it renders from ~30 filmstrip images, so there is no URL to catch. The
download button was then measured working on 10 of 12 clips in a single pass,
with no Chrome block.

**Mute the page first, every time**, before anything else. The CEO may be asleep
beside this machine:

```js
(() => { const m=e=>{e.muted=true;e.volume=0}; const a=()=>document.querySelectorAll('video,audio');
  a().forEach(m); document.addEventListener('play',e=>m(e.target),true);
  new MutationObserver(()=>a().forEach(m)).observe(document.documentElement,{childList:true,subtree:true}); })()
```

Then, once a shot has finished rendering:

1. Click its download control with a **real click** (the `computer` tool), not a
   synthetic JS `.click()`. A genuine user gesture is what keeps this from
   looking like an automated burst.
2. **Wait at least 8 seconds before the next download.** The pause is the whole
   reason this works — Chrome's per-site gate fires on rapid automatic
   downloads, not on a person clicking.
3. The file lands in `~/Downloads` with a descriptive auto-generated name.
   Append `<shot><TAB><exact filename>` to your deliverable tsv **immediately**,
   per shot. Never batch the writing to the end.

`~/Downloads` already holds many unrelated `.mp4`s — report the exact filename
per shot so the CTO can tell yours apart, and **do not move, rename or delete
anything in there.**

**If Chrome's blocked-downloads indicator appears, STOP** and report it with the
shot number you reached. Do not open extra tabs to get around it and do not
build a workaround — one run wrote a local HTTP sink for exactly that and it was
deleted rather than merged.

## Report per shot

A table: shot number · duration set · chips attached in order · credits the
estimate showed · submitted yes/no · clip id · URL captured yes/no · any error
text verbatim.

If a shot fails, say so and move to the next one. Do not retry a failing shot
more than once — three runs today were lost to repeating a broken action.

## Budget

90 steps, 6 screenshots. Answer in text. Do not review the clips, do not judge
them, do not describe what you think they look like — the CTO watches them.
