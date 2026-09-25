# ILAG Studio FB Page branding — round 1 (3 profile + 3 cover options)

Task: task-3532635c. Generation only — nothing uploaded to Facebook.

## Tool / run

`tools/chatgpt_images.py` against the Mac ChatGPT Plus Chrome (CDP `http://127.0.0.1:9223`,
profile `~/.flow-automation/chrome-profile`), driven twice:

1. First run generated 5/6 images then hit `Page.goto: Timeout 30000ms exceeded` on
   `cover-c-lotus-storm` (transient navigation timeout, not a usage-limit/refusal —
   exit code 1, run stopped cleanly per the runner's contract).
2. Re-ran the identical command; it resumed from the one ledger entry not yet `done`
   and finished `cover-c-lotus-storm` clean. No manual `--recover` needed.

Brief: `docs/briefs/ilag-page-branding-round1.json` (6 items, common negative/style
suffix appended to every prompt as given in the task).

## Out paths

`~/MoonieXHQ/Work/task-3532635c/out/`:
- `profile-a-khon.png`, `profile-b-lotus.png`, `profile-c-scales.png` (ChatGPT originals, 1254×1254)
- `cover-a-two-worlds.png`, `cover-b-khon-duel.png`, `cover-c-lotus-storm.png` (ChatGPT originals, 1536×1024)
- `<name>-1080.png` — profile resized to 1080×1080 (originals untouched)
- `<name>-circle170.png` — profile circular-mask preview at 170px
- `<name>-1640x624.png` — cover cropped to centre band, 1640×624
- `<name>-mobile.png` — centre 640×360 crop of the 1640×624 cover (how FB shows it on phone)
- `sheet.png` — 3 profile circles in a row above 3 cover crops, for the CTO to send the CEO
- `ledger.json` — the runner's own run ledger (chat URL, md5, dims, timestamp per image)

## Ledger (chat URLs, for any further same-chat edit)

| name | chat_url | dims |
|---|---|---|
| profile-a-khon | https://chatgpt.com/c/6ab5c98f-9fc8-83ec-bbc7-4f04c59158ae | 1254×1254 |
| profile-b-lotus | https://chatgpt.com/c/6ab5c9d1-86d4-83ec-90d6-4cda1264ea82 | 1254×1254 |
| profile-c-scales | https://chatgpt.com/c/6ab5ca21-baac-83ec-866d-af64b5833069 | 1254×1254 |
| cover-a-two-worlds | https://chatgpt.com/c/6ab5ca5c-c498-83ec-badf-67de1ea9caf5 | 1536×1024 |
| cover-b-khon-duel | https://chatgpt.com/c/6ab5cac6-ab00-83ec-9fa9-1c9f03ff4883 | 1536×1024 |
| cover-c-lotus-storm | https://chatgpt.com/c/6ab5cbc1-e6ec-83ec-9934-18413c96baf0 | 1536×1024 |

## What each image shows (checked by eye, small, per the task's checklist)

- **profile-a-khon**: gold serene deva mask (left) fused with a green/red fanged yaksha mask (right), one face split down the centre, black bg. No text, no Buddha/monk/temple, no banknotes/police. Split reads clearly even shrunk to the 170px circle preview.
- **profile-b-lotus**: white-gold lotus, left half glowing warm, right half turning into black thorny vines dripping into dark water, black bg. Clean split, reads at 170px.
- **profile-c-scales**: golden Thai-style balance scales with kanok ornament, lotus in the left pan, black chains in the right pan, black bg. Reads at 170px; beam sits close to level rather than sharply tipped toward the lotus, but still legibly good-vs-evil at a glance — not flagged as a fix, just noted.
- **cover-a-two-worlds**: one street split by a beam of light — warm lantern-lit golden-hour village/lotus pond (left) vs. rain-soaked night street with red neon and a faceless umbrella figure (right). No faces, no text, subjects sit inside the safe centre band.
- **cover-b-khon-duel**: golden deva mask and green/red yaksha mask facing off across a dark frame, kanok-shaped smoke dividing them.
- **cover-c-lotus-storm**: one pond, calm sunrise lotus bloom (left third) fading through a gradient into a stormy, thorny, lightning-lit dark third (right).

None of the 6 needed a `--continue` fix — all passed the eye-check first pass (no text/letters, no Buddha/monk/temple interior, no banknotes/coins/police, clear good-vs-evil split, profile still readable shrunk to 170px). 0 of the 2-fixes-per-image budget used.

## Rejected / not used

Nothing rejected — all 6 first-pass generations were accepted as delivered by the task brief.

## Not done (out of scope per task)

- No upload to Facebook (explicitly forbidden by the task).
- No touching Chrome CDP 9230 (another worker's FB posting session).
- Images themselves are not committed to git (media policy) — they live under `~/MoonieXHQ/Work/task-3532635c/out/`.
