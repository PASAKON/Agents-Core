# «บัญชี» — how to shoot a shot in Google Flow

Read this once. Everything in it was paid for by an earlier run. Nothing here is
theory; every line is something that cost credits or hours to learn.

## The deep link

https://flow.google.com — project «บัญชี». Do not navigate from the marketing
splash; go to the project directly from the project list.

## Settings — NONE of them are sticky. Set all four before EVERY fire.

| setting | value |
|---|---|
| model | **Gemini Omni Flash 1.1** — the custom voices only work on this model |
| mode | **องค์ประกอบ** (ingredients), never `เฟรม` — a voice reference errors in frame mode |
| aspect | **9:16** |
| quantity | **x1** |

Switching tabs or reloading silently resets the model to the account default.
Read every setting back off the panel before you submit. The live credit
estimate updates as you change them — read it immediately before Submit.

## Attaching chips — the hardest thing in the product

Clicking a character tile **navigates to its editor page**; it does not insert a
chip. The only path that inserts a real chip is:

> the tile's `⋮ more options` menu → click the **inner
> `<span class="label">เพิ่มไปยังพรอมต์</span>` node**, not the outer `<button>`

The outer button silently no-ops on every method. Even the correct inner-span
target is racy — budget retries, it is normal, it is not a blocker.

**Count the chips before you fire.** The picker HIDES characters that are already
attached, so an attached character is one that has DISAPPEARED from the list. A
missing chip means the shot generates with no reference and nobody finds out
until review. Max 3 chips; a 4th is silently disabled.

`<IMAGE_REF_N>` in the prompt is numbered by **chip attach order**. Attach in the
order the sheet lists them.

## The prompt

Paste it, then verify the Thai survived **byte for byte** by reading `innerText`
of the `[contenteditable="true"]` element. Do not trust what you see.

A focused contenteditable still drops the first keystroke about half the time.
Call `el.focus()` via `javascript_tool` and send the first keystroke via
`computer` **in the same `browser_batch` call**, with no tool call in between,
not even a read.

## ⛔ MUTE BEFORE ANY CLIP PLAYS — hard rule

You have no ears. A clip playing at volume is pure cost and zero information, and
the CEO hears it. Before the first clip of the session:

```js
document.querySelectorAll('video,audio').forEach(v => {v.muted = true; v.volume = 0;});
new MutationObserver(() => document.querySelectorAll('video,audio')
  .forEach(v => {v.muted = true; v.volume = 0;}))
  .observe(document.body, {childList: true, subtree: true});
```

Never report that a clip "sounds" like anything. You cannot hear it. Report what
the DOM and the files say.

## Downloading — the download button WORKS. Use it.

An earlier run banned this button from one bad observation and then burned five
runs and four hours on URL-sniffing that could never work: **the player renders
from filmstrip images and never fetches a video file.** There is no URL to catch.

- Use the top-toolbar download icon, or right-click → ดาวน์โหลด.
- A **real** click, not a JS `.click()`.
- **Leave at least 8 seconds between downloads.** Chrome's per-site "automatic
  downloads" gate fires on rapid bursts. One click with a pause is an ordinary
  download and is not gated.
- It arrives in `~/Downloads` as a `.zip` containing one `.mp4`.
- If the export hangs on "Exporting your scene…", full page reload, click again.
  Costs nothing but time.

## ⛔ NAME THE FILE THE MOMENT IT LANDS — hard rule

The zips are all called `ดาวน์โหลด (n).zip` and the mp4 names are auto-generated.
Two operators in one project feed, with no shot number anywhere on a card, once
shipped `shot-06.mp4` and `shot-25.mp4` byte-identical into a cut. It took a
whisper transcription to find.

After each download, immediately:

```bash
cd ~/Downloads && unzip -o -j "<the zip>" -d /tmp/x && \
  mv /tmp/x/*.mp4 ~/Desktop/<DEST>/shot-NN.mp4 && rm -f "<the zip>"
```

Then `shasum ~/Desktop/<DEST>/shot-NN.mp4` and record it in your tsv. A repeated
checksum means you downloaded the same card twice — say so, do not hide it.

## Refusals are refunded — and we know the cause

Google refunds credits for a refused generation. Do not treat a refusal as a
disaster and do not start rewriting on your own taste.

Two phrasings are **proven** to trip the classifier, by bisection with a
confirming revert:

1. a dependent named alongside a demand — *"อย่าเพิ่งไปที่ร้านเลยครับ ลูกผมอยู่ที่นั่น"*
2. money stated as an absolute prohibition — *"ห้ามแตะเด็ดขาด"*
3. ~~a character counting cash while saying ค่ายา~~ — **RETRACTED the same day.**
   I claimed this as proven from one natural experiment. Then shots 6 and 24,
   carrying exactly that wording, refused three times each the day before,
   rendered on the first try (15:13 and 15:28, 19 Sep). **A refusal is not
   reproducible from wording alone.** One pass/fail is not a bisection.

So the rule, which is the CEO's own method with the first step made explicit:

**If a shot is refused, RE-FIRE THE IDENTICAL PROMPT ONCE, unchanged.** Refusals
are refunded, so this costs nothing. Only a second refusal of byte-identical
text says the text is the cause. Report both attempts verbatim and move on —
do not rewrite, do not change two things at once. The CTO decides any rewrite.

## Budgets

- 60 browser steps and 6 screenshots per shot at the very most. Answer in text.
- Do NOT verify: History, the credit page beyond the two readings asked for,
  whether a finished clip "looks right" beyond one contact-sheet glance.
- Read the credit balance ONCE at the start and ONCE at the end. Report both.

## Replay script — required, not optional

You are doing the same operation more than three times. Before you report, write
`scripts/browser/banchi-flow-shoot.js` covering the mechanical steps: set the
four settings, attach N chips by handle, paste a prompt, verify it, submit, wait,
download, rename. Leave only genuine judgement to a model.

A report saying `Replay Script: none` is refused at the merge gate. If one
specific step genuinely cannot be scripted, name that step and say why.

## Report format

```
credits: start N -> end M  (delta D)
shot NN : DONE   sha256=... duration=...s
shot NN : REFUSED "<exact text Google showed, verbatim>"
shot NN : NOT ATTEMPTED (ran out of budget)
Replay Script: scripts/browser/banchi-flow-shoot.js
SKILL-CONTRADICTION: google-flow-ops :: <rule> :: <what happened> :: <date, task>
```
