# task-49212605 — Replace broken Reel post, blocked at video attach

BLOCKED before publish. Nothing was published, nothing was deleted, nothing on
the Page changed. Signed in as **Dorsine Gobb**, Meta Business Suite, Page
"ละครสั้นคุณธรรม by ILAG Studio" (asset_id 1319535331240503), 2026-09-24
~22:10–22:20.

## What happened, in order

1. Inputs verified before starting:
   - Caption file `docs/scripts/banchi-reels-caption.txt` read, matches task brief verbatim.
   - Cover `~/Downloads/ปก-A-จุดจบของเจ้าหนี้นอกระบบ.png` — 2,297,495 bytes, md5
     `1adb0b6f1b3e5c89ebb71d5294377195` — **matches the task brief exactly.**
   - Video `~/Downloads/จุดจบของเจ้าหนี้นอกระบบ-FINAL.mp4` — 844,812,552 bytes —
     **matches the task brief's size exactly** (md5 not computed — file is too
     large to hash quickly and the size match alone was enough to proceed).
2. Selected Mac Chrome (`chrome_device_id` from `config/hosts.yaml`), opened a
   fresh tab, claimed it in `tab_registry.py`, muted the page (one-shot
   `video,audio` mute + MutationObserver, per skill).
3. Business Suite → Home → confirmed correct Page → clicked "สร้างคลิป Reels".
   Reels composer opened cleanly.
4. **Route (a), media library — checked and NOT available.** The composer's
   media section has exactly one control, "เพิ่มวิดีโอ" (Add video), with no
   dropdown/menu and no "เลือกจากคลังสื่อ / คลังเนื้อหา" option next to or under
   it. `find` confirmed only the single button exists; there is no library
   picker in this composer for a brand-new Reel upload.
5. Clicked "เพิ่มวิดีโอ". This opens a **native OS file-open dialog directly**
   (no in-page menu first). Confirmed via `javascript_tool`:
   `document.hidden` flipped to `true` / `visibilityState: "hidden"` immediately
   after the click, while `document.hasFocus()` stayed `true` — the page was
   occluded by a system-level dialog outside the page's own DOM.
6. **Route (b), computer-use on the native dialog — not available in this
   session at all.** Searched the full deferred-tool list (`ToolSearch`) for
   any OS-level/system-wide "computer" tool; the only one present is
   `mcp__claude-in-chrome__computer`, which is scoped to a Chrome **tab** via
   CDP (screenshot/click/type all take a `tabId` and act on that tab's
   rendered page). It cannot see or interact with a native OS dialog that
   isn't part of the page's own render tree:
   - `computer:screenshot` while the dialog was open returned the **cached
     page content underneath**, not the dialog — i.e. it can't even see it.
   - `computer:key Escape` (sent to the tab) had no effect — `document.hidden`
     was still `true` afterward.
   - There is no separate "request access for Google Chrome" grant call
     available to invoke; the capability itself does not exist in this
     session's toolset, so there was nothing to request access to.
   This is a stronger finding than the skill's anticipated "computer-use
   refuses because browsers are read-tier" — here there is no computer-use
   tool of any kind, tab-scoped or system-wide, that can touch a native
   dialog.
7. The dialog was still open and blocking the tab. A `navigate` call to the
   same URL (attempting a reload, to force-clear the stuck dialog) returned an
   error ("blocked by a Leave site? dialog — unsaved changes"), but as a side
   effect **the native file dialog was dismissed** — `document.hidden` read
   `false` again afterward and the composer was back to its empty pre-upload
   state, no video attached.
8. Per the task's step 2c: **stopped.** Clicked "ยกเลิก" (Cancel) on the
   composer, confirmed "ทิ้งการเปลี่ยนแปลง" (discard changes — there were none
   to lose, no video had attached) to close it cleanly. Landed back on
   Business Suite home. **No publish, no edit, no delete performed anywhere.**
9. Released the tab (`tab_registry.py done`), closed it.

## State of the two posts — unchanged from before this task

- **New post: none created.** Never reached caption/cover/AI-label/publish —
  blocked at the very first step (video attach).
- **Broken post (content_id `122115848307470545`): untouched, not deleted.**
  Per task rule, deletion only happens *after* the new post verifies clean —
  that never happened, so this was correctly left alone.

## Why this needs the CEO, not another automated attempt

The video is 844,812,552 bytes. `file_upload` caps at 10 MB combined per call,
so it can never carry this file regardless of the input's `ref` — confirmed by
skill field notes from an earlier task (task-fe56cab4) with the same
constraint. The only route Meta's own UI offers is the native OS picker, and
this session has no way to drive a native OS dialog — not "restricted", just
absent from the toolset. This is a tooling gap, not a retry-with-a-different-
technique situation, so grinding on it further would not help.

## What the CEO needs to do

When back at the screen: open Business Suite → the Page → "สร้างคลิป Reels" →
click "เพิ่มวิดีโอ" → pick `~/Downloads/จุดจบของเจ้าหนี้นอกระบบ-FINAL.mp4` in the
picker himself. After that, a worker can resume from step 3 (caption paste,
cover upload via `file_upload` since the 2.3 MB cover is well under the 10 MB
cap, AI-label toggle, publish) — or he may prefer to finish the post himself
end-to-end given the video attach already needs his hand.

## Replay Script

`none`. This run never got past the file-attach step, so there is nothing
repeatable to script yet. If a future run gets the CEO to attach the video and
hands off the rest (caption/cover/AI-label/publish) to a worker, *that* tail
end is scriptable and should be captured then — the fragile parts observed so
far: the "เพิ่มวิดีโอ" button ref, the discard-changes confirm dialog's two
buttons ("แก้ไขต่อไป" continue-editing vs "ทิ้งการเปลี่ยนแปลง" discard), and the
Reels composer URL
(`business.facebook.com/latest/reels_composer/?ref=biz_web_home_create_reel&asset_id=1319535331240503`).

## Screenshots

None saved to disk — none were needed to prove the blocker; the `document.hidden`
/ `document.hasFocus()` JS reads were the evidence, at ~15 tokens each instead
of a screenshot. Two screenshots were taken to look at (composer empty state,
discard-changes confirm dialog) but not saved — neither was disk-worthy
evidence beyond what the JS check already proved.
