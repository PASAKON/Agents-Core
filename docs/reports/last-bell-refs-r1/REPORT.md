# THE LAST BELL — reference images round 1 (task-ede59d38)

Result: **18 of 18 images done**, zero model turns in the generation loop, no refusals, no usage limit, no re-edits.
Images and sheets are on winbox only (never in git, no Drive, no paid API).

route: step 2 (existing zero-model runner `tools/chatgpt_images.py`, CDP 9224) — the brief names it; no browser MCP call was made.

## The two sheets (winbox)

- `C:\mooniex\last-bell\sheets\characters.jpg` — the ten `ch_*` files (1600x867)
- `C:\mooniex\last-bell\sheets\world.jpg` — `loc_*`, `prop_*`, `key_*` (1599x1131, 8 plates)
- Files: `C:\mooniex\last-bell\refs\<name>.png`; ledger `refs\ledger.json`; logs `C:\mooniex\last-bell\run.log`, `run2.log`, `run3.log`.
- Sheet labels are file names, not numbers. Pick by name, e.g. `ch_yai_a`.

## Table

All files are PNG, 1536x1024. QC checks only the hard rules from the brief, not taste. Each sheet was viewed once. No ChatGPT reply text was captured, because there were no refusals.

| name | bytes | MD5 | QC | reason |
|---|---|---|---|---|
| ch_kaew_a | 2430930 | f508dc4262f8135a8471278fad7c39be | PASS | white bg, 5 numbered panels + full body |
| ch_kaew_b | 2384919 | 3f17dd34933bd1393a4f0e559bc673e9 | PASS | same |
| ch_yai_a | 2501307 | 336b5cd757c108cdf4b311faaac0bdfc | PASS | white bg, 4 numbered panels + full body |
| ch_yai_b | 2436073 | dd1aac9359fa250cf77ae82c411cad59 | PASS | same |
| ch_mek_a | 2360175 | dd7f904d39a0f167b4e69c78121e82f7 | PASS | same |
| ch_mek_b | 2286974 | ebfd572ba6a1cb5c62c06ebfb9054c69 | PASS | same (see governor_b note) |
| ch_governor_a | 2057366 | 0a64cff17cb1e19e06fb2782d4d0ac49 | PASS | same |
| ch_governor_b | 2246522 | 7b6ddf258ff587a7f3a468a25ee5ac63 | PASS | same |
| ch_naga_a | 2797056 | b7638a20fe007143bd4699f6e2c79252 | PASS | white bg, 4 numbered panels + full body; a small human silhouette in the panels for scale |
| ch_naga_b | 3130182 | c29784707fadd5c33610e716699b594e | PASS | same, human silhouette beside the full-body panel |
| loc_city | 3019994 | 6a212ac7a1c2feac51bf7c63075bf4cb | PASS | no people, no watermark seen |
| loc_bell_pavilion | 2808552 | a1649af9ab21d72afe7ff9ece10e449c | PASS | no people |
| loc_yai_house | 2534396 | 9d11e7f822770a079e8cb0b76d7e4cd1 | PASS | no people |
| loc_canal | 2775299 | c4cdfb13b5835a1bcc5a32b15bfccb0f | PASS | no people |
| prop_great_bell | 2980450 | 4846d3de387bcd7729283a28605786ab | PASS | white bg, FRONT/SIDE/BACK, no people |
| prop_mallet | 1423399 | c800212edd7b192858af98861f995abb | PASS | white bg, FRONT/SIDE/TOP, no people |
| key_bell_naga | 3219577 | e1a3d5c0234ebc1194aabbd9a7f3cbe7 | PASS | key art; Kaew in frame as the prompt asked |
| key_storm_city | 2939022 | 54eabb4747c6df31d014fd53cc23d53f | PASS | no people |

All 18 MD5s are distinct. Watermark: none visible at sheet resolution. Sheet view only, so a faint watermark could be missed.

