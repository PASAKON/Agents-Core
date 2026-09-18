# Every plate's image URL, as TEXT. No downloads at all.

## Why this shape

Chrome's per-tab automatic-downloads gate has now stopped two runs at 1–2 files.
That gate is a browser security decision and we do not work around it.

So this task does not download anything. It reads the image URL each tile
already has, as text, and the CTO fetches the bytes with `curl` from the shell —
which is exactly the method `google-flow-ops` already documents for video
("The download button is dead — go straight to the CDN URL"). Same method, image
tiles instead of clips. Chrome's download path is never used, so its gate never
applies.

**You will not click a download button in this task. Not once.**

## The job

Project **"AI Film"** on `flow.google.com`, `ตัวละคร` tab.

For **every** asset tile — characters, locations and props — produce one line:

```
<handle><TAB><full absolute image URL>
```

Write them all to `plate-urls.tsv` in your worktree root.

Get the URL by reading the tile's `<img>` element with `javascript_tool`, e.g.

```js
[...document.querySelectorAll('img')].map(i => i.currentSrc || i.src)
```

and pairing each with the handle text rendered on its tile. Read, never write.

**Give the URL exactly as the DOM holds it** — full and absolute, query string
and all. A signed URL stops working if a single character is dropped, and a
relative path is useless outside the browser. If a URL is a `blob:` URL, say so
for that handle rather than inventing one: a blob cannot be fetched outside the
page and that handle needs a different route.

**These four are the priority** — the CTO cannot start the shoot without them,
so get these first and make sure they are correct even if the rest run long:

`@lung_somchai` · `@nong_daeng` · `@staircase` · `@upstairs_bedroom`

Then the rest: `@grandma_pranom` `@cop_wit` `@side_wall` `@money_fold`
`@empty_pill_pack` `@qr_sign` `@fathers_phone` `@bedrail_marks`
`@noodle_shop_thriving` `@street_front` `@back_alley` `@staff_a` `@jae_muay`
`@lender_cherd` `@noodle_shop` `@prop_envelope`. Skip `@test_char3`.

## Traps

- **The grid stops re-rendering in a background tab.** Keep the tab in the
  foreground and scroll with a real wheel action; `scrollTop` does not thaw it.
  This is what made an earlier run report two assets missing that were there.
- **Do not read the credit balance.** The account menu is flaky and cost a
  previous run 25 minutes. Nothing here costs credits: you are not generating
  and not downloading.
- Never press Submit in the video composer, never open a clip.

## Budget

35 steps, 2 screenshots. Answer in text.

## Deliverable

`plate-urls.tsv` committed at the worktree root, plus
`docs/reports/banchi-plate-urls-20260918/REPORT.md` naming any handle whose URL
could not be read and why.
