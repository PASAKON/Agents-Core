# ILAG trailer — 3 character reference images on ChatGPT — 2026-09-24 (task-e3000e68)

Brief: `docs/ops/briefs/ilag-trailer-chatgpt-characters.md`. Previous run
(task-e78669ee) stopped at the ChatGPT login; the CEO logged ChatGPT in on
winbox Chrome himself before this task started, so login was never touched
here.

## Machine / lease

Ran directly on winbox (this worktree's own machine — `hostname` =
`DESKTOP-3NQB2QO`, matches `hosts.yaml`'s `winbox` entry). The Mac-oriented
`scripts/pc-lease.sh` wrapper failed (`scp: Connection closed` — it assumes
an `ssh winbox` hop from a different machine, which does not apply when
already running on winbox). Called `windows/pc_lease.py` directly with the
local venv Python instead:

```
C:\Users\UsEr\cookierun-bot\.venv\Scripts\python.exe windows\pc_lease.py status|take|give-back
```

- `status` before touching anything: screen free, Cookie Run running.
- `take --who "browser_operator: chatgpt char images task-e3000e68" --minutes 60` → `OK - the screen is yours until 00:47`.
- `give-back` at the end → `OK - lease released and Cookie Run is running again (farming)`.
- **A final `status` check, run purely for this report, after `give-back` had already succeeded, found: `PC: FREE`, `Cookie Run: HELD by a human ESC (stays stopped until a human clears it)`.** This was not caused by this task — no `key`/ESC action was ever sent from this session (checked: no `computer{action:"key"}` calls at all this run), `give-back`'s own resume confirmation had already read back `bot_alive`, and `pc_lease.py`'s own comment on this exact state is `"The CEO pressed ESC while the screen was borrowed. That outranks us."` So a human (almost certainly the CEO, on the physical machine) pressed ESC sometime after this task's `give-back` returned success. Per the skill, this is a human-only hold — `app.py refuses clear_hold unless the CTO is relaying the CEO's own words` — so nothing was attempted to clear it. **Flagging for the CTO: Cookie Run is currently stopped and needs a human to clear the ESC hold before it resumes farming tonight.**

**SKILL-OVERRIDE: winbox-pc-lease :: call `scripts/pc-lease.sh` :: called `windows/pc_lease.py` directly with the local venv Python :: the wrapper's `ssh winbox` hop fails when the calling session is already ON winbox (this task's worktree lives at `C:\Users\UsEr\mooniex\worktrees\...`, winbox's own path per `hosts.yaml`); the underlying lease logic and its safety rules (never ESC, `take`/`give-back` only) were followed exactly, only the transport differed.**

`scripts/browser/tab_registry.py` also could not run from this shell (`python3`/`python` not on PATH in the Git-Bash environment used for `Bash` tool calls on this box) — not blocking since the lease made this the only browser_operator on the machine for the window, but flagging for the CTO: tab_registry ownership tracking has no working path from this box in this session's shell.

## Browser

Multiple Chromes paired to the org account; selected `815ddf16-36ea-4e0d-827a-f51e9ff85351` (winbox-chrome) per `config/hosts.yaml`'s `chrome_device_id` for `winbox`, per skill instruction — no prompt needed.

Confirmed already logged in to chatgpt.com (Thai UI, full chat history sidebar visible) — no Google login flow, no password/2FA prompt encountered.

## The three generations

One new chat per image (fresh `tabs_create_mcp` + `navigate` to `https://chatgpt.com/` each time), prompt pasted verbatim via a clipboard-paste simulation (see REPLAY.md), no follow-up question asked by ChatGPT for any of the three, no refusal, no paywall/usage-limit/login-challenge seen at any point.

| # | prompt | chat title ChatGPT gave | saved path | size | pixel dims |
|---|---|---|---|---|---|
| 1 | char_young | "Character Reference Sheet" | `C:\mooniex\ilag-trailer\plates\char_young.png` | 2,485,593 bytes | 1536×1024 |
| 2 | char_elder | "Character Reference Sheet" | `C:\mooniex\ilag-trailer\plates\char_elder.png` | 2,559,948 bytes | 1536×1024 |
| 3 | char_mount | "Creature Reference Sheet" | `C:\mooniex\ilag-trailer\plates\char_mount.png` | 2,002,051 bytes | 1536×1024 |

ChatGPT's own text reply, all three: **image only, no supplementary text** — no caption, no commentary, no clarifying question. (The composer's own echoed prompt is visible above each image in-thread; that is the user's own message, not a ChatGPT reply.)

Visual check (screenshot, not pixel-measured) on each generated sheet: emotion labels and full-body/hero panel present and legible, character consistent across panels, matches the prompt's described features (young — orange-gold gills, coral-pink skin; elder — violet gills with the notched frill, teal-blue skin, seed-husk necklace; manta creature — sea-green mottled back, glowing lime underside, five labeled views). No text or artifacts beyond the requested panel labels observed. Not retouched or regenerated, per the brief — accepted as generated on the first try for all three.

## Stop conditions

None triggered. No upgrade/paywall/plan/payment prompt, no usage-limit message, no login challenge, at any point across all three generations.

## Lease / tabs

Lease taken before the first click, returned immediately after the third download and both cleanup tab-closes (`give-back` confirmed `Cookie Run is running again (farming)`). All three tabs opened for this task were closed before `give-back` — none left open.

## Browser Actions

- route: step 3 (open own tab) — task requires driving ChatGPT's web UI directly; no API access is authorized/available for this account from this session.
- **screenshots_taken: 8** full screenshots + **2 zoom captures** — over the brief's 6-screenshot budget. Breakdown: 2 screenshots diagnosing why the first two send-button clicks did not actually submit (image 1), 1 confirming the generated thumbnail (image 1), 1 opening the fullscreen viewer (image 1), 1 diagnosing a wrong download-icon click + 2 zooms locating the real download icon by pixel (image 1), 1 confirming image 2's thumbnail before it finished loading, 1 confirming image 2's fullscreen view, 1 confirming image 3's thumbnail (a screenshot call also hit a 30s CDP timeout once and had to be retried, still counted as one capture). Once the reliable JS-only send/download method was found (after image 1), image 2 and 3 needed far fewer diagnostic screenshots each.
- **steps_used: ~70 browser tool calls**, over the 45-step budget — the overage is concentrated in image 1's discovery phase (send button did not respond to a `find`-ref click nor a raw-coordinate click; only a direct `element.click()` via `javascript_tool` worked — see REPLAY.md). This is now documented so a script or a future operator does not need to re-discover it.
- window size: left at the browser's default (not resized) — screenshots came back at 1568×~743, no responsive-layout concerns hit (ChatGPT's composer/generation UI did not change behavior at this width).

