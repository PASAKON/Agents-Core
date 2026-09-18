# Get the twelve Act 1 clips onto disk. ZERO credits, no generation.

## The problem, stated honestly

Twelve clips exist in the **AI Film** project and the CTO cannot watch any of
them. The two paths we know both failed:

- **The in-page player never exposes a `<video>` element.** Measured on six
  separate clips, before and after reload, before and after clicking play:
  `document.querySelectorAll('video')` returns **0**. The black player area is an
  empty `<canvas>` scrub surface. `read_network_requests` never showed a
  `/video/` request — only `/image/<uuid>` filmstrip thumbnails, 28+ per clip.
  So the skill's "play it and catch the CDN URL" method does not work here.
- **Chrome's per-tab automatic-downloads permission** has stopped three earlier
  runs at 1–2 files. We do not work around that gate.

**Your job is to find a path that works, not to confirm these two don't.**
Whichever one works goes into the skill and into a replay script, so this is the
last time anyone pays to discover it.

## Try them in this order

### 1. The project's own asset listing — most likely, cheapest

When the project page loads, the app must fetch a listing of its assets to draw
the grid. That response very likely carries a media URL per asset, the same shape
as the plate URLs we already harvested successfully:

```
https://flow-content.google/image/<uuid>?Expires=…&KeyName=labs-flow-prod-cdn-key&Signature=…
```

So: open `read_network_requests` **unfiltered**, hard-reload the project page,
and read every XHR/fetch response that came back. Look for JSON carrying asset
ids and URLs. If you find one, dump the video URL for each of the twelve clip
ids below.

This is a **read**. You are looking at traffic the page made on its own — not
forging a request, not bypassing a control.

### 2. The Scenebuilder's own export

`google-flow-ops` records that `ดาวน์โหลดฉาก` inside the Scenebuilder saves a
direct `.mp4` rather than the grid card's `.zip`. If it produces a URL you can
read as text, that is as good as path 1.

### 3. One fresh tab, one clip

The Chrome gate is **per-tab and first-download-only** — a fresh tab's first
download succeeds. If paths 1 and 2 fail, report that, and say how many tabs
this task is allowed before trying it. **Do not open twelve tabs on your own
initiative.**

## The twelve clip ids

Shots 1–6 (`clips.tsv` on main has these against their shot numbers):

```
1  33b9b33a-53ad-4f5d-8dad-d0836605d01b
2  c9ed8094-65e7-4564-9d6c-6572f6e1438f
3  97073410-4c33-4a2f-b8f1-5ec78f7c09ad
4  72adbdb4-65f5-4407-9639-9d0990e84290
5  c9dd7934-9c1b-4f83-a05d-54af9de4478a
6  e513be94-693c-4fc1-a935-44560a08d4f1
```

Shots 7–12: read them from `clips-b.tsv` on main (the other operator's run).

## Also capture, whatever happens

Even if no video URL can be found, **capture the filmstrip thumbnail URLs** —
those demonstrably are being fetched, 28+ per clip, and they are frames of the
actual video. They let the CTO judge framing, faces and sets while a better path
is found. One line per thumbnail:

```
<shot number><TAB><thumbnail url>
```

## Rules

- **Zero credits. Generate nothing. Never press Submit in the composer.**
- Do not read the credit balance from the account menu (flaky, cost a run 25 min).
- `javascript_tool` for reads only.
- If you play anything, mute it first:
  `document.querySelectorAll('video').forEach(v=>{v.muted=true;v.volume=0})`.
- Two attempts at any one approach, then move to the next. Three runs today were
  lost to repeating a broken action.

## Budget

60 steps, 3 screenshots. Answer in text.

## Deliverable

1. `clip-urls.tsv` at your worktree root — `<shot><TAB><url>`, absolute and
   complete, for whatever you managed to get (video URLs preferred, thumbnails
   otherwise — say which).
2. `docs/reports/banchi-clip-retrieval-20260918/REPORT.md`: which path worked,
   exactly how, and a `SKILL-ADDITION:` block so this is written down once.
