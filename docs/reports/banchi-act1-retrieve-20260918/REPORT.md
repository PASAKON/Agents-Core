# Act 1 stuck-clip retrieval — 2026-09-18

Task: retrieve 10 clips (48 total shot, 38 already downloaded) that two prior
operators charged for but never got off Flow. Zero-generation task. Balance
verified identical before and after.

**Balance before: 9,413 credits. Balance after: 9,413 credits. Delta: 0.**
No control ever showed a non-zero estimate. Nothing was clicked that generates,
upgrades, or subscribes.

## Result: 0/10 retrieved

Every one of the 10 clips reproduced the exact failure mode the prior two
operators already documented, on a fresh tab / cold browser-context session.
The task's premise — that a cold session would newly succeed where a
cache-poisoned one failed — did not hold, because the failure is server/CDN
disk-cache state shared across the whole Chrome profile, not per-tab or
per-session state. See Skill learning below.

| shot | how located | CDN URL captured | downloaded | ffprobe duration | notes |
|---|---|---|---|---|---|
| 12 | direct `/edit/<id>` from task brief | NO | NO | — | 0 video elements in DOM both attempts (direct open + reload+play). 0 `/video/` network requests either time. Matches operator A's report exactly. |
| 13 | direct `/edit/<id>` | NO | NO | — | Same as shot 12: 0 network requests on direct open and on reload+play. |
| 14 | direct `/edit/<id>` | NO | NO | — | Same as shot 12/13. |
| 16 | direct `/edit/<id>` | NO | NO | — | Same as shot 12/13/14. |
| 21 | direct `/edit/<id>` | NO | NO | — | Same as shot 12/13/14/16. All 5 of operator A's ids behave identically: player never loads, no CDN request ever appears, even with the mute-override pre-installed and a `เล่น` (play) click forced on both attempts. |
| 27 | dialogue search | NO (never located) | NO | — | Tried full dialogue `"ย่า กินข้าวก่อนนะครับ"`, and shorter fragments `"กินข้าวก่อนนะครับ"` / `"กินข้าว"` via the search box. All returned 0 results / "ไม่มีผลลัพธ์ที่ตรงกับรายการที่เลือก". Never found in the feed. |
| 30 | dialogue search — found | YES (id, not video URL — see notes) | NO | — | Search box only worked reliably when set via JS property setter + `input` event dispatch (a `computer` click+type landed in the project-rename field, not the search field, every time it was tried). Query `"อร่อยไหมครับย่า"` (exact dialogue) → 1 exact match, verified against the full prompt text before opening. Asset id `83939c4d-9c06-48a7-8f1c-3c0fc3e44eb3`. Direct open: 0 network requests. Reload + play: still 0 network requests. Classic cache trap — served from disk cache with no network entry on both attempts. |
| 33 | dialogue search — never located | NO | NO | — | Tried full sentence, `"ขึ้นมาใหม่"`, `"เดี๋ยว"` (5 unrelated matches, none this shot), `"ผมขึ้น"`, `"นะครับ"`. None matched this shot's prompt text. Same outcome as operator B's own attempt — never located in the feed. |
| 38 | dialogue search — found | YES (id, not video URL — see notes) | NO | — | Query `"มีเก็บเยอะขนาดนี้เลยเหรอพ่อ"` (exact dialogue) → 1 exact match, verified against full prompt text. Asset id `17ba700a-9f68-49a0-91ee-7a4fa88fc507`. Direct open + play: 0 network requests. Reload + play: 0 network requests. Cache trap, same as shot 30. |
| 46 | dialogue search — never located | NO | NO | — | Tried `"ผมวางไว้ตรงนี้นะลุง"` (วิทย์'s line), `"วิทย์ เอาคืนไป"` (สมชาย's line with name), `"วางไว้"`, `"นะลุง"`. All 0 results. Note: a same-fragment search for `"เอาคืนไป"` alone DID match, but it resolved to **shot 47** (`"เอาคืนไป ลุงไม่รับ"`, id `d744fe99-19e4-4db5-8307-40e959708756`) — one of the already-downloaded 38, not shot 46. Confirmed and left untouched (no download, no play beyond the one muted click already made to verify prompt text). Shot 46 itself was never located. |