## Do-not compliance

No login/password/2FA screen touched (never appeared). No upgrade/paywall/plan/payment control clicked. No retouching or re-generation of any of the three images. No file uploaded. Cookie Run was parked via `take`/`give-back` only — ESC never pressed.

## Files Changed

- `docs/reports/ilag-trailer-chatgpt-characters-20260924/REPORT.md` — this file.
- `docs/reports/ilag-trailer-chatgpt-characters-20260924/REPLAY.md` — click-path script notes for the next 9 images.
- (outside the repo, per brief) `C:\mooniex\ilag-trailer\plates\char_young.png`, `char_elder.png`, `char_mount.png`.

## Commits

- (pending — will commit both report files; the three PNGs are outside the repo tree per the brief's own save path and are not committed)

## Issues / Blockers

- `scripts/pc-lease.sh` cannot be used as-written when the calling session is already on winbox itself (see SKILL-OVERRIDE above) — worth a one-line note in `winbox-pc-lease` for the next same-machine session.
- `scripts/browser/tab_registry.py` has no working Python on this box's Git-Bash `Bash` tool PATH — claim/done calls both failed with `ModuleNotFoundError`/`Python was not found`. Did not block this task (sole operator, lease-enforced) but ownership tracking was effectively unavailable.

## Skill learning

- MISSING [browser-operator | no owner] : ChatGPT's composer send button (`button#composer-submit-button`) did not respond reliably to either a `find`-returned `ref` click or a raw on-screen coordinate click — both looked like they landed (no error) but the message stayed in the composer unsent. A direct `document.querySelector(...).click()` via `javascript_tool` worked every time after that. Worth a line in the skill: for ChatGPT specifically, prefer JS `.click()` on `button#composer-submit-button` / `button[data-testid="send-button"]` over ref/coordinate clicks · evidence: task-e3000e68, image 1's two failed submit attempts (screenshots `ss_83079uce6`, `ss_2969yjyds`) vs the JS click that immediately changed the URL to a new chat id.
- MISSING [browser-operator | no owner] : ChatGPT's per-image "download/save" control in the fullscreen image viewer is **not exposed in the accessibility tree** (`find` returns "no download button present") and its on-screen pixel position is easy to mis-click (it sits between a black "share" pill and a "..." menu, close together at small size). It has a stable `aria-label="บันทึก"` (Thai for "Save") that JS `.click()` hits reliably with zero pixel-hunting: `document.querySelector('button[aria-label="บันทึก"]').click()` · evidence: task-e3000e68, image 1 needed 2 zooms + 2 mis-clicks before finding this; images 2 and 3 used the JS selector directly and downloaded on the first attempt (see REPLAY.md).
