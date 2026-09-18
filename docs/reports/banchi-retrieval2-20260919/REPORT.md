# Banchi CDN URL retrieval — attempt 2 (2026-09-19)

**Result: 0/12 captured.** `clip-urls.tsv` stays empty. Genuine blocker hit — not
a step-budget or clumsiness problem — full detail below.

## Per shot

| shot | id | captured? | how it was attempted |
|---|---|---|---|
| 1 | `33b9b33a-...` | no | direct `/edit/<id>` rendered `<!---->` (the known broken-render trap). Reached the project grid instead but never got back to firing play on it before the blocker below stopped everything. |
| 2 | `c9ed8094-...` | no | **played for real** — clicked the `เล่น` button, it flipped to `หยุดชั่วคราว` (pause), the on-screen clock advanced through multiple loops (`00:00:00` → `00:00:04` → `00:02:12` in MM:SS:FF, i.e. genuine looping playback). `read_network_requests` and `performance.getEntriesByType('resource')` were checked repeatedly across ~15s of real playback: **zero requests to any `flow-content.google/video/...` URL.** All that ever appears under `flow-content.google` is `/image/...` (thumbnails/filmstrip). No `<video>` element exists (confirmed via MutationObserver — matches the task brief). See "Two separate findings" below. |
| 3 | `97073410-...` | no | never successfully played — every click attempt after this point (coordinate, DOM-ref, canvas click, keyboard Space) produced no state change at all. Traced to the tab-visibility blocker below. |
| 4–17 (remaining 9: 4,5,6,11,13,14,15,16,17) | — | not attempted | stopped once the blocker was confirmed on shot 3, to avoid spending more of the one-shot cache window with no working method. |

## Two separate findings, both worth the CTO's attention

### 1. This project's compact clip player may not fetch a discrete video file at all

On shot 2, real playback ran for multiple loop cycles with the pause button
active and the on-screen clock advancing the whole time — this was not a
stalled/frozen player. Despite that, **no `/video/` request ever appeared**,
in either `read_network_requests` or `performance.getEntriesByType('resource')`.
The only `flow-content.google` traffic across the whole session was
`/image/<uuid>?...Signature=...` — roughly 30 of them per clip page, loaded
automatically on navigation, before any click. That strongly suggests this
compact canvas view renders playback from a pre-fetched frame-image sequence
(filmstrip), not a streamed MP4, for this render mode. If so, `read_network_requests`
can never produce a `/video/` URL for this player no matter how carefully it's
clicked — a different UI path (fullscreen, or the per-tile download flow that
this task explicitly forbids) may be the only place a real video byte-stream
gets requested.

I did try `เต็มหน้าจอ` (fullscreen) once on shot 2 as a probe, since the task
doesn't name fullscreen as off-limits (only Submit and the download button are
forbidden) — that is what triggered finding #2 below, so it's inconclusive
whether fullscreen itself would have produced a video fetch.

**SKILL-CONTRADICTION: google-flow-ops :: "read_network_requests on the tab —
the flow-content.google/video/<id> URL is requested even when the player
never shows it" (under "The in-page video player can fail completely") ::
On this AI Film project, on 2026-09-19, real playback (button toggled to
pause, clock visibly advancing through 2+ loop cycles) produced zero
flow-content video requests across ~15s and multiple checks, both via
read_network_requests and performance.getEntriesByType — only /image/
thumbnail requests ever appeared :: task-f5a439cc, shot 2 (c9ed8094-...),
2026-09-19**

### 2. The Chrome window stopped being the OS foreground window, and clicks silently stopped registering

After the fullscreen probe + Escape on shot 2, `document.hidden` on that tab
became permanently `true`. I closed that tab and opened a fresh MCP tab group
(twice) to rule out a per-tab glitch — **every new tab, immediately on
creation, also reads `document.hidden === true`.** `window.focus()` from
inside the page does nothing. `document.hasFocus()` flickers `true`/`false`
across calls in a way that doesn't correlate with anything I did.

While `document.hidden` is `true`: clicking the `เล่น` button (by corrected
screenshot-space coordinate, by DOM-ref, and directly on the canvas), and
pressing the Space-bar shortcut, **all produced zero effect** — button
aria-label never flips, no fetch, nothing. This is consistent and repeatable,
not a one-off miss.

I did not attempt to fix this myself: bringing a window to the OS foreground
needs desktop/computer-use access, which this task explicitly forbids
("⛔ Never request desktop/computer-use access"). This is a **hard stop**, not
a workaround-able trap — someone with desktop access needs to click the Chrome
window (or dock icon) to bring it forward before another attempt can work.

**SKILL-CONTRADICTION: google-flow-ops :: no existing entry addresses a
backgrounded/non-foreground Chrome window as a distinct failure mode (the
closest is the winbox `document.hidden` virtual-scroll note, which is about
list rendering, not play-button clicks) :: On Mac, with the MCP Chrome
extension, once the window loses OS foreground focus, real clicks (coordinate,
ref, and keyboard) on Flow's play button stop having any effect at all, and a
brand-new tab in a brand-new tab group still reads hidden:true — this needs a
human with desktop access to click the Chrome window forward :: task-f5a439cc,
2026-09-19**

## Coordinate system note (worth folding into the skill regardless of the above)

On this session, `computer` tool click coordinates were in **screenshot pixel
space**, not CSS/viewport pixel space — a `getBoundingClientRect()` rect at
1024 CSS width needed multiplying by ~1.3418 (measured: screenshot width 1374
÷ CSS width 1024) before clicking with `computer`. Clicking at the raw CSS-px
coordinates silently missed the target every time (no error, just no effect) —
indistinguishable from the visibility-blocker failure mode until worked out by
first getting a working click on shot 2. `find()`/ref-based clicks did **not**
work at all in this session (no state change on any attempt), matching the
skill's general theme of "money buttons need a trusted click" — worth
generalizing that line beyond just money buttons.

## What's needed to resume

1. A human (or a computer-use-capable session) brings the Chrome window to the
   OS foreground.
2. Re-verify `document.hidden === false` before clicking anything.
3. Before spending more of the one-shot cache window on shots 4–17, get a
   verdict from the CTO on finding #1 — if this player genuinely never
   requests a discrete video file in this mode, no amount of correct clicking
   will produce a URL, and a different capture method (or a Flow UI change) is
   needed before another operator is sent in.

## Cache status

Per the brief, the CTO cleared 788MB of Chrome disk cache specifically for
this run. Shot 2 was played for real (multiple loop cycles) with no capture —
**shot 2 is very likely burned** the same way the brief describes for repeat
plays (though notably, unlike the brief's usual failure mode, this failure
produced no cached artifact either, since nothing was ever fetched over the
network to begin with). Shots 1, 3–17 were never successfully played, so
should still be recoverable on a resumed attempt.
