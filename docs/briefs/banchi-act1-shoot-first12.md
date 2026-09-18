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

## Getting the clips out

**Do not press play with sound.** The CEO is working next to this machine. Before
playing anything, mute the page's media:

```js
document.querySelectorAll('video').forEach(v => { v.muted = true; v.volume = 0; });
```

**Do not click the download button.** Chrome's per-tab automatic-downloads gate
has stopped three runs at 1–2 files. Instead do what worked for the plates today:
collect the **signed CDN URL as text** and let the CTO fetch the bytes.

Capture each clip's id **at submit time** — it is in the submit response and in
the card — and use `read_network_requests` to catch the
`flow-content.google/video/<id>` URL at its **first** fetch. Write one line per
shot into `clips.tsv` at your worktree root:

```
<shot number><TAB><full absolute signed URL>
```

Absolute and complete, query string and all. A signed URL dies if one character
is dropped.

## Report per shot

A table: shot number · duration set · chips attached in order · credits the
estimate showed · submitted yes/no · clip id · URL captured yes/no · any error
text verbatim.

If a shot fails, say so and move to the next one. Do not retry a failing shot
more than once — three runs today were lost to repeating a broken action.

## Budget

90 steps, 6 screenshots. Answer in text. Do not review the clips, do not judge
them, do not describe what you think they look like — the CTO watches them.