**5/10 (12,13,14,16,21): player never loads, 0 network requests, both attempts.**
**2/10 (30,38): located and opened, cache-served, 0 network requests, both attempts.**
**3/10 (27,33,46): never located in the feed at all**, despite the dialogue-search
method the skill and this task both prescribe. Shot 46's search fragments only
ever matched the neighbouring shot 47 (already downloaded), which is exactly
the near-namesake trap the skill warns about for prompt boilerplate — except
here it was the *dialogue* that collided (`"เอาคืนไป"` appears in both shot 46's
and shot 47's line).

**Two attempts per clip, then stop — honoured throughout.** No clip received
more than 2 substantive retrieval attempts (direct-open + reload, or
locate-and-open + reload). Search-fragment tries for the 3 unlocatable shots
(27, 33, 46) went a few tries deep because "locating" is a different step
from "retrieving" and the task explicitly said dialogue is the way to find
them — but no clip was ever opened and retried beyond the 2-attempt cap once
located.

## Skill learning

- WRONG: The task briefed this run on the premise that "YOU ARE A FRESH SESSION
  WITH A COLD CACHE... a clip that was cache-served for the last operator will
  be fetched from the network for you, once." **This is false for a same-machine,
  same-Chrome-profile run.** Chrome's HTTP disk cache is keyed by the exact
  request URL and is shared across all tabs/sessions in one browser profile —
  it is not scoped per Claude conversation. Shots 30 and 38 were already played
  by operator B in this same Chrome, so they were still cache-served with zero
  network entries for this "cold" session too. A genuinely fresh network fetch
  would require a different Chrome profile/device, or clearing that origin's
  cache — neither of which a browser_operator should do unilaterally (clearing
  site data is a destructive, hard-to-reverse action affecting the shared
  browser). This should be corrected in `google-flow-ops`: the fix for the
  cache trap is capturing the URL **at first play, by whoever plays it first**,
  not "send a fresh session later."

- MISSING: The skill's search-box guidance ("search the feed for a distinctive
  fragment of the shot's Thai dialogue line") doesn't mention that **`find()`
  and a `computer` click on the search box reliably land in the wrong input**
  (the project-rename field, aria-label "ข้อความที่แก้ไขได้", not aria-label
  "ค้นหา") — happened 3 separate times with 3 different `find()` queries,
  including once where typed text visibly vanished into nothing observable.
  The reliable method, which should go in the skill: grab
  `document.querySelectorAll('input')[1]` (the one with class `search-input`,
  aria-label `ค้นหา`), set its value via the native property setter, and
  dispatch a real `input` event — a `computer` click+type on this field
  cannot be trusted.

- MISSING: The search index is **not** a full-text match over the raw prompt.
  Exact full-sentence dialogue quotes worked twice (shots 30, 38) but 0/many
  fragments worked for shots 27, 33, 46 — including exact substrings copied
  verbatim from the same prompt template these other two used. Some clips'
  dialogue appears to be simply unindexed by the search box (possibly tied to
  render/caption-generation state, which may be why these specific 3 clips were
  the ones nobody could ever locate — this session included). The skill should
  say plainly: **the dialogue-search method has an unexplained failure rate on
  some clips, and when it fails, more fragment variations are not the fix** —
  stop after 3-4 tries and report unlocatable, don't grind.

- MISSING: A short/common dialogue fragment can match a **different, already-
  downloaded shot with overlapping boilerplate dialogue**, not the target —
  happened with shot 46 vs shot 47 (`"เอาคืนไป"` shared by both lines). Always
  verify a search hit's full prompt text against the target shot's full
  ATTACH+dialogue line (character count, all speaker names) before opening it,
  exactly as this run did — but the skill should name this specific risk
  (dialogue collision, not just prompt-boilerplate collision) explicitly.

- COSTLY: The single most expensive detour was trying to full-text-scan the
  virtualized feed via repeated large `scrollTop` jumps and `document.body.
  innerText` reads. A tight in-page loop over many scroll positions inside one
  `javascript_tool` call **timed out at 45s after only ~6 of ~13 planned
  iterations** — each virtual-scroll jump is expensive (~7s), and this whole
  approach was abandoned once the reliable search-input fix (above) was found.
  Anyone hitting "clip not searchable" next should reach for the corrected
  search-input method FIRST, not the scroll-and-scan approach — it is
  dramatically slower for the same result and can leave the page in an odd
  scroll state.
