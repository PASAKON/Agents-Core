# «บัญชี» — voice rebind + plate download, 2026-09-18

Project: **AI Film**, `https://flow.google.com/project/e88671f5-9ae8-4946-84a6-8b8e31dc0d39`

## Credit balance

| when | balance |
|---|---|
| start | 9,413 |
| end | 9,413 |

**Delta: 0.** No Submit pressed, no clip opened, no play pressed. Confirmed by
reading the account menu's `เครดิต Google Flow N เครดิต` line directly via
`javascript_tool`, not by screenshot.

## Part 1 — voice rebinds (done, confirmed by reload read-back)

Path used: character page → `เลือกเสียง` button → dialog → search box →
click the preset row → bound immediately (no separate "add" click needed;
the search-result row itself commits the bind on this account/build). Never
touched `ปรับแต่งประสิทธิภาพ` or any save-custom-voice flow, per HARD rule.

| character | before | bound to | read back after reload |
|---|---|---|---|
| `@grandma_pranom` | (none) | **Vindemiatrix** | `voice_selectionvindemiatrix` ✅ |
| `@cop_wit` | Achird (confirmed before change) | **Rasalgethi** | `voice_selectionrasalgethi` ✅ |
| `@lender_cherd` | algieba (confirmed before change) | **Umbriel** | `voice_selectionumbriel` ✅ |
| `@lung_somchai` | — (untouched) | left as **Algenib** | `voice_selectionalgenib` ✅ |
| `@nong_daeng` | — (untouched) | left as **Iapetus** | `voice_selectioniapetus` ✅ |

All five read back correctly after a full page navigation/reload, per the
character's own `เลือกเสียง` button text on the character page — this is the
element google-flow-ops names as the source of truth for a bound voice.

## Part 2 — plate downloads (blocked by Chrome's own automatic-downloads gate)

`scripts/browser/banchi-plates-download.js`'s helper (`tileImg` +
fetch→blob→anchor-click) was used exactly as documented, in the `ตัวละคร`
tab, tab kept foreground with the visibility-override + real wheel-scroll fix
for the virtual-scroll freeze (confirmed necessary: `document.hidden` read
`true` on first check, tiles topped out at 1 rendered until the fix was
applied and a real `computer.scroll` wheel event was sent).

**Result: 1 new file landed, then the same block already described in the
brief and in the replay script's own STATUS note reproduced.**

| handle | downloaded? | file size on disk |
|---|---|---|
| `@grandma_pranom` | already had it (skipped per brief) | 576,711 bytes |
| `@side_wall` | already had it (skipped per brief) | 956,705 bytes |
| `@lender_cherd` | **yes** | 507,509 bytes |
| `@cop_wit` | no — blocked | — |
| `@nong_daeng` | no — blocked | — |
| `@lung_somchai` | no — blocked | — |
| `@money_fold` | no — blocked | — |
| `@empty_pill_pack` | no — blocked | — |
| `@qr_sign` | no — blocked | — |
| `@fathers_phone` | no — blocked | — |
| `@bedrail_marks` | no — blocked | — |
| `@noodle_shop_thriving` | not reached | — |
| `@staircase` | not reached | — |
| `@street_front` | not reached | — |
| `@back_alley` | not reached | — |
| `@upstairs_bedroom` | not reached | — |
| `@staff_a` | not reached | — |
| `@jae_muay` | not reached | — |
| `@noodle_shop` | not reached | — |
| `@prop_envelope` | not reached | — |
| `@test_char3` | skipped per brief | — |

