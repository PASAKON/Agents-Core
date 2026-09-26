# Brief — publish film 3 «น้ำไม่เลือกบ้าน» as one Reel + first comment

**The job:** PUBLISH one new Reel on the Page «ละครสั้นคุณธรรม by ILAG Studio», then POST the
first comment as the Page. This is not a check or a rehearsal: the CEO ordered the post.

CEO, 2026-09-27: "ถ้าคุณเห็นว่าผ่านครบหมดแล้ว ให้ เขียน Caption ส่ง Worker Upload + Comment ได้เลย ทันที"
The CTO has audited the film and written the caption.

## Inputs (all exist on the Mac)

| what | path |
|---|---|
| video (1080×1920, ~10:26, 78 shots) | `/Users/gob/Desktop/ep3-FINAL/ep3-FINAL.mp4` |
| cover | `/Users/gob/Desktop/ep3-cover/poster-c-rain.png` |
| caption | `docs/scripts/ep3-reels-caption.txt` |
| first comment | `docs/scripts/ep3-first-comment.txt` |

The tool is `tools/fb_reel_post.py`, merged from task-cfdc75a8 (ee811ec0). It uses Chrome on
CDP `:9230`, which is signed in and already running. Python is
`/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python`. Asset id `1319535331240503`. Leave the
page id and page name at their defaults.

## Steps: three runs at most, in this order

1. `curl -s http://127.0.0.1:9230/json/version` must answer. If it does not, stop and report.
   Do not launch Chrome and do not quit it.
2. **Dry run:**
   `… tools/fb_reel_post.py --asset-id 1319535331240503 --video <video> --cover <cover> --caption-file docs/scripts/ep3-reels-caption.txt --dry-run --screenshot docs/reports/<task-id>/dryrun.png`
   Continue only if it exits 0 and prints `caption readback matches: True`.
3. **Publish, exactly once:** the same command without `--dry-run`, plus
   `--first-comment-file docs/scripts/ep3-first-comment.txt`, with the screenshot saved to
   `docs/reports/<task-id>/publish.png`.
4. **Read the exit code:**
   - `0` = verified. Done.
   - `6` = published but unverified. Do NOT publish again. Run `--resolve-permalink` once, later.
   - `7` = the comment's author could not be confirmed. Stop and report. Do not retry.
   - Any other code: stop and report the last 30 lines of output.

   Only if step 3 exited 0 and printed that the comment was NOT posted, you may run
   `--comment-only --permalink <url> --first-comment-file …` once.

## Hard rules

- **Publish once only.** Never pass `--allow-repost`. Never edit, re-publish or delete any post.
  That includes the old `[TEST-a151e260]` test post: the CEO handles it.
- **No exploration scripts and no extra tabs.** On 2026-09-26 a worker on this exact Page opened
  tabs in a loop, and the CEO stopped it. If the tool fails, report it; do not dig into the page.
- Do not touch any other tab in `:9230`.

## Report — `docs/reports/<task-id>/REPORT.md`

Include:
- the public permalink;
- the exit code of every run;
- `caption readback` and `cover set`;
- whether the comment shows under the Page's name, and whether it is pinned;
- the screenshot paths;
- a `## Skill learning` section.