Notes for the CEO's pick:
- Kaew sheets have 5 panels. The other sheets have 4. That is how the prompts were built, not a fault.
- Pairs `_a`/`_b` are two castings of the same prompt, as designed.

## Incidents

1. **Run 1 stopped at once:** `STOPPED at 'ch_kaew_a': signed_out — composer not present`.
   - Cause: the 9224 Chrome had been launched ~10 s before, and its only tab was the Cloudflare check "รอสักครู่...".
   - Not a real logout: the tab title became "ChatGPT" within about a minute. I re-ran the same command, and no relay-login is needed.
   - Per the playbook, I checked the tab titles (titles only, no URLs) before declaring a blocker.
2. **Run 2:** `ch_governor_b` failed with `MD5 ebfd572ba6a1cb5c62c06ebfb9054c69 matches existing file ch_mek_b.png — refusing duplicate`.
   - The runner's duplicate guard caught a wrong or stale download. It saved ch_mek_b's picture where governor_b's should be.
   - The guard worked, so nothing wrong was kept.
   - The run then died on `Page.goto: Timeout 30000ms` for chatgpt.com, probably a transient page load.
3. **Run 3** (same command): `ch_governor_b` came out with a new MD5 (and a different picture on the sheet), then the 8 remaining images finished.
   - I did not find why governor_b's first download was ch_mek_b's file.
   - Because of that, `ch_mek_b` itself was never doubted: its MD5 was unique, and on the sheet it shows a distinct "mek" casting.

## Lease and machine state

- PC lease taken 2026-10-03 00:59 local (winbox, `browser_operator: Last Bell refs`, 120 min) and given back 01:31 (about 32 min).
- Cookie Run was on a human ESC hold before, during and after. I did not touch or clear it. `give-back` printed "Cookie Run was not running when you took it, so nothing was restarted". `status` afterwards: PC FREE, Cookie Run still HELD by a human ESC.
- 9224 Chrome was started with `schtasks /Run /TN MooniexRelayChrome9224` (from Git Bash, `MSYS_NO_PATHCONV=1` is needed or `/Run` becomes a path). It is left running with one ChatGPT tab. No taskkill.
- Before the run, python.exe processes on winbox were only `infisical_setup.py`, so no other ChatGPT runner shared 9224.
- C: free about 272 GB, so the 5 GB stop condition never applied.
- Wall-clock: about 30 min for generation (roughly 2 min per image across the three runs). Budget used: 2 sheet views, 0 re-edits (limit 4), 0 screenshots for generation, 0 browser MCP calls.

## Browser Actions

steps_used 0 (runner only); screenshots_taken 0; window size n/a. Replay script: none needed, since `tools/chatgpt_images.py` is the replay script.

## Skill learning

- `[MISSING]` BROWSER_OPERATOR_Protocol_Playbook §Step order 2: a runner started right after `schtasks /Run MooniexRelayChrome9224` can report `signed_out — composer not present` on item 1 because the tab is still on the Cloudflare check ("รอสักครู่..."). Wait until `/json/list` shows a page titled "ChatGPT" (about 1 min), then re-run. The brief's "wait until /json/version answers" is not enough. (evidence: task-ede59d38 run.log; ledger entry `ch_kaew_a` signed_out at 18:00:41Z)
- `[MISSING]` same place: `schtasks /Run /TN ...` from Git Bash fails ("Invalid argument/option - 'C:/Program Files/Git/Run'"). Use `MSYS_NO_PATHCONV=1` or PowerShell.
- `[MISSING]` a ChatGPT image batch can save another item's picture under a new name (ch_governor_b got ch_mek_b's bytes). The duplicate-MD5 guard caught it and the resume fixed it. Always check the ledger for `failed` after a run, and do not trust an exit code of 0: all three runs exited 0 even when stopped or failed.
- `[MISSING]` `tools/plate_montage.py` needs Pillow, and the winbox pwvenv has none. The main repo's `.venv\Scripts\python.exe` has it, and I used that read-only.
- `SKILL-OVERRIDE`: none.