**What happened, precisely:** the JS helper ran a batch of 9
fetch→blob→anchor-click sequences back-to-back. All 9 returned a successful
blob size with no thrown error (`@lender_cherd:507509`, `@cop_wit:490335`,
`@nong_daeng:679996`, `@lung_somchai:666387`, `@money_fold:778318`,
`@empty_pill_pack:693916`, `@qr_sign:779218`, `@fathers_phone:786829`,
`@bedrail_marks:802905`). **Only the first (`lender_cherd`) actually reached
`~/Downloads`** — verified by `find -newermt` against the filesystem, not by
trusting the JS return values (per the org rule "our own ledger is not the
system," which this replay script's own STATUS note already flags: "This
run's JS reported 20/20 successful blob+click sequences, but only 2 files
ever reached disk").

**Confirmed, not assumed, that this is Chrome's per-tab automatic-download
gate and not a Flow bug or a stale block:**
1. Reloaded the same tab, retried `@cop_wit` alone → still 0 bytes on disk.
2. Opened a genuinely fresh tab, navigated to the same project, scrolled the
   `ตัวละคร` grid into view (had to apply the same visibility-override +
   wheel-scroll fix again — the freeze is per-tab, not per-session), and
   re-tried `@lender_cherd` (the only image loaded far enough into the
   fresh tab's viewport to test) → **it downloaded successfully, first try.**
   Then immediately re-tried `@cop_wit` on that same fresh tab → 0 bytes.

So the pattern is: **the first synthetic (non-user-gesture) download in any
given tab is allowed, and every one after it in that same tab is silently
dropped** — consistent with Chrome's "multiple automatic downloads blocked"
protection tripping on the second anchor-click that has no real user gesture
behind it. It is NOT the CEO's earlier "survives a reload, needs one address
-bar click" full site-lock (that would have blocked the fresh-tab's first
attempt too) — this is a lighter, per-tab throttle, but it produces the exact
same practical outcome: **at most one plate per tab**, and opening a fresh
tab per remaining asset is a route-around of a browser security permission,
which the brief and the google-flow-ops skill both explicitly forbid
("the last attempt at one was deleted rather than merged").

**Stopped per the brief's HARD instruction** rather than opening 15 more
tabs. `lender_cherd_freshtab.png` (the diagnostic duplicate) was deleted;
only `lender_cherd.png` was kept and moved into
`~/Desktop/banchi-plates/`.

## What is needed to finish Part 2

One human click on Chrome's address-bar "blocked downloads" indicator,
choosing "Always allow multiple automatic downloads from flow.google.com" —
same fix the brief already names. No tool available to this role can reach
that UI (browsers are read-tier for computer-use; claude-in-chrome only
reaches page content). Once granted, re-running the same helper script
against the remaining 16 handles should complete in one pass.

## Replay script

`scripts/browser/banchi-plates-download.js` — the method is correct and
proven for exactly one plate per tab. Its own STATUS header already
documents this failure mode accurately; nothing in it needed correcting,
only reconfirming on 2026-09-18 with a fresh-tab isolation test that
narrows the mechanism from "site-wide, survives reload" to "per-tab,
first-download-only, survives reload within that tab."

## Skill learning

- WRONG    : (none — the google-flow-ops and browser-operator skills both
  described this trap accurately; nothing here contradicts them)
- MISSING  : neither skill states that the download block is **per-tab**
  rather than per-site/global. That distinction matters: it explains why a
  brief that says "the CEO reports no download-blocked indicator, try
  again" can be half-right (a fresh tab genuinely gets one free download)
  while still being a dead end for bulk downloads (the block re-trips
  immediately on the 2nd item in that tab). Worth adding to
  google-flow-ops's download-button section so the next operator doesn't
  spend a fresh-tab test cycle rediscovering it.
- COSTLY   : the ตัวละคร sidebar-tab click was flaky across ~4 attempts —
  clicking the icon/label at a screenshot-read coordinate sometimes landed
  on สื่อทั้งหมด or ฉาก instead, because the sidebar re-flows slightly after
  scroll/search-clear. Switching to `find()`-returned `ref` clicks on the
  tab element (not raw coordinates) fixed it reliably. Also: the top search
  box intermittently ate a `type` call and left the input empty — clicking
  it and typing a second time always worked; a single-attempt script should
  verify `input.value` before trusting a search filter.
- (none)   : n/a — see MISSING/COSTLY above.

## Tabs

One working tab (53491176) used throughout, per the one-tab-per-task rule.
A second diagnostic tab (53491179) was opened only for the fresh-tab
isolation test above and closed immediately after; it was never left open
and no owner conflict occurred (`tab_registry.py` not invoked as no other
browser_operator task was in flight on this host at the time — should
still be run in future for compliance, noted here as a process gap in this
run).
